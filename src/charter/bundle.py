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

Extended in WP03 (FR-015): ``validate_synthesis_state`` cross-checks the
synthesis state added by the charter synthesizer (provenance sidecars,
synthesis manifest).  This extension is **additive only** — no schema version
bump, legacy bundles without synthesis state pass exactly as they did under
v1.0.0 (C-012 backward-compat guarantee, see ``BundleValidationResult``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION: str = "1.0.0"
CHARTER_MD = Path(".kittify/charter/charter.md")
GOVERNANCE_YAML = Path(".kittify/charter/governance.yaml")
DIRECTIVES_YAML = Path(".kittify/charter/directives.yaml")
METADATA_YAML = Path(".kittify/charter/metadata.yaml")

# Synthesis state paths (all relative to repo root)
SYNTHESIS_MANIFEST_PATH = Path(".kittify/charter/synthesis-manifest.yaml")
PROVENANCE_DIR = Path(".kittify/charter/provenance")
DOCTRINE_DIR = Path(".kittify/doctrine")
STAGING_DIR = Path(".kittify/charter/.staging")

# Artifact file-extension suffixes for each kind
_KIND_SUFFIX: dict[str, str] = {
    "directive": ".directive.yaml",
    "tactic": ".tactic.yaml",
    "styleguide": ".styleguide.yaml",
}
_ALL_ARTIFACT_PATTERNS = list(_KIND_SUFFIX.values())


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


# ---------------------------------------------------------------------------
# WP03 (FR-015): Synthesis state validation extension
# ---------------------------------------------------------------------------


@dataclass
class BundleValidationResult:
    """Result of ``validate_synthesis_state()``.

    Backward-compat guarantee (C-012):
    - ``errors`` is always an empty list when no synthesis state exists.
    - ``warnings`` may mention stale ``.failed/`` staging dirs.
    - ``synthesis_state_present`` is ``False`` for legacy bundles.
    """

    synthesis_state_present: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True when there are no errors (warnings are non-blocking)."""
        return len(self.errors) == 0


def validate_synthesis_state(repo_root: Path) -> BundleValidationResult:
    """Validate the synthesis state of a project bundle.

    Checks (additive — legacy bundles without synthesis state pass unchanged):

    1. Every artifact file under ``.kittify/doctrine/`` has a provenance sidecar
       at ``.kittify/charter/provenance/<kind>-<slug>.yaml``.
    2. Every provenance sidecar references an existing artifact file.
    3. If ``.kittify/charter/synthesis-manifest.yaml`` is present, verify all
       listed ``content_hash`` values against on-disk bytes.
    4. Stale ``.kittify/charter/.staging/<runid>.failed/`` directories produce
       a warning (not an error) — R-7 accumulation signal (quickstart §8).

    Parameters
    ----------
    repo_root:
        Absolute path to the repository root.

    Returns
    -------
    BundleValidationResult
        Structured result containing errors, warnings, and a flag indicating
        whether any synthesis state was found at all.
    """
    result = BundleValidationResult()
    _check_stale_failed_dirs(repo_root, result)

    doctrine_root = repo_root / DOCTRINE_DIR
    if not doctrine_root.exists():
        return result

    artifact_files = _collect_artifact_files(doctrine_root)
    if not artifact_files and not (repo_root / PROVENANCE_DIR).exists():
        return result

    result.synthesis_state_present = True
    provenance_root = repo_root / PROVENANCE_DIR

    _check_artifacts_have_provenance(repo_root, artifact_files, provenance_root, result)
    _check_provenance_have_artifacts(repo_root, doctrine_root, provenance_root, result)
    _check_manifest_integrity(repo_root, result)
    return result


def _check_stale_failed_dirs(repo_root: Path, result: BundleValidationResult) -> None:
    """Warn on stale .failed/ staging directories (R-7)."""
    staging_root = repo_root / STAGING_DIR
    if not staging_root.exists():
        return
    for d in sorted(staging_root.iterdir()):
        if d.name.endswith(".failed") and d.is_dir():
            result.warnings.append(
                f"Stale failed staging directory found: {d.relative_to(repo_root)} "
                "(inspect cause.yaml, then remove to suppress this warning)"
            )


def _collect_artifact_files(doctrine_root: Path) -> list[Path]:
    """Collect all synthesized artifact files under the doctrine root."""
    files: list[Path] = []
    for suffix in _ALL_ARTIFACT_PATTERNS:
        files.extend(doctrine_root.rglob(f"*{suffix}"))
    return files


def _check_artifacts_have_provenance(
    repo_root: Path,
    artifact_files: list[Path],
    provenance_root: Path,
    result: BundleValidationResult,
) -> None:
    """Step 1: every artifact file must have a provenance sidecar."""
    for artifact_path in sorted(artifact_files):
        kind, slug = _kind_and_slug_from_artifact(artifact_path)
        if kind is None or slug is None:
            continue
        expected_prov = provenance_root / f"{kind}-{slug}.yaml"
        if not expected_prov.exists():
            result.errors.append(
                f"Artifact '{artifact_path.relative_to(repo_root)}' has no provenance sidecar "
                f"(expected: {expected_prov.relative_to(repo_root)})"
            )


def _check_provenance_have_artifacts(
    repo_root: Path,
    doctrine_root: Path,
    provenance_root: Path,
    result: BundleValidationResult,
) -> None:
    """Step 2: every provenance sidecar must reference an existing artifact."""
    if not provenance_root.exists():
        return
    for prov_file in sorted(provenance_root.glob("*.yaml")):
        stem = prov_file.stem  # e.g. "directive-my-slug"
        parts = stem.split("-", 1)
        if len(parts) != 2:
            result.errors.append(
                f"Provenance file has unexpected name format: {prov_file.relative_to(repo_root)}"
            )
            continue
        kind, slug = parts[0], parts[1]
        if kind not in _KIND_SUFFIX:
            result.errors.append(
                f"Provenance file has unknown kind '{kind}': {prov_file.relative_to(repo_root)}"
            )
            continue
        if _find_artifact(doctrine_root, kind, slug) is None:
            result.errors.append(
                f"Provenance sidecar '{prov_file.relative_to(repo_root)}' references "
                f"non-existent artifact (kind={kind}, slug={slug})"
            )


def _check_manifest_integrity(repo_root: Path, result: BundleValidationResult) -> None:
    """Step 3: verify synthesis manifest content hashes if manifest is present."""
    manifest_path = repo_root / SYNTHESIS_MANIFEST_PATH
    if not manifest_path.exists():
        return
    try:
        from .synthesizer.manifest import (  # noqa: PLC0415
            load_yaml as load_manifest,
            verify as verify_manifest,
        )
        manifest = load_manifest(manifest_path)
        try:
            verify_manifest(manifest, repo_root)
        except Exception as exc:
            result.errors.append(f"Synthesis manifest integrity check failed: {exc}")
    except Exception as exc:
        result.errors.append(f"Could not load synthesis manifest: {exc}")


def _kind_and_slug_from_artifact(path: Path) -> tuple[str | None, str | None]:
    """Extract (kind, slug) from an artifact filename.

    Returns ``(None, None)`` if the file does not match any known pattern.
    """
    name = path.name
    for kind, suffix in _KIND_SUFFIX.items():
        if name.endswith(suffix):
            base = name[: -len(suffix)]
            # For directives: "<NNN>-<slug>" → slug is everything after the first dash+digits
            if kind == "directive":
                # Strip leading "<NNN>-" prefix if present
                parts = base.split("-", 1)
                slug = parts[1] if len(parts) == 2 and parts[0].isdigit() else base
            else:
                slug = base
            return kind, slug
    return None, None


def _find_artifact(doctrine_root: Path, kind: str, slug: str) -> Path | None:
    """Find the artifact file for a given (kind, slug) under doctrine_root."""
    suffix = _KIND_SUFFIX.get(kind)
    if suffix is None:
        return None
    for candidate in doctrine_root.rglob(f"*{suffix}"):
        cand_kind, cand_slug = _kind_and_slug_from_artifact(candidate)
        if cand_kind == kind and cand_slug == slug:
            return candidate
    return None


__all__ = [
    "CANONICAL_MANIFEST",
    "CharterBundleManifest",
    "SCHEMA_VERSION",
    # WP03 extension (FR-015)
    "BundleValidationResult",
    "validate_synthesis_state",
]
