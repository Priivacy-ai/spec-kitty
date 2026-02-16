"""GlossaryScope enum and scope resolution utilities."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

from ruamel.yaml import YAML

from .models import Provenance, SenseStatus, TermSense, TermSurface


class GlossaryScope(Enum):
    """Glossary scope levels in the hierarchy."""
    MISSION_LOCAL = "mission_local"
    TEAM_DOMAIN = "team_domain"
    AUDIENCE_DOMAIN = "audience_domain"
    SPEC_KITTY_CORE = "spec_kitty_core"


# Resolution order (highest to lowest precedence)
SCOPE_RESOLUTION_ORDER: List[GlossaryScope] = [
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


def should_use_scope(scope: GlossaryScope, configured_scopes: List[GlossaryScope]) -> bool:
    """
    Check if a scope should be used in resolution.

    Args:
        scope: Scope to check
        configured_scopes: List of active scopes

    Returns:
        True if scope is configured and should be used
    """
    return scope in configured_scopes


def validate_seed_file(data: Dict[str, Any]) -> None:
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


def load_seed_file(scope: GlossaryScope, repo_root: Path) -> List[TermSense]:
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
            status=SenseStatus.ACTIVE if term_data.get("status") == "active" else SenseStatus.DRAFT,
        )
        senses.append(sense)

    return senses


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
