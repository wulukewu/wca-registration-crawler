"""Discord notification helper with secret-safe diagnostics.

Never write Bot token, channel ID, full API URL, response body or user profile
data into GitHub Actions logs. Notification failure must not alter the
registration outcome.
"""
from __future__ import annotations

import json
import logging
import os
from urllib import request
from urllib.error import HTTPError, URLError

LOG = logging.getLogger("wca")

HINTS = {
    400: "INVALID_REQUEST",
    401: "INVALID_BOT_TOKEN",
    403: "BOT_MISSING_CHANNEL_PERMISSION",
    404: "CHANNEL_NOT_FOUND_OR_INACCESSIBLE",
    429: "RATE_LIMITED",
}


def send_discord_message(content: str) -> bool:
    """Backwards-compatible plain text notification (e.g. smoke tests)."""
    return send_discord_payload({"content": content[:1900]})


def send_discord_payload(message: dict) -> bool:
    """Post a structured Discord payload with mentions disabled."""
    token = os.getenv("DISCORD_TOKEN", "")
    channel = os.getenv("DISCORD_CHANNEL_ID", "")
    if not token or not channel:
        LOG.warning("notification=SKIPPED code=MISSING_DISCORD_CONFIG")
        return False
    if not channel.isdigit():
        LOG.warning("notification=SKIPPED code=INVALID_DISCORD_CHANNEL_ID")
        return False

    payload = json.dumps({
        **message,
        "allowed_mentions": {"parse": []},
    }, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        "https://discord.com/api/v10/channels/" + channel + "/messages",
        data=payload,
        headers={
            "Authorization": "Bot " + token,
            "Content-Type": "application/json",
            "User-Agent": "wca-registration-crawler",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=8) as response:
            if response.status not in (200, 201, 204):
                LOG.warning("notification=FAILED code=UNEXPECTED_HTTP_STATUS http_status=%d",
                            response.status)
                return False
    except HTTPError as exc:
        # Only report numeric Discord error codes; never log response text or URL,
        # both of which can contain private information.
        discord_code = "UNKNOWN"
        try:
            body = json.loads(exc.read().decode("utf-8"))
            value = body.get("code")
            if isinstance(value, int) and not isinstance(value, bool):
                discord_code = str(value)
        except (ValueError, UnicodeError, AttributeError, OSError):
            pass
        LOG.warning(
            "notification=FAILED code=%s http_status=%d discord_code=%s",
            HINTS.get(exc.code, "DISCORD_HTTP_ERROR"), exc.code, discord_code,
        )
        return False
    except (URLError, TimeoutError, OSError):
        LOG.warning("notification=FAILED code=NETWORK_ERROR")
        return False

    LOG.info("notification=SENT")
    return True
