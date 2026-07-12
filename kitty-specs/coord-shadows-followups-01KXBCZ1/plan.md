# Implementation Plan: Coord-Shadows Follow-ups Closeout

**Branch**: `coord-shadows-followups-01KXBCZ1` | **Date**: 2026-07-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/coord-shadows-followups-01KXBCZ1/spec.md`

## Summary

Close five re-verified tech-debt residuals of the merged coord-shadows-arm-closeout mission (PR #2572, epic #2160), all under one theme: **one canonical authority per operation, made correct**. Consolidate the triplicated subtask-gate-dir resolver onto a single seam with the strong git-ancestry fallback (#2574); harden `is_process_alive` against PID reuse with a persisted identity baseline (#2575); guard the out-of-lock rollback-uncheck write (#2576); reconcile the stray fifth checkbox parser onto the canonical `core/subtask_rows` (#2567); and fold the review-lock liveness probe onto the canonical `core/process_liveness` (#2568). Approach validated by a 4-lens pre-spec brownfield squad + a 2-lens post-spec squad.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, psutil, ruamel.yaml, pytest, mypy, ruff (all in-tree; no new dependencies)
**Storage**: Filesystem — `tasks.md` (TASKS_INDEX planning artifact), WP frontmatter (`shell_pid` + a new additive identity-baseline field), `status.events.jsonl`
**Testing**: `pytest` (unit + integration); characterization tests for behavior-preserving folds; a real spawn→kill liveness test; red-first coord-husk resolver test. Parallel run `pytest tests/ -n auto --dist loadfile`; arch suite `tests/architectural/` (incl. dead-code + terminology gates)
**Target Platform**: Linux/macOS developer + CI (process-liveness fix is platform-general)
**Project Type**: single (Python CLI package `src/specify_cli/` + `src/runtime/` + `src/doctrine/`)
**Performance Goals**: N/A — correctness/robustness consolidation; no perf-sensitive paths touched
**Constraints**: 0 new `ruff`/`mypy` findings; dead-code gate clean (no orphans); no psutil-consumer sweep beyond the three named surfaces; F3 owned_files tight (avoid #2573 collision in the same module)
**Scale/Scope**: 5 issues (#2574/#2575/#2576/#2567/#2568), ~5 WPs, single package

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** (governing principle): this mission's raison d'être — each of the three duplication classes collapses to one seam. PASS by construction.
- **DDD + tiered rigour**: `core/` (liveness, subtask_rows) is core-tier — strict typing, focused tests per branch. PASS.
- **ATDD-first / red-first**: FR-002 (coord-husk resolver fix) and FR-004 (PID-reuse) require red-first tests before the fix. PASS (encoded in IC risks).
- **Canonical sources**: reuse `resolve_planning_read_dir(kind=TASKS_INDEX)`, `core/subtask_rows`, `core/process_liveness`, `write_text_within_directory` — no improvised parsers/resolvers/probes (C-003). PASS.
- **Terminology adherence**: no domain-term changes; terminology guard must stay green. PASS.
- **No suppression to pass gates**: load-bearing casts retained (C-002); no new `# noqa`/`# type: ignore`. PASS.

No charter violations → Complexity Tracking omitted.

## Project Structure

### Documentation (this mission)

```
kitty-specs/coord-shadows-followups-01KXBCZ1/
├── spec.md              # committed (56460c7)
├── plan.md              # this file
├── checklists/requirements.md
├── traces/              # #2095 tracer files (tooling-friction / approach / design)
└── tasks.md             # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/
├── missions/
│   └── _read_path_resolver.py        # IC-01: NEW resolve_subtasks_gate_dir seam (home)
├── status/
│   ├── emit.py                       # IC-01: delete _resolve_primary_subtasks_dir, repoint 2 callers
│   └── aggregate.py                  # IC-01: inline dup → call the seam
├── coordination/
│   └── status_transition.py          # IC-01: weak inline dup → call the seam (gains strong fallback)
├── core/
│   ├── process_liveness.py           # IC-02: PID-reuse-aware liveness (baseline compare)
│   ├── stale_detection.py            # IC-02: pass/compare the claim baseline
│   └── subtask_rows.py               # IC-04: NEW whole-file iter_unchecked_subtask_rows
├── cli/commands/
│   ├── implement.py                  # IC-02: co-write identity baseline at claim (~L1400)
│   ├── agent/workflow_executor.py    # IC-02: co-write baseline at implement-claim (~L668) + review-claim (~L1338)
│   └── agent/tasks_move_task.py      # IC-03: guarded rollback-uncheck write (~L1474)
├── acceptance/gates_core.py          # IC-04: migrate _find_unchecked_tasks onto the canonical iterator
├── review/lock.py                    # IC-05: is_stale → not is_process_alive(pid)
├── frontmatter.py                    # IC-02: register the new baseline field
└── status/wp_metadata.py             # IC-02: model the baseline field

tests/
├── specify_cli/status/               # IC-01 resolver characterization + red-first coord-husk
├── specify_cli/core/                 # IC-02 liveness (spawn→kill + baseline mismatch), IC-04 iterator
├── specify_cli/cli/commands/agent/   # IC-03 rollback-uncheck failure-mode
├── specify_cli/acceptance/           # IC-04 gates_core characterization
└── specify_cli/review/               # IC-05 review-lock equivalence
```

**Structure Decision**: Single Python package. Each IC maps to a tightly-scoped set of existing modules; the only NEW symbols are `resolve_subtasks_gate_dir` (in `missions/_read_path_resolver.py`) and `iter_unchecked_subtask_rows` (in `core/subtask_rows.py`), plus one additive frontmatter field.

## Resolved Plan-Phase Decisions

These were the open questions the spec/squads deferred to plan; all now resolved:

- **D1 — F1 helper home (RESOLVED).** Place `resolve_subtasks_gate_dir(feature_dir, repo_root, mission_slug) -> Path` in **`missions/_read_path_resolver.py`** (beside `resolve_planning_read_dir`). Verified: all three F1 sites (`status/emit.py`, `status/aggregate.py`, `coordination/status_transition.py`) **already import `resolve_planning_read_dir` from that module** — so consuming a sibling from there introduces no new import edge and avoids the layering smell of importing a private `status/emit._resolve_primary_subtasks_dir` into `status/aggregate` + `coordination/status_transition`. Contract = emit.py's superset: `repo_root` → else `resolve_canonical_root(feature_dir)` → else `feature_dir` (only on `WorkspaceRootNotFound`). Carry the `cast(Path, ...)` verbatim (C-002).
- **D2 — F3 failure-mode surface (RESOLVED).** The rollback-uncheck read/write routes through `write_text_within_directory` (house guard, C-004-safe). Failure mode = **SURFACED, not swallowed**: on read/write failure, log at error level AND record the incomplete-rollback on `_MoveTaskState` so the `move-task` result envelope reflects it (rather than the current silent log-and-continue that re-manifests #2513). It must **not** abort `_mt_release_review_lock` (which runs at `tasks_move_task.py:1595`, after `_mt_reset_for_planned_rollback`) — so the surfacing is via state/warning, not an early uncaught `raise` that skips lock release. Out-of-lock ordering preserved (C-001). Exact envelope field is an implementation detail for the WP; the invariant (visible, non-silent, lock-release-safe) is fixed here.
- **D3 — F2 baseline shape (RESOLVED, C-007).** ONE additive frontmatter field capturing the claiming process's creation-time (`psutil.Process(pid).create_time()`), co-written with `shell_pid` at claim. `is_process_alive` keeps its `(pid) -> bool` signature (so `review/lock`, `sync/owner`, `sync/daemon`, `dashboard/lifecycle` and other consumers are unaffected — IC-05 dep); reuse-awareness is added via a companion (e.g. `is_claiming_process_alive(pid, baseline)`) or an optional baseline param, consumed **only** by `stale_detection`. No process-identity subsystem.
- **D3a — Baseline degradation is ADDITIVE, zero legacy regression (RESOLVED, post-plan squad).** The compare is gated on the baseline being **present**: baseline present + matches the live PID's `create_time` → alive; baseline present + mismatch (recycled PID) → not-alive → `check_wp_staleness` falls to the **commit-timestamp heuristic** (verified: `stale_detection.py:282` short-circuits to `fresh` only when liveness is True, else applies the threshold — it does NOT hard-flag stale). Baseline **absent** (legacy pre-fix claim) → preserve today's exact behavior (`is_process_alive(pid)` trusts the live PID) so no legacy claim regresses. New claims from every write path carry a baseline (D3b), so the reuse protection applies going forward.
- **D3b — Baseline captured at ALL claim-write sites, close-by-construction (RESOLVED, post-plan squad — was a plan GAP).** `implement.py:1400` is **not** the only `shell_pid` writer. `stale_detection` reads the `shell_pid` key, which is written by THREE independent paths, all of which must co-write the baseline: (1) `cli/commands/implement.py:1400` (`spec-kitty implement`), (2) `cli/commands/agent/workflow_executor.py:668` (`_implement_write_claim_and_commit`, the `agent action implement` per-WP claim the implement-review loop uses — independent `getppid()` at :602), (3) `cli/commands/agent/workflow_executor.py:1338` (the review claim — it OVERWRITES the same `shell_pid` key with the reviewer's PID, so staleness reads it too). `reviewer_shell_pid` is consumed by no liveness path (verified) — it needs no baseline. **Canonical move:** extract ONE helper that co-writes `shell_pid` + baseline and route all three sites through it, so a `shell_pid` cannot be written without its baseline (close-by-construction). Capturing at only :1400 would let the primary `agent action implement` loop emit baseline-less claims → a genuinely-alive long-running WP could be falsely flagged stale.
- **D4 — F2 sequencing (RESOLVED).** Split the cheap truth-in-labeling (docstring fix + rename the mislabeled test to describe the *current* blindness) from the real baseline work so the labeling fix does not wait on the baseline; both live in IC-02 but the labeling subtasks are independent.
- **D5 — #2567 iterator shape (RESOLVED).** Add `iter_unchecked_subtask_rows(text) -> Iterator[str]` (whole-file, fence-aware, T###-scoped) on `core/subtask_rows` shared constants — it yields the offending line strings the acceptance gate needs (the existing `count_subtask_rows` returns counts only; `_walk_wp_section` is WP-scoped). Migrate `gates_core._find_unchecked_tasks` onto it; ratify the T###/fence/indent tightening with a characterization test capturing old→new flagging (FR-009).

## Complexity Tracking

No Charter Check violations — section intentionally empty.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Subtask-gate-dir single seam

- **Purpose**: Collapse the three divergent subtask-gate-dir resolvers into one canonical `resolve_subtasks_gate_dir` with the strong git-ancestry fallback, so no call site can gate on a stale coordination husk.
- **Relevant requirements**: FR-001, FR-002, FR-003; NFR-001, NFR-002; C-002, C-003.
- **Affected surfaces**: `missions/_read_path_resolver.py` (new seam), `status/emit.py` (delete `_resolve_primary_subtasks_dir`, repoint L581/L737), `status/aggregate.py` (`_resolve_review_gate_inputs` → call seam), `coordination/status_transition.py` (`_prepare_event` → call seam, gains fallback); tests under `tests/specify_cli/status/`.
- **Sequencing/depends-on**: none (independent spine keystone).
- **Risks**: The `status_transition.py` change is a **behavior fix** (repo_root=None coord path stops reading husk) — MUST land a **red-first** test on a git-rooted coord fixture proving the new primary resolution, plus a characterization test proving the two strong sites are byte-identical. Dead-code gate will flag if the deleted helper is not fully repointed. Carry `cast(Path, ...)` verbatim.

### IC-02 — PID-reuse-aware liveness + truth-in-labeling

- **Purpose**: Make `is_process_alive` unfoolable by a recycled PID via a persisted creation-time baseline, and correct the mislabeled test + docstring overclaim.
- **Relevant requirements**: FR-004, FR-005, FR-006; NFR-003, NFR-004, NFR-005; C-005, C-007.
- **Affected surfaces**: `core/process_liveness.py`, `core/stale_detection.py` (compare baseline), `cli/commands/implement.py` (co-write baseline at claim ~L1400), `cli/commands/agent/workflow_executor.py` (co-write baseline at the implement-claim ~L668 AND the review-claim ~L1338 — both write the `shell_pid` key staleness reads), `frontmatter.py` (register field), `status/wp_metadata.py` (model field); tests under `tests/specify_cli/core/`. **Canonical:** extract ONE claim-write helper (co-writes `shell_pid` + baseline) and route all three sites through it (D3b, close-by-construction).
- **Sequencing/depends-on**: none; but IC-05 depends on IC-02's `is_process_alive` signature staying `(pid) -> bool`.
- **Risks**: The scope-creep magnet — the PID-reuse compare is fenced to `process_liveness` + the `stale_detection` consumer (C-005); baseline is ONE additive field (C-007). **Degradation is additive (D3a): absent baseline preserves today's live-PID trust — no legacy regression; present-baseline mismatch → timestamp-heuristic fallback, never hard-stale.** All three `shell_pid` write paths must co-write the baseline (D3b) or the primary loop regresses. Truth-in-labeling subtasks are independent of the baseline work (D4) — do not block them. Real spawn→kill + simulated baseline-mismatch tests required (the mismatch is the deterministic seam, not an OS PID-recycle), plus a test that a `workflow_executor`-claimed WP carries the baseline.

### IC-03 — Rollback-uncheck guarded write

- **Purpose**: Ensure a WP rolled back to `planned` reliably loses its `- [x]` rows even when the out-of-lock write errors, so #2513 cannot silently re-manifest.
- **Relevant requirements**: FR-007; C-001, C-004.
- **Affected surfaces**: `cli/commands/agent/tasks_move_task.py` (`_mt_uncheck_rollback_subtasks` ~L1474 only); tests under `tests/specify_cli/cli/commands/agent/`.
- **Sequencing/depends-on**: none.
- **Risks**: Must NOT fold under `feature_status_lock` (C-001) and must NOT touch `_mt_run_pre_review_gate` (#2573 collision, C-004). Failure surface must not abort `_mt_release_review_lock` (D2). Owned_files scoped to the single seam.

### IC-04 — Checkbox-parser canonicalization

- **Purpose**: Replace the acceptance gate's stray whole-file `[ ]` regex with a canonical fence-aware, T###-scoped whole-file iterator, unifying checkbox semantics.
- **Relevant requirements**: FR-008, FR-009; NFR-003.
- **Affected surfaces**: `core/subtask_rows.py` (new `iter_unchecked_subtask_rows`), `acceptance/gates_core.py` (`_find_unchecked_tasks` migration); tests under `tests/specify_cli/core/` + `tests/specify_cli/acceptance/`.
- **Sequencing/depends-on**: none.
- **Risks**: This CHANGES observable acceptance-gate output (narrows to T###/fence-aware) — the tightening MUST be ratified via a characterization test capturing old→new flagging (FR-009), and the terminal-mission normalization must be preserved (edge case). Lowest value; keep tightly scoped.

### IC-05 — Review-lock liveness fold

- **Purpose**: Fold `review/lock.is_stale` onto the canonical `core/process_liveness.is_process_alive` (`return not is_process_alive(pid)`), removing the last stray liveness probe.
- **Relevant requirements**: FR-010; NFR-001.
- **Affected surfaces**: `review/lock.py` (`is_stale` only, and drop now-unused `os.kill`-for-liveness); tests under `tests/specify_cli/review/`.
- **Sequencing/depends-on**: **IC-02** (consumes the `(pid) -> bool` signature; sequence after IC-02 settles it). Equivalence-only — do NOT smuggle in PID-reuse hardening for the lock (would need the lock to persist a baseline = out of scope).
- **Risks**: Preserve branch-equivalence (live/dead/permission-denied) — pin with a characterization test. Keep `os.getpid()` usage intact (only the liveness `os.kill(pid,0)` is removed).
