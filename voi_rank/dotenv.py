"""Settings from the environment or the repo-root .env file (git-ignored, see
.env.example): OPENROUTER_API_KEY and VOI_CLI_TIMEOUT_S. A KEY=VALUE line may
carry a leading 'export ', surrounding quotes and a trailing ' # comment'.
Callers never print a value."""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
# a quoted .env value ('...' or "...") with an optional trailing '# comment';
# group 2 is the value. Unquoted values drop a ' # comment' (whitespace
# before the hash, as in a shell).
_ENV_QUOTED_RE = re.compile(r"""^(["'])(.*?)\1\s*(?:#.*)?$""")


def read_env_file(path: Path | None = None) -> dict[str, str]:
    path = path or ENV_FILE
    out = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        m = _ENV_QUOTED_RE.match(v.strip())
        out[k.strip()] = m.group(2) if m else re.split(r"\s#", v.strip(), maxsplit=1)[0].rstrip()
    return out


def setting(name: str, path: Path | None = None) -> str | None:
    """The environment variable `name`, else its line in .env, else None."""
    return os.environ.get(name) or read_env_file(path).get(name)
