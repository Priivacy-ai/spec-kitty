# Implementation Plan: Test Stabilization — Pre-Existing Failure Cluster Fix

**Branch**: `kitty/mission-test-stabilization-pre-existing-cluster-fix-01KT396S`
**Date**: 2026-06-02
**Spec**: [spec.md](spec.md)
**Mission ID**: 01KT396SYME74WRQ976RS2ZA0S

---

## Summary

Fix five clusters of pre-existing ("C99") test failures deferred from mission `test-stabilization-and-debt-pass-01KSF9HJ`. All fixes are surgical and local: content corrections to doctrine/glossary files, production-code repairs to the charter synthesizer's hash computation and write-chokepoint, exit-code contract alignment in the `next` CLI, test-isolation fixes and minor production repairs for auth/invocation/mypy/mission-switching subsystems, and stabilisation of the charter integration suite. No public API changes; no new subsystems introduced.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy, httpx, pydantic
**Storage**: Filesystem only (YAML, JSON, Markdown content files; no database)
**Testing**: pytest with 90%+ line coverage on net-new production code; mypy --strict on all modified modules; integration tests for CLI commands
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform)
**Project Type**: Single Python CLI package (`src/specify_cli/`)
**Performance Goals**: N/A — test stabilisation, not performance work
**Constraints**: Zero regression on currently-passing tests; no new SPEC_KITTY_TEST_MODE bypasses in production paths; no changes to public CLI surface

---

## Charter Check

Charter governs this project (`.kittify/charter/charter.md` present).

**Applicable directives:**
- **DIRECTIVE_001** (Architectural Integrity): All write operations must continue to respect the PathGuard chokepoint. No fix may bypass it.
- **DIRECTIVE_003** (Decision Documentation): The root cause and fix rationale for each cluster must be captured in `research.md`.
- **DIRECTIVE_010** (Specification Fidelity): Fixes must make failing tests pass against their stated contract — weakening tests is not permitted.
- **DIRECTIVE_024** (Locality of Change): Each WP is scoped to one cluster; cross-cluster changes are prohibited within a WP.
- **DIRECTIVE_037** (Living Documentation Sync): If any fix changes a CLI error message, the corresponding documentation string must be updated in the same WP.

**Violation table**: No violations. All fixes are local, test-fidelity-preserving, and within the existing architecture.

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/test-stabilization-pre-existing-cluster-fix-01KT396S/
├── plan.md              ← this file
├── research.md          ← Phase 0 findings (all five clusters)
├── quickstart.md        ← dev setup and how to run each cluster's tests
└── tasks.md             ← Phase 2 output (run /spec-kitty.tasks)
```

### Source layout (affected paths)

```
spec-kitty/
├── src/
│   ├── charter/
│   │   └── synthesizer/           ← WP02: hash determinism + PathGuard
│   ├── specify_cli/
│   │   ├── charter_runtime/       ← WP06: charter integration suite
│   │   ├── next/                  ← WP03: exit-code contract
│   │   │   └── _internal_runtime/
│   │   ├── auth/                  ← WP04: token refresh exit code
│   │   ├── mission_step_contracts/
│   │   │   └── executor.py        ← WP05: mypy strict
│   │   └── missions/              ← WP05: mission switching
├── tests/
│   ├── charter/synthesizer/       ← WP02, WP06
│   ├── next/                      ← WP03
│   ├── doctrine/                  ← WP01
│   ├── auth/                      ← WP04
│   └── specify_cli/               ← WP04, WP05
└── glossary/contexts/             ← WP01: anchor fixes
    kitty-specs/                   ← WP04: WP file Pydantic fixes
```

---

## Execution Lanes

Three parallel lanes. Dependencies are documented per WP.

### Lane A — Doctrine & CLI (independent)

| WP | Cluster | Issues closed |
|----|---------|---------------|
| WP01 | Doctrine/glossary anchor drift + tactic schema (#1304) | #1304 |
| WP03 | `next` CLI exit-code regressions (#1305) | #1305 |

WP01 and WP03 are fully independent. They run sequentially within Lane A to avoid conftest state collisions, but neither depends on the other or on any other lane.

### Lane B — Charter Synthesizer → Charter Integration Suite

| WP | Cluster | Dependencies | Issues closed |
|----|---------|-------------|---------------|
| WP02 | Charter synthesizer hash + PathGuard (#1303) | none | #1303 |
| WP06 | Charter integration suite (#1307) | WP02 (some integration failures may be caused by synthesizer bugs) | #1307 |

WP06 is sequenced after WP02 in this lane because a subset of the integration suite failures may be downstream of the synthesizer hash regression. Running synthesizer fixes first reduces confounding.

### Lane C — Residual #1310 (two halves)

| WP | Sub-cluster | Dependencies | Notes |
|----|-------------|-------------|-------|
| WP04 | Auth transport, invocation JSON noise, schema-version wording, WP file Pydantic validation | none | Simpler fixes first |
| WP05 | mypy strict on executor.py, mission switching, implement base-flag plumbing, init skill, architectural tests | WP04 (isolation only, not hard dependency) | More complex fixes |

WP04 and WP05 are sequenced within Lane C to avoid conftest pollution. The WP05 dependency on WP04 is soft (isolation, not functional); if Lane C is routed to a single worktree the sequencing is enforced naturally.

---

## Work Package Summaries

### WP01 — Doctrine/Glossary Content Fixes (#1304)

**Goal**: Make `test_glossary_link_integrity` (× 2) and `test_tactic_compliance` (× 2) pass.

**Root cause**: Two glossary context files contain links whose `#anchor` fragments do not match any heading in the target file. The `five-paradigm-parallel-debugging` tactic YAML has an invalid schema (missing required field or dangling `$ref`).

**What to fix**:
1. Locate the two broken links in `glossary/contexts/*.md`:
   - A link to `#doctrine-pack` — either add the heading to the target file or correct the fragment.
   - A link to `#platform-darwin--platform-linux` — same approach.
2. Locate the `five-paradigm-parallel-debugging` tactic file (likely in `.kittify/doctrine/tactics/` or a doctrine bundle). Fix the schema: add missing required field and resolve all `$ref` values.
3. Run `pytest tests/doctrine/` to confirm green.

**Key files**:
- `glossary/contexts/*.md` (scan for the two broken links)
- Tactic YAML for `five-paradigm-parallel-debugging`
- `tests/doctrine/test_glossary_link_integrity.py`
- `tests/doctrine/test_tactic_compliance.py`

---

### WP02 — Charter Synthesizer Hash Determinism + PathGuard (#1303)

**Goal**: Make `test_manifest`, `test_path_guard`, `test_chokepoint_coverage`, and `test_bundle_validate_cli` pass.

**Root cause**: The charter synthesizer's manifest hash computation is non-deterministic across runs (likely because the artifact list is not sorted before hashing) and/or fixtures are stale against the current schema. Additionally, at least one synthesizer module bypasses PathGuard by calling `Path.write_text` or `Path.write_bytes` directly (caught by the R-10 lint test).

**What to fix**:
1. Audit `src/charter/synthesizer/` for all modules that use direct write primitives. Move each to `PathGuard.write_text` / `PathGuard.write_bytes` / `PathGuard.mkdir` / `PathGuard.replace`.
2. Verify the promote pipeline sorts artifact entries by `(kind, slug)` before computing `manifest_hash`. If not, add the sort.
3. Regenerate any stale test fixtures that depend on the manifest hash.
4. Run `pytest tests/charter/synthesizer/` to confirm green.

**Key files**:
- `src/charter/synthesizer/` (all modules — check each for direct write calls)
- `src/charter/synthesizer/path_guard.py`
- `tests/charter/synthesizer/test_bundle_validate_extension.py`
- `tests/charter/synthesizer/test_path_guard.py`
- `tests/charter/synthesizer/test_manifest.py`

---

### WP03 — `next` CLI Exit-Code Regressions (#1305)

**Goal**: Make `test_blocked_result_exit_code`, `test_terminal_state_exit_code_zero`, `test_advancing_mode_with_result_*`, and `test_result_success_calls_decide_not_query` pass.

**Root cause**: The CLI wrapper in `src/specify_cli/next/__init__.py` does not correctly map `DecisionKind` values to `sys.exit()` codes, and/or the `decide_next` function is routing a result-success through the `query` path instead of the `decide` path.

**What to fix**:
1. Read `src/specify_cli/next/__init__.py` and verify the exit-code switch:
   - `DecisionKind.terminal` → `sys.exit(0)`
   - `DecisionKind.blocked` → `sys.exit(1)` (or non-zero)
   - `DecisionKind.step` → `sys.exit(0)` (continuing)
2. Read `src/runtime/next/decision.py` and `src/specify_cli/next/_internal_runtime/engine.py` to verify that a `success` result routes to `decide_next`, not `query_next`.
3. Run `pytest tests/next/test_next_command_integration.py tests/next/test_query_mode_unit.py` to confirm green.

**Key files**:
- `src/specify_cli/next/__init__.py`
- `src/runtime/next/decision.py`
- `src/runtime/next/_internal_runtime/engine.py`
- `tests/next/test_next_command_integration.py`
- `tests/next/test_query_mode_unit.py`

---

### WP04 — #1310 Residual: Auth, Invocation, Schema Version, WP Files (#1310 first half)

**Goal**: Make the following pass: `test_refresh_through_transport`, `test_do` / `test_profiles` / `test_record` invocation tests, `test_schema_version`, `test_all_kitty_specs_wp_files_validate`.

**Root causes and fixes**:

1. **Auth exit code 2** (`test_refresh_through_transport`): The test invokes `sync status --check` via CliRunner. Exit code 2 in Typer/Click means a usage error — the command is missing a required argument or config before reaching auth logic. Inspect the test fixture: likely a required config file (teamspace config, token storage path) is not being provided. Fix: add the missing fixture setup in conftest or the test itself.

2. **Invocation JSON noise** (`test_do`, `test_profiles`, `test_record`): The `logged_out_on_connected_teamspace` condition is leaking into captured JSON output from a prior test's side effect. Fix: add a conftest-level `autouse` fixture that resets auth state between tests, or monkeypatch the condition getter to return `False` for non-auth tests.

3. **Schema-version wording drift** (`test_schema_version`): The error message in the schema-version validation path was rephrased. Fix: update the string assertion in the test to match the current message, or (if the message was unintentionally changed) restore the original message in the production code.

4. **WP file Pydantic validation** (`test_all_kitty_specs_wp_files_validate`): 6 WP JSON files in `kitty-specs/` were written before a schema change. Fix: update each of the 6 files to add the missing field(s) or correct the value type to match the current `WorkPackage` Pydantic model.

**Key files**:
- `tests/auth/integration/test_refresh_through_transport.py` + conftest
- `tests/specify_cli/invocation/` + conftest
- `tests/specify_cli/migration/test_schema_version.py`
- `tests/specify_cli/status/test_wp_metadata.py`
- The 6 failing WP JSON files (run the test to identify them)

---

### WP05 — #1310 Residual: mypy, Mission Switching, Base-Flag, Architectural (#1310 second half)

**Goal**: Make the following pass: `test_mission_step_contracts_executor_is_mypy_strict_clean`, `test_mission_switching_integration` (× 2), `test_implement_base_flag`, `test_implement_bulk_edit_planning`, architectural tests.

**Root causes and fixes**:

1. **mypy strict** (`test_mission_step_contracts_executor_is_mypy_strict_clean`): `mission_step_contracts/executor.py` has a type annotation gap. Fix: run `mypy --strict src/specify_cli/mission_step_contracts/executor.py` to identify errors, then add the missing annotations.

2. **Mission switching** (`test_mission_switching_integration` × 2): The mission-type guard is preventing valid switches. Fix: read the guard logic in the mission switching code path and relax the condition that is incorrectly blocking.

3. **Implement base-flag plumbing** (`test_implement_base_flag`, `test_implement_bulk_edit_planning`): The `--base` flag is not being wired through to the bulk-edit warning emission. Fix: trace the flag from the CLI command through to the bulk-edit gate and ensure it is passed at each layer.

4. **Architectural tests**: These enforce package boundary constraints. Read the failing test output to identify which boundary is violated, then fix the import or move the code to the correct package.

5. **Init skill** (`test_init_creates_agents_skills_for_codex`): If the `spec-kitty.checklist` skill package is missing from the installed skills tree, the init flow cannot create it. If this is blocked by an external dependency (another mission's WP not yet merged), document the skip with a `pytest.mark.skip` + reason and file a follow-up issue.

**Key files**:
- `src/specify_cli/mission_step_contracts/executor.py`
- Mission switching logic (find via `grep -r "mission_switching" src/`)
- `src/specify_cli/cli/commands/implement.py` (base-flag wiring)
- `tests/architectural/` (read failing tests to identify boundary)
- `tests/missions/test_mission_switching_integration.py`
- `tests/cli/commands/test_implement_base_flag.py`
- `tests/cli/test_implement_bulk_edit_planning.py`

---

### WP06 — Charter Integration Suite (#1307)

**Goal**: Make the charter integration suite pass: charter linting over all layers, synthesize error handling, documentation runtime walk, implement-review smoke, and specify-plan commit boundary tests.

**Root cause**: The WP06/WP08 charter.py split (3328 lines → per-subcommand package) and the `charter_runtime/` umbrella with `sys.modules` shim re-exports may have broken the import paths that integration tests rely on. Some failures may also be unblocked by WP02's synthesizer fixes.

**What to fix**:
1. Run the charter integration suite against the WP02 baseline to identify which failures are already resolved by the synthesizer fix.
2. For remaining failures: trace each failing test's import path through the `charter_runtime/` shim layer. Repair any shim re-export that doesn't correctly forward to the new per-subcommand package location.
3. Verify all five sub-suites (charter lint, synthesize error handling, doc runtime walk, implement-review smoke, specify-plan commit boundary) pass.

**Key files**:
- `src/specify_cli/charter_runtime/__init__.py` (shim layer)
- `src/specify_cli/charter_runtime/lint/` (lint checks)
- `src/specify_cli/charter_runtime/freshness/computer.py`
- `src/charter/` (split package — all modules)
- `tests/charter/` (all integration test files)

**Dependency**: Must run after WP02. The WP06 implementer should pull the WP02 branch into their worktree before starting.

---

## Complexity Tracking

No charter violations. All changes are local and within the existing architecture.
