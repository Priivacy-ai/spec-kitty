# Tasks: Frozen-baseline toll reduction

**Mission**: `frozen-baseline-toll-reduction-01M0A42D` | **Branch**: `fix/frozen-baseline-toll-reduction`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contracts**: [contracts/gate-behavior-contracts.md](./contracts/gate-behavior-contracts.md)

Acceptance criteria are taken **verbatim** from the gate-behavior contracts (non-fakeable, post-plan-squad-hardened). `finalize-tasks` computed **three** lanes (`lanes.json`): the helper chain is `lane-a` (WP01) → `lane-b` (WP02, `depends_on_lanes: [lane-a]`, `parallel_group: 1`); the baseline-file work is `lane-c` (WP03, `parallel_group: 0`). WP01 ∥ WP03 start together; WP02 follows WP01. No cross-chain dependency.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Audit + catalog the 3 live provenance-comment formats across the content-tier allowlist | WP01 | |
| T002 | Normalize every content-tier entry to canonical trailing `# module::Name` (reconstruct `::Name` for `# mod`-only) | WP01 | |
| T003 | Add a test asserting every content-tier allowlist entry carries a parseable provenance comment | WP01 | |
| T004 | Verify `test_no_dead_symbols` stays green (comments only, no key changes) | WP01 | |
| T005 | Create `_refresh_dead_symbol_hashes.py` pure core `refresh(corpus, decls, per_symbol, allowlist_source) -> rewritten_source` (injected corpus) | WP02 | |
| T006 | Wire still-dead + new-hash authority via `_compute_offenders(..., frozenset())` + `_resolve_final_key` (single hashing authority) | WP02 | |
| T007 | Implement fail-closed match (identity-minus-hash; `module_path` from key/provenance-comment; exactly-one-still-dead else refuse; unrecoverable/≥2 ⇒ refuse; tier-preserving `tokenize` rewrite) | WP02 | |
| T008 | Add the `python -m tests.architectural._refresh_dead_symbol_hashes` entrypoint | WP02 | |
| T009 | Non-fakeable NFR-001/SC-006 regression: positive control (X refreshed) + Y bare_name-collision not admitted + candidate-set ≥2→{X} assertion + all four Contract-A refuse branches exercised by running the helper | WP02 | |
| T010 | AC3 edge tests: gained-caller body-unchanged → `stale`; gained-caller + body-edit → `dangling`; collision-tier tier preservation | WP02 | |
| T011 | ruff + mypy `--strict` clean; complexity ≤ 15 (WP02 surfaces) | WP02 | |
| T012 | FR-004: derive `category_1` as `len(_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS)` in the growth arm (`:269`) | WP03 | |
| T013 | FR-004: derive in the shrinkage-warns arm (`:405`) + assert the decorative `_baselines.yaml` `category_1` `== len(frozenset)` | WP03 | |
| T014 | FR-004: monkeypatch-the-frozenset derivation test (proves derivation, not `assert 100==100`; incl. US3-AC2 shrink case) | WP03 | |
| T015 | FR-003: remove `_SKIP_MARKED_BLOCKS` from **both** `single_baselines` lists (`:307`, `:441`); dedicated non-failing `fast`-tier test that **asserts the `record_property` growth record fires** | WP03 | |
| T016 | FR-003 NFR-003 guard: `legacy_contract_allowlist=151` stays a growth-fail in `single_baselines` | WP03 | |
| T017 | FR-005: delete inert `test_no_dead_symbols:` YAML block; drain `_GRANDFATHERED_UNREGISTERED_KEYS`→`frozenset()` + coupled equality literal (`:530`); retire stale RL-030 prose (`:133-143`, `:516-524`) | WP03 | |
| T018 | FR-006: add `fast` to both gates' module `pytestmark` | WP03 | |
| T019 | FR-006: verify the `arch-adversarial` `-m` selector does not exclude `fast`; add a `-m fast` collection import-hygiene test (no corpus import) | WP03 | |
| T020 | ruff + mypy clean; full load-bearing-gate green sweep (NFR-003, C-001) | WP03 | |

## Work Packages

### WP01 — Provenance-comment normalization (Lane 1)
- **Goal**: Give the content-tier dead-symbol allowlist a single canonical, parseable `# module::Name` provenance comment on every entry — the fail-closed identity hint WP02's safe match depends on.
- **Priority**: P1 (precondition for WP02). **Independent test**: every content-tier entry parses; `test_no_dead_symbols` green (comments-only diff).
- **Subtasks**: T001, T002, T003, T004
- **Depends on**: none. **Est.**: ~220 lines.
- **Risk**: 3 live formats (176 trailing `::Name`, ~19 `# mod`-only, 159 preceding/absent); mechanical big diff — isolate for review.

### WP02 — Refresh helper + fail-closed match + non-fakeable regression (Lane 1)
- **Goal**: A `tokenize`-based helper that refreshes `body_hash` for still-dead allowlisted symbols and is **structurally incapable** of admitting a new dead symbol (fail-closed on ambiguity), proven by a regression that runs the helper.
- **Priority**: P1 (the mission's safety-critical concern). **Independent test**: the NFR-001/SC-006 regression (positive control + collision + candidate-set assertion).
- **Subtasks**: T005, T006, T007, T008, T009, T010, T011
- **Depends on**: WP01. **Est.**: ~420 lines.
- **Risk**: content-tier key is location-free; `module_path` recovery is the AC2 hinge — fail-closed, never bare-name-only fallback.

### WP03 — Baseline-file toll drains: derive count / skip-marker warn / inert-key / fast markers (Lane 2)
- **Goal**: Drain the four genuine-toll behaviors in `test_ratchet_baselines.py` + `_baselines.yaml` (+ fast-mark the two cheap gates) without weakening any load-bearing sibling.
- **Priority**: P2. **Independent test**: derive-count derivation test; skip-marker no-hard-fail + `record_property` assertion; re-entry rejection; `-m fast` selects both gates; load-bearing gates green.
- **Subtasks**: T012, T013, T014, T015, T016, T017, T018, T019, T020
- **Depends on**: none (Lane 2). **Est.**: ~470 lines.
- **Risk**: FR-003/FR-004 each touch two loop arms; NFR-003 surgical extraction near `legacy_contract_allowlist=151`; FR-006 CI-routing selector.

## MVP / sequencing

- **Lane 1** (`WP01 → WP02`) is the safety-critical MVP — it delivers the highest-value toll fix (dead-symbol hash refresh) with the anti-vacuity teeth.
- **Lane 2** (`WP03`) runs fully in parallel (file-disjoint) and delivers the remaining three toll drains + fast markers.
- Deferred follow-on (out of scope): [#3552](https://github.com/Priivacy-ai/spec-kitty/issues/3552) (non-hashing `source_module` field — root fix for the provenance-comment fragility).
