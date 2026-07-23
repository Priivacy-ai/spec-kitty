"""Tests for the IDENTITY stage of ``sync import-history`` — WP-Y4 (#2262).

Pins the mint-boundary invariants:

* INV-2: the dry-run (read) path never writes ``.kittify/config.yaml``.
* INV-5: ``--apply`` resolves the persisted real UUID (never synthetic), minting
  once at the authorized boundary when the checkout is uninitialized, and
  failing closed when it cannot persist.
"""

from __future__ import annotations

import uuid

import pytest

from specify_cli.identity.project import ProjectIdentity, atomic_write_config
from specify_cli.sync.history_import import identity as identity_module
from specify_cli.sync.history_import.identity import (
    ImportIdentityError,
    resolve_import_identity,
)
from specify_cli.sync.history_import.synthesize import dry_run_project_uuid

pytestmark = pytest.mark.fast

_KNOWN_UUID = uuid.UUID("11111111-2222-3333-4444-555555555555")


def _config_path(repo_root):
    return repo_root / ".kittify" / "config.yaml"


def _seed_identity(repo_root, *, repo_slug="acme/demo-project"):
    atomic_write_config(
        _config_path(repo_root),
        ProjectIdentity(
            project_uuid=_KNOWN_UUID,
            project_slug="demo-project",
            node_id="node-abc",
            repo_slug=repo_slug,
            build_id="build-1",
        ),
    )


# ── dry-run: read-only, synthetic when uninitialized (INV-2) ──────────────────


def test_dry_run_uninitialized_is_synthetic_and_writes_nothing(tmp_path):
    result = resolve_import_identity(tmp_path, ["m-one", "m-two"], apply=False)

    assert result.is_synthetic is True
    assert result.project_uuid == dry_run_project_uuid(["m-one", "m-two"])
    # The read path must never mint/persist an identity (INV-2 / no-dirty-tree).
    assert not _config_path(tmp_path).exists()


def test_dry_run_initialized_uses_real_uuid_without_writing(tmp_path):
    _seed_identity(tmp_path)
    before = _config_path(tmp_path).read_bytes()

    result = resolve_import_identity(tmp_path, ["ignored"], apply=False)

    assert result.is_synthetic is False
    assert result.project_uuid == _KNOWN_UUID
    assert result.repo_slug == "acme/demo-project"
    # Byte-identical config: resolution did not rewrite it.
    assert _config_path(tmp_path).read_bytes() == before


# ── apply: real UUID, never synthetic (INV-5) ─────────────────────────────────


def test_apply_initialized_uses_persisted_uuid_no_remint(tmp_path):
    _seed_identity(tmp_path)
    result = resolve_import_identity(tmp_path, ["ignored"], apply=True)

    assert result.is_synthetic is False
    assert result.project_uuid == _KNOWN_UUID


def test_apply_uninitialized_mints_persists_and_is_idempotent(tmp_path):
    # A real checkout with an uninitialized identity: .kittify/ exists, but no
    # project UUID is persisted yet. --apply is the authorized boundary to mint.
    (tmp_path / ".kittify").mkdir()

    first = resolve_import_identity(tmp_path, [], apply=True)

    assert first.is_synthetic is False
    assert first.project_uuid is not None
    assert _config_path(tmp_path).exists(), "--apply must persist the minted identity"

    # A second apply reuses the persisted UUID — no re-mint (idempotent).
    second = resolve_import_identity(tmp_path, [], apply=True)
    assert second.project_uuid == first.project_uuid


def test_apply_fails_closed_when_config_not_writable(tmp_path, monkeypatch):
    monkeypatch.setattr(identity_module, "is_writable", lambda _path: False)
    with pytest.raises(ImportIdentityError, match="not writable"):
        resolve_import_identity(tmp_path, [], apply=True)


def test_apply_fails_closed_when_persist_silently_fails(tmp_path, monkeypatch):
    """If the boundary reports writable but no UUID actually lands (a silent
    write failure), --apply refuses rather than proceeding under no identity."""
    (tmp_path / ".kittify").mkdir()
    monkeypatch.setattr(identity_module, "is_writable", lambda _path: True)
    # ensure_identity "runs" but persists nothing → the re-read finds no UUID.
    monkeypatch.setattr(identity_module, "ensure_identity", lambda _root: None)
    with pytest.raises(ImportIdentityError, match="did not persist"):
        resolve_import_identity(tmp_path, [], apply=True)


def test_apply_fails_closed_on_a_non_checkout(tmp_path):
    """No ``.kittify/`` at all means this isn't an initialized checkout — apply
    must refuse rather than mint an identity outside a real project."""
    with pytest.raises(ImportIdentityError, match="spec-kitty init"):
        resolve_import_identity(tmp_path, [], apply=True)


# ── slug / repo_slug derivation ───────────────────────────────────────────────


def test_repo_slug_falls_back_to_project_slug_when_absent(tmp_path):
    _seed_identity(tmp_path, repo_slug=None)
    result = resolve_import_identity(tmp_path, ["ignored"], apply=False)
    assert result.repo_slug == result.project_slug == "demo-project"
