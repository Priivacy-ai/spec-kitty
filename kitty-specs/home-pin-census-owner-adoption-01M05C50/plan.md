# Implementation Plan: SPEC_KITTY_HOME Pin Census — Owner Adoption (C-011 / #3121)

**Branch**: `kitty/fix-home-pin-census-owner-adoption-3121` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/home-pin-census-owner-adoption-01M05C50/spec.md`

## Summary

Green the `arch-adversarial (arch_shard_3)` census gate by making the one drifting test adopt
the exempt canonical `SPEC_KITTY_HOME` owner instead of carrying its own `setenv` pin. This is
the design-sanctioned "green path" for a new home-pinning site (R1a User Story 2): the test
requests the `canonical_home` fixture (which already provides the identical
`SPEC_KITTY_HOME=<tmp_path>/home` isolation) and deletes its own write site, so `discover()`
returns to the frozen 40-member class and the three census invariants re-green with **no edit
to any frozen or forbidden artefact**. Validated end-to-end during research (dry run: census
suite 6-red → 29-green, affected test green, ratchet-bite proof red-on-inject).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest (fixtures), the census machinery under `tests/architectural/`
**Storage**: N/A (test-only change)
**Testing**: pytest; ATDD — the census suite + the affected behaviour test ARE the acceptance contract
**Target Platform**: Linux CI (`arch-adversarial (arch_shard_3)`)
**Project Type**: single (test-isolation refactor)
**Performance Goals**: N/A
**Constraints**: no frozen-artefact edits (C-001); no equality relaxation (C-002); `E` stays
arity-2 (C-003); no scanner narrowing / value-evasion (C-004); no product change (C-005)
**Scale/Scope**: one file — `tests/cli/commands/test_sync_status_drain_blockers.py`

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **ATDD-first** ✅ — acceptance is expressed as concrete test runs (SC-001..SC-006); the
  census suite is the executable contract; no new assertions beyond the existing gate.
- **Single canonical authority** ✅ — the fix *reinforces* the single canonical
  `SPEC_KITTY_HOME` owner rather than adding a second isolation path.
- **Locality of change / smallest-viable-diff** ✅ — one test file, ~7 lines; no blast radius.
- **Boy Scout Rule** ✅ — leaves the test cleaner (adopts the blessed owner, richer docstring).
- **Terminology canon** ✅ — no `feature*` terms introduced; "Mission" respected.
- **No gate-dulling** ✅ (binding) — NFR-001 mandates a ratchet-bite proof; the fix moves the
  tree back under the anchor, never the anchor toward the tree.

No charter violations → Complexity Tracking left empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/home-pin-census-owner-adoption-01M05C50/
├── spec.md              # Complete
├── plan.md              # This file
├── tasks.md             # Phase 2 (/spec-kitty.tasks)
└── tasks/               # WP files
```

### Source Code (repository root)

```
tests/
├── cli/commands/
│   └── test_sync_status_drain_blockers.py   # THE change: adopt canonical_home, drop setenv
├── conftest.py                              # canonical_home owner (READ-ONLY reference, :372)
└── architectural/
    ├── test_spec_kitty_home_pin_census.py   # acceptance gate (READ-ONLY — must stay green)
    ├── _home_pin_scan.py / _home_pin_verdict.py / _home_pin_exempt.py / _ratchet_keys.py
    └── census/spec_kitty_home_pin_{R1a,anchor}.yaml   # frozen (MUST NOT edit — C-001)
```

**Structure Decision**: Single-file test change. No production source touched. Everything under
`tests/architectural/` and the two census yaml artefacts are read-only invariants the change
must satisfy, not modify.

## Complexity Tracking

*No charter violations — not applicable.*

## Implementation Concern Map

### IC-01 — Adopt the canonical owner in the drifting test

- **Purpose**: Remove the test's own `SPEC_KITTY_HOME` write site by requesting the exempt
  `canonical_home` fixture, so `discover()` no longer classes the test as a census member,
  while preserving the exact per-test home isolation the test needs.
- **Relevant requirements**: FR-001, FR-002, FR-003; NFR-002, NFR-003; C-001..C-005.
- **Affected surfaces**: `tests/cli/commands/test_sync_status_drain_blockers.py`
  (signature + body of `test_queue_get_drain_blocked_counts_persists_through_drain_round_trip`;
  its docstring). Reference-only: `tests/conftest.py:372`.
- **Sequencing/depends-on**: none (single concern).
- **Risks**:
  - *Owner semantics divergence* — mitigated: `canonical_home` sets the identical
    `<tmp_path>/home` and mkdirs it; empty dir ⇒ no layout record ⇒ still LEGACY. Validated.
  - *Residual pin* — the owner never overrides a self-pinning test, so the `setenv` MUST be
    deleted, not merely supplemented. Encoded as an edge case + acceptance scenario.
  - *Lint fallout* — now-unused `tmp_path`/`monkeypatch` params dropped; `del canonical_home`
    per repo idiom; ruff+mypy clean (NFR-003).

## Verification Strategy (ATDD)

The acceptance tests already exist and are the contract:

1. `PWHEADLESS=1 pytest tests/architectural/test_spec_kitty_home_pin_census.py -q` → 0 failures.
2. `PWHEADLESS=1 pytest tests/cli/commands/test_sync_status_drain_blockers.py -q` → 0 failures.
3. `git diff --stat` → exactly one file changed; `git status tests/architectural/` → clean.
4. Ratchet-bite proof: inject one spurious `setenv("SPEC_KITTY_HOME", str(tmp_path/"home"))`
   in a throwaway test → census suite RED; remove → GREEN. (Executed, not asserted-in-repo.)
5. `ruff check` + `mypy` on the edited file → zero issues.
6. Push → confirm `arch-adversarial (arch_shard_3)` green on CI (from a clean non-dot checkout).
