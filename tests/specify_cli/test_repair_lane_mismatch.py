"""Regression coverage for #2921: ``repair_lane_mismatch`` frontmatter corruption.

``repair_lane_mismatch`` (src/specify_cli/task_metadata_validation.py) destructures
``parse_frontmatter``'s third return value -- the *raw frontmatter text* -- into a
variable named ``padding``, then threads it into ``build_document(fm, body, padding)``,
whose third parameter is the *trailing whitespace* between the closing ``---`` fence
and the body. Feeding raw frontmatter text into that slot splices a duplicated,
stale frontmatter block into the rebuilt document and breaks the closing fence.

This test seeds a realistic WP file (production-shaped frontmatter fields, a
non-trivial body) with a lane mismatch, repairs it, and asserts the repaired file
is a single well-formed document: one frontmatter block, corrected ``lane``, a
clean fence, and an intact, non-duplicated body.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.frontmatter import write_frontmatter
from specify_cli.task_metadata_validation import (
    repair_lane_mismatch,
    validate_task_metadata,
)
from specify_cli.template import parse_frontmatter

REALISTIC_FRONTMATTER = {
    "work_package_id": "WP01",
    "title": "Read-side placement seam migration (Cluster A)",
    "lane": "planned",
    "dependencies": [],
    "requirement_refs": ["FR-001", "FR-002"],
    "tracker_refs": ["#2921"],
    "planning_base_branch": "main",
    "merge_target_branch": "main",
    "subtasks": ["T001", "T002", "T003"],
    "phase": "Phase 1 - Read-side seam",
    "assignee": "",
    "agent": "claude:sonnet:python-pedro:implementer",
    "authoritative_surface": "src/specify_cli/task_metadata_validation.py",
    "execution_mode": "code_change",
    "owned_files": [
        "src/specify_cli/task_metadata_validation.py",
        "tests/specify_cli/test_repair_lane_mismatch.py",
    ],
}

REALISTIC_BODY = """
# WP01: Fix repair_lane_mismatch frontmatter corruption

## Objective

Repair the read-side placement seam so that legacy lane-repair no longer
corrupts WP frontmatter when rewriting the file.

## Acceptance Criteria

- Repaired files contain exactly one frontmatter block.
- The corrected `lane` value matches the directory the file lives in.
- `validate_task_metadata()` reports zero issues after repair.

## Activity Log

- 2026-07-27T00:00:00Z: created via /spec-kitty.tasks
"""


def _seed_mismatched_wp_file(tmp_path: Path) -> Path:
    """Create a WP file under ``tasks/for_review/`` with a stale ``lane: planned``."""
    task_file = tmp_path / "tasks" / "for_review" / "WP01.md"
    task_file.parent.mkdir(parents=True)
    write_frontmatter(task_file, REALISTIC_FRONTMATTER, REALISTIC_BODY)
    return task_file


class TestRepairLaneMismatchFrontmatterCorruption:
    def test_repair_produces_exactly_one_clean_frontmatter_block(self, tmp_path: Path) -> None:
        """Green (post-fix): the repaired file is a single, well-formed document."""
        task_file = _seed_mismatched_wp_file(tmp_path)

        was_repaired, error = repair_lane_mismatch(task_file, agent="claude", shell_pid="12345")

        assert was_repaired is True
        assert error is None

        raw = task_file.read_text(encoding="utf-8-sig")

        # Exactly one opening fence and the matching closing fence -- i.e. no
        # duplicated frontmatter block was spliced into the document.
        assert raw.startswith("---\n"), "document must open with a clean frontmatter fence"
        assert raw.count("\n---\n") == 1, (
            f"expected exactly one closing '---' fence, found corruption in:\n{raw[:800]}"
        )

        frontmatter, body, _ = parse_frontmatter(raw)
        assert frontmatter.get("lane") == "for_review", "lane must be corrected to match the directory"
        assert frontmatter.get("work_package_id") == "WP01"

        # Body must be present, intact, and NOT duplicated.
        assert "Fix repair_lane_mismatch frontmatter corruption" in body
        assert body.count("## Objective") == 1, "body must not be duplicated"
        assert body.count("## Acceptance Criteria") == 1

        assert validate_task_metadata(task_file) == []

    def test_repair_does_not_corrupt_body_on_multiple_repairs(self, tmp_path: Path) -> None:
        """A second no-op call (already-matching lane) must not re-corrupt the file."""
        task_file = _seed_mismatched_wp_file(tmp_path)

        was_repaired, error = repair_lane_mismatch(task_file, agent="claude", shell_pid="1")
        assert was_repaired is True
        assert error is None

        # Lane now matches directory -- second call should be a no-op.
        was_repaired_again, error_again = repair_lane_mismatch(task_file, agent="claude", shell_pid="2")
        assert was_repaired_again is False
        assert error_again is None

        raw = task_file.read_text(encoding="utf-8-sig")
        assert raw.count("\n---\n") == 1
        assert validate_task_metadata(task_file) == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
