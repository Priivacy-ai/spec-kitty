---
work_package_id: WP05
title: Occurrence Classification for Bulk Edits
dependencies: []
requirement_refs:
- FR-011
- FR-012
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T023, T024, T025, T026]
history:
- timestamp: '2026-04-06T18:43:32+00:00'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/upgrade/
execution_mode: code_change
owned_files:
- src/specify_cli/upgrade/skill_update.py
- src/specify_cli/missions/software-dev/command-templates/**
- tests/specify_cli/upgrade/test_skill_update*
---

# WP05: Occurrence Classification for Bulk Edits

## Objective

Add a safety guardrail for bulk rename/cutover work by requiring occurrence classification before edits proceed and post-edit verification afterward. This prevents silent breakage when different string occurrence categories (identifiers, prose, paths, config keys) need different treatment.

**Issue**: [#393](https://github.com/Priivacy-ai/spec-kitty/issues/393)

## Context

`apply_text_replacements()` at `src/specify_cli/upgrade/skill_update.py:117-142` does blind `str.replace()` with no context awareness:

```python
for old, new in replacements:
    content = content.replace(old, new)
```

There is no occurrence classification infrastructure in the codebase. The spec confirms (Assumption 5): occurrence classification is "a workflow step (prompt/template guidance + structured output), not a fully automated NLP classifier."

This WP adds:
1. A template step that requires agents to classify occurrences before editing
2. A verification step to confirm correct edits
3. An optional code-level `context_filter` for programmatic bulk edits

### Key files

| File | Line(s) | What |
|------|---------|------|
| `src/specify_cli/upgrade/skill_update.py` | 117-142 | `apply_text_replacements()` — blind str.replace() |
| `src/specify_cli/upgrade/skill_update.py` | 145-160 | `file_contains_any()` — simple marker search |
| `src/specify_cli/missions/software-dev/command-templates/` | all | Mission command templates (SOURCE, not agent copies) |

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

## Subtasks

### T023: Create Occurrence Classification Template Step

**Purpose**: Add a structured step to the mission command templates that requires agents to classify all occurrences of a target term before making bulk edits.

**Steps**:

1. Identify which command template(s) to modify:
   - The most relevant template is the implement template at `src/specify_cli/missions/software-dev/command-templates/` (whichever template governs cutover/rename WPs)
   - May also need to add guidance in the review template

2. Add a "Bulk Edit Safety" section to the template that instructs the implementing agent:

   > **Before performing bulk renames or term replacements:**
   >
   > 1. Search the codebase for all occurrences of the target term
   > 2. Classify each occurrence into one of these categories:
   >
   > | Category | Example Pattern | Typical Action |
   > |----------|----------------|----------------|
   > | `import_path` | `from module.old_name import` | RENAME |
   > | `class_name` | `class OldName:` | RENAME |
   > | `function_name` | `def old_name():` | RENAME |
   > | `variable` | `old_name = ...` | RENAME |
   > | `dict_key` | `"old_name": value` | RENAME |
   > | `file_path` | `src/old_name/` | RENAME (with filesystem move) |
   > | `config_value` | `setting: old_name` | RENAME |
   > | `log_message` | `log("Processing old_name")` | UPDATE (human-readable) |
   > | `comment` | `# old_name does X` | UPDATE |
   > | `documentation` | `The old_name module...` | UPDATE |
   > | `test_fixture` | `test_old_name_works` | RENAME |
   > | `external_ref` | URL or external API name | PRESERVE |
   >
   > 3. Produce a classification report as a markdown table in the WP implementation notes
   > 4. Get classification confirmed before proceeding with edits
   > 5. Apply edits category by category, verifying each

3. The template should be clear that this step is required for any WP that performs bulk renaming/terminology cutover, not for normal implementation work.

**Validation**:
- [ ] Template includes occurrence classification instructions
- [ ] Category table covers common occurrence types
- [ ] Instructions are clear about when this step applies

### T024: Create Post-Edit Verification Template Step

**Purpose**: After bulk edits, require a verification step that confirms no unintended changes and no missed occurrences.

**Steps**:

1. Add a "Post-Edit Verification" section to the same template(s):

   > **After completing bulk renames:**
   >
   > 1. Search the codebase for any remaining occurrences of the old term:
   >    ```bash
   >    grep -r "old_term" src/ tests/ docs/ --include="*.py" --include="*.md" --include="*.yaml"
   >    ```
   > 2. For each remaining occurrence, classify it:
   >    - **Intentional preservation**: Document why it was kept (e.g., external API name)
   >    - **Missed rename**: Fix it
   >    - **New occurrence**: Introduced by parallel work — rename if appropriate
   > 3. Search command template directories specifically:
   >    ```bash
   >    grep -r "old_term" src/specify_cli/missions/*/command-templates/
   >    grep -r "old_term" .claude/commands/ .codex/prompts/ .opencode/command/
   >    ```
   > 4. Produce a verification report:
   >    - Total occurrences found: N
   >    - Intentionally preserved: M (with reasons)
   >    - Missed renames fixed: K
   >    - Coverage: template dirs checked? doc dirs checked?

2. The verification step should explicitly check template/doc directories (aligned with WP04 audit targets).

**Validation**:
- [ ] Template includes post-edit verification instructions
- [ ] Verification covers template directories and docs
- [ ] Instructions distinguish intentional preservations from missed renames

### T025: Add Optional `context_filter` to `apply_text_replacements()`

**Purpose**: For programmatic bulk edits (migrations, upgrade scripts), allow filtering which files are processed.

**Steps**:

1. In `src/specify_cli/upgrade/skill_update.py`, update `apply_text_replacements()` signature:
   ```python
   def apply_text_replacements(
       file_path: Path,
       replacements: list[tuple[str, str]],
       context_filter: Callable[[Path], bool] | None = None,
   ) -> bool:
   ```

2. When `context_filter` is provided:
   - Call `context_filter(file_path)` before processing
   - If it returns `False`, skip the file and return `False`
   - This allows callers to exclude files by pattern (e.g., skip `.kittify/` paths)

3. Existing callers pass no `context_filter` and behavior is unchanged.

4. Add a few built-in filter factories for common cases:
   ```python
   def exclude_paths(*patterns: str) -> Callable[[Path], bool]:
       """Create a filter that excludes files matching any pattern."""
       def _filter(path: Path) -> bool:
           return not any(fnmatch(str(path), p) for p in patterns)
       return _filter
   ```

**Validation**:
- [ ] `apply_text_replacements()` with no context_filter works as before
- [ ] With context_filter, excluded files are skipped
- [ ] `exclude_paths()` correctly filters by glob patterns

### T026: Write Tests for Occurrence Classification

**Test scenarios**:

1. **test_apply_text_replacements_no_filter**: Existing behavior unchanged
2. **test_apply_text_replacements_with_filter**: File excluded by filter is not modified
3. **test_exclude_paths_filter**: `exclude_paths(".kittify/*")` excludes .kittify files
4. **test_exclude_paths_multiple_patterns**: Multiple exclusion patterns work
5. **test_template_has_classification_section**: Read implement template, verify "Bulk Edit Safety" section exists
6. **test_template_has_verification_section**: Read implement template, verify "Post-Edit Verification" section exists

**Files**: `tests/specify_cli/upgrade/test_occurrence_classification.py` (new file)

## Definition of Done

- Mission templates include occurrence classification and post-edit verification steps
- `apply_text_replacements()` supports optional context_filter
- Template/doc directories are explicitly listed as verification targets
- Existing callers of `apply_text_replacements()` are unaffected
- 90%+ test coverage on new code

## Risks

- Template changes might not be picked up by agents already mid-session (mitigate: agents re-read templates at WP start)
- context_filter could mask legitimate replacement targets if misconfigured (mitigate: filter is optional, off by default)

## Reviewer Guidance

- Verify template instructions are clear and actionable for AI agents
- Check that category table is comprehensive for common rename scenarios
- Confirm context_filter parameter is truly optional (no breaking changes)
- Verify both the SOURCE templates and the generated agent copies are consistent
