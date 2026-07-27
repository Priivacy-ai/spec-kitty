---
work_package_id: WP04
title: '#2667 — load_action_index fails loud on a malformed index'
dependencies: []
requirement_refs:
- FR-007
- FR-008
tracker_refs:
- '2667'
planning_base_branch: feat/mission-type-single-source-gate-wiring
merge_target_branch: feat/mission-type-single-source-gate-wiring
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-single-source-gate-wiring. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-single-source-gate-wiring unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
agent: "claude"
shell_pid: "3274295"
shell_pid_created_at: "1784144158.66"
history:
- at: '2026-07-15T19:00:00Z'
  actor: claude
  note: WP authored post-plan squad — present⇒well-formed / absent⇒empty; broad fail-loud incl. unparseable YAML (operator DD-4).
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/missions/action_index.py
- tests/doctrine/missions/test_action_index.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration. You are the **implementer**.

## Objective

Make `load_action_index` (`src/doctrine/missions/action_index.py`) fail loud on a **present-but-malformed**
action index instead of silently degrading to an empty grain (#2667). A silently-dropped grain lets the
FR-013 cross-grain union pass falsely. **This WP must land before WP05** (the gate is partially vacuous over a
silently-degraded index until this lands).

## Context — READ BEFORE CODING

- **Rule (operator DD-4):** *present ⇒ must be well-formed; absent ⇒ empty.* A present index file that is not
  a well-formed `ActionIndex` raises; only a genuinely-missing file keeps the silent fallback; an
  intentionally-empty-but-well-formed index is empty content (no raise).
- Current silent-degradation points in `load_action_index`:
  - `action_index.py:42` `if not index_path.exists(): return fallback` — **KEEP** (missing → silent).
  - `:48-49` `if not isinstance(data, dict): return fallback` — **RAISE** (non-mapping root).
  - `:51-55` `_str_list` returns `[]` for a non-list value (`directives: "a-string"`) — **RAISE**.
  - `:67-68` `except (OSError, UnicodeDecodeError, YAMLError): return fallback` — **RAISE on YAMLError** (present
    but unparseable). Decide OSError/UnicodeDecodeError: a present file that can't be read is also
    present-but-invalid → raise (wrap with context). Keep the missing-file branch as the only silent path.
- **Blast radius:** the sole `src/` caller is `aggregate_action_grain` (`action_grain.py:147`, no try/except),
  so the raise propagates to the scan/resolver/doctor — the desired loud path. No caller swallows it today;
  do not add a swallow.
- **Doctrine exception convention:** a named `*Error(ValueError)` co-located with the module (cf.
  `MissionTypeNotAnArtifactKind(ValueError)`, `OrgPackSchemaError`). Message names the index path, the
  offending key (or `<root>`), and the found type — mirror `MissionTypeRepository._load`'s `ValueError`
  phrasing.

## Subtasks

### T016 — [ATDD, RED FIRST] fail-loud tests

In `tests/doctrine/missions/test_action_index.py` add:
- non-mapping root (e.g. a top-level scalar/list) → `pytest.raises(ActionIndexError)`.
- non-list field value (`directives: "a-string"`) → `pytest.raises(ActionIndexError)`.
- unparseable YAML → `pytest.raises(ActionIndexError)`.
- **missing file → returns `ActionIndex(action=action)`** (silent fallback; explicit test).
- **present, well-formed, empty content** (e.g. `{action: implement}` or all-empty lists) → empty-content
  `ActionIndex`, NO raise.

### T017 — Implement fail-loud

Add `class ActionIndexError(ValueError)` co-located in `action_index.py`. Raise it on non-mapping root,
non-list field value, and unparseable/unreadable present file. Keep the missing-file fallback. Ensure the
message includes path + offending key + found type. Keep complexity ≤ 15 (extract a small `_require_list`
helper if needed).

### T018 — Re-pin lenient tests

Re-pin the 2 currently-lenient tests (`test_non_list_field_value_returns_empty_list` and the non-dict-root
fallback test) to `pytest.raises(ActionIndexError)`. These encode the OLD lenient contract (the bug) —
**re-pin, do NOT delete** (they still guard the same input, now with the correct expectation).

### T019 — Quality gate

- `uv run ruff check src/doctrine/missions/action_index.py && uv run mypy --strict src/doctrine/missions/action_index.py`
- `uv run pytest tests/doctrine/missions/test_action_index.py -q`
- Smoke that `aggregate_action_grain` still succeeds on the real built-in tree (no false raise on the
  intentionally-empty `plan` indexes): `uv run pytest tests/charter/test_action_grain.py -q`

## Branch Strategy

Base/merge target `feat/mission-type-single-source-gate-wiring`. No dependencies (independent of the IC-1
chain). Execution worktree per `lanes.json` lane.

## Definition of Done

- [ ] `ActionIndexError(ValueError)` added; raises on the 3 present-but-invalid cases; missing→fallback; empty-well-formed→empty.
- [ ] The 2 lenient tests re-pinned to `pytest.raises` (not deleted); new missing/empty tests added.
- [ ] `aggregate_action_grain` still green on the built-in tree (no false raise on empty `plan` indexes).
- [ ] ruff + mypy --strict clean; complexity ≤ 15.
- [ ] ATDD: T016 committed RED first.

## Reviewer guidance

Verify the ONLY silent path is a genuinely-missing file; verify the intentionally-empty `plan` action
indexes do NOT raise (that would break the resolver on a shipped type). Confirm the exception message is
actionable (path + key + type).

## Activity Log

- 2026-07-15T19:36:04Z – claude – shell_pid=3274295 – Assigned agent via action command
- 2026-07-15T19:47:21Z – claude – shell_pid=3274295 – WP04 fail-loud: reviewer-renata APPROVE; ATDD red→green, plan-empty-index boundary verified
- 2026-07-15T19:50:12Z – user – shell_pid=3274295 – reviewer-renata APPROVE
