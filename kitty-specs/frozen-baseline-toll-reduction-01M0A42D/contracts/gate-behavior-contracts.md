# Gate-Behavior Contracts: Frozen-baseline toll reduction

Behavioral contracts for the changed gates and the new helper — hardened by a post-plan adversarial squad (feasibility/boundaries/coverage/anti-laziness) against the real code. These are the observable outcomes the WP tests must pin, with the **exact real symbols** to reuse (no re-implementation / split-brain).

## Contract A — Dead-symbol refresh helper (FR-001 / FR-002)

**Surface**: `tests/architectural/_refresh_dead_symbol_hashes.py` (new). Pure core seam: `refresh(corpus, decls, per_symbol, allowlist_source) -> rewritten_source` (inject the corpus so the NFR-001 regression can construct a tree; do not close over `_SRC_ROOT`). In-place rewrite via `tokenize` (mypy-clean), not regex.

**Authorities to reuse (single source of truth — do NOT re-implement):**
- **Still-dead set**: `test_no_dead_symbols._compute_offenders(decls, per_symbol, star_targets, allowlist=frozenset(), corpus, collision_index)` — with an **empty** allowlist it returns the full currently-dead `module::Name` set via the production aggregate path (`test_no_dead_symbols.py:1965`).
- **New key / hash**: `_resolve_final_key` (`test_no_dead_symbols.py:1806`); tier via `key_tier`, collisions via `classify_collisions` (`_symbol_key.py`). `classify_collisions` returns **all live `__all__` locations** — it has **no** deadness notion; deadness comes only from `_compute_offenders`.

| Input state | Required output | Pins |
|---|---|---|
| Allowlisted symbol still dead, body edited (gate RED with **offender**) | matching existing entry's `body_hash` rewritten; gate passes; no hand-edited hash; **entry tier preserved** (collision-tier keeps `module_path`) | SC-002, US1-AC1 |
| New uncalled `__all__` symbol whose `bare_name` collides with a dangling entry, different `module::Name` | helper **refuses** (fail-closed); new symbol **absent**; gate still **RED** | SC-006, NFR-001, US1-AC2 |
| Allowlisted symbol gained a caller, **body unchanged** | gate REDs with **stale** finding; not refreshed | US1-AC3 |
| Allowlisted symbol gained a caller **AND body edited** | gate REDs with **dangling** finding (old key no longer resolves; has caller so not an offender); not refreshed | US1-AC3 (edge) |
| Entry with 0 still-dead candidates (deleted/relocated) | not refreshed/invented; left to red | US1 edge |
| Entry whose content-tier `module_path` is **unrecoverable/ambiguous** (missing/malformed provenance comment, or ≥2 still-dead candidates) | helper **refuses** — **never** falls back to a bare-name-only corpus-wide match | **NFR-001 (silent-admit guard)** |

**Invariants**: iterate **existing entries only** (never append — this makes admitting a new dead symbol *structurally* impossible); reuse the authorities above as the single hashing authority; recover content-tier `module_path` from the provenance comment (see Contract A-norm) **as a fail-closed hint only, never for hashing**; refresh iff exactly one still-dead candidate after `module_path` narrowing, else refuse; preserve the entry's tier.

### Contract A-norm — provenance-comment normalization (mandatory, not optional)

The content-tier `module_path` recovery is AC2's safety hinge and is **source-only** (`SymbolKey` carries no comment attribute). The live allowlist has **≥3 formats** (verified: 176 trailing `# mod::Name`; ~19 trailing `# mod`-only without `::Name`; 159 with the comment on the *preceding* line or absent; some with parenthetical suffixes). The parser MUST handle all three (reconstruct `::Name` from `bare_name` for the mod-only form) and **fail closed** when absent.

| Requirement | Pins |
|---|---|
| A normalization pass rewrites every content-tier entry to a single canonical trailing `# module::Name` form | research risk #1 |
| A test asserts **every** content-tier allowlist entry carries a parseable provenance comment (defense-in-depth for the 7 duplicate content-tier `bare_name`s whose only discriminator is the comment) | NFR-001 |

## Contract B — Skip-marker growth (FR-003)

**Surface**: `tests/architectural/test_ratchet_baselines.py` — remove `_SKIP_MARKED_BLOCKS` from **both** `single_baselines` lists (growth arm `:307` **and** shrinkage-warns arm `:441`) + a dedicated `fast`-tier test.

**Teeth accounting (be precise about what this mission owns):**
- **Machine-caught, unchanged by this mission**: `_classify_yaml_block` frontmatter-wins (`test_example_round_trip.py:404-414`) + the `missing`→fail rule prevent a stray skip from silently *disabling* a tagged executable block. This is count-independent and **not** modified here — do not credit it as this mission's replacement teeth.
- **Review-caught, this mission's replacement**: the mandatory co-located `# round-trip: skip: <reason>` diff line (reason enforced by the existing `_SKIP_MARKER_RE`). A reviewer sees it in the PR diff. "A reviewer sees the diff" is not machine-assertable — do not write a test that merely asserts the regex exists.

| Input state | Required output | Pins |
|---|---|---|
| Legitimate new skip block added | **no hard CI failure**; growth emitted via `record_property` **and a test asserts that property fires on growth** (`record_property` is write-only in this repo today — `grep user_properties tests/` is empty — so it MUST be asserted, e.g. via `request.node.user_properties`, or the backstop is unverified) | SC-003, US2-AC1 |
| Author substitutes a skip-with-reason for a would-be-executable block (no frontmatter) | classifies as `skip`; **not machine-caught** — caught only by human review of the co-located reason line (disclosed trade, Decision 1) | US2-AC2 (partial) |
| Skip block removed | reduction still observed (shrink-tracked high-water mark) | US2-AC3 |
| Sibling `legacy_contract_allowlist=151` (C-001) | remains a **growth-fail** in `single_baselines` | NFR-003 |

## Contract C — Derived migration count (FR-004)

**Surface**: `tests/architectural/test_ratchet_baselines.py` — special-case `category_1` in **both** the growth (`:269`) and shrinkage-warns (`:405`) 7-category loops.

**Authority (single source — do NOT re-implement the predicate):** `baseline := len(_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS)` — the hand-curated frozenset in `test_no_dead_modules.py:119`, **already imported** at `test_ratchet_baselines.py:270/:405`. There is **no** exposed dead-migration-count accessor; deriving from a re-globbed `glob ∩ no-static-importer` predicate would create a `_has_caller` **split-brain**. Do not do it.

**Honest framing**: deriving the count makes the `category_1` count-check non-load-bearing — that is correct, because its change-detection role always lived in `test_no_dead_modules` (which validates the frozenset membership and is untouched). This removes the double-charge; it does not remove any real coverage.

| Input state | Required output | Pins |
|---|---|---|
| The `_CATEGORY_1` frozenset grows/shrinks (monkeypatched to size N) | the derived `category_1` expected tracks N in **both** arms, with **no `_baselines.yaml` edit** (the test exercises the derivation — it is NOT `assert 100 == 100`) | SC-001, US3-AC1/AC2 |
| The decorative `_baselines.yaml` `category_1: 100` sub-key | asserted `== len(_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS)` to keep the audit value from silently drifting | pedro nit |
| Attempt to derive the frozenset **contents** | out of scope — would make `test_no_dead_modules` vacuous | C-002b |

## Contract D — Inert-key removal (FR-005) & fast markers (FR-006)

| Change | Required output | Pins |
|---|---|---|
| Delete `test_no_dead_symbols:` YAML block; drain `_GRANDFATHERED_UNREGISTERED_KEYS`→`frozenset()` **+ coupled equality literal at `:530`** in lockstep; retire the stale RL-030 comment/docstring (`:133-143`, `:516-524`) | `test_ratchet_baselines` (incl. `test_no_unregistered_baseline_keys_are_added`) stays green; re-adding the key now **rejected** | US4-AC1 |
| Add `fast` to `test_ratchet_baselines` + `test_ratchet_positional_anchor_ban` module `pytestmark` | both selected under `-m fast`; `test_no_dead_symbols` (~72s) **not** selected | SC-005, US5, C-003 |
| **CI-routing verification (FR-006 blast radius)** | before landing, verify the `arch-adversarial` job's `-m` selector does **not** exclude `fast` (else dual-marking silently drops these two tests from the arch job); confirm against `test_marker_job_completeness.py` selection expressions | NFR-003 |
| **Fast-tier import hygiene** (NFR-002 assertable clause) | a test asserts `-m fast` **collection** does not import the `test_example_round_trip` corpus module (holds today only because `_import_module_attr` defers it; a refactor could regress it) | NFR-002 |
