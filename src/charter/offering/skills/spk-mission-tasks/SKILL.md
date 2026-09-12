---
name: spk-mission-tasks
description: "Operate Spec Kitty task and work-package authoring, including tasks outline, package slicing, and finalization."
---

# spk-mission-tasks

Use this skill when converting a plan into executable tasks or work packages.

## Flow

1. Use `/spec-kitty.tasks` for the default path.
2. Use `/spec-kitty.tasks-outline`, `/spec-kitty.tasks-packages`, and
   `/spec-kitty.tasks-finalize` when staged work-package authoring is enabled.
3. Keep package boundaries reviewable: each WP should have a clear scope,
   dependencies, verification, and expected files or systems.
4. If WPs are too broad for implementation/review lanes, split before runtime
   execution begins.

## Reviewability Standard

A reviewer should be able to approve or reject each WP independently.
