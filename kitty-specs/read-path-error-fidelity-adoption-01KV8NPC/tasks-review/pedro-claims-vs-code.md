# Pedro — claims-vs-code review of the 9 WP prompts

**Lens:** python-pedro / claims-vs-code. Every `file:line` / symbol cite in `tasks/WP0*.md`
verified against actual HEAD (`6fee06d33613e28e9273b541703b372593aa929f`).

**Context that matters:** the prompts were authored against HEAD `87697e5e4`; the tree has since
moved (naming-rider + #2004). The prompts *explicitly hedge* line drift in WP03/WP04/WP05
("treat call-site-inventory §6 as authoritative; re-locate by symbol after WP01"). That hedge is
honest and largely accurate — **but two cites name a symbol/site that does not exist where claimed**,
and those are the ones an implementer trips on.

## Verdict (headline)

- **Wrong/stale refs that matter: 2** (1 wrong-symbol, 1 wrong-file-already-noted-but-listed-once-more
  below for completeness) + a **cluster of benign line drift** in WP03/WP09 that the prompts already
  warn about.
- **Already-done / no-op risk: none.** Every "to fix" site genuinely still exhibits the disease on
  HEAD. `ExecutionContext` is **NOT** frozen (`context.py:184` is bare `@dataclass`), so WP01's
  freeze + `:800-808` mutator deletion is real work. WP08 is correctly dispositioned test-only
  (helpers all present, ordering structurally fixed).
- **Single most misleading reference an implementer would trip on:**
  **WP02 T010 — `next_cmd.py:355-361` `_find_mission_slug`.** That symbol **does not exist in
  `next_cmd.py`**; the real function is **`_resolve_mission_slug`** (def `:323`, collapse
  `raise MissionNotFoundError(raw_handle) from exc` at **`:361`**). `_find_mission_slug` is a
  *different* function living in `agent/status.py:58`. An implementer grepping for
  `_find_mission_slug` in the owned file finds only a comment and could edit the wrong module.

## Verification table

| WP | Cited ref / symbol | Verified? | Corrected (HEAD `6fee06d3`) | Severity |
|----|--------------------|-----------|------------------------------|----------|
| WP01 | `resolution.py:739` single `ExecutionContext(` construction | ✅ | `:739` exact; grep confirms **one** `ExecutionContext(` in `src/mission_runtime/` | — |
| WP01 | `resolve_action_context` site | ✅ | def `:689` (cited inline, not by line) | — |
| WP01 | `build_execution_context` (to-be-created) | ✅ | 0 hits in `src/` — correctly framed as new package-private factory | — |
| WP01 | post-build mutator `:800-808` | ✅ | `:800-808` exact (`context.wp_id=` … `context.workspace_path=`) | — |
| WP01 | alt-cite mutator `:793-801` (T002) | ⚠️ | `:793` is mid try-block; mutator truly `:800-808`. Cosmetic — `:800-808` is the load-bearing cite and is exact | LOW |
| WP01 | `ExecutionContext` mutable on HEAD (T002/T003 premise) | ✅ | `context.py:184` is bare `@dataclass` (NOT frozen) — freeze is genuine work, **not** a no-op | — |
| WP01 | `branch_ref.target_branch` invariant target | ✅ | `BranchRefFragment.target_branch` at `context.py:128` | — |
| WP01 | `create_intent` → `tests/mission_runtime/` | ✅ | dir EXISTS | — |
| WP02 | `runtime_bridge.py:3128-3130` `raise MissionNotFoundError(...) from exc` | ✅ | `raise` at `:3130` exact | — |
| WP02 | `runtime_bridge.py:3265-3274` `answer_decision_via_runtime` | ✅ | `except ActionContextError` `:3265`; raises **`MissionRuntimeError`** (not `MissionNotFoundError`) at `:3273-3275`. Cite range correct; the prompt's "preserve the code identically" is still the right ask | LOW |
| WP02 | **`next_cmd.py:355-361` `_find_mission_slug`** | ❌ | **Wrong symbol.** No `_find_mission_slug` in `next_cmd.py`. Real fn = **`_resolve_mission_slug`** (def `:323`); collapse `raise MissionNotFoundError(raw_handle) from exc` at **`:361`**. `_find_mission_slug` lives in `agent/status.py:58` | **HIGH** |
| WP02 | `next_cmd.py:374-408` emitter | ✅ | `_emit_mission_not_found_error` def `:374`; `MISSION_NOT_FOUND` literal `:395` | — |
| WP02 | `next_cmd.py:474-491` QueryModeValidationError reference branch | ✅ | `except QueryModeValidationError` `:474`; envelope `error_code`/`next_step` `:480-486` | — |
| WP02 | `agent/context.py:158` good-citizen `exc.code` emit | ✅ | `error_code: exc.code` at `:158` exact | — |
| WP02 / M1 | `context/resolver.py:164` flatten | ✅ | `except ActionContextError as exc:` at **`:164` exact**; `raise FeatureNotFoundError(msg)` `:169`. (Prior wrong cite `mission_resolver.py` confirmed: that file has **no** flatten.) | — |
| WP02 | `agent/context.py:88-93` translation pattern | ⚠️ | `StatusReadPathNotFound` translation actually `:90-95` (raise at `:91-95`). ~2-line drift | LOW |
| WP02 | `create_intent` test path | ✅ | `tests/specify_cli/cli/commands/` exists | — |
| WP03 | `_commit_to_branch` def `:1120` | ✅ | `:1120` exact | — |
| WP03 | `_find_feature_directory` raise `:1250-1252` | ⚠️ | def `:1214` (raise is inside; not `:1250`). Re-locate by symbol per the prompt's own hedge | MED |
| WP03 | `_build_setup_plan_detection_error` `:1332` | ❌ | def **`:1300`**; called at `:225`. Stale by ~32 lines | MED |
| WP03 | `setup_plan` call site `:2054-2059`/`:2060-2070`/detection `:2112-2116` | ❌ | `setup_plan` def is **`:1905`** (cited region ~2054+ is past EOF of the function as numbered). All `setup_plan`-internal cites drifted | MED |
| WP03 | `_commit_to_branch` handlers `:1165,:1180-1184,:1192-1194,:1186-1188,:1196-1198` | ⚠️ | real handler calls: `_print_artifact_unchanged` `:1166`, `:1185`, `:1193`; `_warn_commit_failed` `:1189`, `:1196`. Close (±a few lines); the "hard-failure swallow already fixed" claim holds (`_warn_commit_failed` + `raise` present) | LOW |
| WP03 | plan caller `commit_created` `:2195` | ❌ | `commit_created` assigned at `:3759`/`:3819` (and `:3416`). `:2195` is stale | MED |
| WP03 | `finalize_tasks` read `:2754-2758` | ❌ | `finalize_tasks` def **`:2656`**; `:2754-2758` drifted | MED |
| WP03 | `finalize_tasks` write re-anchor `:1865-1867` `primary_feature_dir_for_mission` | ✅ | `:1865-1867` exact | — |
| WP03 | `is_committed` def `_substantive.py:286`, coord-leg `:330-339`, HEAD-leg `:341-355` | ✅ | def `:286` exact; coord `cat-file -e {coord_ref}:` `:333`; HEAD `cat-file -e HEAD:` `:349`. Ranges accurate | — |
| WP03 | `create_intent` → `tests/specify_cli/cli/commands/agent/` | ✅ | dir EXISTS | — |
| WP04 | `_resolve_repo_root_and_slug` `:57-119` | ✅ | def `:57`; body through ~`:109` | — |
| WP04 | walk-to-kitty-specs `:86-97`; escape-check `:101-109`; `startswith` `:105` | ✅ | walk `:86`; escape comment `:101`; `startswith` check **`:105` exact**; raise `:107` | — |
| WP04 | `resolve_feature_dir_for_mission` call `:103` | ✅ | `:103` exact | — |
| WP04 | `_SAFE_SLUG_RE` `:79` | ✅ | def `:49`; **`.match()` use at `:79` exact** (the cite means the guard, which is `:79`) | — |
| WP04 | `cmd_verify` `:408`, resolver `:425` | ⚠️ | def `:398` (not `:408`); `resolve_mission_read_path` call `:426`. ~2-10 line drift | LOW |
| WP04 | `agent/context.py:158` reference | ✅ | exact (as WP02) | — |
| WP04 | `decision.py:421` identity-read pattern (referenced by WP09) | ✅ | `_raw_mission_id = _meta.get("mission_id")` `:422`; `resolve_mid8(...mission_id=_mission_id)` `:424`. Pattern present `:421-424` | — |
| WP04 | `feature_dir_resolver.py:60` → `resolution.py:436` raise path | ⚠️ | not re-pinned line-by-line here; routing is real (`resolve_feature_dir_for_mission` imported `decision.py:17`). Treat as descriptive | LOW |
| WP05 | `workflow.py:1341` re-resolve `resolve_workspace_for_wp` | ✅ | `:1341` exact | — |
| WP05 | `workflow.py:1377-1381`; `:1380` "no workspace could be resolved" | ✅ | re-resolve `:1377`; **error string `:1380` exact** | — |
| WP05 | `workflow.py:969` target branch via resolver | ✅ | `resolve_action_context(...)` `:969` exact | — |
| WP05 | `lanes/persistence.py:43`, `:78` ad-hoc `feature_dir / LANES_FILENAME` | ✅ | `:43` and `:78` **both exact** | — |
| WP05 | `workspace/context.py:798` ad-hoc lanes join | ✅ | `feature_dir / 'lanes.json'` in message at **`:798` exact** | — |
| WP05 | `resolve_lanes_dir` (to-be-created, "grep = 0 hits") | ✅ | 0 hits — correct | — |
| WP05 | `create_intent` → `tests/specify_cli/lanes/` | ✅ | dir EXISTS | — |
| WP06 | `resolve_canonical_root` non-worktree branch `paths.py:284-288` (`continue`) | ✅ | `_read_worktree_gitdir(...) is None` `:285`; `continue` **`:288` exact** | — |
| WP06 | regular-`.git`-dir leg `:280-282` | ✅ | `git_path.is_dir(): return candidate.resolve()` `:280-282` exact | — |
| WP06 | real-worktree-pointer leg `:289-290` | ✅ | `return get_main_repo_root(candidate)` `:289-290` exact | — |
| WP06 | `locate_project_root` `.kittify` boundary `:122/:130` | ✅ | `(candidate / KITTIFY_DIR).is_dir(): return candidate` `:122-123`; second marker `:130-131`. Both exact | — |
| WP06 | docstring "keep walking" `:262-263` | ✅ | bullet 3 at `:262-263` exact | — |
| WP06 | `create_intent` → `tests/specify_cli/core/` | ✅ | dir EXISTS | — |
| WP07 | `_collect_charter_sync_status` `:28-104` | ⚠️ | not separately re-pinned; symbol exists, `# noqa: BLE001` claim and `ensure_charter_bundle_fresh`/`generate_all` writes are the stated disease. Cites internal to the file — descriptive, trust the symbol | LOW |
| WP07 | `create_intent` → `tests/specify_cli/cli/commands/charter/` | ✅ | dir EXISTS | — |
| WP08 | `BaselineMergeCommitError` `merge.py:179` | ✅ | `:179` exact | — |
| WP08 | `_record_baseline_merge_commit` `:1633` | ✅ | `:1633` exact | — |
| WP08 | `_recorded_baseline_from_working_meta` `:1711` | ✅ | `:1711` exact | — |
| WP08 | `_assert_baseline_merge_commit_on_target` `:1758` | ✅ | `:1758` exact | — |
| WP08 | `tests/specify_cli/merge/` must be created | ✅ | dir MISSING — correct, WP says create it (+ `__init__.py`) | — |
| WP08 | `tests/merge/test_merge_done_recording.py` reference suite | ✅ | EXISTS | — |
| WP09 | `_resolve_mission_dir` `commands.py:263-266` `StatusReadPathNotFound → return None` | ✅ | def `:241`; `except StatusReadPathNotFound: return None` **`:265-266`** (cite `:263-266` brackets it) | — |
| WP09 | M3 empty seed `resolve_mid8(mission_slug, mission_id=None)` `:261` | ✅ | **`:261` exact** | — |
| WP09 | legacy seeds to PRESERVE `:484` / `:787` | ✅ | `:484` (legacy lane grammar comment + `mission_id=None`) and `:787` **both exact** | — |
| WP09 | 8 endpoints `:587,:652,:735,:870,:997,:1066,:1164,:1268` | ⚠️ | actual `_fail("MISSION_NOT_FOUND")` at `:591,:656,:737,:872,:999,:1068,:1166,:1270` — each ~2-4 lines after the cite (cite = endpoint head). All 8 genuinely exist | LOW |
| WP09 | `_read_path_resolver.py:352` `bool(mid8)` fail-closed gate | ⚠️ | `and bool(mid8)` at **`:353`** (block `fail_closed = (` starts `:351`). 1-line drift | LOW |
| WP09 | `decision.py:421` / `context.py:73` correct-shape reference | ✅ | `decision.py:421-424` ok (above); `context.py:73-83` meta-read + `resolve_mid8(...mission_id=_mission_id)` present | — |
| WP09 | `create_intent` → `tests/specify_cli/orchestrator_api/` | ⚠️ | dir **MISSING**; WP09 does not say to create it (unlike WP08). Implementer must `mkdir` + likely `__init__.py` | MED |

## Summary

- **Refs that are wrong (not just drifted): 1** — WP02 `_find_mission_slug` (wrong symbol; real is
  `_resolve_mission_slug`). The `mission_id` example values (e.g. `01KV8NPC…` 26-char) and the
  topology framing are all sound.
- **Refs with line drift the prompt already warns about (re-locate by symbol): WP03** is the worst
  cluster — `_build_setup_plan_detection_error` (`:1332`→`:1300`), `setup_plan` interior cites
  (anchored at a stale `:2054+` when `setup_plan` def is `:1905`), `commit_created` plan caller
  (`:2195`→`:3759/:3819`), `finalize_tasks` read (`:2754`→def `:2656`). None are wrong *symbols* —
  every function exists and exhibits the described behavior — so MED not HIGH, and WP03 explicitly
  tells the implementer to re-locate by symbol.
- **Already-done fix: NONE.** Notably WP01's freeze is real (composite is mutable on HEAD), WP06's
  submodule `continue` bug is live at `paths.py:288`, WP09's `:261` empty-mid8 seed and the
  `bool(mid8)` guard suppression are both live. WP08 is correctly *test-only* (verified-already-fixed).
- **Test-dir gap:** `tests/specify_cli/orchestrator_api/` is MISSING and WP09 (unlike WP08) does not
  instruct creating it. Worth a one-line addition to WP09 so the new module is collected.

**Single most dangerous trap:** WP02 T010's `_find_mission_slug` cite. An implementer who trusts the
symbol name edits the wrong file (or edits `agent/status.py`), missing the real collapse at
`next_cmd.py:_resolve_mission_slug:361`. Recommend correcting the prompt to
`_resolve_mission_slug (next_cmd.py:323; collapse at :361)`.
