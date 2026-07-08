# Untrusted-segment → FS-sink inventory (WP01 / FR-003, FR-004)

Generated input: `python tests/architectural/untrusted_path_audit/audit.py`
walks `src/specify_cli` and self-asserts this table in BOTH directions —
undercount (every discovered sink is documented) AND overcount/ghost (every
documented row still maps to a live sink), plus known-candidate presence and the
FR-009 `meta.json` row. Dispositions are human-verified against the cited
source — see `RULESET.md` for the vocabulary and the Named-untrusted rule.

**Row identity (FR-004).** Rows are compared by the drift-proof composite
`(file, qualname, token)` — the `qualname` + `token` columns, derived by
`tests.architectural._ratchet_keys.composite_key_from_file`. The **`line` in the
`file:line` locator is NON-authoritative** (a jump-to aid, never compared): a
blank/comment insertion that shifts a sink's line leaves the audit GREEN (this
killed the #2306 false-failure class). A real edit to the sink line changes the
`token` and the audit goes RED. Long tokens are truncated at 60 chars with a `…`
marker (the stored prefix stays unique per `(file, qualname)`).

**Freshen path.** When a sink's content genuinely changes, run the audit: the
undercount error prints the exact `| file:line | qualname | token | … |` row to
paste. Never hand-type a token — it must be tool-derived (`composite_key_from_file`).

**`[inventory-only]` rows.** A row tagged `[inventory-only]` in its rationale is
exempt from the overcount guard because the AST matcher intentionally cannot
discover it — a RULESET known-false-negative class (the FR-009 `meta.json`
write-path keyed on `feature_dir`, or a cross-function diagnostic whose join sits
behind a boundary seam). Each tagged row names WHY. (No *removed-sink* tags exist
at conversion; the 5 tags are all known-FN documentation.)

**Note (WP02/WP03 update):** WP02 added `_is_contained` to `status/store.py`
(new `mission_slug` join; old join shifted out of scope) and WP03 added seam
calls to `dossier/`, `events/`, `migration/`, and `review/arbiter` (those joins
are no longer discovered).

**Conversion record (FR-004 re-key, WP02, recorded).** Every `qualname`+`token`
below was tool-derived by `composite_key_from_file` — reproduce any of them by
re-running that helper on the row's `file:line` (or delete a row and re-run the
audit: the undercount message prints the exact replacement). Discovered rows
froze their live `(qualname, token)`; five rows the matcher cannot AST-discover
(RULESET known-FN) were refreshed to a real current line, tagged
`[inventory-only]`, and exempted from overcount: `mission_metadata.py:458`
(FR-009 write-path), `cli/commands/decision.py:470` (cross-fn `load_meta`),
`status/aggregate.py:514` (`_find_meta_path`), `status/aggregate.py:762` and
`:763` (`save()` diagnostics). The stale duplicate `review/cycle.py:225` (a
second copy of the live `:231` legacy-feedback join) was dropped — the overcount
guard's exact reconciliation purpose.

## Sink table

| file:line | qualname | token | untrusted source | sink op | disposition | rationale |
| --- | --- | --- | --- | --- | --- | --- |
| audit/engine.py:88 | _resolve_mission_filter | candidate = scan_root / resolved . mission_slug | resolved.mission_slug | Path-join (/) | unreachable | `scan_root / resolved.mission_slug` is consumed only by a `.is_dir()` existence filter that returns an empty `frozenset` on miss — no file is opened/written; a traversal slug simply fails `.is_dir()`. (Named-untrusted rule: a value that IS `mission_slug` is dispositioned `unreachable`, not `trusted-source`, even though `resolve_mission` resolves it against the on-disk index.) |
| cli/commands/agent/mission_finalize.py:199 | _collect_finalize_artifacts | feature_dir / / / mission_slug / , | mission_slug | Path-join (/) | routed-through-seam (TODO) | `--mission` slug joined to `.kittify/dossiers/<slug>/snapshot-latest.json` as a finalize commit candidate; no `assert_safe_path_segment` on this CLI path. Deferred (CLI-arg, read-only candidate list). (line shifted +8 by mission 01KVMBD6 #2056 god-tag comment + de-god extraction; then 320→321 by mission single-authority-topology-cleanup-01KVRJ6P WP16 commit-target enum eradication, FR-001b; then 321→317 by mission write-surface-coherence-01KVTVZS kind-aware placement refactor; then 317→318 by mission gate-read-surface-completion-01KVW9B0 WP00 finalize-tasks write-surface re-point extracting `_collect_finalize_artifacts`; then RELOCATED mission.py → mission_finalize.py by mission decompose-mission-god-module-01KVXHF8 #2056 finalize-tasks seam extraction (WP07), settling at :194 after the same mission's whole-tree-mypy redundant-cast removal; then re-anchored on upstream/main with #2135 doctor.py decomposition (no mission_finalize.py impact); then 194→195 by mission lifecycle-tooling-friction WP05 adding the advisory issue-matrix lint candidate one line above this sink; then 195→199 by #2179 JSON-mode finalize diagnostics routing above this sink — same sink, only the line drifted, disposition unchanged) |
| cli/commands/agent/tasks_move_task.py:206 | _mt_warn_worktree_kitty_specs | if worktree_kitty and ( worktree_kitty / st . mission_slug /… | st.mission_slug | Path-join (/) | routed-through-seam (TODO) | `worktree_kitty / st.mission_slug / "tasks"` `.exists()` probe from a raw `--mission` slug; reachable, unguarded. Deferred (CLI-arg, .exists() probe only). (line shifted −11 by mission 01KVJPEQ read-side adoption rebase; then +2 by mission 01KVMBD6 #2058 god-tag comment; then 1902→1933 by mission single-planning-surface-authority-01KVPR00 WP06 map-requirements read-surface consolidation; then 1933→1932 by WP03 import shrink; then 1932→1935 by mission single-authority-topology-cleanup-01KVRJ6P WP16 commit-target enum eradication, FR-001b; then 1935→1972 by mission write-surface-coherence-01KVTVZS kind-aware read-path resolver additions; then 1972→1046 by mission decompose-agent-tasks-god-module-01KVWVAR #2058 seam extraction (helper bodies moved into tasks_*.py modules, shrinking tasks.py); then 1046→1079 by mission single-authority-resolution-gates-01KW1P0F WP02 (#2154 write-leg routing + #2155 mixed-bundle partition + T012 canon-site folds added lines above this sink); then 1079→1076 by mission implement-loop-coord-authority-completion-01KW2E7A (#2160) routing planning reads onto resolve_planning_read_dir (net −3 lines above this sink); then 1076→1077 by the 2026-06-27 rebase onto upstream/main carrying concurrent mission #1057's check_pre30_layout boundary-guard insertions (+1 line above this sink); then 1077→1134 by PR #2277 reliability-papercut-sweep 7-WP coexistence (+57 lines above this sink); then 1134→1325 by mission tasks-py-degod-01KWF08S (#2116) which extracted this probe VERBATIM into the `_mt_warn_worktree_kitty_specs` helper on the `_MoveTaskState` shell — the raw `mission_slug` local became the `st.mission_slug` field on the frozen state object, so the source token is now `st.mission_slug`; same `.exists()`-only probe, same disposition, only the line + receiver drifted; then 1325→732 (#2306 fold, mission tasks-py-degod-wave2-01KWH9EQ WP05 T021): the recorded 1325 was already one line stale on the mission base (actual 1326 — the off-by-one #2306 reports), and wave-2 WP02–WP04 relocations (tasks_shared.py, tasks_command_adapters.py, render-seam unification) removed ~594 lines above the sink; re-located via the gate's own AST audit; then tasks.py:732→tasks_move_task.py:204 by the same mission's WP05 move_task-family relocation (#2305) — `_mt_warn_worktree_kitty_specs` moved VERBATIM into `tasks_move_task.py`; same probe, same disposition, only the module + line changed; then 204→206 by degod-follow-ups PR #2308 constructor-DI collapse — a 2-line explanatory comment added to `_default_move_task_ports` above this sink; same probe, same disposition, line-only drift) |
| cli/commands/agent/tasks_move_task.py:1039 | _mt_run_pre_review_gate | baseline_path = st . feature_dir / / wp_slug / | wp_slug | Path-join (/) | trusted-source | `st.feature_dir / "tasks" / wp_slug / "baseline-tests.json"`; `wp_slug` from `_resolve_wp_slug(...)` — the SAME derived-on-disk-filename provenance as `review/baseline.py:215`'s `capture_baseline` row (`wp.path.stem`-shaped, not external input), `st.feature_dir` the coord-write dir already trusted throughout this module. Read-only `BaselineTestResult.load()` of the pre-review gate's baseline cache (mission review-regression-gate-01KWX6DF WP02, T004). |
| cli/commands/agent/workflow.py:921 | _has_prior_rejection | sub_artifact_dir = feature_dir / / wp_slug | wp_slug | Path-join (/) | trusted-source | `wp_slug` is the WP file stem (`wp.path.stem`) — a derived on-disk filename, not external input; `feature_dir / "tasks" / wp_slug` then `.exists()`/`.glob`. (line shifted −2 by mission 01KVJPEQ workflow.py cascade migration; then +1 by WP05 import addition to module-level _read_path_resolver import block; then 920→921 by mission implement-loop-coord-authority-completion-01KW2E7A (#2160) routing planning reads onto resolve_planning_read_dir — same sink, only the line drifted) |
| cli/commands/agent/workflow.py:1621 | implement | _sub_artifact_dir = feature_dir / / wp_slug | wp_slug | Path-join (/) | trusted-source | Same `wp.path.stem` provenance; read-only `ReviewCycleArtifact.latest(...)`. (line shifted −2 by mission 01KVJPEQ; then +7 by WP05 import addition + _analysis_report_gate_dir routing change; then 1605→1613 by mission implement-loop-coord-authority-completion-01KW2E7A (#2160) routing planning reads onto resolve_planning_read_dir; then 1613→1621 by mission coord-read-residuals-01KW2M8V (#2186) WP01 identity routing adding the sparse-checkout-preflight primary fold above this sink — same sink, only the line drifted) |
| cli/commands/agent/workflow.py:2841 | review | _resolve_workflow_read_dir ( | wp_slug | Path-join (/) | trusted-source | `wp_slug = wp.path.stem`; parent dir now resolved by `_resolve_workflow_read_dir(...)` — the kind-aware read-side wrapper over `resolve_feature_dir_for_mission` → `resolve_mission_read_path` (assert_safe_path_segment). Segment derived, dir guarded. (line shifted −2 by mission 01KVJPEQ; then +7 by WP05 import addition +_analysis_report_gate_dir routing change; then 2647→2686 by mission implement-loop-coord-authority-completion-01KW2E7A (#2160) routing planning reads onto resolve_planning_read_dir; then 2686→2654 by the same mission's pre-merge-squad nit collapsing the vestigial _find_first_for_review_wp walk; then 2654→2670 by mission coord-read-residuals-01KW2M8V (#2186) WP01 identity routing adding primary folds above this sink; then 2670→2841 by mission read-surface-ssot-closeout-01KWZV91 WP04 re-routing the review write-candidate dir through the kind-aware read-side wrapper `_resolve_workflow_read_dir` (replacing the direct `resolve_feature_dir_for_mission` call; upstream/main still routes it directly) — same `wp_slug`-derived sink, disposition unchanged) |
| cli/commands/decision.py:470 | cmd_verify | mission_dir = resolve_handle_to_read_path ( repo_root , miss… | mission_slug | Path-join (/) | routed-through-seam (TODO) | [inventory-only] `repo_root / KITTY_SPECS_DIR / mission_slug` then `load_meta(...)` read; raw `--mission` slug, no seam at this site. Deferred (CLI-arg, load_meta read). |
| merge/done_bookkeeping.py:428 | _resolve_in_branch_status_events_path | rel_events_path = Path ( KITTY_SPECS_DIR ) / mission_slug / … | mission_slug | Path-join (/) | unreachable | Builds a *relative* `kitty-specs/<slug>/status.events.jsonl` only to stringify into a `git show <ref>:<path>` argument (`_assert_merged_wps_done_on_target` → `run_command(["git", "show", …])`); no local FS open — git resolves inside the tree object. (relocated VERBATIM from `cli/commands/merge.py:613` into the `_resolve_in_branch_status_events_path` seam by mission #2057 decompose-merge-god-module-01KVXHDK WP08 — behavior-preserving god-module decomposition, disposition unchanged; then 419→428 by mission coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V (#2185/#2186) merge/identity routing inserting lines above the helper (`def` moved 402→411) — same sink, only the line drifted, disposition unchanged) |
| merge/done_bookkeeping.py:430 | _resolve_in_branch_status_events_path | rel_events_path = Path ( KITTY_SPECS_DIR ) / mission_slug / … | mission_slug | Path-join (/) | unreachable | Same git-ref-argument path as :428 (the `if path_is_under_worktrees(...)` worktree-rewrite branch); no FS sink. (relocated VERBATIM from `cli/commands/merge.py:615` by mission #2057 WP08; then 421→430 by mission coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V (#2185/#2186) merge/identity routing inserting lines above the helper — same sink, only the line drifted, disposition unchanged) |
| merge/ordering.py:297 | _compute_next_mission_number_or_none | target_meta_path = scan_specs / mission_slug / | mission_slug | Path-join (/) | routed-through-seam (TODO) | `scan_specs / mission_slug / "meta.json"` then `read_text()` after `.exists()`; raw `--mission`/target slug, no seam. Deferred (CLI-arg, .exists()+read_text). (relocated VERBATIM from `cli/commands/merge.py:1144` into the mission-number bake cluster by mission #2057 decompose-merge-god-module-01KVXHDK WP07 — behavior-preserving god-module decomposition, disposition unchanged) |
| merge/ordering.py:304 | _compute_next_mission_number_or_none | target_meta = load_meta ( scan_specs / mission_slug , on_mal… | mission_slug | Path-join (/) | routed-through-seam (TODO) | `load_meta(scan_specs / mission_slug, on_malformed="none")` — the canonical meta reader over a second `scan_specs / mission_slug` join inside the `target_meta_path.exists()` guard (sibling of the :297 sink); raw `--mission`/target slug, no `assert_safe_path_segment` at this site. Deferred (CLI-arg, best-effort idempotency peek). (NEW row surfaced by mission read-surface-ssot-closeout-01KWZV91 replacing the prior `_json.loads(target_meta_path.read_text())` read with the canonical `load_meta` reader — upstream/main read via the already-joined `target_meta_path`, this branch composes the second join feeding `load_meta`; same untrusted provenance and disposition as :297) |
| coordination/surface_resolver.py:499 | _coord_mid8 | coord_candidate = repo_root | mission_slug | Path-join (/) | unreachable | Path composed solely to populate `StatusReadPathNotFound(coord_candidate=…)` inside a `raise`; never opened/written — fail-closed diagnostic payload. (line shifted by mission 01KVGCE8 collapse; then 518→472 by mission 01KVN754 WP04 coord-empty Option B deletion of CoordinationWorktreeEmpty + 2 helpers; then 472→487 by 01KVPR00 WP03; then 487→489 by 01KVPR00 WP08/WP09 surface-topology gating; then 489→494 by mission 01KVRJ6P WP02 FR-005 collapse of `_COORD_SURFACE_TOPOLOGIES` + import-block widen; then 494→493 by 3.2.3-coord-surface-regressions #2119/#2125 retrospective-home docstring/error-prose edit in `_coord_mid8`; then 493→494 by mission single-authority-resolution-gates-01KW1P0F WP04 routing `resolve_status_surface_with_anchor` through `_canonicalize_primary_read_handle` (import + 3-line call split above this join); then 494→495 by PR #2277 reliability-papercut-sweep CoordinationBranchDeleted error-message reword (+1 line above this join); then 495→499 by mission coord-primary-partition-lock-01KWZ46V (squash-merged 007528ddf) reworking the `coord_candidate` composition from `CoordinationWorkspace.worktree_path(repo_root, mission_slug, "")` to a direct `repo_root / ".worktrees" / f"{mission_slug}-coord" / KITTY_SPECS_DIR / mission_slug` join (#2091, invariant M-1: `CoordinationWorkspace.worktree_path` now REQUIRES a non-empty mid8 and would raise `CoordinationWorkspaceIdentityUnresolved` before this more specific fail-closed `StatusReadPathNotFound` could raise) — still the same diagnostic-only, no-FS-sink `raise` payload, disposition unchanged) |
| coordination/surface_resolver.py:504 | _coord_mid8 | primary_candidate = repo_root / KITTY_SPECS_DIR / mission_sl… | mission_slug | Path-join (/) | unreachable | Same fail-closed `raise` payload (`primary_candidate=…`); diagnostic Path, no FS sink. (line shifted by mission 01KVGCE8 collapse; then 523→477 by mission 01KVN754 WP04; then 477→492 by 01KVPR00 WP03; then 492→494 by 01KVPR00 WP08/WP09; then 494→499 by mission 01KVRJ6P WP02 FR-005 frozenset collapse; then 499→498 by 3.2.3-coord-surface-regressions #2119/#2125 retrospective-home docstring/error-prose edit in `_coord_mid8`; then 498→499 by mission single-authority-resolution-gates-01KW1P0F WP04 routing `resolve_status_surface_with_anchor` through `_canonicalize_primary_read_handle`; then 499→500 by PR #2277 reliability-papercut-sweep CoordinationBranchDeleted error-message reword (+1 line above this join); then 500→504 by mission coord-primary-partition-lock-01KWZ46V (squash-merged 007528ddf) expanding the sibling `coord_candidate` join above from a single-call form into a 5-line composed `Path` expression (#2091 rework, same commit) — same `primary_candidate` join, only the line drifted, disposition unchanged) |
| migration/mission_state.py:1054 | _repair_mission | repo_root | run_id | Path-join (/) | trusted-source | `run_id = _compute_run_id(...)` is a SHA-256 hex digest (16 chars) derived deterministically from repo-local file content hashes — it is never a CLI argument or external input. The segment is safe by construction. (line shifted 1053→1054 by mission write-surface-coherence-01KVTVZS — same join, only the line drifted) |
| missions/_read_path_resolver.py:1239 | primary_feature_dir_for_mission | primary_dir : Path = get_main_repo_root ( repo_root ) / KITT… | mission_slug | Path-join (/) | routed-through-seam | `primary_feature_dir_for_mission` calls `assert_safe_path_segment(mission_slug)` immediately before `get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug`. Seam present. (line shifted +130 by mission 01KVJPEQ; then +103 by mission 01KVN754 coord_feature_dir/probe_coord_state extraction; then +125 by 01KVN754 WP05 read-path EMPTY/DELETED fold + DELETED hard-fail block; then +16 by PR #2065 read_primary_meta canonicalize-on-miss fix; then 885→1103 by 01KVPR00 WP03/WP04; then 1103→1162 by 01KVPR00 WP08/WP09 candidate_feature_dir topology threading; then 1162→1244 by 01KVRJ6P WP06 classify_from_meta read-path boundary topology absorption; then 1244→1240 by 01KVRJ6P WP17 deleting the 6th coord-routing predicate `_topology_routes_through_coord` + the now-unused `import json` (−4 lines); then 1240→1239 by mission implement-loop-coord-authority-completion-01KW2E7A (#2160) deleting the now-unused `FEATURE_CONTEXT_UNRESOLVED_CODE` module constant (−1 line) — callsite semantically unchanged, seam still present) |
| post_merge/review_artifact_consistency.py:59 | _artifact_dirs_for_wp | exact = tasks_dir / wp_id | wp_id | Path-join (/) | unreachable | `_artifact_dirs_for_wp`: `tasks_dir / wp_id` used only for `.is_dir()` + an `iterdir()` name-prefix filter; no path is opened/written from the raw join, and a traversal `wp_id` fails the `.is_dir()` probe. Read-only existence guard. |
| review/arbiter.py:388 | _find_review_cycle_artifact | wp_subdir = tasks_dir / wp_id | wp_id | Path-join (/) | unreachable | `_find_review_cycle_artifact`: `tasks_dir / wp_id` used for `.exists()` + `.glob("review-cycle-*.md")` only; returns a discovered child path, never opens the raw join. |
| review/arbiter.py:523 | get_arbiter_overrides_for_wp | wp_subdir = tasks_dir / wp_id | wp_id | Path-join (/) | unreachable | `get_arbiter_overrides_for_wp`: `tasks_dir / wp_id` used for `.exists()` + `.glob` reads only; no write, no open of the raw join. |
| review/baseline.py:215 | capture_baseline | artifact_dir = feature_dir / / wp_slug | wp_slug | Path-join (/) | trusted-source | `feature_dir / "tasks" / wp_slug`; `wp_slug` is the WP task-file slug (derived on-disk filename), `feature_dir` supplied trusted. Read/cache of `baseline-tests.json`. |
| review/cycle.py:193 | resolve_review_cycle_pointer | candidate_feature_dir_for_mission ( repo_root , parts . miss… | wp_slug | Path-join (/) | routed-through-seam | Canonical `review-cycle://` parse: `validate_review_cycle_pointer` validates `mission_slug`/`wp_slug`/`filename`; `mission_slug` additionally folded through `candidate_feature_dir_for_mission` (the shared write-seam resolver, propagates `MissionSelectorAmbiguous` — no silent pick, C-009) before `/ "tasks" / wp_slug / filename`. Seam present. (NEW row surfaced by mission retrospective-durable-home-01KVYM1W #2136/#2164 cure routing the review-cycle pointer through the canonical fold instead of a raw `kitty-specs/<slug>` join.) |
| review/cycle.py:231 | resolve_review_cycle_pointer | candidate = ( common_dir / / / mission_slug / wp_slug / file… | wp_slug | Path-join (/) | routed-through-seam | Legacy `feedback://` parse: `mission_slug`/`wp_slug`/`filename` each pass `_validate_segment` → `assert_safe_path_segment` before the join. Seam present. (line shifted 185→231 by mission retrospective-durable-home-01KVYM1W #2136/#2164 cure adding the canonical review-cycle:// fold above this legacy branch.) |
| status/aggregate.py:514 | MissionStatus._find_meta_path | raw_meta = primary_dir / _META_JSON_FILENAME | mission_slug | Path-join (/) | routed-through-seam | [inventory-only] `_find_meta_path`: reached only from `MissionStatus.load`, which calls `_validate_mission_slug` → `assert_safe_path_segment` (raises `InvalidMissionSlug`) at line 228 before any path composition. Seam present. |
| status/aggregate.py:762 | MissionStatus.save | meta_path = diag_primary / _META_JSON_FILENAME , | mission_slug | Path-join (/) | routed-through-seam | [inventory-only] `self.mission_slug` on a `MissionStatus` instance constructed via `load` (slug already validated at construction, line 228); path composed only for a `MissionMetadataUnavailable` diagnostic. |
| status/aggregate.py:763 | MissionStatus.save | primary_candidate = diag_primary , | mission_slug | Path-join (/) | routed-through-seam | [inventory-only] Same validated-at-construction `self.mission_slug`; `primary_candidate` diagnostic Path. |
| status/lifecycle.py:427 | generate_lifecycle_json | output_dir = derived_dir / mission_slug | mission_slug | Path-join (/) | routed-through-seam | `generate_lifecycle_json`: `mission_slug = lifecycle.mission_slug or feature_dir.name`; `lifecycle.mission_slug` derives from the snapshot sanitised by `reducer.safe_mission_slug` (reducer.py:162). Seam present. |
| status/progress.py:219 | generate_progress_json | output_dir = derived_dir / mission_slug | mission_slug | Path-join (/) | routed-through-seam | `generate_progress_json`: `mission_slug = snapshot.mission_slug or feature_dir.name`; `snapshot.mission_slug` sanitised by `reducer.safe_mission_slug`. Seam present. |
| status/store.py:222 | _SlugResolver.resolve | meta_path = self . _mission_specs_root / mission_slug / | mission_slug | Path-join (/) | routed-through-seam | `MissionIdResolver.resolve`: at line 213 `_is_safe_slug(mission_slug)` → `assert_safe_path_segment` validates the slug fail-closed before this join. Additionally, `_is_contained` (called at line 223) validates the *resolved* path via `ensure_within_any`, catching symlink escapes (FR-002). Both grammar and containment seams present. |
| status/views.py:92 | write_derived_views | output_dir = derived_dir / mission_slug | mission_slug | Path-join (/) | routed-through-seam | `write_derived_views`: `mission_slug = snapshot.mission_slug or feature_dir.name`; `snapshot.mission_slug` sanitised by `reducer.safe_mission_slug` before the `derived_dir / mission_slug` `.mkdir()` + writes. Seam present. |
| status/views.py:266 | materialize_if_stale | feature_derived = derived_dir / mission_slug | mission_slug | Path-join (/) | routed-through-seam (TODO) | **RESOLVED at source by WP02 (FR-009).** `materialize_and_refresh_views`: `mission_slug = _stale_check_slug(feature_dir)` → `resolve_mission_identity`, which now routes the `meta.json` slug through `safe_mission_slug(..., feature_dir.name)` (fail-closed). The matcher still flags this join because the seam is **upstream** (cross-function flow is a documented RULESET known-FN), not at the join site. Closed — verified by the WP02 mutation review (reverting the chokepoint made the hostile-meta test create an escaped dir). TODO tag retained only as the matcher-per-site-seam artifact. |
| mission_metadata.py:458 | write_meta | atomic_write ( meta_path , content ) | meta["mission_slug"] (via feature_dir) | atomic_write(...) | routed-through-seam (TODO) | [inventory-only] **RESOLVED by WP02 (FR-009).** `resolve_mission_identity` now sanitises the `meta.json` slug via `safe_mission_slug` before it can key any downstream path; `write_meta`'s `feature_dir / "meta.json"` is keyed off the (now-trusted) slug. Inventory-only assertion (RULESET §6); the matcher cannot trace the source-level seam across functions, so the row is retained as a known-FN artifact, not an open hole. |

## Disposition summary

| disposition | count | meaning |
| --- | --- | --- |
| routed-through-seam | 10 | already safe (seam cited) |
| routed-through-seam (TODO) | 7 | 2 RESOLVED-at-source by WP02 (FR-009; matcher-per-site artifact) + 5 deferred CLI-arg low-risk (follow-up #2037) |
| trusted-source | 6 | derived directory-name / on-disk index / SHA-256 hex provenance |
| unreachable | 8 | no FS open/write reachable with an untrusted segment |
| **total** | **31** | dispositioned rows in the sink table |

Of the 31 rows, 26 are AST-discovered (the live matcher prints
the exact discovered count each run) and 5 are `[inventory-only]`
known-false-negative rows (the FR-009 `mission_metadata.py` write-path + four
cross-function diagnostics the matcher cannot trace across a boundary seam).
`audit.py` asserts both directions: every AST-discovered row appears here
(undercount) AND every non-tagged row still maps to a live sink (overcount).

**WP02/WP03 fixes applied:** The following joins were removed from the discovery
set by routing through the canonical seam (no longer discovered by `audit.py`):
- `dossier/drift_detector.py` — `assert_safe_path_segment` before `dossiers/<slug>` mkdir/open
- `dossier/snapshot.py` — `assert_safe_path_segment` before `dossiers/<slug>` mkdir/open
- `events/decision_log.py` — `assert_safe_path_segment` before `KITTY_SPECS_DIR/<slug>` open
- `migration/mission_state.py` — `assert_safe_path_segment` before quarantine `<slug>` join (run_id remains trusted-source)
- `review/arbiter.py` — `assert_safe_path_segment` before `tasks/<wp_id>` mkdir + `write_text_within_directory`

## Routing of the remaining `routed-through-seam (TODO)` rows

- **WP02 (status/) — DONE:** `status/views.py:266` and the FR-009
  `mission_metadata.py:458` `meta.json` write-path bypass are **closed at source**
  by WP02 (`resolve_mission_identity` → `safe_mission_slug`, fail-closed). They
  remain tagged `(TODO)` only because the matcher inspects the join site and the
  seam is upstream (cross-function flow — a documented RULESET known-FN), not
  because the vulnerability is open. Verified by the WP02 mutation review.
- **Deferred (CLI-arg, low-risk) → follow-up #2037:** `cli/commands/agent/mission_finalize.py:199`,
  `cli/commands/agent/tasks_move_task.py:206`, `cli/commands/decision.py:470`,
  `merge/ordering.py:297` (relocated from `cli/commands/merge.py:1144` by mission
  #2057's behavior-preserving god-module decomposition), and its `merge/ordering.py:304`
  sibling (the canonical `load_meta` read added by mission read-surface-ssot-closeout-01KWZV91)
  — CLI-sourced (`--mission`)
  slugs with only read-only / existence-probe sinks; lower-severity threat model
  than the server-side content paths. Tracked for hardening in #2037 (parent #1868).

## T005 — `status/aggregate.py` raise-guard + composed reads (FR-003)

`MissionStatus._validate_mission_slug` (aggregate.py:345) delegates to
`assert_safe_path_segment` and **raises `InvalidMissionSlug`** on any unsafe
slug. It is called at the top of `MissionStatus.load` (line 228) *before* any
path composition, so every downstream composed read — `_find_meta_path`
(`primary_dir / "meta.json"`, line 431; the `specs_dir.glob(f"{mission_slug}-*/
meta.json")` first-match glob, line 473) and the `_read_meta` `meta_path.
read_text` (line 375) — runs on an already-validated slug. **Disposition:**
`routed-through-seam` (the load-boundary raise-guard is the seam). The
historical silent-first-match glob (line 473) is a *selection* ambiguity
(S8 follow-up), **not** a traversal hole — the slug is already grammar-checked,
so the glob cannot escape the specs root.

## Anti-overfit demonstration (T004)

The seed-set is data. Temporarily adding `"filename"` to
`UNTRUSTED_SEGMENT_NAMES` and re-discovering surfaces **+35 new joins** across
unrelated modules absent from this table — e.g.
`cli/commands/charter/_status_collectors.py:72`, `cli/commands/doctor.py:281`,
`dashboard/handlers/features.py:408`, `doctrine/sources/api_source.py:179` —
proving the matcher generalises rather than hard-coding the known list. The
symbol is **not** committed to the seed-set (`filename` is not a mission-domain
untrusted segment in this audit's scope); the experiment is reproducible by
adding it to `audit.py`'s `UNTRUSTED_SEGMENT_NAMES` and re-discovering.

## Audited-surface list (WP04 anchor)

The stable surface list WP04's guard anchors on is maintained as a separate
machine-readable artifact: `audited-surfaces.md`.
