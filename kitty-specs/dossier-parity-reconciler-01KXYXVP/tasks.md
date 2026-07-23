# Tasks: Dossier Parity Reconciler

**Mission**: dossier-parity-reconciler-01KXYXVP | **Branch**: `feat/dossier-parity-reconciler` | **Tracker**: Priivacy-ai/spec-kitty#2180

## Planning Inputs

- [spec.md](./spec.md) — 9 FRs, 4 NFRs, 5 constraints, AS-1..AS-5
- [plan.md](./plan.md) — 6 Implementation Concerns (IC-01..IC-06)
- **Scope note:** IC-05 (server-side `_compute_snapshot_hash` alignment) lives in `spec-kitty-saas`, so it is delivered as a **companion PR** per constraint C-003, not an in-mission WP. The 5 WPs below are all `spec-kitty` (CLI) work.

## Delivery Strategy

WP01 defines the one canonical hash (foundation). WP02 migrates the CLI emit/validation onto it; WP03 builds the reconciler on it — these two are independent and parallel after WP01. WP04 exposes the reconciler (CLI + library API for #2262) after WP03. WP05 re-baselines existing recorded hashes after WP02.

```
WP01 ─┬→ WP02 ──→ WP05
      └→ WP03 ──→ WP04
```

MVP surface: WP01 + WP03 + WP04 (a provable reconciler over the canonical hash). WP02/WP05 complete the emit-side migration + cutover.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Campsite-clean WP01-owned dossier hash surfaces | WP01 | — |
| T002 | Red tests: canonical hash shape (`path\tcontent_hash`, sha256, `sha256:` prefix) + determinism | WP01 | — |
| T003 | Implement canonical hash over the normalized WPMetadata static projection | WP01 | — |
| T004 | Retire raw-byte WP hashing input in the indexer; route to the static projection | WP01 | — |
| T005 | Prove determinism + order-independence + the NFR-001 stability bar | WP01 | [P] |
| T006 | Red tests: emit carries `sha256:`-prefixed value under the unchanged `snapshot_hash` field | WP02 | — |
| T007 | Migrate `compute_parity_hash_from_dossier` to the canonical definition | WP02 | — |
| T008 | Update `sync/emitter` emit + `_is_sha256_hex` validation to accept the canonical form | WP02 | — |
| T009 | Prove backward-compat call-sites unbroken (field name + envelope shape) | WP02 | [P] |
| T010 | Campsite-clean + scaffold the reconciler module surface | WP03 | — |
| T011 | Red acceptance tests: AS-2 rebuild-parity, AS-3 named divergence, AS-4 churn immunity | WP03 | — |
| T012 | Implement rebuild-from-source of a dossier projection | WP03 | — |
| T013 | Implement compare + `ReconciliationResult` (PARITY \| DIVERGENCE with named artifacts) | WP03 | — |
| T014 | Enforce fail-closed (C-005): any compute/compare failure errors, never defaults parity | WP03 | [P] |
| T015 | Red tests: CLI parity exit 0 / divergence non-zero + named; library-API contract | WP04 | — |
| T016 | Implement the reconcile/verify CLI command wrapping the reconciler | WP04 | — |
| T017 | Expose a stable library API for import-history (#2262) to gate on | WP04 | — |
| T018 | Prove NFR-002: reconcile one mission dossier ≤ 2 s | WP04 | [P] |
| T019 | Red tests: unchanged content yields zero false-divergence after re-baseline (NFR-003) | WP05 | — |
| T020 | Implement the one-time re-baseline recompute of recorded snapshot hashes | WP05 | — |
| T021 | Verify zero false-divergence across the local backlog | WP05 | [P] |

## Work Packages

### WP01 — Canonical hash definition
**Goal:** one canonical dossier snapshot hash (server-shape `path\tcontent_hash` + `sha256:`, over the normalized WPMetadata static projection). **Priority:** P1 (foundation). **Independent test:** the hash function is deterministic and matches a fixed golden value. **Depends on:** none. **Prompt:** [tasks/WP01-canonical-hash-definition.md](./tasks/WP01-canonical-hash-definition.md)

- [x] T001 Campsite-clean WP01-owned dossier hash surfaces (WP01)
- [x] T002 Red tests: canonical hash shape + determinism (WP01)
- [x] T003 Implement canonical hash over the normalized WPMetadata static projection (WP01)
- [x] T004 Retire raw-byte WP hashing input in the indexer (WP01)
- [x] T005 Prove determinism + order-independence + NFR-001 stability (WP01)

### WP02 — CLI emit + validation migration
**Goal:** migrate the CLI snapshot emit + validation onto the canonical hash without changing the `snapshot_hash` field name. **Priority:** P1. **Independent test:** an emitted snapshot event carries the canonical `sha256:` value and validation accepts it. **Depends on:** WP01. **Prompt:** [tasks/WP02-cli-emit-migration.md](./tasks/WP02-cli-emit-migration.md)

- [x] T006 Red tests: emit carries `sha256:`-prefixed value under unchanged field (WP02)
- [x] T007 Migrate `compute_parity_hash_from_dossier` to the canonical definition (WP02)
- [x] T008 Update emitter emit + `_is_sha256_hex` validation (WP02)
- [x] T009 Prove backward-compat call-sites unbroken (WP02)

### WP03 — DossierReconciler
**Goal:** a pure rebuild+compare reconciler returning PARITY or named DIVERGENCE, fail-closed. **Priority:** P1. **Independent test:** AS-2/AS-3/AS-4 acceptance pass. **Depends on:** WP01. **Prompt:** [tasks/WP03-dossier-reconciler.md](./tasks/WP03-dossier-reconciler.md)

- [x] T010 Campsite-clean + scaffold the reconciler module (WP03)
- [x] T011 Red acceptance tests: AS-2/AS-3/AS-4 (WP03)
- [x] T012 Implement rebuild-from-source (WP03)
- [x] T013 Implement compare + `ReconciliationResult` (WP03)
- [x] T014 Enforce fail-closed (C-005) (WP03)

### WP04 — CLI surface + library API
**Goal:** expose the reconciler as a CLI operation and a stable library API for import-history (#2262). **Priority:** P2. **Independent test:** CLI exits 0 on parity, non-zero + named on divergence; API returns a structured result. **Depends on:** WP03. **Prompt:** [tasks/WP04-cli-surface-and-api.md](./tasks/WP04-cli-surface-and-api.md)

- [ ] T015 Red tests: CLI exit codes + named divergence; library-API contract (WP04)
- [ ] T016 Implement the reconcile/verify CLI command (WP04)
- [ ] T017 Expose the stable library API for #2262 (WP04)
- [ ] T018 Prove NFR-002 (≤ 2 s single mission) (WP04)

### WP05 — Re-baseline migration
**Goal:** one-time recompute of recorded snapshot hashes under the canonical definition so unchanged content is not flagged divergent post-cutover. **Priority:** P2. **Independent test:** re-baseline over unchanged content yields zero divergence. **Depends on:** WP02. **Prompt:** [tasks/WP05-rebaseline-migration.md](./tasks/WP05-rebaseline-migration.md)

- [ ] T019 Red tests: zero false-divergence after re-baseline (NFR-003) (WP05)
- [ ] T020 Implement the one-time re-baseline recompute (WP05)
- [ ] T021 Verify zero false-divergence across the local backlog (WP05)
