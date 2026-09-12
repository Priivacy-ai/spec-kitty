"""Unit tests for the owned-advance empty-changeset guard.

``next_cmd._commit_owned_next_mutations`` durably closes the changeset an
owned ``next`` advancement writes. ``safe_commit`` raises a plain
``RuntimeError`` whose message contains ``"(empty changeset)"`` when the
staged tree already matches HEAD (e.g. a terminal owned advance that writes
no new mission content and appends no lifecycle record) -- that is a benign
no-op, not a command failure, and must not crash ``next``. Any OTHER
``RuntimeError`` (protection refusal, HEAD mismatch, a genuine commit
failure, ...) must still propagate unchanged so the command stays
fail-closed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


def _stage_owned_mission(tmp_path: Path, mission_slug: str) -> Path:
    mission_dir = tmp_path / "kitty-specs" / mission_slug
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text("{}", encoding="utf-8")
    return mission_dir


def _install_fakes(monkeypatch: pytest.MonkeyPatch, mission_dir: Path, safe_commit_fake) -> None:
    monkeypatch.setattr(
        "specify_cli.missions._read_path_resolver.compose_meta_json_path",
        lambda _base, _slug: mission_dir / "meta.json",
    )

    class _FakeArtifact:
        commit_target = object()  # any non-None sentinel; safe_commit is faked below

    class _FakeMissionContext:
        def artifact(self, _kind):
            return _FakeArtifact()

    monkeypatch.setattr(
        "mission_runtime.mission_context_for",
        lambda _root, _slug, *, effective_root=None: _FakeMissionContext(),
    )
    monkeypatch.setattr(
        "specify_cli.git.commit_helpers.safe_commit",
        safe_commit_fake,
    )


def test_owned_commit_guard_swallows_empty_changeset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A staged tree that already matches HEAD returns cleanly (no-op)."""
    from specify_cli.cli.commands.next_cmd import _commit_owned_next_mutations

    mission_slug = "owned-guard-mission"
    mission_dir = _stage_owned_mission(tmp_path, mission_slug)

    def _raise_empty_changeset(**_kwargs):
        raise RuntimeError(
            "safe_commit: nothing to commit for destination_ref='refs/heads/x' "
            "(empty changeset)"
        )

    _install_fakes(monkeypatch, mission_dir, _raise_empty_changeset)

    # Must not raise.
    _commit_owned_next_mutations(tmp_path, mission_slug)


def test_owned_commit_guard_propagates_other_runtime_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A genuine safe_commit failure (e.g. HEAD mismatch) still propagates."""
    from specify_cli.cli.commands.next_cmd import _commit_owned_next_mutations

    mission_slug = "owned-guard-mission-2"
    mission_dir = _stage_owned_mission(tmp_path, mission_slug)

    def _raise_head_mismatch(**_kwargs):
        raise RuntimeError("safe_commit: worktree HEAD does not match destination_ref")

    _install_fakes(monkeypatch, mission_dir, _raise_head_mismatch)

    with pytest.raises(RuntimeError, match="HEAD does not match"):
        _commit_owned_next_mutations(tmp_path, mission_slug)
