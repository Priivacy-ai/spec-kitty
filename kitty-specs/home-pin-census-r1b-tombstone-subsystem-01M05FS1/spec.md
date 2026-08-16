# Mission Specification: R1b Tombstone Subsystem + Provable-Class Convergence (#3121)

**Mission Branch**: `kitty/fix-home-pin-census-owner-adoption-3121`
**Created**: 2026-08-16
**Status**: Draft
**Input**: Actually close #3121 ("converge only the provable class"). The R1a census is a
shrink-only ratchet that *cannot shrink* as landed: the tombstone burn-down path is wired to
neither t023 (fixed in prep op `4d1e6fde0`) nor the production regeneration command. This
mission builds the production tombstone subsystem, then converges the provable class.

## Context & Root Cause *(mandatory)*

The `SPEC_KITTY_HOME` pin census (`tests/architectural/_home_pin_*`, C-011) enforces three joint
invariants: `census == anchor` (t023), `discover − E == anchor` (t023), `discover == census ∪ E`
(t024). R1b's intended mechanism is the **tombstone**: a census member adjudicated away has its
pin removed from the tree AND a tombstone recorded, so `census` shrinks while `census ∪ tombstones`
stays pinned to the frozen 40-key set. Two layers block this today:

1. **t023 was not tombstone-aware** — fixed in prep commit `4d1e6fde0` (this branch): both t023
   equalities now target `anchor − tombstoned`, a no-op while `tombstones: []`, with an anti-abuse
   meta-test (a tombstone over a live pin still reds).
2. **The production regeneration command does not support tombstones.** `_home_pin_scan.render_baseline`
   (`:1385-1401`) hardcodes `tombstones: []` and computes `census_key_set_sha256` from the *live*
   member set only. Because t022 requires the checked-in census+baseline to be **byte-identical** to
   the regeneration output, a hand-added tombstone reds t022 (proven: Op0 proof (b) failed t022).
   So no member can be converged: remove a pin → regenerate → `tombstones: []` → t023 reds
   (`discover − E = 39 ≠ anchor − ∅ = 40`).

**The provable class is small (confirms #3121's thesis).** Of 40 members, only **2** are cleanly
equivalent to `canonical_home`; ~11 more convert with a named per-member confirmation; ~23 are
genuinely different seams (HOME/LOCALAPPDATA co-pins, counter-autouse `delenv SAAS`, `setattr`+store
setup, nested-context pins) that **stay**. Convergence takes the census 40 → 26 at best, **not zero**.
`census == ∅` needs a further deletion-mission + a member-promotion mechanism, both out of scope.
Full analysis: `../home-pin-census-owner-adoption-01M05C50/r1b-convergence-plan.md`.

## Subsystem design (the elegant safety property)

`evaluate()` already checks `hash_of_key_set(census ∪ tombstone_keys) == baseline.census_key_set_sha256`.
So making `render_baseline` (a) emit the tombstone keys and (b) compute the hash over
`census_keys ∪ tombstone_keys` is a **no-op while the tombstone manifest is empty**
(`hash(census ∪ ∅) == hash(census)`, `tombstones: []`) — the committed artefacts stay byte-identical
(t022 unaffected) until a real convergence lands. Tombstones are sourced from a new **checked-in
manifest** (`tests/architectural/census/spec_kitty_home_pin_tombstones.yaml`) recording each
adjudicated-away member's frozen 3-tuple key **plus a recorded cause/evidence** (auditable). The
regeneration command reads it from a fixed default path (no CLI-string change → t022's
`REGENERATION_COMMAND` assertion unaffected). `main()` fails closed if a tombstoned key is still a
live census member (`tombstone ∩ census ≠ ∅`) or is not in the frozen anchor.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The census can legitimately shrink, ratchet intact (Priority: P1)

As a maintainer, I want the production regeneration command to support tombstones sourced from an
auditable manifest, so a member converged onto the canonical owner can be removed from the census
while `census ∪ tombstones` stays frozen at 40 — and the ratchet still bites.

**Why this priority**: Nothing can be converged until this exists. It is the load-bearing risk.

**Independent Test**: With an empty manifest, `pytest tests/architectural/` census suite is green and
the committed census/baseline are byte-identical (no-op). With one manifest entry + its pin removed,
the full census suite is green at census 39. Injecting a manifest entry whose pin is still in the
tree reds (fail-closed).

**Acceptance Scenarios**:
1. **Given** an empty tombstone manifest, **When** the census suite runs, **Then** all census tests
   pass and `git diff` shows no change to census/baseline artefacts (subsystem is a no-op).
2. **Given** a member's pin removed from the tree AND a manifest entry for it, **When** the census
   is regenerated, **Then** census has 39 rows, baseline has `tombstones: [that key]`, the hash is
   unchanged (frozen over the 40-key union), and t022/t023/t024 all pass.
3. **Given** a manifest entry whose pin is STILL in the tree, **When** the census suite runs,
   **Then** it reds (t023 discover-side + a fail-closed generation guard) — a tombstone cannot be
   bought without a real removal.
4. **Given** the subsystem, **When** a spurious new `SPEC_KITTY_HOME` pin is injected, **Then** the
   census reds (ratchet still bites).

### User Story 2 - The provable class is converged (Priority: P2)

As a maintainer, I want the 14 provable-class members converged onto `canonical_home` (each with a
recorded tombstone) and the ~23 genuinely-different seams documented as out-of-scope, so #3121's
"converge only the provable class" mandate is satisfied and the issue closes.

**Why this priority**: Depends entirely on US1. Delivers the #3121 outcome.

**Independent Test**: After each convergence batch, the census suite + that batch's behaviour tests
are green; census count drops by the batch size; each removed member has a manifest tombstone with a
recorded cause. Final census 40 → ~26.

**Acceptance Scenarios**:
1. **Given** US1 landed, **When** the 2 clean PC members are converged, **Then** census = 38, both
   behaviour tests green, 2 manifest entries with cause.
2. **Given** the JC/CR members converged behind their named confirmations, **Then** census → ~26,
   all behaviour tests green, no `delenv SAAS`/`SAAS_URL` residual silently dropped.
3. **Given** convergence complete, **When** the mission record is read, **Then** the 23 must-stay
   seams and 3 deletion-scope members are documented out-of-scope with reasons.

### Edge Cases
- **delenv-SAAS traps** (`consent_read_fault`, `consent_resolver`, `local_commit_consent`,
  `local_commit_purge`): converting silently arms SAAS and inverts the test → MUST-STAY.
- **`daemon_publish`** carries `SPEC_KITTY_SAAS_URL` that no autouse restores → converge the home
  dimension only, retain the URL pin.
- **Sibling non-member pins** (`legacy_queue :26`, `routing :131…`): convert ONLY the census-member
  line; leave siblings untouched.
- **Nested-context inline pin** (`tracker_egress_refusal::_run_once`): a fixture cannot be injected;
  MUST-STAY.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-101 | Tombstone manifest artefact | As a maintainer, I want a checked-in `spec_kitty_home_pin_tombstones.yaml` of {key, reason, evidence} entries as the auditable tombstone source. | High | Open |
| FR-102 | render_baseline emits manifest tombstones | `render_baseline` reads the manifest and emits `tombstones: [sorted keys]` (keys only in the baseline). | High | Open |
| FR-103 | Hash frozen over census∪tombstones | `census_key_set_sha256` is computed over `census_keys ∪ tombstone_keys`, keeping it pinned to the frozen 40-key set. | High | Open |
| FR-104 | Fail-closed generation guard | `main()` raises if any tombstoned key is a live census member (`tombstone ∩ census ≠ ∅`) or is absent from the frozen anchor. | High | Open |
| FR-105 | No CLI-string change | The manifest is read from a fixed default path; `REGENERATION_COMMAND` is unchanged (t022's command assertion holds). | Medium | Open |
| FR-106 | Meta-tests for the mechanism | New tests: empty-manifest no-op; manifest round-trip; fail-closed guard; anti-abuse preserved. | High | Open |
| FR-107 | Converge the provable class | Adopt `canonical_home` in the 14 provable members, remove each pin, add each tombstone (with cause), regenerate. census 40 → ~26. | High | Open |
| FR-108 | Document out-of-scope seams | The 23 must-stay + 3 deletion-scope members are recorded out-of-scope with reasons. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-101 | Ratchet preserved | Spurious new pin reds; tombstone over a live pin reds; equalities stay set-equalities; `E` stays arity-2. Zero dulling. | Reliability | High | Open |
| NFR-102 | Empty-manifest no-op | With an empty manifest the committed census/baseline are byte-identical (t022 green, no artefact diff). | Correctness | High | Open |
| NFR-103 | Reproducible | t022 byte-identity holds with tombstones present (manifest is deterministic input). | Correctness | High | Open |
| NFR-104 | Static-analysis clean | Changed files pass ruff + mypy (incl. `mypy --strict` on `_home_pin_exempt.py`). | Quality | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-101 | No immutable-artefact edits | `members.json`, the anchor yaml, and `E` are never edited to green a test. | Technical | High | Open |
| C-102 | No gate-dulling | No equality relaxed to containment; no scanner narrowing; no `resolve_value` evasion. | Technical | High | Open |
| C-103 | Deletion out of scope | The 3 arm-2-GREEN deletion-scope members are NOT converged (belongs to a deletion mission). | Technical | High | Open |
| C-104 | No census==0 claim | This mission closes #3121 on the "provable class converged" DoD (~26), not `census == ∅`. | Business | High | Open |

## Success Criteria *(mandatory)*

- **SC-101**: With an empty manifest, `pytest tests/architectural/test_spec_kitty_home_pin_census.py`
  is green and census/baseline artefacts are unchanged (byte-identical).
- **SC-102**: After converging the 2 PC members, the census suite is green at census 38 with 2
  manifest tombstones (each with a recorded cause) and both behaviour tests green.
- **SC-103**: A manifest entry whose pin is still present reds the census suite (fail-closed).
- **SC-104**: Ratchet-bite proofs pass (spurious pin reds; tombstone-over-live-pin reds).
- **SC-105**: Best-case census 40 → ~26 after all provable members converge; all affected behaviour
  tests green; no SAAS/URL residual dropped.
- **SC-106**: `arch-adversarial (arch_shard_3)` green on CI; ruff + mypy clean on changed files.
