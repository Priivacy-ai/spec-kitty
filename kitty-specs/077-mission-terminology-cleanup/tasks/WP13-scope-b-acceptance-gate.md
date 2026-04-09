---
work_package_id: WP13
title: Contract Docs Alignment and Scope B Acceptance Gate
dependencies:
- WP12
requirement_refs:
- FR-013
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T057
- T058
- T059
- T060
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: docs/reference/
execution_mode: code_change
mission_slug: 077-mission-terminology-cleanup
owned_files:
- docs/reference/event-envelope.md
- docs/reference/orchestrator-api.md
- kitty-specs/077-mission-terminology-cleanup/research/scope-b-acceptance.md
priority: P1
tags: []
---

# WP13 — Contract Docs Alignment and Scope B Acceptance Gate

> ⚠️ **GATED**: This WP cannot start until WP12 is merged on `main`. Per spec §2 + C-004.

## Objective

Update the first-party machine-facing contract docs (`docs/reference/event-envelope.md`, `docs/reference/orchestrator-api.md`) to align with `spec-kitty-events 3.0.0` and the alias window from spec §11.1. Run cross-repo first-party consumer fixtures to verify NFR-006 (zero breakages). Run all spec §10.2 acceptance criteria. Document Scope B completion and close `#543`.

## Context

This is the final WP in the mission. After WP13 lands:
- Scope A (`#241`) is closed
- Scope B (`#543`) is closed
- The mission is complete

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP13` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T057 — Update contract reference docs [P]

**Purpose**: Bring `docs/reference/event-envelope.md` and `docs/reference/orchestrator-api.md` into alignment with the canonical state.

**Steps**:
1. Open `docs/reference/event-envelope.md` (if it exists). Update:
   - Field naming to match `upstream_contract.json` envelope section
   - Any examples that use `feature_slug`/`feature_number` → use `mission_slug`/`mission_number`
   - Add a "Migration" section pointing to the deprecation docs from WP08
2. Open `docs/reference/orchestrator-api.md` (if it exists). Update:
   - CLI flag examples to use `--mission`
   - Field naming examples
   - Note that `--feature` is forbidden in orchestrator-api per `upstream_contract.json`
   - Cross-link to `kitty-specs/077-mission-terminology-cleanup/spec.md` §11.1 for the asymmetric migration policy
3. **Critical**: do not touch `src/specify_cli/orchestrator_api/**` (C-010). This subtask is doc-only.

### T058 — Run cross-repo first-party consumer fixtures and verify NFR-006

**Purpose**: Confirm zero breakages in downstream consumers.

**Steps**:
1. If cross-repo first-party consumer fixtures exist (e.g., in `tests/contract/test_cross_repo_consumers.py`), run them:
   ```bash
   PWHEADLESS=1 uv run pytest tests/contract/test_cross_repo_consumers.py -v
   ```
2. Verify zero breakages.
3. If fixtures do not exist, create a minimal smoke test that imports `spec-kitty-events` and verifies the canonical event names and field names are unchanged from the validated baseline.
4. Document the result in the Scope B acceptance evidence.

### T059 — Run all spec §10.2 acceptance criteria and capture evidence

**Purpose**: Mechanical verification of Scope B's 9 gates.

**Steps**:
1. Read spec §10.2 and run each of the 9 gates. Capture evidence in `scope-b-acceptance.md`.
2. Per-gate procedure (mirrors WP10 T043 structure):

   **Gate 1**: Every first-party machine-facing payload identifying a tracked mission carries `mission_slug`, `mission_number`, `mission_type`. Verified by `tests/contract/test_machine_facing_canonical_fields.py` (from WP12).

   **Gate 2**: Any remaining `feature_*` field is removed, gated, or marked deprecated. Verified by reading the WP11 alignment plan and confirming each decision was applied.

   **Gate 3**: No `mission_run_slug` anywhere. Verified by `test_no_mission_run_slug_in_first_party_payloads` (from WP12).

   **Gate 4**: `MissionCreated`/`MissionClosed` event names unchanged. Verified by `test_mission_created_and_closed_event_names_unchanged` (from WP12).

   **Gate 5**: `aggregate_type="Mission"` unchanged. Verified by `test_aggregate_type_mission_unchanged` (from WP12).

   **Gate 6**: First-party machine-facing surfaces match `spec-kitty-events 3.0.0` field naming. Verified by reading the contract test results.

   **Gate 7**: Compatibility alias window is documented in one place. Verified by checking `docs/reference/orchestrator-api.md` (T057) has the migration section.

   **Gate 8**: CI green; cross-repo consumer fixtures show 0 breakages (NFR-006). Verified by T058.

   **Gate 9**: None of the §3.3 non-goals appear in the diff.
   ```bash
   git diff --name-only main -- . | grep -E "(mission_run_slug|MissionRunCreated|MissionRunClosed)"
   ```
   Expected: empty.

### T060 — Document Scope B completion and close `#543`

**Purpose**: Write the Scope B acceptance evidence and prepare to close the tracking issue.

**Steps**:
1. Create `kitty-specs/077-mission-terminology-cleanup/research/scope-b-acceptance.md`:
   ```markdown
   # Scope B Acceptance Evidence

   **Mission**: 077-mission-terminology-cleanup
   **Scope**: Scope B (issue #543)
   **Acceptance date**: <DATE>
   **HEAD commit**: <git rev-parse HEAD>
   **Scope A acceptance**: see `scope-a-acceptance.md`

   ## Gate Results

   | Gate | Description | Result | Evidence |
   |---|---|---|---|
   | 1 | canonical fields per surface | ✓ PASS | <test output> |
   | 2 | feature_* fields removed/gated/deprecated | ✓ PASS | <inventory completion> |
   | 3 | no mission_run_slug | ✓ PASS | <grep empty> |
   | 4 | MissionCreated/MissionClosed unchanged | ✓ PASS | <grep empty> |
   | 5 | aggregate_type="Mission" unchanged | ✓ PASS | <grep empty> |
   | 6 | spec-kitty-events 3.0.0 alignment | ✓ PASS | <test output> |
   | 7 | compat window documented | ✓ PASS | <doc link> |
   | 8 | cross-repo consumers 0 breakages | ✓ PASS | <test output> |
   | 9 | no §3.3 non-goals in diff | ✓ PASS | <grep empty> |

   ## WP-by-WP Status

   | WP | Title | Status | Merge commit |
   |---|---|---|---|
   | WP11 | Machine-Facing Inventory | ✓ Merged | <hash> |
   | WP12 | Canonical Field Rollout | ✓ Merged | <hash> |
   | WP13 | Contract Docs + Acceptance | ✓ Merged | <hash> |

   ## Mission Complete

   Both Scope A (#241) and Scope B (#543) are accepted. The mission is closed.

   Final state:
   - Operator-facing CLI: canonical `--mission` everywhere; `--feature` is hidden deprecated alias
   - Inverse drift: `--mission-type` canonical on the 3 verified sites; `--mission` is hidden deprecated alias on those sites
   - Doctrine skills + agent-facing docs: clean
   - Top-level project docs (README, CONTRIBUTING, CHANGELOG Unreleased): clean
   - Migration docs published
   - 9 grep guards prevent regression
   - Machine-facing payloads canonical
   - Orchestrator-api unchanged (C-010 honored)
   - Historical artifacts unchanged (C-011 honored)
   ```

2. After this WP merges, the tracking issues `#241` and `#543` may be closed.

## Files Touched

| File | Action |
|---|---|
| `docs/reference/event-envelope.md` | MODIFY |
| `docs/reference/orchestrator-api.md` | MODIFY |
| `kitty-specs/077-mission-terminology-cleanup/research/scope-b-acceptance.md` | CREATE |

## Definition of Done

- [ ] Both contract reference docs are aligned with `spec-kitty-events 3.0.0` and the §11.1 alias window
- [ ] Cross-repo consumer fixtures pass with 0 breakages (NFR-006)
- [ ] All 9 gates from spec §10.2 are documented as PASS in the acceptance evidence
- [ ] `scope-b-acceptance.md` exists with all 9 gates and per-WP merge status
- [ ] `#241` and `#543` can be closed
- [ ] No source code changes outside the docs (this WP is doc + verification only)

## Risks and Reviewer Guidance

**Risks**:
- The contract reference docs may have many examples; updating them all without breaking cross-references is tedious. Verify links after every edit.
- Cross-repo consumer fixtures may not exist; if not, create minimal ones in T058 or document the absence in the evidence.

**Reviewer checklist**:
- [ ] Both reference docs updated to match canonical state
- [ ] Migration docs cross-linked from the reference docs
- [ ] All 9 §10.2 gates have actual evidence
- [ ] Per-WP merge status is documented in the evidence file
- [ ] No source code changes
- [ ] No `kitty-specs/**` modifications outside this mission

## Implementation Command

```bash
spec-kitty implement WP13
```

This WP depends on WP12. Do not start until WP12 is merged on `main`.

## References

- Spec §10.2 — Scope B acceptance criteria
- Spec §11 — Migration policy
- Spec §13.2 — Scope B work package outline
- WP11 inventory + WP12 implementation
- `upstream_contract.json` — canonical contract

## Activity Log

- 2026-04-08T15:01:38Z – unknown – Done override: Mission completed in main checkout
