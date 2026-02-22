"""Doctrine catalog loading for deterministic governance validation."""

from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

from specify_cli.runtime.home import get_package_asset_root


DEFAULT_TEMPLATE_SET = "software-dev-default"


@dataclass(frozen=True)
class DoctrineCatalog:
    """Deterministic doctrine catalog derived from on-disk doctrine assets."""

    paradigms: frozenset[str]
    directives: frozenset[str]
    template_sets: frozenset[str]


def load_doctrine_catalog() -> DoctrineCatalog:
    """Load doctrine catalogs from package assets with development fallbacks."""
    doctrine_root = _resolve_doctrine_root()
    paradigms = _load_yaml_id_catalog(doctrine_root / "paradigms", "*.paradigm.yaml")
    directives = _load_yaml_id_catalog(doctrine_root / "directives", "*.directive.yaml")
    template_sets = _load_template_sets(doctrine_root)

    if not template_sets:
        template_sets = {DEFAULT_TEMPLATE_SET}

    return DoctrineCatalog(
        paradigms=frozenset(sorted(paradigms)),
        directives=frozenset(sorted(directives)),
        template_sets=frozenset(sorted(template_sets)),
    )


def _resolve_doctrine_root() -> Path:
    """Resolve the doctrine package root in installed and dev layouts."""
    try:
        doctrine_pkg = importlib.resources.files("doctrine")
        doctrine_root = Path(str(doctrine_pkg))
        if doctrine_root.is_dir():
            return doctrine_root
    except (ModuleNotFoundError, TypeError):
        pass

    dev_root = Path(__file__).parent.parent.parent / "doctrine"
    if dev_root.is_dir():
        return dev_root

    raise FileNotFoundError("Cannot locate doctrine root. Ensure doctrine assets are packaged.")


def _load_yaml_id_catalog(directory: Path, pattern: str) -> set[str]:
    """Load `id` values from doctrine YAML files in a directory."""
    if not directory.is_dir():
        return set()

    yaml = YAML(typ="safe")
    ids: set[str] = set()
    for path in sorted(directory.glob(pattern)):
        try:
            data = yaml.load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue

        if isinstance(data, dict):
            raw_id = str(data.get("id", "")).strip()
            if raw_id:
                ids.add(raw_id)
                continue

        fallback = path.stem.split(".")[0].strip()
        if fallback:
            ids.add(fallback)

    return ids


def _load_template_sets(doctrine_root: Path) -> set[str]:
    """Load available template set IDs.

    Template set IDs are derived from bundled missions as `{mission}-default`.
    """
    template_sets: set[str] = set()

    missions_root = doctrine_root / "missions"
    if not missions_root.is_dir():
        try:
            missions_root = get_package_asset_root()
        except FileNotFoundError:
            missions_root = doctrine_root / "missions"

    if missions_root.is_dir():
        for mission_dir in sorted(missions_root.iterdir()):
            if mission_dir.is_dir() and (mission_dir / "mission.yaml").is_file():
                template_sets.add(f"{mission_dir.name}-default")

    return template_sets
