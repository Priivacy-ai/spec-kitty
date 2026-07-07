# Implementation Plan: Local pre-PR CI parity + contract-conformance boundary

**Branch**: `feat/ci-delivery-topology` | **Spec**: [spec.md](./spec.md)
**Issues**: Closes #2283 (Phase 3)

## Summary

Architect-first design established that #2283's factor (a)-CI (the `unit-contract-residual` marker gate, `6e5453e6d`/#2034) and factor (c-dynamic) (M5's #2438) are already delivered, so Phase 3 is small and low-blast-radius:
1. **Local pre-PR parity** (the real code): a typer/click **lock-parity check** in `_test_env_check.py` (read `uv.lock` vs installed via `importlib.metadata`; raise `MISSION_REVIEW_ENV_SKEW`, warn-loud, fail-closed opt-in) + a **local residual runner** that runs the CI `(unit or contract) and not (...)` selection, single-sourced from the CI selector — both wired into the review preflight (`review/__init__.py:307`), plus docs.
2. **Verify factor (a)** is present + blocking (no workflow edit).
3. **Boundary adjudication** (governance, no mechanism): record that #2438 discharges (c-dynamic) *conditionally on its merge*, (c-static) → CT7 #2077; file a contract-ownership issue with its URL embedded in the dossier.

## Technical Context
**Language/Version**: Python 3.11+
**Primary Dependencies**: existing internals only — `_test_env_check.py`, `review/__init__.py` preflight, `tomllib`/`importlib.metadata` (stdlib) to read `uv.lock` + installed versions, the CI `-m` selector (`ci-quality.yml:2418`) / `_gate_coverage` marker model as the single source. No new third-party deps.
**Storage**: files — `uv.lock`, `pyproject.toml`, `ci-quality.yml` read-only; no DB.
**Testing**: `pytest` — unit tests for the lock-parity check (mock two `importlib.metadata.version` results + a fixture `uv.lock`) + the residual-runner selection; a verification test for factor (a).
**Target Platform**: the spec-kitty repo's own dev/review loop (dogfooding gate — same repo-scoped pattern as the existing `spec-kitty review` gates).
**Project Type**: single (CLI/library).
**Performance Goals**: negligible — the parity check is two version reads; the residual runner is opt-in.
**Constraints**: NOT a typer/click pin change (C-001); NO new (c) sweep/allowlist (C-002); coordinate with #2438 (C-003, its `pre_review_gate.py` is absent on-branch); no workflow / `uv.lock` / dep-graph change (NFR-001); `ruff`+`mypy --strict` clean (C-004).
**Scale/Scope**: one preflight check + one local runner + `MISSION_REVIEW_ENV_SKEW` code + docs + a verify test + a governance decision/issue. Small.

## Charter Check
*GATE: passes.* Reuses the existing `spec-kitty review` preflight seam + the CI selector as the single source (Canonical-Sources; no drift, NFR-002); warn-loud default (no breakage); ATDD — the skew check is red-first (mock a diverging env). No new suppressions. No new detector/allowlist (avoids the split-brain the charter's architectural-gate-discipline warns against). Terminology guard on the new doc.

## Project Structure

### Documentation (this mission)
```
kitty-specs/ci-local-preflight-parity-01KWXWY0/
├── plan.md · spec.md · tasks.md · tasks/ · contracts/ · decision (boundary adjudication)
```

### Source Code (repository root)
```
src/specify_cli/cli/commands/_test_env_check.py        # + lock-parity check (FR-001) + residual-runner helper (FR-002)
src/specify_cli/cli/commands/review/__init__.py        # wire both into the preflight (:307)
src/specify_cli/cli/commands/review/ERROR_CODES.md     # + MISSION_REVIEW_ENV_SKEW
docs/guides/review-gates.md                            # FR-003 docs (+ cross-link from testing-parallel.md)
tests/specify_cli/cli/commands/test_test_env_check.py  # unit tests (lock-parity + residual selection)
tests/architectural/test_unit_contract_residual_gate.py # FR-004 verify (no workflow edit)
```
**Structure Decision**: all code lands on the `_test_env_check.py` + review-preflight seam; NO `.github/workflows/`, `uv.lock`, or `pyproject.toml`-deps change (NFR-001). The boundary decision is a dossier artifact + a filed issue (URL embedded).

## Implementation Concern Map

### IC-01 — Local pre-PR parity (the code): lock-parity check + residual runner + docs
- **Purpose**: make the local pre-PR layer a faithful mirror of CI — flag typer/click skew vs `uv.lock` (FR-001) + offer a local run of the CI residual selection (FR-002), single-sourced; document it (FR-003).
- **Relevant requirements**: FR-001, FR-002, FR-003, NFR-001, NFR-002, C-001, C-003, C-004.
- **Affected surfaces**: `_test_env_check.py`, `review/__init__.py`, `review/ERROR_CODES.md`, `docs/guides/review-gates.md`, `tests/.../test_test_env_check.py`.
- **Sequencing/depends-on**: none (independent of #2438 — the residual runner reads the CI selector, NOT `pre_review_gate.py`, per C-003).
- **Risks**: hardcoding a divergent `-m` string or typer/click version (mitigate: read `uv.lock` + the CI selector live, NFR-002); bricking a forward-compat dev loop (mitigate: warn-loud default, fail-closed opt-in).

### IC-02 — Verify factor (a) + boundary adjudication (governance)
- **Purpose**: pin factor (a)'s already-landed gate against regression (FR-004, read-only) + record the (c) boundary conditionally on #2438 + file the contract-ownership issue with its URL embedded (FR-005).
- **Relevant requirements**: FR-004, FR-005.
- **Affected surfaces**: `tests/architectural/test_unit_contract_residual_gate.py` (new, read-only assertion over `ci-quality.yml`), the mission dossier decision record + a filed GitHub issue.
- **Sequencing/depends-on**: none. FR-005's (c-dynamic) clause is scoped *conditionally* on #2438's merge (its code isn't on-branch).
- **Risks**: FR-004 duplicating the ci-suite-map-bind gates (mitigate: assert presence/blocking-membership only, don't re-model the marker plane); the boundary record asserting a closed factor with no on-branch code (mitigate: conditional wording + embedded issue URL).
