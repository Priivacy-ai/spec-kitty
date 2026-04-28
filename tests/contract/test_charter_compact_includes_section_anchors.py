"""FR-034 contract: charter compact view preserves IDs + section anchors.

Authority: ``kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/spec.md``
section FR-034 and ``research.md`` D13.

The compact charter view must surface every directive ID, tactic ID, and
section anchor that the bootstrap view would emit. Only the long-form
prose body of each section may be elided. Issue #790 traced bad agent
behaviour to compact mode silently dropping these identifiers.

This contract test is intentionally surface-level: it pins the
:func:`charter.compact.render_compact_view` API against a hand-written
bootstrap view of each fixture charter. We do not exercise the full DRG
loader here -- that is covered by the integration suite. The bootstrap
view is computed from the fixture text using the same anchor extractor
the compact path uses, so any drift in either implementation is caught
by the parity assertion.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.compact import (
    CompactView,
    extract_section_anchors,
    render_compact_view,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "charters"


def _load_fixtures() -> list[Path]:
    return sorted(FIXTURES.glob("*.md"))


def _bootstrap_directive_ids(charter_text: str) -> list[str]:
    """Return DIRECTIVE_* IDs in declaration order.

    Mirrors what the bootstrap renderer surfaces: any ``DIRECTIVE_NNN``
    token mentioned in the charter body is part of the bootstrap view's
    ID set.
    """
    import re

    seen: list[str] = []
    visited: set[str] = set()
    for match in re.finditer(r"DIRECTIVE_\d+", charter_text):
        token = match.group(0)
        if token not in visited:
            visited.add(token)
            seen.append(token)
    return seen


def _bootstrap_tactic_ids(charter_text: str) -> list[str]:
    """Return TAC-* IDs in declaration order."""
    import re

    seen: list[str] = []
    visited: set[str] = set()
    for match in re.finditer(r"TAC-\d+", charter_text):
        token = match.group(0)
        if token not in visited:
            visited.add(token)
            seen.append(token)
    return seen


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """A throwaway repo root with no governance config.

    The compact renderer degrades gracefully when governance is
    unresolved; we still get an ID-bearing view back, which is exactly
    the contract surface this test pins.
    """
    return tmp_path


@pytest.mark.parametrize("fixture_path", _load_fixtures(), ids=lambda p: p.name)
def test_compact_preserves_directive_ids(fixture_path: Path, repo_root: Path) -> None:
    charter_text = fixture_path.read_text(encoding="utf-8")
    bootstrap_directive_ids = _bootstrap_directive_ids(charter_text)
    bootstrap_tactic_ids = _bootstrap_tactic_ids(charter_text)

    compact: CompactView = render_compact_view(
        repo_root,
        directive_ids=bootstrap_directive_ids,
        tactic_ids=bootstrap_tactic_ids,
        charter_text=charter_text,
    )

    assert set(compact.directive_ids) >= set(bootstrap_directive_ids), (
        f"Compact view dropped directive IDs from {fixture_path.name}: "
        f"missing {set(bootstrap_directive_ids) - set(compact.directive_ids)}"
    )

    for directive_id in bootstrap_directive_ids:
        assert directive_id in compact.text, (
            f"Compact text for {fixture_path.name} is missing literal "
            f"directive ID {directive_id!r}."
        )


@pytest.mark.parametrize("fixture_path", _load_fixtures(), ids=lambda p: p.name)
def test_compact_preserves_tactic_ids(fixture_path: Path, repo_root: Path) -> None:
    charter_text = fixture_path.read_text(encoding="utf-8")
    bootstrap_tactic_ids = _bootstrap_tactic_ids(charter_text)

    compact: CompactView = render_compact_view(
        repo_root,
        tactic_ids=bootstrap_tactic_ids,
        charter_text=charter_text,
    )

    assert set(compact.tactic_ids) == set(bootstrap_tactic_ids), (
        f"Compact view tactic IDs drifted from bootstrap on "
        f"{fixture_path.name}: "
        f"compact={sorted(compact.tactic_ids)}, "
        f"bootstrap={sorted(bootstrap_tactic_ids)}"
    )

    for tactic_id in bootstrap_tactic_ids:
        assert tactic_id in compact.text


@pytest.mark.parametrize("fixture_path", _load_fixtures(), ids=lambda p: p.name)
def test_compact_preserves_section_anchors(fixture_path: Path, repo_root: Path) -> None:
    charter_text = fixture_path.read_text(encoding="utf-8")
    bootstrap_anchors = extract_section_anchors(charter_text)
    assert bootstrap_anchors, (
        f"Fixture {fixture_path.name} has no Markdown headings; the "
        "test would be vacuous. Add at least one `# heading`."
    )

    compact: CompactView = render_compact_view(
        repo_root,
        charter_text=charter_text,
    )

    assert set(compact.section_anchors) == set(bootstrap_anchors), (
        f"Compact view dropped section anchors from {fixture_path.name}: "
        f"missing {set(bootstrap_anchors) - set(compact.section_anchors)}"
    )
    for anchor in bootstrap_anchors:
        assert anchor in compact.text, (
            f"Compact text for {fixture_path.name} is missing literal "
            f"section anchor {anchor!r}."
        )


@pytest.mark.parametrize("fixture_path", _load_fixtures(), ids=lambda p: p.name)
def test_compact_view_is_meaningfully_smaller_than_charter(
    fixture_path: Path, repo_root: Path
) -> None:
    """Sanity: compact must not bloat back to bootstrap-equivalent size.

    Heuristic: compact text must be smaller than the charter body. This
    is intentionally loose -- the contract is parity of IDs/anchors, not
    a strict ratio -- but it catches the failure mode where compact
    accidentally inlines the entire prose body.
    """
    charter_text = fixture_path.read_text(encoding="utf-8")
    compact = render_compact_view(repo_root, charter_text=charter_text)
    assert len(compact.text) < max(1, len(charter_text)), (
        f"Compact view for {fixture_path.name} is not smaller than the "
        f"charter body (compact={len(compact.text)}, "
        f"charter={len(charter_text)})."
    )
