# Tasks: Docs Quality Gate Hardening

**Mission**: `docs-gate-hardening-01KZGAG2` | **Branch**: `docs/3253-docs-gaps`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Work-package decomposition of the Implementation Concern Map (plan.md), respecting the post-plan squad's lane shape and no-overlap ownership. `docs-freshness.yml` is written by **exactly one** WP (WP03) — IC-01 and IC-03 are NOT independent, so their workflow edits are serialized there.

## Lane / dependency shape

- **Lane A — WP01** (independent): docs-gate non-vacuity in `scripts/docs/` (publication resolver + related_validator). `depends-on: none`.
- **Lane B — WP02 → WP03** (serialized): WP02 authors the slash-command gate + backfills the doc; WP03 (the sole `docs-freshness.yml` owner) wires the CI step + adds the safety-structure test. **WP03 depends on WP02** (backfill+gate must exist before the CI step is wired, or CI reds).

Lanes A and B run in parallel; the only workflow-file collision is contained in WP03.

## Subtask Index (reference table — not a tracking surface)

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Extract `_vacuity_error()` shared builder (tidy-first, behavior-preserving; reproduce `I-01`/`I-02`/`expected at least` substrings verbatim) | WP01 | |
| T002 | Add `_assert_each_glob_nonvacuous(entries, config_path)` — per-`(entry, include-pattern)` raw pre-exclusion count ≥1, raises `ValueError` | WP01 | |
| T003 | Wire the per-glob guard into `resolve_published_pages` after the collect loop, before `_apply_exclusions`; preserve the 500 floor + `PublishedPageSet` return type | WP01 | |
| T004 | Negative test: one declared glob empty while aggregate ≥500 → `ValueError`; a per-entry check would pass (test_published_pages.py) | WP01 | |
| T005 | FR-004 propagation test: empty-glob fixture through `description_length_check` entry point → `CoverageError` | WP01 | [P] |
| T006 | Add `min_files` (default 1) non-vacuity floor to `related_validator.validate_related` → `RuntimeError` (mirror `relative_link_fixer.py`) | WP01 | [P] |
| T007 | Zero-file negative test for related_validator → `RuntimeError` (test_related_validator.py) | WP01 | [P] |
| T008 | Author `check_slash_command_freshness.py`: new `^##\s+/spec-kitty\.([a-z0-9-]+)\s*$` extractor + bidirectional diff vs `CONSUMER_SKILLS` (MISSING/EXTRA, non-zero exit) | WP02 | |
| T009 | Backfill `tasks-outline` / `tasks-packages` / `tasks-finalize` sections in `docs/api/slash-commands.md` (match existing per-section prose style; `<mission>` placeholders) | WP02 | |
| T010 | Committed negative test (MISSING and EXTRA directions) + green-after-backfill (test_check_slash_command_freshness.py) | WP02 | |
| T011 | Tidy-first (B0): hoist `PYTHONPATH: .` to a job-level `env:` in docs-freshness.yml; leave `SPEC_KITTY_ENABLE_SAAS_SYNC`/`NO_UPGRADE_CHECK` on their single step | WP03 | |
| T012 | Wire `check_slash_command_freshness.py` as a CI step in docs-freshness.yml (after WP02) | WP03 | |
| T013 | New `test_docs_freshness_invariant.py`: assert paths-allowlist present AND absent `tests/**`/`kitty-specs/**`; unfiltered `push:main` backstop; invariant comment present | WP03 | |
| T014 | FR-006: cross-reference the in-file invariant comment to the T013 test (reuse `ui-e2e.yml`'s "Required-check contract" idiom) | WP03 | |
| T015 | FR-007: add a note in docs-pages.yml that `seo_verify` runs push-only (`main`/`2.x`), no `pull_request` trigger | WP03 | [P] |

Record completion with `spec-kitty agent tasks mark-status T001 … --status done` (event-sourced; no checkboxes).

---

## Work Packages

### WP01 — Docs-gate non-vacuity (publication resolver + related_validator)

- **Goal**: Close the silent-under-collection band by making the published-page resolver fail loud when any declared include glob resolves (pre-exclusion) to zero pages, and add the same missing non-vacuity floor to `related_validator.py` (#3264, folded).
- **Priority**: P1 (FR-003) + P2 (FR-004, FR-008).
- **Independent test**: `pytest tests/docs/test_published_pages.py tests/docs/test_description_length_check_propagation.py tests/docs/test_related_validator.py` — negative fixtures raise; current tree passes (all 19 globs ≥1).
- **Subtasks**: T001, T002, T003, T004, T005, T006, T007.
- **Implementation sketch**: extract `_vacuity_error()` (behavior-preserving) → add per-glob helper on `entries` (raw pre-exclusion, `ValueError`) → wire after collect loop / before exclusions → negative + propagation tests → related_validator `min_files` floor + test.
- **Dependencies**: none (Lane A). **Owns**: `scripts/docs/_published_pages.py`, `scripts/docs/related_validator.py`, and their three tests. No workflow edit.
- **Risks**: per-glob attribution must come from `entries` (not the flattened `candidates`); guard runs pre-exclusion so `archive` (14 raw/0 post) doesn't false-fail; must raise `ValueError` for FR-004 propagation. ~380 lines.
- **Prompt**: [tasks/WP01-docs-gate-non-vacuity.md](./tasks/WP01-docs-gate-non-vacuity.md)

### WP02 — Slash-command gate + backfill

- **Goal**: A bidirectional, registry-anchored freshness gate for `docs/api/slash-commands.md`, plus backfill of the three missing command sections so the doc mirrors `CONSUMER_SKILLS` (15/15).
- **Priority**: P1 (FR-001, FR-002).
- **Independent test**: `pytest tests/docs/test_check_slash_command_freshness.py`; run `python scripts/docs/check_slash_command_freshness.py` → exit 0 after backfill; RED (exit 1) on the un-backfilled doc.
- **Subtasks**: T008, T009, T010.
- **Implementation sketch**: author the new heading extractor + gate (RED against today's 12/15) → backfill the three sections (GREEN) → committed negative test for both drift directions.
- **Dependencies**: none. **Owns**: `scripts/docs/check_slash_command_freshness.py` (new), `docs/api/slash-commands.md`, `tests/docs/test_check_slash_command_freshness.py` (new). Does NOT touch `docs-freshness.yml`.
- **Risks**: `check_cli_reference_freshness._HEADING_RE` does not match the slash+dot form — author a new extractor. Backfill prose must match existing style + `<mission>` (C-004). ~320 lines.
- **Prompt**: [tasks/WP02-slash-command-gate.md](./tasks/WP02-slash-command-gate.md)

### WP03 — docs-freshness wiring + safety-structure test

- **Goal**: Wire the slash-command gate into CI, encode the docs-freshness safety structure as a repo-readable test, and record the deploy-side note — all edits to `docs-freshness.yml` live here.
- **Priority**: P1 (FR-001 CI wiring) + P2 (FR-005, FR-006) + P3 (FR-007).
- **Independent test**: `pytest tests/docs/test_docs_freshness_invariant.py`; CI docs job invokes the slash gate and stays green.
- **Subtasks**: T011, T012, T013, T014, T015.
- **Implementation sketch**: B0 hoist PYTHONPATH (behavior-preserving) → wire the slash-gate CI step → author the safety-structure test (absence-from-allowlist, backstop, comment) → cross-ref the invariant comment → docs-pages.yml note.
- **Dependencies**: **WP02** (backfill + gate must exist before the CI step is wired). **Owns**: `.github/workflows/docs-freshness.yml`, `.github/workflows/docs-pages.yml`, `tests/docs/test_docs_freshness_invariant.py` (new).
- **Risks**: hoist ONLY `PYTHONPATH` to job-level; FR-005 asserts absence-from-allowlist (no `!tests/**` pattern exists) and must not hardcode `required=={drift-detector}` (conflicts with `ui-e2e.yml`). ~340 lines.
- **Prompt**: [tasks/WP03-docs-freshness-structure.md](./tasks/WP03-docs-freshness-structure.md)

---

## MVP

**WP01** (Lane A) is the standalone MVP slice: it closes the mission's core thesis (the silent-under-collection band) plus the folded #3264, independently testable with no workflow changes.

## Implement-time gate (DIR-012)

Before the first WP is claimed, assign issue **#3253** to the HiC (tracker rule). `/spec-kitty.analyze` must run before any WP is implemented (the implement gate enforces `analysis_report_required`).
