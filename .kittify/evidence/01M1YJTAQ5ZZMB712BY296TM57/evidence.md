---
verdict: fail
mode: post-merge
reviewed_at: 2026-09-07T18:42:35.656764+00:00
findings: 38
gates_recorded:
  - id: gate_1
    name: wp_lane_check
    command: spec-kitty review (internal gate 1)
    exit_code: 0
    result: pass
  - id: gate_2
    name: dead_code_scan
    command: spec-kitty review (internal gate 2)
    exit_code: 1
    result: fail
  - id: gate_3
    name: ble001_audit
    command: spec-kitty review (internal gate 3)
    exit_code: 0
    result: pass
issue_matrix_present: true
mission_exception_present: false
---

## Gate Results

### Gate 1 - Contract tests

- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest tests/contract/ -q`
- Exit code: `0`
- Result: **PASS**
- Notes: 245 passed, 10 skipped, one deprecation warning in 245.84 seconds.

### Gate 2 - Architectural tests

- Command: `.venv/bin/pytest tests/architectural/ -q`
- Exit code: non-zero (run interrupted after failure set was established)
- Result: **FAIL**
- Notes: 12 failures were observed among the first 718 passes. The failures cover shard markers, archive preservation, built-in path authority, the charter agent-profile sole door, doctrine census, golden-count ratchets, and a scope-explicit inert-form scan. Full evidence and exact test names are tracked in [#3997](https://github.com/spec-kitty/spec-kitty/issues/3997); the missing pre-merge full-suite gate is tracked in [#3943](https://github.com/spec-kitty/spec-kitty/issues/3943).

### Gate 3 - Cross-repo E2E

- Command: `SPEC_KITTY_REPO=<this checkout> SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest scenarios/ -q`
- Exit code: `0`
- Result: **PASS**
- Notes: Canonical `spec-kitty/EXPERIMENTAL-spec-kitty-end-to-end-testing` main HEAD passed all 5 scenarios in 801.94 seconds.

### Gate 4 - Issue matrix

- File: `kitty-specs/upgrade-preview-mission-health-01M1V6E1/issue-matrix.json`
- Rows: 13
- Empty or unknown verdicts: 0
- Deferred rows missing follow-up handles: 0
- Result: **PASS**

The architectural hard-gate failure forces the overall mission-review verdict to **FAIL**. No operator exception is permitted for Gate 2.

## Findings

- **architectural_gate**: Full architectural suite has 12 observed failures. See [#3997](https://github.com/spec-kitty/spec-kitty/issues/3997).
- **baseline_provenance**: Late finalization replaced the absent creation baseline with a post-implementation reconciliation merge, initially making review undeterminable. The verified scaffold parent `c0054153b9bce0778cf41a85d11ecd4e9650031d` was restored; root defect tracked in [#3996](https://github.com/spec-kitty/spec-kitty/issues/3996).
- **dead_code** `src/runtime/next/runtime_bridge_io.py` — `RunIdentityMigrationRequired`: no non-test callers found
- **dead_code** `src/runtime/next/runtime_bridge_io.py` — `RunStateMissing`: no non-test callers found
- **dead_code** `src/runtime/next/runtime_bridge_io.py` — `run_index_key`: no non-test callers found
- **dead_code** `src/specify_cli/cli/commands/cutover_guard.py` — `GitDiffScope`: no non-test callers found
- **dead_code** `src/specify_cli/cli/commands/cutover_guard.py` — `changed_paths_from_git`: no non-test callers found
- **dead_code** `src/specify_cli/cli/commands/cutover_guard.py` — `evaluate_touched_missions`: no non-test callers found
- **dead_code** `src/specify_cli/invocation/org_profiles.py` — `OrgProfileResolution`: no non-test callers found
- **dead_code** `src/specify_cli/runtime/asset_preparation.py` — `node_state`: no non-test callers found
- **dead_code** `src/specify_cli/runtime/asset_preparation.py` — `AssetWrite`: no non-test callers found
- **dead_code** `src/specify_cli/runtime/asset_preparation.py` — `AssetObservation`: no non-test callers found
- **dead_code** `src/specify_cli/runtime/asset_preparation.py` — `lock_paths`: no non-test callers found
- **dead_code** `src/specify_cli/skills/command_installer.py` — `CommandInput`: no non-test callers found
- **dead_code** `src/specify_cli/skills/command_installer.py` — `CommandExecutionArtifact`: no non-test callers found
- **dead_code** `src/specify_cli/skills/command_installer.py` — `observe_destination`: no non-test callers found
- **dead_code** `src/specify_cli/skills/command_installer.py` — `atomic_artifact`: no non-test callers found
- **dead_code** `src/specify_cli/skills/command_installer.py` — `remove_entry`: no non-test callers found
- **dead_code** `src/specify_cli/skills/installer.py` — `SkillBackupReplacement`: no non-test callers found
- **dead_code** `src/specify_cli/skills/installer.py` — `PreparedSkillBackup`: no non-test callers found
- **dead_code** `src/specify_cli/skills/installer.py` — `prepare_skill_backup`: no non-test callers found
- **dead_code** `src/specify_cli/skills/installer.py` — `create_skill_backup`: no non-test callers found
- **dead_code** `src/specify_cli/skills/installer.py` — `PreparedProjectSkillWrite`: no non-test callers found
- **dead_code** `src/specify_cli/skills/manifest.py` — `PreparedSkillManifest`: no non-test callers found
- **dead_code** `src/specify_cli/status/dependency_verdict.py` — `wp_lanes_from_snapshot`: no non-test callers found
- **dead_code** `src/specify_cli/status/locking.py` — `feature_status_lock_path`: no non-test callers found
- **dead_code** `src/specify_cli/tool_surface/bundles/projection.py` — `read_regular`: no non-test callers found
- **dead_code** `src/specify_cli/tool_surface/bundles/projection.py` — `supplier_members`: no non-test callers found
- **dead_code** `src/specify_cli/tool_surface/bundles/projection.py` — `recheck_staging`: no non-test callers found
- **dead_code** `src/specify_cli/tool_surface/bundles/projection.py` — `same_observation`: no non-test callers found
- **dead_code** `src/specify_cli/tool_surface/providers/agent_profiles.py` — `prepare_output`: no non-test callers found
- **dead_code** `src/specify_cli/tool_surface/providers/agent_profiles.py` — `prepare_orphan`: no non-test callers found
- **dead_code** `src/specify_cli/tool_surface/providers/agent_profiles.py` — `entry_owners`: no non-test callers found
- **dead_code** `src/specify_cli/tool_surface/providers/agent_profiles.py` — `prepare_parents`: no non-test callers found
- **dead_code** `src/specify_cli/tool_surface/providers/managed_skills.py` — `GlobalSkillAssetsProvider`: no non-test callers found
- **dead_code** `src/specify_cli/tool_surface/service.py` — `lint_docs_directory`: no non-test callers found
- **dead_code** `src/specify_cli/upgrade/assessment.py` — `provisioning_effects`: no non-test callers found
- **dead_code** `src/specify_cli/upgrade/intent.py` — `UpgradeIntent`: no non-test callers found
