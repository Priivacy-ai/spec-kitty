# Implementation Plan: Bulk Edit Occurrence Classification Guardrail

**Branch**: `main` | **Date**: 2026-04-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/bulk-edit-occurrence-classification-guardrail-01KP423X/spec.md`
**Source**: [Priivacy-ai/spec-kitty#393](https://github.com/Priivacy-ai/spec-kitty/issues/393)

## Summary

Add a workflow guardrail that forces explicit occurrence-category classification before bulk edits begin. Missions marked `change_mode: bulk_edit` gain a required `occurrence_map.yaml` planning artifact. The implement action refuses to start if the artifact is missing or structurally incomplete. The review action validates the artifact is present and admissible. An inference warning alerts when unmarked missions contain rename/migration language. A new doctrine directive codifies the governance rule.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (YAML parsing), pytest (testing), mypy (type checking)
**Storage**: Filesystem only (YAML artifact in `kitty-specs/<mission>/`, JSON metadata in `meta.json`)
**Testing**: pytest with 90%+ coverage for new code, mypy --strict, integration tests for CLI commands
**Target Platform**: CLI tool (cross-platform)
**Project Type**: Single project — Python package `specify_cli`
**Performance Goals**: Gate checks complete in < 2 seconds (NFR-001)
**Constraints**: No AST-based classification; artifact is human-authored (C-001). Must work across all 12 agents (C-004).
**Scale/Scope**: Touches ~8 files in `src/specify_cli/`, adds ~2 new modules, updates 2 command templates, adds 1 doctrine directive

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter Rule | Status | Notes |
|-------------|--------|-------|
| typer for CLI | PASS | No new CLI commands; guard runs within existing implement/review paths |
| rich for console output | PASS | Warnings and errors use existing Rich console patterns |
| ruamel.yaml for YAML parsing | PASS | Occurrence map parsed with ruamel.yaml |
| pytest with 90%+ coverage | PASS | All new modules will have unit + integration tests |
| mypy --strict | PASS | All new code fully typed |
| Integration tests for CLI commands | PASS | Implement and review gate behavior tested via CLI integration tests |
| DIRECTIVE_010 (Spec Fidelity) | PASS | Implementation follows spec FR-001 through FR-011 faithfully |
| DIRECTIVE_003 (Decision Documentation) | PASS | ADR will document guard-vs-step decision |

## Project Structure

### Documentation (this feature)

```
kitty-specs/bulk-edit-occurrence-classification-guardrail-01KP423X/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output — occurrence map schema
├── meta.json            # Mission metadata
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```
src/specify_cli/
├── bulk_edit/                          # NEW: Bulk edit guardrail package
│   ├── __init__.py                     # Public API exports
│   ├── occurrence_map.py               # Occurrence map loading, validation, schema
│   ├── gate.py                         # ensure_occurrence_classification_ready() guard
│   └── inference.py                    # Spec content keyword scanning for warnings
├── mission_metadata.py                 # MODIFIED: Add change_mode to optional fields
├── cli/commands/
│   ├── implement.py                    # MODIFIED: Wire gate into implement flow
│   └── agent/workflow.py               # MODIFIED: Wire gate into review flow
├── mission_v1/guards.py                # MODIFIED: Register occurrence_map_complete guard
└── missions/software-dev/
    ├── command-templates/
    │   ├── implement.md                # MODIFIED: Reference occurrence map in instructions
    │   └── review.md                   # MODIFIED: Reference occurrence map in review checklist
    └── expected-artifacts.yaml         # MODIFIED: Add conditional occurrence_map.yaml

src/doctrine/directives/shipped/
└── 035-bulk-edit-occurrence-classification.directive.yaml  # NEW

tests/specify_cli/
├── bulk_edit/                          # NEW: Test package
│   ├── test_occurrence_map.py          # Schema validation tests
│   ├── test_gate.py                    # Guard function tests
│   └── test_inference.py               # Keyword scanning tests
├── cli/commands/
│   ├── test_implement_bulk_edit.py     # NEW: Integration tests for implement gate
│   └── test_review_bulk_edit.py        # NEW: Integration tests for review gate
└── test_mission_metadata_change_mode.py # NEW: change_mode field tests
```

**Structure Decision**: New `bulk_edit/` package under `specify_cli/` keeps guardrail logic cohesive and testable independently. The guard function is imported by `implement.py` and `workflow.py` rather than inlined, matching the existing pattern of extracted helper modules (e.g., `ownership/inference.py`, `review/lock.py`).

## Integration Points

### 1. Implement Action Guard (Primary Gate — FR-006)

**File**: `src/specify_cli/cli/commands/implement.py`
**Location**: Between Phase 2 (Validate Planning State, ~line 485) and Phase 3 (Workspace Allocation, ~line 487)
**Pattern**: Matches existing guard structure — `_ensure_planning_artifacts_committed_git()` is the precedent

```
implement(WP_ID, --mission SLUG, ...)
  ↓
[DETECT] resolve_mission_handle() → mission_slug
  ↓
find_wp_file() → WP file
  ↓
[VALIDATE] _ensure_planning_artifacts_committed_git()
  ↓
★ NEW: ensure_occurrence_classification_ready(feature_dir)  ← INSERT HERE
  ↓
resolve_workspace_for_wp() → workspace
  ↓
[CREATE] create_lane_workspace()
  ...
```

**Behavior**:
1. Load `meta.json` via `load_meta(feature_dir)`
2. Check `meta.get("change_mode")` — if not `"bulk_edit"`, pass through (zero cost for non-bulk missions)
3. If `bulk_edit`: check `feature_dir / "occurrence_map.yaml"` exists
4. If exists: validate structural completeness (target named, categories enumerated, actions assigned)
5. If missing or incomplete: raise descriptive error with remediation instructions

### 2. Review Action Gate (Secondary Gate — FR-007, FR-008)

**File**: `src/specify_cli/cli/commands/agent/workflow.py`
**Location**: In the `review()` function (~line 1216), after lane state validation (~line 1296), before review claim
**Pattern**: Matches existing review gate pattern (concurrent lock check)

**Behavior**:
1. Same `ensure_occurrence_classification_ready()` function (reused)
2. If bulk_edit mission and occurrence map is missing/incomplete: reject review
3. Review template references occurrence map as governing artifact for diff evaluation

### 3. Inference Warning (Advisory — FR-009, FR-010)

**File**: New `src/specify_cli/bulk_edit/inference.py`
**Trigger point**: Called from `implement.py` when `change_mode` is NOT set
**Pattern**: Matches `ownership/inference.py` keyword scoring approach

**Behavior**:
1. Read `spec.md` content
2. Scan for rename/migration keywords: `rename`, `migrate`, `replace`, `terminology`, `bulk edit`, `find-and-replace`, `sed`, `codemod`, `across the codebase`, `everywhere`
3. If score exceeds threshold: emit Rich warning panel
4. Warning requires acknowledgement: `--acknowledge-not-bulk-edit` flag or interactive prompt
5. If acknowledged: proceed normally. If not: block with instructions to either mark as bulk_edit or acknowledge

### 4. Mission Metadata Extension (FR-001)

**File**: `src/specify_cli/mission_metadata.py`
**Change**: Add `change_mode` to `MissionMetaOptional` TypedDict
**Values**: `"bulk_edit"` (only defined value for now; extensible for future modes)
**Backward compatibility**: Absent field means "not a bulk edit" — zero impact on existing missions

### 5. Guard System Registration

**File**: `src/specify_cli/mission_v1/guards.py`
**Change**: Add `occurrence_map_complete` guard primitive to `GUARD_REGISTRY`
**Expression**: `occurrence_map_complete()` — checks feature_dir for valid occurrence map when change_mode is bulk_edit

### 6. Expected Artifacts

**File**: `src/specify_cli/missions/software-dev/expected-artifacts.yaml`
**Change**: Add `occurrence_map.yaml` as a conditionally-required artifact
**Condition**: Required when `meta.json` has `change_mode: bulk_edit`

### 7. Doctrine Directive

**File**: `src/doctrine/directives/shipped/035-bulk-edit-occurrence-classification.directive.yaml`
**Content**: Defines the governance rule — bulk edits must classify occurrence categories before implementation
**Tactic refs**: Links to a new `occurrence-classification-workflow` tactic

### 8. Command Template Updates

**Files**:
- `src/specify_cli/missions/software-dev/command-templates/implement.md` — Add occurrence map check instructions
- `src/specify_cli/missions/software-dev/command-templates/review.md` — Add occurrence map review instructions

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Inference warning false positives annoy users | Medium | Low | Conservative keyword list + easy acknowledgement path |
| Occurrence map schema too rigid for diverse use cases | Low | Medium | Start minimal (target + categories + actions); extend schema later |
| Gate blocks implement for missions where user set change_mode accidentally | Low | Low | Clear error message with remediation (remove the flag or create the artifact) |
| change_mode field conflicts with future metadata fields | Very Low | Low | Reserved single field name; extensible enum pattern |

## Complexity Tracking

No charter violations. All work fits within the existing architecture using established patterns (guard functions, metadata fields, expected artifacts, doctrine directives).

## ADR

**ADR: Guard condition on implement action vs. first-class workflow step**

- **Decision**: Implement as a guard condition on the `implement` action (option A), not as a new workflow step type (option B) or pre-implement hook (option C).
- **Rationale**: The classification artifact is a mission-level planning deliverable, not a work-package output. A guard on `implement` enforces the rule at the only point that matters (before edits begin) without requiring new step types, status model changes, or dashboard semantics. This minimizes architectural churn while delivering the safety guarantee.
- **Follow-up**: If dashboard visibility or explicit status accounting becomes important, the guard can be promoted to a first-class workflow step (option B) in a future mission.

**ADR: Review compliance is artifact-admissibility, not diff-aware**

- **Decision**: v1 review gate validates occurrence map existence and structural completeness. It does not analyze the git diff against category rules.
- **Rationale**: Diff-aware classification requires occurrence-detection logic that borders on the "helper tooling" explicitly deferred in the spec. The occurrence map is a human-reviewed authority; the implementing and reviewing agents consult it. Automated diff enforcement is a hardening follow-on.
