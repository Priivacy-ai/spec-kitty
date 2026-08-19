---
work_package_id: WP03
title: Husk scaffold + sync.py Tier-1 (chain head)
dependencies:
- WP02
requirement_refs:
- C-005
- FR-002
- FR-006
- NFR-003
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/sync.py
create_intent:
- src/specify_cli/sync/sync_ports.py
- tests/architectural/test_sync_no_early_bind.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/sync/sync_ports.py
- tests/architectural/test_sync_no_early_bind.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile before anything else: `/ad-hoc-profile-load python-pedro`. Then run
`spec-kitty charter context --action implement --json` and apply the resolved
directives/tactics. State which you applied — the campsite directive (`DIRECTIVE_025`,
tidy-first) and the smallest-viable-diff tactic bind the Tier-1 half; the canonical-authority
directive (`DIRECTIVE_044`) binds the husk/ports half.

## Objective

This is the **head of the serial chain** (lane-c) and the first WP that edits
`cli/commands/sync.py`. Two jobs: (1) establish the **husk scaffold** — the guarded re-export
block + the late-bound `sync_module.<name>` calling convention + the `SyncPorts` skeleton —
so that when later WPs relocate private bodies into `specify_cli.sync.*`, the ~60
`monkeypatch.setattr("…commands.sync.<name>", …)` seams keep intercepting (INV-4, C-005); and
(2) land the **Tier-1 mechanical fixes** on `sync.py` (S3358 nested ternaries, S1192 re-inlined
literals, S7632 suppression-format) now that the WP02 golden net protects them (guard #5).

The husk scaffold MUST exist before the first private relocates (WP-translation guard #2) —
that is why it is the chain head, not a "finalize last" step. The `@app.command`-decorated
thin shells **stay in `sync.py`** (the Typer seam anchor — moving a decorated command changes
which callable Typer invokes); only the extracted *logic* moves in later WPs.

## Read first (source of truth)

The mission plan.md (IC-01 Tier-1 + IC-06 husk-scaffold note; the "WP-translation guards" §,
esp. #2 husk-scaffold-early + #5 Tier-1-post-golden), the contract (rules 2 & 3),
`data-model.md` (INV-4 seam, INV-5 complexity, the `SyncPorts` entity),
`research/squad-findings-post-plan.md` (Pr-2/A-4 husk + `@app.command`, A-6 husk LOC ceiling).
Reference `src/specify_cli/agent_tasks_ports.py` — the `TasksPorts` frozen dataclass +
`default_ports()` shape you mirror, and its module docstring on late-binding seams. Skim the
`runtime_bridge` #2531 re-export precedent. This is a Wave-4 degod: **zero behavior change**;
golden (WP02) + the ~60 patch-tests are the guard.

## Environment (CRITICAL — worktree vs editable install)

Work in the lane worktree. The repo-root `.venv` editable-install points at the MAIN checkout,
so test YOUR changes with `PYTHONPATH=<worktree>/src`. Define `VENV=<repo>/.venv/bin;
WT=<worktree>`.

```
SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 PYTHONPATH=$WT/src \
  $VENV/python -m pytest tests/characterization/test_sync_cli_safe.py \
    tests/cli/commands/test_sync_*.py tests/architectural/test_sync_no_early_bind.py \
    -q -p no:cacheprovider
```

(SAAS-enable var is `SPEC_KITTY_ENABLE_SAAS_SYNC`, **NOT** `SPEC_KITTY_SAAS_SYNC`.) Lint/type:
`$VENV/ruff check <files>`, `$VENV/mypy --strict <files>`. Real-port/daemon suites `-n0`. Set a
fast `review.test_command` to avoid the claim-time full-suite hang (guard #8). NEVER run the
full suite or `uv run`.

## Subtasks

### T007 — Husk re-export block + late-bind convention + AST early-bind guard

**Purpose**: make `sync.py` a durable *host* whose private symbols remain reachable as module
attributes even after their bodies move, and lock in the calling convention that keeps
`monkeypatch.setattr` seams live.

**Steps**:

- Add a guarded re-export block to `sync.py` (the `runtime_bridge` #2531 pattern): after the
  `sync_*` cores/adapters exist (later WPs), relocated privates are re-imported back into the
  `sync` namespace so `sync.<name>` resolves. In THIS WP, scaffold the block structure + a
  clear comment marking where relocated symbols re-enter; nothing is relocated yet, so it may
  start near-empty but must be the single canonical place later WPs add to.
- Establish the **late-bound calling convention**: relocated shells reach a monkeypatched
  callee via attribute access on the module object (`sync_module.<name>` / `getattr`), **never**
  `from .sync import <name>` early-binding — because `monkeypatch.setattr(
  "…commands.sync.<name>", …)` rebinds the *module attribute*, which an early-bound local
  reference would not see. Document this convention in the husk block comment.
- Author `tests/architectural/test_sync_no_early_bind.py`: an **AST guard** that parses the
  `sync_*` modules (and any future relocated shell) and fails if a module `from
  …commands.sync import <patched_name>` early-binds a name in the documented seam set (from
  WP02's `SEAM_CALLEES`). This prevents a future WP from silently breaking a patch seam.
- Confirm the `@app.command` decorators STAY in `sync.py` — do not move any decorated command.

**Files**: `src/specify_cli/cli/commands/sync.py`, `tests/architectural/test_sync_no_early_bind.py`.

**Validation**: the AST guard passes; the ~60 patch-tests + golden still green (nothing moved
yet, so this is a no-op-behavior scaffold).

### T008 — `SyncPorts` frozen dataclass + `default_ports()`

**Purpose**: stand up the injectable capability bundle (the `TasksPorts` shape) that WP04+
adapters populate — one bundle, injected on the shell.

**Steps**:

- Create `src/specify_cli/sync/sync_ports.py`. Define `@dataclass(frozen=True) class SyncPorts`
  bundling the ports the later WPs need. **Reuse** `Render` / `GitOps` / `Clock` / `FsReader`
  from `agent_tasks_ports.py` (import them; do NOT fork a second port abstraction —
  `DIRECTIVE_044`). Add fields for the sync-specific ports as placeholder Protocol references
  that WP04-WP08 flesh out (`render`, `runtime`, `dispatch`, `purge`, `authority_read`,
  `authority_write`, `authority_admission`) — but only declare in THIS WP what you can back
  with a real adapter; leave the rest as documented TODO fields the chain fills, or start
  minimal (`render` + reused ports) and grow per-WP. Prefer minimal-and-grow over speculative
  fields.
- Add `default_ports() -> SyncPorts` returning the Real-adapter bundle (mirroring
  `agent_tasks_ports.default_ports()`). Where a real adapter does not yet exist (WP04+), wire
  it in that WP — do not stub a fake here.
- `SyncPorts` lives under `specify_cli.sync.*` (INV-3) — never `runtime` or a new top package.

**Files**: `src/specify_cli/sync/sync_ports.py`.

**Validation**: `mypy --strict` clean; importing `SyncPorts`/`default_ports` succeeds.

### T009 — Tier-1: extract the S3358 nested ternaries

**Purpose**: retire the 5 Sonar `S3358` (nested ternary) smells now that the golden protects
the behavior. Two of them are the **same** percent→color logic duplicated — collapse to one
shared helper.

**Steps**:

- Find the duplicated depth/percent→color ternary at ~L184 (inside `_build_queue_summary_lines`
  / the queue-health render) and its twin at ~L6043 (in the `doctor`/status render region).
  Extract a single shared helper `def _depth_color(pct: float) -> str:` returning the color
  token, and call it from both sites. (Verify exact lines with `grep -n` in your worktree — the
  file is 6,332 LOC and line numbers drift; the two sites are structurally identical
  percent-band ternaries.)
- Flatten the three remaining nested ternaries at ~L2209, ~L2212, and ~L4640 into named
  helpers or `if/else` blocks — one small pure helper each, so the value is byte-identical.
- Each extracted helper needs a focused unit test exercising its bands/branches (Sonar
  new-code-coverage; every new branch/helper gets a test in the same WP).

**Files**: `src/specify_cli/cli/commands/sync.py` (+ a focused test file for the helpers, e.g.
`tests/cli/commands/test_sync_render_helpers.py` if none exists).

**Validation**: `ruff check --select S3358` = 0 on the file; helper tests green; golden green.

### T010 — Tier-1: S1192 re-inlines + S7632 suppression-format

**Purpose**: reference the two re-inlined literals through their existing constants, hoist one
more repeated literal, and correct the *format* of the S7632 suppressions — never delete a
guarded `except`.

**Steps**:

- `"bold yellow"` is re-inlined at ~L6217 and ~L6286 (doctor Rich-table `header_style`) while
  the module already defines `_WARNING_HEADER_STYLE = "bold yellow"` at L103 — route both sites
  through the constant. (Other `[bold yellow]` markup strings at L4297/L4355/L6309 are inline
  Rich markup, not the header-style constant — leave those unless they cleanly consolidate;
  do not over-hoist.)
- Hoist the repeated `"[dim]Unavailable[/dim]"` fallback (L2200-2203, four uses in the routing
  table) to a named module constant and reference it.
- **Correct the S7632 suppression format**: at ~L1865, ~L1889, ~L3694, ~L3720 the `# noqa`
  comments guard intentional `except` blocks but use the wrong format. Rewrite them to the
  canonical `# noqa: <code> — <em-dash rationale>` form (em-dash `—`, not hyphen), keeping the
  narrow scope + inline rationale. **NEVER delete a guarded `except`** (FR-006) — this is a
  format correction only; the exception-handling behavior stays byte-identical.

**Files**: `src/specify_cli/cli/commands/sync.py`.

**Validation**: `ruff check --select S1192,S7632` = 0 on the file; no `except` block removed or
altered in behavior; golden + patch-tests green.

## Branch Strategy

Planning/base + merge target: `refactor/wave4-sync-degod`. The execution worktree is allocated
per the computed lane from `lanes.json` (`spec-kitty implement WP03` prepares it) — do not
reconstruct the path. This is **lane-c head**: WP04-WP12 rebase on this WP's shrunk `sync.py`.

## Definition of Done

- [ ] Husk re-export block scaffolded (single canonical place; `@app.command` shells stay in
      `sync.py`); late-bound `sync_module.<name>` convention documented.
- [ ] `tests/architectural/test_sync_no_early_bind.py` AST guard authored and green.
- [ ] `sync_ports.py` defines `SyncPorts` (reusing Render/GitOps/Clock/FsReader) +
      `default_ports()`; lives under `specify_cli.sync.*` (INV-3).
- [ ] `S3358` = 0 (shared `_depth_color` collapses the L184≡L6043 twin); each helper has a
      focused test.
- [ ] `S1192` re-inlines routed through `_WARNING_HEADER_STYLE` + the hoisted
      `[dim]Unavailable[/dim]` constant; `S7632` suppressions in canonical em-dash format,
      **no guarded `except` deleted**.
- [ ] WP02 golden + the ~60 patch-tests green; `ruff` + `mypy --strict` clean; touched
      functions ≤ 15 complexity.

## Reviewer Guidance

Verify the WP-translation guards that bind this WP:

- **Guard #2 (husk-early)**: confirm the re-export block + late-bind convention exist BEFORE
  any private relocates, and that `@app.command`-decorated commands were NOT moved out of
  `sync.py`.
- **INV-4 (seam)**: confirm the AST guard actually references WP02's seam-callee set and would
  fail on an early-bound patched name.
- **Guard #5 (Tier-1 post-golden)**: confirm WP02 merged first and the golden is green pre/post
  the ternary extractions.
- **FR-006**: diff each `# noqa: S7632` site — the change must be *format only* (em-dash
  rationale); reject any removed/altered `except`.
- **DIRECTIVE_044**: confirm `SyncPorts` reuses the `agent_tasks_ports` protocols and does not
  fork a parallel port abstraction.
- Confirm every new helper (`_depth_color`, flattened ternary helpers) has a focused test.
