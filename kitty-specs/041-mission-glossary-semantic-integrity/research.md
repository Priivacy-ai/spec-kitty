# Research: Glossary Semantic Integrity Runtime

**Feature**: 041-mission-glossary-semantic-integrity
**Date**: 2026-02-16
**Status**: Complete

## Research Goals

1. Understand middleware integration points in spec-kitty 2.x mission primitive execution
2. Extract canonical event schemas from Feature 007 (spec-kitty-events package)
3. Research deterministic term extraction patterns
4. Identify best practices for hierarchical glossary scope resolution
5. Define minimal checkpoint state for deterministic resume

---

## Finding 1: Middleware Architecture (B + D Hybrid)

**Question**: How should glossary checks integrate with mission primitive execution?

**Research**:
- Reviewed spec-kitty 2.x mission framework architecture
- Primitives are config-defined (YAML/JSON), not stable Python class hierarchy
- Need synchronous gate behavior (block generation, prompt, resume) - pure event-driven can't enforce this
- Middleware provides one consistent execution choke point for all primitive types

**Decision**: **B + D Hybrid** - Middleware chain as primary control path + Event emission at boundaries

**Rationale**:
- Middleware gives synchronous control (can block generation deterministically)
- Config-driven primitives don't have stable decorators/base classes to attach to
- Events provide observability/audit/replay (Feature 007 requirement)
- Eventing is for telemetry, not enforcement mechanism

**Middleware Pipeline Design**:

```
PrimitiveExecutionContext (from mission config + step metadata)
    ↓
GlossaryCandidateExtractionMiddleware (pre-step)
    ↓ emits: TermCandidateObserved (for each extracted term)
SemanticCheckMiddleware (pre-generation)
    ↓ emits: SemanticCheckEvaluated (with findings)
GenerationGateMiddleware (block on unresolved high severity)
    ↓ emits: GenerationBlockedBySemanticConflict (if blocked)
ClarificationMiddleware (interactive or defer async)
    ↓ emits: GlossaryClarificationRequested, GlossaryClarificationResolved
ResumeMiddleware (checkpoint continue after resolution)
    ↓ emits: GlossarySenseUpdated (if custom sense provided)
```

**Alternatives Rejected**:
- (A) Decorator pattern: Brittle for config-driven primitives, dynamic loading issues
- (C) Base class hooks: Forces class model that mission system doesn't require
- (D) Pure event-driven: Cannot guarantee inline block/resume semantics (async subscribers can't block)

**Implementation Note**: Middleware attaches to primitive execution via metadata flag: `glossary_check: enabled` in mission.yaml step definitions.

---

## Finding 2: Event Contracts (A + C: Reference Feature 007)

**Question**: Where are canonical glossary event schemas defined?

**Research**:
- Feature 007 spec reviewed: `/Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty-planning/product-ideas/prd-mission-glossary-semantic-integrity-v1.md`
- Canonical events defined in Section 10 (Domain events)
- Events live in `spec-kitty-events` package (private Git dependency per ADR-11)

**Decision**: **A + C** - CLI references/imports events from spec-kitty-events package (not redefining)

**Canonical Event Schemas** (from Feature 007):

1. **GlossaryScopeActivated**:
   - Trigger: Mission starts or scope selected
   - Required: scope_id, glossary_version_id

2. **TermCandidateObserved**:
   - Trigger: New/uncertain term appears in input
   - Required: term, source_step, actor_id, confidence

3. **SemanticCheckEvaluated**:
   - Trigger: Step-level pre-generation validation
   - Required: severity, confidence, conflict_list, recommended_action
   - Consumers: Execution gate, UX prompt

4. **GlossaryClarificationRequested**:
   - Trigger: Policy requires user clarification
   - Required: question, term, options, urgency

5. **GlossaryClarificationResolved**:
   - Trigger: User/participant answer accepted
   - Required: selected/entered meaning, actor_id

6. **GlossarySenseUpdated**:
   - Trigger: New sense or sense edit accepted
   - Required: before/after, reason, actor_id

7. **GenerationBlockedBySemanticConflict**:
   - Trigger: High-severity unresolved conflict at generation boundary
   - Required: step_id, conflicts, blocking_policy_mode

**Rationale**:
- Feature 007 is authoritative source for glossary events
- Prevents contract drift between CLI and SaaS (both use same events package)
- Enables deterministic replay (events are append-only, immutable)

**Alternatives Rejected**:
- (B) Define schemas inline in CLI: Causes contract drift, breaks SaaS integration
- (D) Stub contracts temporarily: Defers integration, blocks replay/audit features

**Implementation Note**: Import events from `spec_kitty_events.glossary.events` module. If Feature 007 package not yet published, stub adapter boundaries and gate implementation on package availability.

---

## Finding 3: Term Extraction (D: Metadata hints + deterministic heuristics)

**Question**: How do we extract candidate terms from step inputs/outputs?

**Research**:
- NLP libraries (spaCy, NLTK): High accuracy but adds dependency weight (~100MB models)
- LLM extraction: Best quality but adds latency (200-500ms) and cost
- Pattern-based heuristics: Fast (< 10ms) but lower recall without context

**Decision**: **D: Hybrid** - Metadata hints (highest confidence) + Deterministic heuristics + Scope-aware normalization

**S2 Extraction Stack**:

1. **Metadata hints (highest confidence)**:
   - `glossary_watch_terms`: Explicit terms to track (e.g., ["workspace", "mission", "primitive"])
   - `glossary_aliases`: Known synonyms (e.g., {"WP": "work package"})
   - `glossary_exclude_terms`: Common words to ignore (e.g., ["the", "and", "it"])
   - `glossary_fields`: Which input/output fields to scan (e.g., ["description", "requirements"])

2. **Deterministic heuristics**:
   - Quoted phrases: "workspace" → extract as term
   - Acronyms: WP, LLM, CLI → extract (uppercase 2-5 chars)
   - Casing patterns: snake_case, camelCase, kebab-case → extract
   - Repeated noun-like phrases: term appears 3+ times → extract
   - Existing glossary matches: term already in any scope → extract

3. **Scope-aware normalization**:
   - Lowercase + trim whitespace
   - Stem-light: workspace/workspaces → workspace (plural → singular)
   - Resolve against scope order: mission_local → team_domain → audience_domain → spec_kitty_core

4. **Confidence scoring**:
   - **High**: metadata hint, existing glossary match
   - **Medium**: quoted phrase, acronym, casing pattern
   - **Low**: repeated noun-like phrase (weak heuristic)

5. **Escalation policy**:
   - High-severity + low-confidence critical term → immediate clarification (blocks generation)
   - All other conflicts → auto-add as draft, continue execution (warn only)

**Rationale**:
- Keeps extraction automatic and mostly invisible (no LLM latency)
- Better precision than raw heuristics via mission metadata
- No heavy NLP dependencies (stays lightweight)
- Opt-in enrichment path: async LLM pass can enhance drafts later (not in hot path)

**Alternatives Rejected**:
- (A) NLP-based (spaCy/NLTK): Adds 100MB+ dependency, slower (50-100ms), overkill for S2
- (B) LLM-based extraction: High quality but 200-500ms latency + cost in hot path
- (C) Pattern-based only: Low precision without metadata context, high false-positive rate

**Implementation Note**: Package in `src/specify_cli/glossary/extraction.py`. Heuristics are pluggable (can add NLP/LLM extractors later without breaking existing code).

---

## Finding 4: Checkpoint/Resume (A: Lightweight event sourcing)

**Question**: How do we save/restore step execution state for resume after conflict resolution?

**Research**:
- Feature 007 invariant #6: "Mission run state is reconstructable from event stream"
- Event sourcing: State is derived from event log, not separate files
- Checkpoint granularity: Generation boundary only (not every statement)

**Decision**: **A: Lightweight event sourcing** - Emit `StepCheckpointed` event before generation gate

**Checkpoint Payload** (minimal deterministic resume context):

```python
StepCheckpointed(
    mission_id: str,           # Which mission
    run_id: str,               # Which run instance
    step_id: str,              # Which step
    strictness: Strictness,    # Resolved strictness mode (off/medium/max)
    scope_refs: List[ScopeRef],  # Active glossary scope versions
    input_hash: str,           # SHA256 of step inputs (detect context changes)
    cursor: str,               # Execution stage: "pre_generation_gate"
    retry_token: str,          # Unique token for this checkpoint (UUID)
    timestamp: datetime,       # When checkpoint created
)
```

**Resume Flow**:

1. User resolves conflict (selects sense or provides custom definition)
2. Emit `GlossaryClarificationResolved` or `GlossarySenseUpdated` event
3. Load `StepCheckpointed` event from log (latest for this step_id)
4. Verify input_hash matches current inputs (detect context changes)
   - If changed: prompt user for confirmation before resuming
   - If unchanged: resume from cursor ("pre_generation_gate")
5. Re-run generation gate with updated glossary state
6. If pass: proceed to generation; If fail: clarification loop continues

**Cross-session resume**:
- State persists in event log (not in-memory)
- User can close CLI, resolve conflict in SaaS, reopen CLI
- Resume loads checkpoint from events, continues execution

**Rationale**:
- Event log is source of truth (Feature 007 requirement)
- Minimal payload (only IDs + refs, no full step state)
- Supports async defer + cross-session resume
- Deterministic replay (same events → same state)

**Alternatives Rejected**:
- (B) Filesystem state file: Conflicts with "no side-channel state" invariant
- (C) In-memory cache: Fails async defer + cross-session resume (state lost on CLI exit)
- (D) Re-run with inputs: Fragile unless all steps fully idempotent and cheap (not safe default)

**Implementation Note**: Checkpoint only at generation boundary (not every middleware layer). Resume is opt-in (only if user resolves conflict, not automatic retry).

---

## Finding 5: Interactive Prompts (B: Typer prompts + Rich formatting)

**Question**: How should CLI implement interactive clarification prompts?

**Research**:
- Existing spec-kitty patterns: typer.confirm/prompt used in `upgrade.py`, `orchestrate.py`
- Rich already used for console output (tables, progress bars, colors)
- Questionary: Nice UX but adds new dependency

**Decision**: **B: Typer prompts for input, Rich for formatting/output** (no new dependencies)

**Recommended Flow**:

1. **Sort conflicts by severity** (high → medium → low), cap to 3 max

2. **Render each conflict with Rich**:
   ```
   🔴 High-severity conflict: "workspace"

   Term: workspace
   Context: "The workspace contains the implementation files"
   Scope: mission_local (no match), team_domain (2 matches)

   Candidate senses:
   1. [team_domain] Git worktree directory for a work package (confidence: 0.9)
   2. [team_domain] VS Code workspace configuration file (confidence: 0.7)
   ```

3. **Prompt with typer.prompt()**:
   ```python
   choice = typer.prompt(
       "Select: 1-2 (candidate), C (custom sense), D (defer to async)",
       type=str
   )
   ```

4. **Handle choice**:
   - `1-N`: Select candidate sense → emit `GlossaryClarificationResolved`
   - `C`: Prompt for custom sense text → emit `GlossarySenseUpdated`
   - `D`: Defer to async → emit `GlossaryClarificationRequested` + exit with blocked status

5. **Resume confirmation** (if context changed):
   ```python
   proceed = typer.confirm(
       "Context may have changed since conflict. Proceed with resolution?"
   )
   ```

**Non-interactive mode**:
- Auto-defer all conflicts
- Emit `GlossaryClarificationRequested` for all high-severity conflicts
- Keep generation blocked (exit with error code)

**Rationale**:
- Matches existing CLI interaction patterns (consistency)
- No new dependencies (typer, rich already in spec-kitty)
- Enough capability for ranked options + custom input + defer flow
- Simple to test (mock typer.prompt, assert Rich output)

**Alternatives Rejected**:
- (A) Rich + questionary: Adds new dependency, overkill for 1-3 questions
- (C) Custom Rich prompts: Reinventing wheel (typer.prompt works fine)
- (D) AskUserQuestion tool: Unclear if exists in codebase, would need research

**Implementation Note**: Package in `src/specify_cli/glossary/clarification.py`. Use Rich tables for candidate rendering, typer.prompt for input, typer.confirm for resume confirmation.

---

## Summary of Key Decisions

| Decision Area | Choice | Rationale |
|---------------|--------|-----------|
| **Architecture** | B + D Hybrid (middleware + events) | Synchronous gate control, config-driven primitives, event observability |
| **Event Contracts** | A + C (reference Feature 007) | Prevent contract drift, enable SaaS integration, deterministic replay |
| **Term Extraction** | D (metadata hints + heuristics) | Automatic, fast (< 100ms), no LLM latency, good precision with metadata |
| **Checkpoint/Resume** | A (lightweight event sourcing) | Event log is source of truth, supports cross-session, minimal payload |
| **Interactive Prompts** | B (Typer + Rich) | Matches existing patterns, no new dependencies, simple to test |

All decisions align with Sprint S2 requirements: automatic glossary capture, mostly invisible process, low-friction clarifications, deterministic replay.

---

## Next Steps

Proceed to Phase 1: Design & Contracts
- Generate data-model.md (entity definitions)
- Generate contracts/events.md (canonical event schemas)
- Generate contracts/middleware.md (interface definitions)
- Generate quickstart.md (developer setup)
