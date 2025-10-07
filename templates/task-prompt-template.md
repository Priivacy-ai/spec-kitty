---
task_id: "TXXX"
title: "Replace with task title"
phase: "Phase N - Replace with phase name"
lane: "planned"  # planned | doing | for_review | done
assignee: ""      # Optional friendly name when in doing/for_review
agent: ""         # CLI agent identifier (claude, codex, etc.)
shell_pid: ""     # PID captured when the task moved to the current lane
history:
  - timestamp: "{{TIMESTAMP}}"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /speckitty.task-prompts"
---

# Task Prompt: {{TASK_ID}} – {{TITLE}}

## Objective

- Summarize the exact outcome that marks this task complete.
- Call out any acceptance criteria or success metrics that must be satisfied.

## Context & Background

- Reference prerequisite knowledge or prior work.
- Link to relevant specs: `.specify/memory/constitution.md`, feature `specs/.../plan.md`, `tasks.md` entry, etc.
- Highlight architectural decisions, constraints, or trade-offs the implementer must honor.

## Files & Entry Points

- List the exact files or directories to read first (include canonical paths).
- Note any new files that must be created and where they belong.

## Implementation Guidance

- Provide a step-by-step outline tailored to this task.
- Include important patterns, edge cases, or validation logic.
- Mention coordination required with other tasks (if any), but keep this task independently executable.

## Test Strategy

- Specify mandatory tests (unit, integration, contract) and where they live.
- Include commands or scripts to run the suite.
- Describe expected test data or fixtures.

## Definition of Done Checklist

- [ ] Code implements the objective and passes tests
- [ ] Documentation updated (if needed)
- [ ] Metrics/telemetry added (if applicable)
- [ ] Observability or logging requirements satisfied
- [ ] Tasks.md updated with status change

## Risks, Concerns & Mitigations

- Call out known pitfalls, performance considerations, or failure modes.
- Provide mitigation strategies or monitoring notes.

## Review Guidance (for /speckitty.review)

- Key acceptance checkpoints the reviewer must verify.
- Any context reviewers should re-read before approving.

## Activity Log

> Append entries here when the task changes lanes. Each entry should include timestamp, agent, shell PID, lane, and a short note.

- {{TIMESTAMP}} – system – lane=planned – Prompt created.

---

### Updating Metadata When Changing Lanes

1. Capture your shell PID: `echo $$` (or use the provided helper scripts when available).
2. Update the frontmatter fields: set `lane`, `assignee` (if you take ownership), `agent`, and `shell_pid`.
3. Add an entry to the **Activity Log** describing the transition.
4. Use `git mv` to move the file between `/tasks/planned`, `/tasks/doing`, `/tasks/for_review`, and `/tasks/done`.
5. Commit or stage the change, preserving history.

### Phase Subdirectories (Optional for Large Features)

If the feature spans multiple phases, create subdirectories such as `tasks/planned/phase-1-setup/` so prompts remain grouped while maintaining lexical ordering.

