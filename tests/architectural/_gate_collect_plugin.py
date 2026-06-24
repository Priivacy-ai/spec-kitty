"""Collection-only pytest plugin for the gate-coverage checker (Issue #2034).

Loaded via ``-p tests.architectural._gate_collect_plugin`` during a
``--collect-only`` pass. For every collected item it records
``{nodeid, relpath, markers}`` (marker names exactly as pytest's ``-m``
evaluator sees them, via :meth:`~_pytest.nodes.Node.iter_markers`) to the JSON
path named by ``$SK_GATE_DUMP``, then clears the item list so nothing executes.

``$SK_GATE_REPO`` gives the repo root used to relativize each test's path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    repo = Path(os.environ["SK_GATE_REPO"]).resolve()
    records: list[dict[str, Any]] = []
    for item in items:
        try:
            relpath = Path(str(item.path)).resolve().relative_to(repo).as_posix()
        except (ValueError, OSError):
            relpath = str(getattr(item, "path", item.nodeid.split("::", 1)[0]))
        markers = sorted({mark.name for mark in item.iter_markers()})
        records.append({"nodeid": item.nodeid, "relpath": relpath, "markers": markers})
    Path(os.environ["SK_GATE_DUMP"]).write_text(
        json.dumps(records), encoding="utf-8"
    )
    # Suppress execution: this is a collection-only introspection pass.
    items[:] = []
