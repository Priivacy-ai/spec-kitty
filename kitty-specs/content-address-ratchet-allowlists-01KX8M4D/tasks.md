# Tasks: Drift-Proof Architectural Ratchet Allow-lists

**Mission**: content-address-ratchet-allowlists-01KX8M4D
**Branch**: `analysis/test-change-coupling` → PR to `main`
**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

6 WPs / 28 subtasks. Dependency spine: **WP01 (WS3)** + **WP02 (DESCRIPTOR keystone)**
are free/parallel; **WP03/WP04** (WS1 migrations) depend on WP02; **WP05**
(META-GUARD) depends on WP03+WP04; **WP06** (WS2 spike) is gated last with a
carve/continue checkpoint. `IC-WS1-TRIO` (#2545 now merged) is a **rebase-gated
fast-follow**, not in this finalize (see note below). WS2 bulk migration
(FR-008/009) is authored only if the WP06 checkpoint says *continue*; else it
carves to standalone #2546 (pre-wired in issue-matrix).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Convert 2 `__module__` sub-tests in test_layer_rules to behavioural | WP01 | [P] |
| T002 | Harden test_template_governance: derive promised-surface from contract/schema | WP01 | [P] |
| T003 | Record FR-012 10-KEEP audit verdict | WP01 | |
| T004 | Plant-and-catch non-vacuity for both WS3 tests | WP01 | |
| T005 | Add `resolve_descriptor`/`descriptor_still_live` to _ratchet_keys.py (reuse audit.py 3-tuple; qualname-map-once) | WP02 | |
| T006 | Exactly-one resolution (RED on 0/>1); key-equal staleness (never ≥1) | WP02 | |
| T007 | Import-time unique-within-qualname assertion helper (GAP-1) | WP02 | |
| T008 | Resolver unit tests: 2-axis disambiguation + 0/>1 → RED | WP02 | |
| T009 | Non-vacuity self-test (resolve == composite_key(true_finding_line)) | WP02 | |
| T010 | Migrate `_ALLOW_LIST_SEED` (WS#1/2/3) to content descriptors | WP03 | |
| T011 | Migrate `_CHECKOUT_GRAMMAR_ALLOW_LIST_SEED` (CG#1-4) | WP03 | |
| T012 | Convert 3 line-number twin-guards to descriptor-still-live | WP03 | |
| T013 | Migrate test_wp05 (scalar 347 + composite_key(source,347)); keep 2 probes | WP03 | |
| T014 | Delete re-anchor changelog fossils (both files) | WP03 | |
| T015 | Plant-and-catch incl. same-qualname sibling; motion battery | WP03 | |
| T016 | Migrate `_RAW_JOIN_SITES` (RJ#1-4; RJ#1/2 same-qualname disambiguation) | WP04 | |
| T017 | Convert its staleness twin-guard to descriptor-still-live | WP04 | |
| T018 | Delete the 8-entry fossil | WP04 | |
| T019 | Plant-and-catch incl. same-qualname sibling (RJ#1/2); motion battery | WP04 | |
| T020 | New test_ratchet_positional_anchor_ban.py: AST int-to-line-sink + YAML field-name rule | WP05 | |
| T021 | FR-014: enumerate the 2 deferred census path::qualname allow-lists | WP05 | |
| T022 | Enroll new test in tests/_arch_shard_map.py + bump _baselines total_tests (SAME WP) | WP05 | |
| T023 | Reuse/extend anchoring helper for the detector; explicit-marker escape hatch | WP05 | |
| T024 | Non-vacuity: plant int line-sink → red; compliant YAMLs `line:`/count-floors stay green | WP05 | |
| T025 | Prototype relocation-proof symbol identity in NEW _symbol_identity module (no bare-name-alone) | WP06 | |
| T026 | Wire T004 no-false-negative fixtures (ArtifactKind×3, GateDecision×2, ResolutionResult/Tier×2) | WP06 | |
| T027 | Body-hash stability probe: motion battery + 3.11↔3.12 normalization | WP06 | |
| T028 | Carve/continue checkpoint (implementer proposes, operator confirms) — do NOT bulk-migrate yet | WP06 | |

## Work Packages

### WP01 — WS3 ratio=1.00 audit residue
**Goal**: the small, dependency-free residue — convert 2 shape-pinned sub-tests +
harden 1 literal-pinned gate + record the 10-KEEP verdict. **Priority**: MVP (free, first).
**Independent test**: `pytest test_layer_rules.py test_template_governance_payload_contract.py` green; the 2 converted sub-tests survive a `__module__` relocation.
- [x] T001 Convert 2 `__module__` sub-tests in test_layer_rules to behavioural (WP01)
- [x] T002 Harden test_template_governance: derive promised-surface from contract/schema (WP01)
- [x] T003 Record FR-012 10-KEEP audit verdict (WP01)
- [x] T004 Plant-and-catch non-vacuity for both WS3 tests (WP01)
**Dependencies**: none. **Prompt**: [WP01-ws3-ratio-audit.md](tasks/WP01-ws3-ratio-audit.md)

### WP02 — IC-DESCRIPTOR keystone (shared content-descriptor resolver)
**Goal**: the shared resolver every WS1 gate consumes — exactly-one, key-equal,
normalized, qualname-map-once, reusing audit.py's path-qualified 3-tuple.
**Priority**: keystone (WS1 migrations depend on it). **Independent test**: resolver
unit tests green; 2-axis disambiguation + 0/>1 → RED proven.
- [x] T005 Add resolve_descriptor/descriptor_still_live to _ratchet_keys.py (WP02)
- [x] T006 Exactly-one resolution (RED on 0/>1); key-equal staleness (WP02)
- [x] T007 Import-time unique-within-qualname assertion helper (WP02)
- [x] T008 Resolver unit tests: 2-axis disambiguation + 0/>1 → RED (WP02)
- [x] T009 Non-vacuity self-test (resolve == composite_key(true_finding_line)) (WP02)
**Dependencies**: none. **Prompt**: [WP02-descriptor-keystone.md](tasks/WP02-descriptor-keystone.md)

### WP03 — IC-WS1-WRITESIDE (write-side + wp05 migration)
**Goal**: migrate the write-side + checkout-grammar seeds + wp05 to content
descriptors (per the plan's descriptor table); delete the fossils. **Priority**: high.
**Independent test**: motion battery 0 false-reds + same-qualname sibling reds.
- [x] T010 Migrate `_ALLOW_LIST_SEED` (WS#1/2/3) to content descriptors (WP03)
- [x] T011 Migrate `_CHECKOUT_GRAMMAR_ALLOW_LIST_SEED` (CG#1-4) (WP03)
- [x] T012 Convert 3 line-number twin-guards to descriptor-still-live (WP03)
- [x] T013 Migrate test_wp05 (scalar 347 + call-arg 347); keep 2 probes (WP03)
- [x] T014 Delete re-anchor changelog fossils (both files) (WP03)
- [x] T015 Plant-and-catch incl. same-qualname sibling; motion battery (WP03)
**Dependencies**: WP02. **Prompt**: [WP03-ws1-writeside.md](tasks/WP03-ws1-writeside.md)

### WP04 — IC-WS1-RAWJOIN (highest-tax gate migration)
**Goal**: migrate `_RAW_JOIN_SITES` (~8 re-anchors — the highest tax); delete the
8-entry fossil. **Priority**: high. **Independent test**: motion battery 0 false-reds;
RJ#1/RJ#2 same-qualname disambiguation proven.
- [x] T016 Migrate `_RAW_JOIN_SITES` (RJ#1-4) to content descriptors (WP04)
- [x] T017 Convert its staleness twin-guard to descriptor-still-live (WP04)
- [x] T018 Delete the 8-entry fossil (WP04)
- [x] T019 Plant-and-catch incl. same-qualname sibling (RJ#1/2); motion battery (WP04)
**Dependencies**: WP02. **Prompt**: [WP04-ws1-rawjoin.md](tasks/WP04-ws1-rawjoin.md)

### WP05 — IC-METAGUARD (standing positional-anchor ban)
**Goal**: the standing all-suite gate (int-to-line-sink Python + YAML field-name)
+ shard-map enrollment + census enumeration. **Priority**: after all WS1.
**Independent test**: plant an int line-sink → red; compliant YAMLs + count-floors stay green; `test_arch_shard_marker_completeness` green.
- [ ] T020 New test_ratchet_positional_anchor_ban.py: AST int-to-line-sink + YAML field-name (WP05)
- [ ] T021 FR-014: enumerate the 2 deferred census path::qualname allow-lists (WP05)
- [ ] T022 Enroll new test in tests/_arch_shard_map.py + bump _baselines total_tests (WP05)
- [ ] T023 Reuse/extend anchoring helper; explicit-marker escape hatch (WP05)
- [ ] T024 Non-vacuity: plant int line-sink → red; compliant YAMLs stay green (WP05)
**Dependencies**: WP03, WP04. **Prompt**: [WP05-standing-metaguard.md](tasks/WP05-standing-metaguard.md)

### WP06 — IC-WS2-SPIKE (relocation-proof key + carve checkpoint)
**Goal**: prototype the relocation-proof symbol identity (no bare-name-alone),
prove T004 no-false-negative, run the body-hash stability probe, and END with an
explicit carve/continue checkpoint — do NOT bulk-migrate the 343-entry allow-list
here. **Priority**: gated LAST; must not gate WS1/WS3 merge. **Independent test**:
T004 fixtures green with the new key; the carve recommendation is written.
- [ ] T025 Prototype relocation-proof symbol identity in NEW _symbol_identity module (WP06)
- [ ] T026 Wire T004 no-false-negative fixtures (ArtifactKind×3, GateDecision×2, ResolutionResult/Tier×2) (WP06)
- [ ] T027 Body-hash stability probe: motion battery + 3.11↔3.12 normalization (WP06)
- [ ] T028 Carve/continue checkpoint — do NOT bulk-migrate yet (WP06)
**Dependencies**: none (sequenced last operationally). **Prompt**: [WP06-ws2-spike.md](tasks/WP06-ws2-spike.md)

## Fast-follow (NOT in this finalize)
- **IC-WS1-TRIO** (FR-005c) — PR #2545 is merged; after the mission branch
  **rebases onto `main`**, `test_trio_seam_only._IO_ALLOWLIST_SITES` (5 entries,
  all UNIQUE per the descriptor table) migrates the same way as WP03/WP04, and
  the file gets a `tests/_arch_shard_map.py` entry. It must land **before** WP05's
  meta-guard can go green on the trio file. Sequence: rebase → migrate TRIO → then
  (re-)green the meta-guard. Handle as a rebase-then-fold in-mission addition.
- **WS2 bulk migration** (FR-008/FR-009) — authored only if the WP06 checkpoint
  says *continue*; else carved to standalone #2546.

## MVP
WP01 (WS3) + WP02 (DESCRIPTOR) + WP03/WP04 (WS1) + WP05 (META-GUARD) is a complete,
shippable mission closing #2547/#2072 and the #2548 residue, even if WS2 carves.
