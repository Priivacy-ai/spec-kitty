"""Shared constants for doctrine test suite.

DOCTRINE_SOURCE_ROOT is the canonical path to the in-repo doctrine source tree.
Compliance-guard and consistency tests import this constant instead of
hardcoding ``REPO_ROOT / "src" / "doctrine"`` independently.  The path is
intentionally *not* routed through ``MissionTemplateRepository`` — these tests
act as layout canaries and should break if the directory structure changes.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
"""Repository root, resolved from ``tests/doctrine/conftest.py``."""

DOCTRINE_SOURCE_ROOT: Path = REPO_ROOT / "src" / "doctrine"
"""Canonical on-disk path to the doctrine source tree (``src/doctrine/``)."""
