---
work_package_id: WP04
title: Doctor Stale Sweep
dependencies:
- WP03
requirement_refs:
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
agent: "claude:fable:reviewer-renata:reviewer"
shell_pid: "50641"
history:
- '2026-06-10T20:15:38Z: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/doctor/
execution_mode: code_change
owned_files:
- src/specify_cli/doctor/ops.py
- src/specify_cli/cli/commands/doctor.py
- tests/specify_cli/invocation/test_doctor_ops.py
- tests/specify_cli/invocation/cli/test_doctor_ops_cli.py
role: implementer
tags: []
---

# WP04 — Doctor Stale Sweep

## ⚡ Do This First: Load Agent Profile

Before reading further, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries for the remainder of this work package.

## Objective

Give `spec-kitty doctor ops` an active remediation mode: `--close-stale [--threshold <hours>]` closes open Ops older than the threshold (default 24; `0` = all) with `outcome="abandoned"`, `closed_by="doctor_sweep"`, routed through the canonical executor close path so idempotency and close-time auto-commit apply uniformly. Report-only behavior without the flag is unchanged. Contract: `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/doctor-ops-close-stale.md` is normative (JSON shape, exit codes).

## Context

- Spec: FR-006, FR-007; NFR-002 (<5 s at 10,000 Op files). Research R4 (threshold rationale; sweep must reuse `complete_invocation`, never append directly).
- Existing: `list_orphan_ops()` in `src/specify_cli/doctor/ops.py` scans `kitty-ops/*.jsonl` for files with a started but no completed event; `spec-kitty doctor ops [--json]` reports them, exit 1 when any exist (`tests/specify_cli/invocation/test_doctor_ops.py` pins this).
- WP03 delivered `complete_invocation(..., closed_by="doctor_sweep")` — the only sanctioned close path for the sweep.

## Subtasks

### T015 — `close_stale_ops()` in the doctor ops module

**Purpose**: sweep engine.

**Steps**:
1. In `src/specify_cli/doctor/ops.py`, add:
   ```python
   def close_stale_ops(repo_root: Path, *, threshold_hours: float, now: datetime) -> SweepReport: ...
   ```
   - Enumerate via `list_orphan_ops()` (reuse, don't reimplement the scan).
   - For each orphan, parse the started event's `started_at`; age = `now - started_at`. Unparseable `started_at` → treat as stale (it's exactly the broken-record case the sweep exists for) and record `parse_warning` in the report.
   - Age > threshold (or threshold == 0): close via a `ProfileInvocationExecutor` with `outcome="abandoned"`, `closed_by="doctor_sweep"`, no evidence. Age ≤ threshold: record as `skipped_fresh`.
   - `now` is an injected parameter (testability); CLI passes `datetime.now(timezone.utc)`.
2. `SweepReport` dataclass mirrors the contract JSON: per-op `{invocation_id, profile_id, started_at, age_hours, action_taken: "none"|"closed_abandoned"|"already_closed"}` plus `swept`, `skipped_fresh`, `threshold_hours`.

**Validation**: unit tests with fabricated op dirs cover stale/fresh/threshold-0/unparseable-timestamp paths.

### T016 — CLI flags

**Purpose**: operator surface.

**Steps**:
1. In the `doctor ops` command (`src/specify_cli/cli/commands/doctor.py` — locate the existing `ops` subcommand), add `--close-stale` (flag) and `--threshold` (float hours, default 24.0, requires `--close-stale`; passing `--threshold` without `--close-stale` is a usage error).
2. Output: rich table or JSON per the contract. Exit codes per the contract: 0 when the sweep completes (even if some `already_closed`); 1 on IO/write errors; 1 when open-but-fresh Ops remain after the sweep (consistent with report mode's "orphans exist" signal).
3. Report-only mode (no flag) byte-compatible with today's behavior — existing tests must keep passing unmodified except for additive JSON fields.

**Validation**: CLI integration tests for flag combinations, exit codes, JSON shape.

### T017 — Race with concurrent manual close

**Purpose**: sweep never crashes on a race; misattribution impossible.

**Steps**:
1. Catch `AlreadyClosedError` per op inside the sweep loop → `action_taken="already_closed"`, continue; not a failure.
2. The exclusive append guard in the writer is the race arbiter — the sweep adds no locking of its own.
3. Any other per-op exception: record as an error entry, continue the sweep, exit 1 at the end (one bad file must not block remediation of the rest).

**Validation**: test simulates a close between enumeration and sweep (close the op manually after listing, then run sweep) → `already_closed`, exit 0.

### T018 — Tests + performance guard

**Purpose**: pin behavior and the NFR.

**Steps**:
1. Extend `tests/specify_cli/invocation/test_doctor_ops.py`: sweep closes only stale; `closed_by="doctor_sweep"` and `outcome="abandoned"` in the written event; auto-commit fired per close (spy on safe_commit path or check git log in a fixture repo); threshold 0 sweeps everything; fresh-only dir → nothing swept, exit 1.
2. New `tests/specify_cli/invocation/cli/test_doctor_ops_cli.py` for the CLI layer (flags, JSON, exit codes).
3. Performance guard: generate 1,000 synthetic op files in tmp_path, assert sweep enumeration+decision (mock the actual close) completes in well under the budget pro-rated (<0.5 s for 1k). Additionally add the full NFR-002 case — 10,000 files, <5 s — behind an opt-in marker (`@pytest.mark.slow` or the repo's existing convention) so the budget is exercised on demand without slowing the default suite. The default-suite guard is an extrapolation; the slow marker is the authoritative NFR-002 check.

**Validation**: `.venv/bin/pytest tests/specify_cli/invocation -q` green; mypy --strict + ruff clean.

## Branch Strategy

Planning base branch: `main`. Final merge target: `main`. Execution worktrees are allocated per computed lane from `lanes.json`. Implement via `spec-kitty agent action implement WP04 --agent <name>` (depends on WP03).

## Definition of Done

- [ ] `--close-stale --threshold` semantics exactly per contract; default 24 h; 0 = all.
- [ ] Sweep closes via the executor (`closed_by="doctor_sweep"`, `outcome="abandoned"`), auto-commit included.
- [ ] Race → `already_closed`, sweep continues; per-op errors don't abort the sweep.
- [ ] Report-only mode unchanged; exit codes per contract; ≥90% coverage; mypy --strict + ruff clean.

## Risks & Reviewer Guidance

- **No second close implementation**: reviewer must verify the sweep calls `complete_invocation` — direct JSONL appends here would fork lifecycle logic (research R4 explicitly rejects this).
- **doctor.py is a god-module** (#1623): add the minimum to the existing `ops` subcommand; resist refactoring the module in this WP.
- **Clock handling**: `started_at` is ISO-8601 with offset; compare timezone-aware datetimes only — a naive/aware mix is the classic bug here.

## Activity Log

- 2026-06-10T21:31:59Z – claude:fable:python-pedro:implementer – shell_pid=47836 – Assigned agent via action command
- 2026-06-10T21:42:15Z – claude:fable:python-pedro:implementer – shell_pid=47836 – Ready for review: close-stale sweep per contract, race-safe, perf guarded
- 2026-06-10T21:42:48Z – claude:fable:reviewer-renata:reviewer – shell_pid=50641 – Started review via action command
- 2026-06-10T21:45:55Z – user – shell_pid=50641 – Review passed: close_stale_ops routes every close through ProfileInvocationExecutor.complete_invocation(outcome=abandoned, closed_by=doctor_sweep) — no second close path; contract-conformant JSON/exit codes (default 24h, --threshold 0 sweeps all, --threshold without --close-stale is usage error); AlreadyClosedError -> already_closed exit 0; per-op errors continue + exit 1; tz-aware math with naive-UTC coercion and unparseable->stale+parse_warning; auto-commit spy pins per-close commit; 373 invocation tests green; slow 10k NFR-002 test passes in 2.8s; mypy/ruff clean; commit touches only owned files; doctor.py addition minimal
