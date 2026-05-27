---
work_package_id: WP01
title: TOML escape fix + snapshot refresh
dependencies: []
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: feat/pre-doctrine-stabilization-remediation
merge_target_branch: feat/pre-doctrine-stabilization-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/pre-doctrine-stabilization-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pre-doctrine-stabilization-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-pre-doctrine-test-stabilization-01KSMG8Y
base_commit: fcec446d1be3c2c67d5ce9f0bc36a40133fe6684
created_at: '2026-05-27T12:18:57.882286+00:00'
subtasks:
- T001
- T002
- T003

shell_pid: "35769"
agent: "claude:claude-sonnet-4-6:implementer-ivan:implementer"
history:
- date: '2026-05-27'
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/missions/software-dev/command-templates/
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/missions/software-dev/command-templates/implement.md
- tests/specify_cli/regression/_twelve_agent_baseline/**
- tests/specify_cli/regression/test_twelve_agent_parity.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load implementer-ivan
```

This profile governs your implementation style, naming conventions, and quality expectations for this work package.

---

## Objective

Fix the unescaped backslash in `src/specify_cli/missions/software-dev/command-templates/implement.md` line 168 that causes a `TOMLDecodeError` for `gemini` and `qwen` agents when `render_command_template()` is called. After the fix, regenerate all twelve-agent snapshots so the parity test suite reflects the corrected output.

**Closes**: GitHub issue #1302

---

## Context

When `render_command_template("implement", agent="gemini")` is called, the rendered output contains an unescaped backslash in a TOML multi-line basic string. The source is this bash snippet at `implement.md:168`:

```bash
CHANGED_PY=$(git diff --name-only --diff-filter=AMR HEAD | rg '\.py$' || true)
```

The `\.` in the `rg` pattern is a literal backslash character. TOML multi-line basic strings (the format used by gemini and qwen) do not allow unescaped backslashes — this is a TOML spec violation, not a rendering bug. The fix must be in the template source, not the renderer.

**Key constraint** from CLAUDE.md: edit the SOURCE template at `src/specify_cli/missions/software-dev/command-templates/implement.md`, NOT the generated copies in `.claude/commands/`, `.amazonq/prompts/`, etc.

---

## Subtask T001 — Fix the backslash in implement.md:168

**Purpose**: Replace `rg '\.py$'` with `grep -E '[.]py$'`. The character-class form `[.]` matches the same input as `\.` but contains no backslash character, eliminating the TOML parse error.

**Important**: `grep -E '\.py$'` is NOT correct — the `\.` still contains a backslash and will trigger the same TOML error. Use `[.]py$` with square brackets.

**Steps**:

1. Open `src/specify_cli/missions/software-dev/command-templates/implement.md`
2. Navigate to line 168. Confirm the current text is:
   ```bash
   CHANGED_PY=$(git diff --name-only --diff-filter=AMR HEAD | rg '\.py$' || true)
   ```
3. Replace with:
   ```bash
   CHANGED_PY=$(git diff --name-only --diff-filter=AMR HEAD | grep -E '[.]py$' || true)
   ```
4. Save the file. Do not touch any other lines.

**Files**: `src/specify_cli/missions/software-dev/command-templates/implement.md`

**Validation**:
- [ ] Line 168 now reads `grep -E '[.]py$'`
- [ ] No other line in the file was modified
- [ ] File does not contain `rg '\.py` anywhere (check with grep)

---

## Subtask T002 — Regenerate twelve-agent snapshots

**Purpose**: The parity test suite compares rendered output against stored snapshots. After fixing the template, the stored snapshots are stale. Regenerate them using the environment variable that puts the snapshot tests into update mode.

**Pre-check**: Before regenerating, count how many agent baselines exist:

```bash
ls tests/specify_cli/regression/_twelve_agent_baseline/implement/ | wc -l
```

CLAUDE.md documents 13 slash-command agents; the test file is named `test_twelve_agent_parity.py`. Record the actual count — if it is 13, the reviewer needs to know 13 snapshots were updated (not 12). If it is 12, note which agent is absent.

**Steps**:

1. Run the snapshot regeneration:
   ```bash
   PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v 2>&1 | tee /tmp/snapshot_refresh.log
   ```

2. Check the diff to confirm only the `rg`→`grep` substitution changed:
   ```bash
   git diff tests/specify_cli/regression/_twelve_agent_baseline/
   ```

3. The diff should show lines like:
   ```
   -CHANGED_PY=$(git diff --name-only --diff-filter=AMR HEAD | rg '\.py$' || true)
   +CHANGED_PY=$(git diff --name-only --diff-filter=AMR HEAD | grep -E '[.]py$' || true)
   ```
   This substitution should appear in every agent snapshot that renders the `implement` template (the substitution will NOT appear in agents that use literal-string TOML or non-TOML formats — those agents were not broken and their snapshots should be unchanged).

4. If any snapshot shows a different change, stop and investigate before committing.

**Files**: `tests/specify_cli/regression/_twelve_agent_baseline/implement/**`

**Validation**:
- [ ] All affected snapshots were regenerated (`PYTEST_UPDATE_SNAPSHOTS=1` exited 0)
- [ ] git diff shows only rg→grep substitution in affected files
- [ ] Unaffected agent snapshots are unchanged

---

## Subtask T003 — Verify parity tests pass

**Purpose**: Confirm the fix works end-to-end by running the parity test suite without `PYTEST_UPDATE_SNAPSHOTS`, which puts it back in assertion mode.

**Steps**:

1. Run the parity tests:
   ```bash
   pytest tests/specify_cli/regression/test_twelve_agent_parity.py -v 2>&1
   ```

2. Specifically confirm:
   - `test_toml_command_output_is_parseable[implement-gemini]` PASSES
   - `test_toml_command_output_is_parseable[implement-qwen]` PASSES
   - All other parity parametrizations still PASS (no regressions)

3. Record in your commit message: how many snapshots were updated, which agent formats carry the TOML restriction (gemini, qwen), and the count (12 or 13) confirmed in T002.

**Validation**:
- [ ] `[implement-gemini]` passes
- [ ] `[implement-qwen]` passes
- [ ] No other parity test regressed
- [ ] Commit message records snapshot count and affected agents

---

## Branch Strategy

- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`
- **Execution**: Worktree allocated per computed lane from `lanes.json`; do not manually branch.

To start implementation:
```bash
spec-kitty agent action implement WP01 --agent claude
```

---

## Definition of Done

- [ ] `src/specify_cli/missions/software-dev/command-templates/implement.md:168` uses `grep -E '[.]py$'`
- [ ] All agent snapshots in `_twelve_agent_baseline/implement/` are updated
- [ ] `test_toml_command_output_is_parseable[implement-gemini]` passes
- [ ] `test_toml_command_output_is_parseable[implement-qwen]` passes
- [ ] No other snapshot test regressed
- [ ] Commit includes both the template fix AND the refreshed snapshots (C-009 constraint)

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Agent count is 13 not 12 | Medium | Count first; note discrepancy in commit message |
| Other agents also use TOML multi-line basic strings | Low | The TOML format restriction is per-agent; check test output |
| Snapshot regeneration overwrites correct baselines | Low | Review git diff before committing; only rg→grep change expected |

---

## Reviewer Guidance

1. Confirm `implement.md:168` uses `[.]py$` (character class) not `\.py$`
2. Confirm `git diff _twelve_agent_baseline/` shows only the one-line substitution per affected file
3. Confirm both gemini and qwen parity tests pass
4. Confirm C-009 is satisfied: template fix and snapshot refresh are in the same commit
</content>

## Activity Log

- 2026-05-27T12:18:58Z – claude:claude-sonnet-4-6:implementer-ivan:implementer – shell_pid=35769 – Assigned agent via action command
- 2026-05-27T12:22:22Z – claude:claude-sonnet-4-6:implementer-ivan:implementer – shell_pid=35769 – T001-T003 complete: implement.md line 168 uses grep -E '[.]py$', 13 agent snapshots refreshed (rg->grep in implement; stale charter/tasks baselines also updated), parity tests pass (208/208 including implement-gemini and implement-qwen TOML parse tests). ruff diff-scoped check: 0 issues, exit 0.
