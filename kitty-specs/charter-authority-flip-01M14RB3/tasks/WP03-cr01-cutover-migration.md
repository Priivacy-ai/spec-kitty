---
work_package_id: WP03
title: CR-01 key cutover + answers migration + serializer
dependencies: []
requirement_refs:
- FR-004
- FR-005
planning_base_branch: feat/charter-authority-flip
merge_target_branch: feat/charter-authority-flip
branch_strategy: Planning artifacts for this mission were generated on feat/charter-authority-flip. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-authority-flip unless the human explicitly redirects the landing branch.
base_branch: feat/charter-authority-flip
base_commit: 7b0c2d3ed53cd47ad50e4f75da84c7b9ca4c3044
created_at: '2026-08-28T18:28:53Z'
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
phase: CR-01 key cutover + answers migration + serializer
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- scripts/migrate_charter_interview_answers.py
- tests/charter/test_governance_key_compat.py
- tests/charter/test_answers_migration.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/sync.py
- src/charter/schemas.py
- src/charter/resolver.py
- src/charter/org_pack_discovery.py
- src/charter/interview.py
- src/specify_cli/cli/commands/charter/_status_collectors.py
- .kittify/charter/charter.yaml
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3664
- https://github.com/Priivacy-ai/spec-kitty/issues/3732
---
