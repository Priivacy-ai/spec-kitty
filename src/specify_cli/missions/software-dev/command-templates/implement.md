---
description: Execute a work package implementation
---
# /spec-kitty.implement - Execute Work Package Implementation

**Version**: 0.12.0+

## Purpose

Execute the implementation of a work package according to its prompt file.
Follow TDD practices, respect file ownership boundaries, and apply safety
guardrails for bulk operations.

---

## Working Directory

**IMPORTANT**: This step works inside the execution workspace (worktree)
allocated by `spec-kitty agent action implement WPxx --agent <name>`. Do NOT modify files outside
your `owned_files` boundaries.

**In repos with multiple missions, always pass `--mission <handle>` to every spec-kitty command.** The `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of the ULID), or `mission_slug`. The resolver disambiguates by `mission_id` and returns a structured `MISSION_AMBIGUOUS_SELECTOR` error on ambiguity — there is no silent fallback.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Execution Steps

### 1. Setup

Run:

```bash
spec-kitty agent context resolve --action implement --mission <handle> --json
```

Then execute the returned `check_prerequisites` command and capture
`feature_dir`. All paths must be absolute.

The output of `spec-kitty agent action implement ...` is the authoritative work
package prompt and execution context. Do **not** separately call
`spec-kitty charter context` or rummage through unrelated files looking for a
"newer" prompt unless the command output tells you to.

### 2. Load Work Package Prompt

Read the WP prompt file from `feature_dir/tasks/WPxx-slug.md`.
Parse frontmatter for:
- `owned_files` -- only modify files matching these globs
- `authoritative_surface` -- primary directory for this WP
- `execution_mode` -- `code_change` or `planning_artifact`
- `subtasks` -- ordered list of subtask IDs
- `dependencies` -- WPs that must be done first

### 3. Verify Dependencies

Confirm all dependency WPs are in `done` status before proceeding.
If any are not done, stop and report which dependencies are blocking.

### 4. Implement Subtasks

Work through each subtask in order:
1. Read the subtask guidance from the WP prompt
2. Write tests first (TDD) when the subtask involves code changes
3. Implement the code to pass the tests
4. Verify tests pass before moving to the next subtask

### 5. Self-Check

After all subtasks are complete:
- All tests pass
- No files outside `owned_files` were modified
- Code follows project conventions (run linter if configured)

---

## Bulk Edit Occurrence Classification

If this mission has `change_mode: bulk_edit` in its `meta.json`, an occurrence
classification artifact is required before implementation can begin.

**What to check**:
1. Read `meta.json` in the feature directory — look for `"change_mode": "bulk_edit"`
2. If present, verify `occurrence_map.yaml` exists in the same directory
3. The occurrence map classifies the target term by semantic category with
   per-category actions: `rename`, `manual_review`, `do_not_change`, `rename_if_user_visible`

**During implementation**:
- Consult the occurrence map before modifying any file
- Respect category actions: do NOT modify occurrences in categories marked `do_not_change`
- For `manual_review` categories, document your decision in the WP review notes
- For `rename_if_user_visible`, only change user-facing text (docs, UI, error messages)
- Check the `exceptions` section for files/patterns with overriding rules

**If the gate blocks you**:
The system will refuse to start implementation if the occurrence map is missing or
incomplete. Create `occurrence_map.yaml` following the schema with `target`, `categories`
(3+ with actions), and optionally `exceptions`. Re-run the implement command.

**If an inference warning fires**:
The system may warn that spec content looks like a bulk edit even without `change_mode` set.
Either set `change_mode: "bulk_edit"` in meta.json, or re-run with `--acknowledge-not-bulk-edit`.

---

## Bulk Edit Safety

**WHEN THIS APPLIES**: Any work package that performs bulk renaming, terminology
cutover, or mass find-and-replace across multiple files. If your WP does NOT
involve bulk text replacement, skip this section.

### Pre-Edit: Occurrence Classification

Before performing bulk renames or term replacements:

1. **Search** the codebase for ALL occurrences of the target term:
   ```bash
   grep -rn "target_term" src/ tests/ docs/ --include="*.py" --include="*.md" --include="*.yaml" --include="*.json"
   ```

2. **Classify** each occurrence into one of these categories:

   | Category | Example Pattern | Typical Action |
   |----------|----------------|----------------|
   | `import_path` | `from module.old_name import` | RENAME |
   | `class_name` | `class OldName:` | RENAME |
   | `function_name` | `def old_name():` | RENAME |
   | `variable` | `old_name = ...` | RENAME |
   | `dict_key` | `"old_name": value` | RENAME |
   | `file_path` | `src/old_name/` | RENAME (with filesystem move) |
   | `config_value` | `setting: old_name` | RENAME |
   | `log_message` | `log("Processing old_name")` | UPDATE (human-readable) |
   | `comment` | `# old_name does X` | UPDATE |
   | `documentation` | `The old_name module...` | UPDATE |
   | `test_fixture` | `test_old_name_works` | RENAME |
   | `external_ref` | URL or external API name | PRESERVE |

3. **Produce a classification report** as a markdown table in the WP
   implementation notes. Example:

   | File | Line | Occurrence | Category | Action |
   |------|------|-----------|----------|--------|
   | `src/foo.py` | 12 | `from old_name import` | `import_path` | RENAME |
   | `docs/api.md` | 45 | `The old_name module` | `documentation` | UPDATE |
   | `src/config.yaml` | 8 | `endpoint: https://api.old_name.com` | `external_ref` | PRESERVE |

4. **Get classification confirmed** before proceeding with edits.

5. **Apply edits category by category**, verifying each category independently.

### Post-Edit: Verification

After completing bulk renames:

1. **Search for remaining occurrences** of the old term:
   ```bash
   grep -rn "old_term" src/ tests/ docs/ --include="*.py" --include="*.md" --include="*.yaml" --include="*.json"
   ```

2. **For each remaining occurrence**, classify it:
   - **Intentional preservation**: Document why it was kept (e.g., external API name, backward compat)
   - **Missed rename**: Fix it
   - **New occurrence**: Introduced by parallel work -- rename if appropriate

3. **Search command template and agent directories** explicitly:
   ```bash
   grep -rn "old_term" src/specify_cli/missions/*/command-templates/
   grep -rn "old_term" .claude/commands/ .codex/prompts/ .opencode/command/
   grep -rn "old_term" .github/prompts/ .gemini/commands/ .cursor/commands/
   grep -rn "old_term" .qwen/commands/ .kilocode/workflows/ .windsurf/workflows/
   grep -rn "old_term" .augment/commands/ .roo/commands/ .amazonq/prompts/
   ```

4. **Produce a verification report**:
   - Total occurrences found: N
   - Intentionally preserved: M (with reasons for each)
   - Missed renames fixed: K
   - Template directories checked: yes/no
   - Agent directories checked: yes/no
   - Doc directories checked: yes/no

---

## Output

After completing implementation:
- All subtasks done with passing tests
- Bulk edit classification and verification reports (if applicable)
- Commit changes with a descriptive message

**Next step**: `spec-kitty next --agent <name>` will advance to review.
