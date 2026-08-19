---
work_package_id: WP11
title: sync_workspace degod — retire C901
dependencies:
- WP10
requirement_refs:
- C-004
- FR-001
- FR-003
- NFR-002
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- src/specify_cli/sync/sync_workspace_core.py
- tests/characterization/test_sync_workspace_render.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/sync/sync_workspace_core.py
- tests/characterization/test_sync_workspace_render.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile before anything else: `/ad-hoc-profile-load python-pedro`. Then run
`spec-kitty charter context --action implement --json` and apply the resolved
directives/tactics. State in your first status note which directives/tactics you applied
(expect `DIRECTIVE_001`/`043` gate discipline, ATDD `acceptance-test-first` — monkeypatch-golden
before restructure — plus smallest-viable-diff / TDD red-green; note C-004 frozen-daemon-behavior
as a hard boundary).

## Objective

`sync_workspace()` (`src/specify_cli/cli/commands/sync.py:2988`, complexity **30**, the third
`# noqa: C901` site) is the last of the three monster degods. It has **no existing CLI coverage**,
and its substantive SYNCED / CONFLICTS / FAILED arms run a **live `git rebase`** — non-deterministic
against a black-box snapshot. So the golden is a **monkeypatch-golden** (pedro Pd-4): stub
`sync.get_vcs` and `sync._detect_workspace_context` (def L2515) to return fixed `SyncResult`s, and
pin the capture encoding for the emoji glyphs. Freeze first (T021), then degod into a thin shell +
`sync_workspace_core.py` (T022), retiring the `# noqa: C901` (complexity ≤ 15).

**Hard boundary (C-004 / INV-6)**: the daemon read/guard code — `_require_daemon_owner_coherence`
(L1357) and the D-3 owner-coherence checks — **relocates INTACT**. Behavior is **frozen, not
changed**: no daemon reuse/kill/lifecycle change of any kind. This is a structural move under the
golden's protection, nothing more.

## Read first (source of truth)

The mission `plan.md` — IC-05 (`sync_workspace` its own WP; daemon read/guard relocates intact,
C-004) and the "WP-translation guards" § (**#3** monster-per-WP, **#6** freeze-before-extract with
the `get_vcs`/`_detect_workspace_context` stub note). The contract
(`contracts/sync-cli-characterization-contract.md`) item **4** — the monkeypatch-golden: stub the
two seams, pin emoji encoding, freeze the SYNCED/CONFLICTS/FAILED arms and the `mission_slug is
None` exit-1 arm. `data-model.md` INV-1/INV-5/INV-6; `research/squad-findings-post-plan.md` Pd-4
and A-1. **Zero behavior change**: identical glyphs, exit codes, and daemon-guard behavior pre/post.

## Environment (CRITICAL — worktree vs editable install)

Work in the lane worktree. The repo-root `.venv` editable-install points at the MAIN checkout,
so test YOUR changes with `PYTHONPATH=<worktree>/src`. Define `VENV=<repo>/.venv/bin; WT=<worktree>`.

Tests (SaaS-enable ON for the non-skip render path, work/gate OFF; the stubs make the rebase arms
hermetic):

```
SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 PYTHONPATH=$WT/src \
  $VENV/python -m pytest \
  tests/characterization/test_sync_workspace_render.py \
  tests/sync tests/cli/commands -k sync -q -p no:cacheprovider
```

Because `sync_workspace` touches daemon read/guard code, run any real-port/daemon-adjacent
regression in its own **`-n0`** pass. Lint/type:

```
$VENV/ruff check $WT/src/specify_cli/cli/commands/sync.py $WT/src/specify_cli/sync/sync_workspace_core.py
$VENV/mypy --strict $WT/src/specify_cli/sync/sync_workspace_core.py
```

NEVER run the full suite or `uv run`. Set a fast `review.test_command` to avoid the claim-time
full-suite hang.

## Subtasks

### T021 — Freeze the `sync_workspace` monkeypatch-golden (before any extraction)

**Purpose**: `sync_workspace` has zero coverage today and its real arms rebase live — pin the
observable output deterministically before touching the function.

**Steps**:

- Create `tests/characterization/test_sync_workspace_render.py` using the WP02 harness scaffolding.
- **Stub the non-determinism (Pd-4)** via late-bound `sync_module.<name>` monkeypatch:
  `monkeypatch.setattr("...cli.commands.sync.get_vcs", ...)` and
  `monkeypatch.setattr("...cli.commands.sync._detect_workspace_context", ...)` (def L2515) to
  return **fixed `SyncResult`s**. Do NOT run a real `git rebase`.
- Freeze the three substantive arms — **SYNCED**, **CONFLICTS**, **FAILED** — one `SyncResult`
  fixture each, snapshotting the full render including the emoji glyphs. **Pin the capture
  encoding** (UTF-8) so the glyphs are byte-stable in the snapshot.
- Freeze the **`mission_slug is None` → exit 1** arm.
- Stubs must target the same late-bound names so they still intercept after T022's relocation
  (INV-4). Confirm green on the **pre-degod** `sync_workspace`.

**Files**: `tests/characterization/test_sync_workspace_render.py` (new).

**Validation**: golden green against current `sync.py`; no DIR-041 ratchet mutation (C-003).

### T022 — Degod `sync_workspace()` into a thin shell + core; retire the C901

**Purpose**: split the cc-30 function into a thin shell + a `sync_workspace_core.py`, relocating
the daemon read/guard code intact, and remove the suppression.

**Steps**:

- Create `src/specify_cli/sync/sync_workspace_core.py` — the pure decision logic (workspace-context
  interpretation, `SyncResult` → render-plan mapping, exit-code decision). **I/O-free**: no
  `Console`/`print`/`git`.
- Restructure `sync_workspace()` (the shell that STAYS under `@app.command` in `sync.py`) into
  gather-I/O → core → render: gather `_detect_workspace_context` (L2515) + `get_vcs` results at the
  top, call the core, then render the SYNCED/CONFLICTS/FAILED lines and the exit-1 arm.
- **Relocate the daemon read/guard code INTACT (C-004)**: `_require_daemon_owner_coherence` (L1357)
  and the D-3 owner-coherence checks move verbatim — same call order, same guard semantics. Behavior
  is frozen, not changed (INV-6). If a check currently runs before the rebase, it still does.
- Reach monkeypatched callees via late-bound `sync_module.<name>` (INV-4 / C-005).
- **Delete the `# noqa: C901`** on the `def sync_workspace(` line; the shell must measure ≤ 15.
- Add focused unit tests for the core (pure) covering SYNCED/CONFLICTS/FAILED mapping and the
  `mission_slug is None` branch (Sonar new-code-coverage, same PR).

**Files**: `src/specify_cli/sync/sync_workspace_core.py` (new); `src/specify_cli/cli/commands/sync.py`
(`sync_workspace` shell rewritten, daemon guard relocated intact, `# noqa: C901` removed).

**Validation**: T021 monkeypatch-golden green pre/post; the ~60 patch-tests green; `sync_workspace`
≤ 15 with no `# noqa: C901`; core has zero `Console`/`print`/`git`.

## Branch Strategy

Planning/base + merge target: `refactor/wave4-sync-degod`. The execution worktree is allocated per
the computed lane from `lanes.json` (`spec-kitty implement WP11` prepares it) — do not reconstruct
the path. This is **lane-c**, position 11 in the serial chain; it edits the single `sync.py` and
depends on WP10 (rebase on its shrunk file). Not a parallel lane.

## Definition of Done

- [ ] `tests/characterization/test_sync_workspace_render.py` is a monkeypatch-golden stubbing
      `get_vcs` + `_detect_workspace_context`, freezing SYNCED/CONFLICTS/FAILED (emoji encoding
      pinned) and the `mission_slug is None` exit-1 arm — green pre AND post-degod.
- [ ] `sync_workspace_core.py` holds the pure decision logic, is I/O-free (no `Console`/`print`/`git`).
- [ ] `sync_workspace()` is a thin gather-I/O → core → render shell staying under `@app.command`;
      the daemon read/guard code (`_require_daemon_owner_coherence` + D-3 checks) relocated
      **INTACT** — behavior frozen, not changed (C-004 / INV-6).
- [ ] The `# noqa: C901` on `sync_workspace` is **removed**; complexity ≤ 15; `ruff`/`mypy --strict`
      clean, zero net-new suppressions.
- [ ] The ~60 sync patch-tests green; focused unit tests execute every new branch (same PR).

## Reviewer Guidance

- **Pd-4 (monkeypatch-golden)**: confirm the golden stubs `get_vcs`/`_detect_workspace_context` and
  runs no live rebase; confirm emoji encoding is pinned (a locale-dependent snapshot is a reject).
- **Guard #6**: T021 golden committed and green **before** the T022 degod commit.
- **C-004 / INV-6 (frozen daemon behavior)**: diff the relocated `_require_daemon_owner_coherence`
  call sites and D-3 checks line-by-line — same order, same semantics. Any behavioral delta
  (reuse/kill/lifecycle) is a hard reject, not a review comment.
- **A-1**: I/O hoisted to the top; the core is pure (grep for `Console`/`print`/`git`).
- **INV-4 / INV-5**: seam preserved via late binding, ~60 patch-tests green; `# noqa: C901` gone
  and `sync_workspace` truly ≤ 15.
