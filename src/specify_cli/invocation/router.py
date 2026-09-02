"""ActionRouter: deterministic request → (profile_id, action) mapping.

ADR-3 (Option A): pure function over canonical role verbs and profile domain keywords.
No I/O, no network, no LLM call at any point.

See: kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/adr-3-deterministic-action-router.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from charter.profiles import DEFAULT_ROLE_CAPABILITIES, Role

from specify_cli.invocation.errors import RouterAmbiguityError
from specify_cli.invocation.registry import ProfileRegistry

# ---------------------------------------------------------------------------
# Stop-words stripped during token normalization (ADR-3 §"Token normalization")
# ---------------------------------------------------------------------------

STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "this",
        "that",
        "these",
        "those",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "please",
        "kindly",
        "some",
        "for",
        "me",
        "us",
        "our",
        "my",
        "to",
        "and",
        "or",
        "in",
        "on",
        "at",
        "of",
        "with",
        "by",
    }
)

# ---------------------------------------------------------------------------
# CANONICAL_VERB_MAP: request token → (canonical_action, Role)
# Authoritative table per ADR-3 §"CANONICAL_VERB_MAP"
# ---------------------------------------------------------------------------

CANONICAL_VERB_MAP: dict[str, tuple[str, Role]] = {
    # IMPLEMENTER
    "implement": ("implement", Role.IMPLEMENTER),
    "build": ("implement", Role.IMPLEMENTER),
    "code": ("implement", Role.IMPLEMENTER),
    "develop": ("implement", Role.IMPLEMENTER),
    "create": ("implement", Role.IMPLEMENTER),
    "write": ("implement", Role.IMPLEMENTER),
    "generate": ("implement", Role.IMPLEMENTER),
    "produce": ("implement", Role.IMPLEMENTER),
    "output": ("implement", Role.IMPLEMENTER),
    "refine": ("implement", Role.IMPLEMENTER),
    "improve": ("implement", Role.IMPLEMENTER),
    "fix": ("implement", Role.IMPLEMENTER),
    "patch": ("implement", Role.IMPLEMENTER),
    "repair": ("implement", Role.IMPLEMENTER),
    "debug": ("implement", Role.IMPLEMENTER),
    # REVIEWER
    "review": ("review", Role.REVIEWER),
    "check": ("review", Role.REVIEWER),
    "inspect": ("review", Role.REVIEWER),
    "evaluate": ("review", Role.REVIEWER),
    "audit": ("review", Role.REVIEWER),
    "assess": ("review", Role.REVIEWER),
    # PLANNER
    "plan": ("plan", Role.PLANNER),
    "decompose": ("plan", Role.PLANNER),
    "break": ("plan", Role.PLANNER),
    "outline": ("plan", Role.PLANNER),
    "schedule": ("plan", Role.PLANNER),
    "prioritize": ("plan", Role.PLANNER),
    "triage": ("plan", Role.PLANNER),
    "rank": ("plan", Role.PLANNER),
    "order": ("plan", Role.PLANNER),
    # ARCHITECT
    "specify": ("specify", Role.ARCHITECT),
    "spec": ("specify", Role.ARCHITECT),
    "define": ("specify", Role.ARCHITECT),
    "requirements": ("specify", Role.ARCHITECT),
    "scope": ("specify", Role.ARCHITECT),
    # DESIGNER
    "design": ("design", Role.DESIGNER),
    "mockup": ("design", Role.DESIGNER),
    "prototype": ("design", Role.DESIGNER),
    "wireframe": ("design", Role.DESIGNER),
    # RESEARCHER
    "analyze": ("analyze", Role.RESEARCHER),
    "investigate": ("analyze", Role.RESEARCHER),
    "research": ("analyze", Role.RESEARCHER),
    "explore": ("analyze", Role.RESEARCHER),
    "study": ("analyze", Role.RESEARCHER),
    "summarize": ("analyze", Role.RESEARCHER),
    "synthesize": ("analyze", Role.RESEARCHER),
    "compile": ("analyze", Role.RESEARCHER),
    "report": ("analyze", Role.RESEARCHER),
    # CURATOR
    "curate": ("curate", Role.CURATOR),
    "classify": ("curate", Role.CURATOR),
    "organize": ("curate", Role.CURATOR),
    "tag": ("curate", Role.CURATOR),
    "validate": ("curate", Role.CURATOR),
    "verify": ("curate", Role.CURATOR),
    # MANAGER
    "coordinate": ("coordinate", Role.MANAGER),
    "manage": ("coordinate", Role.MANAGER),
    "delegate": ("coordinate", Role.MANAGER),
    "monitor": ("coordinate", Role.MANAGER),
    "track": ("coordinate", Role.MANAGER),
}


# ---------------------------------------------------------------------------
# RouterDecision: frozen result returned on successful routing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RouterDecision:
    """Resolved routing result — immutable, serializable."""

    profile_id: str
    action: str
    # "generic_fallback" (WP02/#3064): pinned by
    # specify_cli.invocation.empty_charter.resolve_generic_fallback when the
    # project charter is wholly empty -- never produced by ActionRouter.route()
    # itself (that seam pre-empts the router entirely at the executor branch).
    confidence: Literal["exact", "canonical_verb", "domain_keyword", "generic_fallback"]
    match_reason: str
    # WP2/#3840 (FR-005): every non-winning candidate the router considered,
    # each {"profile_id", "action", "confidence", "match_reason"}. Always a
    # list, never None -- no default, so every construction site must supply
    # it explicitly (mypy --strict enforces this at every production site).
    alternatives: list[dict[str, str]]


# ---------------------------------------------------------------------------
# ActionRouterPlugin: no-op Protocol stub (ADR-3 §"Future Extension Point")
# Reserved for future hybrid routing; not called in v1.
# ---------------------------------------------------------------------------


class ActionRouterPlugin:
    """No-op Protocol stub — reserved for future hybrid routing extension.

    A future release will implement this Protocol to add an LLM fallback
    path that activates only on ROUTER_NO_MATCH.  Not called in v1.
    """


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def _normalize_tokens(text: str) -> list[str]:
    """Lowercase, split on whitespace/punctuation, drop stop-words."""
    raw = re.split(r"[\s\W]+", text.lower())
    return [t for t in raw if t and t not in STOP_WORDS]


# ---------------------------------------------------------------------------
# ActionRouter
# ---------------------------------------------------------------------------


class ActionRouter:
    """Deterministic request → (profile_id, action) router.

    Pure function: no I/O, no network, no LLM call.  All routing decisions
    are based on CANONICAL_VERB_MAP tokens and profile domain keywords.

    Routing precedence (ADR-3):
      1. Explicit profile_hint → exact match
      2. Canonical verb match → canonical_verb confidence
      3. Domain keyword match → domain_keyword confidence
      4. Zero or ambiguous matches → RouterAmbiguityError
    """

    def __init__(
        self,
        registry: ProfileRegistry,
        router_plugin: ActionRouterPlugin | None = None,  # noqa: ARG002
    ) -> None:
        self._registry = registry
        # router_plugin reserved for future hybrid extension; not used in v1

    def route(
        self,
        request_text: str,
        profile_hint: str | None = None,
    ) -> RouterDecision:
        """Route *request_text* to a (profile_id, action) pair.

        Args:
            request_text: Natural-language request from the caller.
            profile_hint: Optional profile identifier to bypass routing.

        Returns:
            RouterDecision with profile_id, action, confidence, match_reason.

        Raises:
            RouterAmbiguityError: On no-match or ambiguous match.
        """
        profiles = self._registry.list_all()
        if not profiles:
            raise RouterAmbiguityError(
                request_text,
                "ROUTER_NO_MATCH",
                [],
                "No profiles available. Run 'spec-kitty charter synthesize'.",
            )

        # ------------------------------------------------------------------
        # Level 1: Explicit profile hint → exact confidence
        # ------------------------------------------------------------------
        if profile_hint is not None:
            from specify_cli.invocation.errors import ProfileNotFoundError  # noqa: PLC0415

            try:
                profile = self._registry.resolve(profile_hint)
            except ProfileNotFoundError as exc:
                raise RouterAmbiguityError(
                    request_text,
                    "PROFILE_NOT_FOUND",
                    [],
                    str(exc),
                ) from exc
            action = self._derive_action_from_tokens(request_text, profile.role)
            return RouterDecision(
                profile_id=profile.profile_id,
                action=action,
                confidence="exact",
                match_reason=f"explicit profile_hint '{profile_hint}'",
                # WP2/#3840: the router never computes candidates on the
                # explicit-hint path (Edge Case / Acceptance Scenario 2).
                alternatives=[],
            )

        tokens = _normalize_tokens(request_text)

        # ------------------------------------------------------------------
        # Level 2: Canonical verb match
        # ------------------------------------------------------------------
        # Map each matched token to its role; first occurrence per role wins.
        verb_matches: dict[Role, tuple[str, str]] = {}  # role → (action, token)
        for token in tokens:
            entry = CANONICAL_VERB_MAP.get(token)
            if entry is not None:
                action, role = entry
                if role not in verb_matches:
                    verb_matches[role] = (action, token)

        # ------------------------------------------------------------------
        # Level 3: Domain keyword match (per-profile)
        # ------------------------------------------------------------------
        # Check specialization_context.domain_keywords (NOT specialization.domain_keywords).
        keyword_matches: list[tuple[str, str, str]] = []  # (profile_id, action, keyword)
        for profile in profiles:
            sc = getattr(profile, "specialization_context", None)
            kws: list[str] = list(sc.domain_keywords) if sc and sc.domain_keywords else []
            # Also fold in collaboration.canonical_verbs as profile-level verb signals
            collab = getattr(profile, "collaboration", None)
            collab_verbs: list[str] = list(collab.canonical_verbs) if collab and collab.canonical_verbs else []
            for cv in collab_verbs:
                if cv not in kws:
                    kws.append(cv)
            for kw in kws:
                if kw.lower() in tokens:
                    caps = DEFAULT_ROLE_CAPABILITIES.get(profile.role) if isinstance(profile.role, Role) else None
                    action = caps.canonical_verbs[0] if caps and caps.canonical_verbs else "review"
                    keyword_matches.append((profile.profile_id, action, kw))

        # ------------------------------------------------------------------
        # Aggregate candidates
        # ------------------------------------------------------------------
        candidates: list[dict[str, str]] = []

        # Verb-matched roles → expand to profiles with that role
        for role, (action, token) in verb_matches.items():
            role_profiles = [p for p in profiles if getattr(p, "role", None) == role]
            for p in role_profiles:
                candidates.append(
                    {
                        "profile_id": p.profile_id,
                        "action": action,
                        "match_reason": f"token '{token}' matched {getattr(role, 'value', str(role))} canonical verb",
                        "_confidence": "canonical_verb",
                    }
                )

        # Keyword-matched profiles (only add if not already in candidates)
        existing_ids = {c["profile_id"] for c in candidates}
        for profile_id, action, kw in keyword_matches:
            if profile_id not in existing_ids:
                candidates.append(
                    {
                        "profile_id": profile_id,
                        "action": action,
                        "match_reason": f"domain keyword '{kw}' matched",
                        "_confidence": "domain_keyword",
                    }
                )
                existing_ids.add(profile_id)

        if not candidates:
            raise RouterAmbiguityError(
                request_text,
                "ROUTER_NO_MATCH",
                [],
                "No profile matched. Use 'spec-kitty dispatch \"<request>\" --profile <id>' or run 'spec-kitty profiles list'.",
            )

        # ------------------------------------------------------------------
        # WP3/#3840 (FR-006, SK-08 rerank -- narrowed by operator ruling on
        # top of the original WP03 commit): partition candidates into the
        # canonical-verb tier and the domain-keyword tier BEFORE any
        # priority-based selection. A canonical-verb candidate always beats
        # a domain-keyword candidate, regardless of routing_priority --
        # routing_priority only continues to break ties WITHIN the
        # canonical-verb tier (unchanged from today). This is the
        # competition case SK-08 actually reported
        # (SPEC-KITTY-LEDGER.md:2727): a lone/weak domain-keyword candidate
        # outranking the request's own canonical-verb match.
        #
        # When the verb tier is EMPTY there is no verb-vs-keyword
        # competition to resolve -- the request's tokens carried no
        # canonical verb at all. That no-competition case is out of SK-08's
        # reported scope: it falls back to the pre-existing (pre-WP03)
        # selection pool of every candidate, which -- since the verb tier is
        # empty -- is exactly the keyword tier. A unique keyword-tier
        # candidate still auto-selects there, and routing_priority still
        # breaks ties among multiple keyword-tier candidates, exactly as
        # before this fix. A real shipped profile depends on this:
        # `chart` is a diagram-daisy domain-keyword-tier signal (folded from
        # collaboration.canonical_verbs), unique across the shipped set,
        # with no competing canonical-verb candidate -- see
        # test_writing_comms_routing.py::test_diagram_as_code_still_routes_to_diagram_daisy.
        # ------------------------------------------------------------------
        verb_tier = [c for c in candidates if c["_confidence"] == "canonical_verb"]

        def _priority(candidate: dict[str, str]) -> int:
            p = self._registry.get(candidate["profile_id"])
            return getattr(p, "routing_priority", 0) if p is not None else 0

        # Selection pool: the verb tier when it is non-empty (cross-tier
        # competition always resolves in the verb tier's favor); otherwise
        # the full candidate list, which is exactly the keyword tier when
        # the verb tier is empty (candidates only ever carry
        # "canonical_verb" or "domain_keyword" confidence -- the two tiers
        # partition `candidates` completely).
        selection_pool = verb_tier if verb_tier else candidates

        if len(selection_pool) == 1:
            c = selection_pool[0]
            return RouterDecision(
                profile_id=c["profile_id"],
                action=c["action"],
                confidence=c["_confidence"],  # type: ignore[arg-type]
                match_reason=c["match_reason"],
                # WP2/#3840 (FR-005, SC-003) + WP3/#3840 (FR-006): every
                # non-winning candidate from the FULL candidates list --
                # verb-tier and keyword-tier losers alike.
                alternatives=[
                    {
                        "profile_id": other["profile_id"],
                        "action": other["action"],
                        "confidence": other["_confidence"],
                        "match_reason": other["match_reason"],
                    }
                    for other in candidates
                    if other is not c
                ],
            )

        # ------------------------------------------------------------------
        # Tiebreaker: routing_priority (higher wins) -- WITHIN the selection
        # pool only. When the verb tier is non-empty this is WITHIN the
        # canonical-verb tier ONLY (FR-006), unchanged from today's
        # intra-tier behavior; a domain-keyword candidate never enters this
        # comparison regardless of its routing_priority. When the verb tier
        # is empty this is within the keyword tier, exactly as it was
        # before WP03 (no competition to resolve, so the pre-existing
        # priority-based selection applies unchanged).
        # ------------------------------------------------------------------
        sorted_pool = sorted(selection_pool, key=_priority, reverse=True)
        top_priority = _priority(sorted_pool[0])
        top_candidates = [c for c in sorted_pool if _priority(c) == top_priority]

        if len(top_candidates) == 1:
            c = top_candidates[0]
            return RouterDecision(
                profile_id=c["profile_id"],
                action=c["action"],
                confidence=c["_confidence"],  # type: ignore[arg-type]
                match_reason=c["match_reason"] + " (selected by routing_priority)",
                # WP2/#3840 (FR-005, SC-003): every non-winning candidate from
                # the FULL `candidates` list, not just `top_candidates` -- a
                # candidate that lost the priority tiebreaker before ever
                # reaching `top_candidates` is still a real alternative the
                # router considered.
                alternatives=[
                    {
                        "profile_id": other["profile_id"],
                        "action": other["action"],
                        "confidence": other["_confidence"],
                        "match_reason": other["match_reason"],
                    }
                    for other in candidates
                    if other is not c
                ],
            )

        # Still ambiguous after the tiebreaker: genuinely tied at the top
        # priority within the selection pool -- either two-or-more tied
        # canonical-verb candidates (unchanged from today), or two-or-more
        # tied keyword-tier candidates when the verb tier is empty
        # (unchanged from pre-WP03: this is a real tie, not merely "zero
        # verb-tier candidates present").
        raise RouterAmbiguityError(
            request_text,
            "ROUTER_AMBIGUOUS",
            [
                {
                    "profile_id": c["profile_id"],
                    "action": c["action"],
                    "match_reason": c["match_reason"],
                    # FR-009: sourced from the same _confidence value computed
                    # above during the verb/keyword match passes -- so
                    # build_ambiguous_dry_run_payload can build `alternatives`
                    # from err.candidates without a schema mismatch.
                    "confidence": c["_confidence"],
                }
                for c in top_candidates
            ],
            "Multiple profiles matched. Use 'spec-kitty dispatch \"<request>\" --profile <id>' or run 'spec-kitty profiles list'.",
        )

    def _derive_action_from_tokens(self, request_text: str, role: object) -> str:
        """Derive canonical action from request tokens, falling back to role default."""
        tokens = _normalize_tokens(request_text)
        for token in tokens:
            entry = CANONICAL_VERB_MAP.get(token)
            if entry is not None:
                action, _ = entry
                return action
        caps = DEFAULT_ROLE_CAPABILITIES.get(role) if isinstance(role, Role) else None
        if caps and caps.canonical_verbs:
            # str() re-types the upstream Any (follow_imports=skip) as str.
            return str(caps.canonical_verbs[0])
        return "review"
