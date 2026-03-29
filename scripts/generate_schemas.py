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


# Each entry: (module_path, class_name, title, description, extra_transforms)
# extra_transforms is a callable(schema) → schema for per-type fixups.
REGISTRY: dict[str, tuple[str, str, str, str, Any]] = {}


def register(
    stem: str,
    module: str,
    cls: str,
    title: str,
    description: str,
    extra: Any = None,
) -> None:
    REGISTRY[stem] = (module, cls, title, description, extra)


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
        "additionalProperties",
        "minItems",
        "items",
        "$ref",
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

    return result


# ---------------------------------------------------------------------------
# Main generation pipeline
# ---------------------------------------------------------------------------


def generate_schema(stem: str) -> dict:
    """Generate the YAML schema dict for a single artifact type."""
    import importlib

    module_path, class_name, title, description, extra_fn = REGISTRY[stem]
    mod = importlib.import_module(module_path)
    model_cls = getattr(mod, class_name)

    raw = model_cls.model_json_schema()

    # Build definition renames: PascalCase → snake_case
    defs = raw.get("$defs", {})
    renames = {name: _pascal_to_snake(name) for name in defs}

    # Phase 1: inline ArtifactKind refs before removing the $def
    schema = _inline_artifact_kind_refs(raw, defs)

    # Phase 2: rename $defs → definitions, rewrite $ref paths
    if "$defs" in schema:
        old_defs = schema.pop("$defs")
        new_defs = OrderedDict()
        for old_name, defn in old_defs.items():
            new_name = renames.get(old_name, _pascal_to_snake(old_name))
            # Skip ArtifactKind — it's been inlined
            if old_name == "ArtifactKind":
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

    stems = args.stems or list(REGISTRY.keys())
    unknown = set(stems) - set(REGISTRY.keys())
    if unknown:
        print(f"Unknown schema stems: {', '.join(sorted(unknown))}")
        print(f"Available: {', '.join(sorted(REGISTRY.keys()))}")
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
