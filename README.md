# WCA Registration Crawler

Selenium-based, **opt-in** Cubing-TW competition registration. Defaults to **dry run**: fills the form and waits for the preview without submitting it. Supports one safe runner; the previous parallel/self-cancel strategy was intentionally removed because a job exit did not prove registration success and multiple simultaneous submissions can duplicate registrations.

## GitHub Actions (recommended)

1. In **Settings → Secrets and variables → Actions**, keep `WCA_ID`, `BIRTHDAY_YEAR`, `BIRTHDAY_MONTH`, `BIRTHDAY_DAY`, and `EMAIL`. Optional: `PHONE`, `DISCORD_TOKEN`, `DISCORD_CHANNEL_ID`. Never enter sensitive values in workflow dispatch inputs.
2. Merge a tested PR into `main`. Wait for **Build registration image** on the merge commit to finish successfully (publishes `ghcr.io/...:sha-<commit>`).
3. Open **Actions → WCA Runner → Run workflow** on **main**. The workflow accepts waiting windows up to **300 minutes (5 hours)** and caps the entire job at **350 minutes**, below GitHub-hosted runners' six-hour limit.
4. Enter the **specific** competition URL, e.g. `https://cubing-tw.net/event/2026TaoyuanAirportCubeDay/registration` (not the generic `/event` index). Select `events` as **one WCA discipline**, e.g. `333` for 3x3x3, **multiple disciplines** with `333,222`, or `all` to select *every available discipline* (not one competition). The program normalizes both `/event/<event>` and `/event/<event>/registration` to the latter. Set `dry_run=true` for rehearsal; it never clicks Send.
5. For a real attempt, run once with `dry_run=false`. Check the workflow result, Discord notification (if configured), and the competition registration/payment status manually.

### Status meanings

| Status | Meaning | Exit |
| --- | --- | --- |
| `DRY_RUN_READY` | Form reached preview; **not submitted** | 0 |
| `SUBMITTED_PAYMENT_PENDING` | Observed archived-style `/registration/checked` transaction form or `/payment` redirect; **payment/acceptance still unverified** | 0 |
| `UNKNOWN` | Clicked Send but did not observe trusted post-submit evidence. **Do not automatically retry**; check the website manually for possible duplicate submission. | 1 |
| `FAILED` | Config, timeout, selector or validation error before proven submission | 1 |

`CONFIRMED` is reserved for a verifiable final receipt; currently no known archive provides this proof, so the crawler does **not** claim final acceptance based on text alone. Actions always writes a non-sensitive `run-result.json` artifact (when the browser starts) and job summary with stage, error code and duration. Browser screenshots, HTML, personal fields and server-issued registration IDs are never uploaded.

### Recommended timing

- **The day before / 30+ minutes before opening:** confirm the event URL, personal-data Secrets, chosen events, and successful GHCR publish; run a `dry_run=true` when the site's form is accessible.
- **Any time within five hours before opening:** launch the real workflow (`dry_run=false`, `wait_minutes` chosen as `15`, `30`, `60`, `120`, `180`, `240`, or `300`). Prefer a buffer longer than your early start to account for GitHub runner startup. It refreshes the event-specific registration page at most once every five seconds and proceeds when registration actually opens. GitHub can delay job startup; a running job is capped at 350 minutes.
- **At opening and afterward:** review the Actions/Discord outcome promptly. If `UNKNOWN`, check your registration on the website before trying again. Finish any required payment yourself.

This remains a **single** browser/runner: `runner_count` is not supported. For the 2026 Taoyuan Airport Cube Day competition, organizers warn against multiple simultaneous browser tabs and duplicate registrations; overlapping sessions may be considered irregular. GitHub-hosted runner start-up can be delayed, and web pages/anti-automation measures can change. Neither a dry run nor CI guarantees a place. Follow competition/site rules; one runner deliberately avoids hammering the registration endpoint.

### Local

Create a local `.env` using the secret names above, plus:

```ini
EVENT_URL=https://cubing-tw.net/event/Example2026
EVENTS=all
DRY_RUN=true
HEADLESS=true
WAIT_MINUTES=60
POLL_SECONDS=5
```

Install `pip install -r requirements.txt` (local Chromium + matching chromedriver required), then `python main.py`. For the supported container, use the repo's `Dockerfile` (Debian-packaged Chromium and driver). `python -m unittest discover -s tests -v` runs pure rules and an offline browser fixture when Chromium is installed.

### Obsolete repository Secrets

After this PR is **merged and the new workflows are active**, `EVENT_URL`, `PAT`, and `DISCORD_GUILD_ID` are no longer used and may be deleted from this repository's Actions Secrets. The old `NO_UI` setting is replaced by `HEADLESS` (a workflow parameter, not a secret). **Do not delete old secrets before merging** if you still need the old workflows. Verify that `PAT` is not shared by another workflow/repository before deleting it.

## Validation limitations

Saved HTML/JavaScript in [wca-webpage-intercept](https://github.com/wulukewu/wca-webpage-intercept) documents 2024's asynchronous `WCAID_Check` and `BTN_Preview`/`BTN_Send` behavior. Offline tests model those details with **synthetic** data, not personal data or backend services. Changes to current Cubing-TW markup, server responses, authentication, payment, rate limits or competition policy require on-site verification. This project does not support WCA-native registration portals.
