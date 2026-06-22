# Tasks: MissionTopology SSOT + structural planning-surface coherence

**Mission**: `single-planning-surface-authority-01KVPR00` · branch `feat/single-planning-surface-authority`
**Driver**: #2069 (MissionTopology SSOT seam — *the design, goes first*) · structurally closes
#2062/#2063/#2064 · epic #2007 / #1619 · campsite #1970 (ACTIVE, opportunistic on touched lines)

8 WPs / 38 subtasks. **Seam-first**: a linearized seam chain (WP00 ratchet re-key →
IC-01 enum/predicate → IC-02 store/backfill → IC-03 pure resolver + retire BOTH derivations)
lands first; structural adoption (IC-04 read / IC-05 write — parallel after the seam → IC-06
map/finalize → IC-07 `is_committed` collapse, LAST and live-repro-gated) follows. Scope is
**FR-001..FR-011**; the `CommitTargetKind` TYPE eradication is **Mission B (#2070, C-007)** and the
verb/guard/de-godding/doctrine work is the **block-C follow-up (C-008)** — neither is in scope here.

> **#1970 campsite (C-001):** every WP remediates adjacent debt on the surface it actually edits,
> bounded to mission goals — opportunistic on touched lines only. The *named* de-godding
> extractions (#2059 doctor, #2056 mission.py) are CARVED to block C; do NOT perform them here.
> **NFR-001/C-002 live-evidence:** #2062 is NOT fixed without a witnessed live flattened-mid-flight
> repro; the differential gate (incl. the on-disk flattened-stale-coord row) must be green at every
> WP boundary.

## Subtask Index

| ID | Description | WP | Parallel |
| --- | --- | --- | --- |
| T001 | Re-key `_ALLOW_LIST` + delete the duplicated `_code_tokens_by_line` (`test_no_write_side_rederivation.py`) | WP00 | |
| T002 | Preserve the line-scoped INTENT + deferred-line tests under the composite-key shape | WP00 | |
| T003 | Re-key `_ALLOWLISTED_RAW_JOINS` in `test_single_mission_surface_resolver.py` | WP00 | |
| T004 | Prove non-vacuity + zero dangling refs + both guard files green | WP00 | |
| T005 | Add the `MissionTopology` enum to `context.py` (FR-001) | WP01 | |
| T006 | Add the `routes_through_coordination` predicate + the `classify_topology` mission-shape classifier to `context.py` (FR-005) | WP01 | |
| T007 | Export all three new symbols (enum, predicate, `classify_topology`) from the `mission_runtime` surface | WP01 | |
| T008 | Route the 5 owned decision sites through the predicate (FR-005) | WP01 | |
| T009 | Add a focused, non-fakeable unit test for the seam | WP01 | |
| T010 | `meta.json` topology schema + the compute-once-then-persist shim | WP02 | |
| T011 | Mint `topology` at `mission create` (FR-002) | WP02 | |
| T012 | `backfill_topology.py` (mirror `backfill_identity.py`) (FR-003) | WP02 | |
| T013 | Register `migrate backfill-topology` CLI (FR-003) | WP02 | |
| T014 | `doctor topology --json` audit subcommand (FR-003) | WP02 | |
| T015 | Add the pure `resolve_context_for_mission` projection (NFR-005, C-003) | WP03 | |
| T016 | Add the optional input-assertion (fail-closed on mismatch) | WP03 | |
| T017 | Retire BOTH derivations onto the stored topology (FR-004) | WP03 | |
| T018 | Pure zero-fixture unit test for the resolver (NFR-005, SC-002) | WP03 | |
| T019 | Grep gate + static-analysis clean (SC-001, NFR-004) | WP03 | |
| T020 | Thread the stored topology into `_resolve_existing_for_slug` (FR-006) | WP04 | |
| T021 | Replace the declared-coord band-aid + correct the stale `:262-264` comment (FR-006, C-004) | WP04 | |
| T022 | ADD the pure stored-topology equivalence cell (FR-010a, NFR-005) | WP04 | |
| T023 | RETAIN/ADD the on-disk flattened-stale-coord row × every handle form (FR-010b, NFR-001) | WP04 | |
| T024 | Live repro + mutation note + static-analysis clean (NFR-001, NFR-004, C-002) | WP04 | |
| T025 | Separate `safe-commit`'s two responsibilities (FR-007, NFR-002) | WP05 | |
| T026 | Confirm + regression-pin `spec_commit_cmd.py` seam routing (FR-007, #2063) | WP05 | |
| T027 | Route the 2 `.kind is COORDINATION` decision sites through the predicate (FR-005) | WP05 | |
| T028 | Status emission resolves `feature_dir` from the seam (FR-009) | WP05 | |
| T029 | `status_transition.py:336` drain decision (LIVE-EVIDENCE-GATED, FR-009) | WP05 | |
| T030 | Tests + static-analysis gate | WP05 | |
| T031 | Consolidate the WP-dir read surface to one resolver (FR-008) | WP06 | |
| T032 | Route the `.kind is COORDINATION` site through the predicate (FR-005) | WP06 | |
| T033 | Non-fakeable regression test: map → finalize agree on a coord topology (#2064) | WP06 | |
| T034 | Predicate-routing test + static gates (NFR-004) | WP06 | |
| T035 | Map the behavioral envelope BEFORE reducing (randy equivalence-evidence) | WP07 | |
| T036 | Route the `.kind is COORDINATION` site through the predicate (FR-005) | WP07 | |
| T037 | Reduce the 3-leg OR to a single-surface check on the resolved placement ref (FR-011) | WP07 | |
| T038 | Prove behavior-preserving + clean gates (NFR-003, NFR-004) | WP07 | |

## Requirement coverage

| FR | WP(s) | NFR / C | WP(s) |
| --- | --- | --- | --- |
| FR-001 | WP01 | NFR-001 (live repro) | WP04, WP07 |
| FR-002 | WP02 | NFR-002 (generic safe-commit) | WP05 |
| FR-003 | WP02 | NFR-003 (behavior-preserving) | WP07 |
| FR-004 | WP03 | NFR-004 (static analysis) | all |
| FR-005 | WP01, WP05, WP06, WP07 | NFR-005 (resolver isolation) | WP03 |
| FR-006 | WP04 | | |
| FR-007 | WP05 | | |
| FR-008 | WP06 | | |
| FR-009 | WP05 | | |
| FR-010 | WP04 | | |
| FR-011 | WP07 | | |

## Work Packages

### WP00 — Composite-key re-key of the gating ratchets (test-only, FIRST)
**Goal**: front-load #2072-A — re-key the two gating architectural guards' `file:line` allowlists
onto the content-addressed `composite_key`, so the seam WPs' line moves don't false-red the gate.
**Dependencies**: none. **Independent test**: both guard files green; planted violation still fails.
Prompt: `tasks/WP00-composite-key-rekey-ratchets.md`
- [x] T001 Re-key `_ALLOW_LIST` + delete duplicated `_code_tokens_by_line` (WP00)
- [x] T002 Preserve line-scoped INTENT + deferred-line tests under composite-key shape (WP00)
- [x] T003 Re-key `_ALLOWLISTED_RAW_JOINS` in `test_single_mission_surface_resolver.py` (WP00)
- [x] T004 Prove non-vacuity + zero dangling refs + both guards green (WP00)

### WP01 — MissionTopology enum + routes_through_coordination predicate (IC-01, seam foundation)
**Goal**: FR-001/FR-005 — name the coord×lanes 2×2 grid as one value; add the predicate; route the
5 owned decision sites. **Dependencies**: WP00. **Independent test**: predicate unit test over all
4 cells; grep proves owned sites no longer read `.kind` to decide.
Prompt: `tasks/WP01-missiontopology-enum-predicate.md`
- [x] T005 Add the `MissionTopology` enum to `context.py` (FR-001) (WP01)
- [x] T006 Add the `routes_through_coordination` predicate (FR-005) (WP01)
- [x] T007 Export both new symbols from the `mission_runtime` public surface (WP01)
- [x] T008 Route the 5 owned decision sites through the predicate (FR-005) (WP01)
- [x] T009 Add a focused, non-fakeable unit test for the seam (WP01)

### WP02 — Store + backfill MissionTopology in meta.json (IC-02, seam)
**Goal**: FR-002/FR-003 — mint `topology` at create; `migrate backfill-topology`; `doctor topology`.
Dogfooding landmine: backfill THIS mission before any caller reads the field.
**Dependencies**: WP01. **Independent test**: new mission has correct topology; backfill idempotent;
doctor audit reports it.
Prompt: `tasks/WP02-store-backfill-topology.md`
- [x] T010 `meta.json` topology schema + compute-once-then-persist shim (WP02)
- [x] T011 Mint `topology` at `mission create` (FR-002) (WP02)
- [x] T012 `backfill_topology.py` (mirror `backfill_identity.py`) (FR-003) (WP02)
- [x] T013 Register `migrate backfill-topology` CLI (FR-003) (WP02)
- [x] T014 `doctor topology --json` audit subcommand (FR-003) (WP02)

### WP03 — Pure resolve_context_for_mission + retire BOTH derivations (IC-03, seam keystone)
**Goal**: FR-004 — pure projection over `build_execution_context` (NFR-005, C-003); retire BOTH
`coordination_branch is None ⇒ FLATTENED` derivations (`resolution.py:706-717` AND
`runtime_bridge.py:144-212`) AND route `surface_resolver.resolve_status_surface_with_anchor:600`'s
status-surface decision through stored topology (FR-006 status-leg, squad expansion; owns
`surface_resolver.py`). **Dependencies**: WP01, WP02. **Independent test**: zero-fixture pure
unit test over 4 topologies; grep proves zero live inference sites (SC-001).
Prompt: `tasks/WP03-pure-resolver-retire-derivations.md`
- [x] T015 Add the pure `resolve_context_for_mission` projection (NFR-005, C-003) (WP03)
- [x] T016 Add the optional input-assertion (fail-closed on mismatch) (WP03)
- [x] T017 Retire BOTH derivations onto the stored topology (FR-004) (WP03)
- [x] T018 Pure zero-fixture unit test for the resolver (NFR-005, SC-002) (WP03)
- [x] T019 Grep gate + static-analysis clean (SC-001, NFR-004) (WP03)

### WP04 — Read path consults stored topology (structural #2062) + differential gate (IC-04)
**Goal**: FR-006/FR-010 — read path resolves from stored topology (not `CoordState.MATERIALIZED`);
differential gate gains a pure cell AND retains the live on-disk flattened-stale-coord row across
all 4 handle forms. **Dependencies**: WP03 (parallel with WP05). **Independent test**: live
flattened repro green on all read legs × all handle forms; mutation reverting to MATERIALIZED turns
the on-disk rows red.
Prompt: `tasks/WP04-read-path-stored-topology-gate.md`
- [x] T020 Thread the stored topology into `_resolve_existing_for_slug` (FR-006) (WP04)
- [x] T021 Replace the declared-coord band-aid + correct the stale `:262-264` comment (FR-006, C-004) (WP04)
- [x] T022 ADD the pure stored-topology equivalence cell (FR-010a, NFR-005) (WP04)
- [x] T023 RETAIN/ADD the on-disk flattened-stale-coord row × every handle form (FR-010b, NFR-001) (WP04)
- [x] T024 Live repro + mutation note + static-analysis clean (NFR-001, NFR-004, C-002) (WP04)

### WP05 — Single write-surface authority across planning commits (IC-05)
**Goal**: FR-007/FR-009 — every planning commit + status emission resolves its write surface via the
seam; `safe-commit`'s two responsibilities separated (NFR-002); the 2 mission.py decision sites
routed; the `status_transition.py:336` HEAD-selector drain live-evidence-gated.
**Dependencies**: WP03 (parallel with WP04). **Independent test**: coord-topology planning commit
lands on the seam-resolved surface (#2063 witnessed); generic safe-commit preserved + tested.
Prompt: `tasks/WP05-write-surface-authority.md`
- [x] T025 Separate `safe-commit`'s two responsibilities (FR-007, NFR-002) (WP05)
- [x] T026 Confirm + regression-pin `spec_commit_cmd.py` seam routing (FR-007, #2063) (WP05)
- [x] T027 Route the 2 `.kind is COORDINATION` decision sites through the predicate (FR-005) (WP05)
- [x] T028 Status emission resolves `feature_dir` from the seam (FR-009) (WP05)
- [x] T029 `status_transition.py:336` drain decision (LIVE-EVIDENCE-GATED, FR-009) (WP05)
- [x] T030 Tests + static-analysis gate (WP05)

### WP06 — map-requirements / finalize-tasks share one WP-frontmatter surface (IC-06)
**Goal**: FR-008 — consolidate the WP-`requirement_refs` READ surface to one place so
`map-requirements` and the following `finalize-tasks --validate-only` agree (zero
`unmapped_functional_requirements`, #2064). **Dependencies**: WP05 (mission.py finalize region
linearized first). **Independent test**: map → finalize agree on a coord-topology mission.
Prompt: `tasks/WP06-map-requirements-one-surface.md`
- [x] T031 Consolidate the WP-dir read surface to one resolver (FR-008) (WP06)
- [x] T032 Route the `.kind is COORDINATION` site through the predicate (FR-005) (WP06)
- [x] T033 Non-fakeable regression test: map → finalize agree on a coord topology (#2064) (WP06)
- [x] T034 Predicate-routing test + static gates (NFR-004) (WP06)

### WP07 — Collapse is_committed 3-leg OR (IC-07, LAST, live-repro-gated)
**Goal**: FR-011 — once the surface is structurally single (WP04+WP05), reduce
`is_committed:317-412` from a 3-surface OR to a single-surface check. GATED on the live convergence
proof (the 3-leg OR is a load-bearing workaround — top risk). **Dependencies**: WP04, WP05.
**Independent test**: single-surface check returns the SAME result the 3-leg OR did across all 4
topologies + #1718/#1848 transients (behavior-preserving, NFR-003).
Prompt: `tasks/WP07-is-committed-collapse.md`
- [x] T035 Map the behavioral envelope BEFORE reducing (randy equivalence-evidence) (WP07)
- [x] T036 Route the `.kind is COORDINATION` site through the predicate (FR-005) (WP07)
- [x] T037 Reduce the 3-leg OR to a single-surface check on the resolved placement ref (FR-011) (WP07)
- [x] T038 Prove behavior-preserving + clean gates (NFR-003, NFR-004) (WP07)

## Dependency graph & lanes

```
WP00 (ratchet re-key)
  └─ WP01 (enum/predicate)
       └─ WP02 (store/backfill)
            └─ WP03 (pure resolver + retire derivations)   <- seam keystone
                 |- WP04 (read path + differential gate)   ┐ parallel after WP03
                 |- WP05 (write authority)                 ┘
                       └─ WP06 (map/finalize one surface)
                 WP04 + WP05 -> WP07 (is_committed collapse, LAST, gated)
```

- **Seam chain (sequential, shared anchors `context.py`/`resolution.py`)**: WP00 → WP01 → WP02 → WP03.
- **Structural adoption**: WP04 ∥ WP05 (both after WP03); WP06 after WP05; WP07 after WP04+WP05.
- **Disjoint owned_files** across all 8 WPs (validated by `finalize-tasks --validate-only`). The
  `status_transition.py:336` drain proof lives in WP05's own `create_intent` test
  (`test_wp05_write_target_drain.py`); only the one-line WP00-guard allowlist removal (gated on a
  proven-dead negative-probe) is a documented out-of-map edit, and the line deletion is in WP05's
  owned `status_transition.py`.

> **#2062 closes in stages (anti-partial-close):** WP04 closes only the **read leg** (witnessed live,
> all 4 handle forms); the **terminal** #2062 close is gated on WP05 (status-emit convergence) + WP07
> (green suite). The #2062 issue-matrix verdict stays **`in-mission`** (non-terminal) until the full
> chain lands — no WP claims "#2062 fixed" outright. FR-005's 9 decision sites are split across
> WP01/WP05/WP06/WP07; WP07 runs the integrating repo-wide completeness sweep (the only surviving
> `.kind is COORDINATION` *decision* read is inside `routes_through_coordination`).
