# Mission Specification: Dossier Parity Reconciler

**Mission:** dossier-parity-reconciler-01KXYXVP
**Tracker:** Priivacy-ai/spec-kitty#2180
**Type:** software-dev

## Overview

Today the dossier snapshot hash is computed two different ways. The CLI computes it as a sorted concatenation of per-artifact content hashes (bare hex); the SaaS server computes it as sorted `path\tcontent_hash` lines with a `sha256:` prefix. The two do not match, and the reconciler the server's contract names does not exist. The result: nothing can prove that a rebuilt dossier projection is the same as its source across the CLI/server boundary.

This mission delivers the parity foundation for provable materialization: **one canonical snapshot-hash definition computed identically on both sides**, and a **DossierReconciler** that rebuilds a dossier projection and proves it byte-identical to the source, failing loud on any divergence. This is what lets historical import (#2262) claim "your projects are faithfully in TeamSpace" as a proven fact rather than a promise. It is a #1091 launch-gate dependency.

## User Scenarios & Testing

### Primary scenario
An operator (or an automated sync/import path acting on their behalf) has a dossier for a mission on the local side and a materialized projection of it on the hosted side. They need to know, with certainty, that the two represent the same content. The reconciler computes the canonical hash on both sides and reports parity or a named divergence. When it reports parity, that is a proof, not an assertion.

### Acceptance scenarios
- **AS-1 (cross-side agreement):** Given the same dossier content, when the hash is computed by the CLI emit path and by the server materialize path, then the two hashes are identical.
- **AS-2 (rebuild proof):** Given a source dossier and its projection, when the reconciler rebuilds the projection and compares hashes, then it reports PARITY and identifies zero differing artifacts.
- **AS-3 (divergence caught):** Given a projection where exactly one artifact differs from source, when the reconciler runs, then it reports DIVERGENCE, names the differing artifact, and exits non-zero — it never reports success.
- **AS-4 (churn immunity):** Given a WP whose runtime-mutable fields changed but whose canonical content did not, when the hash is recomputed, then the hash is unchanged (no false divergence).
- **AS-5 (consumer contract):** Given the import-history path needs to assert server-side parity, when it calls the reconciler as a library API, then it receives a structured parity/divergence result it can gate on.

### Edge cases
- An artifact present in source but absent in the projection (and vice versa) is reported as a named divergence, not a silent skip.
- Empty dossier (zero artifacts) produces a stable, defined hash on both sides.
- Ordering of artifacts on disk must not affect the hash (path-sorted, deterministic).
- A one-time re-baseline of previously recorded hashes must not raise false divergence on unchanged content.

## Domain Language

- **Dossier snapshot hash (canonical):** the single content-addressed anchor for a mission dossier. Definition: for each active artifact, take its normalized-projection content hash; sort entries by artifact path; join `path\tcontent_hash` lines with newlines; `sha256` the result; prefix the digest with `sha256:`. One definition, both sides.
- **DossierReconciler:** the component that rebuilds a dossier projection from source and verifies its snapshot hash equals the recorded/emitted hash.
- **Parity / Divergence:** the two outcomes of a reconciliation. Parity is proof of sameness; Divergence names what differs.
- Avoid: "parity hash" and "snapshot hash" as if they were two things — they are one canonical value under this mission.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The system computes a single canonical dossier snapshot hash that is byte-identical whether produced by the CLI emit path or the server materialize path for the same dossier content. | Draft |
| FR-002 | The canonical hash is computed over the normalized WP static-projection content, not raw artifact bytes, so runtime-mutable churn does not change the hash. | Draft |
| FR-003 | The canonical hash structure is: sort entries by artifact path, join `path\tcontent_hash` lines, `sha256`, `sha256:`-prefixed digest. The CLI's prior concat-of-hashes / bare-hex form is retired. | Draft |
| FR-004 | A DossierReconciler rebuilds a dossier projection from the source artifact/event stream and computes its canonical snapshot hash. | Draft |
| FR-005 | The reconciler compares the rebuilt hash against the recorded/emitted snapshot hash and returns a structured result: PARITY, or DIVERGENCE with the differing artifact paths named. | Draft |
| FR-006 | On divergence the reconciler fails loud — surfaces an explicit error and a non-zero exit on the CLI surface — and never reports success or silently proceeds. | Draft |
| FR-007 | The reconciler is available both as a supported CLI operation and as a library API that import-history (#2262) can consume to gate materialization. | Draft |
| FR-008 | The CLI snapshot-hash emit path and its validation are migrated to the canonical definition without changing the `snapshot_hash` field name in the emitted event; the value format moves to the canonical `sha256:`-prefixed form and validation accepts it. | Draft |
| FR-009 | A one-time re-baseline path recomputes existing recorded snapshot hashes under the canonical definition so unchanged content does not read as divergent after cutover. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Hash computation is deterministic and platform-stable (byte-stable ordering and encoding). | 100% identical hash across >=100 repeated runs and across both repos for the same input. | Draft |
| NFR-002 | Reconciling a single mission dossier is fast enough for interactive and batch use. | <= 2 s for a typical mission dossier; full-project sweep scales linearly in artifact count with no super-linear blowup. | Draft |
| NFR-003 | The migration is backward-safe: no false divergence on content that did not change. | 0 false-divergence reports across the local backlog (~24 projects, ~700 missions) after re-baseline. | Draft |
| NFR-004 | Divergence reporting is actionable. | Every DIVERGENCE result names >=1 specific differing artifact path; no bare "mismatch" without detail. | Draft |

### Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | One canonical definition only. The CLI and server MUST NOT carry two hash formulas; the algorithm has a single owning source. | Binding |
| C-002 | Out of scope: import-history itself (#2262) and WP runtime-state eviction (#2684). This mission delivers only the parity foundation those consume. | Binding |
| C-003 | Cross-repo delivery: reconciler + CLI hash land in `spec-kitty`; the server hash alignment lands as a companion PR in `spec-kitty-saas`. There must be no deployed window where CLI and server disagree — the two land compatibly (canonical hash accepted by both before either becomes authoritative). | Binding |
| C-004 | The canonical hash input is the normalized WP static projection (the #2686 direction). Raw-byte hashing of WP artifacts is retired. #2686/#2684 conform to this definition, not the reverse. | Binding |
| C-005 | Fail-closed: a reconciler that cannot compute or compare a hash reports an error, never a default "parity". | Binding |

## Success Criteria

- **SC-001:** For any mission dossier, the CLI-side and server-side canonical hashes are identical in 100% of cases.
- **SC-002:** A rebuilt projection is verified against source with zero silent passes: 100% of single-artifact divergences are detected and named.
- **SC-003:** Import-history can obtain a provable server-side parity result from the reconciler (the capability exists and is consumable as an API).
- **SC-004:** After cutover and re-baseline, the local backlog shows zero false-divergence reports on unchanged content.

## Key Entities

- **Canonical dossier snapshot hash** — the content-addressed anchor (one definition, both sides).
- **DossierReconciler** — rebuilds and verifies; emits a structured parity/divergence result.
- **Normalized WP static projection** — the churn-free hash input.
- **Reconciliation result** — PARITY | DIVERGENCE(named artifacts); the gate value consumers act on.

## Assumptions

- **A-001:** The canonical definition aligns the CLI to the server's `path\tcontent_hash` + `sha256:` structure. This is a made decision; downstream hash work conforms to it.
- **A-002:** The normalized WP static projection (#2686 input) is the canonical hash input. If #2684/#2686 land after this mission, they adopt this definition.
- **A-003:** A one-time re-baseline of existing recorded hashes is acceptable — there are no live hosted customers, so historical hashes can be recomputed under the canonical definition.
- **A-004:** The server's existing `_compute_snapshot_hash` structure is the correct target shape (it carries path + stable ordering, which the CLI's concat form loses); the CLI moves to it rather than the reverse.

## Dependencies

- **Consumes:** the dossier artifact/event model and the WP projection surface.
- **Consumed by:** import-history (#2262) and the TeamSpace replay projection (#511).
- **Related / conforms-to-this:** #2686 (WP static-projection hash input) and #2684 (WP runtime-state eviction) — this mission sets the canonical hash definition they align to.

## Out of Scope

- Building `spec-kitty sync import-history` (#2262).
- Evicting WP runtime state from `WP##.md` (#2684).
- The TeamSpace-side replay/time-travel projection surface (#511).
