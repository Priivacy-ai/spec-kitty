"""Consistency checks between shipped/proposed profile directive references and directives.

Cross-reference / linking checks apply to **shipped** artifacts only.
_proposed artifacts are work-in-progress and may reference artifacts that do not
yet exist.  Only schema-syntactic checks run across both shipped and _proposed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import jsonschema
from ruamel.yaml import YAML

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCTRINE_ROOT = REPO_ROOT / "src" / "doctrine"

PROFILES_DIR = _DOCTRINE_ROOT / "agent_profiles" / "shipped"
DIRECTIVE_SCHEMA = REPO_ROOT / "src" / "doctrine" / "schemas" / "directive.schema.yaml"

# Scan both shipped and _proposed for each artifact type
_DIRECTIVES_DIRS = [_DOCTRINE_ROOT / "directives" / d for d in ("shipped", "_proposed")]
_TACTICS_DIRS = [_DOCTRINE_ROOT / "tactics" / d for d in ("shipped", "_proposed")]
_PARADIGMS_DIRS = [_DOCTRINE_ROOT / "paradigms" / d for d in ("shipped", "_proposed")]
_STYLEGUIDES_DIRS = [_DOCTRINE_ROOT / "styleguides" / d for d in ("shipped", "_proposed")]
_TOOLGUIDES_DIRS = [_DOCTRINE_ROOT / "toolguides" / d for d in ("shipped", "_proposed")]
_PROCEDURES_DIRS = [_DOCTRINE_ROOT / "procedures" / d for d in ("shipped", "_proposed")]
_TEMPLATES_DIR = _DOCTRINE_ROOT / "templates"
_SHIPPED_DIRECTIVES_DIR = _DOCTRINE_ROOT / "directives" / "shipped"
_SHIPPED_TACTICS_DIR = _DOCTRINE_ROOT / "tactics" / "shipped"
_SHIPPED_PARADIGMS_DIR = _DOCTRINE_ROOT / "paradigms" / "shipped"


def _multi_glob(dirs: list[Path], pattern: str) -> list[Path]:
    """Glob across multiple directories, returning sorted unique paths."""
    results: list[Path] = []
    for d in dirs:
        if d.exists():
            results.extend(d.glob(pattern))
    return sorted(set(results))


def _load_yaml(path: Path) -> dict[str, Any]:
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.load(fh) or {}


def _profile_directive_refs() -> dict[str, str]:
    refs: dict[str, str] = {}
    yaml = YAML(typ="safe")

    for profile_path in sorted(PROFILES_DIR.glob("*.agent.yaml")):
        with profile_path.open("r", encoding="utf-8") as fh:
            profile = yaml.load(fh) or {}

        for ref in profile.get("directive-references", []):
            code = str(ref.get("code", "")).strip()
            title = str(ref.get("name", "")).strip()
            if not code:
                continue
            refs[code] = title

    return refs


def test_all_referenced_directives_have_matching_files_and_titles() -> None:
    refs = _profile_directive_refs()
    assert refs, "No directive references found in shipped profiles"

    for code, expected_title in refs.items():
        matches = _multi_glob(_DIRECTIVES_DIRS, f"{code}-*.directive.yaml")
        assert matches, f"Missing directive file for code {code}"

        directive = _load_yaml(matches[0])
        actual_title = str(directive.get("title", "")).strip()
        assert actual_title == expected_title, (
            f"Directive title mismatch for code {code}: "
            f"expected '{expected_title}', got '{actual_title}'"
        )


def test_directive_files_validate_against_schema() -> None:
    schema = _load_yaml(DIRECTIVE_SCHEMA)
    validator = jsonschema.Draft202012Validator(schema)

    directive_files = _multi_glob(_DIRECTIVES_DIRS, "*.directive.yaml")
    assert directive_files, "No directive files found"

    for path in directive_files:
        data = _load_yaml(path)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        assert not errors, f"Schema validation failed for {path.name}: {[e.message for e in errors]}"


def test_lenient_adherence_directives_declare_explicit_allowances() -> None:
    directive_files = _multi_glob(_DIRECTIVES_DIRS, "*.directive.yaml")
    assert directive_files, "No directive files found"

    violations: list[str] = []
    for path in directive_files:
        data = _load_yaml(path)
        if str(data.get("enforcement", "")).strip() != "lenient-adherence":
            continue

        allowances = data.get("explicit_allowances", []) or []
        if not isinstance(allowances, list) or not any(str(item).strip() for item in allowances):
            violations.append(f"{path.name}: lenient-adherence requires non-empty explicit_allowances")

    assert not violations, "Lenient-adherence directive allowance violations:\n" + "\n".join(violations)


def _shipped_tactic_ids() -> set[str]:
    tactic_ids: set[str] = set()
    for path in _multi_glob([_SHIPPED_TACTICS_DIR], "*.tactic.yaml"):
        data = _load_yaml(path)
        tactic_id = str(data.get("id", "")).strip()
        if tactic_id:
            tactic_ids.add(tactic_id)
    return tactic_ids


def test_all_directive_tactic_refs_resolve_to_shipped_tactics() -> None:
    tactic_ids = _shipped_tactic_ids()
    assert tactic_ids, "No shipped tactics found"

    directive_files = _multi_glob([_SHIPPED_DIRECTIVES_DIR], "*.directive.yaml")
    assert directive_files, "No shipped directive files found"

    unresolved: list[str] = []
    for path in directive_files:
        data = _load_yaml(path)
        refs = data.get("tactic_refs", []) or []
        if not isinstance(refs, list):
            unresolved.append(f"{path.name}: tactic_refs is not a list")
            continue

        for ref in refs:
            ref_str = str(ref).strip()
            if ref_str and ref_str not in tactic_ids:
                unresolved.append(f"{path.name}: unresolved tactic_ref '{ref_str}'")

    assert not unresolved, "Unresolved tactic references:\n" + "\n".join(unresolved)


def _shipped_styleguide_ids() -> set[str]:
    ids: set[str] = set()
    for pattern in ("*.styleguide.yaml", "**/*.styleguide.yaml"):
        for path in _multi_glob(_STYLEGUIDES_DIRS, pattern):
            data = _load_yaml(path)
            styleguide_id = str(data.get("id", "")).strip()
            if styleguide_id:
                ids.add(styleguide_id)
    return ids


def _shipped_toolguide_ids() -> set[str]:
    ids: set[str] = set()
    for path in _multi_glob(_TOOLGUIDES_DIRS, "*.toolguide.yaml"):
        data = _load_yaml(path)
        toolguide_id = str(data.get("id", "")).strip()
        if toolguide_id:
            ids.add(toolguide_id)
    return ids


def _shipped_procedure_ids() -> set[str]:
    ids: set[str] = set()
    for path in _multi_glob(_PROCEDURES_DIRS, "*.procedure.yaml"):
        data = _load_yaml(path)
        procedure_id = str(data.get("id", "")).strip()
        if procedure_id:
            ids.add(procedure_id)
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


def test_directive_references_resolve_to_known_artifacts() -> None:
    """All shipped directive references must point to shipped doctrine artifacts.

    _proposed directives are skipped — they may reference artifacts that are not yet shipped.
    """
    id_map = {
        "directive": _shipped_directive_ids(),
        "tactic": _shipped_tactic_ids(),
        "styleguide": _shipped_styleguide_ids(),
        "toolguide": _shipped_toolguide_ids(),
        "paradigm": _shipped_paradigm_ids(),
        "procedure": _shipped_procedure_ids(),
        "template": _shipped_template_ids(),
    }

    unresolved: list[str] = []
    for path in _multi_glob([_SHIPPED_DIRECTIVES_DIR], "*.directive.yaml"):
        data = _load_yaml(path)
        directive_id = str(data.get("id", "")).strip() or path.name
        for ref in data.get("references", []) or []:
            ref_type = str(ref.get("type", "")).strip()
            ref_id = str(ref.get("id", "")).strip()
            if ref_type not in id_map:
                unresolved.append(f"{directive_id}: unknown reference type '{ref_type}'")
                continue
            if ref_id and ref_id not in id_map[ref_type]:
                unresolved.append(f"{directive_id}: unresolved {ref_type} reference '{ref_id}'")

    assert not unresolved, "Unresolved directive references:\n" + "\n".join(unresolved)


# ---------------------------------------------------------------------------
# Tactic cross-reference graph: loop detection
# ---------------------------------------------------------------------------

def _build_tactic_ref_graph() -> dict[str, list[str]]:
    """Return adjacency list: tactic_id -> [referenced tactic_ids].

    Only shipped tactics are included; _proposed tactics may have dangling refs.
    """
    graph: dict[str, list[str]] = {}
    for path in _multi_glob([_SHIPPED_TACTICS_DIR], "*.tactic.yaml"):
        data = _load_yaml(path)
        tactic_id = str(data.get("id", "")).strip()
        if not tactic_id:
            continue
        neighbours: list[str] = []
        # Root-level references
        for ref in data.get("references", []) or []:
            if ref.get("type") == "tactic":
                neighbours.append(str(ref["id"]).strip())
        # Step-level references
        for step in data.get("steps", []) or []:
            for ref in step.get("references", []) or []:
                if ref.get("type") == "tactic":
                    neighbours.append(str(ref["id"]).strip())
        graph[tactic_id] = neighbours
    return graph


def _detect_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """DFS cycle detection; returns list of cycles (each cycle as ordered node list)."""
    visited: set[str] = set()
    path: list[str] = []
    path_set: set[str] = set()
    cycles: list[list[str]] = []

    def dfs(node: str) -> None:
        if node in path_set:
            start = path.index(node)
            cycles.append(path[start:] + [node])
            return
        if node in visited:
            return
        visited.add(node)
        path.append(node)
        path_set.add(node)
        for neighbour in graph.get(node, []):
            dfs(neighbour)
        path.pop()
        path_set.discard(node)

    for node in graph:
        dfs(node)
    return cycles


def test_tactic_reference_graph_has_no_cycles() -> None:
    """Tactic cross-references must form a DAG; cycles would cause infinite resolution loops."""
    graph = _build_tactic_ref_graph()
    assert graph, "No tactics found to build reference graph"
    cycles = _detect_cycles(graph)
    assert not cycles, (
        "Cyclic tactic references detected (would cause infinite resolution loops):\n"
        + "\n".join(" -> ".join(cycle) for cycle in cycles)
    )


def test_tactic_references_resolve_to_known_tactics() -> None:
    """All tactic-type cross-references inside shipped tactic files must point to a shipped tactic.

    _proposed tactics are excluded — their references may target artifacts not yet shipped.
    """
    tactic_ids = _shipped_tactic_ids()
    unresolved: list[str] = []
    for path in _multi_glob([_SHIPPED_TACTICS_DIR], "*.tactic.yaml"):
        data = _load_yaml(path)
        tactic_id = str(data.get("id", "")).strip()
        for ref in data.get("references", []) or []:
            if ref.get("type") == "tactic":
                ref_id = str(ref.get("id", "")).strip()
                if ref_id and ref_id not in tactic_ids:
                    unresolved.append(f"{tactic_id}: root reference '{ref_id}' not found")
        for step in data.get("steps", []) or []:
            for ref in step.get("references", []) or []:
                if ref.get("type") == "tactic":
                    ref_id = str(ref.get("id", "")).strip()
                    if ref_id and ref_id not in tactic_ids:
                        step_title = step.get("title", "?")
                        unresolved.append(
                            f"{tactic_id} step '{step_title}': reference '{ref_id}' not found"
                        )
    assert not unresolved, "Unresolved tactic-to-tactic references:\n" + "\n".join(unresolved)


# ---------------------------------------------------------------------------
# opposed_by resolution checks
# ---------------------------------------------------------------------------

def _shipped_directive_ids() -> set[str]:
    ids: set[str] = set()
    for path in _multi_glob([_SHIPPED_DIRECTIVES_DIR], "*.directive.yaml"):
        data = _load_yaml(path)
        d_id = str(data.get("id", "")).strip()
        if d_id:
            ids.add(d_id)
    return ids


def _shipped_paradigm_ids() -> set[str]:
    ids: set[str] = set()
    for path in _multi_glob([_SHIPPED_PARADIGMS_DIR], "*.paradigm.yaml"):
        data = _load_yaml(path)
        p_id = str(data.get("id", "")).strip()
        if p_id:
            ids.add(p_id)
    return ids


def test_directive_opposed_by_refs_resolve() -> None:
    """All opposed_by entries in shipped directives must point to known artifacts.

    _proposed directives are excluded — their opposed_by links may be aspirational.
    """
    directive_ids = _shipped_directive_ids()
    tactic_ids = _shipped_tactic_ids()
    paradigm_ids = _shipped_paradigm_ids()
    id_map = {"directive": directive_ids, "tactic": tactic_ids, "paradigm": paradigm_ids}

    unresolved: list[str] = []
    for path in _multi_glob([_SHIPPED_DIRECTIVES_DIR], "*.directive.yaml"):
        data = _load_yaml(path)
        source_id = str(data.get("id", "")).strip()
        for entry in data.get("opposed_by", []) or []:
            ref_type = str(entry.get("type", "")).strip()
            ref_id = str(entry.get("id", "")).strip()
            if ref_type not in id_map:
                unresolved.append(f"{source_id}: unknown opposed_by type '{ref_type}'")
                continue
            if ref_id and ref_id not in id_map[ref_type]:
                unresolved.append(
                    f"{source_id}: opposed_by {ref_type} '{ref_id}' not found"
                )
    assert not unresolved, "Unresolved directive opposed_by references:\n" + "\n".join(unresolved)


def test_tactic_opposed_by_refs_resolve() -> None:
    """All opposed_by entries in shipped tactics must point to known artifacts.

    _proposed tactics are excluded — their opposed_by links may be aspirational.
    """
    directive_ids = _shipped_directive_ids()
    tactic_ids = _shipped_tactic_ids()
    paradigm_ids = _shipped_paradigm_ids()
    id_map = {"directive": directive_ids, "tactic": tactic_ids, "paradigm": paradigm_ids}

    unresolved: list[str] = []
    for path in _multi_glob([_SHIPPED_TACTICS_DIR], "*.tactic.yaml"):
        data = _load_yaml(path)
        source_id = str(data.get("id", "")).strip()
        for entry in data.get("opposed_by", []) or []:
            ref_type = str(entry.get("type", "")).strip()
            ref_id = str(entry.get("id", "")).strip()
            if ref_type not in id_map:
                unresolved.append(f"{source_id}: unknown opposed_by type '{ref_type}'")
                continue
            if ref_id and ref_id not in id_map[ref_type]:
                unresolved.append(
                    f"{source_id}: opposed_by {ref_type} '{ref_id}' not found"
                )
    assert not unresolved, "Unresolved tactic opposed_by references:\n" + "\n".join(unresolved)


def test_paradigm_tactic_refs_resolve_to_shipped_tactics() -> None:
    """All tactic_refs on shipped paradigms must resolve to shipped tactics.

    _proposed paradigms are excluded — their tactic_refs may reference unshipped tactics.
    """
    tactic_ids = _shipped_tactic_ids()
    unresolved: list[str] = []
    for path in _multi_glob([_SHIPPED_PARADIGMS_DIR], "*.paradigm.yaml"):
        data = _load_yaml(path)
        paradigm_id = str(data.get("id", "")).strip()
        for ref in data.get("tactic_refs", []) or []:
            ref_str = str(ref).strip()
            if ref_str and ref_str not in tactic_ids:
                unresolved.append(f"{paradigm_id}: unresolved tactic_ref '{ref_str}'")
    assert not unresolved, "Unresolved paradigm tactic_refs:\n" + "\n".join(unresolved)
