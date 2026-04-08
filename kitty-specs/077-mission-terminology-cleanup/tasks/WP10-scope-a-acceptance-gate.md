---
work_package_id: WP10
title: Charter Reconciliation Spec Edit and Scope A Acceptance Gate
dependencies:
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
requirement_refs:
- FR-005
- FR-006
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Lane workspace per execution lane (resolved by spec-kitty implement WP10)
subtasks:
- T042
- T043
- T044
- T045
- T046
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: kitty-specs/077-mission-terminology-cleanup/
execution_mode: planning_artifact
mission_slug: 077-mission-terminology-cleanup
owned_files:
- kitty-specs/077-mission-terminology-cleanup/spec.md
- kitty-specs/077-mission-terminology-cleanup/research/scope-a-acceptance.md
priority: P0
tags: []
---

# WP10 — Charter Reconciliation Spec Edit and Scope A Acceptance Gate

## Objective

This WP closes Scope A. It performs two things:

1. The **one-line charter reconciliation edit** to spec §11.1: change "deprecated compatibility alias" → "hidden deprecated compatibility alias". This is the only spec change in this entire mission, and it aligns the spec language with the charter's "hidden secondary alias" requirement.

2. **All 15 acceptance gates** from spec §10.1, run mechanically and documented with evidence. This is the gate for Scope B (WP11+) per spec §2 + C-004.

## Context

Scope A consists of WP01-WP09. This WP is the synthesis: it verifies all those WPs landed correctly and produces the acceptance evidence document. The gate is **mechanical** — every check in spec §10.1 is grep, file existence, test pass, or exit-code assertion.

Per spec §2 + C-004, **Scope B work packages cannot be merged until WP10 acceptance is green on `main`**. WP10 is the literal gate.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP10` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T042 — Edit spec.md §11.1 — clarify "hidden deprecated compatibility alias"

**Purpose**: Make the one-line charter reconciliation edit. This is the **only** spec change in this mission.

**Steps**:
1. Open `kitty-specs/077-mission-terminology-cleanup/spec.md`.
2. Locate §11.1 (around line 332-360 — the "During the Migration Window" subsection of "Migration and Deprecation Policy").
3. The relevant lines describe `--feature` as a "deprecated compatibility alias". Per the charter (charter.md §Terminology Canon hyper-vigilance), it should be a **hidden** deprecated alias. Update the language:

   **Before** (around line 332):
   ```markdown
   - `--feature` is accepted as a compatibility alias on every tracked-mission command surface.
   ```

   **After**:
   ```markdown
   - `--feature` is accepted as a **hidden** compatibility alias on every tracked-mission command surface (i.e., declared with `typer.Option(..., hidden=True)`; not advertised in `--help`, examples, tutorials, or docs).
   ```

4. Search the rest of §11.1 and FR-005 for other places that say "deprecated compatibility alias" without the "hidden" qualifier and add the qualifier consistently.

5. **Critical**: this is a **clarification edit, not a behavior change**. Do not modify the runtime behavior described in §11.1 (the warning emit, the conflict detection, the suppression env var). Only the visibility language changes.

6. **Do not edit any other spec section.** The spec is otherwise frozen post-review.

### T043 — Run all 15 acceptance gates from spec §10.1

**Purpose**: Mechanically verify every gate.

**Steps**:
1. Read spec §10.1 and run each of the 15 gates in order. For each gate, capture the evidence (command output, file content, test result).

2. Gate-by-gate procedure:

   **Gate 1**: `rg --type py "(--mission-run|mission-run)" src/specify_cli/cli/commands` returns no result for tracked-mission selector definitions.
   ```bash
   rg --type py "(--mission-run|mission-run)" src/specify_cli/cli/commands
   ```
   Verify any remaining matches are in genuine runtime/session contexts.

   **Gate 2**: `rg --type py "Mission run slug" src/specify_cli/cli/commands` returns zero matches.
   ```bash
   rg --type py "Mission run slug" src/specify_cli/cli/commands
   ```
   Expected: empty.

   **Gate 3**: `mission current --mission A --feature B` exits non-zero with deterministic conflict error.
   ```bash
   uv run spec-kitty mission current --mission 077-test-A --feature 077-test-B
   echo "Exit code: $?"
   ```
   Expected: non-zero exit, conflict message.

   **Gate 4**: `mission current --feature X` succeeds, resolves same as `--mission X`, emits one warning.
   **Gate 5**: `mission current --feature X` exits with same code as `mission current --mission X`.
   **Gate 6**: `mission current --mission X --feature X` succeeds with one warning.

   ```bash
   uv run spec-kitty mission current --feature 077-mission-terminology-cleanup 2>&1 | head -5
   uv run spec-kitty mission current --mission 077-mission-terminology-cleanup --feature 077-mission-terminology-cleanup 2>&1 | head -5
   ```

   **Gate 7**: Every tracked-mission command surface passes the same canonical/alias/conflict assertions. Verified by passing test suite from WP03/WP04.

   **Gate 8**: Doctrine skills under `src/doctrine/skills/**` use `--mission`. Verified by guard 4 in WP09.

   **Gate 9**: Agent-facing docs under `docs/**` use `--mission`. Verified by guard 5 in WP09.

   **Gate 10**: Orchestrator-api remains canonical-only and unchanged.
   ```bash
   git diff main -- src/specify_cli/orchestrator_api/
   ```
   Expected: empty (no changes in this PR).

   **Gate 11**: Migration policy doc published and referenced from CLI deprecation warning. Verified by file existence + warning text smoke test.
   ```bash
   ls -la docs/migration/feature-flag-deprecation.md docs/migration/mission-type-flag-deprecation.md
   uv run spec-kitty mission current --feature 077-mission-terminology-cleanup 2>&1 | grep -o "docs/migration/feature-flag-deprecation.md"
   ```

   **Gate 12**: CI green on touched modules; coverage ≥ 90% on selector paths.
   ```bash
   uv run pytest --cov=specify_cli.cli.selector_resolution tests/specify_cli/cli/commands/test_selector_resolution.py
   ```

   **Gate 13**: None of the §3.3 non-goals appear in the diff.
   ```bash
   git diff main -- . | grep -E "(mission_run_slug|MissionRunCreated|MissionRunClosed|aggregate_type=\"MissionRun\")"
   ```
   Expected: empty.

   **Gate 14**: Each inverse-drift site uses `--mission-type` as canonical with `--mission` as deprecated alias.
   ```bash
   uv run spec-kitty agent mission create --help | grep -E "(--mission-type|--mission\b)"
   uv run spec-kitty charter interview --help | grep -E "(--mission-type|--mission\b)"
   uv run spec-kitty lifecycle specify --help | grep -E "(--mission-type|--mission\b)"
   ```
   Expected on each: `--mission-type` appears, `--mission` does not.

   **Gate 15**: No file under `kitty-specs/**` (other than `077-mission-terminology-cleanup/`) or `architecture/**` is modified.
   ```bash
   git diff --name-only main -- kitty-specs/ architecture/ | grep -v "077-mission-terminology-cleanup"
   ```
   Expected: empty.

3. Capture each gate's command, expected output, and actual output in a structured evidence document (T046).

### T044 — Verify orchestrator-api files unchanged (read-only check)

**Purpose**: Belt-and-suspenders verification of C-010.

**Steps**:
1. Confirm via git diff that none of the orchestrator-api files have been modified by this mission's diff:
   ```bash
   git diff --name-only main -- src/specify_cli/orchestrator_api/
   git diff --name-only main -- src/specify_cli/core/upstream_contract.json
   git diff --name-only main -- tests/contract/test_orchestrator_api.py
   ```
   Expected: all empty.

2. Confirm WP09 Guard 7 (envelope width) passes:
   ```bash
   PWHEADLESS=1 uv run pytest tests/contract/test_terminology_guards.py::test_orchestrator_api_envelope_width_unchanged -v
   ```

3. Confirm `tests/contract/test_orchestrator_api.py::TestForbiddenFlags::test_feature_flag_is_rejected` still passes (regression check):
   ```bash
   PWHEADLESS=1 uv run pytest tests/contract/test_orchestrator_api.py::TestForbiddenFlags::test_feature_flag_is_rejected -v
   ```

### T045 — Verify no historical artifacts modified (C-011 check)

**Purpose**: Belt-and-suspenders verification of C-011.

**Steps**:
1. Run the diff scope check:
   ```bash
   git diff --name-only main | grep -E "^(kitty-specs|architecture)/" | grep -v "kitty-specs/077-mission-terminology-cleanup"
   ```
   Expected: empty.

2. If any line is returned, that's a C-011 violation. Investigate, revert, or escalate.

3. Confirm WP09 Guard 8 (meta-guard) passes:
   ```bash
   PWHEADLESS=1 uv run pytest tests/contract/test_terminology_guards.py::test_grep_guards_do_not_scan_historical_artifacts -v
   ```

### T046 — Capture acceptance evidence and document Scope A completion

**Purpose**: Write a structured acceptance report that future reviewers (and the WP11+ Scope B WPs) can reference.

**Steps**:
1. Create `kitty-specs/077-mission-terminology-cleanup/research/scope-a-acceptance.md`:

   ```markdown
   # Scope A Acceptance Evidence

   **Mission**: 077-mission-terminology-cleanup
   **Scope**: Scope A (issue #241)
   **Acceptance date**: <DATE>
   **HEAD commit**: <git rev-parse HEAD>

   ## Gate Results

   | Gate | Description | Result | Evidence |
   |---|---|---|---|
   | 1 | rg --mission-run check | ✓ PASS | <command output or "empty"> |
   | 2 | rg "Mission run slug" check | ✓ PASS | <output> |
   | 3 | dual-flag conflict in mission current | ✓ PASS | <exit code + error message> |
   | 4 | --feature alias resolves correctly | ✓ PASS | <output> |
   | 5 | --feature exit code matches --mission | ✓ PASS | <both exit codes> |
   | 6 | same-value compat | ✓ PASS | <output> |
   | 7 | tracked-mission test suites pass | ✓ PASS | <pytest output> |
   | 8 | doctrine skills clean | ✓ PASS | <guard 4 output> |
   | 9 | agent-facing docs clean | ✓ PASS | <guard 5 + 5b output> |
   | 10 | orchestrator-api unchanged | ✓ PASS | <git diff empty> |
   | 11 | migration docs published + linked | ✓ PASS | <file list + warning grep> |
   | 12 | coverage ≥ 90% on selector paths | ✓ PASS | <coverage report> |
   | 13 | no §3.3 non-goals in diff | ✓ PASS | <grep output empty> |
   | 14 | inverse-drift sites canonical | ✓ PASS | <--help outputs> |
   | 15 | no historical artifacts modified | ✓ PASS | <git diff empty> |

   ## Spec §11.1 Edit

   The one-line charter reconciliation edit was applied at T042. Diff:
   ```
   <git diff of spec.md showing the §11.1 change>
   ```

   ## WP-by-WP Status

   | WP | Title | Status | Merge commit |
   |---|---|---|---|
   | WP01 | Selector Audit | ✓ Merged | <hash> |
   | WP02 | Selector Resolution Helper | ✓ Merged | <hash> |
   | WP03 | mission current Refactor | ✓ Merged | <hash> |
   | WP04 | next_cmd + agent/tasks Refactor | ✓ Merged | <hash> |
   | WP05 | Inverse Drift Refactor | ✓ Merged | <hash> |
   | WP06 | Doctrine Skills Cleanup | ✓ Merged | <hash> |
   | WP07 | Docs + Top-Level Cleanup | ✓ Merged | <hash> |
   | WP08 | Migration Docs | ✓ Merged | <hash> |
   | WP09 | CI Grep Guards | ✓ Merged | <hash> |
   | WP10 | Spec Edit + Acceptance | ✓ Merged | <hash> |

   ## Scope B Authorization

   With all 15 Scope A gates green, **Scope B (WP11-WP13) is authorized to begin** per
   spec §2 + C-004. The next step is to start WP11 (Machine-Facing Inventory).

   ## Charter Reconciliation Note

   The §11.1 edit aligns the spec language with the charter's "hidden secondary alias"
   language. The implementation behavior is unchanged from the original spec; only the
   visibility wording was updated. Verified by:
   - All `--feature` declarations in CLI command files use `hidden=True` (Guard 3)
   - `--feature` does not appear in `mission current --help` output (Gate 4 + 5 evidence)
   ```

2. Replace the `<...>` placeholders with actual command output captured during T043-T045.

3. Commit the acceptance report to `kitty-specs/077-mission-terminology-cleanup/research/`.

## Files Touched

| File | Action | Notes |
|---|---|---|
| `kitty-specs/077-mission-terminology-cleanup/spec.md` | MODIFY | One-line §11.1 clarification edit (T042) |
| `kitty-specs/077-mission-terminology-cleanup/research/scope-a-acceptance.md` | CREATE | Acceptance evidence (T046) |

**Out of bounds**: this WP does not modify any source code, doctrine skill, or doc. T043-T045 are read-only verification.

## Definition of Done

- [ ] Spec §11.1 contains the "hidden" qualifier on the `--feature` alias language (T042)
- [ ] All 15 gates from spec §10.1 are documented as PASS in the acceptance evidence (T043)
- [ ] Orchestrator-api files have no diff vs `main` (T044)
- [ ] No historical artifacts under `kitty-specs/**` (other than this mission) or `architecture/**` are modified (T045)
- [ ] `scope-a-acceptance.md` exists with all 15 gates and per-WP merge status (T046)
- [ ] WP09 Guards 7 and 8 pass (read-only verification gates)
- [ ] `tests/contract/test_orchestrator_api.py::TestForbiddenFlags::test_feature_flag_is_rejected` still passes
- [ ] No file outside this mission's `kitty-specs/077-mission-terminology-cleanup/` directory is modified by this WP

## Risks and Reviewer Guidance

**Risks**:
- A gate might fail because an upstream WP has a bug. Do not paper over it — return the WP to its owner for fix-up.
- The §11.1 edit is one line. Resist scope creep into other parts of the spec; the spec is otherwise frozen.
- The acceptance evidence document is read by future reviewers. Make it precise; use actual command output, not summaries.

**Reviewer checklist**:
- [ ] Spec §11.1 edit is the only spec change (no other spec lines touched)
- [ ] All 15 gates have actual evidence, not a "PASS" with no detail
- [ ] Orchestrator-api files have zero diff
- [ ] No `kitty-specs/**` (other than 077) or `architecture/**` modifications
- [ ] Scope B authorization paragraph is present and references §2 + C-004

## Implementation Command

```bash
spec-kitty implement WP10
```

This WP depends on WP03, WP04, WP05, WP06, WP07, WP08, WP09. All 7 Scope A WPs must be merged before WP10 starts. WP10 is the gate for Scope B (WP11+).

## References

- Spec §10.1 — All 15 acceptance gates
- Spec §11.1 — Migration policy (the edit target)
- Spec §2 + C-004 — Scope B sequencing constraint
- Charter §Terminology Canon — origin of the "hidden" qualifier
- Plan §"Charter Reconciliation"
