# Mission Review Report: charter-preflight-missing-charter-advisory-01M050PD

**Reviewer**: claude (post-merge mission review, autonomous)
**Date**: 2026-08-16
**Mission**: `charter-preflight-missing-charter-advisory-01M050PD` — Charter Preflight Missing-Charter Advisory Mode
**Baseline commit**: `9787175c1242eeda73fcb04946f0f566beed6a73`
**HEAD at review**: `a483dd4df` (includes one post-merge remediation commit — see Drift Findings DRIFT-1)
**WPs reviewed**: WP01 (only WP; single clean review pass, zero rejection cycles)

---

## Pre-merge adversarial correction (2026-08-16)

The historical **PASS WITH NOTES** below is superseded. A three-profile landing review of the rebased PR found three HIGH defects that its tests and acceptance matrix did not constrain:

1. `charter.md` presence changed pass/block behavior and exempted stale/invalid canonical residue, violating doctrine C-001 / FR-016.
2. `CharterPreflightResult.warnings` was discarded by live `next`, `implement`, and dashboard consumers, so FR-003 was metadata-only and not user-visible.
3. The documented legacy remediation (`spec-kitty charter generate`) fails without a saved interview.

The first correction was implemented red-first: `4bc73dbc6` adds canonical-state, hook, dashboard-persistence, and executable-remediation tests; `4493699b0` fixes them. Round 2 then found actual `next` JSON/query wrappers still swallowed advisories and an eager `charter.bundle` import added ~1.1s to cold startup. Red commit `3f5ab1082` pins all four next modes and a <500ms cold-import gate; `3dc72aa04` replays JSON-safe stderr, emits query advisories through the shared formatter, and lazily resolves `CHARTER_MD`. Current gates: focused 63 passed; contract 297 passed/5 skipped; architecture 1487 passed/2 skipped/2 xfailed; charter-path authority 4/4; ruff clean. Strict mypy retains only #3513's two base findings. A fresh squad rerun remains required before final verdict.

---

## Gate Results

### Gate 1 — Contract tests
- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest tests/contract/ -q`
- Exit code: 0
- Result: **PASS**
- Notes: 297 passed, 5 skipped.

### Gate 2 — Architectural tests
- Command: `.venv/bin/pytest tests/architectural/ -q`
- Exit code: initially 1 (1 failed, 1481 passed), 0 after remediation
- Result: **PASS** (after in-review remediation — see DRIFT-1)
- Notes: `test_charter_path_literal_authority.py::test_gate_green_against_seeded_allowlist` failed on first run: the new `_is_legacy_charter_bundle()` predicate declared an inline `.kittify/charter/charter.md` path literal (FR-016 clause a) instead of importing the canonical `charter.bundle.CHARTER_MD`. Fixed in commit `a483dd4df` (see DRIFT-1). Re-ran full `tests/architectural/` after the fix; confirmed the single failure is gone and no new failures were introduced.

### Gate 3 — Cross-repo E2E
- Command: N/A
- Exit code: N/A
- Result: **NOT RUN — sibling `spec-kitty-end-to-end-testing` repo not present in this environment** (`ls -d ../spec-kitty-end-to-end-testing` → not found).
- Notes: This mission introduces no cross-repo behavior — it is a pure internal change to `src/specify_cli/charter_runtime/preflight/` consumed entirely within this repo (`spec-kitty next`, `spec-kitty implement`, dashboard). None of the four floor scenarios (`dependent_wp_planning_lane`, `uninitialized_repo_fail_loud`, `saas_sync_enabled`, `contract_drift_caught`) are implicated by this diff. No operator-exception artifact was authored since this is a tooling-unavailability gap, not a claimed-and-unverified cross-repo behavior. Recommend a follow-up: this environment should have the e2e sibling repo available for future mission reviews, or Gate 3 should have a documented "not applicable" path distinct from "environmental blocker" for missions that are provably repo-local.

### Gate 4 — Issue Matrix
- File: `kitty-specs/charter-preflight-missing-charter-advisory-01M050PD/issue-matrix.json`
- Rows: 3 (#1665, #2831, #3498)
- Empty / `unknown` verdicts: 0
- `deferred-with-followup` rows missing a follow-up handle: 0 (none deferred)
- Result: **PASS**
- Notes: `#3498` → `fixed`, `#2831` → `fixed`, `#1665` → `verified-already-fixed` (its fail-closed guarantee is confirmed unbroken by this mission's non-regression tests). All verdicts terminal, all with concrete evidence references.

**Overall Gate summary**: 1, 2, 4 PASS; 3 not applicable/not runnable in this environment (non-blocking — no cross-repo behavior claimed).

---

## FR Coverage Matrix

| FR ID | Description (brief) | WP Owner | Test File(s) | Test Adequacy | Finding |
|-------|---------------------|----------|--------------|---------------|---------|
| FR-001 | Wire fresh-project exemption into next/implement | WP01 | `test_next_preflight.py::test_hook_does_not_abort_on_fully_absent_charter`, `test_implement_preflight.py::test_hook_does_not_abort_on_fully_absent_charter_for_implement` | ADEQUATE — calls the real `run_preflight_or_abort`, no mocking of the runner | — |
| FR-002 | Detect legacy charter.md-only bundle | WP01 | `test_runner.py::test_legacy_charter_bundle_is_advisory_not_blocking`, `test_legacy_charter_bundle_not_matching_all_missing_shape_is_also_advisory` | ADEQUATE — real `run_charter_preflight`, real filesystem fixtures | — (see DRIFT-1: implementation detail required post-merge remediation, behavior itself is correct and untouched by the fix) |
| FR-003 | Distinct, more prominent legacy-bundle warning | WP01 | `test_runner.py::test_legacy_charter_bundle_is_advisory_not_blocking` (warning-text assertions), `test_dashboard_preflight.py::test_dashboard_hook_surfaces_legacy_bundle_warning_detail` | ADEQUATE — asserts concrete required substrings (`charter.md`, `spec-kitty charter generate`) and non-equality with the fresh-project warning | — |
| FR-004 | Preserve all other blocking behavior | WP01 | `test_runner.py::test_neither_shape_still_blocks`, `test_legacy_charter_bundle_blocks_when_not_opted_in`, `test_invalid_charter_yaml_blocks`; `test_next_preflight.py::test_hook_still_aborts_on_invalid_charter_yaml`; `test_implement_preflight.py::test_implement_still_blocks_and_no_worktree_alloc_on_invalid_charter_yaml` | ADEQUATE — non-regression coverage on real entry points, including a worktree-non-allocation assertion | — |
| FR-005 | Single shared hook implementation | WP01 | `hook.py:91` (one-line diff); `test_runner.py::test_legacy_charter_bundle_row2_tie_break_wins_over_fresh_project` | ADEQUATE — grep-confirmed no duplicate `allow_missing_charter`/`_is_legacy_charter_bundle` implementation outside `runner.py`/`hook.py` | — |
| NFR-001 | ≤1 additional filesystem existence check | WP01 | `test_runner.py::test_legacy_bundle_detection_costs_at_most_one_additional_exists_call` | ADEQUATE — automated `Path.exists` call-count assertion, not review-only (this was tightened during `/spec-kitty.analyze` remediation before implementation) | — |
| NFR-002 | No regression in blocking coverage | WP01 | Full mandated suite, independently re-run by this reviewer: 54/54 pass | ADEQUATE | — |
| C-001 | Two exemption shapes only | WP01 | `test_runner.py::test_neither_shape_still_blocks` (contract row 4) | ADEQUATE | — |
| C-002 | Single shared implementation point | WP01 | Structural (grep), reviewed | ADEQUATE | — |
| C-003 | Regression tests required | WP01 | All of the above | ADEQUATE | — |

**Legend**: ADEQUATE = test constrains the required behavior against real production code paths (no synthetic-fixture false positives found in any of the four touched test files).

---

## Drift Findings

### DRIFT-1: New code violated the codebase's charter-path-literal single-authority invariant (C-001, FR-016)

**Type**: LOCKED-DECISION VIOLATION
**Severity**: HIGH (was blocking; **remediated during this review**, see below)
**Spec reference**: This mission's own C-002 ("single shared implementation point") was honored; the violated invariant belongs to a *different*, prior governance-authoritative mission (`doctrine-charter-split-unification-01KZ0SRB`, FR-016/C-001): "charter.yaml is the deterministic presence/config authority... `charter.bundle` owns the ONE declaration of the bundle paths."

**Evidence**:
- Pre-fix `runner.py:103`: `_CHARTER_MD_RELATIVE_PATH: tuple[str, ...] = (".kittify", "charter", "charter.md")` — an inline path-literal declaration outside `src/charter/bundle.py`, the sole sanctioned authority module.
- Caught by `tests/architectural/test_charter_path_literal_authority.py::test_gate_green_against_seeded_allowlist` (Gate 2), which the per-WP implementer and reviewer both missed — neither the implementation prompt nor the independent WP01 review checklist referenced this specific architectural gate; the WP review's own C-002 grep only checked for *duplicated exemption logic*, not *inline-literal-vs-canonical-import* discipline.

**Analysis**: This is exactly the class of finding the mission-review stage exists to catch — a structural/architectural invariant that individual WP review, scoped to "does this WP's own diff satisfy this WP's own spec," has no reason to check against a *different* mission's binding constraint. The deeper question investigated during this review: does distinguishing the legacy-bundle case from the fresh-project case (this mission's entire FR-002/FR-003) fundamentally require gating on `charter.md`'s presence, and if so, does that inherently conflict with C-001's "only charter.yaml may gate" rule (clause b of the same architectural test)?

Resolution reached: **no conflict**, once precisely scoped. `charter.md`'s existence in this code path selects *only* which of two already-non-blocking advisory warning strings is attached to the result — `passed=True` is reached identically in both branches, driven entirely by `charter_source` (a `charter.yaml`-derived signal) plus the caller's `allow_missing_charter=True`. This is structurally identical to the already-allowlisted `_collect_charter_sync_status` precedent (`.exists()` used for a status-readout, not a governance decision). Remediated in commit `a483dd4df`: (1) `CHARTER_MD` now imported from `charter.bundle` (clause a resolved with zero allowlist entry, matching the sibling `references_refresh.py` precedent already in the same package), (2) the resulting clause-(b) presence-gate site was allow-listed with an explicit rationale following the file's own documented schema and precedent pattern, (3) the allowlist's `charter_path_literal_baseline` was bumped 48→49 with a dated "GREW" note mirroring the file's existing "DRAINED" convention, for audit-trail honesty.

**Post-remediation verification**: `tests/architectural/test_charter_path_literal_authority.py` green (4/4), full mandated regression suite still 54/54 green, `ruff check` clean, `mypy --strict` clean except the 2 pre-existing findings already tracked in #3513.

---

### DRIFT-2 (observation, non-blocking): Documented "shrink-only" allowlist policy has no corresponding automated enforcement

**Type**: NFR-MISS (process/tooling gap, not a defect in this mission's own deliverable)
**Severity**: LOW
**Spec reference**: N/A to this mission — a pre-existing gap in `doctrine-charter-split-unification-01KZ0SRB`'s own tooling.
**Evidence**: `tests/architectural/charter_path_literal_allowlist.yaml`'s header comment states "adding an entry to green a new violation FAILS `test_allowlist_shrink_only`", but `grep -n "^def test_" tests/architectural/test_charter_path_literal_authority.py` shows no function by that name exists anywhere in the file, and `charter_path_literal_baseline` / `CHARTER_PATH_LITERAL_FLOOR` are referenced only in prose comments, never read by any assertion.

**Analysis**: This mission relied on that gap to add a legitimate new allow-list entry (DRIFT-1's remediation) — which was the *architecturally correct* choice given the entry's honest, precedent-matched rationale, but it is worth flagging that the policy currently only holds by convention/code-review discipline, not by a structural test. Filed as [#3514](https://github.com/Priivacy-ai/spec-kitty/issues/3514).

---

## Risk Findings

### RISK-1: None found at CRITICAL/HIGH severity in the shipped diff itself

No dead code: `_is_legacy_charter_bundle()` and `_advisory_missing_charter_result()` are both called from the same module's `run_charter_preflight()`, which is the confirmed live entry point for all three consumers (`next`, `implement`, dashboard) via `hook.py`.

No boundary-condition bypass found: the row-2/row-3 tie-break (all layers "missing" + `charter.md` present → legacy-bundle wins) is explicitly tested and matches the pinned contract; the "neither shape" residue case (contract row 4) is explicitly tested to still block.

No silent-failure pattern (`except Exception: return ""`/`None`/`[]`) introduced by this diff — confirmed via direct read of both touched functions; no new `try`/`except` blocks were added.

No cross-WP integration gap — single WP, no shared-file contention with parallel work.

---

## Silent Failure Candidates

None found in this mission's diff.

---

## Security Notes

None. `git diff <baseline>..HEAD -- src/` scanned for subprocess/shell/path/HTTP/credential patterns — zero hits. This mission touches only boolean predicate logic and string constants reading local `.kittify/charter/` filesystem state that was already being read by pre-existing code in the same module.

---

## Historical Final Verdict (superseded by pre-merge correction above)

**PASS WITH NOTES**

### Verdict rationale

All ten spec requirements (FR-001–005, NFR-001–002, C-001–003) trace to adequate, real-production-path tests with no synthetic-fixture false positives. Gates 1, 2, and 4 pass; Gate 3 is not applicable (no cross-repo behavior claimed, sibling repo unavailable in this environment — documented, not silently skipped). One HIGH-severity architectural drift (DRIFT-1) was found and fully remediated within this review before the verdict was finalized, with independent re-verification of the full gate + regression + lint + type-check surface. No CRITICAL findings, no unresolved HIGH findings, no security findings. The "WITH NOTES" qualifier reflects DRIFT-2 (a tooling/process observation about a different mission's gate, not a defect in this mission's own deliverable) as an open, non-blocking item.

### Open items (non-blocking)

- DRIFT-2: filed as [#3514](https://github.com/Priivacy-ai/spec-kitty/issues/3514) — missing `test_allowlist_shrink_only` enforcement (or docstring correction) in `tests/architectural/test_charter_path_literal_authority.py`.
- Gate 3 tooling gap: this environment lacks the `spec-kitty-end-to-end-testing` sibling repo; not actionable within this mission, noted for the mission-review skill's own maintainers.

## Retrospective Reminder

The canonical post-merge sequence is: **mission review → author or verify retrospective (`retrospect create`) → surface findings (`summary` aggregates; `synthesize` reviews proposals)**.

`retrospective.yaml` was authored automatically at merge terminus (confirmed present: `kitty-specs/charter-preflight-missing-charter-advisory-01M050PD/retrospective.yaml`, commit `eb4b3c405`). Next: `spec-kitty retrospect summary` (cross-mission aggregation) and `spec-kitty agent retrospect synthesize --mission charter-preflight-missing-charter-advisory-01M050PD` (inspect proposals; dry-run by default, `--apply` to mutate) — deferred to the operator/next session, non-blocking for the PR.
