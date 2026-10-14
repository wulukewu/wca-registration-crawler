"""No network calls: validate Discord status card semantics."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from notification_report import finish_card, start_card, read_results


ENV = {
    "EVENT_URL":"https://cubing-tw.net/event/Example2026/registration",
    "EVENTS":"all", "RUNNER_COUNT":"5", "DRY_RUN":"false",
    "WAIT_MINUTES":"120",
    "GITHUB_REPOSITORY":"wulukewu/wca-registration-crawler",
    "GITHUB_RUN_ID":"12345",
}


def write_row(root, index, outcome, stage="OPEN", code=None):
    folder = Path(root) / ("registration-diagnostics-" + str(index))
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"run-result.json").write_text(json.dumps({
        "outcome":outcome, "stage":stage, "code":code or outcome,
    }),encoding="utf-8")


class NotificationCardsTests(unittest.TestCase):
    def test_start_has_clear_mode_and_no_success_claim(self):
        with patch.dict(os.environ,ENV):
            p = start_card()
        card = p["embeds"][0]
        self.assertIn("已啟動", card["title"])
        self.assertIn("不代表",card["description"])
        self.assertIn("120 分鐘",str(card["fields"]))
        self.assertIn("正式",str(card["fields"]))
        self.assertIn("5 台",str(card["fields"]))
        self.assertIn("Example2026",str(card))
        self.assertNotIn("WCA_ID",str(card))

    def test_five_runner_failure_sends_one_consolidated_card(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,ENV):
            for i in range(1,6):
                write_row(temp,i,"FAILED","OPEN","REGISTRATION_NOT_OPEN_BEFORE_TIMEOUT")
            card = finish_card(temp)["embeds"][0]
            self.assertIn("逾時",card["title"])
            self.assertIn("5/5",str(card["fields"]))
            self.assertEqual(len(finish_card(temp)["embeds"]),1)

    def test_payment_is_not_confirmed_registration(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,ENV):
            write_row(temp,3,"SUBMITTED_PAYMENT_PENDING","VERIFY")
            for i in (1,2,4,5):
                write_row(temp,i,"NOT_SELECTED","OPEN")
            card=finish_card(temp)["embeds"][0]
            self.assertIn("付款",card["title"])
            self.assertIn("不是已付款",card["description"])
            self.assertIn("#3",str(card["fields"]))

    def test_unknown_says_no_retry(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,ENV):
            write_row(temp,1,"UNKNOWN","VERIFY")
            self.assertIn("切勿盲目重跑",finish_card(temp)["embeds"][0]["description"])

    def test_dry_run_always_says_not_submitted(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{**ENV,"DRY_RUN":"true"}):
            write_row(temp,1,"DRY_RUN_READY","PREVIEW")
            card=finish_card(temp)["embeds"][0]
            self.assertIn("未送出",card["title"])
            self.assertIn("測試",str(card["fields"]))

    def test_missing_artifact_is_not_success(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,ENV):
            card=finish_card(temp)["embeds"][0]
            self.assertIn("無法確認",card["title"])
            self.assertIn("缺少",card["description"])

    def test_garbage_is_not_disclosed_in_embed(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,ENV):
            write_row(temp,1,"FAILED","FILL","unsafe<@everyone>")
            card=finish_card(temp)["embeds"][0]
            self.assertNotIn("@everyone",str(card))
            self.assertIn("UNRECOGNIZED",str(card))

    def test_duplicate_active_workers_is_flagged(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,ENV):
            write_row(temp,1,"SUBMITTED_PAYMENT_PENDING","VERIFY")
            write_row(temp,2,"DRY_RUN_READY","PREVIEW")
            self.assertIn("多個 Runner",finish_card(temp)["embeds"][0]["title"])


if __name__=="__main__":
    unittest.main()
