"""Fail-closed coordination behavior; never make real GitHub API calls in tests."""
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
