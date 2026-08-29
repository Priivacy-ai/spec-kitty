"""WP03 (#3470) body-capture short-circuit + anti-swallow guards.

These tests live in ``tests/deactivation/`` on purpose: they must run on the
**default (sync-inactive)** path — the exact path where #3470's body-outbox
``RuntimeError`` traceback fired on a bare install. ``tests/sync/`` is gated off
by WP05's module-level ``skipif``; this file must not be.

**Conftest interaction (BINDING, WP02/WP03 correction).** The suite conftest
(``tests/conftest.py``) unconditionally sets ``SPEC_KITTY_ENABLE_SAAS_SYNC=1``
for every test (only de-masked in WP04). A default-path guard therefore cannot
rely on the "default off" state existing at run time — it must force
sync-inactive **in-test** by ``delenv``-ing the enable flag and normalizing the
disable vars. The ``_force_sync_inactive`` fixture does exactly that; without it
``sync_active()`` is True and the short-circuit assertions are vacuous.

The anti-swallow arm (FR-008 / SC-005) proves the T009 gate is a *gated
early-return keyed on inactive*, NOT a blanket ``try/except``: when sync is
active, a genuine ``_require_project_destination`` violation (``body_queue.py:104``,
untouched — C-003) still SURFACES via ``DossierSyncResult.errors`` — the pipeline
never raises.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from specify_cli.identity.project import ProjectIdentity
from specify_cli.sync import body_queue as body_queue_mod
from specify_cli.sync import dossier_pipeline
from specify_cli.sync.body_queue import BodyEnqueueResult, OfflineBodyUploadQueue
from specify_cli.sync.dossier_pipeline import (
    DossierSyncResult,
    sync_feature_dossier,
    trigger_feature_dossier_sync_if_enabled,
)
from specify_cli.sync.layout_generation import LayoutDestination, LayoutWritePermit
from specify_cli.sync.namespace import NamespaceRef
from specify_cli.sync.project_identity import CanonicalProjectUUID

pytestmark = [pytest.mark.fast]

# A nod to #3470; lowercase canonical hex so it round-trips through
# ``CanonicalProjectUUID`` and the body-queue owner comparison unchanged.
_PROJECT_UUID = "34700000-0000-4000-8000-000000003470"

# A genuine LEGACY-destination permit: exactly what the layout authority hands a
# writer on a bare/legacy install where no project destination is resolvable.
# ``_require_project_destination`` (body_queue.py:104) rejects it — the real
# #3470 RuntimeError.
_LEGACY_PERMIT = LayoutWritePermit(
    project_uuid=CanonicalProjectUUID.parse(_PROJECT_UUID),
    generation=1,
    destination=LayoutDestination.LEGACY,
)


@pytest.fixture
def _force_sync_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``sync_active()`` return False, overriding the autouse conftest arm."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", raising=False)


@pytest.fixture
def _force_sync_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """Arm the sync surface (opt-in) — the anti-swallow / active-path arm."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", raising=False)


def _identity() -> ProjectIdentity:
    return ProjectIdentity(
        project_uuid=UUID(_PROJECT_UUID),
        project_slug="wp03-proj",
        node_id="abcdef123470",
    )


def _patch_trigger_deps(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Stub every collaborator the trigger reaches AFTER the gate.

    Returns a spy installed on ``dossier_pipeline.sync_feature_dossier`` — the
    body-capture entrypoint. If the gate short-circuits, the spy is never
    reached; if it does not, the spy fires (the RED signal for arm (a)).
    ``ProjectSyncStore`` / ``OfflineBodyUploadQueue`` are stubbed so the
    pre-spy path cannot fail for an unrelated reason and false-green the gate.
    """
    monkeypatch.setattr(
        "specify_cli.identity.project.resolve_identity",
        lambda _root: _identity(),
    )
    monkeypatch.setattr(
        "specify_cli.core.paths.get_feature_target_branch",
        lambda _root, _slug: "main",
    )
    monkeypatch.setattr(
        "specify_cli.mission.get_mission_type",
        lambda _feature: "software-dev",
    )
    monkeypatch.setattr(
        "specify_cli.sync.namespace.resolve_manifest_version",
        lambda _mission: "1",
    )
    monkeypatch.setattr(
        "specify_cli.sync.project_store.ProjectSyncStore",
        MagicMock(),
    )
    monkeypatch.setattr(
        "specify_cli.sync.body_queue.OfflineBodyUploadQueue",
        MagicMock(),
    )
    spy = MagicMock(
        return_value=DossierSyncResult(
            dossier=None,
            events_emitted=0,
            body_outcomes=[],
        )
    )
    monkeypatch.setattr(dossier_pipeline, "sync_feature_dossier", spy)
    return spy


def test_default_path_short_circuits_body_capture(
    _force_sync_inactive: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-007: on the default (inactive) path the trigger returns without ever
    reaching the body-capture entrypoint — so no body-outbox RuntimeError
    traceback can fire on a bare install."""
    spy = _patch_trigger_deps(monkeypatch)

    result = trigger_feature_dossier_sync_if_enabled(tmp_path, "047-feat", tmp_path)

    # Enqueue / body-capture path not reached (RED before the T009 gate lands).
    spy.assert_not_called()
    assert result is None
    captured = capsys.readouterr()
    assert "RuntimeError" not in captured.err
    assert "Traceback" not in captured.err


def test_active_path_reaches_body_capture(
    _force_sync_active: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-008: when armed, the gate is a NO-OP — the trigger still drives the
    real body-capture entrypoint. Proves the short-circuit is keyed on inactive,
    not applied unconditionally."""
    spy = _patch_trigger_deps(monkeypatch)

    result = trigger_feature_dossier_sync_if_enabled(tmp_path, "047-feat", tmp_path)

    spy.assert_called_once()
    assert result is not None


class _LegacyLayoutBodyQueue:
    """A stand-in body-outbox queue on a LEGACY layout.

    Its ``enqueue`` invokes the production C-003 guard
    ``body_queue._require_project_destination`` (``body_queue.py:104``,
    untouched by this WP) with a genuine LEGACY permit — reproducing the exact
    #3470 ``RuntimeError`` deterministically, without fighting the layout
    state machine's greenfield->project_only write resolution. It is passed
    where an ``OfflineBodyUploadQueue`` is expected (see the ``cast`` at the
    call site); the pipeline only reaches ``enqueue`` on the legacy path.
    """

    def enqueue(
        self,
        namespace: NamespaceRef,
        artifact_path: str,
        content_hash: str,
        content_body: str,
        size_bytes: int,
        hash_algorithm: str = "sha256",
        *,
        test_hooks: object | None = None,
    ) -> BodyEnqueueResult:
        body_queue_mod._require_project_destination(_LEGACY_PERMIT)
        raise AssertionError("unreachable: the LEGACY permit guard must raise")


def test_active_genuine_destination_violation_surfaces_via_errors(
    _force_sync_active: None,
    tmp_path: Path,
) -> None:
    """SC-005 / FR-008 anti-swallow: with sync armed and a genuine
    ``_require_project_destination`` violation on a LEGACY layout, the failure
    SURFACES via ``DossierSyncResult.errors`` — the pipeline never raises and
    the error is never swallowed. Green both before and after the T009 gate: the
    gate lives in the trigger and does not touch the active body path."""
    from specify_cli.sync.consent import record_project_opt_in

    feature_dir = tmp_path / "kitty-specs" / "047-feat"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        "# Private mission\n\nBody content to enqueue.\n", encoding="utf-8"
    )

    # Consent so the legacy body path reaches enqueue rather than skipping.
    record_project_opt_in(_PROJECT_UUID, actor="test:wp03-anti-swallow")

    namespace_ref = NamespaceRef.from_context(
        identity=_identity(),
        mission_slug="047-feat",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
    )

    result = sync_feature_dossier(
        feature_dir=feature_dir,
        namespace_ref=namespace_ref,
        body_queue=cast(OfflineBodyUploadQueue, _LegacyLayoutBodyQueue()),
        mission_type="software-dev",
    )

    assert isinstance(result, DossierSyncResult)
    assert result.errors, "genuine destination violation must surface, not be swallowed"
    joined = " ".join(result.errors)
    assert "project_only layout" in joined
