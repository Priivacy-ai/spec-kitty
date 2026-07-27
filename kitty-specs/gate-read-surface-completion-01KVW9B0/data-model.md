# Data Model: Gate-command Read-surface (Phase 1)

Not a persistence model — the "data" is the **planning-read site map** and the
**kind → surface** decision the gate commands must adopt.

## Kind → read surface (the rule, post-#2106)

For mission `M` (topology `T`, target branch `B`, coord branch `C`):

```
planning_read_dir(M, kind):
    if is_primary_artifact_kind(kind):     # SPEC, DATA_MODEL, RESEARCH, CHECKLIST,
        return primary_dir(B)              #   FINALIZED_EXECUTION_PLAN, TASKS_INDEX,
                                           #   WORK_PACKAGE_TASK, LANE_STATE, PRIMARY_METADATA
    # status/bookkeeping kind → its placed surface (coord under coord topology)
    return status_read_dir(M)              # STATUS_STATE, ISSUE_MATRIX, ACCEPTANCE_MATRIX,
                                           #   ANALYSIS_REPORT
```

This is exactly `resolve_planning_read_dir` (`_read_path_resolver.py:1244`). The
mission makes every gate command CONSUME it instead of reconstructing the path.

## Planning-read site map (the M-of-N enumeration)

| # | Site | file:line | Kind read | Current resolver | Verdict |
|---|------|-----------|-----------|------------------|---------|
| 1 | `setup_plan` spec.md | `mission.py:2224` | SPEC | `resolve_handle_to_read_path` (coord) | **RESIDUAL** (IC-02) |
| 2-7 | accept spec/plan/tasks/research/data-model | `acceptance/__init__.py:1179-1187` | planning kinds | `status_feature_dir` (coord) | **RESIDUAL** (IC-03) |
| 8-9 | accept `_missing_artifacts` | `acceptance/__init__.py:596` | planning kinds | `status_feature_dir` (coord) | **RESIDUAL** (IC-03) |
| 10 | `map-requirements` WP `tasks/*.md` | `tasks.py:3727` | WORK_PACKAGE_TASK | `resolve_feature_dir_for_mission` (coord) | **RESIDUAL** (IC-04) |
| 11 | record-analysis double-resolution | `mission.py:1980` | planning | manual coord-then-primary | **COLLAPSE** (IC-04) |
| 12-13 | primary-anchor helper pair | `mission.py:1308,1327` | planning | bespoke primary-anchor | **RETIRE → seam** (IC-01) |
| 14 | **`finalize-tasks` COMMIT** | `mission.py` (finalize-tasks cmd) | planning (WRITE) | resolves protected primary `main` (dogfood repro) | **RESIDUAL — write-side → fixed by WP00 (IC-00)**; ratchet write arm WP06 |
| 14b | write-branch resolvers | `core/paths.py:617` `get_feature_target_branch`, `core/git_ops.py:371` `resolve_target_branch` | planning (WRITE) | `candidate_feature_dir_for_mission` → coord → fallback `main` | **RESIDUAL — write-side → fixed by WP00 (IC-00)** (mirror `resolve_merge_target_branch:665`) |
| — | accept STATUS reads (events, acceptance-matrix) | `acceptance/__init__.py:1174,749` | STATUS_STATE / ACCEPTANCE_MATRIX | `status_feature_dir` | **KEEP (coord)** |
| — | `check-prerequisites` | `_primary_anchored_feature_dir` | planning | primary-anchored | OK (not residual) |
| — | `finalize-tasks` *read* | (primary-anchored) | planning | primary-anchored | OK (only the COMMIT is residual — row 14) |
| — | record-analysis **write** | `primary_feature_dir_for_mission` | ANALYSIS_REPORT | primary | OK |

## Self-bookkeeping allowlist (FR-003, distinct from the partition)

| File | Today | Required |
|------|-------|----------|
| `meta.json` | `kind=None` → not allowlisted → preflight blocks | allowlisted as self-bookkeeping |
| `.kittify/encoding-provenance/global.jsonl` | `kind=None` → blocks | allowlisted as self-bookkeeping |

Allowlist lives at `artifacts.py:113` (`_COORD_RESIDUE_FILENAMES` / a dedicated
self-bookkeeping list) — **separate** from the coord-residue partition. Invariant
preserved: a stale **primary** `spec.md` is still "real dirt" (not allowlisted).

## Lock-the-fix guards (Lane B — fixes exist, add scenario-driving guards)

| Issue | Seam (verified) | Guard entry point |
|-------|-----------------|-------------------|
| #2091 | `runtime/next/runtime_bridge.py` (`resolve_mid8` + guard) | `next` → coord branch well-formed (no empty mid8) |
| #2088 | `ownership/validation.py:161` (`_dependency_reachability`) | `finalize-tasks --validate-only` → dep-ordered overlap allowed |
| #2074 | `mission_type.py:632` (`_read_mission_mid8` reads `<dir>/meta.json`) | re-pin fixture to production-shaped `meta.json` |
