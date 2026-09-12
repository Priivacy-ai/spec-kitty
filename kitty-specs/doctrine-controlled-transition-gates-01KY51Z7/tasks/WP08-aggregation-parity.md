---
work_package_id: WP08
title: Verdict aggregation + parity oracle
dependencies: []
requirement_refs:
- FR-014
- NFR-001
- NFR-002
planning_base_branch: feat/doctrine-controlled-transition-gates
merge_target_branch: feat/doctrine-controlled-transition-gates
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-controlled-transition-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-controlled-transition-gates unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-controlled-transition-gates-01KY51Z7
base_commit: 6e039cdc2c2aed3cfae313225ee4562a13c8f7ba
created_at: '2026-07-22T16:15:03.995515+00:00'
subtasks:
- T035
- T036
- T037
- T038
- T039
phase: Phase 4 - Integration
history:
- at: '{{TIMESTAMP}}'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/verdict_aggregation.py
create_intent:
- src/specify_cli/review/verdict_aggregation.py
- tests/review/test_verdict_aggregation.py
- tests/review/test_transition_gate_parity.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/verdict_aggregation.py
- tests/review/test_verdict_aggregation.py
- tests/review/test_transition_gate_parity.py
- tests/review/fixtures/parity/**
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 – Verdict aggregation + parity oracle

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `` (unset — select below)
- **Role**: ``
- **Agent/tool**: ``

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` (`implement`) and `authoritative_surface` (`src/specify_cli/review/verdict_aggregation.py`). This is a pure-function + test-fixture WP; a Python-implementer profile fits.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in code blocks (` ```python `, ` ```bash `).

---

## Objectives & Success Criteria

Deliver the two independently-testable safety surfaces the inverted hook (WP09) will consume:

1. **`aggregate_verdicts()`** — a **pure function** encoding the deterministic aggregation precedence (terminal interruption > opt-in block > warn/pass), with per-handler fail-open semantics baked into its contract (FR-014, NFR-002, C-003).
2. **The parity oracle** — a golden fixture set **captured from base commit `e4ef6e850` against the incumbent `_mt_run_pre_review_gate`** (never regenerated from new code), plus a harness that WP09 uses to prove behaviour preservation through the hook (NFR-001).

**Done when:**

- `src/specify_cli/review/verdict_aggregation.py` exposes `aggregate_verdicts(verdicts, *, block_enabled, force) -> AggregateVerdict` as a standalone pure function (no I/O), complexity ≤15.
- `tests/review/test_verdict_aggregation.py` covers the **full outcome × precedence matrix** including the synthetic multi-handler seam.
- Committed parity fixtures under `tests/review/fixtures/parity/**` carry expected `(outcome, scope, metadata, block/exit, console)` tuples captured from base `e4ef6e850` for **all six** `GateOutcome` members and **both** hard-stops.
- `tests/review/test_transition_gate_parity.py` is a harness that replays the fixtures (WP09 wires it through the inverted hook; here it is authored red against the captured tuples).
- A fail-open fault-injection unit proves each faulting handler yields exactly one visible unverified warning with no cross-suppression.

**Tracker**: NFR-001, NFR-002, FR-014.

## Context & Constraints

- **Mission**: `doctrine-controlled-transition-gates-01KY51Z7` · **Branch**: `feat/doctrine-controlled-transition-gates`.
- **Spec**: [spec.md](../spec.md) FR-014 (`:116`), NFR-001 (`:123`), NFR-002 (`:124`), User Story 2 (`:39-52`), User Story 4 (`:72-85`). **Plan**: [plan.md](../plan.md) IC-05 (`:134-147`), squad findings R-F2 (circular oracle) and R-F3 (synthetic seam). **Data-model**: [data-model.md](../data-model.md) §7 (aggregation, `:272-306`), §2 (`GateOutcome`), §8 (`TransitionGateContext`). **Contract**: [contracts/transition-gate-hook.md](../contracts/transition-gate-hook.md).
- **`GateOutcome`** is the existing six-member enum — do NOT redefine it. `src/specify_cli/review/pre_review_gate.py:742-750`: `NO_COVERAGE`, `NO_NEW_FAILURES`, `NEW_FAILURES`, `UNVERIFIED_BASELINE`, `TIMED_OUT`, `CANCELLED`. `GateVerdict` at `pre_review_gate.py:753-762`.
- **Incumbent precedence to preserve** (from `_mt_run_pre_review_gate`, `tasks_move_task.py:1160-1299`):
  - terminal interruption is checked FIRST (`:1270-1296`, `TIMED_OUT`/`CANCELLED` → `transition_applied=False` then `Exit(1)`), BEFORE the block (`:1298`);
  - block iff `block_enabled AND outcome is NEW_FAILURES AND not force` (`:1258-1261`);
  - the three-catch fail-open shape: `KeyboardInterrupt → CANCELLED` (`:1241-1247`), any other `Exception → NO_COVERAGE` unverified warn (`:1248-1249`), and the `GateAuthoritiesUnavailable → NO_COVERAGE` degrade (`:1056`).
- **Base commit for the oracle**: `e4ef6e850`. Expected values are captured from that commit against the OLD function — **never** regenerated from the refactored code (the circular-oracle trap, squad R-F2).
- **FR-014 synthetic seam (say it plainly)**: half A ships **exactly one** production binding (the Spec-Kitty pre-review handler). The N-handler aggregation branches therefore have **no production caller** — they are a forward-compatibility seam exercised **only** by synthetic/fabricated verdicts in `test_verdict_aggregation.py` (squad R-F3, `data-model.md:280-285`). State this in the module docstring so it is not mistaken for dead code.
- **This WP does NOT invert the hook** — it delivers the pure fn + fixtures WP09 consumes. WP09 owns `tasks_move_task.py`; this WP must not edit it. **Deps**: none — **no code dependency** (it consumes the base-stable `GateVerdict` / `GateOutcome` shapes and captures the incumbent in a detached base worktree at `e4ef6e850`). The frontmatter `dependencies: []` is correct.
- **Quality**: `mypy --strict` + `ruff` zero issues, complexity ≤15/function, ≥90% new-code coverage. `PYTHONPATH=$(pwd)/src`. No `# noqa` / `# type: ignore`.

## Branch Strategy

- **Strategy**: feature-branch (PR-bound, C-004).
- **Planning base branch**: `feat/doctrine-controlled-transition-gates`.
- **Merge target branch**: `feat/doctrine-controlled-transition-gates`.

> Populated by `spec-kitty agent mission tasks`. Do NOT change manually unless the branch topology changed.

## Subtasks & Detailed Guidance

### Subtask T035 – `aggregate_verdicts()` pure function

- **Purpose**: Encode FR-014's deterministic aggregation as a standalone pure function so the hook stays a thin orchestrator (≤15 complexity) and the multi-handler precedence is unit-testable without any real handler (`data-model.md:272-306`).
- **Signature** (design intent — finalize types against `pre_review_gate.GateVerdict`):
  ```python
  def aggregate_verdicts(
      verdicts: Sequence[GateVerdict],
      *,
      block_enabled: bool,
      force: bool,
  ) -> AggregateVerdict: ...
  ```
- **Precedence (highest first), preserving the incumbent order**:
  1. **Terminal interruption** — if ANY `v.outcome in {TIMED_OUT, CANCELLED}`: return an aggregate that sets `transition_applied=False` and signals a hard-stop (`Exit(1)` at the call site). Checked BEFORE the block (mirrors `tasks_move_task.py:1270` before `:1298`).
  2. **Block** — else block iff `block_enabled AND any(v.outcome == NEW_FAILURES for v in verdicts) AND not force`.
  3. **Warn/pass** — else the transition completes; each verdict contributes at most one console warning line.
- **Invariants** (encode + test):
  - **≤1 warning per handler** — one visible line per verdict, even a faulting one.
  - **No cross-suppression** — a `NO_COVERAGE`-degraded (faulting) verdict never removes another verdict's `NEW_FAILURES` from the block computation (US4 AS3). Aggregation reads EVERY verdict.
  - **Pure** — no I/O, no `typer.Exit`; return a value describing the decision (terminal / block / warn-pass + ordered per-handler warnings). The hook (WP09) performs the actual `Exit`/console emission.
- **Steps**: define a small frozen `AggregateVerdict` result type (decision enum + per-handler warning tuple + `transition_applied` flag); implement the three-tier precedence as flat branches (extract a `_is_terminal` / `_should_block` helper each if complexity approaches 15). Do NOT inline this logic into any hook.
- **Files**: `src/specify_cli/review/verdict_aggregation.py` (create).
- **Parallel?**: No — T036 tests it directly.
- **Notes**: The dispatch ORDER is fixed by WP09/WP06's stable sort; `aggregate_verdicts` consumes an already-ordered sequence and preserves it (it must not re-sort).

### Subtask T036 – `test_verdict_aggregation.py` full outcome × precedence matrix

- **Purpose**: Exercise the pure fn across the complete matrix — the ONLY exercise the multi-handler branches get in half A (synthetic seam).
- **Steps**:
  1. Single-handler arm: each of the six `GateOutcome` members × `{block_enabled, not}` × `{force, not}` → assert the decision (terminal / block / warn-pass) and `transition_applied`.
  2. **Synthetic multi-handler arm** (fabricate 2–3 `GateVerdict`s — no real handler): assert terminal-beats-block (a `TIMED_OUT` verdict co-firing with a `NEW_FAILURES` verdict → terminal wins); block-with-a-faulting-sibling (`NEW_FAILURES` + a `NO_COVERAGE`-degraded verdict, `block_enabled`, `not force` → still blocks — no cross-suppression, US4 AS3); two warn-shaped verdicts → each one warning, never blocked.
  3. Assert **≤1 warning per verdict** in every arm.
  4. Add an explicit comment in the test module that these multi-handler cases are the synthetic exercise of a one-production-binding seam (FR-014, squad R-F3).
- **Files**: `tests/review/test_verdict_aggregation.py` (create).
- **Parallel?**: No — depends on T035's surface.
- **Notes**: Fabricate `GateVerdict`s directly; do NOT import or run a real handler here.

### Subtask T037 – Capture the parity golden from base `e4ef6e850` (red-first)

- **Purpose**: Pin the parity oracle to the incumbent behaviour BEFORE the refactor, so WP09's parity test cannot become a circular oracle that snapshots the new code (squad R-F2, NFR-001, `contracts/transition-gate-hook.md:76-80`).
- **Steps**:
  1. Author a small, committed **capture script** (e.g. under `tests/review/fixtures/parity/_capture.py`, the *output* fixtures committed) that runs against base commit `e4ef6e850` via a **detached `git worktree` checked out at `e4ef6e850`** — this detached-base-worktree capture is **THE method (mandatory)**, not an "if hard to capture" fallback. The script drives the incumbent `_mt_run_pre_review_gate` for scenarios covering **all six** `GateOutcome` members AND **both** hard-stops (opt-in `NEW_FAILURES` block; terminal `TIMED_OUT`/`CANCELLED`).
  2. **Provenance safety (mandatory)**: the capture script MUST `assert git rev-parse HEAD == e4ef6e850` and **fail loudly** otherwise, and MUST **machine-emit the actual SHA it ran against** into each fixture header (read it from the running worktree — **reject any hand-typed SHA literal**).
  3. **Force the two terminal outcomes at base**: monkeypatch the wait/timeout path → `TIMED_OUT`, and inject a `KeyboardInterrupt` → `CANCELLED`, so both hard-stops are captured from the incumbent function at base.
  4. For each scenario record the full expected tuple: `(outcome, scope, transition metadata payload, block/exit behaviour, console surface)` — the metadata payload is `_mt_pre_review_gate_metadata` (`tasks_move_task.py:1071-1096`); the console surface is `_mt_pre_review_gate_console_warning`.
  5. Commit the captured expected values as static fixtures under `tests/review/fixtures/parity/**`. The machine-emitted base SHA (`e4ef6e850`) in each fixture header records that values are captured-from-base, **never** regenerated from HEAD.
  6. Author the fixtures RED-first: at this point the refactored hook does not yet exist, so the harness (T038) is expected to fail until WP09 lands — that is the correct red state, not a regression.
- **Files**: `tests/review/fixtures/parity/**` (committed fixtures + capture script).
- **Parallel?**: No — T038 replays these.
- **Notes**: **GUARD (circular-oracle trap)**: never regenerate expected values from the new implementation. The detached `e4ef6e850` worktree + machine-emitted SHA header is the enforced method — do not hand-write values guessed from the new code, and do not hand-type the provenance SHA.

### Subtask T038 – `test_transition_gate_parity.py` harness vs base fixtures

- **Purpose**: The replay harness comparing the (post-refactor) result to the base-captured tuples across all six outcomes + both hard-stops (NFR-001; WP09 wires it through `_mt_run_transition_gates`).
- **Steps**:
  1. Load each committed fixture from `tests/review/fixtures/parity/**`.
  2. For each scenario, assert the produced `(outcome, scope, metadata, block/exit, console)` equals the fixture's captured tuple — a strict, field-by-field comparison of the metadata payload and console line, not a loose "outcome matches".
  3. Structure the harness so WP09 supplies the drive-through-the-hook adapter; here, assert against the captured tuples so the test is meaningfully RED until the refactored hook reproduces them.
  4. Include a comment pointing to `e4ef6e850` as the oracle provenance and to WP09 as the surface under test.
- **Files**: `tests/review/test_transition_gate_parity.py` (create).
- **Parallel?**: No.
- **Notes**: This is the "parity through the hook, not just the engine" guard (NFR-001) — the metadata + block/exit + console fields are load-bearing; do not compare outcome alone.

### Subtask T039 – Fail-open fault-injection unit

- **Purpose**: Prove NFR-002 at the aggregation seam — each faulting handler surfaces exactly one visible unverified warning and never suppresses a co-firing handler's verdict.
- **Steps**:
  1. Simulate the per-handler fail-open contract: a handler that raises maps to a `NO_COVERAGE` "unverified" verdict (mirrors `tasks_move_task.py:1248-1249`); a `KeyboardInterrupt` maps to `CANCELLED` (`:1241-1247`).
  2. Fault-inject one verdict-as-degraded alongside a normal verdict; assert (a) the transition still completes / aggregates, (b) the faulting verdict yields exactly ONE warning, (c) the co-firing verdict's outcome is unaffected (no cross-suppression).
  3. Assert the `NEW_FAILURES`-plus-fault case still blocks (US4 AS3) — the fault does not remove the block.
- **Files**: `tests/review/test_verdict_aggregation.py` (extends T036's module) or a sibling; keep in `owned_files`.
- **Parallel?**: No.
- **Notes**: Fail-open is a per-handler property; here it is exercised at the aggregation boundary. WP09 owns the try/except dispatch wrapping (the three-catch mirror); this WP proves the aggregation half never blocks or crashes on a degraded verdict.

## Test Strategy (tests required)

- **Unit**: `tests/review/test_verdict_aggregation.py` — full outcome × precedence matrix + fault-injection (synthetic verdicts only).
- **Golden/parity**: `tests/review/test_transition_gate_parity.py` replaying `tests/review/fixtures/parity/**` captured from base `e4ef6e850`.
- **Commands**:
  ```bash
  PYTHONPATH=$(pwd)/src pytest tests/review/test_verdict_aggregation.py -q
  PYTHONPATH=$(pwd)/src pytest tests/review/test_transition_gate_parity.py -q
  mypy --strict src/specify_cli/review/verdict_aggregation.py
  ruff check src/specify_cli/review/verdict_aggregation.py tests/review/
  ```
- **Red-first**: author T036 before/with T035 and show it red; capture the parity fixtures (T037) then show T038 red against them (green only once WP09 lands the inverted hook). Record both red states in the Activity Log so migration-red is distinguishable from regression-red.

## Risks & Mitigations

- **Circular oracle (blocker)** — regenerating expected values from the new code makes parity decorative. *Mitigation (GUARD)*: capture from base `e4ef6e850` against the OLD `_mt_run_pre_review_gate`; commit values with a base-commit provenance header; never regenerate from HEAD.
- **Coverage-by-integration illusion** — relying on the single production binding to exercise aggregation leaves the N-handler branches untested. *Mitigation*: `aggregate_verdicts` is a pure fn with a synthetic full-matrix unit test (FR-014 synthetic seam).
- **Precedence inversion** — checking block before terminal would flip the incumbent order. *Mitigation*: terminal is tier 1, verified by the multi-handler terminal-beats-block case (`tasks_move_task.py:1270` before `:1298`).
- **Cross-suppression** — a faulting handler dropping another's `NEW_FAILURES`. *Mitigation*: aggregation reads every verdict; T039 asserts block survives a co-firing fault.
- **Complexity creep** — the matrix tempts nested conditionals. *Mitigation*: extract `_is_terminal` / `_should_block` helpers; keep each ≤15.

## Review Guidance

- Verify the parity fixtures carry a base-commit (`e4ef6e850`) provenance header and were NOT regenerated from the refactored code.
- **Reject if the fixture provenance SHA is not machine-emitted by the capture run** — a hand-typed SHA literal is a review failure; the capture script must `assert rev-parse HEAD == e4ef6e850` and write the SHA it actually ran against into each fixture header.
- Verify the aggregation matrix covers all six outcomes × block/force × single/multi-handler, and that the multi-handler arm uses synthetic verdicts.
- Verify `aggregate_verdicts` is pure (no `Exit`, no I/O) and ≤15 complexity; the hook (WP09) owns the exit/console emission.
- Verify T038 compares metadata + block/exit + console (not outcome alone) and is meaningfully red until the WP09 hook exists.
- Verify no edit to `tasks_move_task.py` (that is WP09's owned file).

## Activity Log

> **CRITICAL**: entries in chronological order (oldest first, newest last). Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>` (UTC, `date -u "+%Y-%m-%dT%H:%M:%SZ"`).

- {{TIMESTAMP}} – system – Prompt created.
