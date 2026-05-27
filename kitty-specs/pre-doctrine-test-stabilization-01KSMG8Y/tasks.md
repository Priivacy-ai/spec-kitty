# Tasks: Pre-Doctrine Test Stabilization

**Mission**: `pre-doctrine-test-stabilization-01KSMG8Y`  
**Branch**: `feat/pre-doctrine-stabilization-remediation`  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Generated**: 2026-05-27T11:26:35Z

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-----------|----|---------|
| T001 | Fix `rg '\.py$'` → `grep -E '[.]py$'` in implement.md:168 | WP01 | |
| T002 | Regenerate twelve-agent snapshots (PYTEST_UPDATE_SNAPSHOTS=1) | WP01 | |
| T003 | Verify gemini/qwen parity tests pass; confirm snapshot diff scope | WP01 | |
| T004 | Pre-check skill file links in advise/runtime-next SKILL.md files | WP02 | |
| T005 | Add `## Governance layer` section to README.md (6 assertions) | WP02 | |
| T006 | Replace frontmatter lane read in wp_files.py:92 with guarded get_wp_lane() | WP02 | |
| T007 | Add test: classify_wp_files() does not raise on mission without event log | WP02 | |
| T008 | Remove doctrine import and add_typer from commands/__init__.py:40,78 | WP02 | |
| T009 | Run failing doctrine/glossary tests to identify exact missing anchors | WP03 | |
| T010 | Add `doctrine-pack` anchor to correct glossary context YAML | WP03 | |
| T011 | Add `platform-darwin--platform-linux` anchor to correct context YAML | WP03 | |
| T012 | Fix five-paradigm-parallel-debugging.tactic.yaml schema + unresolved refs | WP03 | |
| T013 | Fix SpecifyStarted event not emitted at mission create | WP04 | [P] |
| T014 | Fix atomic commit leaving dirty status artifacts after move_task | WP04 | [P] |
| T015 | Fix wrong commit message on lane branch in move_task.py | WP04 | [P] |
| T016 | Fix implement not blocking on alloc failure | WP04 | [P] |
| T017 | Fix org-layer source name missing in charter lint output | WP05 | [P] |
| T018 | Fix wrong error class from synthesize_without_charter_md | WP05 | [P] |
| T019 | Fix discover action blocking despite spec.md authored (check charter_preflight first) | WP05 | [P] |
| T020 | Fix implement-review-retrospect smoke test failure | WP05 | [P] |
| T021 | Fix wrong branch in rejection-cycle handoff (coordinate with WP04 re: move_task.py) | WP05 | [P] |
| T022 | Fix substantive plan not auto-committed in specify-plan | WP05 | [P] |
| T023 | Investigate decide_next_via_runtime return value for terminal states | WP06 | |
| T024 | Fix Decision.kind return for terminal states in runtime_bridge.py | WP06 | |
| T025 | Update mock target in test_query_mode_unit.py if patch path changed | WP06 | |
| T026 | Add restart.py to daemon-allowlist or refactor unauthorized call | WP07 | [P] |
| T027 | Fix BuildRegistered not queued at init | WP07 | [P] |
| T028 | Fix MissionOriginBound not queued without WebSocket | WP07 | [P] |
| T029 | Add actor/wp_title fields to WPCreated fixture payload | WP07 | [P] |
| T030 | Remove vendored events tree src/specify_cli/spec_kitty_events/ if present | WP07 | [P] |
| T031 | Add # pydantic_model: frontmatter to YAML codeblock in example fixture | WP07 | [P] |
| T032 | Run charter synthesizer tests to identify exact hash computation path | WP08 | |
| T033 | Sort file lists before hashing in synthesizer manifest to ensure determinism | WP08 | |
| T034 | Enforce path_guard.py chokepoint for direct write primitives | WP08 | |
| T035 | Refresh stored manifest hashes in test fixtures | WP08 | |
| T036 | Fix auth integration exit-code returning wrong value | WP09 | [P] |
| T037 | Prevent logged_out_on_connected_teamspace noise from JSON CLI output | WP09 | [P] |
| T038 | Fix mypy --strict failures in mission_step_contracts/executor.py | WP09 | [P] |
| T039 | Fix or exclude legacy kitty-specs/ WP files failing Pydantic validation | WP09 | [P] |
| T040 | Investigate and fix mission-switching blocking condition | WP09 | [P] |
| T041 | File GitHub issues for re-deferred items (checklist skill, schema-version wording) | WP09 | |
| T050 | Delete all stray test-feature-* dirs from kitty-specs/ + add pytest teardown + .gitignore guard | WP09 | |
| T042 | Audit all WP01-WP09 touched test directories for missing pytestmark | WP10 | |
| T043 | Add pytestmark to tests/agent/test_context_unit.py | WP10 | [P] |
| T044 | Add category mark to tests/specify_cli/test_lane_regression_guard.py | WP10 | [P] |
| T045 | Verify existing architectural guard passes without modification | WP10 | |
| T046 | Run PWHEADLESS=1 pytest tests/ -q --tb=no and record output | WP11 | |
| T047 | Commit baseline.md to docs/01KSMG8Y-closeout/ | WP11 | |
| T048 | Close or re-defer GitHub issues #1301-#1310 with linking commits | WP11 | |
| T049 | Post closing comment on #1298 with final failure delta | WP11 | |

---

## Work Package Breakdown

### Wave A — Zero-risk quick fixes

---

## WP01 — TOML escape fix + snapshot refresh (FR-001 / #1302)

**Goal**: Fix unescaped backslash in `implement.md` that causes `TOMLDecodeError` for gemini/qwen agents; refresh all twelve-agent snapshots.  
**Priority**: High (blocks gemini/qwen usage and parity test suite)  
**Estimated prompt size**: ~250 lines  
**Execution lane**: lane-a  
**Profile**: `implementer-ivan`  

**Included subtasks:**
- [x] T001 Fix `rg '\.py$'` → `grep -E '[.]py$'` in implement.md:168 (WP01)
- [x] T002 Regenerate twelve-agent snapshots (PYTEST_UPDATE_SNAPSHOTS=1) (WP01)
- [x] T003 Verify gemini/qwen parity tests pass; confirm snapshot diff scope (WP01)

**Implementation notes:**
1. Edit `src/specify_cli/missions/software-dev/command-templates/implement.md` line 168
2. Run `PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v`
3. Confirm all 12 (or 13 — count first) agent snapshots updated with only the rg→grep substitution
4. Run parity tests without `PYTEST_UPDATE_SNAPSHOTS` to verify all pass

**Dependencies**: none  
**Prompt file**: [tasks/WP01-toml-escape-fix-snapshot-refresh.md](tasks/WP01-toml-escape-fix-snapshot-refresh.md)

---

## WP02 — README Governance + chokepoint guards (FR-002, FR-003, FR-004 / #1308, #1309, #1310-partial)

**Goal**: Three independent quick fixes: add README governance section, fix frontmatter-lane read in wp_files.py, remove doctrine CLI group.  
**Priority**: High (4 confirmed test failures directly verifiable)  
**Estimated prompt size**: ~380 lines  
**Execution lane**: lane-b  
**Profile**: `implementer-ivan`  

**Included subtasks:**
- [ ] T004 Pre-check skill file links in advise/runtime-next SKILL.md files (WP02)
- [ ] T005 Add `## Governance layer` section to README.md (6 assertions) (WP02)
- [ ] T006 Replace frontmatter lane read in wp_files.py:92 with guarded get_wp_lane() (WP02)
- [ ] T007 Add test: classify_wp_files() does not raise on mission without event log (WP02)
- [ ] T008 Remove doctrine import and add_typer from commands/__init__.py:40,78 (WP02)

**Implementation notes:**
1. FR-002: Read both skill files first; fix any broken links found (DIR-013 if unexpected)
2. FR-002: Add governance section to README with all 6 required elements
3. FR-003: Add guarded get_wp_lane() to wp_files.py; add guard-fallback test
4. FR-004: Remove 2 lines from commands/__init__.py; verify charter group unaffected

**Dependencies**: none  
**Prompt file**: [tasks/WP02-readme-governance-chokepoint-guards.md](tasks/WP02-readme-governance-chokepoint-guards.md)

---

### Wave B — Structural fixes

---

## WP03 — Doctrine / glossary anchor + tactic repair (FR-005 / #1304)

**Goal**: Add two missing glossary anchors and fix the five-paradigm-parallel-debugging tactic schema.  
**Priority**: High (4 failing doctrine tests)  
**Estimated prompt size**: ~280 lines  
**Execution lane**: lane-c  
**Profile**: `curator-carla`  

**Included subtasks:**
- [x] T009 Run failing doctrine/glossary tests to identify exact missing anchors (WP03)
- [x] T010 Add `doctrine-pack` anchor to correct glossary context YAML (WP03)
- [x] T011 Add `platform-darwin--platform-linux` anchor to correct context YAML (WP03)
- [x] T012 Fix five-paradigm-parallel-debugging.tactic.yaml schema + unresolved refs (WP03)

**Implementation notes:**
1. Always run tests first: `pytest tests/doctrine/ -v --tb=long` — output names the exact files
2. Anchors are content additions to existing YAML; no schema version bump needed
3. Fix tactic schema in-place; run tactic compliance test to confirm

**Dependencies**: none  
**Prompt file**: [tasks/WP03-doctrine-glossary-anchor-tactic-repair.md](tasks/WP03-doctrine-glossary-anchor-tactic-repair.md)

---

## WP04 — Status / lifecycle event drift (FR-006 / #1306)

**Goal**: Fix four independent status/lifecycle event regressions; holds exclusive ownership of `move_task.py`.  
**Priority**: High (4 failing status tests)  
**Estimated prompt size**: ~400 lines  
**Execution lane**: lane-d  
**Profile**: `debugger-debbie`  

**Included subtasks:**
- [ ] T013 Fix SpecifyStarted event not emitted at mission create (WP04)
- [ ] T014 Fix atomic commit leaving dirty status artifacts after move_task (WP04)
- [ ] T015 Fix wrong commit message on lane branch in move_task.py (WP04)
- [ ] T016 Fix implement not blocking on alloc failure (WP04)

**Implementation notes:**
1. Run each failing test in isolation with `--tb=long` before editing production code
2. WP04 has **exclusive ownership** of `src/specify_cli/tasks/move_task.py`
3. If WP05 item 5 (rejection-cycle handoff) is rooted in move_task.py, coordinate the fix here
4. Four independent fixes — each can be addressed in any order

**Dependencies**: none  
**Prompt file**: [tasks/WP04-status-lifecycle-event-drift.md](tasks/WP04-status-lifecycle-event-drift.md)

---

## WP05 — Charter integration suite regressions (FR-007 / #1307)

**Goal**: Fix six independent charter integration test failures.  
**Priority**: High (6 failing integration tests)  
**Estimated prompt size**: ~460 lines  
**Execution lane**: lane-e  
**Profile**: `debugger-debbie`  

**Included subtasks:**
- [ ] T017 Fix org-layer source name missing in charter lint output (WP05)
- [ ] T018 Fix wrong error class from synthesize_without_charter_md (WP05)
- [ ] T019 Fix discover action blocking despite spec.md authored (check charter_preflight first) (WP05)
- [ ] T020 Fix implement-review-retrospect smoke test failure (WP05)
- [ ] T021 Fix wrong branch in rejection-cycle handoff (coordinate with WP04 re: move_task.py) (WP05)
- [ ] T022 Fix substantive plan not auto-committed in specify-plan (WP05)

**Implementation notes:**
1. Run each integration test in isolation with `-x --tb=short` before editing
2. **Do NOT touch** `src/specify_cli/tasks/move_task.py` — owned by WP04
3. **Do NOT begin** `runtime_bridge.py` edits until WP06 is merged (shared file risk)
4. T019 fix may be in `src/specify_cli/charter_preflight/` — check there before `runtime_bridge.py`
5. WP05 item 2 touches CLI adapter only (`src/specify_cli/cli/commands/charter/synthesize.py`), not `src/charter/synthesizer/errors.py`

**Dependencies**: Coordinate with WP04 before touching move_task.py; coordinate with WP06 before touching runtime_bridge.py  
**Prompt file**: [tasks/WP05-charter-integration-regressions.md](tasks/WP05-charter-integration-regressions.md)

---

## WP06 — `next` CLI exit-code regressions (FR-008 / #1305)

**Goal**: Fix `decide_next_via_runtime` returning wrong Decision.kind for terminal states; update mock targets if call-path changed.  
**Priority**: High (4 failing next-CLI tests)  
**Estimated prompt size**: ~280 lines  
**Execution lane**: lane-f  
**Profile**: `debugger-debbie`  

**Included subtasks:**
- [x] T023 Investigate decide_next_via_runtime return value for terminal states (WP06)
- [x] T024 Fix Decision.kind return for terminal states in runtime_bridge.py (WP06)
- [x] T025 Update mock target in test_query_mode_unit.py if patch path changed (WP06)

**Implementation notes:**
1. Run `pytest tests/next/ -v --tb=long` first to identify divergence point
2. Fix is in `runtime_bridge.py::decide_next_via_runtime` return value — NOT in next_cmd.py
3. Do NOT change the exit-code mapping in `next_cmd.py`
4. If mock is not being hit, patch target likely changed — check current import path

**Dependencies**: WP05 must not begin runtime_bridge.py edits until WP06 is merged  
**Prompt file**: [tasks/WP06-next-cli-exit-code-regressions.md](tasks/WP06-next-cli-exit-code-regressions.md)

---

### Wave C — Shared-package and architectural fixes

---

## WP07 — Shared-package events drift residual (FR-009 / #1301)

**Goal**: Fix six residual structural failures from the events package alignment done in 01KSF9HJ.  
**Priority**: Medium (6 sync/contract test failures)  
**Estimated prompt size**: ~380 lines  
**Execution lane**: lane-g  
**Profile**: `implementer-ivan`  

**Included subtasks:**
- [ ] T026 Add restart.py to daemon-allowlist or refactor unauthorized call (WP07)
- [ ] T027 Fix BuildRegistered not queued at init (WP07)
- [ ] T028 Fix MissionOriginBound not queued without WebSocket (WP07)
- [ ] T029 Add actor/wp_title fields to WPCreated fixture payload (WP07)
- [ ] T030 Remove vendored events tree src/specify_cli/spec_kitty_events/ if present (WP07)
- [ ] T031 Add # pydantic_model: frontmatter to YAML codeblock in example fixture (WP07)

**Implementation notes:**
1. Run `uv sync --frozen` first; confirm spec_kitty_events version matches uv.lock pin
2. T026–T028 are production code; T029–T031 are test/fixture fixes
3. T030: check existence before attempting delete; if re-appeared, it is a regression

**Dependencies**: none (can run in parallel with WP08, WP09)  
**Prompt file**: [tasks/WP07-shared-package-events-drift.md](tasks/WP07-shared-package-events-drift.md)

---

## WP08 — Charter synthesizer determinism (FR-010 / #1303)

**Goal**: Fix non-deterministic manifest hash computation in the charter synthesizer; enforce path_guard.py chokepoint.  
**Priority**: Medium (5 failing bundle-validate tests)  
**Estimated prompt size**: ~300 lines  
**Execution lane**: lane-h  
**Profile**: `python-pedro`  

**Included subtasks:**
- [ ] T032 Run charter synthesizer tests to identify exact hash computation path (WP08)
- [ ] T033 Sort file lists before hashing in synthesizer manifest to ensure determinism (WP08)
- [ ] T034 Enforce path_guard.py chokepoint for direct write primitives (WP08)
- [ ] T035 Refresh stored manifest hashes in test fixtures (WP08)

**Implementation notes:**
1. Source path: `src/charter/synthesizer/` (not `src/specify_cli/charter/`)
2. WP08 must NOT touch `src/specify_cli/cli/commands/charter/synthesize.py` (owned by WP05)
3. Run tests twice before + after fix to confirm hash determinism

**Dependencies**: none (can run in parallel with WP07, WP09)  
**Prompt file**: [tasks/WP08-charter-synthesizer-determinism.md](tasks/WP08-charter-synthesizer-determinism.md)

---

## WP09 — Misc debt — auth / invocation / mypy / mission switching (FR-011 / #1310)

**Goal**: Fix five in-scope miscellaneous debt items; re-defer two with new GitHub issues.  
**Priority**: Medium (5 test clusters; 2 re-deferred)  
**Estimated prompt size**: ~440 lines  
**Execution lane**: lane-i  
**Profile**: `debugger-debbie`  

**Included subtasks:**
- [ ] T036 Fix auth integration exit-code returning wrong value (WP09)
- [ ] T037 Prevent logged_out_on_connected_teamspace noise from JSON CLI output (WP09)
- [ ] T038 Fix mypy --strict failures in mission_step_contracts/executor.py (WP09)
- [ ] T039 Fix or exclude legacy kitty-specs/ WP files failing Pydantic validation (WP09)
- [ ] T040 Investigate and fix mission-switching blocking condition (WP09)
- [ ] T041 File GitHub issues for re-deferred items (checklist skill, schema-version wording) (WP09)
- [ ] T050 Delete all stray test-feature-* dirs from kitty-specs/ + add pytest teardown + .gitignore guard (WP09)

**Implementation notes:**
1. T039 self-referential trap: run validator first to see current failures; this mission's own WP files are included in the glob
2. T041 must be done BEFORE closing WP09 — two new GitHub issues required per C-008
3. All five in-scope items are independent; address in any order

**Dependencies**: none (can run in parallel with WP07, WP08)  
**Prompt file**: [tasks/WP09-misc-debt-auth-invocation-mypy.md](tasks/WP09-misc-debt-auth-invocation-mypy.md)

---

### Wave D — Closeout

---

## WP10 — CI test-mark audit (FR-012)

**Goal**: Audit all test files in modules touched by WP01–WP09; add missing CI-quality marks; verify existing architectural guard passes.  
**Priority**: High (gate for WP11)  
**Estimated prompt size**: ~250 lines  
**Execution lane**: lane-j  
**Profile**: `curator-carla`  

**Included subtasks:**
- [ ] T042 Audit all WP01-WP09 touched test directories for missing pytestmark (WP10)
- [ ] T043 Add pytestmark to tests/agent/test_context_unit.py (WP10)
- [ ] T044 Add category mark to tests/specify_cli/test_lane_regression_guard.py (WP10)
- [ ] T045 Verify existing architectural guard passes without modification (WP10)

**Implementation notes:**
1. **Pre-condition**: WP01–WP09 must all be merged before this WP begins
2. No new guard test file — existing `tests/architectural/test_pytest_marker_convention.py` is the guard
3. T044: add `pytest.mark.unit` alongside existing `pytest.mark.non_sandbox` (non_sandbox alone is not a CI-quality split mark)

**Dependencies**: Depends on WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08, WP09  
**Prompt file**: [tasks/WP10-ci-test-mark-audit.md](tasks/WP10-ci-test-mark-audit.md)

---

## WP11 — Full-suite re-baseline + issue closeout (FR-013) — planning lane

**Goal**: Run the full test suite, record baseline, close all 10 sub-issues.  
**Priority**: Critical (mission success gate)  
**Estimated prompt size**: ~230 lines  
**Execution lane**: lane-planning  
**Profile**: `human-in-charge`  

**Included subtasks:**
- [ ] T046 Run PWHEADLESS=1 pytest tests/ -q --tb=no and record output (WP11)
- [ ] T047 Commit baseline.md to docs/01KSMG8Y-closeout/ (WP11)
- [ ] T048 Close or re-defer GitHub issues #1301-#1310 with linking commits (WP11)
- [ ] T049 Post closing comment on #1298 with final failure delta (WP11)

**Implementation notes:**
1. Gate: failure count ≤75. If >75, file DIR-013 issues for remaining clusters and document in baseline.md
2. This is a planning-lane WP — no worktree; runs in main checkout after all lanes merged

**Dependencies**: Depends on WP10  
**Prompt file**: [tasks/WP11-full-suite-rebaseline-closeout.md](tasks/WP11-full-suite-rebaseline-closeout.md)

---

## Dependency Graph

```
WP01 ──┐
WP02 ──┤
WP03 ──┤
WP04 ──┼──► WP10 ──► WP11
WP05 ──┤
WP06 ──┘
WP07 ──┐
WP08 ──┤
WP09 ──┘
```

WP01–WP06 (waves A+B) can run in parallel.  
WP07–WP09 (wave C) can run in parallel.  
WP10 depends on WP01–WP09.  
WP11 depends on WP10.
</content>