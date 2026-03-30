"""Consistency checks for doctrine procedure artifacts.

Cross-reference / linking checks apply to **shipped** procedures only.
_proposed procedures are work-in-progress and may reference artifacts that do not
yet exist.  Only schema-syntactic checks run across both shipped and _proposed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema
from ruamel.yaml import YAML
import pytest
pytestmark = [pytest.mark.fast, pytest.mark.doctrine]



REPO_ROOT = Path(__file__).resolve().parents[2]
DOCTRINE_ROOT = REPO_ROOT / "src" / "doctrine"
SCHEMA_PATH = DOCTRINE_ROOT / "schemas" / "procedure.schema.yaml"

_SCAN_SUBDIRS = ("shipped", "_proposed")
_PROCEDURE_DIRS = [DOCTRINE_ROOT / "procedures" / subdir for subdir in _SCAN_SUBDIRS]
# Cross-reference checks only apply to shipped artifacts.
_SHIPPED_PROCEDURE_DIRS = [DOCTRINE_ROOT / "procedures" / "shipped"]
_TEMPLATES_DIR = DOCTRINE_ROOT / "templates"


def _multi_glob(dirs: list[Path], pattern: str) -> list[Path]:
    results: list[Path] = []
    for directory in dirs:
        if directory.exists():
            results.extend(directory.glob(pattern))
    return sorted(set(results))


def _load_yaml(path: Path) -> dict[str, Any]:
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.load(handle) or {}
    assert isinstance(data, dict), f"{path}: expected mapping root"
    return data


def _shipped_ids(artifact_type: str, pattern: str) -> set[str]:
    base = DOCTRINE_ROOT / artifact_type / "shipped"
    ids: set[str] = set()
    if not base.exists():
        return ids

    for path in base.glob(pattern):
        payload = _load_yaml(path)
        artifact_id = str(payload.get("id", "")).strip()
        if artifact_id:
            ids.add(artifact_id)
    return ids


def _shipped_template_ids() -> set[str]:
    ids: set[str] = set()
    if not _TEMPLATES_DIR.exists():
        return ids

    for path in _TEMPLATES_DIR.glob("**/*.md"):
        if path.is_dir():
            continue
        if any(part.startswith(".") for part in path.relative_to(_TEMPLATES_DIR).parts):
            continue
        ids.add(path.stem.replace(".", "-"))
    return ids


def test_procedure_files_validate_against_schema() -> None:
    schema = _load_yaml(SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema)

    for path in _multi_glob(_PROCEDURE_DIRS, "*.procedure.yaml"):
        payload = _load_yaml(path)
        errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
        assert not errors, f"Schema validation failed for {path.name}: {[err.message for err in errors]}"


def test_procedure_references_resolve_to_shipped_artifacts() -> None:
    """All references in shipped procedures must resolve to shipped artifacts.

    _proposed procedures are excluded — they may reference artifacts not yet shipped.
    """
    id_map = {
        "directive": _shipped_ids("directives", "*.directive.yaml"),
        "tactic": _shipped_ids("tactics", "*.tactic.yaml"),
        "styleguide": _shipped_ids("styleguides", "**/*.styleguide.yaml"),
        "toolguide": _shipped_ids("toolguides", "*.toolguide.yaml"),
        "paradigm": _shipped_ids("paradigms", "*.paradigm.yaml"),
        "procedure": _shipped_ids("procedures", "*.procedure.yaml"),
        "template": _shipped_template_ids(),
    }

    unresolved: list[str] = []
    for path in _multi_glob(_SHIPPED_PROCEDURE_DIRS, "*.procedure.yaml"):
        payload = _load_yaml(path)
        procedure_id = str(payload.get("id", "")).strip() or path.name
        for ref in payload.get("references", []) or []:
            ref_type = str(ref.get("type", "")).strip()
            ref_id = str(ref.get("id", "")).strip()
            if ref_type not in id_map:
                unresolved.append(f"{procedure_id}: unknown reference type '{ref_type}'")
                continue
            if ref_id and ref_id not in id_map[ref_type]:
                unresolved.append(f"{procedure_id}: unresolved {ref_type} reference '{ref_id}'")

    assert not unresolved, "Unresolved procedure references:\n" + "\n".join(unresolved)


def test_procedure_step_tactic_refs_resolve_to_shipped_tactics() -> None:
    """All step tactic_refs in shipped procedures must resolve to shipped tactics.

    _proposed procedures are excluded — their tactic_refs may target unshipped tactics.
    """
    tactic_ids = _shipped_ids("tactics", "*.tactic.yaml")
    unresolved: list[str] = []

    for path in _multi_glob(_SHIPPED_PROCEDURE_DIRS, "*.procedure.yaml"):
        payload = _load_yaml(path)
        procedure_id = str(payload.get("id", "")).strip() or path.name
        for step in payload.get("steps", []) or []:
            step_title = str(step.get("title", "?")).strip()
            for tactic_ref in step.get("tactic_refs", []) or []:
                ref_id = str(tactic_ref).strip()
                if ref_id and ref_id not in tactic_ids:
                    unresolved.append(f"{procedure_id} step '{step_title}': unresolved tactic_ref '{ref_id}'")

    assert not unresolved, "Unresolved procedure step tactic_refs:\n" + "\n".join(unresolved)
