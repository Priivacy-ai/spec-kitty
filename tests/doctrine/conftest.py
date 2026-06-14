"""Shared constants for doctrine test suite.

DOCTRINE_SOURCE_ROOT is the canonical path to the in-repo doctrine source tree.
Compliance-guard and consistency tests import this constant instead of
hardcoding ``REPO_ROOT / "src" / "doctrine"`` independently.  The path is
intentionally *not* routed through ``MissionTemplateRepository`` — these tests
act as layout canaries and should break if the directory structure changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from doctrine.drg.models import DRGGraph

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
"""Repository root, resolved from ``tests/doctrine/conftest.py``."""

DOCTRINE_SOURCE_ROOT: Path = REPO_ROOT / "src" / "doctrine"
"""Canonical on-disk path to the doctrine source tree (``src/doctrine/``)."""

SHIPPED_GRAPH_PATH: Path = DOCTRINE_SOURCE_ROOT / "graph.yaml"
"""Canonical on-disk path to the shipped DRG (``src/doctrine/graph.yaml``)."""


# ---------------------------------------------------------------------------
# Shipped DRG graph cache (WP03/T012, FR-009, NFR-007)
# ---------------------------------------------------------------------------
#
# Several doctrine tests re-run ``load_graph(graph.yaml)`` (~0.18s each) and
# then ``merge_layers``/``assert_valid`` on the SAME shipped graph. This
# session fixture loads, merges, and validates the shipped graph exactly ONCE
# and hands read-only consumers the resulting ``DRGGraph``.
#
# READ-ONLY contract: consumers may only *read* the returned graph (node/edge
# lookups, traversal). They must NOT mutate it — a ``DRGGraph`` mutated in one
# test would bleed into every other test sharing the session fixture. Tests
# that need to construct/modify their own graph keep building synthetic
# in-memory graphs (e.g. ``test_drg_relations.py`` / ``test_drg_merge.py``).
#
# CARVE-OUTS (must NOT use this cache):
#   * ``test_graph_file_exists`` / ``test_shipped_graph_yaml_is_fresh`` and any
#     freshness/existence canary — they assert the *on-disk* file, not a parsed
#     in-memory cache, and must read from disk every run.
#   * idempotency / "loads twice" tests — they assert independent load behaviour.


@pytest.fixture(scope="session")
def shipped_drg_graph() -> DRGGraph:
    """Load + merge + validate the shipped DRG once per session (read-only).

    Imported lazily so that merely collecting the doctrine suite does not pay
    the doctrine import cost; the fixture body runs only when a test requests
    it. Consumers MUST treat the returned graph as read-only (see module note).
    """
    from doctrine.drg.loader import load_graph, merge_layers
    from doctrine.drg.validator import assert_valid

    graph = load_graph(SHIPPED_GRAPH_PATH)
    merged = merge_layers(graph, None)
    assert_valid(merged)
    return merged
