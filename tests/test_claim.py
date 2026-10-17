"""Fail-closed coordination behavior; never make real GitHub API calls in tests."""
import logging
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from main import Runner
from registration_claim import claim_registration, claim_already_exists
from registration_logic import Config, Outcome, RegistrationError


class Response:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


ENV = {
    "GITHUB_REPOSITORY": "example/registrations",
    "GITHUB_RUN_ID": "123456",
    "GITHUB_SHA": "a" * 40,
    "GITHUB_TOKEN": "unit-test-only",
}


class ClaimTests(unittest.TestCase):
    def test_polling_scales_with_worker_count_even_with_override(self):
        from main import load_config
        with (patch.dict(os.environ, {"RUNNER_COUNT": "4", "POLL_SECONDS": "5"}),
              patch("main.load_dotenv")):
            cfg = load_config()
            self.assertEqual(cfg.runner_count, 4)
            self.assertEqual(cfg.poll_seconds, 20)

    def test_worker_index_is_loaded_from_actions_matrix(self):
        from main import load_config
        with (patch.dict(os.environ, {"RUNNER_COUNT": "4", "RUNNER_INDEX": "3"}),
              patch("main.load_dotenv")):
            cfg = load_config()
            self.assertEqual(cfg.runner_index, 3)
            self.assertEqual(cfg.poll_seconds, 20)

    def test_initial_request_waits_for_its_slot(self):
        from main import Runner
        from registration_logic import Config

        operations = []

        class Input:
            def is_displayed(self):
                return True

        class Driver:
            def get(self, url):
                operations.append(("get", url))

            def find_elements(self, by, value):
                return [Input()] if value.startswith("input[id^=") else []

        cfg = Config(
            "https://cubing-tw.net/event/Test", "2020ABCD01",
            "2000", "1", "1", "test@example.invalid",
            runner_count=5, runner_index=3, poll_seconds=25,
        )
        runner = Runner(Driver(), cfg)
        with (patch("main.time.time", return_value=100.0),
              patch("main.time.sleep", side_effect=lambda delay: operations.append(("sleep", delay)))):
            runner.await_open("https://cubing-tw.net/event/Test/registration")
        self.assertEqual(operations[0], ("sleep", 10))
        self.assertEqual(operations[1][0], "get")
        self.assertEqual(runner.open_requests, 1)

    def test_diagnostic_summary_records_open_requests_without_personal_data(self):
        import json
        import tempfile
        from pathlib import Path
        from main import write_summary
        cfg = Config("https://cubing-tw.net/event/Test", "2020ABCD01",
                     "2000", "1", "1", "test@example.invalid")
        runner = Runner(object(), cfg)
        runner.open_started_at = 12.0
        runner.open_requests = 7
        with tempfile.TemporaryDirectory() as tmp:
            output = str(Path(tmp) / "run-result.json")
            with (patch.dict(os.environ, {"RESULT_PATH": output, "GITHUB_STEP_SUMMARY": ""}),
                  patch("main.time.monotonic", return_value=31.3)):
                write_summary(Outcome.FAILED, "OPEN",
                              "REGISTRATION_NOT_OPEN_BEFORE_TIMEOUT", 10.0, runner)
            record = json.loads(Path(output).read_text())
            self.assertEqual(record["open_requests"], 7)
            self.assertAlmostEqual(record["open_elapsed_seconds"], 19.3)
            self.assertNotIn("2020ABCD01", str(record))
            self.assertNotIn("test@example.invalid", str(record))

    def test_api_failure_logs_only_numeric_http_status(self):
        for status in (401, 403, 429, 500):
            with self.subTest(status=status):
                error = HTTPError("https://secret-host.example", status,
                                  "private response body", {}, None)
                with (patch.dict(os.environ, ENV),
                      patch("registration_claim.request.urlopen", side_effect=error) as api,
                      self.assertLogs("wca", logging.WARNING) as logs):
                    with self.assertRaises(RegistrationError) as failure:
                        claim_registration(3)
                self.assertEqual(failure.exception.code, "CLAIM_SERVICE_ERROR")
                self.assertEqual(api.call_count, 1)
                self.assertIn("http_status=" + str(status), " ".join(logs.output))
                self.assertNotIn("secret-host", " ".join(logs.output))
                self.assertNotIn("private response", " ".join(logs.output))
                self.assertNotIn(ENV["GITHUB_TOKEN"], " ".join(logs.output))

    def test_claim_observer_http_failure_logs_numeric_status(self):
        error = HTTPError("https://secret-host.example", 403, "private", {}, None)
        with (patch.dict(os.environ, ENV),
              patch("registration_claim.request.urlopen", side_effect=error),
              self.assertLogs("wca", logging.WARNING) as logs):
            with self.assertRaises(RegistrationError):
                claim_already_exists(5)
        self.assertIn("http_status=403", " ".join(logs.output))
        self.assertNotIn("secret-host", " ".join(logs.output))

    def test_single_runner_uses_no_github_claim(self):
        with patch("registration_claim.request.urlopen") as request:
            self.assertTrue(claim_registration(1))
            request.assert_not_called()

    def test_only_first_worker_wins(self):
        with patch.dict(os.environ, ENV), patch("registration_claim.request.urlopen", return_value=Response(201)) as api:
            self.assertTrue(claim_registration(5))
            self.assertEqual(api.call_count, 1)
            request = api.call_args.args[0]
            self.assertEqual(request.get_method(), "POST")
            self.assertIn(b"wca-registration-claim-123456", request.data)

    def test_duplicate_claim_stops_other_workers(self):
        conflict = HTTPError("https://api.github.com", 422, "exists", {}, None)
        with patch.dict(os.environ, ENV), patch("registration_claim.request.urlopen", side_effect=[conflict, Response(200)]) as api:
            self.assertFalse(claim_registration(3))
            self.assertEqual(api.call_count, 2)
            self.assertEqual(api.call_args_list[1].args[0].get_method(), "GET")

    def test_ambiguous_network_failure_does_not_retry(self):
        with patch.dict(os.environ, ENV), patch("registration_claim.request.urlopen", side_effect=URLError("offline")) as api:
            with self.assertRaises(RegistrationError) as error:
                claim_registration(2)
            self.assertEqual(error.exception.code, "CLAIM_SERVICE_UNCERTAIN")
            self.assertEqual(api.call_count, 1)

    def test_standby_observes_existing_claim(self):
        with patch.dict(os.environ, ENV), patch("registration_claim.request.urlopen", return_value=Response(200)) as api:
            self.assertTrue(claim_already_exists(5))
            request = api.call_args.args[0]
            self.assertIn("/git/ref/heads/wca-registration-claim-123456", request.full_url)
            self.assertEqual(request.get_method(), "GET")

    def test_standby_observes_missing_claim(self):
        missing = HTTPError("https://api.github.com", 404, "missing", {}, None)
        with patch.dict(os.environ, ENV), patch("registration_claim.request.urlopen", side_effect=missing):
            self.assertFalse(claim_already_exists(2))

    def test_missing_env_cannot_continue_to_registration(self):
        with patch.dict(os.environ, {**ENV, "GITHUB_TOKEN": ""}):
            with self.assertRaises(RegistrationError) as error:
                claim_registration(4)
            self.assertEqual(error.exception.code, "CLAIM_CONFIG_MISSING")

    def test_unexplained_422_is_not_treated_as_winner(self):
        conflict = HTTPError("https://api.github.com", 422, "invalid", {}, None)
        missing = HTTPError("https://api.github.com", 404, "missing", {}, None)
        with patch.dict(os.environ, ENV), patch("registration_claim.request.urlopen", side_effect=[conflict, missing]) as api:
            with self.assertRaises(RegistrationError) as error:
                claim_registration(5)
            self.assertEqual(error.exception.code, "CLAIM_VALIDATION_FAILED")
            self.assertEqual(api.call_count, 2)

    def test_standby_exits_before_election_when_claim_is_observed(self):
        config = Config("https://cubing-tw.net/event/Test", "2020ABCD01", "2000", "1", "1", "test@example.invalid", runner_count=3)
        runner = Runner(object(), config)
        with (patch.object(runner, "await_open", return_value=False),
              patch("main.claim_registration") as claimed,
              patch.object(runner, "identify") as identified):
            self.assertEqual(runner.run("https://cubing-tw.net/event/Test/registration"), Outcome.NOT_SELECTED)
            claimed.assert_not_called()
            identified.assert_not_called()

    def test_losing_worker_never_fills_or_submits(self):
        config = Config("https://cubing-tw.net/event/Test", "2020ABCD01", "2000", "1", "1", "test@example.invalid", runner_count=3)
        runner = Runner(object(), config)
        with (patch.object(runner, "await_open") as opened,
              patch("main.claim_registration", return_value=False),
              patch.object(runner, "identify") as identified,
              patch.object(runner, "fill") as filled,
              patch.object(runner, "preview") as preview,
              patch.object(runner, "submit") as submit):
            self.assertEqual(runner.run("https://cubing-tw.net/event/Test/registration"), Outcome.NOT_SELECTED)
            opened.assert_called_once()
            identified.assert_not_called()
            filled.assert_not_called()
            preview.assert_not_called()
            submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
