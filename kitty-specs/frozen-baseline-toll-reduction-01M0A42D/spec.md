# Mission Specification: Frozen-baseline toll reduction

**Mission Branch**: `fix/frozen-baseline-toll-reduction`
**Created**: 2026-08-18
**Status**: Draft (revised after post-spec adversarial squad)
**Input**: The #2853 **broader ask** (source-derived counts, warning-not-fail, run gates in the fast/local suite) — distinct from the golden-count classifier facet (#3458) already shipped in PR #3538. Scoped via a two-facet researcher-robbie pass and hardened by a 4-lens post-spec squad, all verified against the tree. Brief: `docs/plans/testing/friction-burn-down-sequencing.md`.

## Overview

Spec Kitty's frozen-absolute-baseline architectural gates hard-fail CI when a count or hash they pin moves. A verified scoping pass separated the family into **load-bearing gates** (P0-security boundaries, still-shrinking burn-downs, zero-pins, change-detectors — which keep their teeth) and a **narrow set of genuine-toll gates** that tax legitimate *additive* change with a manual baseline edit that catches no real defect and is discovered only in CI. This mission drains that narrow toll set and leaves every load-bearing gate untouched.

> **Anti-vacuity discipline (load-bearing):** the mission's safety-critical requirement is that the toll fixes must not quietly *weaken* the gates they touch. Acceptance criteria here are written to be non-fakeable — a fixture must reach the actual decision point it claims to test (the F1 lesson from #3458). See FR-002 / NFR-001 / SC-006.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Editing a dead symbol no longer forces a manual hash refresh (Priority: P1)

A maintainer edits the body of a symbol legitimately on the `test_no_dead_symbols` allowlist (a public `__all__` symbol with no runtime caller). Today the edited body changes the live `body_hash`, so `_compute_offenders` REDs the gate with an **offender** finding (the new key is un-allowlisted) and the old entry is suppressed — the author must hand-refresh the allowlist hash, a mechanical toll (the "rehashed WPxx" cadence) that catches nothing. After this mission the author runs a single refresh helper that recomputes hashes for **entries already in the allowlist whose symbol is still dead**, and the gate is green — **without** the helper ever admitting a *new* dead symbol, including the dangerous case where a new dead symbol shares a `bare_name` with an existing entry.

**Why this priority**: The biggest recurring toll in the family, and the one with real safety nuance — the membership gate must stay load-bearing across a hash change, and the content-tier key is deliberately location-free, so re-identifying "the same symbol" is a genuine design decision (FR-002).

**Independent Test**: Edit a still-dead allowlisted symbol's body → gate REDs with an **offender** finding → run the refresh helper → gate green, with no hand-edited hash. Separately, add a *new* uncalled `__all__` symbol whose `bare_name` collides with an existing allowlist entry → run the helper → the new symbol is **not** admitted and the gate still REDs.

**Acceptance Scenarios**:

1. **Given** an allowlisted still-dead symbol whose body was edited (gate RED with an *offender* finding), **When** the refresh helper runs, **Then** the matching existing allowlist entry's hash is updated and `test_no_dead_symbols` passes — with no hand-edited hash.
2. **Given** a newly-added uncalled `__all__` symbol whose `bare_name` is **identical** to an existing (now-dangling) allowlist entry but whose `module::Name` differs, **When** the helper runs, **Then** the helper **refuses to refresh onto it (fail-closed on `bare_name` ambiguity)**, the new symbol is absent from the resulting allowlist, and the gate still REDs. *(This fixture differs from Scenario 1 by exactly one thing — it has no legitimately-matching dangling entry — so it exercises the helper's admit decision, not an unrelated skip.)*
3. **Given** an allowlisted symbol that has since gained a runtime caller, **When** the gate is evaluated, **Then** it still REDs with a **stale** finding; the helper does not silence a now-wired symbol.

### User Story 2 - Adding a legitimate skip-marker no longer hard-fails CI (Priority: P2)

An author adds a legitimate `# round-trip: skip: <reason>` block to a non-executable contract example. Today the grow-only `skip_marker_blocks` baseline (live value **13**) is exceeded and CI **hard-fails** until someone bumps the number. That hard-fail is a *review-forcing* mechanism (its design purpose is to make each new skip explicit), but it blocks the build on routine legitimate growth. After this mission, routine growth is permitted without a blocking CI failure, while the change is **still forced into a reviewer's view** (reviewability-with-teeth) and a genuine regression is not silenced.

**Why this priority**: Frequent, blocks the build on legitimate additive growth; but its replacement must preserve review-forcing, so it carries design care (C-002).

**Independent Test**: Add a legitimate skip-marker block → CI does not hard-fail → the growth is surfaced in a channel a reviewer encounters during PR review. Separately, introduce a skip-marker where a frontmatter contract is expected → the replacement signal does **not** silence it.

**Acceptance Scenarios**:

1. **Given** a legitimately-added skip-marker block, **When** the gate runs in CI, **Then** it does not hard-fail, and the growth is surfaced where a reviewer encounters it during PR review (not only stderr in an otherwise-green job).
2. **Given** a skip-marker introduced where an executable frontmatter contract is expected (a genuine regression), **When** the gate runs, **Then** the replacement signal does **not** silence it (the anti-silencing property holds).
3. **Given** a skip-marker block was removed, **When** the gate runs, **Then** the reduction is still observed (shrinkage is not lost).

### User Story 3 - Adding a migration module no longer double-charges the baseline (Priority: P2)

A maintainer adds an auto-discovered `m_*.py` migration module with no static importer. Today it REDs **two** gates: the `_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS` frozenset in `test_no_dead_modules.py` (the module must be named) **and** the redundant `category_1_auto_discovered_migrations` **count** in `_baselines.yaml` — a double-charge, since the count is just the length of that frozenset/dead-set. After this mission the **count baseline is derived** from the gate's own dead-migration authority (glob ∩ no-static-`src/`-importer), so the count no longer needs a manual bump. Whether the frozenset hand-list itself is toll (convert to warn) or a load-bearing change-detector (keep) is a plan-phase decision (see C-002) — deriving the frozenset *contents* would make `test_no_dead_modules` vacuous and is out of scope.

**Why this priority**: Removes a pure double-charge with no vacuity risk; the harder frozenset question is deferred, not forced.

**Independent Test**: Add a new auto-discovered dead migration module → the `category_1` **count** gate passes with no `_baselines.yaml` edit (the count is derived from the gate's dead-migration authority).

**Acceptance Scenarios**:

1. **Given** a new auto-discovered dead migration module, **When** the `category_1` count gate runs, **Then** it passes with no `_baselines.yaml` edit because the expected count is derived from the gate's dead-migration authority (glob ∩ no-static-importer), not a raw `m_*.py` glob.
2. **Given** a migration module that gains a static importer, **When** the gate runs, **Then** the derived count reflects the reduced dead-set without a manual edit (the derivation tracks the *gate's* predicate, not the file count).

### User Story 4 - The inert dead-symbol baseline key is fully removed (Priority: P3)

The `test_no_dead_symbols:` block in `_baselines.yaml` is a grandfathered key that no comparison reads, and `_GRANDFATHERED_UNREGISTERED_KEYS` in `test_ratchet_baselines.py` grandfathers it — a standing hole through which re-adding that exact key stays silently permitted. After this mission the YAML block is deleted **and** the grandfather residue is drained (constant → `frozenset()`, with the coupled equality literal updated in lockstep), closing the re-entry hole (RL-030).

**Why this priority**: Cleanup; near-zero risk, but must be complete or it swaps one inert artifact for another.

**Independent Test**: Delete the block, drain `_GRANDFATHERED_UNREGISTERED_KEYS` to `frozenset()`, update the coupled literal → `test_ratchet_baselines` (incl. `test_no_unregistered_baseline_keys_are_added`) stays green, and re-adding a `test_no_dead_symbols:` key would now be rejected.

**Acceptance Scenarios**:

1. **Given** the inert `test_no_dead_symbols:` block and its grandfather entry, **When** both the YAML block and the `_GRANDFATHERED_UNREGISTERED_KEYS` entry (with its coupled equality literal) are removed, **Then** all `test_ratchet_baselines` checks remain green and the re-entry hole is closed.

### User Story 5 - Authors run the two cheap gates under the fast marker (Priority: P2)

The two sub-second architectural gates (`test_ratchet_baselines`, `test_ratchet_positional_anchor_ban`) run only in the CI `arch-adversarial` tier, so a baseline red surfaces only after pushing. After this mission they carry the `fast` marker and are selectable in a local `-m fast` run, shrinking the feedback loop. **No pre-push harness is built** and the ~72s `test_no_dead_symbols` is **not** `fast`-marked (kept out of the fast tier).

**Why this priority**: Near-zero-cost feedback-loop shortening for the cheapest gates.

**Independent Test**: Run `pytest -m fast` → both sub-second gates are selected and execute; `test_no_dead_symbols` is not selected by `-m fast`.

**Acceptance Scenarios**:

1. **Given** the two sub-second gates, **When** a `-m fast` run executes, **Then** both are selected and run.
2. **Given** `test_no_dead_symbols` (~72s), **When** `-m fast` runs, **Then** it is **not** selected.

### Edge Cases

- **Bare_name collision (US1-AC2):** a new dead symbol sharing a `bare_name` with an existing dangling entry MUST NOT be silently refreshed-onto; the helper fails closed on ambiguity rather than guessing.
- **Body-edited AND gained-a-caller simultaneously:** such a symbol REDs as **dangling** (new key un-allowlisted, has a caller → not an offender; old entry orphaned). A naive "refresh dangling entries" helper would re-admit a now-wired symbol; the helper MUST NOT refresh an entry whose symbol now has a caller (defer to the `stale` check).
- **Migration derivation predicate:** the derived count MUST equal the gate's own deadness computation (glob ∩ no-static-importer), never a raw `m_*.py` file glob (which over-counts by the statically-imported set).
- **Anti-silencing (US2-AC2):** the FR-003 replacement MUST NOT silence a skip-marker introduced where a frontmatter contract is expected.
- **Frozenset vacuity (FR-004):** deriving the `_CATEGORY_1` frozenset *contents* (not just the count) would make `test_no_dead_modules` a tautology — explicitly out of scope.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Dead-symbol hash-refresh helper | Provide a helper that recomputes `body_hash` for allowlist entries whose symbol is **still dead**, so editing a dead symbol's body does not force a manual hash edit. | High | Open |
| FR-002 | Refresh identity is safe and explicit | The helper MUST derive its refresh domain from **existing allowlist entries** (identity-minus-hash: `bare_name` [+ `module_path`]), never from the live dead-set; MUST reuse the gate's own resolver/classifier as the single hashing authority (not a private recompute); and MUST **fail closed on `bare_name` ambiguity** (refuse to refresh when a name maps to more than one candidate) rather than guess. It MUST NOT add a new symbol to the allowlist, and MUST NOT refresh an entry whose symbol has gained a caller. | High | Open |
| FR-003 | Skip-marker growth: reviewable-with-teeth, not hard-fail | Replace the `skip_marker_blocks` hard-fail-on-growth with a signal that permits routine additive growth without blocking CI **yet still forces the new skip into a reviewer's view during PR review** and does not silence a genuine regression (a skip where a frontmatter contract is expected). Shrinkage remains observed. | Medium | Open |
| FR-004 | Derive the redundant migration count | Derive the `category_1_auto_discovered_migrations` **count** baseline from the gate's own dead-migration authority (glob ∩ no-static-`src/`-importer), removing the double-charge, so adding a dead migration needs no count bump. Deriving the frozenset **contents** is out of scope (would make `test_no_dead_modules` vacuous). | Medium | Open |
| FR-005 | Fully remove the inert dead-symbol key | Delete the inert `test_no_dead_symbols:` block from `_baselines.yaml` **and** drain its `_GRANDFATHERED_UNREGISTERED_KEYS` residue (constant → `frozenset()`, coupled equality literal updated in lockstep), closing the silent re-entry hole (RL-030). | Low | Open |
| FR-006 | Fast-mark the two sub-second gates | Add the `fast` marker to `test_ratchet_baselines` and `test_ratchet_positional_anchor_ban` so they are selectable in a local `-m fast` run. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Membership gate stays load-bearing (non-fakeable) | A regression test MUST **run the helper** over a tree containing a newly-added uncalled `__all__` symbol — including the `bare_name`-collision case (US1-AC2) — and assert the symbol is absent from the resulting allowlist AND `test_no_dead_symbols` still REDs. The fixture must reach the helper's admit decision point (differ from a refreshable entry by exactly one property). | Correctness | High | Open |
| NFR-002 | Fast-marked gates stay cheap warm | Each `fast`-marked gate MUST execute under 1 second per test **call** (warm), and the `fast` mark MUST NOT pull an expensive transitive import (e.g. the `test_example_round_trip` corpus walk) into a cold pre-push venv. Measurement unit (per-call, warm) is pinned. | Performance | Medium | Open |
| NFR-003 | Zero load-bearing regression | Every load-bearing gate (C-001) MUST remain green with no baseline or predicate weakening. In particular, separating `skip_marker_blocks` from the shared `single_baselines` growth-fail loop MUST NOT loosen its sibling `legacy_contract_allowlist=151` (a C-001 gate). | Reliability | High | Open |
| NFR-004 | Quality bar | New/changed code MUST pass ruff and mypy `--strict` with zero new suppressions and cyclomatic complexity ≤ 15, with tests exercising each new branch directly. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Do-not-touch load-bearing gates | The P0-security gates (`egress_consent_boundary` ×2, `unfiltered_journal_read_boundary`), still-shrinking burn-downs (`grandfathered_orphans`, `legacy_contract_allowlist=151`, `no_inert_schema_slots`, `reference_enum_ratchet`), zero-pins (`backcompat_shims=0`, `known_ungated_files=0`), and `test_artifact_kinds` exact-set (in `tests/doctrine/`, not `tests/architectural/`; deriving it would make it vacuous) MUST NOT be modified. **This refines the brief's blanket "`_baselines.yaml` count-keyed ratchets = don't touch" counterweight**: `skip_marker_blocks` and the `category_1` count are carved out as genuine toll per the per-gate scoping rationale, not the blanket rule. | Technical | High | Open |
| C-002 | Deferred design decisions (plan + architect) | Two HOW-decisions are deferred to plan with architect-alphonso input: (a) the FR-003 reviewable-with-teeth **mechanism**; (b) the FR-004 frozenset hand-list disposition (convert-to-warn vs keep-as-change-detector). Both MUST honor a cost ceiling: **no new CI job and no external-service integration**; the FR-003 signal MUST be observable in ordinary PR review. The spec fixes the behavior, not the mechanism. | Technical | Medium | Open |
| C-003 | Exclude the slow gate from the fast tier | `test_no_dead_symbols` (~72s) MUST NOT be `fast`-marked or added to a blocking pre-push path; it stays in the CI tier only. No pre-push harness is in scope. | Technical | Medium | Open |
| C-004 | Scope boundary | #2625 (golden-count bulk conversion of ~553 excluded-dir sites) and #2323 (legacy-contract 151→0 frontmatter backfill) are explicit follow-on missions and MUST NOT be undertaken here. | Business | High | Open |
| C-005 | Git workflow | Changes land via the PR workflow (merge to local `main`, then a PR to `upstream`); no direct push to `origin/main`. | Technical | High | Open |

### Key Entities

- **Frozen baseline key**: a top-level entry in `tests/architectural/_baselines.yaml` pinning a count; classified load-bearing vs genuine-toll by the scoping pass.
- **Dead-symbol allowlist entry**: a `SymbolKey` in `test_no_dead_symbols.py` — content-tier (`name`, `body_hash`, `module_path=None`, deliberately location-free) or collision-tier (`name`, `module_path`, `body_hash`). Its original `module::Name` survives only in a non-contract trailing comment — the source of the FR-002 re-identification problem.
- **Dead auto-discovered migration**: an `m_*.py` module with no static `src/` importer — the gate's own predicate, and the single authority FR-004 must derive against.
- **Gate classification**: the load-bearing / genuine-toll partition (per-gate rationale from the scoping pass) that governs C-001.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Adding a new auto-discovered dead migration module requires **zero** `category_1` count-baseline edits (the count is derived); the surviving frozenset acknowledgment, if retained, is the only edit.
- **SC-002**: Editing a still-dead symbol's body requires exactly **one** helper invocation (no hand-editing of hashes) to return `test_no_dead_symbols` to green.
- **SC-003**: Adding a legitimate skip-marker block produces **no** hard CI failure, while the growth remains visible to a reviewer in PR review.
- **SC-004**: **100%** of load-bearing gates (C-001) remain green with **zero** baseline or predicate weakening after the mission.
- **SC-005**: Both sub-second gates are selected under `-m fast`; `test_no_dead_symbols` is **not** `fast`-marked.
- **SC-006**: With the helper implemented, running it over a tree containing a newly-added uncalled `__all__` symbol — including one whose `bare_name` collides with an existing dangling entry — leaves that symbol **absent** from the resulting allowlist and `test_no_dead_symbols` **still RED** (the membership gate is provably still load-bearing; the proof runs the helper).

## Assumptions

- The scoping pass's tree-verified findings (load-bearing vs toll partition; `arch-adversarial` CI placement; timings; the 10 live duplicate bare_names; the 105-file/100-count migration delta) hold at plan time; the plan MUST re-verify against `main` before implementing (the audit was found stale once), especially the live `skip_marker_blocks` and `category_1` counts that FR-003/FR-004 fixtures key off.
- The `fast` marker and pre-push conventions follow existing testing docs (`docs/development/testing/`), not a new mechanism.
- FR-002's re-identification and FR-003/FR-004's warning mechanism are resolved in plan with architect-alphonso; this spec fixes the behavior and the safety invariants, not the mechanism.
