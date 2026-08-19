---
work_package_id: WP10
title: doctor degod — retire C901
dependencies:
- WP09
requirement_refs:
- FR-001
- FR-003
- NFR-002
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- src/specify_cli/sync/sync_doctor_core.py
- tests/characterization/test_sync_doctor_render.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/sync/sync_doctor_core.py
- tests/characterization/test_sync_doctor_render.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile before anything else: `/ad-hoc-profile-load python-pedro`. Then run
`spec-kitty charter context --action implement --json` and apply the resolved
directives/tactics. State in your first status note which directives/tactics you applied
(expect `DIRECTIVE_001`/`043` gate discipline, the ATDD `acceptance-test-first` tactic — golden
freeze before restructure — and smallest-viable-diff / TDD red-green front-of-mind).

## Objective

`doctor()` (`src/specify_cli/cli/commands/sync.py:5991`, complexity **73**, the second
`# noqa: C901` site) is the second monster degod. Like `status`, it interleaves I/O with issue
accumulation — `_check_server_connection` at L6135, `scan_sync_daemons` at L6165, and the three
shared render helpers `_render_per_project_store` (L6200), `_render_consent_readability` (L6205),
`_render_tracker_egress` (L6210) each **print AND mutate `issues`** as they go. Per architect
finding **A-1** this is a *gather-I/O → pure core → render* **restructure**, not a relocate.
WP07 already split those three shared helpers into compute (pure) + render; this WP builds the
pure `build_doctor_report()` on top of their compute halves, leaves a thin render shell, and
retires the `# noqa: C901` (complexity ≤ 15).

Per WP-translation guard **#6**, freeze the `doctor` golden **inside this WP, before the
extraction** (T019), then restructure (T020).

**Watch the surface (pedro Pd-3)**: `sync doctor` takes **NO arguments and has NO `--json`** —
those `{available, total, valid, invalid, results}` JSON shapes belong to `diagnose`, not
`doctor`. Do not invent a `--json` arm; freeze what `doctor` actually emits.

## Read first (source of truth)

The mission `plan.md` — IC-04 (Pd-2: the three shared helpers' compute-half lands in
`sync_store_report_core` **before** both the status and doctor degods) and IC-05, plus the
"WP-translation guards" § (**#3** monster-per-WP, **#6** freeze-before-extract). The contract
(`contracts/sync-cli-characterization-contract.md`) item **3** — the corrected `doctor` surface:
Rich table + issues list, "No issues detected. Sync is healthy." (L6314) vs the unhealthy
summary, and the `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE` exit-4 recovery arm (L6329).
`data-model.md` INV-1/INV-5; `research/squad-findings-post-plan.md` A-1, Pd-2, Pd-3. **Zero
behavior change**: identical table, identical issue text, identical exit codes pre/post.

## Environment (CRITICAL — worktree vs editable install)

Work in the lane worktree. The repo-root `.venv` editable-install points at the MAIN checkout,
so test YOUR changes with `PYTHONPATH=<worktree>/src`. Define `VENV=<repo>/.venv/bin; WT=<worktree>`.

Tests (SaaS-enable ON to reach the non-skip render path, work/gate OFF for a hermetic golden):

```
SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 PYTHONPATH=$WT/src \
  $VENV/python -m pytest \
  tests/characterization/test_sync_doctor_render.py \
  tests/sync tests/cli/commands -k sync -q -p no:cacheprovider
```

Lint/type:

```
$VENV/ruff check $WT/src/specify_cli/cli/commands/sync.py $WT/src/specify_cli/sync/sync_doctor_core.py
$VENV/mypy --strict $WT/src/specify_cli/sync/sync_doctor_core.py
```

NEVER run the full suite or `uv run`. Real-port/daemon tests run in their own `-n0` pass. Set a
fast `review.test_command` to avoid the claim-time full-suite hang.

## Subtasks

### T019 — Freeze the `doctor` golden (before any extraction)

**Purpose**: pin `doctor`'s observable output — table, issues, healthy/unhealthy summary, and the
exit-4 recovery arm — so the A-1 reorder is provably behavior-stable.

**Steps**:

- Create `tests/characterization/test_sync_doctor_render.py` using the WP02 harness scaffolding.
- `sync doctor` takes NO args and has NO `--json`. Freeze:
  - the full Rich table render + the accumulated **issues list** order/text;
  - the **healthy** summary — the exact "No issues detected. Sync is healthy." line (L6314) —
    vs an **unhealthy** arm (≥1 issue) so both summary branches are frozen;
  - the `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE` **exit-4** recovery arm (raised at L6329).
- **Determinism**: stub the I/O seams via late-bound `sync_module.<name>` monkeypatch —
  `_check_server_connection` (L6135), `scan_sync_daemons` (L6165), and the per-project-store /
  consent / tracker-egress data seams — so the snapshot is stable and the stubs survive T020's
  relocation (INV-4).
- Confirm green on the **pre-restructure** `doctor`.

**Files**: `tests/characterization/test_sync_doctor_render.py` (new).

**Validation**: golden green against current `sync.py`; no DIR-041 ratchet mutation (C-003).

### T020 — Restructure `doctor()` into gather-I/O → core → render; retire the C901

**Purpose**: build the pure issue-accumulation core on WP07's compute halves and remove the
suppression.

**Steps**:

- Create `src/specify_cli/sync/sync_doctor_core.py` — **I/O-free** (no `Console`/`print`/network/fs).
- Extract `build_doctor_report(facts) -> DoctorReport` — pure issue-accumulation. The three
  shared helpers were split by WP07: `_render_per_project_store` (L6200), `_render_consent_readability`
  (L6205), `_render_tracker_egress` (L6210) now have compute-halves in `sync_store_report_core`.
  `build_doctor_report` **calls those compute halves** and folds their findings into a
  `DoctorReport` (the ordered issues + the healthy/unhealthy verdict). It does NOT print and does
  NOT re-implement them (`DIRECTIVE_044`, Pd-2 decoupling).
- In `doctor()` (the shell that STAYS under `@app.command` in `sync.py`): hoist all I/O to the
  top (`_check_server_connection` L6135, `scan_sync_daemons` L6165, the store/consent/tracker data
  reads), call `build_doctor_report`, then render — the render shell calls the render-halves of the
  three helpers and prints the summary line + exit-4 arm exactly as before.
- Reach monkeypatched callees via late-bound `sync_module.<name>` (INV-4 / C-005).
- **Delete the `# noqa: C901`** on `def doctor()`; the shell must measure ≤ 15.
- Add focused unit tests for `build_doctor_report` (pure) covering healthy, unhealthy, and each
  issue-source branch (Sonar new-code-coverage, same PR).

**Files**: `src/specify_cli/sync/sync_doctor_core.py` (new); `src/specify_cli/cli/commands/sync.py`
(`doctor` shell rewritten, `# noqa: C901` removed).

**Validation**: T019 golden green pre/post; the ~60 patch-tests green; `doctor` ≤ 15 with no
`# noqa: C901`; core has zero `Console`/`print`.

## Branch Strategy

Planning/base + merge target: `refactor/wave4-sync-degod`. The execution worktree is allocated per
the computed lane from `lanes.json` (`spec-kitty implement WP10` prepares it) — do not reconstruct
the path. This is **lane-c**, position 10 in the serial chain; it edits the single `sync.py` and
depends on WP09 (rebase on its shrunk file). Not a parallel lane.

## Definition of Done

- [ ] `tests/characterization/test_sync_doctor_render.py` freezes the Rich table + issues list,
      the healthy vs unhealthy summary, and the exit-4 recovery arm — no `--json` arm invented —
      green pre AND post-restructure.
- [ ] `sync_doctor_core.py` holds `build_doctor_report`, is I/O-free, and consumes WP07's
      store/consent/tracker compute halves (does not re-implement or print).
- [ ] `doctor()` is a thin gather-I/O → core → render shell staying under `@app.command`; all I/O
      hoisted to the top; late-bound `sync_module.<name>` seam preserved.
- [ ] The `# noqa: C901` on `doctor` is **removed**; complexity ≤ 15; `ruff`/`mypy --strict` clean,
      zero net-new suppressions.
- [ ] The ~60 sync patch-tests green; focused unit tests execute every new branch/helper (same PR).

## Reviewer Guidance

- **Pd-3 (surface)**: confirm the golden freezes `doctor`'s real surface — no `--json`, no args;
  the JSON shapes belong to `diagnose`. A `--json` freeze on `doctor` is a reject.
- **Guard #6**: T019 golden committed and green **before** the T020 restructure commit.
- **Pd-2 / DIRECTIVE_044**: `build_doctor_report` must call WP07's compute halves, not re-derive
  the store/consent/tracker findings — grep the core for `Console`/`print`; any hit is a reject.
- **A-1**: all I/O hoisted to the top of the shell; the core is pure.
- **INV-4 / INV-5**: seam preserved via late binding, ~60 patch-tests green; the `# noqa: C901`
  is gone and `doctor` truly measures ≤ 15.


## Post-tasks squad corrections (BINDING)
- **Rn-1:** the `doctor` render golden is **frozen in WP02** (`test_sync_cli_safe.py`), not here. T019 is now: **VERIFY** that golden is green before and after your restructure (do not re-freeze). Add `build_doctor_report()` unit tests in `test_sync_doctor_render.py`; the behavior-lock is the WP02 snapshot. (`doctor` has no `--json` — do not invent one.)
