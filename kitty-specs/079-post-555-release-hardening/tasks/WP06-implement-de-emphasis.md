---
work_package_id: WP06
title: Track 6 — Implement De-emphasis
dependencies:
- WP01
- WP03
requirement_refs:
- FR-501
- FR-502
- FR-504
- FR-505
- FR-506
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
history:
- at: '2026-04-09T07:30:50Z'
  event: created
authoritative_surface: README.md
execution_mode: code_change
mission_slug: 079-post-555-release-hardening
owned_files:
- README.md
- src/specify_cli/missions/software-dev/command-templates/**
- docs/explanation/**
- docs/how-to/**
- tests/docs/**
- tests/missions/**
tags: []
---

# WP06 — Track 6: Implement De-emphasis

**Spec FRs**: FR-501, FR-502, FR-504, FR-505, FR-506
**Note**: FR-503 (`implement --help`) is covered by WP03 T014. The `init.py` next-steps edit (FR-501) is covered by WP01 T003. WP06 handles all OTHER surfaces.
**Priority**: P1 — closes the remaining canonical-path teach-out gap across README, templates, and docs.
**Estimated size**: ~300 lines

## Objective

Remove top-level `spec-kitty implement` from all user-facing canonical-path teach-out surfaces:
- `README.md` canonical workflow line + mermaid diagram
- Slash-command source templates under `src/specify_cli/missions/software-dev/command-templates/`
- Getting-started portions of ~12 docs files under `docs/`

The canonical user workflow for 3.1.1 is: `spec-kitty next --agent <name> --mission <slug>` (loop entry) → `spec-kitty agent action implement <WP> --agent <name>` / `spec-kitty agent action review <WP> --agent <name>` (per-decision verbs).

`spec-kitty implement` still runs for compatibility. The `/spec-kitty.implement` slash command file may remain but its body must teach `spec-kitty agent action implement`, not top-level `spec-kitty implement`.

## Context

**Surfaces that still teach top-level `spec-kitty implement`** (from Phase 0 research, pre-3.1.1):
- `README.md:8-9`: `` `spec` -> `plan` -> `tasks` -> `implement` -> `review` -> `merge` ``
- `README.md:64-80`: mermaid/ASCII diagram with `⚡ Implement | Agent workflows` step
- `missions/software-dev/command-templates/tasks.md` lines 40, 267-268: `spec-kitty implement WP##` examples
- `missions/software-dev/command-templates/tasks-packages.md` lines 133-134: `spec-kitty implement WP01`
- `missions/software-dev/command-templates/specify.md` line 145: `spec-kitty implement WP##`
- `missions/software-dev/command-templates/implement.md` lines 16-19, 35-36: teaches `spec-kitty implement` as allocation command (the slash command template itself)
- `docs/explanation/{execution-lanes,git-workflow,spec-driven-development,kanban-workflow,multi-agent-orchestration,mission-system}.md` — first 5 paragraphs
- `docs/how-to/{implement-work-package,parallel-development,handle-dependencies,recover-from-implementation-crash,sync-workspaces,diagnose-installation}.md` — first 5 paragraphs

**Phase 0 also found**: The `implement.md` command template ALREADY teaches `spec-kitty next --agent <name>` at line 159. So the templates are partially correct; we just need to clean up the remaining `spec-kitty implement WP##` examples.

**NOT in scope**: `implement.py` docstring is WP03. `init.py` next-steps is WP01.

## Branch Strategy

Plan in `main`, implement in the lane worktree. Merge back to `main` on completion.

## Subtask Guidance

### T024 — Update `README.md` canonical workflow

**File**: `README.md`

**Steps**:

1. Find the canonical workflow line at lines ~8-9. Current text:
   `` `spec` -> `plan` -> `tasks` -> `implement` -> `review` -> `merge` ``
   Replace with something like:
   `` `spec` -> `plan` -> `tasks` -> `spec-kitty next` (agent loop) -> `review` -> `merge` ``
   Or, if the style is slash-command names:
   `` `/spec-kitty.specify` → `/spec-kitty.plan` → `/spec-kitty.tasks` → `spec-kitty next` (loop) → `/spec-kitty.review` → `/spec-kitty.merge` ``
   Use the exact style that fits the existing README formatting. The key constraint: no `implement` in this line.

2. Find the mermaid / ASCII diagram at lines ~64-80. It currently has an `⚡ Implement | Agent workflows` step or similar. Replace it with a step that names `spec-kitty next` as the loop step. Keep the diagram compact — don't add new rows.

3. Do a final grep: `grep -n "spec-kitty implement" README.md` — only acceptable matches are in compatibility-surface context (troubleshooting, `--help` description, etc.), not in "how to use" context.

**Validation**:
- `README.md` canonical workflow line does not contain the word `implement` as a step.
- `README.md` mermaid diagram does not have `spec-kitty implement` or `` `implement` `` as a canonical step cell.
- Test T6.4: grep README for `spec-kitty implement` in canonical sections → 0 matches.

---

### T025 — Update slash-command source templates

**File**: `src/specify_cli/missions/software-dev/command-templates/` (multiple .md files)

**Per-file action**:

**`tasks.md`**:
- Find line 40: `"After tasks are generated, use \`spec-kitty implement WP##\` to create or reuse the execution workspace"`. Replace with: `"After tasks are finalized, run your agent loop: \`spec-kitty next --agent <agent> --mission <slug>\`"`.
- Find lines 267-268: `"No dependencies: \`spec-kitty implement WP01\`"`. Replace with: `"No dependencies: \`spec-kitty agent action implement WP01 --agent <name>\`"`.

**`tasks-packages.md`**:
- Find lines 133-134: `spec-kitty implement WP01` and `spec-kitty implement WP02`. Replace with `spec-kitty agent action implement WP01 --agent <name>` and `spec-kitty agent action implement WP02 --agent <name>`.

**`tasks-outline.md`** (if exists; from Phase 0 research it teaches `spec-kitty next`):
- Audit: already correct. No changes if it already uses `spec-kitty next`.

**`specify.md`**:
- Find line 145: `"Use \`spec-kitty implement WP##\` after task finalization computes execution lanes"`. Replace with: `"After \`/spec-kitty.tasks\` finishes, run: \`spec-kitty next --agent <agent> --mission <slug>\`"`.

**`implement.md`** (the source template for the `/spec-kitty.implement` slash command):
- This template's line 159 already teaches `spec-kitty next` (correct). Audit lines 16-19 and 35-36: if they still say `spec-kitty implement` as the allocation command, replace with `spec-kitty agent action implement <WP> --agent <name>`. The slash command `/spec-kitty.implement` stays — it's the slash-command entry point. But its body should say: "To implement a WP: `spec-kitty agent action implement <WP> --agent <name>`".

**After all changes**:
```bash
grep -r "spec-kitty implement WP" src/specify_cli/missions/software-dev/command-templates/
```
Must return no matches.

**Validation**:
- T6.5: for each template, grep for `spec-kitty implement WP` → 0 matches.
- Template files still teach `spec-kitty next` and `spec-kitty agent action implement`.
- The `/spec-kitty.implement` slash command file itself still exists (it's a valid slash command name).

---

### T026 — Update `docs/` canonical-path mentions

**Files**: `docs/explanation/*.md`, `docs/how-to/*.md` (selected files, first ~5 paragraphs only)

**Scope**: Update ONLY lines in the first ~5 paragraphs or first "Quick Start" / "How to" section of each file that name `spec-kitty implement` as the canonical recommended command. Leave troubleshooting / recovery / how-to-deeply contexts alone — those describe `spec-kitty implement` as a lower-level tool, which is accurate for its new role as internal infrastructure.

**Files to update** (from Phase 0 research, canonical-path mentions in first 5 paragraphs):
1. `docs/explanation/execution-lanes.md`
2. `docs/explanation/git-workflow.md`
3. `docs/explanation/spec-driven-development.md`
4. `docs/explanation/kanban-workflow.md`
5. `docs/explanation/multi-agent-orchestration.md`
6. `docs/explanation/mission-system.md`
7. `docs/how-to/implement-work-package.md` (primary user-facing how-to — needs the most work)
8. `docs/how-to/parallel-development.md`
9. `docs/how-to/handle-dependencies.md`
10. `docs/how-to/recover-from-implementation-crash.md` (leave — recovery context)
11. `docs/how-to/sync-workspaces.md`
12. `docs/how-to/diagnose-installation.md`

**Per-file pattern**:
For each file, read the first 20-30 lines. If they say something like "After planning, run `spec-kitty implement WP01`", change to "After planning, run your agent loop: `spec-kitty next --agent <agent> --mission <slug>`. Your agent will call `spec-kitty agent action implement WP01 --agent <name>` for each WP."

**For `docs/how-to/implement-work-package.md`** (the dedicated how-to guide): This file likely has a full `spec-kitty implement` workflow. Update the quick-start section. Do NOT rewrite the entire file. Add a preamble paragraph noting that `spec-kitty implement` is available as an internal tool for advanced users, but the canonical path is the `spec-kitty next` loop.

**For recovery/troubleshooting files** (`recover-from-implementation-crash.md`): These describe `spec-kitty implement --recover` which is a valid direct invocation. Leave them as-is — recovery is a compatibility-surface context.

**After all changes**:
```bash
grep -rn "spec-kitty implement WP" docs/
```
Should return 0 matches in "how to use" / quickstart contexts. May still appear in compatibility-surface contexts.

**Validation**:
- Test T6.4 (extended): grep docs/ for `spec-kitty implement WP` in canonical-path context → 0 matches.

---

### T027 — Regression tests for Track 6

**Files**: `tests/agent/cli/commands/test_implement_help.py` (note: this file is in WP03's owned_files because FR-503 is there; WP06's tests are in separate files), `tests/docs/test_readme_canonical_path.py`, `tests/missions/test_command_templates_canonical_path.py`

**Important**: The `test_implement_help.py` test is in WP03's owned files (since WP03 owns `implement.py`). WP06's tests cover README and templates.

**Test T6.4 — README does not name `spec-kitty implement` in canonical workflow**:
```python
# tests/docs/test_readme_canonical_path.py
def test_readme_canonical_workflow_line_does_not_name_implement():
    readme = Path("README.md").read_text()
    # Find the canonical workflow line (near the top of the file)
    # It should contain "spec-kitty next" somewhere
    assert "spec-kitty next" in readme, "README must name spec-kitty next as canonical loop"
    
    # The canonical workflow line must not name bare "spec-kitty implement" as a step
    # Find the first 30 lines (where the canonical workflow line is)
    first_30_lines = "\n".join(readme.split("\n")[:30])
    assert "spec-kitty implement WP" not in first_30_lines
```

**Test T6.5 — Command templates do not teach `spec-kitty implement WP##`**:
```python
# tests/missions/test_command_templates_canonical_path.py
import glob

def test_command_templates_do_not_teach_bare_implement():
    template_dir = "src/specify_cli/missions/software-dev/command-templates"
    for template_path in glob.glob(f"{template_dir}/*.md"):
        content = Path(template_path).read_text()
        # The literal invocation pattern "spec-kitty implement WP" must not appear
        assert "spec-kitty implement WP" not in content, (
            f"{template_path} still teaches bare 'spec-kitty implement WP##'. "
            f"Replace with 'spec-kitty agent action implement <WP> --agent <name>'."
        )
```

**Test T6.2 — `spec-kitty implement` still runs (compatibility)**:
```python
# tests/agent/cli/commands/test_implement_runs.py (or extend existing)
def test_implement_command_still_runs(runner):
    # Just verify the command entrypoint exists and responds to --help
    result = runner.invoke(app, ["implement", "--help"])
    assert result.exit_code == 0
```

## Definition of Done

- [ ] `README.md` canonical workflow line names `spec-kitty next`, not `spec-kitty implement`.
- [ ] `README.md` mermaid / ASCII diagram does not have `spec-kitty implement` as a canonical step.
- [ ] `grep -r "spec-kitty implement WP" src/specify_cli/missions/software-dev/command-templates/` → 0 matches.
- [ ] First 5 paragraphs of the 12 docs files updated to name canonical commands.
- [ ] T6.4, T6.5 pass.
- [ ] `spec-kitty implement` still runs for direct invokers (T6.2).
- [ ] No changes to `init.py` (WP01 owns that).
- [ ] No changes to `implement.py` (WP03 owns that).

## Risks

| Risk | Mitigation |
|------|-----------|
| Template edits must be in SOURCE files, not agent copies | Per `CLAUDE.md`: edit `src/specify_cli/missions/software-dev/command-templates/` only. Never touch `.claude/commands/`, `.codex/prompts/`, etc. The spec-kitty upgrade mechanism deploys source → agent copies. |
| Docs update too aggressive (breaks recovery how-tos) | Read each file fully before editing. Only update canonical-path mentions. Leave `--recover` flag descriptions, troubleshooting contexts, and direct-invocation examples alone. |
| README mermaid diagram format breaks | Test the rendered diagram locally if possible. At minimum, verify the markdown is syntactically valid (no unclosed backticks). |

## Reviewer Guidance

1. Verify `CLAUDE.md` rule: changes are in `src/specify_cli/missions/software-dev/command-templates/`, NOT in `.claude/commands/` or `.codex/prompts/`.
2. Run `grep -r "spec-kitty implement WP" src/specify_cli/missions/ docs/ README.md` — should be 0 canonical-path matches.
3. Confirm `spec-kitty implement` appears ONLY in compatibility-surface / internal-tool / troubleshooting contexts after this WP.
4. Run T6.4 and T6.5.
