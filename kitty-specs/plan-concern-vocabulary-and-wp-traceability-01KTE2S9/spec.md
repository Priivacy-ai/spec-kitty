# Mission Specification: Plan Concern Vocabulary and WP Traceability

**Mission**: plan-concern-vocabulary-and-wp-traceability-01KTE2S9
**GitHub Issue**: #1730
**Date**: 2026-06-06
**Status**: Draft

---

## Summary

The plan phase and the tasks phase share no formal vocabulary for the intermediate layer between architecture-level intent and executable work packages. Plan templates currently use "Parallel Work Analysis", "Work Distribution", and "Agent Assignments" — language that reads as work-package-level decomposition. Agents and reviewers treat these plan slices as pseudo-WPs. When the tasks phase generates real `WP##` units, they diverge in wording from the plan slices, and there is no machine-readable link explaining the translation.

This mission introduces a formal **implementation concern** vocabulary (`IC-01`, `IC-02`, …) at the plan phase, replacing pseudo-WP sections in plan templates. It also adds a `plan_concern_refs` field to the WP manifest schema so every work package can cite which concern(s) it covers, making the plan-to-tasks translation explicit, traceable, and many-to-many.

---

## Actors

- **Planner** (human or agent): runs `/spec-kitty.plan` to produce planning artifacts
- **Tasks agent** (human or agent): runs `/spec-kitty.tasks` to translate plan concerns into executable WPs
- **Reviewer**: reads `plan.md` and `tasks.md` to verify the translation from plan intent to implementation units

---

## User Scenarios

### Primary scenario: Planner creates concerns, tasks agent traces them

1. Planner runs `/spec-kitty.plan` on an existing spec.
2. The plan template presents an **Implementation Concern Map** section with IC-01, IC-02 stubs.
3. Planner fills in each concern: id, name, purpose, relevant requirements, affected surfaces, sequencing dependencies, risks.
4. Plan explicitly states: implementation concerns are not executable — `/spec-kitty.tasks` translates them into WPs.
5. Planner runs `/spec-kitty.tasks` (or `tasks-outline`).
6. Tasks agent reads the concern map and produces `wps.yaml` where each WP lists `plan_concern_refs: [IC-01]` or `[IC-01, IC-03]` as appropriate.
7. `tasks-packages` generates WP prompt files that carry `plan_concern_refs` in frontmatter.
8. Generated `tasks.md` renders a "Plan concerns" line per WP.
9. Reviewer sees `plan.md` (concerns) → `tasks.md` (WPs with concern refs) and can trace intent without apparent mismatch.

### Edge case: concern splits across multiple WPs

A single concern (IC-02) is large enough to require three WPs. Each WP lists `plan_concern_refs: [IC-02]`. A single WP may also cover multiple concerns: `plan_concern_refs: [IC-01, IC-03]` when two small concerns are implemented together.

### Edge case: existing mission without concern refs

A pre-existing mission runs `finalize-tasks`. Its `wps.yaml` has no `plan_concern_refs` key on any entry. The system accepts it without error — the field defaults to an empty list.

### Edge case: cross-cutting WP

A WP that addresses infrastructure shared across all concerns (e.g., a test harness setup) has no specific concern. It declares `cross_cutting: true` with a rationale string in `wps.yaml`. The `finalize-tasks` command emits a warning (not an error) for WPs missing both `plan_concern_refs` and `cross_cutting`.

---

## Domain Language

| Canonical term | Definition | Avoid |
|----------------|-----------|-------|
| **Implementation concern** | A named, plan-level architectural unit of intent that captures purpose, affected surfaces, sequencing, and risks. Not executable. | "work block", "wave", "slice", "workstream" |
| **IC-##** | Two-digit identifier for an implementation concern (e.g. IC-01, IC-02). | WP-prefixed plan slices |
| **Implementation Concern Map** | The section of `plan.md` that lists all IC-## entries for a mission. | "Parallel Work Analysis", "Work Distribution" |
| **plan_concern_refs** | The list of IC-## identifiers in a `wps.yaml` WP entry that records which concerns the WP addresses. | N/A |
| **Work package (WP##)** | The only executable unit used by implementation, review, lane, and merge machinery. | "plan work package", "plan block" |

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | The plan template (`src/doctrine/missions/software-dev/templates/plan-template.md`) must replace the `## Parallel Work Analysis` section (including `### Work Distribution`, `### Dependency Graph`, and Agent assignments) with an `## Implementation Concern Map` section containing IC-## placeholder stubs with fields: concern-id, name, purpose, relevant-requirements, affected-surfaces, sequencing/dependencies-on, risks. | Proposed |
| FR-002 | The plan template must include an explicit note: "Implementation concerns are NOT work packages and are NOT executable units. `/spec-kitty.tasks` translates these into executable WPs. One concern may become multiple WPs; multiple small concerns may merge into one WP." | Proposed |
| FR-003 | The `/spec-kitty.plan` prompt (`src/doctrine/missions/mission-steps/software-dev/plan/prompt.md`) must be updated so its stop-point and report language refers to "implementation concerns" and states that `/spec-kitty.tasks` translates concerns into WPs — not that it "generates work packages from the plan". | Proposed |
| FR-004 | The built-in tasks step-contract (`src/doctrine/missions/built_in_step_contracts/tasks.step-contract.yaml`) step `outline` description must not imply WPs are directly derived from plan slices; it must reference concern translation. | Proposed |
| FR-005 | The legacy all-in-one tasks prompt (`src/doctrine/missions/mission-steps/software-dev/tasks/prompt.md`) description header must be updated from "Break a plan into work packages" to "Translate implementation concerns into work packages". | Proposed |
| FR-006 | `WorkPackageEntry` in `src/specify_cli/core/wps_manifest.py` must gain an optional field `plan_concern_refs: list[str]` with a default empty list and a field validator that rejects any entry not matching the pattern `IC-\d{2}` (e.g. IC-01, IC-23). `WorkPackageEntry` must also gain a `cross_cutting: bool` field with a default of `False`, used as an advisory marker for the FR-013 warning check. No pattern validator is needed for `cross_cutting` — pydantic handles bool coercion. | Proposed |
| FR-007 | `generate_tasks_md_from_manifest()` in `wps_manifest.py` must render a `**Plan Concerns**: IC-01, IC-03` line per WP when `plan_concern_refs` is non-empty, following the existing `**Requirement Refs**: …` and `**Owned Files**: …` rendering pattern. When `plan_concern_refs` is empty, render nothing (no label, no blank line). | Proposed |
| FR-008 | The `tasks-outline` prompt (`src/doctrine/missions/mission-steps/software-dev/tasks-outline/prompt.md`) must include a step requiring each WP to cite which IC-## concern(s) it addresses in `plan_concern_refs`, or explicitly declare `cross_cutting: true` with a rationale string. | Proposed |
| FR-009 | The `tasks-packages` prompt (`src/doctrine/missions/mission-steps/software-dev/tasks-packages/prompt.md`) must instruct agents to populate `plan_concern_refs` in `wps.yaml` entries for generated WPs. The prompt must NOT include `plan_concern_refs` in WP prompt file frontmatter templates — `WPMetadata` (which parses WP prompt frontmatter) is configured `extra="forbid"` and will raise `ValidationError` on `finalize-tasks --validate-only` if unknown fields appear in frontmatter. `plan_concern_refs` is a `wps.yaml`-only field. | Proposed |
| FR-010 | Existing missions whose `wps.yaml` contains no `plan_concern_refs` key must continue to parse, render, and finalize without error or warning. The field is optional with an empty-list default. | Proposed |
| FR-011 | The concern-to-WP mapping must support many-to-many: a single IC-## may appear in multiple WPs, and a single WP may list multiple IC-## refs. | Proposed |
| FR-012 | Command-renderer snapshot tests (`tests/specify_cli/skills/test_command_renderer.py`) must pass after template changes; snapshots must be regenerated if they fail due to template content changes. | Proposed |
| FR-013 | `finalize-tasks` must emit a non-fatal warning (not an error) for any WP missing both `plan_concern_refs` (empty or absent) and `cross_cutting: true`, to guide authors without blocking existing missions. The check must be implemented via a helper function `check_concern_refs_coverage(manifest: WpsManifest) -> list[str]` in `wps_manifest.py` (returning one warning string per non-compliant WP), called from the `finalize_tasks` command in `src/specify_cli/cli/commands/agent/mission.py` and appended to the existing `all_ownership_warnings` list. | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Backwards compatibility: no existing mission's `finalize-tasks` run fails due to the new field. | Zero regressions across all fixtures in `tests/` | Proposed |
| NFR-002 | Test coverage for the new `plan_concern_refs` field (parsing, validation, rendering, backwards-compat) must meet the project's 90% coverage standard for new code paths. | ≥90% branch coverage for touched `wps_manifest.py` paths | Proposed |
| NFR-003 | After template changes, the ripple check `rg "Parallel Work Analysis\|Work Distribution\|work-package outline derived from the plan\|Break a plan into work packages"` must return zero hits in live source template files. | 0 hits in `src/doctrine/missions/` and `src/specify_cli/missions/` | Proposed |
| NFR-004 | `mypy --strict` must pass on all modified Python files. | Zero type errors | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Real `WP##` IDs, lane/status/merge semantics, and `finalize-tasks` workflow control are unchanged. | Confirmed |
| C-002 | The `plan.md` hard stop before task generation is unchanged — `/spec-kitty.plan` still does not generate `tasks.md` or WP files. | Confirmed |
| C-003 | Historical `kitty-specs/` artifacts must not be rewritten unless tests explicitly depend on generated fixtures that must be updated. | Confirmed |
| C-004 | `mission_id`, `mission_number`, and all identity fields are untouched. | Confirmed |
| C-005 | The `cross_cutting` field in `wps.yaml` is advisory only — `finalize-tasks` warns but does not hard-fail on WPs lacking both `plan_concern_refs` and `cross_cutting`. | Confirmed |

---

## Success Criteria

1. A planner running `/spec-kitty.plan` on any new mission never sees "Parallel Work Analysis", "Work Distribution", or "Agent Assignments" section headers in the generated `plan.md`.
2. A tasks agent running `/spec-kitty.tasks` on a plan with IC-## entries produces a `wps.yaml` where every WP has at least one entry in `plan_concern_refs` (or `cross_cutting: true`), without manual instruction.
3. A reviewer reading a generated `tasks.md` can see which IC-## concern(s) each WP covers.
4. All existing missions' `finalize-tasks` calls succeed without error after the schema change is deployed.
5. The stale-phrase ripple check passes: zero hits for banned plan-phase pseudo-WP language in live source templates.
6. All renderer snapshot tests pass.

---

## Assumptions

- `src/specify_cli/missions/software-dev/templates/plan-template.md` (the second, specify_cli-tree copy) is stranded with no live runtime consumer and will be addressed separately by issue #1731; this mission targets only the doctrine-tree template.
- The `cross_cutting` field on `WorkPackageEntry` is a new optional boolean field with a `False` default; it need not be validated against a pattern.
- The `tasks-outline` prompt change (FR-008) is the primary enforcement point for concern citation; `finalize-tasks` warning (FR-013) is the secondary backstop.

---

## Out of Scope

- Renaming or resequencing real `WP##` IDs.
- Changing lane, status, implementation, review, or merge semantics.
- Requiring a strict one-to-one mapping between concerns and WPs.
- Rewriting historical `kitty-specs/` artifacts except where snapshot tests require fixture updates.
- Consolidating the redundant template tree (covered by issue #1731).
- Updating downstream repos (`spec-kitty-events`, `spec-kitty-orchestrator`, `agent-log-analyzer`) — those are generated-artifact follow-up work.
