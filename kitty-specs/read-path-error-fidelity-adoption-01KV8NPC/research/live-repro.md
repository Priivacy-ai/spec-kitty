# Live Repro on HEAD — read-path / error-fidelity adoption (01KV8NPC)

**Author:** Debugger Debbie
**Date:** 2026-06-16
**Repo HEAD:** `87697e5e4` (`git describe` = `v3.2.0-108-g87697e5e4`).
**CRITICAL TOOLING NOTE:** the `spec-kitty` on `$PATH` is a **pipx install pinned at 3.2.0rc44**
(`/home/stijn/.local/share/pipx/venvs/spec-kitty-cli/...`), NOT current HEAD. The editable HEAD
install lives in the **pyenv 3.11.15** interpreter
(`/home/stijn/.pyenv/versions/3.11.15/bin/python`, editable project location =
this repo). All repros below were run with that interpreter via
`python -m specify_cli ...` so they exercise **current HEAD source**, confirmed by tracebacks
landing in `/home/stijn/Documents/.../spec-kitty/src/...`. (The internal version constant still
self-reports `3.2.0rc45` — it lags the tag — but the source under test is HEAD.)

**Method:** Live invocation against real, topology-true fixtures with full 26-char ULID
`mission_id`, real coordination worktrees, and a real git submodule (`.git` FILE). Each typed
error was additionally traced by calling the resolver directly to capture the `code` the operator
never sees.

---

## #15 (P0) — `next` collapses the typed read-path error into `MISSION_NOT_FOUND`

**Topology built** (`/tmp/debbie-coord`): a single git repo on `main`, `.kittify/config.yaml`
present, one mission `read-path-coord-repro-01kv8npc` (`mission_id`
`01KV8NPCDEBBIE0REPRO0COORD`, 26 chars). Its `meta.json` declares
`coordination_branch: kitty/mission-...-01KV8NPC-coord` but **no coord branch and no coord
worktree are materialized** — the #1718/#1692 fail-closed trigger. The mission dir and spec exist
on disk.

**Exact command:**
```
cd /tmp/debbie-coord
python -m specify_cli next --mission read-path-coord-repro-01kv8npc --json
```

**Observed output (exit 1):**
```json
{
  "result": "error",
  "error_code": "MISSION_NOT_FOUND",
  "handle": "read-path-coord-repro-01kv8npc",
  "next_step": "Run 'spec-kitty mission list' to see available missions, then re-run with a valid handle (attempted: 'read-path-coord-repro-01kv8npc').",
  "remediation": "Run 'spec-kitty mission list' ...",
  "spec_kitty_version": "3.2.0rc45"
}
```

**Typed error the resolver actually produced (live trace of `resolve_action_context`):**
```
ActionContextError code= COORDINATION_BRANCH_DELETED
message= Coordination branch '...-coord' ... declared in meta.json but deleted from git.
         Run `spec-kitty agent worktree repair --mission ...`, or flatten the mission by
         removing the `coordination_branch` key from meta.json ...
```

**Verdict: REPRODUCES-ON-HEAD.** The resolver emits a precise, actionable typed error
(`COORDINATION_BRANCH_DELETED`, a `STATUS_READ_PATH_NOT_FOUND` subclass) with the real remediation,
and `next` discards ALL of it and substitutes `MISSION_NOT_FOUND` + "run mission list" — which
points the operator the wrong way (the mission is not missing; the read-path is broken).

**Confirmed failing code path:**
`src/runtime/next/runtime_bridge.py:3130` — `query_current_state` catches `ActionContextError`
and does `raise MissionNotFoundError(mission_slug) from exc`, dropping `.code` + the message.
Surfaced at `src/specify_cli/cli/commands/next_cmd.py:469-470` (`except MissionNotFoundError` →
`_emit_mission_not_found_error`). Validates **FR-001 / FR-002, SC-001**.

---

## #8 — `decision open` rejects a valid coord-aware handle (uncaught typed error)

**Topology built:** same `/tmp/debbie-coord` fixture (coord declared, no coord worktree).

**Exact command:**
```
cd /tmp/debbie-coord
python -m specify_cli agent decision open --mission read-path-coord-repro-01kv8npc \
  --flow plan --input-key approach --question "Which approach?" --options '["a","b"]' --json
```

**Observed output (exit non-zero):** a **raw Python traceback** — an uncaught
`ActionContextError` (code `COORDINATION_BRANCH_DELETED`, `from CoordinationBranchDeleted` /
`StatusReadPathNotFound`) printed by Rich, NOT a structured `--json` error payload.

**Verdict: REPRODUCES-ON-HEAD — with a correction to the prior triage.** The prior
`debbie-repro-triage.md` predicted the symptom would be the escape-check `"Mission path would
escape kitty-specs/"` at `decision.py:105-107`. On the binary, the **live failure is different and
worse**: the escape-check is *never reached* because `_resolve_repo_root_and_slug` first calls
`resolve_feature_dir_for_mission(...)` at `decision.py:103`, which calls `resolve_action_context`,
which **raises `ActionContextError` uncaught** → operator sees a stack trace, not a typed error.

**Confirmed failing code path:**
`src/specify_cli/cli/commands/decision.py:103` (`resolved = resolve_feature_dir_for_mission(...)`)
→ `src/specify_cli/missions/feature_dir_resolver.py:60` (`resolve_action_context`)
→ `src/mission_runtime/resolution.py:436` (`raise ActionContextError(exc.error_code, str(exc))`).
No `try/except ActionContextError` wraps the call in `cmd_open` / `_resolve_repo_root_and_slug`.
Validates **FR-003, SC-002** (single-authority adoption + typed-error pass-through). Note: the
escape-check at `decision.py:105-107` is still the dead second authority FR-003 wants deleted; it
is simply masked by the earlier crash.

---

## #7 — `spec_committed:false` while the spec IS committed on the primary target branch

**Topology built** (`/tmp/debbie-committed7b`): mission `committed-primary-7b-01kv8npc`
(`mission_id` `01KV8NPCDEBBIECOMMIT7B0000`). `meta.json` declares the coordination branch; a real
coord branch AND coord worktree are materialized (`.worktrees/...-01KV8NPC-coord`). The coord
worktree contains the mid8-suffixed mission dir (`kitty-specs/<slug>-01KV8NPC/`) but **no
spec.md**. The substantive `spec.md` is committed **only on `main` (the primary target branch)**;
the coord branch lacks it. Verified: `main:.../spec.md` = present, `coord:.../spec.md` = absent.

**Exact probe (live `is_committed` against the resolved surface):**
```python
fd = _find_feature_directory(repo_root, cwd, "committed-primary-7b-01kv8npc")
# -> /tmp/debbie-committed7b/.worktrees/...-01KV8NPC-coord/kitty-specs/<slug>-01KV8NPC   (COORD surface)
pl = _resolve_planning_placement(repo_root, slug)   # CommitTargetKind.COORDINATION
is_committed(fd/"spec.md", repo_root, placement=pl)  # -> False
```
**Observed:** `is_committed(...) = False` even though the spec is genuinely committed on `main`.
End-to-end `setup-plan` on this topology returns `error_code: SPEC_FILE_MISSING` /
`feature_dir = <coord surface>`.

**Verdict: REPRODUCES-ON-HEAD.** The mechanism is exactly FR-005: `is_committed`
(`src/specify_cli/missions/_substantive.py:286`) has only two legs —
(1) coord-ref `git cat-file -e {coord_ref}:{tree_path}` (`:333`) and
(2) HEAD `git cat-file -e HEAD:{tree_path}` against `git_cwd` (`:349`, which for a coord-resolved
path is the coord worktree's HEAD = the coord branch). **There is no leg that checks
`{target_branch}:{tree_path}` on the primary target branch.** When the read-path's coord-priority
hands `is_committed` the coord artifact path and the spec lives only on the primary target branch,
both legs miss and the gate reports `False`.

> Caveat (honest scoping): when the coord worktree does NOT contain the mission dir,
> `_find_feature_directory` resolves to the **primary** dir and `is_committed` then passes
> (`spec_committed:true`) — verified on `/tmp/debbie-committed`. So the false-negative is
> **surface-specific**: it requires the coord worktree to carry the mission dir while the spec is
> committed only on primary. A fabricated single-repo fixture masks it (the exact trap NFR-002
> warns about). The regression test MUST build the coord-worktree-with-mission-dir topology.

**Confirmed failing code path:** `src/specify_cli/missions/_substantive.py:330-372` (no
primary-target-branch leg); caller wiring at `src/specify_cli/cli/commands/agent/mission.py:2076`
(`spec_file = feature_dir/"spec.md"` from the coord-aware `_find_feature_directory`) and `:2116`
(`is_committed(spec_file, repo_root, placement=_spec_placement)`). Validates **FR-005, SC-004**.

### #7 secondary — `_commit_to_branch` no commit-hash, silent benign-swallow

**Verdict: PARTIAL (REPRODUCES as a contract/diagnostic gap).**
`src/specify_cli/cli/commands/agent/mission.py:1120` `_commit_to_branch(...) -> None` — confirmed
return annotation `None` (live `inspect.signature`). **Success never reports the real commit
hash** (FR-006: "success MUST report the real commit hash" → VIOLATED). The benign no-op paths
(`:1165` `_artifact_has_no_git_changes`, `:1180-1184` "nothing to commit", `:1192-1194` empty
changeset) return via `_print_artifact_unchanged` with **no `commit_created` value** propagated to
the JSON contract; the plan caller (`:2195`) does not capture a hash. On HEAD the *hard*-failure
swallow is already fixed — real `CalledProcessError`/`RuntimeError` now `_warn_commit_failed` +
`raise` (`:1186-1188`, `:1196-1198`). So FR-006 is half-done: errors surface, but success/no-op
still emit no typed `commit_created`. Validates **FR-006** (residual = report the hash + a typed
no-op/diagnostic in JSON).

---

## #4 — `setup-plan` hard-requires `--mission` in a single-mission repo

**Topology built** (`/tmp/debbie-single`): single git repo, `.kittify/config.yaml`, **exactly
one** mission `single-mission-plan-01kv8npc` (`mission_id` `01KV8NPCDEBBIESINGLEPLAN00`), no coord
topology, spec committed on `main`.

**Exact command:**
```
cd /tmp/debbie-single
python -m specify_cli agent mission setup-plan --json     # (no --mission — as the help example shows)
```

**Observed output:**
```json
{"error_code": "PLAN_CONTEXT_UNRESOLVED", "mission_flag": null,
 "error": "1 missions found, pass --mission <slug> to disambiguate",
 "available_missions": ["single-mission-plan-01kv8npc"],
 "example_command": "spec-kitty agent mission setup-plan --mission single-mission-plan-01kv8npc --json",
 "remediation": "Re-run with --mission <slug>"}
```

**Verdict: REPRODUCES-ON-HEAD.** With exactly one mission present, `setup-plan` refuses to
auto-select it and demands `--mission`, contradicting its own `--help` example
(`spec-kitty agent mission setup-plan --json`).

**Confirmed failing code path:**
`src/specify_cli/cli/commands/agent/mission.py:1252` — `_find_feature_directory` raises
`FEATURE_CONTEXT_UNRESOLVED "--mission <slug> is required"` when no handle is given (no exact-one
branch). The error builder `_build_setup_plan_detection_error` then unconditionally emits the
disambiguate message even when `n == 1` (`:1332`). Validates **FR-004, SC-003**.

---

## #6 / #2011 (launch-blocker) — submodule root misresolution in `resolve_canonical_root`

**Topology built** (`/tmp/debbie-submod`): a REAL git submodule.
- Parent repo `econcept-next` (its own `.git` DIRECTORY), **no `.kittify`**.
- Submodule `elissar-api` added via `git submodule add` → its `.git` is a **FILE**
  (`gitdir: ../.git/modules/elissar-api`), and it carries its own `.kittify/config.yaml` + a
  mission `elissar-mission-01kv8npc` (`mission_id` `01KV8NPCDEBBIESUBMODULE001`).

**Exact probe (live, run from inside the submodule):**
```python
resolve_canonical_root(<submodule>)  -> /tmp/debbie-submod/econcept-next        # PARENT — WRONG
locate_project_root(<submodule>)     -> /tmp/debbie-submod/econcept-next/elissar-api  # correct
```

**Operator-facing live impact (the specify/plan/tasks guard):**
```python
assert_initialized()   # from inside the submodule
# raises SpecKittyNotInitialized:
#   SPEC_KITTY_REPO_NOT_INITIALIZED: ... Resolved root: /tmp/debbie-submod/econcept-next
#   Missing: /tmp/debbie-submod/econcept-next/.kittify/config.yaml
```

**Verdict: REPRODUCES-ON-HEAD (launch-blocker confirmed).** Exactly Robert's symptom. The two
root authorities diverge: `locate_project_root` was patched (#1944/#1965) and stops at the
submodule, but `resolve_canonical_root` — the one the live `assert_initialized` guard uses — walks
UP into the parent.

**Confirmed failing code path:**
`src/specify_cli/core/paths.py:284-288` — for a submodule `.git` FILE, `_read_worktree_gitdir`
returns `None` (non-worktree pointer) → executes `continue` (`:287` "keep walking so an enclosing
repo is still resolved"), ascending past the submodule with **no `.kittify`/`kitty-specs` boundary
check and no submodule-boundary stop**, landing on the parent (whose `.git` is a directory,
`:280-282`). Validates **FR-007, SC-005**.

---

## #1827 (RE-TEST-FIRST) — `spec-kitty merge` post-merge baseline ordering

**Issue (Priivacy-ai/spec-kitty #1827, OPEN):** `spec-kitty merge` completes the merge, then
errors `baseline_merge_commit is missing from committed meta.json on main`. The validation ran
*before* the tool wrote the field; re-running re-merges and fails identically (circular,
unrecoverable except by manual meta.json edit).

**Topology built** (`/tmp/debbie1827-*`, real git repo): modern mission
`merge-baseline-repro-01kv8npc` (`mission_id` `01KV8NPCDEBBIE1827REPRO000`), meta.json initially
WITHOUT `baseline_merge_commit`. I drove the **exact HEAD merge sequence** with the real helpers:
1. `_record_baseline_merge_commit(fdir, target_baseline, mission_id)` (merge.py:2574)
2. bookkeeping commit (carries meta.json to target)
3. `_assert_baseline_merge_commit_on_target(...)` (merge.py:2741)
then the **resume/re-run trigger**: advance HEAD past the baseline and re-run record+assert.

**Observed:**
- Step 3 assert: **PASSED.**
- Resume re-record kept the original baseline (idempotent — did not overwrite with the advanced
  HEAD); resume assert: **PASSED.**

**Falsification guard (proves the harness is real, not a false negative):** running the helpers in
the BROKEN order (assert BEFORE the bookkeeping commit lands the field on target) produced the
**exact #1827 error string**: `"...baseline_merge_commit is missing from committed
kitty-specs/.../meta.json on main..."`. So the harness detects the failure mode; HEAD simply does
not trigger it.

**Verdict: DOES-NOT-REPRODUCE on HEAD.** The ordering is structurally fixed: the assert
(`merge.py:1705`, called at `:2741`) reads the **recorded** baseline from working meta.json
(`_recorded_baseline_from_working_meta`) rather than the re-derived HEAD, and
`_record_baseline_merge_commit` (`merge.py:1580`) is idempotent — together they neutralize both
the original ordering bug and the resume circularity. The in-code comment at `merge.py:2733-2739`
documents this fix explicitly. Existing unit suite `tests/merge/test_merge_done_recording.py`
(30 tests) passes on HEAD.

**FR-012 verdict (RECORD THIS):** #1827 is **verified-already-fixed**. Scope = **regression test
only, NO code fix.** The regression test should drive the full record→commit→assert sequence on a
real modern-mission repo INCLUDING the resume/re-run path (HEAD advanced past baseline), asserting
no `BaselineMergeCommitError`. A pure-unit assertion is insufficient — it must exercise the
ordering end-to-end so a future reordering regression is caught (the falsification guard above is
the shape).

---

## Summary table

| Bug | Reproduces on HEAD? | Validates FR | Failing path (file:line on HEAD) | Regression-test topology (TDD-first) |
|-----|---------------------|--------------|----------------------------------|--------------------------------------|
| **#15** (P0) | **REPRODUCES** | FR-001 / FR-002 (SC-001) | `runtime_bridge.py:3130` collapse → `next_cmd.py:469-470` emit | Single repo + mission with `coordination_branch` declared, NO coord worktree (fail-closed). Assert `next --json` returns the typed read-path code (not `MISSION_NOT_FOUND`). |
| **#8** | **REPRODUCES** (as uncaught crash, not escape-check) | FR-003 (SC-002) | `decision.py:103` → `feature_dir_resolver.py:60` → `resolution.py:436` (uncaught `ActionContextError`) | Same coord-declared-no-worktree topology. Assert `agent decision open` returns a structured typed error, not a traceback; delete escape-check at `decision.py:105-107`. |
| **#7** | **REPRODUCES** | FR-005 (SC-004) | `_substantive.py:330-372` (no primary-target leg); caller `mission.py:2076,2116` | Coord worktree materialized WITH mission dir; spec committed on `main` only, absent on coord branch. Assert `is_committed(resolved_coord_spec, COORD) == True`. |
| **#7 sec.** | **PARTIAL** | FR-006 | `mission.py:1120` (`-> None`, no hash); no-op paths `:1165,1180,1192` | Force a commit no-op + a forced failure; assert success reports a real `commit_created` hash and a typed no-op/error in JSON. |
| **#4** | **REPRODUCES** | FR-004 (SC-003) | `mission.py:1252` (hard-require) + `:1332` (n==1 still disambiguates) | Repo with EXACTLY one mission. Assert `setup-plan --json` (no `--mission`) auto-selects it; ≥2 still errors `MISSION_AMBIGUOUS_SELECTOR`. |
| **#6 / #2011** (launch-blocker) | **REPRODUCES** | FR-007 (SC-005) | `core/paths.py:284-288` (`continue` past submodule) | REAL git submodule (`.git` FILE, `gitdir: ../.git/modules/<name>`) with `.kittify` in the submodule, none in parent. Assert `resolve_canonical_root(submodule) == submodule == locate_project_root(submodule)`. |
| **#1827** | **DOES-NOT-REPRODUCE** | FR-012 | (fixed: `merge.py:1705`/`:2741` read recorded baseline; `:1580` idempotent) | Real modern-mission repo; drive record→commit→assert + resume (HEAD advanced past baseline); assert no `BaselineMergeCommitError`. Test-only. |

---

## Explicit #1827 call-out

**#1827 DOES NOT reproduce on HEAD.** The exact merge ordering (record at `merge.py:2574` →
bookkeeping commit → assert at `:2741`) succeeds, and the original circular trigger (re-run/resume
after HEAD advanced past the baseline) also passes because the assert compares against the
**recorded** baseline and `_record_baseline_merge_commit` is idempotent. My falsification harness
reproduced the exact #1827 error string under the broken ordering, so the negative result is
trustworthy, not a missed repro. **FR-012 disposition: verified-already-fixed — write a
regression test (full record→commit→assert + resume), do NOT write a code fix.** Do not write a
"fiction" fix test pretending the ordering bug is live.
