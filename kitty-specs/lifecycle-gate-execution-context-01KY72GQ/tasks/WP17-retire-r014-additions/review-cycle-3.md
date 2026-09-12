---
affected_files:
- src/specify_cli/acceptance/__init__.py
- tests/specify_cli/acceptance/test_accept_dirty_kitty_ops.py
cycle_number: 3
mission_slug: lifecycle-gate-execution-context-01KY72GQ
reproduction_command: PWHEADLESS=1 uv run --extra test pytest tests/specify_cli/acceptance/test_accept_dirty_kitty_ops.py tests/specify_cli/test_accept_gate_convergence.py tests/architectural/test_exemption_registry_ratchet.py -q
reviewed_at: '2026-07-24T11:05:00Z'
reviewer_agent: reviewer-renata (claude/opus)
verdict: approved
wp_id: WP17
---

# WP17 Review — Cycle 2 (artifact cycle-3): APPROVE

Reviewer: reviewer-renata (independent scrutiny). Focused re-verification of the cycle-1 BLOCKER 1 fix (commit `d41fa28e6`). All other cycle-1 PASS checks (symbol absence, survivor honesty, dead field, quality) were untouched by the fix and remain valid.

## BLOCKER 1 (cycle-1) — CLOSED

The accept-gate false-pass on `status.events.jsonl` is fixed. `_is_accept_pipeline_own_write` (`src/specify_cli/acceptance/__init__.py:161-166`) now scopes the `STATUS_STATE` branch to the specific own-write basename:

```python
kind = kind_for_mission_file(path, mission_slug=mission_slug)
if kind is MissionArtifactKind.ACCEPTANCE_MATRIX:
    return True
if kind is MissionArtifactKind.STATUS_STATE:
    basename = to_posix(path).rsplit("/", 1)[-1]
    return basename == "status.json"
return False
```

`ACCEPTANCE_MATRIX` (maps only to `acceptance-matrix.json`) still matches wholesale; the append-only `status.events.jsonl` (also `STATUS_STATE`) no longer qualifies. It is a function-local kind-typed branch — no filename frozenset reintroduced (R-014 ratchet untripped; `ACCEPT_OWNED_PATHS` still absent from `src/`).

**Empirical proof** (`_is_accept_pipeline_own_write`, flat mission):

| path | result | expected |
|---|---|---|
| `status.events.jsonl` | `0` — BLOCKS | blocks (read-only for accept; genuine uncommitted lane-state) ✓ |
| `status.json` | `1` — exempt | exempt (daemon-materialized own-write) ✓ |
| `acceptance-matrix.json` | `1` — exempt | exempt (`_check_lane_gates` own-write) ✓ |
| `other-mission/status.json` | `0` — BLOCKS | blocks (mission-scoped) ✓ |

## Red-first test — genuine

`tests/.../test_accept_dirty_kitty_ops.py::TestAcceptGateOwnWriteScoping` calls the real `_accept_dirty_gate` (flat/SINGLE_BRANCH fixture, coord-residue arm is a no-op → isolates arm 1) and asserts the actual gate output, not a spy:

- `test_status_events_jsonl_still_blocks_accept_gate_under_flat_topology` asserts `len(result) == 1` (the path SURVIVES filtering = blocks). This reddens on the pre-fix `kind in (ACCEPTANCE_MATRIX, STATUS_STATE)` predicate (verified in cycle-1 that the old code benigned it under flat) — a true block-assertion, red-first by construction.
- Three counter-contracts pin `status.json` exempt, `acceptance-matrix.json` exempt, and another mission's `status.json` still blocking.

## Suites / quality

- `tests/specify_cli/acceptance/test_accept_dirty_kitty_ops.py` + `tests/specify_cli/test_accept_gate_convergence.py`: **18 passed**.
- `tests/architectural/test_exemption_registry_ratchet.py`: **12 passed** (no new exemption row/frozenset).
- ruff clean on `acceptance/__init__.py`; mypy shows the 2 pre-existing errors only, now line-shifted to `:270` (subclass `TaskCliError`) and `:696` (return-Any) — same defects on untouched lines, not new. Zero new suppressions.

## Verdict

APPROVE. The false pass is closed with a genuine red-first block test; the survivor split and all other cycle-1 PASS checks hold.
