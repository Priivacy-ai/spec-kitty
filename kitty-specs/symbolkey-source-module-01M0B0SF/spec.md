# Mission Specification: SymbolKey source_module provenance field

**Mission Branch**: `remediation/symbolkey-source-module-3552`
**Created**: 2026-08-18
**Status**: Draft
**Input**: Root-cause follow-up to #2853 (frozen-baseline toll reduction); closes #3552; parented under EPIC #1931. Scope locked by a four-lens research squad (design / invariants / code-state / related-work).

## User Scenarios & Testing *(mandatory)*

The actor throughout is a **repo developer/maintainer** working in the architectural
test suite. "The gate" means the dead-symbol architectural gate
(`tests/architectural/test_no_dead_symbols.py`) and its #2853 refresh helper
(`tests/architectural/_refresh_dead_symbol_hashes.py`).

### User Story 1 - Refresh a still-dead allowlisted symbol without touching a comment (Priority: P1)

A developer edits the body of a still-dead allowlisted symbol. The refresh helper
must recover which module that symbol came from to refresh its `body_hash` safely.
Today it can only do so by parsing a free-form provenance comment, failing closed
when the comment is missing or ambiguous — so a load-bearing safety property depends
on comment hygiene.

**Why this priority**: This is the root cause #3552 exists to remove. Machine-readable
provenance is what lets the helper work without comment-parsing.

**Independent Test**: With `source_module` populated, the helper resolves provenance
from the field alone; deleting/garbling the provenance comment does not change the
refresh decision.

**Acceptance Scenarios**:

1. **Given** an allowlist entry carrying `source_module=`, **When** the refresh helper decides its fate, **Then** it uses `source_module` (not the comment) to recover the module, and the decision is unchanged if the comment text is altered or removed.
2. **Given** the machine comment-parsing path has been retired, **When** the gate and helper run, **Then** no code reads the provenance comment for machine decisions.

---

### User Story 2 - Provenance recovery is independent of comment text (Priority: P1)

A developer garbles or removes the free-form `# module::Name` provenance comment on
an allowlist entry that carries `source_module`. The refresh helper must still recover
the correct originating module and reach the same decision — because provenance now
lives in a machine field, not in comment prose.

**Why this priority**: This is the falsifiable proof that comment-*dependence* is gone —
the core value of `source_module`. It is red-first constructible against today's
comment-parsing path.

**Independent Test**: Populate `source_module` on an entry, then alter/delete its
provenance comment; the helper's recovered module and refresh decision are unchanged.

**Acceptance Scenarios**:

1. **Given** an allowlist entry carrying `source_module=`, **When** its provenance comment is deleted or garbled and the helper runs, **Then** the recovered module and the refresh decision are identical to the run with an intact comment.

> **Scope boundary (post-plan squad, #3560 Finding-1):** a genuine *live* same-`bare_name`+same-`body_hash` collision still — correctly — escalates to `NEEDS_MODULE_PATH`. `source_module` is `compare=False`, so it is invisible to `final_key in allowlist` and to tier selection; it **cannot** and must **not** exempt a live collision (that would forfeit relocation-tolerance, C-002/G3). Such a collision is resolved the normal way — a hand-authored collision-tier `module_path=` entry — which is **orthogonal** to `source_module`. `decide()` and the `NEEDS_MODULE_PATH` outcome are unchanged by this mission.

---

### User Story 3 - One canonical provenance source (Priority: P2)

Provenance is split today: structured `module_path=` for the 25 collision-tier entries,
free-form comment for the 338 content-tier entries — the same fact (origin module) split
along a tier boundary. The developer should have a single canonical machine source.

**Why this priority**: SSOT hygiene; closes the whack-a-field trap of leaving two
provenance representations alive.

**Independent Test**: Every content-tier allowlist entry carries `source_module`; the
comment-parsing surfaces no longer exist in the codebase.

**Acceptance Scenarios**:

1. **Given** the mission is complete, **When** the content-tier entries are inspected, **Then** all 338 carry `source_module=`, and the `# module::Name` comment remains as human audit only.

### Edge Cases

- What happens if a future edit makes the field *comparing*? Every provenance-bearing entry would stop matching its resolver-minted key and the whole allowlist would false-red — the keystone guard (G6) must fail the instant `compare` is flipped.
- What happens if the backfill runs but the parse-path deletion does not (or vice-versa)? A half-retired state. Because `ruff` line-length (164) forces some backfilled entries to reflow — which shifts `Call.lineno` and would red the still-live parseable-comment test — the backfill and the parse-path retirement MUST land in **one** commit/WP (C-004).
- What happens when a content-tier entry is added later without `source_module`? Deleting the parseable-comment test removes the only completeness gate; a replacement completeness guard (FR-006) must fail if any content-tier allowlist entry lacks `source_module`, so SSOT is *kept*, not just achieved once.
- What if a backfilled `source_module` value is wrong (drift)? Deleting `_recover_provenance`'s `Name == bare_name` cross-check removes the only integrity net; an integrity guard (FR-007) must pin `source_module` against the retained audit comment / known corpus module so drift cannot silently move onto the field.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Non-hashing `source_module` field on `SymbolKey` | As a maintainer, I want `SymbolKey` to carry an optional `source_module` that is excluded from equality, hash, `body_hash`, `key_tier`, and `as_tuple()`, so provenance is machine-readable without affecting identity. | High | Open |
| FR-002 | Helper consumes `source_module` | As a maintainer, I want the refresh helper to recover a symbol's module from `source_module` (preferred over the comment), so refresh no longer depends on comment hygiene. | High | Open |
| FR-003 | Backfill all content-tier entries | As a maintainer, I want all 338 content-tier allowlist entries to carry `source_module`, applied by a scripted AST rewrite (not hand-edited), so provenance is complete and uniform. | High | Open |
| FR-004 | Retire the machine comment-parsing path | As a maintainer, I want the machine comment-parsing surfaces removed (`_PROVENANCE_COMMENT_RE`, `_content_tier_entry_lines`/`_comments_by_line`, `_comments_by_row`, `_recover_provenance` and its call, `AllowlistEntry.module_path`'s comment branch, the parseable-comment test), keeping the comment text as human audit, so there is one canonical provenance source. `Outcome.UNRECOVERABLE` is retained as the generic fail-closed backstop — only its comment-specific docstring is reworded. | High | Open |
| FR-005 | Comment-independent recovery | As a maintainer, I want the refresh helper to reach the same decision when a provenance comment is altered or deleted (given `source_module` is set), so a load-bearing property no longer depends on comment hygiene. A genuine live collision still correctly escalates to `NEEDS_MODULE_PATH` (unchanged); `source_module` never exempts it. | High | Open |
| FR-006 | Completeness guard | As a maintainer, I want a structural test that fails if any content-tier allowlist entry lacks `source_module=`, replacing the deleted parseable-comment completeness gate, so SSOT is kept as the corpus grows. | High | Open |
| FR-007 | Integrity guard | As a maintainer, I want a test that pins each entry's `source_module` against the **live importable corpus** (the named module exists and declares the symbol), replacing the deleted `_recover_provenance` cross-check — explicitly **not** by re-parsing the audit comment, so the guard does not recreate a machine comment-parser under a new name (that would defeat SC-004). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Identity invariance | Guard tests (G1–G6) prove `source_module` is excluded from `__eq__`/`__hash__`/`body_hash`/`key_tier`/`as_tuple()`; the SymbolKey allowlist cardinality is unchanged by the backfill (the count is taken from the allowlist-scoped reader, not a hardcoded literal — ≈338 content-tier + ≈25 collision-tier). Measured: all guard tests present and green; pre/post cardinality equal. | Correctness | High | Open |
| NFR-002 | No gate regression | The full `tests/architectural/test_no_dead_symbols.py` suite and the #2853 refresh-helper suite pass; `tests/architectural/test_ratchet_baselines.py` baselines are unchanged (no ratchet key added or moved). Measured: 0 failures, 0 baseline deltas. | Reliability | High | Open |
| NFR-003 | Lint/type/version hygiene | `ruff check` and `mypy --strict` are clean on every touched file; no `pyproject.toml` version bump (test-infra only, no `src/` change); a CHANGELOG entry is added. Measured: ruff 0, mypy 0, no version diff. | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Field never enters hash/tier | `source_module` MUST NOT participate in `body_hash` or `key_tier`. | Technical | High | Open |
| C-002 | No tier escalation | The field MUST NOT escalate content-tier entries to collision-tier; relocation-tolerance (D-1) is preserved (content-tier keys stay location-free for equality/hash). | Technical | High | Open |
| C-003 | No ratchet key | MUST NOT add any `_baselines.yaml` / `test_ratchet_baselines.py` key for `test_no_dead_symbols`; re-adding one REDs by design (`test_readding_inert_dead_symbols_key_is_now_rejected`). | Technical | High | Open |
| C-004 | Atomic retirement | The backfill (FR-003) and the parse-path deletion (FR-004) MUST land as one coherent change set — no half-retired state where the field is populated but comment-parsing is still live, or vice-versa. | Technical | High | Open |

### Key Entities

- **SymbolKey**: the dead-symbol identity (`tests/architectural/_symbol_key.py`). Content-tier = `(bare_name, body_hash)`; collision-tier adds `module_path`. Gains `source_module` as a non-comparing provenance attribute.
- **Allowlist entry**: a `SymbolKey(...)` call in `test_no_dead_symbols.py` with an accompanying `# module::Name` provenance comment. 338 content-tier + 25 collision-tier.
- **Refresh helper**: `_refresh_dead_symbol_hashes.py` — consumes provenance to refresh `body_hash`; today parses the comment, will read `source_module`.
- **Refresh-helper test suite**: `tests/architectural/test_refresh_dead_symbol_hashes.py` — in the blast radius: it builds `AllowlistEntry` via a local helper passing `provenance_module=`/`kwarg_module_path=` and asserts on `Outcome.UNRECOVERABLE`; its fixtures/assertions move with FR-002/FR-004. Its two `#3560` Finding-1 tests (`test_decide_escalates_content_tier_entry_needing_collision_tier`, `..._escalates_end_to_end`) assert `NEEDS_MODULE_PATH` is correct and **stay green** (unchanged).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of content-tier allowlist entries carry `source_module` after the mission — asserted by the completeness guard (FR-006) counting allowlist-scoped entries, not a hardcoded literal; 0 depend on comment-parsing for machine decisions.
- **SC-002**: With `source_module` set, deleting or garbling an entry's provenance comment does **not** change the helper's recovered module or refresh decision (red-first against today's comment-parsing path). A genuine live collision still escalates to `NEEDS_MODULE_PATH` (the two #3558 Finding-1 tests stay green).
- **SC-003**: All non-goal guard tests (G1–G6, incl. the keystone `compare is False` guard) are present and green; the SymbolKey allowlist cardinality is unchanged pre/post backfill (allowlist-scoped reader count).
- **SC-004**: Zero machine comment-parsing call-sites remain — mechanically checked: a grep/assert for `_recover_provenance`, `_PROVENANCE_COMMENT_RE`, `_comments_by_row`, and the parseable-comment test returns nothing; the comment text is retained as human audit. `Outcome.UNRECOVERABLE`'s fail-closed branch is retained (docstring reworded only).
