# Tasks: SymbolKey source_module provenance field (#3552)

**Mission**: symbolkey-source-module-01M0B0SF · **Branch**: `remediation/symbolkey-source-module-3552`
**Scope**: Option A (provenance-only), re-scoped by the post-plan squad.

Subtask completion is event-sourced — record with
`spec-kitty agent tasks mark-status Txxx --status done`. Rows below are references, not checkboxes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `source_module: str \| None = field(default=None, compare=False)` to `SymbolKey` (+ `field` import; reword docstring) | WP01 | |
| T002 | G6 keystone guard: `fields(SymbolKey)['source_module'].compare is False` | WP01 | [P] |
| T003 | G1/G2 guards: equality + hash + frozenset membership invariant across differing/absent `source_module` | WP01 | [P] |
| T004 | G3/G4 guards: content-tier stays `is_content_tier`, `key_tier` unescalated; `as_tuple()` excludes the field | WP01 | [P] |
| T005 | G5 guard: resolver-minted key has `source_module is None`; `body_hash` unaffected by a provenance peer | WP01 | [P] |
| T006 | Verify WP01: ruff + mypy --strict clean; G1–G6 green | WP01 | |
| T007 | Backfill script: call the existing verified reader to source each entry's module, assert reader count == backfilled count, reflow E501 (>164) to canonical multiline; run it to populate `source_module=` on every content-tier entry | WP02 | |
| T008 | Rewire `AllowlistEntry.module_path` → `source_module`; delete `_recover_provenance` + its call and `_comments_by_row` | WP02 | |
| T009 | Delete the 3 `test_no_dead_symbols.py` parse surfaces (`_PROVENANCE_COMMENT_RE`, `_content_tier_entry_lines`/`_comments_by_line`, `test_every_content_tier_entry_has_parseable_provenance_comment`) — same commit as the T007 reflow | WP02 | |
| T010 | Reword (do NOT delete) `Outcome.UNRECOVERABLE`'s comment-specific docstring; keep the fail-closed branch | WP02 | |
| T011 | Add FR-006 completeness guard (`test_every_content_tier_entry_has_source_module`) + FR-007 integrity guard (`source_module` ↔ retained audit comment / known module) | WP02 | |
| T012 | Add FR-005 comment-independent-recovery test (garble/delete comment → decision unchanged) — red-first against the pre-rewire path | WP02 | |
| T013 | Update `test_refresh_dead_symbol_hashes.py` `AllowlistEntry` fixtures / `UNRECOVERABLE` asserts; confirm the two #3560 Finding-1 tests stay green | WP02 | |
| T014 | Verify WP02: ruff + mypy --strict; `test_no_dead_symbols` + refresh-helper + `test_ratchet_baselines` green; allowlist cardinality unchanged | WP02 | |
| T015 | CHANGELOG entry (`docs/changelog/CHANGELOG.md`) — consumer-focused, test-infra-only, no version bump | WP03 | |
| T016 | Confirm `test_ratchet_positional_anchor_ban.py` needs no change (squad expects none); note it in the WP | WP03 | |
| T017 | Verify WP03: terminology guard + markdownlint on the changelog | WP03 | |

## Work Packages

### WP01 — SymbolKey source_module field + G1–G6 non-goal guards

- **Goal**: Add the non-hashing `source_module` field and pin the invariants that keep it out of identity. Foundation.
- **Priority**: P1 · **Depends on**: none
- **Independent test**: `pytest tests/unit/test_symbol_key.py` — G1–G6 green; `_symbol_key.py` ruff + mypy --strict clean. Nothing else changes → suite stays green on this commit alone.
- **Subtasks**: T001–T006 · **Prompt**: `tasks/WP01-symbolkey-field-and-guards.md` (~250 lines)
- **Risks**: R1 (comparing field false-reds the whole allowlist) — closed by construction + G6.

### WP02 — Backfill + helper rewire + parse retirement + completeness/integrity guards (ATOMIC)

- **Goal**: Populate `source_module` on every content-tier entry, rewire the helper to read it, delete the machine comment-parse surfaces, and add the completeness + integrity guards — **all in one commit** so the suite is green before and after, never mid-way.
- **Priority**: P1 · **Depends on**: WP01
- **Independent test**: full `tests/architectural/test_no_dead_symbols.py` + `test_refresh_dead_symbol_hashes.py` + `test_ratchet_baselines.py` green; garble-comment test passes; cardinality unchanged.
- **Subtasks**: T007–T014 · **Prompt**: `tasks/WP02-backfill-rewire-retire.md` (~480 lines)
- **⚠️ Atomicity (C-004)**: MUST be one WP on one lane. `ruff` line-length 164 forces some backfilled entries to reflow, which shifts `Call.lineno` and reds the still-live parseable-comment test — so the reflow (T007) and that test's deletion (T009) must co-commit. Do NOT split across lanes.
- **Risks**: highest regression risk — scripted, verified against `git diff`; `decide()`/`NEEDS_MODULE_PATH` unchanged (confirm, don't rewrite).

### WP03 — Docs + changelog

- **Goal**: Consumer-focused CHANGELOG entry; confirm the anchor-ban gate needs no change.
- **Priority**: P2 · **Depends on**: WP02
- **Independent test**: terminology guard green; markdownlint 0 on the changelog.
- **Subtasks**: T015–T017 · **Prompt**: `tasks/WP03-docs-changelog.md` (~150 lines)

## Dependencies

- WP01 → WP02 → WP03 (strictly linear). No parallel lanes (WP02 is atomic and single-lane).

## MVP

WP01 + WP02 deliver the whole feature (field + backfill + SSOT). WP03 is the record.
