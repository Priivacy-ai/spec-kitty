# Implementation Plan: SymbolKey source_module provenance field

**Mission**: symbolkey-source-module-01M0B0SF
**Branch**: `remediation/symbolkey-source-module-3552` (planning base and merge target)
**Closes**: #3552 · **Refs**: #2853, #3560 · **Epic**: #1931

## Summary

Add an optional, non-hashing `source_module` attribute to `SymbolKey`
(`tests/architectural/_symbol_key.py`) so dead-symbol allowlist entries carry a
stable machine identity for disambiguation. Backfill it across all 338 content-tier
entries via a scripted AST rewrite, rewire the #2853 refresh helper to read the
field (retiring the machine comment-parsing surfaces, keeping comment text as human
audit), and pin non-goal guards so the field can never enter `body_hash`/`key_tier`
or escalate content-tier to collision-tier. Relocation-tolerance (D-1) is preserved
because the field is excluded from equality/hash by construction.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: stdlib `dataclasses` + `ast` (no new third-party dependency); `pytest`, `ruff`, `mypy` (existing)
**Storage**: N/A (in-repo test allowlist source)
**Testing**: `pytest` — targeted `tests/architectural/test_no_dead_symbols.py`, `tests/architectural/test_refresh_dead_symbol_hashes.py`, and new non-goal guards in `tests/unit/test_symbol_key.py`; `ruff` + `mypy --strict` on every touched file
**Target Platform**: Developer/CI Python environment (test infrastructure only)
**Project Type**: single (test-infrastructure change; no `src/` change)
**Performance Goals**: N/A — no runtime/latency surface; the backfill is a one-time authoring rewrite
**Constraints**: `source_module` MUST NOT enter `body_hash`/`key_tier`; MUST NOT escalate content-tier→collision-tier (D-1 relocation-tolerance preserved); MUST NOT add any `_baselines.yaml`/`test_ratchet_baselines.py` key; backfill + parse-path deletion MUST land atomically; no `pyproject.toml` version bump
**Scale/Scope**: ~363 allowlist entries (~338 content-tier to backfill + ~25 collision-tier already structured; exact counts taken from the allowlist-scoped reader at implementation time, never hardcoded — a whole-file grep over-counts by including test-body synthetics); 7 machine comment-parse surfaces to retire; ~5 touched files

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** — ✅ `source_module` becomes the single canonical machine provenance source; the split comment/`module_path=` representation is unified (retires the whack-a-field risk).
- **Architectural alignment** — ✅ Extends the existing `SymbolKey` tiered design; no new seam. Non-goals (C-001/C-002) mirror the issue and are pinned by guard tests.
- **DDD + tiered rigour** — ✅ Test-infra glue tier; the change is contained to the architectural test surface.
- **ATDD-first** — ✅ The #3560 Finding-1 collision is the acceptance anchor (FR-005/SC-002); non-goal guards (G1–G6) are red-first authored.
- **Terminology adherence** — ✅ No product terminology touched; `source_module` is a test-infra field name.
- **Tech-debt standing orders** — ✅ Campsite: retires the duplicate `_comments_by_row`/`_comments_by_line` provenance readers (SSOT). No baseline gaming.

No violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/symbolkey-source-module-01M0B0SF/
├── spec.md              # committed
├── plan.md              # this file
├── research.md          # Phase 0 output (condensed from the squad dossiers)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (non-goal invariants contract)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
tests/architectural/_symbol_key.py                 # FR-001: add the field
tests/architectural/test_no_dead_symbols.py         # FR-003 backfill; FR-004 retire parse surfaces; FR-006/FR-007 guards
tests/architectural/_refresh_dead_symbol_hashes.py  # FR-002 consume field; retire _recover_provenance/_comments_by_row; reword UNRECOVERABLE docstring
tests/architectural/test_refresh_dead_symbol_hashes.py # blast radius: AllowlistEntry fixtures/UNRECOVERABLE asserts; #3560 tests stay green
tests/unit/test_symbol_key.py                       # NFR-001: G1–G6 non-goal guards
docs/changelog/CHANGELOG.md                          # NFR-003 entry
```

## Complexity Tracking

*None — Charter Check passes with no violations.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

> **Post-plan squad revision (Option A — provenance-only).** `source_module`
> is provenance-for-narrowing; it does **not** resolve the #3560 Finding-1 live
> collision (that stays a correct `NEEDS_MODULE_PATH` escalation). The former
> IC-02 (backfill) and IC-03 (parse retirement) are **merged into one atomic
> concern** because `ruff` (line-length 164) forces some backfilled entries to
> reflow, which shifts `Call.lineno` and reds the still-live parseable-comment
> test — so the reflow and that test's deletion must land in the same commit.

### IC-01 — Non-hashing field + non-goal guards

- **Purpose**: Add `source_module: str | None = field(default=None, compare=False)` to `SymbolKey` and pin the invariants that keep it out of identity.
- **Relevant requirements**: FR-001; NFR-001; C-001; C-002.
- **Affected surfaces**: `tests/architectural/_symbol_key.py`; `tests/unit/test_symbol_key.py` (G1–G6, keystone G6 = `fields(SymbolKey)[...'source_module'].compare is False`).
- **Sequencing/depends-on**: none (foundation). Green on its own commit (adds a defaulted field + guards; nothing else changes).
- **Risks**: R1 (critical) — a *comparing* field false-reds the whole allowlist; closed by construction + G6. R4 — a "consistency" edit appends the field to `as_tuple()`; pinned by G4.

### IC-02 — Backfill + helper rewire + parse retirement (ONE atomic WP, same lane)

- **Purpose**: Populate `source_module=` on every content-tier entry (scripted), rewire the helper to read it, delete the machine comment-parse surfaces, and add the completeness + integrity guards — all in one commit so the suite is green before and after, never mid-way.
- **Relevant requirements**: FR-002; FR-003; FR-004; FR-005; FR-006; FR-007; C-004; SC-001; SC-002; SC-004.
- **Affected surfaces**:
  - `test_no_dead_symbols.py`: backfill entries; delete `_PROVENANCE_COMMENT_RE`, `_content_tier_entry_lines`/`_comments_by_line`, `test_every_content_tier_entry_has_parseable_provenance_comment`; add `test_every_content_tier_entry_has_source_module` (FR-006) and a `source_module`↔audit-comment integrity guard (FR-007).
  - `_refresh_dead_symbol_hashes.py`: `AllowlistEntry.module_path` returns `source_module`; delete `_recover_provenance` + its call and `_comments_by_row`; **reword** (do not delete) the `Outcome.UNRECOVERABLE` branch — it stays the generic fail-closed backstop.
  - `test_refresh_dead_symbol_hashes.py`: update `AllowlistEntry` fixtures / `UNRECOVERABLE` asserts; the two #3560 Finding-1 tests stay green (assert `NEEDS_MODULE_PATH` — unchanged).
- **Backfill mechanics (pin before tasks)**: source values by calling the existing **verified** reader (`_content_tier_entry_lines`/`_comments_by_line`) one last time *before* deleting it; assert the reader's own allowlist-scoped count equals the number backfilled (turns SC-001 into a mechanical gate, no hardcoded literal). Handle E501: the script must reflow entries that exceed 164 to a canonical multi-line form in the same pass; because that shifts `lineno`, the parseable-comment test is deleted in the same commit.
- **Sequencing/depends-on**: IC-01. `decide()`/`NEEDS_MODULE_PATH` logic is unchanged (confirm, don't rewrite).
- **Risks**: highest regression risk — scripted, verified against `git diff`; must be one WP on one lane (both `test_no_dead_symbols.py` and `_refresh_dead_symbol_hashes.py` owned by this WP) so no out-of-order lane consolidation can create the half-retired state C-004 forbids.

### IC-03 — Docs + changelog

- **Purpose**: CHANGELOG entry; update any docstring/CLAUDE.md note referencing the provenance-comment mechanism; confirm `test_ratchet_positional_anchor_ban.py` needs no update once `source_module=` kwargs appear (squad confirmed it targets positional int anchors, not kwargs — expected no change).
- **Relevant requirements**: NFR-003.
- **Affected surfaces**: `docs/changelog/CHANGELOG.md`; docstrings in the touched files.
- **Sequencing/depends-on**: IC-02.
- **Risks**: markdownlint file-scope on CHANGELOG; run the terminology guard after prose edits.
