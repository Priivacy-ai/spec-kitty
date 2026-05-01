"""Regression test: emit_status_transition fan-out works end-to-end.

After P1.3 the status package no longer imports from sync; SaaS fan-out
and dossier-sync triggers are routed through registered adapters. This
test guards against the failure mode where the registry pattern silently
drops fan-out because registration never ran.

Cases covered:
1. Sync pre-imported -> handlers registered -> emit_status_transition
   fans out as expected.
2. No sync import (and registry cleared) -> fan-out is a silent no-op.
   This documents the bootstrap requirement.
3. A failing handler does not block canonical persistence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.status import adapters
from specify_cli.status.emit import emit_status_transition
from specify_cli.status.models import Lane, StatusEvent, TransitionRequest

pytestmark = pytest.mark.fast


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    fd = tmp_path / "kitty-specs" / "test-feature"
    fd.mkdir(parents=True)
    return fd


class TestFanOutPreservation:
    """emit_status_transition must invoke registered fan-out handlers."""

    def test_saas_fanout_fires_when_handler_registered(self, feature_dir: Path) -> None:
        """Registering a SaaS handler causes emit_status_transition to call it."""
        adapters.reset_handlers()
        captured: list[dict] = []

        def fake_saas(**kwargs: object) -> None:
            captured.append(dict(kwargs))

        adapters.register_saas_fanout_handler(fake_saas)

        try:
            event = emit_status_transition(
                TransitionRequest(
                    feature_dir=feature_dir,
                    mission_slug="test-feature",
                    wp_id="WP01",
                    to_lane="claimed",
                    actor="test-actor",

                )
            )
            assert isinstance(event, StatusEvent)
            assert event.to_lane == Lane.CLAIMED

            assert len(captured) == 1, "SaaS fan-out handler must be invoked exactly once"
            call = captured[0]
            assert call["wp_id"] == "WP01"
            assert call["to_lane"] == "claimed"
            assert call["actor"] == "test-actor"
            assert call["mission_slug"] == "test-feature"
        finally:
            adapters.reset_handlers()

    def test_dossier_sync_fires_when_handler_registered(self, feature_dir: Path, tmp_path: Path) -> None:
        """Registering a dossier-sync handler causes emit_status_transition to call it."""
        adapters.reset_handlers()
        captured: list[tuple] = []

        def fake_dossier(fd: Path, slug: str, repo: Path) -> None:
            captured.append((fd, slug, repo))

        adapters.register_dossier_sync_handler(fake_dossier)

        try:
            emit_status_transition(
                TransitionRequest(
                    feature_dir=feature_dir,
                    mission_slug="test-feature",
                    wp_id="WP01",
                    to_lane="claimed",
                    actor="test-actor",
                    repo_root=tmp_path,
                )
            )
            assert len(captured) == 1
            assert captured[0][1] == "test-feature"
        finally:
            adapters.reset_handlers()

    def test_no_handlers_registered_is_silent_no_op(self, feature_dir: Path) -> None:
        """Empty registry -> emit_status_transition succeeds with silent fan-out drop."""
        adapters.reset_handlers()

        try:
            event = emit_status_transition(
                TransitionRequest(
                    feature_dir=feature_dir,
                    mission_slug="test-feature",
                    wp_id="WP01",
                    to_lane="claimed",
                    actor="test-actor",

                )
            )
            assert event is not None
            assert event.to_lane == Lane.CLAIMED
        finally:
            adapters.reset_handlers()

    def test_handler_exception_does_not_block_persistence(self, feature_dir: Path) -> None:
        """A failing handler must not propagate or block canonical persistence."""
        adapters.reset_handlers()

        def boom(**kwargs: object) -> None:
            raise RuntimeError("handler exploded")

        adapters.register_saas_fanout_handler(boom)

        try:
            event = emit_status_transition(
                TransitionRequest(
                    feature_dir=feature_dir,
                    mission_slug="test-feature",
                    wp_id="WP01",
                    to_lane="claimed",
                    actor="test-actor",

                )
            )
            assert event is not None
        finally:
            adapters.reset_handlers()


class TestSyncBootstrapRegisters:
    """Importing specify_cli.sync registers all three handlers/emitters."""

    def test_sync_import_registers_all_three(self) -> None:
        """Bootstrap proof: importing sync wires up the full fan-out chain."""
        import importlib

        import specify_cli.sync

        adapters.reset_handlers()
        from specify_cli.dossier import emitter_adapter

        emitter_adapter.reset_dossier_emitter()

        # Reload to re-trigger the registration block at the bottom of
        # sync/__init__.py.
        importlib.reload(specify_cli.sync)

        assert len(adapters._saas_handlers) >= 1, (
            "sync import should register a SaaS fan-out handler"
        )
        assert len(adapters._dossier_handlers) >= 1, (
            "sync import should register a dossier-sync handler"
        )
        assert emitter_adapter._emitter is not None, (
            "sync import should register a dossier emitter"
        )

    def test_repeated_sync_reloads_do_not_duplicate_handlers(self) -> None:
        """Reloading sync N times must NOT produce N duplicate handlers.

        register_dossier_sync_handler / register_saas_fanout_handler
        are idempotent by qualified name. A reload re-executes the
        registration block but creates fresh function objects with the
        same __qualname__; the registry must replace rather than
        append, otherwise reload-based test isolation produces
        duplicate fan-out invocations on every status transition.
        """
        import importlib

        import specify_cli.sync
        from specify_cli.dossier import emitter_adapter

        adapters.reset_handlers()
        emitter_adapter.reset_dossier_emitter()

        for _ in range(3):
            importlib.reload(specify_cli.sync)

        assert len(adapters._saas_handlers) == 1, (
            f"Expected exactly 1 SaaS handler after 3 reloads, got "
            f"{len(adapters._saas_handlers)}"
        )
        assert len(adapters._dossier_handlers) == 1, (
            f"Expected exactly 1 dossier-sync handler after 3 reloads, got "
            f"{len(adapters._dossier_handlers)}"
        )
        # Dossier emitter is single-slot already (replace semantics)
        assert emitter_adapter._emitter is not None
