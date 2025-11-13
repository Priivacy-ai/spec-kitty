"""Template rendering helpers."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Dict

import yaml

DEFAULT_PATH_PATTERNS: dict[str, str] = {
    r"(?<!\.kittify/)scripts/": ".kittify/scripts/",
    r"(?<!\.kittify/)templates/": ".kittify/templates/",
    r"(?<!\.kittify/)memory/": ".kittify/memory/",
}

VariablesResolver = Mapping[str, str] | Callable[[dict[str, Any]], Mapping[str, str]]


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str, str]:
    """Parse frontmatter from markdown content.

    Returns a tuple of (metadata, body, raw_frontmatter_text). If no frontmatter
    is present the metadata dict is empty and the raw text is an empty string.
    """
    normalized = content.replace("\r", "")
    if not normalized.startswith("---\n"):
        return {}, normalized, ""

    closing_index = normalized.find("\n---", 4)
    if closing_index == -1:
        return {}, normalized, ""

    frontmatter_text = normalized[4:closing_index]
    body_start = closing_index + len("\n---")
    if body_start < len(normalized) and normalized[body_start] == "\n":
        body_start += 1
    body = normalized[body_start:]

    try:
        metadata = yaml.safe_load(frontmatter_text) or {}
        if not isinstance(metadata, dict):
            metadata = {}
    except yaml.YAMLError:
        metadata = {}

    return metadata, body, frontmatter_text


def rewrite_paths(content: str, replacements: Mapping[str, str] | None = None) -> str:
    """Rewrite template paths so generated files point to .kittify assets."""
    patterns = replacements or DEFAULT_PATH_PATTERNS
    rewritten = content
    for pattern, replacement in patterns.items():
        rewritten = re.sub(pattern, replacement, rewritten)
    return rewritten


def render_template(
    template_path: Path,
    variables: VariablesResolver | None = None,
) -> tuple[dict[str, Any], str, str]:
    """Render a template by applying frontmatter parsing and substitutions."""
    text = template_path.read_text(encoding="utf-8").replace("\r", "")
    metadata, body, raw_frontmatter = parse_frontmatter(text)
    replacements = _resolve_variables(variables, metadata)
    rendered = _apply_variables(body, replacements)
    rendered = rewrite_paths(rendered)
    if not rendered.endswith("\n"):
        rendered += "\n"
    return metadata, rendered, raw_frontmatter


def _resolve_variables(
    variables: VariablesResolver | None, metadata: Dict[str, Any]
) -> Mapping[str, str]:
    if variables is None:
        return {}
    if callable(variables):
        resolved = variables(metadata) or {}
    else:
        resolved = variables
    return resolved


def _apply_variables(content: str, variables: Mapping[str, str]) -> str:
    rendered = content
    for placeholder, value in variables.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


__all__ = [
    "DEFAULT_PATH_PATTERNS",
    "parse_frontmatter",
    "render_template",
    "rewrite_paths",
]
