---
work_package_id: WP05
title: '#2650 — classifier-only swap of commit_router onto the residue predicate (FR-005)'
dependencies:
- WP04
requirement_refs:
- C-004
- C-007
- FR-005
- NFR-001
- NFR-003
tracker_refs:
- '2650'
planning_base_branch: mission/2533-pr-bound-coord-claim-precondition
merge_target_branch: mission/2533-pr-bound-coord-claim-precondition
branch_strategy: Planning artifacts for this mission were generated on mission/2533-pr-bound-coord-claim-precondition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/2533-pr-bound-coord-claim-precondition unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2807328"
shell_pid_created_at: "1784125350.25"
history:
- at: '2026-07-15T07:36:38Z'
  actor: claude
  note: Classifier-only swap (squad RISK-3) — reuse the EXISTING residue predicate; no new cli-side partition_of; keep resolve_placement_only for the COORD ref.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- tests/specify_cli/coordination/test_commit_router_partition_authority.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/coordination/commit_router.py
- tests/specify_cli/coordination/test_commit_router_partition_authority.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration.
You are the **implementer**.

## Objective

Close the #2533 hole in the partition classifier (FR-005, partition half). Swap
`commit_router._group_files_by_partition`'s divergent `kind_for_mission_file(file) or kind`
classifier (`commit_router.py:404`) onto the **existing**
`mission_runtime.is_coordination_artifact_residue_path` predicate — the same authority the
other two sites already use — so `kind=None` routes PRIMARY (C-007) everywhere.

## Context — READ BEFORE CODING (scope correction, squad RISK-3)

- **Classifier-only.** Change ONLY how the per-file PRIMARY/COORD partition is decided.
  `commit_router` still needs its actual COORD ref (`other_ref`, `commit_router.py:416`) —
  **keep `resolve_placement_only` for the ref**; do NOT route ref resolution through the
  read-side helper.
- **Do NOT add a new cli-side `partition_of` wrapper.** It is redundant with the existing
  `is_coordination_artifact_residue_path`, and homing it in `cli/commands` would invert the
  `cli → coordination` layering (C-008). `mission_runtime/*` stays READ-ONLY. No net-new
  public symbol.
- **WP04's characterization gate is the contract.** The disagreement set is "non-coord path
  under a coord caller → PRIMARY". Make WP04's intended-contract assertions turn green.
- **C-004:** #2648 (WP01) + the #2533 regression stay green.

## Subtasks

### T023 — Swap the classifier

**NOT a one-line predicate substitution (squad RISK-4).** Today `_group_files_by_partition`
partitions **relative to the caller's kind** (`caller_is_primary`, `same_partition`/
`other_partition`, `other_kind` capture) and resolves `same_ref = resolve_placement_only(kind=kind)`
/ `other_ref = resolve_placement_only(kind=other_kind)`. Replacing the classifier with an
**absolute** residue split means reconciling that same/other-relative-to-caller ref machinery so
it can't invert refs when the caller is PRIMARY.

1. Replace the per-file `kind_f = kind_for_mission_file(file) or kind` +
   `is_primary_artifact_kind(kind_f)` classification with the residue predicate:
   `is_coordination_artifact_residue_path(file)` → COORD bucket, else PRIMARY bucket.
2. Make the buckets **absolute**: the PRIMARY bucket commits to the primary ref, the COORD
   bucket to the coord ref — both still resolved via `resolve_placement_only` (keep it for the
   refs; the swap is classifier-only). Do NOT leave the split relative to `caller_is_primary`.

**Validation**: `ruff` + `mypy --strict` clean; the split routes `kind=None`→PRIMARY; refs are
correct for BOTH a PRIMARY-caller and a COORD-caller batch (see T025).

### T024 — Structural test: the kind classifier is dropped for the split

Create `tests/specify_cli/coordination/test_commit_router_partition_authority.py`:
1. Assert `_group_files_by_partition` routes the `kind=None` set (`meta.json`, unrecognized)
   to PRIMARY.
2. Assert the split no longer consults `is_primary_artifact_kind(kind_for_mission_file(...))`
   (e.g. a path that the kind classifier would call COORD-by-caller now routes PRIMARY).
   Frame the assertion behaviorally so it survives rename churn.

**Validation**: the structural test is green and would fail if the kind classifier returned.

### T025 — Regressions + caller-is-PRIMARY behavior preservation

1. **Behavior-preservation for the caller-is-PRIMARY batch (RISK-4):** add an assertion that a
   PRIMARY-caller mixed batch still routes coord-residue paths to `other_ref` and primary paths
   to the primary ref (the disagreement-set test T024 is framed around a COORD caller and does
   NOT exercise this). Model it on the existing `test_commit_router_partition.py` /
   `test_commit_router_placement.py`.
2. Run the #2533 solo-coord repro (`test_implement.py::TestSoloPrBoundCoordMission…`),
   WP01's narrow-triple test, the 3 write-side `None` cases, and WP04's gate — all green.

**Validation**: caller-is-PRIMARY refs unchanged by the swap; all named regressions green.

### T026 — Gate clean

1. `ruff` + `mypy --strict` zero new issues; coordination suite green.

**Validation**: clean gate.

## Branch Strategy

Planning branch / final merge target: **mission/2533-pr-bound-coord-claim-precondition**.
Lane B (`commit_router.py`), after WP04. This is the commit_router half of FR-005; WP04
already did the cli-side characterization gate + read/write ref unification.

## Definition of Done

- `commit_router:404` routes partition through `is_coordination_artifact_residue_path`;
  `kind=None`→PRIMARY (FR-005, C-007). `resolve_placement_only` kept for the COORD ref.
- No new cli-side `partition_of`; `mission_runtime` untouched (C-008, boundary).
- Structural test (T024) pins the kind classifier is dropped for the split — the
  commit_router site of SC-004 (WP04 covers the cli-side sites).
- #2533 + #2648 + WP04 gate green (C-004, NFR-003); `ruff` + `mypy --strict` clean (NFR-001).

## Risks & Reviewer Guidance

- **Highest risk (paula BLOCKER-2 / C-007):** consolidating onto the kind classifier's
  caller-fallback would misroute `meta.json`→COORD and reintroduce #2533. Reviewer must
  confirm the residue predicate is the authority and the kind classifier is gone from the
  split.
- Confirm `other_ref` (COORD ref) still comes from `resolve_placement_only` — the swap is
  classifier-only, not ref-resolution.

## Activity Log

- 2026-07-15T13:59:26Z – claude:sonnet:python-pedro:implementer – shell_pid=2763252 – Assigned agent via action command
- 2026-07-15T14:18:15Z – claude:sonnet:python-pedro:implementer – shell_pid=2763252 – Ready for review: commit_router classifier→residue predicate; absolute buckets; caller-is-PRIMARY preserved
- 2026-07-15T14:22:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=2807328 – Started review via action command
- 2026-07-15T14:27:17Z – user – shell_pid=2807328 – Review passed: classifier-only swap correct — line 462 is_coordination_artifact_residue_path is the SOLE membership authority; kind classifier (kind_for_mission_file) now only feeds _representative_kind_for_bucket for ref resolution, never the split; kind=None→PRIMARY unconditionally (C-007). ABSOLUTE BUCKETS / NO REF INVERSION (RISK-4): primary_kind is always a primary-partition kind and coord_kind always a coord kind (caller's kind when it matches, else the expect_primary-cross-checked representative or a partition-correct fallback), so primary_files→primary ref and coord_files→coord ref for BOTH caller polarities — verified by TestCallerIsPrimaryBucketsStayAbsolute + end-to-end TestCommitForMissionEndToEndPrimaryCallerRefsNotInverted (status.events.jsonl→COORD ref under a PRIMARY caller). Zero-resolve single-partition fast path byte-preserved (calls==[] assertion). CROSS-WP FLIP LEGITIMATE: WP05 flipped only TestDisagreementSet...'s one method that WP04 pinned as the pre-fix #2533-class hole ('COORD today'→'PRIMARY now'); the path genuinely routes PRIMARY post-swap, the flip is documented with rationale in the class docstring, and NO other WP04 gate assertion weakened — INV-7 narrow-triple, cli-side kind=None→PRIMARY, _primary_ref_for shared-expression, and the AST no-xfail guard all intact. Adversarial stub test proves kind_for_mission_file's return can't override membership. Scope clean: only commit_router.py + new structural test + the permitted WP04 characterization edit; mission_runtime/transaction.py untouched; _representative_kind_for_bucket module-private, no new public symbol/partition_of (C-008). Gates: ruff clean, mypy --strict commit_router.py clean (11 pre-existing errors in other coordination modules, none in commit_router.py), 321 passed.
