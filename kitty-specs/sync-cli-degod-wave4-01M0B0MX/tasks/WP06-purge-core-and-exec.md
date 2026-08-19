---
work_package_id: WP06
title: Purge core + exec extraction
dependencies:
- WP05
requirement_refs:
- FR-002
- NFR-002
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T013
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- src/specify_cli/sync/sync_purge_core.py
- src/specify_cli/sync/sync_purge_exec.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/sync/sync_purge_core.py
- src/specify_cli/sync/sync_purge_exec.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```bash
/ad-hoc-profile-load python-pedro
spec-kitty charter context --action implement --json
```

State which profile loaded and which doctrine constraints apply (expect
`DIRECTIVE_044` canonical authority, `DIRECTIVE_001`/`043` architectural + gate
discipline, `DIRECTIVE_025` campsite, the ATDD-first tactic, and the ≤15 complexity
ceiling). If profile load fails, stop and report — no ungoverned edits.

## Objective

Extract the **purge subsystem** out of `cli/commands/sync.py` into two new modules:
`src/specify_cli/sync/sync_purge_core.py` (the **pure** census differentials + verdict
logic) and `src/specify_cli/sync/sync_purge_exec.py` (the census **readers** and
**executors** that touch the journal/ledger/body-queue). Rewrite the `purge`
`@app.command` into a thin shell that stays in `sync.py`, **retiring its `# noqa: C901`
(cc26)**. **Zero behavior change.**

The purge subsystem (`sync.py` **L3490–L4358**, roughly) is the one genuinely
self-contained block in the chain — pedro-confirmed **disjoint**: it has its own
`_RawCensus` type (**L3537**) and its own openers, and shares no state with the other
commands. That makes core-vs-exec separation clean here. It still edits the single
`sync.py` (removing its body), so it remains part of the **serial chain**
(WP05 → **WP06** → WP07), not a parallel lane.

## Read first (source of truth)

- **`plan.md` § "WP-translation guards"** — guard #1 (serial on `sync.py`; the purge
  block is disjoint but still edits `sync.py`), guard #2 (`@app.command` shell stays;
  privates late-bound), guard #8 (test env).
- **`plan.md` IC-03/IC-04** — purge is the "one genuinely-isolatable extraction"; the
  core is pure (no `Console`/`print`), the exec holds the readers/executors; every new
  branch/helper gets a focused unit test **in this WP** (Sonar new-code coverage).
- **`contracts/sync-cli-characterization-contract.md`** — rules 2 (behavior-stable)
  and 3 (~60-seam co-gate). The purge command's observable CLI behavior is frozen by
  the golden harness.
- **`data-model.md`** INV-1 (behavior byte-stable), INV-3 (module under
  `specify_cli.sync.*`, no `runtime` import), INV-5 (retire the `# noqa: C901`, ≤15
  complexity, ≤800 LOC/module).
- **Zero-behavior-change**: the golden protects every extraction. `purge`'s golden and
  the existing purge suites (`tests/sync/test_project_store*`,
  `tests/cli/commands/test_sync_report_label_is_a_purge_selector_3030.py`,
  `test_sync_doctor_per_project_3030.py`, and any `test_sync_purge_*`) must stay green.

## Environment

- Work in **this WP's lane worktree** (resolved from `lanes.json` via
  `spec-kitty implement WP06`; call it `$WT`). Rebase on the WP05-shrunk `sync.py`
  first — the chain is serial.
- Repo `.venv` is an **editable install pointing at the MAIN checkout**, so run
  everything with `PYTHONPATH=$WT/src` and the repo interpreter `$VENV/python`. Never a
  bare `python`/`spec-kitty` (pyenv shim → wrong fork), never `uv run` (destroys the
  `.venv`).
- **Targeted tests** (never full suite):

  ```bash
  SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 \
    PYTHONPATH=$WT/src $VENV/python -m pytest \
    tests/characterization/test_sync_*.py \
    tests/cli/commands/test_sync_commands.py \
    tests/cli/commands/test_sync_report_label_is_a_purge_selector_3030.py \
    tests/sync/ src/specify_cli/sync/  -q -p no:cacheprovider
  ```

  Add the new `tests/sync/test_sync_purge_core_*.py` you author. Use `-n0` for any
  daemon/real-port file. Set a fast `review.test_command` to avoid the claim-time
  full-suite hang.
- Lint/type changed files only, via `$VENV/bin/ruff` / `$VENV/bin/mypy` with
  `PYTHONPATH=$WT/src`.

## Subtasks

### T013 — Extract purge core (pure) + exec (readers/executors); retire `purge` cc26

Re-grep line anchors in `$WT` (WP05 shifted them). Current anchors:

**→ `sync_purge_core.py` (PURE — no I/O, no `Console`, returns dataclasses)**
- `_purge_differential(before, after, scope)` — **L3748**.
- `_purge_ledger_differential(before, after)` — **L3761**.
- `_purge_left_behind(census)` — **L3736**.
- `_purge_unattributable_keys(census)` — **L3731**.
- `_purge_frames_scope(census, frames_result, *, all_events, selector_uuid)` — **L3998**.
- `_purge_faults(...)` — **L4216**.
- `_purge_outcomes(...)` — **L4059**.
- `_purge_validate_invocation(...)` — **L3886**.
- Carry the `_RawCensus` dataclass (**L3537**) and the `_PURGE_*` scope constants into
  the core (they are the pure data shape both modules share) — or a shared spot the
  core owns; the exec imports them from the core. Also relocate the pure helpers these
  depend on: `_purge_stored_spelling_conflicts` (**L3774**), `_purge_ledger_view`
  (**L3948**).

**→ `sync_purge_exec.py` (census readers + executors — touch journal/ledger/queue)**
- Census readers: `_purge_journal_census` (**L3610**), `_purge_ledger_census`
  (**L3646**), `_purge_body_census` (**L3682**), `_purge_frames_census` (**L3699**).
- Executors: `_purge_run_journal_ledger` (**L3964**), `_purge_run_body_queue`
  (**L4021**), `_purge_resolve_project` (**L3803**).

**→ `sync.py` — thin `purge` shell (stays put, retire C901)**
- The `purge` command is at **L4358–L4359**. It currently orchestrates:
  build `before` censuses → resolve project → run journal/ledger + body executors →
  build `after` censuses → `_purge_frames_scope` → `_purge_outcomes` → `_purge_faults`
  → render. Rewrite it as **parse → open ports → call exec (readers/executors) → call
  core (differentials/verdict) → render**, so the `@app.command def purge` body drops
  below **complexity 15** and the `# noqa: C901` is **deleted** (INV-5). Do not fold
  or drop any branch — every current arm keeps its behavior.

**Mechanics + tests**
1. Core module must be **truly I/O-free**: no `Console`, no `print`, no filesystem, no
   SQLite. If a "pure" function currently reaches I/O, that part belongs in exec — but
   per pedro's confirmation the differentials/verdict are already pure, so this should
   be a clean cut.
2. In `sync.py`, moved symbols are reached late-bound via the WP03 `sync_module`
   convention so `monkeypatch.setattr("...commands.sync._purge_*", ...)` still lands
   (INV-4). Keep the AST early-bind guard green.
3. **Author focused unit tests** for the pure core in `tests/sync/` (Sonar new-code
   coverage — every relocated differential/verdict branch exercised directly with
   stub `_RawCensus` inputs): empty census, unreadable census, disjoint scope,
   ledger-vs-journal differential, left-behind accounting, faults derivation. These
   are new tests **in this WP**.
4. Writer census (A-5): if any relocated purge function is a tracked writer, do a
   **1:1 census-key swap** (`test_sync_writer_census.py`); no net key growth.
5. Keep each new module ≤ 800 LOC, every function ≤ 15 complexity.

## Branch Strategy

- **Base + merge target:** `refactor/wave4-sync-degod`. `branch_strategy: lane-per-wp`.
- Worktree resolved from `lanes.json` for WP06. **Depends on WP05** — rebase on the
  WP05-shrunk `sync.py` first (serial chain: every degod WP edits `sync.py`).
- Commit in units: core module + its unit tests, then exec module, then the `purge`
  shell rewrite + C901 retirement.

## Definition of Done

- `sync_purge_core.py` (pure) and `sync_purge_exec.py` exist; `purge` is a thin shell
  in `sync.py` with its **`# noqa: C901` deleted** and complexity ≤ 15.
- The purge golden snapshot(s) + the existing purge suites green pre/post; the ~60
  `sync`-monkeypatch tests green (INV-4).
- New focused unit tests for the pure core land in this WP and pass; each relocated
  differential/verdict branch is exercised directly.
- `ruff` + `mypy --strict` clean on all three changed files; zero net-new
  `C901`/`S3776` suppressions.
- Core is provably I/O-free (no `Console`/`print`/SQLite import in
  `sync_purge_core.py`).
- Any relocated writer is a 1:1 census-key swap; `test_sync_writer_census.py` green.
- No `runtime`-package import (INV-3); AST early-bind guard green (INV-4).

## Reviewer Guidance

- Verify `sync_purge_core.py` imports nothing that does I/O — grep for `Console`,
  `print(`, `sqlite`, `open(`, filesystem calls; a leak there breaks the pure-core
  contract (IC-04).
- Confirm the `purge` command lost its `# noqa: C901` and actually measures ≤ 15 (run
  `ruff check --select C901`), not merely "tests pass".
- Check the new core unit tests hit the **branches**, not just one happy path —
  differential with empty/unreadable/disjoint inputs, ledger vs journal, faults.
- Diff moved bodies against pre-move: readers/executors relocate verbatim; only the
  `purge` shell is legitimately rewritten (and only into parse→exec→core→render).
- Confirm no golden snapshot bytes changed and the census swap is 1:1.


## Post-tasks squad corrections (BINDING)
- **Rn-3:** if this extraction relocates a consent/grant writer, perform the 1:1 census-key swap and keep `tests/architectural/test_sync_writer_census.py` green — editing that file is an authorized **small, individually-justified out-of-map edit** (one-line rationale). It is not in `owned_files` (shared arch-gate surface).
