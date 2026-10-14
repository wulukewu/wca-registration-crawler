"""Format one Discord status card for a whole WCA registration workflow."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from discord_notify import send_discord_payload

STATUS = {
    "SUBMITTED_PAYMENT_PENDING": ("🟠 已進入付款階段", "不是已付款或確認錄取；請確認報名名單並付款。", 0xf39c12),
    "DRY_RUN_READY": ("🟣 預覽完成（未送出）", "只完成預覽，沒有正式送出報名。", 0x9b59b6),
    "CONFIRMED": ("🟢 已取得確認", "仍請以主辦方公布的最終資格為準。", 0x2ecc71),
    "UNKNOWN": ("🚨 送出結果不明", "可能已經送出！請先查官方名單，切勿盲目重跑。", 0xe74c3c),
    "FAILED": ("🔴 自動報名未完成", "請查看錯誤階段與原因，必要時改用人工報名。", 0xe74c3c),
    "TIMEOUT": ("⏰ 等待逾時（未報名）", "沒有偵測到開放的報名入口，未執行送出。", 0x95a5a6),
    "INFRA": ("🔴 無法確認執行結果", "沒有完整的 Runner 診斷資料，請查看 Actions。", 0xe74c3c),
    "CONFLICT": ("🚨 多個 Runner 進入流程", "請立即人工核對，切勿自動重跑。", 0xe74c3c),
}
STAGE = {"INIT":"初始化","CONFIG":"設定","OPEN":"等待開放","COORDINATE":"協調",
         "IDENTIFY":"WCA ID 驗證","FILL":"填寫資料","PREVIEW":"預覽",
         "SUBMIT":"送出","VERIFY":"確認回應"}
OUTCOMES = {"SUBMITTED_PAYMENT_PENDING","DRY_RUN_READY","CONFIRMED","UNKNOWN","FAILED","NOT_SELECTED"}


def event_info():
    raw = os.getenv("EVENT_URL", "")
    try:
        u = urlsplit(raw)
        parts = u.path.strip("/").split("/")
        if (u.scheme == "https" and u.hostname in ("cubing-tw.net","www.cubing-tw.net")
                and len(parts) in (2,3) and parts[0] == "event"
                and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", parts[1])
                and (len(parts) == 2 or parts[2] == "registration")
                and not (u.username or u.password or u.port or u.query or u.fragment)):
            return parts[1], "https://cubing-tw.net/event/" + parts[1] + "/registration"
    except (ValueError, AttributeError):
        pass
    return "比賽待確認", None


def safe_events():
    raw = os.getenv("EVENTS", "all")
    if raw.strip().lower() == "all":
        return "全部可選項目（all）"
    values = [x.strip().lower() for x in raw.split(",")]
    if 0 < len(values) <= 20 and all(re.fullmatch(r"[a-z0-9]{2,12}", x) for x in values):
        return "、".join(values)[:180]
    return "項目設定待確認"


def worker_count():
    try:
        n = int(os.getenv("RUNNER_COUNT", "1"))
        return n if 1 <= n <= 5 else 1
    except ValueError:
        return 1


def run_url():
    repo, run = os.getenv("GITHUB_REPOSITORY", ""), os.getenv("GITHUB_RUN_ID", "")
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) and re.fullmatch(r"[0-9]+", run):
        return "https://github.com/" + repo + "/actions/runs/" + run
    return None


def make_card(title, description, color, more=()):
    event, link = event_info()
    mode = ("🧪 測試（不會送出）" if os.getenv("DRY_RUN", "true").lower() == "true"
            else "🚀 正式（允許送出一次）")
    fields = [
        {"name":"🧩 比賽","value":event,"inline":False},
        {"name":"🎯 項目","value":safe_events(),"inline":False},
        {"name":"⚙️ 模式","value":mode,"inline":True},
        {"name":"🖥️ Runner","value":str(worker_count())+" 台","inline":True},
    ]
    fields.extend({"name":name,"value":str(value)[:1024],"inline":inline}
                  for name,value,inline in more)
    links = []
    if link:
        links.append("[報名頁]("+link+")")
    if run_url():
        links.append("[Actions]("+run_url()+")")
    embed = {"title":title,"description":description+("\n"+" · ".join(links) if links else ""),
             "color":color,"fields":fields,
             "footer":{"text":"Cubing-TW · 非官方工具｜以網站結果為準"},
             "timestamp":datetime.now(timezone.utc).isoformat()}
    if run_url():
        embed["url"] = run_url()
    return {"content": title + "｜" + event, "embeds":[embed]}


def read_results(root):
    rows = []
    for path in sorted(Path(root).glob("registration-diagnostics-*/run-result.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            index = int(path.parent.name.rsplit("-",1)[1])
            if (not isinstance(data,dict) or data.get("outcome") not in OUTCOMES
                    or not 1 <= index <= 5):
                continue
            code = str(data.get("code",""))[:100]
            code = code if re.fullmatch(r"[A-Za-z0-9_]+",code) else "UNRECOGNIZED"
            stage = str(data.get("stage",""))
            rows.append({"index":index,"outcome":data["outcome"],"code":code,
                         "stage":stage if stage in STAGE else "INIT"})
        except (ValueError, OSError, TypeError):
            continue
    return rows


def finish_card(root):
    rows = read_results(root)
    active = [r for r in rows if r["outcome"] != "NOT_SELECTED"]
    important = [r for r in active if r["outcome"] in
                 ("SUBMITTED_PAYMENT_PENDING","CONFIRMED","UNKNOWN","DRY_RUN_READY")]
    if len(important) > 1:
        key, chosen = "CONFLICT", None
    elif len(important) == 1:
        key, chosen = important[0]["outcome"], important[0]
    elif active and all(r["code"] == "REGISTRATION_NOT_OPEN_BEFORE_TIMEOUT" for r in active):
        key, chosen = "TIMEOUT", active[0]
    elif active:
        key, chosen = "FAILED", next((r for r in active if r["code"] !=
                                    "REGISTRATION_NOT_OPEN_BEFORE_TIMEOUT"),active[0])
    else:
        key, chosen = "INFRA", None
    title, description, color = STATUS[key]
    extra = [("📊 診斷紀錄",str(len(rows))+"/"+str(worker_count())+" 台",True)]
    if chosen:
        extra += [("📍 卡住階段",STAGE[chosen["stage"]],True),
                  ("🏁 主要 Runner","#"+str(chosen["index"]),True),
                  ("🔎 結果代碼",chosen["code"],False)]
    if len({r["index"] for r in rows}) < worker_count():
        description += "\n⚠️ 部分 Runner 沒有診斷資料。"
    if os.getenv("REGISTER_RESULT") not in ("","success"):
        description += "\n⚠️ 有 GitHub 工作失敗，請檢查記錄。"
    return make_card(title,description,color,extra)


def start_card():
    waiting = os.getenv("WAIT_MINUTES","")
    duration = waiting+" 分鐘" if re.fullmatch(r"[0-9]{1,3}",waiting) else "待確認"
    return make_card("🔵 報名監控已啟動","正在等待開放；**不代表已報名成功**。",
                     0x3498db,[("⏱️ 最長等待",duration,True)])


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(message)s")
    if len(sys.argv) == 2 and sys.argv[1] == "start":
        payload = start_card()
    elif len(sys.argv) == 3 and sys.argv[1] == "finish":
        payload = finish_card(sys.argv[2])
    else:
        raise SystemExit("Use: notification_report.py start | finish RESULTS_DIR")
    send_discord_payload(payload)
