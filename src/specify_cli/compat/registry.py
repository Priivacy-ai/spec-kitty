"""Load and validate the shim registry YAML."""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from packaging.version import InvalidVersion, Version
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_DOTTED_NAME = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[a-z]\d+)?$")
_TRACKER = re.compile(r"^(#\d+|https?://.+)$")

_REQUIRED_KEYS = {
    "legacy_path",
    "canonical_import",
    "introduced_in_release",
    "removal_target_release",
    "tracker_issue",
    "grandfathered",
}


@dataclasses.dataclass(frozen=True)
class ShimEntry:
    legacy_path: str
    canonical_import: str | list[str]
    introduced_in_release: str
    removal_target_release: str
    tracker_issue: str
    grandfathered: bool
    extension_rationale: str | None = None
    notes: str | None = None


_SHIM_ENTRY_FIELDS = {field.name for field in dataclasses.fields(ShimEntry)}


class RegistrySchemaError(Exception):
    """Raised when the registry YAML fails schema validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def load_registry(repo_root: Path) -> list[ShimEntry]:
    registry_path = repo_root / "architecture" / "2.x" / "shim-registry.yaml"
    if not registry_path.exists():
        raise FileNotFoundError(f"Shim registry not found at {registry_path}")
    yaml = YAML(typ="safe")
    try:
        with registry_path.open() as fp:
            data = yaml.load(fp)
    except YAMLError as exc:
        raise RegistrySchemaError([f"YAML parse error: {exc}"]) from exc
    validate_registry(data)
    return [
        ShimEntry(**{k: v for k, v in entry.items() if k in _SHIM_ENTRY_FIELDS})
        for entry in data["shims"]
    ]


def _validate_canonical_import(i: int, ci: object, errors: list[str]) -> None:
    if isinstance(ci, str):
        if not _DOTTED_NAME.match(ci):
            errors.append(f"entry[{i}].canonical_import: must be a dotted identifier string")
    elif isinstance(ci, list):
        if not ci:
            errors.append(f"entry[{i}].canonical_import: list must not be empty")
        for j, item in enumerate(ci):
            if not isinstance(item, str) or not _DOTTED_NAME.match(item):
                errors.append(f"entry[{i}].canonical_import[{j}]: must be a dotted identifier string")
    else:
        errors.append(f"entry[{i}].canonical_import: must be a string or list of strings")


def _validate_version_order(i: int, entry: dict[str, object], errors: list[str]) -> None:
    introduced = entry.get("introduced_in_release")
    removal = entry.get("removal_target_release")
    if not (isinstance(introduced, str) and isinstance(removal, str)):
        return
    if not (_SEMVER.match(introduced) and _SEMVER.match(removal)):
        return
    try:
        if Version(removal) < Version(introduced):
            errors.append(f"entry[{i}].removal_target_release: must be >= introduced_in_release")
    except InvalidVersion:
        errors.append(f"entry[{i}]: version strings are not valid semver")


def _validate_legacy_path(i: int, entry: dict[str, object], seen_paths: set[str], errors: list[str]) -> None:
    lp = entry["legacy_path"]
    if not isinstance(lp, str) or not _DOTTED_NAME.match(lp):
        errors.append(f"entry[{i}].legacy_path: must be a dotted identifier string")
    elif lp in seen_paths:
        errors.append(f"entry[{i}].legacy_path: duplicate value '{lp}'")
    else:
        seen_paths.add(lp)


def _validate_optional_fields(i: int, entry: dict[str, object], errors: list[str]) -> None:
    er = entry.get("extension_rationale")
    if er is not None and (not isinstance(er, str) or not er.strip()):
        errors.append(f"entry[{i}].extension_rationale: if present, must be a non-empty string")

    notes = entry.get("notes")
    if notes is not None and not isinstance(notes, str):
        errors.append(f"entry[{i}].notes: if present, must be a string")


def _validate_entry(i: int, entry: object, seen_paths: set[str], errors: list[str]) -> None:
    if not isinstance(entry, dict):
        errors.append(f"entry[{i}]: must be a mapping")
        return

    missing = _REQUIRED_KEYS - set(entry)
    for key in sorted(missing):
        errors.append(f"entry[{i}].{key}: required field is missing")
    if missing:
        return

    _validate_legacy_path(i, entry, seen_paths, errors)
    _validate_canonical_import(i, entry["canonical_import"], errors)

    for field in ("introduced_in_release", "removal_target_release"):
        val = entry[field]
        if not isinstance(val, str) or not _SEMVER.match(val):
            errors.append(f"entry[{i}].{field}: must be a semver string like '1.2.3' or '1.2.3a1'")

    _validate_version_order(i, entry, errors)

    ti = entry["tracker_issue"]
    if not isinstance(ti, str) or not _TRACKER.match(ti):
        errors.append(f"entry[{i}].tracker_issue: must be '#123' or a URL")

    gf = entry["grandfathered"]
    if not isinstance(gf, bool):
        errors.append(f"entry[{i}].grandfathered: must be a boolean (true/false), got {type(gf).__name__}")

    _validate_optional_fields(i, entry, errors)


def validate_registry(data: object) -> None:
    if not isinstance(data, dict) or "shims" not in data:
        raise RegistrySchemaError(["top-level: must be a mapping with a 'shims' key"])
    if not isinstance(data["shims"], list):
        raise RegistrySchemaError(["top-level.shims: must be a list"])

    errors: list[str] = []
    seen_paths: set[str] = set()
    for i, entry in enumerate(data["shims"]):
        _validate_entry(i, entry, seen_paths, errors)

    if errors:
        raise RegistrySchemaError(errors)
