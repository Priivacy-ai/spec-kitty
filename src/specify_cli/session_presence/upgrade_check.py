"""PyPI version cache management for the upgrade check mechanism.

Background refresh only — never blocks the foreground. Never raises on any failure.

Cache location: ``~/.kittify/last-cli-check.json``
TTL: 3600 seconds (1 hour)
"""

from __future__ import annotations

import json
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
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            script = (
                "import subprocess, json, os; "
                "from pathlib import Path; "
                "from datetime import datetime, timezone; "
                "r = subprocess.run("
                "    ['uv', 'pip', 'index', 'versions', 'spec-kitty-cli', '--quiet'],"
                "    capture_output=True, text=True, timeout=10"
                "); "
                "v = r.stdout.strip().split('\\n')[0] if r.returncode == 0 and r.stdout.strip() else None; "
                f"p = Path(r'{CACHE_PATH}'); "
                "p.parent.mkdir(parents=True, exist_ok=True); "
                "tmp = p.with_suffix('.tmp'); "
                "tmp.write_text(json.dumps({"
                "    'checked_at': datetime.now(timezone.utc).isoformat(),"
                "    'latest_version': v"
                "})); "
                "os.replace(tmp, p)"
            )
            subprocess.Popen(
                ["python3", "-c", script],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:  # intentionally silent — background task must never raise
            pass
