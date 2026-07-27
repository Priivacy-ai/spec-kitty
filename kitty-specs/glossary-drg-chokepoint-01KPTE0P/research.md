# Research: Glossary DRG Residence and Executor Chokepoint

**Mission:** `glossary-drg-chokepoint-01KPTE0P`
**Date:** 2026-04-22
**Status:** Complete — all decisions resolved during planning interrogation.

---

## Decision 1 — DRG Population Model

**Decision:** Runtime-computed in-memory layer (not persisted YAML).

**Approach:** A new `GlossaryDRGBuilder` function materializes `DRGNode` / `DRGEdge` / `DRGGraph` objects from the active `GlossaryStore` at executor construction time. These are real domain objects using the existing `doctrine.drg.models` types. No `.kittify/doctrine/graph.yaml` is written; no new CLI command is introduced. The builder function is reusable: WP02 consumes it for the `GlossaryTermIndex`; a future WP5.5 entity-page renderer can consume the same builder without model changes. Persistence can be added later as an export/cache concern if operators need it.

**Why:** FR-013 and FR-015 require "rebuildable on demand, no operator action." A persisted YAML model would impose sync discipline on operators and require a new `spec-kitty glossary drg-sync` command. The runtime-computed model satisfies all acceptance gates without that burden. Vocabulary freshness is guaranteed because the index is always built from the live glossary store.

**Alternatives rejected:**
- Persisted YAML in `.kittify/doctrine/graph.yaml`: requires a sync command, operator maintenance, and reopens charter-sync plumbing. Rejected.

---

## Decision 2 — `glossary:<id>` URN Derivation

**Decision:** `glossary:<sha256(canonical_surface, utf-8)[:8]>` — 8 lowercase hex characters derived from the canonical surface form.

**Approach:** `canonical_surface = term.surface.surface_text` (already normalized to lowercase, trimmed). The ID is `hashlib.sha256(canonical_surface.encode()).hexdigest()[:8]`. Example: "lane" → `glossary:d93244e7`. The derivation is deterministic and stable: the same term always produces the same URN across process restarts and store rebuilds.

**Collision probability:** With 8 hex chars (4 billion space), expected collision with 10,000 terms is ~1.2×10⁻⁵. Negligible for any realistic glossary. If a collision is detected at index build time, the builder logs a warning and retains the first term (predictable, deterministic behavior).

**NodeKind value:** The existing `NodeKind` StrEnum validates that `urn.split(":")[0] == kind.value`. To produce `glossary:` URN prefixes, the new enum member must have value `"glossary"`:
```python
GLOSSARY = "glossary"   # NodeKind.GLOSSARY, URN prefix: "glossary:"
```
This is the only clean path through the existing URN validator without relaxing the validator itself. The attribute name `GLOSSARY` is descriptive in context.

**Alternatives rejected:**
- Sequential integer IDs: not stable across store rebuilds (different insertion order). Rejected.
- ULIDs: non-deterministic (time-based). Rejected.
- `NodeKind.GLOSSARY_TERM = "glossary_term"` with `glossary_term:` URNs: would contradict the spec's `glossary:<id>` notation. The DRG validator enforces `urn_prefix == kind.value`, so this would require `glossary_term:` URNs everywhere. Rejected in favour of `NodeKind.GLOSSARY = "glossary"` which produces `glossary:` URNs as specified.

---

## Decision 3 — Lemmatization Strategy

**Decision:** Pure Python suffix-stripping with no new library dependencies.

**Rules applied after lowercasing (in order, first match with stem ≥ 3 chars wins):**
1. Strip multi-char suffixes first: `-ments`, `-ment`, `-tions`, `-tion`, `-ness`, `-ings`, `-ing`, `-ers`, `-ed`, `-er`
2. Strip `-s` last (handles "lanes" → "lane", "missions" → "mission")
3. The `-es` rule is intentionally absent — applying it before `-s` would produce "lan" from "lanes" (incorrect). The simple `-s` rule suffices for Spec Kitty's domain terms.
4. Normalize hyphens and underscores to spaces; split on whitespace and punctuation

**Rationale:** The existing codebase (`extraction.py`) already uses regex-based patterns with no NLP library. Adding NLTK or spaCy for lemmatization would be a significant dependency. Suffix stripping is sufficient for the chokepoint's purpose — detecting known glossary terms in request text. Operators who want variant forms (e.g., "worktrees" → "worktree") can list them as aliases in seed files.

**Alternatives rejected:**
- NLTK PorterStemmer: heavyweight dep, not in project. Rejected.
- spaCy: heavyweight dep, wrong scale for this use case. Rejected.
- Exact-match only (no stemming): too narrow. "lanes" would not match "lane". Rejected.

---

## Decision 4 — Vocabulary Applicability for v1

**Decision:** All `spec_kitty_core` and `team_domain` senses are applicable to every action node (broad). `mission_local` and `audience_domain` terms are excluded from the static builder layer for this tranche.

**Rationale:** The simplest model that satisfies FR-003's "for this tranche" qualifier. The action-scoped term set for any action URN is: all active `spec_kitty_core` + `team_domain` senses in the `GlossaryStore`. This can be tightened in a follow-on (e.g., per-action allow-lists in seed files) without changing the builder's interface.

**v1 applicability rule:** `applicable = {s for s in all_senses if s.scope in (SPEC_KITTY_CORE, TEAM_DOMAIN) and s.status == ACTIVE}`

---

## Decision 5 — Glossary Observation Trail Integration

**Decision:** Append a third JSONL line (event `"glossary_checked"`) to the existing per-invocation file immediately after `write_started()`.

**Rationale:** The invocation file at `.kittify/events/profile-invocations/{invocation_id}.jsonl` uses an append-only pattern. A third event type is additive — readers that only understand `started`/`completed` events will skip unrecognized events. No modification to the frozen `InvocationRecord` Pydantic model is needed. The writer method `write_glossary_observation()` serializes the bundle directly to dict and appends it.

**JSONL line schema (new event type):**
```json
{
  "event": "glossary_checked",
  "invocation_id": "<ulid>",
  "duration_ms": 12.4,
  "tokens_checked": 47,
  "matched_urns": ["glossary:d93244e7"],
  "high_severity_count": 1,
  "all_conflict_count": 2,
  "error_msg": null,
  "conflicts": [
    {"urn": "glossary:d93244e7", "term": "lane", "conflict_type": "inconsistent", "severity": "high", "confidence": 0.9}
  ]
}
```

**Alternatives rejected:**
- Adding `glossary_observations` field to `InvocationRecord`: requires modifying the frozen Pydantic model and changing the v1 schema. Schema version bump would be needed. Rejected.
- Separate log file per invocation: fragments the audit trail. Rejected.

---

## Decision 6 — InvocationPayload Extension

**Decision:** Add `glossary_observations` as a new slot in `InvocationPayload.__slots__`. Type: `GlossaryObservationBundle` (never `None`).

**Rationale:** `InvocationPayload.to_dict()` iterates `self.__slots__`, so any new slot automatically appears in the dict output. Existing callers receive a new key `"glossary_observations"` in the dict — additive and backward-compatible. The bundle is always set: an empty bundle (no conflicts) when the chokepoint finds nothing, an error-bundle when it fails.

---

## Decision 7 — Exception Boundary

**Decision:** A `try/except Exception` wraps the entire chokepoint call in `ProfileInvocationExecutor.invoke()`. On any exception: log `WARNING` via `logging.getLogger`, assign `GlossaryObservationBundle(error_msg=repr(exc), high_severity=(), all_conflicts=(), ...)` to the payload, and continue. The invocation is never blocked or interrupted.

**Why:** FR-010 and C-001 require this. The chokepoint is infrastructure layered over the critical invocation path — its failure must never degrade the invocation.

---

## Decision 8 — Index Caching Scope

**Decision:** Per-executor-instance cache via a lazily initialized instance variable (`self._term_index: GlossaryTermIndex | None = None`). The index is built on first `run()` call and reused for all subsequent calls on the same executor.

**Rationale:** FR-013 specifies "lifetime of the executor instance." CLI processes construct one executor per command, so the index is built at most once per command — acceptable cost. Module-level caching would risk stale data in test scenarios where the store is mutated between tests. Per-instance lazy init is the safest default.

---

## Decision 9 — ADR-5 Timing

**Decision:** ADR-5 ("Glossary Chokepoint p95 Measurement") is drafted in WP02 after benchmarking against real inputs. The p95 ≤ 50ms target is an assumption (A-1 in the spec) that WP02 must validate. If benchmarks show the target is unachievable, ADR-5 documents the revised threshold and rationale.

**Benchmark inputs:** 500 active `spec_kitty_core` + `team_domain` senses; request texts of 50, 500, and 2,000 words; repeated 1,000 times per input size.

---

## Dependency Audit

| Dependency | Status | Notes |
|-----------|--------|-------|
| `doctrine.drg.models` (`DRGNode`, `DRGEdge`, `DRGGraph`, `NodeKind`, `Relation`) | Existing — extend `NodeKind` | Add `GLOSSARY = "glossary"` enum member |
| `specify_cli.glossary.models` (`TermSense`, `SemanticConflict`, `Severity`, `ConflictType`) | Existing — no changes | Used as-is by the chokepoint |
| `specify_cli.glossary.scope` (`GlossaryScope`, `SCOPE_RESOLUTION_ORDER`) | Existing — no changes | Used to filter applicable senses |
| `specify_cli.glossary.store` (`GlossaryStore`) | Existing — no changes | Source of truth for active senses |
| `specify_cli.invocation.executor` (`ProfileInvocationExecutor`) | Existing — modify `invoke()` and `InvocationPayload` | Add chokepoint call + `glossary_observations` slot |
| `specify_cli.invocation.writer` (`InvocationWriter`) | Existing — add `write_glossary_observation()` | New method only; no existing methods changed |
| `hashlib` (stdlib) | Stdlib — no new dep | Used for `glossary:<id>` URN derivation |
| `time` (stdlib) | Stdlib — no new dep | Used for `duration_ms` measurement |
