"""Integration: status-event emission is side-effect-free and identity-stable (#2263).

WP02 of the worktree-clean sync invariant mission routes every read/emit/background
``ensure_identity`` call site to the side-effect-free ``resolve_identity``. The emit
path (``sync.events.get_emitter`` / ``emit_wp_status_changed`` → ``sync.emitter``)
must therefore resolve a *complete, stable* project identity **without** persisting it
to ``.kittify/config.yaml``.

Covered acceptance:

* AS-2 / FR-001 / FR-002 — emitting a status event on an *incomplete-identity*
  checkout leaves ``.kittify/config.yaml`` byte-identical and ``git status
  --porcelain`` unchanged, while the emitted event still carries a complete identity.
* NFR-001 — two consecutive emits resolve the **same** ``project_uuid`` and
  ``build_id`` (WP01's deterministic ``build_id`` derivation; 0 variance).
* FR-008 / AS-6 — with SaaS sync disabled, the emit path remains side-effect-free.

RED preconditions (mirrors ``test_accept_readiness_no_write``):

1. The fixture ``.kittify/config.yaml`` MUST be *provably incomplete* (``build_id``
   missing) — a complete fixture never reproduces the side-effect.
2. The emitter is a process-global singleton seeded only on first init, so we call
   ``reset_emitter()`` before exercising it to actually hit the identity seam.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.identity.project import load_identity
from specify_cli.sync.events import emit_wp_status_changed, get_emitter, reset_emitter

pytestmark = [pytest.mark.non_sandbox, pytest.mark.git_repo]

_CONFIG_RELPATH = ".kittify/config.yaml"


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo_root), *args], check=True, capture_output=True)


def _porcelain_status(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _write_incomplete_config(repo_root: Path) -> Path:
    """Write a ``.kittify/config.yaml`` with provably-incomplete project identity.

    ``project.build_id`` (required for ``ProjectIdentity.is_complete``) is omitted so a
    *writing* identity call would mint + persist it, dirtying the tree. The read path
    must instead resolve it in-memory only.
    """
    config_path = repo_root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "project:\n"
        "  uuid: 22222222-2222-4222-8222-222222222222\n"
        "  slug: emit-readonly-identity\n"
        "  node_id: fedcba543210\n"
        # build_id intentionally omitted → identity incomplete
        "\n"
    )
    return config_path


def _make_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Init a git repo with an incomplete-identity config; return (repo_root, config)."""
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir()
    _git(repo_root, "init")
    config_path = _write_incomplete_config(repo_root)
    # Commit the seed so a side-effect write shows up as a dirty tracked file.
    _git(repo_root, "add", "-A")
    _git(repo_root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "seed")
    return repo_root, config_path


def test_incomplete_identity_precondition(tmp_path: Path) -> None:
    """Guard (RED precondition 1): the fixture identity MUST be incomplete."""
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir()
    config_path = _write_incomplete_config(repo_root)

    identity = load_identity(config_path)
    assert identity.build_id is None, "fixture identity must be incomplete (build_id missing)"
    assert not identity.is_complete, "fixture identity must be incomplete to reproduce #2263"


def test_emit_does_not_persist_identity_or_dirty_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AS-2 / FR-001 / FR-002: a status emit leaves config.yaml + worktree untouched.

    The emitted event must still carry a complete, in-memory identity even though the
    checkout's on-disk identity stays incomplete.
    """
    repo_root, config_path = _make_repo(tmp_path)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)

    bytes_before = config_path.read_bytes()
    mtime_before = config_path.stat().st_mtime_ns
    status_before = _porcelain_status(repo_root)

    reset_emitter()
    with patch("specify_cli.sync.runtime.get_runtime", return_value=MagicMock()):
        emit_wp_status_changed(
            "WP01", "planned", "in_progress", mission_slug="emit-readonly-identity"
        )

    # No persistence: config.yaml byte-identical, mtime unchanged, on-disk still incomplete.
    assert config_path.read_bytes() == bytes_before, (
        "emit mutated .kittify/config.yaml — emit path must not persist identity (#2263)"
    )
    assert config_path.stat().st_mtime_ns == mtime_before, "emit rewrote config.yaml (mtime)"
    assert not load_identity(config_path).is_complete, "emit must not complete identity on disk"

    # Worktree clean: git porcelain byte-identical before/after (AS-1/AS-2).
    assert _porcelain_status(repo_root) == status_before, (
        "emit changed `git status --porcelain` — the worktree-clean invariant is violated"
    )

    # The event still resolves a complete in-memory identity for provenance.
    identity = get_emitter()._get_identity()
    assert identity.is_complete, "emitter must carry a complete in-memory identity"
    assert identity.project_uuid is not None
    assert identity.build_id is not None


def test_two_consecutive_emits_resolve_stable_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NFR-001: repeated emit-path identity resolution has 0 variance (uuid + build_id)."""
    repo_root, config_path = _make_repo(tmp_path)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)

    with patch("specify_cli.sync.runtime.get_runtime", return_value=MagicMock()):
        reset_emitter()
        first = get_emitter()._get_identity()
        reset_emitter()
        second = get_emitter()._get_identity()

    assert first.is_complete and second.is_complete
    assert first.project_uuid == second.project_uuid, "project_uuid drifted across emits"
    assert first.build_id == second.build_id, "build_id drifted across emits (NFR-001)"
    # Stability does not come from a sneaky persist between calls.
    assert not load_identity(config_path).is_complete


def test_emit_is_side_effect_free_with_sync_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-008 / AS-6: with SaaS sync disabled the emit path stays side-effect-free."""
    repo_root, config_path = _make_repo(tmp_path)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    # Opt OUT of the autouse SaaS-sync flag for this case.
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")
    monkeypatch.chdir(repo_root)

    bytes_before = config_path.read_bytes()
    status_before = _porcelain_status(repo_root)

    reset_emitter()
    with patch("specify_cli.sync.runtime.get_runtime", return_value=MagicMock()):
        emit_wp_status_changed(
            "WP01", "planned", "in_progress", mission_slug="emit-readonly-identity"
        )

    assert config_path.read_bytes() == bytes_before, (
        "emit mutated config.yaml even with sync disabled (FR-008)"
    )
    assert _porcelain_status(repo_root) == status_before, (
        "emit dirtied the worktree with sync disabled (FR-008/AS-6)"
    )
    assert not load_identity(config_path).is_complete
