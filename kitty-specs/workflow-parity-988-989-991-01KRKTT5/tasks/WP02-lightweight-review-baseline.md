---
work_package_id: WP02
title: Lightweight review dead-code parity
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-010
- C-004
- C-005
planning_base_branch: fix/workflow-parity-988-989-991
merge_target_branch: fix/workflow-parity-988-989-991
branch_strategy: Planning artifacts for this mission were generated on fix/workflow-parity-988-989-991. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/workflow-parity-988-989-991 unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
agent: claude
history:
- at: '2026-05-14T18:15:00Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/review/
execution_mode: code_change
mission_slug: workflow-parity-988-989-991-01KRKTT5
owned_files:
- src/specify_cli/cli/commands/review/_dead_code.py
- src/specify_cli/cli/commands/review/_diagnostics.py
- src/specify_cli/cli/commands/review/_mode.py
- src/specify_cli/cli/commands/review/__init__.py
- tests/specify_cli/cli/commands/review/test_dead_code_baseline.py
role: implementer
tags: []
---

# WP02 — Lightweight review dead-code parity (#989)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Stop `spec-kitty review --mode lightweight` from silently producing a clean pass on modern numbered missions whose `meta.json` has `baseline_merge_commit: null`. Emit a structured failure with code `LIGHTWEIGHT_REVIEW_MISSING_BASELINE` for modern missions; preserve the historical skip-pass behavior for genuinely legacy missions but tag the path with `LEGACY_MISSION_DEAD_CODE_SKIP`.

## Context

- Bug report: https://github.com/Priivacy-ai/spec-kitty/issues/989
- Spec: [../spec.md](../spec.md) (see FR-004..FR-006, FR-010, C-004, C-005)
- Research: [../research.md](../research.md) (`#989` section)
- Contract: [../contracts/lightweight-review-baseline.md](../contracts/lightweight-review-baseline.md)

### Code map (read these first)

- Skip site: `src/specify_cli/cli/commands/review/_dead_code.py:30` — `scan_dead_code()` emits "Dead-code scan skipped"
- Mode dispatch: `src/specify_cli/cli/commands/review/__init__.py:45` — `review_mission()`
- Mode resolution: `src/specify_cli/cli/commands/review/_mode.py:57` — `resolve_mode()`; peer at line 24 for `MISSION_REVIEW_MODE_MISMATCH`
- Diagnostic registry: `src/specify_cli/cli/commands/review/_diagnostics.py:21`

## Branch Strategy

- Planning/base branch: `fix/workflow-parity-988-989-991`
- Final merge target: `fix/workflow-parity-988-989-991` → ultimately `main`
- Shared feature branch (no per-lane worktree).

## Subtasks

### T004 — Add diagnostic codes

**Purpose**: Make the failure greppable (NFR-004) and follow the existing diagnostic-registry pattern.

**Steps**:
1. Open `src/specify_cli/cli/commands/review/_diagnostics.py`.
2. Add two constants alongside `MISSION_REVIEW_MODE_MISMATCH`:
   - `LIGHTWEIGHT_REVIEW_MISSING_BASELINE`
   - `LEGACY_MISSION_DEAD_CODE_SKIP`
3. If the file uses an `Enum` for codes, add them to the enum; if it uses module-level string constants, add string constants. Match the local style.
4. Ensure both new codes are exported via `__all__` (if present).

**Files**:
- `src/specify_cli/cli/commands/review/_diagnostics.py` (modify, ~10 lines)

**Validation**:
- [ ] `rg "LIGHTWEIGHT_REVIEW_MISSING_BASELINE" src/` returns at least one hit.
- [ ] `rg "LEGACY_MISSION_DEAD_CODE_SKIP" src/` returns at least one hit.

### T005 — Update `scan_dead_code()` branching

**Purpose**: Encode the modern-vs-legacy decision at the only site that currently emits the skip message.

**Steps**:
1. Open `src/specify_cli/cli/commands/review/_dead_code.py`.
2. The function currently checks `if baseline_merge_commit is None: emit "skipped" and pass`. Replace with:
   ```python
   if baseline_merge_commit is not None:
       # existing scan path, unchanged
       ...
   elif _mission_is_modern(mission_meta):
       return _structured_failure(
           code=LIGHTWEIGHT_REVIEW_MISSING_BASELINE,
           mission_id=mission_meta.mission_id,
           mission_slug=mission_meta.mission_slug,
           remediation="Run `spec-kitty merge` to bake baseline_merge_commit, or rerun review with --mode post-merge after merge.",
       )
   else:
       return _legacy_skip(code=LEGACY_MISSION_DEAD_CODE_SKIP, ...)
   ```
3. Define `_mission_is_modern(meta) -> bool` as `bool(getattr(meta, "mission_id", None))` (the canonical ULID introduced by mission 083 — see CLAUDE.md "Mission Identity Model").
4. Propagate the structured failure through whatever return contract `scan_dead_code()` already uses (likely a `ReviewVerdict` or analogous dataclass — match local naming).
5. Wire the verdict so that `review --mode lightweight` exits non-zero when a modern mission gets the new failure. If the existing lightweight aggregation already exits non-zero on a non-pass `ReviewVerdict`, no additional CLI change is needed; otherwise add the exit-code wiring.
6. Do **not** touch `MISSION_REVIEW_MODE_MISMATCH` behavior or the `post-merge` mode dispatch.

**Files**:
- `src/specify_cli/cli/commands/review/_dead_code.py` (modify, ~40 lines)
- `src/specify_cli/cli/commands/review/__init__.py` (modify if exit-code wiring needs an explicit branch, ~5 lines)

**Validation**:
- [ ] `mypy --strict src/specify_cli/cli/commands/review` passes.
- [ ] Manual smoke: on a modern mission with `baseline_merge_commit: null`, `uv run spec-kitty review --mission <slug> --mode lightweight` exits non-zero.
- [ ] On a mission with `baseline_merge_commit` set, the existing scan still runs unchanged.

### T006 — Regression test

**Purpose**: Lock all three branches: modern-fail, modern-pass (baseline present), legacy-pass-tagged.

**Steps**:
1. Create `tests/specify_cli/cli/commands/review/test_dead_code_baseline.py`.
2. Use the same fixture pattern as `tests/specify_cli/cli/commands/review/test_mode_resolution.py` (the nearest peer).
3. Test cases:
   - `test_modern_mission_missing_baseline_returns_structured_failure`: Mission `meta.json` has `mission_id` set, `baseline_merge_commit: null`. Run lightweight review programmatically (via CLI runner). Assert exit code non-zero AND output mentions `LIGHTWEIGHT_REVIEW_MISSING_BASELINE`.
   - `test_modern_mission_with_baseline_runs_scan`: `mission_id` set, `baseline_merge_commit` set to a fake SHA. Assert exit code zero AND output does not contain `LIGHTWEIGHT_REVIEW_MISSING_BASELINE`.
   - `test_legacy_mission_skip_path_tagged`: No `mission_id` in `meta.json`, `baseline_merge_commit` null. Assert exit code zero (preserve legacy behavior) AND output contains `LEGACY_MISSION_DEAD_CODE_SKIP`.

**Files**:
- `tests/specify_cli/cli/commands/review/test_dead_code_baseline.py` (new, ~140 lines)

**Validation**:
- [ ] All three tests fail before T005 lands (the first asserts non-zero exit, today it's zero).
- [ ] All three pass after T005.
- [ ] `uv run pytest tests/specify_cli/cli/commands/review/test_dead_code_baseline.py tests/specify_cli/cli/commands/review/test_mode_resolution.py tests/specify_cli/cli/commands/test_review.py -q` is green.

## Definition of Done

- [ ] Three subtasks complete and committed.
- [ ] Contract [../contracts/lightweight-review-baseline.md](../contracts/lightweight-review-baseline.md) is satisfied.
- [ ] `uv run pytest tests/specify_cli/cli/commands/review/ tests/specify_cli/cli/commands/test_review.py -q` is green.
- [ ] `uv run mypy --strict src/specify_cli/cli/commands/review` is green.
- [ ] `rg "LIGHTWEIGHT_REVIEW_MISSING_BASELINE" src/ tests/` returns hits in both surfaces.

## Risks & Mitigations

- **R-1**: Breaking existing post-merge mode coverage.
  - **Mitigation**: Only modify the lightweight path; do not touch `_mode.py`'s post-merge resolution branch or `MISSION_REVIEW_MODE_MISMATCH`. Re-run `test_mode_resolution.py` to confirm.
- **R-2**: Misclassifying a legacy mission as modern (or vice versa).
  - **Mitigation**: Anchor on `mission_id` presence — it was introduced by the canonical identity migration (mission 083) and is the contract marker for modern missions per CLAUDE.md.

## Reviewer guidance

- Confirm the silent-skip path is gone for modern missions.
- Confirm the new diagnostic code appears in `_diagnostics.py` (single source) and is consumed (not just defined).
- Confirm exit codes flow from the structured failure all the way to `sys.exit`.
