---
work_package_id: WP04
title: Shrink-only guard (armed last) + archive gate + closing audit
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-006
- FR-007
planning_base_branch: feat/charter-authority-flip
merge_target_branch: feat/charter-authority-flip
branch_strategy: Planning artifacts for this mission were generated on feat/charter-authority-flip. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-authority-flip unless the human explicitly redirects the landing branch.
base_branch: feat/charter-authority-flip
base_commit: 7b0c2d3ed53cd47ad50e4f75da84c7b9ca4c3044
created_at: '2026-08-28T18:28:53Z'
subtasks:
- T018
- T019
- T020
- T021
phase: Shrink-only guard (armed last) + archive gate + closing audit
history: []
agent_profile: reviewer-renata
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_transition_guard_shrink_only.py
- tests/architectural/test_archive_root_byte_identical.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_no_legacy_terminology.py
role: reviewer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3664
- https://github.com/Priivacy-ai/spec-kitty/issues/3732
---
