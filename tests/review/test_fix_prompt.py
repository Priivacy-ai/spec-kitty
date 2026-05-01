"""Tests for fix-mode prompt generation (WP02).

Coverage target: 90%+ for src/specify_cli/review/fix_prompt.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.review.artifacts import AffectedFile, ReviewCycleArtifact
from specify_cli.review.fix_prompt import (
    _MAX_FULL_FILE_LINES,
    generate_fix_prompt,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_artifact(**kwargs: object) -> ReviewCycleArtifact:
    defaults: dict = {
        "cycle_number": 1,
        "wp_id": "WP01",
        "mission_slug": "066-review-loop-stabilization",
        "reviewer_agent": "claude",
        "verdict": "rejected",
        "reviewed_at": "2026-04-06T12:00:00Z",
        "affected_files": [
            AffectedFile(
                path="src/specify_cli/example.py",
                line_range="10-20",
            )
        ],
        "reproduction_command": "pytest tests/example/ -x",
        "body": "## Findings\n\nThe function is missing error handling.",
    }
    defaults.update(kwargs)
    return ReviewCycleArtifact(**defaults)  # type: ignore[arg-type]


def _write_source_file(tmp_path: Path, rel_path: str, content: str) -> Path:
    """Write a source file relative to tmp_path, creating parent dirs."""
    full = tmp_path / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full


# ---------------------------------------------------------------------------
# T007/T008: Unit tests for generate_fix_prompt
# ---------------------------------------------------------------------------


class TestGenerateFixPromptSingleFile:
    """test_generate_fix_prompt_single_file — one affected file, verify findings + code appear."""

    def test_contains_findings(self, tmp_path: Path) -> None:
        _write_source_file(tmp_path, "src/specify_cli/example.py", "def foo():\n    pass\n")
        artifact = _make_artifact()
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "The function is missing error handling." in prompt

    def test_contains_file_path(self, tmp_path: Path) -> None:
        _write_source_file(tmp_path, "src/specify_cli/example.py", "def foo():\n    pass\n")
        artifact = _make_artifact()
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "src/specify_cli/example.py" in prompt

    def test_contains_code(self, tmp_path: Path) -> None:
        content = "\n".join(f"line {i}" for i in range(1, 31))
        _write_source_file(tmp_path, "src/specify_cli/example.py", content)
        artifact = _make_artifact(affected_files=[AffectedFile(path="src/specify_cli/example.py", line_range="10-20")])
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        # Should show lines around 10-20 (with context)
        assert "line 10" in prompt

    def test_header_format(self, tmp_path: Path) -> None:
        _write_source_file(tmp_path, "src/specify_cli/example.py", "x = 1\n")
        artifact = _make_artifact()
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "# Fix Mode: WP01" in prompt
        assert "Cycle 1" in prompt


class TestGenerateFixPromptMultipleFiles:
    """test_generate_fix_prompt_multiple_files — three affected files, all appear in output."""

    def test_all_files_present(self, tmp_path: Path) -> None:
        files = [
            "src/a.py",
            "src/b.ts",
            "src/c.go",
        ]
        for f in files:
            _write_source_file(tmp_path, f, f"// content of {f}\n")

        artifact = _make_artifact(
            affected_files=[AffectedFile(path=f) for f in files],
        )
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        for f in files:
            assert f in prompt

    def test_language_detection(self, tmp_path: Path) -> None:
        """Language tags are set based on file extension."""
        _write_source_file(tmp_path, "src/foo.py", "pass\n")
        _write_source_file(tmp_path, "src/bar.ts", "const x = 1;\n")
        artifact = _make_artifact(
            affected_files=[
                AffectedFile(path="src/foo.py"),
                AffectedFile(path="src/bar.ts"),
            ],
        )
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "```python" in prompt
        assert "```typescript" in prompt


class TestGenerateFixPromptWithLineRange:
    """test_generate_fix_prompt_with_line_range — snippet is focused on the range."""

    def test_shows_relevant_lines(self, tmp_path: Path) -> None:
        lines = [f"line {i:03d}" for i in range(1, 101)]
        content = "\n".join(lines)
        _write_source_file(tmp_path, "src/big.py", content)

        artifact = _make_artifact(affected_files=[AffectedFile(path="src/big.py", line_range="50-60")])
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        # Lines in range + context should appear
        assert "line 050" in prompt
        assert "line 060" in prompt

    def test_line_range_label_shown(self, tmp_path: Path) -> None:
        _write_source_file(tmp_path, "src/big.py", "x = 1\n" * 20)
        artifact = _make_artifact(affected_files=[AffectedFile(path="src/big.py", line_range="5-10")])
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "lines 5-10" in prompt

    def test_context_lines_included(self, tmp_path: Path) -> None:
        """Lines slightly outside the range should appear (context padding)."""
        lines = [f"L{i}" for i in range(1, 31)]
        _write_source_file(tmp_path, "src/ctx.py", "\n".join(lines))
        artifact = _make_artifact(affected_files=[AffectedFile(path="src/ctx.py", line_range="15-15")])
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        # Context: lines 10-20 (15 ± 5)
        assert "L10" in prompt
        assert "L20" in prompt


class TestGenerateFixPromptWithoutLineRange:
    """test_generate_fix_prompt_without_line_range — full file shown (truncated if large)."""

    def test_short_file_shown_fully(self, tmp_path: Path) -> None:
        content = "def hello():\n    return 42\n"
        _write_source_file(tmp_path, "src/short.py", content)
        artifact = _make_artifact(
            affected_files=[AffectedFile(path="src/short.py")]  # no line_range
        )
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "def hello():" in prompt
        assert "return 42" in prompt
        assert "only the first portion" not in prompt

    def test_long_file_truncated(self, tmp_path: Path) -> None:
        lines = [f"line {i}" for i in range(1, _MAX_FULL_FILE_LINES + 50)]
        _write_source_file(tmp_path, "src/long.py", "\n".join(lines))
        artifact = _make_artifact(affected_files=[AffectedFile(path="src/long.py")])
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "only the first portion" in prompt
        # The line beyond the cap should NOT appear
        assert f"line {_MAX_FULL_FILE_LINES + 1}" not in prompt


class TestFixPromptSizeVsOriginal:
    """test_fix_prompt_size_vs_original — fix prompt < 25% of a typical 491-line WP prompt."""

    def test_prompt_smaller_than_25_percent(self, tmp_path: Path) -> None:
        # A typical WP prompt is ~491 lines × ~50 chars ≈ 24 550 chars
        typical_wp_size = 491 * 50  # characters

        # Single-file finding, short snippet
        source_lines = [f"def func_{i}():\n    pass" for i in range(5)]
        _write_source_file(tmp_path, "src/target.py", "\n".join(source_lines))

        artifact = _make_artifact(
            body="## Issues\n\nFix the function signature.\n",
            affected_files=[AffectedFile(path="src/target.py", line_range="1-3")],
            reproduction_command="pytest tests/ -x",
        )
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        threshold = typical_wp_size * 0.25
        assert len(prompt) < threshold, (
            f"Fix prompt ({len(prompt)} chars) should be < 25% of typical WP prompt ({typical_wp_size} chars), threshold={threshold:.0f}"
        )


class TestGenerateFixPromptMissingFile:
    """test_generate_fix_prompt_missing_file — affected file doesn't exist, handled gracefully."""

    def test_missing_file_no_exception(self, tmp_path: Path) -> None:
        artifact = _make_artifact(affected_files=[AffectedFile(path="src/nonexistent.py")])
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "src/nonexistent.py" in prompt
        assert "File not found" in prompt

    def test_missing_file_still_contains_findings(self, tmp_path: Path) -> None:
        artifact = _make_artifact(
            body="Critical bug in nonexistent.py",
            affected_files=[AffectedFile(path="src/gone.py")],
        )
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "Critical bug in nonexistent.py" in prompt


class TestFixPromptIncludesReproductionCommand:
    """test_fix_prompt_includes_reproduction_command — reproduction_command appears in output."""

    def test_reproduction_command_present(self, tmp_path: Path) -> None:
        _write_source_file(tmp_path, "src/example.py", "pass\n")
        artifact = _make_artifact(reproduction_command="pytest tests/review/ -v --tb=short")
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "pytest tests/review/ -v --tb=short" in prompt

    def test_no_reproduction_command_omits_section(self, tmp_path: Path) -> None:
        _write_source_file(tmp_path, "src/example.py", "pass\n")
        artifact = _make_artifact(reproduction_command=None)
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "## Reproduction" not in prompt

    def test_instructions_include_move_task(self, tmp_path: Path) -> None:
        _write_source_file(tmp_path, "src/example.py", "pass\n")
        artifact = _make_artifact()
        prompt = generate_fix_prompt(
            artifact=artifact,
            worktree_path=tmp_path,
            mission_slug="066-review-loop-stabilization",
            wp_id="WP01",
        )
        assert "move-task WP01 --to for_review" in prompt
        assert "066-review-loop-stabilization" in prompt
