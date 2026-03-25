"""Doctrine catalog loading for deterministic governance validation."""

from __future__ import annotations

import importlib.resources
import logging
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_log = logging.getLogger(__name__)


def _get_package_asset_root() -> Path:
    """Lazy import of specify_cli.runtime.home to avoid circular initialisation.

    ``constitution.catalog`` is imported early in the constitution package, and
    ``specify_cli.__init__`` imports CLI commands that import from constitution.
    A top-level ``from specify_cli.runtime.home import ...`` would trigger
    ``specify_cli.__init__`` while constitution is still partially initialised,
    causing an ImportError.  Deferring the import to call-time breaks the cycle.
    """
    from specify_cli.runtime.home import get_package_asset_root  # noqa: PLC0415

    return get_package_asset_root()


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


def load_doctrine_catalog(*, include_proposed: bool = False) -> DoctrineCatalog:
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

    domains_present: set[str] = set()

    paradigms, paradigms_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "paradigms", "**/*.paradigm.yaml", include_proposed=include_proposed
    )
    if paradigms_present:
        domains_present.add("paradigms")

    directives, directives_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "directives", "**/*.directive.yaml", include_proposed=include_proposed
    )
    if directives_present:
        domains_present.add("directives")

    template_sets, template_sets_present = _load_template_sets_with_presence(doctrine_root)
    if template_sets_present:
        domains_present.add("template_sets")

    tactics, tactics_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "tactics", "**/*.tactic.yaml", include_proposed=include_proposed
    )
    if tactics_present:
        domains_present.add("tactics")

    styleguides, styleguides_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "styleguides", "**/*.styleguide.yaml", include_proposed=include_proposed
    )
    if styleguides_present:
        domains_present.add("styleguides")

    toolguides, toolguides_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "toolguides", "**/*.toolguide.yaml", include_proposed=include_proposed
    )
    if toolguides_present:
        domains_present.add("toolguides")

    procedures, procedures_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "procedures", "**/*.procedure.yaml", include_proposed=include_proposed
    )
    if procedures_present:
        domains_present.add("procedures")

    profiles, profiles_present = _load_yaml_id_catalog_with_presence(
        doctrine_root / "agent_profiles",
        "**/*.agent.yaml",
        id_field="profile-id",
        include_proposed=include_proposed,
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
        directory, pattern, id_field=id_field, include_proposed=include_proposed
    )
    return ids


def _load_yaml_id_catalog_with_presence(
    directory: Path,
    pattern: str,
    *,
    id_field: str = "id",
    include_proposed: bool = False,
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

    shipped_dir = directory / "shipped"
    proposed_dir = directory / "_proposed"
    if shipped_dir.is_dir() or proposed_dir.is_dir():
        # Structured layout: domain is present regardless of content.
        present = True
        scan_roots = [shipped_dir] if shipped_dir.is_dir() else []
        if include_proposed and proposed_dir.is_dir():
            scan_roots.append(proposed_dir)
    else:
        # Preserve generic helper behavior for tests or flat directories.
        present = True
        scan_roots = [directory]

    yaml = YAML(typ="safe")
    ids: set[str] = set()
    for scan_root in scan_roots:
        for path in sorted(scan_root.glob(pattern)):
            try:
                data = yaml.load(path.read_text(encoding="utf-8")) or {}
            except (OSError, YAMLError, TypeError):
                continue

            if isinstance(data, dict):
                raw_id = str(data.get(id_field, "")).strip()
                if raw_id:
                    ids.add(raw_id)
                    continue

            fallback = path.stem.split(".")[0].strip()
            if fallback:
                ids.add(fallback)

    return ids, present


def _load_template_sets(doctrine_root: Path) -> set[str]:
    """Load available template set IDs.

    Template set IDs are derived from bundled missions as ``{mission}-default``.
    """
    template_sets, _ = _load_template_sets_with_presence(doctrine_root)
    return template_sets


def _load_template_sets_with_presence(doctrine_root: Path) -> tuple[set[str], bool]:
    """Load available template set IDs, also reporting domain presence.

    Returns:
        Tuple of (template_sets, present) where ``present`` is ``True`` when the
        missions directory exists.  An empty set with ``present=True`` means no
        mission directories were found — every template-set selection is invalid.
        ``present=False`` means the missions directory is not deployed.
    """
    template_sets: set[str] = set()

    missions_root = doctrine_root / "missions"
    if not missions_root.is_dir():
        try:
            missions_root = _get_package_asset_root()
        except FileNotFoundError:
            missions_root = doctrine_root / "missions"

    if not missions_root.is_dir():
        return template_sets, False

    for mission_dir in sorted(missions_root.iterdir()):
        if mission_dir.is_dir() and (mission_dir / "mission.yaml").is_file():
            template_sets.add(f"{mission_dir.name}-default")

    return template_sets, True
