# Implementation Plan: Glossary Semantic Integrity Runtime for Mission Framework

**Branch**: `041-mission-glossary-semantic-integrity` | **Date**: 2026-02-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/041-mission-glossary-semantic-integrity/spec.md`

## Summary

Implement a glossary semantic integrity runtime system that enforces semantic consistency in mission execution by attaching term resolution and conflict detection to mission primitives. The system uses a middleware chain architecture to extract terms from step inputs/outputs, resolve against a 4-tier scope hierarchy, detect semantic conflicts, block LLM generation on high-severity issues, and prompt users for interactive clarification with checkpoint/resume capability. All state is stored in the event log using Feature 007 canonical contracts (no side-channel state).

**Primary capabilities**: Metadata-driven check attachment, automatic term extraction, scope-aware resolution (mission_local → team_domain → audience_domain → spec_kitty_core), 4 conflict types detection, 3 strictness modes (off/medium/max), hybrid interactive/async clarification flow, event-sourced checkpoint/resume.

**Technical approach**: Middleware pipeline with 5 layers (extraction → semantic check → generation gate → clarification → resume), deterministic heuristics + metadata hints for term extraction (no LLM in hot path), event sourcing for checkpoint (minimal payload at generation boundary), Typer prompts + Rich formatting for CLI interaction, Feature 007 canonical event contracts for observability/audit/replay.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement from constitution)
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (seed file parsing), spec-kitty-events (Feature 007 canonical event contracts via Git dependency per ADR-11)
**Storage**: Event log only (JSONL via spec-kitty-events), optional seed files (`.kittify/glossaries/{scope}.yaml`)
**Testing**: pytest with 90%+ coverage (constitution requirement), mypy --strict (no type errors), integration tests for full middleware pipeline
**Target Platform**: Cross-platform (Linux, macOS, Windows 10+ per constitution)
**Project Type**: Single project (CLI library extension, not separate web/mobile app)
**Performance Goals**:
- Term extraction < 100ms per step (deterministic heuristics, no LLM)
- Clarification prompt display < 500ms (Rich rendering)
- Checkpoint/resume < 200ms (minimal payload)
- Event emission < 50ms (append-only JSONL)
**Constraints**:
- No side-channel state (event log is source of truth per Feature 007 invariant #6)
- No LLM in runtime hot path (async enrichment only)
- Default behavior "mostly invisible" (auto-capture, only block on high-severity)
- Strictness precedence: global → mission → step → runtime override
**Scale/Scope**:
- Support 100+ mission primitives (metadata-driven attachment)
- Handle 1000+ terms per glossary scope (efficient lookup)
- 3 strictness modes, 4 scope levels, 4 conflict types

**Integration Points**:
- Mission primitive execution context (middleware injection point)
- Feature 007 event contracts (import from spec-kitty-events package)
- Existing typer CLI commands (extend with clarification prompts)
- Existing rich console output (extend with ranked candidate rendering)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Dependencies

✅ **Python 3.11+**: Aligned with constitution requirement
✅ **typer, rich**: Existing spec-kitty dependencies (no new framework surface)
✅ **ruamel.yaml**: Already used for frontmatter parsing in spec-kitty
✅ **spec-kitty-events**: Git dependency per ADR-11 dual-repository pattern (commit-pinned for determinism)

**New dependency**: None (all dependencies already in spec-kitty or spec-kitty-events)

### Testing Requirements

✅ **pytest with 90%+ coverage**: Will cover all middleware layers, term extraction, conflict detection, clarification flow
✅ **mypy --strict**: All new code will have type annotations
✅ **Integration tests**: Full pipeline tests (term extraction → gate → clarification → resume)
✅ **Unit tests**: Term extraction heuristics, conflict scoring, scope resolution

### Performance Requirements

✅ **CLI operations < 2 seconds**: Term extraction and semantic check are deterministic (no LLM), designed for < 100ms per step
✅ **No lag on 100+ work packages**: Glossary checks are step-scoped, don't accumulate state across WPs

### Architecture Alignment

✅ **2.x branch target**: This is a 2.x feature (event sourcing, spec-kitty-events integration)
✅ **Event sourcing with Lamport clocks**: Uses Feature 007 canonical events from spec-kitty-events
✅ **No 1.x compatibility constraints**: Greenfield implementation for 2.x

### Deployment Constraints

✅ **Cross-platform**: Pure Python, no platform-specific dependencies
✅ **PyPI distribution**: Will vendor spec-kitty-events per constitution Section 103 (until events goes public)

### Code Quality

✅ **Type annotations**: All middleware classes, term extraction, conflict detection
✅ **Docstrings**: Public API (middleware interfaces, event emission helpers)
✅ **No security issues**: No credential handling, no secrets (glossary terms are user-visible domain language)

### Breaking Changes

⚠️ **Behavior change**: Glossary checks enabled by default (opt-out model) - impacts all mission primitives unless strictness=off

**Justification**: Spec says "mostly invisible" and "automatic glossary capture" (FR-020). Default-enabled aligns with "automatic by default" design intent from Sprint S2 kickoff.

**Migration**: Provide global config option to disable: `strictness: off` in `.kittify/config.yaml` for users who want opt-in behavior.

### Verdict

✅ **PASS**: All constitution requirements met. One behavior change (default-enabled checks) justified by spec requirements and mitigated with config option.

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/041-mission-glossary-semantic-integrity/
├── spec.md              # Feature specification (created by /spec-kitty.specify)
├── plan.md              # This file (created by /spec-kitty.plan)
├── research.md          # Phase 0 output (architectural research)
├── data-model.md        # Phase 1 output (entities and event contracts)
├── quickstart.md        # Phase 1 output (developer quickstart)
├── contracts/           # Phase 1 output (event schema examples)
│   ├── events.md        # Canonical event reference (Feature 007)
│   └── middleware.md    # Middleware interface contracts
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/
├── glossary/                      # NEW: Glossary semantic integrity package
│   ├── __init__.py               # Public API exports
│   ├── middleware.py             # Middleware pipeline components
│   │   ├── GlossaryCandidateExtractionMiddleware
│   │   ├── SemanticCheckMiddleware
│   │   ├── GenerationGateMiddleware
│   │   ├── ClarificationMiddleware
│   │   └── ResumeMiddleware
│   ├── extraction.py             # Term extraction (heuristics + metadata)
│   ├── resolution.py             # Scope-aware term resolution
│   ├── conflict.py               # Conflict detection and scoring
│   ├── clarification.py          # Interactive prompt handling (Typer + Rich)
│   ├── checkpoint.py             # Event-sourced checkpoint/resume
│   ├── scope.py                  # Scope hierarchy and seed file loading
│   ├── events.py                 # Event emission adapters (Feature 007 contracts)
│   └── strictness.py             # Strictness policy (off/medium/max)
├── missions/                      # EXISTING: Mission framework
│   └── [primitives integration point for middleware attachment]
├── cli/                           # EXISTING: CLI commands
│   └── commands/
│       └── glossary.py           # NEW: Glossary management commands (if needed)
└── [existing spec-kitty packages]

tests/specify_cli/glossary/        # NEW: Glossary tests
├── test_middleware.py            # Middleware pipeline integration tests
├── test_extraction.py            # Term extraction heuristics tests
├── test_resolution.py            # Scope resolution tests
├── test_conflict.py              # Conflict detection and scoring tests
├── test_clarification.py         # Interactive prompt tests
├── test_checkpoint.py            # Event-sourced checkpoint/resume tests
├── test_scope.py                 # Scope hierarchy and seed file tests
├── test_events.py                # Event emission tests (Feature 007 contracts)
└── test_strictness.py            # Strictness policy tests

.kittify/glossaries/               # NEW: Glossary seed files (optional)
├── spec_kitty_core.yaml          # Spec Kitty canonical terms
├── team_domain.yaml              # Team-specific terms (optional)
└── audience_domain.yaml          # Audience-specific terms (optional)
```

**Structure Decision**: Single project (Option 1) selected. This is a CLI library extension, not a separate web/mobile app. All code lives in `src/specify_cli/glossary/` package to keep glossary semantics modular and testable. Middleware integrates with existing mission primitive execution context. Seed files live in `.kittify/glossaries/` for user-managed glossary bootstrapping.

## Complexity Tracking

*No violations requiring justification. All constitution requirements met.*

---

## Phase 0: Research

**Prerequisites**: Constitution Check passed ✅

### Research Goals

1. **Middleware Integration Points**: Understand how mission primitives execute in spec-kitty 2.x to identify middleware injection points
2. **Feature 007 Event Contracts**: Extract canonical event schemas from spec-kitty-events package
3. **Term Extraction Heuristics**: Research deterministic patterns for domain term detection (quoted phrases, acronyms, casing patterns)
4. **Scope Resolution Strategies**: Best practices for hierarchical glossary lookup with fallback
5. **Checkpoint State Minimization**: Identify minimal state needed for deterministic resume

### Research Outputs

See [research.md](research.md) for detailed findings.

**Key Decisions**:

1. **Middleware Architecture (B + D Hybrid)**:
   - **Decision**: Use middleware chain as primary control path, with event emission at boundaries
   - **Rationale**: Primitives are config-defined and customizable (not stable class hierarchy). Middleware provides one consistent execution choke point. Events are for observability/audit/replay, not enforcement.
   - **Alternatives considered**: (A) Decorator pattern (brittle for config-driven primitives), (C) Base class hooks (forces class model mission system doesn't require), (D) Pure event-driven (can't guarantee inline block/resume semantics)

2. **Event Contracts (A + C: Reference Feature 007)**:
   - **Decision**: CLI references/imports events package contracts from spec-kitty-events (not redefining)
   - **Rationale**: Feature 007 is authoritative source for glossary event schemas. Prevents contract drift between CLI and SaaS.
   - **Alternatives considered**: (B) Define schemas inline in CLI (causes contract drift), (D) Stub contracts temporarily (defers integration)

3. **Term Extraction (D: Metadata hints + deterministic heuristics)**:
   - **Decision**: Hybrid extraction with metadata hints (highest confidence) + deterministic heuristics (quoted phrases, acronyms, casing patterns) + scope-aware normalization
   - **Rationale**: Keeps extraction automatic and mostly invisible, avoids LLM latency/cost in hot path, better precision than raw heuristics via mission metadata
   - **Alternatives considered**: (A) NLP-based (spaCy/NLTK - adds dependency weight), (B) LLM-based (high quality but latency/cost), (C) Pattern-based only (low precision)

4. **Checkpoint/Resume (A: Lightweight event sourcing)**:
   - **Decision**: Emit `StepCheckpointed` event before generation gate with minimal payload (mission/run/step IDs, strictness, scope/version refs, input hash, cursor, retry token)
   - **Rationale**: Event log is source of truth (Feature 007 invariant #6), supports cross-session resume, deterministic replay
   - **Alternatives considered**: (B) Filesystem state file (conflicts with "no side-channel state"), (C) In-memory cache (fails async defer + cross-session), (D) Re-run with inputs (fragile unless fully idempotent)

5. **Interactive Prompts (B: Typer prompts + Rich formatting)**:
   - **Decision**: Use typer.prompt() for input, rich for output formatting (no new dependencies)
   - **Rationale**: Matches existing CLI patterns (typer.confirm/prompt in upgrade.py, orchestrate.py), enough capability for ranked options + custom input + defer flow
   - **Alternatives considered**: (A) Rich + questionary (new dependency), (C) Custom Rich prompts (reinventing wheel), (D) AskUserQuestion tool (unclear if exists)

---

## Phase 1: Design & Contracts

**Prerequisites**: Phase 0 research complete ✅

### Data Model

See [data-model.md](data-model.md) for complete entity definitions and relationships.

**Core Entities**:

1. **TermSurface**: Raw string (e.g., "workspace")
2. **TermSense**: Meaning per scope (surface, scope, definition, provenance, confidence, status)
3. **GlossaryScope**: Enum (mission_local, team_domain, audience_domain, spec_kitty_core)
4. **SemanticConflict**: Conflict classification (term, type, severity, confidence, candidates, context)
5. **StepCheckpoint**: Minimal state for resume (mission/run/step IDs, strictness, scope refs, input hash, cursor, retry token)

**Middleware Components**:

1. **GlossaryCandidateExtractionMiddleware**: Extract terms from step I/O using metadata hints + heuristics
2. **SemanticCheckMiddleware**: Resolve terms against scope hierarchy, detect conflicts
3. **GenerationGateMiddleware**: Block generation on unresolved high-severity conflicts
4. **ClarificationMiddleware**: Render ranked candidates, prompt user (Typer + Rich)
5. **ResumeMiddleware**: Load checkpoint from events, restore step execution context

### Event Contracts

See [contracts/events.md](contracts/events.md) for canonical schemas from Feature 007.

**Canonical Events** (from spec-kitty-events package):

1. **GlossaryScopeActivated**: (scope_id, glossary_version_id)
2. **TermCandidateObserved**: (term, source_step, actor_id, confidence)
3. **SemanticCheckEvaluated**: (step_id, mission_id, timestamp, findings, overall_severity, confidence, effective_strictness, recommended_action, blocked)
4. **GlossaryClarificationRequested**: (question, term, options, urgency)
5. **GlossaryClarificationResolved**: (conflict_id, term_surface, selected_sense, actor, timestamp, resolution_mode, provenance)
6. **GlossarySenseUpdated**: (term_surface, scope, new_sense, actor, timestamp, update_type, provenance)
7. **GenerationBlockedBySemanticConflict**: (step_id, mission_id, timestamp, conflicts, strictness_mode, effective_strictness)

**CLI-specific events** (may need to add if not in Feature 007):

8. **StepCheckpointed**: (mission_id, run_id, step_id, strictness, scope_refs, input_hash, cursor, retry_token, timestamp)

### Middleware Interface Contracts

See [contracts/middleware.md](contracts/middleware.md) for interface definitions.

**Middleware Base Interface**:

```python
class GlossaryMiddleware(Protocol):
    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        """Process primitive execution context, return modified context or raise BlockedByConflict."""
        ...
```

**Pipeline Execution Order**:

1. Extraction → 2. Semantic Check → 3. Generation Gate → 4. Clarification (if blocked) → 5. Resume (on retry)

### Quickstart

See [quickstart.md](quickstart.md) for developer setup and common workflows.

**Developer Setup**:
1. Install spec-kitty 2.x with glossary feature
2. (Optional) Create seed files in `.kittify/glossaries/`
3. Configure strictness mode in `.kittify/config.yaml` (default: medium)

**Common Workflows**:
1. Mission author: Add `glossary_check: enabled` to step metadata in mission.yaml
2. Developer: Encounter conflict, resolve interactively via Typer prompt
3. Operator: Set `strictness: off` for local dev, `strictness: max` for production

---

## Agent Context Update

*This section will be auto-updated by the agent context script during `/spec-kitty.plan` execution.*

**Action**: Run agent context update script to add new technology stack to appropriate agent-specific context file.

**New technology to add**:
- Python package: `src/specify_cli/glossary/` (glossary semantic integrity runtime)
- Dependencies: typer (CLI), rich (console), ruamel.yaml (seed files), spec-kitty-events (Feature 007 contracts)
- Testing: pytest (90%+ coverage), mypy --strict
- Event contracts: Feature 007 canonical glossary events (GlossaryScopeActivated, TermCandidateObserved, SemanticCheckEvaluated, etc.)

**Agent-specific files**:
- Claude Code: `.claude/context.md`
- GitHub Copilot: `.github/context.md`
- (Other agents as detected by script)

---

## Phase 2: Task Generation

**STOP**: This is the end of `/spec-kitty.plan` workflow. Do NOT proceed to task generation.

The user must explicitly run `/spec-kitty.tasks` to generate work packages.

---

## Implementation Notes

**Risks**:
- Over-questioning can reduce velocity if severity policy too aggressive (mitigate: cap at 3 questions per burst, severity-first prioritization)
- Weak confidence scoring can under-detect conflicts (mitigate: start conservative, tune based on user feedback)
- Feature 007 events package not yet published (mitigate: stub adapter boundaries, gate implementation on 007 availability)

**Assumptions**:
- Mission primitives in 2.x are configurable and can carry glossary-check metadata (validate during WP01 implementation)
- Participants will answer targeted clarifications when prompted (design escape hatch: defer to async)
- Term extraction heuristics have acceptable precision (validate with test corpus, iterate if needed)

**Open Questions**:
- Confidence scoring calibration strategy for v1 default policy (defer to WP03: conflict detection implementation)
- Exact dashboard ROI metrics beyond "prevented rework" (out of scope for CLI, defer to SaaS)

---

**Next command**: `/spec-kitty.tasks` (user must invoke explicitly)
