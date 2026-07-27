# Bulk Edit Occurrence Classification Guardrail

**Mission**: bulk-edit-occurrence-classification-guardrail-01KP423X
**Source**: [Priivacy-ai/spec-kitty#393](https://github.com/Priivacy-ai/spec-kitty/issues/393)
**Parent**: [Priivacy-ai/spec-kitty#391](https://github.com/Priivacy-ai/spec-kitty/issues/391) — Tech Debt Remediation

## Problem Statement

When a codebase-wide edit changes a term (rename, terminology update, API migration), the same string appears in semantically different contexts: import paths, class/function names, filesystem path literals, dictionary/YAML keys, log messages, CLI command names, docstrings, and test fixtures. Each category may have different change rules — for example, a Python class name changes but the on-disk serialized key it writes to must not. Mechanical find-and-replace treats all occurrences identically, producing silent runtime breakage in categories that should have been excluded.

Today, Spec Kitty has no workflow mechanism to force a deliberate classification of occurrence types before edits begin. The result is that any mission or PR performing bulk string changes risks silent failures: tests that exercise the affected paths fail at runtime, but the edits themselves produce no errors or warnings at planning or review time.

## Motivation

Bulk renames and terminology migrations are common in healthy codebases. They become dangerous when the operator treats "rename X to Y everywhere" as a single mechanical operation rather than a multi-category decision. The cost of a missed category is high: serialized data becomes unreadable, CLI interfaces break for users, API contracts silently change, and test fixtures drift from production behavior — all without any build-time signal.

A guardrail that forces explicit category-by-category classification before implementation begins turns a high-risk mechanical task into a deliberate, reviewable decision.

## Actors

- **Mission Author** — The person who creates or specifies a mission that involves bulk edits. Responsible for declaring the mission as occurrence-sensitive and producing the classification artifact.
- **Implementing Agent** — The AI agent (or human) executing work packages. Blocked from starting implementation until the classification artifact exists and is accepted.
- **Reviewing Agent** — The agent or human reviewing completed work packages. Validates that the diff respects the approved classification (no changes to forbidden categories, no unclassified categories touched).
- **Spec Kitty Runtime** — The system enforcing gates: detecting missing declarations, blocking implementation without the artifact, and validating compliance at review.

## User Scenarios & Testing

### Scenario 1: Mission Author Declares Bulk Edit

A mission author creates a software-dev mission to rename the internal term "constitution" to "charter" across the codebase. During the specify or plan phase, they mark the mission as `change_mode: bulk_edit`. The system inserts a required `classify_occurrences` step before implementation. The author produces an occurrence map classifying each category (code symbols: rename, filesystem paths: review manually, serialized keys: do not change, etc.). Implementation is unblocked only after this artifact exists.

**Test**: Verify that a mission with `change_mode: bulk_edit` in its metadata gains the `classify_occurrences` step in its workflow. Verify that attempting to start implementation without the artifact produces a blocking error.

### Scenario 2: Inference Warning for Unmarked Mission

A mission author creates a software-dev mission with spec language like "rename all occurrences of X to Y across the codebase" but does not declare it as a bulk edit. The system detects rename/migration language in the spec and raises a warning: "This mission looks occurrence-sensitive. Mark it as a bulk edit or acknowledge that it is not." The author must explicitly acknowledge or mark the mission before proceeding.

**Test**: Verify that a mission with rename/migration keywords in the spec triggers a warning if `change_mode` is not set. Verify that the warning requires explicit acknowledgement.

### Scenario 3: Implementation Gate Enforcement

An implementing agent attempts to begin work on a WP in a mission marked as `change_mode: bulk_edit`. The classification artifact does not yet exist. The system blocks implementation with a clear error message identifying the missing artifact and how to produce it.

**Test**: Verify that `spec-kitty agent action implement WP01` fails with a descriptive error when the classification artifact is missing for a bulk-edit mission.

### Scenario 4: Review Compliance Validation

A reviewing agent checks a completed WP. The diff modifies strings in a category that was classified as `do_not_change` in the occurrence map. The review gate rejects the WP with a specific error identifying which files and categories violated the classification.

**Test**: Verify that review detects and rejects changes to categories marked `do_not_change`. Verify that review accepts changes that stay within approved categories.

### Scenario 5: Unclassified Category Appears in Diff

An implementing agent changes a string occurrence that falls in a category not present in the occurrence map (e.g., telemetry labels were never classified). The review gate rejects with a warning that unclassified categories were touched, requiring the author to update the classification artifact.

**Test**: Verify that review rejects diffs touching categories absent from the occurrence map.

## Functional Requirements

| ID | Requirement | Status |
|----|------------|--------|
| FR-001 | Mission metadata supports a `change_mode` field with at least the value `bulk_edit` to explicitly declare a mission as occurrence-sensitive | Proposed |
| FR-002 | When a mission is marked `change_mode: bulk_edit`, a required occurrence-classification artifact must exist and pass validation before the implement action proceeds. (Implemented as a guard condition on the implement action — see plan.md ADR.) | Proposed |
| FR-003 | The `classify_occurrences` step produces a machine-readable classification artifact (e.g., `occurrence_map.yaml`) listing each target token, its occurrence categories, and the approved action per category | Proposed |
| FR-004 | Occurrence categories include at minimum: code symbols, import/module paths, filesystem paths, serialized keys/API fields, CLI commands/flags, user-facing strings/docs, tests/snapshots/fixtures, logs/telemetry labels | Proposed |
| FR-005 | Per-category actions include at minimum: `rename`, `manual_review`, `do_not_change`, and `rename_if_user_visible` | Proposed |
| FR-006 | Implementation is blocked (cannot start any WP) until the classification artifact exists for a `bulk_edit` mission | Proposed |
| FR-007 | At review time, the system inspects the work-package diff and rejects it when any changed file maps (by path heuristic) to a category whose action is `do_not_change`, unless the file matches an explicit exception with a compatible action. | Proposed |
| FR-008 | At review time, the system inspects the work-package diff and rejects it when any changed file cannot be classified against the occurrence map's categories (unclassified surface touched). | Proposed |
| FR-009 | When a mission is not marked as `bulk_edit` but spec content contains rename/migration/replace-everywhere language, the system raises a warning requiring explicit acknowledgement | Proposed |
| FR-010 | The warning from FR-009 can be resolved by either marking the mission as `bulk_edit` or explicitly acknowledging that bulk-edit classification is not needed | Proposed |
| FR-011 | Doctrine artifacts are updated to define the bulk-edit classification rule as a governance requirement | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|------------|-----------|--------|
| NFR-001 | The implementation gate check completes within 2 seconds of the implement command invocation | < 2 seconds | Proposed |
| NFR-002 | The review compliance validation adds no more than 5 seconds to a standard WP review cycle | < 5 seconds | Proposed |
| NFR-003 | The inference warning (FR-009) has a false-positive rate below 20% on missions that are genuinely not bulk edits | < 20% false positive rate | Proposed |
| NFR-004 | The classification artifact format is human-readable and editable in any text editor without specialized tooling | Human-editable YAML | Proposed |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | The classification artifact is authored by humans (or AI with human review); the system does not attempt automated language-aware AST classification | Proposed |
| C-002 | The feature works within existing mission types (software-dev primarily); no new mission type is created | Proposed |
| C-003 | Optional scan/suggestion tooling that proposes classification buckets is assistive only and never authoritative — the human-reviewed artifact is the sole authority | Proposed |
| C-004 | The feature must work across all 12 supported AI agents without agent-specific behavior | Proposed |

## Success Criteria

1. **Zero unclassified bulk edits reach review** — When a mission is marked as a bulk edit, 100% of implementation attempts are blocked until the classification artifact exists and every standard occurrence category (FR-004) is classified.
2. **Forbidden-category violations caught before merge** — Review rejects 100% of diffs where a changed file is classified (by path heuristic) into a category whose action is `do_not_change`, unless an explicit exception overrides that action.
3. **Unclassified categories flagged** — Review rejects 100% of diffs where any changed file cannot be mapped to a known category and no matching exception is declared.
4. **Inference warning surfaces risky missions** — At least 80% of missions containing rename/migration language that are not marked as bulk edits receive a warning before implementation begins.
5. **No workflow slowdown for non-bulk-edit missions** — Missions without the `bulk_edit` flag experience zero additional gates or delays.

**Note on classification method**: The review gate classifies each changed file
by its filesystem path (extension and directory heuristics). This is a
deliberate trade-off per constraint C-001 — full AST-level classification is
out of scope. Authors can override a path-based classification using the
`exceptions` section of the occurrence map (e.g., to allow changes to a
specific YAML file while keeping `serialized_keys: do_not_change` as the
default rule).

## Key Entities

- **Occurrence Map** — Machine-readable artifact (`occurrence_map.yaml`) that classifies target tokens by occurrence category with per-category change actions. Created during the `classify_occurrences` step. Authoritative for implementation and review gates.
- **Occurrence Category** — A semantic context in which a target string appears (e.g., code symbol, import path, filesystem path, serialized key, CLI text, docs, tests, logs).
- **Change Action** — The approved operation for a given category: `rename`, `manual_review`, `do_not_change`, or `rename_if_user_visible`.
- **Change Mode** — Mission metadata field declaring the mission's edit sensitivity. `bulk_edit` triggers the classification workflow.

## Assumptions

- Mission authors have sufficient understanding of their codebase to classify occurrence categories meaningfully. The system provides categories but does not perform static analysis.
- The `change_mode` metadata field can be added to `meta.json` without breaking existing missions that lack it (absence means "not a bulk edit").
- Doctrine updates can reference the classification requirement without requiring a new doctrine version or migration.
- The inference warning (FR-009) uses simple keyword matching on spec content, not semantic analysis.

## Scope Boundaries

**In scope:**
- Mission metadata declaration (`change_mode: bulk_edit`)
- Required `classify_occurrences` planning step with artifact production
- Implementation gate blocking on missing artifact
- Review compliance validation against the artifact
- Inference warning for unmarked missions with rename/migration language
- Doctrine updates defining the governance rule

**Out of scope:**
- Automated language-aware occurrence classification (AST parsing, tree-sitter, etc.)
- Automatic bulk refactoring execution
- A standalone mission type for renames
- Cross-repository occurrence tracking
- Helper scan tooling that proposes classification buckets (deferred to a follow-on)

## Dependencies

- Existing mission metadata system (`meta.json`) for the `change_mode` field
- Existing workflow step injection mechanism for inserting `classify_occurrences`
- Existing implementation gate infrastructure (used by lane-based execution)
- Existing review validation hooks
- Doctrine/charter system for governance rule definition
