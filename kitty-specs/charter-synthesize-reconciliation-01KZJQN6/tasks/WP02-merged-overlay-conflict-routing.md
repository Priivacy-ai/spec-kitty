---
work_package_id: WP02
title: Merged-overlay conflict routing (report, not crash)
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-014
planning_base_branch: fix/charter-synthesize-reconciliation
merge_target_branch: fix/charter-synthesize-reconciliation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-synthesize-reconciliation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-synthesize-reconciliation unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
phase: Phase 2 - Spine
history:
- timestamp: '2026-08-09T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/charter/synthesizer/
create_intent:
- tests/charter/synthesizer/test_synthesize_conflict_routing.py
execution_mode: code_change
mission_id: 01KZJQN68SWZ7T1YKGDB4Q4EVH
owned_files:
- src/charter/activation/synthesizer/validation_gate.py
- tests/charter/synthesizer/test_synthesize_conflict_routing.py
tags: []
tracker_refs: []
agent_profile: python-pedro
role: implementer
agent: claude
wp_code: WP02
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role:
implementer) before anything else. Then read `plan.md`, `research.md`, `data-model.md`, and
`contracts/synthesize-seam.md`, plus `src/doctrine/drg/merge.py` (the conflict model you will
reuse).

# Work Package Prompt: WP02 – Merged-overlay conflict routing (report, not crash)

## Objectives & Success Criteria

- Validate the **merged** (preserved + emitted) overlay. WP01 detects, classifies, and passes the
  conflicts in-memory; WP02 receives them via a **widened `validate()` signature** and performs the
  **suppress-vs-raise decision only**: a conflict caused by **preserved on-disk content** (duplicate
  `(source,target,relation)` triple, or a dangling edge endpoint) is **suppressed and reported**
  (surfaced through `delta.conflicts`) rather than raising an uncaught `ProjectDRGValidationError`.
- A conflict introduced by the **current emit** (`provenance == "new_emit"`) remains a hard error
  (unchanged behavior).
- No input that previously produced silent loss now produces a hard crash (NFR-003).
- **No sidecar**: the hand-off is in-memory (`ReconciliationDelta.conflicts` + widened signature);
  there is no `.reconcile-conflicts.json` staging file.
- **Traceability note (FR-006 split)**: FR-006 is split — **WP01 detects and classifies** conflicts
  (populating `delta.conflicts`); **this WP (WP02) routes** them (suppress preserved / raise
  new-emit). WP02 does not detect or classify.

## Context & Constraints

- **Why this exists** (research.md, squad finding): preserved nodes/edges bypass
  `emit_project_layer`'s additive-only guard, then hit `merge_layers` (`loader.py:189` concatenates
  edges) + `validate_graph` (`validator.py:209-237` hard-fails on dup triple / dangling endpoint).
  Without routing, WP01's preservation turns silent loss into a crash-and-trap.
- **Model after the DRG shape — do NOT reuse `merge.py` (C-001, FR-014)**: the
  `ReconciliationConflict` object and its remediation vocabulary live in `reconcile.py` (WP01),
  **modeled after** the DRG typed-conflict shape. `src/doctrine/drg/merge.py`
  (`OrgDRGConflict`/`_CONFLICT_REMEDIATIONS`) is the org-pack fragment-merge subsystem — a closed
  `kind` Literal with no `duplicate_triple`, no `backing_artifact`/`remediation` — and is neither
  reused nor edited. Reconciliation `kind`s are distinct (`duplicate_triple`,
  `preserved_dangling_endpoint`). Every reported class carries a remediation line, from
  `reconcile.py`'s own set (WP01 adds the completeness test mirroring
  `test_every_conflict_class_carries_a_remediation_line`).
- **Scope boundary**: you own `validation_gate.py`. `reconcile.py` (types + remediation vocabulary),
  the seam, conflict **detection + classification**, and `delta.conflicts` population are WP01's;
  the structured duplicate/dangling helpers (`duplicate_edge_triples` / `dangling_endpoints`) are
  extracted by WP01 in `src/doctrine/drg/validator.py` as the shared SSOT — consume them, do NOT
  re-implement the checks in `validation_gate.py`. Do not modify `orchestrator.py`,
  `project_drg.py`, `reconcile.py`, or the CLI.

## Subtasks & Detailed Guidance

### Subtask T007 – Validate the merged overlay
- **Purpose**: Ensure validation sees the merged overlay WP01 produced, not only the emitted set.
- **Steps**: In `validation_gate.validate`, confirm the staged overlay being validated is the
  merged one (WP01 persists merged before validation). Where validation currently assumes an
  emit-only overlay, adjust to operate on the merged staged graph.

### Subtask T008 – Receive WP01's classified conflicts (widened signature)
- **Purpose**: Consume the emitted-vs-preserved partition WP01 already computed — do NOT re-derive
  it and do NOT parse `validate_graph` strings.
- **Steps**: **Widen `validate()`'s signature** to accept the classified conflicts (the
  `ReconciliationConflict` list, or the preserved/new-emit partition) that WP01 populates on the
  delta in-memory. WP01 changes the call site to pass them; you change the signature. There is no
  `.reconcile-conflicts.json` sidecar to read.

### Subtask T009 – Suppress preserved / raise new-emit (decision only)
- **Purpose**: Report preserved conflicts; hard-fail new-emit conflicts. `delta.conflicts` is
  **populated by WP01** — this WP only decides suppress-vs-raise.
- **Steps**:
  - `provenance == "preserved"`: **suppress** the `validate_graph` hard-fail for that offending
    triple/endpoint and let the run continue (the conflict is already reported on
    `delta.conflicts`; the CLI/boundary decides presentation). Do **not** raise.
  - `provenance == "new_emit"` (or any conflict not classified preserved): raise
    `ProjectDRGValidationError` as today (unchanged).
- **Notes**: keep the additive-only guard in `emit_project_layer` intact for the emit set; this WP
  only changes how *preserved-content* conflicts surface. Match preserved conflicts to the
  `validate_graph` surface by `target_id` (the offending triple/endpoint), not by string parsing.

### Subtask T010 – Tests
- New `tests/charter/synthesizer/test_synthesize_conflict_routing.py`:
  - **Preserved duplicate-triple**: inject an on-disk edge whose triple duplicates a built-in
    edge → synthesize preserves and **reports** it in `delta.conflicts`; no exception.
  - **Preserved dangling endpoint**: inject an on-disk edge whose target URN is absent from the
    current built-in snapshot → **reported**, not raised; graph not silently truncated.
  - **New-emit collision still raises**: a current target colliding with a built-in URN/edge →
    `ProjectDRGValidationError` (regression guard that the additive guard still bites for emit).
    **Fixture note**: the new-emit-collision case synthesizes a fresh target set — the
    `FixtureAdapter` is inputs-hash-keyed and RAISES on a miss, so record/add the matching fixture
    under `tests/charter/fixtures/synthesizer/**` for that target before asserting the raise.
  - Assert each reported conflict class carries a non-empty remediation.

## Branch Strategy

- Planning-base / merge-target: `fix/charter-synthesize-reconciliation` (PRs into `main`).
- Depends on WP01; run `spec-kitty agent action implement WP02 --agent <name>` after WP01 is
  approved/done. Execution worktree per computed lane from `lanes.json`.

## Definition of Done

- [ ] Preserved-content conflicts are reported (typed shape + remediation), not raised.
- [ ] New-emit collisions still hard-fail.
- [ ] Conflict-routing tests green; no new uncaught-exception path on divergent inputs.
- [ ] `ruff` + `mypy` clean; complexity ≤ 15.

## Risks & Reviewer Guidance

- **Risk**: mis-attributing provenance (reporting a real new-emit collision, or crashing on a
  preserved one). Reviewer: check the emitted-vs-preserved set derivation and both test branches.
- **Risk**: dangling endpoints from a since-removed built-in node — ensure these are reported with
  an actionable remediation, not silently dropped.

## 🔴 Post-tasks squad amendments (MUST READ before implementing)

1. **[BLOCKER] Consume WP01's classified conflicts via a WIDENED `validate()` signature (in-memory,
   NO sidecar).** WP01 detects, classifies (`provenance`), and populates `delta.conflicts` in
   memory, then passes the conflicts (or the preserved/new-emit partition) into `validate()` at the
   call site it owns. **Widen `validate()`'s signature** to accept them — there is NO
   `.reconcile-conflicts.json` staging file to read (filesystem IPC inside one in-process
   `synthesize()` call would contradict the in-memory contract-of-record). For an offending
   edge/node whose conflict is `provenance == "preserved"`, **suppress the `validate_graph`
   hard-fail** (it is already reported on `delta.conflicts`); for `new_emit` (or any conflict not
   classified preserved), raise `ProjectDRGValidationError` as today. You do NOT re-derive
   provenance and you may not edit `orchestrator.py`.
2. **[BLOCKER] Remediation vocabulary + kind names come from `reconcile.py` (WP01), not `merge.py`.**
   The reconciliation `kind`s are `duplicate_triple` and `preserved_dangling_endpoint` — DISTINCT
   from `merge.py`'s closed-`Literal` `unresolved_edge_endpoint` (no name-collision on a forked
   string). `src/doctrine/drg/merge.py` has no `duplicate_triple` key and is a different subsystem;
   use the reconciliation remediation set WP01 defines. Every reported class must carry a non-empty
   remediation line.
3. **[SSOT] Structured duplicate/dangling detection lives in `src/doctrine/drg/validator.py`.**
   `validator.py` already exposes `validate_dangling_references` / `_validate_duplicate_edges`
   ("Exposed rather than copied so there is one definition of 'dangling'"). The structured helpers
   `duplicate_edge_triples(graph) -> list[DRGEdge]` and `dangling_endpoints(graph) -> list[DRGEdge]`
   are extracted **in `validator.py`** so BOTH `validate_graph` (string formatting) and `reconcile.py`
   (provenance classification, WP01) consume one definition. **Do NOT re-implement these checks in
   `validation_gate.py` or fork them into `reconcile.py`.** (Placement note: the extraction is
   performed by WP01 — the first consumer and the mission foundation — because WP02 depends on WP01;
   WP02 relies on the extracted helpers rather than owning them. See WP01 amendment #3.)
