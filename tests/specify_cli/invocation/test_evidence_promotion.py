"""Tests for evidence artifact promotion (Tier 2) via complete_invocation()."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.invocation.executor import ProfileInvocationExecutor


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "profiles"

_COMPACT_CTX = MagicMock()
_COMPACT_CTX.mode = "compact"
_COMPACT_CTX.text = "test governance context"


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal project with fixture profiles."""
    profiles_dir = tmp_path / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)
    (tmp_path / ".kittify" / "events" / "profile-invocations").mkdir(parents=True)
    return tmp_path


def _make_executor_with_started_record(
    tmp_path: Path,
) -> tuple[ProfileInvocationExecutor, str]:
    """Create an executor and start an invocation; return (executor, invocation_id)."""
    project = _setup_project(tmp_path)
    with patch(
        "specify_cli.invocation.executor.build_charter_context",
        return_value=_COMPACT_CTX,
    ):
        executor = ProfileInvocationExecutor(project)
        profiles = list(executor._registry.list_all())
        if not profiles:
            pytest.skip("No fixture profiles available")
        profile = profiles[0]
        payload = executor.invoke(
            request_text="test evidence request",
            profile_hint=profile.profile_id,
            actor="claude",
        )
    return executor, payload.invocation_id


def test_complete_with_evidence_creates_tier2_directory(tmp_path: Path) -> None:
    """complete_invocation with evidence_ref must create the Tier 2 evidence directory."""
    evidence_file = tmp_path / "test_evidence.md"
    evidence_file.write_text("## Test Evidence\n\nAll assertions passed.", encoding="utf-8")

    executor, invocation_id = _make_executor_with_started_record(tmp_path)

    executor.complete_invocation(
        invocation_id=invocation_id,
        outcome="done",
        evidence_ref=str(evidence_file),
    )

    evidence_dir = tmp_path / ".kittify" / "evidence" / invocation_id
    assert evidence_dir.exists(), f"Tier 2 directory not created at {evidence_dir}"
    assert (evidence_dir / "evidence.md").exists()
    assert (evidence_dir / "record.json").exists()
    assert "All assertions passed." in (evidence_dir / "evidence.md").read_text()


def test_complete_without_evidence_skips_tier2(tmp_path: Path) -> None:
    """complete_invocation without evidence_ref must NOT create any evidence directory."""
    executor, invocation_id = _make_executor_with_started_record(tmp_path)

    executor.complete_invocation(invocation_id=invocation_id, outcome="done")

    evidence_dir = tmp_path / ".kittify" / "evidence"
    # Either dir doesn't exist, or exists but is empty
    if evidence_dir.exists():
        assert not list(evidence_dir.iterdir()), "Unexpected evidence directory created"


def test_complete_with_nonexistent_evidence_path_uses_inline_content(tmp_path: Path) -> None:
    """When evidence_ref is not a valid file path, use it as inline content."""
    executor, invocation_id = _make_executor_with_started_record(tmp_path)

    executor.complete_invocation(
        invocation_id=invocation_id,
        outcome="done",
        evidence_ref="all tests passed: 42/42",  # a label, not a path
    )

    evidence_dir = tmp_path / ".kittify" / "evidence" / invocation_id
    assert evidence_dir.exists()
    assert "all tests passed" in (evidence_dir / "evidence.md").read_text()


def test_complete_with_relative_escape_path_uses_inline_content(tmp_path: Path) -> None:
    """Relative evidence paths must stay inside repo_root after resolution."""
    outside_file = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside_file.write_text("top secret outside repo", encoding="utf-8")
    executor, invocation_id = _make_executor_with_started_record(tmp_path)

    executor.complete_invocation(
        invocation_id=invocation_id,
        outcome="done",
        evidence_ref=f"../{outside_file.name}",
    )

    evidence_dir = tmp_path / ".kittify" / "evidence" / invocation_id
    promoted_content = (evidence_dir / "evidence.md").read_text(encoding="utf-8")
    assert promoted_content == f"../{outside_file.name}"
