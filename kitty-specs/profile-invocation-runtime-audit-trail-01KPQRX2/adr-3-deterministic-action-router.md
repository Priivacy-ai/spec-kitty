# ADR-3: Deterministic Action Router for Phase 4 Runtime

**Status**: Accepted  
**Date**: 2026-04-21  
**Mission**: `profile-invocation-runtime-audit-trail-01KPQRX2`  
**Resolves**: GitHub issue #519 ([ADR-3] Profile action router design)  
**Gates**: WP4.2 implementation  

---

## Context

`ProfileInvocationExecutor` needs to map a natural-language request string (e.g., `"implement the payment module"`) to a resolved `(profile_id, action)` pair. Issue #519 identified three candidate approaches and left the choice open. This ADR closes that choice for the 3.2.0 release.

The primary constraint from issue #466 is: **"Spec Kitty must not spawn a parallel LLM call when a host LLM is already engaged."** This invariant rules out Option B (LLM call in the routing path) as a v1 choice for any path where the caller may already be a running LLM agent.

### Options Considered

**Option A — Deterministic verb-mapping table**
Pure function over canonical role verbs (`DEFAULT_ROLE_CAPABILITIES.canonical_verbs`) and profile domain keywords (`AgentProfile.specialization.domain_keywords`). No external calls. On ambiguity or no match, returns a structured error directing the caller to use `spec-kitty ask <profile>`.

**Option B — Constrained-vocabulary LLM call**
Spec Kitty calls a small LLM to classify the request. Fast and flexible, but introduces an LLM dependency in the routing path — directly violating the no-parallel-LLM invariant from #466.

**Option C — Hybrid: deterministic primary, LLM fallback**
Option A for all resolvable cases; LLM fallback only on `ROUTER_NO_MATCH`. Correct long-term, but adds a live-model dependency to CI testing and increases the scope of the smallest releaseable chunk.

---

## Decision

**Option A — Deterministic verb-mapping table, no LLM call in routing path.**

This is the 3.2.0 v1 choice. The hybrid fallback (Option C) remains explicitly open for a future release after real invocation/event data shows where the table's coverage gaps are.

---

## Routing Algorithm

The router is a pure Python function: `route(request_text: str, profile_hint: str | None = None) -> RouterDecision | RouterAmbiguityError`. No I/O, no network.

### Precedence (evaluated in order, first match wins)

**Level 1 — Explicit profile hint**: if `profile_hint` is supplied, resolve the profile via `AgentProfileRepository.get(hint)`. Derive the action from the normalized request tokens using `DEFAULT_ROLE_CAPABILITIES[profile.role].canonical_verbs`. If the profile hint does not resolve, return `RouterAmbiguityError(error_code="PROFILE_NOT_FOUND")`. Confidence: `"exact"`.

**Level 2 — Canonical verb match**: normalize request tokens (lowercase, split on `r'[\s\W]+'`, drop stop-words). Look up each token against `CANONICAL_VERB_MAP` (see below). For each mapping entry found, collect the corresponding role. If exactly one role maps to exactly one available profile, return `RouterDecision(confidence="canonical_verb")`.

**Level 3 — Domain keyword match**: for each profile in the repository, check whether any `AgentProfile.specialization.domain_keywords` entry appears in the normalized token set. Score by `routing_priority`. If exactly one profile has the highest score, return `RouterDecision(confidence="domain_keyword")`.

**Level 4 — Ambiguity or no match**: if zero profiles match or multiple profiles tie, return `RouterAmbiguityError` with candidates and suggestion.

### CANONICAL_VERB_MAP

| Request token(s) | Canonical action | Mapped role |
|-----------------|-----------------|------------|
| implement, build, code, develop, create, write | implement | IMPLEMENTER |
| generate, produce, output | implement | IMPLEMENTER |
| refine, improve, fix, patch, repair, debug | implement | IMPLEMENTER |
| review, check, inspect, evaluate | review | REVIEWER |
| audit, assess | review | REVIEWER |
| plan, decompose, break, outline, schedule | plan | PLANNER |
| prioritize, triage, rank, order | plan | PLANNER |
| specify, spec, define, requirements, scope | specify | ARCHITECT |
| design, mockup, prototype, wireframe | specify | DESIGNER |
| analyze, investigate, research, explore, study | analyze | RESEARCHER |
| summarize, synthesize, compile, report | analyze | RESEARCHER |
| curate, classify, organize, tag, validate, verify | curate | CURATOR |
| coordinate, manage, delegate, monitor, track | coordinate | MANAGER |

### Token normalization

```python
STOP_WORDS = frozenset({
    "a", "an", "the", "this", "that", "these", "those",
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "must", "can",
    "please", "kindly", "some", "for", "me", "us", "our", "my",
})

def normalize_tokens(text: str) -> list[str]:
    raw = re.split(r'[\s\W]+', text.lower())
    return [t for t in raw if t and t not in STOP_WORDS]
```

### Action normalization

Canonical action tokens:
`implement | review | plan | specify | analyze | design | curate | coordinate | advise`

The resolved action is stored in `InvocationRecord.action`. Unknown verb tokens that do not map to a canonical token are stored as-is (pass-through).

### Ambiguity payload

When multiple canonical verbs map to different roles that each have exactly one profile:
```json
{
  "error_code": "ROUTER_AMBIGUOUS",
  "candidates": [
    {"profile_id": "cleo", "action": "implement", "match_reason": "token 'create' matched IMPLEMENTER"},
    {"profile_id": "pedro", "action": "review", "match_reason": "domain keyword 'quality' matched reviewer profile"}
  ],
  "suggestion": "Use 'spec-kitty ask <profile> <request>' to specify a profile explicitly."
}
```

---

## Future Extension Point

`ActionRouter.__init__` accepts `router_plugin: ActionRouterPlugin | None = None`. `ActionRouterPlugin` is a no-op `Protocol` with no methods in v1. A future hybrid release will implement this protocol to add an LLM fallback path that activates only on `ROUTER_NO_MATCH`.

This slot is documented, never called in v1, and its existence does not affect routing behavior.

---

## Consequences

**Positive**:
- The routing path has zero external calls — fully testable offline, CI-safe.
- Preserves the no-parallel-LLM invariant from #466.
- Smallest releaseable chunk for 3.2.0: no new runtime model dependency.
- Future hybrid upgrade is additive (fill in the plugin slot) with no interface change.

**Negative**:
- Requests that do not contain canonical verbs or profile domain keywords produce `ROUTER_NO_MATCH`. Operators must use `ask <profile>` explicitly.
- Coverage gaps will only be visible once real invocation event data accumulates. The index at `.kittify/events/invocation-index.jsonl` can be mined for common `ROUTER_NO_MATCH` patterns as a signal for expanding the alias table.

**Accepted trade-off**: a higher `ROUTER_NO_MATCH` rate in v1 is acceptable because the operator fallback (`ask <profile>`) is well-defined and low-friction. The hybrid upgrade can be driven by real data rather than guessing at coverage needs upfront.

---

## Reviewer sign-off required

This ADR must be reviewed and accepted before WP4.2 implementation is opened for review.

| Reviewer | Status |
|----------|--------|
| Robert Douglass | Confirmed via planning interrogation (2026-04-21) |
