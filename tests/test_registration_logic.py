import unittest

from registration_logic import (
    Config, Outcome, RegistrationError, classify_after_submit, normalize_event_url,
    parse_events, registration_select_url, seconds_until_worker_slot, validate_config,
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

    def test_taoyuan_url_and_one_event(self):
        self.assertEqual(
            normalize_event_url("https://cubing-tw.net/event/2026TaoyuanAirportCubeDay/registration"),
            "https://cubing-tw.net/event/2026TaoyuanAirportCubeDay/registration",
        )
        self.assertEqual(parse_events("333"), {"333"})

    def test_extended_wait_window(self):
        for minutes in (15, 60, 120, 180, 240, 300):
            with self.subTest(minutes=minutes):
                self.assertTrue(validate_config(config(wait_minutes=minutes)).endswith("/registration"))
        for minutes in (0, 301, 360):
            with self.subTest(minutes=minutes), self.assertRaises(RegistrationError):
                validate_config(config(wait_minutes=minutes))

    def test_event_specific_registration_start_link(self):
        base = "https://cubing-tw.net/event/Example2026/registration"
        self.assertEqual(registration_select_url(base, "select"), base + "/select")
        self.assertEqual(registration_select_url(base, base + "/select"), base + "/select")
        for invalid in ("https://evil.example/event/Example2026/registration/select",
                        "https://cubing-tw.net/event/Another/registration/select",
                        "https://cubing-tw.net/event/Example2026/payment",
                        "https://cubing-tw.net/event/Example2026/registration/select?foo=1"):
            with self.subTest(invalid=invalid):
                self.assertIsNone(registration_select_url(base, invalid))

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


class WorkerSlotTests(unittest.TestCase):
    def test_evenly_staggered_5_workers(self):
        delays = [seconds_until_worker_slot(100, i, 5, 25)
                  for i in range(1, 6)]
        self.assertEqual(delays, [0, 5, 10, 15, 20])

    def test_staggering_scales_without_a_five_worker_assumption(self):
        # The current Actions UI still limits N to 5.
        for count in (1, 2, 3, 5, 12, 20):
            with self.subTest(count=count):
                period = 5 * count
                delays = [seconds_until_worker_slot(100 * count, i, count, period)
                          for i in range(1, count + 1)]
                self.assertEqual(delays, [5 * k for k in range(count)])

    def test_slots_do_not_shift_with_worker_start_times(self):
        self.assertAlmostEqual(seconds_until_worker_slot(111.7, 2, 5, 25), 18.3)
        self.assertAlmostEqual(seconds_until_worker_slot(119.9, 2, 5, 25), 10.1)
        self.assertAlmostEqual(seconds_until_worker_slot(100.3, 1, 5, 25), 24.7)

    def test_invalid_slot_configuration_fails_closed(self):
        for args in ((0, 1, 0, 25), (0, 0, 5, 25), (0, 6, 5, 25),
                     (0, 1, -1, 25), (0, 1, 5, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                seconds_until_worker_slot(*args)

    def test_worker_index_validation(self):
        for kwargs in (dict(runner_count=3, runner_index=0),
                       dict(runner_count=3, runner_index=4),
                       dict(runner_count=1, runner_index=2)):
            with self.subTest(kwargs=kwargs), self.assertRaises(RegistrationError):
                validate_config(config(**kwargs))
        self.assertTrue(validate_config(config(runner_count=5, runner_index=5)))


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
