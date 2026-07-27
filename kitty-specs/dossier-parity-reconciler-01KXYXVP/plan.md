# Implementation Plan: Dossier Parity Reconciler

**Branch**: `feat/dossier-parity-reconciler` | **Date**: 2026-07-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/dossier-parity-reconciler-01KXYXVP/spec.md`
**Tracker**: Priivacy-ai/spec-kitty#2180

## Summary

Unify the dossier snapshot hash so the CLI and the SaaS server compute one canonical value identically, and build a `DossierReconciler` that rebuilds a dossier projection and proves it byte-identical to source, failing loud on divergence. This is the provable-parity foundation import-history (#2262) consumes; it is a #1091 launch-gate dependency.

Approach: pick the server's structural hash shape (`path\tcontent_hash` lines, `sha256`, `sha256:` prefix) as canonical, computed over the normalized `WPMetadata` static projection (not raw bytes); migrate the CLI onto it; add the reconciler as a pure rebuild+compare component exposed as both a CLI operation and a library API; land the server-side alignment as a companion PR so the two never disagree in a deployed window; and provide a one-time re-baseline of existing recorded hashes.

## Technical Context

**Language/Version**: Python 3.11+ (CLI package `specify_cli` in spec-kitty; Django app `apps/` in spec-kitty-saas)
**Primary Dependencies**: `hashlib` (sha256); CLI `specify_cli.dossier` (`snapshot.py`, `hasher.py`, `indexer.py`), `specify_cli.sync.emitter`; SaaS `apps/dossier/materialize.py`; `spec_kitty_events`
**Storage**: dossier artifacts on disk (`kitty-specs/**`) + the append-only event journal (source); SaaS Postgres projection (materialized). No new storage introduced.
**Testing**: pytest both repos; ATDD-first — acceptance tests drive parity/divergence outcomes (AS-1..AS-5), plus unit tests for the canonical hash function and the reconciler branches
**Target Platform**: Linux (CLI is cross-platform / host-run; SaaS is a Linux server)
**Project Type**: cross-repo — CLI library + command in `spec-kitty`, server hash alignment in `spec-kitty-saas` (companion PR)
**Performance Goals**: reconcile one mission dossier ≤ 2 s (NFR-002); hash is O(artifacts), no super-linear blowup
**Constraints**: byte-stable deterministic hashing across platforms/runs (NFR-001); fail-closed — never default to "parity" (C-005); no deployed window where CLI and server disagree (C-003)
**Scale/Scope**: re-baseline covers the local backlog (~24 projects, ~700 missions) with zero false-divergence (NFR-003)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** — satisfied and central: the hash algorithm gets ONE owning definition (C-001); this mission exists to remove the current dual-definition drift.
- **Architectural alignment** — no shared-package boundary violation: the canonical hash stays in `specify_cli.dossier`; the server mirrors the same definition (documented cross-repo contract), it does not import the CLI.
- **DDD + tiered rigour** — the reconciler is a pure domain function (rebuild → hash → compare); no request/DB coupling in the core.
- **ATDD-first** — acceptance criteria AS-1..AS-5 drive the tests before implementation.
- **Terminology adherence** — "dossier snapshot hash" is the single canonical term (Domain Language in spec.md); "parity hash" is retired as a synonym.

No violations. Charter check passes.

## Project Structure

### Documentation (this mission)

```
kitty-specs/dossier-parity-reconciler-01KXYXVP/
├── plan.md              # this file
├── spec.md              # committed
├── checklists/          # committed (requirements.md)
├── research.md          # canonical-hash decision record (Phase 0)
├── data-model.md        # ReconciliationResult + hash-input shapes (Phase 1)
├── contracts/           # CLI↔server hash contract + reconciler API contract (Phase 1)
└── tasks.md             # Phase 2 (/spec-kitty.tasks)
```

### Source Code

```
# spec-kitty (CLI) — primary
src/specify_cli/dossier/
├── hasher.py            # IC-01/IC-02: canonical hash (path\tcontent_hash, sha256, sha256: prefix)
├── indexer.py           # IC-01: normalized WPMetadata static-projection input (retire raw-byte WP hashing)
├── snapshot.py          # IC-02: compute_parity_hash_from_dossier migrated to canonical def
├── reconciler.py        # IC-03: NEW — DossierReconciler (rebuild + compare, PARITY|DIVERGENCE)
src/specify_cli/sync/
├── emitter.py           # IC-02: snapshot_hash emit + _is_sha256_hex validation accept sha256: form
src/specify_cli/cli/commands/
├── dossier.py (or sync) # IC-04: NEW reconcile/verify CLI surface + library API for import-history
tests/dossier/           # unit (hash determinism, reconciler branches) + acceptance (AS-1..AS-5)

# spec-kitty-saas (companion PR) — IC-05
apps/dossier/materialize.py   # _compute_snapshot_hash aligned to the canonical definition
```

**Structure Decision**: single-package-per-repo. The canonical hash + reconciler live in `specify_cli.dossier`; the CLI surface in `cli/commands`; the server alignment is a small, separately-reviewable companion change in `apps/dossier/materialize.py`. No new top-level packages.

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Canonical hash definition
- **Purpose**: define ONE hash — sort by path, join `path\tcontent_hash` lines, `sha256`, `sha256:` prefix — computed over the normalized `WPMetadata` static projection, not raw file bytes.
- **Relevant requirements**: FR-001, FR-002, FR-003; C-001, C-004; NFR-001.
- **Affected surfaces**: `dossier/hasher.py`, `dossier/indexer.py`.
- **Sequencing/depends-on**: none (foundation).
- **Risks**: the normalized-projection input aligns with #2686's direction — keep the projection shape stable and documented so #2684/#2686 conform rather than re-defining it.

### IC-02 — CLI emit + validation migration
- **Purpose**: migrate `compute_parity_hash_from_dossier`, the snapshot emit, and `_is_sha256_hex` validation from the old concat/bare-hex form to the canonical definition, without changing the `snapshot_hash` field name.
- **Relevant requirements**: FR-008.
- **Affected surfaces**: `dossier/snapshot.py`, `dossier/hasher.py`, `sync/emitter.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: existing recorded hashes become non-comparable — paired with IC-06 re-baseline; validation must accept the `sha256:` prefix.

### IC-03 — DossierReconciler
- **Purpose**: pure component that rebuilds a dossier projection from source, computes its canonical hash, compares to the recorded/emitted hash, and returns a structured `ReconciliationResult` (PARITY, or DIVERGENCE with named artifacts), failing loud.
- **Relevant requirements**: FR-004, FR-005, FR-006; C-005; NFR-004.
- **Affected surfaces**: NEW `dossier/reconciler.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: fail-closed discipline — any inability to compute/compare returns an error, never a default parity.

### IC-04 — CLI surface + library API
- **Purpose**: expose the reconciler as a supported CLI operation and as a stable library API import-history (#2262) can call to gate materialization.
- **Relevant requirements**: FR-007.
- **Affected surfaces**: `cli/commands/` + the reconciler public entrypoint.
- **Sequencing/depends-on**: IC-03.
- **Risks**: keep the library API narrow and stable so #2262 binds to a contract, not internals.

### IC-05 — Server hash alignment (companion, spec-kitty-saas)
- **Purpose**: align `apps/dossier/materialize.py::_compute_snapshot_hash` to the canonical definition so the server-computed hash equals the CLI-emitted one.
- **Relevant requirements**: FR-001; C-003.
- **Affected surfaces**: `spec-kitty-saas/apps/dossier/materialize.py` (companion PR).
- **Sequencing/depends-on**: IC-01 (shares the definition).
- **Risks**: cross-repo landing order — the canonical hash must be accepted by both sides before either becomes authoritative; no deployed disagreement window.

### IC-06 — Re-baseline migration
- **Purpose**: one-time recompute of existing recorded snapshot hashes under the canonical definition so unchanged content does not read as divergent after cutover.
- **Relevant requirements**: FR-009; NFR-003.
- **Affected surfaces**: a migration/backfill path over recorded hashes.
- **Sequencing/depends-on**: IC-02, IC-05.
- **Risks**: acceptable because there are no live hosted customers; verify zero false-divergence across the local backlog.
