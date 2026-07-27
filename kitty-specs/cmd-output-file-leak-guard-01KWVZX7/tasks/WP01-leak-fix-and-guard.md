---
work_package_id: WP01
title: Fix the leaking fake + add the registered filename guard
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-001
tracker_refs: []
planning_base_branch: fix/cmd-output-file-leak-guard
merge_target_branch: fix/cmd-output-file-leak-guard
branch_strategy: Planning artifacts for this mission were generated on fix/cmd-output-file-leak-guard. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/cmd-output-file-leak-guard unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude"
shell_pid: "406768"
history:
- 'Created by planner for #2169 tasks phase'
agent_profile: python-pedro
authoritative_surface: tests/
create_intent:
- tests/architectural/test_no_invalid_windows_filenames.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/review/test_baseline.py
- tests/architectural/test_no_invalid_windows_filenames.py
- tests/_arch_shard_map.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Fix the leaking fake + add the registered filename guard

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` to load the agent profile in the frontmatter and follow it before reading on.
- **Profile**: `python-pedro` · **Role**: `implementer` · **Model**: `claude-sonnet-5`

---

## Objective
Stop the one test double that leaks a `"${SPEC_KITTY_CMD_OUTPUT_FILE}"`-named junk file into the working tree, and add a class-closing architectural guard — **registered in the sharded arch pole** — so a Windows-illegal filename can never reach Windows CI again.

## Context (post-spec/plan squad, verified)
- **Sole leaker**: `fake_run_with_xml` in `tests/review/test_baseline.py` (~807-833, `test_capture_baseline_custom_test_runner_label`). It does `m = re.search(r"--output=(\S+)", cmd_text)` then `Path(m.group(1)).write_text(...)` — the command carries `--output="${SPEC_KITTY_CMD_OUTPUT_FILE}"`, so it captures the **literal** and writes it as a **relative path into cwd**, ignoring `kwargs["env"]`. It leaks whether the env var is set or unset.
- **Safe siblings** at ~253/294/338 do it right: `Path(kwargs["env"]["SPEC_KITTY_CMD_OUTPUT_FILE"]).write_text(...)`.
- **The product is correct** — do NOT touch `configured_command.py`. `test_configured_command.py` is inert (0 fs writes) — do NOT touch it.
- **Arch pole is sharded (#2397)**: a `tests/architectural/` file earns an `arch_shard_N` marker ONLY if registered in `tests/_arch_shard_map.py`; unregistered → `shard_for()` returns `None` → deselected on all shards AND `tests/architectural/test_arch_shard_marker_completeness.py` goes RED.

## Detailed Guidance

### T001 — Fix BOTH `--output=` parsers (FR-001, FR-002)
In `tests/review/test_baseline.py`, `test_capture_baseline_custom_test_runner_label` has **two** copies of the leaking pattern: the wired `fake_run_with_xml` (~807-822) AND a dead-but-copy-paste-ready twin `fake_run` (~789-805), both doing `re.search(r"--output=(\S+)")` + `Path(m.group(1)).write_text(...)`. Remediate **both**: redirect each write target to `kwargs["env"]["SPEC_KITTY_CMD_OUTPUT_FILE"]` (mirror the safe siblings at ~253/294/338), or **delete the unused `fake_run`** if it is genuinely dead (never patched in). Then grep the whole function for `re.search(r"--output` / `Path(m.group` and confirm **no** residue remains. Keep the test's custom-runner-label assertion intact (C-001).

### T002 — New filename guard (FR-003)
Add `tests/architectural/test_no_invalid_windows_filenames.py`: enumerate `git ls-files` (repo root), assert no tracked path contains a forbidden character, checked as **two distinct, clearly-named sets** (not conflated):
1. **Windows-illegal** — `<`, `>`, `:`, `"`, `\`, `|`, `?`, `*` (the `"` is the actual char that exit-128'd Windows checkout on #2161); the `:` exception is a legitimate drive prefix (none expected in tracked repo-relative paths).
2. **shell-expansion leak telltale** — `$`, `{`, `}` (Windows-*legal*, but their presence in a filename is a shell-substitution-leak signature like this one).
Fail listing the offender(s) and which set matched. Cheap (single `git ls-files`, no per-file IO).

### T003 — Register the guard in the shard map (NFR-001)
Add `"tests/architectural/test_no_invalid_windows_filenames.py"` to one of `_ARCH_SHARD_1_FILES` / `_ARCH_SHARD_2_FILES` / `_ARCH_SHARD_3_FILES` in `tests/_arch_shard_map.py` (pick the lightest shard for balance). Confirm `shard_for("tests/architectural/test_no_invalid_windows_filenames.py")` returns that N. Give the guard the matching `pytest.mark` if the convention requires an explicit marker in-file (check how the sibling registered guards are marked); the shard marker itself is applied by `conftest.py` from the map.

### T004 — Non-vacuous proof + all-green (FR-004, SC-001..003)
- **Leak red-first**: run `test_capture_baseline_custom_test_runner_label` from a scratch cwd BEFORE the fix → a `"${…}"` file appears (env-independent: try var set AND unset); AFTER the fix → cwd clean. Record it.
- **Guard non-vacuous**: mutation-check with a **genuinely-Windows-illegal** char (the class that actually broke CI) — e.g. `git add` a file named `a"b.txt` (or `a|b.txt`) → RED; and separately a `${}`-telltale file → RED; remove → GREEN. The witness MUST include the Windows-illegal arm, not only `${}`, so it pins the real FR-003 contract.
- Confirm the guard is selected: `PWHEADLESS=1 uv run pytest tests/architectural/test_no_invalid_windows_filenames.py -m 'arch_shard_<N> and not windows_ci and (git_repo or integration or architectural)'` collects it.
- `tests/architectural/test_arch_shard_marker_completeness.py` stays green.

## Definition of Done
- [ ] BOTH `--output=` parsers in `test_capture_baseline_custom_test_runner_label` remediated (wired `fake_run_with_xml` + dead twin `fake_run`); no `Path(m.group(...))` literal-write residue anywhere in the function; a scratch-cwd run leaks nothing (var set or unset).
- [ ] New filename guard present with two named sets (Windows-illegal + shell-telltale); RED on a genuinely-Windows-illegal tracked file (e.g. `a"b.txt`) AND on a `${}` file, GREEN on the clean tree (mutation-verified).
- [ ] Guard registered in `tests/_arch_shard_map.py`; `shard_for(...)` returns its N; selected under the per-shard selector.
- [ ] `test_arch_shard_marker_completeness.py` green.
- [ ] `PWHEADLESS=1 uv run pytest tests/review/test_baseline.py tests/architectural/test_no_invalid_windows_filenames.py -q` green.
- [ ] `ruff` + `mypy --strict` clean on the touched files; no new suppressions.

## Commit
From the lane worktree: `git add -A && git commit -m "fix(#2169): stop the literal-output-file test leak + add a registered Windows-illegal-filename guard"`.

## Reviewer Guidance
Confirm BOTH `--output=` parsers are remediated — grep the **whole `test_capture_baseline_custom_test_runner_label` function** (not just the diff; the twin is dead code that won't appear in a diff) for `re.search(r"--output` / `Path(m.group`; none should remain writing a parsed literal. Confirm the guard's mutation witness includes a genuinely-Windows-illegal char (not only `${}`). Mutation-check the guard (add a forbidden-char tracked file → RED). Verify the shard-map registration by running `shard_for(...)` and confirming `test_arch_shard_marker_completeness.py` is green. Confirm `configured_command.py` and `test_configured_command.py` are untouched.

## Activity Log

- 2026-07-06T16:23:54Z – claude – shell_pid=406768 – Assigned agent via action command
