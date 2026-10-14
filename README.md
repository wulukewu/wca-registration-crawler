# WCA Registration Crawler

A Selenium-based helper for **Cubing-TW competition registration**. It runs from GitHub Actions or locally, waits for the registration window, fills the form, and (only with explicit opt-in) submits **once**.

> **Important:** This is an unofficial tool. The default is `dry_run=true` (no submission). It supports **1–5 concurrent readiness workers**, coordinated with an atomic GitHub claim so at most one proceeds to the personal-data form and Send. More workers can increase site requests and may violate competition rules; use one when multiple sessions are prohibited. The competition website's rules always take precedence; a successful CI run or preview is **not** proof of a confirmed registration.

## 快速開始｜Run with GitHub Actions

1. 到 **Settings → Secrets and variables → Actions** 檢查下方的必要 Secrets。
2. 確認 `main` 的 **Build registration image** 已成功。新版程式會使用當次 `main` commit 對應的 GHCR image，不會混用舊版 `latest`。
3. 進入 **Actions → [WCA Runner](../../actions/workflows/runner.yml) → Run workflow**，選 `main`，填寫四個欄位：

   | 欄位 | 填法 | 預設值 |
   | --- | --- | --- |
   | `event_url` | 特定比賽網址，例如 `https://cubing-tw.net/event/2026TaoyuanAirportCubeDay/registration` | 必填 |
   | `events` | 比賽**項目**代碼：`333`、`333,222,444` 或 `all` | `all` |
   | `runner_count` | `1`～`5` 台平行等待節點；**只有一台取得提交權**，不會各自送出 | `1` |
   | `dry_run` | `true`（勾選）：填表到預覽，但**不送出**；`false`（取消勾選）：真的送出 | `true` |
   | `wait_minutes` | 最多等待開放的分鐘數：`15`、`30`、`60`、`120`、`180`、`240`、`300` | `60` |

4. 測試時保留 `dry_run=true`；正式報名才改 `false`。執行後在該次 **Actions → Summary** 查看 `outcome`、階段與錯誤碼。
5. 若已觀察到送出後的付款頁，請**自行確認官方報名名單／付款狀態並完成付款**。`UNKNOWN` 時先手動確認，**不要直接重跑**。

網址可以使用 `/event/<event>` 或 `/event/<event>/registration`；程式會標準化成後者。不能只填 `https://cubing-tw.net/event`、其他網站、帶 query string 的網址，或 `/registration/select`。

### `events` 是什麼？｜WCA event IDs

**`events` 是同一場比賽中你要參加的「項目」，不是比賽場數。**

- `all`：勾選這場報名表**所有開放且可選**的項目；可能是很多項，報名費也會隨之增加。
- `333`：只報名三階。
- `333,222,444`：報名三階、二階與四階；以**英文逗號**分隔，不加引號。
- `333bf,333oh`：報名三盲與單手；程式會把部分 WCA ID 自動轉成 Cubing-TW 表單代碼。

| 項目（Event） | 建議輸入（WCA ID） | Cubing-TW 表單 ID |
| --- | --- | --- |
| 二階 2×2×2 | `222` | `222` |
| 三階 3×3×3 | `333` | `333` |
| 四階 4×4×4 | `444` | `444` |
| 五階 5×5×5 | `555` | `555` |
| 六階 6×6×6 | `666` | `666` |
| 七階 7×7×7 | `777` | `777` |
| 三階單手 3×3×3 One-Handed | `333oh` | `333oh` |
| 三階盲解 3×3×3 Blindfolded | `333bf` | `3bld` |
| 三階最少步 3×3×3 Fewest Moves | `333fm` | `3fmc` |
| 四階盲解 4×4×4 Blindfolded | `444bf` | `4bld` |
| 五階盲解 5×5×5 Blindfolded | `555bf` | `5bld` |
| 多顆盲解 3×3×3 Multi-Blind | `333mbf` | `mbld` |
| 魔錶 Clock | `clock` | `clock` |
| 五魔 Megaminx | `minx` | `minx` |
| 金字塔 Pyraminx | `pyram` | `pyram` |
| 斜轉 Skewb | `skewb` | `skewb` |
| Square-1 | `sq1` | `sq1` |

代碼參考 [WCA 官方項目規則](https://www.worldcubeassociation.org/regulations/)；第三欄是本專案根據保存的 Cubing-TW 表單所使用／推定的 ID，尤其是盲解與最少步的特殊對照。**各場比賽實際開放的項目以當次網站表單為準**。指定項目不存在、不可選時，會回報 `REQUESTED_EVENT_NOT_AVAILABLE` 並停止，不會擅自改成 `all`；`all` 也只會選目前表單中可選的項目。

例如「2026 桃園機場飛機盃」公告的八項是 `222,333,444,555,clock,pyram,skewb,sq1`。只想報名三階就填 `333`；想報名八項才用 `all`。**輸入的項目與報名費請以主辦方最新公告為準**。

### 等待時間、Runner 與成功後行為

- 單一 Runner 在等待開放時大約**每 5 秒**檢查一次；多 Runner 會依數量延長各自檢查間隔，直到開放或到達 `wait_minutes` 限制。
- 可提早數小時啟動：例如 20:00 開放、16:00 執行，可選 `300`。等待時間是**最多等多久**，不是固定延遲，也不是報名成功後還會持續執行的時間。
- 此版本整個 GitHub Actions Job 的 `timeout-minutes` 為 **350 分鐘**（少於 GitHub-hosted runner 的六小時限制）。請保留啟動與填表的緩衝；Actions 開始排程可能有延遲。
- `runner_count` 可選 `1`～`5`，每一台是獨立 GitHub-hosted Runner。多台只負責偵測開放；**第一台偵測到並成功建立 GitHub 原子提交鎖的 Runner** 才能繼續使用 WCA ID、填表和送出，其他 Runner 回報 `NOT_SELECTED` 即停止。
- 使用 `2`～`5` 時，每台會把輪詢間隔增為 `5 × runner_count` 秒（最多 25 秒），避免隨著 Runner 數量線性加快向網站請求；實際啟動時間不同，不保證各次請求平均分散。
- 若提交權持有者在送出前失敗，**不會自動轉移提交權或由其他 Runner 重試**，因為無法一律判斷是否已送出。GitHub 在所有 Runner 結束後會嘗試清除這次執行專屬的鎖。
- GitHub Actions 的 concurrency 也避免兩次**不同的 workflow run** 同時執行，但 queued/重跑仍請人工確認是否已報名。
- 報名送出時**最多點擊一次 Send**。觀察到付款階段會結束；送出後結果不明也會結束，**不會自動重送**。但目前**沒有**在送出前自動查詢「你是否早就報名成功」的功能。
- **網站規範優先**：有些賽事明確警告多分頁／重複報名可能被視為異常操作，即使這裡只有一台會送出，其他平行瀏覽器也可能被認定為多工作階段。對此類比賽請設 `runner_count=1`，不要為了增加機率而頻繁重跑。

### 結果怎麼看？｜Outcomes

| `outcome` | 意義 | Exit code | 你的下一步 |
| --- | --- | --- | --- |
| `NOT_SELECTED` | 另一台 Runner 已取得本次提交鎖；這台沒有填表或送出 | 0 | 查看取得鎖的 Runner 最終結果 |
| `DRY_RUN_READY` | 已填表並到達預覽，**沒有送出** | 0 | 正式報名須另行以 `dry_run=false` 執行 |
| `SUBMITTED_PAYMENT_PENDING` | 偵測到舊版網站結構相符的付款轉跳／交易表單；**不代表完成付款或最終錄取** | 0 | 去官方網站查報名名單並付款 |
| `UNKNOWN` | 點擊 Send 後無法證明是否已送出 | 1 | **先查官方報名狀態，切勿盲目重跑** |
| `FAILED` | 設定錯誤、等待超時、找不到欄位或表單驗證失敗 | 1 | 查 `stage`、`code` 修正原因 |

`CONFIRMED` 僅保留給未來有可驗證正式收據的情況；現有實作**不會**只憑頁面文字就宣稱已錄取。

每次執行會在 Actions Summary 和有效的 `registration-diagnostics` artifact 中保留 `run-result.json`（`outcome`、`stage`、`code`、耗時、時間戳）；artifact 保留七天。**不會上傳 HTML、畫面截圖、姓名、WCA ID、生日、Email 或報名單號**。有設定 Discord 時也會通知結果與執行連結。

## Secrets 設定與清理

到 **Settings → Secrets and variables → Actions** 設定；這些**不是**手動觸發時填的欄位：

| Secret | 是否必要 | 用途 |
| --- | --- | --- |
| `WCA_ID` | 必須 | 格式如 `2020ABCD01`（示意值） |
| `BIRTHDAY_YEAR`、`BIRTHDAY_MONTH`、`BIRTHDAY_DAY` | 必須 | 西元年、月、日；可用 `1` 或 `01` |
| `EMAIL` | 必須 | 報名用 Email |
| `PHONE` | 選用 | 網站有對應欄位時填入 |
| `DISCORD_TOKEN`、`DISCORD_CHANNEL_ID` | 選用，須成對 | Discord Bot 通知；不使用可不設定 |

以下是**本 repository 新版 workflow 不再使用**的舊 Secrets，可以在確定沒有其他用途後刪除：

- `EVENT_URL`：已改由手動執行填 `event_url`。
- `PAT`：GHCR 改用 Actions 自動提供的 `GITHUB_TOKEN`；若此 PAT 在別處共用，別直接撤銷它。
- `DISCORD_GUILD_ID`：通知現在直接使用 Channel ID。
- `NO_UI`：新版使用 `HEADLESS=true`，由 workflow 自動設定，不需要新增 Secret。

> GitHub 不允許查看 Secret 原始值；要確認值正確需重新設定或做一次受控測試。不要把個資、密碼或 Token 填在 Run workflow 的明文欄位。

## 在本機執行｜Local development

需求：Python、Chrome／Chromium 和相容的 ChromeDriver，與 `requirements.txt` 中的 Python 套件。

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

在根目錄建立不提交的 `.env`（另外填入上表中的個人資料環境變數）：

```ini
EVENT_URL=https://cubing-tw.net/event/Example2026/registration
EVENTS=333
DRY_RUN=true
HEADLESS=true
WAIT_MINUTES=60
RUNNER_COUNT=1
POLL_SECONDS=5
```

然後執行 `python main.py`。Repository 另附 `Dockerfile`，GitHub Actions 會在合併到 `main` 後建置對應 SHA 的 GHCR image。多 Runner 需要 GitHub Actions `GITHUB_TOKEN` 具有 `contents: write` 權限以建立執行專用的原子鎖，已由 workflow 的 job 權限設定處理，不必新增 Secret。

## 技術邊界與參考資料｜Limitations

- 支援 **Cubing-TW** 的既有報名流程，不支援直接在 WCA 官方網站報名，也不保證主辦方沒有更改 DOM、AJAX 或驗證方式。
- 報名頁的 WCA ID 驗證採非同步流程；程式等待驗證完成才送出下一步，並確認 Preview 有效，再決定是否送出。
- 付款、收據及最終參賽資格都需要以主辦方提供的最新資訊查核。