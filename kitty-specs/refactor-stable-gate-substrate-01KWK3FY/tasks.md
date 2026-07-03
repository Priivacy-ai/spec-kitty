# Tasks: Refactor-Stable Gate Substrate

**Mission**: `refactor-stable-gate-substrate-01KWK3FY` | **Branch**: `tidy/gate-substrate` | **Generated**: 2026-07-03
**Input**: spec.md (rev 2), plan.md (IC-01..IC-06), research.md (D1–D8), data-model.md, contracts/ (gate-conversion + audit-identity)

Five ownership-disjoint parallel WPs + one serialized closeout. Every WP's validation
section binds to the two mission contracts; the mission's own deliverables obey the
refactor-stable doctrine (C-001).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Fail-closed freeze converter → rewrite the 10 YAML entries (file/qualname/token + line locator) | WP01 | |
| T002 | GateAllowlistKey conversion: rel_path added, frozen token comparand; loader | WP01 | |
| T003 | Scanners emit (path, qualname, token); zero node.lineno in keys; diagnostics locator kept | WP01 | |
| T004 | Re-pin the ~6 int-line test constructors + derive_live_key unit tests | WP01 | |
| T005 | Theater TRIAD at both check_*_gate entry points + staleness-guard semantics | WP01 | |
| T006 | WP01 validation sweep (mypy strict together, ruff, full gate file) | WP01 | |
| T007 | Untrusted SinkRow identity + audit.py Check-2 → composite | WP02 | [P] |
| T008 | Convert the duplicated raw-line compare (test_untrusted_path_containment.py:328) | WP02 | |
| T009 | Re-key inventory.md (30 rows): line → locator; [inventory-only] tag support | WP02 | |
| T010 | NEW overcount/ghost-row check (untrusted) | WP02 | |
| T011 | Theater triad incl. the #2306 regression case; WP02 validation | WP02 | |
| T012 | Surface ResolutionRow Check-2 + SelectionRow check → composite | WP03 | [P] |
| T013 | Re-key surface inventory.md; split-brain reconciliation (resolver test UNMODIFIED) | WP03 | |
| T014 | NEW overcount/ghost-row check (surface) | WP03 | |
| T015 | Theater triad; WP03 validation incl. resolver-test unmodified-green proof | WP03 | |
| T016 | Author the 6 refactor-stable principles + patterns/anti_patterns (PR #2308 examples) | WP04 | [P] |
| T017 | generate_graph regeneration; both freshness gates green | WP04 | |
| T018 | Acceptance-time content-check script (mission artifact) | WP04 | |
| T019 | Implement-day re-verification of the 15 quarantined nodes | WP05 | [P] |
| T020 | Remove the 15 markers; per-file CI-selection verification | WP05 | |
| T021 | Real-CI-shard-form determinism, two consecutive runs | WP05 | |
| T022 | Honest stay-behind reasons (2 uv-tool rewrites + upstream issue; A16 kept) | WP05 | |
| T023 | Design-P reference docstring note in test_no_worktree_name_guess.py (no key changes) | WP06 | |
| T024 | Tracker closeout: #2072 partial comment; #2310/#2311 verdicts; issue-matrix terminal | WP06 | |
| T025 | Tracer close-outs + acceptance-matrix evidence prep | WP06 | |

## Phase 1 — Parallel substrate work

### WP01 — Resolution-gate Design-P conversion

**Goal**: The last raw-line-keyed gate becomes drift-immune AND content-detecting (frozen `(file, qualname, token)` comparands). **Priority**: P1. **Prompt**: [tasks/WP01-resolution-gate-design-p.md](tasks/WP01-resolution-gate-design-p.md) (~380 lines)
**Independent test**: theater triad at both entry points — +1-line drift green / token-edit red / new-offender red; staleness guard loud.
**Dependencies**: none.

- [x] T001 Fail-closed freeze converter → rewrite the 10 YAML entries (WP01)
- [x] T002 GateAllowlistKey conversion + loader (WP01)
- [x] T003 Scanners emit composite keys; diagnostics locator kept (WP01)
- [x] T004 Re-pin int-line test constructors + derive_live_key tests (WP01)
- [x] T005 Theater TRIAD + staleness-guard semantics (WP01)
- [x] T006 WP01 validation sweep (WP01)

### WP02 — Untrusted-path audit identity redesign

**Goal**: Kill the #2306 failure class at its origin; both tripwire directions guarded. **Priority**: P1. **Prompt**: [tasks/WP02-untrusted-audit-identity.md](tasks/WP02-untrusted-audit-identity.md) (~330 lines)
**Independent test**: synthetic line-only drift green; undocumented sink red; ghost row red; the #2306 historical shape green.
**Dependencies**: none (disjoint files from WP01).

- [x] T007 SinkRow identity + Check-2 → composite (WP02)
- [x] T008 Convert the duplicated compare at :328 (WP02)
- [x] T009 Re-key inventory.md; [inventory-only] tag (WP02)
- [x] T010 NEW overcount/ghost-row check (WP02)
- [x] T011 Theater triad + #2306 regression case; validation (WP02)

### WP03 — Surface-resolution audit identity redesign

**Goal**: The twin's redesign + SelectionRow + split-brain reconciliation. **Priority**: P1. **Prompt**: [tasks/WP03-surface-audit-identity.md](tasks/WP03-surface-audit-identity.md) (~320 lines)
**Independent test**: same triad as WP02 for BOTH row types; `test_single_mission_surface_resolver.py` green UNMODIFIED.
**Dependencies**: none (disjoint files).

- [x] T012 ResolutionRow + SelectionRow checks → composite (WP03)
- [x] T013 Re-key surface inventory; split-brain reconciliation (WP03)
- [x] T014 NEW overcount/ghost-row check (WP03)
- [x] T015 Theater triad + resolver-test unmodified proof (WP03)

### WP04 — Refactor-stable doctrine styleguide + DRG

**Goal**: CT8 — the operator rulings become governance in testing-principles.styleguide.yaml. **Priority**: P2. **Prompt**: [tasks/WP04-doctrine-styleguide.md](tasks/WP04-doctrine-styleguide.md) (~260 lines)
**Independent test**: both DRG byte-freshness gates green; the acceptance-check script parses ≥6 principles with examples.
**Dependencies**: none.

- [x] T016 Author principles + patterns/anti_patterns (WP04)
- [x] T017 generate_graph regen + freshness gates (WP04)
- [x] T018 Acceptance-time content-check script (WP04)

### WP05 — CT9 un-quarantine

**Goal** (RESCOPED — operator CI-green fold, FR-010): the quarantine-visibility CI
job goes GREEN — all 31 quarantined tests adjudicated on CI evidence
(remediate-then-unquarantine / honest skip+issue / delete), no workarounds.
**Priority**: P1. **Prompt**: [tasks/WP05-ct9-unquarantine.md](tasks/WP05-ct9-unquarantine.md)
**Independent test**: lane green on the mission PR; differential local evidence (bypass unset: remediated PASS + disabled SKIPPED).
**Dependencies**: none.

- [x] T019 CI-evidence adjudication census (31 rows) (WP05)
- [x] T020 Execute adjudications (remediate/skip/delete) (WP05)
- [x] T021 Differential determinism ×2, bypass unset (WP05)
- [x] T022 Stay-behind reasons + upstream uv-tool issue + A16 verdict (WP05)

## Phase 2 — Closeout (serialized)

### WP06 — Reference-pattern doc + closeout

**Goal**: FR-005 (reframed) + FR-009: document the Design-P reference implementation, terminal tracker verdicts, tracer close-outs. **Priority**: P3. **Prompt**: [tasks/WP06-reference-doc-closeout.md](tasks/WP06-reference-doc-closeout.md) (~220 lines)
**Independent test**: docstring note present with zero key changes (diff proves); issue-matrix verdicts terminal; #2072 partial comment posted.
**Dependencies**: WP01, WP02, WP03, WP04, WP05.

- [ ] T023 Design-P reference docstring note (WP06)
- [ ] T024 Tracker closeout + issue-matrix verdicts (WP06)
- [ ] T025 Tracer close-outs + acceptance evidence prep (WP06)

## Dependency graph

```
WP01 ─┐
WP02 ─┤
WP03 ─┼─→ WP06
WP04 ─┤
WP05 ─┘
```

**Parallel opportunities**: WP01–WP05 are fully ownership-disjoint (five separate file
sets) and run in parallel lanes; WP06 serializes last.

## MVP scope

WP01 alone delivers CT1's core (the gate the unshim wave churns most); WP01+WP02
close the #2306 class entirely.
