"""Discord notification tests never contact Discord or use actual secrets."""
import io
import logging
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from discord_notify import send_discord_message, send_discord_payload


class Response:
    status = 201

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class DiscordNotifyTests(unittest.TestCase):
    def test_success(self):
        with (patch.dict(os.environ, {"DISCORD_TOKEN": "example-test-token",
                                      "DISCORD_CHANNEL_ID": "123456789012345678"}),
              patch("discord_notify.request.urlopen", return_value=Response()) as api,
              self.assertLogs("wca", logging.INFO) as logs):
            self.assertTrue(send_discord_message("test"))
            self.assertEqual(api.call_count, 1)
            request = api.call_args.args[0]
            self.assertEqual(request.get_method(), "POST")
            self.assertIn(b'"allowed_mentions"', request.data)
            self.assertTrue(any("notification=SENT" in msg for msg in logs.output))
            self.assertNotIn("example-test-token", " ".join(logs.output))
            self.assertNotIn("123456789012345678", " ".join(logs.output))

    def test_missing_configuration_skips_without_request(self):
        with (patch.dict(os.environ, {"DISCORD_TOKEN": "", "DISCORD_CHANNEL_ID": ""}),
              patch("discord_notify.request.urlopen") as api,
              self.assertLogs("wca", logging.WARNING) as logs):
            self.assertFalse(send_discord_message("test"))
            self.assertIn("MISSING_DISCORD_CONFIG", " ".join(logs.output))
            api.assert_not_called()

    def test_invalid_channel_id_skips_without_request(self):
        with (patch.dict(os.environ, {"DISCORD_TOKEN": "test", "DISCORD_CHANNEL_ID": "not-an-id"}),
              patch("discord_notify.request.urlopen") as api,
              self.assertLogs("wca", logging.WARNING) as logs):
            self.assertFalse(send_discord_message("test"))
            self.assertIn("INVALID_DISCORD_CHANNEL_ID", " ".join(logs.output))
            api.assert_not_called()

    def test_discord_http_status_is_safe_and_diagnostic(self):
        cases = [(401, "INVALID_BOT_TOKEN"), (403, "BOT_MISSING_CHANNEL_PERMISSION"),
                 (404, "CHANNEL_NOT_FOUND_OR_INACCESSIBLE"), (429, "RATE_LIMITED")]
        for status, code in cases:
            with self.subTest(status=status):
                failure = HTTPError("https://discord.com/api/v10/secret-endpoint",
                                    status, "HTTP Error", {},
                                    io.BytesIO(b'{"message":"private details","code":50013}'))
                with (patch.dict(os.environ, {"DISCORD_TOKEN": "example-test-token",
                                              "DISCORD_CHANNEL_ID": "123456789012345678"}),
                      patch("discord_notify.request.urlopen", side_effect=failure),
                      self.assertLogs("wca", logging.WARNING) as logs):
                    self.assertFalse(send_discord_message("test"))
                    output = " ".join(logs.output)
                    self.assertIn(code, output)
                    self.assertIn("discord_code=50013", output)
                    self.assertNotIn("private details", output)
                    self.assertNotIn("example-test-token", output)
                    self.assertNotIn("123456789012345678", output)

    def test_network_error_returns_false(self):
        with (patch.dict(os.environ, {"DISCORD_TOKEN": "example-test-token",
                                      "DISCORD_CHANNEL_ID": "123456789012345678"}),
              patch("discord_notify.request.urlopen", side_effect=URLError("network details")),
              self.assertLogs("wca", logging.WARNING) as logs):
            self.assertFalse(send_discord_message("test"))
            self.assertIn("NETWORK_ERROR", " ".join(logs.output))
            self.assertNotIn("network details", " ".join(logs.output))


if __name__ == "__main__":
    unittest.main()
