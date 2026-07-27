---
work_package_id: WP02
title: tasks.md Header Regex Standardization (#410)
dependencies: [WP01]
requirement_refs:
- FR-004
planning_base_branch: feature/metadata-state-type-hardening
merge_target_branch: feature/metadata-state-type-hardening
branch_strategy: Planning artifacts for this feature were generated on feature/metadata-state-type-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/metadata-state-type-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 1 - Bug Fix & Foundation
assignee: ''
agent: "opencode"
shell_pid: "152804"
history:
- at: '2026-04-06T05:37:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/status/emit.py
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/status/emit.py
- src/specify_cli/cli/commands/agent/tasks.py
task_type: implement
agent_profile: python-implementer
---

# Work Package Prompt: WP02 – tasks.md Header Regex Standardization (#410)

## IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: As you address each feedback item, update the Activity Log.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- **Objective**: Update all 5 `tasks.md` header-parsing regex sites to accept `##`, `###`, and `####` WP headers (no deeper).
- **SC-003**: `finalize-tasks` correctly parses dependencies from a `tasks.md` file using `#### WP01` headers.
- **FR-004**: All parsing sites accept `#{2,4}` depth; `#####`+ headings are NOT matched.

## Context & Constraints

- **Upstream issue**: #410 — header regex mismatch causes silent F015 dependency-parse failure
- **Research**: `kitty-specs/065-wp-metadata-state-type-hardening/research.md` (Finding 2 — Header Regex Sites)
- **Plan**: `kitty-specs/065-wp-metadata-state-type-hardening/plan.md` (WP02 section)
- **Root cause**: 5 regex sites across 3 files each assume different header depths (`##`, `###`) — none match `####`. When LLMs generate `tasks.md` with `####` headings, dependencies are silently stripped.

**5 regex sites** (from research.md Finding 2):

| Site | File | Line | Current Pattern |
|------|------|------|-----------------|
| WP section parse | `cli/commands/agent/feature.py` | ~1953 | `^(?:##\s+(?:Work Package\s+)?\|###\s+)(WP\d{2})` |
| Subtask inference | `status/emit.py` | ~148 | `^##.*\b{wp_id}\b` |
| Section end | `status/emit.py` | ~151 | `^##\s+` |
| Subtask start | `cli/commands/agent/tasks.py` | ~305 | `##.*{wp_id}\b` |
| Section end | `cli/commands/agent/tasks.py` | ~310 | `##.*WP\d{2}\b` |

**Standardized patterns** (from research.md):
- WP header match: `^#{2,4}\s+(?:Work Package\s+)?(WP\d{2})(?:\b|:)`
- Section boundary (WP-specific): `^#{2,4}.*\b{wp_id}\b`
- Section end (any heading): `^#{2,4}\s+`

**Doctrine**:
- `acceptance-test-first.tactic.yaml` — spec scenarios drive test
- `change-apply-smallest-viable-diff.tactic.yaml`
- `034-test-first-development.directive.yaml`

**Cross-cutting**:
- **Boy Scout** (DIRECTIVE_025): Remove unused `repo_root` param at `emit.py:441` while touching that file.
- **Self Observation Protocol** (NFR-009): Write observation log at session end.
- **Quality Gate** (DIRECTIVE_030): Tests + type checks must pass before `for_review`.

## Branch Strategy

- **Implementation command**: `spec-kitty implement WP02 --base WP01`
- **Planning base branch**: `feature/metadata-state-type-hardening`
- **Merge target branch**: `feature/metadata-state-type-hardening`

## Subtasks & Detailed Guidance

### Subtask T005 – Write regression tests for header depth across all 5 sites

- **Purpose**: Create a test harness that exercises all 5 regex sites with `##`, `###`, `####`, and `#####` (boundary) headers before changing anything. Tests for `##` and `###` must pass now (regression). Tests for `####` must fail now (proving the bug). Tests for `#####` must always fail (boundary — never matched).
- **Steps**:
  1. Search for existing tests covering WP header parsing:
     ```bash
     rg -l "parse_wp_sections\|_infer_subtasks\|WP\d{2}" tests/
     ```
  2. Create or extend test files for each site. You need tests covering:
     - **`_parse_wp_sections_from_tasks_md()`** (`feature.py`): Parse a `tasks.md` with `## WP01`, `### WP01`, `#### WP01`, and `##### WP01` headers. Assert the first three are detected; the last is NOT.
     - **`_infer_subtasks_complete()`** (`emit.py`): Provide a `tasks.md` body with WP headers at each depth. Assert subtask sections are found for `##`/`###`/`####`, not for `#####`.
     - **Subtask checker** (`tasks.py`): Same pattern.
  3. Use parameterized tests for depth variations:
     ```python
     @pytest.mark.parametrize("depth,expected", [
         ("##", True),
         ("###", True),
         ("####", True),
         ("#####", False),
     ])
     def test_wp_header_depth(depth, expected):
         content = f"{depth} WP01: Setup\n\nSome content\n"
         result = _parse_wp_sections(content)
         assert ("WP01" in result) == expected
     ```
  4. Run tests and verify that `####` tests fail (proving the bug):
     ```bash
     pytest tests/ -x -v -k "header_depth or regex"
     ```
- **Files**:
  - Test files in `tests/specify_cli/` (locate or create)
- **Validation**:
  - [ ] Tests for `##` and `###` pass (regression)
  - [ ] Tests for `####` fail (bug confirmation)
  - [ ] Tests for `#####` pass with `expected=False` (boundary)

### Subtask T006 – Fix `_parse_wp_sections_from_tasks_md()` in feature.py

- **Purpose**: Update the primary `tasks.md` parser to accept `####` headers.
- **Steps**:
  1. Open `src/specify_cli/cli/commands/agent/feature.py`
  2. Find `_parse_wp_sections_from_tasks_md()` (around line 1953, verify with `rg`):
     ```bash
     rg "_parse_wp_sections_from_tasks_md" src/specify_cli/cli/commands/agent/feature.py
     ```
  3. Update the regex from the current pattern to:
     ```python
     # Before (only matches ## and ###):
     r'^(?:##\s+(?:Work Package\s+)?|###\s+)(WP\d{2})'
     
     # After (matches ##, ###, ####):
     r'^#{2,4}\s+(?:Work Package\s+)?(WP\d{2})(?:\b|:)'
     ```
  4. Also check for any section-end boundary regex in the same function that needs updating.
  5. Run the T005 tests for this site:
     ```bash
     pytest tests/ -x -v -k "parse_wp_sections"
     ```
- **Files**:
  - `src/specify_cli/cli/commands/agent/feature.py` (~line 1953)
- **Parallel?**: Yes — after T005 is written, this can run in parallel with T007 and T008.
- **Validation**:
  - [ ] `####` test for this site now passes
  - [ ] `##` and `###` tests still pass (regression)

### Subtask T007 – Fix `_infer_subtasks_complete()` in emit.py

- **Purpose**: Update the subtask inference regex in `emit.py` to accept `####` headers.
- **Steps**:
  1. Open `src/specify_cli/status/emit.py`
  2. Find `_infer_subtasks_complete()` (around lines 148 and 151, verify with `rg`):
     ```bash
     rg "_infer_subtasks_complete\|##.*wp_id\|##\\\\s" src/specify_cli/status/emit.py
     ```
  3. Update both regex patterns:
     - **Line ~148** (WP section start): Update to `^#{2,4}.*\b{wp_id}\b`
     - **Line ~151** (section end): Update to `^#{2,4}\s+`
  4. Run the T005 tests for this site:
     ```bash
     pytest tests/ -x -v -k "infer_subtasks"
     ```
- **Files**:
  - `src/specify_cli/status/emit.py` (lines ~148, ~151)
- **Parallel?**: Yes — can run in parallel with T006 and T008.
- **Validation**:
  - [ ] `####` test for this site now passes
  - [ ] `##` and `###` tests still pass (regression)

### Subtask T008 – Fix tasks.py regex + Boy Scout emit.py cleanup

- **Purpose**: Update the subtask checker regex in `tasks.py` and apply Boy Scout fix to `emit.py`.
- **Steps**:
  1. Open `src/specify_cli/cli/commands/agent/tasks.py`
  2. Find the subtask checker (around lines 305 and 310):
     ```bash
     rg "##.*wp_id\|##.*WP\\\\d" src/specify_cli/cli/commands/agent/tasks.py
     ```
  3. Update both regex patterns:
     - **Line ~305** (subtask start): Update to `^#{2,4}.*\b{wp_id}\b`
     - **Line ~310** (section end): Update to `^#{2,4}.*WP\d{2}\b`
  4. **Boy Scout fix** (DIRECTIVE_025): While `emit.py` is already touched by T007, also remove the unused `repo_root` parameter at `emit.py:441`:
     ```bash
     rg "repo_root" src/specify_cli/status/emit.py
     ```
     - Remove the parameter from the function signature
     - Update all call sites (search with `rg` for callers)
     - Verify no test breakage
  5. Run all T005 tests:
     ```bash
     pytest tests/ -x -v -k "header_depth or regex or subtask"
     ```
  6. Run full test suite:
     ```bash
     pytest tests/ -x --timeout=60
     ```
- **Files**:
  - `src/specify_cli/cli/commands/agent/tasks.py` (lines ~305, ~310)
  - `src/specify_cli/status/emit.py` (line ~441, unused `repo_root` param)
- **Parallel?**: Yes — regex fixes parallel with T006/T007; Boy Scout fix sequential after T007.
- **Validation**:
  - [ ] All `####` tests pass
  - [ ] `##` and `###` tests still pass (regression)
  - [ ] `#####` tests correctly NOT matched
  - [ ] Unused `repo_root` param removed from `emit.py`
  - [ ] Full test suite passes

## Definition of Done

- [ ] Regression tests cover `##`, `###`, `####`, `#####` for all 5 regex sites (T005)
- [ ] All 5 regex sites updated to `#{2,4}` (T006, T007, T008)
- [ ] `finalize-tasks` correctly parses `#### WP01` headers
- [ ] Boy Scout: unused `repo_root` param removed from `emit.py` (T008)
- [ ] Full test suite passes with zero regressions
- [ ] Type checks pass

## Risks & Mitigations

- **Risk**: Regex patterns may be more complex than shown in research.md. **Mitigation**: Use `rg` to find exact patterns before editing; test each change individually.
- **Risk**: Removing `repo_root` param may break callers. **Mitigation**: Search all call sites with `rg` before removing.

## Review Guidance

- Verify that the regex `#{2,4}` correctly excludes `#` (h1) and `#####`+ (h5+).
- Check that all 5 sites are updated, not just a subset.
- Confirm the Boy Scout `repo_root` removal didn't break any callers.

## Activity Log

- 2026-04-06T05:37:00Z – system – Prompt created.
- 2026-04-06T10:23:30Z – opencode – shell_pid=152804 – Started implementation via action command
- 2026-04-06T10:35:12Z – opencode – shell_pid=152804 – All 5 regex sites updated to #{2,4}, Boy Scout repo_root removal, 20 regression tests, full suite 8594 pass
- 2026-04-06T10:35:28Z – opencode – shell_pid=152804 – Started review via action command
- 2026-04-06T10:36:16Z – opencode – shell_pid=152804 – Review passed: all 5 regex sites correctly updated to #{2,4}, f-string brace escaping correct, Boy Scout repo_root removal clean, 20 regression tests comprehensive, full suite green
