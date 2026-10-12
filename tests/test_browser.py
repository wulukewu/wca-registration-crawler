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
