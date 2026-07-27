# Tasks — name-vs-authority-remediation-01KTYGTE

> **Branch retarget (2026-06-12):** PR #1895's branch (`feat/doctrine-glossary-consolidation-01KTNWFC`) entered review/merge; this mission now lands on `feat/name-vs-authority-remediation-01KTYGTE` (branched from that head). All branch-contract references to the old branch resolve to the new one.


**Plan**: [plan.md](./plan.md) | **Decisions**: plan §Plan-time decisions (D1–D4, all resolved) | **change_mode**: standard
**Branch**: planning base = merge target = `feat/doctrine-glossary-consolidation-01KTNWFC`

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Pinning regressions for #1889 + #1885 symptom (ATDD, pass on current tree) | WP01 | [P] |
| T002 | FR-001 #1884: committed-spec gate via placement authority | WP01 | |
| T003 | FR-003 #1885 residual: structured error replaces silent stub | WP01 | |
| T004 | FR-013 #1896: substantive-gate regex alignment + actionable reason | WP01 | |
| T005 | Evidence pack for verified-fixed ticket closures | WP01 | |
| T006 | Accept convergence test (ATDD, all modes — RED first) | WP02 | [P] |
| T007 | ACCEPT_OWNED_PATHS seam: snapshot-before-write + exclusion | WP02 | |
| T008 | Mode-matrix tests + upstream-workaround compatibility | WP02 | |
| T009 | WorktreeTopology + classifier + registry xref (ATDD incl. husk case) | WP03 | [P] |
| T010 | FR-008 decision table incl. net-new R3 (branch-deleted, loud) | WP03 | |
| T011 | Migrate 5 topology consumer sites | WP03 | |
| T012 | Topology suites + architectural green | WP03 | |
| T013 | mission_branch_name_required + BranchIdentityUnresolved (ATDD, dual-era) | WP04 | [P] |
| T014 | Migrate 6 branch-identity consumer sites (incl. legacy-only parsers) | WP04 | |
| T015 | #1860 regression + dual-era integration tests | WP04 | |
| T016 | aggregate.py: both-seam migration | WP05 | |
| T017 | status_transition.py:265 fabrication kill + predicate migration (C-002 ranges) | WP05 | |
| T018 | implement.py:395 fabrication kill | WP05 | |
| T019 | Cross-seam integration tests + grep-zero fabrication | WP05 | |
| T020 | #1865 styleguide deltas (+2 addenda) | WP06 | [P] |
| T021 | #1866 procedure canonical-tree carve-out | WP06 | |
| T022 | #1867 toolguide pagination generalization + validate + conditional regen | WP06 | |
| T023 | Flip resolver default + 2 source prompts + charter.md | WP07 | [P] |
| T024 | Update 2 governance-contract + 3 charter tests | WP07 | |
| T025 | Regenerate agent copies + twelve-agent parity baselines (atomic with templates) | WP07 | |
| T026 | ADR append-only "executed" addendum + full architectural green | WP07 | |
| T027 | Extractor: _resolve_path_ref + styleguide reference walk (deterministic) | WP08 | [P] |
| T028 | Toolguide schema: additive references field + walk | WP08 | |
| T029 | Graph regen (+~27 edges) + freshness/idempotency/unit tests | WP08 | |
| T030 | Ratchet: 3 assertions (allowlist / AST compose scan / fabrication zero) | WP09 | |
| T031 | Strictness proofs ×3 (rogue injections, mandatory evidence) | WP09 | |
| T032 | Full architectural suite + marker conventions | WP09 | |

## Work Packages

### WP01 — P0 quick fixes + verification pins (FRs 001/003/004/013) · prompt: [tasks/WP01-p0-quickfixes-and-pins.md](tasks/WP01-p0-quickfixes-and-pins.md)
Goal: kill the small live roots, pin the already-fixed P0s, fix the gate parser. Independent; dispatch first (release-critical).
- [x] T001 Pinning regressions #1889 + #1885 symptom (WP01)
- [x] T002 FR-001 placement-authority gate (WP01)
- [x] T003 FR-003 structured error (WP01)
- [x] T004 FR-013 parser alignment (WP01)
- [x] T005 Evidence pack (WP01)

### WP02 — Accept idempotency (FR-002) · prompt: [tasks/WP02-accept-idempotency.md](tasks/WP02-accept-idempotency.md)
Goal: ROOT-β — accept ∘ accept converges in every mode. Independent; release-critical.
- [ ] T006 Convergence test, all modes (WP02)
- [ ] T007 ACCEPT_OWNED_PATHS seam (WP02)
- [ ] T008 Mode-matrix tests (WP02)

### WP03 — Topology authority seam + R3 (FR-005, FR-008) · prompt: [tasks/WP03-topology-authority-seam.md](tasks/WP03-topology-authority-seam.md)
Goal: the registry disposes. Parallel with WP04.
- [x] T009 Seam API + classifier (WP03)
- [x] T010 Decision table + R3 (WP03)
- [x] T011 Migrate 5 sites (WP03)
- [x] T012 Suites green (WP03)

### WP04 — Branch-identity authority seam (FR-006) · prompt: [tasks/WP04-branch-identity-seam.md](tasks/WP04-branch-identity-seam.md)
Goal: grammar + meta dispose; dual-era resolution; closes the #1860 class. Parallel with WP03.
- [x] T013 Grammar helper + structured error (WP04)
- [x] T014 Migrate 6 sites (WP04)
- [x] T015 #1860 regression + dual-era tests (WP04)

### WP05 — Cross-seam consumers + fabrication eradication (FR-007) · prompt: [tasks/WP05-cross-seam-consumers.md](tasks/WP05-cross-seam-consumers.md)
Depends on: WP03, WP04.
- [x] T016 aggregate.py both-seam migration (WP05)
- [x] T017 status_transition.py fabrication + predicate (WP05)
- [x] T018 implement.py fabrication (WP05)
- [x] T019 Integration tests (WP05)

### WP06 — Doctrine deltas #1865/66/67 (FR-010) · prompt: [tasks/WP06-doctrine-deltas.md](tasks/WP06-doctrine-deltas.md)
Independent lane; deltas pre-drafted in research.
- [ ] T020 Styleguide deltas (WP06)
- [ ] T021 Procedure carve-out (WP06)
- [ ] T022 Toolguide pagination + validate (WP06)

### WP07 — Authority-path flip (FR-011) · prompt: [tasks/WP07-authority-path-flip.md](tasks/WP07-authority-path-flip.md)
Independent lane; the WHOLE 7-link chain in one WP, parity baselines included.
- [ ] T023 Resolver + prompts + charter.md (WP07)
- [ ] T024 5 test updates (WP07)
- [ ] T025 Agent copies + parity baselines (WP07)
- [ ] T026 ADR addendum + architectural green (WP07)

### WP08 — DRG extractor walk (FR-012) · prompt: [tasks/WP08-extractor-walk.md](tasks/WP08-extractor-walk.md)
Independent lane.
- [x] T027 Path-ref resolver + styleguide walk (WP08)
- [x] T028 Toolguide schema field + walk (WP08)
- [x] T029 Regen + tests (WP08)

### WP09 — Topology ratchet (FR-009) · prompt: [tasks/WP09-topology-ratchet.md](tasks/WP09-topology-ratchet.md)
Depends on: WP03, WP04, WP05. Lands LAST; strictness proofs mandatory.
- [x] T030 Three assertions (WP09)
- [x] T031 Strictness proofs (WP09)
- [x] T032 Full suite + markers (WP09)

## Parallelization

Wave 1 (immediate, parallel): WP01, WP02, WP03, WP04, WP06, WP07, WP08 — seven independent lanes (release-critical WP01/WP02 first if capacity-limited). Wave 2: WP05 (after WP03+WP04, lanes merged in). Wave 3: WP09 (after WP05). Critical path: WP03/WP04 → WP05 → WP09 (3 hops).
