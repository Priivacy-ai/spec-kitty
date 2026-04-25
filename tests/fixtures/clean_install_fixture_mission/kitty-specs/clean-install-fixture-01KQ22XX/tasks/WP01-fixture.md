---
work_package_id: WP01
title: Fixture
dependencies: []
requirement_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Single-WP fixture mission. Operates on main; no worktree.
subtasks:
- T001
history:
- at: '2026-04-25T12:00:00+00:00'
  actor: planner
  event: created
authoritative_surface: hello.txt
execution_mode: code_change
owned_files:
- hello.txt
tags: []
---

# WP01 — Fixture

## Objective

Create a file `hello.txt` containing the word `OK`. This is a no-op
subtask whose only purpose is to give `spec-kitty next` something to
advance through.

## Subtasks

### T001 — Create `hello.txt`

Write the literal string `OK` to `hello.txt`.

## Definition of Done

- [ ] `hello.txt` exists with content `OK`.
