"""Empty-charter generic-agent routing fallback (WP02, #3064).

Seam: called ONLY from the executor's auto-route branch
(``ProfileInvocationExecutor.invoke`` -- the ``elif self._router is not None:``
no-profile-hint path). This module is a surgical pre-check that short-circuits
before ``ActionRouter.route()`` when the project charter is wholly empty --
it does NOT touch the shared activation gate (``charter/resolver.py``) or
``ProfileRegistry``, so explicit ``--profile <specialist>`` dispatch under an
empty charter still resolves normally (research.md Decision 2).

Composite predicate (research.md Decision 3): "empty charter" means ALL
charter-activatable dimensions are unconfigured --

- ``charter_activated_urns(repo_root) == set()`` (the 6 URN kinds: directives,
  tactics, toolguides, procedures, paradigms, styleguides)
- ``PackContext.activated_agent_profiles is None``
- ``PackContext.activated_mission_step_contracts is None``
- ``PackContext.activated_glossary_packs is None``
- ``PackContext.org_roots == ()`` (no org/project packs)

``anti_pattern`` is not charter-activatable (excluded alongside ``template``/
``asset``) and is intentionally not part of this predicate.

Pure of side effects beyond the config reads ``PackContext.from_config`` and
``charter_activated_urns`` already perform -- no writes, no logging, no I/O
beyond reading ``.kittify/config.yaml``.
"""

from __future__ import annotations

from pathlib import Path

from charter.pack_context import PackContext, charter_activated_urns
from charter.profiles import DEFAULT_ROLE_CAPABILITIES, Role
from specify_cli.invocation.router import CANONICAL_VERB_MAP, RouterDecision, _normalize_tokens

#: Built-in profile pinned when the charter is wholly empty (Decision 2/3).
GENERIC_AGENT_ID = "generic-agent"

#: Human-readable reason recorded on the resulting ``RouterDecision`` --
#: surfaced by ``dispatch.py``'s warning panel and useful for audit trails.
_MATCH_REASON = (
    "empty charter: no directive/tactic/toolguide/procedure/paradigm/styleguide/"
    "agent-profile/mission-step-contract/glossary-pack/org-pack activations found"
)


def is_charter_empty(repo_root: Path) -> bool:
    """Return ``True`` iff no charter-activatable dimension is configured.

    See module docstring for the composite predicate (research.md Decision 3).
    A narrower check (e.g. URN kinds only) would false-fallback on a repo that
    activated only a glossary pack, a mission-step-contract, or an org pack --
    the exact defect the post-plan adversarial squad caught.
    """
    if charter_activated_urns(repo_root):
        return False
    pack_context = PackContext.from_config(repo_root)
    if pack_context.activated_agent_profiles is not None:
        return False
    if pack_context.activated_mission_step_contracts is not None:
        return False
    if pack_context.activated_glossary_packs is not None:
        return False
    # bool(...) narrows mypy's Any (charter.* is a follow_imports=skip module)
    # back to the declared bool return type.
    return bool(pack_context.org_roots == ())


def _derive_fallback_action(request_text: str) -> str:
    """Derive the canonical action from the request verb.

    Reuses the router's own tokenizer and ``CANONICAL_VERB_MAP`` (ADR-3) --
    NOT duplicated here -- so the fallback's action derivation can never drift
    from the router's. When no token matches a canonical verb, falls back to
    the IMPLEMENTER role's default verb (``generic-agent`` is an implementer
    profile), mirroring ``ActionRouter._derive_action_from_tokens``.
    """
    for token in _normalize_tokens(request_text):
        entry = CANONICAL_VERB_MAP.get(token)
        if entry is not None:
            action, _role = entry
            return action
    caps = DEFAULT_ROLE_CAPABILITIES.get(Role.IMPLEMENTER)
    if caps and caps.canonical_verbs:
        return str(caps.canonical_verbs[0])
    return "implement"


def resolve_generic_fallback(repo_root: Path, request_text: str) -> RouterDecision | None:
    """Pin ``generic-agent`` when the project charter is wholly empty.

    Called at the executor's auto-route branch as
    ``resolve_generic_fallback(...) or self._router.route(...)`` -- returning
    ``None`` here is the short-circuit "not empty, defer to the router" signal.

    Returns
    -------
    RouterDecision | None
        A decision routing to ``GENERIC_AGENT_ID`` with ``confidence=
        "generic_fallback"`` when :func:`is_charter_empty` is ``True``;
        ``None`` otherwise (any activation dimension present).
    """
    if not is_charter_empty(repo_root):
        return None
    return RouterDecision(
        profile_id=GENERIC_AGENT_ID,
        action=_derive_fallback_action(request_text),
        confidence="generic_fallback",
        match_reason=_MATCH_REASON,
    )
