"""GlossaryScope enum and scope resolution utilities."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from .models import Provenance, SenseStatus, TermSense, TermSurface


class GlossaryScope(Enum):
    """Glossary scope levels in the hierarchy."""

    MISSION_LOCAL = "mission_local"
    TEAM_DOMAIN = "team_domain"
    AUDIENCE_DOMAIN = "audience_domain"
    SPEC_KITTY_CORE = "spec_kitty_core"


# Resolution order (highest to lowest precedence)
SCOPE_RESOLUTION_ORDER: list[GlossaryScope] = [
    GlossaryScope.MISSION_LOCAL,
    GlossaryScope.TEAM_DOMAIN,
    GlossaryScope.AUDIENCE_DOMAIN,
    GlossaryScope.SPEC_KITTY_CORE,
]


def get_scope_precedence(scope: GlossaryScope) -> int:
    """
    Get numeric precedence for a scope (lower number = higher precedence).

    Args:
        scope: GlossaryScope enum value

    Returns:
        Precedence integer (0 = highest precedence)
    """
    try:
        return SCOPE_RESOLUTION_ORDER.index(scope)
    except ValueError:
        # Unknown scope defaults to lowest precedence
        return len(SCOPE_RESOLUTION_ORDER)


def should_use_scope(scope: GlossaryScope, configured_scopes: list[GlossaryScope]) -> bool:
    """
    Check if a scope should be used in resolution.

    Args:
        scope: Scope to check
        configured_scopes: List of active scopes

    Returns:
        True if scope is configured and should be used
    """
    return scope in configured_scopes


def validate_seed_file(data: dict[str, Any]) -> None:
    """
    Validate seed file schema.

    Args:
        data: Parsed YAML data

    Raises:
        ValueError: If seed file schema is invalid
    """
    if "terms" not in data:
        raise ValueError("Seed file must have 'terms' key")

    for term in data["terms"]:
        if "surface" not in term:
            raise ValueError("Term must have 'surface' key")
        if "definition" not in term:
            raise ValueError("Term must have 'definition' key")


_STATUS_MAP = {
    "active": SenseStatus.ACTIVE,
    "deprecated": SenseStatus.DEPRECATED,
    "draft": SenseStatus.DRAFT,
}


def _parse_sense_status(raw: str | None) -> SenseStatus:
    """Map a status string to the corresponding SenseStatus enum value.

    Args:
        raw: Status string from seed file or event payload (e.g. "active",
            "deprecated", "draft"). None or unrecognised values default
            to DRAFT.

    Returns:
        Matching SenseStatus enum member.
    """
    if raw is None:
        return SenseStatus.DRAFT
    return _STATUS_MAP.get(raw, SenseStatus.DRAFT)


def load_seed_file(scope: GlossaryScope, repo_root: Path) -> list[TermSense]:
    """
    Load seed file for a scope.

    Args:
        scope: GlossaryScope to load
        repo_root: Repository root path

    Returns:
        List of TermSense objects from seed file
    """
    seed_path = repo_root / ".kittify" / "glossaries" / f"{scope.value}.yaml"

    if not seed_path.exists():
        return []  # Skip cleanly if not configured

    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(seed_path)

    validate_seed_file(data)

    senses = []
    for term_data in data.get("terms", []):
        sense = TermSense(
            surface=TermSurface(term_data["surface"]),
            scope=scope.value,
            definition=term_data["definition"],
            provenance=Provenance(
                actor_id="system:seed_file",
                timestamp=datetime.now(),
                source="seed_file",
            ),
            confidence=term_data.get("confidence", 1.0),
            status=_parse_sense_status(term_data.get("status")),
        )
        senses.append(sense)

    return senses


def _needs_quoting(value: str) -> bool:
    return ": " in value or "'" in value


def _yaml_scalar(value: str) -> str:
    if _needs_quoting(value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _confidence_str(conf: float) -> str:
    return f"{conf:.1f}" if conf == int(conf) else str(round(conf, 4))


def _default_header(scope: GlossaryScope) -> list[str]:
    return [f"# Spec Kitty glossary seed — scope: {scope.value}", ""]


def save_seed_file(
    scope: GlossaryScope,
    repo_root: Path,
    terms: list[TermSense],
) -> None:
    """Write terms to the seed file for *scope*, sorting alphabetically by surface.

    Creates the file if it does not exist. Preserves the header comment block of
    an existing file so hand-written documentation is not lost on update.
    """
    seed_path = repo_root / ".kittify" / "glossaries" / f"{scope.value}.yaml"
    seed_path.parent.mkdir(parents=True, exist_ok=True)

    # Preserve existing header comment lines; fall back to a generated one.
    if seed_path.exists():
        header: list[str] = []
        for line in seed_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or stripped == "":
                header.append(line)
            else:
                break
    else:
        header = _default_header(scope)

    sorted_terms = sorted(terms, key=lambda t: t.surface.surface_text.lower())

    lines: list[str] = list(header) + ["terms:"]
    for sense in sorted_terms:
        lines.append("")
        lines.append(f"  - surface: {_yaml_scalar(sense.surface.surface_text)}")
        lines.append(f"    definition: {_yaml_scalar(sense.definition)}")
        lines.append(f"    confidence: {_confidence_str(sense.confidence)}")
        lines.append(f"    status: {sense.status.value}")
    lines.append("")

    seed_path.write_text("\n".join(lines), encoding="utf-8")


def activate_scope(
    scope: GlossaryScope,
    version_id: str,
    mission_id: str,
    run_id: str,
    repo_root: Path | None = None,
) -> None:
    """
    Activate a glossary scope and emit GlossaryScopeActivated event.

    Args:
        scope: Scope to activate
        version_id: Glossary version ID
        mission_id: Mission ID
        run_id: Run ID
        repo_root: Repository root for event log persistence. If None,
            events are logged but not persisted to disk.
    """
    from .events import emit_scope_activated

    emit_scope_activated(
        scope_id=scope.value,
        glossary_version_id=version_id,
        mission_id=mission_id,
        run_id=run_id,
        repo_root=repo_root,
    )
