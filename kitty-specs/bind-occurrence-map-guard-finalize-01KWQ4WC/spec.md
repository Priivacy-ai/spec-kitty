# Mission Specification: Bind Occurrence-Map Guard at Finalize

**Mission Branch**: `feat/bind-occurrence-map-guard-finalize`
**Created**: 2026-07-04
**Status**: Draft
**Input**: GitHub issue #2345 — "Bind the `occurrence_map_complete` guard at plan/tasks-finalize so bulk-edit schema errors fail before implement" (residual of #1347; overlaps #1790).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bulk-edit author is stopped at finalize, not at first implement (Priority: P1)

A contributor runs a bulk-edit mission (one that changes the same existing identifier/path/key/term across many files). Their `occurrence_map.yaml` is missing a required field or otherwise violates the occurrence-map schema. Today the mission passes task finalization and only fails much later, at the first `implement WP##` preflight — after lanes and worktrees have been computed and work has begun. This mission moves that failure to task finalization, where it is cheapest to fix.

**Why this priority**: This is the entire point of the issue — eliminating the late-failure timing that #1347/#1790 complained about. Without it the mission delivers no value.

**Independent Test**: Create a bulk-edit mission with an invalid `occurrence_map.yaml` (schema-invalid or inadmissible), run task finalization, and confirm finalization fails with the occurrence-map gate's error output — before any work package is implemented.

**Acceptance Scenarios**:

1. **Given** a bulk-edit mission whose `occurrence_map.yaml` is missing, schema-invalid, or inadmissible (e.g. below the minimum occurrence-category count, or carrying placeholder terms), **When** the contributor finalizes tasks, **Then** finalization fails and surfaces the occurrence-map gate's existing error output naming the problem.
2. **Given** a bulk-edit mission whose `occurrence_map.yaml` is present, schema-valid, **and admissible**, **When** the contributor finalizes tasks, **Then** finalization succeeds and proceeds to lane computation as before.

---

### User Story 2 - Non-bulk-edit missions are never gated on an occurrence map (Priority: P1)

A contributor runs an ordinary mission (a new capability, a localized bug fix — no cross-file identifier rename). Such a mission has no `occurrence_map.yaml` and is not expected to. The new finalize-time gate must be invisible to them: finalization behaves exactly as it does today.

**Why this priority**: A gate that fires on missions it does not apply to would block the majority of everyday work — a regression worse than the problem being solved. The guard must key on the stored classification, never on the mere absence of a file.

**Independent Test**: Finalize a non-bulk-edit mission with no `occurrence_map.yaml` and confirm finalization succeeds with no occurrence-map-related error and no behavioral change versus the pre-mission baseline.

**Acceptance Scenarios**:

1. **Given** a mission not classified as bulk-edit, **When** the contributor finalizes tasks, **Then** the occurrence-map gate does not run and finalization succeeds unchanged.

---

### User Story 3 - Implement-time gate remains a backstop (Priority: P2)

Even with the finalize-time gate in place, the existing implement-time enforcement must remain. If a bad occurrence map ever reaches implementation (e.g. edited after finalize, or a path that bypasses finalize), the first `implement WP##` still refuses to proceed.

**Why this priority**: Defense in depth. The issue explicitly requires the implement-time gate to persist as a backstop; removing it would trade one gap for another.

**Independent Test**: With a schema-invalid `occurrence_map.yaml` reaching the implement step, confirm the implement preflight still fails with the occurrence-map gate's error.

**Acceptance Scenarios**:

1. **Given** a bulk-edit mission with a schema-invalid `occurrence_map.yaml` at implement time, **When** a work package is implemented, **Then** the implement preflight still fails on the occurrence-map gate.

---

### Edge Cases

- **Missing file**: bulk-edit mission with no `occurrence_map.yaml` at all → finalize fails with a clear "missing/incomplete occurrence classification" error, not a stack trace.
- **Schema-invalid content**: file present but violates the occurrence-map schema → finalize fails and the error identifies the schema violation.
- **Inadmissible content**: file present and schema-valid but semantically inadmissible (below the minimum occurrence-category count, or carrying placeholder terms) → finalize fails; the gate rejects it exactly as the existing implement-time call does.
- **Classification absent/normal**: `change_mode` is unset or normal → the gate is a no-op and finalize proceeds.
- **Valid map**: schema-valid *and admissible* `occurrence_map.yaml` on a bulk-edit mission → finalize proceeds normally.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Finalize-time occurrence-map gate | As a bulk-edit mission author, I want task finalization to fail when my `occurrence_map.yaml` is missing or schema-invalid, so that I fix it before implementation begins. | High | Open |
| FR-002 | Gate reuses existing guard output | As a contributor, I want the finalize-time failure to carry the same occurrence-map error output that already exists, so that the message is consistent wherever it fires. | High | Open |
| FR-003 | Non-bulk-edit missions unaffected | As a contributor on an ordinary mission, I want finalization behavior unchanged, so that missions without an occurrence map are never blocked. | High | Open |
| FR-004 | Existing backstops preserved | As a maintainer, I want the two existing occurrence-map enforcement sites — the implement-time preflight (`implement.py`) and the review-workflow gate (`agent/workflow.py`) — to remain unchanged, so a bad map reaching implementation or review is still caught. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No finalize overhead for ordinary missions | For a non-bulk-edit mission, the added gate introduces no measurable finalize latency regression (added wall-time under 20 ms and no new filesystem scan beyond reading the already-loaded classification). | Performance | Medium | Open |
| NFR-002 | Quality gate | New/changed code passes `mypy --strict` and `ruff` with zero issues and zero warnings, with no new blanket suppressions (per charter DIR-006/DIR-030). | Maintainability | High | Open |
| NFR-003 | Branch coverage | Every new decision branch (bulk-edit fail, bulk-edit pass, non-bulk skip) is exercised by a focused test in the same change. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No new validation logic | Reuse the existing enforcement (`ensure_occurrence_classification_ready`, and its registered `occurrence_map_complete` guard wrapper); do not author new schema- or admissibility-validation code. | Technical | High | Open |
| C-002 | Bind at a surface the live runtime evaluates | Reuse an enforcement surface the live runtime actually runs: either add the registered `occurrence_map_complete` guard to the `plan → implement` FSM transition `conditions` in `software-dev/mission.yaml` (which already carries `artifact_exists("tasks.md")`), or reuse the existing in-command `ensure_occurrence_classification_ready` call pattern at the finalize / pre-implement path. Do NOT target a step-contract `guards` field (no such field exists) or the deprecated `mission_v1` `evaluate_guards` evaluator. | Technical | High | Open |
| C-003 | Condition on stored classification | The gate runs only when the mission's stored `change_mode` is `bulk_edit`; it must read the stored classification, never infer bulk-edit from the presence or absence of a file. | Technical | High | Open |
| C-004 | Backward compatibility | Existing missions and existing finalize/implement tests continue to pass; no change to the occurrence-map schema, template, or classification skill. | Technical | High | Open |
| C-005 | Live-surface verification is a hard plan gate | Before implementation, plan MUST identify which enforcement surface fires in the live `runtime.next` / `runtime_bridge` path at the plan-completion / pre-implement boundary and confirm the chosen binding is on that live path — not the deprecated `evaluate_guards` / `mission_v1` FSM evaluator. Planning may not proceed to tasks until this is pinned with evidence. | Technical | High | Open |

### Key Entities

- **`occurrence_map.yaml`**: the bulk-edit occurrence-classification artifact enumerating every occurrence of the target string and its per-occurrence disposition; checked for presence, schema validity, and admissibility.
- **`ensure_occurrence_classification_ready` / `occurrence_map_complete` guard**: the existing, tested enforcement. The *registry guard* (`occurrence_map_complete`) is currently wired into no live path; the *live* enforcement today is the direct `ensure_occurrence_classification_ready` call at the implement preflight sites. Both delegate to the same presence + schema + admissibility check and carry the canonical error output.
- **`change_mode` classification**: the stored mission attribute distinguishing `bulk_edit` from ordinary missions; the sole trigger for the gate.
- **`plan → implement` FSM transition (`software-dev/mission.yaml`)**: the declarative `conditions` surface that already carries `artifact_exists("tasks.md")`; the candidate binding point for the gate, pending the C-005 live-runtime confirmation. There is no step-contract-level `guards` field.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A bulk-edit mission with a missing, schema-invalid, or inadmissible `occurrence_map.yaml` fails at the plan-completion / task-finalization boundary — not at the first implement step — in 100% of runs, via an enforcement surface confirmed to fire in the live runtime.
- **SC-002**: Non-bulk-edit missions show zero new finalization failures; the existing finalize test suite passes unchanged.
- **SC-003**: An invalid occurrence map (schema-invalid or inadmissible) that reaches the implement step is still rejected by the implement-time backstop, verified by test.
- **SC-004**: The change introduces zero new `mypy`/`ruff` findings, and each new branch is covered by a focused test in the same change.

## Assumptions

- **The enforcement surface is deliberately unresolved at spec time and is a hard plan gate (see C-005).** Adversarial review confirmed the issue's framing is imprecise: there is no step-contract `guards` field; the registry guard `occurrence_map_complete` is registered but wired into no live path; the FSM `evaluate_guards` evaluator is deprecated (≥2.0.0); and the *live* occurrence-map enforcement today is a direct `ensure_occurrence_classification_ready` call at the implement preflight sites. Plan must pin the correct live surface, with evidence, before any code.
- "Plan/tasks-finalize transition" is treated as the plan-completion / pre-implement boundary; the `plan → implement` FSM transition (which already gates on `artifact_exists("tasks.md")`) is the natural candidate, subject to the C-005 live-runtime check.
- `ensure_occurrence_classification_ready` enforces three conditions — presence, schema validity, and admissibility — so "valid" throughout this spec means schema-valid *and* admissible.
- The rich-`occurrences` schema/template example requested in #1790 is explicitly out of scope for this mission (per the triage note on #2345).
