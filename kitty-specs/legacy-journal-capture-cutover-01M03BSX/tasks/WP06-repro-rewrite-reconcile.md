---
work_package_id: WP06
title: 'Rewrite #3425 reproductions + coordinated LEGACY-flip reconcile'
dependencies:
- WP01
- WP03
requirement_refs:
- FR-008
- FR-009
planning_base_branch: fix/legacy-journal-capture-cutover
merge_target_branch: fix/legacy-journal-capture-cutover
branch_strategy: Planning artifacts for this mission were generated on fix/legacy-journal-capture-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/legacy-journal-capture-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
history:
- at: '2026-08-15T00:00:00Z'
  actor: claude
  note: WP authored by tasks phase
agent_profile: implementer-ivan
authoritative_surface: tests/
create_intent: []
execution_mode: code_change
owned_files:
- tests/regression/test_issue_3425_setup_plan_legacy_layout_silent_capture.py
- tests/sync/test_layout_generation.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before doing anything else, load your governance profile:

```
/ad-hoc-profile-load implementer-ivan
```

This binds your identity, boundaries, and the doctrine context (red-first / ATDD,
canonical-sources, ownership boundaries, campsite discipline) that governs every step
below. Do not begin reading or editing until the profile is loaded.

## Objective

Turn the **mis-built #3425 reproductions** green against the **real ProjectSyncStore
contract** while *keeping* their behavioral pins — end-to-end journal conservation and
capture-failure-warning absence — and reconcile the existing **LEGACY-default** test pins
that WP03's default-flip reddens, so a green `regression tests (blocking)` gate cannot mask
an **NFR-003 / NFR-004** regression hiding in the non-blocking `tests/sync` / `tests/event_journal`
suites.

This is Implementation Concern **IC-06** in [`plan.md`](../plan.md). It satisfies **FR-008**
(reproductions assert the current contract and pass) and **FR-009** (preserve the
ProjectSyncStore-owned queue selection — the rewrite asserts that contract, it does **not**
revert the code to the retired API). It underwrites **NFR-003** (already-migrated roots see
0 behavior change; the pre-existing suites stay green), **NFR-004** (blocking CI green
on-branch with 0 new reds attributable to the diff), and **SC-003** (the three #3425
reproductions pass and `regression tests (blocking)` is green on-branch).

**Do NOT hollow the tests into permit-enum assertions.** The rewrite corrects *attribution*
and *drops a retired API call*; it must keep driving the real `setup_plan` entry point end
to end and keep asserting the observable outcome (events land in the journal, the legacy
store is untouched, no swallowed capture-failure warning). A test that only asserts
`permit.destination is LayoutDestination.PROJECT_STORE` and stops there is a hollowed
behavioral pin and an automatic reviewer rejection.

## Context

- **Test A mis-attributes the failure to a RETIRED API.** The current
  `test_authenticated_setup_plan_lands_in_scoped`
  ([`tests/regression/test_issue_3425_setup_plan_legacy_layout_silent_capture.py:288`](../../../tests/regression/test_issue_3425_setup_plan_legacy_layout_silent_capture.py))
  asserts `default_queue_db_path() == expected_scoped_path` and later instantiates a
  **no-arg** `OfflineBodyUploadQueue()` (line 372) then asserts `.db_path == expected_scoped_path`.
  That `default_queue_db_path()` (`src/specify_cli/sync/queue.py:195-196`) now raises
  `LegacyQueueMigrationRequiredError` **unconditionally** — it is not layout-gated, so the
  test's docstring root-cause narrative (that `LayoutMode.LEGACY` makes it "fail closed") is
  wrong. The no-arg `.db_path` resolution is a **retired** queue API under the
  ProjectSyncStore-owned selection (FR-009 / C-003).
- **The ACTUAL swallowed error on the reproduced path is the journal guard, not the queue.**
  The live #3425 shape — the warning `mission create` emitted five times — is
  `ProjectLayoutRequiredError("live payload writes require the project_only layout; legacy
  state is migration input only")` raised by `_require_project_destination`
  (`src/specify_cli/event_journal/journal.py:117-119`, class defined at `journal.py:42`).
  Correct attribution points at `journal.py:119`, not `queue.py:195`.
- **The LEGACY-default pins sit OUTSIDE the regression-blocking selection.** ~15 files under
  `tests/sync` / `tests/event_journal` reference `LEGACY`; roughly a half-dozen assert the
  greenfield LEGACY default as a **hard** pin (enumerated in T029). WP03 flips that default to
  `project_only` for no-legacy-data roots, so those hard pins go RED — but they are **not** in
  the `regression tests (blocking)` selection, so a green blocking gate would mask them.
  Reconciling them here is the NFR-004 guarantee.
- **Auth-adjacent tests pin `HOME` but the runtime root honors `SPEC_KITTY_HOME` first.**
  Test A sets only `HOME` (line 254); `_scope_home_classmethod` (line 147) pins
  `Path.home` + `HOME` / `USERPROFILE` / `LOCALAPPDATA` but **not** `SPEC_KITTY_HOME`. Yet
  `get_runtime_root()` (`src/specify_cli/paths/windows_paths.py:60`) and `runtime/home.py:39`
  both resolve `SPEC_KITTY_HOME` **before** any HOME-derived path ("always wins regardless of
  platform", `runtime/home.py:36`). On this dev box — itself a live machine-global legacy root
  — an ambient or leaked `SPEC_KITTY_HOME` therefore escapes the temp-root isolation. The sibling
  `tests/sync/test_layout_generation.py:31` already pins `SPEC_KITTY_HOME`; the #3425 file must too.

## Subtasks

### T027 — Rewrite Test A to the real contract, KEEP the behavioral pins

- **File**: `tests/regression/test_issue_3425_setup_plan_legacy_layout_silent_capture.py`
  (owned).
- **Correct the attribution.** Rewrite the module docstring and Test A so the root cause is
  the journal guard `ProjectLayoutRequiredError` (`journal.py:119`), not the unconditional
  `default_queue_db_path()` (`queue.py:195-196`). Remove the wrong "LayoutMode.LEGACY makes
  `default_queue_db_path()` fail closed" narrative.
- **Drop the retired no-arg queue API.** Delete the assertions that call `default_queue_db_path()`
  with no arguments (lines 288-289) and the no-arg `OfflineBodyUploadQueue()` `.db_path`
  equality (lines 372-373). Under the ProjectSyncStore-owned selection (FR-009) the live
  write path is resolved through the store, not a module-level default-path helper — assert
  the store-owned contract instead.
- **KEEP the end-to-end behavioral assertions.** Continue driving the **real** `setup_plan`
  entry point (`specify_cli.cli.commands.agent.mission.setup_plan`) end to end, then assert:
  (a) **journal conservation** — the emitted event lands in the project journal exactly once;
  (b) the **legacy store is untouched** — the existing `legacy_body_rows == 0` /
  `legacy_event_rows == 0` pins (lines 397-404) stay; (c) **warning-absence** — assert
  `capsys` shows **no** capture-failure warning (no "live payload writes require the
  project_only layout" / "event journal capture failed" / "Explicit-context event capture
  failed" on stderr). This warning-absence pin is the load-bearing #3425 assertion — it is
  what proves the silent-success shape is gone.
- **Do NOT hollow.** The test must still exercise capture through the command boundary. A
  rewrite that deletes the enqueue/count/warning assertions and substitutes only a
  permit-enum check fails the Objective and must be rejected.
- **Validation**: run only this test post-WP03; it must be GREEN, and removing the WP03 fix
  (mentally / on the base) must make the warning-absence assertion RED — i.e. the pin still
  detects the P0.
- **Edge cases**: some environments skip the dossier helper (SaaS sync disabled / no project
  UUID) — the existing test already guards the `created_queues` loop for that (lines 362-366);
  preserve a path that still exercises a real capture through the command boundary rather than
  asserting on an empty list. The `expected_scope` / `scope_db_path` derivation (lines 274-279)
  is fine to keep for computing *where* the journal should land — the change is that you assert
  the row landed there via the store contract, not that a retired no-arg helper returns that
  path.

### T028 — Green all three #3425 reproductions end-to-end

- **File**: same owned regression file (Test A plus the two WP04 preflight tests).
- **`test_setup_plan_refuses_on_daemon_owner_mismatch`** (line 426): with credential parsing
  restored (WP01 / IC-01) the FR-011 auth gate no longer short-circuits, so the **boundary
  preflight** daemon-owner-mismatch refusal is the one that fires. Keep the `exit_code == 2`
  and `"Refusing" in combined` assertions (lines 489-498) and the post-refusal "no queue
  rows" pins (lines 501-504) — they now pass because the intended gate, not the auth
  cascade, is exercised.
- **`test_setup_plan_authenticated_coherent_succeeds`** (line 506): a coherent authenticated
  host must get **past** the preflight — keep the `code != 2` assertion (line 555). Post-WP01
  the auth gate confirms authentication instead of refusing.
- **All three end to end** — do not stub the capture path out of existence. The tests drive
  `setup_plan` for real (the `_patches_for_setup_plan` seam only stubs git / project-root
  discovery, lines 206-235); keep that seam, keep the real queue-write / journal path live.
- **Do NOT weaken the daemon-owner-mismatch semantics.** The `exit 2` there is the boundary
  preflight refusal, a *different* gate from the FR-011 auth refusal the old test tripped
  first. Keep the `"Refusing"` banner assertion so a regression that reintroduces the auth
  short-circuit (masking the boundary diagnostic) is still caught — do not relax it to a bare
  `exit_code == 2` that either gate could satisfy.
- **Edge cases**: the coherent-host test tolerates a non-2 downstream exit (no real plan
  template in `tmp_path`, lines 546-558) — keep that tolerance; the assertion is specifically
  `code != 2`, i.e. "did not refuse at preflight", not "exit 0". Do not tighten it to `exit 0`
  and reintroduce flakiness on the absent-template path.
- **Validation**: `pytest tests/regression/test_issue_3425_setup_plan_legacy_layout_silent_capture.py -q`
  → 3 passed, on-branch, with the WP01 + WP03 fixes present. Confirm each of the three passes
  for the *intended* reason (capture lands / boundary preflight refuses / preflight not
  refused), not because a gate was stubbed away.

### T029 — ENUMERATE + reconcile the coordinated LEGACY-flip set (checklist)

- **The default flip (WP03) reddens every test that HARD-asserts the greenfield LEGACY
  default.** Update each so it asserts the post-flip contract (fresh/no-legacy-data root →
  `project_only`; only a root actually seeded with legacy data → `LEGACY`). Reconcile — do
  **not** delete a pin to make it pass. Work this explicit checklist:

  - [ ] `tests/sync/test_layout_generation.py:59` — `assert state.mode is LayoutMode.LEGACY`
        (peek on an **absent** authority = greenfield). Post-flip a no-legacy-data root
        resolves `project_only`; re-pin to the new default, or seed legacy data first if the
        test's intent is the legacy branch. **(owned file)**
  - [ ] `tests/sync/test_layout_generation.py:92` — `assert legacy.destination is
        LayoutDestination.LEGACY` (`issue_write_permit()` on a fresh store). **(owned file)**
  - [ ] `tests/sync/test_layout_generation.py:243` — `assert inserts[0].destination is
        LayoutDestination.LEGACY` (mid-cutover writer barrier). Verify whether the permit is
        issued before any legacy seed; if the barrier test still means to exercise the LEGACY
        insert, seed legacy data so the destination stays LEGACY intentionally. **(owned file)**
  - [ ] `tests/sync/test_migration_writer_barrier.py:215` — `assert permit.destination is
        LayoutDestination.LEGACY`.
  - [ ] `tests/sync/test_legacy_queue_guard_3030.py:50` — `assert
        store.layout_generation().peek_state().mode is LayoutMode.LEGACY`.
  - [ ] `tests/event_journal/test_project_store_journal.py:112` — `assert
        observed_destinations == [LayoutDestination.LEGACY]`.

- **Also audit the conditional `if ... is LayoutMode.LEGACY:` guards** — they branch rather
  than hard-assert, so most will not redden, but each must be re-read to confirm the branch it
  guards (seed / skip) is still correct post-flip; adjust the seed if the guard silently
  becomes dead:

  - [ ] `tests/sync/test_final_sync_diagnostics.py:52`
  - [ ] `tests/sync/test_project_store_cross_platform.py:248` and `:267`
  - [ ] `tests/sync/test_body_integration.py:55`
  - [ ] `tests/sync/test_spec_kitty_home_paths.py:145`
  - [ ] `tests/sync/test_issue_598_hang_fixes.py:82`
  - [ ] `tests/sync/tracker/test_origin_integration.py:714`
  - [ ] `tests/sync/tracker/test_tracker_egress_refusal_3108.py:1718`

- **Regenerate the checklist from source, do not trust this snapshot alone.** Re-run the grep
  on the WP03-merged branch to catch any file the flip newly reddens:

  ```
  grep -rn "is LayoutMode.LEGACY\|LayoutDestination.LEGACY\|== LayoutMode.LEGACY" tests/sync/ tests/event_journal/
  ```

- **Validation**: every enumerated file GREEN on-branch after reconcile; no LEGACY-default
  hard pin left red, no pin deleted to dodge the flip.

### T030 — Pin auth-adjacent tests on `SPEC_KITTY_HOME` + verify both gates green

- **File**: `tests/regression/test_issue_3425_setup_plan_legacy_layout_silent_capture.py`
  (owned) — plus any coordinated-set file from T029 that resolves a runtime root.
- **Set `SPEC_KITTY_HOME`, not just `HOME`.** In Test A (line 254) and in
  `_scope_home_classmethod` (line 147) add `monkeypatch.setenv("SPEC_KITTY_HOME", str(<temp
  root>))` so the runtime root resolves inside the temp tree. Rationale: `get_runtime_root()`
  (`src/specify_cli/paths/windows_paths.py:60`) and `runtime/home.py:39` resolve
  `SPEC_KITTY_HOME` **before** any HOME-derived path ("always wins", `runtime/home.py:36`) —
  pinning only `HOME` leaves an ambient/leaked `SPEC_KITTY_HOME` able to escape isolation onto
  this box's live legacy root. Mirror the sibling `tests/sync/test_layout_generation.py:31`.
- **Verify BOTH gates green on-branch**: (a) the `regression tests (blocking)` selection —
  the three reproductions plus whatever else that job selects — is GREEN with 0 new reds
  attributable to this diff (NFR-004 / SC-003); and (b) the reconciled
  `tests/sync` / `tests/event_journal` set from T029 is GREEN. The second gate is the point of
  this WP: a green blocking gate alone must not certify the change.
- **Validation**:

  ```
  PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 .venv/bin/python -m pytest \
    tests/regression/test_issue_3425_setup_plan_legacy_layout_silent_capture.py \
    tests/sync/test_layout_generation.py tests/sync/test_migration_writer_barrier.py \
    tests/sync/test_legacy_queue_guard_3030.py tests/event_journal/test_project_store_journal.py -q
  ```

## Branch Strategy

- **Base branch**: `fix/legacy-journal-capture-cutover`.
- **Merge target**: `fix/legacy-journal-capture-cutover` (mission integration branch; this is
  **NOT** `main`).
- **Lane worktree**: per-lane worktree materialized from `lanes.json` — do not hand-build or
  reconstruct the `.worktrees/...` path.
- **Dependencies gate first**: `WP01` (credential parsing / IC-01, un-reds the auth gate) and
  `WP03` (layout resolution + default flip / IC-02, reddens the LEGACY pins) must be
  `approved` or `done` before this WP is claimed — this WP reconciles against *their* landed
  behavior. If either is not yet satisfied the reconcile targets a moving contract.
- **Prepare the workspace only via the resolver**:

  ```
  spec-kitty agent action implement WP06 --agent <name>
  ```

  Consume the resolved workspace path; never `cd` into a reconstructed worktree directory.

## Test Strategy

- **This WP IS tests.** There is no `create_intent`; every deliverable is an edit to an
  existing test file that turns red-or-mis-built into green-and-behavioral.
- **Run targeted, never the full suite** (the full suite hangs the session). Always with the
  sync gate disabled so the pre-review full-suite hang does not fire:

  ```
  PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 .venv/bin/python -m pytest <paths> -q
  ```

  Use `.venv/bin/python -m pytest` — never a bare `uv run`, which re-syncs and destroys the
  hand-built `.venv`.
- **Temp roots ONLY — never the real `~/.spec-kitty`.** This dev box is itself a live
  machine-global legacy root; a layout/cutover test run against it mutates real data. Every
  test resolves its root from an isolated temp tree via `tmp_path` + `SPEC_KITTY_HOME` /
  `HOME` (plan Risk MINOR-8 / research Decision 10). T030 exists precisely to close the
  `SPEC_KITTY_HOME` leak.
- **The coordinated set is broad and only two files are `owned_files`.** A small, targeted
  edit to an additional reddened test file discovered by the T029 grep (outside the two owned
  files) is **acceptable** when it carries a one-line rationale in the diff/PR noting it is a
  coordinated LEGACY-flip reconcile. The real guard is **no overlap** with another WP's
  `owned_files` — keep edits confined to test files the default-flip reddens, and never touch
  a `src/` file (that is WP01 / WP03 territory).

## Definition of Done

- The three #3425 reproductions
  (`tests/regression/test_issue_3425_setup_plan_legacy_layout_silent_capture.py`) are GREEN
  end-to-end on-branch **and still behavioral**: journal conservation, legacy-store-untouched,
  and capture-failure-**warning-absence** all asserted; attribution corrected to
  `journal.py:119 ProjectLayoutRequiredError`; the retired no-arg `default_queue_db_path()` /
  `OfflineBodyUploadQueue().db_path` assertions removed (FR-008, FR-009, SC-003).
- The coordinated LEGACY-flip set is **enumerated** (T029 checklist, regenerated from the
  source grep) and **GREEN** — every hard LEGACY-default pin reconciled to the post-flip
  contract, no pin deleted to dodge the flip, conditional guards audited (NFR-003, NFR-004).
- `regression tests (blocking)` is GREEN on-branch with 0 new reds attributable to the diff
  (NFR-004), **and** the reconciled `tests/sync` / `tests/event_journal` set is GREEN — both
  verified, not just the blocking gate.
- Auth-adjacent tests pin `SPEC_KITTY_HOME` (not only `HOME`); isolation holds on this live
  legacy box.
- `ruff check .` clean on the touched files — zero new issues, zero suppressions.
- No file outside `owned_files` is modified **except** coordinated LEGACY-flip test-file
  reconciles, each carrying a one-line rationale; **no `src/` file touched**; no overlap with
  another WP's `owned_files`.

## Risks & Reviewer Guidance

- **Hollowing the behavioral pin is the primary risk.** The easy wrong move is to "fix" Test
  A by deleting the enqueue / row-count / warning assertions and replacing them with a bare
  `permit.destination is LayoutDestination.PROJECT_STORE`. **Reviewer: confirm the rewritten
  reproductions still (a) count the journaled event, (b) assert the legacy store stays at 0
  rows, and (c) assert the absence of a capture-failure warning via `capsys`.** If any of the
  three is gone, the #3425 pin no longer detects the P0 — reject.
- **A green blocking gate can MASK a reddened non-blocking file.** The whole reason IC-06
  enumerates the coordinated set is that `regression tests (blocking)` does not select the
  `tests/sync` / `tests/event_journal` LEGACY pins. **Reviewer: re-run the T029 grep on the
  branch and confirm no LEGACY-default hard assert is left red** — a missed file passes the
  blocking gate and ships an NFR-003/004 regression silently.
- **Reconcile, do not delete.** A LEGACY pin turned green by removing the assertion (rather
  than re-pinning it to the post-flip contract, or seeding legacy data where the LEGACY branch
  is the genuine intent) is a coverage regression dressed as a fix.
- **Attribution must name the journal guard.** If the rewritten docstring or assertion still
  blames `default_queue_db_path()` / `queue.py:195` for the silent capture, the correction did
  not land — the reproduced swallow is `journal.py:119 ProjectLayoutRequiredError`.
- **Isolation on a live legacy box.** Confirm no test resolves the runtime root without
  `SPEC_KITTY_HOME` pinned to a temp tree; a leaked `SPEC_KITTY_HOME` is a data-safety defect
  here, not a flake.
- **Dependency ordering.** This WP reconciles against WP01's restored auth gate and WP03's
  flipped default. If claimed before both are `approved`/`done`, the target contract is still
  moving and the reconcile will churn.
