"""PyPI version cache management for the upgrade check mechanism.

Background refresh only — never blocks the foreground. Never raises on any failure.

Cache location: ``~/.kittify/last-cli-check.json``
TTL: 3600 seconds (1 hour)
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

__all__ = [
    "CACHE_PATH",
    "TTL_SECONDS",
    "UpgradeChecker",
]

CACHE_PATH: Path = Path.home() / ".kittify" / "last-cli-check.json"
TTL_SECONDS: int = 3600
OPT_OUT_ENV_VAR: str = "SPEC_KITTY_NO_UPGRADE_CHECK"


def _is_opt_out_set() -> bool:
    """Return True when upgrade checks are disabled by environment."""
    raw = os.environ.get(OPT_OUT_ENV_VAR, "").strip().lower()
    return raw in ("1", "true", "yes", "on")


class UpgradeChecker:
    """Manage the PyPI version cache at ``~/.kittify/last-cli-check.json``.

    All public methods are safe to call unconditionally — any I/O or subprocess
    error is swallowed so callers never need to guard against exceptions.
    """

    def get_available_version(self) -> str | None:
        """Return the cached latest version string, or ``None`` if unavailable.

        Algorithm:
        1. Try to read ``CACHE_PATH``. If absent or unreadable: return ``None``.
        2. Parse JSON. If malformed: return ``None``.
        3. Parse ``checked_at`` as ISO 8601 datetime.  Calculate age in seconds.
        4. If age < TTL_SECONDS: return ``latest_version`` field.
        5. If age >= TTL_SECONDS: return last known ``latest_version``
           (stale but better than ``None``).
        """
        if _is_opt_out_set():
            return None

        try:
            text = CACHE_PATH.read_text(encoding="utf-8")
        except OSError:
            return None

        try:
            data: dict[str, object] = json.loads(text)
        except json.JSONDecodeError:
            return None

        latest_version = data.get("latest_version")
        if not isinstance(latest_version, str):
            return None

        # Always return the cached value (stale or fresh — callers just want best-known).
        # We still parse checked_at so malformed timestamps fall back to None gracefully.
        checked_at_raw = data.get("checked_at")
        if isinstance(checked_at_raw, str):
            try:
                datetime.fromisoformat(checked_at_raw)
            except ValueError:
                return None

        return latest_version

    def check_in_background(self) -> None:
        """Spawn a background subprocess to refresh the PyPI version cache.

        Fire-and-forget — returns immediately.  Any failure (subprocess not found,
        permission error, network timeout, …) is silently swallowed.
        """
        if _is_opt_out_set():
            return

        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            script = f"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

v = None
try:
    req = urllib.request.Request(
        "https://pypi.org/pypi/spec-kitty-cli/json",
        headers={{"User-Agent": "spec-kitty-cli session-presence-upgrade-check"}},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        payload = json.load(response)
    info = payload.get("info") if isinstance(payload, dict) else None
    candidate = info.get("version") if isinstance(info, dict) else None
    if isinstance(candidate, str):
        v = candidate
except Exception:
    v = None

p = Path({str(CACHE_PATH)!r})
p.parent.mkdir(parents=True, exist_ok=True)
tmp = p.with_suffix(".tmp")
tmp.write_text(json.dumps({{
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "latest_version": v,
}}))
os.replace(tmp, p)
"""
            subprocess.Popen(
                ["python3", "-c", script],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:  # intentionally silent — background task must never raise
            pass
