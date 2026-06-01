---
work_package_id: WP06
title: Retire relationship fields (hard cutover)
dependencies:
- WP07
requirement_refs:
- FR-028
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts were generated on mission/org-doctrine-profile-integrity-activation-closure. During implement this WP runs in its computed lane; completed changes merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/agent_profiles/schema_models.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/doctrine/tactics/models.py
- src/doctrine/styleguides/models.py
- src/doctrine/paradigms/models.py
- src/doctrine/procedures/models.py
- src/doctrine/agent_profiles/schema_models.py
- src/doctrine/agent_profiles/profile.py
- tests/doctrine/test_relationship_fields_rejected.py
role: implementer
tags: []
---

# WP06 — Retire relationship fields (hard cutover)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## ⚠️ BULK-EDIT GATE

This WP is governed by [../occurrence_map.yaml](../occurrence_map.yaml) (`change_mode: bulk_edit`). The `code_symbols` category covers exactly these field removals. The `implement` command will refuse to start until classification is satisfied. Consult the map before editing; do not touch occurrences outside the `code_symbols` action.

## Objective

Execute the hard cutover (OQ-2-i / FR-028): remove the `enhances`/`overrides` fields from the five content-kind models and `enhances`/`overrides`/`specializes_from` from the agent-profile schema, so authoring those keys becomes a validation error. Relationships are henceforth authored as DRG fragment edges (emitted by WP04, migrated by WP07).

## Context

- Spec: FR-028, OQ-2-i (hard cutover; rc breakage acceptable). Data model §3. Contract C2.1.
- **Sequencing**: depends on **WP07** — built-in YAML must already be migrated to fragment edges before the field becomes a hard error, else built-ins fail to load (NFR-005). Do not invert.

### Code map

- `src/doctrine/tactics/models.py:51-59` (`overrides`/`enhances` Fields); same shape in `styleguides`, `paradigms`, `procedures` models.
- `src/doctrine/agent_profiles/schema_models.py:192` + `profile.py:231` (`specializes_from`, `enhances`, `overrides`).
- All use `ConfigDict(extra="forbid")` → removing the field makes the key an unknown-field error automatically; add a clearer message.

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP07.

## Subtasks

### T025 — Remove `enhances`/`overrides` from content-kind models

**Steps**: Delete the `overrides`/`enhances` Field declarations from `tactics`, `styleguides`, `paradigms`, `procedures` `models.py`. Remove now-dead validators/refs to them within those files.

**Validation**: - [ ] fields gone; modules import; `mypy` clean.

### T026 — Remove relationship fields from agent profile

**Steps**: Remove `specializes_from`, `enhances`, `overrides` from `agent_profiles/schema_models.py` and `profile.py` (field + any accessors). Note: the lineage *resolver* migrates in WP05 (different file: `repository.py`), so only remove the field/accessors here.

**Validation**: - [ ] fields/accessors gone; no syntax refs remain in these two files.

### T027 — Actionable rejection message

**Steps**: With `extra="forbid"`, ensure the resulting validation error is actionable — add a model-level note or a custom message hook so the error says relationships are authored in DRG fragments, not fields (point to the fragment authoring docs from WP07/FR-004).

**Validation**: - [ ] loading an artifact with `enhances:`/`overrides:`/`specializes_from:` raises a clear, fragment-pointing error.

### T028 — Field-rejection negative tests

**Steps**: `tests/doctrine/test_relationship_fields_rejected.py` — parametrized over the kinds: a YAML/dict with the legacy field fails validation with the actionable message.

**Validation**: - [ ] each kind rejects the field; ruff/mypy clean.

## Definition of Done

- [ ] Relationship fields removed from all owned model files; keys rejected with an actionable message; negative tests green.
- [ ] CC-2 gates + bulk-edit gate (CC-5) pass. Built-in artifacts still load (because WP07 already migrated them) — run the doctrine load smoke to confirm NFR-005.

## Risks

- **Ordering hazard**: if this lands before WP07, built-in loads break. The dependency on WP07 enforces order; verify in `lanes.json` before starting.
- Do not edit `repository.py` (WP05) or any YAML data (WP07) — ownership boundaries.

## Reviewer Guidance (reviewer-renata)

- Confirm no relationship field remains on any owned model (grep).
- Confirm the rejection message points authors to DRG-fragment authoring.
- Confirm built-in doctrine still loads clean (NFR-005) given WP07 ran first.
