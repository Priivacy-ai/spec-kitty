"""Determinism + no-write guarantees for minted build_id (WP01 / FR-002).

Locks Decision C: a *missing* build_id is derived deterministically from the
resolved (project_uuid, node_id) pair via :func:`derive_build_id`, so the
read-only resolver (:func:`resolve_identity`) returns a stable identity without
drifting build_id between calls and without writing ``config.yaml``
(NFR-001 / SC-003 / C-005 / C-IR-4).
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from ruamel.yaml import YAML

from specify_cli.identity.project import (
    ProjectIdentity,
    atomic_write_config,
    derive_build_id,
    resolve_identity,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_NODE_ID = "abc123def456"
_OTHER_NODE_ID = "ffffffffffff"


def _config_path(repo_root: Path) -> Path:
    return repo_root / ".kittify" / "config.yaml"


def test_derive_build_id_is_stable_across_repeated_calls() -> None:
    """Same inputs produce an identical build_id across N>=5 calls (NFR-001)."""
    project_uuid = uuid4()
    results = {derive_build_id(project_uuid, _NODE_ID) for _ in range(6)}
    assert len(results) == 1


def test_derive_build_id_returns_valid_uuid_string() -> None:
    """The derived value is a parseable UUID string (upstream-contract shape)."""
    derived = derive_build_id(uuid4(), _NODE_ID)
    # Must not raise — a malformed string would.
    assert str(UUID(derived)) == derived


def test_derive_build_id_varies_with_project_uuid() -> None:
    """Different project_uuid (same node_id) yields a different build_id."""
    node_id = _NODE_ID
    a = derive_build_id(uuid4(), node_id)
    b = derive_build_id(uuid4(), node_id)
    assert a != b


def test_derive_build_id_varies_with_node_id() -> None:
    """Different node_id (same project_uuid) yields a different build_id."""
    project_uuid = uuid4()
    a = derive_build_id(project_uuid, _NODE_ID)
    b = derive_build_id(project_uuid, _OTHER_NODE_ID)
    assert a != b


def test_with_defaults_completes_identity_with_derived_build_id(tmp_path: Path) -> None:
    """A missing build_id is filled deterministically; is_complete becomes True."""
    project_uuid = uuid4()
    identity = ProjectIdentity(
        project_uuid=project_uuid,
        project_slug="repo",
        node_id=_NODE_ID,
        build_id=None,
    )

    completed = identity.with_defaults(tmp_path)

    assert completed.is_complete
    assert completed.build_id == derive_build_id(project_uuid, _NODE_ID)


def test_with_defaults_preserves_present_build_id(tmp_path: Path) -> None:
    """An already-present build_id is returned unchanged (C-005)."""
    identity = ProjectIdentity(
        project_uuid=uuid4(),
        project_slug="repo",
        node_id=_NODE_ID,
        build_id="pre-existing-build-id",
    )

    completed = identity.with_defaults(tmp_path)

    assert completed.build_id == "pre-existing-build-id"


def test_resolve_identity_legacy_missing_build_id_is_stable_no_write(tmp_path: Path) -> None:
    """Legacy identity (uuid+slug+node, no build_id): repeated resolve is stable, no write."""
    config_path = _config_path(tmp_path)
    legacy = ProjectIdentity(
        project_uuid=uuid4(),
        project_slug="legacy-repo",
        node_id=_NODE_ID,
        build_id=None,
    )
    atomic_write_config(config_path, legacy)
    before = config_path.read_text(encoding="utf-8")

    first = resolve_identity(tmp_path)
    second = resolve_identity(tmp_path)

    assert first.is_complete
    assert first.project_uuid == second.project_uuid
    assert first.build_id == second.build_id
    # build_id was derived, not random.
    assert legacy.project_uuid is not None  # set by the legacy fixture above; narrows UUID|None -> UUID
    assert first.build_id == derive_build_id(legacy.project_uuid, _NODE_ID)
    # No write occurred (file content byte-identical).
    assert config_path.read_text(encoding="utf-8") == before


def test_resolve_identity_complete_on_disk_returned_unchanged(tmp_path: Path) -> None:
    """A complete persisted identity is returned unchanged (C-005)."""
    config_path = _config_path(tmp_path)
    complete = ProjectIdentity(
        project_uuid=uuid4(),
        project_slug="complete-repo",
        node_id=_NODE_ID,
        build_id="stored-build-id",
    )
    atomic_write_config(config_path, complete)
    before = config_path.read_text(encoding="utf-8")

    resolved = resolve_identity(tmp_path)

    assert resolved.project_uuid == complete.project_uuid
    assert resolved.project_slug == complete.project_slug
    assert resolved.node_id == complete.node_id
    assert resolved.build_id == "stored-build-id"
    assert config_path.read_text(encoding="utf-8") == before


def test_resolve_identity_empty_config_reports_uninitialized_no_write(tmp_path: Path) -> None:
    """resolve_identity on a missing config never mints project_uuid (C-IR-4)."""
    config_path = _config_path(tmp_path)
    assert not config_path.exists()

    resolved = resolve_identity(tmp_path)

    assert not resolved.is_complete
    assert resolved.project_uuid is None
    assert resolved.build_id is None
    assert resolved.project_slug is not None
    assert resolved.node_id is not None
    assert not config_path.exists()


def test_resolve_identity_empty_config_does_not_create_kittify_dir(tmp_path: Path) -> None:
    """No side-effect directory creation on the read path for an uninitialized checkout."""
    resolve_identity(tmp_path)
    assert not (tmp_path / ".kittify").exists()


def test_resolve_identity_empty_config_has_no_uuid_drift(tmp_path: Path) -> None:
    """Repeated uninitialized reads stay not-initialized instead of minting UUIDs."""
    first = resolve_identity(tmp_path)
    second = resolve_identity(tmp_path)

    assert first.project_uuid is None
    assert second.project_uuid is None
    assert first.build_id is None
    assert second.build_id is None
    assert first.node_id == second.node_id


def test_stored_legacy_build_id_survives_a_persisting_roundtrip(tmp_path: Path) -> None:
    """Sanity: once a derived build_id is persisted, reloading yields the same value."""
    config_path = _config_path(tmp_path)
    project_uuid = uuid4()
    resolved = ProjectIdentity(
        project_uuid=project_uuid,
        project_slug="repo",
        node_id=_NODE_ID,
        build_id=None,
    ).with_defaults(tmp_path)

    atomic_write_config(config_path, resolved)

    yaml = YAML()
    with open(config_path, encoding="utf-8") as handle:
        stored = yaml.load(handle)
    assert stored["project"]["build_id"] == derive_build_id(project_uuid, _NODE_ID)
