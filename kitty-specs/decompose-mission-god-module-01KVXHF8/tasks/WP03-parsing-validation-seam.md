---
work_package_id: WP03
title: Parsing & validation seam (Seam C)
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-006
- NFR-001
- NFR-002
tracker_refs: []
planning_base_branch: prog/2056-mission
merge_target_branch: prog/2056-mission
branch_strategy: Planning artifacts for this mission were generated on prog/2056-mission. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2056-mission unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-decompose-mission-god-module-01KVXHF8
base_commit: cc74304cd7f3ac2d26cc05c3904ff69feb19f276
created_at: '2026-06-24T19:52:40.998893+00:00'
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 2 - Parsing surface
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3139198"
history:
- timestamp: '2026-06-24T19:52:40Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/mission_parsing.py
create_intent:
- src/specify_cli/cli/commands/agent/mission_parsing.py
- tests/specify_cli/cli/commands/agent/test_mission_parsing.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_parsing.py
- tests/specify_cli/cli/commands/agent/test_mission_parsing.py
tags: []
---

# Work Package Prompt: WP03 – Parsing & validation seam (Seam C)

## Do This First

1. Confirm WP02 merged and the golden test is green.
2. Read research.md §3 Seam C and §5 (the parsers are currently exercised only INDIRECTLY via finalize —
   this WP adds the missing DIRECT unit tests; Sonar: every helper needs a focused test).
3. `tasks.py` imports `_parse_requirement_refs_from_tasks_md` — it must stay resolvable (via `mission.<name>`).

## Objective

Extract the (mostly pure) parsers, owned-files validators, and JSON emit shims into `mission_parsing.py`,
and give every pure helper a direct unit test.

## Implementation

### T009 — Create the seam module
Move into `mission_parsing.py`:
- Parsers: `_parse_wp_sections_from_tasks_md`, `_parse_dependencies_from_tasks_md`,
  `_parse_requirement_refs_from_tasks_md`, `_parse_requirement_refs_from_wp_files`,
  `_parse_requirement_ids_from_spec_md`, `_extract_wp_ids_from_task_files`.
- Owned-files validators: `_normalize_owned_file_path`, `_is_mission_specs_owned_file`,
  `_owned_files_yaml_is_explicit_empty_list`, `_raw_frontmatter_has_field`,
  `_invalid_mission_specs_owned_files`.
- JSON emit shims: `_emit_json`, `_with_cli_version`, `_with_mission_aliases`,
  `_emit_console_or_json_error`, `_utc_now_iso`.

### T010 — Repoint references
Update `mission.py` imports to the new seam (documented out-of-map edit).

### T011 — Direct unit tests
Author `test_mission_parsing.py`: DIRECT tests per parser (well-formed, empty, malformed inputs), per
validator (valid/invalid owned-files cases incl. explicit empty list), and per emit shim (envelope key
injection). Target ≥90%.

### T012 — Gates
Confirm JSON-envelope keys unchanged via golden + `test_json_envelope_strict.py`; ruff + mypy clean.

## Acceptance

- Pure parsers/validators have direct tests (closes the §5 gap); ≥90% coverage of the seam.
- Envelope keys byte-identical (INV-2); golden green; no function over CC 15.

## Out-of-map edits

- `src/specify_cli/cli/commands/agent/mission.py`: import-line edits only.

## Activity Log

- 2026-06-24T20:50:55Z – claude:opus:randy-reducer:implementer – shell_pid=3081068 – Assigned agent via action command
- 2026-06-24T21:03:11Z – claude:opus:randy-reducer:implementer – shell_pid=3081068 – Seam C extracted; 32 seam tests (98% cov) + golden + json_envelope + tasks + analysis_report green (438+153); ruff C901 clean; mypy clean on new files. --force: pre-existing mission-branch status bookkeeping contamination only (same as approved lanes a/b).
- 2026-06-24T21:03:21Z – claude:opus:reviewer-renata:reviewer – shell_pid=3139198 – Started review via action command
- 2026-06-24T21:03:25Z – user – shell_pid=3139198 – Review passed: behavior-preserving Seam C extraction; pure parsers/validators/emit shims with direct tests (32, 98% cov) closing research §5 gap; envelope keys byte-identical (golden+json_envelope green); tasks.py + test_wp_header_regex_depth import edges + mission._emit_json patch targets all green; ruff C901 clean; mypy clean on new files (3 pre-existing findings relocated, no new). Scope clean. --force: pre-existing status bookkeeping contamination.
