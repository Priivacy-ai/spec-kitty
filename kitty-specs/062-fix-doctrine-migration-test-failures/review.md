## Architectural Review: Mission 062 — Fix Doctrine Migration Test Failures

**Verdict**: APPROVE with follow-up items  
**Reviewer**: Architect Alphonso (opencode agent, reviewer profile)  
**Date**: 2026-04-03  
**Scope**: WP01–WP07 cumulative changes

---

### Summary

Mission 062 successfully resolves doctrine migration test failures across 7 work packages. The changes are architecturally sound: test fixtures were migrated to the new `src/doctrine/` canonical location, the `MissionTemplateRepository` abstraction is used consistently where appropriate, CI quality gates were split into enforced critical-path and advisory full-report tiers, and dashboard handler coverage was added. No blocking issues were found.

Three areas warrant follow-up work outside this mission's scope.

---

### Findings

#### T028 — Path Convention Consistency

**Assessment: Moderately consistent — acceptable for this mission.**

- **13 test files** correctly use the `MissionTemplateRepository` abstraction for path resolution.
- **6 test files** hardcode `REPO_ROOT / "src" / "doctrine" / "missions"` paths. These fall into two defensible categories:
  1. **Structural/compliance guard tests** (`test_template_lane_guard.py`, `test_lane_regression_guard.py`, `test_template_compliance.py`) — these intentionally assert source-tree layout contracts and _should_ break if the directory moves.
  2. **Migration and E2E tests** — these scan multiple directories and validate cross-cutting filesystem state.
- The three compliance guard files share duplicated path literals, which is a minor maintainability concern but not a correctness issue.

**Rationale for approval**: The hardcoded paths serve a distinct purpose from the repository abstraction. Forcing them through `MissionTemplateRepository` would defeat their role as layout canaries.

#### T029 — Dashboard JS Backward-Compat Approach

**Assessment: Dead-code fallback — recommend clean break as follow-up.**

- `dashboard.js` line 1246 uses `data.missions || data.features` and `data.active_mission_id || data.active_feature_id`.
- The backend handler (`missions.py`) **only returns `missions` and `active_mission_id` keys** — the `data.features` and `data.active_feature_id` branches can never activate.
- The JS still fetches from `/api/features` (line 1241), though the router accepts both `/api/missions` and `/api/features`.
- The `||` fallback masks potential future regressions and violates the Terminology Canon's hard-break policy against `feature*` aliases in active codepaths.

**Rationale for approval**: The current code is functionally correct — the right data flows through. The dead fallback is technical debt, not a bug. A clean break (removing `data.features` fallback, switching fetch URL to `/api/missions`) is appropriate as a follow-up.

#### T030 — Feature-to-Mission Rename Gaps

**Assessment: ~30 missed renames identified — follow-up mission recommended.**

Findings by category:

| Category | Count | Files | Action |
|----------|-------|-------|--------|
| Missed renames (parameters, variables, functions, classes, docstrings) | ~30 | 18 production files | Follow-up mission |
| Intentional backward-compat aliases (documented wrappers) | ~30+ | 15 files | Keep — remove only when compat window closes |
| Legitimate uses (feature flags, generic English) | 4 | various | No action |
| Legacy data fallbacks (reading persisted JSONL) | 3 | various | Keep — data-format compat required |

**Priority files for rename** (highest impact, lowest risk):
1. `tracker/origin_models.py` — `feature_dir`, `feature_slug` fields on `MissionFromTicketResult`
2. `tracker/saas_client.py` — `feature_slug` parameter in `bind_mission_origin()`
3. `status/bootstrap.py` — `feature_dir`, `feature_slug` parameters
4. `legacy_detector.py` — `feature_path` parameter
5. `core/vcs/types.py` — `FeatureVCSConfig` class name
6. `core/worktree.py` — `create_feature_worktree()` function name
7. `dashboard/static/dashboard/dashboard.js` — extensive `feature` terminology in frontend
8. `scripts/debug-dashboard-scan.py` — utility script with old naming

**Wire-format caution**: `sync/emitter.py` `MissionOriginBound` event schema uses `feature_slug` as a payload key. Renaming this is a **breaking wire-format change** requiring coordinated SaaS deployment. This must be handled in a dedicated migration, not as a bulk rename.

**Rationale for approval**: The missed renames are cosmetic/terminology debt — they do not affect correctness or test outcomes. Fixing them in this mission would expand scope beyond the charter (test failure fixes). A dedicated follow-up mission with proper wire-format migration planning is the right approach.

---

### Follow-up Items

1. **Centralize hardcoded doctrine paths in compliance tests** — Extract `REPO_ROOT / "src" / "doctrine" / "missions"` from the 3 compliance guard test files into a shared `DOCTRINE_SOURCE_ROOT` constant. Low priority, maintainability improvement only.

2. **Dashboard JS terminology clean break** — Remove `data.features` / `data.active_feature_id` fallbacks from `dashboard.js`, switch fetch URL from `/api/features` to `/api/missions`. Consider removing the `/api/features` route alias from the router once the JS is updated. File as a separate mission or attach to an existing terminology-canon mission.

3. **Feature-to-mission bulk rename mission** — Create a dedicated mission to rename ~30 missed `feature*` identifiers across 18 production files. Must include:
   - Wire-format migration plan for `sync/emitter.py` `feature_slug` payload key (requires SaaS coordination)
   - Backward-compat alias deprecation schedule for the ~30 existing wrappers
   - Test updates to match renamed identifiers
   - Related issue: Priivacy-ai/spec-kitty#361 (TypedDict codegen for dashboard API) may intersect

4. **CI coverage threshold tuning** — Monitor the 90% critical-path coverage gate (WP07) over several CI runs. Adjust the file list or threshold if it proves too brittle or too lenient.

---

### Approval Conditions

None — approved as-is. All findings are documented as follow-up items outside this mission's scope. The changes from WP01–WP07 are architecturally aligned, test failures are resolved, and no regressions were introduced.
