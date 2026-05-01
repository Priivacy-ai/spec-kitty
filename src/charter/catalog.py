"""Doctrine catalog loading for deterministic governance validation."""

from __future__ import annotations

import importlib.resources
import logging
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from doctrine.shared.scoping import applies_to_languages_match, normalize_languages
from kernel.paths import get_package_asset_root as _get_package_asset_root

_log = logging.getLogger(__name__)


DEFAULT_TEMPLATE_SET = "software-dev-default"


@dataclass(frozen=True)
class DoctrineCatalog:
    """Deterministic doctrine catalog derived from on-disk doctrine assets.

    ``domains_present`` records which shipped-artifact domains have a ``shipped/``
    subdirectory on disk.  A domain that is present but has an empty ``shipped/``
    directory contributes an *empty* frozenset to the corresponding field — which
    means every selection against that domain is invalid.  A domain that is
    completely absent (directory does not exist) is *not* included in
    ``domains_present``, and the resolver should skip validation for it.
    """

    paradigms: frozenset[str]
    directives: frozenset[str]
    template_sets: frozenset[str]
    tactics: frozenset[str]
    styleguides: frozenset[str]
    toolguides: frozenset[str]
    procedures: frozenset[str]
    agent_profiles: frozenset[str]
    domains_present: frozenset[str] = frozenset()


def load_doctrine_catalog(
    *,
    include_proposed: bool = False,
    active_languages: list[str] | tuple[str, ...] | None = None,
) -> DoctrineCatalog:
    """Load doctrine catalogs from package assets with development fallbacks.

    By default, only canonised ``shipped/`` artifacts participate in the catalog.
    Callers may opt into ``_proposed/`` artifacts explicitly to support curation
    flows that need visibility into pre-canonisation content.

    ``DoctrineCatalog.domains_present`` records which artifact domains have a
    ``shipped/`` directory on disk.  The resolver uses this to distinguish between
    "domain not deployed in this install" (safe to skip validation) and "domain
    present but shipped set is empty" (every selection is invalid).
    """
    doctrine_root = resolve_doctrine_root()
    normalized_languages = None if active_languages is None else normalize_languages(active_languages)

    domains_present: set[str] = set()

    paradigms, paradigms_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "paradigms",
        "**/*.paradigm.yaml",
        include_proposed=include_proposed,
        active_languages=normalized_languages,
    )
    if paradigms_present:
        domains_present.add("paradigms")

    directives, directives_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "directives",
        "**/*.directive.yaml",
        include_proposed=include_proposed,
        active_languages=normalized_languages,
    )
    if directives_present:
        domains_present.add("directives")

    template_sets, template_sets_present = _load_template_sets_with_presence(doctrine_root)
    if template_sets_present:
        domains_present.add("template_sets")

    tactics, tactics_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "tactics",
        "**/*.tactic.yaml",
        include_proposed=include_proposed,
        active_languages=normalized_languages,
    )
    if tactics_present:
        domains_present.add("tactics")

    styleguides, styleguides_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "styleguides",
        "**/*.styleguide.yaml",
        include_proposed=include_proposed,
        active_languages=normalized_languages,
    )
    if styleguides_present:
        domains_present.add("styleguides")

    toolguides, toolguides_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "toolguides",
        "**/*.toolguide.yaml",
        include_proposed=include_proposed,
        active_languages=normalized_languages,
    )
    if toolguides_present:
        domains_present.add("toolguides")

    procedures, procedures_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "procedures",
        "**/*.procedure.yaml",
        include_proposed=include_proposed,
        active_languages=normalized_languages,
    )
    if procedures_present:
        domains_present.add("procedures")

    profiles, profiles_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "agent_profiles",
        "**/*.agent.yaml",
        id_field="profile-id",
        include_proposed=include_proposed,
        active_languages=normalized_languages,
    )
    if profiles_present:
        domains_present.add("agent_profiles")

    return DoctrineCatalog(
        paradigms=frozenset(sorted(paradigms)),
        directives=frozenset(sorted(directives)),
        template_sets=frozenset(sorted(template_sets)),
        tactics=frozenset(sorted(tactics)),
        styleguides=frozenset(sorted(styleguides)),
        toolguides=frozenset(sorted(toolguides)),
        procedures=frozenset(sorted(procedures)),
        agent_profiles=frozenset(sorted(profiles)),
        domains_present=frozenset(sorted(domains_present)),
    )


def resolve_doctrine_root() -> Path:
    """Resolve the doctrine package root in installed and development layouts."""
    try:
        doctrine_pkg = importlib.resources.files("doctrine")
        doctrine_root = Path(str(doctrine_pkg))
        if doctrine_root.is_dir():
            return doctrine_root
    except (ModuleNotFoundError, TypeError):
        _log.debug("doctrine: importlib.resources lookup failed, trying dev layout")

    dev_root = Path(__file__).parent.parent.parent / "doctrine"
    if dev_root.is_dir():
        _log.debug("doctrine: resolved via dev layout at %s", dev_root)
        return dev_root

    # 3. Installed layout: doctrine is not a separate package on PyPI.
    #    Fall back to the specify_cli package root so that callers can still
    #    discover missions/ (via get_package_asset_root) and receive empty
    #    sets for paradigms/directives which don't ship in the wheel.
    try:
        result = _get_package_asset_root().parent
        _log.debug("doctrine: resolved via package asset root fallback")
        return result
    except FileNotFoundError:
        pass

    raise FileNotFoundError("Cannot locate doctrine root. Ensure doctrine assets are packaged.")


# Backward-compatible alias for existing private callers.
def _resolve_doctrine_root() -> Path:
    return resolve_doctrine_root()


def _load_yaml_id_catalog(
    directory: Path,
    pattern: str,
    *,
    id_field: str = "id",
    include_proposed: bool = False,
    active_languages: list[str] | tuple[str, ...] | None = None,
) -> set[str]:
    """Load ID values from doctrine YAML files in a directory.

    Args:
        directory: Artifact root directory to search.
        pattern: Glob pattern (supports ``**`` for recursive search).
        id_field: YAML key containing the artifact ID. Defaults to ``"id"``.
                  Use ``"profile-id"`` for agent profile files.
        include_proposed: Whether `_proposed/` artifacts should be included in
                  addition to `shipped/` artifacts. Defaults to shipped-only.
    """
    ids, _ = _load_yaml_id_catalog_with_presence(
        directory,
        pattern,
        id_field=id_field,
        include_proposed=include_proposed,
        active_languages=active_languages,
    )
    return ids


def _extract_artifact_id(
    path: Path,
    id_field: str,
    active_languages: list[str] | tuple[str, ...] | None,
    yaml: object,
) -> str | None:
    """Return the artifact ID from a single YAML file, or None to skip."""
    try:
        data = yaml.load(path.read_text(encoding="utf-8")) or {}  # type: ignore[attr-defined]
    except (OSError, YAMLError, TypeError):
        return None
    if isinstance(data, dict) and not applies_to_languages_match(data.get("applies_to_languages"), active_languages):
        return None
    if isinstance(data, dict):
        raw_id = str(data.get(id_field, "")).strip()
        if raw_id:
            return raw_id
    fallback = path.stem.split(".")[0].strip()
    return fallback or None


def _collect_ids_from_roots(
    scan_roots: list[Path],
    pattern: str,
    id_field: str,
    active_languages: list[str] | tuple[str, ...] | None = None,
) -> set[str]:
    """Collect artifact IDs from one or more scan roots.

    Args:
        scan_roots: Directories to scan (shipped/ and/or _proposed/).
        pattern: Glob pattern for artifact files (supports ``**``).
        id_field: YAML key containing the artifact ID.

    Returns:
        Set of discovered IDs (falls back to stem when YAML id_field is absent).
    """
    yaml = YAML(typ="safe")
    ids: set[str] = set()
    for scan_root in scan_roots:
        for path in sorted(scan_root.glob(pattern)):
            artifact_id = _extract_artifact_id(path, id_field, active_languages, yaml)
            if artifact_id:
                ids.add(artifact_id)
    return ids


def _resolve_scan_roots(
    directory: Path,
    *,
    include_proposed: bool,
) -> tuple[list[Path], bool]:
    """Determine which subdirectories to scan and whether the domain is present.

    Returns:
        Tuple of (scan_roots, present).  ``present`` is ``True`` whenever the
        shipped/ or _proposed/ subdirectory exists, or the directory itself is
        a valid flat layout.
    """
    shipped_dir = directory / "shipped"
    proposed_dir = directory / "_proposed"
    if shipped_dir.is_dir() or proposed_dir.is_dir():
        scan_roots = [shipped_dir] if shipped_dir.is_dir() else []
        if include_proposed and proposed_dir.is_dir():
            scan_roots.append(proposed_dir)
        return scan_roots, True

    # Preserve generic helper behavior for tests or flat directories.
    return [directory], True


def _load_yaml_id_catalog_with_presence(
    directory: Path,
    pattern: str,
    *,
    id_field: str = "id",
    include_proposed: bool = False,
    active_languages: list[str] | tuple[str, ...] | None = None,
) -> tuple[set[str], bool]:
    """Load ID values from doctrine YAML files, also reporting domain presence.

    Returns:
        Tuple of (ids, present) where ``present`` is ``True`` when the artifact
        directory exists and has a recognisable ``shipped/`` or flat layout.
        A ``True`` ``present`` value with an empty id set means the shipped
        catalog is explicitly empty — every selection against this domain is
        invalid.  A ``False`` ``present`` value means the domain is not
        deployed in this install and validation should be skipped.

    Args:
        directory: Artifact root directory to search.
        pattern: Glob pattern (supports ``**`` for recursive search).
        id_field: YAML key containing the artifact ID. Defaults to ``"id"``.
                  Use ``"profile-id"`` for agent profile files.
        include_proposed: Whether `_proposed/` artifacts should be included in
                  addition to ``shipped/`` artifacts. Defaults to shipped-only.
    """
    if not directory.is_dir():
        return set(), False

    scan_roots, present = _resolve_scan_roots(directory, include_proposed=include_proposed)
    ids = _collect_ids_from_roots(
        scan_roots,
        pattern,
        id_field,
        active_languages,
    )
    return ids, present


def _load_template_sets(doctrine_root: Path) -> set[str]:
    """Load available template set IDs.

    Template set IDs are derived from bundled missions as ``{mission}-default``.
    """
    template_sets, _ = _load_template_sets_with_presence(doctrine_root)
    return template_sets


def _load_template_sets_with_presence(_doctrine_root: Path) -> tuple[set[str], bool]:
    """Load available template set IDs, also reporting domain presence.

    Returns:
        Tuple of (template_sets, present) where ``present`` is ``True`` when the
        missions directory exists.  An empty set with ``present=True`` means no
        mission directories were found — every template-set selection is invalid.
        ``present=False`` means the missions directory is not deployed.
    """
    from doctrine.missions import MissionTemplateRepository

    repo = MissionTemplateRepository.default()
    mission_names = repo.list_missions()

    if not mission_names and not repo._missions_root.is_dir():
        return set(), False

    template_sets = {f"{name}-default" for name in mission_names}
    return template_sets, True
