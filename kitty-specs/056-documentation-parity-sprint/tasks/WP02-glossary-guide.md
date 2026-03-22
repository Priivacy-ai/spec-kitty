---
work_package_id: WP02
title: Glossary Management Guide
lane: "doing"
dependencies: [WP01]
requirement_refs: [FR-002]
planning_base_branch: fix/skill-audit-and-expansion
merge_target_branch: fix/skill-audit-and-expansion
branch_strategy: Planning artifacts for this feature were generated on fix/skill-audit-and-expansion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/skill-audit-and-expansion unless the human explicitly redirects the landing branch.
base_branch: 056-documentation-parity-sprint-WP01
base_commit: a3c2fae9fa7c40e05f6ae6b06619574b80195a42
created_at: '2026-03-22T14:58:44.302666+00:00'
subtasks: [T006, T007, T008, T009, T010]
shell_pid: "21973"
agent: "coordinator"
history:
- date: '2026-03-22'
  action: created
  agent: claude
  note: Generated from plan.md Phase 2
---

# WP02: Glossary Management Guide

## Objective

Create `docs/how-to/manage-glossary.md` — a user-facing guide distilled from
the `spec-kitty-glossary-context` skill. Focus on what end users need to know:
CLI commands, scope management, conflict resolution. Omit internal architecture
(middleware pipeline, extraction methods, checkpoint/resume).

## Source Material

Read `src/doctrine/skills/spec-kitty-glossary-context/SKILL.md` and its
references for the full technical detail. Distill to ~40-60% of the length.

## Implementation

### T006: Glossary concepts section

Explain what the glossary is and why it matters. Cover:
- Terms have a surface (the word), definition, scope, confidence, and status
- 4 scopes in precedence order: mission_local > team_domain > audience_domain > spec_kitty_core
- Status lifecycle: draft → active → deprecated
- Keep it practical — users need to know scopes exist, not how LRU caching works

### T007: CLI commands with examples

Document each command with copy-pasteable examples and expected output:

```bash
spec-kitty glossary list
spec-kitty glossary list --scope team_domain --status active --json
spec-kitty glossary conflicts
spec-kitty glossary conflicts --unresolved
spec-kitty glossary resolve <conflict-id>
```

Show example table output for `list` and example JSON for `--json` mode.

### T008: Strictness modes

Explain the 3 modes at user level:
- `off` — glossary never blocks mission execution
- `medium` (default) — blocks only HIGH severity conflicts
- `max` — blocks any unresolved conflict

Explain how to change strictness in `.kittify/config.yaml`.

### T009: Seed file editing

Show the YAML format with a concrete example:

```yaml
terms:
  - surface: deployment
    definition: The process of releasing code to production
    confidence: 1.0
    status: active
```

Explain which scope file to edit based on term ownership.

### T010: Update toc.yml

Add `manage-glossary.md` entry to `docs/how-to/toc.yml`.

## Definition of Done

- [ ] Guide created at `docs/how-to/manage-glossary.md`
- [ ] All CLI commands verified against `--help`
- [ ] No internal architecture details (no middleware, no extraction methods)
- [ ] toc.yml updated

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

## Activity Log

- 2026-03-22T14:58:44Z – coordinator – shell_pid=21973 – lane=doing – Assigned agent via workflow command
