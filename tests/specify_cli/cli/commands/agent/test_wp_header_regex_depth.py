"""WP02 / FR-004: Regression tests for WP header regex depth across the section-walk sites.

Each site must accept ``##``, ``###``, ``####`` headings and reject ``#####``+.

Sites under test:
1. ``_parse_wp_sections_from_tasks_md()`` in mission.py
2-3. ``iter_wp_section_subtask_rows()`` in core/subtask_rows.py — the canonical
     WP-section walker (section start + section end), shared by the migration
     backfill, the dashboard progress counter, and the ``move-task --to planned``
     rollback writer.

#2816 IC-10 rerouted the lane-transition guard (``emit._infer_subtasks_complete``)
onto the event-log snapshot — roster from the WP ``subtasks:`` frontmatter,
completion from the reduced ``subtasks`` slot — so the guard is NO LONGER a
``tasks.md`` section-walk site and carries no heading-depth semantics. The
heading-depth + canonical-only regressions live entirely on the walker surface
below (its remaining consumers), where they are still load-bearing.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Site 1: mission.py — _parse_wp_sections_from_tasks_md()
# ---------------------------------------------------------------------------


pytestmark = [pytest.mark.unit, pytest.mark.fast]

class TestParseWpSectionsHeaderDepth:
    """_parse_wp_sections_from_tasks_md must detect WP sections at h2/h3/h4."""

    @pytest.mark.parametrize(
        "depth,expected",
        [
            ("##", True),
            ("###", True),
            ("####", True),
            ("#####", False),
        ],
        ids=["h2", "h3", "h4", "h5-boundary"],
    )
    def test_wp_header_depth(self, depth: str, expected: bool) -> None:
        from specify_cli.cli.commands.agent.mission import _parse_wp_sections_from_tasks_md

        content = f"{depth} WP01: Setup\n\nSome body content\n"
        result = _parse_wp_sections_from_tasks_md(content)
        assert ("WP01" in result) == expected, f"Header '{depth} WP01' should {'be' if expected else 'NOT be'} detected"

    @pytest.mark.parametrize(
        "depth",
        ["##", "###", "####"],
        ids=["h2", "h3", "h4"],
    )
    def test_wp_header_with_work_package_prefix(self, depth: str) -> None:
        """'Work Package' prefix variant must also work at supported depths."""
        from specify_cli.cli.commands.agent.mission import _parse_wp_sections_from_tasks_md

        content = f"{depth} Work Package WP01: Setup\n\nBody\n"
        result = _parse_wp_sections_from_tasks_md(content)
        assert "WP01" in result

    def test_multiple_sections_mixed_depth(self) -> None:
        """Parser must handle mixed heading depths within a single tasks.md."""
        from specify_cli.cli.commands.agent.mission import _parse_wp_sections_from_tasks_md

        content = "## WP01: Setup\n\nWP01 body\n\n### WP02: Core\n\nWP02 body\n\n#### WP03: Tests\n\nWP03 body\n"
        result = _parse_wp_sections_from_tasks_md(content)
        assert set(result.keys()) == {"WP01", "WP02", "WP03"}


# ---------------------------------------------------------------------------
# NOTE: ``emit._infer_subtasks_complete`` was formerly a header-depth site here.
# #2816 IC-10 rerouted it off ``tasks.md`` onto the frontmatter roster + reduced
# snapshot, so it no longer parses WP-section headings — its header-depth tests
# were retired (superseded by the walker-surface tests below, which own the
# remaining ``tasks.md`` section-walk consumers). The gate's own behavior is
# covered by ``test_infer_subtasks_primary.py`` and ``test_diffcov_2684_*``.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Sites 2-3: the canonical WP-section walker
# ``core.subtask_rows.iter_wp_section_subtask_rows`` (section start + section
# end). #2816 IC-10 rerouted the lane-transition guard onto the event-log
# snapshot (roster from frontmatter, completion from the reduced ``subtasks``
# slot), so the guard is no longer a section-walk site. The walker below is the
# surface the backfill / dashboard / rollback still share, so the heading-depth
# + canonical-only regressions live here now, on that surface.
# ---------------------------------------------------------------------------


def _walker_unchecked(content: str, wp_id: str) -> list[str]:
    from specify_cli.core.subtask_rows import iter_wp_section_subtask_rows

    return [tid for tid, checked in iter_wp_section_subtask_rows(content, wp_id) if not checked]


def _walker_found_any(content: str, wp_id: str) -> bool:
    from specify_cli.core.subtask_rows import iter_wp_section_subtask_rows

    return bool(list(iter_wp_section_subtask_rows(content, wp_id)))


class TestSectionWalkerHeaderDepth:
    """The canonical WP-section walker must detect WP sections at h2/h3/h4."""

    @pytest.mark.parametrize(
        "depth,expected_found",
        [
            ("##", True),
            ("###", True),
            ("####", True),
            ("#####", False),
        ],
        ids=["h2", "h3", "h4", "h5-boundary"],
    )
    def test_wp_section_detection(self, depth: str, expected_found: bool) -> None:
        """WP section start regex must match at h2-h4 depth only."""
        content = f"{depth} WP01: Setup\n\n- [ ] T001 Do something\n"
        assert _walker_found_any(content, "WP01") == expected_found, (
            f"Header '{depth} WP01' should {'be' if expected_found else 'NOT be'} detected"
        )

    def test_section_end_boundary(self) -> None:
        """Section-end regex must stop scanning at the next WP heading."""
        content = "### WP01: Setup\n\n- [x] T001 Done\n\n### WP02: Core\n\n- [ ] T002 Not done\n"
        assert _walker_unchecked(content, "WP01") == [], "WP01's unchecked belongs to WP02, not WP01"

    def test_section_end_boundary_h4(self) -> None:
        """Section-end regex must work with #### headings too."""
        content = "#### WP01: Setup\n\n- [x] T001 Done\n\n#### WP02: Core\n\n- [ ] T002 Not done\n"
        assert _walker_unchecked(content, "WP01") == [], "WP01 section should end at #### WP02 boundary"


# ---------------------------------------------------------------------------
# Finding 2: only canonical ``- [ ] T###`` rows are WP subtask rows.
# Validation/command rows, prose, and fenced code blocks must NOT count.
# ---------------------------------------------------------------------------


class TestSectionWalkerCanonicalOnly:
    """The canonical WP-section walker must only yield canonical T### subtasks."""

    def test_real_unchecked_tasks_still_counted(self) -> None:
        """Genuine ``- [ ] T###`` rows must still be yielded (regression guard)."""
        content = (
            "## WP01: Setup\n\n"
            "### Included Subtasks\n"
            "- [ ] T001 Create the module\n"
            "- [x] T002 Already done\n"
            "- [ ] T003 Wire it up\n"
        )
        assert _walker_unchecked(content, "WP01") == ["T001", "T003"]

    def test_validation_command_rows_do_not_count(self) -> None:
        """Validation/checklist command rows like ``- [ ] swift test`` must NOT count."""
        content = (
            "## WP01: Setup\n\n"
            "### Included Subtasks\n"
            "- [x] T001 Implement feature\n\n"
            "### Validation\n"
            "- [ ] swift test\n"
            "- [ ] git status --short\n"
            "- [ ] npm run lint\n"
            "- [ ] Review the diff before merging\n"
        )
        assert _walker_unchecked(content, "WP01") == []

    def test_fenced_code_task_like_lines_do_not_count(self) -> None:
        """Task-like lines inside fenced code blocks must NOT count."""
        content = (
            "## WP01: Setup\n\n"
            "### Included Subtasks\n"
            "- [x] T001 Implement feature\n\n"
            "### Implementation Notes\n"
            "Example task list to mimic in the README:\n"
            "```markdown\n"
            "- [ ] T999 This is documentation, not a real subtask\n"
            "- [ ] T998 Neither is this\n"
            "```\n"
        )
        assert _walker_unchecked(content, "WP01") == []

    def test_mixed_real_and_noise(self) -> None:
        """Real unchecked T### is yielded even when surrounded by command/code noise."""
        content = (
            "## WP01: Setup\n\n"
            "### Included Subtasks\n"
            "- [ ] T001 Real unchecked subtask\n"
            "- [ ] swift test\n"
            "```sh\n"
            "- [ ] T500 fenced noise\n"
            "```\n"
            "- [ ] git status --short\n"
        )
        assert _walker_unchecked(content, "WP01") == ["T001"]
