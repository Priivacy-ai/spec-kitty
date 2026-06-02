---
work_package_id: WP07
title: Migrate built-in relationships to fragments (zero-loss)
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-029
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts for this mission were generated on mission/org-doctrine-profile-integrity-activation-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
- T033
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/graph.yaml
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/doctrine/graph.yaml
- src/doctrine/tactics/built-in/**
- src/doctrine/styleguides/built-in/**
- src/doctrine/paradigms/built-in/**
- src/doctrine/procedures/built-in/**
- src/doctrine/agent_profiles/built-in/**
- docs/explanation/doctrine-relationships.md
- tests/doctrine/test_relationship_migration.py
- tests/doctrine/fixtures/relationship_packs/**
role: implementer
tags: []
---

# WP07 — Migrate built-in relationships to fragments (zero-loss)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## ⚠️ BULK-EDIT GATE

Governed by [../occurrence_map.yaml](../occurrence_map.yaml) — `serialized_keys` (remove the key from YAML, add the fragment edge) and `tests_fixtures` actions. Update the map's "as executed" notes in T033.

## Objective

Migrate every field-authored relationship in built-in doctrine (and shipped fixtures) from the `enhances`/`overrides`/`specializes_from` **fields** to **DRG fragment edges** in `graph.yaml`, with a **zero-loss** proof (NFR-007). Add lineage/augmentation fixtures and the FR-004 docs. This must land **before** WP06 makes the field a hard error.

## Context

- Spec: FR-001/003/004/029, NFR-007. Data model §3 (I-A1 zero-loss). Contract C2.2, C2.6.
- This is the data side of the hard cutover; WP04 provides the emission/validation path, WP02/WP03 provide the relation + merged DRG.

### Code map

- `src/doctrine/graph.yaml` — shipped DRG (destination for migrated edges).
- `src/doctrine/<kind>/built-in/*.yaml` — artifacts currently carrying the fields (grep `enhances:`/`overrides:`/`specializes_from:` to enumerate the exact set — do NOT trust counts; discover them).
- Emission/validation: `doctrine/drg/org_pack_loader.py` (post-WP04).

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP02, WP03, WP04.

## Subtasks

### T029 — Migrate built-in relationships to `graph.yaml` edges

**Steps**:
1. Grep all built-in artifact YAML for `enhances:`/`overrides:`/`specializes_from:`. Record the full occurrence set (feeds T031 + T033).
2. For each, add the equivalent typed edge to `src/doctrine/graph.yaml` (`relation: enhances|overrides|specializes_from`, source/target URNs) and **remove the key** from the artifact YAML.
3. Regenerate/validate the shipped graph if there is a generator (`DIRECTIVE_018` doctrine versioning — bump version metadata as required).

**Validation**: - [ ] no built-in artifact YAML contains the three keys (grep is empty); - [ ] `graph.yaml` validates.

### T030 — Lineage + augment-all-kinds fixtures

**Steps**: Under `tests/doctrine/fixtures/relationship_packs/`, add: a pack with a profile-to-profile `specializes_from` edge (Scenario 1); a pack authoring `enhances`/`overrides` edges on a directive, toolguide, mission-step-contract, and mission-type (Scenario 10); a negative `legacy-field-pack` still using the field form (for WP06's rejection test to reference).

**Validation**: - [ ] fixtures load/validate as intended (positive validate; legacy-field-pack will fail post-WP06).

### T031 — Zero-loss migration test (NFR-007)

**Steps**: `tests/doctrine/test_relationship_migration.py` — assert the set of relationships represented as merged DRG edges after migration equals the pre-migration field-authored set (count + identity diff). Use the occurrence set from T029 as the expected baseline.

**Validation**: - [ ] every pre-existing relationship has exactly one corresponding merged edge; zero loss.

### T032 — FR-004 relationship docs [P]

**Steps**: Write `docs/explanation/doctrine-relationships.md` explaining lineage (`specializes_from`) vs delegation (`delegates_to`) vs enhancement/override/replacement, with the canonical fragment-edge authoring example. Anchor to the `Relation` enum docstring (WP02) and DIRECTIVE_037 living docs.

**Validation**: - [ ] doc present, accurate, references the fragment-authoring model.

### T033 — Update occurrence map as executed

**Steps**: Fill the `serialized_keys` and `tests_fixtures` occurrence lists in `occurrence_map.yaml` with the concrete files touched (from T029/T030), each with decision + reason.

**Validation**: - [ ] occurrence map reflects the actual migration; bulk-edit gate satisfied.

## Definition of Done

- [ ] All built-in relationships live as `graph.yaml` edges; keys removed from artifact YAML; zero-loss test green; fixtures + docs added; occurrence map updated.
- [ ] Built-in doctrine loads with zero diagnostics (NFR-005) — run the load smoke.
- [ ] CC-2 + bulk-edit gates pass.

## Risks

- **Highest-risk data change.** The zero-loss test is the safety net — write it against the discovered occurrence set, not assumptions.
- Topology kinds (step-contract/mission-type): ensure migrated `enhances` edges preserve ordering semantics (coordinate with WP04 T018).
- `occurrence_map.yaml` is co-owned conceptually with WP06's `code_symbols`; only edit the `serialized_keys`/`tests_fixtures`/`user_facing_strings` sections here.

## Reviewer Guidance (reviewer-renata)

- Run the grep yourself: confirm zero remaining field occurrences in built-in YAML.
- Confirm the zero-loss test compares against the real occurrence set, not a hardcoded number.
- Confirm `graph.yaml` edge URNs are correct (source/target resolve to real nodes).
