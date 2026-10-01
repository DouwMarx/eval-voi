"""Hermetic defaults for every test: no `claude` binary (neither `--version`
nor the `auth status` preflight), no `git` state and no network. A test that
needs the real behaviour restores it explicitly."""

import io
import json
import urllib.error
import urllib.request

import pytest

from voi_rank import db, pricing
from voi_rank.providers import claude_cli, openrouter


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def fake_key_opener(req, timeout=None, context=None):
    """The default urlopen under test: answers the OpenRouter key preflight
    with a valid key and refuses every other URL loudly."""
    url = req.full_url if hasattr(req, "full_url") else str(req)
    if url == openrouter.AUTH_URL:
        return FakeResponse(json.dumps({"data": {"label": "test", "usage": 0, "limit": None}}).encode())
    raise AssertionError(f"unexpected network call in a test: {url}")


@pytest.fixture(autouse=True)
def hermetic(monkeypatch):
    monkeypatch.setattr(db, "claude_cli_version", lambda: "test-cli")
    monkeypatch.setattr(claude_cli, "check_auth", lambda: "claude CLI preflight: test")
    monkeypatch.setattr(db, "git_state", lambda cwd=None: ("test-head", []))
    monkeypatch.setattr(urllib.request, "urlopen", fake_key_opener)
    monkeypatch.setattr(pricing, "fetch_json", offline_catalogue)


def offline_catalogue(url, opener=None):
    """The default catalogue fetch under test: offline, so a plan prices an
    openrouter member from the fallback file (a test that wants the live
    path injects its own fetch)."""
    raise urllib.error.URLError("offline in tests")
