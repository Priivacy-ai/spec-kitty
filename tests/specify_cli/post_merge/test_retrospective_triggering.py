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
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from specify_cli.post_merge.retrospective_terminus import run_retrospective_postcondition

pytestmark = [pytest.mark.unit]

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
    """Patch resolve_feature_dir_for_slug at its source module to return feature_dir."""
    return patch(
        "specify_cli.missions.feature_dir_resolver.resolve_feature_dir_for_slug",
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
