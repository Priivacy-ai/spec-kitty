# Contract — Placement Enforcement (write + read)

## Write (FR-001, NFR-001, NFR-004)
- **Given** any `src/` Python module, **when** it performs a mission-artifact commit (`safe_commit(target=…)` / constructs `CommitTarget(ref=…)` / calls `write_meta(...)` for a mission-artifact path), **then** the target MUST be derived from the placement seam (`resolve_placement_only` / `placement_seam.write_target(kind)`).
- **Gate**: `tests/architectural/test_no_write_side_rederivation.py` scans **all** of `src/` (no module allowlist); `test_safe_commit_import_boundary.py` additionally asserts `target=CommitTarget(...)` is seam-derived. A synthetic non-seam-derived write in any module reds the gate.
- **Exclusions**: only individually-justified sanctioned primitives (e.g. lane-deliverable commit, invocation/upgrade commits) — each carries an inline rationale; the exclusion set is NOT a module allowlist.
- **Non-regression**: the three existing gates stay green.

## Read (FR-004, NFR-002)
- **Given** a mission-artifact read for a kind, **when** it resolves a surface, **then** it MUST resolve through `artifact_home_for(kind).read_surface`; a coord-homed kind resolving to a primary substitute **raises a typed partition-mismatch error** (no silent fallback).
- **Gate**: NEW `tests/architectural/test_read_surface_placement_guard.py`, symmetric to the write gate.
- **Reconciliation**: existing #2906 accept-time read guards remain; the new authority generalizes them, it does not double-guard or regress the lenient diagnose path.

## Routing coverage (FR-003, FR-006)
- The `emit` `_current_branch` HEAD-derived fallback (#1716) is removed; `bookkeeping_projection` / `bookkeeping_commit` / `decision_log` route through the port; `decisions.events.jsonl` and `traces/` are classified in the partition SSOT (COORD).
