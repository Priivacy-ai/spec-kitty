# Quickstart: Coordination and Merge Stabilization

**Audience**: implementer agents picking up WPs of mission `coordination-merge-stabilization-01KTXRVR` (mid8 `01KTXRVR`).

## Orientation (read first, in order)

1. [spec.md](spec.md) — FRs/NFRs/Constraints; C-001..C-005 are binding.
2. [plan.md](plan.md) — IC map; your WP maps to one IC.
3. [research.md](research.md) — fix-shape decisions R1–R8; do not re-litigate falsified hypotheses.
4. The contract for your class under [contracts/](contracts/).
5. File:line evidence: [validation/debbie-analysis.md](validation/debbie-analysis.md) §your-class.

## Reproduce each defect (red test first)

```bash
# Class B (#1826): coord-topology mission, ≥2 lanes; run spec-kitty merge;
# observe SafeCommitBackstopError at the bookkeeping commit after Stage-1 update-ref.
# Fixture pattern: tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py

# Class C (#1861): on a branch != mission target:
git symbolic-ref HEAD   # note value
spec-kitty agent mission finalize-tasks --mission <m> --validate-only
git symbolic-ref HEAD   # today: changed. Expected: identical.

# Class D (#1833): plant a husk, then exercise move-task:
mkdir -p .worktrees/<slug>-<mid8>-lane-a   # no .git inside
# today: git falls through to primary repo → misattributed verdicts.

# Class A residual (#1814): finalize a coord-topology mission;
git status --porcelain   # today: untracked lanes.json / tasks/* residue on primary

# Class F (#1736): see tests/status/test_event_log_merge.py — add mixed at/timestamp/neither case.
```

## Verify (per WP definition of done)

```bash
.venv/bin/pytest tests/specify_cli/cli/commands/ tests/status/ tests/architectural/ -x -q
.venv/bin/ruff check .
.venv/bin/mypy --strict src/specify_cli   # zero suppressions (NFR-004)
pytest tests/architectural/test_no_legacy_terminology.py  # before any push (C-005)
```

Existing ratchets that must stay green (NFR-005): `tests/status/test_views_gitop_guard.py`, `tests/sync/test_daemon_singleton_reaper_consolidation.py`, `tests/retrospective/test_record_committable_1771.py`, `tests/architectural/test_execution_context_parity.py`.

## Hard rules

- Stability only — if your fix wants to refactor a resolver, allocator, or topology: STOP, it belongs in the #1666 umbrella (C-001).
- No silent data discard — any automated reset/cleanup proves-or-refuses (NFR-002).
- Errors name the resolution used: worktree, ref, placement (NFR-003).
- One mechanism per invariant — no belt-and-braces duplicates (R1, C-003).
- All landing via PR to origin/main; `spec-kitty merge` → local main only (C-005).
