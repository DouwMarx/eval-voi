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
"""

from __future__ import annotations

import json
import subprocess

from voi_rank.dotenv import setting

DEFAULT_CLI_TIMEOUT_S = 600
TIMEOUT_SETTING = "VOI_CLI_TIMEOUT_S"
AUTH_TIMEOUT_S = 60
ISOLATION = ["--tools", "", "--setting-sources", "", "--no-session-persistence"]


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
    'cli: exit <n>: ...', "cli: 'claude' executable not found", 'cli:
    is_error: ...', 'json: envelope parse failed: ...'."""
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
        return None, raw or proc.stderr, f"cli: exit {proc.returncode}: {proc.stderr[-300:]}"
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as ex:
        return None, raw, f"json: envelope parse failed: {ex}"
    if envelope.get("is_error"):
        return envelope, raw, f"cli: is_error: {str(envelope.get('result'))[:300]}"
    return envelope, raw, None
