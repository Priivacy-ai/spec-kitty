"""Per-artifact provenance sidecar writer — WP03 (T015).

Owns the on-disk representation of ProvenanceEntry.  The model itself is
defined in ``synthesize_pipeline.py`` (WP02) so that the synthesis pipeline
can assemble provenance in-memory without importing this writer module.

Storage layout (data-model.md §E-4):
    .kittify/charter/provenance/<kind>-<slug>.yaml

All filesystem writes go through ``PathGuard`` (FR-016).
Serialization uses ``canonical_yaml`` from synthesize_pipeline so that
``artifact_content_hash`` computed at assembly time matches the hash of the
bytes written to disk (NFR-006 byte-stability contract).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

from .synthesize_pipeline import ProvenanceEntry, canonical_yaml

if TYPE_CHECKING:
    from .path_guard import PathGuard


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def provenance_path_for(kind: str, slug: str) -> str:
    """Return the repo-relative provenance sidecar path for a given artifact.

    Format: ``.kittify/charter/provenance/<kind>-<slug>.yaml``
    """
    return f".kittify/charter/provenance/{kind}-{slug}.yaml"


def dump_yaml(entry: ProvenanceEntry, path: Path, guard: PathGuard) -> None:
    """Serialize ``entry`` to ``path`` via ``PathGuard.write_text``.

    Uses the same ``canonical_yaml`` serializer that WP02's pipeline uses to
    compute ``artifact_content_hash`` — ensuring byte-parity between the stored
    hash and the on-disk bytes (NFR-006).

    Parameters
    ----------
    entry:
        Fully-assembled ``ProvenanceEntry`` from the synthesis pipeline.
    path:
        Target path (must be within the PathGuard allowlist).
    guard:
        PathGuard instance used for all writes.
    """
    data = entry.model_dump(mode="python")
    yaml_bytes = canonical_yaml(data)
    guard.write_text(
        path,
        yaml_bytes.decode("utf-8"),
        encoding="utf-8",
        caller="provenance.dump_yaml",
    )


def load_yaml(path: Path) -> ProvenanceEntry:
    """Deserialize a provenance sidecar from ``path`` and validate with Pydantic.

    Parameters
    ----------
    path:
        Absolute or repo-relative path to a provenance YAML sidecar.

    Returns
    -------
    ProvenanceEntry
        Validated provenance entry.

    Raises
    ------
    pydantic.ValidationError
        If the YAML content does not match the ProvenanceEntry schema.
    FileNotFoundError
        If ``path`` does not exist.
    """
    yaml = YAML()
    raw = yaml.load(path.read_text(encoding="utf-8"))
    return ProvenanceEntry.model_validate(raw)


__all__ = [
    "dump_yaml",
    "load_yaml",
    "provenance_path_for",
    # Re-export ProvenanceEntry so callers can import from here if convenient.
    "ProvenanceEntry",
]
