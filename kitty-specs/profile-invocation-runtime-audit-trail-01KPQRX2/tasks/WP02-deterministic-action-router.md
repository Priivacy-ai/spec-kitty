---
work_package_id: WP02
title: Deterministic Action Router (ADR-3)
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-010
- FR-011
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "78980"
history:
- date: '2026-04-21'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/invocation/router.py
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/router.py
- tests/specify_cli/invocation/test_router.py
tags: []
---

# WP02 — Deterministic Action Router (ADR-3)

## Objective

Implement `ActionRouter` — the pure deterministic routing function that maps a request string
to a `(profile_id, action)` pair using canonical role verbs and profile domain keywords.
Wire it into the executor's no-hint path (executor.py). Produce no LLM call at any point.

**Implementation command**:
```bash
spec-kitty agent action implement WP02 --agent claude
```

## Branch Strategy

Planning base: `main`. Merge target: `main`.
Execution worktree: allocated by `lanes.json`.

## Entry Gate

**ADR-3 MUST be reviewed and accepted before this WP merges.**

The ADR-3 document is at:
`kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/adr-3-deterministic-action-router.md`

Read it in full before implementing. The routing algorithm in the ADR-3 document is authoritative.

**Decision (from ADR-3)**:
- Option A baked in: deterministic verb-mapping table, no LLM
- Routing precedence: explicit hint → canonical_verb match → domain_keyword match → ambiguity
- Future hybrid slot: `ActionRouterPlugin` Protocol, no-op in v1

## Context

**WP01 must be approved** before starting this WP. You will:
- Modify `src/specify_cli/invocation/executor.py` (from WP01) to wire the router
- Create `src/specify_cli/invocation/router.py` (new file)

**Key imports**:
- `from doctrine.agent_profiles.capabilities import DEFAULT_ROLE_CAPABILITIES`
- `from doctrine.agent_profiles.profile import Role`
- `from specify_cli.invocation.registry import ProfileRegistry`
- `from specify_cli.invocation.errors import RouterAmbiguityError`

---

## Subtask T008 — `router.py`: ActionRouter

**Purpose**: Pure function. No I/O, no network, no LLM. Takes a request string (+ optional profile hint) and returns either `RouterDecision` or raises `RouterAmbiguityError`.

**Steps**:

1. Create `src/specify_cli/invocation/router.py`:

```python
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Literal

from doctrine.agent_profiles.capabilities import DEFAULT_ROLE_CAPABILITIES
from doctrine.agent_profiles.profile import Role
from specify_cli.invocation.errors import RouterAmbiguityError
from specify_cli.invocation.registry import ProfileRegistry

# Stop-words to strip from request tokens
STOP_WORDS = frozenset({
    "a", "an", "the", "this", "that", "these", "those",
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "must", "can",
    "please", "kindly", "some", "for", "me", "us", "our", "my",
    "to", "and", "or", "in", "on", "at", "of", "with", "by",
})

# Maps normalized request token → canonical action token
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
    "outline": ("plan", Role.PLANNER),
    "schedule": ("plan", Role.PLANNER),
    "prioritize": ("plan", Role.PLANNER),
    "triage": ("plan", Role.PLANNER),
    "rank": ("plan", Role.PLANNER),
    # ARCHITECT / DESIGNER
    "specify": ("specify", Role.ARCHITECT),
    "spec": ("specify", Role.ARCHITECT),
    "define": ("specify", Role.ARCHITECT),
    "requirements": ("specify", Role.ARCHITECT),
    "scope": ("specify", Role.ARCHITECT),
    "design": ("specify", Role.DESIGNER),
    "mockup": ("specify", Role.DESIGNER),
    "prototype": ("specify", Role.DESIGNER),
    # RESEARCHER
    "analyze": ("analyze", Role.RESEARCHER),
    "investigate": ("analyze", Role.RESEARCHER),
    "research": ("analyze", Role.RESEARCHER),
    "explore": ("analyze", Role.RESEARCHER),
    "study": ("analyze", Role.RESEARCHER),
    "summarize": ("analyze", Role.RESEARCHER),
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


@dataclass(frozen=True)
class RouterDecision:
    profile_id: str
    action: str
    confidence: Literal["exact", "canonical_verb", "domain_keyword"]
    match_reason: str


def _normalize_tokens(text: str) -> list[str]:
    raw = re.split(r"[\s\W]+", text.lower())
    return [t for t in raw if t and t not in STOP_WORDS]


class ActionRouterPlugin:
    """No-op Protocol stub — reserved for future hybrid routing extension. Not called in v1."""


class ActionRouter:
    def __init__(self, registry: ProfileRegistry) -> None:
        self._registry = registry

    def route(
        self,
        request_text: str,
        profile_hint: str | None = None,
    ) -> RouterDecision:
        """
        Route request_text to a (profile_id, action) pair.
        Raises RouterAmbiguityError on no-match or ambiguous match.
        Never spawns an LLM call.
        """
        profiles = self._registry.list_all()
        if not profiles:
            raise RouterAmbiguityError(
                request_text,
                "ROUTER_NO_MATCH",
                [],
                "No profiles available. Run 'spec-kitty charter synthesize'.",
            )

        # Level 1: explicit hint
        if profile_hint is not None:
            from specify_cli.invocation.errors import ProfileNotFoundError
            try:
                profile = self._registry.resolve(profile_hint)
            except ProfileNotFoundError as e:
                raise RouterAmbiguityError(
                    request_text,
                    "PROFILE_NOT_FOUND",
                    [],
                    str(e),
                ) from e
            action = self._derive_action(request_text, profile.role)
            return RouterDecision(
                profile_id=profile.profile_id,
                action=action,
                confidence="exact",
                match_reason=f"explicit profile_hint '{profile_hint}'",
            )

        tokens = _normalize_tokens(request_text)

        # Level 2: canonical verb match
        verb_matches: dict[Role, tuple[str, str]] = {}  # role → (action, token)
        for token in tokens:
            if token in CANONICAL_VERB_MAP:
                action, role = CANONICAL_VERB_MAP[token]
                if role not in verb_matches:
                    verb_matches[role] = (action, token)

        # Level 3: domain keyword match
        keyword_matches: list[tuple[str, str, str]] = []  # (profile_id, action, keyword)
        for profile in profiles:
            # domain_keywords lives in specialization_context (SpecializationContext),
            # NOT in specialization (Specialization). Always check for None.
            sc = getattr(profile, "specialization_context", None)
            kws = list(sc.domain_keywords) if sc and sc.domain_keywords else []
            # Also check collaboration.canonical_verbs as profile-specific verb signals
            collab = getattr(profile, "collaboration", None)
            collab_verbs = list(collab.canonical_verbs) if collab and collab.canonical_verbs else []
            kws = kws + [v for v in collab_verbs if v not in kws]
            for kw in kws:
                if kw.lower() in tokens:
                    caps = DEFAULT_ROLE_CAPABILITIES.get(profile.role) if hasattr(profile, "role") else None
                    action = caps.canonical_verbs[0] if caps and caps.canonical_verbs else "advise"
                    keyword_matches.append((profile.profile_id, action, kw))

        # Resolve: find the single best match
        candidates: list[dict[str, str]] = []

        for role, (action, token) in verb_matches.items():
            role_profiles = [p for p in profiles if getattr(p, "role", None) == role]
            for p in role_profiles:
                candidates.append({
                    "profile_id": p.profile_id,
                    "action": action,
                    "match_reason": f"token '{token}' matched {role.value} canonical verb",
                    "_confidence": "canonical_verb",
                })

        for profile_id, action, kw in keyword_matches:
            if not any(c["profile_id"] == profile_id for c in candidates):
                candidates.append({
                    "profile_id": profile_id,
                    "action": action,
                    "match_reason": f"domain keyword '{kw}' matched",
                    "_confidence": "domain_keyword",
                })

        if len(candidates) == 1:
            c = candidates[0]
            return RouterDecision(
                profile_id=c["profile_id"],
                action=c["action"],
                confidence=c["_confidence"],  # type: ignore[arg-type]
                match_reason=c["match_reason"],
            )

        # No match or ambiguous
        if not candidates:
            raise RouterAmbiguityError(
                request_text,
                "ROUTER_NO_MATCH",
                [],
                "No profile matched. Use 'spec-kitty ask <profile> <request>' to be explicit.",
            )

        # Sort candidates by routing_priority (higher = preferred)
        sorted_candidates = sorted(
            candidates,
            key=lambda c: getattr(self._registry.get(c["profile_id"]), "routing_priority", 0),
            reverse=True,
        )
        top_priority = getattr(
            self._registry.get(sorted_candidates[0]["profile_id"]), "routing_priority", 0
        )
        top_candidates = [
            c for c in sorted_candidates
            if getattr(self._registry.get(c["profile_id"]), "routing_priority", 0) == top_priority
        ]

        if len(top_candidates) == 1:
            c = top_candidates[0]
            return RouterDecision(
                profile_id=c["profile_id"],
                action=c["action"],
                confidence=c["_confidence"],  # type: ignore[arg-type]
                match_reason=c["match_reason"] + " (selected by routing_priority)",
            )

        raise RouterAmbiguityError(
            request_text,
            "ROUTER_AMBIGUOUS",
            [
                {"profile_id": c["profile_id"], "action": c["action"], "match_reason": c["match_reason"]}
                for c in top_candidates
            ],
            "Multiple profiles matched. Use 'spec-kitty ask <profile> <request>' to be explicit.",
        )

    def _derive_action(self, request_text: str, role: object) -> str:
        tokens = _normalize_tokens(request_text)
        for token in tokens:
            if token in CANONICAL_VERB_MAP:
                action, mapped_role = CANONICAL_VERB_MAP[token]
                return action
        caps = DEFAULT_ROLE_CAPABILITIES.get(role) if isinstance(role, Role) else None
        if caps and caps.canonical_verbs:
            return caps.canonical_verbs[0]
        return "advise"
```

**Files**: `src/specify_cli/invocation/router.py`

---

## Subtask T009 — Wire Router into `executor.py`

**Purpose**: Update `ProfileInvocationExecutor` (created in WP01) so CLI commands can inject an `ActionRouter`. The executor's `invoke()` already has the `self._router` slot from WP01 — WP02 makes this functional.

**Steps**:

1. In `executor.py`, update the no-hint branch to use the real `ActionRouter`:
   - The existing code in WP01 already checks `self._router is not None`
   - Ensure it imports and uses `ActionRouter` correctly (not just the Protocol)
   - Add a deferred import: `from specify_cli.invocation.router import ActionRouter, RouterDecision`
   - The executor's `_router` slot accepts `ActionRouter | None`

2. Update `__init__` signature to clarify `router` type:
   ```python
   from specify_cli.invocation.router import ActionRouter
   def __init__(self, repo_root: Path, router: ActionRouter | None = None) -> None:
   ```

3. CLI commands (WP03/WP04) will pass `router=ActionRouter(registry)` to the executor. The tests in WP02 should inject the router directly to test the routing path.

**Files**: `src/specify_cli/invocation/executor.py` (modify WP01's version)

---

## Subtask T010 — `test_router.py` + ADR-3 Review Gate

**Purpose**: Table-driven tests covering all routing outcomes. The reviewer must confirm the ADR-3 document exists and was not overridden during implementation.

### Test cases (table-driven):

```python
@pytest.mark.parametrize("request_text,profile_hint,expected_profile,expected_action,expected_confidence", [
    # Case 1: Explicit hint bypasses router
    ("fix the auth bug", "implementer-fixture", "implementer-fixture", "implement", "exact"),
    # Case 2: Canonical verb match
    ("implement the payment module", None, "implementer-fixture", "implement", "canonical_verb"),
    # Case 3: Canonical verb match (reviewer)
    ("review WP03", None, "reviewer-fixture", "review", "canonical_verb"),
    # Case 4: Domain keyword match (if request has no canonical verb but a domain keyword)
    ("build something for code quality", None, "implementer-fixture", "implement", "canonical_verb"),
    # Case 5: Stop-word stripping ("please do an implement" still routes to implementer)
    ("please do an implement", None, "implementer-fixture", "implement", "canonical_verb"),
])
def test_router_success(request_text, profile_hint, expected_profile, expected_action, expected_confidence, ...):
    ...

def test_router_ambiguity_two_profiles_same_score(...):
    """Two profiles with equal routing_priority and overlapping verbs → ROUTER_AMBIGUOUS"""
    ...

def test_router_no_match_vague_request(...):
    """'help me' → ROUTER_NO_MATCH"""
    ...

def test_router_missing_profile_hint(...):
    """profile_hint='nonexistent' → RouterAmbiguityError(PROFILE_NOT_FOUND)"""
    ...
```

### ADR-3 review gate test:
```python
def test_adr3_document_exists():
    """Confirm ADR-3 is committed as required entry gate for this WP."""
    from pathlib import Path
    adr_path = Path("kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/adr-3-deterministic-action-router.md")
    assert adr_path.exists(), f"ADR-3 document not found at {adr_path}"
    content = adr_path.read_text()
    assert "Option A" in content, "ADR-3 must document Option A as the accepted decision"
    assert "no LLM" in content.lower() or "no lm" in content.lower()
```

**Files**: `tests/specify_cli/invocation/test_router.py`

**Acceptance**:
- [ ] All 7+ router test cases pass
- [ ] `test_adr3_document_exists` passes
- [ ] `mypy --strict` clean on `router.py`
- [ ] No LLM call anywhere in the router code path (assert via mock)

## Definition of Done

- [ ] `src/specify_cli/invocation/router.py` exists with `ActionRouter` and `CANONICAL_VERB_MAP`
- [ ] `executor.py` wired to accept `router=ActionRouter(registry)` from CLI commands
- [ ] All test cases in `test_router.py` pass
- [ ] `mypy --strict` clean

## Risks

- **Role enum type mismatches**: `CANONICAL_VERB_MAP` values use `Role` enum values. Confirm `Role` is the exact type from `profile.py` — not a string or custom type.
- **domain_keywords path**: `AgentProfile.specialization.domain_keywords` — verify the exact attribute path; it may be nested differently in the shipped profile YAML.
- **Routing priority conflicts**: The fallback to `routing_priority` tiebreaker may produce different results than expected if test fixture profiles have the same priority. Set `routing_priority` explicitly in test fixtures.

## Reviewer Guidance

1. Confirm ADR-3 doc exists and is not modified (check the timestamp).
2. Verify `CANONICAL_VERB_MAP` matches the alias table in ADR-3 doc.
3. Verify no `httpx`, `anthropic`, or LLM client import anywhere in `router.py`.
4. Verify `ActionRouterPlugin` is a no-op Protocol (no methods, not called).
5. Verify routing_priority tiebreaker works correctly in the ambiguity case.

## Activity Log

- 2026-04-21T12:09:47Z – claude:sonnet-4-6:implementer:implementer – shell_pid=76739 – Started implementation via action command
- 2026-04-21T12:16:05Z – claude:sonnet-4-6:implementer:implementer – shell_pid=76739 – WP02 complete: ActionRouter with CANONICAL_VERB_MAP (59 entries), executor wired with real import, 21 table-driven tests, ADR-3 doc gate test passes, mypy --strict clean on router.py
- 2026-04-21T12:16:48Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=78980 – Started review via action command
