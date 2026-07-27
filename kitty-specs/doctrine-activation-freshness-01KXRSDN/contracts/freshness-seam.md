# Contract — Activation ⇒ freshness seam

Behavioral contracts (this is a CLI/library mission — no HTTP endpoints). Each contract is a
red-first acceptance target through a pre-existing entry point.

## CT-01 — Activation makes the derived signal stale (FR-001/002/003; SC-002)

- **Entry point**: `charter activate <kind> <id>` then the freshness computation
  (`_compute_synthesized_drg` via `compute_freshness`).
- **Given** a project whose bundle + DRG are fresh,
  **When** `charter activate` flips an `activated_*` key,
  **Then** the synthesized-DRG signal is `stale` (config↔derived parity mismatch), where it
  previously reported `fresh`.
- **And** reconciling (`charter generate`/`synthesize`) returns it to `fresh`.
- **And** `deactivate` is symmetric.
- **Writer-agnostic**: a config state produced by `merge_defaults` (not `commit_plan`) is
  equally visible.

## CT-02 — references.yaml absence is actionable, not a dead-end (FR-005; SC-003)

- **Entry point**: freshness/synthesize on a synced-but-not-generated project.
- **Given** `governance/directives/metadata.yaml` present but `references.yaml` absent,
  **When** freshness/synthesize preflight runs,
  **Then** it fails **closed** with a single actionable message naming `charter generate` —
  **not** a permanent-stale `None` that `synthesize` cannot clear.
- **And** the 4-file hash set is unchanged (no narrowing); a **complete** bundle hashes
  byte-identically to before (NFR-002).

## CT-03 — One-pass prerequisite report (FR-006; SC-004)

- **Entry point**: the implement-boundary charter preflight (`_attempt_auto_refresh`).
- **Given** `charter_source`, `synced_bundle`, and `synthesized_drg` all owing refresh,
  **When** the preflight runs,
  **Then** it reports **all** outstanding charter-owed prerequisites in one pass (not raise-on-first).
- **And** each per-prerequisite verdict is unchanged vs today (additive aggregation).
- **Fence**: the analyzer-freshness gate (`check_analysis_report_current`, #2157b) is untouched.

## CT-04 — Opt-in eager resynthesis; default stays cheap (FR-007; NFR-001/003)

- **Entry point**: `charter activate/deactivate [--resynthesize]`.
- **Given** a fresh project,
  **When** `charter activate <kind> <id> --resynthesize` runs,
  **Then** the freshness signal is `fresh` immediately afterward.
- **When** `charter activate <kind> <id>` runs **without** the flag,
  **Then** the signal is `stale` **and zero** synthesis/`regenerate-graph` subprocess was spawned
  (call-count/subprocess spy).
- **And** the `spec-kitty upgrade` migration + `org_charter` `promote_activations` spawn no synthesis.
- **And** `commit_plan` (charter) is not modified (C-001).

## CT-05 — Shipped DRG durably fresh (FR-004; SC-001; NFR-004)

- **Entry point**: `spec-kitty doctrine regenerate-graph --check` and the 4 DRG tests.
- **Given** the shipped doctrine source,
  **When** the graph is regenerated,
  **Then** it is byte-identical to the committed `graph.yaml`; the zero-delta baseline matches;
  the charter citation resolves (no dangling reference).
- **And** the four tests pass with `@pytest.mark.regression` removed.

## CT-06 — #2732 content-identity preserved (NFR-002; SC-006)

- **Given** an unchanged bundle,
  **When** `compute_bundle_content_hash` runs before and after this mission's changes,
  **Then** the hash is identical; the per-file recipe, write-side stamps, `built_in_only`
  normalization, and fresh-seed early-exit are intact.
