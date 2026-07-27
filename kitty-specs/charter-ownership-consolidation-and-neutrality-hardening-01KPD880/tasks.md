# Tasks — Charter Ownership Consolidation and Neutrality Hardening

**Mission**: `01KPD880` · **Feature slug**: `charter-ownership-consolidation-and-neutrality-hardening-01KPD880`
**Planning base branch**: `main` → **Merge target branch**: `main`
**Change mode**: `bulk_edit` (per `occurrence_map.yaml`; approved 2026-04-17)
**Authoring date**: 2026-04-17

---

## Baseline observation that shapes this task breakdown

A pre-breakdown audit (see research.md R-001, R-002) confirmed that `src/charter/` is already the canonical implementation owner and `src/specify_cli/charter/` contains only 4 thin re-export shim files. A repo-wide grep for `from specify_cli.charter` outside mission planning artifacts found:

- `tests/specify_cli/charter/test_defaults_unit.py` — C-005 compatibility fixture, occurrence_map exception, **do not change**.
- `tests/charter/test_sync_paths.py` — C-005 compatibility fixture, occurrence_map exception, **do not change**.
- `src/specify_cli/charter/__init__.py` — the shim itself.
- `pyproject.toml:238` — stale `[[tool.mypy.overrides]]` quarantine entry for a submodule that never existed.

**Live internal callers of `specify_cli.charter.*` outside those four locations: zero.** The "28 import-site migration" estimate from earlier planning drafts was historical; the real surface is already consolidated. The work is therefore concentrated on:

1. Installing the deprecation signal on the surviving shims (FR-004, FR-005).
2. Building the neutrality tripwire from scratch (FR-008 through FR-014).
3. Building the ownership-invariant test (FR-001, FR-002, SC-001).
4. Locking the legacy surface so it cannot regrow (premortem mitigation).
5. Removing the stale mypy quarantine and verifying `mypy --strict` (NFR-003).
6. Documenting the sunset plan (FR-015).

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Author `tests/charter/test_charter_ownership_invariant.py` per contract C-6 | WP01 | [P] | [D] |
| T002 | Verify invariant passes on clean baseline | WP01 | | [D] |
| T003 | Document the CANONICAL_OWNERS registry update protocol in the test's docstring | WP01 | | [D] |
| T004 | Create `src/charter/neutrality/` package with public `__init__.py` | WP02 | [D] |
| T005 | Author `banned_terms.yaml` with 4 seed entries PY-001..PY-004 per C-4 | WP02 | | [D] |
| T006 | Author `language_scoped_allowlist.yaml` with audited seed entries per C-5 | WP02 | | [D] |
| T007 | Implement `lint.py` — scanner, `BannedTermHit`, `NeutralityLintResult` per C-3 | WP02 | | [D] |
| T008 | Verify scanner returns clean on baseline (zero hits, zero stale entries) | WP02 | | [D] |
| T009 | Confirm `mypy --strict src/charter/neutrality/` passes | WP02 | | [D] |
| T010 | Author `tests/charter/test_neutrality_lint.py` with `test_generic_artifacts_are_neutral` | WP03 | | [D] |
| T011 | Add fault-injection test that catches a synthetic regression (SC-005) | WP03 | | [D] |
| T012 | Add runtime-budget assertion (NFR-001, ≤ 5 s on baseline) | WP03 | | [D] |
| T013 | Confirm ≥ 90% coverage on `src/charter/neutrality/lint.py` | WP03 | | [D] |
| T014 | Edit `src/specify_cli/charter/__init__.py` — add deprecation constants + single `warnings.warn` | WP04 | [D] |
| T015 | Leave submodule shims silent; strip any existing per-submodule `warnings.warn` calls | WP04 | | [D] |
| T016 | Author `tests/specify_cli/charter/test_shim_deprecation.py` per contract C-2 | WP04 | | [D] |
| T017 | Re-run C-005 compatibility tests (`test_defaults_unit.py`, `test_sync_paths.py`, `test_chokepoint_coverage.py`) and confirm they still pass | WP04 | | [D] |
| T018 | Author `tests/specify_cli/charter/test_no_new_legacy_modules.py` (premortem guard) | WP05 | | [D] |
| T019 | Add content-shape assertions — no new `class` / non-re-export `def` under `src/specify_cli/charter/` | WP05 | | [D] |
| T020 | Document the guard's purpose in an in-file docstring | WP05 | | [D] |
| T021 | Run `mypy --strict src/charter/context.py` and record diagnostics | WP06 | [D] |
| T022 | Fix any strict errors surfaced, or rename quarantine entry to `charter.context` with removal TODO | WP06 | | [D] |
| T023 | Remove the stale `specify_cli.charter.context` line from `pyproject.toml` `[[tool.mypy.overrides]]` and confirm config parses | WP06 | | [D] |
| T024 | Author `docs/migration/charter-ownership-consolidation.md` naming canonical path + removal release 3.3.0 | WP07 | | [D] |
| T025 | Add CHANGELOG entry for the landing release with shim-removal target call-out | WP07 | | [D] |
| T026 | Cross-validate `__removal_release__` in `src/specify_cli/charter/__init__.py` matches the CHANGELOG text | WP07 | | [D] |

Total: **26 subtasks** across **7 work packages**. Average ~3.7 subtasks per WP.

---

## Work Packages

### WP01 — Charter Ownership Invariant Test

**Goal**: Install the executable invariant that SC-001 demands — exactly one real definition of `build_charter_context` and `ensure_charter_bundle_fresh` under `src/`, each at its canonical location.

**Priority**: P1 (foundational; confirms baseline is already clean).

**Independent test**: `pytest tests/charter/test_charter_ownership_invariant.py` returns pass on a clean checkout. The test fails with a named, actionable diagnostic if a duplicate definition is introduced anywhere under `src/`.

**Included subtasks**:

- [x] T001 Author `tests/charter/test_charter_ownership_invariant.py` per contract C-6 (WP01)
- [x] T002 Verify invariant passes on clean baseline (WP01)
- [x] T003 Document the CANONICAL_OWNERS registry update protocol in the test's docstring (WP01)

**Dependencies**: None.

**Parallelizable with**: WP02, WP04, WP06 (disjoint files).

**Estimated prompt size**: ~220 lines.

**Prompt file**: [tasks/WP01-charter-ownership-invariant-test.md](./tasks/WP01-charter-ownership-invariant-test.md)

---

### WP02 — Neutrality Lint Scaffolding

**Goal**: Build the neutrality tripwire module — scanner, banned-terms config, language-scoped allowlist — as a new package `src/charter/neutrality/`.

**Priority**: P1 (blocks WP03 regression test).

**Independent test**: `python -c "from charter.neutrality import run_neutrality_lint; print(run_neutrality_lint().passed)"` returns `True` on a clean baseline.

**Included subtasks**:

- [x] T004 Create `src/charter/neutrality/` package with public `__init__.py` (WP02)
- [x] T005 Author `banned_terms.yaml` with 4 seed entries PY-001..PY-004 per C-4 (WP02)
- [x] T006 Author `language_scoped_allowlist.yaml` with audited seed entries per C-5 (WP02)
- [x] T007 Implement `lint.py` — scanner, `BannedTermHit`, `NeutralityLintResult` per C-3 (WP02)
- [x] T008 Verify scanner returns clean on baseline (zero hits, zero stale entries) (WP02)
- [x] T009 Confirm `mypy --strict src/charter/neutrality/` passes (WP02)

**Dependencies**: None.

**Parallelizable with**: WP01, WP04, WP06.

**Estimated prompt size**: ~520 lines (the largest WP — scanner logic + two YAML schemas to populate).

**Prompt file**: [tasks/WP02-neutrality-lint-scaffolding.md](./tasks/WP02-neutrality-lint-scaffolding.md)

---

### WP03 — Neutrality Regression Test

**Goal**: Wire the scanner from WP02 into a pytest module that fails on banned-term hits and proves it catches a synthetic regression.

**Priority**: P1.

**Independent test**: `pytest tests/charter/test_neutrality_lint.py` passes on baseline and fails on a fault-injected generic artifact containing `pytest`.

**Included subtasks**:

- [x] T010 Author `tests/charter/test_neutrality_lint.py` with `test_generic_artifacts_are_neutral` (WP03)
- [x] T011 Add fault-injection test that catches a synthetic regression (SC-005) (WP03)
- [x] T012 Add runtime-budget assertion (NFR-001, ≤ 5 s on baseline) (WP03)
- [x] T013 Confirm ≥ 90% coverage on `src/charter/neutrality/lint.py` (WP03)

**Dependencies**: WP02.

**Estimated prompt size**: ~280 lines.

**Prompt file**: [tasks/WP03-neutrality-regression-test.md](./tasks/WP03-neutrality-regression-test.md)

---

### WP04 — Shim Deprecation Signaling

**Goal**: Install the `DeprecationWarning` + metadata constants on the `specify_cli.charter` package `__init__.py`, and assert the behavior from a dedicated test. Submodule shims stay silent per C-2.

**Priority**: P1.

**Independent test**: `pytest tests/specify_cli/charter/test_shim_deprecation.py` passes; importing `specify_cli.charter` (or any submodule) from a fresh process emits exactly one `DeprecationWarning` that names `charter` and `3.3.0`.

**Included subtasks**:

- [x] T014 Edit `src/specify_cli/charter/__init__.py` — add deprecation constants + single `warnings.warn` (WP04)
- [x] T015 Leave submodule shims silent; strip any existing per-submodule `warnings.warn` calls (WP04)
- [x] T016 Author `tests/specify_cli/charter/test_shim_deprecation.py` per contract C-2 (WP04)
- [x] T017 Re-run C-005 compatibility tests and confirm they still pass (WP04)

**Dependencies**: None.

**Parallelizable with**: WP01, WP02, WP06.

**Estimated prompt size**: ~330 lines.

**Prompt file**: [tasks/WP04-shim-deprecation-signaling.md](./tasks/WP04-shim-deprecation-signaling.md)

---

### WP05 — Legacy Surface Lockdown

**Goal**: Install a premortem-mitigation test that fails if any contributor adds a non-shim module under `src/specify_cli/charter/` in the future. Addresses premortem item 1 in research.md.

**Priority**: P2.

**Independent test**: `pytest tests/specify_cli/charter/test_no_new_legacy_modules.py` passes today (only the 4 shim files exist) and fails if a new file exceeds the shim-shape thresholds.

**Included subtasks**:

- [x] T018 Author `tests/specify_cli/charter/test_no_new_legacy_modules.py` (premortem guard) (WP05)
- [x] T019 Add content-shape assertions — no new `class` / non-re-export `def` under `src/specify_cli/charter/` (WP05)
- [x] T020 Document the guard's purpose in an in-file docstring (WP05)

**Dependencies**: WP04 (the four shim files must carry their canonical `__deprecated__` attribute so the guard can distinguish "legitimate shim" from "regrowth").

**Estimated prompt size**: ~210 lines.

**Prompt file**: [tasks/WP05-legacy-surface-lockdown.md](./tasks/WP05-legacy-surface-lockdown.md)

---

### WP06 — mypy Quarantine Cleanup

**Goal**: Remove the stale `specify_cli.charter.context` entry from the `[[tool.mypy.overrides]]` "Transitional quarantine" block. Gated on a passing `mypy --strict src/charter/context.py` run (R-008).

**Priority**: P2.

**Independent test**: `mypy --strict src/charter/context.py` returns zero errors; `pyproject.toml` parses clean; no quarantine entry names `specify_cli.charter.context`.

**Included subtasks**:

- [x] T021 Run `mypy --strict src/charter/context.py` and record diagnostics (WP06)
- [x] T022 Fix any strict errors surfaced, or rename quarantine entry to `charter.context` with removal TODO (WP06)
- [x] T023 Remove the stale line from `pyproject.toml` `[[tool.mypy.overrides]]` and confirm config parses (WP06)

**Dependencies**: None.

**Parallelizable with**: WP01, WP02, WP04.

**Estimated prompt size**: ~200 lines.

**Prompt file**: [tasks/WP06-mypy-quarantine-cleanup.md](./tasks/WP06-mypy-quarantine-cleanup.md)

---

### WP07 — Migration Docs and CHANGELOG

**Goal**: Produce the contributor-facing migration guide and CHANGELOG entry that together satisfy FR-015 and SC-006. Cross-validate the removal release constant against the CHANGELOG text.

**Priority**: P2.

**Independent test**: `docs/migration/charter-ownership-consolidation.md` exists, names `charter` as canonical and `3.3.0` as removal target; `CHANGELOG.md` has a corresponding entry; `specify_cli.charter.__removal_release__` equals `"3.3.0"`.

**Included subtasks**:

- [x] T024 Author `docs/migration/charter-ownership-consolidation.md` naming canonical path + removal release 3.3.0 (WP07)
- [x] T025 Add CHANGELOG entry for the landing release with shim-removal target call-out (WP07)
- [x] T026 Cross-validate `__removal_release__` in `src/specify_cli/charter/__init__.py` matches the CHANGELOG text (WP07)

**Dependencies**: WP04 (the removal-release constant must be in place before the docs cite it).

**Estimated prompt size**: ~220 lines.

**Prompt file**: [tasks/WP07-migration-docs-and-changelog.md](./tasks/WP07-migration-docs-and-changelog.md)

---

## Execution order and parallelization

```
Wave 1 (parallel):  WP01  |  WP02  |  WP04  |  WP06
Wave 2 (parallel):  WP03 (← WP02)  |  WP05 (← WP04)
Wave 3:             WP07 (← WP04)
```

Wave 1 can go entirely in parallel — four independent file surfaces. Wave 2 opens once WP02 and WP04 land. Wave 3 (docs) lands last so CHANGELOG + migration guide can reference the final removal release constant.

---

## MVP scope recommendation

**WP02 + WP03 + WP04**: these three together deliver the user-visible mission outcomes (neutrality tripwire working end-to-end, shim deprecation warning firing). WP01 is the ownership invariant (already passing today — the test is a regression guard). WP05, WP06, and WP07 are hygiene and documentation that follow naturally.

For any contributor wondering "what's the smallest merge that represents this mission landing?", the answer is WP02 + WP03 + WP04.

---

## Requirement coverage

(Populated by `spec-kitty agent tasks map-requirements --batch` after WP prompt files are written; see WP frontmatter `requirement_refs` for canonical mapping.)
