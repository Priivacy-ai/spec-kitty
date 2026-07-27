# Data Model: Glossary Semantic Integrity Runtime

**Feature**: 041-mission-glossary-semantic-integrity
**Date**: 2026-02-16
**Status**: Complete

## Overview

This document defines the core entities, value objects, and relationships for the glossary semantic integrity runtime. All entities follow event sourcing principles (Feature 007) with append-only state changes.

---

## Core Entities

### TermSurface

Raw string representation of a term as observed in mission inputs/outputs.

**Attributes**:

- `surface_text` (str): The actual text (e.g., "workspace", "mission", "WP")

**Invariants**:

- Normalized form: lowercase, trimmed whitespace
- Stem-light applied: "workspaces" → "workspace" (plural → singular)
- Unique per scope (no duplicate surfaces in active glossary)

**Example**:

```python
TermSurface(surface_text="workspace")
```

---

### TermSense

Meaning of a TermSurface within a specific GlossaryScope.

**Attributes**:

- `surface` (TermSurface): The term this sense defines
- `scope` (GlossaryScope): Which scope this sense belongs to
- `definition` (str): Human-readable meaning
- `provenance` (Provenance): Who/when/why this sense was created
- `confidence` (float): Confidence score 0.0-1.0 (extraction quality)
- `status` (SenseStatus): active | deprecated | draft

**Invariants**:

- One sense can exist per (surface, scope) pair
- Deprecated senses remain in history but not in active resolution
- Draft senses auto-created by extraction (low confidence) until promoted

**Provenance fields**:

- `actor_id` (str): User ID or LLM actor who created this sense
- `timestamp` (datetime): When created
- `source` (str): Where it came from (e.g., "user_clarification", "metadata_hint", "auto_extraction")

**Example**:

```python
TermSense(
    surface=TermSurface("workspace"),
    scope=GlossaryScope.TEAM_DOMAIN,
    definition="Git worktree directory for a work package",
    provenance=Provenance(
        actor_id="user:alice",
        timestamp=datetime(2026, 2, 16, 12, 0, 0),
        source="user_clarification"
    ),
    confidence=1.0,
    status=SenseStatus.ACTIVE
)
```

---

### GlossaryScope

Enumeration of scope levels in the glossary hierarchy.

**Values**:

- `mission_local`: Mission-specific temporary/working semantics (highest precedence)
- `team_domain`: Language used by mission participants/contributors
- `audience_domain`: Language for intended recipients (customers/stakeholders/users)
- `spec_kitty_core`: Spec Kitty canonical terms (lowest precedence)

**Resolution order**: mission_local → team_domain → audience_domain → spec_kitty_core

**Scope activation**:

- Mission start emits `GlossaryScopeActivated` for each active scope
- Scopes without seed files are skipped cleanly (no error)

**Example**:

```python
# Scope resolution for term "workspace"
# 1. Check mission_local (no match)
# 2. Check team_domain (2 matches - ambiguous!)
# 3. (Stop - conflict detected, clarification required)
```

---

### SemanticConflict

Classification of a term conflict detected during semantic check.

**Attributes**:

- `term` (TermSurface): The conflicting term
- `conflict_type` (ConflictType): Type of conflict (see below)
- `severity` (Severity): low | medium | high
- `confidence` (float): Confidence in conflict detection (0.0-1.0)
- `candidate_senses` (List[TermSense]): Possible meanings from scope resolution
- `context` (str): Usage location (e.g., "step input: description field")

**ConflictType values**:

- `UNKNOWN`: Term not found in any scope (no match in scope stack)
- `AMBIGUOUS`: Multiple active senses in current scope stack, usage unqualified
- `INCONSISTENT`: LLM output uses sense contradicting active glossary
- `UNRESOLVED_CRITICAL`: Unknown/new critical term with low confidence, no resolved sense before generation

**Severity scoring**:

- **High**: Ambiguous in critical step + low confidence OR unresolved critical term
- **Medium**: Ambiguous in non-critical step OR unknown term with medium confidence
- **Low**: Inconsistent usage in non-critical step OR unknown term with high confidence (likely safe)

**Example**:

```python
SemanticConflict(
    term=TermSurface("workspace"),
    conflict_type=ConflictType.AMBIGUOUS,
    severity=Severity.HIGH,
    confidence=0.9,
    candidate_senses=[
        TermSense(..., definition="Git worktree directory"),
        TermSense(..., definition="VS Code workspace file")
    ],
    context="step input: requirements field"
)
```

---

### StepCheckpoint

Minimal state for resuming step execution after conflict resolution.

**Attributes**:

- `mission_id` (str): Which mission
- `run_id` (str): Which run instance
- `step_id` (str): Which step
- `strictness` (Strictness): Resolved strictness mode (off/medium/max)
- `scope_refs` (List[ScopeRef]): Active glossary scope versions
- `input_hash` (str): SHA256 of step inputs (detect context changes)
- `cursor` (str): Execution stage (e.g., "pre_generation_gate")
- `retry_token` (str): Unique token for this checkpoint (UUID)
- `timestamp` (datetime): When checkpoint created

**ScopeRef structure**:

- `scope` (GlossaryScope): Which scope
- `version_id` (str): Glossary version ID (for deterministic replay)

**Usage**:

1. Emit `StepCheckpointed` before generation gate
2. User resolves conflict
3. Resume loads checkpoint, verifies input_hash
4. If hash matches: resume from cursor
5. If hash differs: prompt for confirmation

**Example**:

```python
StepCheckpoint(
    mission_id="041-mission",
    run_id="run-2026-02-16-001",
    step_id="step-specify-001",
    strictness=Strictness.MEDIUM,
    scope_refs=[
        ScopeRef(scope=GlossaryScope.MISSION_LOCAL, version_id="v1"),
        ScopeRef(scope=GlossaryScope.TEAM_DOMAIN, version_id="v3"),
    ],
    input_hash="abc123...",
    cursor="pre_generation_gate",
    retry_token="uuid-1234-5678",
    timestamp=datetime(2026, 2, 16, 12, 30, 0)
)
```

---

## Middleware Components

### GlossaryCandidateExtractionMiddleware

Extracts candidate terms from step inputs/outputs.

**Inputs**:

- `context` (PrimitiveExecutionContext): Step inputs, metadata, config

**Outputs**:

- `context` (modified): Adds `extracted_terms` field
- **Events**: `TermCandidateObserved` (for each extracted term)

**Extraction logic** (see research.md Finding 3):

1. Load metadata hints (glossary_watch_terms, glossary_aliases, etc.)
2. Apply deterministic heuristics (quoted phrases, acronyms, casing, repeats)
3. Normalize (lowercase, trim, stem-light)
4. Score confidence (metadata > pattern > weak heuristic)

**Example**:

```python
# Input context
context.inputs = {"description": "The workspace contains implementation files"}

# After extraction
context.extracted_terms = [
    ExtractedTerm(
        surface=TermSurface("workspace"),
        confidence=0.8,
        source="casing_pattern",
        context="description field"
    )
]
```

---

### SemanticCheckMiddleware

Resolves extracted terms against scope hierarchy, detects conflicts.

**Inputs**:

- `context.extracted_terms` (from extraction middleware)
- Active glossary scopes (loaded from seed files + event log)

**Outputs**:

- `context.conflicts` (List[SemanticConflict]): Detected conflicts
- **Events**: `SemanticCheckEvaluated` (with findings, severity, recommended action)

**Resolution logic**:

1. For each extracted term:
   - Resolve against scope order (mission_local → team_domain → audience_domain → spec_kitty_core)
   - If no match: conflict type = UNKNOWN
   - If 1 match: resolved (no conflict)
   - If 2+ matches: conflict type = AMBIGUOUS
   - If LLM output contradicts glossary: conflict type = INCONSISTENT
2. Score severity based on step criticality + confidence
3. Emit `SemanticCheckEvaluated` with overall severity and recommended action

**Example**:

```python
# Input
context.extracted_terms = [TermSurface("workspace")]

# After check
context.conflicts = [
    SemanticConflict(
        term=TermSurface("workspace"),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.HIGH,
        candidate_senses=[...],
        context="description field"
    )
]
```

---

### GenerationGateMiddleware

Blocks LLM generation on unresolved high-severity conflicts.

**Inputs**:

- `context.conflicts` (from semantic check middleware)
- `context.strictness` (resolved strictness mode)

**Outputs**:

- If pass: continue to next middleware
- If block: raise `BlockedByConflict` exception
- **Events**: `GenerationBlockedBySemanticConflict` (if blocked)

**Gate logic**:

- Strictness = `off`: always pass (no blocking)
- Strictness = `medium`: block only if high-severity conflicts exist
- Strictness = `max`: block if any unresolved conflicts exist

**Example**:

```python
# Input
context.strictness = Strictness.MEDIUM
context.conflicts = [SemanticConflict(severity=Severity.HIGH, ...)]

# Output
raise BlockedByConflict(conflicts=context.conflicts)
# Emit: GenerationBlockedBySemanticConflict
```

---

### ClarificationMiddleware

Renders ranked candidate senses, prompts user for resolution.

**Inputs**:

- `context.conflicts` (from generation gate)
- Interactive mode flag (CLI vs non-interactive)

**Outputs**:

- User selection or async defer
- **Events**: `GlossaryClarificationRequested`, `GlossaryClarificationResolved`, `GlossarySenseUpdated`

**Clarification logic**:

1. Sort conflicts by severity (high → medium → low), cap to 3
2. Render each conflict with Rich:
   - Term, context, scope, ranked candidate senses (by confidence)
3. Prompt with typer.prompt():
   - Select candidate (1..N)
   - Custom sense (C)
   - Defer to async (D)
4. Handle choice:
   - Candidate selected: emit `GlossaryClarificationResolved`, update glossary
   - Custom sense: emit `GlossarySenseUpdated`, add to glossary
   - Defer: emit `GlossaryClarificationRequested`, exit with blocked status

**Non-interactive mode**:

- Auto-defer all conflicts
- Emit `GlossaryClarificationRequested` for all high-severity
- Exit with error code (generation still blocked)

**Example**:

```python
# Interactive prompt
"""
🔴 High-severity conflict: "workspace"

Term: workspace
Context: "The workspace contains the implementation files"
Scope: team_domain (2 matches)

Candidate senses:
1. [team_domain] Git worktree directory for a work package (confidence: 0.9)
2. [team_domain] VS Code workspace configuration file (confidence: 0.7)

Select: 1-2 (candidate), C (custom sense), D (defer to async)
> 1

✅ Resolved: workspace = Git worktree directory for a work package
"""
```

---

### ResumeMiddleware

Loads checkpoint from events, restores step execution context.

**Inputs**:

- `retry_token` (from user retry request)
- Event log (to load `StepCheckpointed` event)

**Outputs**:

- Restored `context` (from checkpoint)
- Resume from cursor (skip already-completed stages)

**Resume logic**:

1. Load latest `StepCheckpointed` event for this step_id
2. Verify input_hash matches current inputs
   - If changed: prompt user for confirmation
   - If unchanged: restore context
3. Load updated glossary state from `GlossarySenseUpdated` events
4. Resume from cursor ("pre_generation_gate")
5. Re-run generation gate with updated state

**Example**:

```python
# Load checkpoint
checkpoint = load_checkpoint(step_id="step-specify-001")

# Verify inputs unchanged
if checkpoint.input_hash != hash_inputs(context.inputs):
    if not typer.confirm("Context changed. Proceed?"):
        raise AbortResume()

# Restore context
context.strictness = checkpoint.strictness
context.scope_refs = checkpoint.scope_refs

# Resume from cursor
if checkpoint.cursor == "pre_generation_gate":
    # Skip extraction and semantic check (already done)
    # Re-run generation gate (with updated glossary)
    run_generation_gate(context)
```

---

## Relationships

```
TermSurface (1) ----< (N) TermSense
                         |
                         |--- GlossaryScope (1)
                         |--- Provenance (1)
                         |--- SenseStatus (enum)

SemanticConflict (1) ----< (N) TermSense (candidate_senses)
                    |
                    |--- TermSurface (1)
                    |--- ConflictType (enum)
                    |--- Severity (enum)

StepCheckpoint (1) ----< (N) ScopeRef
                   |
                   |--- Strictness (enum)

Middleware Pipeline:
  GlossaryCandidateExtractionMiddleware
    ↓ (emits TermCandidateObserved)
  SemanticCheckMiddleware
    ↓ (emits SemanticCheckEvaluated)
  GenerationGateMiddleware
    ↓ (emits GenerationBlockedBySemanticConflict if blocked)
  ClarificationMiddleware
    ↓ (emits GlossaryClarificationRequested/Resolved, GlossarySenseUpdated)
  ResumeMiddleware
    ↓ (loads StepCheckpointed, resumes from cursor)
```

---

## State Transitions

### TermSense Status

```
draft (auto-extracted, low confidence)
  ↓ (user clarification)
active (promoted by user selection)
  ↓ (user deprecation or newer sense)
deprecated (kept in history, not in active resolution)
```

### Conflict Resolution Flow

```
Conflict detected (SemanticCheckEvaluated)
  ↓
Generation blocked (GenerationBlockedBySemanticConflict)
  ↓
Clarification requested (GlossaryClarificationRequested)
  ↓ (user resolves)
Clarification resolved (GlossaryClarificationResolved)
  ↓
Glossary updated (GlossarySenseUpdated)
  ↓
Resume from checkpoint (StepCheckpointed)
  ↓
Generation unblocked (continue execution)
```

---

## Validation Rules

### TermSurface

- Must not be empty
- Must be normalized (lowercase, trimmed)
- Must be unique per scope

### TermSense

- Definition must not be empty
- Confidence must be 0.0-1.0
- Provenance must have actor_id and timestamp

### SemanticConflict

- Must have at least 1 candidate sense (for AMBIGUOUS type)
- Severity must align with confidence (high severity → low confidence)

### StepCheckpoint

- mission_id, run_id, step_id must not be empty
- input_hash must be valid SHA256 (64 hex chars)
- retry_token must be valid UUID

---

## Event Schema References

See [contracts/events.md](contracts/events.md) for canonical event schemas from Feature 007.

All events conform to spec-kitty-events package contracts. CLI imports events, not redefines them.
