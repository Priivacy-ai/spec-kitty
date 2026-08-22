---
work_package_id: WP09
title: status degod — retire C901
dependencies:
- WP08
requirement_refs:
- FR-001
- FR-003
- NFR-002
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- src/specify_cli/sync/sync_status_core.py
- tests/characterization/test_sync_status_render.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/sync/sync_status_core.py
- tests/characterization/test_sync_status_render.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile before anything else: `/ad-hoc-profile-load python-pedro`. Then run
`spec-kitty charter context --action implement --json` and apply the resolved
directives/tactics. State in your first status note which directives/tactics you applied
(expect `DIRECTIVE_001`/`043` architectural-gate discipline, the ATDD `acceptance-test-first`
tactic — the golden freeze lands **before** the restructure — and the smallest-viable-diff /
TDD red-green tactics to be front-of-mind on this degod).

## Objective

`status()` (`src/specify_cli/cli/commands/sync.py:5387`, complexity **90**, one of the three
`# noqa: C901` sites) is the first of the three monster degods. Its non-`--check` human-render
path (the cc-90 build path) is currently a **gather-render-interleave**: network and daemon I/O
run *between* row emissions — `_check_server_connection` at L5524, `scan_sync_daemons` at L5541,
runtime-open and token-read happen mid-table-build. Per architect finding **A-1** this is NOT a
relocate: you must **restructure** into *gather-all-I/O → pure core → render*. Hoist every I/O
call to the top of the shell, hand the gathered facts to a pure core that decides the
`(label, value, color)` row tuples plus the boundary-coherence verdict, and let a thin render
shell print. Retire the `# noqa: C901`; drive `status` to complexity ≤ 15.

Per WP-translation guard **#6**, the `status` full-human-render golden must be **frozen inside
this WP, before the extraction** — a "golden done" tick on WP02 does NOT satisfy FR-001 for this
monster. Freeze first (T017), then restructure (T018).

## Read first (source of truth)

The mission `plan.md` — IC-04 ("Pure decision cores", the A-1 restructure risk note) and IC-05
("Monster degods"), plus the "WP-translation guards" § (esp. **#3** IC-05 → its own WP per
monster, and **#6** gap-freeze gates to the extraction WP). The contract
(`contracts/sync-cli-characterization-contract.md`) items **2** (`status` full human-render is a
frozen snapshot of the rendered table) and **1** (`status --check --json` → exit 0/2, already
frozen by WP02). `data-model.md` INV-1 (byte-stable observable contract), INV-5 (retire the
C901, ≤15 complexity, ≤800 LOC/module). `research/squad-findings-post-plan.md` A-1 and Pd-2 (the
`_render_per_project_store` compute-half already split by WP07). This is a **zero behavior
change** refactor: every rendered glyph, color, row order, and exit code is identical pre/post.

## Environment (CRITICAL — worktree vs editable install)

Work in the lane worktree. The repo-root `.venv` editable-install points at the MAIN checkout,
so test YOUR changes with `PYTHONPATH=<worktree>/src`. Define `VENV=<repo>/.venv/bin; WT=<worktree>`.

Tests (the render arms need SaaS-enable ON to reach the non-skip path; keep work/gate OFF so the
golden is hermetic — the two vars are orthogonal, WP-translation guard #8):

```
SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 PYTHONPATH=$WT/src \
  $VENV/python -m pytest \
  tests/characterization/test_sync_status_render.py \
  tests/characterization/test_sync_status_check.py \
  tests/sync tests/cli/commands -k sync -q -p no:cacheprovider
```

Lint/type:

```
$VENV/ruff check $WT/src/specify_cli/cli/commands/sync.py $WT/src/specify_cli/sync/sync_status_core.py
$VENV/mypy --strict $WT/src/specify_cli/sync/sync_status_core.py
```

NEVER run the full suite or `uv run` (a bare `uv run` re-syncs and destroys the hand-built
`.venv`). Run any real-port/daemon test in its own `-n0` pass. Set a fast `review.test_command`
to avoid the claim-time full-suite hang on this WP.

## Subtasks

### T017 — Freeze the `status` FULL human-render golden (before any extraction)

**Purpose**: pin the observable output of the cc-90 non-`--check` build path so the A-1 reorder
is provably behavior-stable. This is the load-bearing safety net for T018.

**Steps**:

- Create `tests/characterization/test_sync_status_render.py`. Use the WP02 golden harness
  scaffolding (`CliRunner`, HOME isolation, the `SPEC_KITTY_ENABLE_SAAS_SYNC=1` fixture) — reuse,
  do not re-invent (`DIRECTIVE_044`).
- Snapshot the **full rendered table** of `spec-kitty sync status` (no `--check`): every row
  `(label, value, color)`, the row order, the server-connection line, the daemon/orphan lines,
  the boundary-coherence block, and the per-project-store block. This is the branch WP02
  deliberately left to this WP (contract item 2) — a `--json`-only or `--check`-only freeze does
  NOT satisfy FR-001 here.
- **Determinism**: stub the I/O seams so the snapshot is stable — `_check_server_connection`
  (L5524 call site), `scan_sync_daemons` / `get_sync_daemon_status` (L5429/L5541), and the
  runtime-open/token-read seam. Reach them via late-bound `sync_module.<name>` monkeypatch
  (`monkeypatch.setattr("...cli.commands.sync.<name>", ...)`) so the seam survives T018's
  relocation (INV-4). Cover at least: coherent-boundary + healthy-server, and an
  incoherent-boundary arm, so both the OK and the failure row-sets are frozen.
- Confirm the snapshot is green on the **pre-restructure** `status` (run before touching T018).

**Files**: `tests/characterization/test_sync_status_render.py` (new).

**Validation**: golden green against current `sync.py`; does NOT mutate any DIR-041 ratchet
allowlist (C-003).

### T018 — Restructure `status()` into gather-I/O → core → render; retire the C901

**Purpose**: convert the interleaved build into a three-phase shell backed by a pure core, and
remove the complexity suppression.

**Steps**:

- Create `src/specify_cli/sync/sync_status_core.py`. It is **I/O-free** — no `Console`, no
  `print`, no network, no filesystem. It consumes the WP07 `sync_store_report_core` compute
  outputs and the gathered facts, and returns dataclasses.
- Extract two pure functions into the core:
  - `build_status_rows(facts) -> list[StatusRow]` — decides the `(label, value, color)` tuples
    from the already-gathered connection/daemon/store facts (the row logic currently inlined
    L5429-5600).
  - `evaluate_boundary_coherence(...) -> BoundaryVerdict` — the boundary gate. **Reuse** the
    canonical `build_boundary_failure_set` (imported at L5604, called L5618) and
    `_build_boundary_check_failures` (def L5038, called from the `--check` path L5847) — do NOT
    re-implement boundary logic (`DIRECTIVE_044`); the core assembles the verdict from their
    output.
- In `status()` (the shell that STAYS in `sync.py` under `@app.command` — the seam anchor):
  hoist **all** I/O to the top (`_check_server_connection` L5524, `scan_sync_daemons` L5541,
  runtime-open, token-read), then call the two core functions, then render. The `--check --json`
  arm (frozen by WP02) routes through `evaluate_boundary_coherence` and emits the same exit 0/2.
- Reach any monkeypatched callee via late-bound `sync_module.<name>` attribute access — never
  `from .sync import <name>` early-binding (INV-4 / C-005).
- **Delete the `# noqa: C901`** on the `def status(` line; the shell must genuinely measure ≤ 15.
- Add focused unit tests for `build_status_rows` and `evaluate_boundary_coherence` (pure,
  stub-testable) exercising each new branch — the Sonar new-code-coverage expectation for every
  extracted helper (same PR).

**Files**: `src/specify_cli/sync/sync_status_core.py` (new); `src/specify_cli/cli/commands/sync.py`
(`status` shell rewritten, `# noqa: C901` removed).

**Validation**: T017 golden green pre/post; `status --check --json` (WP02) green; the ~60
patch-tests green; `status` complexity ≤ 15 with no `# noqa: C901`; core has zero `Console`/`print`.

## Branch Strategy

Planning/base + merge target: `refactor/wave4-sync-degod`. The execution worktree is allocated per
the computed lane from `lanes.json` (`spec-kitty implement WP09` prepares it) — do not reconstruct
the path. This is **lane-c**, position 9 in the serial chain: it edits the single `sync.py` and so
depends on WP08 (rebase on its shrunk file). Not a parallel lane.

## Definition of Done

- [ ] `tests/characterization/test_sync_status_render.py` freezes the full non-`--check`
      human-render (rows + boundary block + store block), covering coherent and incoherent arms,
      green pre AND post-restructure.
- [ ] `sync_status_core.py` holds `build_status_rows` + `evaluate_boundary_coherence`, is
      I/O-free (no `Console`/`print`/network/fs), consumes WP07's store-report core, and delegates
      boundary logic to `build_boundary_failure_set` / `_build_boundary_check_failures`.
- [ ] `status()` is a thin gather-I/O → core → render shell that STAYS under `@app.command` in
      `sync.py`; all I/O hoisted to the top; late-bound `sync_module.<name>` seam preserved.
- [ ] The `# noqa: C901` on `status` is **removed**; complexity ≤ 15; `ruff`/`mypy --strict`
      clean with zero net-new suppressions.
- [ ] `status --check --json` exit 0/2 (WP02 golden) green; the ~60 sync patch-tests green.
- [ ] Focused unit tests execute every new branch/helper in the core (same PR).

## Reviewer Guidance

- **Guard #6 (freeze-before-extract)**: confirm T017's full-render golden was committed and green
  **before** the T018 restructure commit — check commit order. A `--json`/`--check`-only freeze is
  a reject; item 2 of the contract demands the human table.
- **A-1 (restructure, not relocate)**: verify all I/O is genuinely hoisted to the top of the shell
  and the core is pure — grep the core for `Console`, `print`, `scan_sync_daemons`,
  `_check_server_connection`; any hit is a reject.
- **DIRECTIVE_044 (no fork)**: the core must call `build_boundary_failure_set` /
  `_build_boundary_check_failures`, not re-implement boundary evaluation.
- **INV-4 (seam)**: confirm the relocation uses late-bound `sync_module.<name>` and the ~60
  patch-tests pass; confirm the render snapshot's stubs still intercept post-move.
- **INV-5**: the `# noqa: C901` is gone and `status` truly measures ≤ 15 (not merely "tests pass").


## Post-tasks squad corrections (BINDING)
- **Rn-1:** the `status` full-human-render golden is **frozen in WP02** (`test_sync_cli_safe.py`), not here. T017 is now: **VERIFY** that golden is green BEFORE your restructure commit and again AFTER (do not re-freeze it). You MAY add extraction-specific assertions (e.g. `build_status_rows()`/`evaluate_boundary_coherence()` unit tests) in `test_sync_status_render.py`, but the behavior-lock is the WP02 snapshot.
