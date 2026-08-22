---
work_package_id: WP03
title: Write/echo/audit boundaries + FR-009 exemption allow-list
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-006
- FR-009
planning_base_branch: rc3-canonical-mission-type-reader-01M0GGWM
merge_target_branch: rc3-canonical-mission-type-reader-01M0GGWM
branch_strategy: Planning artifacts for this mission were generated on rc3-canonical-mission-type-reader-01M0GGWM. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-canonical-mission-type-reader-01M0GGWM unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
phase: Phase 2 - Convergence
history:
- at: '2026-08-22T04:16:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/architectural/inline_meta_read_allowlist.yaml
- tests/specify_cli/test_mission_type_write_boundaries.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_create.py
- src/specify_cli/cli/commands/_mission_type_audit.py
- src/specify_cli/upgrade/feature_meta.py
- src/charter/interview.py
- tests/architectural/inline_meta_read_allowlist.yaml
- tests/specify_cli/test_mission_type_write_boundaries.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Write/echo/audit boundaries + FR-009 exemption allow-list

## Objectives & Success Criteria

- Classify the **non-read** sites (research.md WRITE-BOUNDARY / EXEMPT rows):
  converge the *field set* where a site still **echoes** legacy `mission`; keep
  create/inference writers and the field-aware audit tool as-is, each with an
  encoded rationale (FR-002, FR-006).
- **FR-009**: encode the inline `meta.json` reads in the frozen migrations and any
  charter-layer read as either replay-equivalent conversions **or**
  `inline_meta_read_allowlist.yaml` exemptions citing #2477–#2480 — **never a
  silent path-exclude** (AC-6).

## Context & Constraints

- Depends on **WP01** (the FR-010 gate consumes the allow-list this WP creates).
- Load `../research.md` §FR-009 and the WRITE-BOUNDARY census rows.
- The allow-list is the encoded seam the FR-010 source-scan reads: every entry
  MUST carry an issue ref + one-line rationale. It is an allow-list of *encoded
  exemptions*, not a path-exclude.

## Branch Strategy

- **Merge target branch**: `rc3-canonical-mission-type-reader-01M0GGWM`

## Subtasks & Detailed Guidance

### Subtask T015 – mission_create echo field set
- **Steps**: `mission_create.py:374` echoes `meta.get("mission_type", meta.get("mission", ""))` into the result dict. Drop the legacy `mission` echo → `str(result.meta.get("mission_type", ""))` (or delegate via the seam on the dict). Pin the echoed value.

### Subtask T016 [P] – feature_meta infer_mission
- **Steps**: `upgrade/feature_meta.py` `infer_mission` reads `mission_type` only and returns `"software-dev"` on `_set_if_blank` **write**. This is inference-on-upgrade (a writer), not a runtime read. Document the default disposition; if converged, keep the create-time default explicit and note why. Pin behavior.

### Subtask T017 [P] – interview payload exemption
- **Steps**: Confirm `charter/interview.py:225` reads the **interview form payload** (`self.mission`, line 209), not `meta.json`'s `mission_type`. Encode as exempt-with-rationale (not a runtime meta-type reader).

### Subtask T018 [P] – audit tool stays field-aware
- **Steps**: `_mission_type_audit.py` reads both fields **by design** — it classifies legacy-only as its own bucket (the census/audit tool). Keep it field-aware; add an allow-list entry with rationale. Ensure its existing legacy-only classification test still passes.

### Subtask T019 – inline_meta_read_allowlist.yaml
- **Steps**: Create `tests/architectural/inline_meta_read_allowlist.yaml` with entries: `m_0_13_0_research_csv_schema_check.py` (historical legacy `mission` read, #2477); `m_0_13_5_add_commit_workflow_to_templates.py` (`mission_name`, different field/file); `migration/mission_state.py:1617` (frozen legacy→canonical backfill write); `_mission_type_audit.py` (field-aware census tool). Each: `path`, `issue`, `rationale`.

### Subtask T020 – Frozen-migration replay/exempt
- **Steps**: For each frozen migration site, either add a byte-exact replay-equivalence assertion vs. `main`, or rely on the encoded exemption. No silent path-exclude. Add/confirm a fixture-replay test where feasible.

## Test Strategy

- `pytest tests/specify_cli/test_mission_type_write_boundaries.py tests/architectural/test_mission_type_reader_invariants.py -q`
- The FR-010 source-scan now reads the allow-list; write-boundary sites are either converged or encoded-exempt.

## Risks & Mitigations

- Over-converging a writer removes a legitimately-needed create-time default → keep writers as writers.
- Frozen-migration replay drift → prefer encoded exemption where equivalence can't be guaranteed.

## Review Guidance

- Every allow-list entry has an issue + rationale; no silent path-exclude; the audit tool's legacy-only bucket still works; echo path no longer reads legacy.

## Activity Log

- 2026-08-22T04:16:17Z – system – Prompt created.
