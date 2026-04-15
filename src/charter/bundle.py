"""Unified charter bundle manifest (v1.0.0).

Declares the files ``src/charter/sync.py :: sync()`` materializes as the
project's governance bundle. v1.0.0 scope is limited to the three
sync-produced derivatives. See
``architecture/2.x/06_unified_charter_bundle.md`` for the full contract and
``kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/bundle-manifest.schema.yaml``
for the JSON Schema.

Out of v1.0.0 scope (per C-012):

* ``references.yaml`` — produced by ``src/charter/compiler.py``.
* ``context-state.json`` — runtime state written by
  ``src/charter/context.py :: build_charter_context``.

Expanding the manifest requires a schema bump and a new migration; the
project ``.gitignore`` MAY carry additional entries for those files.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION: str = "1.0.0"
CHARTER_MD = Path(".kittify/charter/charter.md")
GOVERNANCE_YAML = Path(".kittify/charter/governance.yaml")
DIRECTIVES_YAML = Path(".kittify/charter/directives.yaml")
METADATA_YAML = Path(".kittify/charter/metadata.yaml")


class CharterBundleManifest(BaseModel):
    """Typed declaration of the unified charter bundle contract."""

    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    tracked_files: list[Path] = Field(min_length=1)
    derived_files: list[Path]
    derivation_sources: dict[Path, Path]
    gitignore_required_entries: list[str]

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _validate(self) -> CharterBundleManifest:
        # No path may appear in both tracked and derived.
        tracked = set(self.tracked_files)
        derived = set(self.derived_files)
        overlap = tracked & derived
        if overlap:
            raise ValueError(
                f"Paths appear in both tracked and derived: {sorted(str(p) for p in overlap)}"
            )
        # Every key in derivation_sources must appear in derived_files.
        missing_keys = set(self.derivation_sources.keys()) - derived
        if missing_keys:
            raise ValueError(
                "derivation_sources keys not in derived_files: "
                f"{sorted(str(p) for p in missing_keys)}"
            )
        # Every value in derivation_sources must appear in tracked_files.
        missing_values = set(self.derivation_sources.values()) - tracked
        if missing_values:
            raise ValueError(
                "derivation_sources values not in tracked_files: "
                f"{sorted(str(p) for p in missing_values)}"
            )
        return self


CANONICAL_MANIFEST: CharterBundleManifest = CharterBundleManifest(
    schema_version=SCHEMA_VERSION,
    tracked_files=[CHARTER_MD],
    derived_files=[
        GOVERNANCE_YAML,
        DIRECTIVES_YAML,
        METADATA_YAML,
    ],
    derivation_sources={
        GOVERNANCE_YAML: CHARTER_MD,
        DIRECTIVES_YAML: CHARTER_MD,
        METADATA_YAML: CHARTER_MD,
    },
    gitignore_required_entries=[
        str(DIRECTIVES_YAML),
        str(GOVERNANCE_YAML),
        str(METADATA_YAML),
    ],
)


__all__ = [
    "CANONICAL_MANIFEST",
    "CharterBundleManifest",
    "SCHEMA_VERSION",
]
