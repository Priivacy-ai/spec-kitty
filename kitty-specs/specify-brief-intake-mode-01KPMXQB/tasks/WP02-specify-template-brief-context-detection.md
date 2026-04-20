---
work_package_id: WP02
title: 'Specify Template: Brief Context Detection'
dependencies:
- WP01
requirement_refs:
- C-002
- C-003
- C-004
- C-005
- C-006
- C-007
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
history:
- date: '2026-04-20'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: src/specify_cli/missions/software-dev/command-templates/
execution_mode: code_change
owned_files:
- src/specify_cli/missions/software-dev/command-templates/specify.md
- .claude/commands/spec-kitty.specify.md
- .amazonq/prompts/spec-kitty.specify.md
- .gemini/commands/spec-kitty.specify.md
- .cursor/commands/spec-kitty.specify.md
- .qwen/commands/spec-kitty.specify.md
- .opencode/command/spec-kitty.specify.md
- .windsurf/workflows/spec-kitty.specify.md
- .kilocode/workflows/spec-kitty.specify.md
- .augment/commands/spec-kitty.specify.md
- .roo/commands/spec-kitty.specify.md
- .kiro/prompts/spec-kitty.specify.md
- .agent/workflows/spec-kitty.specify.md
- .github/prompts/spec-kitty.specify.md
- .agents/skills/spec-kitty.specify/SKILL.md
tags: []
---

# WP02 — Specify Template: Brief Context Detection

## Objective

Insert a new **"Brief Context Detection (check before discovery)"** section into the `/spec-kitty.specify` source template, then propagate the change to all 13 agent directories via `spec-kitty upgrade`. This teaches the specify agent to detect `.kittify/mission-brief.md` and `.kittify/ticket-context.md` before starting the Discovery Gate and enter an efficient brief-intake extraction mode when found.

This WP does not depend on WP01's code at runtime — the template section is a prose change that stands alone. Both WPs are in `lane-a` and will execute sequentially; WP02 runs after WP01 in the lane but does not require WP01 to be merged first.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP02 --agent <name>`

## Context

### The CLAUDE.md Rule (CRITICAL)

> **Edit the SOURCE template, NOT the agent copies.**

| What | Location | Action |
|------|----------|--------|
| SOURCE template | `src/specify_cli/missions/software-dev/command-templates/specify.md` | ✅ EDIT THIS |
| Agent copies | `.claude/commands/`, `.amazonq/prompts/`, etc. | ❌ DO NOT EDIT — `spec-kitty upgrade` writes these |

After editing the source, run `spec-kitty upgrade` to propagate to all 13 agent directories. The upgrade command is the only supported mechanism for updating agent copies.

### Existing Template Structure

Read `src/specify_cli/missions/software-dev/command-templates/specify.md` fully before editing. The key structural landmarks (use exact heading text to find insertion points):

- `## Charter Context Bootstrap (required)` — **insert NEW SECTION immediately after this block ends**
- `## Discovery Gate (mandatory)` — new section must appear before this heading

The new section goes between the last line of the Charter Context Bootstrap block and the `## Discovery Gate` heading.

### Section Content Specification

The new section must implement exactly what the spec (FR-009 through FR-016) describes. The section is prose instructions for the AI agent, not Python code. Use the format established by the rest of the template (bash code blocks for commands the agent should run, plain text for conditional logic).

---

## Subtasks

### T007 — Insert Brief Context Detection section in the source template

**Purpose**: Teach the specify agent to detect brief files before discovery and enter brief-intake mode.

**File**: `src/specify_cli/missions/software-dev/command-templates/specify.md` (modify)

**Insertion point**: Immediately after the `## Charter Context Bootstrap (required)` section block ends, before `## Discovery Gate (mandatory)`.

**Section to insert** (verbatim — preserve exact headings, bash blocks, and table format):

```markdown
## Brief Context Detection (check before discovery)

Before starting discovery, check for a pre-existing mission brief:

\```bash
ls .kittify/mission-brief.md 2>/dev/null && echo "MISSION_BRIEF_FOUND"
ls .kittify/ticket-context.md 2>/dev/null && echo "TICKET_CONTEXT_FOUND"
\```

Check in priority order:
1. `.kittify/mission-brief.md` — general plan intake (written by `spec-kitty intake`)
2. `.kittify/ticket-context.md` — tracker ticket (written by `mission create --from-ticket`)

### If a brief file is found → Enter Brief-Intake Mode

**BRIEF DETECTED: `<filename>` (source: `<source_file>`)**

1. **Read the full brief.** Do not skim.

2. **Summarise for the user.** Present a single paragraph: what the brief says the goal is, who it is for, and what the key constraints are. Example: "I found a plan document from Claude Code plan mode. Here's what I understand the goal to be: [summary]. I'll extract the spec from this brief rather than running a full discovery interview."

3. **Extract requirements directly.** Map the brief's content to `FR-###`, `NFR-###`, and `C-###` IDs. Do not ask questions the brief already answers. Specifically extract:
   - Objective → Functional Requirements
   - Constraints and non-goals → Non-Functional Requirements and Constraints
   - Acceptance criteria → FR status and Definition of Done markers
   - Risks and open questions → Assumptions or `[NEEDS CLARIFICATION]` markers (max 3)

4. **Ask gap-filling questions only.** Scale to brief quality:

   | Brief quality | Discovery questions |
   |---------------|---------------------|
   | Comprehensive (objective + constraints + approach + ACs) | 0–1 gap-filling questions |
   | Good (objective + constraints, no ACs) | 2–3 questions |
   | Partial (goal statement only) | 4–5 questions |
   | Empty / missing | Proceed to normal Discovery Gate below |

5. **Show the extracted requirement set.** Present the full FR/NFR/C table to the user: "I extracted X functional requirements and Y non-functional requirements. Does this look right?" Wait for one round of confirmation. The user may correct or supplement before you write the spec.

6. **Write spec.md normally.** Apply the same quality checklist and readiness gate as standard specify. Brief-intake mode does NOT lower the quality bar — spec.md must still pass all validation items.

7. **After spec.md is committed, delete all brief files** (each only if present):
   \```bash
   rm -f .kittify/mission-brief.md
   rm -f .kittify/brief-source.yaml
   rm -f .kittify/ticket-context.md
   rm -f .kittify/pending-origin.yaml
   \```

**What brief-intake mode does NOT do:**
- Does not copy brief prose verbatim into spec.md — it extracts and structures requirements
- Does not skip the quality checklist
- Does not skip the readiness gate
- Does not require the brief to be in any particular format — Markdown prose is fine

### If no brief file is found → Proceed with normal Discovery Gate

No change to current behaviour. Continue to the Discovery Gate section below.
```

**Validation**:
- [ ] The section heading is exactly `## Brief Context Detection (check before discovery)`
- [ ] It appears after `## Charter Context Bootstrap (required)` and before `## Discovery Gate (mandatory)` in the file
- [ ] No other content in the file is modified

---

### T008 — Run `spec-kitty upgrade` to propagate to all 13 agent directories

**Purpose**: Propagate the source template edit to every configured agent directory.

**Command**:
```bash
spec-kitty upgrade
```

Run from the repository root. The upgrade command reads from `src/specify_cli/missions/*/command-templates/` and writes to all 13 agent directories:

| Agent | Directory | Subdirectory |
|-------|-----------|--------------|
| Claude Code | `.claude/` | `commands/` |
| GitHub Copilot | `.github/` | `prompts/` |
| Google Gemini | `.gemini/` | `commands/` |
| Cursor | `.cursor/` | `commands/` |
| Qwen Code | `.qwen/` | `commands/` |
| OpenCode | `.opencode/` | `command/` |
| Windsurf | `.windsurf/` | `workflows/` |
| Kilocode | `.kilocode/` | `workflows/` |
| Augment Code | `.augment/` | `commands/` |
| Roo Cline | `.roo/` | `commands/` |
| Amazon Q | `.amazonq/` | `prompts/` |
| Kiro | `.kiro/` | `prompts/` |
| Google Antigravity | `.agent/` | `workflows/` |
| Codex / Vibe | `.agents/skills/` | `spec-kitty.specify/SKILL.md` |

**Expected outcome**: `spec-kitty upgrade` exits 0. Some agents may not be configured for this project (that is acceptable — the upgrade only processes configured agents).

**Validation**:
- [ ] `spec-kitty upgrade` exits 0 with no error output
- [ ] Git status shows modified files in agent directories (confirms propagation happened)

---

### T009 — Verify propagation

**Purpose**: Confirm the new section is present in at least the Claude Code agent copy as a representative spot-check.

**Check**:
```bash
grep -n "Brief Context Detection" .claude/commands/spec-kitty.specify.md
```

Expected output: a line number and the heading text.

Also verify structural order in the Claude copy:
```bash
grep -n "Charter Context Bootstrap\|Brief Context Detection\|Discovery Gate" .claude/commands/spec-kitty.specify.md
```

Expected: lines in ascending order — Charter Bootstrap line number < Brief Context Detection line number < Discovery Gate line number.

**Validation**:
- [ ] `grep "Brief Context Detection" .claude/commands/spec-kitty.specify.md` produces output
- [ ] Section appears between Charter Context Bootstrap and Discovery Gate in the agent copy
- [ ] Spot-check one other configured agent directory (e.g., `.opencode/command/spec-kitty.specify.md`)

---

## Definition of Done

- [ ] Source template (`src/specify_cli/missions/software-dev/command-templates/specify.md`) contains the new section in the correct position
- [ ] `spec-kitty upgrade` exits 0
- [ ] `.claude/commands/spec-kitty.specify.md` contains `## Brief Context Detection (check before discovery)`
- [ ] Section appears after Charter Context Bootstrap and before Discovery Gate in the source and all agent copies
- [ ] No other sections in the specify template are modified
- [ ] `git diff src/specify_cli/missions/software-dev/command-templates/specify.md` shows only the insertion (no deletions, no modifications to surrounding content)

## Risks

| Risk | Mitigation |
|------|-----------|
| Incorrect insertion point corrupts template structure | Read template fully; search for exact heading text before inserting |
| `spec-kitty upgrade` fails for some agents | Check exit code; if non-zero, inspect stderr and fix before declaring done |
| New section inadvertently modifies Discovery Gate behaviour | Verify Discovery Gate heading and content are unchanged after insertion |
| Bash backticks in the section content confuse Markdown rendering | Use proper fenced code blocks; test that the agent copy renders correctly |

## Reviewer Guidance

- The section heading must be `## Brief Context Detection (check before discovery)` (exact text — this is what agents grep for)
- The priority order must be: `mission-brief.md` first, `ticket-context.md` second
- The quality table must include all four rows from the spec (FR-013)
- Verify the cleanup `rm -f` commands cover all four files: `mission-brief.md`, `brief-source.yaml`, `ticket-context.md`, `pending-origin.yaml`
- The "If no brief file is found" branch must explicitly say to proceed with the normal Discovery Gate (FR-016)
- Compare `.claude/commands/spec-kitty.specify.md` before and after upgrade to confirm only the new section was added
