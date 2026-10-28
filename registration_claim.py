"""Atomic GitHub ref claim: one worker enters the registration form per workflow run.

Never reissue a claim after a possible submission or an ambiguous GitHub response.
Other workers finish without touching personal data or submitting.
"""
from __future__ import annotations

import json
import logging
import os
import re
from urllib import request
from urllib.error import HTTPError, URLError

from registration_logic import RegistrationError

LOG = logging.getLogger('wca')


def claim_registration(runner_count: int) -> bool:
    if runner_count == 1:
        return True
    repo = os.getenv("GITHUB_REPOSITORY", "")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    sha = os.getenv("GITHUB_SHA", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
            or not re.fullmatch(r"[0-9]+", run_id)
            or not re.fullmatch(r"[a-fA-F0-9]{40}", sha)
            or not token):
        raise RegistrationError("COORDINATE", "CLAIM_CONFIG_MISSING")

    ref = "refs/heads/wca-registration-claim-" + run_id
    endpoint = "https://api.github.com/repos/" + repo + "/git/refs"
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "wca-registration-crawler",
    }
    body = json.dumps({"ref": ref, "sha": sha}).encode("utf-8")
    try:
        with request.urlopen(request.Request(endpoint, data=body, headers=headers, method="POST"), timeout=12) as response:
            if response.status != 201:
                raise RegistrationError("COORDINATE", "CLAIM_RESPONSE_UNEXPECTED")
            return True
    except HTTPError as exc:
        if exc.code != 422:
            # The status is safe to disclose; request headers and response text
            # may contain secrets and must never enter Actions logs.
            LOG.warning("stage=COORDINATE code=CLAIM_SERVICE_ERROR http_status=%d", exc.code)
            raise RegistrationError("COORDINATE", "CLAIM_SERVICE_ERROR") from None
        # A 422 can indicate either an existing ref or invalid input.
        # Only treat it as a lost race if the common ref actually exists.
        try:
            with request.urlopen(request.Request(endpoint.replace("/git/refs", "/git/ref") + "/heads/wca-registration-claim-" + run_id,
                                                headers=headers, method="GET"), timeout=12) as response:
                if response.status == 200:
                    return False
        except (HTTPError, URLError, TimeoutError):
            pass
        LOG.warning("stage=COORDINATE code=CLAIM_VALIDATION_FAILED http_status=422")
        raise RegistrationError("COORDINATE", "CLAIM_VALIDATION_FAILED") from None
    except (URLError, TimeoutError):
        # HTTP may have arrived; do not retry an ambiguous claim.
        raise RegistrationError("COORDINATE", "CLAIM_SERVICE_UNCERTAIN") from None

def claim_already_exists(runner_count: int) -> bool:
    """Check at most once a minute so waiting workers stop after a winner exits."""
    if runner_count == 1:
        return False
    repo = os.getenv("GITHUB_REPOSITORY", "")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
            or not re.fullmatch(r"[0-9]+", run_id) or not token):
        raise RegistrationError("COORDINATE", "CLAIM_CONFIG_MISSING")
    endpoint = ("https://api.github.com/repos/" + repo
                + "/git/ref/heads/wca-registration-claim-" + run_id)
    req = request.Request(endpoint, method="GET", headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "wca-registration-crawler",
    })
    try:
        with request.urlopen(req, timeout=12) as response:
            if response.status != 200:
                raise RegistrationError("COORDINATE", "CLAIM_RESPONSE_UNEXPECTED")
            return True
    except HTTPError as exc:
        if exc.code == 404:
            return False
        LOG.warning("stage=COORDINATE code=CLAIM_SERVICE_ERROR http_status=%d", exc.code)
        raise RegistrationError("COORDINATE", "CLAIM_SERVICE_ERROR") from None
    except (URLError, TimeoutError):
        raise RegistrationError("COORDINATE", "CLAIM_SERVICE_UNCERTAIN") from None
