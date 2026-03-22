---
name: spec-kitty-glossary-context
description: >-
  Curate and apply canonical terminology across Spec Kitty missions.
  Triggers: "update the glossary", "use canonical terms", "check terminology",
  "add a term", "fix term drift", "glossary conflicts", "resolve ambiguity",
  "review terminology consistency".
  Does NOT handle: runtime loop advancement, setup or repair requests,
  agent configuration, or direct code implementation tasks.
---

# spec-kitty-glossary-context

Maintain semantic integrity by curating the project glossary, detecting term
drift, and ensuring that all mission artifacts use canonical terminology.

Use this skill when the user wants to inspect, update, or enforce glossary
terms. Do not use it for purely operational tasks like advancing the runtime
loop or repairing an installation.

---

## How the Glossary Works

The glossary is a **semantic integrity runtime** — a 5-layer middleware pipeline
that intercepts mission step execution, extracts terms from inputs/outputs,
checks them against stored definitions, and can **block generation** if
terminology conflicts are unresolved.

### Data Model

**Terms** have a `surface` (normalized to lowercase), `definition`, `scope`,
`confidence` (0.0–1.0), and `status` (draft/active/deprecated).

**Seed files** (`.kittify/glossaries/{scope}.yaml`) provide initial definitions.
**Event logs** (`.kittify/events/glossary/*.events.jsonl`) record all runtime
mutations as append-only JSONL. State is reconstructed by replaying seed files
then events.

### 4 Scopes (narrowest wins)

| Precedence | Scope | Use For |
|:---:|---|---|
| 0 (highest) | `mission_local` | Feature-specific jargon |
| 1 | `team_domain` | Team/org conventions |
| 2 | `audience_domain` | Industry/domain standards |
| 3 (lowest) | `spec_kitty_core` | Framework terms (lane, work package, mission) |

### The 5-Layer Middleware Pipeline

When a mission primitive executes (via `@glossary_enabled` decorator or
`GlossaryAwarePrimitiveRunner`), this pipeline processes the step:

**Layer 1 — Term Extraction.** Scans step input/output for terminology using
multiple methods (in priority order):

| Method | Confidence | Example |
|---|:---:|---|
| Metadata hints (`glossary_watch_terms`) | 1.0 | Explicit list of terms to monitor |
| Quoted phrases | 0.8 | `"work package"` in text |
| Acronyms (2-5 uppercase) | 0.8 | `WP`, `API` |
| Casing patterns (snake_case, CamelCase) | 0.8 | `worktree_node`, `WorkspaceManager` |
| Repeated nouns (3+ occurrences) | 0.5 | Frequent domain words |

Emits `TermCandidateObserved` events.

**Layer 2 — Semantic Check.** Resolves each extracted term against the scope
hierarchy and classifies conflicts:

| Conflict Type | Trigger | Severity |
|---|---|---|
| `UNKNOWN` | Term not in any scope | Varies by confidence + criticality |
| `AMBIGUOUS` | 2+ active senses for same surface | HIGH in critical steps |
| `INCONSISTENT` | Output contradicts glossary definition | LOW (informational) |
| `UNRESOLVED_CRITICAL` | Unknown term in critical step, low confidence | HIGH |

Emits `SemanticCheckEvaluated` events.

**Layer 3 — Clarification (runs BEFORE the gate).** Users get a chance to
resolve conflicts before generation is blocked:

- In interactive mode: prompts user to select a candidate sense, provide a
  custom definition, or defer
- In non-interactive mode (CI/headless): auto-defers all conflicts
- Resolved conflicts are removed; deferred ones pass to Layer 4

Emits `GlossaryClarificationRequested`, `GlossaryClarificationResolved`,
and `GlossarySenseUpdated` events.

**Layer 4 — Generation Gate.** Evaluates whether to block based on strictness:

| Strictness | Behavior |
|---|---|
| `off` | Never block |
| `medium` (default) | Block only HIGH severity conflicts |
| `max` | Block any unresolved conflict |

Strictness resolved via 4-tier precedence: runtime flag > step metadata >
mission config > global default (`.kittify/config.yaml`).

If blocking: saves a **checkpoint** (SHA256 input hash, scope versions, retry
token), emits `StepCheckpointed` and `GenerationBlockedBySemanticConflict`
events, then raises `BlockedByConflict`.

**Layer 5 — Resume.** For retry after a block:

- Loads checkpoint from event log
- Verifies input hash hasn't changed (detects context drift)
- Prompts user if context changed
- Restores execution state

### Step-Level Configuration

Individual mission steps can control glossary behavior via metadata:

```yaml
# In step definition
glossary_check: enabled          # or "disabled" to skip this step
glossary_check_strictness: max   # override strictness for this step
glossary_watch_terms:            # explicit terms to monitor (confidence 1.0)
  - work package
  - lane
glossary_aliases:                # map synonyms to canonical forms
  task: work package
  status: lane
glossary_exclude_terms:          # terms to ignore
  - the
  - a
```

### 8 Event Types

| Event | When | Effect |
|---|---|---|
| `GlossaryScopeActivated` | Scope loaded at runtime | Informational |
| `TermCandidateObserved` | Term extracted from text | Records extraction |
| `SemanticCheckEvaluated` | Semantic check completes | Records findings |
| `GlossaryClarificationRequested` | Conflict needs resolution | Creates pending conflict |
| `GlossaryClarificationResolved` | User selects a sense | Promotes selected sense |
| `GlossarySenseUpdated` | Term added/definition changed | Updates store |
| `GenerationBlockedBySemanticConflict` | Gate blocks generation | Records block |
| `StepCheckpointed` | State saved before block | Enables resume |

All events are append-only in `.kittify/events/glossary/{mission-id}.events.jsonl`.

### Integration Patterns

```python
# 1. Decorator (simplest)
@glossary_enabled(repo_root=Path("."))
def my_primitive(context):
    return {"result": "ok"}

# 2. Function processor
processor = attach_glossary_pipeline(repo_root, runtime_strictness, interaction_mode)
processed_context = processor(context)  # May raise BlockedByConflict

# 3. Runner class
runner = GlossaryAwarePrimitiveRunner(repo_root, runtime_strictness)
result = runner.execute(primitive_fn, context)
```

The `BlockedByConflict` exception carries the `conflicts` list, `strictness`
mode, and a user-facing message. Callers should catch it, present the conflicts,
and offer resolution before retrying.

---

## Step 1: Locate Glossary Context

Identify the glossary state for the current project.

**What to check:**

- Seed files under `.kittify/glossaries/` (one YAML per scope)
- Event logs under `.kittify/events/glossary/` (JSONL, event-sourced)
- The store replays seed files then events at query time

**Commands:**

```bash
spec-kitty glossary list
spec-kitty glossary list --scope spec_kitty_core
spec-kitty glossary list --status active --json
```

**Expected outcome:** You know which scopes are populated and whether event
logs contain runtime mutations.

---

## Step 2: Check Conflicts and Strictness

The glossary gates mission execution through the strictness system.

**Commands:**

```bash
spec-kitty glossary conflicts
spec-kitty glossary conflicts --unresolved
spec-kitty glossary conflicts --strictness max --mission 012-documentation-mission
```

**Expected outcome:** You understand why a conflict blocked the runtime, or you
can confirm no blocking conflicts exist.

---

## Step 3: Update Terms and Resolve Conflicts

**Adding or editing terms:** Edit the seed file for the appropriate scope.

Choose the scope by term ownership:

- Project-internal jargon: `mission_local.yaml`
- Shared domain vocabulary: `team_domain.yaml`
- User-facing terms: `audience_domain.yaml`
- Spec Kitty concepts: `spec_kitty_core.yaml` (rarely edited)

Rules: `surface` must be lowercase/trimmed; `status` is `active`, `deprecated`,
or `draft`; `confidence` is 0.0–1.0.

**Seed file format:**

```yaml
terms:
  - surface: <lowercase trimmed string>
    definition: <non-empty string>
    confidence: <float 0.0-1.0>       # default 1.0
    status: <active|deprecated|draft>  # default draft
```

**Status lifecycle:** `draft` → (promote) → `active` → (retire) → `deprecated`
→ (re-draft) → `draft`. Deprecated senses are excluded from resolution but
remain in event history.

**Resolving conflicts interactively:**

```bash
spec-kitty glossary resolve <conflict_id>
spec-kitty glossary resolve <conflict_id> --mission 012-docs
```

The resolver presents candidate senses. You can select one, enter a custom
definition, or defer. Custom definitions emit both a
`GlossaryClarificationResolved` and a `GlossarySenseUpdated` event.

**Expected outcome:** The glossary reflects intended terminology and runtime-
blocking conflicts are resolved.

---

## Step 4: Detect and Prevent Semantic Drift

Semantic drift occurs when artifacts gradually diverge from glossary definitions.
See `references/semantic-drift-examples.md` for six concrete drift patterns.

**Detection:**

1. Run `spec-kitty glossary list --json` and compare definitions against spec,
   plan, and task files
2. Run `spec-kitty glossary conflicts --unresolved` for terms the runtime flagged
3. Search WP frontmatter for informal synonyms (e.g., "task" instead of the
   canonical "work package")

**Correction:**

- Artifact is wrong: replace with the canonical term
- Glossary is outdated: update the seed file definition
- Genuinely ambiguous: add a second sense and let the strictness system force
  disambiguation

**Prevention:**

- Set strictness to `medium` or `max` so the runtime catches conflicts early
- Add domain terms to the glossary before writing specs that use them
- Use `glossary_watch_terms` in step metadata for high-value terms
- Use `glossary_aliases` to map known synonyms to canonical forms
- Review the conflict log after each completed mission

**Consistency checklist:**

1. Every WP title and description uses canonical surface forms
2. Plan documents reference terms as defined in the glossary
3. No informal synonyms appear without a corresponding glossary entry
4. Deprecated terms are not reintroduced in new artifacts

**Expected outcome:** Terminology is consistent across all mission artifacts
and the glossary remains a living, enforced contract.

---

## References

- `references/glossary-field-guide.md` -- Seed file schema, scope precedence, status lifecycle, event-sourcing mechanics, and CLI quick reference
- `references/semantic-drift-examples.md` -- Concrete drift patterns with detection and correction strategies
