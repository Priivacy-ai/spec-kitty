# Quickstart — Verifying Stability & Hygiene Hardening

**Mission**: `stability-and-hygiene-hardening-2026-04-01KQ4ARB`
**Date**: 2026-04-26
**Audience**: An operator who wants to spot-check the mission's claims after
implementation lands.

All commands assume CWD is the repo root of `spec-kitty` inside the workspace
at `/Users/robert/spec-kitty-dev/spec-kitty-20260426-091819-hxH6lN/spec-kitty`.
Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` for any SaaS / sync flow.

## Scenario 1 — Multi-WP mission with planning lane lands cleanly

```bash
# Run the e2e harness for the planning-lane scenario
python -m pytest spec-kitty-end-to-end-testing/scenarios/dependent_wp_planning_lane.py -v
```

Expected: 0 failures. The test creates a mission with 3 sequential
implementation WPs and 1 planning lane, drives it through merge, and asserts
every approved commit lands on `main`.

## Scenario 2 — Interrupted merge resumes cleanly

```bash
# Drive a long mission, interrupt mid-merge, resume
python -m pytest tests/integration/test_merge_resume.py -v
```

Expected: resume completes within 30s on a 10-lane fixture mission (NFR-005).

## Scenario 3 — Oversized intake plan is rejected

```bash
# Generate a 50 MB plan file, point intake at it
dd if=/dev/urandom of=/tmp/big-plan.md bs=1M count=50 2>/dev/null
spec-kitty intake /tmp/big-plan.md
# Expect non-zero exit, INTAKE_TOO_LARGE error
```

Memory ceiling: peak RSS ≤ 1.5× the configured cap (default 5 MB).

## Scenario 4 — Reviewer claim emits the correct transition

```bash
# Drive a fixture mission to for_review, then claim
python -m pytest tests/unit/status/test_review_claim_transition.py -v
```

Expected: the emitted event's `to_lane` is `in_review` (not `in_progress`).

## Scenario 5 — Candidate release blocked without downstream verification

```bash
# Run the release-gate scenario
python -m pytest tests/integration/test_release_gate_downstream_consumer.py -v
```

Expected: a candidate release that has not been verified against a real
downstream consumer is rejected by the gate.

## Scenario 6 — Offline queue overflow surfaces a recoverable path

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 python -m pytest tests/integration/test_offline_queue_overflow.py -v
```

Expected: 0 events dropped; structured `OfflineQueueFull` raised; drain file
created with all overflow events; replay is idempotent.

## Scenario 7 — Spec ceremony fails loudly in uninitialized repo

```bash
python -m pytest tests/integration/test_fail_loud_uninitialized_repo.py -v
```

Expected: `spec-kitty specify`, `plan`, and `tasks` each exit non-zero with
`SPEC_KITTY_REPO_NOT_INITIALIZED` and write zero files outside the temp
fixture root.

## Scenario 8 — Cross-repo e2e gate runs

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
  python -m pytest spec-kitty-end-to-end-testing/scenarios/ -v --tb=short
```

Expected: full suite ≤ 20 min wall-clock (NFR-006); 0 failures.

## Smoke checklist

```bash
# Contract gate (mission-review hard gate, FR-023)
pytest tests/contract/ -v

# Architectural invariants (no runtime PyPI dep, no direct httpx in subsystems)
pytest tests/architectural/ -v

# CLI cold-start (NFR-009)
time spec-kitty --version
```

Cold start should be under 1.5 s on a developer laptop.

## What "done" looks like for the mission

- `kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/issue-matrix.md`
  exists; every issue from `start-here.md` has a verdict.
- `pytest tests/contract/` is green.
- `pytest tests/architectural/` is green.
- `spec-kitty-end-to-end-testing` suite runs and passes (or has an explicit
  operator-approved exception).
- Mission-review skill verifies the matrix and the contract gate before
  approval.
