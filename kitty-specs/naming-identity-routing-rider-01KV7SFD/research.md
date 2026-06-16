# Phase 0 Research — Naming/Identity Routing Rider

**Mission:** `naming-identity-routing-rider-01KV7SFD` · **Date:** 2026-06-16
**Method:** exhaustive `rg` inventory of identity-derivation idioms across `src/`, with per-site
classification and ownership mapping. Supersedes the spec's "~20 sites" estimate with the verified count.

## Decision 1 — Call-site inventory (the exact target set)

### Class A — bare short-id derivations (`*_id[:8]` / `[0:8]`)
Raw `rg '\b\w*_id\[0?:8\]'` returned 27 hits; after excluding the **seam internals** (the canonical
implementations) and **docstrings/comments**, the **live shadow sites** are:

| # | File:line | Holds an `ExecutionContext`? | Class | Action |
|---|-----------|------------------------------|-------|--------|
| 1 | `src/runtime/next/_internal_runtime/retrospective_terminus.py:69` | No | A-route | `mid8(mission_id)` |
| 2 | `src/specify_cli/status/aggregate.py:250` | No | A-route | `resolve_mid8`/`mid8` (guard empty) |
| 3 | `src/specify_cli/git/sparse_checkout.py:286` | No | A-route | `mid8(mission_id)` |
| 4 | `src/specify_cli/dashboard/scanner.py:438` | No (consumes read kernel, wrong cardinality) | A-route | `mid8`/`resolve_mid8` |
| 5 | `src/specify_cli/cli/commands/doctor.py:3070` | No | A-route | `mid8(mission_id)` |
| 6 | `src/specify_cli/cli/commands/doctor.py:3162` | No | A-route | `mid8(mission_id)` |
| 7 | `src/specify_cli/doctrine_synthesizer/apply.py:745` | No | A-route | `mid8(mission_id)` |
| 8 | `src/specify_cli/doctrine_synthesizer/apply.py:831` | No | A-route | `mid8(mission_id)` |
| 9 | `src/specify_cli/cli/commands/implement.py:386` | No (holds a `meta` dict; already routes downstream via `resolve_transaction_mid8`) | A-route | `mid8(mission_id)` for the fallback |
| 10 | `src/specify_cli/context/mission_resolver.py:163` | No | A-route | `mid8(mission_id)` |

**Seam internals — KEEP (these ARE the SSOT):** `branch_naming.py` (`mid8` line 122 body, `resolve_mid8`
169, the provable-match cross-check 192/408) and `mission_runtime/context.py` (`IdentityFragment`
single-derivation 112 + its `__post_init__` guard 99). These are the *one* place `mission_id[:8]` is
allowed to live; everything else routes to them.

**NON-target (must not false-positive the ratchet):** `src/specify_cli/invocation/executor.py:469`
uses `invocation_id[:8]` — an **Op invocation id** truncation for a log message, a *different identity
domain* (not `mission_id`). The ratchet's pattern must target mission-identity short-ids specifically,
or carry this as an explicitly-justified allow-list entry.

**Verdict:** **10 live route-sites**, **0 genuine fragment-adopt sites** (no site re-derives while
holding an `ExecutionContext` — the expected 2–3 turned out to be already-correct or meta-dict-based).
So FR-002 collapses to a **verification** (confirm `IdentityFragment` is the only context-held
derivation), and the work is overwhelmingly **route-don't-thread**.

### Class C — static branch/worktree composes outside the seam (#2000/#1899-tail/#1900)
Most `kitty/mission-` and `.worktrees/` hits are docstrings, the `WORKTREES_DIR`/`LANES_FILENAME`
constants, husk-detection (path *inspection*, not composition), or regexes. The genuine live composes:

| File:line | Note | Action |
|-----------|------|--------|
| `src/specify_cli/lanes/recovery.py:135` | `pattern = f"kitty/mission-{mission_slug}*"` — a branch-listing **glob** | Route via a seam glob helper or justify as search-only |
| `src/specify_cli/core/vcs/detection.py:161` | `parse_mission_slug_from_branch(f"kitty/mission-{worktree_name}")` — compose-to-parse round-trip | Route the compose through the seam |

`workspace/context.py:817` already carries a "Route the COMPOSE … through the seam" comment — confirm it
is genuinely routed (it appears done).

## Decision 2 — `coordination/workspace.py` is NOT a shadow path (already routed)
`CoordinationWorkspace.worktree_path` / `.branch_name` already delegate to the seam
(`_seam_coord_dir_name`, `_seam_coord_reconstruct_branch`, FR-010 of the 3.2.0 mission). **No action** —
and explicitly out of scope (write-side/coord is 3.2.2 per C-005).

## Decision 3 — `locate_project_root` (#1971-tail) is already consolidated → verify-and-close
Three definitions exist, but they form a **single-authority delegation chain**, not a triplication:
- `src/specify_cli/core/paths.py:48` — **authoritative** (env-var Tier 1 / worktree-pointer Tier 2 / `.kittify` walk Tier 3).
- `src/specify_cli/core/project_resolver.py:8` — deferred-import delegate to `paths` (import-cycle safety; explicit #1971 rationale).
- `src/specify_cli/__init__.py:52` — deferred-import delegate to `project_resolver`.

**Verdict:** #1971-tail = **verify the delegation chain is intact + add/confirm a regression test that
all three converge**; do not "consolidate" further (the shims are intentional). Reverting either shim to
a module-level import is the documented regression.

## Decision 4 — #1993 `resolve_lanes_dir` is real → extract WITH read-side adoption (resolves C-002)
There is **no** `resolve_lanes_dir`/`_lanes_feature_dir` seam. The lanes file path is composed inline as
`feature_dir / "lanes.json"` (and the `LANES_FILENAME` constant) across ~10 read sites:
`workspace/context.py:798`, `context/resolver.py:203`, `lanes/persistence.py`, `lanes/worktree_allocator.py`,
`lanes/compute.py`, `lanes/recovery.py`, `lanes/merge.py`, `core/worktree_topology.py:154`.

- **C-002 RESOLUTION: carry-with-adoption (recommended path confirmed).** Extract `resolve_lanes_dir(feature_dir)`
  **and** route the ~10 inline `feature_dir / "lanes.json"` read sites through it **in the same WP**. The
  adoption is mechanically simple (one-line substitution per site) and therefore **bounded** — it does
  not warrant deferral. Shipping the extraction *alone* would leave the inline joins as a parallel
  `_lanes_feature_dir` twin (the half-strangle C-002 forbids). **Decision: carry. Do not defer to 3.2.2.**

## Decision 5 — Ratchet design (the tripwire; the sole form-coupled test)
Extend `tests/architectural/test_no_worktree_name_guess.py`:
- Add a detector for bare mission-identity short-ids (`mission_id[:8]`, `…_id[:8]`, `[0:8]`) across `src/`,
  **including `dashboard/scanner.py`**.
- Seed an **explicit allow-list** of the currently-known sites, then **remove each entry as its site is
  routed** — the allow-list must end strictly smaller (ideally empty for the mission-identity class).
- Scope honestly: this is **syntax-level** and defeated by `mid[:8]`/helper indirection — documented as a
  **tripwire, not a completeness oracle** (NFR-003). Shape-aware/AST detection is explicitly out of scope.
- Keep the `invocation_id[:8]` non-target from tripping it (pattern specificity or a justified entry).

## Decision 6 — Test strategy (operator caveat, binding)
- **Function over form / behavioral.** Assert derived names/paths are correct & unchanged end-to-end
  (NFR-001 byte-parity), not which internal fragment was read.
- **Verification-by-deletion (C-004).** Delete each shadow implementation (FR-009); the behavioral suite
  staying green proves the seam is the only path — this replaces white-box "which-fragment" assertions.
- **TDD-first (C-003)** for any behavioral change; for pure routing with byte-parity, a characterization
  test pinning the current output precedes the substitution.
- The **ratchet is the lone intentional form-coupled test** (architectural-consistency exception).

## Net scope (initial Phase 0 estimate — CORRECTED below)
10 route-sites · ~2 static composes · #1993 extract+adopt · #1971-tail & #1888 verify-and-close · 1
ratchet extension.

## Corrections from the adversarial scope review (2026-06-16) — AUTHORITATIVE
Full detail: `scope-review/SCOPE-REVIEW-SYNTHESIS.md` + the four `scope-review/*.md` findings.

- **+5 missed route-sites** (var-name-independent shapes the `*_id[:8]` grep missed):
  `mission_runtime/resolution.py:171` (`str(raw_mission_id)[:8]`, a core read-path producer),
  `cli/commands/agent/mission.py:772` (`raw_mid[:8]`), `cli/commands/mission_type.py:643`
  (`…_id_meta[:8]`), `cli/commands/agent/workflow.py:292` (`mid[:8]`),
  `retrospective/generator.py:112` (`mid[:8]`). → **~15 route-sites.**
- **#1993 RETIRED from this rider.** The lanes-path is already centralized in `persistence.py`
  (`read_lanes_json`/`require_lanes_json`); a `resolve_lanes_dir` seam would be a **second authority =
  C-001 violation**. #1993's real target is the coord-aware `_lanes_feature_dir` fallback in `implement()`
  → **deferred to 3.2.2**.
- **#2000 re-targeted:** real compose sites are `core/mission_creation.py:321` + `core/worktree.py:367/370`
  (route through `mission_dir_name`/`worktree_dir_name`), NOT `recovery.py`/`detection.py`.
- **#1888 is a real P1 bug** (no existence check in `ownership/validation.py`), not verify-and-close.
- **#1899-tail = duplicate-of-#2000** (#1899 closed in PR #2001); **#1900 deferred** (coord write-side).
- **5 byte-parity landmines** (two seam contracts: `mid8()` raises vs `resolve_mid8()` returns `""`) —
  `status/aggregate.py`, `dashboard/scanner.py`, `doctor.py:3070/3162`, `implement.py:386` need
  `resolve_mid8`/`or None`, not bare `mid8()`. Per-site contract table required (FR-008).
- **Operator directive (FR-010):** the 3.2.0 **failover mechanic** (`resolve_mid8`/`resolve_transaction_mid8`/
  `resolve_mission_branch` + one-shot legacy-failover warning) is the **entrypoint** routing must use; the
  ratchet forbids bypassing it. Realize via (a) formalize+ratchet-enforce [recommended] or (b) refactor
  `mid8()` to internal so the failover resolver is the only public door.

**Corrected net scope:** ~15 route-sites (via the failover entrypoint) · #2000 compose-routing (2 sites) ·
#1888 real fix · #1971-tail verify-close · ratchet (new AST detector + bypass rule) · failover-entrypoint
formalization. **Dropped/deferred:** #1993, #1900, #1899-tail. No new authority; no write-side; no
`ExecutionContext` builder change.
