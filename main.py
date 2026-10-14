"""Cubing-TW registration runner. Submission is opt-in; no blind retry after Send."""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from discord_notify import send_discord_message
from registration_claim import claim_registration, claim_already_exists
from registration_logic import (
    Config, Outcome, RegistrationError, classify_after_submit, parse_events,
    validate_config, registration_select_url, seconds_until_worker_slot,
)

LOG = logging.getLogger("wca")


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    if value.lower() not in {"true", "false"}:
        raise RegistrationError("CONFIG", f"INVALID_{name}")
    return value.lower() == "true"


def load_config() -> Config:
    load_dotenv()
    try:
        wait_minutes = int(os.getenv("WAIT_MINUTES", "60"))
        runner_count = int(os.getenv("RUNNER_COUNT", "1"))
        runner_index = int(os.getenv("RUNNER_INDEX", "1"))
        poll_seconds = max(float(os.getenv("POLL_SECONDS", "5")), 5 * runner_count)
    except ValueError:
        raise RegistrationError("CONFIG", "INVALID_WAIT_SETTINGS") from None
    return Config(
        event_url=os.getenv("EVENT_URL", ""),
        wca_id=os.getenv("WCA_ID", "").strip().upper(),
        year=os.getenv("BIRTHDAY_YEAR", ""),
        month=os.getenv("BIRTHDAY_MONTH", ""),
        day=os.getenv("BIRTHDAY_DAY", ""),
        email=os.getenv("EMAIL", ""),
        phone=os.getenv("PHONE", ""),
        events=os.getenv("EVENTS", "all"),
        dry_run=env_bool("DRY_RUN", True),
        wait_minutes=wait_minutes, poll_seconds=poll_seconds,
        headless=env_bool("HEADLESS", True), runner_count=runner_count,
        runner_index=runner_index,
    )


class Runner:
    def __init__(self, driver, cfg: Config):
        self.driver = driver
        self.cfg = cfg
        self.stage = "OPEN"

    def _visible(self, selector: str):
        from selenium.webdriver.common.by import By
        return next((el for el in self.driver.find_elements(By.CSS_SELECTOR, selector)
                     if el.is_displayed()), None)

    def _until(self, stage: str, code: str, condition, seconds: int = 20):
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException
        try:
            return WebDriverWait(self.driver, seconds, poll_frequency=0.2).until(condition)
        except TimeoutException:
            raise RegistrationError(stage, code) from None

    def await_open(self, url: str):
        self.stage = "OPEN"
        deadline = time.monotonic() + self.cfg.wait_minutes * 60
        if self.cfg.runner_count > 1:
            # Align even the first request: GitHub workers start at different times.
            delay = seconds_until_worker_slot(
                time.time(), self.cfg.runner_index,
                self.cfg.runner_count, self.cfg.poll_seconds,
            )
            LOG.info("stage=OPEN status=SLOT_READY worker=%d/%d delay_seconds=%.2f",
                     self.cfg.runner_index, self.cfg.runner_count, delay)
            time.sleep(min(delay, max(0.0, deadline - time.monotonic())))
        if time.monotonic() >= deadline:
            raise RegistrationError("OPEN", "REGISTRATION_NOT_OPEN_BEFORE_TIMEOUT")
        try:
            self.driver.get(url)
        except Exception as exc:
            LOG.warning("stage=OPEN status=NAVIGATION_RETRY error_type=%s", type(exc).__name__)
        last_note = -1
        next_claim_check = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self.cfg.runner_count > 1 and time.monotonic() >= next_claim_check:
                if claim_already_exists(self.cfg.runner_count):
                    LOG.info("stage=OPEN status=OTHER_WORKER_CLAIMED")
                    return False
                next_claim_check = time.monotonic() + 60
            if self._visible("input[id^='WCAID_input']"):
                LOG.info("stage=OPEN status=READY")
                return
            # Archived page: registration landing -> primary link to /registration/select
            # -> WCA ID selection screen. Never click an unrelated primary button.
            link = self._registration_start_link(url)
            if link:
                LOG.info("stage=OPEN status=SELECT_LINK_AVAILABLE")
                try:
                    self.driver.get(link)
                    self._until("OPEN", "SELECT_PAGE_NOT_READY",
                                lambda driver: self._visible("input[id^='WCAID_input']"), 15)
                    LOG.info("stage=OPEN status=READY")
                    return
                except Exception as exc:
                    LOG.warning("stage=OPEN status=SELECT_RETRY error_type=%s", type(exc).__name__)
            remaining = int(deadline - time.monotonic())
            note = remaining // 60
            if note != last_note:
                LOG.info("stage=OPEN status=WAITING remaining_minutes=%d", max(note, 0))
                last_note = note
            delay = (
                self.cfg.poll_seconds if self.cfg.runner_count == 1
                else seconds_until_worker_slot(
                    time.time(), self.cfg.runner_index,
                    self.cfg.runner_count, self.cfg.poll_seconds,
                )
            )
            time.sleep(min(delay, max(0.0, deadline - time.monotonic())))
            if time.monotonic() >= deadline:
                break
            try:
                self.driver.get(url)  # Re-enter original path even if the server redirected.
            except Exception as exc:
                LOG.warning("stage=OPEN status=RELOAD_RETRY error_type=%s", type(exc).__name__)
        raise RegistrationError("OPEN", "REGISTRATION_NOT_OPEN_BEFORE_TIMEOUT")

    def _registration_start_link(self, event_url: str) -> str | None:
        for link in self.driver.find_elements("css selector", "a[href*='registration/select']"):
            if not link.is_displayed() or not link.is_enabled():
                continue
            href = registration_select_url(event_url, link.get_attribute("href") or "")
            if href:
                return href
        return None

    def identify(self):
        self.stage = "IDENTIFY"
        field = self._until("IDENTIFY", "WCA_INPUT_NOT_FOUND",
                            lambda d: self._visible("input[id^='WCAID_input']"))
        field.clear()
        field.send_keys(self.cfg.wca_id)

        def validation(d):
            # The archived Cubing-TW script marks the input and hidden form_Profile
            # asynchronously after /event/ajax/WCAID_Check returns OK.
            current = self._visible("input[id^='WCAID_input']")
            if not current:
                return False
            classes = (current.get_attribute("class") or "").split()
            if "is-invalid" in classes:
                raise RegistrationError("IDENTIFY", "WCA_ID_REJECTED")
            profile = next(iter(d.find_elements("css selector", "#form_Profile")), None)
            profile_ready = bool(profile and profile.get_attribute("value"))
            flag = d.execute_script("return typeof WCAID_Check === 'undefined' ? null : WCAID_Check")
            if flag is not None:
                return flag == 1 and profile_ready
            return profile_ready and "is-valid" in classes

        self._until("IDENTIFY", "WCA_VALIDATION_TIMEOUT", validation, 25)
        button = self._until("IDENTIFY", "GO_BUTTON_NOT_FOUND",
                             lambda d: self._visible("#WCAID_Button"))
        button.click()
        self._until("IDENTIFY", "REGISTRATION_FORM_NOT_LOADED",
                    lambda d: self._visible("#MainForm"), 25)
        LOG.info("stage=IDENTIFY status=VALIDATED")

    def fill(self):
        from selenium.webdriver.support.ui import Select
        self.stage = "FILL"
        d = self.driver

        def select_value(selector, value):
            el = self._until("FILL", "BIRTHDAY_SELECTOR_MISSING",
                             lambda driver: self._visible(selector))
            sel = Select(el)
            match = next((opt for opt in sel.options
                          if opt.get_attribute("value") == str(int(value))
                          or opt.text.strip() == str(int(value))), None)
            if not match:
                raise RegistrationError("FILL", "BIRTHDAY_VALUE_UNAVAILABLE")
            sel.select_by_visible_text(match.text)

        select_value("#form_birthday_year", self.cfg.year)
        select_value("#form_birthday_month", self.cfg.month)
        # The site's birthday script regenerates the day options on month changes.
        self._until("FILL", "BIRTHDAY_DAY_NOT_READY",
                    lambda driver: any(o.get_attribute("value") == str(int(self.cfg.day))
                                       for o in Select(driver.find_element("css selector", "#form_birthday_day")).options))
        select_value("#form_birthday_day", self.cfg.day)

        field = self._until("FILL", "EMAIL_FIELD_MISSING", lambda driver: self._visible("#form_email"))
        field.clear()
        field.send_keys(self.cfg.email)
        phone_field = self._visible("#form_phone")
        if self.cfg.phone and phone_field:
            phone_field.clear()
            phone_field.send_keys(self.cfg.phone)
        elif self.cfg.phone:
            LOG.warning("stage=FILL code=OPTIONAL_PHONE_FIELD_MISSING")

        requested = parse_events(self.cfg.events)
        available = {el.get_attribute("id")[len("form_event_"):]: el
                     for el in d.find_elements("css selector", "#div_events input[id^='form_event_']")
                     if el.is_enabled() and el.is_displayed() and el.get_attribute("id")}
        if not available:
            raise RegistrationError("FILL", "NO_SELECTABLE_EVENTS")
        if requested is not None and not requested.issubset(available):
            raise RegistrationError("FILL", "REQUESTED_EVENT_NOT_AVAILABLE")
        selected = requested if requested is not None else set(available)

        def set_event_checked(code: str, checked: bool) -> None:
            # Real Cubing-TW forms use a Bootstrap checkbox with an associated
            # <label for="...">. Selenium may report that the visible label
            # intercepts clicks intended for the checkbox itself.
            from selenium.common.exceptions import ElementClickInterceptedException

            checkbox = available[code]
            if checkbox.is_selected() == checked:
                return

            d.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
                checkbox,
            )
            try:
                checkbox.click()
            except ElementClickInterceptedException:
                # An intercepted Selenium click might or might not have
                # changed state; inspect it before attempting another click.
                LOG.warning("stage=FILL code=EVENT_INPUT_INTERCEPTED event_code=%s", code)
                if checkbox.is_selected() != checked:
                    labels = d.find_elements(
                        "css selector", f"#div_events label[for='form_event_{code}']"
                    )
                    label = next(
                        (item for item in labels if item.is_displayed() and item.is_enabled()),
                        None,
                    )
                    if label is None:
                        raise RegistrationError("FILL", "EVENT_LABEL_NOT_CLICKABLE")
                    try:
                        label.click()
                    except ElementClickInterceptedException:
                        # Do not use a forced JavaScript click to bypass overlays,
                        # which may be a real server-side or validation gate.
                        raise RegistrationError("FILL", "EVENT_LABEL_CLICK_INTERCEPTED") from None

            self._until(
                "FILL", "EVENT_SELECTION_NOT_APPLIED",
                lambda driver: checkbox.is_selected() == checked, 5,
            )

        for code in sorted(available):
            set_event_checked(code, code in selected)
        if not selected or any(available[code].is_selected() is False for code in selected):
            raise RegistrationError("FILL", "EVENT_SELECTION_FAILED")

        # Archived forms also require WCA-prefilled name/gender/country.
        for selector in ("#form_english_name", "#form_country"):
            field = self._visible(selector)
            if field and not field.get_attribute("value"):
                raise RegistrationError("FILL", "REQUIRED_PROFILE_FIELD_EMPTY")
        radios = d.find_elements("css selector", "input[name='form_gender']")
        if radios and not any(r.is_selected() for r in radios):
            raise RegistrationError("FILL", "REQUIRED_PROFILE_FIELD_EMPTY")
        LOG.info("stage=FILL status=READY selected_event_count=%d", len(selected))

    def preview(self):
        self.stage = "PREVIEW"
        button = self._until("PREVIEW", "PREVIEW_BUTTON_MISSING",
                             lambda d: self._visible("#BTN_Preview"))
        button.click()
        if self.driver.find_elements("css selector", ".is-invalid, #div_events.text-danger"):
            raise RegistrationError("PREVIEW", "FORM_VALIDATION_FAILED")

        def ready(d):
            if d.find_elements("css selector", ".is-invalid, #div_events.text-danger"):
                raise RegistrationError("PREVIEW", "FORM_VALIDATION_FAILED")
            modal = self._visible("#Preview_Modal")
            content = next(iter(d.find_elements("css selector", "#Preview_main")), None)
            js_active = d.execute_script("return typeof jQuery === 'undefined' ? null : jQuery.active")
            return modal and content and (content.text or "").strip() and js_active in (None, 0)

        self._until("PREVIEW", "PREVIEW_NOT_READY", ready, 25)
        LOG.info("stage=PREVIEW status=VALID")

    def submit(self) -> Outcome:
        self.stage = "SUBMIT"
        button = self._until("SUBMIT", "SEND_BUTTON_MISSING",
                             lambda d: self._visible("#BTN_Send"))
        try:
            button.click()  # Never click a second time after this point.
        except Exception:
            # A browser disconnect during click cannot establish whether POST arrived.
            return Outcome.UNKNOWN
        LOG.info("stage=SUBMIT status=CLICKED awaiting_server_result")
        self.stage = "VERIFY"

        def result(d):
            url = d.current_url
            payment_form = bool(d.find_elements("css selector", "#Tran_Form input[name='RegUID']"))
            outcome = classify_after_submit(url, payment_form)
            return outcome if outcome != Outcome.UNKNOWN else False

        try:
            return self._until("VERIFY", "RESPONSE_NOT_RECOGNIZED", result, 35)
        except Exception:
            return Outcome.UNKNOWN  # submission might have succeeded; never blindly retry

    def run(self, url: str) -> Outcome:
        if self.await_open(url) is False:
            return Outcome.NOT_SELECTED
        self.stage = "COORDINATE"
        if not claim_registration(self.cfg.runner_count):
            LOG.info("stage=COORDINATE status=NOT_SELECTED")
            return Outcome.NOT_SELECTED
        LOG.info("stage=COORDINATE status=CLAIMED")
        self.identify()
        self.fill()
        self.preview()
        if self.cfg.dry_run:
            LOG.info("stage=PREVIEW status=DRY_RUN_READY submit_skipped=true")
            return Outcome.DRY_RUN_READY
        return self.submit()


def send_discord(status: Outcome, code: str, run_url: str) -> None:
    # Best effort: Discord errors should never redefine the registration result.
    send_discord_message(f"WCA crawler: {status.value} ({code}). {run_url}")


def write_summary(outcome: Outcome, stage: str, code: str, started: float) -> None:
    result = {
        "outcome": outcome.value, "stage": stage, "code": code,
        "duration_seconds": round(time.monotonic() - started, 2),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    Path(os.getenv("RESULT_PATH", "run-result.json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"### WCA registration: `{outcome.value}`\n\n"
                         f"- Stage: `{stage}`\n- Code: `{code}`\n"
                         f"- Elapsed: {result['duration_seconds']} s\n"
                         "- `SUBMITTED_PAYMENT_PENDING` means submission evidence, **not** payment or final acceptance.\n")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    started = time.monotonic()
    outcome = Outcome.FAILED
    code, stage = "UNEXPECTED", "INIT"
    driver = None
    try:
        cfg = load_config()
        target = validate_config(cfg)  # fail before opening a browser
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        options = webdriver.ChromeOptions()
        if os.path.isfile(os.getenv("CHROME_BIN", "")):
            options.binary_location = os.environ["CHROME_BIN"]
        if cfg.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1366,900")
        driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver") if os.path.isfile("/usr/bin/chromedriver") else Service(), options=options)
        driver.set_page_load_timeout(20)
        runner = Runner(driver, cfg)
        try:
            outcome = runner.run(target)
        finally:
            stage = runner.stage
        code = outcome.value
    except RegistrationError as exc:
        outcome, code, stage = Outcome.FAILED, exc.code, exc.stage
    except Exception as exc:
        # No exception string, HTML or screenshot: those can contain personal data.
        outcome, code = Outcome.FAILED, f"UNEXPECTED_{type(exc).__name__}"
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                LOG.warning("cleanup=DRIVER_QUIT_FAILED")
        LOG.info("outcome=%s stage=%s code=%s", outcome.value, stage, code)
        write_summary(outcome, stage, code, started)
        run_url = f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/{os.getenv('GITHUB_REPOSITORY', '')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}"
        if outcome != Outcome.NOT_SELECTED and os.getenv("DISCORD_NOTIFY_IN_WORKFLOW", "").lower() != "true":
            send_discord(outcome, code, run_url)
    return 0 if outcome in (Outcome.DRY_RUN_READY, Outcome.SUBMITTED_PAYMENT_PENDING, Outcome.CONFIRMED, Outcome.NOT_SELECTED) else 1


if __name__ == "__main__":
    sys.exit(main())
