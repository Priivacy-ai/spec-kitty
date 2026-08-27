"""Keep CI control-plane cursors out of this product repository (issue #288).

CI cursors and baselines belong only in the planning repository (`PROGRAM.md`
§3) — this repo is a product repo, not the control plane. `state/ci-spec-kitty-saas.json`
was a stray CI cursor committed here by mistake; this guard fails if a
`state/ci-*.json` file is ever committed again.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXCLUDED_DIR_NAMES = frozenset({".git", ".venv", "node_modules"})


def scan_for_ci_control_plane_cursors(root: Path) -> list[Path]:
    """Return every `<...>/state/ci-*.json` cursor file under *root*."""
    violations: list[Path] = []
    for state_dir in root.rglob("state"):
        if not state_dir.is_dir():
            continue
        if any(part in _EXCLUDED_DIR_NAMES for part in state_dir.parts):
            continue
        violations.extend(state_dir.glob("ci-*.json"))
    return sorted(violations)


def test_no_ci_control_plane_cursor_committed() -> None:
    violations = scan_for_ci_control_plane_cursors(_REPO_ROOT)
    assert violations == [], "CI cursors and baselines belong only in the planning repository (PROGRAM.md §3), never in this product repo:\n" + "\n".join(
        str(path.relative_to(_REPO_ROOT)) for path in violations
    )


def test_scanner_rejects_a_planted_cursor(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    planted = state_dir / "ci-spec-kitty-saas.json"
    planted.write_text("{}\n", encoding="utf-8")
    assert scan_for_ci_control_plane_cursors(tmp_path) == [planted]


def test_scanner_ignores_non_matching_state_contents(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "notes.json").write_text("{}\n", encoding="utf-8")
    (state_dir / "ci-baseline.txt").write_text("not json\n", encoding="utf-8")
    assert scan_for_ci_control_plane_cursors(tmp_path) == []
