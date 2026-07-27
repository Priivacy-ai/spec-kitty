# Work Packages: Local pre-PR CI parity + contract-conformance boundary

**Mission**: `ci-local-preflight-parity-01KWXWY0` | **Issues**: Closes #2283 (Phase 3) | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Subtask Format: `[Txxx] Description (WP)`

## Path Conventions
Repo-root-relative. WP01 = the local-parity code (lock-parity check + residual runner + docs); WP02 = verify factor-(a) + the boundary governance. Independent (WP02 needs no WP01 output); parallelizable.

| Subtask | Description | WP | Requirement |
| --- | --- | --- | --- |
| T001 | `_test_env_check.py` typer/click lock-parity check: read locked versions from `uv.lock` vs installed (`importlib.metadata`); raise `MISSION_REVIEW_ENV_SKEW` (warn-loud default, fail-closed opt-in); wire into `review/__init__.py:307` | WP01 | FR-001 |
| T002 | Local residual-selection runner: run the CI `(unit or contract) and not (...)` selection, `-m` expression single-sourced from the CI selector (`ci-quality.yml:2418` / `_gate_coverage`), NOT hardcoded | WP01 | FR-002 |
| T003 | Docs: add the skew-flag + local-residual-run items to `docs/guides/review-gates.md` (the `--frozen` section already exists); unit tests for the parity check + selection | WP01 | FR-003 |
| T004 | Verify factor-(a): assert `unit-contract-residual` is always-on (no `if:`) + in `quality-gate.needs` by name; reference (don't re-pin) the existing exactly-one assertion. No workflow edit | WP02 | FR-004 |
| T005 | Boundary adjudication (dossier decision, conditional on #2438) + file the contract-ownership/CT7-sharpening issue with its URL embedded in the decision record. No (c) mechanism | WP02 | FR-005 |

---

## Work Package WP01: Local pre-PR parity — lock-parity check + residual runner + docs (Priority: P1)
**Prompt**: `/tasks/WP01-local-parity.md`
**Goal**: the local pre-PR layer faithfully mirrors CI — flags typer/click skew vs `uv.lock` + offers a local run of the CI residual selection (single-sourced), documented. Zero workflow/lock/dep change.
### Included Subtasks
- [ ] T001 Lock-parity check + `MISSION_REVIEW_ENV_SKEW` (WP01)
- [ ] T002 Local residual runner (single-sourced) (WP01)
- [ ] T003 Docs + unit tests (WP01)
### Dependencies
None (independent of #2438 — reads the CI selector, not `pre_review_gate.py`).
### Risks & Mitigations
- Hardcoded `-m`/version drift → read `uv.lock` + the CI selector live (NFR-002).
- Bricking a forward-compat dev loop → warn-loud default, fail-closed opt-in.

## Work Package WP02: Verify factor-(a) + boundary adjudication (Priority: P2)
**Prompt**: `/tasks/WP02-verify-and-boundary.md`
**Goal**: pin factor-(a)'s already-landed gate against regression (2 uncovered facts only) + record the (c) boundary conditionally on #2438 + file the contract-ownership issue (URL embedded).
### Included Subtasks
- [ ] T004 Verify factor-(a) (2 uncovered facts, no dup) (WP02)
- [ ] T005 Boundary decision + filed issue (URL embedded) (WP02)
### Dependencies
None.
### Risks & Mitigations
- Duplicating the ci-suite-map-bind exactly-one gate → assert only always-on + needs-membership; reference the existing assertion.
- Asserting a closed factor with no on-branch code → conditional wording + embedded issue URL (SC-005).
