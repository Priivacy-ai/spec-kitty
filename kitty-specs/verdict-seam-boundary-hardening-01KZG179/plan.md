# Implementation Plan: Verdict-Seam Boundary Hardening

**Branch**: `hardening/verdict-seam-facade-followup` | **Date**: 2026-08-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/verdict-seam-boundary-hardening-01KZG179/spec.md`

## Summary

Finish the single-authority *write* boundary opened by PR #3245 and clear six tracked debt/bug follow-ons, **without** touching the verdict authority model or read semantics (already unified — C-001). The work is grounded by a 3-lens research squad + a 2-lens pre-planning squad against `upstream/main` tip `3ac01d247`. (A seventh, #3216, was folded during pre-planning then descoped by the post-tasks squad — its target reader was already retired by the prior mission's WP05; closed as already-resolved.) Five surfaces:

1. **Status façade completeness + guard non-vacuity** (#3254) — promote the full verdict bridge onto `status.__all__`, migrate every submodule-object consumer (8 verdict_vocab + 4 collateral) to façade symbols, retire the duplicated merge-blocking decode, and widen the boundary guard so the bypass it should forbid is actually caught.
2. **Verdict-seam census completeness** (#3236 + folded #3217) — narrow the wholesale module exclusion to function level *and* teach the classifier to see helper-constructed readers, so the census is fully (not half) hardened.
3. **Arbiter override resilience** (#3244) — red-first fix for the conflict-marked-artifact crash via a filename-only cycle-number resolver.
4. **`accept --json` advisory parity** (#3255) — surface the SC-008 advisory in a structured JSON field.
5. **Stress CI lane isolation** (#3256) — a dedicated `-m stress -n0` lane so the heavyweight durability test stops riding the fast pool.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (existing); no new deps
**Storage**: N/A (append-only `status.events.jsonl` is the verdict authority — untouched)
**Testing**: pytest (+ xdist `--dist loadfile`), architectural gates under `tests/architectural/`, pytest markers in `pytest.ini`, CI in `.github/workflows/ci-quality.yml`
**Target Platform**: Linux/macOS dev + CI; the stress lane is POSIX-only (fork)
**Project Type**: single (Python CLI package `src/specify_cli/`)
**Performance Goals**: N/A (correctness/boundary mission)
**Constraints**: ruff/mypy clean, zero new suppressions; complexity ceiling 15 (C901/S3776); every new branch/helper gets a focused test in the same WP (Sonar new-code coverage)
**Scale/Scope**: ~18 production files touched (mostly small import-shape migrations), 2 architectural gate tests widened, 1 CI workflow + `pytest.ini`

## Charter Check

*GATE: pass before implementation; re-check after design.*

- **Single canonical authority** ✅ — the mission's whole thesis is *one* import surface (`status` façade) and *one* verdict decode (`review_result_from_state`); no new authority introduced. C-001 forbids touching the verdict authority/read model.
- **Campsite cleaning** ✅ — per-WP campsite steps threaded from the pre-planning census (constant hoists, extract-helpers, stale-docstring deletion, S110 fix). See per-WP tables.
- **Mission tracer files** ✅ — three seeded at planning (`tracers/`), appended during implement.
- **Test-remediation / red-first** ✅ — #3244 is red-first (C-006); the reducer test rename (FR-006) is a name/docstring fix with assertions already correct (not a soften).
- **Architectural gate discipline** ⚠️ — this mission *edits two arch gates* (`test_status_module_boundary.py`, `test_verdict_seam_census.py`). Both must remain **non-vacuous** (NFR-002): each gets a synthetic-violation teeth test. Re-baseline is comment-only per research (no golden-count/shard-map file changes — NFR-005).
- **Canonical sources** ✅ — reuse existing helpers (`_cycle_number_or_zero`, `_REVIEW_CYCLE_NUMBER_RE`, `_RUNTIME_SLOTS`) rather than re-implement.
- **Git/workflow discipline** ✅ — mission branch → PR to origin/main; operator merges. Commit+push on point-cuts.

## Implementation Concern Map (IC-##)

| IC | Concern | Issues | Primary surfaces | Independence |
|----|---------|--------|------------------|--------------|
| **IC-01** | Status façade = sole import surface, actively enforced | #3254 (+ FR-006 rename) | `status/__init__.py`, `status/reducer.py`, 8 verdict_vocab consumers, 4 collateral consumers, `post_merge/review_artifact_consistency.py`, `tests/architectural/test_status_module_boundary.py` | Internal hard ordering (export → migrate/dedup → widen guard) |
| **IC-02** | Verdict-seam census sees every reader (direct + helper-constructed) | #3236 + #3217 | `tests/architectural/test_verdict_seam_census.py`, `migration/verdict_provenance_backfill.py`, `migration/backfill_runtime_state.py` | Independent code surface from IC-01 → parallel lane |
| **IC-03** | Arbiter override survives damaged artifacts | #3244 | `review/artifacts.py`, `review/arbiter.py` | Independent → parallel lane; red-first |
| **IC-04** | `accept --json` advisory parity | #3255 | `cli/commands/accept.py` | Independent → parallel lane |
| **IC-05** | Stress CI lane isolation | #3256 | `.github/workflows/ci-quality.yml`, `pytest.ini`, `tests/status/test_emit_durability.py` | Independent (CI infra) → parallel lane |

## Work-Package Decomposition (preview — finalized by `/spec-kitty.tasks`)

> Ordering is dependency-driven, not issue-numbered. WP01 is foundational for WP02; WP03–WP06 are independent parallel lanes.

### WP01 — Façade exports (IC-01a) · foundational
- Promote the **full** `verdict_vocab` public surface (8 functions + `EventVerdict` alias + `APPROVED`/`REJECTED`/`CHANGES_REQUESTED`) **and** `review_result_from_state` onto `status/__init__.__all__`.
- **C-002 hard ordering:** this WP lands the exports *before* WP02's dedup.
- **Campsite:** place `review_result_from_state` beside its sibling `event_sourced_review_result` (already exported ~L293) and mirror the per-symbol WP-provenance comment style; the `reducer` import block (L34-43) already pulls the symbol — only the `__all__` entry is missing.
- **Campsite (FR-006):** rename the two drifted reducer tests in `tests/status/test_reducer.py` (`test_forced_null_review_result_defers_to_frontmatter_and_still_refuses` + sibling) — name/docstring only, assertions already correct. *(Collision watch: PR #3209 touches this file — rebase-check before push.)*
- **Tests:** façade-adoption test (`test_status_facade_adoption_wp02.py`) extended; export presence asserted.

### WP02 — Consumer migration + dedup + guard widening (IC-01b) · depends WP01
- Migrate **8** verdict_vocab submodule-object consumers to façade symbols: `review/cycle.py`, `proof/events.py`, `sync/emitter.py`, `orchestrator_api/commands.py`, `retrospective/generator.py`, `post_merge/review_artifact_consistency.py`, `cli/commands/agent/tasks_move_task.py`, `migration/verdict_provenance_backfill.py`.
- Migrate **4** collateral submodule-object imports to façade symbols: `orchestrator_api/commands.py:1558` (`emit`), `coordination/status_service.py:290,308` (`store`×2), `merge/done_bookkeeping.py:154` (`lane_reader`). *(Operator: migrate all four, no exemption ledger.)*
- Retire the duplicated `review_result` decode in `_event_sourced_gate_verdict` → delegate to `review_result_from_state` with `str(lookup.result.verdict) if lookup.result else None` (behavior-preserving across all 5 decode cases — NFR-001; merge-blocking path).
- **Delete the now-false local-decode justification docstring** in `review_artifact_consistency.py` (L148-158) and reconcile the echoed rationale in `reducer.review_result_from_state` docstring (L522-527).
- Widen `test_status_module_boundary.py::_is_bypass_import` to inspect `alias.name` on `ImportFrom`, **targeting submodule names specifically** (filesystem `.py` check / explicit set — NOT a bare `startswith`, which would flag 100+ legitimate façade-symbol imports — C-003). Add a synthetic-violation teeth test (NFR-002).
- **Campsites (same WP):** `tasks_move_task.py::_mt_emit_runtime_state` is **cc=13** — extract a helper (e.g. `_build_claim_review_override`) *before* adding the migration branch; `done_bookkeeping.py:119` hard-coded `verdict="approved"` → `verdict_vocab.APPROVED` (routed via façade).
- **Do-not-touch traps in edited modules:** `orchestrator_api/commands.py::_execute_lane_merge` (cc=15) / `transition` (14); `retrospective/generator.py::_build_findings` (15) — keep diffs surgically inside the verdict regions (`_parse_review_result_json`, the ~L340 helper). Verify `status_service.py` function-scoped `PLC0415` noqas and `generator.py:332` cycle-break import are respected (don't hoist blindly).

### WP03 — Census completeness (IC-02) · parallel
- Add a **function-level exclusion** mechanism to `test_verdict_seam_census.py` (none exists today); remove `verdict_provenance_backfill.py` from `_EXCLUDED_MODULE_REASONS`; exclude **only** its write-side helpers by name so `_legacy_frontmatter_verdict` surfaces as a reader row (#3236).
- Extend the classifier to recognize **helper-constructed** reader records so `migration/backfill_runtime_state.py::_review_from_frontmatter` surfaces (#3217). Together: census fully hardened (spec Story 2 §4).
- Flip the 3 tests asserting wholesale exclusion / zero rows (~L1075, L1421, L1461-1465) to the new function-level shape; confirm the module's other 8 functions classify as non-readers (or reconcile new rows). Non-vacuity teeth test retained.
- **Census guard:** do NOT merge this file with `test_2093_authority_invariant.py` (explicit warning L55-59).

### WP04 — Arbiter resilience (IC-03) · parallel · RED-FIRST
- **Red-first (C-006):** regression driving public `persist_arbiter_decision` against a conflict-marked latest `review-cycle-N.md` (no valid frontmatter) → asserts no crash + override recorded. RED before fix (mirror `test_arbiter.py::test_persist_decision_resolves_via_slug_and_emits_override`).
- Add `ReviewCycleArtifact.latest_cycle_number()` (filename-only, reuse `_cycle_number_or_zero`) to `review/artifacts.py`; swap it into `arbiter.py:466-467`. **Leave `.latest`/`from_file` untouched** (C-004 — `workflow_executor.py:1134` needs the full body; flag that identical-shape site as a follow-up, not in-scope).
- **Campsite (S1192):** hoist the `review-cycle-*.md` glob + `review-cycle-{n}.md` filename builder to shared constants (16 occurrences in `artifacts.py`; `arbiter.py:468` shares) — add `latest_cycle_number` as a *third* helper, do not merge the existing deliberately-separate helpers.
- **Census check:** `latest_cycle_number` must trip neither WRITER nor READER census predicates (pure cycle-number loader) — verify.
- **Direct micro-test** for `latest_cycle_number` (mixed valid + conflict-marked siblings → highest by filename, no raise).

### WP05 — `accept --json` advisory (IC-04) · parallel
- Lift `provenance_note` out of the `if not json_output:` gate (accept.py ~L675); inject a uniform top-level `advisories: list[str]` at the CLI emit layer across the 4 non-error JSON emit sites (~L751/763/773/879) via a shared helper. **No coupling into the acceptance domain model** (C-005).
- **Campsite (S110):** `_safe_emit_error_logged` (L49-51) `except Exception: pass` → debug-log + `# noqa: BLE001` rationale, matching the sibling handler at L72.
- **Test:** stranded fixture (`_write_stranded_mission`) → assert advisory in JSON; converged → empty `advisories` array.

### WP06 — Stress CI lane (IC-05) · parallel · CI-infra
- Add a `-m "stress and not windows_ci" -n0` serial job to `ci-quality.yml` (mirror `timing-nfr-serial`), POSIX-only.
- Right-size `test_emit_durability.py::test_two_concurrent_distinct_verdicts_are_both_durable` out of the fast pool (drop the module `fast` sweep for it / re-home to `tests/stress/`).
- Correct the inaccurate `pytest.ini:47` "excluded from the fast suite" wording.
- **Coordinate with #3235** (P0 concurrency data-loss, same test family): if the durability test moves/renames, do not strand #3235's repro — leave a pointer.

## Dependency & Lane Graph

```
WP01 (façade exports) ──▶ WP02 (migrate + dedup + guard widen)
WP03 (census)          ── parallel
WP04 (arbiter #3244)   ── parallel   (red-first)
WP05 (accept --json)   ── parallel
WP06 (stress CI lane)  ── parallel
```

Only WP01→WP02 is a hard edge (C-002 export-before-dedup). Everything else is independent code surface → concurrent lanes.

## Rebase-Collision Watch (from pre-planning sweep)

- **PR #3247** (`merge_driver.py`) — we do **not** edit `merge_driver.py` (the #3244 fix lives in `artifacts.py`/`arbiter.py`), so collision risk is low; re-verify at push.
- **PR #3209** (`tests/status/test_reducer.py`) — WP01's FR-006 rename touches this file. **Rebase-check before pushing WP01.**
- **PR #3252** (seam-census neighborhood) — glance so the two census patterns don't diverge.
- Surfaces currently collision-free: `status/__init__.py`, `review/artifacts.py`, `review/arbiter.py`, `accept.py`, `test_status_module_boundary.py`, `verdict_vocab.py`.

## Pre-existing Reds — Do NOT Misattribute (DIR-013 applies)

- **#3220** — `test_event_sourced_review_result_this_missions_own_meta_json_fixture` in `test_reducer.py` is a known pre-existing red (asserts on a live mutable repo fixture). We touch `reducer.py`/`verdict_provenance_backfill.py` — expect this on the base; do **not** "fix" it as mission collateral.
- Per **DIR-013**: any *newly-encountered* pre-existing failure gets a GitHub issue (command + failure summary + why pre-existing) before being treated as baseline.

## Non-Goals

- No change to the verdict authority model or read semantics (C-001; consistent with epic #3044's closed shape).
- Not touching `workflow_executor.py:1134`'s `.latest` full-body consumer (flagged as a same-shape follow-up).
- #3216 (dedup a hand-rolled review-cycle reader) was folded then **descoped** — the post-tasks squad found its target already retired by the prior mission's WP05; closed as already-resolved. WP04 no longer touches `tasks_parsing_validation.py`.
- #3243 (review-cycle numbering off-by-one) considered and left separate.
- #3235 (P0 concurrency data-loss) is a real durability fix — separate; WP06 only relocates the test.

## Tracer Files (seeded at planning — `tracers/`)

- `tracers/tooling-friction.md` — spec-commit no-op + broken pre-commit hook already logged.
- `tracers/approach.md` — research-squad-first grounding + point-cut squad cadence.
- `tracers/design-decisions.md` — corrected scope, export-before-dedup ordering, submodule-name-targeted guard, `latest_cycle_number` over touching `.latest`, fold adjudications.
