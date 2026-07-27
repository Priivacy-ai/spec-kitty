---
work_package_id: WP18
title: External enforcement, disclosure & deferral-contract docs (IC-10)
dependencies:
- WP04
- WP06
requirement_refs:
- FR-016
- FR-017
- FR-018
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T088
- T089
- T090
- T091
- T092
phase: Phase 9 - Enforcement, Docs & Archiving
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: docs/guides/accept-and-merge.md
create_intent:
- scripts/ci/check_dangling_deferrals.py
- src/specify_cli/status/deferral_disclosure.py
- tests/integration/test_deferral_enforcement_and_disclosure.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/guides/accept-and-merge.md
- scripts/ci/check_dangling_deferrals.py
- src/specify_cli/status/deferral_disclosure.py
- tests/integration/test_deferral_enforcement_and_disclosure.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP18 – External enforcement, disclosure & docs (IC-10)

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further. Consider consulting `curator-carla` guidance for the docs subtasks (T090–T092).

---

## Objectives & Success Criteria

The deferral contract's enforcement lives in CI (FR-016), not a loop guardrail (the matrix has one reader, pre-consolidation). Assign-time disclosure (FR-017) tells operators the loop will not verify a deferral and what gate they need. The operator guide (FR-018) makes the contract discoverable before an operator meets it. **Write the docs AFTER the semantics land.**

**Done** = a PR carrying a dangling `deferred_to_consolidation` invariant fails the CI check; assigning the deferral emits the disclosure; `accept-and-merge.md` describes the contract; `check_docs_freshness --ci` and `test_no_legacy_terminology.py` pass.

## Context & Constraints

- Spec FR-016/FR-017/FR-018; data-model NI-6/NI-7; ADR 2026-07-23-2.
- **Enforcement is EXTERNAL** — a consistency check at the front of the CI quality run, on the PR, where the consolidated tree and artifact are both available. Do NOT add a loop guardrail that cannot fire.
- **Terminology guard** is a CI-only gate — run `tests/architectural/test_no_legacy_terminology.py` before considering docs done (canonical `Mission`, `consolidation` not bare `merge`, `status commit` not `ceremony`).
- Doc index refresh needs `PYTHONPATH=.` (see #2887).
- The final paths (`scripts/ci/...`, `status/deferral_disclosure.py`) are indicative — confirm the actual CI-config surface and the status-assignment code path at implement time and adjust `owned_files`/`create_intent`.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T088 – FR-016 CI consistency check

- **Steps**: A check at the front of the CI quality run that fails any PR still carrying an unresolved `deferred_to_consolidation` invariant. Wire it into the CI quality-run configuration.

### Subtask T089 – FR-017 assignment-time disclosure

- **Steps**: When the status-assignment path writes `deferred_to_consolidation`, emit a disclosure telling the operator the loop will not verify it and what gate they need. (The write site is on the WP04 matrix/gates surface — edit under leeway, documented.)

### Subtask T090 – FR-018 guide

- **Steps**: Update `docs/guides/accept-and-merge.md` to explain when an invariant is deferred, what the post-consolidation step verifies, and what gate a downstream repo needs. Cross-link `docs/context/orchestration.md` (post-consolidation / `CONSOLIDATED` are already governed there).

### Subtask T091 – Refresh doc indexes + freshness gates

- **Steps**: `PYTHONPATH=. python scripts/docs/freshen_adr_inventory.py` then `PYTHONPATH=. python scripts/docs/docs_index.py --write`. Run `test_no_legacy_terminology.py` and `check_docs_freshness --ci`.

### Subtask T092 – Docs after behaviour

- **Steps**: Confirm the deferral semantics (WP04) and post-consolidation seam (WP06) have landed before writing the docs; docs written ahead of behaviour go stale silently.

## Test Strategy

- New: `tests/integration/test_deferral_enforcement_and_disclosure.py` (CI check fails on a dangling deferral; disclosure emitted at assignment).
- Run: `uv run --extra test pytest tests/architectural/test_no_legacy_terminology.py -q`; `check_docs_freshness --ci`.

## Risks & Mitigations

- Docs stale-silently if written early → T092 gate.
- Leeway: the disclosure emit site on the WP04 matrix/gates surface.

## Review Guidance

- Confirm enforcement is external (CI on the PR), not a loop guardrail.
- Confirm the terminology + docs-freshness gates pass.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
