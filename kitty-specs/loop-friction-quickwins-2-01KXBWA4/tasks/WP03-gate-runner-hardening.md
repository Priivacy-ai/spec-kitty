---
work_package_id: WP03
title: Pre-review gate runner — interpreter + contention + sub-agent contract
dependencies: []
requirement_refs:
- C-004
- FR-003
- FR-004
- FR-005
- NFR-003
- NFR-005
tracker_refs:
- '2570'
- '2493'
- '2555'
planning_base_branch: feat/loop-friction-quickwins-2
merge_target_branch: feat/loop-friction-quickwins-2
branch_strategy: Planning artifacts for this mission were generated on feat/loop-friction-quickwins-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/loop-friction-quickwins-2 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-loop-friction-quickwins-2-01KXBWA4
base_commit: 5244322b8f5db8809af619fe2e4f3d56cd64cc38
created_at: '2026-07-12T21:33:58.172545+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
phase: Gate runner hardening
agent: "claude"
shell_pid: '1482898'
shell_pid_created_at: '1783892026.99'
history:
- at: '2026-07-12T19:30:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-03; FR-003+FR-004 non-splittable)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent:
- src/specify_cli/review/_interpreter.py
- tests/review/test_pre_review_gate_interpreter.py
execution_mode: code_change
owned_files:
- src/specify_cli/review/pre_review_gate.py
- src/specify_cli/review/_interpreter.py
- tests/review/test_pre_review_gate_engine.py
- tests/review/test_pre_review_gate_interpreter.py
- src/doctrine/skills/spk-run-implement-review/SKILL.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 — Pre-review gate runner hardening

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objectives & Success Criteria

The pre-review gate must return a REAL verdict — never a spurious `no_coverage` that forces `--force` —
under a uv-managed interpreter and under concurrent-lane contention; and the sub-agent long-gate contract
must be documented.

- **SC (NFR-003)**: in a checkout where `sys.executable -m pytest` fails but `uv run pytest` is green, the gate returns pass/fail (not `no_coverage`). Forced `--force` attributable to interpreter selection = 0.
- **SC**: concurrent gate runs do not produce a false timeout-driven `no_coverage`.
- **SC**: `uv` absent → falls back to `sys.executable` without crashing.

## Context & Constraints

- **#2570.3 (interpreter)**: `run_scoped_tests_at_head` (`src/specify_cli/review/pre_review_gate.py:358`)
  hardcodes `command = [sys.executable, "-m", "pytest", ...]` (~379-386). `pytest` is a test-only
  optional-dependency extra, so the CLI interpreter legitimately lacks it → `No module named pytest` →
  `HeadRunResult(ran=False)` → `GateOutcome.NO_COVERAGE`. Distinct from #2534 (missing `_gate_coverage`
  module — a scope-derivation failure). There is NO existing `uv run` execution helper in `src/` (verified).
- **#2493.3 (contention)**: `_DEFAULT_HEAD_RUN_TIMEOUT = 300` (:109) → `subprocess.run(..., timeout=timeout)`
  (:388-398). Under N concurrent lanes a 30s shard can exceed 300s → `TimeoutExpired` → `no_coverage`.
- **#2555.4 (contract)**: the behavior of a dispatched sub-agent that hits a multi-minute gate is undefined.

**KEEP invariants:**
- **C-004**: the two existing real-subprocess tests (`test_pre_review_gate_engine.py:209/219`) run under a
  pytest-equipped interpreter and MASK #2570.3 — you MUST add a pytest-lacking regression and update those two.
- **K-9**: the contention lock's acquire MUST have its OWN timeout + fallback-to-run, DECOUPLED from the 300s
  subprocess timeout. Charging a lock-wait against the run timeout re-creates the exact bug FR-004 removes.
- The gate still ENFORCES by default; skip only via the already-shipped `--skip-pre-review-gate` / disable env (#2573).

Plan: IC-03. Research: R-03/R-04/R-05. Contract: C-B1/C-B2.

## Branch Strategy

- **Planning base branch / Merge target**: feat/loop-friction-quickwins-2

## Subtasks & Detailed Guidance

### Subtask T008 — Interpreter-resolution helper

- **Purpose**: Run pytest via the project interpreter that actually has it.
- **Steps**: Add the canonical `uv run` executor in a NEW `src/specify_cli/review/_interpreter.py` (SSOT
  D3 — there is NO existing shared uv-run executor in `src/`; `compat/` only has `uv tool install`
  provenance, a different concern, so do NOT try to "align" with it). Resolve: if `uv` is on PATH
  (`shutil.which("uv")`) AND `<repo_root>/pyproject.toml` exists → `["uv","run","--project",str(repo_root),"python","-m","pytest",...]`;
  else `[sys.executable,"-m","pytest",...]`. Make it importable so a later consumer can reuse it.
- **Files**: `src/specify_cli/review/_interpreter.py` (new), consumed by `pre_review_gate.py`.

### Subtask T009 — Apply helper + contention lock

- **Purpose**: Use the resolved interpreter; serialize scoped runs safely.
- **Steps**: Replace the hardcoded command at ~379-386 with the helper output. Add an advisory lock around
  the scoped subprocess run (scoped `fcntl.flock` or an async bridge to `MachineFileLock` — note the
  canonical `MachineFileLock` at `core/file_lock.py:311` is ASYNC-only while this path is sync; pick and
  justify the mechanism). Give lock-acquire its own bounded timeout + fallback-to-run-without-lock; do NOT
  charge the wait against the 300s subprocess timeout.
- **Files**: `src/specify_cli/review/pre_review_gate.py`.

### Subtask T010 — Red-first: pytest-lacking interpreter (unmask #2570.3)

- **Purpose**: Prove the interpreter fix; remove the masking.
- **Steps**: New `tests/review/test_pre_review_gate_interpreter.py`: monkeypatch so `sys.executable -m pytest`
  fails (`No module named pytest`) and a fake `uv` is on PATH returning a green junit → the gate returns a
  real verdict, not `no_coverage`. Cover ALL THREE branches: (i) uv-present+pyproject → `uv run`; **(ii)
  uv-present but NO `pyproject.toml` at root → `sys.executable` fallback (G2 — the AND's second leg, a named
  spec edge case)**; (iii) uv-absent → `sys.executable`. Update the two real-subprocess tests in
  `test_pre_review_gate_engine.py:208/218` (def-body lines) that currently mask this.
- **Files**: the new test + `tests/review/test_pre_review_gate_engine.py`.

### Subtask T011 — Red-first: contention

- **Steps**: A test that two overlapping scoped runs serialize (no interleaved corruption) and that a lock
  WAIT does not trip the run timeout (patch the lock to sleep beyond a short lock-acquire timeout → falls
  back to run; the 300s subprocess timeout is untouched).
- **Files**: `tests/review/test_pre_review_gate_engine.py` (or the new file).

### Subtask T012 — Document the sub-agent long-gate contract

- **Purpose**: Define expected behavior (FR-005).
- **Steps**: In `src/doctrine/skills/spk-run-implement-review/SKILL.md`, add a short section: a dispatched
  implement/review sub-agent POLLS the synchronous gate to completion; to skip, it uses
  `--skip-pre-review-gate` or the honored disable env; the orchestrator must not assume a silent hand-back.
  Use canonical terminology (`Mission`, not `feature`) — this file is under a terminology-scanned root.
  **FR-005 is intentionally doc-only (per contract C-B2 — no product-code test).** Note in the PR that the
  edited skill propagates to agent copies via `spec-kitty upgrade` (do not hand-edit agent-dir copies).
- **Files**: `src/doctrine/skills/spk-run-implement-review/SKILL.md`.

## Definition of Done

- Interpreter resolved via `uv run` with `sys.executable` fallback; contention lock with decoupled timeout.
- Pytest-lacking regression added; the two masking tests updated; contention test passes.
- Sub-agent contract documented; terminology guard green (`pytest tests/architectural/test_no_legacy_terminology.py`).
- `PWHEADLESS=1 uv run pytest tests/review/ -q` green; `ruff` + `mypy` clean.

## Risks & Reviewer Guidance

- **Risk**: a naive lock reintroduces false timeouts — reviewer verifies T011's decoupled-timeout assertion.
- **Risk**: the masking tests silently keep passing — reviewer confirms T010 fails on unpatched (bug-present) code.

## Activity Log

- 2026-07-12T21:57:33Z – claude – shell_pid=1482898 – reviewer-renata APPROVE: C-004 behavioral red-first genuine; lock/timeout decoupled (captured [300], elapsed<2s); fcntl choice sound
- 2026-07-12T21:57:47Z – claude – shell_pid=1482898 – reviewer-renata APPROVE
