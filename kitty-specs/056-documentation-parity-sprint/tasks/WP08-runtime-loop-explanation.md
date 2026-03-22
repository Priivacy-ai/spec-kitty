---
work_package_id: WP08
title: Runtime Loop Explanation
lane: "approved"
dependencies: [WP01]
requirement_refs: [FR-004]
planning_base_branch: fix/skill-audit-and-expansion
merge_target_branch: fix/skill-audit-and-expansion
branch_strategy: Planning artifacts for this feature were generated on fix/skill-audit-and-expansion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/skill-audit-and-expansion unless the human explicitly redirects the landing branch.
base_branch: 056-documentation-parity-sprint-WP01
base_commit: a3c2fae9fa7c40e05f6ae6b06619574b80195a42
created_at: '2026-03-22T14:58:58.362388+00:00'
subtasks: [T038, T039, T040, T041, T042]
agent: coordinator
shell_pid: '21973'
reviewed_by: "Robert Douglass"
review_status: "approved"
history:
- date: '2026-03-22'
  action: created
  agent: claude
  note: Generated from plan.md Phase 3
---

# WP08: Runtime Loop Explanation

## Objective

Create `docs/explanation/runtime-loop.md` — a user-facing explanation distilled
from the `spec-kitty-runtime-next` skill. Explain what `spec-kitty next` does,
when to use it, how to interpret results, and the known issues.

## Source Material

Read `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and
`references/runtime-result-taxonomy.md` and `references/blocked-state-recovery.md`.

## Implementation

### T038: What is spec-kitty next?

Explain the core concept: `spec-kitty next` is the autonomous alternative to
manually running slash commands. Instead of the user deciding "now I should
run /spec-kitty.implement for WP03", an agent calls `spec-kitty next` and the
runtime tells it what to do.

Explain when to use it:
- Multi-agent orchestration (agents running in a loop)
- Autonomous feature development
- When you want the runtime to decide ordering

Explain when NOT to use it:
- Manual workflow (just use slash commands directly)
- Single-developer, single-feature work

### T039: Decision kinds

Document the 4 kinds with user-facing examples:

| Kind | What it means | What to do |
|---|---|---|
| `step` | Action available | Read the prompt_file, do the work |
| `decision_required` | Runtime needs input | Answer with --answer |
| `blocked` | Can't proceed | Read reason, fix the blocker |
| `terminal` | Mission complete | Run /spec-kitty.accept |

Show example JSON output for a `step` decision.

### T040: The agent loop

Explain the conceptual pattern without code:
1. Call `spec-kitty next --agent claude --feature <slug> --json`
2. Read the decision
3. If step: execute the prompt, report result
4. If blocked/terminal: stop or fix
5. Repeat

Mention that WP02-WP09 in an implementation phase will return different WP
IDs on each call but the same step_id ("implement").

### T041: Known issues

Document the two bugs as user-facing notes:
- **Completed features may return `step` instead of `terminal`** (#335) —
  Workaround: check if `progress.done_wps == progress.total_wps`
- **Some steps return `prompt_file: null`** (#336) —
  Workaround: treat null prompt as blocked

Frame these as "things to be aware of" not "bugs in the product."

### T042: Update toc.yml

Add `runtime-loop.md` to `docs/explanation/toc.yml`.

## Definition of Done

- [ ] Guide created at `docs/explanation/runtime-loop.md`
- [ ] Explains when to use next vs slash commands
- [ ] Decision kinds documented with examples
- [ ] Known issues documented with workarounds
- [ ] No internal architecture (no runtime_bridge.py, no DAG planner code)
- [ ] toc.yml updated

## Implementation Command

```bash
spec-kitty implement WP08 --base WP01
```

## Activity Log

- 2026-03-22T14:58:58Z – coordinator – shell_pid=21973 – lane=doing – Assigned agent via workflow command
- 2026-03-22T15:03:40Z – coordinator – shell_pid=21973 – lane=for_review – Runtime loop explanation created
- 2026-03-22T15:06:42Z – coordinator – shell_pid=21973 – lane=approved – Review passed: docs-only changes, correct files, toc updated
