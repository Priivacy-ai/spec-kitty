"""Integration tests for ``init``/``upgrade`` ToolSurfaceContract wiring (T040).

These tests exercise the *real* CLI wiring (FR-001/FR-002): they invoke the
checkout-local ``specify_cli`` package as a subprocess — never a direct call to
``run_surface_repair`` — so a regression that disconnects ``init``/``upgrade``
from the repair service is caught here even though the function itself still
works in isolation.

Drift policy:
  - FR-003 missing  -> auto-created during init/upgrade (no prompt)
  - FR-004 stale    -> auto-repaired during init/upgrade (no prompt)
  - FR-006 drifted  -> ``--yes`` (non-interactive) reports only and exits
    non-zero; it MUST NOT overwrite the user's edits (NFR-007)
  - FR-008 idempotent: a second consecutive run reports zero changes
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .integration._compat_support import run_spec_kitty

pytestmark = [pytest.mark.integration, pytest.mark.non_sandbox]


def _init_claude_project(root: Path) -> None:
    """Run ``init --ai claude --non-interactive`` in *root* (real CLI wiring)."""
    result = run_spec_kitty(
        "init", "--ai", "claude", "--non-interactive", cwd=root
    )
    assert result.returncode == 0, (
        f"init failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def _agent_profile_states(root: Path) -> set[str]:
    result = run_spec_kitty(
        "doctor", "tool-surfaces", "--kind", "agent-profile", "--json", cwd=root
    )
    payload = result.json()
    return {surface["state"] for surface in payload["surfaces"]}


def test_init_creates_missing_profile_dirs(tmp_path: Path) -> None:
    """``init`` creates missing native agent profile dirs via the CLI (FR-001)."""
    assert not (tmp_path / ".claude" / "agents").exists()

    _init_claude_project(tmp_path)

    agents_dir = tmp_path / ".claude" / "agents"
    assert agents_dir.exists(), ".claude/agents/ must be created by init"
    profiles = list(agents_dir.glob("*.md"))
    assert profiles, ".claude/agents/ must contain at least one .md profile"
    for profile in profiles:
        assert profile.read_text(encoding="utf-8").startswith("---"), (
            f"{profile.name} must carry YAML frontmatter"
        )

    # doctor reports no missing/stale/drifted agent profiles.
    states = _agent_profile_states(tmp_path)
    assert states <= {"present", "not_applicable"}, (
        f"unexpected agent-profile states after init: {states}"
    )


def test_upgrade_recreates_deleted_profile_dirs(tmp_path: Path) -> None:
    """``upgrade`` re-creates missing profile dirs even on the up-to-date path.

    FR-002 regression guard: when no migrations are pending (project already at
    the current version) the surface-repair service must still run. Deleting
    ``.claude/agents/`` and re-running ``upgrade --yes`` must heal it.
    """
    _init_claude_project(tmp_path)
    agents_dir = tmp_path / ".claude" / "agents"
    before = {p.name for p in agents_dir.glob("*.md")}
    assert before, "init must have produced profile files"

    # Prime the up-to-date path: the first upgrade applies the wiring marker so
    # the second upgrade exercises the "already up to date" branch.
    first = run_spec_kitty("upgrade", "--yes", cwd=tmp_path)
    assert first.returncode == 0, first.stderr

    import shutil

    shutil.rmtree(agents_dir)
    assert not agents_dir.exists()

    second = run_spec_kitty("upgrade", "--yes", cwd=tmp_path)
    assert second.returncode == 0, second.stderr
    assert agents_dir.exists(), "upgrade must re-create deleted .claude/agents/"
    after = {p.name for p in agents_dir.glob("*.md")}
    assert after == before, "re-created profile set must match the original"


def test_upgrade_repairs_stale_manifest(tmp_path: Path) -> None:
    """``upgrade`` auto-repairs a stale (truncated) command-skill manifest (FR-030)."""
    import json

    # codex is a command-skill agent, so its config produces the manifest.
    init_result = run_spec_kitty(
        "init", "--ai", "claude,codex", "--non-interactive", cwd=tmp_path
    )
    assert init_result.returncode == 0, init_result.stderr
    manifest_path = tmp_path / ".kittify" / "command-skills-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    canonical_count = len(manifest["entries"])
    assert canonical_count > 1, "init should yield a multi-entry manifest"

    # Degrade: drop all but one entry (simulates an rc44-era short manifest).
    manifest["entries"] = manifest["entries"][:1]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_spec_kitty("upgrade", "--yes", cwd=tmp_path)
    assert result.returncode == 0, result.stderr

    repaired = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(repaired["entries"]) == canonical_count, (
        "stale manifest must be repaired back to the canonical entry count"
    )


def test_upgrade_with_yes_does_not_overwrite_drifted(tmp_path: Path) -> None:
    """``--yes`` must report-only on drift and exit non-zero (FR-006/NFR-007)."""
    _init_claude_project(tmp_path)

    # Prime the up-to-date path so the wiring marker exists.
    run_spec_kitty("upgrade", "--yes", cwd=tmp_path)

    agents_dir = tmp_path / ".claude" / "agents"
    custom_content = "# Hand-modified agent\n\nCustom content.\n"
    drifted_path: Path | None = None
    for md in sorted(agents_dir.glob("*.md")):
        md.write_text(custom_content, encoding="utf-8")
        drifted_path = md
        break
    assert drifted_path is not None, "no managed profile files found after init"

    result = run_spec_kitty("upgrade", "--yes", cwd=tmp_path)
    # FR-006: non-interactive upgrade exits non-zero when unresolved drift exists.
    assert result.returncode != 0, "--yes must exit non-zero on unresolved drift"
    # NFR-007: the drifted file is preserved verbatim.
    assert drifted_path.read_text(encoding="utf-8") == custom_content, (
        "drifted file must not be overwritten by --yes"
    )


def test_second_upgrade_is_idempotent(tmp_path: Path) -> None:
    """A second consecutive ``upgrade`` reports zero changes (FR-008/NFR-006)."""
    _init_claude_project(tmp_path)

    first = run_spec_kitty("upgrade", "--yes", cwd=tmp_path)
    assert first.returncode == 0, first.stderr

    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    second = run_spec_kitty("upgrade", "--yes", cwd=tmp_path)
    assert second.returncode == 0, second.stderr
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before, "second upgrade must not change any file bytes"
