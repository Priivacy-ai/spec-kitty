"""Migration: heal absolute built-in-pack ``source_path`` provenance to portable tokens.

Companion to the T011/T012/T013 emit-side fix (``charter.offering.provenance.
to_portable_source_path``, routed through ``charter.compiler.
_doctrine_yaml_reference`` and ``specify_cli.tool_surface.profiles.
projection._manifest_source_path``): a project that compiled its charter or
projected its agent-profile manifest *before* that fix committed an
operator-/platform-specific absolute filesystem path for a built-in-pack
source into git (contracts/provenance-and-channel.md C-PRV-4, empirically
real on this very repository -- a Linux path in ``.kittify/charter/
charter.yaml`` and a macOS Homebrew wheel path in
``.kittify/agent_profiles_manifest.json``). This migration rewrites BOTH
carriers' healable entries to the same ``${SPEC_KITTY_PACKS_ROOT}/built-in/...``
token the fixed emit path now produces, so re-running it (or a fresh compile)
converges to zero further changes (C-MIG-1).

**Healable scope, mirroring C-PRV-6's excluded normalizer callers exactly.**
Only entries the FIXED emit path would itself have tokenized are healed:

- Catalog references whose ``kind`` is NOT ``"template_set"`` -- the mission-
  template reference (``charter.compiler._template_reference``) is a
  deliberately excluded normalizer caller (still routes through
  ``_trim_source_path``, which returns a post-relocation mission.yaml path
  UNCHANGED, i.e. still absolute). Healing that entry here would just get
  re-absoluted by the next ``spec-kitty charter generate`` -- oscillation,
  not a fix -- so it is left alone, exactly like the emit-side fix leaves it.
- Manifest entries' ``source_path`` field -- never ``output_path`` (a
  distinct, deliberately excluded carrier that stays repo-relative via
  ``_paths.relativize_under_root``, untouched by this migration).

Within that scope, only paths that ``charter.offering.provenance.is_built_in_pack_path``
classifies as built-in are rewritten -- an out-of-tree absolute source (a
legitimate, if unusual, local-support/org override) is preserved as-is,
matching the normalizer's own class-(c) behaviour.

**``target_version`` vs. the ``m_3_2_7_...`` filename (deliberately not the
same number).** Mirrors ``m_3_2_7_review_cycle_merge_driver.py``'s own
documented precedent for exactly this situation: this module is named
``m_3_2_7_...`` (the WP's prescribed filename/migration id), but
``target_version`` is pinned to the CURRENT installed package version
(``"3.2.6rc2"`` at authoring time) rather than the unreleased ``"3.2.7"`` --
``spec-kitty upgrade``/``test_discovered_migration_targets_do_not_exceed_
package_version`` skip/flag any migration whose ``target_version`` exceeds
the installed package version, so targeting ``"3.2.7"`` literally would mean
this migration silently never runs (and would fail that architectural gate)
until a release actually reaches 3.2.7. Distinct from WP04's provision
migration target ``"3.2.8"`` either way -- heal and provision are
independently ordered, heal is not gated on the sync-consent axis WP04 owns.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING, Any

from charter.bundle import CHARTER_YAML
from charter.provenance import is_built_in_pack_path, to_portable_source_path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

if TYPE_CHECKING:
    from specify_cli.tool_surface.model import NativeAgentProfile

MIGRATION_ID = "3.2.7_heal_provenance_paths"
TARGET_VERSION = "3.2.6rc2"

#: Not a charter-bundle path (that authority is ``charter.bundle.CHARTER_YAML``,
#: imported above for :func:`_charter_yaml_path`) -- this is the unrelated
#: top-level ``.kittify/agent_profiles_manifest.json`` sidecar's own dirname.
_KITTIFY_DIRNAME = ".kittify"
_MANIFEST_FILENAME = "agent_profiles_manifest.json"

#: Catalog reference kind excluded from healing -- mirrors C-PRV-6's excluded
#: normalizer caller, ``_template_reference``. See the module docstring.
_EXCLUDED_CATALOG_KIND = "template_set"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _charter_yaml_path(project_path: Path) -> Path:
    # The ``charter.*`` mypy override (pyproject.toml [[tool.mypy.overrides]])
    # sets follow_imports="skip" for intra-package imports, which erases
    # CHARTER_YAML's declared ``Path`` type to Any at this call site.
    # Annotating recovers the real type without a suppression comment (mirrors
    # charter/bundle.py's own compute_bundle_content_hash precedent).
    charter_yaml_path: Path = project_path / CHARTER_YAML
    return charter_yaml_path


def _manifest_path(project_path: Path) -> Path:
    return project_path / _KITTIFY_DIRNAME / _MANIFEST_FILENAME


# ---------------------------------------------------------------------------
# Catalog (charter.yaml) side
# ---------------------------------------------------------------------------


def _catalog_references(charter_path: Path) -> list[dict[str, Any]]:
    """Return ``catalog.references`` from *charter_path*, or ``[]`` when unavailable."""
    if not charter_path.exists():
        return []

    from charter.charter_yaml_io import load_charter_yaml  # noqa: PLC0415 -- lazy (C-002)

    document = load_charter_yaml(charter_path)
    catalog = document.get("catalog") if hasattr(document, "get") else None
    if not isinstance(catalog, dict):
        return []
    references = catalog.get("references")
    return references if isinstance(references, list) else []


def _catalog_ref_is_healable(ref: Any) -> bool:
    if not isinstance(ref, dict) or ref.get("kind") == _EXCLUDED_CATALOG_KIND:
        return False
    source_path = ref.get("source_path")
    if not isinstance(source_path, str) or not source_path or not Path(source_path).is_absolute():
        return False

    return is_built_in_pack_path(source_path)


def _healable_catalog_refs(charter_path: Path) -> list[dict[str, Any]]:
    return [ref for ref in _catalog_references(charter_path) if _catalog_ref_is_healable(ref)]


def _heal_catalog(project_path: Path, charter_path: Path, dry_run: bool) -> list[str]:
    """Rewrite healable catalog ``source_path`` entries to tokens; return change log lines."""
    healable = _healable_catalog_refs(charter_path)
    if not healable:
        return []

    from charter.charter_yaml_io import load_charter_yaml, update_charter_yaml_section  # noqa: PLC0415

    changes: list[str] = []
    document = load_charter_yaml(charter_path)
    catalog = document["catalog"]
    for ref in catalog.get("references", []):
        if not _catalog_ref_is_healable(ref):
            continue
        old_value = ref["source_path"]
        new_value = to_portable_source_path(old_value, project_root=project_path)
        changes.append(f"charter.yaml catalog[{ref.get('id', '?')}].source_path: {old_value} -> {new_value}")
        if not dry_run:
            ref["source_path"] = new_value

    if changes and not dry_run:
        update_charter_yaml_section(charter_path, "catalog", catalog)

    return changes


# ---------------------------------------------------------------------------
# Manifest (agent_profiles_manifest.json) side
# ---------------------------------------------------------------------------


def _manifest_entry_is_healable(entry: NativeAgentProfile) -> bool:
    source_path = entry.source_path
    if not source_path or not Path(source_path).is_absolute():
        return False

    return is_built_in_pack_path(source_path)


def _healable_manifest_entries(project_path: Path) -> list[NativeAgentProfile]:
    manifest_path = _manifest_path(project_path)
    if not manifest_path.exists():
        return []

    from specify_cli.tool_surface.profiles.manifest import ProfileManifest  # noqa: PLC0415

    manifest = ProfileManifest.load(project_path)
    return [entry for entry in manifest.all_entries() if _manifest_entry_is_healable(entry)]


def _heal_manifest(project_path: Path, dry_run: bool) -> list[str]:
    """Rewrite healable manifest ``source_path`` entries to tokens; return change log lines."""
    healable = _healable_manifest_entries(project_path)
    if not healable:
        return []

    from specify_cli.tool_surface.profiles.manifest import ProfileManifest  # noqa: PLC0415

    changes: list[str] = []
    manifest = ProfileManifest.load(project_path)
    for entry in healable:
        old_value = entry.source_path
        # ``_manifest_entry_is_healable`` already rejected a None/empty
        # source_path, but that narrowing does not cross the function
        # boundary for mypy -- assert it back for the type checker.
        assert old_value is not None
        new_value = to_portable_source_path(old_value, project_root=project_path)
        changes.append(f"agent_profiles_manifest.json[{entry.profile_urn}/{entry.tool_key}].source_path: {old_value} -> {new_value}")
        if not dry_run:
            manifest.record(dataclasses.replace(entry, source_path=new_value))

    if changes and not dry_run:
        manifest.save()

    return changes


# ---------------------------------------------------------------------------
# Leak reporting (shared with the ``doctor provenance`` sibling, T015)
# ---------------------------------------------------------------------------


def describe_leaks(project_path: Path) -> list[str]:
    """Return a human-readable description of every healable leak, read-only.

    The single source of truth ``cli.commands._provenance_doctor``'s
    ``doctor provenance`` leak-check reads from -- reusing exactly the same
    classification :meth:`HealProvenancePathsMigration.detect` uses so a
    leak the doctor flags is always one ``apply()`` (or a fresh compile)
    would actually fix, and vice versa. Never mutates anything.
    """
    charter_path = _charter_yaml_path(project_path)
    descriptions = [
        f"charter.yaml catalog[{ref.get('id', '?')}].source_path={ref.get('source_path')!r}"
        for ref in _healable_catalog_refs(charter_path)
    ]
    descriptions.extend(
        f"agent_profiles_manifest.json[{entry.profile_urn}/{entry.tool_key}]"
        f".source_path={entry.source_path!r}"
        for entry in _healable_manifest_entries(project_path)
    )
    return descriptions


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


@MigrationRegistry.register
class HealProvenancePathsMigration(BaseMigration):
    """Heal absolute built-in-pack ``source_path`` provenance to portable tokens (C-PRV-4)."""

    migration_id = MIGRATION_ID
    description = (
        "Rewrite absolute built-in-pack source_path entries in charter.yaml's "
        "catalog and agent_profiles_manifest.json to portable "
        "${SPEC_KITTY_PACKS_ROOT}/built-in/... tokens (mission-template and "
        "output_path excluded, byte-preserved)."
    )
    target_version = TARGET_VERSION
    runs_on_worktrees = False

    def detect(self, project_path: Path) -> bool:
        return bool(
            _healable_catalog_refs(_charter_yaml_path(project_path))
            or _healable_manifest_entries(project_path)
        )

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if self.detect(project_path):
            return True, ""
        return (
            False,
            "no absolute built-in-pack source_path found in charter.yaml's "
            "catalog or agent_profiles_manifest.json",
        )

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        charter_path = _charter_yaml_path(project_path)
        changes = _heal_catalog(project_path, charter_path, dry_run)
        changes.extend(_heal_manifest(project_path, dry_run))
        return MigrationResult(success=True, changes_made=changes)
