---
work_package_id: WP08
title: Dispatch core + exec extraction
dependencies:
- WP07
requirement_refs:
- FR-002
- NFR-002
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T016
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- src/specify_cli/sync/sync_dispatch_core.py
- src/specify_cli/sync/sync_dispatch_exec.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/sync/sync_dispatch_core.py
- src/specify_cli/sync/sync_dispatch_exec.py
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
discipline, `DIRECTIVE_025` campsite, the ATDD-first tactic, ≤15 complexity ceiling).
If profile load fails, stop and report.

## Objective

Extract the **dispatch subsystem** out of `cli/commands/sync.py` into
`src/specify_cli/sync/sync_dispatch_core.py` (the **pure** batching + exit-code
decisions) and `src/specify_cli/sync/sync_dispatch_exec.py` (the SaaSQueue delivery
executors). **Retire `_enforce_sync_now_exit_from_dispatch`'s `# noqa: C901` (cc22)**
by moving its pure `DispatchSummary → exit-int` decision into the core. Freeze `now`'s
exit-code contract (already golden-covered). **Zero behavior change.**

Last adapter/core extraction in the serial chain before the monster degods
(WP07 → **WP08** → WP09 `status`).

## Read first (source of truth)

- **`plan.md` IC-03/IC-04** — pure decision cores (batching + exit-code map) vs
  executors (delivery); every new branch/helper gets a focused unit test **in this
  WP** (Sonar new-code coverage).
- **`plan.md` § "WP-translation guards"** — guard #1 (serial on `sync.py`), guard #2
  (`@app.command def now` stays in `sync.py`; privates late-bound), guard #8 (test env).
- **`contracts/sync-cli-characterization-contract.md`** — item 5 (`now`: `--strict`
  exits, preflight exit 2, unauthenticated exit 1,
  `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE`) is the **frozen exit-code contract** the
  core must reproduce exactly; rules 2/3 (behavior-stable + ~60-seam co-gate).
- **`data-model.md`** — INV-1 (behavior byte-stable), INV-3 (module under
  `specify_cli.sync.*`, no `runtime` import), INV-5 (retire the `# noqa: C901`, ≤15,
  ≤800 LOC/module).
- **Zero-behavior-change**: the golden protects every extraction. The `now` golden
  arm (exit codes) is the load-bearing net for the exit-code map extraction — it must
  stay green.

## Environment

- Lane worktree from `lanes.json` (`spec-kitty implement WP08`; call it `$WT`). Rebase
  on the WP07-shrunk `sync.py` first (serial chain).
- Repo `.venv` is editable-installed against the **MAIN checkout** — run with
  `PYTHONPATH=$WT/src` and `$VENV/python`. Never bare `python`/`spec-kitty` (pyenv →
  wrong fork), never `uv run`.
- **Targeted tests**:

  ```bash
  SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 \
    PYTHONPATH=$WT/src $VENV/python -m pytest \
    tests/characterization/test_sync_*.py \
    tests/cli/commands/test_sync_commands.py \
    tests/sync/ src/specify_cli/sync/ -q -p no:cacheprovider
  ```

  Add the new `tests/sync/test_sync_dispatch_core_*.py` you author. `-n0` for
  daemon/real-port files. Fast `review.test_command` to avoid the claim-time
  full-suite hang.
- Lint/type changed files only via `$VENV/bin/ruff` / `$VENV/bin/mypy`,
  `PYTHONPATH=$WT/src`.

## Subtasks

### T016 — Extract dispatch core (pure) + exec; retire `_enforce_sync_now_exit` cc22

Re-grep in `$WT` (WP07 shifted lines). Current anchors:

**→ `sync_dispatch_core.py` (PURE — no I/O, returns decisions/dataclasses)**
- `_combine_dispatch_summaries(left, right)` — **L850** (pure `DispatchSummary`
  reduction).
- `_batch_is_oversized(summary)` — **L870**.
- `_transient_block_message(summary)` — **L889** (pure message builder).
- **The `DispatchSummary → exit-int` mapper**: the decision core of
  `_enforce_sync_now_exit_from_dispatch` (**L297**, carries the `# noqa: C901` cc22).
  Extract the **pure exit-code decision** — given a `DispatchSummary | None` + the
  pending-work signal → the strict exit int — into `sync_dispatch_core.py`. The
  remaining thin wrapper in `sync.py` (or the `now` shell) applies the console print +
  `raise typer.Exit(code)`; the **decision** is pure and unit-tested. Deleting the
  `# noqa: C901` (INV-5) follows from moving the branchy mapping into a tested pure
  function.

**→ `sync_dispatch_exec.py` (SaaSQueue delivery executors — do I/O)**
- `_run_dispatch_batches(...)` — **L905**.
- `_run_event_sync_dispatch()` — **L1194**.
- `_resolve_active_receiver(target, config, *, auth_token=None)` — **L773**.
- The **exec half of `_resolve_gated_receiver`** — **L799** (WP07 extracted its
  admission-authority wrapper into `sync_authority.py`; this WP relocates the delivery/
  receiver-resolution execution path). Keep the authority-admission call reaching
  `sync_authority.py` late-bound; the exec half does the receiver plumbing.

**→ `sync.py` — `now` shell (stays put)**
- `now` command at **L3325**; it calls `_run_event_sync_dispatch()` (**L3396**) then
  `_enforce_sync_now_exit_from_dispatch(...)` (**L3404**). After extraction `now` is a
  thin shell: open ports → call exec (`_run_event_sync_dispatch`) → call core
  (exit-code decision) → print + `raise typer.Exit`. **Freeze its exit-code contract**
  — the golden `now` arm (contract item 5) must be byte-identical pre/post.

**Mechanics + tests**
1. Core must be **truly I/O-free** (no `Console`/`print`/network). The exit-code mapper
   returns an int; the print+raise stays in the shell/wrapper.
2. Late-bind moved symbols via the `sync_module` convention so
   `monkeypatch.setattr("...commands.sync._run_event_sync_dispatch", ...)`,
   `..._enforce_sync_now_exit_from_dispatch`, `..._resolve_active_receiver` still
   intercept (INV-4). Keep the AST early-bind guard green.
3. **Author focused unit tests** for the pure core in `tests/sync/` (new-code
   coverage): the exit-code mapper across every arm (delivered / nothing-pending /
   transient-block / preflight-fail / unauthenticated /
   `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE`), `_combine_dispatch_summaries` identity +
   reduction, `_batch_is_oversized` boundary, `_transient_block_message` text.
4. Writer census (A-5): 1:1 census-key swap for any relocated writer
   (`test_sync_writer_census.py`); no net key growth.
5. Each new module ≤ 800 LOC, every function ≤ 15 complexity.

## Branch Strategy

- **Base + merge target:** `refactor/wave4-sync-degod`. `branch_strategy: lane-per-wp`.
- Worktree from `lanes.json` for WP08. **Depends on WP07** — rebase on the WP07-shrunk
  `sync.py` first. Serial chain (every degod WP edits `sync.py`).
- Commit in units: core + its unit tests, then exec module, then the
  `_enforce_sync_now_exit` wrapper + C901 retirement + `now` shell.

## Definition of Done

- `sync_dispatch_core.py` (pure) and `sync_dispatch_exec.py` exist; `now` is a thin
  shell; `_enforce_sync_now_exit_from_dispatch`'s **`# noqa: C901` is deleted** and the
  exit-code decision lives in a tested pure function (≤15 complexity).
- The `now` exit-code golden arm (contract item 5) byte-identical pre/post; all golden
  snapshots + the ~60 `sync`-monkeypatch tests green (INV-1, INV-4).
- New focused unit tests for the pure core land in this WP and exercise every exit-code
  arm + the summary/batch helpers directly.
- Core is provably I/O-free (no `Console`/`print`/network import in
  `sync_dispatch_core.py`).
- `ruff` + `mypy --strict` clean on all three changed files; zero net-new
  `C901`/`S3776`.
- Any relocated writer is a **1:1 census-key swap**; `test_sync_writer_census.py` green.
- No `runtime`-package import (INV-3); AST early-bind guard green (INV-4).

## Reviewer Guidance

- Confirm `_enforce_sync_now_exit_from_dispatch` lost its `# noqa: C901` and the
  exit-code **decision** is a pure, separately-tested function returning an int — the
  print + `raise typer.Exit` must be the only thing left in the wrapper/shell.
- Read the new exit-code unit tests: every arm from contract item 5 must be exercised
  (preflight exit 2, unauthenticated exit 1, `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE`,
  strict-exit). A green bar with only the happy arm is insufficient.
- Verify `sync_dispatch_core.py` does no I/O (grep `Console`, `print(`, network,
  `dispatch(`).
- Diff moved executor bodies against pre-move — verbatim relocate; only the
  exit-code mapper and the `now` shell are legitimately restructured.
- Confirm the `now` golden bytes are unchanged and the census swap is 1:1.


## Post-tasks squad corrections (BINDING)
- **Rn-2:** relocate the receiver-resolution **residual** that WP07 left behind in `sync.py` (the plumbing/exec half of `_resolve_gated_receiver`) into `sync_dispatch_exec.py`; the admission-assert wrapper stays in `sync_authority.py` (WP07), reached late-bound via `sync_module.<name>`. **DoD:** no branch dropped; `now`/dispatch golden byte-green.
- **Rn-3:** if this extraction relocates a consent/grant writer, do the 1:1 census-key swap and keep `test_sync_writer_census.py` green — editing that file / the arch-gate baseline data is an authorized **small, individually-justified out-of-map edit** (record a one-line rationale); they are not in `owned_files` to avoid cross-mission overlap.
