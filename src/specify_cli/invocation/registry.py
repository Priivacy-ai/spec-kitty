"""ProfileRegistry: thin wrapper over AgentProfileRepository for invocation use."""

from __future__ import annotations

from pathlib import Path

from charter.profiles import AgentProfile, AgentProfileRepository

from specify_cli.doctrine_service_factory import build_activation_aware_doctrine_service
from specify_cli.invocation.errors import ProfileNotFoundError

# Provenance layers exposed by ``AgentProfileRepository.get_provenance``.
_LAYER_BUILTIN = "builtin"
_LAYER_ORG = "org"
_LAYER_PROJECT = "project"

# Doctrine layers that the dispatch routing catalog draws from the
# activation-aware service. The doctrine *project* layer
# (``.kittify/agent_profiles``) is intentionally excluded: routing has never
# carried it, and the legacy ``.kittify/profiles`` invocation project layer is
# overlaid separately (and ungated) below.
_DOCTRINE_ROUTING_LAYERS = frozenset({_LAYER_BUILTIN, _LAYER_ORG})


class ProfileRegistry:
    """Thin wrapper over AgentProfileRepository with invocation-friendly API.

    When ``.kittify/profiles/`` does not exist, ``project_dir=None`` causes
    the repo to fall back to built-in profiles gracefully (no exception).
    If built-in profiles also produce an empty list, ``has_profiles()``
    returns False — the executor uses this to produce the
    "run charter synthesize" error message.

    Routing parity with the governance-context seam (R3): the **doctrine**
    layers (built-in + org) are drawn from the same charter-activation-aware
    service that ``build_charter_context`` and ``charter/resolver.py`` use, so
    a built-in (or org) profile the charter de-activated is absent from the
    routing catalog exactly as it is from the governance context. The legacy
    ``.kittify/profiles`` invocation project layer is OUTSIDE the doctrine
    activation model: it is overlaid ungated and always wins on id collision
    (C-002/FR-007). The raw ``org_dirs`` are never spliced here (C-008).

    Two independent gates apply to the doctrine layers, and both must be
    inert for the catalog to be byte-identical to the pre-mission output
    (NFR-001):

    * **Activation gate** — the three-state ``activated_agent_profiles``
      contract. With no ``activated_agent_profiles`` key the gate admits
      every doctrine layer (inert).
    * **Language-scope filter** — ``build_activation_aware_doctrine_service``
      always computes ``active_languages=infer_repo_languages(repo_root)``
      (FR-008 unification, charter-sole-door-bypass-closure-01KZ3WAA WP01)
      and every language-scoped profile (e.g. ``frontend-freddy``) is
      dropped unless it overlaps that set. This filter is inert for a
      project with no compiled charter and no interview answers because
      ``infer_repo_languages`` resolves that "truly nothing configured yet"
      case to ``None`` ("unknown" — admits every scoped profile), not an
      explicitly empty list (landing-fold regression fix: a prior revision
      of this unification returned ``[]`` for that case, which dropped
      every language-scoped profile instead of admitting all of them — see
      ``charter.activation.language_scope.infer_repo_languages``'s docstring for the
      ``None``-vs-``[]`` contract). The filter still narrows the catalog for
      a *configured* project whose compiled charter or interview transcript
      names a real, non-empty language subset (e.g. this repository's own
      root, whose compiled charter declares ``languages: [python]``) — that
      narrowing is intentional, not a bug.

    So byte-identity with the pre-mission catalog holds only when both gates
    are simultaneously inert (nothing de-activated, and either every
    supported language is active or no profile is language-scoped) — not
    unconditionally. Callers that need the full, unfiltered catalog (e.g. the
    ``profiles list`` CLI display surface) intentionally read an ungated,
    unfiltered repository directly instead of this class — see the "Display
    surface" note above ``_profile_catalog`` in
    ``specify_cli/cli/commands/profiles_cmd.py``.
    """

    def __init__(self, repo_root: Path) -> None:
        project_profiles_dir = repo_root / ".kittify" / "profiles"
        self._repo = AgentProfileRepository(
            project_dir=project_profiles_dir if project_profiles_dir.exists() else None,
        )
        self._merged = self._build_merged_profiles(repo_root)

    def _build_merged_profiles(self, repo_root: Path) -> dict[str, AgentProfile]:
        """Build the routing catalog: activation-gated doctrine + legacy project.

        The doctrine layers (built-in + org) come from the activation-aware
        service so they pass the same ``activated_agent_profiles`` three-state
        gate the governance-context seam applies (R3 parity). The legacy
        ``.kittify/profiles`` project layer is then overlaid ungated and always
        wins on id collision (it is outside the doctrine activation model).
        """
        service = build_activation_aware_doctrine_service(repo_root)
        gated = service.agent_profiles
        inner_repo = service.agent_profile_repository
        merged: dict[str, AgentProfile] = {
            profile_id: profile
            for profile_id, profile in gated.items()
            if inner_repo.get_provenance(profile_id) in _DOCTRINE_ROUTING_LAYERS
        }
        for profile in self._repo.list_all():
            if self._repo.get_provenance(profile.profile_id) == _LAYER_PROJECT:
                merged[profile.profile_id] = profile
        return merged

    def list_all(self) -> list[AgentProfile]:
        """Return all loaded profiles (project + activated org) sorted by profile_id."""
        return sorted(self._merged.values(), key=lambda profile: profile.profile_id)

    def get(self, profile_id: str) -> AgentProfile | None:
        """Get profile by ID or None if not found."""
        return self._merged.get(profile_id)

    def resolve(self, profile_id: str) -> AgentProfile:
        """Get profile by ID, raising ProfileNotFoundError if not found."""
        profile = self._merged.get(profile_id)
        if profile is None:
            available = sorted(self._merged)
            raise ProfileNotFoundError(profile_id, available)
        return profile

    def has_profiles(self) -> bool:
        """Return True if any profiles are available."""
        return bool(self._merged)
