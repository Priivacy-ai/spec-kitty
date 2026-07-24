"""IDENTITY resolution for ``sync import-history`` (WP-Y4, #2262).

Resolves the ``(project_uuid, project_slug, repo_slug)`` trio the SYNTHESIZE
stage stamps onto every envelope, honoring the mint-boundary invariants:

* **INV-2 (single mint boundary):** project identity is *persisted* only at a
  write-authorized boundary. The dry-run path is read-only
  (:func:`resolve_identity` never writes ``.kittify/config.yaml``); ``--apply``
  is the authorized boundary that may mint+persist via :func:`ensure_identity`.
* **INV-5 (real UUID on apply):** ``--apply`` uploads under the persisted real
  ``project_uuid``. The synthetic offline ``uuid5`` is dry-run-only and, by
  construction here, can never be produced on the apply path.

The stale "add ``persist_identity``" note in the issue §4 predates #1916, which
added :func:`resolve_identity` — the read-only counterpart of
:func:`ensure_identity`. We reuse that canonical seam rather than add a parallel
persist path.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence

from specify_cli.identity.project import (
    ensure_identity,
    is_writable,
    load_identity,
    resolve_identity,
)
from specify_cli.sync.history_import.synthesize import dry_run_project_uuid

_CONFIG_RELPATH = Path(".kittify") / "config.yaml"


class ImportIdentityError(RuntimeError):
    """Raised when ``--apply`` cannot obtain a persisted real project UUID.

    Fail-closed (INV-5/INV-6): the import must never upload historical events
    under an ephemeral or synthetic identity.
    """


@dataclass(frozen=True)
class ImportIdentity:
    """The project-identity trio threaded into every synthesized envelope."""

    project_uuid: uuid.UUID
    project_slug: str
    repo_slug: str
    is_synthetic: bool


def resolve_import_identity(
    repo_root: Path,
    mission_slugs: Sequence[str],
    *,
    apply: bool,
) -> ImportIdentity:
    """Resolve the identity trio for an import run.

    * ``--apply`` → the persisted real ``project_uuid`` (minting+persisting once
      at this authorized boundary if the checkout is uninitialized, else failing
      closed). Never synthetic.
    * dry-run → the persisted real UUID when the checkout is initialized, else a
      synthetic offline ``uuid5`` for schema-only preview. Never persists.
    """
    persisted = resolve_identity(repo_root)  # read-only; never writes config
    project_slug = persisted.project_slug or repo_root.resolve().name
    repo_slug = persisted.repo_slug or project_slug

    if apply:
        return ImportIdentity(
            project_uuid=_real_uuid_for_apply(repo_root, persisted.project_uuid),
            project_slug=project_slug,
            repo_slug=repo_slug,
            is_synthetic=False,
        )

    if persisted.project_uuid is not None:
        return ImportIdentity(
            project_uuid=persisted.project_uuid,
            project_slug=project_slug,
            repo_slug=repo_slug,
            is_synthetic=False,
        )

    return ImportIdentity(
        project_uuid=dry_run_project_uuid(mission_slugs),
        project_slug=project_slug,
        repo_slug=repo_slug,
        is_synthetic=True,
    )


def _real_uuid_for_apply(repo_root: Path, persisted_uuid: uuid.UUID | None) -> uuid.UUID:
    """Return the persisted real project UUID for ``--apply``, or fail closed.

    An already-initialized checkout returns its persisted UUID with no mint
    (INV-2). A truly-uninitialized checkout mints+persists once here (the
    authorized boundary) and re-reads to confirm the write landed — refusing to
    proceed under an ephemeral identity that a re-run could not reproduce.
    """
    if persisted_uuid is not None:
        return persisted_uuid

    config_path = repo_root / _CONFIG_RELPATH
    if not is_writable(config_path):
        raise ImportIdentityError(
            "cannot persist a project identity (config.yaml is not writable); run `spec-kitty init` in this checkout before importing history"
        )

    ensure_identity(repo_root)  # mints + persists at this authorized boundary
    minted: uuid.UUID | None = load_identity(config_path).project_uuid
    if minted is None:
        raise ImportIdentityError("project identity did not persist; refusing to upload under an ephemeral UUID that a re-run could not reproduce")
    return minted
