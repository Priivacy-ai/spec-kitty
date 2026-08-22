---
work_package_id: WP01
title: '#3605 — procedure reference rationale reaches the DRG'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- NFR-002
planning_base_branch: rc3-drg-projection-completeness-01M0GGS7
merge_target_branch: rc3-drg-projection-completeness-01M0GGS7
branch_strategy: Planning artifacts for this mission were generated on rc3-drg-projection-completeness-01M0GGS7. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-drg-projection-completeness-01M0GGS7 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-drg-projection-completeness-01M0GGS7
base_commit: e1239c9dcfbc0435607341bcb46b3619ddb06d61
created_at: '2026-08-21T18:08:55.720792+00:00'
subtasks:
- T001
- T002
- T003
- T004
history: []
agent_profile: implementer-ivan
authoritative_surface: src/doctrine/drg/migration/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/drg/migration/extractor.py
- tests/doctrine/drg/migration/test_extractor.py
tags: []
tracker_refs: []
---

# WP01 — #3605: procedure reference rationale reaches the DRG

**Goal:** the procedures branch of the DRG extractor must carry authored
`when`/`reason` on its edges, like directive/tactic/paradigm — **without changing
any edge triple** (source, target, relation). Red-first.

**Grounding (current main):** the procedures loop mints `DRGEdge(...)` inline at
`src/doctrine/drg/migration/extractor.py:878–906`, bypassing the single authority
`_reference_edge_kwargs(ref)` (`:542`). The helper's own docstring documents the
gap. Directive (`:768`) / tactic-top (`:802`) / tactic-step (`:823`) / paradigm
(`:875`) already route through it.

### Subtask T001 — `[red]` procedure reason round-trip test
- **Purpose:** pin FR-001/AC-001 red-first.
- **Files:** `tests/doctrine/drg/migration/test_extractor.py` (+~30 lines).
- Mirror `test_directive_reference_reason_roundtrips` (`:266`) /
  `test_tactic_reference_reason_roundtrips` (`:313`): fixture with a procedure
  `references:` entry authoring `when`/`reason` → `extract_artifact_edges(root)` →
  assert the `procedure --…--> target` edge carries that `when`/`reason`; a
  reference without `reason` → `reason is None`. **Must fail before T002.**

### Subtask T002 — route procedures through the single authority
- **Purpose:** FR-001 fix.
- **Files:** `extractor.py` (procedures loop `:878–906`).
- Replace the inline `DRGEdge(source, target, relation=_relation_for_procedure_ref_type(ref_type))`
  with a construction that spreads `**_reference_edge_kwargs(ref)` while keeping the
  same relation computation. GREEN T001.

### Subtask T003 — `[red]` triple-identity guard (NFR-002/AC-009)
- **Purpose:** guarantee only metadata is added; no silent graph corruption.
- **Files:** `test_extractor.py` (+~20 lines).
- Assert the procedure edge **(source, target, relation)** set over the built-in
  corpus (or a representative fixture) is identical pre/post fix; only `when`/`reason`
  differ. This is the byte-identity guard the re-ledger relies on.

### Subtask T004 — *(optional, FR-002/AC-002)* single-helper structural test
- **Purpose:** stop a future branch from dropping a field.
- **Files:** `extractor.py`, `test_extractor.py`.
- Only if it stays a small diff: extract one shared emit helper for the five
  `{type,id,when?,reason?}` branches and add a structural test (`inspect.getsource`
  + regex over `extract_artifact_edges`) that every branch routes through it. Skip
  if it churns unrelated branches (smallest-viable-diff wins).

## Definition of Done
- [ ] T001 red before T002, green after.
- [ ] Procedures loop routes through `_reference_edge_kwargs`; relation unchanged.
- [ ] T003 triple-identity guard passes.
- [ ] (opt) T004 single-helper test, only if small.
- [ ] `ruff` + `mypy` clean, no new suppressions. **Do NOT regenerate goldens here**
      (that is WP04's single re-ledger).

Implement: `spec-kitty agent action implement WP01 --agent claude`
