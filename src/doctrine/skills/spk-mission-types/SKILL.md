---
name: spk-mission-types
description: "Explain Spec Kitty mission types, step contracts, action indices, and when to choose each mission workflow."
---

# spk-mission-types

Use this skill when the user asks which kind of mission to run or how mission
types differ.

## Workflow

1. Identify the requested work: software change, standalone planning,
   documentation, research, or custom/team workflow.
2. Compare available mission types before creating new process.
3. Use the legacy `spec-kitty-mission-system` skill for detailed step-contract,
   procedure, action-index, and template-resolution mechanics.

## Boundary

Mission types define workflow behavior. Skills explain how to operate that
behavior; they do not redefine the mission DAG.

## Built-In Types

- `software-dev`: default feature/change workflow with tasks and WP iteration.
- `research`: evidence-gathering workflow before or during product decisions.
- `plan`: planning-only workflow.
- `documentation`: documentation-oriented workflow.
