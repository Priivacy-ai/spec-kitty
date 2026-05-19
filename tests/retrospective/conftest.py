"""Shared pytest fixtures for retrospective tests.

Provides helpers for scaffolding charter and config files in tmp_path fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Charter scaffolding helpers
# ---------------------------------------------------------------------------


def write_charter(
    repo_root: Path,
    *,
    frontmatter: dict[str, object] | None = None,
    body: str = "# Charter\n\nThis is a test charter.\n",
) -> Path:
    """Write a minimal charter file with optional YAML frontmatter.

    Args:
        repo_root: Project root directory (tmp_path).
        frontmatter: Dict to serialize as YAML frontmatter.  ``None`` produces
            a charter with no frontmatter block (plain markdown body only).
        body: Markdown body appended after the frontmatter block.

    Returns:
        The path to the written charter file.
    """
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_path = charter_dir / "charter.md"

    if frontmatter is None:
        charter_path.write_text(body, encoding="utf-8")
        return charter_path

    # Serialize frontmatter manually (simple key:value for test purposes)
    lines: list[str] = ["---"]
    for key, value in frontmatter.items():
        lines.append(_serialize_yaml_value(key, value))
    lines.append("---")
    lines.append("")
    lines.append(body)

    charter_path.write_text("\n".join(lines), encoding="utf-8")
    return charter_path


def write_charter_with_retrospective(
    repo_root: Path,
    retrospective_fields: dict[str, object],
    extra_frontmatter: dict[str, object] | None = None,
) -> Path:
    """Write a charter with a ``retrospective:`` block in frontmatter.

    Args:
        repo_root: Project root directory.
        retrospective_fields: Fields to nest under ``retrospective:``.
        extra_frontmatter: Any additional top-level frontmatter keys.

    Returns:
        The path to the written charter file.
    """
    fm: dict[str, object] = dict(extra_frontmatter or {})
    fm["retrospective"] = retrospective_fields
    return write_charter(repo_root, frontmatter=fm)


def write_config(
    repo_root: Path,
    content: str,
) -> Path:
    """Write a ``.kittify/config.yaml`` file with the given content.

    Args:
        repo_root: Project root directory.
        content: Raw YAML string to write.

    Returns:
        The path to the written config file.
    """
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text(content, encoding="utf-8")
    return config_path


def write_config_with_retrospective(
    repo_root: Path,
    retrospective_fields: dict[str, object],
) -> Path:
    """Write a config file with a ``retrospective:`` block.

    Uses simple YAML serialization suitable for test purposes.

    Args:
        repo_root: Project root directory.
        retrospective_fields: Fields to nest under ``retrospective:``.

    Returns:
        The path to the written config file.
    """
    lines: list[str] = ["retrospective:"]
    for key, value in retrospective_fields.items():
        if isinstance(value, dict):
            lines.append(f"  {key}:")
            for sub_key, sub_val in value.items():
                lines.append(f"    {sub_key}: {_yaml_scalar(sub_val)}")
        else:
            lines.append(f"  {key}: {_yaml_scalar(value)}")
    content = "\n".join(lines) + "\n"
    return write_config(repo_root, content)


# ---------------------------------------------------------------------------
# Internal serialization helpers
# ---------------------------------------------------------------------------


def _serialize_yaml_value(key: str, value: object, indent: int = 0) -> str:
    """Produce a YAML key: value line.  Handles scalars and one-level dicts."""
    prefix = "  " * indent
    if isinstance(value, dict):
        sub_lines = [f"{prefix}{key}:"]
        for sub_key, sub_val in value.items():
            sub_lines.append(_serialize_yaml_value(sub_key, sub_val, indent + 1))
        return "\n".join(sub_lines)
    return f"{prefix}{key}: {_yaml_scalar(value)}"


def _yaml_scalar(value: object) -> str:
    """Format a scalar Python value as a YAML inline value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "null"
    # String — quote if it contains special characters or looks like a bool/null
    s = str(value)
    if s.lower() in {"true", "false", "null", "yes", "no", "on", "off"}:
        return f'"{s}"'
    return s


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """Return a temporary repo root with no charter or config pre-created."""
    return tmp_path
