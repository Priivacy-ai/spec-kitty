# Call-Site / Bypass Inventory — Read-Path / Error-Fidelity Adoption

**Mission:** `read-path-error-fidelity-adoption-01KV8NPC`
**Author:** architect-alphonso (profile-loaded; DIR-001 one-owning-module, DIR-003 decision-documented, DIR-031 bounded-context translation, DIR-032 conceptual alignment)
**Date:** 2026-06-16
**HEAD:** `87697e5e4` (`v3.2.0-…`; mission spec/meta commits only — code == prior HEAD behavior)
**Mode:** READ-ONLY. No production code edited. Every line:cite verified against HEAD; drift corrected in §6.

> **Framing (binding, from spec + alphonso-systemic + debbie):** the typed authority
> `resolve_action_context → ExecutionContext / ActionContextError` ALREADY EXISTS and is correct
> (`resolution.py:689`). The six failing commands fail because they (a) **flatten** its typed error or
> (b) hold a **second authority** wrapping it. **C-001: adopt, do not build.**

---

## 1. Classification table — every relevant call-site

Legend for the disposition column:
- **(a) route-through-resolver** — already consumes `resolve_action_context`; GOOD citizen, the model others copy.
- **(b) fragment-adopt** — holds the resolved `ExecutionContext` but reads the wrong fragment / re-derives a value the context already carries.
- **(c) compose/parse** — derives a path/value ad-hoc that should come from the resolver primitive.
- **(d) bypass-to-fix** — catches+reclassifies the typed error, OR runs a parallel second authority. The fixes.

| # | Call-site | file:line (HEAD) | Routes resolver? | Disposition | Owning file |
|---|-----------|------------------|------------------|-------------|-------------|
| C1 | `query_current_state` (next query mode) — catches `ActionContextError`, raises `MissionNotFoundError(slug)` | `src/runtime/next/runtime_bridge.py:3128-3130` + `:3132-3134` | YES (calls it) | **(d) bypass-to-fix** — drops `.code`+`checked_paths` (FR-001/002) | `runtime_bridge.py` |
| C2 | `answer_decision_via_runtime` — catches `ActionContextError`, raises `MissionRuntimeError`, logs only "not found" | `runtime_bridge.py:3265-3274` | YES | **(d) bypass-to-fix** — same flatten, decision-answer path | `runtime_bridge.py` |
| C3 | `_find_mission_slug` (next handle canon) — catches `StatusReadPathNotFound`, raises `MissionNotFoundError(raw_handle)` | `src/specify_cli/cli/commands/next_cmd.py:355-361` | partial (read primitive) | **(d) bypass-to-fix** — drops `exc.error_code` + checked-paths msg (FR-001) | `next_cmd.py` |
| C4 | `_run_query_mode` — emits MISSION_NOT_FOUND envelope; has no `error_code`/`checked_paths` from the resolver to emit | `next_cmd.py:467-491` + emitter `:374-408` | n/a (sink) | **(b) fragment-adopt** — must surface the typed code/paths C1/C3 are told to preserve | `next_cmd.py` |
| C5 | `agent context resolve` — routes resolver, JSON-emits `error_code=exc.code` | `src/specify_cli/cli/commands/agent/context.py:135-142` + `:156-161` | YES | **(a) route-through-resolver** — REFERENCE pattern; no change | `agent/context.py` |
| C6 | `decision open` → `_resolve_repo_root_and_slug` — walk-up-to-`kitty-specs/` root + escape-check, THEN `resolve_feature_dir_for_mission` | `src/specify_cli/cli/commands/decision.py:86-97` (walk) + `:101-109` (escape) + `:103` (resolver) | YES, but wrapped | **(d) bypass-to-fix** — second authority anchors escape-check on PRIMARY base; rejects coord path (FR-003) | `decision.py` |
| C7 | `decision verify` → same `_resolve_repo_root_and_slug` + then `resolve_mission_read_path` directly | `decision.py:408` + `:425` | YES | **(c) compose/parse** — second authority shared with C6; folds out once C6's helper is fixed | `decision.py` |
| C8 | `setup-plan` → `_find_feature_directory(…, explicit_feature=None)` hard-raises `--mission required` | `agent/mission.py:2054-2059` (call) → `:1250-1252` (raise) | YES (when handle given) | **(d) bypass-to-fix** — no exact-one auto-select before raise (FR-004) | `agent/mission.py` |
| C9 | `is_committed` — checks coord-ref then `HEAD` of `git_cwd`; **no primary-target-branch leg** | `src/specify_cli/missions/_substantive.py:330-339` (coord) + `:341-355` (HEAD) | n/a (git primitive) | **(d) bypass-to-fix** — add target-branch leg (FR-005) | `missions/_substantive.py` |
| C10 | `is_committed` caller in setup-plan — passes `placement` but spec_file is the coord-resolved `feature_dir` path | `agent/mission.py:2112-2116` | YES (placement) | **(b) fragment-adopt** — should also pass the primary target-branch surface | `agent/mission.py` |
| C11 | `_commit_to_branch` → `safe_commit` `CalledProcessError`/`RuntimeError` "nothing to commit" → returns None silently | `agent/mission.py:1180-1197` (handlers); fn def `:1120` | YES (placement) | **(d) bypass-to-fix** — surface failed auto-commit; report real hash (FR-006) | `agent/mission.py` |
| C12 | `resolve_canonical_root` — `.git` FILE non-worktree pointer → `continue` walks UP into parent repo | `src/specify_cli/core/paths.py:284-288` | n/a (root authority) | **(d) bypass-to-fix** — submodule boundary stop + `.kittify`/`kitty-specs` check (FR-007) | `core/paths.py` |
| C13 | `locate_project_root` — already stops at submodule via per-candidate `.kittify` check (#1944/#1965) | `core/paths.py:99-131` (esp. `:122-131`) | n/a (root authority) | **(a) — already correct**; C12 must AGREE with it | `core/paths.py` |
| C14 | `agent action implement` — re-resolves `resolve_workspace_for_wp` AFTER claim, then again after create; "no workspace resolved" | `src/specify_cli/cli/commands/agent/workflow.py:1341` + `:1377-1381` | YES (target branch `:969`) | **(b) fragment-adopt** — consume the claim's resolved context, single resolution path (FR-008/#1832) | `agent/workflow.py` |
| C15 | `finalize-tasks` → `_find_feature_directory` (coord-aware) for reads; re-anchors writes via `primary_feature_dir_for_mission` | `agent/mission.py:2754-2758` (read) + `:1865-1867` (write re-anchor) | YES | **(b) fragment-adopt** — `require_exists=True` pre-read can fail-closed on materialized-empty coord BEFORE primary read (#11/#1718) | `agent/mission.py` |
| C16 | `ExecutionContext` — mutable `@dataclass`; substrate `target_branch`/`branch_name` set independently of frozen `branch_ref` | `src/mission_runtime/context.py:184` (class) + builder `resolution.py:739,747,804` | n/a (the SSOT) | **(d) bypass-to-fix** — build-time invariant + immutability (FR-009) | `mission_runtime/context.py` + `resolution.py` |
| C17 | `charter status/sync` collectors — `generate_all()` + `ensure_charter_bundle_fresh()` inside read-only status | `src/specify_cli/cli/commands/charter/_status_collectors.py:36-42` | n/a | **(d) bypass-to-fix** — side-effect-free + JSON-safe normalized hash (FR-010, no-op slice of #1914) | `charter/_status_collectors.py` |

---

## 2. Typed-error flow trace — the fidelity-loss points (FR-001/002)

`ActionContextError(code, message)` is defined at **`resolution.py:62-71`** — carries `.code` (str) and the
message; the message is where the resolver embeds checked-path text. It is RAISED with a typed code at:
`:103` (`FEATURE_CONTEXT_UNRESOLVED`), `:134/:436/:668` (boundary-translated `exc.error_code` from
`StatusReadPathNotFound` — typically `STATUS_READ_PATH_NOT_FOUND`), `:705` (`INVALID_ACTION`), `:771/:779`
(`WORK_PACKAGE_UNRESOLVED`), `:794` (`CANONICAL_STATUS_UNREADABLE`), `:136` (`FEATURE_CONTEXT_UNRESOLVED`
with the checked-handle text). **The code + checked-path message are intact at the resolver boundary.**

**Fidelity is lost at exactly three downstream catch-sites — all in the `next` family:**

1. **`runtime_bridge.py:3128-3130`** (`query_current_state`):
   `except ActionContextError as exc: raise MissionNotFoundError(mission_slug) from exc`.
   `MissionNotFoundError.error_code` is the constant `"MISSION_NOT_FOUND"` (`runtime_bridge.py:254`). The
   resolver's `exc.code` (e.g. `STATUS_READ_PATH_NOT_FOUND`) and its checked-path message are **discarded**
   — only chained on `__cause__`, never surfaced. **This is bug #15, the P0.** `next` is the primary agent
   entrypoint and it reports a read-path miss as a missing mission.

2. **`runtime_bridge.py:3265-3274`** (`answer_decision_via_runtime`): same flatten into `MissionRuntimeError`
   with a hand-written "not found" string; `exc.code` dropped. Lower blast radius (answer path) but same class.

3. **`next_cmd.py:355-361`** (`_find_mission_slug`): `except StatusReadPathNotFound as exc: raise
   MissionNotFoundError(raw_handle) from exc`. This catches the *raw* read-primitive error (one layer below
   `ActionContextError`) and flattens it to `MISSION_NOT_FOUND` before the resolver ever runs. `exc.error_code`
   dropped.

**The sink** (`next_cmd.py:374-408` `_emit_mission_not_found_error` + `:467-491` `_run_query_mode`) can ONLY
emit what it is handed. Today it hard-codes `error_code: "MISSION_NOT_FOUND"` (`:395`). The
`QueryModeValidationError` branch (`:474-491`) already preserves `error_code`+`next_step` (the #1911 repair) —
**that is the template**: the `MissionNotFoundError` branch must carry the resolver's real `.code` and
checked-paths and emit them the same way.

**Cheapest high-leverage cut (alphonso, confirmed):** preserve `ActionContextError.code` + checked-paths
across C1/C2/C3 (give `MissionNotFoundError` an optional `resolver_code`/`checked_paths`, OR stop collapsing
and let a typed envelope through). Closes #12/#14/#15 with **zero resolver change**. C5 (`agent context
resolve`) already does this — copy it.

> **DIR-031 note:** the fix is pure error-translation at a boundary; it adds NO new error type (C-001).
> `ActionContextError` stays the one type; the consumers stop *narrowing* it.

---

## 3. The six named commands — route vs. second-authority

| Command | Verdict | Pin |
|---------|---------|-----|
| `next` (query/advance) | routes resolver, **flattens error** | `runtime_bridge.py:3122` routes; `:3128-3134` flattens. Fix = C1/C2/C3. |
| `agent context resolve` | **fully adopts + preserves code** | `agent/context.py:135` + `:158`. No fix — the reference. |
| `setup-plan` | routes resolver, **hard `--mission`** | `agent/mission.py:2054` → `_find_feature_directory:1250-1252` raises `--mission <slug> is required` on empty handle. No exact-one auto-select. Fix = C8. |
| `finalize-tasks` | routes resolver, **fail-closed pre-read on coord edge** | `agent/mission.py:2754` (`require_exists=True` via `_find_feature_directory:1258-1263`); writes correctly re-anchored at `:1865-1867`. Fix = C15. |
| `decision open` | **dual authority** | `decision.py:86-97` walk-up + `:101-109` escape-check (primary base) wrap `resolve_feature_dir_for_mission` (`:103`, which DOES route `resolve_action_context` via `feature_dir_resolver.py:50-67`). The escape-check rejects the coord-worktree path the resolver legitimately returns. Fix = C6. |
| `agent action implement`+`review` | routes target-branch, **re-resolves workspace** | `workflow.py:969` routes target via resolver; `:1341`/`:1377` re-call `resolve_workspace_for_wp` instead of consuming the claim's context → `:1380` "no workspace could be resolved". Fix = C14. |

**`decision.py` dual authority — DEFINITIVE (DIR-031):** the second authority is NOT a second resolver. It is
the **root-determination + escape-validation** in `_resolve_repo_root_and_slug` (`decision.py:57-119`):
`repo_root` is derived by a private 20-level walk to `kitty-specs/` (`:86-97`), then the resolved mission dir
is asserted to live under `repo_root/kitty-specs/` (`:101-109`). Because `resolve_feature_dir_for_mission`
returns a **coord-worktree** path (`.worktrees/<slug>-coord/kitty-specs/…`) while `repo_root` is the
**primary** checkout, the `startswith(base)` check at `:105` fails → `"Mission path would escape kitty-specs/"`.
Two anchors (primary base vs coord resolved path), one decision — the textbook bounded-context leak.
**Fix:** delete the escape-walk for *resolved* paths; keep path-traversal rejection on the **raw operator
token only** (the `_SAFE_SLUG_RE` at `:79` already does this — it is sufficient). Then `repo_root` should come
from the canonical root authority, not a private walk. `cmd_verify` (C7) shares the helper, so the fix lands
once.

**`setup-plan` hard `--mission` — DEFINITIVE:** drift-corrected to `:1250-1252` (spec said 1248-1250). The
raise is inside the **shared** `_find_feature_directory` — which is ALSO used by `finalize-tasks` (C15) and
others. **Do NOT add auto-select inside `_find_feature_directory`** (it would change behavior for every caller,
including ones that intend to require explicit selection). Add exact-one resolution **in `setup_plan` only**,
before the call: enumerate `kitty-specs/*` (substantive missions), and if exactly one, pass it as
`explicit_feature`; if >1, let the existing structured `MISSION_AMBIGUOUS_SELECTOR`/detection-error path fire
(`agent/mission.py:2060-2070`). This keeps the no-overlap boundary clean and matches FR-004's "no silent
fallback".

---

## 4. The two root resolvers (FR-007)

Both live in `core/paths.py` (one owning module — DIR-001 already satisfied for *location*, not *behavior*):

- **`locate_project_root`** (`:99-133`): per-candidate logic. For a `.git` FILE it follows ONLY worktree
  pointers (`:110`), and CRUCIALLY runs a per-candidate `.kittify` directory check (`:122-131`, current-first)
  — so inside a submodule it **stops at the submodule root**. Patched by #1944/#1965. **CORRECT on submodule.**
- **`resolve_canonical_root`** (`:247-292`): for a `.git` FILE, if `_read_worktree_gitdir(git_path) is None`
  (submodule / separate-git-dir → not worktree topology) it executes `continue` (`:285-288`) — **no `.kittify`
  / `kitty-specs` boundary check, no submodule stop** — and walks UP until it hits the parent repo's `.git`
  DIRECTORY (`:280-282`), returning the **parent repo**. **WRONG on submodule.**

**Divergence pin:** submodule `.git` FILE → `locate_project_root` returns the submodule; `resolve_canonical_root`
returns the parent. Debbie reproduced this live (`econcept-next` parent / `elissar-api` submodule). The live
guard `assert_initialized` (`src/specify_cli/workspace/assert_initialized.py`) calls `resolve_canonical_root`,
NOT `locate_project_root` — so the #1944/#1965 fix never covers the real specify/plan/tasks path. **This is
why #6 still fires on a binary that contains the fix.**

**Fix (C12):** at `paths.py:284-288`, before `continue` on a non-worktree `.git` pointer, treat the candidate
directory as a boundary — if `candidate/.kittify` or `candidate/kitty-specs` exists, return it; else (and/or)
stop ascent at the submodule boundary. Mirror `locate_project_root`'s `:122-131` logic so the two AGREE
(NFR-001 behavioral equivalence). **No new authority** — harden the existing one to match its sibling.

**#1971 / #2011 relation:** #2011 pins *this* resolver (`resolve_canonical_root`); #1971 is a separate 3-way
`locate_project_root` consolidation. They are siblings, NOT the same fix — #1971 alone does not close FR-007.
Note in matrix; do not conflate.

---

## 5. `is_committed` / `_commit_to_branch` (FR-005/006)

**`is_committed`** (`_substantive.py:286-355`): the legs it checks, in order —
1. **Coord ref leg** (`:330-339`): `git cat-file -e {coord_ref}:{tree_path}` — only when `placement.kind ==
   COORDINATION`.
2. **HEAD leg** (`:341-355`): `ls-files --error-unmatch` + `cat-file -e HEAD:{tree_path}` against `git_cwd`.

`git_cwd` comes from `_git_commit_check_context` (`:263-283`): if the file is under `.worktrees/<name>/`, it
returns the **worktree root** — so for a coord-resolved `feature_dir`, `git_cwd` is the **coord worktree** and
HEAD is the **coord branch**. **MISSING leg:** the **primary target-branch** ref. When the spec is committed on
`main`/the target branch but the coord branch lacks it (coord created before the spec, or spec auto-committed
to primary), BOTH legs miss → `spec_committed: false` on a genuinely-committed spec (debbie repro `/tmp/debbie7c`).

**Fix (C9):** add a target-branch leg — `git -C <primary_repo_root> cat-file -e {target_branch}:{primary_tree_path}`
— ORed with the existing legs. The check must run against the **primary** repo root with the **primary**
tree-path (not the worktree-relative one). Caller C10 (`agent/mission.py:2112-2116`) must supply the
target-branch surface (it already has `target_branch` from `_show_branch_context`). Emit diagnostics listing
every ref/surface checked (the issue's own fix direction).

**`_commit_to_branch`** (`agent/mission.py:1120`, handlers `:1180-1197` — drift-corrected; spec said 1178-1195):
- `CalledProcessError` with "nothing to commit"/"nothing added to commit" in stderr → `_print_artifact_unchanged`
  + `return` (`:1183-1186`). **Silent benign-swallow.**
- `RuntimeError` empty-changeset AND `_artifact_has_no_git_changes` → same swallow (`:1192-1194`).
- Other errors → `_warn_commit_failed` + `raise` (correct).

The silent-swallow is the #7 secondary trigger: when a coord-destined commit no-ops against the wrong worktree
(placement resolution fell back), the artifact stays untracked and the function reports nothing — `commit_created:
None` + untracked `plan.md`. **Fix (C11):** distinguish "genuinely unchanged" (artifact present & committed at
the resolved placement) from "no-op against wrong surface" (artifact NOT present at placement). The former may
stay benign; the latter MUST surface a typed diagnostic. On success, report the real commit hash (the function
returns `None` today — give it a typed result or thread the hash into the caller's `commit_created`).

---

## 6. Line-number drift corrections (spec said X, HEAD is Y)

| Reference | Spec / research said | HEAD (verified) | Note |
|-----------|----------------------|-----------------|------|
| `resolve_action_context` def | `resolution.py:682` | **`:689`** | (`:682` is mid-docstring of `resolve_placement_only`) |
| `ExecutionContext` builder split-brain | `resolution.py:793-801` | substrate set at **`:739,:747`** (`target_branch`), WP fields at **`:800-808`** (`branch_name` at `:804`) | the "793-801" window is now the lane-read try/except; the mutation moved. **`branch_name` is the WP LANE branch, NOT `branch_ref.target_branch`** — see §7 semantic correction. |
| `next` collapse | `runtime_bridge.py:3128-3134` | **EXACT** `:3128-3134` | confirmed |
| `next_cmd` consume | `next_cmd.py:469-473` | **EXACT** `:469-473` | confirmed (+ second collapse at `:355-361` not in spec) |
| `decision open` escape-check | `decision.py:86-107` | walk **`:86-97`**, escape **`:101-109`** | in `_resolve_repo_root_and_slug` (`:57`), used by `cmd_open` via `:231` |
| `decision` canonical resolver | `decision.py:425` | **`:425`** but inside **`cmd_verify`**, NOT `cmd_open` | `cmd_open` routes via `resolve_feature_dir_for_mission` (`:103`); both share the dual-authority helper |
| `setup-plan` `--mission` raise | `agent/mission.py:1248-1250` | **`:1250-1252`** | inside shared `_find_feature_directory` |
| `is_committed` | `missions/_substantive.py` (no line) | def **`:286`**, legs **`:330-339`/`:341-355`** | confirmed surface-blind |
| `_commit_to_branch` swallow | `agent/mission.py:1178-1195` | def **`:1120`**, swallow **`:1180-1197`** | the 1178-1195 window is mid-function |
| `resolve_canonical_root` submodule | `core/paths.py:284-288` | **EXACT** `:284-288` | confirmed `continue` |
| `ExecutionContext` | `context.py:184` | **`:184`** | confirmed mutable `@dataclass` |

---

## 7. Semantic correction on FR-009 (architect verdict — load-bearing for the plan)

FR-009 / the research say "fix the split-brain at `resolution.py:793-801` where `branch_name` can diverge from
`branch_ref.target_branch`." **This conflates two semantically-distinct fields.** On HEAD:

- `context.target_branch` (substrate, `context.py:206`) and `branch_ref.target_branch` (fragment, `:128`) are
  BOTH assigned from the **single** `target_branch` variable resolved once at `resolution.py:721` (substrate
  `:744`, fragment via `_assemble_core_fragments` `:723`). **They are already equal at build time.**
- `context.branch_name` (substrate, `:212`, default `None`) is set at `resolution.py:804` from
  `wp_workspace.branch_name` — the **WP LANE branch** (`kitty/mission-…-lane-a`). This is a DIFFERENT concept
  from the mission target branch and is **expected** to differ. Demanding `branch_name == branch_ref.target_branch`
  would be wrong.

**The real in-authority residual is two-fold and both are valid FR-009 work:**
1. **Mutability** — `ExecutionContext` is a plain `@dataclass` (`:184`) while every fragment is `frozen=True`.
   A consumer CAN mutate `target_branch` post-build, diverging it from the frozen `branch_ref.target_branch`.
   **Harden = freeze the composite** (or `field(init=False)` + a single assembly), so the build-time equality
   `context.target_branch == branch_ref.target_branch` is an invariant that cannot be broken downstream.
2. **Post-freeze substrate assignment** — `:800-808` mutate WP fields after the fragments are frozen. The
   builder should assemble the WP-bearing context in one shot (or via a `replace`-style immutable update),
   asserting `context.target_branch == branch_ref.target_branch` at construction (reject on mismatch — the
   "single declared rule").

**Recommended FR-009 rule (decide in plan):** **reject**, not normalize. Assert
`context.target_branch == branch_ref.target_branch` at build; raise `ActionContextError("CONTEXT_INVARIANT_VIOLATION", …)`
if violated. Normalizing would hide a builder bug. Freezing the dataclass makes the assertion permanent.
**This is the cheapest safe grain;** it does NOT require retiring the flat substrate (a larger #1619 grain that
should stay deferred). **Flag for the operator:** the spec's "branch_name == branch_ref.target_branch" wording
should be re-stated as "target_branch substrate == branch_ref.target_branch + immutability" in the plan.

---

## 8. #1993 / #1716 sizing (C-005 carry-vs-defer recommendation)

### #1993 — `resolve_lanes_dir()` pure seam

**Current state:** NO `resolve_lanes_dir` function exists (`grep` = 0 hits). The lanes-dir is derived ad-hoc as
`feature_dir / LANES_FILENAME` inside `lanes/persistence.py` (`:43`, `:78`) and `workspace/context.py`
(`:798`), keyed on whatever `feature_dir` the caller resolved. Per the #2007 binding note it **MUST NOT land
alone** — it pairs with #1832 (C14) or carries minimal adoption.

**Bounded read-side adoption that fits THIS mission?** YES, minimally:
- Extract a 1-function pure seam `resolve_lanes_dir(feature_dir) -> Path` in `lanes/persistence.py` (≈6-10 LOC
  incl. docstring) and route the 2-3 ad-hoc derivations through it.
- **Sizing:** ~15-25 LOC, 2-3 files (`lanes/persistence.py`, `workspace/context.py`), **LOW risk** (pure path
  composition, no topology semantics). Tests: 1 focused unit test on the seam (~20 LOC).
- **Recommendation: CARRY (minimal).** It is genuinely low-cost, satisfies the co-dependency by riding with
  C14 (#1832), and removes the last ad-hoc lanes-dir derivation so the resolver-adoption story is complete.
  Owned by the same IC as C14 (workspace) to avoid a cross-file collision.

### #1716 — write-side coord topology authority root

**Surface size:** `coordination/transaction.py` (1176 LOC) + `surface_resolver.py` (569) + `workspace.py` (349)
= ~2094 LOC of write-side topology mechanics. This is a **large** redesign surface (the alphonso capstone /
#1878 strangler).

**Is ANY bounded slice required for read-path behavioral-equivalence?** **NO.** Every FR-001..FR-009 read-path
fix is achievable on the READ side without touching write-side topology:
- #6/FR-007 is a root-resolver fix (`core/paths.py`), not topology.
- #7/FR-005 reads an additional ref leg; #6/FR-006 surfaces a swallow — neither restructures placement.
- #8/FR-003 deletes a consumer-side escape-check; #11/#15 are read-anchor/fail-closed fixes.
- #1832/FR-008 consumes the already-resolved context — no new write authority.
The single write-adjacent edge is #11's "placement vs input" split (C15), and that is handled as **read-side
adoption** (anchor reads on `primary_root`), NOT a topology rework.

- **Recommendation: DEFER.** Pulling any #1716 slice would re-blow the scope the operator deliberately parked
  and violate C-001's "no new authority." The read-path behavior is made equivalent across input classes
  entirely on the read/error side. **Risk of carrying even a slice: HIGH** (2094-LOC surface, write-durability
  semantics, idempotency invariants — NFR-005 conflict-surface explosion). Keep it on #1878.

**Net C-005 verdict: CARRY #1993 (minimal, ~20 LOC, pairs with C14). DEFER #1716 entirely.**

---

## 9. Proposed no-overlap ownership partition for ICs

Shared-surface collision risk is concentrated in **`agent/mission.py`** (C8, C10, C11, C15) and
**`runtime_bridge.py`** (C1, C2). The partition below assigns each shared file to ONE IC and groups by concern
so no two ICs edit the same file (NFR-005 bounded conflict surface; DIR-001 one-owner-per-concern).

| IC | Concern | Owns (files) | Call-sites | FRs |
|----|---------|--------------|------------|-----|
| **IC-A — Typed-error pass-through (`next` family)** | error fidelity | `runtime_bridge.py`, `next_cmd.py` | C1, C2, C3, C4 | FR-001, FR-002, (#1911) |
| **IC-B — `decision` single authority** | bounded-context escape-check | `decision.py` | C6, C7 | FR-003 |
| **IC-C — `mission.py` planning entry** (setup-plan + finalize-tasks + commit) | mission-entry adoption | **`agent/mission.py`** (SOLE owner), `missions/_substantive.py` | C8, C9, C10, C11, C15 | FR-004, FR-005, FR-006, (#11) |
| **IC-D — Root resolver unification** | root authority | `core/paths.py` | C12, C13 | FR-007 |
| **IC-E — implement/workspace single resolution** | workspace adoption | `agent/workflow.py`, `lanes/persistence.py`, `workspace/context.py` | C14, **#1993 seam** | FR-008, FR-011 (#1993) |
| **IC-F — ExecutionContext builder-hardening** | the SSOT invariant | `mission_runtime/context.py`, `mission_runtime/resolution.py` | C16 | FR-009 |
| **IC-G — Charter status no-op** | side-effect-free read | `charter/_status_collectors.py` | C17 | FR-010 |

**Why this partitions cleanly:**
- **`agent/mission.py` is the one true collision risk** — C8/C10/C11/C15 all live in it. Assigning ALL of them
  to **IC-C** (one IC, "planning entry adoption") removes the collision. IC-C also owns `_substantive.py` since
  C9 (is_committed) is the read-leg half of C10's caller change — same concern, must move together.
- **IC-F (the SSOT) is sequenced FIRST or alongside IC-A/IC-E** — the adoption spine assumes a trustworthy
  context. But it touches only `mission_runtime/` so it never collides with the consumer ICs. Its build-time
  invariant (target_branch equality) is a precondition the consumers rely on.
- **IC-E carries #1993** because the lanes-dir seam lives in `workspace/`+`lanes/`, the same surface as C14's
  workspace re-resolution — natural co-ownership, satisfies the co-dependency.
- **`branch_naming.py` is OUT** (prior naming-rider mission #2012) — no IC touches it. Confirmed: none of the
  fixes above require lane-branch NAME composition, only consumption of already-resolved values.

**Sequencing (DIR-003 decision):** IC-F (invariant) → IC-A (error pass-through, cheapest, closes #12/#14/#15) →
IC-C / IC-D / IC-E / IC-B (parallel; disjoint files) → IC-G (independent, anytime). IC-A and IC-F are the safe
lead.

---

## 10. Executive summary (8 lines)

1. **IC partition (7 lanes, zero file-overlap):** IC-A `next`-error-passthrough (`runtime_bridge.py`+`next_cmd.py`); IC-B `decision` single-authority (`decision.py`); IC-C planning-entry — setup-plan+finalize+is_committed+commit, SOLE owner of `agent/mission.py`+`_substantive.py`; IC-D root-resolver (`core/paths.py`); IC-E implement+#1993 (`workflow.py`+`workspace/`+`lanes/persistence.py`); IC-F ExecutionContext invariant (`mission_runtime/`); IC-G charter no-op (`_status_collectors.py`).
2. **The one collision risk is `agent/mission.py`** — all four of its call-sites (C8/C10/C11/C15) are assigned to a single IC-C to keep the conflict surface bounded (NFR-005).
3. **#1993 → CARRY (minimal):** the `resolve_lanes_dir` seam does NOT exist yet; extract ~20 LOC and route the 2-3 ad-hoc `feature_dir/lanes.json` derivations, owned by IC-E alongside #1832 (satisfies the co-dependency). LOW risk.
4. **#1716 → DEFER entirely:** ~2094 LOC write-side surface; NO slice is required for read-path behavioral-equivalence (every FR is achievable read-side). Carrying it violates C-001 and explodes the conflict surface. Keep on #1878.
5. **Typed-error fidelity loss is exactly THREE catch-sites, all in `next`:** `runtime_bridge.py:3128-3130`, `:3265-3274`, `next_cmd.py:355-361` — each drops `ActionContextError.code`+checked-paths into `MISSION_NOT_FOUND`. `agent context resolve` (`context.py:158`) already preserves the code — copy it. Closes #12/#14/#15 with zero resolver change.
6. **`decision open` is NOT a second resolver** — it is a primary-anchored escape-check (`decision.py:101-109`) wrapping the correct coord-aware resolver; the fix DELETES the escape-walk for resolved paths, keeping `_SAFE_SLUG_RE` traversal-rejection on raw tokens only (DIR-031).
7. **Two root resolvers diverge on submodule:** `locate_project_root` stops at the submodule (`.kittify` check `:122-131`); `resolve_canonical_root` `continue`s up to the parent (`:284-288`) — the live `assert_initialized` guard uses the BROKEN one, so the #1944/#1965 fix never covered #6.
8. **SURPRISE / spec correction (FR-009):** the spec's "`branch_name` ≠ `branch_ref.target_branch`" conflates two fields — `branch_name` is the WP LANE branch (expected to differ). The real residual is (a) `ExecutionContext` mutability + (b) the post-freeze substrate write; the invariant to assert is `context.target_branch == branch_ref.target_branch` (already equal at build), enforced by FREEZING the composite. Recommend **reject-on-mismatch**, not normalize. Re-word in the plan.
