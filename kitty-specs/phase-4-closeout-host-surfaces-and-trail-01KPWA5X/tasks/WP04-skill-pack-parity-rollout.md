---
work_package_id: WP04
title: Skill-Pack Parity Rollout to Remaining Agent Surfaces
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
agent: "claude:sonnet-4-6:implementer:implementer"
shell_pid: "16292"
history:
- event: created
  at: '2026-04-23T05:10:00Z'
  note: Initial generation from /spec-kitty.tasks
authoritative_surface: .github/prompts/
execution_mode: code_change
owned_files:
- .github/prompts/spec-kitty-standalone.md
- .gemini/commands/spec-kitty-standalone.md
- .cursor/commands/spec-kitty-standalone.md
- .qwen/commands/spec-kitty-standalone.md
- .opencode/command/spec-kitty-standalone.md
- .windsurf/workflows/spec-kitty-standalone.md
- .kilocode/workflows/spec-kitty-standalone.md
- .augment/commands/spec-kitty-standalone.md
- .roo/commands/spec-kitty-standalone.md
- .amazonq/prompts/spec-kitty-standalone.md
- .kiro/prompts/spec-kitty-standalone.md
- .agent/workflows/spec-kitty-standalone.md
tags: []
---

# WP04 — Skill-Pack Parity Rollout to Remaining Agent Surfaces

## Objective

Bring the 12 non-canonical host surfaces to parity with the advise/ask/do governance-injection contract. The canonical reference is `.agents/skills/spec-kitty.advise/SKILL.md`; the in-repo already-shipped content for Claude Code lives in `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`.

Each of the 12 surfaces receives a new file at `<agent-dir>/spec-kitty-standalone.md` whose shape is determined by WP01's inventory: either inline content (fits surfaces whose convention is to host skill-pack files in-repo) or a pointer file (fits surfaces whose host primarily consumes `/spec-kitty.*` slash-command templates generated from mission sources, where duplicating canonical content would be churn).

## Context

**Why new files, not edits to existing ones**: per project CLAUDE.md, the generated `/spec-kitty.*` slash-command templates in each agent directory are mirrors of `src/specify_cli/missions/*/command-templates/`. Editing them is wrong. The new `spec-kitty-standalone.md` file is not a mission-step slash-command mirror — it is a standalone-invocation skill-pack file, authored directly in each agent directory. Spec-kitty's upgrade machinery does not regenerate these files.

**Why the same filename across surfaces**: consistency makes the parity matrix readable. Host LLMs that scan their agent directory for recognisable file patterns find a predictable name.

**Why three groups**: 12 surfaces is too many to audit and update as one atomic effort; 3 groups of 4 keeps each subtask within reviewable scope.

## Branch Strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: allocated from `lanes.json` at implement time. WP04 depends on WP01 for inventory scope but can run in parallel with WP02 and WP03.

## Subtask Guidance

### T015 — Decide inline vs pointer per surface

**Purpose**: Lock in the content shape for each of the 12 surfaces before implementing.

**Inputs**:
- `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md` (from WP01).
- `.agents/skills/spec-kitty.advise/SKILL.md` (canonical content reference).

**Steps**:
1. Open the inventory. For each row with `parity_status ∈ {partial, missing}`, confirm the `guidance_style` column (`inline` or `pointer`) and the specific file path.
2. If any row's `guidance_style` disagrees with the convention below, update the inventory and record a note.

**Recommended convention per surface family**:

| Surface family | Convention | Reason |
|----------------|-----------|--------|
| Slash-command hosts that primarily run `/spec-kitty.*` mission commands (copilot, gemini, cursor, qwen, opencode, windsurf, kilocode, auggie, roo, q, kiro, agent) | **Pointer** | Their agent directory is dominated by generated mission-step files; adding inline canonical content duplicates doctrine. A pointer file that redirects the host to `.agents/skills/spec-kitty.advise/SKILL.md` is the minimal intervention. |

Most surfaces will be `pointer` style. That is the expected outcome.

### T016 — Surface group 1 (copilot, gemini, cursor, qwen)

**Purpose**: Ship the 4 pointer files.

**Per surface, create the file listed in owned_files with this template**:

```markdown
# spec-kitty standalone invocation

This host should read Spec Kitty's canonical standalone-invocation skill pack at:

**`.agents/skills/spec-kitty.advise/SKILL.md`**

That file teaches:
- When to call `spec-kitty advise`, `spec-kitty ask <profile>`, or `spec-kitty do <request>`.
- How to read `governance_context_text` from the response and inject it as binding governance context.
- How to close the invocation record with `spec-kitty profile-invocation complete --invocation-id <id> --outcome done`.

These commands are available alongside the `/spec-kitty.*` mission-step commands in this directory. Use them for standalone invocations that are not part of a running mission workflow.

For the shipped trail contract and SaaS read-model policy, see [`docs/trail-model.md`](../../docs/trail-model.md).
```

Adjust the relative path to `docs/trail-model.md` based on the depth of the target file's directory. For example:
- `.cursor/commands/spec-kitty-standalone.md` → `../../docs/trail-model.md` (two `..`).
- `.github/prompts/spec-kitty-standalone.md` → `../../docs/trail-model.md`.

**Specific files this subtask creates**:
- `.github/prompts/spec-kitty-standalone.md`
- `.gemini/commands/spec-kitty-standalone.md`
- `.cursor/commands/spec-kitty-standalone.md`
- `.qwen/commands/spec-kitty-standalone.md`

### T017 — Surface group 2 (opencode, windsurf, kilocode)

**Purpose**: Ship the 3 pointer files.

**Files**:
- `.opencode/command/spec-kitty-standalone.md` (note: `command/` singular, not `commands/` — matches project CLAUDE.md AGENT_DIRS mapping).
- `.windsurf/workflows/spec-kitty-standalone.md`
- `.kilocode/workflows/spec-kitty-standalone.md`

Use the same template as T016.

### T018 — Surface group 3 (auggie, roo, q, kiro, agent)

**Purpose**: Ship the 5 pointer files.

**Files**:
- `.augment/commands/spec-kitty-standalone.md`
- `.roo/commands/spec-kitty-standalone.md`
- `.amazonq/prompts/spec-kitty-standalone.md`
- `.kiro/prompts/spec-kitty-standalone.md`
- `.agent/workflows/spec-kitty-standalone.md`

Use the same template as T016.

### T019 — Update inventory matrix

**Purpose**: After the 12 files are shipped, update the matrix so every row reads `at_parity`.

**Steps**:
1. Open `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md`.
2. For each of the 12 surfaces WP04 touched, set:
   - `has_advise_guidance = yes`
   - `has_governance_injection = yes` (the canonical file teaches it; the pointer makes it reachable)
   - `has_completion_guidance = yes`
   - `guidance_style = pointer` (or `inline` if the inventory said so)
   - `parity_status = at_parity`
   - `notes`: one line confirming the pointer file path and that the canonical content is reachable.
3. Commit the inventory update in the same commit as the 12 pointer files (or as the WP's final commit).

**Note**: WP01 owns the inventory file at rest. WP04 mutating it is fine because WP04 is downstream of WP01 in the dependency graph; the ownership validator treats a single `owned_files` entry for the inventory as WP01's, but file modification across lanes is supported under the lane-sequencing model when explicit. If the validator flags this: move the inventory update into WP05 (T024) instead — WP05 owns this surface at closeout. Implementer: verify which approach passes `finalize-tasks --validate-only`; prefer updating the inventory in WP04 but fall back to WP05 if the validator rejects it.

## Definition of Done

- [ ] All 12 pointer files listed in `owned_files` exist with the template content.
- [ ] Each file's relative link to `docs/trail-model.md` resolves correctly from its location.
- [ ] Inventory matrix updated to show `at_parity` for every touched surface (T019).
- [ ] `git diff --stat` shows exactly 12 new files under agent directories, no modifications to existing generated `/spec-kitty.*` command templates.
- [ ] No change to `.agents/skills/spec-kitty.advise/SKILL.md` (canonical reference stays stable).
- [ ] Commit message references `#496` and WP04.

## Risks

- **Inline-vs-pointer inconsistency**: an inventory row reads `inline` but the file is shipped as pointer (or vice versa). Mitigation: T015 locks the decision; review verifies the shipped file matches the inventory claim.
- **Path depth mismatch**: the relative `../../docs/trail-model.md` link breaks if a surface's directory structure is deeper than 2 levels from repo root. Mitigation: verify each link by opening the file and clicking through, or use an absolute repo-relative path from the user's perspective (acceptable in markdown).
- **Agent directory missing**: some projects may not have all 12 agent directories (user configured only a subset per `.kittify/config.yaml`). Per the project's AGENT_DIRS guidance and `get_agent_dirs_for_project()` helper, the rollout should respect the project's own agent config. However, since this WP ships on the spec-kitty repo itself — which hosts ALL 13 slash-command agent directories for development — every directory should be present. If one is unexpectedly absent, the WP reports the mismatch rather than improvising.
- **Validator rejects WP04 mutating the WP01-owned inventory**: see T019 note. Fallback is to leave the inventory update for WP05.

## Reviewer Guidance

Reviewer should:
- Verify all 12 files exist (`ls .github/prompts/spec-kitty-standalone.md .gemini/commands/spec-kitty-standalone.md …`).
- Open 3 random files and confirm the template matches the prescribed content.
- Click each relative `docs/trail-model.md` link from the rendered markdown — all must resolve.
- Confirm no file under `.claude/`, `.agents/skills/spec-kitty.advise/`, or `src/doctrine/skills/spec-kitty-runtime-next/` was modified (the canonicals stay untouched).
- Confirm the inventory matrix reads `at_parity` for every touched row.

## Activity Log

- 2026-04-23T05:41:41Z – claude:sonnet-4-6:implementer:implementer – shell_pid=16292 – Started implementation via action command
- 2026-04-23T05:46:34Z – claude:sonnet-4-6:implementer:implementer – shell_pid=16292 – 12 pointer files shipped; 11 agents enabled via config add (antigravity key for .agent/); agent dirs required git add -f (gitignored in ref repo); T019 inventory update deferred to WP05 (validator blocks kitty-specs on lane branch)
