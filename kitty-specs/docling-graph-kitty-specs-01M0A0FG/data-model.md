# Research Data Model

## Entities

### AuthorityFact

A source-specific claim with `fact_class`, `value`, canonical authority, mutation owner, logical artifact identity, raw byte span, and lifecycle phase. Contradictory facts remain separate claims; a graph must not collapse them.

### ArtifactIdentity

The tuple `repository_uuid + mission_id + MissionArtifactKind + logical path + source blob`. Local IDs such as `FR-001` or `WP02` are qualified by this tuple before aggregation.

### SourceEvidence

A registered primary source or raw empirical result with source ID, immutable revision/hash, access date, inclusion status, and supported claim IDs.

### Candidate

One instantiated option-lattice row: representation, authority/mutation owner, transform, persistence, lifecycle, aggregation, inference, egress/retention/consent, migration, and rollback.

### ProbeObservation

An immutable result linked to candidate, sealed input, command, environment, repetition, oracle scope, status (`PASS|FAIL|UNKNOWN|N/A`), and raw-result hash.

### DerivedProjection

A non-authoritative disposable or content-addressed view over `AuthorityFact` records. It owns no canonical facts and must refuse stale reads after any authority/config/schema/model change.

## Invariants

1. Current source formats remain authoritative during this mission; probes never mutate them.
2. Canonical-replacement options are evaluated counterfactually, not assumed safe or impossible.
3. Every derived fact keeps authority class, artifact identity, and exact provenance; inference never upgrades to authored truth.
4. Repository and mission namespaces precede local identifiers.
5. PRIMARY/COORD placement is resolved through `MissionArtifactKind`; a directory walk is not a logical mission read.
6. Persisted projections have explicit invalidation, deletion, rollback, permission, consent, and version contracts.
7. Missing semantic, privacy, platform, ecosystem, or user evidence stays `UNKNOWN`; it is never imputed.

## Candidate state machine

`absent → building → valid(hash-bound) → stale → rebuilding|deleted`, with failure returning to the last valid content-addressed version or `absent`. Canonical cutover candidates additionally require `precutover snapshot → transactional cutover → sole writer → verified views`, with atomic rollback to the immutable snapshot.
