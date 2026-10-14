"""Pure configuration and outcome rules for the Cubing-TW registration workflow."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from urllib.parse import urljoin, urlsplit, urlunsplit


class Outcome(str, Enum):
    DRY_RUN_READY = "DRY_RUN_READY"
    SUBMITTED_PAYMENT_PENDING = "SUBMITTED_PAYMENT_PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    NOT_SELECTED = "NOT_SELECTED"


class RegistrationError(Exception):
    def __init__(self, stage: str, code: str):
        self.stage = stage
        self.code = code
        super().__init__(f"{stage}: {code}")


@dataclass(frozen=True)
class Config:
    event_url: str
    wca_id: str
    year: str
    month: str
    day: str
    email: str
    phone: str = ""
    events: str = "all"
    dry_run: bool = True
    wait_minutes: int = 60
    poll_seconds: float = 5.0
    headless: bool = True
    runner_count: int = 1
    runner_index: int = 1


EVENT_ALIASES = {
    "333bf": "3bld", "333fm": "3fmc", "444bf": "4bld",
    "555bf": "5bld", "333mbf": "mbld",
}


def seconds_until_worker_slot(
    now: float, runner_index: int, runner_count: int, poll_seconds: float
) -> float:
    """Seconds to the next wall-clock polling slot for a one-based worker.

    N workers share one period; worker i has phase (i - 1) / N.
    No assumptions about a maximum N, worker start order, or GitHub launch times.
    Page-load latency still affects actual request timing.
    """
    if not (runner_count >= 1 and 1 <= runner_index <= runner_count and poll_seconds > 0):
        raise ValueError("invalid worker slot")
    phase = (runner_index - 1) * (poll_seconds / runner_count)
    return (phase - now % poll_seconds) % poll_seconds


def normalize_event_url(raw: str) -> str:
    """Accept a specific event URL, not the generic events index or other hosts."""
    try:
        u = urlsplit(raw.strip())
        if (u.scheme != "https" or u.hostname not in {"cubing-tw.net", "www.cubing-tw.net"}
                or u.username or u.password or u.port or u.query or u.fragment):
            raise ValueError()
        segments = [x for x in u.path.split("/") if x]
        if (len(segments) not in (2, 3) or segments[0] != "event"
                or not re.fullmatch(r"[A-Za-z0-9_-]+", segments[1])
                or (len(segments) == 3 and segments[2] != "registration")):
            raise ValueError()
    except (ValueError, AttributeError):
        raise RegistrationError("CONFIG", "INVALID_EVENT_URL") from None
    return urlunsplit(("https", "cubing-tw.net", f"/event/{segments[1]}/registration", "", ""))



def registration_select_url(event_url: str, href: str) -> str | None:
    """Only follow the event's own /registration/select link, never generic buttons."""
    try:
        target = normalize_event_url(event_url)
        url = urljoin(target + "/", href)
        part = urlsplit(url)
        if (part.scheme == "https" and part.hostname in {"cubing-tw.net", "www.cubing-tw.net"}
                and not part.username and not part.password and not part.port
                and not part.query and not part.fragment
                and part.path == urlsplit(target).path + "/select"):
            return url
    except (RegistrationError, ValueError, AttributeError):
        pass
    return None


def parse_events(raw: str) -> set[str] | None:
    if raw.strip().lower() == "all":
        return None
    names = [x.strip().lower() for x in raw.split(",")]
    if not names or "all" in names or any(not re.fullmatch(r"[a-z0-9]+", name) for name in names):
        raise RegistrationError("CONFIG", "INVALID_EVENTS")
    canonical = {EVENT_ALIASES.get(name, name) for name in names}
    if len(canonical) != len(names):
        raise RegistrationError("CONFIG", "DUPLICATE_EVENTS")
    return canonical


def validate_config(c: Config) -> str:
    url = normalize_event_url(c.event_url)
    if not re.fullmatch(r"\d{4}[A-Z]{4}\d{2}", c.wca_id):
        raise RegistrationError("CONFIG", "INVALID_WCA_ID_FORMAT")
    try:
        from datetime import date
        date(int(c.year), int(c.month), int(c.day))
    except (ValueError, TypeError):
        raise RegistrationError("CONFIG", "INVALID_BIRTHDAY") from None
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", c.email):
        raise RegistrationError("CONFIG", "INVALID_EMAIL")
    if not (1 <= c.wait_minutes <= 300) or not (2 <= c.poll_seconds <= 60) or not (1 <= c.runner_count <= 5) or not (1 <= c.runner_index <= c.runner_count):
        raise RegistrationError("CONFIG", "INVALID_WAIT_SETTINGS")
    parse_events(c.events)
    return url


def classify_after_submit(url: str, payment_form: bool, receipt: bool = False) -> Outcome:
    """Positive, structural evidence only: generic page text is not a receipt."""
    path = urlsplit(url).path.rstrip("/")
    if not path.startswith("/event/"):
        return Outcome.UNKNOWN
    if receipt and re.search(r"/registration/(success|confirmed)$", path):
        return Outcome.CONFIRMED
    if re.search(r"/registration/checked$", path) and payment_form:
        return Outcome.SUBMITTED_PAYMENT_PENDING
    if re.search(r"/payment$", path):
        return Outcome.SUBMITTED_PAYMENT_PENDING
    return Outcome.UNKNOWN
