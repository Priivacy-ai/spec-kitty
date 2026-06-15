# Mission Review Report: cli-bug-sweep-tool-surface-self-registration-01KV5AWE

**Reviewer**: Claude (spec-kitty-mission-review)
**Date**: 2026-06-15
**Mission**: `cli-bug-sweep-tool-surface-self-registration-01KV5AWE` — CLI bug sweep + tool-surface self-registration (mission #137)
**Baseline commit**: `ed214e16c11f7e8a9c858acfbbde7cad4671d510`
**HEAD at review**: `27086358a` (includes review fixes)
**WPs reviewed**: WP01..WP05 (all `done`)

---

## Gate Results

### Gate 1 — Contract tests
- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest tests/contract/`
- Exit code: 0
- Result: **PASS** (258 passed). Trailing line is a SaaS-sync auth warning, not a test failure.

### Gate 2 — Architectural tests
- Command: `.venv/bin/pytest tests/architectural/`
- Initial result: **FAIL** — `test_every_test_file_declares_a_pytestmark_marker` (1 failed, 372 passed).
- Cause: WP02's `test_bundle_validate_fresh_seed.py` and WP05's `test_map_requirements_coord.py` lacked a module-level `pytestmark`, making them invisible to marker-based CI profiles. (Pre-existing `tests/_support/test_wall_clock_assertions.py` from #1967 had the same defect.)
- Action taken: added `pytestmark = [pytest.mark.fast]` to all three. Re-run: **PASS**.
- This gate runs only in CI's integration job, not the fast-tests suites — which is why per-WP review did not catch it.

### Gate 3 — Cross-repo E2E
- Result: **N/A (not run)**. The `spec-kitty-end-to-end-testing` repo is not present in this workspace. This mission is a CLI-internal bug sweep (tool_surface registry, charter bundle validation, branch naming, ownership validation, map-requirements path resolution) and claims **no cross-repo behavior**, so no new e2e scenarios are required. No `mission-exception.md` is needed because no cross-repo behavior was claimed.

### Gate 4 — Issue Matrix
- File: `kitty-specs/.../issue-matrix.md` — 7 rows.
- Initial result: **FAIL** — #1949 and #1951 carried `in-mission` verdicts that survived to mission `done` (their WPs WP02/WP03/WP04 were already merged).
- Action taken: upgraded both to `fixed` with merged-WP evidence.
- Re-check: all 7 rows terminal — `fixed` (#1949, #1951, #1953, #1981, #1982), `verified-already-fixed` (#1950), `deferred-with-followup` with follow-up handle (#1947). **PASS**.

---

## FR Coverage Matrix

| FR | Description (brief) | WP | Test(s) | Adequacy |
|----|---------------------|----|---------|----------|
| FR-001 | xfail removed; init-flag regressions surface | WP01 | test_distribution.py | ADEQUATE |
| FR-002 | pathological mid8-mismatch tests | WP01 | test_branch_naming_human_slug.py | ADEQUATE |
| FR-003 | singular kind subdir names | WP02 | test_bundle_validate_fresh_seed.py + synthesizer suite | ADEQUATE |
| FR-004 | stale provenance sidecars removed | WP02 | code review (git rm) | ADEQUATE |
| FR-005 | built_in_only fresh-seed early-exit | WP02 | test_bundle_validate_fresh_seed.py | ADEQUATE |
| FR-006 | one-module provider add | WP03/WP04 | test_provider_registration.py | ADEQUATE |
| FR-007 | provider self-declares registration | WP04 | test_provider_registration.py::test_all_providers_registered | ADEQUATE |
| FR-008 | multi-def / synthetic-key / multi-token | WP03/WP04 | test_registry.py | ADEQUATE |
| FR-009 | coordinator derives config + Directive-030 test | WP03/WP04 | test_provider_registration.py::test_service_py_has_no_central_provider_literals | ADEQUATE |
| FR-010 | deterministic ordering | WP03 | test_registry.py + test_registration_orders_are_unique | ADEQUATE |
| FR-011 | map-requirements resolves from main checkout | WP05 | test_map_requirements_coord.py | ADEQUATE |
| FR-012 | create_intent hint always shown | WP05 | tests/specify_cli/ownership/ | ADEQUATE |

All 12 FRs have closed spec→WP→test→code chains. The new tests exercise production code paths (verified by per-WP reviewers and confirmed here); none rely on synthetic fixtures that would pass with the implementation deleted.

---

## Drift Findings

None. No non-goal invasion, no locked-decision violation. The implementation matches the spec scope exactly. Success Criterion 3 (zero parallel-lane conflict) is enforced structurally by the Directive-030 conformance test (T019), as the spec itself acknowledged is the achievable proof.

Scope note (informational, not drift): the provider self-registration wiring (WP04's T012–T018) was authored in WP03's commit because WP03's implementation agent completed it coherently before dying on an auth error. WP03→WP04 are sequential lanes (no parallel-conflict risk), so this is acceptable; WP04's net-new contribution was the T019 conformance test. A populated registry is a strict superset of WP03's "empty registry" requirement.

---

## Risk Findings

None blocking.

- **Dead code**: none. `_registry.py` and `_discovery.py` are consumed by `service.py` (`build_providers`, `build_registry`, `_KIND_TOKENS`); all 7 providers import `_registry` and self-register. Verified by grep of `src/` (excluding tests).
- **Cross-WP integration**: tool_surface providers + service.py + registry integrate cleanly; 503 tool_surface tests pass.

---

## Silent Failure Candidates

| Location | Condition | Result | Verdict |
|----------|-----------|--------|---------|
| `src/charter/bundle.py:207` `_manifest_is_fresh_seed` | manifest unparseable | returns `False` | NOT a silent failure — returning False causes fall-through to full validation, which surfaces the load error via `_check_manifest_integrity()`. Documented with inline comment. Correct. |

---

## Security Notes

Low risk. The mission adds no new subprocess, `shell=True`, network, or credential operations. `map_requirements` change uses pure filesystem path resolution (`resolve_feature_dir_for_slug`); bundle validation is read-only. No path-traversal or injection surface introduced.

Suppressions audit (NFR-002): 3 `noqa` added, all narrowly scoped with inline rationale and consistent with the project policy — `PLC0415` (intentional lazy import to avoid cycle), `BLE001` (broad except that falls through to full validation, not swallowing), `F401` (side-effect registration import, prescribed by the WP03 design). No `type: ignore` added. `ruff check` clean on all mission source.

---

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale

All 12 FRs are adequately covered with production-path tests. No locked decisions violated, no non-goals invaded, no dead code, no silent-failure anti-patterns, no security findings. Two gate failures were found during this review and both were **fixed in this review pass**: (1) Gate 2 architectural marker-convention violation on two mission test files (+ one pre-existing file), and (2) Gate 4 two `in-mission` issue-matrix verdicts surviving to mission `done`. After fixes, all runnable gates (1, 2, 4) pass; Gate 3 is N/A (cross-repo repo absent, no cross-repo behavior claimed). No remaining blocking findings.

### Open items (non-blocking) — RESOLVED in this review pass

1. **#1947 follow-up** — RESOLVED: filed as **#1983** (host-CLI ⇄ source provenance contract); issue-matrix `evidence_ref` updated to reference it.
2. **`_discovery.py` stale docstring** — RESOLVED: replaced the "registry remains empty until WP04" note with an accurate description (each provider self-registers at module scope; importing `_discovery` fully populates the registry).

No remaining open items.

## Retrospective Reminder

Canonical post-merge sequence: **mission review → author/verify retrospective → surface findings**. Verify the retrospective record exists at `.kittify/missions/01KV5AWE08DZ7VCJ673QDB0R9P/retrospective.yaml`; if absent, run `spec-kitty retrospect create --mission cli-bug-sweep-tool-surface-self-registration-01KV5AWE`. Then `spec-kitty retrospect summary` (cross-mission aggregation) and `spec-kitty agent retrospect synthesize --mission <slug>` (dry-run proposals).
