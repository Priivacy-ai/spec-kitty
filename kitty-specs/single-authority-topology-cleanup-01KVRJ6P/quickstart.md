# Quickstart / Validation — Single-Authority Topology Cleanup & Dedup

How a reviewer validates the mission's acceptance levers. All commands run from the
repo root. This is a behavior-neutral refactor — the gates ARE the acceptance.

## 1. Differential-equivalence gate (FR-010, the central lever)
```bash
PWHEADLESS=1 pytest tests/missions/test_surface_resolution_equivalence.py -q
```
- Must be **green** across every `(topology × transient)` cell, **including** the new classify-on-read ≡ backfill-then-read cell.
- The new cell asserts GREEN — it must NOT be parked behind an `_XFAIL_*_OUT_OF_SCOPE` marker (DIRECTIVE_041 / IC-01).

## 2. The FR-004 correctness improvement — live RED→GREEN repro (NFR-002)
```bash
# On pre-FR-004 code the un-backfilled-flattened-mission repro is RED
#   (resolves to the stale-coord husk). After FR-004 it is GREEN (resolves PRIMARY).
PWHEADLESS=1 pytest tests/missions/ -k "unbackfilled_flattened or classify_on_read" -q
```
- Acceptance: the test **fails on `main` (pre-FR-004)** and **passes after FR-004**, proving the absorption is a real correctness win, not a static edit.

## 3. AST guard — non-fakeable eradication (FR-011 / NFR-003)
```bash
PWHEADLESS=1 pytest tests/architectural/ -k "commit_target_kind or topology_inference" -q
# planted-literal self-check: a planted `CommitTargetKind` ref OR a serialized
# former `FLATTENED.value` must make the guard RED (symbol/AST, not grep).
```

## 4. The eradication is complete (SC-001)
```bash
# zero CommitTargetKind references in src/ (AST-level; the guard enforces this)
rg -n "CommitTargetKind" src/ ; echo "expect: no matches in src/"
```

## 5. accept + merge no longer trip on coordination residue (SC-002, FR-008/009/012)
```bash
PWHEADLESS=1 pytest tests/specify_cli/ -k "accept and (dirty or residue or unchecked)" -q
PWHEADLESS=1 pytest tests/ -k "advance_branch_ref or post_merge_invariant or coord_owned" -q
```
- A coordination-topology mission with only residue passes the accept dirty gate; a flat mission's real primary artifacts still block.
- A post-write ff-advance with coordination residue on a checked-out worktree does not raise `RefAdvanceDirtyWorktreeError`.
- An orchestrated mission (all WPs approved/done, checkboxes unticked) passes the unchecked-tasks gate.

## 6. #1891 — `--json` emits valid JSON (FR-013)
```bash
spec-kitty agent tasks map-requirements --mission <handle> --json | python3 -m json.tool >/dev/null && echo "valid JSON"
```

## 7. Dedup is real + KEEP set intact (SC-004 / SC-005 / NFR-004/005)
```bash
# net LOC reduction reported in the PR body; KEEP sites unchanged/test-pinned
PWHEADLESS=1 pytest tests/architectural/ -q          # full architectural sweep, green
git diff --stat main...HEAD | tail -1                 # net negative LOC
```
- KEEP check: `surface_resolver.py:667-678` husk short-circuit (C-001), the three C-002 relays, the 5-hop path (C-003), and the transient probes (C-005) map to unchanged or test-pinned sites.

## Full pre-merge sweep (NFR-001)
```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
PWHEADLESS=1 pytest tests/sync/test_orphan_sweep.py -n0 -q   # serial real-port pass
ruff check . && mypy src/
pytest tests/architectural/test_no_legacy_terminology.py     # CI-only gate, run pre-push
```
