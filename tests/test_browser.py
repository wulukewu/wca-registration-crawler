"""Actual headless Chrome against a local, synthetic archive-derived DOM."""
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
except ImportError:
    webdriver = None

from registration_logic import Config, Outcome


@unittest.skipUnless(webdriver and (shutil.which("google-chrome") or shutil.which("chromium")),
                     "Chrome/Selenium not installed")
class BrowserFlowTests(unittest.TestCase):
    def test_registration_landing_redirects_to_selection_form(self):
        from main import Runner
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        if shutil.which("chromium"):
            options.binary_location = shutil.which("chromium")
        driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver") if Path("/usr/bin/chromedriver").exists() else Service(), options=options)
        try:
            gate = Path(__file__).parent / "fixtures" / "registration-gate.html"
            cfg = Config(event_url="https://cubing-tw.net/event/Demo", wca_id="2020ABCD01",
                         year="2000", month="1", day="15", email="test@example.invalid",
                         dry_run=True, poll_seconds=2, wait_minutes=1)
            # file:// is allowed ONLY by this test stub. Production domain allowlisting
            # is separately verified in test_registration_logic.py.
            with patch("main.registration_select_url", side_effect=lambda _base, href: href if href.startswith("file:") and "registration/select" in href else None):
                Runner(driver, cfg).await_open(gate.resolve().as_uri())
            self.assertIn("archived-flow.html", driver.current_url)
            self.assertTrue(driver.find_element("css selector", "#WCAID_input").is_displayed())
        finally:
            driver.quit()

    def test_event_checkbox_covered_by_label_recovers_safely(self):
        # The archived fixture originally lacks overlapping labels. Simulate
        # the real-site element click interception seen on 2026-10-14.
        from main import Runner
        from selenium.common.exceptions import ElementClickInterceptedException
        import logging

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        if shutil.which("chromium"):
            options.binary_location = shutil.which("chromium")
        driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver") if Path("/usr/bin/chromedriver").exists() else Service(), options=options)
        try:
            fixture = Path(__file__).parent / "fixtures" / "archived-flow.html"
            cfg = Config(event_url="https://cubing-tw.net/event/Demo", wca_id="2020ABCD01",
                         year="2000", month="1", day="15", email="test@example.invalid",
                         events="333", dry_run=True, poll_seconds=2, wait_minutes=1)
            driver.get(fixture.resolve().as_uri())
            runner = Runner(driver, cfg)
            runner.identify()

            driver.execute_script("""
                const checkbox = document.getElementById('form_event_333');
                const rect = checkbox.getBoundingClientRect();
                const label = document.createElement('label');
                label.setAttribute('for', 'form_event_333');
                label.id = 'overlapping-label';
                Object.assign(label.style, {
                    position: 'fixed', left: rect.left + 'px',
                    top: rect.top + 'px', width: rect.width + 'px',
                    height: rect.height + 'px', zIndex: '999999',
                    background: 'rgba(0,0,0,0.05)'
                });
                document.getElementById('div_events').appendChild(label);
            """)

            # Verify the fixture really reproduces the original Selenium issue
            # before asserting the recovery path works.
            with self.assertRaises(ElementClickInterceptedException):
                driver.find_element("css selector", "#form_event_333").click()

            with self.assertLogs("wca", logging.WARNING) as logs:
                runner.fill()
            self.assertIn("EVENT_INPUT_INTERCEPTED", " ".join(logs.output))
            self.assertTrue(driver.find_element("css selector", "#form_event_333").is_selected())
            self.assertFalse(driver.find_element("css selector", "#form_event_222").is_selected())
            runner.preview()
            self.assertEqual(driver.execute_script("return window.submitClicks"), 0)
        finally:
            driver.quit()

    def test_async_wca_validation_preview_and_dry_run_never_submits(self):
        from main import Runner
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        if shutil.which("chromium"):
            options.binary_location = shutil.which("chromium")
        driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver") if Path("/usr/bin/chromedriver").exists() else Service(), options=options)
        try:
            fixture = Path(__file__).parent / "fixtures" / "archived-flow.html"
            cfg = Config(event_url="https://cubing-tw.net/event/Demo", wca_id="2020ABCD01",
                         year="2000", month="1", day="15", email="test@example.invalid",
                         events="333,222", dry_run=True, poll_seconds=2, wait_minutes=1)
            result = Runner(driver, cfg).run(fixture.resolve().as_uri())
            self.assertEqual(result, Outcome.DRY_RUN_READY)
            self.assertEqual(driver.execute_script("return window.submitClicks"), 0)
            self.assertEqual(driver.execute_script("return WCAID_Check"), 1)
            self.assertTrue(driver.find_element("css selector", "#form_event_333").is_selected())
            self.assertTrue(driver.find_element("css selector", "#form_event_222").is_selected())
        finally:
            driver.quit()


if __name__ == "__main__":
    unittest.main()
