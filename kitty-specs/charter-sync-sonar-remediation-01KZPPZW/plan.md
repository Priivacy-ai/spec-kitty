# Implementation Plan: Charter & Sync Sonar Remediation

**Branch**: `fix/charter-sync-sonar-remediation` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)

## Summary

Clear the 80 Sonar findings in `charter` (45, incl. one `S8786` ReDoS BLOCKER) and `sync` (35), the same
behavior-preserving way the doctrine sweep (#3232) did: hoist duplicate literals to constants, extract
tested helpers to bring over-complex functions to ≤15, fix/remove malformed suppression comments, drop
unused params, and simplify the ReDoS regex (match-equivalent). No new suppressions. Full findings
inventory: scratchpad `charter-sync-sonar-findings.txt` (per module → rule → file:line).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest; the existing `charter`/`sync` modules and their tests
**Testing**: `tests/charter/**`, `tests/sync/**` (existing suites stay green); new focused tests per extracted `S3776` helper; a characterization test for the `S8786` regex
**Project Type**: single (refactor-only; no new runtime surfaces)
**Performance Goals**: the `S8786` regex becomes linear-time (removes super-linear backtracking)
**Constraints**: behavior-preserving (NFR-001); no new suppressions (NFR-002); scoped to `src/charter/` + `src/specify_cli/charter_runtime/` + `src/specify_cli/sync/` + their tests (C-001); `merge_driver.py:519` `S8786` out of scope (C-002)
**Scale/Scope**: 80 findings across ~34 files; 27 `S3776` (all tractable, complexity 16-33 — no deferral); 15 `S1192`; 20 `S7632`; misc + 1 BLOCKER

## Charter Check

- **ATDD / test-remediation**: PASS — every `S3776` helper gets a focused test; the `S8786` regex gets a
  characterization test proving match-equivalence; existing suites lock behavior.
- **Canonical sources / no false-green**: PASS — real fixes only; NFR-002 forbids added suppressions.
- **Refactor-stable / campsite**: PASS — behavior-preserving extractions; scoped to the two modules.
- **Sonar expectations (repo charter)**: PASS — this mission *is* the Sonar-shaped-constraint cleanup
  (complexity ≤15 via tested helpers, literals→constants, no suppression to silence).

No charter violations.

## Project Structure

```
src/charter/**, src/specify_cli/charter_runtime/**   # charter WPs
src/specify_cli/sync/**                              # sync WPs
tests/charter/**, tests/sync/**                       # helper tests + characterization test
```

**Structure Decision**: refactor-only; no new modules. No arch-guard co-evolution expected (these are
maintainability fixes, not topology changes) — implementers confirm `ruff`/`mypy`/existing suites.

## Implementation Concern Map

> `/spec-kitty.tasks` maps these to WPs. **WPs are split by FILE-GROUP (disjoint owners), not by rule** —
> a file with both an `S3776` and an `S1192` is fixed wholly in one WP, so no two WPs own the same file
> (the same ownership discipline #3232 used for `extractor.py`). The BLOCKER is its own priority WP.

### IC-01 — Charter ReDoS BLOCKER (FR-001, NFR-003, SC-003)

- Simplify `src/charter/activation/context_renderers/token_budget.py:308` regex to remove super-linear backtracking.
- Add a characterization test: the new regex matches EXACTLY the same inputs (representative + adversarial
  backtracking inputs) as the old one, and runs linear-time. Own this file (+ its test) alone → highest priority.

### IC-02 — Charter complexity, batch 1 & 2 (FR-002, NFR-001)

- 20 `S3776` functions (complexity 16-29) across ~15 charter files. Extract deterministic helpers with
  focused tests; target ≤15. Split into ~2 file-group WPs so each owns a disjoint set of files. Highest:
  `evidence/code_reader.py:182` (33), `charter_runtime/lint/checks/org_layer.py:64` (29),
  `context_renderers/token_budget.py:365` (28 — same file as IC-01, so IC-01's WP also owns this one).

### IC-03 — Charter literals + suppression comments + misc (FR-003, FR-004, FR-005)

- `S1192` ×6 → constants; `S7632` ×13 malformed suppression comments → fix/remove (prefer removal);
  `S1172` ×3 unused params (drop or `_`-prefix per convention); `S3516` ×1; `S5890` ×1. Grouped with the
  files they live in (folded into the charter file-group WPs to keep ownership disjoint).

### IC-04 — Sync complexity (FR-006, NFR-001)

- 7 `S3776` functions (16-33) across ~7 sync files (`dossier_pipeline.py:38` (33),
  `runtime_event_emitter.py:186` (21), `body_upload.py:212` (19), `owner.py`, `orphan_sweep.py`,
  `background.py`, `classification.py`). Tested helper extraction → ≤15. One file-group WP.

### IC-05 — Sync literals + suppression comments + misc (FR-007, FR-008, FR-009)

- `S1192` ×9 → constants; `S7632` ×7 → fix/remove; `S107` ×3 too-many-params (introduce a params object or
  keyword-only grouping — behavior-preserving); `S1172` ×2; `S6353` ×1 (regex `\w`, mind `re.ASCII` like
  #3232 WP04); `S7503` ×1; `S5713` ×2; `S5779` ×1 (assert-in-except); `S8572` ×2. Grouped by file.

### IC-06 — Verification

- Per WP: `ruff check` (incl. `C901`) + `mypy` + the touched modules' existing tests + the new helper tests,
  all green. No new suppressions (grep the diff). A fresh Sonar re-scan is post-merge; verify by inspection
  + the rule counts dropping.
