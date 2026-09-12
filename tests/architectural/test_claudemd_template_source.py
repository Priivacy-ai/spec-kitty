"""Architectural test: CLAUDE.md must not point at the retired template source path.

Mission ``self-documenting-repo-01M0287X`` WP02 (FR-002) found CLAUDE.md's
"Template Source Location" section, flow diagram, and "Use Canonical
Sources" section still pointing mission-step-prompt authors at
``src/charter/offering/missions/mission-steps/`` — a path that no longer exists.
The canonical source is ``packs/built-in/missions/mission-steps/`` (see
``CLAUDE.md``'s own "Template Source Location" table). This test pins the
correction: it fails if the stale path fragment ever reappears in
CLAUDE.md, whether via a hand-edit, a bad merge, or copy-paste from an old
mission artifact.

``CLAUDE.md`` at the repo root is a symlink to ``AGENTS.md`` (both agents
read the same content under different filenames); ``Path.read_text``
follows the symlink transparently, so this test scans through whichever
name is passed without needing special-case handling.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLAUDE_MD = _REPO_ROOT / "CLAUDE.md"
_STALE_TEMPLATE_SOURCE_FRAGMENT = "src/charter/offering/missions/"


def test_claudemd_has_no_stale_mission_steps_source_path() -> None:
    """CLAUDE.md must not reference the retired src/charter/offering/missions/ template source."""
    content = _CLAUDE_MD.read_text(encoding="utf-8")
    assert _STALE_TEMPLATE_SOURCE_FRAGMENT not in content, (
        f"CLAUDE.md still references the retired template source path "
        f"{_STALE_TEMPLATE_SOURCE_FRAGMENT!r}; the canonical source is "
        f"packs/built-in/missions/mission-steps/ (WP02, FR-002)."
    )
