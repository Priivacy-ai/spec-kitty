# Contract: Write-Seam Adoption (FR-007) — implements ADR 2026-06-24-1 C-006

**Not a new ADR** — a citation contract for the adoption pass. Cites `2026-06-24-1` (partition + no-parallel-resolver), `2026-06-24-2` (`target_branch`/`meta.json` anchor), `2026-07-23-1` (COORD is a resolved surface, not a topology condition).

## Rule
Every artifact write that today hand-derives a destination or takes a caller-resolved `feature_dir` MUST resolve its surface through `PlacementSeam.write_target(kind)` and materialize via `commit_for_mission`. No per-command exception to the `kitty-specs/` guards; no second write resolver.

## The TRUE bypass set (route these — NOT the seam's own engine)
- Caller-resolved-`feature_dir` matrix writers: `write_acceptance_matrix` callers (`gates_core.py:492`, `post_consolidation.py:275`, `accept.py`, `backfill_provenance.py:109`); the issue-matrix writer.
- The tracer writer (new).
- The four coord-authority-gate write sites: `decisions/emit.py:71`, `widen/state.py:63`, `agent_tasks_ports.py:322`, `lanes/recovery.py:765`.
- `#2663`: `implement.py::_partition_files_for_commit` partition arm.
- `status/emit.py` write (#2966 slice, route-only per C-003).

## Do NOT route (seam's own engine — routing is circular)
`commit_router` ×4, `write_target_degrade`, `status_transition:300` (the FR-006 mirror), merge infra — the raw `resolve_placement_only` census is not the target.

## Recursion guard (Ledger-M16)
Public boundary → seam; internal callers/leaves (`retrospective/writer.py`, the `read_dir(RETROSPECTIVE)` short-circuit) → the leaf directly. A new writer beneath the short-circuit calls the leaf/`write_target`, never `read_dir`.

## Verification
The read-side census, C-008 shards, and the coord-authority gate stay green; a re-introduced hand-derived write to the wrong surface must still fail a gate (non-vacuity).
