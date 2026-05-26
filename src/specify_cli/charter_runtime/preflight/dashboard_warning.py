"""Persistence helpers for the dashboard preflight banner (T025).

The dashboard CLI runs preflight before launching the server. The server
itself runs as a detached subprocess, so the warning is communicated via
a tiny JSON file under ``.kittify/`` that the server's API handler reads
on demand. This keeps the CLI / daemon boundary explicit and avoids
plumbing the warning through process arguments.

Schema:

```json
{"blocked_reason": "..."}
```

Absent file ⇒ no warning. Empty / corrupt file ⇒ no warning (best-effort;
the daemon must not crash because the CLI wrote a malformed banner).
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = [
    "write_preflight_warning",
    "clear_preflight_warning",
    "read_preflight_warning",
]


PREFLIGHT_WARNING_FILENAME = "preflight-warning.json"


def preflight_warning_path(repo_root: Path) -> Path:
    """Return the path used to persist the dashboard preflight warning."""
    return repo_root / ".kittify" / PREFLIGHT_WARNING_FILENAME


def write_preflight_warning(repo_root: Path, blocked_reason: str) -> None:
    """Persist a preflight ``blocked_reason`` for the dashboard SPA to render.

    The ``.kittify/`` directory is created if missing so this helper works
    in test fixtures that pre-create only the project root.
    """
    path = preflight_warning_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"blocked_reason": blocked_reason}
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def clear_preflight_warning(repo_root: Path) -> None:
    """Remove any persisted preflight warning (no-op if absent)."""
    preflight_warning_path(repo_root).unlink(missing_ok=True)


def read_preflight_warning(repo_root: Path) -> str | None:
    """Return the persisted ``blocked_reason`` or ``None``.

    Returns ``None`` for any failure mode (missing file, corrupt JSON,
    wrong shape) so the dashboard API stays operational even when the
    warning channel is misconfigured.
    """
    path = preflight_warning_path(repo_root)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    reason = data.get("blocked_reason")
    return reason if isinstance(reason, str) and reason else None
