---
work_package_id: WP02
title: Compat-surface guard (WP-0b, BLOCKING safety net)
dependencies: []
requirement_refs:
- FR-012
- C-004
tracker_refs:
- '2531'
planning_base_branch: design/runtime-bridge-degod
merge_target_branch: design/runtime-bridge-degod
branch_strategy: Planning artifacts for this mission were generated on design/runtime-bridge-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/runtime-bridge-degod unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-runtime-bridge-degod-01KX8M1C
base_commit: cdbcf0783e582c9c4f0089708c13dcc7523b7fde
created_at: '2026-07-11T14:30:55.110327+00:00'
subtasks:
- T007
- T008
- T009
- T010
phase: Extraction spine
shell_pid: '1268842'
history:
- at: '2026-07-11T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/runtime/
create_intent:
- tests/runtime/test_bridge_compat_surface.py
execution_mode: code_change
owned_files:
- tests/runtime/test_bridge_compat_surface.py
role: implementer
tags: []
task_type: implement
---

# WP02 — Compat-surface guard (WP-0b, BLOCKING safety net)

## Context

The **biggest land-ability risk** of the mission. Tests bind to **~50 distinct
private symbols** on `runtime.next.runtime_bridge` (via four idioms:
`from …runtime_bridge import _x`, `monkeypatch.setattr(runtime_bridge, _x, …)`,
`mocker.patch("…runtime_bridge._x")`, and bare `runtime_bridge._x`). When an
extraction WP relocates a symbol, a **plain re-export silently breaks patching**:
`monkeypatch.setattr(runtime_bridge, "_x", …)` becomes a **no-op** if `_x`'s leaf
is called by another function that moved into the *same* seam — the intra-seam
call resolves via the **seam module's own global**, not the shim, so the test
passes by coincidence (false-green). This guard exists to catch exactly that.

Read `contracts/compat-surface.md` — it is the authority for this WP. Build it
**now, against unmodified source**, alongside the WP01 parity oracle; both are
C-004 blocking gates. `research.md §Compat` is the derivation;
`rbresearch-C-compat.md` (scratchpad) holds the full per-symbol table.

**Red-first note.** Like WP01, this guard's final state on unmodified source is
GREEN. But guard (A) is only meaningful if the sentinel actually **fires** — so
each sentinel MUST be authored red-first: patch the symbol, drive its reaching
entry, and prove the injected sentinel is raised. A sentinel that is a no-op
(wrong entry, or symbol never reached) passes vacuously — that is the false-green
this WP must make impossible. Prove each sentinel fires before declaring the
guard green.

## Ordered steps

### T007 — Inventory the ~50 patched symbols mapped to reaching entry (`test_bridge_compat_surface.py`)
Enumerate all ~50 distinct private symbols bound by tests today (across the four
idioms). For **each** symbol, record its **reaching public entry** —
`decide_next_via_runtime` (`:2524`), `query_current_state` (`:3199`), and/or
`answer_decision_via_runtime` (`:3355`) — because a symbol reached only via
query/answer cannot be exercised by driving `decide_next`. **Per-entry reach
mapping is BINDING.** Note the heaviest / grounded high-risk cases so later WPs
size their compat work:
- `_check_cli_guards` (26 imports); `_state_to_action` / `_compute_wp_progress`
  (10 patches each); `_build_prompt_or_error` (9);
  `_advance_run_state_after_composition` (8 patch + 9 attr).
- 🔴 `_primary_runtime_feature_dir` (patched 6×; intra-seam caller
  `_resolve_mission_ulid` calls it unpatched → LAZY-ACCESSOR required later);
  `_build_discovery_context` (reached only via intra-seam movers).
- ⚠ SPLIT-flag (patchable via residual path, dead via render-seam path):
  `_state_to_action`, `_compute_wp_progress`, `_build_prompt_or_error`,
  `_is_wp_iteration_step`.
- KEEP-IN-PLACE anchors: `_wrap_with_decision_git_log` (`:187`) and the thin
  `_advance_run_state_after_composition` residual delegate.

### T008 — Guard (A): per-entry behavioral sentinel (`test_bridge_compat_surface.py`)
For **each** of the ~50 symbols: `monkeypatch.setattr(runtime_bridge, <name>, …)`
with a patch that injects a **sentinel** (raise a unique marker), drive **the
public entry that reaches it** (from T007), and `pytest.raises` on the sentinel.
If the patch is a no-op the sentinel never fires → the test **FAILS** (catches
false-green).
- **Per-entry reach mapping is BINDING and drives correctness.** A single-entry
  sentinel (all patches driven through `decide_next_via_runtime`) is **itself
  false-green** for symbols reached only via `query_current_state` (e.g. the
  `_build_*_query_decision` family) or `answer_decision_via_runtime` (e.g. the
  `_map_runtime_decision` cluster) — the patched leaf is never executed, the
  sentinel never fires, the guard passes vacuously.
- Symbols reached from more than one entry: drive **each** reaching entry.
- Prove each sentinel fires (red-first) — a sentinel that cannot be shown to fire
  is not a guard.

### T009 — Guard (B): static AST identity + forbid function-scope re-imports (`test_bridge_compat_surface.py`)
Two static checks over the module family:
- **Identity re-export** — for every relocated symbol, assert `rb.x is seam.x`
  (the compat name on `runtime_bridge` **is** the seam's object, not a copy).
- **Forbid function-scope re-imports of compat names** — AST-walk the seam
  modules and fail on any `import`/`from … import` of a compat name inside a
  function body (the exact structural signature of false-green shadowing —
  a local re-import shadows the patched global).
On unmodified source (no relocations yet), the identity check has nothing to
assert; author it so it becomes load-bearing as WP03+ relocate symbols, and prove
the AST anti-shadow walk runs and passes now.

### T010 — Prove the compat guard GREEN on unmodified source (`test_bridge_compat_surface.py`)
Run the full guard against **unmodified** source: every sentinel fires when
driven through its correct reaching entry (guard A green), and the AST walk passes
(guard B green). Record, in the test module docstring or a comment, the per-symbol
→ reaching-entry map so later WPs re-run this guard as their acceptance gate
without re-deriving the mapping.

## Acceptance
- Guard **green on unmodified source**.
- **Every symbol's sentinel proven to fire** — no false-green; each driven through
  its correct reaching entry (query/answer-only symbols driven via query/answer,
  not `decide_next`).
- Static AST guard (B): identity re-export check + function-scope re-import
  prohibition both present and passing.
- Per-symbol → reaching-entry inventory recorded for reuse by extraction WPs.
- `ruff` + `mypy` clean on the new file; no suppressions added.

## Safeguards
- **A sentinel driven through the wrong entry silently never fires** — map each
  symbol to its reaching entry (T007) and drive **that** entry. This is the
  single most common way this guard goes vacuously green.
- Re-export alone is insufficient for names a **sibling module calls** — those
  need the `_wf`-style LAZY-ACCESSOR in the relocating WP; flag them in T007 so
  WP10 (identity) and the sibling-called cases get it.
- `__all__` (introduced later for the 8 public names) governs only `import *`; it
  does **NOT** preserve the ~50 private symbols — those live in the explicit
  guarded compat re-export block. Do not conflate the two.

## References
- `contracts/compat-surface.md` — authoritative contract (implement verbatim)
- `research.md:61-78` §Compat (50-symbol inventory, false-green minefield, two guards)
- `src/runtime/next/runtime_bridge.py:2524` `decide_next_via_runtime` (reaching entry 1)
- `src/runtime/next/runtime_bridge.py:3199` `query_current_state` (reaching entry 2 — the `_build_*_query_decision` family)
- `src/runtime/next/runtime_bridge.py:3355` `answer_decision_via_runtime` (reaching entry 3 — the `_map_runtime_decision` cluster)
- `src/runtime/next/runtime_bridge.py:78` `_primary_runtime_feature_dir`, `:134` `_resolve_mission_ulid` (grounded high-risk intra-seam pair)
- `src/runtime/next/runtime_bridge.py:187` `_wrap_with_decision_git_log` (KEEP-IN-PLACE anchor)
- `tests/runtime/test_runtime_bridge_identity.py` (existing patch sites for `_primary_runtime_feature_dir`)

## Activity Log

- 2026-07-11T16:51:32Z – user – shell_pid=1268842 – Moved to for_review
- 2026-07-11T17:03:48Z – user – shell_pid=1268842 – Moved to approved
