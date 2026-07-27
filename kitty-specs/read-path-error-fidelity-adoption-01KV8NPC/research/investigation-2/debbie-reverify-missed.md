# Investigation-2 — Re-verify on current tree + Missed-surface hunt

**Author:** Debugger Debbie (profile-loaded: five-paradigm lens; pragmatic)
**Date:** 2026-06-16
**Repo HEAD:** `bb3d74399` (`Flatten read-path mission topology (remove stale coordination_branch; resolver reads primary)`)
**Binary under test:** editable HEAD at `/home/stijn/Documents/_code/SDD/fork/spec-kitty`, exercised via
`/home/stijn/.pyenv/versions/3.11.15/bin/python -m specify_cli …`.
**Tooling fidelity (CHANGED vs investigation-1):** the editable interpreter now reports **`Version: 3.2.1`**
(`pip show spec-kitty-cli` → `Editable project location: …/spec-kitty`). Every live repro below printed
`"spec_kitty_version": "3.2.1"` in its payload, proving the source under test is current HEAD (investigation-1
ran rc44/rc45). `src/specify_cli/__init__.py` is the imported module.
**Tree movement accounted for:** the naming-rider (8 commits, `26a2a7670…b76473d5d`) and `#2004`
(`9ddb91c81 docs: consolidate learnings…(#2004)` — **docs only**) both landed. The C3 merge.py routing
(`primary_feature_dir_for_mission`) landed via `aa9ec6392`/`78024bd48` (#1956/#1972), NOT #2004 itself.
**Method:** topology-true /tmp fixtures — full 26-char ULID `mission_id`, real coord branch+worktree, REAL git
submodule (`.git` FILE). Cleaned up after.

---

## 1. Re-verification table (all 5 bugs + #1827)

| Bug | Reproduces on HEAD (3.2.1)? | Changed vs inv-1? | Failing file:line confirmed live |
|-----|------------------------------|-------------------|----------------------------------|
| **#15** (P0) — `next` collapses typed read-path → `MISSION_NOT_FOUND` | **YES — REPRODUCES** | No (identical) | `runtime_bridge.py:3128-3130` (`except ActionContextError → raise MissionNotFoundError`). Live: `next --json` emitted `MISSION_NOT_FOUND` + "run mission list"; resolver actually produced `COORDINATION_BRANCH_DELETED` + real repair remediation. Surfaced at `next_cmd.py:374-408`/`:467-491`. |
| **#8** — `decision open` uncaught typed error | **YES — REPRODUCES** (raw traceback) | No | `decision.py:103` → `feature_dir_resolver.py` → `resolution.py:436` (`raise ActionContextError`). Live: Rich-printed stack trace ending at `resolution.py:436`, NOT a `--json` payload. Escape-check at `decision.py:105-107` still present but masked by the earlier crash. |
| **#7 primary** — `spec_committed:false` while committed on primary target branch | **YES — REPRODUCES** (mechanism confirmed) | No | `_substantive.py:330-339` (coord leg) + `:341-355` (HEAD leg) — **still only two legs, no primary-target-branch leg**. Caller `agent/mission.py:2116`. |
| **#7 secondary** — `_commit_to_branch` no hash + benign-swallow | **PARTIAL** (as before) | No | `agent/mission.py:1120` def `-> None` (no hash); benign no-op swallows `:1166/:1185/:1193`; hard-failures correctly `raise` `:1190/:1197`. FR-006 still half-done. |
| **#4** — `setup-plan` hard-requires `--mission` with exactly one mission | **YES — REPRODUCES** | No | `agent/mission.py:1252` (`_find_feature_directory` raises `--mission required`) + builder `:1332` unconditional "disambiguate" even at `n==1`. Live: `{"error_code":"PLAN_CONTEXT_UNRESOLVED","error":"1 missions found, pass --mission <slug> to disambiguate"}`. |
| **#6 / #2011** (launch-blocker) — submodule root misresolution | **YES — REPRODUCES** | No | `core/paths.py:284-288` (`continue` past non-worktree `.git` FILE, no `.kittify`/submodule stop). Live (real submodule): `resolve_canonical_root(sub)=…/econcept-next` (PARENT, wrong) vs `locate_project_root(sub)=…/elissar-api` (correct). Operator impact: `assert_initialized()` raised `SPEC_KITTY_REPO_NOT_INITIALIZED: Resolved root: …/econcept-next`. |
| **#1827** — merge baseline ordering | **DOES-NOT-REPRODUCE** (unchanged) | No | Structurally fixed: `merge.py:1705`/`:2741` read recorded baseline; `:1580` idempotent. FR-012 = regression-test only. |

**Net:** every prior verdict holds on the current tree. The naming-rider and #2004/#1956/#1972 landings did
**not** alter any of the five failing paths — line numbers are byte-stable. No #1827-style "already-fixed"
surprise among the five (the only already-fixed item remains #1827 itself).

---

## 2. Robert's #2004 / merge.py C3 fix — verify-don't-redo

**What landed & what it fixes (live-traced via git history):**
- `#2004` (`9ddb91c81`) is a **docs-only** consolidation commit — no merge.py code.
- The merge.py `primary_feature_dir_for_mission(...)` routing is in two `fix(merge)` commits:
  `aa9ec6392` "stage merge bookkeeping from target checkout" (**#1956**) and
  `78024bd48` "persist target bookkeeping" (**#1972**).
- Behavior fixed: the final merge **bookkeeping commit** runs from `main_repo` onto the target branch, so it
  must stage **primary-checkout** status paths even when the topology-aware `status_feature_dir` points at the
  coordination worktree. `_target_bookkeeping_status_paths` (`merge.py:785-789`) re-anchors to
  `primary_feature_dir_for_mission(main_repo, slug)` **iff** the status dir is `is_under_worktrees_segment`;
  `_assert_status_path_within_target_surface` (`merge.py:803-817`) rejects bookkeeping paths that escape the
  primary mission surface. This is a real witnessed bug (#1956/#1972: status events staged from the wrong
  checkout / outside the target surface).

**Overlap with our ICs:** **NONE.** `merge.py` is not owned by any of the 7 ICs (IC-A..IC-G). The only merge.py
touch in our scope is the #1827 FR-012 **test-only** assessment. `primary_feature_dir_for_mission` is the
**canonical read primitive our fixes CONSUME** — C15 already re-anchors finalize-tasks writes through the same
function (`agent/mission.py:1865-1867`). Robert's routing is the *correct single-authority adoption pattern*
applied to the merge bookkeeping seam — i.e. the same thing this mission preaches, on a surface we don't own.

**Verdict: VERIFY-DON'T-REDO — nothing to re-implement.** Do not touch `merge.py`. Treat Robert's
`primary_feature_dir_for_mission` routing as an exemplar of the adoption pattern (alongside C5
`agent context resolve`), not as IC scope.

---

## 3. MISSED SURFACES table (operator's explicit ask)

Broad greps run: `except ActionContextError` (8 sites), `except StatusReadPathNotFound` (13 sites),
`MISSION_NOT_FOUND`/`MissionNotFoundError(`, `KITTY_SPECS_DIR /` + `.parents`/`.parent` root-walks,
`resolve_canonical_root` (consumers), `is_committed`, and the naming-rider `resolve_mid8` consumers (29 sites).

| # | New surface | file:line | FR/IC | Reproduces? | Disposition |
|---|-------------|-----------|-------|-------------|-------------|
| **M1** | `resolve_context` (`spec-kitty context mission-resolve`) catches `ActionContextError` → raises `FeatureNotFoundError("…Check that the mission slug is correct.")` — drops `exc.code` (`COORDINATION_BRANCH_DELETED`/`STATUS_READ_PATH_NOT_FOUND`) + checked-paths + remediation | `src/specify_cli/context/resolver.py:162-169` | **NET-NEW** (#15 class; IC-A scopes only `next_cmd.py`/`runtime_bridge.py`) | **YES — live** | **NEW WP / extend IC-A.** Same flatten as #15 on a different operator entrypoint. Preserve resolver `.code`+checked-paths (copy C5 / the `agent context.py:88-93` pattern, which already translates correctly). |
| **M2** | `_resolve_mission_dir` (orchestrator-api) catches `StatusReadPathNotFound` → `return None`; all 8 endpoints then `_fail("MISSION_NOT_FOUND", "…not found in kitty-specs/")` — drops `error_code`/`coord_candidate`/`primary_candidate` | `src/specify_cli/orchestrator_api/commands.py:263-266` (helper) + endpoints `:587,:652,:735,:870,:997,:1066,:1164,:1268` | **NET-NEW** (#15 class ×8 on the EXTERNAL orchestrator surface) | **Reachable** (fail-closed window) — confirmed by code path; the live flatten requires the strict coord-materialized-empty window | **NEW WP / extend IC-A.** External-automation surface flattens the typed read-path error 8×. Lower fidelity than #15 (uses the read primitive, never `resolve_action_context`, so it can't even surface `COORDINATION_BRANCH_DELETED`). |
| **M3** | `_resolve_mission_dir` seeds `resolve_mid8(mission_slug, mission_id=None)` → empty `mid8` (`''`), which **suppresses the coord-aware fail-closed branch** (`_read_path_resolver.py:352` `bool(mid8)`); orchestrator-api then reads the **possibly-stale primary** surface without the fail-closed guard every other reader has | `src/specify_cli/orchestrator_api/commands.py:261` (`resolve_mid8(…, mission_id=None)`) | **NET-NEW** — naming-rider-EXPOSED correctness gap (read-path safety, not just error fidelity) | **YES — live** (`resolve_mid8('…', None) == ''`; empty mid8 → fail-closed never evaluates) | **NEW WP (read-path safety).** The orchestrator should resolve the real `mission_id` from meta (like `decision.py:421`/`context.py:73`) before `resolve_mid8`, so coord-aware fail-closed actually fires. Otherwise external automation can read stale status on a coord topology. |
| **M4** | `_find_first_for_review_wp` does its OWN parent-walk + `candidate_feature_dir_for_mission` composition to locate `tasks/` in a worktree, instead of consuming the resolver's surface | `src/specify_cli/cli/commands/agent/workflow.py:2040-2062` | **IC-E** (workspace re-resolution family; DISTINCT call-site from C14's `resolve_workspace_for_wp` at `:1341/:1377`) | Not independently operator-facing (review-mode helper) | **FOLD into IC-E.** Re-deriver bypass; route through the canonical surface. Lower blast radius. |
| **M5** | `decision.py` (C7, `cmd_verify`) does a NEW primary-only `load_meta(repo_root/KITTY_SPECS_DIR/slug)` pre-read at `:420-421` to seed `resolve_mid8` (`:424`), then `resolve_mission_read_path` at `:425` can raise `StatusReadPathNotFound` **uncaught** (no try/except) — same uncaught-crash class as `cmd_open` | `src/specify_cli/cli/commands/decision.py:420-425` | **IC-B** (decision single-authority — already in scope, but the naming-rider ADDED the primary-only pre-read + a 2nd uncaught raise site) | **Reachable** (uncaught raise on coord-deleted, like #8) | **FOLD into IC-B.** When fixing C6/C7, also wrap/translate the `:425` raise and drop the primary-only `:420-421` pre-read (it reads empty meta on a coord-only topology and seeds the wrong mid8). |
| **M6** | `agent/context.py` helper (`_resolve_feature_dir`-style) does a primary-only `load_meta(repo_root/KITTY_SPECS_DIR/raw_handle)` at `:72-73` to seed `resolve_mid8`, BEFORE the canonical `resolve_mission_read_path` | `src/specify_cli/cli/commands/agent/context.py:72-93` | **Watch / NET-NEW (LOW)** — naming-rider pattern | Benign here (resolver is authoritative; the `StatusReadPathNotFound` IS correctly translated at `:88-93`) | **DOCUMENT, no WP.** Error fidelity is GOOD (it raises a typed `ActionContextError` with checked-paths). Flag only as the recurring primary-only-meta-pre-read shape (M3/M5/M6) the rider introduced. |

### Benign-by-design catch-sites (verified, NOT bugs — for the falsified-hypothesis catalog)
- `implement.py:560` (`except ActionContextError: return None`) — placement-filter helper, conservative fallback. OK.
- `agent/mission.py:725` (`except ActionContextError: return None`) — record-analysis placement helper, conservative. OK.
- `mission_type.py:443` (`except StatusReadPathNotFound: return mission_slug`) — slug-canonicalization fallback; runtime surfaces its own diagnostic downstream. OK.
- `coordination/status_transition.py:221` — translates to `exc.primary_candidate` (preserves the signal). OK.
- `status/aggregate.py:339` — translates to typed `CoordAuthorityUnavailable(coord_candidate, primary_candidate)`. OK.
- `status/aggregate.py:470` — falls through to re-surface `CoordAuthorityUnavailable`. OK.
- `mission_runtime/resolution.py:262/430/664` — the resolver itself (boundary translation INTO `ActionContextError`); these are the SOURCE of fidelity, not a flatten. OK.

### Recurring naming-rider shape (M3/M5/M6 — structural note)
The rider standardized `resolve_mid8(handle, mission_id=...)` as the mid8 seam (good). But three consumers
(M3 orchestrator, M5 decision-verify, M6 context-helper) now do a **primary-only `load_meta` pre-read** to seed
`mission_id` *before* the read-path resolver runs. On a coord-only / coord-deleted topology this pre-read returns
empty meta → `mission_id=None`/`''` → `resolve_mid8` declines the tail → **the coord-aware fail-closed branch is
suppressed** (M3 is the live-confirmed harm: orchestrator reads stale primary). This is a small but real
read-path-safety regression-shape the rider introduced. M6 happens to be safe because its resolver call uses
`require_exists=True` and translates the error; M3 is the dangerous one.

---

## 4. Executive summary

- **All 5 bugs still reproduce on the current tree (HEAD `bb3d74399`, editable 3.2.1):** #15 (P0
  `next`→`MISSION_NOT_FOUND` collapse, `runtime_bridge.py:3130`), #8 (`decision open` uncaught traceback,
  `resolution.py:436`), #7 primary (`is_committed` no primary-target leg, `_substantive.py:341-355`), #4
  (`setup-plan` "1 missions… disambiguate", `mission.py:1332`), #6/#2011 (submodule root divergence,
  `paths.py:285-288`; live `assert_initialized` resolved the parent repo). #7-secondary remains PARTIAL.
  Line numbers are byte-stable — the naming-rider and #2004/#1956/#1972 did **not** touch any failing path.
- **No #1827-style surprise:** #1827 remains the only already-fixed item (FR-012 = test-only). Nothing else
  silently fixed by the new landings; conversely the rider exposed a NEW gap (M3).
- **Robert's #2004 merge.py "C3" = #1956/#1972 fix (not #2004 — that's docs).** It routes the merge bookkeeping
  commit through `primary_feature_dir_for_mission` — the same single-read-authority this mission preaches, on a
  surface NO IC owns. **Verify-don't-redo: do not touch merge.py.**
- **Missed surfaces: 6 (2 high-severity NET-NEW WPs, 1 high-severity read-path-safety WP, 2 folds, 1 doc-only).**
  - **HIGH / NET-NEW:** **M1** `context mission-resolve` flattens the typed error → "check the slug"
    (`resolver.py:164`) — live-confirmed, NOT covered by IC-A (which scopes only the `next` family). **New WP or
    extend IC-A.**
  - **HIGH / NET-NEW:** **M2** orchestrator-api flattens `StatusReadPathNotFound`→`MISSION_NOT_FOUND` across **8
    external endpoints** (`commands.py:263-266`). **New WP or extend IC-A.**
  - **HIGH / NET-NEW (read-path SAFETY, not just fidelity):** **M3** orchestrator-api seeds
    `resolve_mid8(..., mission_id=None)`→`''`, suppressing the coord-aware fail-closed guard → external automation
    can read **stale primary status** on a coord topology (live-confirmed empty-mid8 suppression). **New WP.**
  - **FOLD:** **M4** `workflow.py:2040-2062` parent-walk re-deriver → IC-E. **M5** `decision.py:420-425` rider-added
    primary-only pre-read + 2nd uncaught `StatusReadPathNotFound` raise → IC-B.
  - **DOC-ONLY:** **M6** `context.py:72-93` primary-only meta pre-read — error fidelity is fine; note the shape.
