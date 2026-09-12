# FR-007 / #3140 — `load_meta(` caller census

**Mission:** `doctrine-charter-split-unification-01KZ0SRB` · **Emitted by:** WP07 (T003)  
**Gates:** WP08 and WP09 (they route the sites this file enumerates; the NFR-003 full-census
contract test is driven from this row set).

## 0. Scope (read before treating this as a full inventory of `meta.json` reads)

**This census enumerates calls to the canonical parser (`load_meta(`-style call
sites), not every place `meta.json` is read.** The row set is reconciled against
`grep -rn "load_meta(" --include="*.py" .` (§1), so a raw `meta.json` read that
bypasses `load_meta`/`load_meta_fail_closed` entirely — e.g. its own
`Path.read_text()` + `json.loads()`, or `git show HEAD:<path>` piped through a
private JSON parse — produces no `load_meta(` token and therefore never
appears as a row here, and is not covered by the NFR-003 full-census contract
this file backs.

A known example: `src/specify_cli/git/ref_advance.py`'s
`_committed_meta_object` (~line 192) and `_meta_change_is_vcs_lock_only`
(~line 242) both read a mission's `meta.json` directly — via `git show
HEAD:<path>` and `Path.read_text()` respectively, each parsed by the module's
own `_parse_meta_object` helper — without ever calling `load_meta` or
`load_meta_fail_closed`. Neither site appears in this census, nor in
`tests/architectural/test_inline_meta_read_gate.py`'s allowlist
(`inline_meta_read_allowlist.yaml`), which gates a *different* class of inline
reads. These two sites are tracked as a known raw-read gap in follow-up issue
[#3162](https://github.com/Priivacy-ai/spec-kitty/issues/3162) rather than
routed here — routing them through `load_meta_fail_closed` is out of this
mission's scope (same carve-out as #3162's other `pending-batch-a` sites).

## 1. Anti-omission reconciliation (research.md D10 — BINDING)

The NFR-003 full-census contract is **self-referential**: a silently omitted call site would leak
through undetected. So the row set here is generated from — and reconciled against — the raw grep,
not hand-curated.

```
$ grep -rn "load_meta(" --include="*.py" .      # from the repo root of this checkout
```

| Measure | Count |
|---|---|
| Raw grep occurrences at WP07's merge-base (pre-routing) | 193 |
| … minus the one site WP07 routed (`lifecycle_phase.py`, see §4) | −1 |
| **Raw grep occurrences on this tree (post-WP07)** | **192** |
| **Rows in this census (sections 5 + 6)** | **192** |
| Undercount | **0 — row-count == occurrence-count** ✅ |

Distinct files touched: **85** (landing-pass correction, PR #3155: `doc_analysis/doc_state.py`
dropped out of this count — see the doc_state.py note in §5; it never actually belonged, since all
7 of its sites already called `load_meta_fail_closed(`, not the raw `load_meta(` this census
enumerates). Reconcile at any time with:

```
grep -rn "load_meta(" --include="*.py" . | wc -l     # must equal this census's row count
```

### ⚠️ The invariant SHRINKS — read this before writing the WP09 contract test

Routing a site **removes it from the grep set**: the call text changes from `load_meta(` to
`load_meta_fail_closed(`, which the literal grep no longer matches. WP07 already demonstrated this
(193 → 192). So the invariant is **not** a frozen constant:

- **Correct invariant:** `grep_count == number of census rows still labelled as un-routed`, i.e.
  every occurrence is *accounted for* — each row is either still present with its classification, or
  explicitly recorded as routed (§4).
- **A newly added, unclassified `load_meta(` site pushes `grep_count` ABOVE the census row set** —
  that is the regression the D10 contract must fail on.
- **Do NOT** pin `192` as a literal expected count in WP09. As WP08/WP09 route their sites the count
  will fall toward the `deliberately-silent` + `non-call-mention` + `definition-site` floor
  (**65** rows on today's classification). Pin the *set*, not the number.

> **Why 192 and not the ~108/110 the spec/research estimated.** The earlier estimate counted
> `src/` only (**109** rows here: 104 `src/specify_cli` + 3 `src/mission_runtime` + 2 `src/runtime`).
> The mandated grep is tree-wide, so it also captures **83** rows under `tests/`. Both are carried
> below; the `scope` column separates them. The literal grep also matches *suffixed* names
> (`_safe_load_meta(`, `canonical_load_meta(`, `_load_meta(`) and prose/docstring mentions — these
> are rows too, and are labelled honestly rather than dropped.

## 2. Classification vocabulary

The three mandated labels apply to **live call sites**:

| Label | Meaning | WP08/WP09 action |
|---|---|---|
| `route-unwrapped` | Calls the canonical parser on its **raising** contract (explicit or default `on_malformed="raise"`) with **no** local handling — a corrupt `meta.json` escapes as a raw `ValueError`. | **Route** through `load_meta_fail_closed`. |
| `divergent-wrapper` | Wraps the read in its **own** ad-hoc `except ValueError`/`except Exception` contract — a second, per-module fail-closed authority. | **Route**: replace the ad-hoc arm with the one reader (`MissionMetaReadError`). |
| `deliberately-silent` | Opted into the silent contract (`on_malformed="none"`/`"empty"`, incl. `load_meta_or_empty`). Corruption is *intentionally* absorbed. | **Preserve untouched** (spec Edge Cases). |

Two further labels are structural — they exist so every grep occurrence is a row, and they are
**not** routing targets:

| Label | Meaning |
|---|---|
| `definition-site` | The `def` of one of the TWO `load_meta` functions. |
| `non-call-mention` | Prose, comment, docstring, or a string-literal test fixture — not an executable call. |
| `authority-internal` | The one public reader's own internal call (`core/paths.py`). Not a divergent wrapper: it *is* the authority. |

## 3. The TWO `load_meta` definitions (D4 disambiguation — a census acceptance criterion)

Every row is tagged with which definition it targets. Mis-tagging a `DEF B` site mis-wires WP08/WP09,
because the two take **different arguments**:

| Tag | Definition | Signature | Contract |
|---|---|---|---|
| **DEF A** | `src/specify_cli/mission_metadata.py:275` | `load_meta(feature_dir, *, allow_missing=True, on_malformed="raise", encoding="utf-8")` | The canonical **parser**. Takes the mission **directory**. Polymorphic error contract. |
| **DEF B** | `src/specify_cli/task_utils/support.py:599` | `load_meta(meta_path)` | Thin **adapter** for the task CLI. Takes the **`meta.json` file path**. Missing → `TaskCliError`; malformed → `ValueError`. Delegates to DEF A. |

`DEF B` is reached by only **7** rows tree-wide (its own `def`, plus 4 contract tests in
`tests/tasks/test_tasks_support.py` and 2 aliased references) — every other row targets `DEF A`.
Routing DEF B means routing it **behind** the adapter (it already delegates to DEF A), or converting
its `ValueError` arm to the typed error — **not** passing a `feature_dir` to it.

## 4. Tally

| Classification | product (`src/`) | test (`tests/`) | total |
|---|---|---|---|
| `route-unwrapped` | 37 | 57 | **94** |
| `divergent-wrapper` | 26 | 0 | **26** |
| `deliberately-silent` | 31 | 7 | **38** |
| `authority-internal` | 1 | 0 | **1** |
| `definition-site` | 2 | 0 | **2** |
| `non-call-mention` | 5 | 19 | **24** |
| **TOTAL** | **102** | **83** | **185** |

**Routing workload handed to WP08/WP09:** 37 product `route-unwrapped` + 26 product `divergent-wrapper` = **63 product sites to route**, with 31 `deliberately-silent` product sites to leave alone.
(Landing-pass correction, PR #3155: the doc_state.py note in §5 removes 7 rows that were always
`route-unwrapped`/product — 44 → 37, 109 → 102, 192 → 185 tree-wide. See §7 for why 185 is *also*
no longer the live count.)

### Routed by WP07 (no longer in the grep set)

| Site | Was | Now |
|---|---|---|
| `src/mission_runtime/lifecycle_phase.py` `_read_baseline_merge_commit` | `route-unwrapped`, `DEF A` — the raw `ValueError` leaked out of `resolve_artifact_surface`; **this was the #3140 red** | Routed through `core.paths.load_meta_fail_closed`. The typed `MissionMetaReadError` is degraded to the absent-baseline answer (`""`) so the corruption verdict stays with `status.aggregate.MissionStatus._read_meta`, which raises `MissionMetadataUnavailable` with the slug + primary candidate attached. |

> WP07 deliberately routed **only** this site (its `owned_files`). The remaining product rows were
> intended for WP08/WP09's parallel routing lanes (D5), but the table below was never actually
> claimed by either WP's `owned_files` — see the correction note that follows it.

**Highest-priority remainder — NOT actually routed by WP08 or WP09** (same `mission_runtime`/`runtime`
subsystem as the fixed leak):

> **Correction (landing-pass review, PR #3155):** despite the heading above, none of the five sites in
> this table appear in `tasks/WP08-meta-fail-closed-route-batch-a.md`'s or
> `tasks/WP09-meta-fail-closed-route-batch-b.md`'s `owned_files` lists. Both WPs shipped and closed
> #3140 without ever touching these files — they remain genuinely unrouted (raw `ValueError` still
> escapes on a corrupt `meta.json`). This is now tracked as follow-up issue
> [#3162](https://github.com/Priivacy-ai/spec-kitty/issues/3162), which also covers the rest of this
> mission's `pending-batch-a` bucket (see the NFR-003 ledger in
> `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`). #3140's closure does not cover
> this table.

| Site | Class | Target |
|---|---|---|
| `src/runtime/next/runtime_bridge_io.py:380` (`_workflow_runtime_template`) | `route-unwrapped` | DEF A (canonical, feature_dir) |
| `src/runtime/next/_internal_runtime/planner.py:188` (`_resolve_workflow_for_mission`) | `route-unwrapped` | DEF A (canonical, feature_dir) |
| `src/mission_runtime/resolution.py:509` (`_mid8_from_primary_meta`) | `divergent-wrapper` | DEF A (canonical, feature_dir) |
| `src/mission_runtime/resolution.py:852` (`_resolve_coordination_branch`) | `divergent-wrapper` | DEF A (canonical, feature_dir) |
| `src/mission_runtime/resolution.py:1106` (`_resolve_mission_id`) | `divergent-wrapper` | DEF A (canonical, feature_dir) |

## 5. Product call sites (`src/`) — 109 rows

| # | File:line | Enclosing | Classification | Target def | Call contract |
|---|---|---|---|---|---|
| 1 | `src/runtime/next/_internal_runtime/planner.py:188` | `_resolve_workflow_for_mission` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 2 | `src/runtime/next/runtime_bridge_io.py:380` | `_workflow_runtime_template` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 3 | `src/specify_cli/acceptance/__init__.py:1179` | `_commit_acceptance_meta` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 4 | `src/specify_cli/acceptance/__init__.py:1241` | `_commit_acceptance_meta_via_router` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 5 | `src/specify_cli/bulk_edit/gate.py:57` | `_is_bulk_edit_mission` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 6 | `src/specify_cli/bulk_edit/gate.py:80` | `ensure_occurrence_classification_ready` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 7 | `src/specify_cli/cli/commands/agent/mission_setup_plan.py:415` | `_resolve_plan_template` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise' |
| 8 | `src/specify_cli/cli/commands/mission_type.py:1076` | `_resolve_mission_handle` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 9 | `src/specify_cli/cli/commands/mission_type.py:1084` | `_resolve_mission_handle` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 10 | `src/specify_cli/cli/commands/mission_type.py:1194` | `reopen_cmd` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 11 | `src/specify_cli/context/resolver.py:75` | `_read_meta_json` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=False,on_malformed='raise' |
| 12 | `src/specify_cli/coordination/status_transition.py:765` | `_identity_for_request` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise' |
| 13 | `src/specify_cli/coordination/surface_resolver.py:700` | `resolve_status_surface_with_anchor` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise' |
| 14 | `src/specify_cli/coordination/surface_resolver.py:771` | `resolve_status_surface_with_anchor` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise' |
> **doc_state.py note (landing-pass review, PR #3155):** a subsequent fold (`190932c2d`) collapsed 7 duplicated fail-closed guard blocks in `doc_analysis/doc_state.py` into a single shared `_require_meta()` helper. Even *before* that consolidation, all 7 sites already called `load_meta_fail_closed(` -- not the raw `load_meta(` this census enumerates -- so this file was never actually a live member of the literal `load_meta(` grep set §0 defines, and contributes zero rows now. The 7 rows WP07 originally enumerated here (reproduced in this commit's history for the curious) are removed rather than collapsed to one, because a single `_require_meta()` call to `load_meta_fail_closed` doesn't match this census's own grep methodology either.
| 15 | `src/specify_cli/merge/executor.py:1342` | `_phase_cleanup_worktrees_and_branches` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 16 | `src/specify_cli/merge/ordering.py:604` | `_assign_planning_only_mission_number_if_needed` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 17 | `src/specify_cli/migration/backfill_identity.py:373` | `backfill_mission_ids` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 18 | `src/specify_cli/migration/backfill_topology.py:98` | `read_topology` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=False |
| 19 | `src/specify_cli/migration/mission_state.py:1266` | `_canonicalize_meta` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise' |
| 20 | `src/specify_cli/migration/normalize_mission_lifecycle.py:118` | `_apply_identity_normalization` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise' |
| 21 | `src/specify_cli/migration/runtime_state_cutover.py:218` | `_flip_phase` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise' |
| 22 | `src/specify_cli/mission_metadata.py:234` | `resolve_mission_identity` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 23 | `src/specify_cli/mission_metadata.py:475` | `record_acceptance` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 24 | `src/specify_cli/mission_metadata.py:519` | `set_vcs_lock` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 25 | `src/specify_cli/mission_metadata.py:536` | `set_documentation_state` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 26 | `src/specify_cli/mission_metadata.py:561` | `set_origin_ticket` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 27 | `src/specify_cli/mission_metadata.py:588` | `set_target_branch` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 28 | `src/specify_cli/mission_metadata.py:605` | `set_purpose_summary` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 29 | `src/specify_cli/mission_metadata.py:635` | `set_change_mode` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 30 | `src/specify_cli/mission_metadata.py:672` | `clear_merge_metadata` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 31 | `src/specify_cli/mission_metadata.py:704` | `clear_coordination_metadata` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 32 | `src/specify_cli/mission_metadata.py:722` | `get_change_mode` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 33 | `src/specify_cli/missions/_read_path_resolver.py:846` | `read_primary_meta` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 34 | `src/specify_cli/missions/_read_path_resolver.py:862` | `read_primary_meta` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 35 | `src/specify_cli/status/lifecycle.py:143` | `_fallback_created_at` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise' |
| 36 | `src/specify_cli/status/lifecycle.py:242` | `_last_merge_marker_at` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise' |
| 37 | `src/specify_cli/tracker/origin.py:248` | `bind_mission_origin` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 38 | `src/mission_runtime/resolution.py:509` | `_mid8_from_primary_meta` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise'; except(ValueError) |
| 39 | `src/mission_runtime/resolution.py:852` | `_resolve_coordination_branch` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise'; except(ValueError) |
| 40 | `src/mission_runtime/resolution.py:1106` | `_resolve_mission_id` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise'; except(ValueError) |
| 41 | `src/specify_cli/audit/classifiers/meta.py:45` | `classify_meta_json` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise); except(ValueError) |
| 42 | `src/specify_cli/cli/commands/_identity_audit.py:280` | `_read_stored_topology` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise'; except(ValueError) |
| 43 | `src/specify_cli/cli/commands/agent/mission_feature_resolution.py:122` | `<def>` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise) |
| 44 | `src/specify_cli/cli/commands/agent/mission_feature_resolution.py:150` | `_safe_load_meta` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise); except(ValueError) |
| 45 | `src/specify_cli/cli/commands/agent/workflow.py:317` | `_load_coord_branch_meta` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise); except(Exception) |
| 46 | `src/specify_cli/cli/commands/implement.py:428` | `_load_primary_anchored_mission_meta` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise); except(Exception) |
| 47 | `src/specify_cli/cli/commands/implement.py:442` | `_load_fallback_mission_meta` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise); except(Exception) |
| 48 | `src/specify_cli/cli/commands/implement.py:989` | `_ensure_vcs_in_meta` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=False,on_malformed='raise'; except(FileNotFoundError,ValueError) |
| 49 | `src/specify_cli/cli/commands/merge.py:284` | `_teardown_coordination_for_abort` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise); except(Exception) |
| 50 | `src/specify_cli/cli/commands/mission_type.py:1093` | `<def>` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise) |
| 51 | `src/specify_cli/cli/commands/mission_type.py:1096` | `_safe_load_meta` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise); except((ValueError, OSError)) |
| 52 | `src/specify_cli/dashboard/diagnostics.py:25` | `_resolve_mission_from_feature` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise); except(Exception) |
| 53 | `src/specify_cli/decisions/service.py:134` | `_resolve_mission_id` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=False,on_malformed='raise'; except(FileNotFoundError,ValueError) |
| 54 | `src/specify_cli/merge/baseline.py:87` | `record_baseline_merge_commit` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise); except(ValueError) |
| 55 | `src/specify_cli/merge/baseline.py:122` | `_recorded_baseline_from_working_meta` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise); except(ValueError) |
| 56 | `src/specify_cli/migration/backfill_identity.py:134` | `backfill_mission` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=False; except((FileNotFoundError, ValueError)) |
| 57 | `src/specify_cli/migration/backfill_topology.py:169` | `backfill_mission_topology` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=False; except((FileNotFoundError, ValueError)) |
| 58 | `src/specify_cli/migration/normalize_mission_lifecycle.py:76` | `_load_meta_for_normalization` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise'; except(Exception) |
| 59 | `src/specify_cli/missions/_resolve_planning_branch.py:116` | `load_mission_target_branch` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=False,on_malformed='raise'; except(FileNotFoundError,ValueError) |
| 60 | `src/specify_cli/status/aggregate.py:415` | `MissionStatus._read_meta` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=False,on_malformed='raise'; except((FileNotFoundError, ValueError)) |
| 61 | `src/specify_cli/status/identity_audit.py:139` | `classify_mission` | `divergent-wrapper` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise'; except((OSError, ValueError)) |
| 62 | `src/specify_cli/status/store.py:247` | `_SlugResolver.resolve` | `divergent-wrapper` | DEF A (canonical, feature_dir) | on_malformed='raise'; except((json.JSONDecodeError, OSError, ValueError)) |
| 63 | `src/specify_cli/upgrade/feature_meta.py:42` | `load_feature_meta` | `divergent-wrapper` | DEF A (canonical, feature_dir) | defaults (raise); except(ValueError) |
| 64 | `src/specify_cli/cli/commands/_coordination_doctor.py:634` | `check_and_warn_coord_staleness` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 65 | `src/specify_cli/cli/commands/_coordination_doctor.py:779` | `_collect_coordination_findings` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 66 | `src/specify_cli/cli/commands/_coordination_doctor.py:1329` | `_apply_coord_staleness_fixes` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 67 | `src/specify_cli/cli/commands/agent/mission_check_prerequisites.py:74` | `_read_meta_for_emission` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='none' |
| 68 | `src/specify_cli/cli/commands/agent/mission_repair.py:274` | `run_mission_repair` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 69 | `src/specify_cli/cli/commands/mission_type.py:648` | `_read_mission_mid8` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='none' |
| 70 | `src/specify_cli/cli/commands/mission_type.py:769` | `_expected_discard_branches` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='none' |
| 71 | `src/specify_cli/cli/commands/mission_type.py:896` | `_delete_legacy_coordination_branch` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='none' |
| 72 | `src/specify_cli/cli/commands/tracker.py:101` | `_resolve_active_feature_slug` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 73 | `src/specify_cli/context/mission_resolver.py:176` | `_build_index` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 74 | `src/specify_cli/coordination/commit_router.py:657` | `_resolve_mid8` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='none' |
| 75 | `src/specify_cli/coordination/legacy_resolution.py:83` | `_load_mission_meta` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 76 | `src/specify_cli/core/vcs/detection.py:132` | `_get_locked_vcs_from_feature` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 77 | `src/specify_cli/core/vcs/detection.py:183` | `_get_locked_vcs_from_feature` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 78 | `src/specify_cli/dashboard/scanner.py:388` | `_read_mission_identity` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none',encoding='utf-8-sig' |
| 79 | `src/specify_cli/dashboard/scanner.py:653` | `_read_dashboard_feature_meta` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none',encoding='utf-8-sig' |
| 80 | `src/specify_cli/git/sparse_checkout.py:269` | `_load_managed_lane_policies` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 81 | `src/specify_cli/lanes/recovery.py:245` | `_mission_id_from_meta` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 82 | `src/specify_cli/lanes/worktree_allocator.py:564` | `_read_coordination_branch` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 83 | `src/specify_cli/merge/ordering.py:305` | `_compute_next_mission_number_or_none` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 84 | `src/specify_cli/merge/ordering.py:403` | `_write_mission_number_to_branch` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 85 | `src/specify_cli/migration/backfill_runtime_state.py:293` | `_mission_id` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='none' |
| 86 | `src/specify_cli/migration/backfill_runtime_state.py:821` | `_synthesize_claim_anchor` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='none' |
| 87 | `src/specify_cli/migration/runtime_state_cutover.py:359` | `stamp_accept_cutover` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='none' |
| 88 | `src/specify_cli/mission_metadata.py:365` | `load_meta_strict` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=False,on_malformed='empty',encoding=_UTF8_SIG if bom_tolerant else _UTF8 |
| 89 | `src/specify_cli/mission_metadata.py:383` | `load_meta_or_empty` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='empty' |
| 90 | `src/specify_cli/missions/_read_path_resolver.py:115` | `_declares_coordination_branch` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 91 | `src/specify_cli/status/cutover_eligibility.py:85` | `_read_meta` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='empty',encoding='utf-8-sig' |
| 92 | `src/specify_cli/status/emit.py:115` | `_load_mission_id` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='none' |
| 93 | `src/specify_cli/status/emit.py:385` | `_read_status_phase` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='none' |
| 94 | `src/specify_cli/upgrade/migrations/m_zz_runtime_state_backfill.py:152` | `_mission_needs_cutover` | `deliberately-silent` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='none' |
| 95 | `src/specify_cli/core/paths.py:676` | `load_meta_fail_closed` | `authority-internal` | DEF A (canonical, feature_dir) | allow_missing=True,on_malformed='raise' |
| 96 | `src/specify_cli/mission_metadata.py:275` | `<def>` | `definition-site` | DEF A (canonical, feature_dir) | — |
| 97 | `src/specify_cli/task_utils/support.py:599` | `<def>` | `definition-site` | DEF B (adapter, meta_path) | — |
| 98 | `src/specify_cli/acceptance/__init__.py:1331` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 99 | `src/specify_cli/coordination/legacy_resolution.py:76` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 100 | `src/specify_cli/decisions/service.py:142` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 101 | `src/specify_cli/lanes/recovery.py:242` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 102 | `src/specify_cli/upgrade/feature_meta.py:36` | `<prose/fixture>` | `non-call-mention` | n/a | — |

**Subtotal (product): 102 rows.**

## 6. Test-tree occurrences (`tests/`) — 83 rows

| # | File:line | Enclosing | Classification | Target def | Call contract |
|---|---|---|---|---|---|
| 1 | `tests/coordination/test_status_write_authority.py:79` | `test_fallback_commits_status_to_coord_worktree` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 2 | `tests/integration/test_mission_close.py:201` | `test_teardown_silently_skips_when_mid8_missing` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 3 | `tests/merge/test_squash_reconcilers_2709.py:170` | `test_write_meta_validate_false_never_drops_unknown_key` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 4 | `tests/mission_runtime/test_consolidated_resolution.py:167` | `_consolidate_e1` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 5 | `tests/mission_runtime/test_consolidated_resolution.py:435` | `test_squash_publish_resolves_via_content_presence_not_ancestry` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 6 | `tests/mission_runtime/test_lifecycle_phase.py:148` | `_consolidate_e1` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 7 | `tests/mission_runtime/test_lifecycle_phase.py:298` | `test_c003_target_ref_absent_without_terminal_completion_is_pre_consolidation` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 8 | `tests/missions/test_wp17_husk_arm_collapse.py:348` | `test_load_meta_canonical_default_contract` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 9 | `tests/missions/test_wp17_husk_arm_collapse.py:354` | `test_load_meta_canonical_default_contract` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 10 | `tests/missions/test_wp17_husk_arm_collapse.py:387` | `test_status_transition_meta_exists_false_on_missing` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 11 | `tests/regression/test_issue_2709_squash_provenance.py:77` | `_make_meta_valid` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 12 | `tests/regression/test_issue_2795_claim_blocker.py:189` | `test_vcs_lock_only_meta_change_does_not_block_consolidation` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 13 | `tests/regression/test_issue_2795_claim_blocker.py:197` | `_write_genuine_meta_edit` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 14 | `tests/regression/test_issue_3033_post_consolidation_write.py:232` | `_record_e1_consolidation` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 15 | `tests/regression/test_issue_3033_post_consolidation_write.py:388` | `test_safe_commit_succeeds_for_primary_kind_write_on_e2_mission` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 16 | `tests/regression/test_issue_3033_post_consolidation_write.py:493` | `test_write_artifact_succeeds_for_coord_kind_write_on_e2_mission` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 17 | `tests/regression/test_issue_3086_merge_delete_branch_flattens_coordination_metadata.py:166` | `test_issue_3086_merge_delete_branch_flattens_coordination_metadata` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 18 | `tests/specify_cli/cli/commands/agent/test_mission_feature_resolution.py:169` | `test_safe_load_meta_returns_none_for_unknown_mission` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 19 | `tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py:455` | `test_setup_plan_uses_single_loaded_meta_snapshot_when_file_changes_after_read._load_then_mutate` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=allow_missing,on_malformed=on_malformed,encoding=encoding |
| 20 | `tests/specify_cli/cli/commands/test_implement.py:393` | `TestPlanningArtifactPath.test_modern_mission_resolves_coord_branch_from_meta` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 21 | `tests/specify_cli/cli/commands/test_implement.py:403` | `TestPlanningArtifactPath.test_legacy_mission_has_no_coord_branch` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 22 | `tests/specify_cli/cli/commands/test_lifecycle_read_seam_migration.py:216` | `test_safe_load_meta_reads_primary_meta_regardless_of_coord_state` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 23 | `tests/specify_cli/cli/commands/test_safe_commit_cmd.py:114` | `_seed_merged_and_pruned_mission` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 24 | `tests/specify_cli/coordination/test_write_seam_thunk.py:157` | `_record_e1_consolidation` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 25 | `tests/specify_cli/test_canonical_acceptance.py:498` | `TestOrchestratorParity.test_orchestrator_and_standard_acceptance_identical_structure` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 26 | `tests/specify_cli/test_canonical_acceptance.py:499` | `TestOrchestratorParity.test_orchestrator_and_standard_acceptance_identical_structure` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 27 | `tests/specify_cli/test_canonical_acceptance.py:539` | `TestOrchestratorParity.test_orchestrator_acceptance_includes_acceptance_mode` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 28 | `tests/specify_cli/test_canonical_acceptance.py:574` | `TestAcceptanceMetadataWrite.test_record_acceptance_sets_all_fields` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 29 | `tests/specify_cli/test_canonical_acceptance.py:593` | `TestAcceptanceMetadataWrite.test_record_acceptance_without_commits` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 30 | `tests/specify_cli/test_canonical_acceptance.py:618` | `TestAcceptanceMetadataWrite.test_record_acceptance_clears_stale_commit_fields` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 31 | `tests/specify_cli/test_canonical_acceptance.py:730` | `TestEndToEndCanonicalAcceptance.test_e2e_acceptance_no_activity_log_fallback` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 32 | `tests/specify_cli/test_feature_metadata.py:67` | `TestLoadMeta.test_load_valid` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 33 | `tests/specify_cli/test_feature_metadata.py:71` | `TestLoadMeta.test_load_missing_returns_none` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 34 | `tests/specify_cli/test_feature_metadata.py:78` | `TestLoadMeta.test_load_malformed_json_raises_valueerror` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 35 | `tests/specify_cli/test_feature_metadata.py:85` | `TestLoadMeta.test_load_meta_non_dict_json` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 36 | `tests/specify_cli/test_feature_metadata.py:411` | `TestRecordAcceptance.test_record_acceptance_clears_stale_commit_fields` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 37 | `tests/specify_cli/test_feature_metadata.py:493` | `TestSetTargetBranch.test_persists_to_disk` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 38 | `tests/specify_cli/test_feature_metadata.py:516` | `TestUnknownFieldPreservation.test_write_preserves_unknown_fields` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 39 | `tests/specify_cli/test_feature_metadata.py:531` | `TestUnknownFieldPreservation.test_mutation_preserves_unknown_fields` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 40 | `tests/specify_cli/test_feature_metadata.py:568` | `TestUnicodeHandling.test_unicode_round_trip` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 41 | `tests/specify_cli/test_feature_metadata.py:619` | `TestVcsLockStandardFormat.test_vcs_lock_preserves_existing_fields` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 42 | `tests/specify_cli/test_feature_metadata.py:771` | `TestCompatibilityWrappers.test_wrapper_round_trip_matches_canonical` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 43 | `tests/specify_cli/test_feature_metadata_origin.py:127` | `TestSetOriginTicketOverwrite.test_overwrites_existing_origin_ticket` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 44 | `tests/specify_cli/test_mission_metadata.py:78` | `test_load_meta_reads_valid_object` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 45 | `tests/specify_cli/test_mission_metadata.py:88` | `test_contract_a_missing_returns_none` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 46 | `tests/specify_cli/test_mission_metadata.py:96` | `test_contract_a_malformed_raises` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 47 | `tests/specify_cli/test_mission_metadata.py:102` | `test_contract_a_non_object_top_level_raises` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 48 | `tests/specify_cli/test_mission_metadata.py:112` | `test_contract_b_missing_raises` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=False |
| 49 | `tests/specify_cli/test_mission_metadata.py:212` | `test_valid_object_identical_across_contracts` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 50 | `tests/specify_cli/test_mission_metadata.py:213` | `test_valid_object_identical_across_contracts` | `route-unwrapped` | DEF A (canonical, feature_dir) | allow_missing=False |
| 51 | `tests/specify_cli/test_mission_metadata_change_mode.py:76` | `test_set_change_mode_bulk_edit` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 52 | `tests/specify_cli/test_mission_metadata_change_mode.py:115` | `test_change_mode_preserved_through_write_meta` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 53 | `tests/specify_cli/test_mission_metadata_change_mode.py:121` | `test_change_mode_preserved_through_write_meta` | `route-unwrapped` | DEF A (canonical, feature_dir) | defaults (raise) |
| 54 | `tests/tasks/test_tasks_support.py:319` | `TestSupportLoadMetaContract.test_missing_meta_raises_task_cli_error` | `route-unwrapped` | DEF B (adapter, meta_path) | defaults (raise) |
| 55 | `tests/tasks/test_tasks_support.py:327` | `TestSupportLoadMetaContract.test_valid_meta_returns_dict` | `route-unwrapped` | DEF B (adapter, meta_path) | defaults (raise) |
| 56 | `tests/tasks/test_tasks_support.py:337` | `TestSupportLoadMetaContract.test_bom_encoded_meta_returns_dict` | `route-unwrapped` | DEF B (adapter, meta_path) | defaults (raise) |
| 57 | `tests/tasks/test_tasks_support.py:353` | `TestSupportLoadMetaContract.test_malformed_meta_raises` | `route-unwrapped` | DEF B (adapter, meta_path) | defaults (raise) |
| 58 | `tests/specify_cli/test_mission_metadata.py:162` | `test_contract_c_missing_returns_empty` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='empty' |
| 59 | `tests/specify_cli/test_mission_metadata.py:169` | `test_contract_c_malformed_returns_empty` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='empty' |
| 60 | `tests/specify_cli/test_mission_metadata.py:186` | `test_contract_c_non_object_returns_empty` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='empty' |
| 61 | `tests/specify_cli/test_mission_metadata.py:195` | `test_on_malformed_none_missing_returns_none` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 62 | `tests/specify_cli/test_mission_metadata.py:201` | `test_on_malformed_none_malformed_returns_none` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 63 | `tests/specify_cli/test_mission_metadata.py:214` | `test_valid_object_identical_across_contracts` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='empty' |
| 64 | `tests/specify_cli/test_mission_metadata.py:215` | `test_valid_object_identical_across_contracts` | `deliberately-silent` | DEF A (canonical, feature_dir) | on_malformed='none' |
| 65 | `tests/architectural/test_inline_meta_read_gate.py:648` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 66 | `tests/architectural/test_inline_meta_read_gate.py:651` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 67 | `tests/architectural/test_no_raw_mission_spec_paths.py:65` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 68 | `tests/mission_runtime/test_read_path_create_window_invariant.py:91` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 69 | `tests/missions/test_wp17_husk_arm_collapse.py:378` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 70 | `tests/specify_cli/cli/commands/agent/test_wp06_meta_reader_sweep.py:154` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 71 | `tests/specify_cli/missions/test_read_path_resolver_validation.py:263` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 72 | `tests/specify_cli/test_feature_metadata.py:62` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 73 | `tests/specify_cli/test_feature_metadata.py:81` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 74 | `tests/specify_cli/test_feature_metadata.py:709` | `<def>` | `non-call-mention` | n/a | — |
| 75 | `tests/specify_cli/test_feature_metadata.py:710` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 76 | `tests/specify_cli/test_meta_reader_sweep.py:105` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 77 | `tests/specify_cli/test_meta_reader_sweep.py:120` | `<def>` | `non-call-mention` | n/a | — |
| 78 | `tests/specify_cli/test_mid8_direct_routing.py:112` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 79 | `tests/specify_cli/test_wp18_meta_reader_contracts.py:81` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 80 | `tests/specify_cli/test_wp18_meta_reader_contracts.py:129` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 81 | `tests/status/test_derived_view_slug_traversal.py:239` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 82 | `tests/status/test_derived_view_slug_traversal.py:247` | `<prose/fixture>` | `non-call-mention` | n/a | — |
| 83 | `tests/status/test_emit.py:290` | `<prose/fixture>` | `non-call-mention` | n/a | — |

**Subtotal (test): 83 rows.**

## 7. Reconciliation footer

- Section 5 rows: **102**
- Section 6 rows: **83**
- **Total census rows (post doc_state.py correction): 185**

> **Landing-pass correction (PR #3155, second-round accuracy review).** The line above is **not**
> `185 == raw grep occurrences` — as of this fold, `grep -rn "load_meta(" --include="*.py" . | wc -l`
> from the repo root returns **168**, not 185. Do not "fix" this by pinning 185 as a new frozen
> constant either; verify live with the same command §1 prescribes.
>
> The gap is real and explained, not an error in this arithmetic: this census is **WP07's
> historical snapshot** (its role is stated explicitly in
> `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`'s module docstring — the live
> NFR-003 gate deliberately does **not** source its site list from this file, precisely so a site
> added or routed after WP07 wrote it isn't silently invisible). Since WP07 authored it:
> - WP08 (`7cd14d35e`, landed as part of this mission, well before the PR #3155 landing-fold
>   sequence) routed the batch-A `coordination`/`migration`/`audit`/`status` subsystem sites this
>   census enumerates through `load_meta_fail_closed` — removing roughly two dozen product rows
>   from the live grep set without a census update.
> - This landing-fold's own commits removed 7 more (the doc_state.py consolidation, §5 note above)
>   and a further handful of individual sites in `acceptance/__init__.py`, `implement.py`,
>   `mission_type.py`'s `_safe_load_meta`, `mission_feature_resolution.py`'s `_safe_load_meta`,
>   `merge/ordering.py`, and `migration/runtime_state_cutover.py` (each already delegates to
>   `load_meta_fail_closed`, some only still grep-matching because of a `_load_meta`-style import
>   alias).
> - New test files added since WP07's authorship (`test_meta_fail_closed_full_census_contract.py`,
>   `test_meta_fail_closed_batch_a.py`, `test_meta_read_permission_denied_regression.py`, plus a new
>   regression test in `test_mission_metadata.py`) contribute mentions/call sites this snapshot never
>   saw.
>
> A full row-by-row re-numbering of sections 5–6 against the current 168-occurrence grep set was
> assessed and **not** attempted in this fold — it is materially bigger surgery than a landing-pass
> doc fix (every one of ~90 affected rows needs its own source-level re-classification, which is real
> risk of introducing a *new* silent inaccuracy into the one document whose entire purpose is
> precision). If per-row accuracy against the live tree is needed, treat this file as reference
> history only and consult the AST-based `_ACCOUNTED_SITES` ledger in
> `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` instead — that ledger, not this
> markdown snapshot, is the live, continuously-enforced source of truth (D10).

A new `load_meta(` site added anywhere in the tree is caught by that AST-based contract test, not by
this markdown file — this file no longer self-enforces via a literal row-count equality (see the
correction above).
