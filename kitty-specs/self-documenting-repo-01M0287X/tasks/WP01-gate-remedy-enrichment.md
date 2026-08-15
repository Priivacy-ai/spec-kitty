---
work_package_id: WP01
title: Gate-remedy enrichment (G1)
dependencies: []
requirement_refs:
- FR-001
- NFR-003
- C-005
planning_base_branch: kitty/mission-self-doc-gapclose
merge_target_branch: kitty/mission-self-doc-gapclose
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-self-doc-gapclose. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-self-doc-gapclose unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-self-documenting-repo-01M0287X
base_commit: ecc0215b995f3a816b44e68507e350a80a413dbc
created_at: '2026-08-15T08:45:54.652668+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1
history:
- timestamp: '2026-08-15T08:10:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_gate_remedy_presence.py
execution_mode: code_change
mission_id: 01M0287XCV1R9VDEXHSDB0RTYR
owned_files:
- tests/architectural/test_no_write_side_rederivation.py
- tests/architectural/test_no_inert_schema_slots.py
- tests/docs/test_relative_link_fixer.py
- tests/docs/test_related_validator.py
tags: []
tracker_refs: []
wp_code: WP01
---

# Work Package Prompt: WP01 – Gate-remedy enrichment (G1)

## Objective
Add content-anchored remedy text to the architectural/docs gates that genuinely lack it, **derived from each gate's current logic and validated by tripping it** (C-005) — never transcribed from a private note. Pin remedy presence with a meta-test.

## Subtasks
- **T001 Locate + classify.** For each enumerated gate, find its real owning test and classify: remedy-extensible vs not-applicable. Known outcomes (post-plan squad): the shard-registration remedy is **retired** by #2671 auto-cover (`tests/_arch_shard_map.py:46-63`, `default_fallback=True`) → manifest 'behavior retired', no edit; `analysis-report-staleness` (`tests/specify_cli/test_analysis_report_charter_yaml_staleness.py`) is a narrow correctness test → likely not remedy-bearing; `docs-move` → `test_relative_link_fixer.py` + `test_related_validator.py`; `mission-gate-artifact` → locate or drop. Record classifications for WP05's manifest.
- **T002 Enrich.** Add a content-anchored remedy line to each confirmed gate, using `test_golden_count_ban.py` (escape-hatch marker + re-freeze) as the model. Content descriptors only — never file:line / whole-file allowlist (NFR-003 / DIRECTIVE_041).
- **T003 Meta-test (property, not echo).** `tests/architectural/test_gate_remedy_presence.py` asserts each registered gate's assertion carries a remedy that is **content-anchored** — i.e. contains a directive verb and **no** `file:line` pattern or whole-file-path token (NFR-003) — rather than merely echoing a literal the implementer also wrote (which would be tautological). Register it wherever the arch suite requires (verify against auto-cover — likely nothing to add).
- **T004 Validate (evidenced).** Trip each enriched gate in a scratch tree and **paste the failing assertion output into the WP review evidence** — the reviewer treats this as a hard gate (SC-001's manual half). A remedy that reads 'fix it' fails this check even though it passes the substring meta-test.

## Done
SC-001 machine check green; ruff/mypy clean; no snapshot pins broken by the message change.
