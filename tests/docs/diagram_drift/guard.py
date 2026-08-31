"""Drift-guard engine: diagram field set vs. model field set, both introspected.

Public entry points:

* :func:`collect_findings` — read the corpus, return a list of human-readable
  drift findings (empty == clean).
* :func:`assert_no_drift` — raise :class:`DiagramDriftError` if any finding.

Patchable seams (so the non-fakeable tests can inject drift WITHOUT mutating a
frozen enum or a ``frozen=True`` pydantic model — both of which reject mutation):

* :func:`artifact_kind_values` — the live ``ArtifactKind`` member values.
* :func:`model_field_set` — the introspected field/member set for one binding.
"""

from __future__ import annotations

import dataclasses
import re
from enum import Enum
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel
from ruamel.yaml import YAML

from charter.offering.artifact_kinds import ArtifactKind

from .binding_table import (
    ARTIFACT_KIND_DISPOSITIONS,
    BINDINGS,
    DiagramBinding,
    ModelKind,
)

__all__ = [
    "DiagramDriftError",
    "artifact_kind_values",
    "assert_no_drift",
    "collect_findings",
    "model_field_set",
    "parse_startyaml_blocks",
]

_VALID_DISPOSITIONS = frozenset({"diagrammed", "consciously-omitted"})
_PLANTUML_BLOCK = re.compile(r"```plantuml\s*\n(.*?)\n```", re.DOTALL)
_START_END = re.compile(r"@start\w+|@end\w+", re.IGNORECASE)
_DIRECTIVE_LINE = re.compile(r"^\s*(title|header|footer|caption|skinparam)\b", re.IGNORECASE)


class DiagramDriftError(AssertionError):
    """Raised when a diagram's field set diverges from its bound model."""


def artifact_kind_values() -> list[str]:
    """Live ``ArtifactKind`` member values (patchable seam for the completeness test)."""
    return [member.value for member in ArtifactKind]


def parse_startyaml_blocks(md_text: str) -> list[object]:
    """Extract every ```plantuml @start.../@end... block and YAML-parse its body.

    The PlantUML ``title``/directive lines and the ``@start*``/``@end*`` fences are
    stripped; the remainder is a YAML mapping/list. Returns one parsed tree per block.
    """
    yaml = YAML(typ="safe")
    trees: list[object] = []
    for raw in _PLANTUML_BLOCK.findall(md_text):
        lines = [
            line
            for line in raw.splitlines()
            if not _START_END.search(line) and not _DIRECTIVE_LINE.match(line)
        ]
        body = "\n".join(lines).strip()
        if not body:
            continue
        loaded = yaml.load(body)
        if loaded is not None:
            trees.append(loaded)
    return trees


def _find_anchor(node: object, anchor: str) -> object | None:
    """Recursively find the first mapping value whose key == ``anchor``."""
    if isinstance(node, dict):
        mapping = cast("dict[object, object]", node)
        for key, value in mapping.items():
            if key == anchor:
                return value
            found = _find_anchor(value, anchor)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in cast("list[object]", node):
            found = _find_anchor(item, anchor)
            if found is not None:
                return found
    return None


def diagram_field_set(node: object) -> set[str]:
    """The declared field/member set on the diagram side.

    A mapping's *keys* are the declared fields; a list's *values* are the enum
    members. Scalar example values are never treated as fields.
    """
    if isinstance(node, dict):
        return {str(key) for key in node}
    if isinstance(node, list):
        return {str(item) for item in node}
    raise DiagramDriftError(f"anchor value is neither a mapping nor a list: {node!r}")


def model_field_set(binding: DiagramBinding) -> set[str]:
    """The field/member set on the model side (patchable seam).

    Pydantic uses ``FieldInfo.alias or name`` (kebab aliases normalized); frozen
    dataclasses use ``fields()``; StrEnums use their member values via ``list()``.
    """
    if binding.kind is ModelKind.PYDANTIC:
        model = cast("type[BaseModel]", binding.model)
        return {info.alias or name for name, info in model.model_fields.items()}
    if binding.kind is ModelKind.DATACLASS:
        return {field.name for field in dataclasses.fields(cast("Any", binding.model))}
    if binding.kind is ModelKind.STRENUM:
        enum_cls = cast("type[Enum]", binding.model)
        return {str(member.value) for member in enum_cls}
    raise DiagramDriftError(f"unknown ModelKind: {binding.kind!r}")  # pragma: no cover


def _check_disposition_completeness() -> list[str]:
    findings: list[str] = []
    for value in artifact_kind_values():
        disposition = ARTIFACT_KIND_DISPOSITIONS.get(value)
        if disposition is None:
            findings.append(
                f"ArtifactKind member {value!r} has NO disposition in the binding table "
                f"(add {value!r}: 'diagrammed' | 'consciously-omitted')"
            )
        elif disposition not in _VALID_DISPOSITIONS:
            findings.append(
                f"ArtifactKind {value!r} has invalid disposition {disposition!r} "
                f"(must be one of {sorted(_VALID_DISPOSITIONS)})"
            )
    return findings


def _check_binding(binding: DiagramBinding, doc_texts: dict[str, str]) -> list[str]:
    text = doc_texts.get(binding.doc)
    if text is None:
        return [f"{binding.doc}: file not found for binding {binding.anchor!r}"]
    trees = parse_startyaml_blocks(text)
    node = None
    for tree in trees:
        node = _find_anchor(tree, binding.anchor)
        if node is not None:
            break
    if node is None:
        return [f"{binding.doc}: no @startyaml anchor {binding.anchor!r} found"]
    diagram_fields = diagram_field_set(node)
    model_fields = model_field_set(binding)
    if diagram_fields != model_fields:
        missing = sorted(model_fields - diagram_fields)
        extra = sorted(diagram_fields - model_fields)
        return [
            f"{binding.doc}:{binding.anchor} drift vs {binding.model.__name__}: "
            f"missing-in-diagram={missing} extra-in-diagram={extra}"
        ]
    return []


def collect_findings(repo_root: Path, bindings: tuple[DiagramBinding, ...] = BINDINGS) -> list[str]:
    """Return all drift findings for the corpus (empty == clean)."""
    findings = _check_disposition_completeness()
    doc_texts: dict[str, str] = {}
    for binding in bindings:
        if binding.doc not in doc_texts:
            path = repo_root / binding.doc
            doc_texts[binding.doc] = path.read_text(encoding="utf-8") if path.exists() else ""
    for binding in bindings:
        findings.extend(_check_binding(binding, doc_texts))
    return findings


def assert_no_drift(repo_root: Path, bindings: tuple[DiagramBinding, ...] = BINDINGS) -> None:
    """Raise :class:`DiagramDriftError` if the corpus has any drift."""
    findings = collect_findings(repo_root, bindings)
    if findings:
        raise DiagramDriftError("schema-diagram drift:\n" + "\n".join(findings))
