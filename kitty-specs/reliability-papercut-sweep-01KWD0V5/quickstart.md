# Quickstart: Verifying the Reliability Papercut Sweep

Each fix has a red-first regression test (NFR-001). Run from the repo root with the venv active
(`export PATH="$PWD/.venv/bin:$PATH"`). All commands are read-only verification.

## Per-fix verification

| FR / IC | Verify | Existing test home |
|---------|--------|--------------------|
| FR-001 / IC-01 | `record-analysis` with only a `kitty-ops/<ulid>.jsonl` orphan succeeds; genuine dirt still blocks | `tests/mission_runtime/test_self_bookkeeping_allowlist.py` (extend) |
| FR-002 / IC-02 | a meta declaring an absent coord branch is not classified healthy `coord`; remediation leads with flatten; `classify_topology` unit tests unchanged | new regression near `surface_resolver` / `backfill_topology` tests |
| FR-003 / IC-03 | `doctor coordination` recommends only existing+working commands; #1890 dead-command guard | `tests/specify_cli/cli/commands/test_doctor_coordination.py` + `test_doctor_cli_surface_golden.py` (re-pin) |
| FR-004 / IC-04 | decision event for a flat mission persists a ULID `mission_id`, never a slug; fail-closed when none | `tests/specify_cli/events/test_decision_log.py` (invert stale test) |
| FR-005 / IC-05 | corrupt-meta read surfaces an error (no silent default-branch); field-absent still defaults | `tests/agent/test_orchestrator_merge_target.py` (extend) |
| FR-006 / IC-06 | composition with no resolvable mid8 fails closed / mints once — never empty-mid8 | new regression near `runtime_bridge` tests |

## Full gate (before PR)
```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider     # parallel suite
PWHEADLESS=1 pytest tests/architectural/ -p no:cacheprovider               # arch gates
ruff check . && mypy src/                                                   # zero issues
pytest tests/architectural/test_no_legacy_terminology.py                   # terminology guard (CI-only gate)
```

## Definition of done (mission)
- All 6 FRs satisfied with a red-first regression test demonstrated red pre-fix, green post-fix (SC-006).
- 0 silent slug-as-mission_id or silent default-branch substitutions (SC-004/SC-005, NFR-002).
- `classify_topology` remains pure (C-001); #2139 call sites unchanged (C-005).
- ruff + mypy clean; complexity ≤ 15 on touched functions (NFR-003).
- The 6 issues closed via the PR from `fix/reliability-papercut-sweep` → `main`.
