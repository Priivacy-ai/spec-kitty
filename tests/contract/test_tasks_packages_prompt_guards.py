"""Contract guard: tasks-packages/prompt.md must not include plan_concern_refs in WP frontmatter.

FR-009: plan_concern_refs is a wps.yaml-only field. WPMetadata uses extra="forbid"; any WP
prompt file with plan_concern_refs in its frontmatter will cause `finalize-tasks --validate-only`
to raise a ValidationError.

Added after WP02 cycle-1 of mission #129 caught this exact violation.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract, pytest.mark.fast]

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS_PACKAGES_PROMPT = (
    REPO_ROOT / "src/doctrine/missions/mission-steps/software-dev/tasks-packages/prompt.md"
)

# Marker that identifies a WP prompt frontmatter template block (vs a wps.yaml example block)
_WP_FRONTMATTER_MARKER = "work_package_id:"


def _extract_frontmatter_blocks(content: str) -> list[str]:
    """Return all YAML blocks delimited by --- ... --- in a markdown document."""
    return re.findall(r"(?m)^---\n(.*?)\n---", content, re.DOTALL)


class TestFR009Guard:
    """plan_concern_refs must never appear in the WP prompt frontmatter template."""

    def test_prompt_file_exists(self) -> None:
        assert TASKS_PACKAGES_PROMPT.exists(), (
            f"tasks-packages/prompt.md not found at {TASKS_PACKAGES_PROMPT}"
        )

    def test_wp_frontmatter_template_has_no_plan_concern_refs(self) -> None:
        """The WP prompt frontmatter template block must not contain plan_concern_refs.

        Regression guard: WP02 cycle-1 of mission #129 caught a violation where
        plan_concern_refs was erroneously placed in this block. WPMetadata parses WP
        prompt files with extra='forbid'; an agent-generated WP with plan_concern_refs
        in its frontmatter would cause finalize-tasks --validate-only to raise
        ValidationError for every such file.
        """
        content = TASKS_PACKAGES_PROMPT.read_text(encoding="utf-8")
        blocks = _extract_frontmatter_blocks(content)
        wp_frontmatter_blocks = [b for b in blocks if _WP_FRONTMATTER_MARKER in b]
        assert wp_frontmatter_blocks, (
            "No WP frontmatter template block found in tasks-packages/prompt.md "
            f"(expected a --- block containing '{_WP_FRONTMATTER_MARKER}'). "
            "The guard cannot run — check whether the prompt structure changed."
        )
        for block in wp_frontmatter_blocks:
            assert "plan_concern_refs" not in block, (
                "plan_concern_refs found in the WP prompt frontmatter template block "
                "of tasks-packages/prompt.md. This field belongs in wps.yaml only. "
                "WPMetadata uses extra='forbid' and will reject any WP prompt file "
                "that carries this field in its frontmatter (FR-009)."
            )

    def test_warning_about_plan_concern_refs_is_present(self) -> None:
        """Verify the prompt still contains the FR-009 warning text.

        If someone deletes the warning while also inadvertently re-introducing the field
        into the frontmatter template, the previous test would catch the field; this test
        catches removal of the protective warning text.
        """
        content = TASKS_PACKAGES_PROMPT.read_text(encoding="utf-8")
        assert "plan_concern_refs" in content, (
            "tasks-packages/prompt.md no longer mentions plan_concern_refs at all. "
            "The prompt should contain wps.yaml example usage and FR-009 warnings. "
            "Check whether the prompt was accidentally truncated."
        )
        assert "wps.yaml" in content, (
            "tasks-packages/prompt.md no longer mentions wps.yaml. "
            "The prompt should guide agents to populate plan_concern_refs in wps.yaml."
        )
