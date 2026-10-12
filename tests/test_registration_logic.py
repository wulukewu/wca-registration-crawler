import unittest

from registration_logic import (
    Config, Outcome, RegistrationError, classify_after_submit, normalize_event_url,
    parse_events, validate_config,
)


def config(**kwargs):
    values = dict(event_url="https://cubing-tw.net/event/Example2026", wca_id="2020ABCD01",
                  year="2000", month="2", day="29", email="test@example.invalid")
    values.update(kwargs)
    return Config(**values)


class ConfigTests(unittest.TestCase):
    def test_specific_event_url_only(self):
        self.assertEqual(normalize_event_url("https://cubing-tw.net/event/Example2026"),
                         "https://cubing-tw.net/event/Example2026/registration")
        self.assertEqual(normalize_event_url("https://cubing-tw.net/event/Example2026/registration/"),
                         "https://cubing-tw.net/event/Example2026/registration")
        for invalid in ("https://cubing-tw.net/event", "https://evil.example/event/Foo",
                        "https://cubing-tw.net.evil.example/event/Foo",
                        "http://cubing-tw.net/event/Foo", "https://cubing-tw.net/event/Foo?x=1",
                        "https://cubing-tw.net/event/Foo/registration/checked"):
            with self.subTest(invalid=invalid), self.assertRaises(RegistrationError):
                normalize_event_url(invalid)

    def test_config_checks_sensitive_inputs_without_logging(self):
        self.assertTrue(validate_config(config()).endswith("/registration"))
        for kwargs in (dict(wca_id="oops"), dict(month="2", day="30"),
                       dict(email="invalid"), dict(wait_minutes=0), dict(poll_seconds=1)):
            with self.subTest(kwargs=kwargs), self.assertRaises(RegistrationError):
                validate_config(config(**kwargs))

    def test_events(self):
        self.assertIsNone(parse_events("all"))
        self.assertEqual(parse_events("333,333bf,444bf"), {"333", "3bld", "4bld"})
        for raw in ("", "333,", "333,333", "333bf,3bld", "all,222", "333;222"):
            with self.subTest(raw=raw), self.assertRaises(RegistrationError):
                parse_events(raw)


class ResultTests(unittest.TestCase):
    def test_payment_pending_requires_structural_evidence(self):
        checked = "https://cubing-tw.net/event/Demo/registration/checked"
        self.assertEqual(classify_after_submit(checked, True), Outcome.SUBMITTED_PAYMENT_PENDING)
        self.assertEqual(classify_after_submit(checked, False), Outcome.UNKNOWN)
        self.assertEqual(classify_after_submit("https://cubing-tw.net/event/Demo/payment", False),
                         Outcome.SUBMITTED_PAYMENT_PENDING)

    def test_generic_page_text_is_not_proof(self):
        self.assertEqual(classify_after_submit("https://cubing-tw.net/event/Demo/registration", False),
                         Outcome.UNKNOWN)
        self.assertEqual(classify_after_submit("https://other.example/payment", True), Outcome.UNKNOWN)
        self.assertEqual(classify_after_submit("https://cubing-tw.net/event/Demo/registration/success", False),
                         Outcome.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
