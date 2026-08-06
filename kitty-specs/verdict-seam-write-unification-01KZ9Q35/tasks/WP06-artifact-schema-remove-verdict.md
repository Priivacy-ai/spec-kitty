---
work_package_id: WP06
title: 'Artifact schema: remove verdict field + census resolver retirements'
dependencies:
- WP05
requirement_refs:
- FR-001
- FR-003
- FR-006
- FR-007
- FR-011
planning_base_branch: feat/verdict-seam-write-unification
merge_target_branch: feat/verdict-seam-write-unification
branch_strategy: Planning artifacts for this mission were generated on feat/verdict-seam-write-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verdict-seam-write-unification unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
- T033
- T034
- T035
- T055
history: []
agent_profile: python-pedro
authoritative_surface: tests/review/test_artifacts_no_verdict_field.py
create_intent:
- tests/review/test_artifacts_no_verdict_field.py
- tests/coordination/test_verdict_dir_co_resolution.py
execution_mode: code_change
owned_files:
- tests/coordination/test_analysis_report_rehome.py
- tests/review/test_artifacts_no_verdict_field.py
- tests/coordination/test_verdict_dir_co_resolution.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned profile: run `/ad-hoc-profile-load python-pedro` (or
`spec-kitty charter context --action implement`). Do not start work until the profile is loaded.

## Objective

Make single-authority **structural**: remove the `verdict` field from `ReviewCycleArtifact` so the
written `review-cycle-N.md` physically cannot carry a verdict (SC-007). Discharge the census resolver
retirements, re-express `_guard_feedback_source_provenance` without a verdict read-back, and reconcile
the FR-011 docstring + FR-007 fallback wording. This lands in the **same PR / lane as WP05** — it edits
WP05-owned `review/artifacts.py` + `review/cycle.py` as same-lane continuation (out-of-map, rationale
below), and owns only its two test files.

## Context

- **Requirements**: FR-003 / SC-007 (artifact carries no verdict field), FR-006 (5 resolver-retire + 3
  unrouted + 2 raw-join census rows), FR-007 (fallback re-scoped to the write/prose-locate seam;
  location gate concrete), FR-011 (stale `cycle.py:70-77` docstring); SC-001, SC-007.
- **Decisions**: **D-PLAN-12** (SC-007 is a **schema change** — remove the field from the dataclass,
  `to_dict`, and `from_dict`/`validate_review_artifact` validation — **plus** a new serialized-artifact
  assertion; the parser-family retirement in WP05 must precede the field removal or `from_dict` breaks),
  **D-PLAN-5** (`_guard_feedback_source_provenance` re-expressed without a verdict read-back),
  **D-PLAN-16** (IC-04's physical write-partition flip is **largely subsumed** — the commit is already
  COORD; whether to additionally relocate the on-disk write, re-pinning `test_analysis_report_rehome:232`,
  is a narrow call, **not** a mission guarantee).
- **Ownership (out-of-map, rationale)**: `review/artifacts.py` + `review/cycle.py` are **WP05-owned**.
  WP06 depends on WP05 and edits them as **same-lane continuation** (WP05's parser retirement lands
  first, then WP06 removes the field). This is the ownership-map-leeway pattern — no concurrent writer
  because WP06 strictly follows WP05. WP06's `owned_files` are only its two test files.
  > Alternative considered: fold WP06 into WP05. Kept separate so the schema change and its new
  > serialized-artifact assertion are independently reviewable; flagged to the orchestrator.

Verified anchors: `artifacts.py:148` `verdict: str` field; `:179` `to_dict` emits `"verdict"`;
`:214-216` `from_dict` hard-validates it.

## Subtasks

### T030 — Red-first: serialized-artifact carries no verdict key (SC-007)
- **Purpose**: The structural single-authority anchor. Parse a **written** `review-cycle-N.md` and
  assert it has **no** `verdict` key (D-PLAN-12 — this is a serialized-field assertion, NOT the census,
  which classifies functions).
- **Steps**: In new `tests/review/test_artifacts_no_verdict_field.py`: (a) write an artifact via the
  real path and assert the on-disk frontmatter has **no** `verdict` key; (b) **also gate the schema
  directly (squad #12)** — assert `from_dict`/`validate_review_artifact` **no longer requires** a
  `verdict` key (a payload without `verdict` deserializes cleanly) **and no longer accepts** it as an
  authoritative field (a stray `verdict` in the payload is ignored/rejected per the chosen semantics,
  not stored as authority). Red against the current schema.
- **Files**: `tests/review/test_artifacts_no_verdict_field.py`.
- **Validation**: fails before T031; green after — both the serialized-output check and the
  `from_dict`/`validate` input check.

### T031 — Remove the `verdict` field from the dataclass + `to_dict` + `from_dict` validation
- **Purpose**: FR-003 / SC-007 schema change (D-PLAN-12).
- **Steps**: Out-of-map edit `review/artifacts.py`: drop `verdict` from the `ReviewCycleArtifact`
  dataclass (`:132`/`:148`), from `to_dict` (`:179`), and remove the `verdict` requirement/validation in
  `from_dict`/`validate_review_artifact` (`:214-216`, `:241`) so a payload without `verdict` deserializes
  cleanly (T030 input check). This is safe now because WP05 already retired the **verdict** parser
  functions (`.latest`/`.from_file` are kept — do not touch them). Update `REVIEW_ARTIFACT_VERDICTS`
  usage if it becomes dead.
- **Files**: out-of-map `src/specify_cli/review/artifacts.py`.
- **Validation**: T030 (both checks) green; no importer references the removed field (grep).

### T032 — Re-express `_guard_feedback_source_provenance` without a verdict read-back
- **Purpose**: D-PLAN-5 — the #990/#2996 duplicate-feedback guard parses `feedback_source` as an
  artifact; with no verdict field it must check prose identity without a verdict read-back (or retire if
  the event authority fully covers it).
- **Steps**: Out-of-map edit `review/cycle.py` (`_guard_feedback_source_provenance`, ~`:380`): re-express
  to prose-identity, add its own test. Resolve the design fork here (spec FR-003), do not leave it open.
- **Files**: out-of-map `src/specify_cli/review/cycle.py` + a test in `tests/review/`.
- **Validation**: byte-identical recurring-defect re-report stays admissible (spec edge case).

### T033 — Census resolver retirements (FR-006): 5 retire + 3 unrouted + 2 raw-join rows
- **Purpose**: FR-006/C-004 — name the modules from `verdict_seam_census.yaml` `status: retire`.
- **Steps**: Out-of-map edit WP01's `verdict_seam_census.yaml`: discharge the 5 resolver retire rows,
  the 3 unrouted sites, and the 2 raw-join re-homes with `retiring_fr`. Serial after WP05 (safe). Ensure
  the derived active set == fixture (G3).
- **Files**: out-of-map `tests/architectural/verdict_seam_census.yaml`.
- **Validation**: `pytest tests/architectural/test_verdict_seam_census.py -q` green.

### T034 — FR-007 LOCATION gate (real artifact) + FR-011 docstring + fallback wording
- **Purpose**: FR-007 requires a **concrete location gate**, not prose reconciliation (squad #11), plus
  the FR-011 doc-hygiene.
- **Steps**:
  1. **FR-007 LOCATION gate (owned artifact)** — add a test in a WP06-owned file
     (`tests/coordination/test_verdict_dir_co_resolution.py`) that parses `doctor review-cycle-reconcile
     --json` (an informational, exit-0 command) and **asserts zero `live_coord_pre_adr_primary_record`
     findings**. This is the FR-007 location gate as a real, runnable artifact — distinct from WP02's
     *provenance* predicate (D-PLAN-15). If the reconcile-doctor surface does not yet emit that class,
     point the test at the pre-existing finding key and fail loudly if it is missing (do not discharge
     FR-007 by prose alone).
  2. Out-of-map edit `review/cycle.py:70-77` docstring — the merge gate does **not** opt into
     `REVIEW_CYCLE` (FR-011).
  3. Reconcile the FR-007 wording: `_review_cycle_wp_dir` is `status: retire`, so the COORD→PRIMARY
     exception-absorption fallback is **relocated** into the canonical placement resolver (not
     "preserved verbatim"); its rationale is re-scoped to the surviving write/prose-locate seam.
- **Files**: `tests/coordination/test_verdict_dir_co_resolution.py`; out-of-map `src/specify_cli/review/cycle.py`.
- **Validation**: the location-gate test asserts zero `live_coord_pre_adr_primary_record`; docstring
  matches behaviour; `test_no_legacy_terminology.py` green.

### T035 — Physical-flip decision + `test_analysis_report_rehome` (SC-001, narrow)
- **Purpose**: D-PLAN-16 — decide whether to additionally relocate the on-disk `.md` write to COORD for
  prose-consistency (re-pinning `test:232`) or leave it (already green; commit is COORD via per-file
  classifier). This is a `/tasks`-level call, **not** a mission guarantee.
- **Steps**: Own `tests/coordination/test_analysis_report_rehome.py`. If relocating, re-pin the physical
  path and update the test; if not, keep it green and record the decision in the WP note. Either way,
  assert SC-001 (one identical directory resolved by every path) via the existing co-resolution surface.
- **Files**: `tests/coordination/test_analysis_report_rehome.py`.
- **Validation**: `pytest tests/coordination/test_analysis_report_rehome.py -q` green; decision recorded.

### T055 — Deliver SC-001's two verifications as real artifacts (squad #3, FR-001)
- **Purpose**: SC-001 names **two** verifications that were previously unowned (squad #3) — deliver both
  as runnable tests, not "keep the already-green test green." WP06 owns the resolver retirements, so it
  is the right home.
- **Steps**: In new `tests/coordination/test_verdict_dir_co_resolution.py`:
  1. **US2 multi-consumer co-resolution test** — under a materialized coordination topology, record a
     verdict and assert the write, the safety verdict reader, the approval probe, the allocator, the
     pointer resolver, and the fix-mode sites all resolve the **same** COORD directory (and the same one
     PRIMARY directory under `SINGLE_BRANCH`/`LANES`).
  2. **AST invariant** — assert **no** consumer resolves a review-cycle path from a caller-supplied
     directory or at a `kind` different from the safety-critical reader. Add a synthetic-poison arm (a
     fake consumer resolving at a divergent `kind` / from a caller dir) that reds the invariant
     (non-vacuity).
- **Files**: `tests/coordination/test_verdict_dir_co_resolution.py`.
- **Validation**: both checks green on the real tree; the poison arm reds. (This file also hosts the
  FR-007 location gate from T034.)

## Branch Strategy note

`already-confirmed`; base == target. Prepare with `spec-kitty implement WP06`. Depends on WP05 (must
land after the parser retirement); same lane as WP05 for the shared `artifacts.py`/`cycle.py` edits.
Serial in the census chain (after WP05).

## Definition of Done

- SC-007: the written `.md` carries no verdict field **and** `from_dict`/`validate` no longer
  requires/accepts it (T030/T031).
- SC-001: **both** verifications delivered as real artifacts (T055) — the US2 multi-consumer
  co-resolution test **and** the AST invariant (no caller-supplied dir / no divergent `kind`), each
  with a poison arm. The FR-007 location gate (T034) asserts zero `live_coord_pre_adr_primary_record`.
- FR-006 resolver retirements discharged with matching census rows (T033); FR-011 docstring + FR-007
  wording reconciled (T034); `_guard_feedback_source_provenance` re-expressed (T032).
- Gate: `pytest tests/review/test_artifacts_no_verdict_field.py
  tests/coordination/test_verdict_dir_co_resolution.py tests/coordination/test_analysis_report_rehome.py
  tests/architectural/test_verdict_seam_census.py -q` green; `ruff` + `mypy --strict src/specify_cli/review`
  clean (NFR-003); `test_no_legacy_terminology.py` green.

## Risks

- **`from_dict` breakage** — removing the field before WP05's parser retirement lands would break
  deserialization; the WP05 dependency prevents this (D-PLAN-12).
- **Durability-matrix `.verdict` reads** — the field removal may red `.verdict` reads in
  `test_review_durability_matrix.py` (WP05-owned, already re-pointed in WP05 T028); coordinate — if a
  residual `.verdict` read survives, flag it to WP05 rather than re-pinning the WP05-owned file here.

## Reviewer guidance

Confirm the no-verdict-key assertion is on a **serialized** artifact, not the census (D-PLAN-12).
Confirm WP05's parser retirement landed first. Confirm the fallback is described as **relocated**, not
"verbatim" (FR-007). Confirm the physical-flip decision is explicitly recorded.
