# Pre-Doctrine Test Stabilization

**Mission ID:** 01KSMG8Y0V5V2ZM4YEQMKFWN2K  
**Mission slug:** pre-doctrine-test-stabilization-01KSMG8Y  
**Mission type:** software-dev  
**Target branch:** feat/pre-doctrine-stabilization-remediation  
**Parent triage:** #1298 / mission `test-stabilization-and-debt-pass-01KSF9HJ`  
**Sub-issues addressed:** #1301, #1302, #1303, #1304, #1305, #1306, #1307, #1308, #1309, #1310

---

## Overview

The `test-stabilization-and-debt-pass-01KSF9HJ` (01KSF9HJ) mission completed triage and
approved 12 work packages addressing a 249-failure pytest baseline. All 12 WPs reached
`approved` status but **none of the lane code was ever merged into upstream/main**. The
10 DIR-013 sub-issues (#1301–#1310) were filed for pre-existing clusters that 01KSF9HJ
explicitly deferred, and they remain open and unresolved in the current codebase.

Cross-examination of the current `main` confirmed four issues are immediately verifiable:

| Issue | Confirmed broken behaviour |
|-------|---------------------------|
| #1302 | `render_command_template` for `gemini`/`qwen` raises `TOMLDecodeError` at line 146 col 68 — unescaped `\` from `rg '\.py$'` in `implement.md:168` |
| #1308 | `README.md` has no `## Governance layer` section; four tests in `test_readme_governance.py` fail |
| #1309 | `audit/classifiers/wp_files.py:92` reads `frontmatter.get("lane")` — Phase-2 (3.x) frontmatter lane regression |
| #1310 (partial) | `commands/__init__.py:78` still registers `doctrine` via `add_typer`; `test_doctrine_parent_group_is_unregistered` fails with `assert 0 != 0` |

The remaining six clusters (#1301, #1303–#1307) are structurally confirmed by the 01KSF9HJ
triage document and require per-cluster targeted fixes.

This mission resolves all ten sub-issues in four ordered waves, enforces CI test-mark
hygiene across every touched directory, and declares a ≤75-failure baseline as the
prerequisite gate before doctrine/charter/glossary-pack feature work resumes.

---

## Stakeholder Context

**Primary driver:** Doctrine and charter feature missions cannot proceed reliably while
the test suite has ~200+ unexplained failures — the noise-to-signal ratio makes it
impossible to distinguish regressions from pre-existing debt.

**Secondary driver:** CI test-mark gaps mean some tests are silently excluded from fast
CI runs. Fixing marks restores confidence that green CI actually reflects green code.

**Release gate:** This mission is scoped under the 3.2.x stabilization effort. Its
outcome is a prerequisite for issuing a stable 3.2.0 release and for resuming active
feature development on doctrine/charter subsystems.

---

## User Scenarios & Testing

### Primary scenario — Developer runs the full test suite and sees a clean baseline

1. Developer clones the repo and runs `PWHEADLESS=1 pytest tests/ -q --tb=no`.
2. The command completes with ≤75 failures (down from ~194–249 before this mission).
3. All 10 DIR-013 sub-issues are either closed (fix landed) or explicitly re-deferred
   with a filed follow-on issue and rationale.

### Secondary scenario — CI fast-run picks up every new test

1. Developer writes a new unit test for a bug fix, tagging it `[pytest.mark.fast]`.
2. The CI `fast-tests-*` job for the relevant module runs it and it passes.
3. No new test is silently excluded because of a missing or incorrect mark.

### Edge scenario — Pre-existing failure discovered during implementation

1. Implementer encounters a failure outside this mission's scope.
2. Per DIR-013, a GitHub issue is filed before the failure is treated as accepted
   baseline context.
3. The failure is not fixed within this mission's scope unless it belongs to #1301–#1310.

---

## Functional Requirements

### Wave A — Zero-risk quick fixes

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The source template `src/specify_cli/missions/software-dev/command-templates/implement.md` must be updated so that the rendered TOML output for `gemini` and `qwen` agents parses without `TOMLDecodeError`. The fix must address the unescaped backslash in the `rg '\.py$'` bash snippet at source line 168 by replacing it with a backslash-free equivalent (e.g. `grep -E '[.]py$'` or `rg '[.]py$'`). The twelve-agent parity snapshot must be refreshed after the fix. Closes #1302. | Proposed |
| FR-002 | `README.md` must gain a `## Governance layer` subsection satisfying all six assertions in `tests/specify_cli/docs/test_readme_governance.py`: (1) heading `## Governance layer` present; (2) link to `docs/trail-model.md`; (3) link to `docs/host-surface-parity.md`; (4) substrings `spec-kitty advise`, `spec-kitty ask`, and `spec-kitty do` all present within the section; (5) every relative `.md` link in `.agents/skills/spec-kitty.advise/SKILL.md` resolves to an existing file; (6) every relative `.md` link in `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` resolves to an existing file. Closes #1308. | Proposed |
| FR-003 | `src/specify_cli/audit/classifiers/wp_files.py` must not read the frontmatter `lane` or `status` keys directly. The replacement must use `specify_cli.status.lane_reader.get_wp_lane()` wrapped in a guard (either `has_event_log()` pre-check or `try/except CanonicalStatusNotFoundError`) so that the classifier does not raise for pre-3.0 missions or missions that have not yet run `finalize-tasks`. The `classify_wp_files()` function's "never raises" contract must be preserved. The `test_lane_regression_guard` test for `wp_files.py` must pass, and a new test must confirm `classify_wp_files()` does not raise when called on a mission directory with WP files but no event log. Closes #1309 (frontmatter lane regression). | Proposed |
| FR-004 | The `doctrine` top-level CLI group must not be registered in the root Typer application. The import and `add_typer` call in `src/specify_cli/cli/commands/__init__.py` must be removed. All three assertions in `tests/specify_cli/cli/test_doctrine_cli_removed.py` must pass. Closes #1310 (doctrine group registration part). | Proposed |

### Wave B — Structural fixes

| ID | Requirement | Status |
|----|-------------|--------|
| FR-005 | The doctrine glossary must include the anchors `doctrine-pack` and `platform-darwin--platform-linux` in the contexts where `test_glossary_link_integrity` expects them. The `five-paradigm-parallel-debugging` tactic schema must be valid and all referenced terms must resolve. All four `tests.doctrine.test_glossary_link_integrity` and `test_tactic_compliance` failures must be eliminated. Closes #1304. | Proposed |
| FR-006 | Status and lifecycle event emission must be restored to the correct contract: (a) `SpecifyStarted` event must be emitted at mission-create time (#1067 regression); (b) atomic commit flow must not leave status artifacts dirty after `move_task`; (c) `move_task` must not surface the wrong commit message to the lane branch; (d) `implement` must block when lane allocation fails. The four affected tests in `test_atomic_status_commits_unit`, `test_mission_creation_specify_started`, `test_move_task_git_validation_unit`, and `test_status_emit_on_alloc_failure` must pass. Closes #1306. | Proposed |
| FR-007 | The charter integration suite must be restored: (a) org-layer source name must appear in lint output; (b) `synthesize_without_charter_md` must surface the correct error class; (c) the `discover` action in the runtime walk must not block when `spec.md` is already authored; (d) the implement-review-retrospect smoke must pass; (e) the rejection cycle must report the correct branch in the handoff; (f) the specify-plan commit boundary test must observe auto-commit of a substantive plan. All six affected integration tests must pass. Closes #1307. | Proposed |
| FR-008 | The `next` CLI exit-code contract must match the documented spec: terminal states return exit 0; blocked states return exit 1; `decide_next` mocks must be invoked when the code path reaches them. The four failing tests in `test_next_command_integration` and `test_query_mode_unit` must pass. Closes #1305. | Proposed |

### Wave C — Shared-package and architectural fixes

| ID | Requirement | Status |
|----|-------------|--------|
| FR-009 | The shared-package events residual cluster must be resolved: (a) `src/specify_cli/sync/restart.py` must be added to the daemon-allowlist or refactored so the daemon-intent gate test passes; (b) `BuildRegistered` must be queued at `init` time; (c) `MissionOriginBound` must be queued when no WebSocket is available; (d) the `WPCreated` handoff fixture must carry `actor` and `wp_title` fields; (e) no vendored events tree must exist under `src/specify_cli/spec_kitty_events`; (f) the YAML codeblock in the example round-trip fixture must carry `# pydantic_model:` frontmatter. All six `tests.sync` and `tests.contract` failures listed in #1301 must pass. Closes #1301. | Proposed |
| FR-010 | The charter synthesizer must produce deterministic manifest hashes. Direct write primitives must not leak outside `path_guard.py`. The chokepoint coverage gap must be closed. All five `tests.charter.synthesizer.test_bundle_validate_extension` assertions must pass. Closes #1303. | Proposed |
| FR-011 | The miscellaneous debt cluster from #1310 must be resolved or formally re-deferred per issue. In-scope items for this mission: (a) auth integration exit-code must return the correct value; (b) `logged_out_on_connected_teamspace` noise must not leak into JSON CLI output; (c) `mission_step_contracts/executor.py` must be mypy-strict-clean; (d) WP files in legacy `kitty-specs` that fail Pydantic validation must be fixed or explicitly excluded from the validator; (e) mission switching must not be blocked. Items that cannot be fixed without a dedicated mission (e.g. schema-version wording drift, `spec-kitty.checklist` skill package) are re-deferred with a filed follow-on issue. Closes #1310 (partially; re-deferred items get new issues). | Proposed |

### Wave D — Closeout

| ID | Requirement | Status |
|----|-------------|--------|
| FR-012 | Every test file in directories touched by FR-001 through FR-011 must carry a module-level `pytestmark` with at least one of the canonical CI-quality marks (`fast`, `unit`, `integration`, `e2e`, `slow`, `contract`, `architectural`, `doctrine`). Additionally, `tests/agent/test_context_unit.py` (the one currently untagged test file) must receive the appropriate mark. A new or updated guard test must verify that no test file in a touched module directory is missing a `pytestmark`. | Proposed |
| FR-013 | A full `PWHEADLESS=1 pytest tests/ -q --tb=no` run on the post-mission commit must produce ≤75 failures. The run output and failure list must be committed to `docs/01KSMG8Y-closeout/baseline.md`. All ten parent sub-issues (#1301–#1310) must be either closed (linked to the fixing commit) or re-deferred with a new filed issue. `#1298` must receive a closing comment with the final delta. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-001 | Full-suite failure count after mission merge | ≤75 failures (`pytest tests/ -q --tb=no`) |
| NFR-002 | No new failures introduced by Wave A fixes | 0 — Wave A changes must not increase the failure count vs. the pre-fix baseline |
| NFR-003 | CI fast-run coverage of touched modules | Every test file in a fixed module must have at least one test marked `fast` or `unit` that runs in the appropriate `fast-tests-<module>` CI job |
| NFR-004 | Test suite runtime stability | The full suite run time must not regress by more than 10% vs. the pre-mission baseline (~924s) |

---

## Constraints

| ID | Constraint |
|----|-----------|
| C-001 | All fixes are behaviour-preserving. No feature extension, no new CLI surfaces, no schema changes outside what is required to make existing tests pass. |
| C-002 | `SPEC_KITTY_TEST_MODE=1` bypass is permitted only in ceremony-commit guards (as established in commit `64ddadc5f`). It must not be introduced in production logic paths. |
| C-003 | Frontmatter `lane` reads are illegal in Phase-2 (3.x) runtime code. Any fix that reads lane state must use `specify_cli.status.lane_reader.get_wp_lane()`. |
| C-004 | All `meta.json` mutations must route through `src/specify_cli/feature_metadata/mission_metadata.py`. No direct `meta.json` file writes in new or fixed code. |
| C-005 | The `charter` top-level CLI group must remain registered. FR-004 removes only the `doctrine` group. Removing `charter` is out of scope. |
| C-006 | DIR-013 applies to all WPs in this mission. Any new pre-existing failure discovered during implementation must be filed as a GitHub issue before it is treated as accepted baseline context. |
| C-007 | The stale brief files (`.kittify/mission-brief.md`, `.kittify/ticket-context.md`, `.kittify/brief-source.yaml`) must be deleted after this spec is committed. They belong to a different mission context (`01KRJGKH4DJCSF277K9QV3WBE7`). |
| C-008 | Wave C item FR-011 may re-defer items that require dedicated missions (e.g. `spec-kitty.checklist` skill package restoration). Each re-deferred item must have a filed follow-on GitHub issue before FR-011 is declared complete. |
| C-009 | The twelve-agent parity snapshot refresh (FR-001) must be committed alongside the template fix, not as a separate follow-on. |

---

## Assumptions

1. The `uv.lock` pin for `spec_kitty_events` is already at `5.2.0` in the current codebase. FR-009 addresses structural residual items, not the package version itself (which was aligned by 01KSF9HJ WP02 planning-lane work).
2. The doctrine glossary anchor additions (FR-005) are content additions to existing YAML files, not schema changes. No glossary schema version bump is needed.
3. The `implement.md` backslash fix (FR-001) applies equally to all 13 TOML-format agents rendered from the same source. The snapshot refresh will cover all affected agents in one pass.
4. "Test-mark audit" (FR-012) targets module directories touched by FR-001–FR-011. It does not require a full audit of the entire test suite beyond the one known untagged file (`tests/agent/test_context_unit.py`).
5. Wave ordering (A → B → C → D) is the recommended sequencing but lanes within each wave may be parallelised where write-scope permits.

---

## Success Criteria

1. A full `pytest tests/ -q --tb=no` run reports ≤75 failures after mission merge.
2. All ten GitHub sub-issues (#1301–#1310) are either closed with a linked commit or re-deferred with a new filed issue.
3. `#1298` receives a closing comment documenting the final delta.
4. Every CI `fast-tests-<module>` job that covers a module touched by this mission runs at least one test and passes.
5. `tests/specify_cli/cli/test_doctrine_cli_removed.py` — all three assertions pass.
6. `tests/specify_cli/docs/test_readme_governance.py` — all four assertions pass.
7. `tests/specify_cli/regression/test_twelve_agent_parity.py::test_toml_command_output_is_parseable[implement-gemini]` and `[implement-qwen]` pass.
8. `tests/specify_cli/test_lane_regression_guard.py` for `src/specify_cli/audit/classifiers/wp_files.py` passes.
9. The closeout document `docs/01KSMG8Y-closeout/baseline.md` is committed with the final failure list.

---

## Out of Scope

- Any new feature work (doctrine packs, charter vocabulary, glossary UI).
- The Quality and DevEx Hardening mission (`01KRJGKH4DJCSF277K9QV3WBE7`, epic #822) — separate mission tracking mypy strict, Sonar gate, stale-lane auto-rebase, and upgrade-check UX.
- Fixes for the `test-stabilization-and-debt-pass-01KSF9HJ` WP05–WP08 code (LD-1, MS-1, LD-3, LD-5 architectural debt) — those are approved but unmerged; they may be cherry-picked or re-implemented if they directly resolve a sub-issue, but the architectural restructuring work itself is not in scope.
- Full Sonar quality-gate remediation (coverage uplift, hotspot review) — in scope of the separate quality/devex mission.
- Any change to release versioning or CHANGELOG entries beyond what the test assertions require.
