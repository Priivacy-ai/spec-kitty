"""Integration tests for the specify/plan auto-commit boundary (issue #846).

Locks in the contract from
``kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/specify-plan-commit-boundary.md``:

(a) ``mission create`` does NOT commit ``spec.md`` (``meta.json`` is still written).
(b) Uncommitted populated ``spec.md`` -> setup-plan blocks ("committed AND substantive").
(c) Committed but scaffold-only ``spec.md`` -> setup-plan blocks (substantive-spec).
(d) Committed substantive spec + populated plan -> plan commits, phase_complete=True.
(e) Same as (d) but plan left as template -> setup-plan returns phase_complete=False.

Plus a focused unit-style assertion for the section-presence-only gate:
scaffold + 300 bytes of arbitrary prose stays NON-substantive.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.core.mission_creation import create_mission_core
from specify_cli.missions._substantive import is_committed, is_substantive

pytestmark = pytest.mark.fast


_CORE_MODULE = "specify_cli.core.mission_creation"


# ---------------------------------------------------------------------------
# Repo / mission fixtures
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _init_git_repo(repo: Path) -> None:
    (repo / ".kittify").mkdir(parents=True, exist_ok=True)
    (repo / "kitty-specs").mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, capture_output=True, check=True)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "commit", "-m", "init", "--allow-empty")


def _summary(slug: str) -> dict[str, str]:
    title = slug.replace("-", " ")
    return {
        "friendly_name": title.title(),
        "purpose_tldr": f"Deliver {title} cleanly for the team.",
        "purpose_context": (
            f"This mission delivers {title} so stakeholders can track outcomes "
            "without parsing the spec text directly."
        ),
    }


def _create_mission(repo: Path, slug: str) -> Path:
    """Run create_mission_core against ``repo`` and return the feature_dir."""
    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=repo),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
    ):
        result = create_mission_core(repo, slug, **_summary(slug))
    feature_dir: Path = result.feature_dir
    return feature_dir


def _file_in_head(repo: Path, rel_path: str) -> bool:
    """Return True iff ``rel_path`` is tracked AND present at HEAD."""
    ls = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--error-unmatch", rel_path],
        capture_output=True,
    )
    if ls.returncode != 0:
        return False
    head = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"HEAD:{rel_path}"],
        capture_output=True,
    )
    return head.returncode == 0


# ---------------------------------------------------------------------------
# spec / plan content helpers
# ---------------------------------------------------------------------------


_SUBSTANTIVE_SPEC = """\
# Spec — Test Mission

## Functional Requirements

| ID | Title | Description | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Auth flow | Users sign in via SSO with email and one-time code. | High | Open |
"""

_SCAFFOLD_SPEC = """\
# Spec — Test Mission

## Functional Requirements

| ID | Title | Description | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | [Short title] | As a [role], I want [goal] so that [benefit]. | High | Open |
"""


_SUBSTANTIVE_PLAN = """\
# Plan — Test Mission

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: typer, rich, pytest
**Storage**: filesystem only
**Testing**: pytest with integration coverage
"""

_SCAFFOLD_PLAN = """\
# Plan — Test Mission

## Technical Context

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]
"""

_PLAN_WITH_ONLY_LANGUAGE = """\
# Plan — Test Mission

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]
"""


def _commit_file(repo: Path, rel_path: str, message: str) -> None:
    _git(repo, "add", rel_path)
    _git(repo, "commit", "-m", message)


# ---------------------------------------------------------------------------
# Unit assertion — section-presence only (no byte-length OR fallback)
# ---------------------------------------------------------------------------


def test_is_substantive_rejects_scaffold_plus_arbitrary_prose(tmp_path: Path) -> None:
    """Scaffold + 300 bytes of prose without an FR row stays NON-substantive."""
    spec = tmp_path / "spec.md"
    body = _SCAFFOLD_SPEC + "\n\n" + ("Lorem ipsum prose paragraph. " * 20)
    assert len(body) > 600  # well over any imagined byte threshold
    spec.write_text(body, encoding="utf-8")
    assert is_substantive(spec, "spec") is False


def test_is_substantive_accepts_populated_fr_row(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text(_SUBSTANTIVE_SPEC, encoding="utf-8")
    assert is_substantive(spec, "spec") is True


def test_is_substantive_rejects_placeholder_technical_context(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text(_SCAFFOLD_PLAN, encoding="utf-8")
    assert is_substantive(plan, "plan") is False


def test_is_substantive_rejects_language_without_peer_context(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text(_PLAN_WITH_ONLY_LANGUAGE, encoding="utf-8")
    assert is_substantive(plan, "plan") is False


def test_is_substantive_accepts_populated_technical_context(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text(_SUBSTANTIVE_PLAN, encoding="utf-8")
    assert is_substantive(plan, "plan") is True


def test_is_committed_returns_false_for_untracked(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    f = tmp_path / "untracked.md"
    f.write_text("hello", encoding="utf-8")
    assert is_committed(f, tmp_path) is False


def test_is_committed_returns_true_for_committed(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    f = tmp_path / "tracked.md"
    f.write_text("hello", encoding="utf-8")
    _commit_file(tmp_path, "tracked.md", "add tracked")
    assert is_committed(f, tmp_path) is True


def test_is_committed_returns_false_for_staged_only(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    f = tmp_path / "staged.md"
    f.write_text("hello", encoding="utf-8")
    _git(tmp_path, "add", "staged.md")
    assert is_committed(f, tmp_path) is False


# ---------------------------------------------------------------------------
# Scenario (a) — mission create does NOT commit spec.md
# ---------------------------------------------------------------------------


def test_mission_create_does_not_commit_spec_md(tmp_path: Path) -> None:
    """meta.json is written; spec.md is left untracked on disk."""
    _init_git_repo(tmp_path)
    feature_dir = _create_mission(tmp_path, "mission-a")

    rel_root = feature_dir.relative_to(tmp_path)
    spec_rel = str(rel_root / "spec.md")

    assert (feature_dir / "spec.md").exists(), "spec.md scaffold must remain on disk"
    assert (feature_dir / "meta.json").exists(), "meta.json must still be written"
    assert _file_in_head(tmp_path, spec_rel) is False, "spec.md must NOT be committed at create"


# ---------------------------------------------------------------------------
# setup-plan invocation helpers
# ---------------------------------------------------------------------------


def _run_setup_plan(repo: Path, mission_handle: str) -> dict[str, object]:
    """Invoke ``mission setup-plan --json --mission <handle>`` against ``repo``.

    Returns the parsed JSON payload from the command. Patches the path
    detection helpers so the command treats ``repo`` as the project root and
    finds the feature directly under ``kitty-specs/``.
    """
    from specify_cli.cli.commands.agent import mission as mission_module
    from typer.testing import CliRunner

    runner = CliRunner()
    feature_dir = repo / "kitty-specs" / mission_handle

    def _fake_show_branch_context(
        _repo_root: Path, _slug: str, _json: bool
    ) -> tuple[str, str]:
        return ("main", "main")

    with (
        patch.object(mission_module, "locate_project_root", return_value=repo),
        patch.object(mission_module, "_enforce_git_preflight"),
        patch.object(
            mission_module,
            "_find_feature_directory",
            return_value=feature_dir,
        ),
        patch.object(
            mission_module,
            "_show_branch_context",
            side_effect=_fake_show_branch_context,
        ),
        patch.object(mission_module, "get_current_branch", return_value="main"),
        patch.object(mission_module, "_resolve_feature_target_branch", return_value="main"),
        patch(
            "specify_cli.sync.dossier_pipeline.trigger_feature_dossier_sync_if_enabled"
        ),
    ):
        result = runner.invoke(
            mission_module.app,
            ["setup-plan", "--json", "--mission", mission_handle],
            catch_exceptions=False,
        )
    assert result.exit_code in (0, 1), f"unexpected exit {result.exit_code}: {result.output}"
    # Locate the JSON envelope in the output (commands print plain JSON).
    output = result.output.strip()
    # Find the last '{' ... '}' block.
    start = output.find("{")
    end = output.rfind("}")
    assert start != -1 and end != -1, f"no JSON in output: {output!r}"
    payload: dict[str, object] = json.loads(output[start : end + 1])
    return payload


# ---------------------------------------------------------------------------
# Scenario (b) — uncommitted populated spec blocks setup-plan
# ---------------------------------------------------------------------------


def test_setup_plan_blocks_when_spec_uncommitted(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    feature_dir = _create_mission(tmp_path, "mission-b")
    handle = feature_dir.name
    # Populate spec but do NOT commit it.
    (feature_dir / "spec.md").write_text(_SUBSTANTIVE_SPEC, encoding="utf-8")

    payload = _run_setup_plan(tmp_path, handle)

    assert payload.get("phase_complete") is False
    assert payload.get("result") == "blocked"
    reason = str(payload.get("blocked_reason", ""))
    assert "committed AND substantive" in reason
    # plan.md must not have been written / committed
    plan_path = feature_dir / "plan.md"
    plan_rel = str(plan_path.relative_to(tmp_path))
    assert _file_in_head(tmp_path, plan_rel) is False


# ---------------------------------------------------------------------------
# Scenario (c) — committed but scaffold-only spec blocks setup-plan
# ---------------------------------------------------------------------------


def test_setup_plan_blocks_when_spec_committed_but_scaffold(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    feature_dir = _create_mission(tmp_path, "mission-c")
    handle = feature_dir.name
    # Commit a scaffold-only spec.md.
    (feature_dir / "spec.md").write_text(_SCAFFOLD_SPEC, encoding="utf-8")
    spec_rel = str((feature_dir / "spec.md").relative_to(tmp_path))
    _commit_file(tmp_path, spec_rel, "add scaffold spec")

    payload = _run_setup_plan(tmp_path, handle)

    assert payload.get("phase_complete") is False
    assert payload.get("result") == "blocked"
    assert payload.get("spec_committed") is True
    assert payload.get("spec_substantive") is False
    plan_rel = str((feature_dir / "plan.md").relative_to(tmp_path))
    assert _file_in_head(tmp_path, plan_rel) is False


# ---------------------------------------------------------------------------
# Scenario (d) — committed substantive spec + populated plan -> commit + phase_complete=True
# ---------------------------------------------------------------------------


def test_setup_plan_commits_substantive_plan(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    feature_dir = _create_mission(tmp_path, "mission-d")
    handle = feature_dir.name

    # Populate + commit substantive spec.
    (feature_dir / "spec.md").write_text(_SUBSTANTIVE_SPEC, encoding="utf-8")
    spec_rel = str((feature_dir / "spec.md").relative_to(tmp_path))
    _commit_file(tmp_path, spec_rel, "add substantive spec")

    # Pre-write the plan so setup-plan does NOT overwrite it (C-007).
    (feature_dir / "plan.md").write_text(_SUBSTANTIVE_PLAN, encoding="utf-8")

    payload = _run_setup_plan(tmp_path, handle)

    assert payload.get("phase_complete") is True
    assert payload.get("result") == "success"
    plan_rel = str((feature_dir / "plan.md").relative_to(tmp_path))
    assert _file_in_head(tmp_path, plan_rel) is True


# ---------------------------------------------------------------------------
# Scenario (e) — committed spec + scaffold plan -> phase_complete=False
# ---------------------------------------------------------------------------


def test_setup_plan_blocks_when_plan_left_as_template(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    feature_dir = _create_mission(tmp_path, "mission-e")
    handle = feature_dir.name

    (feature_dir / "spec.md").write_text(_SUBSTANTIVE_SPEC, encoding="utf-8")
    spec_rel = str((feature_dir / "spec.md").relative_to(tmp_path))
    _commit_file(tmp_path, spec_rel, "add substantive spec")

    # Pre-write a SCAFFOLD plan so setup-plan does NOT overwrite it (C-007),
    # and the exit gate sees it as non-substantive.
    (feature_dir / "plan.md").write_text(_SCAFFOLD_PLAN, encoding="utf-8")

    payload = _run_setup_plan(tmp_path, handle)

    assert payload.get("phase_complete") is False
    assert payload.get("result") == "blocked"
    reason = str(payload.get("blocked_reason", ""))
    assert "Technical Context" in reason or "substantive" in reason
    plan_rel = str((feature_dir / "plan.md").relative_to(tmp_path))
    assert _file_in_head(tmp_path, plan_rel) is False
