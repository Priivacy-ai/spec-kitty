# Test Stabilization: Pre-Existing Failure Cluster Fix

**Mission ID**: 01KT396SYME74WRQ976RS2ZA0S
**Mission type**: software-dev
**Status**: Specifying

---

## Purpose

During mission `test-stabilization-and-debt-pass-01KSF9HJ`, 90 pre-existing ("C99") test failures were explicitly deferred into ten sub-issues (#1301–#1310). This mission resolves five of those clusters:

- **#1303** — Charter synthesizer manifest hash non-determinism and PathGuard chokepoint gaps
- **#1304** — Doctrine glossary missing anchors and invalid tactic schema
- **#1305** — `next` CLI exit-code contract regressions
- **#1307** — Charter integration suite failures
- **#1310** — 8 residual sub-failures: auth transport exit code, invocation JSON noise, migration error-message wording, WP file Pydantic validation, init skill package, mypy strict, implement base-flag plumbing, and mission switching

The goal is for each affected GitHub issue to be closeable with a passing test run as evidence, and for the overall suite failure count to decrease measurably.

---

## User Scenarios & Testing

### Scenario A — Developer runs the full test suite and cluster failures are gone

A developer runs `pytest tests/` in the `spec-kitty` package. Before this mission, the five clusters produce approximately 25+ failing tests. After this mission, all tests in each cluster pass. Tests that were already passing before this mission continue to pass (no regression).

**Primary exception**: If a sub-failure turns out to require a design decision beyond simple fixing (e.g., the missing `spec-kitty.checklist` skill depends on a WP from another mission not yet merged), that item is documented as a known skip with a `# TODO: unblock after <issue>` comment and tracked for follow-up — it is not silently suppressed.

### Scenario B — Developer verifies mypy strict compliance

A developer runs `mypy --strict` across the modified modules. It passes with zero new errors introduced. Existing mypy errors in unrelated modules are out of scope.

### Scenario C — Glossary links resolve correctly

A developer runs the glossary integrity tests. All local markdown links in `glossary/contexts/*.md` files resolve to valid files with the correct anchor headings. The two previously missing anchors (`doctrine-pack` and `platform-darwin--platform-linux`) now exist in their target files, or the links are corrected to match existing headings.

### Scenario D — `next` CLI returns the correct exit code

An agent or developer invokes `spec-kitty next` in a state where the result is blocked (non-zero exit) or terminal (zero exit). The CLI exit code matches the contract asserted by the integration tests. The `decide` path is invoked on result-success, not the `query` path.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | The charter synthesizer produces an identical `manifest_hash` for identical artifact inputs regardless of the order in which artifacts are inserted. | Proposed |
| FR-002 | All write operations inside `src/charter/synthesizer/` are routed through `PathGuard`. No module in that package calls `Path.write_text`, `Path.write_bytes`, `Path.mkdir`, or `Path.replace` directly. | Proposed |
| FR-003 | The tests `test_manifest`, `test_path_guard`, `test_chokepoint_coverage`, and `test_bundle_validate_cli` in `tests/charter/synthesizer/test_bundle_validate_extension.py` all pass. | Proposed |
| FR-004 | All local markdown links in `glossary/contexts/*.md` resolve to valid files with the correct anchor headings. The anchors `doctrine-pack` and `platform-darwin--platform-linux` exist in their respective target files, or the links that reference them are corrected to point to headings that exist. | Proposed |
| FR-005 | The `five-paradigm-parallel-debugging` tactic schema is valid and all `$ref` values in it resolve. The tests `test_glossary_link_integrity` and `test_tactic_compliance` pass. | Proposed |
| FR-006 | `spec-kitty next` exits with a non-zero code when the result is `blocked` and exits with code 0 when the result reaches a terminal passing state. The tests `test_blocked_result_exit_code` and `test_terminal_state_exit_code_zero` pass. | Proposed |
| FR-007 | When a `next` invocation produces a successful result, the `decide` code path is taken, not the `query` code path. The test `test_result_success_calls_decide_not_query` passes. | Proposed |
| FR-008 | The charter integration suite passes: charter linting over all layers, synthesize error handling, documentation runtime walk, implement-review smoke, and specify-plan commit boundary tests. | Proposed |
| FR-009 | The auth integration test `test_refresh_through_transport` passes. The `sync status --check` command exits with code 0 after successfully refreshing an expired access token through the token manager. | Proposed |
| FR-010 | Invocation CLI tests (`test_do`, `test_profiles`, `test_record`) pass without `logged_out_on_connected_teamspace` noise appearing in captured JSON output. | Proposed |
| FR-011 | The migration test `test_schema_version` passes. The error message wording in the schema-version validation path matches what the test asserts. | Proposed |
| FR-012 | All WP JSON files in `kitty-specs/` pass Pydantic validation against the current WP model. The 6 legacy WP files that were failing are either updated to conform or the model is made backward-compatible in a non-breaking way. | Proposed |
| FR-013 | The init integration test `test_init_creates_agents_skills_for_codex` passes. The `spec-kitty.checklist` skill package is present and registered so the init flow can create it. | Proposed |
| FR-014 | `mypy --strict` passes on `mission_step_contracts/executor.py`. The test `test_mission_step_contracts_executor_is_mypy_strict_clean` passes. | Proposed |
| FR-015 | The `--base` flag plumbing for the `implement` command works correctly. The tests `test_implement_base_flag` and `test_implement_bulk_edit_planning` pass, including correct warning emission for bulk-edit mode. | Proposed |
| FR-016 | Mission switching between different mission types is not erroneously blocked. The tests `test_mission_switching_integration` (× 2) pass. | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | No currently-passing test is broken by this mission's changes. | Zero regressions measured by running the full suite before and after on the same commit. | Proposed |
| NFR-002 | All modified Python modules pass `mypy --strict` with no new type errors introduced. | Zero new mypy errors in the diff. | Proposed |
| NFR-003 | Any new production code added to fix a failure is covered by at least one test. | 90% line coverage on net-new production lines. | Proposed |
| NFR-004 | Each of the five GitHub issues (#1303, #1304, #1305, #1307, #1310) is closeable with a passing test run referenced in the closing comment. | All five closed by end of mission. | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Fixes must not change the public CLI surface or any behavior observable by end users of `spec-kitty`. Internal test-side patches and data corrections to content files are permitted. | Proposed |
| C-002 | Glossary anchor and tactic schema fixes must be applied to the source content files, not to the tests. Tests must not be weakened to pass around broken content. | Proposed |
| C-003 | No new `SPEC_KITTY_TEST_MODE` bypasses may be introduced in production code paths. The one existing bypass (ceremony-commit refusal) is the maximum permitted scope. | Proposed |
| C-004 | WP file fixes for FR-012 must prefer updating the WP files to match the current schema over changing the Pydantic model, unless the model change is explicitly backward-compatible and does not affect any active mission's state. | Proposed |
| C-005 | Template source files for agent commands live in `src/doctrine/missions/mission-steps/`. If any fix touches command behavior, the source template is updated — not the generated agent copies under `.claude/`, `.amazonq/`, etc. | Proposed |

---

## Success Criteria

1. The full `pytest tests/` run in the `spec-kitty` package shows zero failures in any test previously attributed to clusters #1303, #1304, #1305, #1307, or #1310.
2. The total suite failure count drops by at least 25 compared to the pre-mission baseline.
3. All five GitHub issues are closed with a passing CI reference or a manual test-run excerpt in the closing comment.
4. `mypy --strict` passes on all modules touched by this mission's commits.

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `SynthesisManifest` | The charter synthesizer's manifest model. Its `manifest_hash` must be deterministic across identical inputs (FR-001). |
| `PathGuard` | The write-chokepoint class in `src/charter/synthesizer/path_guard.py`. All synthesizer writes must go through it (FR-002). |
| `glossary/contexts/` | Directory of canonical glossary context markdown files. Links within them must resolve to valid anchors (FR-004). |
| `five-paradigm-parallel-debugging` | A tactic defined in the doctrine layer whose YAML schema is currently invalid (FR-005). |
| `DecisionKind` | The enum in `src/runtime/next/decision.py` whose values drive the `next` CLI exit-code mapping (FR-006, FR-007). |
| `TokenManager` | The auth subsystem component responsible for detecting expired tokens and refreshing them via the single-flight lock (FR-009). |
| `mission_step_contracts/executor.py` | The module that must pass `mypy --strict` (FR-014). |

---

## Assumptions

1. The `test_init_creates_agents_skills_for_codex` failure (FR-013) may depend on WP03 of another mission that has not yet merged. If it cannot be independently fixed, it will be documented as a known external dependency and skipped with a tracked comment rather than silently suppressed.
2. The charter integration suite failures (FR-008) are caused by the WP06/WP08 charter.py split and the `sys.modules` shim layer in `charter_runtime/`. The shim re-exports are assumed to be the correct architectural mechanism — this mission repairs the shim layer, not the split.
3. The 6 WP files failing Pydantic validation (FR-012) are legacy files that pre-date a schema change. Updating the files to the current schema is preferred over adding backward-compatibility shims in the model.
4. The `logged_out_on_connected_teamspace` noise in invocation tests (FR-010) is a test-isolation issue — the condition is being set by another test and not cleaned up. The fix is a conftest-level teardown or monkeypatch, not a production-code change.

---

## Out of Scope

- Issues #1301 (shared-package events drift residual), #1302 (TOML rendering escape bug), #1306 (status/lifecycle event drift), #1308 (README + CHANGELOG drift), and #1309 (meta.json + lane regression) — addressed in separate missions.
- Any newly discovered failures not listed in the five target clusters. Those may be filed as new issues but are not fixed here.
- Performance improvements or refactoring beyond what is required to make the failing tests pass.
