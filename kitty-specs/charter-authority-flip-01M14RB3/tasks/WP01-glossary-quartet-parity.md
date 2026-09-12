---
work_package_id: WP01
title: Glossary parity + charter Canon + authority-3 rename + intra-context links
dependencies: []
requirement_refs:
- FR-001
- FR-003
planning_base_branch: feat/charter-authority-flip
merge_target_branch: feat/charter-authority-flip
branch_strategy: Planning artifacts for this mission were generated on feat/charter-authority-flip. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-authority-flip unless the human explicitly redirects the landing branch.
base_branch: feat/charter-authority-flip
base_commit: 7b0c2d3ed53cd47ad50e4f75da84c7b9ca4c3044
created_at: '2026-08-28T18:28:53Z'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T005a
- T006
phase: Glossary parity + charter Canon + authority-3 rename + intra-context links
history: []
agent_profile: python-pedro
authoritative_surface: docs/context/
create_intent:
- docs/context/charter.md
- tests/architectural/test_glossary_authority_parity.py
- tests/architectural/test_charter_owner_map_executed.py
execution_mode: code_change
model: ''
owned_files:
- docs/context/doctrine.md
- .kittify/glossaries/spec_kitty_core.yaml
- packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml
- docs/context/orchestration.md
- docs/context/governance.md
- docs/context/configuration-project-structure.md
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3664
- https://github.com/Priivacy-ai/spec-kitty/issues/3732
---
