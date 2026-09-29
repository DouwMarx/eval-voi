"""Headless `claude -p` provider (spec §6.1, deviations recorded in
LEARNINGS.md and verified against `claude --help` on CLI 2.1.220):
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
"is_error": true, "result": "You've hit your session limit · resets ...",
"total_cost_usd": 0, "usage": {"input_tokens": 0, "output_tokens": 0}}`,
i.e. no model call was made and nothing was billed (LEARNINGS 2026-09-29:
1,391 such attempts were stored as 'cli: exit 1' failures). call_claude
classifies a non-zero exit whose stdout is such an envelope as
USAGE_LIMIT_PREFIX ('cli: usage-limit (zero-usage exit 1): <result>');
elicit.run_jobs never stores it and pauses the run instead (see there), and
health reads a legacy 'cli: exit 1' row with that envelope as an outage.
"""

from __future__ import annotations

import json
import re
import subprocess

from voi_rank.dotenv import setting

DEFAULT_CLI_TIMEOUT_S = 600
TIMEOUT_SETTING = "VOI_CLI_TIMEOUT_S"
AUTH_TIMEOUT_S = 60
ISOLATION = ["--tools", "", "--setting-sources", "", "--no-session-persistence"]
USAGE_LIMIT_PREFIX = "cli: usage-limit"
_USAGE_LIMIT_RE = re.compile(r"^cli: usage-limit \(zero-usage exit \d+\)")
_EXIT_RE = re.compile(r"^cli: exit \d+\b")


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


def usage_limit_error(returncode: int, envelope: dict, stderr: str = "") -> str:
    """'cli: usage-limit (zero-usage exit <n>): <the CLI's message>'."""
    text = str(envelope.get("result") or "").strip() or stderr.strip()[-300:]
    return f"{USAGE_LIMIT_PREFIX} (zero-usage exit {returncode}): {text[:300]}"


def is_usage_limit(error: str | None, raw: str | None = None) -> bool:
    """A usage-limit outage: the error call_claude classifies as one, or a
    legacy 'cli: exit <n>' row (stored before the class existed) whose raw
    response is a zero-usage envelope."""
    if not error:
        return False
    if _USAGE_LIMIT_RE.match(error):
        return True
    return _EXIT_RE.match(error) is not None and zero_usage_envelope(raw) is not None


def cli_timeout_s() -> float:
    """Wall-clock cap per call, from VOI_CLI_TIMEOUT_S (environment, else
    .env), else DEFAULT_CLI_TIMEOUT_S."""
    value = setting(TIMEOUT_SETTING)
    if not value:
        return float(DEFAULT_CLI_TIMEOUT_S)
    try:
        seconds = float(value)
    except ValueError:
        raise RuntimeError(f"{TIMEOUT_SETTING}={value!r} is not a number of seconds") from None
    if seconds <= 0:
        raise RuntimeError(f"{TIMEOUT_SETTING} must be positive, got {value!r}")
    return seconds


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
    stdout is a zero-usage envelope: nothing was billed), 'cli: exit <n>:
    ...', "cli: 'claude' executable not found", 'cli: is_error: ...', 'json:
    envelope parse failed: ...'."""
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
            return envelope, raw, usage_limit_error(proc.returncode, envelope, proc.stderr)
        return None, raw or proc.stderr, f"cli: exit {proc.returncode}: {proc.stderr[-300:]}"
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as ex:
        return None, raw, f"json: envelope parse failed: {ex}"
    if envelope.get("is_error"):
        return envelope, raw, f"cli: is_error: {str(envelope.get('result'))[:300]}"
    return envelope, raw, None
