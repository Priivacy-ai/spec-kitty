---
work_package_id: WP03
title: 'Single-owner ci-quality.yml surgery: composite groups, fast-matrix split, always-on de-serialized arch pole, needs-lists'
dependencies:
- WP02
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- NFR-004
- C-002
- C-003
tracker_refs:
- '#2378'
- '#1933'
- '#2383'
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-topology-shrink-01KWQAVX
base_commit: aa998ede7e31927286e78e7819757e03c2f2c604
created_at: '2026-07-04T21:00:00+00:00'
subtasks:
- T007
- T008
- T009
- T010
- T011
phase: Phase 3 - Workflow surgery
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1139017"
history:
- at: '2026-07-04T21:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: .github/workflows/ci-quality.yml
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/ci-quality.yml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Single-owner `ci-quality.yml` surgery

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

You are the **SOLE owner** of `.github/workflows/ci-quality.yml` (C-003 — a `lanes` allocator rejects overlapping `owned_files`; per-slice WPs cannot co-own this file, so ALL topology edits land here). Turn WP02's eight RED invariants GREEN while keeping the 8 #2368 WP04 invariants green throughout (NFR-007). This is the fat WP — inherent to C-003.

The load-bearing insight (all 3 post-spec lenses): **un-blind (US2) and wallclock (US3) are the SAME arch-pole move (FR-013)** — de-serializing the arch shard from `fast-tests-core-misc` moves its tail 29.4→12.3 min AND runs it on 100% of PRs. Realize it as an **always-on arch job that adds NO filter group** (Option A) so the FR-010 parsed relations stay untouched (C-001 additive).

## Subtasks & Detailed Guidance

### Subtask T007 – Composite filter groups + 5-edit surfaces 1-3 (FR-001/002/010)
For each census worklist dir, register it into a **composite** src-backed filter group (FR-010 caps job-count under the NFR-005 ceiling; the research §3 design proposes `auth_audit_git`, `lifecycle`, `agent_surface`, `closeout`, `governance`, `platform` — WP01's census is the authoritative member map). Land the 5-edit atomic registration surfaces 1-3 per group IN ONE COMMIT (research §4.4):
1. dorny `filters:` block — group + `src/specify_cli/<members>/**` globs.
2. `changes.outputs.<group>` row — the exact `(run_all || …unmatched…) && 'true' || …filter…` shape.
3. `unmatched` enumeration loop (`:309-329`) — add `"${{ steps.filter.outputs.<group> }}"`.
Keep FR-010c enumeration (`test_unmatched_refs_equal_parsed_filter_groups_live`) and FR-010 boolean (`test_unmatched_boolean_semantics`) green.

### Subtask T008 – Fast-matrix split + ignore mirror + nested roots (FR-003/004/012)
- Subdivide `fast-tests-core-misc` (`:1321-1376`) into a focused matrix mirroring the `integration-tests-core-misc` shards (FR-003). Each shard owns coherent, non-overlapping test roots (NFR-003).
- Update the `fast-tests-core-misc` `--ignore` mirror in LOCKSTEP with every carve (FR-012 invariant `test_catch_all_ignore_lists_mirror_owned_roots_live`) — carve a shard ⇒ add `--ignore=tests/<root>` AND give the root a positional home, together.
- Update the integration-matrix `ignore_args` for nested `tests/specify_cli/<D>` roots (orchestrator_api, bulk_edit) by hand (FR-004 — NOT covered by FR-012's whole-tree check).
- Consolidate the `migration` double-root (`tests/migration` + `tests/specify_cli/migration`) into ONE home preserving `and not slow` (the `@slow` perf test runs only in `slow-tests`) (FR-012).
- Carve `dossier` (globbed in core_misc but in NO integration shard — fixes a latent hole).

### Subtask T009 – Always-on de-serialized arch pole (FR-005/006/013/011/009)
- Extract the `architectural` matrix shard (`tests/adversarial tests/architectural tests/architecture tests/lint`, marker `not windows_ci and (git_repo or integration or architectural)`) into a STANDALONE job (proposed `arch-adversarial`).
- `if: always()` (like `lint`) — unconditional, references NO dorny filter output → it does NOT enter `JOB_GROUPS`, `src_backed_groups`, or the `unmatched` loop → FR-010/FR-011 relations untouched (C-001). **CRITICAL**: the job must carry NO filter-group `if:` or it perturbs `src_backed_groups` and reds FR-010 + NFR-002.
- Drop `needs: fast-tests-core-misc` (`:1433`) — de-serialize (FR-013). Arch tail ≈12.3 min from t=0.
- Emit `coverage-*.xml` under the glob-consumed name so the aggregator wildcard download picks it up (FR-006).
- Preserve `-n0` serial passes + `--dist loadfile` + per-worker HOME isolation on every new shard (FR-011). Preserve the fail-closed catch-all so an unmapped/new src path still forces coverage and nightly `run_all` still over-covers (FR-009).

### Subtask T010 – JOB_GROUPS heredoc + all needs-lists (FR-002 surfaces 4-5, FR-007, C-005, C-002)
- 5-edit surfaces 4-5 per group: wire each group into ≥1 test-job `if:` and add its `JOB_GROUPS` heredoc row (`:3219-3258`) — keep `test_job_groups_table_equals_parsed_if_gating_live` green.
- Register every new test job (incl. `arch-adversarial`) into `quality-gate.needs`, `sonarcloud.needs` (`:2517-2552`), `diff-coverage.needs` (`:2370-2387`), and `mutation-testing.needs` (`:2485-2503`, `if: false` but parsed) — per FR-007 + C-005.
- **NEVER** add integration/arch jobs to `slow-tests.needs` (`:2152-2168`, fast-jobs-only — would red on arrival). This is the sharpest latent hazard (research §4.5).
- Every derived surface stays asserted-against-parsed-source (C-002 / Decision 8) — no hand-added surface beside the model.

### Subtask T011 – Gates + probe evidence
- WP02's eight invariants flip RED→GREEN: `test_ci_topology_worklist`, `test_arch_unblind_matrix`, `test_same_tier_uniqueness`, `test_coverage_consumer_needs`, `test_serial_port_preservation`, `test_job_count_ceiling`, `test_arch_pole_deserialized` (FR-013 — the parsed arch/adversarial `needs` set drops `fast-tests-core-misc`), `test_shard_universe_bounded` (SC-003a — no single shard collects the full universe post-split).
- The 8 #2368 invariants stay green: `PWHEADLESS=1 uv run pytest tests/architectural/test_src_filter_coverage.py tests/architectural/test_workflow_coherence.py tests/architectural/test_marker_job_completeness.py tests/architectural/test_gate_coverage.py -q`.
- `_gate_coverage` orphan count stays 0, total `run_all` selected count unchanged (SC-004).
- A probe PR per representative slice (e.g. touch only `src/specify_cli/auth/**`) demonstrates focused routing + always-on gates and NO full-matrix run (SC-006). Paste probe evidence in the Activity Log.

## Campsite cleaning (standing rule; ride the WP's normal review)

`ci-quality.yml` is YAML, not Python — Sonar/ruff campsite is N/A here, but keep the file coherent: no orphaned anchors, no dead filter globs (`test_every_filter_glob_is_live` covers this file). Do NOT expand scope to `ci-windows.yml` (WP04 owns it) or the baseline (WP06 owns it).

## Definition of Done (non-fakeable — every anchor is a green test)

- **WP02's eight invariants GREEN** (recorded run output).
- **The arch/adversarial job's parsed `needs` contains NO fast-lane job** (FR-013 de-serialized — `always()` alone does NOT parallelize; the `needs: fast-tests-core-misc` edge is dropped) — `test_arch_pole_deserialized` green.
- **No single shard collects the full catch-all universe** (SC-003a — the monolith is genuinely split, not merely same-tier-unique) — `test_shard_universe_bounded` green.
- **8 #2368 invariants GREEN** (recorded run output); orphan count 0, total selected unchanged.
- Each composite group's 5 surfaces landed atomically (FR-002) — no partial registration (a partial reds FR-010c/FR-011).
- The `arch-adversarial` job is always-on, group-less, de-serialized, and coverage-wired (NFR-002 asserts it selects 100% of dirs).
- Probe-PR evidence recorded: a single-area PR routes to its focused shard + always-on gates, not a full-matrix run (SC-006).

## Risks / Reviewer Guidance

- **C-003 topology**: if per-slice workflow edits become unavoidable, STOP and escalate to flatten the mission to `single_branch` with linearized shared-surface edits — do NOT split this file across lanes.
- The always-on arch job MUST carry no filter-group `if:` — reviewer verifies NFR-002 stays green (it proves the job stays unconditional).
- Reviewer confirms `slow-tests.needs` gained NO integration/arch job (C-005 correction).

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-04T21:00:00Z – system – Prompt created.
- 2026-07-04T23:27:00Z – claude:opus:python-pedro:implementer – shell_pid=1040736 – Assigned agent via action command
- 2026-07-04T23:39:15Z – claude:opus:python-pedro:implementer – shell_pid=1040736 – BLOCKED (escalation): WP02 test_ci_topology_worklist.py is internally contradictory. test_no_worklist_dir_falls_to_unmatched_run_all requires every census worklist dir to be in mapped_src_dirs; test_census_worklist_matches_live_derivation requires census.worklist == live_derived_worklist(), and live_derived_worklist() EXCLUDES mapped dirs. Mapping the 32 dirs (routing green) => live worklist=0 => freshness RED; regenerating census to match => empty => test_worklist_is_non_empty RED. Root cause: _gate_coverage.py:live_derived_worklist mapped-exclusion (WP01, non-owned, allocator-rejected). Cannot make the WP02 gate fully green by editing only ci-quality.yml. Reported to orchestrator; no ci-quality.yml edits made to avoid a partial/red-gate handoff.
- 2026-07-04T23:45:26Z – user – shell_pid=1040736 – Moved to planned
- 2026-07-05T00:06:05Z – claude:opus:python-pedro:implementer – shell_pid=1082052 – Started implementation via action command
- 2026-07-05T02:30:00Z – claude:opus:python-pedro:implementer – shell_pid=1082052 – COMPLETE. Substrate blocker resolved by WP01's frozen `_PRE_MISSION_MAPPED_SRC_DIRS` baseline; full surgery landed on `.github/workflows/ci-quality.yml` (sole owned file). Profile python-pedro: applied DIR-030 (both gate suites green before handoff), DIR-043 (composite groups + shard split + always-on pole close the defect classes by construction), DIR-024 (only ci-quality.yml edited).
  T007 — Composite src-backed filter groups (5-edit atomic registration per group, surfaces 1-3): added 6 groups to the dorny `filters:` block with `src/specify_cli/<member>/**` globs, 6 `changes.outputs.<group>` rows (exact run_all/unmatched shape), and 6 entries in the `unmatched` enumeration loop. Group→member map (per census target_group / `_COMPOSITE_ROUTING`): auth_audit_git={auth,audit,git}; lifecycle={migration,invocation,compat,template}; agent_surface={orchestrator_api,tracker,dossier,bulk_edit,skills}; closeout={retrospective,readiness,decisions,doc_analysis,widen}; governance={doctrine,policy,ownership,validators,calibration,context}; platform={workspace,session_presence,mission_v1,mission_loader,events,paths,saas_client,task_utils,intake}. All 32 worklist dirs mapped.
  T008 — fast-tests-core-misc SPLIT into a shard matrix (SC-003a): shard `specify-cli-rest` (tests/specify_cli minus the nested roots owned by dedicated fast jobs: cli/missions/lanes/next/status/charter_freshness/charter_lint/charter_preflight) + shard `core-misc` (whole-tree residual). --ignore mirror updated in lockstep (FR-012): residual adds tests/specify_cli + tests/docs to the current 21; every carved root owned by a dedicated positional. Integration specify-cli-rest ignore_args expanded by hand for nested roots (FR-004): +cli,+missions,+lanes,+charter_{freshness,lint,preflight} (migration/invocation/status/next already present). coordination consolidated to specify-cli-rest as its sole integration owner (its architectural marker arm covers the 3 arch-marked coordination boundary tests integration-tests-status' git_repo/integration marker dropped) — tests/specify_cli/coordination removed from integration-tests-status. Result: same-tier fast double-runs 2494→0, integration 796→0, shard-universe monolith split.
  T009 — Always-on de-serialized arch pole (load-bearing): extracted the `architectural` matrix shard into standalone `arch-adversarial` job — `if: always()` (no dorny filter-group if → group-less → does NOT enter JOB_GROUPS/src_backed_groups/unmatched loop, NFR-002 untouched); NO `needs: fast-tests-core-misc` (DE-SERIALIZED, FR-013); single-entry `architectural` matrix shard so the paths stay evaluated under the gate-coverage structure checker's shard key; roots tests/adversarial+architectural+architecture+lint, marker `not windows_ci and (git_repo or integration or architectural)`, emits coverage-arch-adversarial-architectural.xml (glob-consumed, FR-006); `-n auto --dist loadfile` (no bare load), no daemon test so no -n0 pass (FR-011). Dropped `needs: fast-tests-core-misc` from integration-tests-core-misc too (it retains the architectural marker arm but with no fast-lane need → test_arch_pole_deserialized green) and removed the now-moot exec-context special-path block (parity runs in the always-on pole).
  T010 — JOB_GROUPS + needs-lists: JOB_GROUPS rows for fast-tests-core-misc and integration-tests-core-misc updated to equal their parsed `if:` gating (the 6 composites added; test_job_groups_table_equals_parsed_if_gating_live green). arch-adversarial registered into quality-gate.needs (blocking), sonarcloud.needs, diff-coverage.needs, mutation-testing.needs. **C-005 fix: mission-loader-coverage added to sonarcloud.needs** (it emits --cov=src/specify_cli/mission_loader but was absent — the exact drop test_src_coverage_emitters_are_sonarcloud_consumers reds on). NEVER added integration/arch jobs to slow-tests.needs.
  T011 — GATE (uv run, both suites FULLY GREEN):
    Suite 1 (WP02 8 invariants): 29 passed in 119.94s — test_ci_topology_worklist, test_arch_unblind_matrix, test_same_tier_uniqueness, test_coverage_consumer_needs, test_serial_port_preservation, test_job_count_ceiling, test_arch_pole_deserialized, test_shard_universe_bounded.
    Suite 2 (#2368 4 files): 57 passed in 118.96s — test_src_filter_coverage, test_workflow_coherence, test_marker_job_completeness, test_gate_coverage.
    SC-004: orphan_count 0 (test_split_preserves_zero_orphans + gate_coverage ratchet green); total collected 28702, no test dropped; same-tier duplicate double-runs 3290→ (700 cross-tier report-only duplicates remain, intentional). YAML valid (`python3 -c yaml.safe_load` -> ok).
  Probe (SC-006, parsed-model simulation): src/specify_cli/auth/* → auth_audit_git only, unmatched=False (no run_all); src/specify_cli/retrospective/* → closeout, unmatched=False; src/specify_cli/workspace/* → platform, unmatched=False. always_on_arch_present=True (arch-adversarial runs 100% of PRs), arch-adversarial group-less=True. Confirms focused routing + always-on arch, NO full-matrix run_all.
  Lane diff = .github/workflows/ci-quality.yml ONLY.
- 2026-07-05T02:45:00Z – claude:opus:python-pedro:implementer – shell_pid=1082052 – T008 dossier latent-hole carve (FR-004): added `tests/dossier` (top-level) to the integration-tests-core-misc `misc` shard — it was globbed by core_misc but present in NO integration shard, so top-level dossier integration tests had no integration home (tests/specify_cli/dossier is covered by specify-cli-rest). Re-verified collect-heavy trio (same_tier + shard_universe + gate_coverage): 24 passed, orphan_count 0, duplicate 700 unchanged — the carve closes the hole by construction without a new same-tier overlap. Amended lane commit b4cb334e357d6a11f4d08554a0d0ba0ec5e38532 (ci-quality.yml only, +261/-61). Both gate suites remain FULLY GREEN. Moved WP03 in_progress -> for_review.
- 2026-07-05T01:03:54Z – claude:opus:python-pedro:implementer – shell_pid=1082052 – Composite groups + fast-matrix split + always-on arch pole; WP02 8 green (29 passed), #2368 4-file suite green (57 passed), orphan 0, mission-loader-coverage C-005 fixed
- 2026-07-05T01:09:29Z – claude:opus:reviewer-renata:reviewer – shell_pid=1139017 – Started review via action command
- 2026-07-05T01:15:54Z – user – shell_pid=1139017 – Review passed cycle 2 (arbiter override: cycle-1 rejection was the WP01 substrate defect, now fixed by WP01 frozen _PRE_MISSION_MAPPED_SRC_DIRS baseline; test_ci_topology_worklist GREEN). 16 invariants GREEN: WP02 suite 29 passed/123s; #2368 suite 57 passed/120s (orphan 0). FR-013 arch pole REAL: arch-adversarial needs=None (de-serialized), if:always(), group-less (NFR-002 green). integration-tests-core-misc.needs=[changes]; retained architectural marker arm does NOT double-run arch suite (no remaining shard globs tests/architectural|adversarial). slow-tests.needs clean: fast-tests-* only. 6 composite groups registered across all 5 surfaces (parse-verified). fast-tests-core-misc split into 2 disjoint non-empty shards; ignore mirror consistent. C-005: mission-loader-coverage + arch-adversarial in sonarcloud.needs; arch-adversarial in quality-gate/diff-coverage/mutation-testing. Single-entry architectural matrix shard = legit structural accommodation. YAML valid. Commit b4cb334e touches ONLY .github/workflows/ci-quality.yml (+261/-61).
