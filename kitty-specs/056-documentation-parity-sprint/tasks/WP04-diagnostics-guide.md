---
work_package_id: WP04
title: Installation Diagnostics Guide
lane: "doing"
dependencies: [WP01]
requirement_refs: [FR-006]
planning_base_branch: fix/skill-audit-and-expansion
merge_target_branch: fix/skill-audit-and-expansion
branch_strategy: Planning artifacts for this feature were generated on fix/skill-audit-and-expansion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/skill-audit-and-expansion unless the human explicitly redirects the landing branch.
base_branch: 056-documentation-parity-sprint-WP01
base_commit: a3c2fae9fa7c40e05f6ae6b06619574b80195a42
created_at: '2026-03-22T14:58:49.090445+00:00'
subtasks: [T017, T018, T019, T020, T021]
shell_pid: "21973"
agent: "coordinator"
history:
- date: '2026-03-22'
  action: created
  agent: claude
  note: Generated from plan.md Phase 2
---

# WP04: Installation Diagnostics Guide

## Objective

Create `docs/how-to/diagnose-installation.md` — a user-facing guide distilled
from the `spec-kitty-setup-doctor` skill. Help users verify their installation,
diagnose common problems, and recover from failure states.

## Source Material

Read `src/doctrine/skills/spec-kitty-setup-doctor/SKILL.md` and
`references/common-failure-signatures.md`.

## Implementation

### T017: Verify-setup walkthrough

Document the primary diagnostic command:
```bash
spec-kitty verify-setup
```

Explain what it checks (installed tools, skill integrity, agent config) and
how to read the output (checkmarks, warnings, errors).

### T018: Common failure patterns

Document each pattern with symptoms and causes:
1. Missing skill root — agent can't find skills
2. Missing wrapper root — slash commands unavailable
3. Manifest drift — skill files manually edited
4. Runtime not found — .kittify/ missing
5. Dashboard not starting — port conflict
6. Stale agent config — orphaned directories
7. Corrupted config — YAML parse errors
8. Worktree linkage broken — stale git references

### T019: Recovery steps

For each failure pattern, document the exact recovery command:
- Most issues: `spec-kitty init --here`
- Worktree issues: `git worktree prune`
- Corrupted config: backup, remove, re-init

### T020: Safety warning for --remove-orphaned

Document the `.github/` shared directory hazard:
- `spec-kitty agent config sync --remove-orphaned` deletes the entire parent
  directory, not just the agent subdirectory
- `.github/prompts/` shares `.github/` with CI workflows
- Safe alternative: manually delete only the agent subdirectory

### T021: Update toc.yml

Add `diagnose-installation.md` entry to `docs/how-to/toc.yml`.

## Definition of Done

- [ ] Guide created at `docs/how-to/diagnose-installation.md`
- [ ] verify-setup command verified against actual output
- [ ] All 8 failure patterns documented with recovery steps
- [ ] Safety warning included
- [ ] toc.yml updated

## Implementation Command

```bash
spec-kitty implement WP04 --base WP01
```

## Activity Log

- 2026-03-22T14:58:49Z – coordinator – shell_pid=21973 – lane=doing – Assigned agent via workflow command
