# CI Job Contract — `e2e-cross-cutting` mypy Availability

**Mission:** `charter-contract-cleanup-tranche-1-01KQATS4`
**Authority:** spec.md FR-008 + research.md R-006 (decision_id `01KQAVR8S1299R9N67BTFAD67Q`)

This document is the contract between `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` and the CI job that runs it.

---

## Job: `e2e-cross-cutting`

**File:** `.github/workflows/ci-quality.yml`

**Required environment (post-mission):**

- Python 3.12 (unchanged).
- Project installed via `pip install -e .[test,lint]` so the `lint` extra (which already pins `mypy>=1.10.0`) is available.
- `python -m mypy --strict src/specify_cli/mission_step_contracts/executor.py` exits 0 from the repository root.

**Pre-mission state (the bug being fixed):**

- Project installed via `pip install -e .[test]` only — `mypy` not on PATH.
- The test fails with `python -m mypy: not found` (or equivalent), and the failure surfaces as an `e2e-cross-cutting` job failure rather than a strict-typing regression.

**Acceptance:**

- `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` passes inside the `e2e-cross-cutting` job on a PR built from current `main` plus this mission's diff.
- No other job in the workflow regresses (NFR-002).

---

## Local-developer contract (informational)

To run the same test locally, developers should already use the documented path:

```bash
uv run --extra test --extra lint python -m pytest \
  tests/cross_cutting/test_mypy_strict_mission_step_contracts.py -q
```

This matches the test's docstring and is unaffected by this mission.
