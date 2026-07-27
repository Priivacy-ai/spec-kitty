---
title: Read-side placement-seam classification ledger
description: "Per-site verdicts (migrate-fail-loud / stay-lenient / sanction-infra) for every production call site that bypasses PlacementSeam.read_dir(kind), the spine WP03-WP08 of the read-side-placement-seam-migration mission consume."
doc_status: active
updated: '2026-07-27'
type: reference
related:
- docs/architecture/execution-lanes.md
---

# Read-side placement-seam classification ledger

`PlacementSeam.read_dir(kind)` (`src/mission_runtime/resolution.py:1404`, which
delegates to `resolve_artifact_surface` at `:1634`) is the one kind-aware,
fail-loud read authority: it raises `CoordinationBranchDeleted` when a
COORD-partition kind is required but the mission's declared coordination
branch has been deleted from git, and it resolves identically to the
historical primitives for every other cell. PR #2920 hardened that seam but
did not migrate its ~60 pre-existing bypassers.

This ledger is the classification spine for the read-side-placement-seam-migration
mission (WP02): it enumerates **every** production call site of the two bypass
primitives defined in `src/specify_cli/missions/_read_path_resolver.py` —

- `candidate_feature_dir_for_mission(repo_root, mission_slug)` — **kind-blind**
  (no `MissionArtifactKind` at all; always topology-routed).
- `resolve_planning_read_dir(repo_root, mission_slug, kind=K)` — **kind-aware
  but lenient** (never raises `CoordinationBranchDeleted`).

— and assigns each site exactly one verdict: **migrate-fail-loud** (route
through `PlacementSeam.read_dir(kind)`), **stay-lenient** (diagnostic/audit
path that must tolerate a half-materialized or deleted coord branch; recorded
as a future allow-list entry with rationale), or **sanction-infra** (the read
authority's own implementation; migrating it would be self-referential).

## Method (how this census was built)

1. `grep -rl -E "candidate_feature_dir_for_mission|resolve_planning_read_dir" src --include="*.py"`
   found **62 files**. Removing the two DEFINITION modules
   (`src/specify_cli/missions/_read_path_resolver.py`, which defines both
   primitives, and `src/mission_runtime/resolution.py`, which is the seam
   itself and calls `resolve_planning_read_dir` once internally to canonicalize
   a handle) leaves **60 consumer files** — this is the file-level census this
   ledger's row count reconciles against (§ Coverage reconciliation).
2. A textual line grep (`symbol\(`) over those 60 files found 93 apparent call
   sites. **3 were false positives** — prose/docstring mentions that happen to
   contain a literal `symbol(...)` substring (one plain `#` comment, two inside
   triple-quoted docstrings) — caught by cross-checking against an `ast.walk`
   census (below), not by the textual grep alone.
3. An AST-based census (`ast.parse` + `ast.walk` over every `ast.Call` node,
   matching `Name.id` or `Attribute.attr` against the two symbol names) gives
   the authoritative, zero-false-positive site list: **90 real call sites**
   across **54 files** (the other 6 of the 60 have a grep hit but zero real
   `ast.Call` sites — a comment or docstring mention only). This is exactly
   the discrimination the future structural gate (`test_no_read_side_bypass.py`,
   WP08) must make via its own AST walk — the bite test ("a prose/docstring
   mention stays green") this ledger's method already had to get right.
4. Of the 90 real sites: **31 kind-blind** (`candidate_feature_dir_for_mission`)
   and **59 kind-aware** (`resolve_planning_read_dir`).

## Coverage reconciliation

```
grep -rl -E "candidate_feature_dir_for_mission|resolve_planning_read_dir" src --include="*.py" | wc -l
  → 62
minus the 2 definition modules (_read_path_resolver.py, mission_runtime/resolution.py)
  → 60  == this ledger's file-row count (§ Full ledger, every one of the 60 files
          appears exactly once, either in a verdict table or the "no real call
          site" table)
AST-verified real call sites across those 60 files: 90  == the sum of every
  per-file "sites" column below (72 migrate + 16 stay-lenient + 2 sanction-infra)
```

100% of the 60 consumer files and 100% of the 90 real call sites are
classified below. No row carries an `unknown` verdict.

File counts below are **site-containing** (a mixed file such as
`tasks_status_cmd.py` appears in both migrate and stay-lenient).
`54 = 42 migrate-containing + 11 stay-containing − 1 mixed + 2 sanction`.

## Summary

| Verdict | Sites | Files (site-containing) |
|---|---|---|
| migrate-fail-loud | 72 | 42 |
| stay-lenient | 16 | 11 |
| sanction-infra | 2 | 2 |
| **Total real call sites** | **90** | **54** |
| No real call site (docstring/comment mention only) | 0 | 6 |
| **Grand total (file-level census)** | | **60** |

- **Ambiguous — reviewer confirm** (defaulted to the safer disposition, per
  mission instructions): 9 stay-lenient sites — `tasks_move_task.py:2368`,
  `tasks_status_cmd.py:160`, `archive.py:65`, `reconcile.py:126`,
  `retrospect.py:110`, `dossier/api.py:227,397,435`, `manifest.py:272` —
  plus `next_cmd.py:377` (defaulted **migrate-fail-loud**, flagged for a
  dead-except-clause check). See the per-row rationale for each.
- **Multi-kind readers flagged for split**: `archive.py:65` and
  `reconcile.py:126` — one resolved dir feeds more than one downstream
  artifact kind read (see rows). Both stay lenient until the owning
  migration WP can split them by kind (blind single-kind swap would be a
  false precision).
- **Research hard-case note**: `_cutover_doctor.py` is named in research.md
  as a diagnostic/audit reader, but it has **zero** calls to either bypass
  primitive (it delegates to `migration.runtime_state_cutover.cutover_repo`);
  correctly absent from this census.
- **Sanctioned set** (mirrors `resolution.py`'s own self-exclusion style, and
  the write-gate's `BOUNDARY_SANCTIONED_MODULES` per-file rationale
  convention in `tests/architectural/_placement_whole_tree_scan.py`):
  - `src/specify_cli/missions/_read_path_resolver.py` — the primitive
    authority itself (excluded from the consumer census entirely, per FR-003 —
    it does not call itself).
  - `src/specify_cli/coordination/surface_resolver.py` — canonical surface
    resolver infra (FR-003 explicit).
  - `src/mission_runtime/write_target_degrade.py` — already covered by the
    `src/mission_runtime/` `BOUNDARY_SANCTIONED_PREFIXES` blanket on the
    write-side gate; carries its own per-file rationale here too so the
    read-side gate's sanctioned-module test can assert it directly, matching
    the "carries a rationale" discipline `test_sanctioned_modules_carry_a_rationale`
    already enforces on the write side.
- **Doctrine-named stay-lenient modules** (research.md hard cases, honoured
  verbatim): `_coordination_doctor.py`, `dashboard/scanner.py`,
  `status/aggregate.py`, `retrospective/summary.py`, and the `retrospect.py`
  corpus-walk classifier — every real call site in these modules stays
  lenient regardless of whether the specific declared kind is PRIMARY-partition
  (behaviorally risk-free) or COORD-partition (real fail-loud risk), because
  the module's *purpose* — never crash a corpus scan or audit report — is the
  invariant, not the incidental safety of today's kind assignment.
- **`workflow.py` correction**: research.md's pre-planning grounding squad
  counted **17** raw grep hits for `cli/commands/agent/workflow.py`. The
  AST-verified count is **7 real call sites** (2 of the original textual hits,
  at lines 843 and 1447, are docstring prose describing the very migration
  this ledger performs, not real calls). Recorded here so WP03 does not
  over-scope its `workflow.py` slice against the inflated textual figure.

## Full ledger

Columns: `file` · `symbol(s)` · `sites` (file:line) · `family` · `verdict` ·
`kind` (target `MissionArtifactKind` for a kind-blind migrate site; `n/a` for
sanction/stay-lenient/already-kind-aware) · `cluster` (which migration WP
consumes this row) · `rationale`.

### Sanction-infra

| file | symbol(s) | sites | family | verdict | kind | cluster | rationale |
|---|---|---|---|---|---|---|---|
| `src/mission_runtime/write_target_degrade.py` | `candidate_feature_dir_for_mission` | 1 (:183) | kind-blind | sanction-infra | n/a | N/A — sanctioned | Bootstrap-window write-target degrade helper (`resolve_write_target_or_degrade`); already excluded from the write-side whole-tree scan via the `src/mission_runtime/` `BOUNDARY_SANCTIONED_PREFIXES` blanket. Self-referential resolution infra, not a migration target (mirrors FR-003). |
| `src/specify_cli/coordination/surface_resolver.py` | `candidate_feature_dir_for_mission` | 1 (:675) | kind-blind | sanction-infra | n/a | N/A — sanctioned | The canonical surface resolver (`resolve_status_surface_with_anchor` et al.) that `candidate_feature_dir_for_mission` itself is partly built to serve; FR-003 names this module explicitly as sanctioned infra, not a bypass site awaiting a route. |

### WP03 — agent-CLI (`src/specify_cli/cli/commands/agent/**`)

| file | symbol(s) | sites | family | verdict | kind | cluster | rationale |
|---|---|---|---|---|---|---|---|
| `cli/commands/agent/mission_feature_resolution.py` | — | 0 real (grep hit only) | n/a | no-site | n/a | WP03 | Grep hit is prose (`:78,93,131,258`) describing the seam/primitives; zero `ast.Call` sites. |
| `cli/commands/agent/status.py` | `candidate_feature_dir_for_mission` | 1 (:72) | kind-blind | migrate-fail-loud | `PRIMARY_METADATA` | WP03 | Slug-canonicalization idiom (`legacy_dir = candidate_feature_dir_for_mission(...); if legacy_dir.exists(): return legacy_dir.name`) — the SAME idiom the seam's own `resolve_artifact_surface` uses (`canonical_slug = primary_dir.name`) for handle→dir-name folding. `candidate_feature_dir_for_mission`'s own docstring states it never raises `StatusReadPathNotFound`, only `MissionSelectorAmbiguous` (unchanged either way) — migration is behavior-preserving. |
| `cli/commands/agent/tasks_dependency_graph.py` | `resolve_planning_read_dir` | 1 (:134) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` | WP03 | Builds the WP dependency graph from `tasks/` (PRIMARY-partition); genuine functional read, already kind-annotated. |
| `cli/commands/agent/tasks_map_requirements.py` | `resolve_planning_read_dir` | 2 (:312, :694) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` (both) | WP03 | `map-requirements` WP-frontmatter read. (Line 679 is a docstring restatement of the :694 call — not a third site.) |
| `cli/commands/agent/tasks_materialization.py` | `resolve_planning_read_dir` | 1 (:118) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` | WP03 | `tasks/WP*.md` materialization read. |
| `cli/commands/agent/tasks_move_task.py` | `candidate_feature_dir_for_mission` | 1 (:2368) | kind-blind | **stay-lenient** (ambiguous — reviewer confirm) | n/a | WP03 | Structurally atypical call: `repo_root` is `CoordinationWorkspace.worktree_path(...)` (an **already-resolved coord worktree path**, not the primary checkout) and the slug arg is a composed `mission_dir_name(...)`, not a raw handle — a direct probe of an already-verified coord worktree's own `status.events.jsonl`, not the seam's `repo_root`+topology contract. Defaulted lenient (no behavior change) pending a bespoke (non-mechanical) fix, not a kind-route. |
| `cli/commands/agent/tasks_parsing_validation.py` | `resolve_planning_read_dir` | 1 (:949) | kind-aware | migrate-fail-loud | `RESEARCH` | WP03 | Research-artifact dirty-tree check; explicitly documented as needing the PRIMARY leg, not the coord husk. |
| `cli/commands/agent/tasks.py` | `resolve_planning_read_dir` | 4 (:842, :943, :1155, :1303) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` (:842, :1303), `TASKS_INDEX` (:943, :1155) | WP03 | `tasks/` reads and the pre-3.0-layout boundary guard; all four already kind-annotated. |
| `cli/commands/agent/tasks_shared.py` | `candidate_feature_dir_for_mission`, `resolve_planning_read_dir` | 2 (:252, :455) | mixed | migrate-fail-loud (both) | `PRIMARY_METADATA` (:252, slug-canon idiom — same as `status.py:72`), `TASKS_INDEX` (:455) | WP03 | :252 is the same recurring slug-canonicalization idiom as `status.py:72`/`mission_type.py:413`/`next_cmd.py:377`/`merge/resolve.py:67`/`workflow.py:820` (6 near-duplicate sites — a consolidation candidate for a future helper, out of this mission's scope but worth flagging). |
| `cli/commands/agent/tasks_status_cmd.py` | `candidate_feature_dir_for_mission`, `resolve_planning_read_dir` | 2 (:160, :170) | mixed | :160 **stay-lenient** (ambiguous — reviewer confirm); :170 migrate-fail-loud | n/a (:160); `WORK_PACKAGE_TASK` (:170) | WP03 | :160 is explicitly documented as a "last-ditch fallback to the original worktree-aware path" using a **CWD-derived** `status_read_root` (not `repo_root`) "so tests / projects that stand up status files in unusual places still work." The seam is explicitly CWD-invariant by design (data-model.md) — routing this fallback through it would defeat its documented purpose. |
| `cli/commands/agent/workflow_executor.py` | `resolve_planning_read_dir`, `candidate_feature_dir_for_mission` | 2 (:1713, :1721) | mixed | migrate-fail-loud (both) | `WORK_PACKAGE_TASK` (:1713); `STATUS_STATE` (:1721) | WP03 | :1721 reads the event log to warn about dependent WPs during review — a genuine functional STATUS read (not diagnostic); fail-loud-appropriate. |
| `cli/commands/agent/workflow.py` | `candidate_feature_dir_for_mission` (3), `resolve_planning_read_dir` (4) | 7 real (:820, :855, :862, :1391, :1396, :1450, :1465) | mixed | migrate-fail-loud (all 7) | `PRIMARY_METADATA` (:820, slug-canon idiom); `WORK_PACKAGE_TASK` (:855, :1391, :1450); `STATUS_STATE` (:862, :1465 — dependency-gate/review-gate lane reads via the event log); `LANE_STATE` (:1396) | WP03 | **Hard case / own attention** (highest site-density file). See the research.md-correction note above: raw grep counted 9 hits here, 2 are docstring prose (`:843`, `:1447`) describing the exact calls at `:855`/`:1465` — only 7 are real. |

### WP04 — CLI-commands (`src/specify_cli/cli/commands/*.py` + `cli/commands/charter/_widen.py`)

| file | symbol(s) | sites | family | verdict | kind | cluster | rationale |
|---|---|---|---|---|---|---|---|
| `cli/commands/archive.py` | `candidate_feature_dir_for_mission` | 1 (:65) | kind-blind | **stay-lenient, flagged multi-kind** (ambiguous — reviewer confirm) | n/a | WP04 | `feature_dir` is an existence probe then passed into `archive_mission(feature_dir=...)` (`src/specify_cli/missions/_archive.py:300`), which threads it into BOTH `terminal_state_resolver` (a STATUS_STATE read) and `invariants_reader` (an ACCEPTANCE_MATRIX read) — a genuine multi-kind reader off one kind-blind anchor. A single-kind `PRIMARY_METADATA` swap would be false precision. Defaulted **stay-lenient** (mission ambiguous→safer rule); WP04 should split into two seam calls (`STATUS_STATE` + `ACCEPTANCE_MATRIX`) before migrating. |
| `cli/commands/charter/_widen.py` | `candidate_feature_dir_for_mission` | 1 (:54) | kind-blind | migrate-fail-loud | `PRIMARY_METADATA` | WP04 | Reads `meta.json` only (`load_meta_or_empty(feature_dir).get("mission_id")`). |
| `cli/commands/_coordination_doctor.py` | `resolve_planning_read_dir` | 2 (:933, :1057) | kind-aware | **stay-lenient** | n/a (`WORK_PACKAGE_TASK` already declared, but kept lenient by doctrine) | WP04 | Named explicitly in research.md's hard-cases list — a diagnostic tool auditing `pending_coord_reconcile` markers / live-strand findings across the corpus; both sites already catch `(ValueError, MissionSelectorAmbiguous)` and degrade to a warning finding rather than abort the doctor run. Kept lenient module-wide per doctrine, independent of this particular kind's incidental safety. |
| `cli/commands/decision.py` | — | 0 real (grep hit only) | n/a | no-site | n/a | WP04 | Grep hit at `:125` is a comment describing the STATUS-partition leg; zero `ast.Call` sites. |
| `cli/commands/merge.py` | `resolve_planning_read_dir` | 1 (:284) | kind-aware | migrate-fail-loud | `PRIMARY_METADATA` | WP04 | `--abort` teardown reading `meta.json` to discover the coord worktree's `mid8`; genuine functional read. |
| `cli/commands/mission_type.py` | `candidate_feature_dir_for_mission` | 1 (:413) | kind-blind | migrate-fail-loud | `PRIMARY_METADATA` | WP04 | Same slug-canonicalization idiom as `agent/status.py:72` (see the 6-site cluster note under `tasks_shared.py`). |
| `cli/commands/next_cmd.py` | `candidate_feature_dir_for_mission` | 1 (:377) | kind-blind | **migrate-fail-loud** (ambiguous — reviewer confirm) | `PRIMARY_METADATA` | WP04 | Same slug-canonicalization idiom, but this site's `except StatusReadPathNotFound` branch explicitly `raise`s (re-surfaces the typed error) rather than degrading — the author evidently believed this exception was reachable here. Per the primitive's own docstring it is not (only `MissionSelectorAmbiguous` propagates), so the branch is already dead; migrating to `PRIMARY_METADATA` preserves that (still dead, never reachable). Flagged so WP04 double-checks this specific site's except-clause before/after the swap. |
| `cli/commands/reconcile.py` | `candidate_feature_dir_for_mission` | 1 (:126) | kind-blind | **stay-lenient, flagged multi-kind** (ambiguous — reviewer confirm) | n/a | WP04 | `feature_dir` feeds `dossier.snapshot.load_snapshot` (reads a `.kittify/dossiers/<slug>/snapshot-latest.json` cache — no direct `MissionArtifactKind` mapping) and then a `present_projection` rebuild that hashes across several artifact kinds for drift comparison — a genuine multi-kind reader with no single clean target kind. Defaulted lenient; the fail-closed `ReconciliationResult.ERROR` return already absorbs any resolution failure gracefully, so no regression from staying put. |
| `cli/commands/research.py` | `resolve_planning_read_dir` | 2 (:95, :110) | kind-aware | migrate-fail-loud | `RESEARCH` (:95), `FINALIZED_EXECUTION_PLAN` (:110) | WP04 | Research-artifact scaffold + `plan.md` validation reads; both already kind-annotated. |
| `cli/commands/retrospect.py` | `candidate_feature_dir_for_mission` | 2 (:110, :1005) | kind-blind | **stay-lenient** (both; :110 ambiguous — reviewer confirm) | n/a | WP04 | :110 (`_canonical_events_path`) is an explicit fallback fired only when `resolve_status_surface` raises `FileNotFoundError`/`ValueError` — "meta.json absent for a legacy mission" per its own docstring; migrating the fallback leg to the fail-loud seam risks raising `CoordinationBranchDeleted` in exactly the degraded window this fallback exists to tolerate. :1005 is a corpus-walk classifier iterating **every** mission under `.kittify/missions/` to compute a 4-state retrospective-coverage report — a single problematic mission's coord-branch deletion must not abort the whole report (named diagnostic pattern, research.md). |
| `cli/commands/validate_tasks.py` | `resolve_planning_read_dir` | 1 (:120) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` | WP04 | `scan_all_tasks_for_mismatches` WP-frontmatter read; already kind-annotated, explicit prior bugfix (coord husk silently returned `{}`). |
| `cli/commands/verify.py` | `candidate_feature_dir_for_mission` | 1 (:33) | kind-blind | migrate-fail-loud | `PRIMARY_METADATA` | WP04 | Existence-gated presentation adapter (`spec-kitty verify` environment check) — a pure existence probe; `PRIMARY_METADATA` never raises `CoordinationBranchDeleted`, so migration is a behavior no-op regardless of the tool's diagnostic framing. |

### WP05 — merge+lanes (`src/specify_cli/merge/**` + `src/specify_cli/lanes/**`)

| file | symbol(s) | sites | family | verdict | kind | cluster | rationale |
|---|---|---|---|---|---|---|---|
| `lanes/lifecycle_sync.py` | `resolve_planning_read_dir` | 1 (:149) | kind-aware | migrate-fail-loud | `LANE_STATE` | WP05 | Auto-rebase `lanes.json` read; already kind-annotated, explicit prior silent-skip bugfix note. |
| `lanes/merge.py` | `resolve_planning_read_dir` | 2 (:143, :291) | kind-aware | migrate-fail-loud | `LANE_STATE` (both) | WP05 | Mission-merge `lanes.json` reads. |
| `lanes/recovery.py` | `resolve_planning_read_dir`, `candidate_feature_dir_for_mission` | 3 (:602, :606, :706) | mixed | migrate-fail-loud (all 3) | `LANE_STATE` (:602, :706); `STATUS_STATE` (:606, comment: "STATUS leg: the append-only event log stays coord-aware") | WP05 | Recovery-state computation genuinely needs to know whether the coord branch backing a WP's event log was deleted, rather than silently reading a stale/absent surface. |
| `lanes/worktree_allocator.py` | `resolve_planning_read_dir` | 1 (:442) | kind-aware | migrate-fail-loud | `PRIMARY_METADATA` | WP05 | Chicken-and-egg coord-topology discovery read (`meta.json.coordination_branch`); explicitly documented as needing the topology-blind PRIMARY leg (it produces the very topology answer a coord-aware read would need). |
| `merge/done_bookkeeping.py` | `resolve_planning_read_dir` | 2 (:262, :578) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` (both) | WP05 | Merge-complete WP-file lookup + committed-events anchor; already kind-annotated with an explicit "historical comment predated the kind-aware split" correction note. |
| `merge/executor.py` | `resolve_planning_read_dir`, `candidate_feature_dir_for_mission` | 4 (:520, :1540, :1547, :1550) | mixed | migrate-fail-loud (all 4) | `WORK_PACKAGE_TASK` (:520); `STATUS_STATE` (:1540, comment: "MUST stay on topology-aware resolver"); `PRIMARY_METADATA` (:1547); `LANE_STATE` (:1550) | WP05 | :1540's STATUS leg is a genuine functional read feeding `run.feature_dir` for the coord-aware event log during a lane-based merge — fail-loud-appropriate (a merge must not silently treat a deleted coord branch as healthy). |
| `merge/forecast.py` | `resolve_planning_read_dir` | 1 (:160) | kind-aware | migrate-fail-loud | `LANE_STATE` | WP05 | Dry-run `lanes.json` read; explicit prior bugfix note (spurious "missing lanes" report off the coord husk). |
| `merge/ordering.py` | — | 0 real (grep hit only) | n/a | no-site | n/a | WP05 | Grep hit at `:372` is a comment describing `candidate_feature_dir_for_mission`; zero `ast.Call` sites. |
| `merge/resolve.py` | `candidate_feature_dir_for_mission`, `resolve_planning_read_dir` | 2 (:67, :109) | mixed | migrate-fail-loud (both) | `PRIMARY_METADATA` (:67, slug-canon idiom; :109, merge-state key identity read) | WP05 | :67 is the same 6-site slug-canonicalization idiom as `agent/status.py:72`. |

### WP06 — diagnostic-heavy

| file | symbol(s) | sites | family | verdict | kind | cluster | rationale |
|---|---|---|---|---|---|---|---|
| `coordination/status_transition.py` | `candidate_feature_dir_for_mission`, `resolve_planning_read_dir` | 3 (:606, :623, :1259) | mixed | migrate-fail-loud (all 3) | `PRIMARY_METADATA` (:606, :623 — `_canonical_primary_feature_dir`'s create-window/malformed-meta degrade branches, which want the topology-blind PRIMARY anchor, not a coord read); `LANE_STATE` (:1259) | WP06 | :606/:623 compute the transaction-identity **primary anchor** for the status write path (not a STATUS read) — `PRIMARY_METADATA` is the correct, behavior-preserving target (never raises, matching the existing degrade contract verbatim). Not one of the 3 FR-003-named sanctioned modules, so this is a regular migrate site despite its proximity to the status machinery. |
| `dashboard/scanner.py` | `resolve_planning_read_dir` | 2 (:423, :461) | kind-aware | **stay-lenient** | n/a (`PRIMARY_METADATA`, `TASKS_INDEX` already declared, but kept lenient by doctrine) | WP06 | Named explicitly in research.md's hard-cases list; both sites already catch `(ValueError, MissionSelectorAmbiguous)` with an explicit "the dashboard scan must never crash" comment. Kept lenient module-wide. |
| `decisions/service.py` | `resolve_planning_read_dir` | 1 (:173) | kind-aware | migrate-fail-loud | `STATUS_STATE` | WP06 | Decision-log companion `status.events.jsonl` read — explicitly documented as needing to "agree with where `emit.py` writes" (the permanent coord-authority write target); a genuine functional read, fail-loud-appropriate (a stale/deleted coord branch here is a real split-brain risk, not tolerable). |
| `dossier/api.py` | `candidate_feature_dir_for_mission` | 3 (:227, :397, :435) | kind-blind | **stay-lenient** (all 3; ambiguous — reviewer confirm) | n/a | WP06 | Every site feeds `dossier.snapshot.load_snapshot`, which reads a `.kittify/dossiers/<slug>/snapshot-latest.json` cache file — not a `MissionArtifactKind`-mapped artifact. The API already treats "not found" as an expected outcome (`error_response(..., 404)`), not an exception; these are external/SaaS-facing read endpoints (`SnapshotExportResponse` docstring: "SaaS import-compatible") that should not start raising `CoordinationBranchDeleted` for a mission whose coord branch was later consolidated away (a plausible steady state post-merge). |
| `retrospective/summary.py` | `candidate_feature_dir_for_mission` | 1 (:220) | kind-blind | **stay-lenient** | n/a (`STATUS_STATE`) | WP06 | Own docstring: "Returns (0, 0, 0) on any error, including missing slug, missing log, or corrupt lines" — an explicitly resilient summary-statistics reader, named in the WP06 diagnostic cluster. |
| `retrospective/writer.py` | — | 0 real (grep hit only) | n/a | no-site | n/a | WP06 | Grep hit at `:55` is a docstring cross-reference to `resolve_planning_read_dir`; zero `ast.Call` sites. |
| `review/cycle.py` | `resolve_planning_read_dir` | 1 (:49) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` | WP06 | Docstring already documents this site as having "retir[ed] the kind-blind `candidate_feature_dir_for_mission` fold" historically (#2646/#2697/#2275) — this is the final swap from the lenient kind-aware resolver to the seam. |
| `status/aggregate.py` | `candidate_feature_dir_for_mission` | 1 (:527) | kind-blind | **stay-lenient** | n/a | WP06 | Named explicitly in research.md's hard-cases list; the surrounding code already translates `StatusReadPathNotFound` into a graceful fail-closed result for every handle form rather than letting it propagate raw — status aggregation is itself an audit/reporting surface. |

### WP07 — core/misc

| file | symbol(s) | sites | family | verdict | kind | cluster | rationale |
|---|---|---|---|---|---|---|---|
| `acceptance/__init__.py` | `resolve_planning_read_dir` | 1 (:824) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` | WP07 | Accept-gate WP-task read; explicit invariant check (`is_primary_artifact_kind(WORK_PACKAGE_TASK)`) already guards for a future re-partition. |
| `agent_tasks_ports.py` | `resolve_planning_read_dir` | 2 (:244, :250) | kind-aware | migrate-fail-loud | passthrough (:244, caller-supplied `kind`); `WORK_PACKAGE_TASK` (:250) | WP07 | `FsReader` port adapter (`RealFsReader`) — a direct 1:1 swap: `resolve_planning_read_dir(root, slug, kind=kind)` → `PlacementSeam(root, slug).read_dir(kind)`. |
| `agent_utils/status.py` | `resolve_planning_read_dir` | 1 (:137) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` | WP07 | Tasks-status report read of the PRIMARY leg. |
| `cli/commands/agent/mission_record_analysis.py` | `resolve_planning_read_dir` | 1 (:321) | kind-aware | migrate-fail-loud | `SPEC` (via `_kind_for_artifact("spec")`) | WP07 | Analysis-report gate-dir read feeding `write_analysis_report`; already kind-annotated (dynamically). Note: this file sits under `cli/commands/agent/` (WP03's directory glob) but is explicitly assigned to WP07 by the mission's cluster list — flagging the directory/cluster mismatch for the WP03/WP07 owners to coordinate `owned_files` on this one file. |
| `context/resolver.py` | `resolve_planning_read_dir` | 2 (:222, :252) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` (:222 — single anchor also used for the immediately-following `meta.json` read; both `WORK_PACKAGE_TASK` and `PRIMARY_METADATA` are PRIMARY-partition and resolve to the identical dir, so this is a documented single-kind anchor, not a multi-kind split candidate); `LANE_STATE` (:252) | WP07 | `MissionContext` construction; both already kind-annotated. |
| `core/stale_detection.py` | `resolve_planning_read_dir` | 1 (:446) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` | WP07 | Already wrapped in a broad `except Exception: return None` at the call site, independent of the seam's own fail-loud behavior. |
| `core/worktree_topology.py` | `resolve_planning_read_dir` | 1 (:145) | kind-aware | migrate-fail-loud | `LANE_STATE` | WP07 | Co-resolves identity + `lanes.json` + dependency graph from one PRIMARY anchor; documented single-kind anchor (all three are PRIMARY-partition). |
| `doctrine_synthesizer/apply.py` | `resolve_planning_read_dir` | 1 (:167) | kind-aware | migrate-fail-loud | `STATUS_STATE` | WP07 | Per-kind apply logic's STATUS surface read; a genuine functional (not diagnostic) read — fail-loud-appropriate. |
| `manifest.py` | `candidate_feature_dir_for_mission` | 1 (:272) | kind-blind | **stay-lenient** (ambiguous — reviewer confirm) | n/a | WP07 | The `worktree_path` (not `repo_root`) is passed as the resolver's first arg — a deliberate "what artifacts physically exist in THIS worktree" probe, compared against the sibling `artifacts_in_main` leg (already migrated to `placement_seam(self.repo_root, feature).read_dir(PRIMARY_METADATA)` per the adjacent comment). Structurally incompatible with the seam's repo_root+topology contract; migrating would collapse the main-vs-worktree drift comparison this diagnostic exists to make. |
| `mission_loader/command.py` | `candidate_feature_dir_for_mission` | 1 (:157) | kind-blind | migrate-fail-loud | `PRIMARY_METADATA` | WP07 | Feeds `_ensure_feature_metadata(feature_dir, ...)` — a `meta.json`-adjacent read. |
| `missions/plan/plan_interview.py` | `resolve_planning_read_dir` | 1 (:66) | kind-aware | migrate-fail-loud | `PRIMARY_METADATA` | WP07 | `mission_id` read for the plan interview; already kind-annotated. |
| `missions/plan/specify_interview.py` | `resolve_planning_read_dir` | 1 (:66) | kind-aware | migrate-fail-loud | `PRIMARY_METADATA` | WP07 | Same pattern as `plan_interview.py:66` (near-duplicate module pair). |
| `orchestrator_api/commands.py` | — | 0 real (grep hit only) | n/a | no-site | n/a | WP07 | Grep hit at `:1544` is a comment describing the seam route; zero `ast.Call` sites. |
| `runtime/next/runtime_bridge_identity.py` | — | 0 real (grep hit only) | n/a | no-site | n/a | WP07 | Grep hit at `:97` is a docstring mention of `candidate_feature_dir_for_mission`; zero `ast.Call` sites. Also the shared-package-boundary file the spec's edge cases flag for a routing confirmation — moot here since there is no real call to route. |
| `sync/events.py` | `candidate_feature_dir_for_mission` | 1 (:120) | kind-blind | migrate-fail-loud | `PRIMARY_METADATA` | WP07 | "Best-effort lookup of the canonical `mission_id`" for a dashboard sync trigger; reads `meta.json` only. |
| `task_utils/support.py` | `resolve_planning_read_dir` | 1 (:548) | kind-aware | migrate-fail-loud | `WORK_PACKAGE_TASK` | WP07 | `tasks/` root read for the CLI task-view reconstruction. |
| `workspace/context.py` | `resolve_planning_read_dir` | 6 (:481, :679, :730, :770, :811, :877) | kind-aware | migrate-fail-loud (all 6) | `WORK_PACKAGE_TASK` (:481, :679, :730); `LANE_STATE` (:770, :811, :877) | WP07 | Partially migrated already: line 477 (adjacent to :481) already uses `placement_seam(repo_root, context.mission_slug).read_dir(MissionArtifactKind.STATUS_STATE)` directly — the remaining 6 sites are the same file's not-yet-migrated PRIMARY-partition legs. |

## Notes for the migration WPs (WP03–WP07)

- **The 6-site slug-canonicalization idiom** (`legacy_dir = candidate_feature_dir_for_mission(...); if legacy_dir.exists(): return legacy_dir.name`) recurs verbatim in `cli/commands/agent/status.py:72`, `cli/commands/agent/tasks_shared.py:252`, `cli/commands/agent/workflow.py:820`, `cli/commands/mission_type.py:413`, `cli/commands/next_cmd.py:377`, and `merge/resolve.py:67` — all six migrate to `PlacementSeam.read_dir(MissionArtifactKind.PRIMARY_METADATA)`, mirroring the seam's own internal canonicalization pattern in `resolve_artifact_surface`. Six near-identical duplications of the same "resolve a handle to its canonical on-disk directory name" operation is itself a recurring-boundary-leak worth a follow-up consolidation ticket (a shared helper), but is out of this mission's scope (C-001 forbids introducing a second read authority; a shared *helper* built atop the one authority would not violate that, but is not requested by any FR here).
- **Two files fall outside the WP03–WP07 directory globs but are explicitly assigned by the mission's own cluster list**: `cli/commands/agent/mission_record_analysis.py` (physically under `cli/commands/agent/**`, WP03's glob) is assigned to **WP07**, and `cli/commands/charter/_widen.py` (not under a bare `cli/commands/*.py` glob) is assigned to **WP04** explicitly. Both are called out here so the corresponding `owned_files` lists match the mission's cluster assignment, not the naive directory glob.
- No bypass file fell outside all five clusters (WP03–WP07) or the sanctioned-infra set — every one of the 60 consumer files is accounted for above.
