# Implementation Plan: Pre-Doctrine Test Stabilization

**Branch**: `feat/pre-doctrine-stabilization-remediation` | **Date**: 2026-05-27 | **Spec**: [spec.md](spec.md)  
**Mission ID**: 01KSMG8Y0V5V2ZM4YEQMKFWN2K  
**Input**: `kitty-specs/pre-doctrine-test-stabilization-01KSMG8Y/spec.md`

---

## Summary

Fix all 10 DIR-013 sub-issues (#1301–#1310) from the 01KSF9HJ triage that were filed but never merged into `upstream/main`. Four confirmed bugs are directly verifiable in current `main` (TOML escape, README Governance, `wp_files.py` frontmatter lane, doctrine CLI group). Six clusters require targeted per-surface investigation and fix. All tests written during this mission carry CI-quality marks (`fast` + domain mark). Final deliverable: ≤75-failure baseline committed to `docs/01KSMG8Y-closeout/baseline.md` and all ten GitHub issues resolved or re-deferred.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pytest 9.x, ruff, mypy --strict (for surfaces explicitly in scope), typer, spec-kitty CLI  
**Storage**: Filesystem only — YAML, JSON, JSONL, Markdown (no database mutations)  
**Testing**: pytest with `pytestmark` module-level marks; CI splits on `fast`, `integration`, `e2e`, `architectural`, `contract`, `doctrine`; new tests require `[pytest.mark.fast]` plus one domain mark  
**Target Platform**: Linux / macOS / Windows (cross-platform CLI tool)  
**Project Type**: Single Python project (`src/specify_cli`, `src/charter`, `src/doctrine`, `src/kernel`)  
**Performance Goals**: Full-suite run time must not regress by > 10% vs. pre-mission baseline (~924 s)  
**Constraints**: All fixes are behaviour-preserving; no feature extension; DIR-013 applies throughout; Phase-2 frontmatter-lane reads are illegal; `meta.json` writes must route through `feature_metadata/mission_metadata.py`

---

## Charter Check

**Mode**: compact. Applicable directives from project charter:

| Directive | Impact on this mission |
|-----------|----------------------|
| DIR-005 | Tests added for every changed behaviour — verified |
| DIR-006 | mypy --strict must pass for surfaces touched (executor.py, WP scope) |
| DIR-013 | New pre-existing failures encountered during implementation → file a GitHub issue before treating as baseline |

No charter violations anticipated. All fixes are additive corrections to existing behaviour. The doctrine-CLI removal (FR-004) was originally committed to by mission 01KP54J6 and is being completed here — not a new architectural decision.

---

## Project Structure

### Planning artifacts

```
kitty-specs/pre-doctrine-test-stabilization-01KSMG8Y/
├── spec.md              ← committed
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── tasks.md             ← /spec-kitty.tasks output (not yet)
├── checklists/
│   └── requirements.md  ← committed
└── tasks/               ← /spec-kitty.tasks output (not yet)
```

### Source touchpoints (by wave)

```
Wave A — quick fixes
  src/specify_cli/missions/software-dev/command-templates/implement.md   ← FR-001
  tests/specify_cli/regression/_twelve_agent_baseline/                   ← FR-001 snapshot refresh
  README.md                                                               ← FR-002
  src/specify_cli/audit/classifiers/wp_files.py                          ← FR-003
  src/specify_cli/cli/commands/__init__.py                                ← FR-004

Wave B — structural fixes
  src/doctrine/glossary/                                                   ← FR-005
  src/doctrine/tactics/built-in/five-paradigm-parallel-debugging.tactic.yaml  ← FR-005
  src/specify_cli/status/emit.py (or mission_creation.py)                ← FR-006 (SpecifyStarted)
  src/specify_cli/git/ (atomic commit flow)                               ← FR-006
  src/specify_cli/tasks/move_task.py                                      ← FR-006
  src/specify_cli/charter*/                                               ← FR-007
  tests/integration/                                                      ← FR-007
  src/specify_cli/next/decision.py (or runtime_bridge.py)                ← FR-008
  src/specify_cli/cli/commands/next_cmd.py                               ← FR-008

Wave C — shared-package / architectural
  src/specify_cli/sync/restart.py                                         ← FR-009 (allowlist)
  tests/sync/                                                             ← FR-009
  tests/contract/                                                         ← FR-009
  src/specify_cli/charter/ (synthesizer)                                  ← FR-010
  src/specify_cli/mission_step_contracts/executor.py                      ← FR-011 (mypy)
  src/specify_cli/cli/commands/invocations_cmd.py (or similar)            ← FR-011 (JSON noise)
  auth/                                                                   ← FR-011 (exit code)

Wave D — closeout
  tests/ (mark audit — all touched modules)                              ← FR-012
  docs/01KSMG8Y-closeout/                                                ← FR-013
```

---

## Work Package Structure

### Overview

| WP | Wave | FRs | Title | Lane | Parallel group |
|----|------|-----|-------|------|---------------|
| WP01 | A | FR-001 | TOML escape fix + snapshot refresh | lane-a | 0 |
| WP02 | A | FR-002, FR-003, FR-004 | README Governance + chokepoint guards | lane-b | 0 |
| WP03 | B | FR-005 | Doctrine / glossary anchor + tactic repair | lane-c | 0 |
| WP04 | B | FR-006 | Status / lifecycle event drift | lane-d | 0 |
| WP05 | B | FR-007 | Charter integration suite regressions | lane-e | 0 |
| WP06 | B | FR-008 | `next` CLI exit-code regressions | lane-f | 0 |
| WP07 | C | FR-009 | Shared-package events drift residual | lane-g | 1 |
| WP08 | C | FR-010 | Charter synthesizer determinism | lane-h | 1 |
| WP09 | C | FR-011 | Misc debt — auth / invocation / mypy / mission switching | lane-i | 1 |
| WP10 | D | FR-012 | CI test-mark audit + guard test | lane-j | 2 |
| WP11 | D | FR-013 | Full-suite re-baseline + issue closeout | lane-planning | 3 |

**Dependency graph:**

```
WP01 ──┐
WP02 ──┤
WP03 ──┤
WP04 ──┼──► WP10 (mark audit) ──► WP11 (closeout)
WP05 ──┤
WP06 ──┘
WP07 ──┐
WP08 ──┤
WP09 ──┘
```

WP01–WP06 (waves A + B) can run in parallel; WP07–WP09 (wave C) can run in parallel;
WP10 depends on WP01–WP09 being merged; WP11 depends on WP10.

### WP01 — TOML escape fix + snapshot refresh (FR-001 / #1302)

**Write scope:**
- `src/specify_cli/missions/software-dev/command-templates/implement.md` — escape `\.py$` in the `rg` command at line 168 (use `'[.]py$'` or `grep -E '\.py$'` to avoid the unescaped backslash in TOML-format rendered output)
- `tests/specify_cli/regression/_twelve_agent_baseline/` — regenerate all affected agent snapshots via `PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v`

**Acceptance:** `test_toml_command_output_is_parseable[implement-gemini]` and `[implement-qwen]` pass; snapshot diff contains only the template change.

**Test marks required:** `pytest.mark.unit` + `pytest.mark.fast` (parity test already has `pytestmark = [pytest.mark.unit]`)

### WP02 — README Governance + chokepoint guards (FR-002, FR-003, FR-004 / #1308, #1309, #1310-partial)

**Write scope:**
- `README.md` — add `## Governance layer` section with links to `docs/trail-model.md` and `docs/host-surface-parity.md`
- `src/specify_cli/audit/classifiers/wp_files.py:92` — replace `frontmatter.get("lane")` with `specify_cli.status.lane_reader.get_wp_lane()` call; update imports
- `src/specify_cli/cli/commands/__init__.py:40,78` — remove `doctrine` import and `add_typer` registration

**Acceptance:** All four `test_readme_governance` assertions pass; `test_lane_regression_guard[src/specify_cli/audit/classifiers/wp_files.py]` passes; all three `test_doctrine_cli_removed` assertions pass.

**Test marks required:** existing tests already tagged; no new tests needed (pure production fix)

### WP03 — Doctrine / glossary anchor + tactic repair (FR-005 / #1304)

**Write scope:**
- `src/doctrine/glossary/` — add anchors `doctrine-pack` and `platform-darwin--platform-linux` in the appropriate context YAML files
- `src/doctrine/tactics/built-in/five-paradigm-parallel-debugging.tactic.yaml` — fix schema violations and unresolved refs

**Investigation required:** run `pytest tests/doctrine/test_glossary_link_integrity.py tests/doctrine/test_tactic_compliance.py -v` to pinpoint which context files are missing the anchors and which refs are unresolved.

**Acceptance:** All four failing tests in `test_glossary_link_integrity` and `test_tactic_compliance` pass.

**Test marks required:** existing tests already tagged with `pytest.mark.doctrine`

### WP04 — Status / lifecycle event drift (FR-006 / #1306)

**Write scope (four independent fixes):**
1. `SpecifyStarted` event not emitted at mission-create (#1067 regression) — surface: `src/specify_cli/core/mission_creation.py` or `src/specify_cli/status/emit.py`
2. Atomic commit flow leaves status artifacts dirty after `move_task` — surface: `src/specify_cli/git/` (atomic commit helpers)
3. Wrong commit message bubbled to lane branch — surface: `src/specify_cli/tasks/move_task.py`
4. `implement` does not block on alloc failure — surface: `src/specify_cli/cli/commands/implement.py` or related

**Investigation required:** read each failing test to identify the exact call path before editing production code.

**Acceptance:** `test_atomic_status_commits_unit`, `test_mission_creation_specify_started` (×2), `test_move_task_git_validation_unit` (the commit-message variant), and `test_status_emit_on_alloc_failure` all pass.

**Test marks required:** new tests (if any) must carry `[pytest.mark.fast, pytest.mark.git_repo]` or `[pytest.mark.integration, pytest.mark.git_repo]` as appropriate

### WP05 — Charter integration suite regressions (FR-007 / #1307)

**Write scope (six independent integration failures):**
1. Org-layer source name missing in lint output — `src/specify_cli/charter_lint/`
2. Wrong error class from `synthesize_without_charter_md` — `src/specify_cli/charter/` or `src/specify_cli/cli/commands/charter/`
3. `discover` action blocks despite `spec.md` authored — `src/specify_cli/next/` or runtime walk
4. implement-review-retrospect smoke — cross-cutting
5. Wrong branch in rejection-cycle handoff — `src/specify_cli/tasks/move_task.py` or implement/review path
6. Substantive plan not auto-committed in specify-plan — `src/specify_cli/cli/commands/`

**Investigation required:** run each failing integration test individually with `--tb=short` to identify the minimal reproduction before touching production code.

**Acceptance:** All six integration tests in `test_charter_lint_lints_all_layers`, `test_charter_synthesize_fresh`, `test_documentation_runtime_walk`, `test_implement_review_retrospect_smoke`, `test_rejection_cycle`, `test_specify_plan_commit_boundary` pass.

**Test marks required:** integration tests already carry `[pytest.mark.integration, pytest.mark.git_repo]`; any new tests follow the same pattern

### WP06 — `next` CLI exit-code regressions (FR-008 / #1305)

**Write scope:**
- `src/specify_cli/next/runtime_bridge.py` or `src/specify_cli/next/decision.py` — restore exit-0 for terminal states and exit-1 for blocked states
- `src/specify_cli/cli/commands/next_cmd.py` — verify exit-code propagation from `decide_next_via_runtime`

**Investigation required:** run `pytest tests/next/ -v --tb=short` to identify where exit codes diverge from the expected contract.

**Acceptance:** All four failing tests in `test_next_command_integration` (exit codes, advancing mode) and `test_query_mode_unit` (mock invoked) pass.

**Test marks required:** new tests (if any) must carry `[pytest.mark.fast, pytest.mark.unit]`

### WP07 — Shared-package events drift residual (FR-009 / #1301)

**Write scope:**
- `src/specify_cli/sync/restart.py` — add to daemon-allowlist or refactor unauthorized call site
- `tests/sync/` — fix `test_lifecycle_readiness` (`BuildRegistered` queued at init) and `test_event_queued_when_no_websocket` (`MissionOriginBound` queued)
- `tests/contract/test_handoff_fixtures.py` — add `actor` and `wp_title` fields to `WPCreated` payload
- `src/specify_cli/spec_kitty_events/` — remove vendored events tree if it re-appeared
- Contract fixture YAML — add `# pydantic_model:` frontmatter to the flagged example

**Investigation required:** confirm current `spec_kitty_events` package version vs. `uv.lock` pin; run `uv sync --frozen` if mismatched before editing test code.

**Acceptance:** All six tests listed in #1301 pass.

**Test marks required:** sync tests already carry `[pytest.mark.fast]` or `[pytest.mark.integration]`; follow existing convention

### WP08 — Charter synthesizer determinism (FR-010 / #1303)

**Write scope:**
- `src/specify_cli/charter/` (synthesizer) — fix manifest hash determinism (sort keys before hashing, or use content-addressed deterministic ordering)
- `src/specify_cli/charter/path_guard.py` — block direct write primitives from bypassing chokepoint
- Test fixtures — refresh stored manifest hashes after fix

**Investigation required:** run `pytest tests/charter/synthesizer/ -v --tb=long` to identify the exact hash computation path.

**Acceptance:** All five `test_bundle_validate_extension` assertions pass.

**Test marks required:** charter tests already carry marks; new tests use `[pytest.mark.fast, pytest.mark.unit]`

### WP09 — Misc debt — auth / invocation / mypy / mission switching (FR-011 / #1310)

**Write scope (in-scope items):**
- `src/specify_cli/auth/` — fix auth integration exit-code returning 2 instead of expected value
- `src/specify_cli/cli/commands/invocations_cmd.py` (or related) — prevent `logged_out_on_connected_teamspace` noise from leaking into JSON output
- `src/specify_cli/mission_step_contracts/executor.py` — fix mypy --strict failures
- Legacy `kitty-specs/` WP files — fix or exclude from Pydantic validation the 6 WP files failing `test_all_kitty_specs_wp_files_validate`
- Mission-switching tests — identify and fix the blocking condition in `test_mission_switching_integration`

**Re-defer (per C-008):**
- `spec-kitty.checklist` skill package restoration (#1310 item) — file a new sub-issue; this requires dedicated template work outside this mission's scope
- Schema-version wording drift — minor UX; file a new issue for CHANGELOG-tracked fix

**Acceptance:** Five of the ~15 `#1310` failures resolved in-scope; re-deferred items each have a new GitHub issue filed before WP09 is declared complete.

**Test marks required:** new tests carry `[pytest.mark.fast, pytest.mark.unit]` or `[pytest.mark.integration]` as appropriate

### WP10 — CI test-mark audit + guard test (FR-012)

**Write scope:**
- All test files in modules touched by WP01–WP09: verify each has a `pytestmark` with at least one canonical CI-quality mark
- `tests/agent/test_context_unit.py` — add missing `pytestmark`
- New guard test (location TBD — likely `tests/specify_cli/test_codebase_sweep.py` or a new `tests/architectural/test_test_mark_coverage.py`) — asserts that every `test_*.py` file in the directories touched by this mission has a module-level `pytestmark`

**Acceptance:** No test file in a touched directory is missing `pytestmark`; the new guard test passes; `tests/agent/test_context_unit.py` is tagged.

**Test marks required:** guard test itself carries `[pytest.mark.architectural, pytest.mark.fast]`

### WP11 — Full-suite re-baseline + issue closeout (FR-013) — planning lane

**Write scope (planning lane — no worktree):**
- `docs/01KSMG8Y-closeout/baseline.md` — record full `pytest tests/ -q --tb=no` output and failure list post-merge
- GitHub issues — close #1301–#1310 with linking commits, or re-defer with new sub-issues
- `#1298` — post closing comment with final delta
- `kitty-specs/pre-doctrine-test-stabilization-01KSMG8Y/` — final status update

**Gate:** Failure count ≤75. If > 75, identify remaining clusters, file DIR-013 issues, document in baseline.md, and declare mission complete with the known gap and a follow-on issue.

---

## Phase 0: Research

See `research.md` for consolidated findings from the pre-mission cross-examination.

Key pre-confirmed root causes requiring no further research:
- FR-001: `rg '\.py$'` at `implement.md:168` → unescaped `\` in TOML multi-line basic string
- FR-002: `README.md` has 0 occurrences of `## Governance layer`
- FR-003: `wp_files.py:92` → `frontmatter.get("lane")`
- FR-004: `commands/__init__.py:78` → `add_typer(doctrine_module.app, name="doctrine")`

Items requiring targeted investigation before editing (WP03–WP09):
- FR-005: exact anchor context files + tactic schema errors → run tests with `--tb=long`
- FR-006: four independent call paths → read each failing test before editing
- FR-007: six integration failures → run each in isolation before editing
- FR-008: `decide_next_via_runtime` exit-code propagation path
- FR-009: daemon-allowlist entries + payload schema for `WPCreated`
- FR-010: synthesizer hash computation source
- FR-011: auth exit-code source, JSON output filtering point, mypy errors in executor.py

---

## Phase 1: Design Notes

This mission is purely corrective. There are no new data models, API contracts, or external-facing schemas. The design notes capture invariants that each implementer must respect:

### Invariant: Phase-2 lane authority (C-003)

No code path may read `frontmatter.get("lane")` or `frontmatter.get("status")` as the WP lane value. The canonical read is `specify_cli.status.lane_reader.get_wp_lane(feature_dir, wp_id)`. Any test that was previously asserting frontmatter lane values must be updated to assert against the event-log-derived lane.

### Invariant: chokepoint routing (C-004)

All `meta.json` mutations must pass through `src/specify_cli/feature_metadata/mission_metadata.py`. Any code path that writes a `meta.json` key directly (e.g., `Path(...) / "meta.json").write_text(...)`) is a regression.

### Invariant: test-mark contract (FR-012)

Every `test_*.py` file in a directory touched by this mission must have:
```python
pytestmark = [pytest.mark.<primary_mark>]
# or
pytestmark = [pytest.mark.<primary_mark>, pytest.mark.<secondary_mark>]
```
Where `<primary_mark>` is one of: `fast`, `unit`, `integration`, `e2e`, `slow`, `contract`, `architectural`, `doctrine`.

Tests that require a real git repository also add `pytest.mark.git_repo`. Tests that spawn subprocesses or touch the network add `pytest.mark.non_sandbox`.

### Doctrine CLI removal safety (FR-004)

Removing `doctrine` from `add_typer` in `__init__.py` must not be confused with the `charter` group (which must remain). The `doctrine.py` command module file may remain on disk (it is imported nowhere after the deregistration); deleting it is optional and out of scope.

---

## Gates

| Gate | Condition |
|------|-----------|
| Spec committed + substantive | ✅ — committed at `587f2c3da` |
| No NEEDS CLARIFICATION markers | ✅ — decision verify returned `status: clean` |
| Plan committed + substantive | Pending — this document |
| All WP11 baseline gates | ≤75 failures, all sub-issues resolved |

---

## Branch Contract (repeated per protocol)

- **Current branch at plan start**: `feat/pre-doctrine-stabilization-remediation`
- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`
- `branch_matches_target: true` ✓

**Next step**: `/spec-kitty.tasks` to generate WP files and finalize lanes.
