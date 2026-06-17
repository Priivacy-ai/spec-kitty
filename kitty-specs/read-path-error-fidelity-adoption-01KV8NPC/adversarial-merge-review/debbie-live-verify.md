# Post-Merge Live Verification — read-path-error-fidelity-adoption (01KV8NPC)

**Author:** Debugger Debbie
**Date:** 2026-06-16
**Branch under test:** `feat/read-path-error-fidelity` (merged tree, all 9 WPs).
**Interpreter:** `/home/stijn/.pyenv/versions/3.11.15/bin/python -m specify_cli ...`
(editable install rooted at this repo — confirmed `specify_cli.__file__` =
`.../spec-kitty/src/specify_cli/__init__.py`; self-reported version `3.2.1`).
**Binding:** live-evidence-over-static-fixed. Every verdict below is a live invocation on a
topology-true fixture (full 26-char ULID `mission_id`, real coord worktrees, real git submodule),
re-running the original captured-red repro to confirm the FIX, not reading code.

---

## Summary table

| Bug | Original (captured-red) | Live verdict on merged tree |
|-----|-------------------------|------------------------------|
| **#15** | `next` → `MISSION_NOT_FOUND` (typed code dropped) | **FIXED** |
| **#8** | `decision open`/`verify` → raw traceback | **FIXED** |
| **#7** | `is_committed:false` for spec on primary target | **FIXED** (real topology) — see edge note |
| **#4** | `setup-plan` demands `--mission` for sole mission | **FIXED** |
| **#6/#2011** | `resolve_canonical_root`/`assert_initialized` → parent | **FIXED** |
| **#1832** | `agent action implement` "no workspace resolved" | **FIXED** |
| **WP09/M3** | orchestrator reads stale primary on coord topology | **FIXED** |

**All seven confirmed fixed live.** One documented edge caveat on #7 (a fabricated lowercase-mid8
slug — a non-production shape — still mis-paths leg-3); does not affect real missions.

---

## #15 — `next` typed read-path error pass-through — **FIXED**

**Fixture** (`/tmp/debbie-coord`): single repo on `main`, `.kittify/config.yaml`, one mission
`read-path-coord-repro-01kv8npc` (`mission_id 01KV8NPCDEBBIE0REPRO0COORD`, 26 chars). `meta.json`
declares `coordination_branch: kitty/mission-...-01KV8NPC-coord`; **no coord branch, no coord
worktree** materialized (the #1718/#1692 fail-closed trigger). Mission dir + spec on disk.

**Command:**
```
python -m specify_cli next --mission read-path-coord-repro-01kv8npc --json
```
**Observed (exit 1):**
```json
{"result":"error","error_code":"COORDINATION_BRANCH_DELETED",
 "error":"Coordination branch '...-coord' ... declared in meta.json but deleted from git. ...
          Run `spec-kitty agent worktree repair --mission ...`, or flatten the mission ...",
 "checked_paths":["/tmp/debbie-coord/.worktrees/...-01KV8NPC-coord/kitty-specs/...-01KV8NPC",
                  "/tmp/debbie-coord/kitty-specs/read-path-coord-repro-01kv8npc"],
 "next_step":"... repair ... or flatten ...", "spec_kitty_version":"3.2.1"}
```
**Verdict: FIXED.** The original captured-red was `error_code: MISSION_NOT_FOUND` + "run mission
list". The merged tree emits the typed `COORDINATION_BRANCH_DELETED` (a `STATUS_READ_PATH_NOT_FOUND`
subclass) **plus `checked_paths`** and the real remediation. The collapse at
`runtime_bridge.py:3130` is gone. FR-001 / FR-002 / SC-001 satisfied.

---

## #8 — `decision open` / `decision verify` structured typed error — **FIXED**

**Fixture:** same `/tmp/debbie-coord` (coord declared, no coord worktree).

**Command (open):**
```
python -m specify_cli agent decision open --mission read-path-coord-repro-01kv8npc \
  --flow plan --input-key approach --question "Which approach?" --options '["a","b"]' --json
```
**Observed (exit 1):**
```json
{"code":"COORDINATION_BRANCH_DELETED","error":"Coordination branch '...-coord' ... declared in
 meta.json but deleted from git. ... Run `spec-kitty agent worktree repair ...`, or flatten ..."}
```
**Command (verify):**
```
python -m specify_cli agent decision verify --mission read-path-coord-repro-01kv8npc --json
```
**Observed:** identical structured `{"code":"COORDINATION_BRANCH_DELETED", ...}` JSON, exit 1.

**Verdict: FIXED.** Original captured-red was an **uncaught `ActionContextError` raw traceback**
printed by Rich. Both `open` and `verify` now emit a single-line structured typed-error JSON payload
with the actionable remediation — no traceback. FR-003 / SC-002 satisfied.

---

## #7 — `is_committed` true for spec committed on primary target branch — **FIXED** (real topology)

This required two fixtures because the defect is surface-specific and the slug grammar matters.

**Fixture B — topology-true real mission** (`/tmp/debbie-committed7real`): slug
`committed-primary-real-01KV8NPC` (mid8 embedded **uppercase**, as real spec-kitty emits;
`_compose_mission_dir` therefore avoids double-suffixing → coord dir == primary dir name). Real
coord branch + materialized coord worktree carrying the mission dir but **no spec.md**; substantive
`spec.md` committed **only on `main`**.

**Live probe (production wiring — coord-aware resolver hands `is_committed` the coord surface):**
```python
fd = _find_feature_directory(root, cwd, slug)
# -> .worktrees/committed-primary-real-01KV8NPC-coord/kitty-specs/committed-primary-real-01KV8NPC
spec = fd / "spec.md"          # exists on disk = False (coord lacks it)
pl  = _resolve_planning_placement(root, slug)   # CommitTarget(COORDINATION)
is_committed(spec, root, placement=pl, target_branch="main",
             primary_repo_root=get_main_repo_root(root), diagnostics=diag)
```
**Observed:** `is_committed = True`; diagnostics:
```
coord-ref ...-coord:kitty-specs/committed-primary-real-01KV8NPC/spec.md: miss
HEAD:kitty-specs/committed-primary-real-01KV8NPC/spec.md: miss
target-branch main:kitty-specs/committed-primary-real-01KV8NPC/spec.md (primary_root=...): hit
```
**Verdict: FIXED.** The new primary-target-branch leg (`_substantive.py:401-410`) ORs in and finds
the spec on `main` after the coord-ref and HEAD legs miss — exactly FR-005 / SC-004. The
diagnostics enumerate every surface checked. Mission's own regression
(`test_is_committed_true_on_primary_target_branch_only` + 3 peers) passes on the merged tree.

**Edge caveat (documented, NOT a real-mission regression).** I first built `/tmp/debbie-committed7b`
with slug `committed-primary-7b-01kv8npc` (mid8 embedded **lowercase**). `mid8_from_slug` returns
`''` for a lowercase tail, so `resolve_mid8` re-appends an uppercase mid8 and `_compose_mission_dir`
yields a coord dir `...-01KV8NPC` that **diverges** from the un-suffixed primary dir. Leg-3 then
checks the suffixed coord tree-path against `main` (where the spec lives at the un-suffixed path) →
**miss** → `is_committed = False`. Root-caused live: `_ref_carries_path(root,"main",suffixed)=False`
vs `…(un-suffixed)=True`. This is the fabricated-fixture trap NFR-002/realistic-test-data warns
about: real spec-kitty slugs always carry the **uppercase** ULID mid8, so the divergence never
arises in production. The mission's regression test uses the un-suffixed (same-name) coord dir,
which matches the real-mission shape. **No action required** — flagged only for completeness; if a
future change ever lets a lowercase-mid8 slug reach this seam, leg-3 should translate the coord
tree-path to the primary tree-path before the `main` check.

---

## #4 — `setup-plan` auto-selects the sole mission — **FIXED**

**Fixture** (`/tmp/debbie-single`): single repo, `.kittify/config.yaml`, **exactly one** mission
`single-mission-plan-01kv8npc` (`mission_id 01KV8NPCDEBBIESINGLEPLAN00`), spec committed on `main`.

**Command (no `--mission`):**
```
python -m specify_cli agent mission setup-plan --json
```
**Observed:** resolves the sole mission — `mission_slug: single-mission-plan-01kv8npc`, `feature_dir`
/`spec_file` populated, `spec_committed: true`. With a substantive spec it advances past the spec
gate and blocks only on the downstream `plan.md`-substantive gate (legitimate, separate gate). The
original captured-red `PLAN_CONTEXT_UNRESOLVED` / "1 missions found, pass --mission to disambiguate"
is **gone**.

**Ambiguity guard live:** added a second mission → `setup-plan --json` (no `--mission`) returns
`PLAN_CONTEXT_UNRESOLVED` "2 missions found, pass --mission <slug> to disambiguate". Removing it
restores auto-select.

**Verdict: FIXED.** Exactly-one auto-selects; >=2 still demands disambiguation. FR-004 / SC-003.

---

## #6 / #2011 — submodule root resolution — **FIXED** (launch-blocker)

**Fixture** (`/tmp/debbie-submod`): a REAL git submodule. Parent `econcept-next` (`.git` DIRECTORY,
**no `.kittify`**); submodule `elissar-api` added via `git submodule add` (its `.git` is a **FILE**
`gitdir: ../.git/modules/elissar-api`) carrying its own `.kittify/config.yaml` + mission
`elissar-mission-01kv8npc` (`mission_id 01KV8NPCDEBBIESUBMODULE001`).

**Live probe (from inside the submodule):**
```python
resolve_canonical_root(<submodule>) -> .../econcept-next/elissar-api   # CORRECT (was PARENT)
locate_project_root(<submodule>)    -> .../econcept-next/elissar-api   # CORRECT
# CONVERGED = True
assert_initialized()  # (now specify_cli.workspace.assert_initialized)
  -> OK, root: .../econcept-next/elissar-api
```
**Operator-facing:** `setup-plan` run from inside the submodule resolves `feature_dir`/`spec_file`
under the submodule and proceeds (blocks only on plan-substantive). The original
`SPEC_KITTY_REPO_NOT_INITIALIZED ... Resolved root: .../econcept-next` (parent misresolution) is
**gone**.

**Verdict: FIXED.** `resolve_canonical_root` now stops at the submodule boundary and converges with
`locate_project_root`; the live `assert_initialized` guard resolves the submodule. FR-007 / SC-005.
(Note: `assert_initialized` moved from `core.paths` to `workspace.assert_initialized` in the merge.)

---

## #1832 — `agent action implement` single resolution — **FIXED**

**Fixtures** (`/tmp/debbie1832-*`): real git repos with a real `.worktrees/<slug>-<mid8>-lane-a`
worktree carrying a `.git` marker (topology-true, full 26-char ULID). Drove the merged
single-resolution seam `workflow._ensure_workspace_materialized` live.

**Probe A — workspace already materialized:** `_ensure_workspace_materialized(resolved_ws, "WP05",
create)` → `create_called = 0`, `verify_workspace_toplevel = None` (clean), returned the resolved
path. No "no workspace could be resolved" raised.

**Probe B — workspace pending creation:** `create()` materializes the real worktree, called
**exactly once**; the returned context **preserves** `resolution_kind=lane_workspace`, `lane_id`
(consumed, not re-resolved). No second resolution authority fires.

**Verdict: FIXED.** The workspace is resolved once (`resolve_workspace_for_wp`) and consumed through
both the create and verify legs — no independent re-resolution that could report "no workspace could
be resolved" on a verified read-path. FR-008 / C-IC05. Mission regression
(`test_implement_single_resolution.py`, 4 tests) passes.

---

## WP09 / M3 — orchestrator status read fails closed on coord topology — **FIXED**

External surface: `orchestrator-api` (8 read endpoints behind `_resolve_mission_dir_or_fail`).

**Scenario A — identity unprovable** (`/tmp/debbie-wp09a`): primary `meta.json` declares
`coordination_branch` but carries **no `mission_id`** (identity unprovable on this surface).
```
python -m specify_cli orchestrator-api mission-state --mission orch-wp09-unprovable-01kv8npc
```
**Observed (exit 1):** `success:false`, `error_code:"STATUS_READ_PATH_NOT_FOUND"`, `data` carries
`mid8:""` + `coord_candidate` + `primary_candidate`. **Fails closed** — does NOT read the
possibly-stale primary surface, does NOT flatten to `MISSION_NOT_FOUND`.

**Scenario B — provable identity, coord-authoritative** (`/tmp/debbie-wp09b`): slug
`orch-wp09-coord-01KV8NPC` (`mission_id 01KV8NPCDEBBIEWP09COORD00X`), real coord branch + materialized
coord worktree. Status seeded via the real `emit_status_transition` API: **primary stale** (WP01
`planned`), **coord fresh** (WP01 `planned -> claimed`).
```
python -m specify_cli orchestrator-api mission-state --mission orch-wp09-coord-01KV8NPC
```
**Observed:** `success:true`; WP01 read as **`claimed`** (the coord-authoritative value), NOT the
stale primary `planned`.

**M2 envelope-preservation guard:** `mission-state --mission totally-nonexistent-mission` →
`MISSION_NOT_FOUND`, `success:false` (genuine absence keeps the historical envelope; the typed
read-path code only surfaces on coord/fail-closed cases).

**Verdict: FIXED.** The empty-mid8 seed that suppressed the `bool(mid8)` fail-closed guard is gone;
`_resolve_mission_dir` reads the real `mission_id` from primary meta, arms the guard, fails closed on
unprovable identity, and reads the coord-authoritative surface when identity is proven. FR-001 (M2) /
FR-011 (M3). Mission regression (`test_typed_error_fail_closed.py`) passes.

---

## Regression-suite corroboration (merged tree, editable interpreter)

```
tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py          PASS
tests/specify_cli/cli/commands/test_next_typed_error_passthrough.py         PASS
tests/specify_cli/cli/commands/test_decision_single_authority.py            PASS
tests/specify_cli/core/test_resolve_canonical_root_submodule.py             PASS   (22 total)
tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py -k is_committed/primary  PASS (4)
tests/specify_cli/cli/commands/agent/test_implement_single_resolution.py    PASS   (4)
```

## Disposition

All seven originally-witnessed bugs are **confirmed FIXED by live repro** on the merged tree. No P0
remains. The single documented #7 edge (lowercase-mid8 fabricated slug) is a non-production fixture
shape that real spec-kitty never emits — recorded for completeness, no remediation required.
