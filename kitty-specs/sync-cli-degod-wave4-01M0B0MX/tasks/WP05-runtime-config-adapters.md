---
work_package_id: WP05
title: Runtime + config adapters
dependencies:
- WP04
requirement_refs:
- C-001
- C-002
- FR-002
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T012
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- src/specify_cli/sync/sync_runtime.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/sync/sync_runtime.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your operating profile and the action-scoped doctrine:

```bash
/ad-hoc-profile-load python-pedro
spec-kitty charter context --action implement --json
```

State in your opening message which profile loaded and which doctrine constraints
apply to this WP (expect at minimum: `DIRECTIVE_044` single canonical authority,
`DIRECTIVE_001`/`043` architectural + gate discipline, `DIRECTIVE_025` campsite,
the ATDD-first / acceptance-test-first tactic). If the profile load fails, stop and
report — do not improvise an ungoverned edit.

## Objective

Extract the **runtime-open / lifecycle adapters** and the **config-I/O adapters** out
of `cli/commands/sync.py` into a new `src/specify_cli/sync/sync_runtime.py`. This is a
**pure move behind the port seam** (IC-03): the runtime openers and config
readers/writers relocate verbatim; `sync.py` reaches them through the late-bound
`sync_module.<name>` convention established in WP03. **Zero behavior change.**

This is the second adapter extraction in the serial `sync.py` chain
(WP03 → WP04 → **WP05** → WP06 → …). It rebases on WP04's already-shrunk `sync.py`.

## Read first (source of truth)

- **`plan.md` § "WP-translation guards"** — especially guard #1 (adapters **serialize
  on `sync.py`**, never parallel lanes), guard #2 (`@app.command` shells stay in
  `sync.py`; privates reached via late-bound `sync_module.<name>`), and guard #8
  (test-env vars).
- **`plan.md` IC-03** — port/adapter seam; "one adapter per port"; the **1:1
  census-key swap** rule for each relocated writer (`test_sync_writer_census.py`).
- **`contracts/sync-cli-characterization-contract.md`** — the golden freezes the
  observable behavior of all 22 subcommands. Contract rule 2 (behavior-stable) and
  rule 3 (seam co-gate, ~60 monkeypatch tests) are your gate.
- **`data-model.md`** INV-1 (behavior byte-stable), INV-3 (new module under
  `specify_cli.sync.*`, zero `runtime`-package import), INV-4 (seam), INV-6 (no
  daemon-lifecycle behavior change; no env-var deletion).
- **Zero-behavior-change is the whole contract of this WP.** The golden protects
  every extraction: if a golden snapshot or a patch-test moves, you changed behavior
  and must revert, not re-baseline.

## Environment

- Work in **this WP's lane worktree**, resolved from `lanes.json` (do not reconstruct
  the path by hand — `spec-kitty implement WP05` prepares/reuses it). Call the
  resolved path `$WT`.
- The repo `.venv` is an **editable install pointing at the MAIN checkout**, not your
  worktree. So you MUST run everything with `PYTHONPATH=$WT/src` to exercise the code
  under `$WT`. Call the interpreter `$VENV/python` (the repo `.venv/bin`); never a
  bare `python`/`spec-kitty` (pyenv shim runs the wrong fork) and never `uv run`
  (it re-syncs and destroys the hand-built `.venv`).
- **Targeted test invocation** (never the full suite):

  ```bash
  SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 \
    PYTHONPATH=$WT/src $VENV/python -m pytest \
    tests/characterization/test_sync_*.py \
    tests/cli/commands/test_sync_commands.py \
    tests/sync/ -q -p no:cacheprovider
  ```

  `SPEC_KITTY_ENABLE_SAAS_SYNC=1` reaches the non-skip render arms;
  `SPEC_KITTY_SYNC_DISABLE=1` keeps the run hermetic (disables work/gate, orthogonal
  to render). Use `-n0` for any daemon/real-port file. **Do not run the full suite**
  (≈1h hang) and set a fast `review.test_command` to avoid the claim-time full-suite
  gate.
- Lint/type on changed files only:
  `PYTHONPATH=$WT/src $VENV/bin/ruff check src/specify_cli/sync/sync_runtime.py src/specify_cli/cli/commands/sync.py`
  and `$VENV/bin/mypy` on the same.

## Subtasks

### T012 — Extract `sync_runtime.py` (runtime-open/lifecycle + config I/O adapters)

Relocate the following symbols from `cli/commands/sync.py` into the new
`src/specify_cli/sync/sync_runtime.py`, preserving their bodies **verbatim**. Real
current line anchors (WP04 will have shifted them slightly — re-grep in `$WT` before
cutting):

**Runtime dataclasses + openers**
- `_EventSyncRuntime` dataclass — **L476**.
- `_ProjectDispatchRuntime` dataclass — **L492**.
- `_open_event_sync_runtime(*, include_target=True)` — **L522** (the **READ**-authority
  open path).
- `_open_event_sync_runtime_readonly()` — **L606**.
- `_open_project_dispatch_runtime(...)` — **L556** (the **DISPATCH**-authority open
  path).
- `_open_retention_runtime_or_exit()` — **L611**.
- `_open_active_body_queue(...)` — **L967**.
- `_ScopedStatusJournal` — **L1567**; `_open_journal_readonly()` — **L1581**.

  > **GUARD — the two runtime openers are the read-vs-dispatch authority split
  > (architect A-2 / plan IC-03).** `_open_event_sync_runtime` is the READ open;
  > `_open_project_dispatch_runtime` is the DISPATCH open bound to delivery. **Keep
  > them as two distinct functions** — do not "de-duplicate" them into one opener.
  > `_open_project_dispatch_runtime` irreducibly mixes read+write authority at the
  > flow level and is **frozen verbatim (C-007)** — relocate it byte-identical, do
  > NOT purify or refactor its authority calls.

  > **Cross-WP note:** `_open_project_dispatch_runtime` calls
  > `_assert_event_sync_runtime_authority` (L589) and
  > `_assert_delivery_target_matches_context` (L594), which still live in `sync.py`
  > at WP05 (they relocate later in **WP07** → `sync_authority.py`). Reach them the
  > same way `sync.py` reaches relocated privates — late-bound through the
  > `sync_module` convention (or a module-level indirection), **never** an
  > early-binding `from ...commands.sync import _assert_...` at import time, so the
  > ~60 monkeypatch seams keep intercepting (INV-4). Confirm the AST early-bind
  > guard from WP03 still passes.

**Config I/O adapters**
- `_event_sync_config_path()` — **L675**.
- `_read_event_sync_table()` — **L681**.
- `_load_event_sync_config()` — **L696**.
- `_write_event_sync_config(mode, external_endpoint)` — **L720** (called from the
  `mode` command around **L5030** — that call site stays in `sync.py` and must resolve
  the relocated writer through the seam).
- `_event_sync_access_token()` — **L745**.

**Mechanics**
1. Move each body unchanged into `sync_runtime.py`; carry the imports each function
   needs (types like `EventSyncConfig`, `Mode`, `Path`). New module imports must stay
   within `specify_cli.sync.*` / stdlib / existing deps — **zero `runtime`-package
   import** (INV-3), no new `status`/`dossier`→sync edge (C-001).
2. In `sync.py`, replace each moved definition with the WP03 re-export/late-bind
   accessor so `sync.<name>` still resolves and every existing
   `monkeypatch.setattr("...commands.sync.<name>", ...)` still lands (INV-4). Any
   in-`sync.py` caller of a moved symbol (e.g. the `mode` command's
   `_write_event_sync_config`, and every `_open_*` caller) must reach it late-bound,
   not via a stale local reference.
3. **Writer census (A-5):** if any relocated function is a consent/grant **writer**
   tracked by `test_sync_writer_census.py`, perform a **1:1 census-key swap** — drop
   the old `relpath::qualname::kind::effect::evidence` key and add the equivalent for
   the new module path. Never a net addition. `_write_event_sync_config` is the
   likely candidate; audit each moved symbol against the census fixture and swap
   per-writer.
4. Keep `sync_runtime.py` ≤ 800 LOC and every function ≤ 15 complexity (these are
   moves, so complexity should be unchanged — do not fold logic).

## Branch Strategy

- **Base + merge target:** `refactor/wave4-sync-degod` (the mission integration
  branch). `branch_strategy: lane-per-wp`.
- Work in the worktree resolved from `lanes.json` for WP05. This WP **depends on WP04**
  — rebase on the WP04-shrunk `sync.py` before extracting; the chain is serial because
  every degod WP edits the single `sync.py`.
- Commit in small, reviewable units (per the commit-often discipline): the module
  scaffold, then the runtime openers, then the config adapters, then the census swap.

## Definition of Done

- New `src/specify_cli/sync/sync_runtime.py` holds all listed runtime/config adapters,
  bodies verbatim; `sync.py` calls through the seam.
- **All golden characterization snapshots green pre/post** (contract rule 2); the ~60
  `sync`-monkeypatch tests green (contract rule 3 / INV-4) — run the targeted command
  above.
- The two runtime openers remain **distinct**; `_open_project_dispatch_runtime` and
  the config writer are byte-identical relocations (C-007).
- `ruff` and `mypy --strict` clean on both changed files; zero net-new `C901`/`S3776`
  suppressions; no new `# noqa`/`# type: ignore`.
- Each relocated grant/consent writer is a **1:1 census-key swap** —
  `test_sync_writer_census.py` green with no net key growth.
- WP03's AST early-bind guard still passes (no early-binding a monkeypatched name).
- No `runtime`-package import in the new module (INV-3); no daemon-lifecycle behavior
  change and no env-var deletion (INV-6).

## Reviewer Guidance

- Diff each moved function against its pre-move body — this WP is a **relocate, not a
  rewrite**. Any semantic delta (reordered authority calls, merged openers, changed
  default args) is a reject.
- Confirm `_open_event_sync_runtime` and `_open_project_dispatch_runtime` are still two
  functions and that the dispatch opener's authority asserts are reached late-bound
  (not early-imported) — grep the new module for `from ...commands.sync import`.
- Verify the census swap is 1:1 (one key dropped per key added), not a re-pin of the
  whole fixture.
- Spot-check that `monkeypatch.setattr` on any moved name (`_load_event_sync_config`,
  `_open_active_body_queue`, `_write_event_sync_config`, …) in the existing suites
  still intercepts — run those specific tests and read the assertions, don't infer
  from a green bar alone.
- Confirm no golden snapshot file changed bytes (a changed snapshot = changed behavior).


## Post-tasks squad corrections (BINDING)
- **Rn-3:** if this extraction relocates a consent/grant writer, perform the 1:1 census-key swap and keep `tests/architectural/test_sync_writer_census.py` green — editing that file is an authorized **small, individually-justified out-of-map edit** (one-line rationale). It is not in `owned_files` (shared arch-gate surface).
