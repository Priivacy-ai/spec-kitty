---
work_package_id: WP07
title: Consolidated golden-path E2E + docs sync
dependencies:
- WP01
- WP02
- WP05
- WP06
requirement_refs:
- FR-016
- FR-017
planning_base_branch: release/3.2.0a6-tranche-2
merge_target_branch: release/3.2.0a6-tranche-2
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a6-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a6-tranche-2 unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
- T039
- T040
agent: "claude:opus-4-7:default:reviewer"
shell_pid: "72407"
history:
- at: '2026-04-28T09:30:00Z'
  by: spec-kitty.tasks
  note: Created as part of tranche-2 specify→plan→tasks pipeline
authoritative_surface: tests/e2e/test_charter_epic_golden_path.py
execution_mode: code_change
owned_files:
- tests/e2e/test_charter_epic_golden_path.py
- docs/**/*.md
- CHANGELOG.md
tags: []
---

# WP07 — Consolidated golden-path E2E + docs sync

## Branch Strategy

- **Planning/base branch**: `release/3.2.0a6-tranche-2`
- **Final merge target**: `release/3.2.0a6-tranche-2`
- Lane A, position 3 (capstone after WP06; depends on WP01, WP02, WP05, WP06).
- Implementation command: `spec-kitty agent action implement WP07 --agent claude`.

## Objective

The end-to-end golden-path test exercises the full fresh-project chain through the public CLI only and passes within the 120-second CI budget. User-facing docs match the new CLI invariants. CHANGELOG carries a tranche-2 summary. A final acceptance pass confirms all spec success criteria are met.

## Context

This is the capstone WP. It does not introduce new behavior; it certifies that the rest of the tranche works together and updates the surrounding documentation. Its dependency set spans the fresh-project chain (WP01, WP06) plus the production-state fixes (WP02 strict JSON, WP05 lifecycle records) that the consolidated E2E exercises.

**FRs**: FR-016, FR-017 · **NFR**: NFR-007 · **SC**: SC-001, SC-007, SC-008 · **Spec sections**: Scenario 7 exception path; Acceptance section · **Quickstart**: [quickstart.md](../quickstart.md)

## Always-true rules

- The E2E uses **public CLI only** (per Assumption A2).
- The E2E does **not** hand-seed `.kittify/doctrine/`.
- The E2E does **not** hand-edit `.kittify/metadata.yaml`.
- The E2E completes in **< 120s** on CI (NFR-007).

---

## Subtask T036 — Update `tests/e2e/test_charter_epic_golden_path.py`

**Purpose**: Tighten the golden-path E2E so it exercises only what users actually run.

**Steps**:

1. Open `tests/e2e/test_charter_epic_golden_path.py`. Identify and remove:
   - Any block that pre-creates files under `.kittify/doctrine/`.
   - Any block that writes or rewrites `.kittify/metadata.yaml` by hand.
   - Any internal-API call that bypasses the public CLI to seed state.
2. Replace those blocks with the public CLI sequence:
   ```bash
   spec-kitty init
   spec-kitty charter setup            # use whatever non-interactive mode the test fixture supports
   spec-kitty charter generate
   spec-kitty charter bundle validate  # MUST succeed (validates WP06 / #841)
   spec-kitty charter synthesize       # MUST succeed without hand seeding (validates WP06 / #839)
   spec-kitty next --agent claude --mission <slug>   # MUST work end-to-end
   ```
   Use the existing `runner` / `cli_runner` fixture for invocation.
3. Add assertions that exercise the other tranche fixes:
   - For `--json` outputs (e.g., `mission branch-context --json`): `json.loads(result.stdout)` succeeds (validates WP02 / #842).
   - After `next` issues an action: assert at least one `started` profile-invocation lifecycle record is present in the local store (validates WP05 / #843).
4. Wrap any SaaS-touching subcommand with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` per C-003.

**Files to edit**:
- `tests/e2e/test_charter_epic_golden_path.py`

---

## Subtask T037 — Verify under-120s budget on CI

**Purpose**: Ensure the consolidated E2E doesn't bloat CI time.

**Steps**:

1. Run the test locally with timing:
   ```bash
   PWHEADLESS=1 pytest tests/e2e/test_charter_epic_golden_path.py -v --durations=10
   ```
2. If wall-clock exceeds ~100s locally (CI overhead typically adds 10–20%), profile the slowest fixture / subcommand and reduce work (skip non-essential post-conditions, prefer in-memory mocks for SaaS).
3. Add an assertion or `pytest` marker that captures the budget intent:
   ```python
   @pytest.mark.timeout(120)
   def test_charter_epic_golden_path(...):
       ...
   ```
   (Use `pytest-timeout` if it's already a dev dep; otherwise document the budget in a docstring and rely on CI step timeout.)

**Files to edit**:
- `tests/e2e/test_charter_epic_golden_path.py`

---

## Subtask T038 — Update governance setup docs to remove redundant `git add`  [P]

**Purpose**: Match docs to FR-013/FR-014 invariant.

**Steps**:

1. Search the docs tree for any documented governance-setup flow that still tells the operator to run `git add charter.md` (or similar) between `charter generate` and `charter bundle validate`. Likely locations:
   - `docs/explanation/`
   - `docs/how-to/`
   - `docs/charter/`
   - The README, if it covers the governance flow.
2. Remove the redundant `git add` step. Replace with a one-line note that `charter generate` now auto-tracks the produced files (post-#841).
3. If the docs include a worked example, update it to reflect the new sequence.

**Files to edit**:
- `docs/**/*.md` (per the inventory)

---

## Subtask T039 — CHANGELOG entry: tranche-2 summary  [P]

**Purpose**: Stitch the per-WP CHANGELOG entries into a tranche-level summary.

**Steps**:

1. In `CHANGELOG.md`, add a top-level "3.2.0a6 — Tranche 2 (bug-only)" section with:
   - One-line per fixed issue (#840, #842, #833, #676, #843, #841, #839), each linking to its issue.
   - A short paragraph stating the tranche's goal: restore the fresh-project golden path, lock in strict JSON, fix agent identity and review-cycle accounting, add `next` lifecycle observability.
2. Verify per-WP entries from WP01, WP02 are not duplicated by this summary — they can coexist as the section header for individual entries.

**Files to edit**:
- `CHANGELOG.md`

---

## Subtask T040 — Final acceptance pass against `spec.md` SC-001..SC-008

**Purpose**: Certify the tranche.

**Steps**:

1. Walk every Success Criterion in `spec.md` and verify it is supported by a passing test or a documented run:
   - SC-001 (Fresh-path completion): T036 covers.
   - SC-002 (JSON parsability): WP02 tests cover; T036 spot-checks one `--json` command.
   - SC-003 (Identity preservation): WP03 tests cover.
   - SC-004 (Review-cycle precision): WP04 tests cover.
   - SC-005 (Lifecycle observability): WP05 tests cover; T036 spot-checks.
   - SC-006 (Charter parity rate): WP06 tests cover.
   - SC-007 (Documentation/CLI agreement): T038 covers.
   - SC-008 (Bug-only discipline): grep the merged diff for new public CLI subcommands or new top-level deps; assert zero. Add a note in the PR description.
2. Add a "Tranche-2 acceptance pass" comment in the PR description listing each SC and the test/run that demonstrates it.

**Files to edit**:
- (none in code; this is a PR-description / final-check task)

---

## Test Strategy

- **E2E**: T036 + T037 are the consolidated proof.
- **Cross-WP**: T036 also touches `--json`, `next` lifecycle records, and charter generate/synthesize as side proofs.
- **Coverage**: maintain ≥ 90% on touched code (NFR-002).
- **Type safety**: `mypy --strict` clean.

## Definition of Done

- [ ] T036 — golden-path E2E uses public CLI only, no hand seeding, no metadata edit.
- [ ] T037 — E2E completes in < 120s on CI.
- [ ] T038 — governance docs match the new CLI invariants.
- [ ] T039 — CHANGELOG carries tranche-2 summary.
- [ ] T040 — all SC-001..SC-008 demonstrably met.
- [ ] All upstream WPs (WP01, WP02, WP05, WP06) merged and passing on this branch.

## Risks

- **Risk**: Removing seed code reveals an additional hidden dependency.
  **Mitigation**: Run T036 against the merged tranche-2 branch first; if it fails, the failing assertion identifies what WP01/WP02/WP05/WP06 missed. Escalate to those WPs rather than re-introducing the seed.
- **Risk**: Doc grep misses a redundant `git add` instruction.
  **Mitigation**: Use a literal grep for `git add charter.md` (and a few near-miss variants) across the entire docs tree.
- **Risk**: 120s budget too tight on slow CI runners.
  **Mitigation**: Profile via `--durations`; if a subcommand dominates, mock it down. If profile reveals the budget is intrinsically too tight, escalate to revisit NFR-007 — do not silently raise the budget.

## Reviewer guidance

- Read the diff of `tests/e2e/test_charter_epic_golden_path.py` line by line: every removed seed block must be traceable to a tranche-2 fix.
- Verify the test does not reach into `.kittify/doctrine/` directly anywhere except through the CLI.
- Verify the docs diff does not introduce new content beyond removing the redundant step (we are documenting an existing change, not designing new docs).
- Verify the CHANGELOG summary references all seven issues.
- Verify the SC-008 acceptance note in the PR description: zero new public CLI subcommands, zero new top-level deps.

## Out of scope

- New tests beyond what verifies the tranche.
- Doc rewrites unrelated to the tranche-2 invariants.
- Bumping the package version.

## Activity Log

- 2026-04-28T10:46:08Z – claude:opus-4-7:default:implementer – shell_pid=63926 – Started implementation via action command
- 2026-04-28T10:58:05Z – claude:opus-4-7:default:implementer – shell_pid=63926 – WP07 ready: golden-path E2E uses public CLI only, docs sync, tranche CHANGELOG, SC-001..SC-008 acceptance pass
- 2026-04-28T10:58:49Z – claude:opus-4-7:default:reviewer – shell_pid=72407 – Started review via action command
- 2026-04-28T11:01:31Z – claude:opus-4-7:default:reviewer – shell_pid=72407 – Review passed: golden-path E2E uses public CLI only (no doctrine seed, no metadata edit, no git add charter), passes in 26.66s well under 120s budget, docs sync adds clean auto-track note, CHANGELOG references all 7 issues with SC-001..SC-008 acceptance pass.
