"""Unit tests threading ``effective_root`` through the ``next --answer`` sub-path.

Every OTHER owned-``next`` call site in ``next_cmd`` (``_pair_previous_
lifecycle_record``, ``_write_issuance_lifecycle_record``,
``_emit_mission_next_invoked``, ``_resolve_mission_slug``) branches on
``effective_root`` and resolves via ``mission_context_for(..., effective_root=
effective_root)`` instead of the primary-folding ``placement_seam(...).
read_dir(...)``. ``_handle_answer`` (the ``next --answer`` sub-path) used to be
the one holdout: it always called ``placement_seam(...)``, which folds a
linked-worktree root back to the primary checkout (``get_main_repo_root``) --
the "old way" the ADR forbids for opted-in owned layers. That made
``spec-kitty next --owned-checkout <linked-worktree> --answer ...`` resolve
mission identity against primary instead of the owned checkout, where the
owned mission dir does not exist.

These tests assert ``_handle_answer`` now takes the same fork as its
siblings: ``mission_context_for(..., effective_root=...)`` when
``effective_root`` is supplied, and the historical ``placement_seam(...)``
call when it is not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.cli.commands import next_cmd

pytestmark = pytest.mark.fast


class _FakeRunRef:
    def __init__(self, run_dir: str) -> None:
        self.run_dir = run_dir


class _FakeRuntimeBridge:
    """Stand-in for ``_runtime_bridge_module()`` that records the repo root it saw."""

    def __init__(self, run_dir: str) -> None:
        self._run_dir = run_dir
        self.get_or_start_run_calls: list[tuple[str, object, str]] = []
        self.answer_calls: list[tuple[str, str, str, str, object]] = []

    def get_or_start_run(self, mission_slug, repo_root, mission_type):
        self.get_or_start_run_calls.append((mission_slug, repo_root, mission_type))
        return _FakeRunRef(self._run_dir)

    def answer_decision_via_runtime(self, mission_slug, decision_id, answer, agent, repo_root):
        self.answer_calls.append((mission_slug, decision_id, answer, agent, repo_root))


def _patch_common(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, seen_feature_dirs: list[Path]) -> _FakeRuntimeBridge:
    fake_bridge = _FakeRuntimeBridge(run_dir=str(tmp_path / "run-dir"))
    monkeypatch.setattr(next_cmd, "_runtime_bridge_module", lambda: fake_bridge)
    monkeypatch.setattr(
        "specify_cli.mission.get_mission_type",
        lambda feature_dir: (seen_feature_dirs.append(feature_dir), "software-dev")[1],
    )
    return fake_bridge


def test_handle_answer_without_effective_root_uses_placement_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Historical behavior: no ``effective_root`` -> the primary-folding seam."""
    primary_marker = tmp_path / "primary-marker"
    seen_feature_dirs: list[Path] = []
    fake_bridge = _patch_common(monkeypatch, tmp_path, seen_feature_dirs)

    seam_calls: list[tuple[object, str]] = []

    class _FakeSeamReader:
        def read_dir(self, kind):
            return primary_marker

    def _fake_placement_seam(repo_root, mission_slug):
        seam_calls.append((repo_root, mission_slug))
        return _FakeSeamReader()

    def _unexpected_mission_context_for(*_args, **_kwargs):
        raise AssertionError("mission_context_for must not be called without effective_root")

    monkeypatch.setattr(next_cmd, "placement_seam", _fake_placement_seam)
    monkeypatch.setattr("mission_runtime.mission_context_for", _unexpected_mission_context_for)

    result = next_cmd._handle_answer(
        "claude",
        "some-mission",
        "yes",
        "input:review",
        tmp_path,
    )

    assert result == "input:review"
    assert seam_calls == [(tmp_path, "some-mission")]
    assert seen_feature_dirs == [primary_marker]
    assert fake_bridge.answer_calls == [
        ("some-mission", "input:review", "yes", "claude", tmp_path)
    ]


def test_handle_answer_with_effective_root_uses_mission_context_for(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owned-checkout path: ``effective_root`` supplied -> resolves against it,
    never against ``placement_seam``'s primary-folding read."""
    owned_root = tmp_path / "owned-checkout"
    owned_marker = tmp_path / "owned-marker"
    seen_feature_dirs: list[Path] = []
    fake_bridge = _patch_common(monkeypatch, tmp_path, seen_feature_dirs)

    context_calls: list[tuple[object, str, Path | None]] = []

    class _FakeArtifact:
        read_dir = owned_marker

    class _FakeMissionContext:
        def artifact(self, kind):
            return _FakeArtifact()

    def _fake_mission_context_for(repo_root, mission_slug, *, effective_root=None):
        context_calls.append((repo_root, mission_slug, effective_root))
        return _FakeMissionContext()

    def _unexpected_placement_seam(*_args, **_kwargs):
        raise AssertionError("placement_seam must not be called when effective_root is supplied")

    monkeypatch.setattr(next_cmd, "placement_seam", _unexpected_placement_seam)
    monkeypatch.setattr("mission_runtime.mission_context_for", _fake_mission_context_for)

    result = next_cmd._handle_answer(
        "claude",
        "owned-mission",
        "yes",
        "input:review",
        owned_root,
        effective_root=owned_root,
    )

    assert result == "input:review"
    assert context_calls == [(owned_root, "owned-mission", owned_root)]
    assert seen_feature_dirs == [owned_marker]
    assert fake_bridge.answer_calls == [
        ("owned-mission", "input:review", "yes", "claude", owned_root)
    ]


def test_maybe_handle_answer_threads_effective_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The call-site wrapper (``_maybe_handle_answer``) forwards ``effective_root``
    to ``_handle_answer`` unchanged -- this is what closes the owned ``--answer``
    gap at the ``next_step`` call site."""
    captured: dict[str, object] = {}

    def _fake_handle_answer(agent, mission_slug, answer, decision_id, repo_root, *, effective_root=None):
        captured["effective_root"] = effective_root
        return "resolved-id"

    monkeypatch.setattr(next_cmd, "_handle_answer", _fake_handle_answer)

    owned_root = tmp_path / "owned-checkout"
    result = next_cmd._maybe_handle_answer(
        "claude",
        "owned-mission",
        "yes",
        None,
        owned_root,
        False,
        effective_root=owned_root,
    )

    assert result == "resolved-id"
    assert captured["effective_root"] == owned_root
