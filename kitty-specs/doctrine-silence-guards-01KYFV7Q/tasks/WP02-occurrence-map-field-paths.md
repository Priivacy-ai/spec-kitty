---
work_package_id: WP02
title: Occurrence-map field-path granularity
dependencies:
- WP01
requirement_refs:
- FR-002
- C-005
planning_base_branch: remediation/doctrine-silence-guards
merge_target_branch: remediation/doctrine-silence-guards
branch_strategy: Planning artifacts for this mission were generated on remediation/doctrine-silence-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/doctrine-silence-guards unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
phase: Phase 1 - Guards
history:
- at: '2026-07-26T19:45:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/bulk_edit/
create_intent:
- tests/specify_cli/bulk_edit/test_occurrence_map_field_paths.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/schemas/occurrence-map.schema.yaml
- src/specify_cli/bulk_edit/occurrence_map.py
- src/specify_cli/bulk_edit/diff_check.py
- src/doctrine/templates/occurrence-map-template.yaml
- tests/specify_cli/bulk_edit/test_occurrence_map_field_paths.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Occurrence-map field-path granularity

## ⚡ Do This First: Load Agent Profile

Load the `python-pedro` profile via `/ad-hoc-profile-load` and behave according to its guidance before parsing the rest of this prompt.

---

## Objectives & Success Criteria

- `do_not_change` can name a YAML **field path** inside a file that also carries migrating entries.
- Mission B2's real exemption set (188 GOVERNANCE + 14 RAW) is expressible.
- Legacy single-term maps keep validating unchanged.

**Requirement refs**: FR-002, C-005, SC-011

## Context & Constraints

The guardrail cannot currently express its own mission. `exceptions` are **path globs**, but **all 17** of B2's GOVERNANCE files also carry migrating entries and **5 of 7** RAW files do too — so no file-level cut separates them.

C-005 is why this is here and not in B2: deferring it converts a known defect into an invisible one, and letting B2 author its own guardrail would be self-validation.

**Binding, every WP in this mission:**

- **Never run the full `tests/architectural/` directory** (C-003) — a known harness issue kills the session. Targeted single-file runs only.
- The 6 inherited `arch-adversarial` reds stay red (C-004). No greenwashing, no retry-to-green.
- **ATDD (C-006)**: the failing test is the **first commit** of this WP, RED on the planning base and GREEN at the final commit.
- New code passes `ruff` and `mypy --strict` with zero issues. No `# noqa` / `# type: ignore` to get there.
- Charter: `.kittify/charter/charter.md`. Spec: `../spec.md`. Plan: `../plan.md`. Manifest: `../tasks.md`.

## Branch Strategy

- **Planning base branch**: `remediation/doctrine-silence-guards`
- **Merge target branch**: `remediation/doctrine-silence-guards` → draft PR to `main`; the operator merges.

## Subtasks & Detailed Guidance

### Subtask T006 – Failing-first test.

A field-path exemption in a mixed file is currently inexpressible. Prove it.

### Subtask T007 – Extend the schema.

Add field-path granularity to `occurrence-map.schema.yaml`. Keep `additionalProperties: false` discipline.

### Subtask T008 – Loader + admissibility.

`occurrence_map.py` — parse and validate the new form; keep `check_admissibility`'s standard-category totality.

### Subtask T009 – Diff compliance.

`diff_check.py` — honour field-path exemptions so the reviewer reviews exceptions, not a 169-file sweep.

### Subtask T010 – Template + docs.

Update `occurrence-map-template.yaml` with a worked field-path example.

### Subtask T011 – Backward compatibility.

Legacy single-term maps validate unchanged (C-OMAP-1). Prove with an existing committed map.

## Test Strategy

- `PYTHONPATH=src python -m pytest tests/specify_cli/bulk_edit/ -q`
- Round-trip B2's map at `kitty-specs/drg-edge-migration-extractor-retirement-01KYFV8C/occurrence_map.yaml`.

## Note on SC-011's demonstration

`owned_files` may not reference `kitty-specs/` paths, so B2's real `occurrence_map.yaml` cannot be
owned here. That does **not** license a throwaway fixture labelled "B2's exemption set" — which the
post-tasks squad flagged as this WP's cheapest fake. Instead: **read** B2's actual map and its real
exemption set (188 GOVERNANCE occurrences across 17 files, 14 RAW across 7) and assert the new schema
can express it. Mission B2 re-authors its own map against this schema before it implements.

Note the unit slip in SC-011's wording: "188 GOVERNANCE + 14 RAW" are **occurrences**, while the
inexpressibility argument is about **files** (17 and 7). Both matter; do not conflate them.

## Risks & Mitigations

- Breaking legacy maps is the main hazard — prove compatibility against a committed one, not a fixture.
- Do not add a second exemption mechanism alongside the existing one; extend it (single canonical authority).

## Review Guidance

- Verify red→green: the WP's first commit was RED on `remediation/doctrine-silence-guards` and is GREEN at the final commit.
- Verify every gate added is **non-vacuous**: it must reject a planted violation, and its allowlist must be empty.
- Verify the graph invariant where the WP claims it (311 nodes / 774 edges).

## Activity Log

> **CRITICAL**: entries in chronological order, oldest first. **Append** new entries at the END.

- 2026-07-26T19:45:15Z – system – Prompt created.
- 2026-07-27T01:00:00Z – claude – **Approved.** Formal approval was held on a cross-lane artefact, not on WP02's own content: `test_a_baseline_entry_does_not_survive_its_owner` fires on any lane where WP05 is `approved` (status is mission-global) but WP05's 8 baseline deletions are absent (files are lane-local, on lane-e). Diagnosis confirmed by direct measurement rather than assumed — the gate **passes on lane-e** and **fails on lane-b** with the same commit of WP01's checker. It resolves at lane consolidation, when status and files land together. Recorded here so a later reader does not mistake it for a WP02 defect or for the gate misbehaving.
