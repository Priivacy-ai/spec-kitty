---
work_package_id: WP01
title: P0 birth-cutover seed ordering and verification
dependencies: []
requirement_refs:
- C-001
- C-002
- C-005
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-010
- NFR-001
- NFR-002
- NFR-004
planning_base_branch: fix/annoying-bugs-sweep
merge_target_branch: fix/annoying-bugs-sweep
branch_strategy: Planning artifacts for this mission were generated on fix/annoying-bugs-sweep. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/annoying-bugs-sweep unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-annoying-bugs-sweep-01KYHQ9F
base_commit: dc2ed9bbabcc3a78071ffc58d6add11170960ba5
created_at: '2026-07-27T13:50:57.790248+00:00'
subtasks:
- T027
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Release-critical P0
history:
- at: '2026-07-27T13:34:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/migration/
create_intent:
- tests/regression/baselines/issue_2985_red_first.md
execution_mode: code_change
model: gpt-5.6-sol
owned_files:
- src/specify_cli/migration/backfill_runtime_state.py
- tests/unit/migration/test_backfill_runtime_state.py
- tests/integration/test_migration_backfill.py
- tests/regression/test_birth_cutover.py
- tests/regression/baselines/issue_2985_red_first.md
role: implementer
tags: []
tracker_refs:
- '#2985'
---

# Work Package Prompt: WP01 - P0 birth-cutover seed ordering and verification

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile from frontmatter before reading further.
Resolve it with `spec-kitty agent profile show python-pedro`, then load
`spec-kitty charter context --action implement --json` and apply both outputs.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

## Objective

Fix #2985 at the shared migration owner so a historical birth-cutover seed can never supersede an
active WP's lane or runtime slots. Preserve genuine legacy runtime data, deterministic seed and
repair identities, idempotency, and all five writing callers.

## Context And Binding Decisions

- Read `spec.md` US1, `research.md` R1/R2, `data-model.md`, and
  `contracts/birth-cutover-ordering.md`.
- The global reducer is not the fix site. Do not change `_should_apply_event`.
- Do not suppress claim seeds for terminal WPs: that loses `shell_pid`,
  `shell_pid_created_at`, and `agent`.
- Transition and annotation histories are ordered separately. The seed floor must cover both.
- An already-persisted colliding seed cannot be repaired by re-appending its ID: the reducer keeps
  the first row. Use the contract's distinct deterministic append-only compatibility identity.
- Verification needs at least one witness derived directly from `read_legacy_runtime`, not only the
  seed builder.
- `cutover_mission` remains the single authority. Caller edits require a demonstrated caller defect.

## Branch Strategy

- **Planning base**: `fix/annoying-bugs-sweep`
- **Merge target**: `fix/annoying-bugs-sweep`
- `lanes.json` supplies the execution workspace and branch. Do not reconstruct either.

## Subtasks

### T027 - Open the WP: tracker, ownership, and campsite

Before code changes, assign #2985 to the current Human-in-Charge and add a tracker comment naming
this mission; record both links in the evidence file. Re-check the actual intended diff against all
five WPs and C-005, then scout the owned migration and regression surfaces for domain-matched Sonar,
complexity, and overlong-function debt. Perform any necessary behavior-preserving tidy-first change
with focused tests before the functional fix, or record a clean bounded finding. Stop and update the
ownership map before touching any undeclared file.

### T001 - Commit the red-first reproduction

Add a mixed fixture with at least three WPs, terminal and non-terminal lanes, real legacy claim
are appended. Record the exact node ID and base failure at `git merge-base HEAD upstream/main` in
the owned evidence file before implementing the fix.

The same fixture family must include a persisted pre-fix seed with its old payload and original
terminal/annotation history. Mark the exact #2985 node `pytest.mark.regression` and prove it is
collected by the blocking `regression-tests` CI command:
`python -m pytest tests/ -m regression --collect-only -q`.

The oracle is lane and per-slot delta, not event count. `--no-commit` and diagnose are
convergence-only paths; only accept commit mode exercises the stamp.

### T002 - Derive a per-WP history floor

Extract a deterministic helper that observes both transitions and annotations for one WP and
returns a seed ordering key strictly below every existing row under the reducer's raw
`(at, event_id)` comparison. Preserve the existing synthesized anchor when the WP has no event
history. Fail closed if a strict, valid floor cannot be represented.

Test transition-only, annotation-only, mixed, same-`at`, no-history, malformed timestamp,
minimum-representable timestamp, and repeated invocation cases. An invalid floor must fail before
any partial append or `status_phase` flip.

### T003 - Apply the floor to every seed

Use the resolved floor for the claim transition and all migration annotations for that WP. Preserve
the existing deterministic IDs for newly-created seeds. For a persisted pre-fix collision, append a
separately namespaced deterministic compatibility event only when the old seed currently corrupts
state; restore the value reduced with migration seeds excluded and preserve any later legitimate
writer. Verification must recognize the old seed plus repair witness. A second invocation is
byte-identical and appends nothing. Do not rewrite the stream, add a writer, or change reducer
precedence.

### T004 - Add independent claim-slot witnesses

Strengthen `verify_backfill` so each non-null legacy claim slot is explicitly equal in raw seed
evidence. Require equality in the reduced snapshot only when no later legitimate writer owns that
slot; otherwise prove that later value wins. Do not use `_has_snapshot_runtime` as the oracle.
Retain exact deterministic row checks for new seeds and the explicit compatibility witness for old
seeds.

Include an anti-disable test where terminal history and genuinely unseeded claim state coexist.

### T005 - Cover all writing callers

Show the shared fix holds through accept commit mode, merge, upgrade migration,
`migrate backfill-runtime-state` single mode, and corpus mode. Prefer shared-authority integration
coverage over changing caller code. Verify already-seeded corpora still flip or remain converged.

### T006 - Quality gates

Run:

```bash
PWHEADLESS=1 pytest tests/unit/migration/test_backfill_runtime_state.py -q
PWHEADLESS=1 pytest tests/integration/test_migration_backfill.py -q
PWHEADLESS=1 pytest tests/regression/test_birth_cutover.py -q
PWHEADLESS=1 python -m pytest tests/ -m regression --collect-only -q
ruff check src/specify_cli/migration/backfill_runtime_state.py tests/unit/migration/test_backfill_runtime_state.py tests/integration/test_migration_backfill.py tests/regression/test_birth_cutover.py
mypy src/specify_cli/migration/backfill_runtime_state.py
```

Classify any broad-run red against `upstream/main`; never green-wash known P0 failures.

## Definition Of Done

- The committed reproduction demonstrably reds on the merge base and greens on the WP.
- Its exact node is selected by the blocking `regression-tests` marker command.
- Every seeded row sorts before existing per-WP history.
- A persisted old colliding seed is healed append-only and a byte-identical rerun appends nothing.
- Canonical lanes and later runtime slots remain unchanged.
- Raw legacy claim slots survive; snapshot checks account explicitly for later legitimate writers.
- All five writer paths and idempotent rerun behavior are covered.
- No reducer change, seed suppression, new writer, or unrelated refactor.
- The actual changed-file set remains disjoint from every other WP.

## Reviewer Guidance

Reject if the test can pass with zero seeds, checks only `verify.ok`, checks only one runtime slot,
or ignores annotations. Compare the pre/post reduced WP maps and inspect the raw ordering keys.
