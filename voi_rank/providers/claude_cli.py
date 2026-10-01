"""Headless `claude -p` provider (deviations recorded in LEARNINGS.md and
verified against `claude --help` on CLI 2.1.220):
- `--bare` exists but restricts Anthropic auth to ANTHROPIC_API_KEY, which is
  absent under OAuth login. Context is instead isolated with `--tools ""`,
  `--setting-sources ""` and an explicit `--system-prompt`; verified
  empirically to exclude CLAUDE.md / user settings (227 input tokens).
- `--max-turns` no longer exists; with all tools disabled the call is
  single-turn by construction.

Every call runs in its own session (start_new_session), so a terminal Ctrl-C
is delivered to the harness alone: the running calls finish and their paid
result is stored instead of dying with 'killed by signal 2'. A call that
hangs (an invalid ANTHROPIC_API_KEY makes the CLI wait for ever with no
output) is cut after the timeout, VOI_CLI_TIMEOUT_S in the environment or
.env (default DEFAULT_CLI_TIMEOUT_S). check_auth() is the harness preflight:
`claude auth status --json` (free, no model call) refuses a CLI that is not
logged in; it does not verify an API key (CLI 2.1.280 reports loggedIn true
for any ANTHROPIC_API_KEY), which the timeout halt in elicit.run_jobs covers.

Usage-limit outages: during a claude.ai usage-limit window the CLI exits 1
(CLI 2.1.x) and prints a ZERO-USAGE envelope on stdout, `{"type": "result",
"is_error": true, "api_error_status": 429, "result": "You've hit your
session limit · resets 4:30am (Europe/Brussels)", "total_cost_usd": 0,
"usage": {"input_tokens": 0, "output_tokens": 0}}`, i.e. no model call was
made and nothing was billed (LEARNINGS 2026-09-29: the old harness stored
1,620 such exits as 'cli: exit 1' failures in one night). Any API error
the CLI meets before a model answers gives the same zero-usage shape, so
the status decides: usage_limit_envelope is a zero-usage envelope with
api_error_status 429 (or none, an older CLI) whose message names no login
or key problem. call_claude classifies a non-zero exit carrying one as
USAGE_LIMIT_PREFIX ('cli: usage-limit (zero-usage exit 1): <result>');
elicit.run_jobs never stores it and pauses the run instead (see there).
Any other zero-usage exit is 'cli: exit <n> (zero-usage, api <status>):
<result>' (an unknown model id is api 404; 'api none' when the CLI names
no status), an ordinary failed attempt, and elicit halts the member on
api 401/402/403/404 or a login message. is_usage_limit applies the same
test to a legacy 'cli: exit <n>' row, so every reader of stored rows (the
plan's cost estimate, a later analysis) classifies them as the harness does.
usage_limit_reset reads the reset time the message names.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from voi_rank.dotenv import seconds_setting

DEFAULT_CLI_TIMEOUT_S = 600
TIMEOUT_SETTING = "VOI_CLI_TIMEOUT_S"
AUTH_TIMEOUT_S = 60
ISOLATION = ["--tools", "", "--setting-sources", "", "--no-session-persistence"]
USAGE_LIMIT_PREFIX = "cli: usage-limit"
USAGE_LIMIT_STATUS = 429         # the API status of a usage-limit exit (every stored outage row)
# a login or key problem (the CLI's own text), matched case-insensitively:
# the member's environment, never an outage; elicit.halts_member uses it too
AUTH_PATTERN = r"not logged in|invalid api key|authentication"
_AUTH_RE = re.compile(AUTH_PATTERN, re.IGNORECASE)
_USAGE_LIMIT_RE = re.compile(r"^cli: usage-limit \(zero-usage exit \d+\)")
_LEGACY_EXIT_RE = re.compile(r"^cli: exit \d+: ")   # before 2026-09-29 every non-zero exit read so
# 'resets 4:30am (Europe/Brussels)', 'resets 9pm (UTC)': the CLI's usage-limit message
_RESET_RE = re.compile(r"\bresets\s+(\d{1,2})(?::(\d{2}))?\s*([ap]m)\s*\(([^)\s]+)\)", re.IGNORECASE)


def zero_usage_envelope(raw: str | None) -> dict | None:
    """The parsed CLI envelope when `raw` is one that billed nothing
    (total_cost_usd 0 or absent, usage.input_tokens and output_tokens 0);
    None for anything else (a paid answer, an empty stdout, non-JSON)."""
    try:
        data = json.loads(raw or "")
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("usage"), dict):
        return None
    usage = data["usage"]
    try:
        cost = float(data.get("total_cost_usd") or 0.0)
        tokens = float(usage.get("input_tokens") or 0.0) + float(usage.get("output_tokens") or 0.0)
    except (TypeError, ValueError):
        return None
    return data if cost == 0.0 and tokens == 0.0 else None


def usage_limit_envelope(envelope: dict | None, text: str | None = None) -> bool:
    """Whether a zero-usage envelope (zero_usage_envelope) is a usage-limit
    outage: api_error_status 429, or absent (a CLI that omits it), and a
    message (`text`, default the envelope's result) that names no login or
    key problem. False for None and for any other status (an unknown model
    id is 404, an invalid key 401)."""
    if envelope is None:
        return False
    status = envelope.get("api_error_status")
    if status is not None and status != USAGE_LIMIT_STATUS:
        return False
    text = str(envelope.get("result") or "") if text is None else text
    return _AUTH_RE.search(text) is None


def zero_usage_error(returncode: int, envelope: dict, stderr: str = "") -> str:
    """The error of a non-zero exit with a zero-usage envelope: 'cli:
    usage-limit (zero-usage exit <n>): <message>' for a usage-limit outage,
    else 'cli: exit <n> (zero-usage, api <status | none>): <message>'. The
    message is the envelope's result, else the tail of stderr."""
    text = (str(envelope.get("result") or "").strip() or stderr.strip()[-300:])[:300]
    if usage_limit_envelope(envelope, text):
        return f"{USAGE_LIMIT_PREFIX} (zero-usage exit {returncode}): {text}"
    return f"cli: exit {returncode} (zero-usage, api {envelope.get('api_error_status') or 'none'}): {text}"


def is_usage_limit(error: str | None, raw: str | None = None) -> bool:
    """A usage-limit outage: the error call_claude classifies as one, or a
    legacy 'cli: exit <n>: ...' row (stored before the class existed) whose
    raw response is a zero-usage envelope that usage_limit_envelope accepts;
    never an error that names a login or key problem. The one test the harness
    (elicit.usage_limit) and the plan's cost estimate apply."""
    if not error or _AUTH_RE.search(error):
        return False   # a login or key problem is never an outage
    if _USAGE_LIMIT_RE.match(error):
        return True
    # a 'cli: exit <n> (zero-usage, api ...)' row is classified already: not an outage
    return _LEGACY_EXIT_RE.match(error) is not None and usage_limit_envelope(zero_usage_envelope(raw))


def usage_limit_reset(error: str | None, now: datetime) -> datetime | None:
    """The next moment after `now` (timezone-aware) that a usage-limit
    message names as its reset ('resets 4:30am (Europe/Brussels)'), in that
    time zone; None when the message names no such time or an unknown zone.
    A time already past today is tomorrow's."""
    m = _RESET_RE.search(error or "")
    if m is None:
        return None
    hour, minute = int(m.group(1)), int(m.group(2) or 0)
    if not 1 <= hour <= 12 or minute > 59:
        return None
    hour = hour % 12 + (12 if m.group(3).lower() == "pm" else 0)
    try:
        tz = ZoneInfo(m.group(4))
    except (ZoneInfoNotFoundError, ValueError):
        return None
    local = now.astimezone(tz)
    reset = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if reset <= local:
        reset += timedelta(days=1)   # wall-clock arithmetic in `tz`: the same local time tomorrow
    return reset


def cli_timeout_s() -> float:
    """Wall-clock cap per call, from VOI_CLI_TIMEOUT_S (environment, else
    .env), else DEFAULT_CLI_TIMEOUT_S."""
    return seconds_setting(TIMEOUT_SETTING, DEFAULT_CLI_TIMEOUT_S)


def check_auth() -> str:
    """Preflight: `claude auth status --json`. Returns a one-line description
    (auth method and API key source; never an email or a key) or raises
    RuntimeError when the executable is missing, the command gives no answer
    within AUTH_TIMEOUT_S, exits non-zero or reports loggedIn false, so the
    caller submits nothing."""
    cmd = ["claude", "auth", "status", "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=AUTH_TIMEOUT_S,
                              start_new_session=True)
    except FileNotFoundError:
        raise RuntimeError("claude CLI preflight failed: 'claude' executable not found"
                           " (no elicitation call was made)") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"claude CLI preflight failed: `{' '.join(cmd)}` gave no answer within"
                           f" {AUTH_TIMEOUT_S}s (no elicitation call was made)") from None
    try:
        status = json.loads(proc.stdout)
    except json.JSONDecodeError:
        status = {}
    if not isinstance(status, dict):
        status = {}
    if proc.returncode != 0 or not status.get("loggedIn"):
        detail = f"exit {proc.returncode}, auth {status.get('authMethod', 'unknown')}"
        if proc.stderr.strip():
            detail += f": {proc.stderr.strip()[-300:]}"
        raise RuntimeError(f"claude CLI is not logged in ({detail}); run `claude auth login`"
                           " (no elicitation call was made)")
    return (f"claude CLI logged in (auth {status.get('authMethod', 'unknown')}, API key source"
            f" {status.get('apiKeySource') or 'none'}; the key itself is not verified here)")


def call_claude(prompt: str, model: str, system_prompt: str):
    """Returns (envelope | None, raw_stdout, error | None). raw_stdout is the
    full JSON envelope as printed by the CLI (stored verbatim in the DB); the
    model's answer is envelope['result'] and its cost envelope['total_cost_usd'].
    Error strings: 'cli: timeout after <n>s', 'cli: killed by signal <n>: ...',
    'cli: usage-limit (zero-usage exit <n>): ...' (a non-zero exit whose
    stdout is a zero-usage envelope of a usage limit: nothing was billed),
    'cli: exit <n> (zero-usage, api <status>): ...' (any other zero-usage
    exit, e.g. an unknown model id), 'cli: exit <n>: ...', "cli: 'claude'
    executable not found", 'cli: is_error: ...', 'json: envelope parse
    failed: ...'."""
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "json",
           *ISOLATION, "--system-prompt", system_prompt]
    timeout = cli_timeout_s()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              start_new_session=True)
    except subprocess.TimeoutExpired:
        return None, "", f"cli: timeout after {timeout:g}s"
    except FileNotFoundError:
        return None, "", "cli: 'claude' executable not found"
    raw = proc.stdout
    if proc.returncode < 0:
        return None, raw or proc.stderr, f"cli: killed by signal {-proc.returncode}: {proc.stderr[-300:]}"
    if proc.returncode != 0:
        envelope = zero_usage_envelope(raw)
        if envelope is not None:
            return envelope, raw, zero_usage_error(proc.returncode, envelope, proc.stderr)
        return None, raw or proc.stderr, f"cli: exit {proc.returncode}: {proc.stderr[-300:]}"
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as ex:
        return None, raw, f"json: envelope parse failed: {ex}"
    if envelope.get("is_error"):
        return envelope, raw, f"cli: is_error: {str(envelope.get('result'))[:300]}"
    return envelope, raw, None
