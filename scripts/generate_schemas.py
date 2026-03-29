#!/usr/bin/env python3
"""Generate YAML JSON-Schema files from Pydantic models.

The Pydantic models in ``src/doctrine/*/models.py`` are the **single source
of truth**. This script derives the YAML schema files that live in
``src/doctrine/schemas/`` and are used by ``jsonschema`` validators at
runtime and in tests.

Usage::

    python scripts/generate_schemas.py          # write schemas
    python scripts/generate_schemas.py --check  # verify schemas are up-to-date (CI)

Exit codes:
    0  schemas written / schemas are up-to-date
    1  --check failed (schemas are stale)
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

# ---------------------------------------------------------------------------
# Registry: maps schema filename stem → (model class path, metadata, overrides)
# ---------------------------------------------------------------------------

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "src" / "doctrine" / "schemas"

# Subset of ArtifactKind values used in cross-reference enums.
# The full ArtifactKind includes agent_profile, mission_step_contract, template
# which are not valid in reference "type" fields.
_REFERENCE_KINDS = [
    "directive",
    "tactic",
    "styleguide",
    "toolguide",
    "paradigm",
    "procedure",
    "template",
]

_CONTRADICTION_KINDS = ["directive", "tactic", "paradigm"]


def _schema_id(stem: str) -> str:
    return f"https://spec-kitty.dev/schemas/doctrine/{stem}.schema.yaml"


# Each entry: (module_path, class_name, title, description, extra_transforms,
#               use_aliases)
# extra_transforms is a callable(schema) → schema for per-type fixups.
REGISTRY: dict[str, tuple[str, str, str, str, Any, bool]] = {}

# Custom generators for schemas that cannot use the standard pipeline.
CUSTOM_GENERATORS: dict[str, Any] = {}


def register(
    stem: str,
    module: str,
    cls: str,
    title: str,
    description: str,
    extra: Any = None,
    *,
    by_alias: bool = False,
) -> None:
    REGISTRY[stem] = (module, cls, title, description, extra, by_alias)


def register_custom(stem: str, generator: Any) -> None:
    """Register a fully custom schema generator function."""
    CUSTOM_GENERATORS[stem] = generator


# --- Paradigm ---
register(
    "paradigm",
    "doctrine.paradigms.models",
    "Paradigm",
    "Paradigm",
    "Minimal schema for doctrine paradigms.",
    extra=lambda s: _add_item_patterns(
        s,
        {
            "tactic_refs": r"^[a-z][a-z0-9-]*$",
            "directive_refs": r"^DIRECTIVE_\d{3}$",
        },
    ),
)

# --- Tactic ---
def _tactic_fixups(schema: dict) -> dict:
    _add_item_patterns(schema, {})
    # Add description to notes field
    props = schema.get("properties", {})
    if "notes" in props:
        notes = props["notes"]
        notes["description"] = (
            "Free-form supplementary material (scoring rubrics, timing guidance, "
            "reference models, etc.) that enriches the tactic but does not fit "
            "into a single step."
        )
    # Inline steps references minItems
    if "references" in props:
        ref_prop = props["references"]
        if "items" in ref_prop and "minItems" not in ref_prop:
            ref_prop["minItems"] = 1
    # Ensure step-level references also have minItems: 1
    defs = schema.get("definitions", {})
    step_def = defs.get("tactic_step", {})
    step_props = step_def.get("properties", {})
    if "references" in step_props:
        step_refs = step_props["references"]
        if "minItems" not in step_refs:
            step_refs["minItems"] = 1
    if "examples" in step_props:
        step_examples = step_props["examples"]
        if "minItems" not in step_examples:
            step_examples["minItems"] = 1
    return schema


register(
    "tactic",
    "doctrine.tactics.models",
    "Tactic",
    "Tactic",
    "Minimal schema for reusable behavior tactics.",
    extra=_tactic_fixups,
)


# --- Directive ---
def _directive_fixups(schema: dict) -> dict:
    # Add explicit_allowances minItems: 1
    props = schema.get("properties", {})
    if "explicit_allowances" in props:
        props["explicit_allowances"]["minItems"] = 1
    # Add allOf conditional: lenient-adherence requires explicit_allowances
    schema["allOf"] = [
        {
            "if": {
                "properties": {"enforcement": {"const": "lenient-adherence"}},
                "required": ["enforcement"],
            },
            "then": {"required": ["explicit_allowances"]},
        }
    ]
    return schema


register(
    "directive",
    "doctrine.directives.models",
    "Directive",
    "Directive",
    "Schema for governance directives with optional enrichment fields.",
    extra=_directive_fixups,
)


# --- Procedure ---
def _procedure_fixups(schema: dict) -> dict:
    props = schema.get("properties", {})
    if "notes" in props:
        props["notes"]["description"] = (
            "Free-form notes, rationale, or supplementary material "
            "that does not fit into structured fields."
        )
    if "anti_patterns" in props:
        props["anti_patterns"]["description"] = (
            "Common mistakes or failure modes to avoid when following this procedure."
        )
    # Add reason description in procedure_reference
    defs = schema.get("definitions", {})
    ref_def = defs.get("procedure_reference", {})
    ref_props = ref_def.get("properties", {})
    if "reason" in ref_props:
        ref_props["reason"]["description"] = (
            "Why this reference is relevant to the procedure."
        )
    return schema


register(
    "procedure",
    "doctrine.procedures.models",
    "Procedure",
    "Procedure",
    "Schema for doctrine procedures — reusable orchestrated workflows.",
    extra=_procedure_fixups,
)


# --- Styleguide ---
def _styleguide_fixups(schema: dict) -> dict:
    props = schema.get("properties", {})
    # anti_patterns: minItems 1 when present
    if "anti_patterns" in props:
        props["anti_patterns"]["minItems"] = 1
    if "patterns" in props:
        props["patterns"]["minItems"] = 1
        props["patterns"]["description"] = (
            "Concrete code patterns demonstrating how to apply the styleguide's "
            "principles. Each pattern includes a name, description, and optional "
            "good/bad examples."
        )
    if "tooling" in props:
        props["tooling"]["description"] = (
            "Recommended tools for enforcing the styleguide (formatters, linters, "
            "type checkers, test runners, etc.)."
        )
    return schema


register(
    "styleguide",
    "doctrine.styleguides.models",
    "Styleguide",
    "Styleguide",
    "Minimal schema for doctrine styleguides.",
    extra=_styleguide_fixups,
)

# --- Toolguide ---
register(
    "toolguide",
    "doctrine.toolguides.models",
    "Toolguide",
    "Toolguide",
    "Minimal schema for doctrine toolguides.",
)


# --- Mission ---
def _mission_fixups(schema: dict) -> dict:
    """Convert anyOf → oneOf for state items (string | object union)."""
    defs = schema.get("definitions", {})
    orch = defs.get("mission_orchestration", {})
    orch_props = orch.get("properties", {})
    if "states" in orch_props:
        states = orch_props["states"]
        items = states.get("items", {})
        # Pydantic generates anyOf for str | MissionStateObject; schema uses oneOf
        if "anyOf" in items:
            items["oneOf"] = items.pop("anyOf")
    return schema


register(
    "mission",
    "doctrine.missions.models",
    "Mission",
    "Mission",
    "Minimal schema for doctrine mission definitions.",
    extra=_mission_fixups,
    by_alias=True,
)


# --- Model-to-task_type ---
def _model_task_fixups(schema: dict) -> dict:
    """Add format/description annotations matching the hand-written schema."""
    props = schema.get("properties", {})
    if "generated_at" in props:
        props["generated_at"]["format"] = "date-time"
    if "source_snapshot" in props:
        props["source_snapshot"]["description"] = (
            "Optional source snapshot ID/hash for traceability."
        )
    # Add format: uri to cost.pricing_source_url
    defs = schema.get("definitions", {})
    cost_def = defs.get("model_cost", {})
    cost_props = cost_def.get("properties", {})
    if "pricing_source_url" in cost_props:
        cost_props["pricing_source_url"]["format"] = "uri"
    # Add format: uri and format: date-time to data_source fields
    ds_def = defs.get("data_source", {})
    ds_props = ds_def.get("properties", {})
    if "url" in ds_props:
        ds_props["url"]["format"] = "uri"
    if "snapshot_at" in ds_props:
        ds_props["snapshot_at"]["format"] = "date-time"
    # Add default: USD to cost.currency
    if "currency" in cost_props:
        cost_props["currency"]["default"] = "USD"
    return schema


register(
    "model-to-task_type",
    "doctrine.model_task_routing.models",
    "ModelToTaskType",
    "Model-to-Task Type Mapping",
    "Catalog of model capabilities, costs, and routing policy for task assignment.",
    extra=_model_task_fixups,
)


# --- Agent Profile ---
def _agent_profile_fixups(schema: dict) -> dict:
    """Add descriptions matching the hand-written schema."""
    props = schema.get("properties", {})

    # Add descriptions to top-level properties
    _desc_map = {
        "profile-id": "Unique identifier for this agent profile (kebab-case)",
        "name": "Human-readable name for this agent",
        "description": "Optional brief description",
        "schema-version": "Schema version for compatibility",
        "purpose": "The agent's primary purpose or mission statement",
        "role": (
            "Agent role (architect, implementer, reviewer, planner, etc.) "
            "- accepts both known roles and custom roles"
        ),
        "capabilities": "List of capabilities this agent can perform",
        "specializes-from": "Parent profile ID this agent specializes from (for hierarchy)",
        "routing-priority": "Priority for routing tasks to this agent (0-100, higher is more preferred)",
        "max-concurrent-tasks": "Maximum number of tasks this agent can handle concurrently",
        "initialization-declaration": "Agent's initialization prompt or declaration",
    }
    for field_name, desc in _desc_map.items():
        if field_name in props:
            props[field_name]["description"] = desc

    # Add description to self-review-protocol
    if "self-review-protocol" in props:
        srp = props["self-review-protocol"]
        # It may be a $ref; if it's inline, add description
        if "description" not in srp and "$ref" not in srp:
            srp["description"] = "Self-review checklist the agent runs before handing off work"

    # Add descriptions to nested definitions
    defs = schema.get("definitions", {})

    # Context sources
    cs_def = defs.get("agent_context_sources", {})
    cs_props = cs_def.get("properties", {})
    _cs_descs = {
        "doctrine-layers": "Doctrine layers this agent consults",
        "directives": "Directive IDs this agent references",
        "tactics": "Tactic IDs this agent references",
        "toolguides": "Toolguide IDs this agent references",
        "styleguides": "Styleguide IDs this agent references",
        "additional": "Additional context sources",
    }
    for field_name, desc in _cs_descs.items():
        if field_name in cs_props:
            cs_props[field_name]["description"] = desc

    # Specialization
    spec_def = defs.get("agent_specialization", {})
    spec_props = spec_def.get("properties", {})
    _spec_descs = {
        "primary-focus": "Primary area of specialization",
        "secondary-awareness": "Secondary areas agent is aware of",
        "avoidance-boundary": "What this agent explicitly avoids",
        "success-definition": "How success is defined for this agent",
    }
    for field_name, desc in _spec_descs.items():
        if field_name in spec_props:
            spec_props[field_name]["description"] = desc

    # Collaboration
    collab_def = defs.get("agent_collaboration", {})
    collab_props = collab_def.get("properties", {})
    _collab_descs = {
        "handoff-to": "Roles/agents this agent hands off to",
        "handoff-from": "Roles/agents that hand off to this agent",
        "works-with": "Roles/agents this agent collaborates with",
        "output-artifacts": "Artifacts this agent produces",
        "operating-procedures": "Procedures this agent follows",
        "canonical-verbs": "Standard verbs for this agent's actions",
    }
    for field_name, desc in _collab_descs.items():
        if field_name in collab_props:
            collab_props[field_name]["description"] = desc

    # Mode defaults
    md_def = defs.get("agent_mode_default", {})
    md_props = md_def.get("properties", {})
    _md_descs = {
        "mode": "Mode name",
        "description": "Mode description",
        "use-case": "When to use this mode",
    }
    for field_name, desc in _md_descs.items():
        if field_name in md_props:
            md_props[field_name]["description"] = desc

    # Specialization context
    sc_def = defs.get("agent_specialization_context", {})
    sc_props = sc_def.get("properties", {})
    _sc_descs = {
        "languages": "Programming languages this agent specializes in",
        "frameworks": "Frameworks this agent knows",
        "file-patterns": "File patterns this agent matches (glob patterns)",
        "domain-keywords": "Domain keywords for matching",
        "writing-style": "Preferred writing styles",
        "complexity-preference": "Task complexity preferences (low, medium, high)",
    }
    for field_name, desc in _sc_descs.items():
        if field_name in sc_props:
            sc_props[field_name]["description"] = desc

    # Directive reference descriptions
    dr_def = defs.get("agent_directive_reference", {})
    dr_props = dr_def.get("properties", {})
    _dr_descs = {
        "code": "Directive code",
        "name": "Directive name",
        "rationale": "Why this directive is referenced",
    }
    for field_name, desc in _dr_descs.items():
        if field_name in dr_props:
            dr_props[field_name]["description"] = desc

    # Tactic/toolguide/styleguide reference descriptions
    for ref_def_name in ("agent_tactic_reference", "agent_toolguide_reference",
                         "agent_styleguide_reference"):
        ref_def = defs.get(ref_def_name, {})
        ref_props = ref_def.get("properties", {})
        kind = ref_def_name.replace("agent_", "").replace("_reference", "").capitalize()
        if "id" in ref_props:
            ref_props["id"]["description"] = f"{kind} ID"
        if "rationale" in ref_props:
            ref_props["rationale"]["description"] = f"Why this {kind.lower()} is referenced"

    # Self-review step descriptions
    srs_def = defs.get("self_review_step", {})
    srs_props = srs_def.get("properties", {})
    _srs_descs = {
        "name": "Step name",
        "command": "Command to run for this step",
        "gate": "Pass/fail criteria for this step",
    }
    for field_name, desc in _srs_descs.items():
        if field_name in srs_props:
            srs_props[field_name]["description"] = desc

    return schema


register(
    "agent-profile",
    "doctrine.agent_profiles.schema_models",
    "AgentProfileSchema",
    "Agent Profile",
    "Rich agent profile schema with 6-section structure for spec-kitty doctrine framework",
    extra=_agent_profile_fixups,
    by_alias=True,
)


# --- Import Candidate (custom generator) ---
def _generate_import_candidate_schema() -> dict:
    """Generate import-candidate schema from two Pydantic model variants.

    This schema uses a top-level ``oneOf`` with two independent object
    schemas — one for the WP01 legacy format and one for the WP03 curation
    scaffold. This cannot be expressed by a single Pydantic model, so we
    generate each variant separately, apply post-processing, and assemble
    the outer wrapper.
    """
    import importlib

    mod = importlib.import_module("doctrine.import_candidates.models")
    legacy_cls = getattr(mod, "LegacyImportCandidate")
    curation_cls = getattr(mod, "CurationImportCandidate")

    # Generate each variant
    legacy_raw = legacy_cls.model_json_schema()
    curation_raw = curation_cls.model_json_schema()

    # Process each variant through the standard cleanup pipeline
    legacy_schema = _process_variant(legacy_raw, "Legacy import-candidate (WP01 baseline)")
    curation_schema = _process_variant(curation_raw, "Doctrine curation import-candidate (WP03 scaffold)")

    # Add the allOf conditional to curation variant:
    # if status == "adopted" then resulting_artifacts is required with minItems: 1
    curation_schema["allOf"] = [
        {
            "if": {
                "properties": {"status": {"const": "adopted"}},
            },
            "then": {
                "required": ["resulting_artifacts"],
                "properties": {
                    "resulting_artifacts": {"minItems": 1},
                },
            },
        }
    ]

    # Assemble the outer wrapper
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": _schema_id("import-candidate"),
        "title": "Import Candidate",
        "description": "Compatibility schema for curated external practice candidates.",
        "type": "object",
        "oneOf": [legacy_schema, curation_schema],
    }

    return schema


def _process_variant(raw: dict, title: str) -> dict:
    """Process a single import-candidate variant schema."""
    defs = raw.get("$defs", {})
    renames = {name: _pascal_to_snake(name) for name in defs}

    # Inline all enum refs (status enums)
    schema = _inline_all_enum_refs(raw, defs)

    # Inline all $refs — for import-candidate variants we want everything
    # inline (no definitions section) since the oneOf wrapper doesn't share defs.
    schema = _inline_all_refs(schema, defs, renames)

    # Remove $defs since everything is inlined
    schema.pop("$defs", None)
    schema.pop("definitions", None)

    # Standard cleanup
    schema = _remove_titles(schema)
    schema = _simplify_nullable(schema)
    schema = _remove_defaults_for_empty_collections(schema)
    schema = _add_minlength_to_string_fields(schema)

    # Remove top-level Pydantic metadata
    schema.pop("description", None)

    # Add title
    schema["title"] = title

    # Order: type, title, additionalProperties, required, properties
    ordered: dict[str, Any] = {}
    for key in ("title", "type", "additionalProperties", "required", "properties",
                "allOf"):
        if key in schema:
            ordered[key] = schema[key]
    for key in schema:
        if key not in ordered:
            ordered[key] = schema[key]

    # Order property definitions
    if "properties" in ordered:
        ordered["properties"] = {
            k: dict(_order_property(v)) if isinstance(v, dict) else v
            for k, v in ordered["properties"].items()
        }

    return ordered


register_custom("import-candidate", _generate_import_candidate_schema)


# ---------------------------------------------------------------------------
# Post-processing transforms
# ---------------------------------------------------------------------------


def _pascal_to_snake(name: str) -> str:
    """Convert PascalCase to snake_case."""
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1).lower()


def _rewrite_refs(obj: Any, old_prefix: str, new_prefix: str, renames: dict[str, str]) -> Any:
    """Recursively rewrite $ref paths and apply definition renames."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str) and v.startswith(old_prefix):
                old_name = v[len(old_prefix):]
                new_name = renames.get(old_name, _pascal_to_snake(old_name))
                result[k] = f"{new_prefix}{new_name}"
            else:
                result[k] = _rewrite_refs(v, old_prefix, new_prefix, renames)
        return result
    elif isinstance(obj, list):
        return [_rewrite_refs(item, old_prefix, new_prefix, renames) for item in obj]
    return obj


def _remove_titles(obj: Any, *, inside_properties: bool = False) -> Any:
    """Remove Pydantic-generated 'title' keys from schema metadata.

    Pydantic adds ``title: "Field Name"`` to every property and definition.
    The hand-written schemas omit these. However, ``title`` can also be a
    legitimate *property name* (e.g. ``properties.title`` in TacticStep).
    We only strip ``title`` when it appears as schema metadata — i.e. when
    it is a sibling of ``type`` and NOT a key inside a ``properties`` dict.
    """
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "title" and not inside_properties:
                # Skip Pydantic metadata titles (siblings of 'type', '$ref', etc.)
                continue
            # When recursing into a "properties" dict, mark that we are
            # now at the level where keys are real field names.
            child_inside_props = (k == "properties")
            result[k] = _remove_titles(v, inside_properties=child_inside_props)
        return result
    elif isinstance(obj, list):
        return [_remove_titles(item, inside_properties=False) for item in obj]
    return obj


def _simplify_nullable(obj: Any) -> Any:
    """Convert anyOf: [{type: X}, {type: null}] → just {type: X}.

    Pydantic emits anyOf for Optional fields, but our hand-written schemas
    just omit the field from 'required' and use a plain type.
    """
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if k == "anyOf" and isinstance(v, list) and len(v) == 2:
                types = [item.get("type") for item in v if isinstance(item, dict)]
                if "null" in types:
                    non_null = [item for item in v if item.get("type") != "null"]
                    if len(non_null) == 1:
                        # Merge the non-null type inline, skip anyOf
                        for nk, nv in non_null[0].items():
                            new[nk] = _simplify_nullable(nv)
                        # Also preserve any sibling keys (like 'default')
                        continue
            new[k] = _simplify_nullable(v)
        # Remove default: null (it's implicit when not in required)
        if new.get("default") is None and "default" in new:
            del new["default"]
        return new
    elif isinstance(obj, list):
        return [_simplify_nullable(item) for item in obj]
    return obj


def _remove_defaults_for_empty_collections(obj: Any) -> Any:
    """Remove default: [] and default: {} — implicit when not required."""
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if k == "default" and v in ([], {}):
                continue
            new[k] = _remove_defaults_for_empty_collections(v)
        return new
    elif isinstance(obj, list):
        return [_remove_defaults_for_empty_collections(item) for item in obj]
    return obj


def _inline_artifact_kind_refs(obj: Any, defs: dict) -> Any:
    """Replace $ref to ArtifactKind with inline enum restricted to reference kinds."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            # Match both old ($defs) and new (definitions) paths
            if "ArtifactKind" in ref or "artifact_kind" in ref:
                return {
                    "type": "string",
                    "enum": _REFERENCE_KINDS,
                    "description": obj.get("description", "Doctrine artifact type being referenced."),
                }
        return {k: _inline_artifact_kind_refs(v, defs) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_inline_artifact_kind_refs(item, defs) for item in obj]
    return obj


def _is_enum_def(defn: dict) -> bool:
    """Check if a $defs entry is a StrEnum definition."""
    return isinstance(defn, dict) and "enum" in defn and defn.get("type") == "string"


def _inline_all_enum_refs(obj: Any, defs: dict) -> Any:
    """Replace all $ref to StrEnum definitions with inline enum values.

    Unlike ``_inline_artifact_kind_refs`` which only handles ArtifactKind,
    this function inlines *all* StrEnum references found in ``$defs``.
    Used for schemas like model-to-task_type that have many enums.
    """
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            if ref.startswith("#/$defs/"):
                def_name = ref[len("#/$defs/"):]
                if def_name in defs and _is_enum_def(defs[def_name]):
                    enum_def = defs[def_name]
                    result: dict[str, Any] = {"type": "string", "enum": enum_def["enum"]}
                    # Preserve sibling keys like description
                    for k, v in obj.items():
                        if k != "$ref":
                            result[k] = v
                    return result
            elif ref.startswith("#/definitions/"):
                def_name = ref[len("#/definitions/"):]
                if def_name in defs and _is_enum_def(defs[def_name]):
                    enum_def = defs[def_name]
                    result = {"type": "string", "enum": enum_def["enum"]}
                    for k, v in obj.items():
                        if k != "$ref":
                            result[k] = v
                    return result
        return {k: _inline_all_enum_refs(v, defs) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_inline_all_enum_refs(item, defs) for item in obj]
    return obj


def _inline_all_refs(obj: Any, defs: dict, renames: dict[str, str]) -> Any:
    """Inline ALL $ref references by replacing them with the definition body.

    Used for import-candidate variants where each variant must be fully
    self-contained (no shared definitions section).
    """
    if isinstance(obj, dict):
        if "$ref" in obj and len(obj) == 1:
            ref = obj["$ref"]
            if ref.startswith("#/$defs/"):
                def_name = ref[len("#/$defs/"):]
                if def_name in defs:
                    # Recursively inline nested refs in the definition body
                    return _inline_all_refs(dict(defs[def_name]), defs, renames)
        return {k: _inline_all_refs(v, defs, renames) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_inline_all_refs(item, defs, renames) for item in obj]
    return obj


def _add_item_patterns(schema: dict, patterns: dict[str, str]) -> dict:
    """Add regex patterns to array item definitions."""
    props = schema.get("properties", {})
    for field_name, pattern in patterns.items():
        if field_name in props:
            prop = props[field_name]
            items = prop.get("items", {})
            items["pattern"] = pattern
            prop["items"] = items
    return schema


def _add_minlength_to_string_fields(obj: Any, required_fields: list[str] | None = None) -> Any:
    """Add minLength: 1 to required string fields that lack other constraints.

    The hand-written schemas add minLength: 1 to most required string fields
    (except those with pattern constraints). This replicates that convention.
    """
    if not isinstance(obj, dict):
        return obj

    required = set(obj.get("required", []) if required_fields is None else required_fields)
    props = obj.get("properties", {})

    for field_name, prop_def in props.items():
        if not isinstance(prop_def, dict):
            continue
        if prop_def.get("type") == "string" and field_name in required:
            # Don't add minLength if there's already a pattern or minLength
            if "pattern" not in prop_def and "minLength" not in prop_def:
                prop_def["minLength"] = 1

    # Recurse into definitions
    for def_name, def_body in obj.get("definitions", {}).items():
        if isinstance(def_body, dict) and "properties" in def_body:
            _add_minlength_to_string_fields(def_body)

    return obj


def _order_schema(schema: dict) -> OrderedDict:
    """Order top-level keys to match the hand-written convention."""
    key_order = [
        "$schema",
        "$id",
        "title",
        "description",
        "type",
        "additionalProperties",
        "required",
        "definitions",
        "properties",
        "allOf",
        "oneOf",
    ]

    ordered = OrderedDict()
    for key in key_order:
        if key in schema:
            ordered[key] = schema[key]
    # Any remaining keys
    for key in schema:
        if key not in ordered:
            ordered[key] = schema[key]
    return ordered


def _order_definition(defn: dict) -> OrderedDict:
    """Order keys within a definition object."""
    key_order = [
        "type",
        "additionalProperties",
        "required",
        "properties",
        "description",
    ]
    ordered = OrderedDict()
    for key in key_order:
        if key in defn:
            ordered[key] = defn[key]
    for key in defn:
        if key not in ordered:
            ordered[key] = defn[key]
    return ordered


def _order_property(prop: dict) -> OrderedDict:
    """Order keys within a property definition."""
    key_order = [
        "type",
        "pattern",
        "minLength",
        "enum",
        "default",
        "description",
        "format",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "additionalProperties",
        "minItems",
        "items",
        "required",
        "properties",
        "$ref",
        "oneOf",
        "anyOf",
    ]
    ordered = OrderedDict()
    for key in key_order:
        if key in prop:
            ordered[key] = prop[key]
    for key in prop:
        if key not in ordered:
            ordered[key] = prop[key]
    return ordered


def _deep_order(schema: dict) -> dict:
    """Apply ordering recursively to produce clean, deterministic output.

    Returns plain ``dict`` instances (not OrderedDict) because Python 3.7+
    preserves insertion order and ruamel.yaml serialises OrderedDict as
    ``!!omap`` which breaks JSON-Schema validators.
    """
    result = dict(_order_schema(schema))

    # Order definitions
    if "definitions" in result:
        ordered_defs: dict[str, Any] = {}
        for def_name in sorted(result["definitions"]):
            defn = result["definitions"][def_name]
            if isinstance(defn, dict):
                ordered_defn = dict(_order_definition(defn))
                if "properties" in ordered_defn:
                    ordered_defn["properties"] = {
                        k: dict(_order_property(v)) if isinstance(v, dict) else v
                        for k, v in ordered_defn["properties"].items()
                    }
                ordered_defs[def_name] = ordered_defn
            else:
                ordered_defs[def_name] = defn
        result["definitions"] = ordered_defs

    # Order top-level properties
    if "properties" in result:
        result["properties"] = {
            k: dict(_order_property(v)) if isinstance(v, dict) else v
            for k, v in result["properties"].items()
        }

    # Order oneOf entries (for import-candidate)
    if "oneOf" in result:
        result["oneOf"] = [
            _deep_order_variant(v) if isinstance(v, dict) else v
            for v in result["oneOf"]
        ]

    return result


def _deep_order_variant(variant: dict) -> dict:
    """Order keys within a oneOf variant (no definitions section)."""
    key_order = [
        "title", "type", "additionalProperties", "required", "properties",
        "allOf",
    ]
    ordered: dict[str, Any] = {}
    for key in key_order:
        if key in variant:
            ordered[key] = variant[key]
    for key in variant:
        if key not in ordered:
            ordered[key] = variant[key]
    if "properties" in ordered:
        ordered["properties"] = {
            k: dict(_order_property(v)) if isinstance(v, dict) else v
            for k, v in ordered["properties"].items()
        }
    return ordered


# ---------------------------------------------------------------------------
# Main generation pipeline
# ---------------------------------------------------------------------------


def generate_schema(stem: str) -> dict:
    """Generate the YAML schema dict for a single artifact type."""
    # Check for custom generators first
    if stem in CUSTOM_GENERATORS:
        schema = CUSTOM_GENERATORS[stem]()
        return _deep_order(schema)

    import importlib

    module_path, class_name, title, description, extra_fn, use_aliases = REGISTRY[stem]
    mod = importlib.import_module(module_path)
    model_cls = getattr(mod, class_name)

    raw = model_cls.model_json_schema(by_alias=use_aliases)

    # Build definition renames: PascalCase → snake_case
    defs = raw.get("$defs", {})
    renames = {name: _pascal_to_snake(name) for name in defs}

    # Phase 1: inline enum refs
    # For schemas with many enums (model-to-task_type), inline ALL enum refs.
    # For others, only inline ArtifactKind.
    enum_defs = {k for k, v in defs.items() if _is_enum_def(v)}
    if enum_defs - {"ArtifactKind"}:
        schema = _inline_all_enum_refs(raw, defs)
    else:
        schema = _inline_artifact_kind_refs(raw, defs)

    # Phase 2: rename $defs → definitions, rewrite $ref paths
    if "$defs" in schema:
        old_defs = schema.pop("$defs")
        new_defs = OrderedDict()
        for old_name, defn in old_defs.items():
            new_name = renames.get(old_name, _pascal_to_snake(old_name))
            # Skip enum definitions — they've been inlined
            if old_name in enum_defs or old_name == "ArtifactKind":
                continue
            new_defs[new_name] = defn
        if new_defs:
            schema["definitions"] = new_defs

    schema = _rewrite_refs(schema, "#/$defs/", "#/definitions/", renames)

    # Phase 3: clean up Pydantic artifacts
    schema = _remove_titles(schema)
    schema = _simplify_nullable(schema)
    schema = _remove_defaults_for_empty_collections(schema)
    schema = _add_minlength_to_string_fields(schema)

    # Phase 4: remove description/title from definitions
    for def_body in schema.get("definitions", {}).values():
        if isinstance(def_body, dict):
            def_body.pop("description", None)
            def_body.pop("title", None)

    # Phase 5: add metadata
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = _schema_id(stem)
    schema["title"] = title
    schema["description"] = description

    # Phase 6: per-type fixups
    if extra_fn is not None:
        schema = extra_fn(schema) or schema

    # Phase 7: order keys
    schema = _deep_order(schema)

    return schema


def write_schema(stem: str, schema: dict) -> Path:
    """Write a schema dict to its YAML file."""
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 120  # avoid excessive line wrapping
    yaml.allow_unicode = True

    path = SCHEMA_DIR / f"{stem}.schema.yaml"
    with path.open("w") as f:
        yaml.dump(schema, f)

    return path


def check_schema(stem: str, schema: dict) -> bool:
    """Check if the generated schema matches the existing file."""
    from io import StringIO

    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 120
    yaml.allow_unicode = True

    buf = StringIO()
    yaml.dump(schema, buf)
    generated = buf.getvalue()

    path = SCHEMA_DIR / f"{stem}.schema.yaml"
    if not path.exists():
        print(f"  MISSING: {path}")
        return False

    existing = path.read_text()
    if generated != existing:
        print(f"  STALE: {path.name}")
        return False

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify schemas are up-to-date (for CI); exit 1 if stale.",
    )
    parser.add_argument(
        "stems",
        nargs="*",
        help="Specific schema stems to generate (default: all registered).",
    )
    args = parser.parse_args()

    all_stems = list(REGISTRY.keys()) + list(CUSTOM_GENERATORS.keys())
    stems = args.stems or all_stems
    unknown = set(stems) - set(all_stems)
    if unknown:
        print(f"Unknown schema stems: {', '.join(sorted(unknown))}")
        print(f"Available: {', '.join(sorted(all_stems))}")
        return 1

    all_ok = True
    for stem in stems:
        schema = generate_schema(stem)
        if args.check:
            ok = check_schema(stem, schema)
            if not ok:
                all_ok = False
            else:
                print(f"  OK: {stem}.schema.yaml")
        else:
            path = write_schema(stem, schema)
            print(f"  Generated: {path.name}")

    if args.check and not all_ok:
        print(
            "\nSchemas are stale. Run `python scripts/generate_schemas.py` to update."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
