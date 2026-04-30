"""Synthesis manifest writer — WP03 (T017).

Owns the ``SynthesisManifest`` and ``ManifestArtifactEntry`` Pydantic models
plus their IO helpers.

The manifest is written **last** in the promote pipeline (KD-2 authority
rule): a partial promote (e.g. crashed after some ``os.replace`` calls but
before the manifest write) leaves the live tree in an authors-but-no-manifest
state that readers treat as partial-and-rerunable.

Storage location: ``.kittify/charter/synthesis-manifest.yaml``

Data model reference: data-model.md §E-6 / §E-6a.
Schema reference: contracts/synthesis-manifest.schema.yaml.

All filesystem writes go through ``PathGuard`` (FR-016).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

from .errors import ManifestIntegrityError
from .synthesize_pipeline import canonical_yaml

if TYPE_CHECKING:
    from .path_guard import PathGuard

# Canonical location of the synthesis manifest.
MANIFEST_PATH = Path(".kittify/charter/synthesis-manifest.yaml")
_ARTIFACT_PATH_PREFIX = Path(".kittify/doctrine")
_PROVENANCE_PATH_PREFIX = Path(".kittify/charter/provenance")


# ---------------------------------------------------------------------------
# Data models (data-model.md §E-6 / §E-6a)
# ---------------------------------------------------------------------------


class ManifestArtifactEntry(BaseModel):
    """One synthesized artifact listed in the synthesis manifest (data-model §E-6a)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["directive", "tactic", "styleguide"]
    slug: str
    path: str
    """Repo-relative path to the artifact YAML under ``.kittify/doctrine/``."""

    provenance_path: str
    """Repo-relative path to the provenance sidecar under ``.kittify/charter/``."""

    content_hash: str
    """SHA-256 hex digest of the artifact YAML bytes."""


class SynthesisManifest(BaseModel):
    """Top-of-bundle manifest — the authoritative commit marker (data-model §E-6).

    Written last by ``write_pipeline.promote`` so that readers can detect
    partial-promote states: manifest absent → partial; manifest present but
    hash mismatch → corrupt; manifest present + all hashes pass → live tree
    is authoritative.

    Schema version 2 (Phase 7): added synthesizer_version and manifest_hash.
    ``manifest_hash`` is the SHA-256 hex digest of ``canonical_yaml(all fields
    except manifest_hash)`` — allows readers to verify manifest self-integrity.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["2"] = "2"
    mission_id: str | None = None
    created_at: str
    """ISO 8601 UTC timestamp."""

    run_id: str
    """ULID matching the staging directory that produced this manifest."""

    adapter_id: str
    """Primary adapter id.  Empty string for mixed-identity runs."""

    adapter_version: str
    """Primary adapter version.  Empty string for mixed-identity runs."""

    synthesizer_version: str = Field(..., min_length=1)
    """Version of the spec-kitty-cli package that produced this manifest."""

    manifest_hash: str = Field(..., min_length=64, max_length=64)
    """SHA-256 hex digest of canonical_yaml(all manifest fields except manifest_hash)."""

    artifacts: list[ManifestArtifactEntry] = Field(default_factory=list)
    """One entry per committed artifact, in deterministic order."""


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------


def _yaml_instance() -> YAML:
    y = YAML()
    y.default_flow_style = False
    y.explicit_start = False
    return y


def dump_yaml(manifest: SynthesisManifest, path: Path, guard: PathGuard) -> None:
    """Serialize ``manifest`` to ``path`` via ``PathGuard.write_text``.

    Uses ``canonical_yaml`` for stable serialization so that the file bytes
    are deterministic under identical inputs (NFR-006).

    Parameters
    ----------
    manifest:
        Fully-assembled ``SynthesisManifest``.
    path:
        Target path.  Must be within the PathGuard allowlist.
    guard:
        PathGuard instance used for all writes.
    """
    data = manifest.model_dump(mode="python")
    # Serialize the top-level manifest using canonical_yaml for key ordering.
    yaml_bytes = canonical_yaml(data)
    guard.write_text(
        path,
        yaml_bytes.decode("utf-8"),
        encoding="utf-8",
        caller="manifest.dump_yaml",
    )


def load_yaml(path: Path) -> SynthesisManifest:
    """Deserialize the manifest from ``path`` and validate with Pydantic.

    Parameters
    ----------
    path:
        Absolute or repo-relative path to the synthesis manifest YAML.

    Returns
    -------
    SynthesisManifest
        Validated manifest.

    Raises
    ------
    pydantic.ValidationError
        If the YAML content does not match the SynthesisManifest schema.
    FileNotFoundError
        If ``path`` does not exist.
    """
    y = _yaml_instance()
    raw = y.load(path.read_text(encoding="utf-8"))
    return SynthesisManifest.model_validate(raw)


def verify_manifest_hash(manifest: SynthesisManifest) -> None:
    """Verify the manifest self-hash field.

    Recomputes SHA-256 of the canonical YAML serialization of all manifest
    fields except ``manifest_hash`` itself and compares to the stored value.

    Raises
    ------
    ValueError
        If the computed hash does not match ``manifest.manifest_hash``.
    """
    data = manifest.model_dump(mode="python")
    data_without_hash = {k: v for k, v in data.items() if k != "manifest_hash"}
    computed = hashlib.sha256(canonical_yaml(data_without_hash)).hexdigest()
    if computed != manifest.manifest_hash:
        raise ValueError(
            f"manifest_hash mismatch (stored {manifest.manifest_hash[:12]}..., "
            f"computed {computed[:12]}...)"
        )


def _validate_manifest_path(raw_path: str, *, field_name: str, required_prefix: Path) -> Path:
    """Return a safe repo-relative manifest path under ``required_prefix``."""
    path = Path(raw_path.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(
            f"{field_name} must be repo-relative and stay under "
            f"{required_prefix.as_posix()}: {raw_path}"
        )
    try:
        path.relative_to(required_prefix)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be under {required_prefix.as_posix()}: {raw_path}"
        ) from exc
    return path


def _resolve_under_repo(repo_root: Path, rel_path: Path, *, field_name: str) -> Path:
    """Resolve ``rel_path`` and fail if symlinks escape ``repo_root``."""
    repo_resolved = repo_root.resolve(strict=False)
    resolved = (repo_root / rel_path).resolve(strict=False)
    try:
        resolved.relative_to(repo_resolved)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} resolves outside repository root: {rel_path.as_posix()}"
        ) from exc
    return resolved


def verify(manifest: SynthesisManifest, repo_root: Path) -> None:
    """Verify that every artifact listed in the manifest exists with matching hash.

    Implements the **authority rule** from KD-2: live tree is authoritative IFF
    manifest is present AND all ``content_hash`` checks pass.

    Parameters
    ----------
    manifest:
        The manifest to verify.
    repo_root:
        Repository root used to resolve relative artifact paths.

    Raises
    ------
    ManifestIntegrityError
        When any artifact file is missing or its on-disk hash does not match
        the ``content_hash`` stored in the manifest entry.
    """
    manifest_path = str(MANIFEST_PATH)
    for entry in manifest.artifacts:
        artifact_rel = _validate_manifest_path(
            entry.path,
            field_name="manifest artifact path",
            required_prefix=_ARTIFACT_PATH_PREFIX,
        )
        _validate_manifest_path(
            entry.provenance_path,
            field_name="manifest provenance path",
            required_prefix=_PROVENANCE_PATH_PREFIX,
        )
        artifact_path = _resolve_under_repo(
            repo_root,
            artifact_rel,
            field_name="manifest artifact path",
        )
        if not artifact_path.exists():
            raise ManifestIntegrityError(
                manifest_path=manifest_path,
                offending_artifact=entry.path,
            )
        on_disk_bytes = artifact_path.read_bytes()
        on_disk_hash = hashlib.sha256(on_disk_bytes).hexdigest()
        if on_disk_hash != entry.content_hash:
            raise ManifestIntegrityError(
                manifest_path=manifest_path,
                offending_artifact=entry.path,
            )


__all__ = [
    "ManifestArtifactEntry",
    "SynthesisManifest",
    "MANIFEST_PATH",
    "dump_yaml",
    "load_yaml",
    "verify",
    "verify_manifest_hash",
]
