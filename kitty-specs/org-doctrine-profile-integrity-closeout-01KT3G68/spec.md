# Org Doctrine Profile Integrity — Review Close-Out

**Mission ID**: `01KT3G68VNA6QF8GKXDA40H8VD`
**Mission slug**: `org-doctrine-profile-integrity-closeout-01KT3G68`
**Mission type**: software-dev
**Base / Target / Coordination branch**: `mission/org-doctrine-profile-integrity-activation-closure` (all three — this is a stacked close-out; it does **not** fork from or merge to `main`)
**Parent mission**: `org-doctrine-profile-integrity-activation-closure-01KT1TV1`
**Source of record**: [`../org-doctrine-profile-integrity-activation-closure-01KT1TV1/adversarial-review-debrief.md`](../org-doctrine-profile-integrity-activation-closure-01KT1TV1/adversarial-review-debrief.md) — findings I-1..I-12.

---

## Overview

The parent mission (org-doctrine profile integrity / charter activation / template discovery) implemented all 36 FRs and is wired to live paths with exemplary test quality, but a 4-reviewer adversarial review (reviewer-renata, architect-alphonso, debugger-debbie, python-pedro) surfaced **12 findings** that must be closed before the parent mission merges. This close-out mission remediates them **on the parent's own branch** so the parent work and its hardening land as one coherent change.

Two findings block merge: a **core-objective functional regression** (`doctor doctrine` can still report a pack HEALTHY when a profile is invalid — the very class #1584 set out to kill) and a **CI-visibility regression** (five new mission test files are invisible to the marker-filtered CI gates). The remainder are type-safety, architectural boundary hygiene, operator-trust, completion-proof, and documentation-accuracy fixes. Three findings share the parent mission's own anti-pattern — *"a thing reported done/healthy when it isn't"* — and are treated as one trust-surface hardening pass.

This mission makes **no new feature changes**; it only hardens, corrects, documents, and proves the parent mission's work.

---

## User Scenarios and Testing

### Scenario 1 — `doctor doctrine` never reports a pack healthy while a profile is invalid (I-1, I-9)
An operator runs `spec-kitty doctor doctrine --json` against a project whose org pack contains a profile with a forbidden inline-reference field (e.g. `tactic_refs`). The report MUST show `healthy: false`, surface the offending profile (path, id, error summary), and MUST NOT hide the rest of the profile surface. The skip-vs-propagate contract for inline-reference rejection MUST be consistent across the code and its documentation.

### Scenario 2 — The mission's tests actually run in CI (I-2)
A maintainer runs the marker-filtered CI profiles (`-m fast`, `-m contract`, `-m architectural`). Every test file authored by the parent mission carries a `pytestmark`, so the flagship contract tests execute and `tests/architectural/test_pytest_marker_convention.py` passes.

### Scenario 3 — Type gate is clean on mission-authored code (I-3)
`mypy --strict src/doctrine/drg/merge.py` reports zero errors.

### Scenario 4 — Runtime→charter→doctrine boundary is honored without unnecessary exceptions (I-4)
The charter CLI commands reach doctrine only through charter facades. `tests/architectural/test_runtime_charter_doctrine_boundary.py` passes with `_BASELINE_ALLOWLIST` back at 0; `_baselines.yaml` reflects 0.

### Scenario 5 — Activation/cascade operator output is coherent (I-5)
`charter activate <kind> <id> --cascade all` (and the deactivate equivalent) produce a single coherent message; the stale "cascade not yet implemented / deferred" warnings are gone while cascade behaves correctly.

### Scenario 6 — Completion-proof artifacts match reality (I-6, I-7)
The parent mission's dead-symbol completion claim (its final FR) is true (no stale/redundant re-export masking), and `acceptance-matrix.json` records real per-FR acceptance criteria + the test IDs that prove them, with a non-pending `overall_verdict`.

### Scenario 7 — Living documentation is synced (I-8)
`CLAUDE.md` describes the charter activation/cascade model, the canonical kind vocabulary, and the `specializes_from` lineage relation.

### Scenario 8 — Quality debt and pre-existing failures are tracked, not silently inherited (I-10, I-11, I-12)
Deferred quality items carry trackers; pre-existing architectural failures (legacy `ceremony` term, two `git_repo` marker gaps) have a referenced issue per DIRECTIVE_013.

---

## Functional Requirements

| ID | Requirement | Source finding | Severity |
|----|-------------|----------------|----------|
| FR-001 | An inline-ref-invalid profile MUST make `doctor doctrine` report `healthy: false`, surface that profile (`{path, id, error_summary}` with a clear readable error), and **exit RC=1** (operator preference: loud RC=1 over hidden RC=0), while **valid sibling profiles (same pack, other packs, built-in layer) remain visible**. (Fix at the load layer — `repository._load_layer` → `_record_skip` — since loading is eager/all-or-nothing; a consumer-only catch cannot keep valid profiles visible.) | I-1 | HIGH |
| FR-002 | A new integration test MUST drive `doctor doctrine` against an org profile carrying a forbidden inline-ref field and assert `healthy: false` + the profile is surfaced (the currently-missing `_collect_profile_health` seam). | I-1 | HIGH |
| FR-003 | The inline-reference-rejection contract (skip vs propagate) MUST be consistent: `diagnostics.py` documentation and `repository.py` behavior/comments agree. | I-9 | LOW |
| FR-004 | Every test file authored by the parent mission MUST declare a module-level `pytestmark`; `test_pytest_marker_convention` passes. (Known files: `test_kind_vocabulary.py`, `test_operational_context.py`, `test_drg_merge.py`, `test_relationship_migration.py`, `test_operational_context_wiring.py`.) | I-2 | HIGH |
| FR-005 | `src/doctrine/drg/merge.py` MUST pass `mypy --strict` (make `_tag_source` generic over `BaseModel`). | I-3 | HIGH |
| FR-006 | The charter CLI commands (`activate.py`, `list_cmd.py`) MUST import doctrine symbols only through charter facades; add a `charter.template_catalog` re-export facade for `discover_templates`/`TemplateRef`/`TierRoot`. | I-4 | MEDIUM |
| FR-007 | `_BASELINE_ALLOWLIST` in `test_runtime_charter_doctrine_boundary.py` MUST return to 0 and `_baselines.yaml` MUST record 0; the boundary + ratchet gates pass. | I-4 | MEDIUM |
| FR-008 | The activation/deactivation CLI MUST NOT emit "cascade not yet implemented / deferred" warnings (delete **both** stale `pack_manager` branches — passing `cascade=False` does not work); a test asserts the string is absent from both activate AND deactivate `--cascade` output, and the existing `test_activate_cascade_calls_with_true` / `test_activate_cascade_flag_accepted` are updated to the new contract. | I-5 | MEDIUM |
| FR-009 | The parent mission's dead-symbol completion claim MUST be accurate: redundant `events.py` re-exports masking real callers are removed (or the claim is scoped precisely), and `test_no_dead_symbols` reflects the true surface. | I-6 | MEDIUM |
| FR-010 | `kitty-specs/<parent>/acceptance-matrix.json` MUST be populated with real per-FR acceptance criteria and the proving test IDs; `overall_verdict` is set (not `pending`). | I-7 | MEDIUM |
| FR-011 | `CLAUDE.md` MUST gain a section covering the charter activation/cascade model, the canonical kind vocabulary, and the `specializes_from` lineage relation. | I-8 | MEDIUM |
| FR-012 | The `doctor.py` health-render helpers SHOULD move beside `_doctrine_health.py` (or a `doctor/_health_render.py`) to arrest god-module growth, OR a tracker is filed if deferred. | I-10 | LOW |
| FR-013 | The `provenance` sidecar on frozen DRG models SHOULD be expressed via a typed wrapper / declared field (removing the `object.__setattr__` monkey-patch), OR a tracker is filed if deferred. | I-11 | LOW |
| FR-014 | A tracker issue MUST be filed for the pre-existing architectural failures (legacy `ceremony` term in `guidelines.md`; two `git_repo` marker gaps) per DIRECTIVE_013, referenced from the baseline. | I-12 | LOW |

## Non-Functional Requirements

- **NFR-001** No regression to the parent mission's 36 FRs: the full `tests/charter/ tests/doctrine/ tests/specify_cli/ tests/architectural/` suites stay green. (The gate root is `tests/specify_cli/` — not just `.../cli/commands/charter/` — so the flagship I-1 test and the FR-009 events check are inside the gate — review P-1.)
- **NFR-002** This close-out introduces no new dead symbols, no new boundary-allowlist growth, and no new architectural-gate failures (net allowlist must not grow; `test_ratchet_baselines` passes).
- **NFR-003** ATDD-first (C-011): every behavioral fix (FR-001/005/008) lands with a test that fails before the fix and passes after; documentation/tracker FRs are verified by inspection.
- **NFR-005** Error-handling philosophy (operator directive): **a clear, readable RC=1 error is strongly preferred over an RC=0 that hides a defect.** No fix in this mission may convert a surfaced failure into a silent success; surfaced skips/errors must carry an actionable message (the offending path + reason + remediation), and health/validation surfaces must exit non-zero when they detect a problem.
- **NFR-004** All work lands on `mission/org-doctrine-profile-integrity-activation-closure` (base = target = merge = coordination); nothing forks from or targets `main`.

## Success Criteria

- **SC-001** The I-1 integration test is RED on the current code and GREEN after FR-001 (`doctor doctrine` reports `healthy:false`, surfaces the invalid profile with a readable error, keeps valid siblings visible, and exits RC=1).
- **SC-002** `test_pytest_marker_convention` passes for all mission-authored files (FR-004).
- **SC-003** `mypy --strict src/doctrine/drg/merge.py` → 0 errors (FR-005).
- **SC-004** `test_runtime_charter_doctrine_boundary` passes with allowlist 0; `_baselines.yaml` == 0 (FR-006/007).
- **SC-005** A test asserts the absence of the stale cascade-deferral string (FR-008).
- **SC-006** `acceptance-matrix.json` has zero `pending`/`null` entries for implemented FRs and a set `overall_verdict` (FR-010).
- **SC-007** `CLAUDE.md` contains the new-subsystem section (FR-011).
- **SC-008** Trackers exist for any deferred FR-012/013 work and for FR-014's pre-existing failures.
- **SC-009** `test_no_dead_symbols` passes with the two payload re-exports absent from `events.py.__all__` and their allowlist entries removed (their `import` lines retained as annotations); the parent's dead-symbol claim is accurate (FR-009). FR-003/FR-009-docstring reconciliation is inspection-verified.

## Out of Scope

- Any new feature/behavior beyond the parent mission (this is hardening only).
- The framework-level coordination/claim-commit fixes (`#1597`, `#1598`/`#1602`) — those live on their own PR branches against `main`.
- The pre-existing-on-`main` failures themselves (only their tracking is in scope — FR-014).

## Dependencies & Constraints

- Stacked on the parent mission branch; the parent work is **not yet merged to main**. This close-out commits onto the same branch so parent + hardening merge together.
- Given the known coordination/lane status defects (#1597/#1602), execution may run in-place on the branch (manual or direct) rather than via the lane loop; `meta.json` therefore pins `coordination_branch` to the branch itself.
- Findings, evidence, and remediation detail are recorded in the parent mission's `adversarial-review-debrief.md` (the authoritative source for this mission's scope).
