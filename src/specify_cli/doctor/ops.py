"""Op orphan detection for spec-kitty doctor ops."""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.invocation.writer import EVENTS_DIR

_NON_OP_JSONL = {
    "ops-index.jsonl",
    "lifecycle.jsonl",
    "propagation-errors.jsonl",
}


def _has_completed_event(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict) and event.get("event") == "completed":
                    return True
    except OSError:
        return False
    return False


def list_orphan_ops(repo_root: Path) -> list[Path]:
    ops_dir = repo_root / EVENTS_DIR
    if not ops_dir.exists():
        return []
    return [
        path
        for path in sorted(ops_dir.glob("*.jsonl"))
        if path.name not in _NON_OP_JSONL and not _has_completed_event(path)
    ]
