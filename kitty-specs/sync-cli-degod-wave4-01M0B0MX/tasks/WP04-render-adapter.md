---
work_package_id: WP04
title: Render adapter extraction
dependencies:
- WP03
requirement_refs:
- C-001
- C-002
- FR-002
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T011
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- src/specify_cli/sync/sync_render.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/sync/sync_render.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile before anything else: `/ad-hoc-profile-load python-pedro`. Then run
`spec-kitty charter context --action implement --json` and apply the resolved
directives/tactics. State which you applied — the smallest-viable-diff tactic and the
canonical-authority directive (`DIRECTIVE_044`, one adapter per port) bind this extraction.

## Objective

Extract the sync render layer — all `rich.Console` emit helpers and `--json`-envelope
builders — out of `cli/commands/sync.py` into a new `src/specify_cli/sync/sync_render.py`
module behind the `Render` port, and have `sync.py` call through it. This is a **pure move**:
byte-for-byte behavior-preserving; the WP02 golden + the ~60 patch-tests are the guard.

This is the first adapter link after the chain head (WP03). It **serializes on `sync.py`** —
it removes bodies from the single `sync.py` and adds call-throughs, so it rebases on WP03's
shrunk file and is NOT a parallel lane (WP-translation guard #1). One adapter per port
(`DIRECTIVE_044`): the render family goes behind the one `Render` port reused from
`agent_tasks_ports.py`.

**Scope boundary**: move only the render *mechanics*. The `_render_per_project_store` helper
has a COMPUTE half that also mutates an `issues` list — that compute half moves later in WP07
(`sync_store_report_core`, splitting compute from render). Here you move only its render-half
mechanics along with the rest of the render family. Do not pull the status/doctor decision
logic into `sync_render.py`.

## Read first (source of truth)

The mission plan.md (IC-03 Port/adapter seam; the "WP-translation guards" §, esp. #1 serialize
+ #4 IC-03→~5 sequential WPs; the Structure Decision on late-bound seams), the contract (rules
2 & 3), `data-model.md` (the `Render` port entity, INV-1/INV-3/INV-4/INV-5),
`research/squad-findings-post-plan.md` (Pr-1 serial, Pd-2 the shared render+`issues` helpers
belong to WP07's compute split). Reference `agent_tasks_ports.py::Render`/`RealRender` — the
port + adapter shape you reuse. This is a Wave-4 degod: **zero behavior change**.

## Environment (CRITICAL — worktree vs editable install)

Work in the lane worktree. The repo-root `.venv` editable-install points at the MAIN checkout,
so test YOUR changes with `PYTHONPATH=<worktree>/src`. Define `VENV=<repo>/.venv/bin;
WT=<worktree>`.

```
SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 PYTHONPATH=$WT/src \
  $VENV/python -m pytest tests/characterization/test_sync_cli_safe.py \
    tests/cli/commands/test_sync_*.py tests/sync/ \
    -q -p no:cacheprovider
```

(SAAS-enable var is `SPEC_KITTY_ENABLE_SAAS_SYNC`, **NOT** `SPEC_KITTY_SAAS_SYNC`.) Lint/type:
`$VENV/ruff check <files>`, `$VENV/mypy --strict <files>`. Real-port/daemon suites `-n0`. Set a
fast `review.test_command` to avoid the claim-time full-suite hang. NEVER run the full suite or
`uv run`.

## Subtasks

### T011 — Extract `sync_render.py` behind the Render port

**Purpose**: consolidate the Console-emit + `--json`-envelope family into one adapter module,
leaving `sync.py` to call through the `Render` port; retire the render mechanics from the host.

**Steps**:

1. Create `src/specify_cli/sync/sync_render.py`. Move the group-B render family (verify exact
   lines with `grep -n` in your worktree — the file is large and lines drift):
   - `_build_queue_summary_lines` (~L180), `_render_drain_blockers` (~L199),
     `_render_retry_distribution` (~L224), `_render_top_event_types` (~L246),
     `format_queue_health` (~L433) — the queue-health render cluster.
   - the `_print_*_result` family: `_print_retention_result` (~L1136),
     `_print_migration_result` (~L1147), `_print_cleanup_result` (~L1167),
     `_print_resolution_result` (~L1182), `_print_identity_backfill_result` (~L2076).
   - `_render_event_sync_status` (~L1277).
   - the JSON-envelope emitters: `_emit_status_check_json` (~L5209),
     `_emit_project_store_migration_json` (~L4660).
   - the **render-half** of `_render_per_project_store` (~L1609) — move the print mechanics
     only; leave a clean seam where WP07 will inject the pure compute result (the `issues`
     mutation / compute half stays for WP07). If a clean split is not yet possible without
     WP07's core, move the whole helper as render for now and add a `# WP07: split compute`
     marker — do NOT invent the compute core here.
2. Route these behind the reused `Render` port (`human` / `json_envelope`) from
   `agent_tasks_ports.py`. Where a helper prints directly to a module-level `Console`, keep the
   emit semantics identical (same markup, same glyphs, same `json.dumps` separators — the
   `RealRender` default-separator parity obligation).
3. In `sync.py`, replace each moved body with a call-through. Reach any monkeypatched callee
   via the **late-bound `sync_module.<name>`** convention (WP03) — never `from .sync_render
   import <name>` early-binding for a name that a test patches on `commands.sync`.
4. **Writer-census 1:1 key swap**: if any moved helper is a consent/grant *writer* tracked by
   `test_sync_writer_census.py` (key = `relpath::qualname::…`), drop the old key and add the
   equivalent new key — never a net addition (A-5). Render helpers are usually not writers, but
   check.
5. Add the new render module + any relocated seam to the husk re-export block (WP03) so
   `sync.<name>` still resolves for the ~60 patch-tests.
6. Keep `sync_render.py` ≤ 800 LOC, each function ≤ 15 complexity (INV-5).

**Files**: `src/specify_cli/sync/sync_render.py` (new), `src/specify_cli/cli/commands/sync.py`
(bodies → call-throughs + re-export).

**Validation**: golden + the ~60 patch-tests green; `ruff` + `mypy --strict` clean; the AST
early-bind guard (`test_sync_no_early_bind.py`) green.

## Branch Strategy

Planning/base + merge target: `refactor/wave4-sync-degod`. The execution worktree is allocated
per the computed lane from `lanes.json` (`spec-kitty implement WP04` prepares it) — do not
reconstruct the path. **Serial chain**: rebases on WP03; WP05 rebases on this. Not a parallel
lane (shares `sync.py`).

## Definition of Done

- [ ] `sync_render.py` holds the Console-emit + `--json`-envelope family behind the `Render`
      port; `sync.py` calls through.
- [ ] Only render mechanics moved — the `_render_per_project_store` COMPUTE/`issues` half is
      left for WP07 (marker in place if not cleanly splittable yet).
- [ ] Late-bound `sync_module.<name>` used for any patched callee; husk re-export updated so
      `sync.<name>` resolves.
- [ ] Any moved writer got a **1:1** census-key swap (no net key addition).
- [ ] WP02 golden + the ~60 patch-tests green; AST early-bind guard green.
- [ ] `ruff` + `mypy --strict` clean; `sync_render.py` ≤ 800 LOC, functions ≤ 15 complexity;
      one adapter per port (no forked Render abstraction).

## Reviewer Guidance

Verify the WP-translation guards / invariants that bind this WP:

- **Pure move (INV-1)**: diff the moved bodies — behavior (markup, glyphs, `json.dumps`
  separators, exit paths) must be byte-identical. Reject any "while I'm here" logic tweak.
- **Guard #1 (serial)**: confirm this rebased on WP03's `sync.py` and did not fan out a
  parallel lane.
- **Pd-2 / WP07 boundary**: confirm the `_render_per_project_store` compute/`issues` half was
  NOT prematurely turned into a core here — that split is WP07's.
- **INV-4 (seam)**: confirm patched callees are reached late-bound and the husk re-export keeps
  `sync.<name>` resolvable; the ~60 patch-tests are green.
- **A-5 (census)**: if any writer moved, confirm a 1:1 key swap, not a growth.
- **DIRECTIVE_044**: confirm the reused `Render` port — no second render port abstraction.


## Post-tasks squad corrections (BINDING)
- **Rn-3:** if this extraction relocates a consent/grant writer, perform the 1:1 census-key swap and keep `tests/architectural/test_sync_writer_census.py` green — editing that file is an authorized **small, individually-justified out-of-map edit** (one-line rationale). It is not in `owned_files` (shared arch-gate surface).
