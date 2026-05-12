"""Tests for the remediation pass on 6 existing issue-matrix.md files (T021).

Verifies that:
- Auto-normalized files have lowercase headers and provenance comments.
- Structural drift files have a sibling .remediation-note.md.
- Conforming files are untouched.

NOTE: The remediation changes live on the target branch
(fix/3.2.x-review-merge-gate-hardening). The lane worktree has these files
restored to mission-base state. The canonical location for these artifacts is
the main git repository root, not the worktree. These tests resolve the path
from the git common directory to find the authoritative files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast, pytest.mark.non_sandbox]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_repo_root() -> Path:
    """Find the main repository root (not the worktree root).

    In a git worktree, the .git file points to the common git dir.
    We use `git rev-parse --git-common-dir` to find the shared .git directory,
    then derive the main repo root from there.
    """
    worktree_root = Path(__file__).parents[5]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=worktree_root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            git_common = Path(result.stdout.strip())
            # git-common-dir is either absolute or relative to worktree_root
            if not git_common.is_absolute():
                git_common = worktree_root / git_common
            # Main repo root is the parent of the .git directory
            candidate = git_common.parent
            if (candidate / "kitty-specs").exists():
                return candidate
    except (OSError, subprocess.SubprocessError):
        pass
    # Fallback: use the worktree root
    return worktree_root


_REPO_ROOT = _find_repo_root()
_KITTY_SPECS = _REPO_ROOT / "kitty-specs"


def _mission_dir(slug: str) -> Path:
    return _KITTY_SPECS / slug


def _matrix(slug: str) -> Path:
    return _mission_dir(slug) / "issue-matrix.md"


def _remediation_note(slug: str) -> Path:
    return _mission_dir(slug) / ".remediation-note.md"


# ---------------------------------------------------------------------------
# release-3-2-0a5-tranche-1-01KQ7YXH
# ---------------------------------------------------------------------------


class TestTranche1Matrix:
    SLUG = "release-3-2-0a5-tranche-1-01KQ7YXH"

    def test_matrix_exists(self) -> None:
        assert _matrix(self.SLUG).exists()

    def test_header_lowercase(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        # Find the table header line
        for line in text.splitlines():
            if "|" in line and "issue" in line.lower() and "verdict" in line.lower():
                # Headers should be lowercase
                assert "| issue |" in line.lower()
                assert "Issue" not in line.split("|")[1] if len(line.split("|")) > 1 else True
                break

    def test_provenance_comment_present(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        assert "normalized 2026-05-12" in text

    def test_remediation_note_exists_for_multi_table(self) -> None:
        # This file has a summary Aggregate table → structural drift
        assert _remediation_note(self.SLUG).exists()

    def test_remediation_note_mentions_multi_table(self) -> None:
        note = _remediation_note(self.SLUG).read_text(encoding="utf-8")
        assert "ISSUE_MATRIX_MULTI_TABLE" in note


# ---------------------------------------------------------------------------
# release-3-2-0a6-tranche-2-01KQ9MKP
# ---------------------------------------------------------------------------


class TestTranche2Matrix:
    SLUG = "release-3-2-0a6-tranche-2-01KQ9MKP"

    def test_matrix_exists(self) -> None:
        assert _matrix(self.SLUG).exists()

    def test_provenance_comment_present(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        assert "normalized 2026-05-12" in text

    def test_remediation_note_exists(self) -> None:
        # Verifying tests column not in vocabulary → structural drift
        assert _remediation_note(self.SLUG).exists()

    def test_remediation_note_mentions_schema_drift(self) -> None:
        note = _remediation_note(self.SLUG).read_text(encoding="utf-8")
        assert "ISSUE_MATRIX_SCHEMA_DRIFT" in note

    def test_alias_fr_normalized(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        # FR(s) should be normalized to fr
        assert "FR(s)" not in text
        assert "| fr |" in text

    def test_alias_nfr_normalized(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        assert "NFR(s)" not in text
        assert "| nfr |" in text


# ---------------------------------------------------------------------------
# stability-and-hygiene-hardening-2026-04-01KQ4ARB
# ---------------------------------------------------------------------------


class TestStabilityMatrix:
    SLUG = "stability-and-hygiene-hardening-2026-04-01KQ4ARB"

    def test_matrix_exists(self) -> None:
        assert _matrix(self.SLUG).exists()

    def test_provenance_comment_present(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        assert "normalized 2026-05-12" in text

    def test_alias_theme_normalized_to_scope(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        # theme → scope (alias normalized)
        for line in text.splitlines():
            if "|" in line and "issue" in line.lower():
                assert "theme" not in line.lower()
                break

    def test_alias_wp_id_normalized_to_wp(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        for line in text.splitlines():
            if "|" in line and "issue" in line.lower():
                assert "wp_id" not in line.lower()
                break

    def test_remediation_note_exists_for_column_order(self) -> None:
        assert _remediation_note(self.SLUG).exists()

    def test_remediation_note_mentions_schema_drift(self) -> None:
        note = _remediation_note(self.SLUG).read_text(encoding="utf-8")
        assert "ISSUE_MATRIX_SCHEMA_DRIFT" in note


# ---------------------------------------------------------------------------
# stable-320-p1-release-confidence-01KQTPZC (no-op)
# ---------------------------------------------------------------------------


class TestP1ReleaseConfidenceMatrix:
    SLUG = "stable-320-p1-release-confidence-01KQTPZC"

    def test_matrix_exists(self) -> None:
        assert _matrix(self.SLUG).exists()

    def test_no_remediation_note(self) -> None:
        # This file was already conforming; no remediation note should exist
        assert not _remediation_note(self.SLUG).exists()

    def test_no_provenance_comment(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        # Conforming file should not have been touched
        assert "normalized 2026-05-12" not in text


# ---------------------------------------------------------------------------
# stable-320-release-blocker-cleanup-01KQW4DF
# ---------------------------------------------------------------------------


class TestReleaseBlockerMatrix:
    SLUG = "stable-320-release-blocker-cleanup-01KQW4DF"

    def test_matrix_exists(self) -> None:
        assert _matrix(self.SLUG).exists()

    def test_provenance_comment_present(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        assert "normalized 2026-05-12" in text

    def test_header_lowercase(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        # Find header line
        for line in text.splitlines():
            if "|" in line and "issue" in line.lower() and "verdict" in line.lower():
                assert "Issue" not in line
                assert "Verdict" not in line
                break

    def test_evidence_ref_alias_resolved(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        # "Evidence ref" → "evidence_ref"
        assert "Evidence ref" not in text
        assert "evidence_ref" in text

    def test_no_remediation_note(self) -> None:
        # Only capitalization drift — no structural issues
        assert not _remediation_note(self.SLUG).exists()


# ---------------------------------------------------------------------------
# charter-golden-path-e2e-tranche-1-01KQ806X
# ---------------------------------------------------------------------------


class TestCharterGoldenPathMatrix:
    SLUG = "charter-golden-path-e2e-tranche-1-01KQ806X"

    def test_matrix_exists(self) -> None:
        assert _matrix(self.SLUG).exists()

    def test_remediation_note_exists(self) -> None:
        assert _remediation_note(self.SLUG).exists()

    def test_remediation_note_mentions_multi_table(self) -> None:
        note = _remediation_note(self.SLUG).read_text(encoding="utf-8")
        assert "ISSUE_MATRIX_MULTI_TABLE" in note

    def test_no_auto_modification_to_matrix(self) -> None:
        text = _matrix(self.SLUG).read_text(encoding="utf-8")
        # This file was NOT auto-normalized (structural drift only)
        assert "normalized 2026-05-12" not in text
