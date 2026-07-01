"""Regression tests for WP07 — Terminus Retrospective Triggering (FR-007, Issue #1888).

Verifies that ``run_retrospective_postcondition`` is ACTUALLY CALLED on the
merge completion path and that the correct invariants hold:

  * If ``retrospective.yaml`` is absent → capture is invoked.
  * If ``retrospective.yaml`` is present → function is a no-op (idempotent).
  * If capture fails → ``capture_failed`` event is emitted; merge is NOT aborted.
  * The function calls ``_run_retrospective_learning_capture`` from the runtime
    bridge (T032 — no duplicate implementation).

These tests target the public function directly (not the CLI) so they remain
fast, hermetic, and free of git-subprocess overhead.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from specify_cli.post_merge.retrospective_terminus import (
    _commit_captured_retrospective,
    run_retrospective_postcondition,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MISSION_SLUG = "017-my-test-mission"


def _make_feature_dir(tmp_path: Path, *, mission_id: str = "01HXYZ0000000000000000000A") -> Path:
    """Return a minimal kitty-specs/<slug>/ directory for tests."""
    feature_dir = tmp_path / "kitty-specs" / MISSION_SLUG
    feature_dir.mkdir(parents=True)
    meta = {"mission_id": mission_id, "mission_slug": MISSION_SLUG}
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return feature_dir


def _patch_resolver(feature_dir: Path) -> Any:
    """Patch the retrospective-home resolver the terminus ACTUALLY calls.

    The live path is ``resolve_retrospective_home`` (writer.py) →
    ``primary_feature_dir_for_mission``; the old patch targeted
    ``resolve_feature_dir_for_slug``, which this path never calls, so it was a
    dead no-op that only "worked" because the real primitive happened to return
    the same tmp path. Patch the real seam so the test genuinely controls
    resolution.
    """
    return patch(
        "specify_cli.retrospective.writer.resolve_retrospective_home",
        return_value=feature_dir,
    )


def _patch_invoke(side_effect: Any = None) -> Any:
    """Patch _invoke_capture (wraps _run_retrospective_learning_capture)."""
    return patch(
        "specify_cli.post_merge.retrospective_terminus._invoke_capture",
        side_effect=side_effect,
    )


# ---------------------------------------------------------------------------
# T035 — merge path → retrospective fires
# ---------------------------------------------------------------------------


class TestRunRetrospectivePostcondition:
    """Core invariants for run_retrospective_postcondition (FR-007)."""

    def test_capture_called_when_yaml_absent(self, tmp_path: Path) -> None:
        """Merge path: retrospective.yaml absent → _invoke_capture is called."""
        feature_dir = _make_feature_dir(tmp_path)
        # Confirm retrospective.yaml does NOT exist yet.
        assert not (feature_dir / "retrospective.yaml").exists()

        with _patch_resolver(feature_dir), _patch_invoke() as mock_invoke:
            run_retrospective_postcondition(
                mission_slug=MISSION_SLUG,
                repo_root=tmp_path,
            )

        mock_invoke.assert_called_once()
        _, kwargs = mock_invoke.call_args
        assert kwargs["mission_slug"] == MISSION_SLUG
        assert kwargs["feature_dir"] == feature_dir
        assert kwargs["repo_root"] == tmp_path

    def test_noop_when_yaml_already_exists(self, tmp_path: Path) -> None:
        """Idempotent: retrospective.yaml present → _invoke_capture is NOT called."""
        feature_dir = _make_feature_dir(tmp_path)
        # Pre-create retrospective.yaml (simulates terminus already ran).
        (feature_dir / "retrospective.yaml").write_text("schema_version: 1\n", encoding="utf-8")

        with _patch_resolver(feature_dir), _patch_invoke() as mock_invoke:
            run_retrospective_postcondition(
                mission_slug=MISSION_SLUG,
                repo_root=tmp_path,
            )

        mock_invoke.assert_not_called()

    def test_merge_does_not_abort_on_capture_failure(self, tmp_path: Path) -> None:
        """Fail-open: capture exception → merge path continues, does NOT raise."""
        feature_dir = _make_feature_dir(tmp_path)

        with (
            _patch_resolver(feature_dir),
            _patch_invoke(side_effect=RuntimeError("simulated generator failure")),
            patch(
                "specify_cli.post_merge.retrospective_terminus._emit_capture_failed"
            ) as mock_emit,
        ):
            # Must NOT raise — fail-open contract.
            run_retrospective_postcondition(
                mission_slug=MISSION_SLUG,
                repo_root=tmp_path,
            )

        # Failure should be reported via _emit_capture_failed.
        mock_emit.assert_called_once()

    def test_capture_failed_event_emitted_on_failure(self, tmp_path: Path) -> None:
        """On failure, capture_failed event kwargs contain mission_slug and exc."""
        feature_dir = _make_feature_dir(tmp_path)
        boom = OSError("disk full")

        with (
            _patch_resolver(feature_dir),
            _patch_invoke(side_effect=boom),
            patch(
                "specify_cli.post_merge.retrospective_terminus._emit_capture_failed"
            ) as mock_emit,
        ):
            run_retrospective_postcondition(
                mission_slug=MISSION_SLUG,
                repo_root=tmp_path,
            )

        assert mock_emit.call_count == 1
        _, kwargs = mock_emit.call_args
        assert kwargs["mission_slug"] == MISSION_SLUG
        assert kwargs["exc"] is boom

    def test_invoke_capture_delegates_to_runtime_bridge(self, tmp_path: Path) -> None:
        """T032: _invoke_capture calls _run_retrospective_learning_capture (no duplicate impl)."""
        feature_dir = _make_feature_dir(tmp_path)

        with patch(
            "runtime.next.runtime_bridge._run_retrospective_learning_capture"
        ) as mock_bridge:
            from specify_cli.post_merge.retrospective_terminus import _invoke_capture

            _invoke_capture(
                mission_id="01HXYZ0000000000000000000A",
                mission_slug=MISSION_SLUG,
                feature_dir=feature_dir,
                repo_root=tmp_path,
            )

        mock_bridge.assert_called_once_with(
            mission_id="01HXYZ0000000000000000000A",
            mission_slug=MISSION_SLUG,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            block_on_failure=False,
        )

    def test_mission_id_resolved_from_meta_json(self, tmp_path: Path) -> None:
        """T034: mission_id is read from the canonical feature_dir/meta.json path."""
        feature_dir = _make_feature_dir(tmp_path, mission_id="01HTEST000000000000000000B")

        with _patch_resolver(feature_dir), _patch_invoke() as mock_invoke:
            run_retrospective_postcondition(
                mission_slug=MISSION_SLUG,
                repo_root=tmp_path,
            )

        _, kwargs = mock_invoke.call_args
        assert kwargs["mission_id"] == "01HTEST000000000000000000B"

    def test_legacy_mission_without_mission_id_succeeds(self, tmp_path: Path) -> None:
        """Legacy missions (no mission_id in meta.json) don't crash — use empty string."""
        feature_dir = tmp_path / "kitty-specs" / MISSION_SLUG
        feature_dir.mkdir(parents=True)
        # meta.json without mission_id (pre-083 style)
        (feature_dir / "meta.json").write_text(
            json.dumps({"mission_slug": MISSION_SLUG}), encoding="utf-8"
        )

        with _patch_resolver(feature_dir), _patch_invoke() as mock_invoke:
            run_retrospective_postcondition(
                mission_slug=MISSION_SLUG,
                repo_root=tmp_path,
            )

        mock_invoke.assert_called_once()
        _, kwargs = mock_invoke.call_args
        assert kwargs["mission_id"] == ""

    def test_emit_capture_failed_classify_io_error(self, tmp_path: Path) -> None:
        """_classify_exc maps OSError to 'io_error'."""
        from specify_cli.post_merge.retrospective_terminus import _classify_exc

        assert _classify_exc(OSError("disk full")) == "io_error"
        assert _classify_exc(PermissionError("no access")) == "io_error"

    def test_emit_capture_failed_classify_missing_artifacts(self, tmp_path: Path) -> None:
        """_classify_exc maps FileNotFoundError to 'missing_artifacts'."""
        from specify_cli.post_merge.retrospective_terminus import _classify_exc

        assert _classify_exc(FileNotFoundError("no file")) == "missing_artifacts"
        assert _classify_exc(IsADirectoryError("is dir")) == "missing_artifacts"

    def test_emit_capture_failed_classify_generator_exception(self, tmp_path: Path) -> None:
        """_classify_exc maps generic exceptions to 'generator_exception'."""
        from specify_cli.post_merge.retrospective_terminus import _classify_exc

        assert _classify_exc(ValueError("bad value")) == "generator_exception"
        assert _classify_exc(RuntimeError("boom")) == "generator_exception"


# ---------------------------------------------------------------------------
# #2119 follow-up — the auto-captured retrospective must be COMMITTED, so a
# merged/closed mission is never left with an uncommitted event-log append.
# ---------------------------------------------------------------------------


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    """Init a git repo on ``main`` with one seed commit so HEAD is on a branch."""
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / ".gitkeep").write_text("", encoding="utf-8")
    _git(root, "add", ".gitkeep")
    _git(root, "commit", "-m", "seed")


def _porcelain(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()


class TestRetrospectiveCommit:
    """The captured retrospective + its event-log append are committed (FR-016)."""

    def test_captured_retrospective_is_committed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Success path: retrospective.yaml + status.events.jsonl are committed →
        the working tree is clean after the postcondition (no dirty append)."""
        monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")
        _init_repo(tmp_path)
        feature_dir = _make_feature_dir(tmp_path)
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-m", "seed mission dir")
        assert _porcelain(tmp_path) == ""  # pre-condition: clean

        def _fake_capture(**_kwargs: Any) -> None:
            (feature_dir / "retrospective.yaml").write_text("schema_version: 1\n", encoding="utf-8")
            (feature_dir / "status.events.jsonl").write_text(
                '{"event": "RetrospectiveCaptured"}\n', encoding="utf-8"
            )

        with _patch_resolver(feature_dir), _patch_invoke(side_effect=_fake_capture):
            run_retrospective_postcondition(mission_slug=MISSION_SLUG, repo_root=tmp_path)

        assert (feature_dir / "retrospective.yaml").exists()
        # The retrospective artifacts specifically must be committed (absent from
        # porcelain) — unrelated runtime scratch (e.g. .kittify/) is not our concern.
        dirty = _porcelain(tmp_path)
        assert "retrospective.yaml" not in dirty, dirty
        assert "status.events.jsonl" not in dirty, dirty
        last_msg = _git(tmp_path, "log", "-1", "--format=%s").stdout.strip()
        assert "capture mission retrospective" in last_msg

    def test_capture_failed_event_is_committed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Failure path: the capture_failed event append is also committed — the
        durable event log is never left dirty even when capture fails."""
        monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")
        _init_repo(tmp_path)
        feature_dir = _make_feature_dir(tmp_path)
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-m", "seed mission dir")

        def _emit(**_kwargs: Any) -> None:
            (feature_dir / "status.events.jsonl").write_text(
                '{"event": "retrospective.capture_failed"}\n', encoding="utf-8"
            )

        with (
            _patch_resolver(feature_dir),
            _patch_invoke(side_effect=RuntimeError("boom")),
            patch(
                "specify_cli.post_merge.retrospective_terminus._emit_capture_failed",
                side_effect=_emit,
            ),
        ):
            run_retrospective_postcondition(mission_slug=MISSION_SLUG, repo_root=tmp_path)

        assert "status.events.jsonl" not in _porcelain(tmp_path), "capture_failed append must be committed"

    def test_noop_when_not_a_git_repo(self, tmp_path: Path) -> None:
        """Fail-open: a non-git tree does not raise; the file is left in place."""
        feature_dir = _make_feature_dir(tmp_path)
        (feature_dir / "retrospective.yaml").write_text("schema_version: 1\n", encoding="utf-8")

        # Must not raise even though tmp_path is not a git worktree.
        _commit_captured_retrospective(
            mission_slug=MISSION_SLUG, feature_dir=feature_dir, repo_root=tmp_path
        )
        assert (feature_dir / "retrospective.yaml").exists()

    def test_detached_head_reports_and_skips(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Detached HEAD: cannot resolve a destination → warn + skip (leave dirty),
        never raise. The warning surfaces the uncommitted append to the operator."""
        _init_repo(tmp_path)
        feature_dir = _make_feature_dir(tmp_path)
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-m", "seed mission dir")
        head_sha = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
        _git(tmp_path, "checkout", head_sha)  # detach HEAD
        (feature_dir / "retrospective.yaml").write_text("schema_version: 1\n", encoding="utf-8")

        import logging

        with caplog.at_level(logging.WARNING):
            _commit_captured_retrospective(
                mission_slug=MISSION_SLUG, feature_dir=feature_dir, repo_root=tmp_path
            )

        assert any("NOT committed" in rec.message for rec in caplog.records)
        # File remains uncommitted (skipped), but the operator was told.
        assert "retrospective.yaml" in _porcelain(tmp_path)

    def test_commit_failure_is_fail_open_with_remediation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """safe_commit RAISES → fail-open: no re-raise, the WARNING carries the
        manual ``git add && git commit`` remediation, and the artifacts are left
        dirty (never lost). Guards the terminus's 'must never abort merge/close'
        contract at the commit boundary."""
        import logging

        monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")
        _init_repo(tmp_path)
        feature_dir = _make_feature_dir(tmp_path)
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-m", "seed mission dir")

        def _fake_capture(**_kwargs: Any) -> None:
            (feature_dir / "retrospective.yaml").write_text("schema_version: 1\n", encoding="utf-8")
            (feature_dir / "status.events.jsonl").write_text(
                '{"event": "RetrospectiveCaptured"}\n', encoding="utf-8"
            )

        with (
            _patch_resolver(feature_dir),
            _patch_invoke(side_effect=_fake_capture),
            patch(
                "specify_cli.git.bookkeeping_commit.commit_merge_bookkeeping",
                side_effect=RuntimeError("boom: git index locked"),
            ),
            caplog.at_level(logging.WARNING),
        ):
            # Fail-open: must NOT raise even though the commit blew up.
            run_retrospective_postcondition(mission_slug=MISSION_SLUG, repo_root=tmp_path)

        # Artifacts are left dirty (never silently dropped).
        dirty = _porcelain(tmp_path)
        assert "retrospective.yaml" in dirty, dirty
        # The WARNING surfaces the exact manual remediation command.
        joined = " ".join(rec.getMessage() for rec in caplog.records)
        assert "could NOT be committed" in joined, joined
        assert "git -C" in joined and " add " in joined and "commit -m" in joined, joined

    def test_idempotency_heals_a_previously_failed_commit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Re-running after a FAILED commit re-commits the leftover dirt (#2280).

        First run: capture writes the artifacts but the commit fails (fail-open →
        left dirty). Second run: retrospective.yaml already exists so capture is
        skipped, yet the postcondition HEALS the leftover append. Exactly ONE
        retrospective commit lands and the tree ends clean."""
        monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")
        _init_repo(tmp_path)
        feature_dir = _make_feature_dir(tmp_path)
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-m", "seed mission dir")
        base_count = int(_git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip())

        def _fake_capture(**_kwargs: Any) -> None:
            (feature_dir / "retrospective.yaml").write_text("schema_version: 1\n", encoding="utf-8")
            (feature_dir / "status.events.jsonl").write_text(
                '{"event": "RetrospectiveCaptured"}\n', encoding="utf-8"
            )

        from specify_cli.git.bookkeeping_commit import commit_merge_bookkeeping as _real_commit

        calls = {"n": 0}

        def _flaky_commit(**kwargs: Any) -> Any:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient commit failure")
            return _real_commit(**kwargs)

        with (
            _patch_resolver(feature_dir),
            _patch_invoke(side_effect=_fake_capture),
            patch(
                "specify_cli.git.bookkeeping_commit.commit_merge_bookkeeping",
                side_effect=_flaky_commit,
            ),
        ):
            # Run 1 — capture succeeds, commit fails → artifacts left dirty.
            run_retrospective_postcondition(mission_slug=MISSION_SLUG, repo_root=tmp_path)
            assert "retrospective.yaml" in _porcelain(tmp_path), "run 1 commit should have failed"
            # Run 2 — capture skipped (yaml exists) but the leftover dirt is healed.
            run_retrospective_postcondition(mission_slug=MISSION_SLUG, repo_root=tmp_path)

        assert "retrospective.yaml" not in _porcelain(tmp_path), "run 2 should have healed the append"
        assert "status.events.jsonl" not in _porcelain(tmp_path)
        final_count = int(_git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip())
        assert final_count - base_count == 1, "exactly one retrospective commit must land"

    def test_symlinked_repo_root_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """F1: a symlinked repo_root must not raise out of the fail-open boundary.

        When the resolved feature_dir sits outside the LEXICAL symlink repo_root,
        the pre-fix ``path.relative_to(repo_root)`` raised ``ValueError`` and
        aborted the merge/close. Resolving both sides keeps it fail-open."""
        monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")
        real = tmp_path / "real"
        real.mkdir()
        _init_repo(real)
        link = tmp_path / "link"
        link.symlink_to(real, target_is_directory=True)

        # feature_dir on the REAL path; repo_root passed as the SYMLINK → the
        # naive lexical relative_to() would raise.
        feature_dir = real / "kitty-specs" / MISSION_SLUG
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps({"mission_id": "01HXYZ0000000000000000000A", "mission_slug": MISSION_SLUG}),
            encoding="utf-8",
        )
        (feature_dir / "retrospective.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        (feature_dir / "status.events.jsonl").write_text(
            '{"event": "RetrospectiveCaptured"}\n', encoding="utf-8"
        )

        # Must NOT raise (ValueError would abort merge/close). The artifacts are
        # never lost regardless of whether the commit lands.
        _commit_captured_retrospective(
            mission_slug=MISSION_SLUG, feature_dir=feature_dir, repo_root=link
        )
        assert (feature_dir / "retrospective.yaml").exists()
