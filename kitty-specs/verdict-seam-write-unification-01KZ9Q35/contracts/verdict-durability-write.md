# Contract — Verdict-Durability Write (SC-004 / D2)

**Owner**: `status/emit.py::emit_status_transition` (the authoritative durable write).
**Demoted**: `review/cycle.py` per-file `.md` commit → best-effort render.

## Guarantees

- **G1 (single authoritative call)**: exactly one `emit_status_transition` append per recorded
  verdict is the authoritative durable act. The `.md` render commit is best-effort and **MAY fail
  without erroring**. *(NFR-004)*
- **G2 (concurrency)**: two concurrent distinct verdicts → two durable event records or one explicit
  refusal; never a silent drop, never a spurious crash. The event log is union-merge-driver protected,
  so concurrent appends union rather than clobber. *(SC-003)*
- **G3 (NFR-001)**: no inter-process lock is held across a `git` subprocess. Serialization is the
  event-log append discipline, not a lock spanning `git`.
- **G4 (responsiveness)**: one verdict record incl. durable persistence completes < 2 s. *(NFR-005)*

## Retired (as authoritative machinery)

The per-file `_commit_review_cycle_artifact` retry loop, hard-error-on-non-committed, and
orphan-cleanup are retired as the *authoritative* durability path (kept at most as best-effort-render
defense-in-depth during migration).

## Verified by

`tests/integration/test_review_durability_matrix.py` (50 iterations × 2 OS processes, serial `-n0`);
`tests/review/test_cycle.py` (perf).
