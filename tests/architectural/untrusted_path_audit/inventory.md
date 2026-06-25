# Untrusted-segment → FS-sink inventory (WP01 / FR-003, FR-004)

Generated input: `python tests/architectural/untrusted_path_audit/audit.py`
walks `src/specify_cli` and self-asserts this table (count consistency +
known-candidate presence + FR-009 `meta.json` row). Dispositions are
human-verified against the cited source — see `RULESET.md` for the vocabulary
and the Named-untrusted rule.

**Locator convention:** `package/module.py:line` matches the AST-discovered
line. The `mission_metadata.py` row is an inventory-only assertion (FR-009
false-negative class — see RULESET §6).

**Note (WP02/WP03 update):** WP02 added `_is_contained` to `status/store.py`
(new `mission_slug` join at :222; old :184 shifted out of scope) and WP03
added seam calls to `dossier/`, `events/`, `migration/`, and `review/arbiter`
(those joins are no longer discovered). Line numbers updated accordingly.

## Sink table

| file:line | untrusted source | sink op | disposition | rationale |
| --- | --- | --- | --- | --- |
| audit/engine.py:88 | resolved.mission_slug | Path-join (/) | unreachable | `scan_root / resolved.mission_slug` is consumed only by a `.is_dir()` existence filter that returns an empty `frozenset` on miss — no file is opened/written; a traversal slug simply fails `.is_dir()`. (Named-untrusted rule: a value that IS `mission_slug` is dispositioned `unreachable`, not `trusted-source`, even though `resolve_mission` resolves it against the on-disk index.) |
| cli/commands/agent/mission_finalize.py:194 | mission_slug | Path-join (/) | routed-through-seam (TODO) | `--mission` slug joined to `.kittify/dossiers/<slug>/snapshot-latest.json` as a finalize commit candidate; no `assert_safe_path_segment` on this CLI path. Deferred (CLI-arg, read-only candidate list). (line shifted +8 by mission 01KVMBD6 #2056 god-tag comment + de-god extraction; then 320→321 by mission single-authority-topology-cleanup-01KVRJ6P WP16 commit-target enum eradication, FR-001b; then 321→317 by mission write-surface-coherence-01KVTVZS kind-aware placement refactor; then 317→318 by mission gate-read-surface-completion-01KVW9B0 WP00 finalize-tasks write-surface re-point extracting `_collect_finalize_artifacts`; then RELOCATED mission.py → mission_finalize.py by mission decompose-mission-god-module-01KVXHF8 #2056 finalize-tasks seam extraction (WP07), settling at :194 after the same mission's whole-tree-mypy redundant-cast removal; then re-anchored on upstream/main with #2135 doctor.py decomposition (no mission_finalize.py impact) — same sink, moved out of the shim into the seam) |
| cli/commands/agent/tasks.py:1046 | mission_slug | Path-join (/) | routed-through-seam (TODO) | `worktree_kitty / mission_slug / "tasks"` `.exists()` probe from a raw `--mission` slug; reachable, unguarded. Deferred (CLI-arg, .exists() probe only). (line shifted −11 by mission 01KVJPEQ read-side adoption rebase; then +2 by mission 01KVMBD6 #2058 god-tag comment; then 1902→1933 by mission single-planning-surface-authority-01KVPR00 WP06 map-requirements read-surface consolidation; then 1933→1932 by WP03 import shrink; then 1932→1935 by mission single-authority-topology-cleanup-01KVRJ6P WP16 commit-target enum eradication, FR-001b; then 1935→1972 by mission write-surface-coherence-01KVTVZS kind-aware read-path resolver additions; then 1972→1046 by mission decompose-agent-tasks-god-module-01KVWVAR #2058 seam extraction (helper bodies moved into tasks_*.py modules, shrinking tasks.py) — same sink, only the line drifted) |
| cli/commands/agent/workflow.py:919 | wp_slug | Path-join (/) | trusted-source | `wp_slug` is the WP file stem (`wp.path.stem`) — a derived on-disk filename, not external input; `feature_dir / "tasks" / wp_slug` then `.exists()`/`.glob`. (line shifted −2 by mission 01KVJPEQ workflow.py cascade migration) |
| cli/commands/agent/workflow.py:1598 | wp_slug | Path-join (/) | trusted-source | Same `wp.path.stem` provenance; read-only `ReviewCycleArtifact.latest(...)`. (line shifted −2 by mission 01KVJPEQ) |
| cli/commands/agent/workflow.py:2640 | wp_slug | Path-join (/) | trusted-source | `wp_slug = wp.path.stem`; parent `feature_dir` from `resolve_feature_dir_for_mission` → `resolve_mission_read_path` (assert_safe_path_segment). Segment derived, dir guarded. (line shifted −2 by mission 01KVJPEQ) |
| cli/commands/decision.py:464 | mission_slug | Path-join (/) | routed-through-seam (TODO) | `repo_root / KITTY_SPECS_DIR / mission_slug` then `load_meta(...)` read; raw `--mission` slug, no seam at this site. Deferred (CLI-arg, load_meta read). |
| merge/done_bookkeeping.py:419 | mission_slug | Path-join (/) | unreachable | Builds a *relative* `kitty-specs/<slug>/status.events.jsonl` only to stringify into a `git show <ref>:<path>` argument; no local FS open — git resolves inside the tree object. (relocated VERBATIM from `cli/commands/merge.py:613` into the `_target_bookkeeping_status_paths` seam by mission #2057 decompose-merge-god-module-01KVXHDK WP08 — behavior-preserving god-module decomposition, disposition unchanged) |
| merge/done_bookkeeping.py:421 | mission_slug | Path-join (/) | unreachable | Same git-ref-argument path as :419 (worktree-rewrite branch); no FS sink. (relocated VERBATIM from `cli/commands/merge.py:615` by mission #2057 WP08 — same sink, only the file/line moved, disposition unchanged) |
| merge/ordering.py:297 | mission_slug | Path-join (/) | routed-through-seam (TODO) | `scan_specs / mission_slug / "meta.json"` then `read_text()` after `.exists()`; raw `--mission`/target slug, no seam. Deferred (CLI-arg, .exists()+read_text). (relocated VERBATIM from `cli/commands/merge.py:1144` into the mission-number bake cluster by mission #2057 decompose-merge-god-module-01KVXHDK WP07 — behavior-preserving god-module decomposition, disposition unchanged) |
| coordination/surface_resolver.py:494 | mission_slug | Path-join (/) | unreachable | Path composed solely to populate `StatusReadPathNotFound(coord_candidate=…)` inside a `raise`; never opened/written — fail-closed diagnostic payload. (line shifted by mission 01KVGCE8 collapse; then 518→472 by mission 01KVN754 WP04 coord-empty Option B deletion of CoordinationWorktreeEmpty + 2 helpers; then 472→487 by 01KVPR00 WP03; then 487→489 by 01KVPR00 WP08/WP09 surface-topology gating; then 489→494 by mission 01KVRJ6P WP02 FR-005 collapse of `_COORD_SURFACE_TOPOLOGIES` + import-block widen — same diagnostic join, only the line drifted, disposition unchanged) |
| coordination/surface_resolver.py:499 | mission_slug | Path-join (/) | unreachable | Same fail-closed `raise` payload (`primary_candidate=…`); diagnostic Path, no FS sink. (line shifted by mission 01KVGCE8 collapse; then 523→477 by mission 01KVN754 WP04; then 477→492 by 01KVPR00 WP03; then 492→494 by 01KVPR00 WP08/WP09; then 494→499 by mission 01KVRJ6P WP02 FR-005 frozenset collapse — same diagnostic join, only the line drifted, disposition unchanged) |
| migration/mission_state.py:1054 | run_id | Path-join (/) | trusted-source | `run_id = _compute_run_id(...)` is a SHA-256 hex digest (16 chars) derived deterministically from repo-local file content hashes — it is never a CLI argument or external input. The segment is safe by construction. (line shifted 1053→1054 by mission write-surface-coherence-01KVTVZS — same join, only the line drifted) |
| missions/_read_path_resolver.py:1240 | mission_slug | Path-join (/) | routed-through-seam | `primary_feature_dir_for_mission` calls `assert_safe_path_segment(mission_slug)` immediately before `get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug`. Seam present. (line shifted +130 by mission 01KVJPEQ; then +103 by mission 01KVN754 coord_feature_dir/probe_coord_state extraction; then +125 by 01KVN754 WP05 read-path EMPTY/DELETED fold + DELETED hard-fail block; then +16 by PR #2065 read_primary_meta canonicalize-on-miss fix; then 885→1103 by 01KVPR00 WP03/WP04; then 1103→1162 by 01KVPR00 WP08/WP09 candidate_feature_dir topology threading; then 1162→1244 by 01KVRJ6P WP06 classify_from_meta read-path boundary topology absorption; then 1244→1240 by 01KVRJ6P WP17 deleting the 6th coord-routing predicate `_topology_routes_through_coord` + the now-unused `import json` (−4 lines) — callsite semantically unchanged, seam still present) |
| post_merge/review_artifact_consistency.py:59 | wp_id | Path-join (/) | unreachable | `_artifact_dirs_for_wp`: `tasks_dir / wp_id` used only for `.is_dir()` + an `iterdir()` name-prefix filter; no path is opened/written from the raw join, and a traversal `wp_id` fails the `.is_dir()` probe. Read-only existence guard. |
| review/arbiter.py:388 | wp_id | Path-join (/) | unreachable | `_find_review_cycle_artifact`: `tasks_dir / wp_id` used for `.exists()` + `.glob("review-cycle-*.md")` only; returns a discovered child path, never opens the raw join. |
| review/arbiter.py:523 | wp_id | Path-join (/) | unreachable | `get_arbiter_overrides_for_wp`: `tasks_dir / wp_id` used for `.exists()` + `.glob` reads only; no write, no open of the raw join. |
| review/baseline.py:215 | wp_slug | Path-join (/) | trusted-source | `feature_dir / "tasks" / wp_slug`; `wp_slug` is the WP task-file slug (derived on-disk filename), `feature_dir` supplied trusted. Read/cache of `baseline-tests.json`. |
| review/cycle.py:185 | wp_slug | Path-join (/) | routed-through-seam | Legacy `feedback://` parse: `mission_slug`/`wp_slug`/`filename` each pass `_validate_segment` → `assert_safe_path_segment` (lines 140-141) before the join. Seam present. |
| review/cycle.py:225 | wp_slug | Path-join (/) | routed-through-seam | `common_dir / "spec-kitty" / "feedback" / mission_slug / wp_slug / filename`; all three segments validated via `_validate_segment` (lines 211-213) before this join. Seam present. |
| status/aggregate.py:430 | mission_slug | Path-join (/) | routed-through-seam | `_find_meta_path`: reached only from `MissionStatus.load`, which calls `_validate_mission_slug` → `assert_safe_path_segment` (raises `InvalidMissionSlug`) at line 228 before any path composition. Seam present. |
| status/aggregate.py:668 | mission_slug | Path-join (/) | routed-through-seam | `self.mission_slug` on a `MissionStatus` instance constructed via `load` (slug already validated at construction, line 228); path composed only for a `MissionMetadataUnavailable` diagnostic. |
| status/aggregate.py:669 | mission_slug | Path-join (/) | routed-through-seam | Same validated-at-construction `self.mission_slug`; `primary_candidate` diagnostic Path. |
| status/lifecycle.py:427 | mission_slug | Path-join (/) | routed-through-seam | `generate_lifecycle_json`: `mission_slug = lifecycle.mission_slug or feature_dir.name`; `lifecycle.mission_slug` derives from the snapshot sanitised by `reducer.safe_mission_slug` (reducer.py:162). Seam present. |
| status/progress.py:219 | mission_slug | Path-join (/) | routed-through-seam | `generate_progress_json`: `mission_slug = snapshot.mission_slug or feature_dir.name`; `snapshot.mission_slug` sanitised by `reducer.safe_mission_slug`. Seam present. |
| status/store.py:222 | mission_slug | Path-join (/) | routed-through-seam | `MissionIdResolver.resolve`: at line 213 `_is_safe_slug(mission_slug)` → `assert_safe_path_segment` validates the slug fail-closed before this join. Additionally, `_is_contained` (called at line 223) validates the *resolved* path via `ensure_within_any`, catching symlink escapes (FR-002). Both grammar and containment seams present. |
| status/views.py:92 | mission_slug | Path-join (/) | routed-through-seam | `write_derived_views`: `mission_slug = snapshot.mission_slug or feature_dir.name`; `snapshot.mission_slug` sanitised by `reducer.safe_mission_slug` before the `derived_dir / mission_slug` `.mkdir()` + writes. Seam present. |
| status/views.py:266 | mission_slug | Path-join (/) | routed-through-seam (TODO) | **RESOLVED at source by WP02 (FR-009).** `materialize_and_refresh_views`: `mission_slug = _stale_check_slug(feature_dir)` → `resolve_mission_identity`, which now routes the `meta.json` slug through `safe_mission_slug(..., feature_dir.name)` (fail-closed). The matcher still flags this join because the seam is **upstream** (cross-function flow is a documented RULESET known-FN), not at the join site. Closed — verified by the WP02 mutation review (reverting the chokepoint made the hostile-meta test create an escaped dir). TODO tag retained only as the matcher-per-site-seam artifact. |
| mission_metadata.py:328 | meta["mission_slug"] (via feature_dir) | atomic_write(...) | routed-through-seam (TODO) | **RESOLVED by WP02 (FR-009).** `resolve_mission_identity` now sanitises the `meta.json` slug via `safe_mission_slug` before it can key any downstream path; `write_meta`'s `feature_dir / "meta.json"` is keyed off the (now-trusted) slug. Inventory-only assertion (RULESET §6); the matcher cannot trace the source-level seam across functions, so the row is retained as a known-FN artifact, not an open hole. |

## Disposition summary

| disposition | count | meaning |
| --- | --- | --- |
| routed-through-seam | 10 | already safe (seam cited) |
| routed-through-seam (TODO) | 6 | 2 RESOLVED-at-source by WP02 (FR-009; matcher-per-site artifact) + 4 deferred CLI-arg low-risk (follow-up #2037) |
| trusted-source | 5 | derived directory-name / on-disk index / SHA-256 hex provenance |
| unreachable | 8 | no FS open/write reachable with an untrusted segment |
| **total** | **29** | 28 AST-discovered rows + 1 inventory-only FR-009 row |

`mission_metadata.py:328` is the inventory-only FR-009 row (not AST-discovered);
the 28 AST-discovered rows + this assertion (29 total) are all asserted by
`audit.py` (count consistency + known-candidate presence + FR-009 tag).

**WP02/WP03 fixes applied:** The following joins were removed from the discovery
set by routing through the canonical seam (no longer discovered by `audit.py`):
- `dossier/drift_detector.py:211,233` — `assert_safe_path_segment` before `dossiers/<slug>` mkdir/open
- `dossier/snapshot.py:142,160` — `assert_safe_path_segment` before `dossiers/<slug>` mkdir/open
- `events/decision_log.py:99` — `assert_safe_path_segment` before `KITTY_SPECS_DIR/<slug>` open
- `migration/mission_state.py:1052` — `assert_safe_path_segment` before quarantine `<slug>` join (run_id now at :1054 as trusted-source)
- `review/arbiter.py:483` — `assert_safe_path_segment` before `tasks/<wp_id>` mkdir + `write_text_within_directory`

## Routing of the remaining `routed-through-seam (TODO)` rows

- **WP02 (status/) — DONE:** `status/views.py:266` and the FR-009
  `mission_metadata.py:328` `meta.json` write-path bypass are **closed at source**
  by WP02 (`resolve_mission_identity` → `safe_mission_slug`, fail-closed). They
  remain tagged `(TODO)` only because the matcher inspects the join site and the
  seam is upstream (cross-function flow — a documented RULESET known-FN), not
  because the vulnerability is open. Verified by the WP02 mutation review.
- **Deferred (CLI-arg, low-risk) → follow-up #2037:** `cli/commands/agent/mission_finalize.py:194`,
  `cli/commands/agent/tasks.py:1046`, `cli/commands/decision.py:464`,
  `merge/ordering.py:297` (relocated from `cli/commands/merge.py:1144` by mission
  #2057's behavior-preserving god-module decomposition) — CLI-sourced (`--mission`)
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
