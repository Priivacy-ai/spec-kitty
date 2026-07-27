# Research: Bulk Edit Occurrence Classification Guardrail

**Date**: 2026-04-13
**Mission**: bulk-edit-occurrence-classification-guardrail-01KP423X

## Research Questions

### RQ-1: Where to insert the implement guard

**Decision**: Insert between planning-state validation and workspace allocation in `src/specify_cli/cli/commands/implement.py`.

**Rationale**: The implement function has a clear 3-phase pipeline: detect → validate → create. The guard belongs in the validate phase, after `_ensure_planning_artifacts_committed_git()` (which confirms planning artifacts are committed) and before `resolve_workspace_for_wp()` (which begins workspace creation). This is the last checkpoint before work begins.

**Evidence**: The existing guard `_ensure_planning_artifacts_committed_git()` at ~line 179 sets the precedent — it validates a planning-phase condition before allowing implementation to proceed. The new guard follows the same pattern.

**Alternatives considered**:
- Inserting in Phase 1 (detect): Too early — mission slug isn't resolved yet
- Inserting in Phase 3 (workspace creation): Too late — workspace allocation has side effects
- Separate pre-implement hook system: Unnecessary abstraction for a single guard

### RQ-2: Occurrence map YAML schema design

**Decision**: Minimal schema with three required sections: `target`, `categories`, and `exceptions`. Each category entry requires an `action` field.

**Rationale**: The schema must be strict enough to be machine-validatable but flexible enough that authors don't fight the format. The three-section structure maps directly to the classification workflow: what are you changing, where does it appear, and what's special.

**Evidence**: Surveyed existing spec-kitty YAML artifacts:
- `lanes.json` — strict machine-readable, minimal fields
- `governance.yaml` — structured sections with string lists
- `meta.json` — flat key/value with optional nested structures
- `expected-artifacts.yaml` — typed fields with validation

The occurrence map follows the `expected-artifacts.yaml` pattern: typed fields with clear validation rules.

**Alternatives considered**:
- Free-form YAML with no required structure: Too loose — can't validate completeness
- JSON instead of YAML: YAML is the established format for planning artifacts in spec-kitty
- Embedded in plan.md instead of separate file: Separate file is machine-parseable and referenceable

### RQ-3: Inference keyword strategy

**Decision**: Conservative keyword list with scoring threshold. Keywords are weighted by specificity.

**Rationale**: The spec requires < 20% false positive rate (NFR-003). A conservative approach with high-specificity keywords reduces noise. The warning is advisory, not blocking — false positives are annoying but not harmful.

**Evidence**: Examined `src/specify_cli/ownership/inference.py` for the existing keyword scoring pattern:
- Uses `planning_signals` and `code_signals` lists
- Scores by presence/absence
- Threshold determines classification

The inference warning follows the same pattern but with rename/migration-specific keywords.

**Keywords by weight**:
- High (3 points): `rename across`, `bulk edit`, `codemod`, `find-and-replace`, `replace everywhere`, `terminology migration`
- Medium (2 points): `rename`, `migrate`, `replace all`, `across the codebase`, `globally`
- Low (1 point): `update`, `change`, `modify`, `refactor`
- Threshold: >= 4 points triggers warning

**Alternatives considered**:
- NLP/semantic analysis: Over-engineered for v1; simple keywords sufficient
- No inference at all: Spec requires it (FR-009)
- Binary keyword match (any keyword triggers): Too noisy — common words like "update" would trigger constantly

### RQ-4: Guard function reuse between implement and review

**Decision**: Single `ensure_occurrence_classification_ready()` function in `src/specify_cli/bulk_edit/gate.py`, imported by both `implement.py` and `workflow.py`.

**Rationale**: The check is identical in both contexts: is this a bulk_edit mission, and if so, is the occurrence map present and complete? Deduplication prevents drift between the two gates.

**Evidence**: Existing patterns:
- `review/lock.py` exports `acquire_review_lock()` used by the review action
- `ownership/inference.py` exports functions used by multiple callers
- The gate function follows the same extract-and-import pattern

### RQ-5: Doctrine directive numbering

**Decision**: Use directive number 035 — next available after existing directives (001, 003, 010, 018, 024, 025, 028–034).

**Rationale**: Directive numbering follows sequential assignment in `src/doctrine/directives/shipped/`. The highest existing is 034 (`test-first-development`), so 035 is the next available slot.

**Evidence**: Scanned `src/doctrine/directives/shipped/` directory — found directives through 034.
