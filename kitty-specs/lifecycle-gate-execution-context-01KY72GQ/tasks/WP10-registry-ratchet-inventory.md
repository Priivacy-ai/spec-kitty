---
work_package_id: WP10
title: Exemption registry + anti-ninth ratchet + enrolment inventory + cross-gate agreement
dependencies:
- WP09
requirement_refs:
- FR-012
- FR-013
- NFR-006
- NFR-008
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T053
- T054
- T055
- T056
- T057
- T058
phase: Phase 7 - Ratchet & Registry
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_exemption_registry_ratchet.py
create_intent:
- tests/architectural/test_exemption_registry_ratchet.py
- tests/architectural/test_cross_gate_churn_agreement.py
- tests/architectural/tool_artifact_enrolment/inventory.md
- tests/architectural/tool_artifact_enrolment/test_enrolment_inventory.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- tests/architectural/test_exemption_registry_ratchet.py
- tests/architectural/test_cross_gate_churn_agreement.py
- tests/architectural/tool_artifact_enrolment/inventory.md
- tests/architectural/tool_artifact_enrolment/test_enrolment_inventory.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP10 – Registry, ratchet, enrolment inventory & cross-gate agreement

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Land the **stall countermeasure** (R-017) EARLY — second in the owner track, **before any retirement**: an enumerated exemption registry with a negative structural scan, the anti-ninth ratchet, the tool-artifact enrolment inventory, and the cross-gate agreement test (RED on base). Each later retirement WP deletes its own registry row (red→green), and a stall at any point leaves the codebase strictly better than found.

**Done** = owner contract C1/C7/C8/C9 pass; the registry is pre-populated with every mechanism (expected-present); the cross-gate test is RED on base.

## Context & Constraints

- Plan IC-08; owner contract C1/C7/C8/C9; spec FR-013, NFR-006, NFR-008 (amended).
- **Mode: enumerated registry ROWS, NOT a golden count.** Golden-count mode was explicitly rejected (it reinstates the hand-derived oracle R-012 repudiated, makes all retirement WPs co-own one file, and collides with the golden-count ban gate). Keep the scan **negative** (assert nothing exists outside the shrinking registry); never a positive literal count.
- **NFR-008 amended**: this is the single permitted structural test — negative, registry-backed, for an inherently structural property.
- **Registry rows** (derived by rule R-014 — *every frozenset/tuple/compiled-regex of filenames/basenames/suffixes/path-prefixes consulted by a dirty-state or churn-classification predicate*): the 8 original symbols + the 4 R-014 additions. Enumerate all (≥11), initially expected-present. See `tool-artifact-owner.md` C5.
- **Explicitly NOT a row**: the non-`pending` preservation branch in `matrix.py` (a state guard, not a filename match; NI-2 pins it; NFR-004 forbids regressing it).

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T053 – Exemption registry (negative scan)

- **Steps**: Enumerate every mechanism (≥11) as an explicit registry row, each expected-present. **Structure the registry as one row artifact per mechanism** (e.g. a per-mechanism row file under `tests/architectural/tool_artifact_enrolment/registry/`, which you own), so a retirement WP deletes **only its own** mechanism's row without touching a file a sibling retirement also edits — this is what makes the `[P]` retirements (WP15/WP16) and WP17 genuinely collision-free (squad finding), and it honors the plan's stated reason for rejecting golden-count mode ("makes all retirement WPs co-own one file"). A negative structural scan over the R-014 derivation rule asserts no such mechanism exists **outside** the enumerated rows, and the registry only shrinks. Add the per-mechanism row files to this WP's `create_intent` when you materialize them.

### Subtask T054 – Anti-ninth ratchet (C9)

- **Steps**: Adding a new filename-based exemption to any dirty-state gate fails the suite and the failure **names the owner** as the supported route. Pin a behavioural invariant, not a literal source scan.

### Subtask T055 – Enrolment inventory (owner C1)

- **Steps**: A tool-derived inventory of generated-write sites that self-asserts in BOTH directions (no discovered sink missing; no row without a live sink). **Clone `tests/architectural/untrusted_path_audit/`** — the undercount arm + overcount/ghost arm + drift-proof composite key. Never hand-write the list.

### Subtask T056 – Cross-gate agreement (owner C7, RED on base)

- **Steps**: Same corpus of paths → every churn-classifying gate returns the identical classification. This goes RED on base: `merge/git_probes.py:173` exempts a tracked-modified `meta.json` via `is_self_bookkeeping_path` while `git/ref_advance.py` never consults it (its `excluded_filenames` escape applies only to untracked entries). That disagreement is the #2795 repro — red-first for WP11/WP13.

### Subtask T057 – C-006 registration

- **Steps**: Register the new architectural test file(s) with the shard map / shard registry. Keep NEGATIVE (absence outside registry); avoid the golden-count-ban collision.

### Subtask T058 – C8 rename-invariance

- **Steps**: C8a — same bytes+kind written to a different basename → classification unchanged. C8b — an operator-authored file whose basename collides with a generated artifact's basename → NOT classified as generated. A filename-based classifier cannot pass either arm.

## Test Strategy

- New: `tests/architectural/test_exemption_registry_ratchet.py`, `tests/architectural/test_cross_gate_churn_agreement.py`, `tests/architectural/tool_artifact_enrolment/`.
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/architectural/test_exemption_registry_ratchet.py tests/architectural/test_cross_gate_churn_agreement.py -q` (the cross-gate one RED until WP11/WP13).

## Risks & Mitigations

- Structural by necessity — keep it negative and registry-backed, never a positive count (NFR-008).
- File-disjoint (tests only) → parallel with the retirement chain's start.

## Review Guidance

- Confirm the registry is enumerated (not a count) and only shrinks.
- Confirm the cross-gate test is genuinely RED on base (red-first).
- Confirm the enrolment inventory self-asserts both directions and is tool-derived.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
