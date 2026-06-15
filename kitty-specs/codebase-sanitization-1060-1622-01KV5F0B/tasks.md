# Tasks: Internal `--feature` & `status_service` sanitization

**Mission**: codebase-sanitization-1060-1622-01KV5F0B
**Branch**: `mission/codebase-sanitization-1060-1622` (planning base = merge target; PR to `upstream/main`)
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Bulk-edit map**: [occurrence_map.yaml](occurrence_map.yaml)

## Overview

5 work packages. Workstream 1 (#1060-A): WP01 + WP02 remove the hidden `--feature`
alias from the 10 in-scope commands; WP03 locks the terminology gate and proves
out-of-scope commands are unchanged. Workstream 2 (#1622): WP04 is verify-only —
locks the already-resolved state with a regression test + closes the ticket.
Boyscout (adversarial-squad fold-in F1): WP05 retires the dead
`hidden_feature_option` helper (FR-009).

**Bounded conflict surface (NFR-001):** no edits under `src/specify_cli/status/`,
`src/specify_cli/task_utils/`, or `legacy_detector.py`. `resolve_selector` and
`_legacy_aliases.py` are RETAINED (FR-008). Each removal WP follows ATDD at the
behavioral level (de-alias rejection test red → green within the WP); WP03 lands
the global gate as the regression lock once all removals are merged.

## Dependencies

```
WP01 (agent cmds)  ─┬─→ WP03 (gate lock + out-of-scope proof)
WP02 (other cmds)  ─┴─→ WP05 (retire dead _legacy_aliases helper)   [WP05 deps WP02]
WP04 (#1622 verify) ── independent (parallel with all)
```

- WP01 ∥ WP02 ∥ WP04 (different files — fully parallel).
- WP03 depends on WP01 + WP02 (the global gate only goes green after both
  removals land).
- WP05 depends on WP02 (it owns `test_legacy_feature_alias.py`, whose
  `charter/lint.py`-keeps-`--feature` assertion is invalidated once WP02 lands).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Remove `--feature` from `agent/tasks.py` (12 hits) + retarget resolve_selector | WP01 | |
| T002 | Remove `--feature` from `agent/status.py` (9 hits) | WP01 | [P] |
| T003 | Remove `--feature` from `agent/workflow.py` (4 hits; keep unrelated status_service import) | WP01 | [P] |
| T004 | Remove `--feature` from `agent/context.py` + `agent/mission.py` | WP01 | [P] |
| T005 | Update agent-namespace tests: de-alias rejection + `--mission` still works | WP01 | |
| T006 | ruff/mypy clean + run targeted agent-command tests | WP01 | |
| T007 | Remove `--feature` from `charter/lint.py` | WP02 | [P] |
| T008 | Remove `--feature` from `materialize.py` | WP02 | [P] |
| T009 | Remove `--feature` from `validate_encoding.py` + `validate_tasks.py` | WP02 | [P] |
| T010 | Remove `--feature` from `verify.py` | WP02 | [P] |
| T011 | Update these commands' tests: de-alias rejection + `--mission` still works | WP02 | |
| T012 | ruff/mypy clean + run targeted tests | WP02 | |
| T013 | Extend terminology guard: in-scope cluster must have NO `--feature` option (hidden or visible) | WP03 | |
| T014 | Out-of-scope preservation regression test (e.g. `merge --feature` still resolves) | WP03 | |
| T015 | Verify FR-003: no first-party `src/doctrine/` source passes `--feature` to an in-scope command | WP03 | |
| T016 | Run full contract + architectural suites; confirm green | WP03 | |
| T017 | Grep-proof #1622 evidence: 2 funcs absent; 3 enums/error de-exported live internals | WP04 | |
| T018 | Confirm dead-symbol gate green (`test_no_dead_symbols`, baselines unchanged) | WP04 | |
| T019 | Close #1622 with re-classification (2/5 deletions; 3 retained-because-live) | WP04 | |
| T020 | Remove dead `hidden_feature_option` + `LEGACY_FEATURE_HELP` from `_legacy_aliases.py` | WP05 | |
| T021 | Reconcile `test_legacy_feature_alias.py` (retire helper tests + lint-keeps-feature assertion) | WP05 | |
| T022 | Remove dead-symbol/dead-module allowlist entries; confirm gates green | WP05 | |

---

## Phase 1 — Alias removal (parallel)

### WP01 — Remove `--feature` from agent-namespace commands

- **Goal**: Delete the hidden `--feature` option + `feature`/`explicit_feature`
  plumbing from `agent status/tasks/workflow/context/mission`, retargeting
  `resolve_selector` calls to the mission-only path. `--mission` behavior
  unchanged.
- **Priority**: P1 (largest surface; `agent/tasks.py` has 12 hits)
- **Requirements**: FR-001, FR-002, FR-008
- **Independent test**: `spec-kitty agent tasks status --feature X` errors as an
  unknown option; `--mission X` works identically to before.
- **Subtasks**: T001–T006 · **Est.**: ~380 lines · **Deps**: none
- **Prompt**: [tasks/WP01-remove-feature-agent-commands.md](tasks/WP01-remove-feature-agent-commands.md)

- [x] T001 Remove `--feature` from `agent/tasks.py` (12 hits) + retarget resolve_selector (WP01)
- [x] T002 Remove `--feature` from `agent/status.py` (9 hits) (WP01)
- [x] T003 Remove `--feature` from `agent/workflow.py`; keep unrelated status_service import (WP01)
- [x] T004 Remove `--feature` from `agent/context.py` + `agent/mission.py` (WP01)
- [x] T005 Update agent-namespace tests: de-alias rejection + `--mission` works (WP01)
- [x] T006 ruff/mypy clean + run targeted agent-command tests (WP01)

### WP02 — Remove `--feature` from non-agent in-scope commands

- **Goal**: Same removal for `charter lint`, `materialize`, `validate_encoding`,
  `validate_tasks`, `verify`.
- **Priority**: P1
- **Requirements**: FR-001, FR-002, FR-008
- **Independent test**: `spec-kitty verify --feature X` errors as unknown option;
  `--mission X` works.
- **Subtasks**: T007–T012 · **Est.**: ~320 lines · **Deps**: none
- **Prompt**: [tasks/WP02-remove-feature-other-commands.md](tasks/WP02-remove-feature-other-commands.md)

- [x] T007 Remove `--feature` from `charter/lint.py` (WP02)
- [x] T008 Remove `--feature` from `materialize.py` (WP02)
- [x] T009 Remove `--feature` from `validate_encoding.py` + `validate_tasks.py` (WP02)
- [x] T010 Remove `--feature` from `verify.py` (WP02)
- [x] T011 Update these commands' tests: de-alias rejection + `--mission` works (WP02)
- [x] T012 ruff/mypy clean + run targeted tests (WP02)

## Phase 2 — Regression lock

### WP03 — Terminology gate lock + out-of-scope preservation proof

- **Goal**: Tighten the contract gate so any `--feature` Typer option (hidden or
  visible) on an in-scope command fails CI; prove out-of-scope commands still
  accept the alias; confirm no first-party caller regressions.
- **Priority**: P1
- **Requirements**: FR-003, FR-004, FR-005
- **Independent test**: re-adding a `--feature` option to any in-scope file makes
  the gate fail; `merge --feature X` still resolves.
- **Subtasks**: T013–T016 · **Est.**: ~280 lines · **Deps**: WP01, WP02
- **Prompt**: [tasks/WP03-terminology-gate-and-scope-proof.md](tasks/WP03-terminology-gate-and-scope-proof.md)

- [ ] T013 Extend terminology guard: in-scope cluster must have NO `--feature` option (WP03)
- [ ] T014 Out-of-scope preservation regression test (`merge --feature` still resolves) (WP03)
- [ ] T015 Verify FR-003: no `src/doctrine/` source passes `--feature` to an in-scope command (WP03)
- [ ] T016 Run full contract + architectural suites; confirm green (WP03)

### WP05 — Retire dead `hidden_feature_option` helper (boyscout / FR-009)

- **Goal**: Remove the dead `hidden_feature_option()` + `LEGACY_FEATURE_HELP`
  from `_legacy_aliases.py` (0 `src/` callers), retire their tests, and drop the
  dead-symbol/dead-module allowlist entries. `resolve_selector` untouched.
- **Priority**: P2
- **Requirements**: FR-009
- **Independent test**: `git grep hidden_feature_option` → 0 repo-wide; dead-symbol
  + dead-module gates green.
- **Subtasks**: T020–T022 · **Est.**: ~170 lines · **Deps**: WP02
- **Prompt**: [tasks/WP05-retire-dead-legacy-aliases-helper.md](tasks/WP05-retire-dead-legacy-aliases-helper.md)

- [ ] T020 Remove dead `hidden_feature_option` + `LEGACY_FEATURE_HELP` from `_legacy_aliases.py` (WP05)
- [ ] T021 Reconcile `test_legacy_feature_alias.py` (retire helper tests + lint-keeps-feature assertion) (WP05)
- [ ] T022 Remove dead-symbol/dead-module allowlist entries; confirm gates green (WP05)

## Phase 3 — Verify-and-close (#1622)

### WP04 — #1622 verify-and-close (regression lock + ticket close)

- **Goal**: Lock the already-resolved `status_service` state with a new
  regression test (no `status_service.py` edit) and close #1622 with the
  re-classification.
- **Priority**: P2
- **Requirements**: FR-006, FR-007
- **Independent test**: the new regression test passes; dead-symbol gate green;
  #1622 closed with the re-classification comment.
- **Subtasks**: T017–T019 · **Est.**: ~190 lines · **Deps**: none
- **Prompt**: [tasks/WP04-1622-verify-and-close.md](tasks/WP04-1622-verify-and-close.md)

- [x] T017 Add regression test: 2 funcs absent; 3 enums/error de-exported but live internals (WP04)
- [x] T018 Confirm dead-symbol gate green (`test_no_dead_symbols`, baselines unchanged) (WP04)
- [x] T019 Close #1622 with re-classification (WP04)

---

## MVP

WP01 (the largest alias-removal surface) is the MVP demonstrating the de-aliasing
pattern; WP02 mirrors it; WP03 locks it; WP04 closes the bookkeeping.
