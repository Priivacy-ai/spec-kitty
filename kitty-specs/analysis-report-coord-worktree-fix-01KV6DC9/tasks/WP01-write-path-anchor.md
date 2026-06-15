---
work_package_id: WP01
title: Write-Path Anchor in record_analysis()
dependencies: []
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: fix/analysis-report-coord-worktree-fix
merge_target_branch: fix/analysis-report-coord-worktree-fix
branch_strategy: Planning artifacts for this mission were generated on fix/analysis-report-coord-worktree-fix. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/analysis-report-coord-worktree-fix unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: claude
history:
- event: created
  at: '2026-06-15T19:57:30Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## Objective

Fix `record_analysis()` in `src/specify_cli/cli/commands/agent/mission.py` so that
`write_analysis_report()` always receives the **main-checkout** mission directory,
not the coord-worktree path that `_find_feature_directory()` may return when a
coordination worktree is active.

This is the root defect from issue #1989. When a coord worktree exists,
`_find_feature_directory()` returns the coord-worktree path, which lacks `spec.md` —
causing `write_analysis_report()` to raise `AnalysisReportError("Required artifact
missing: ...")`. Agents forced to work around this write `analysis-report.md` directly
in carrier format, which the implement gate then rejects.

## Branch Strategy

- **Planning/execution branch**: `fix/analysis-report-coord-worktree-fix`
- **Merge target**: `fix/analysis-report-coord-worktree-fix`
- Your worktree is allocated per `lanes.json`. Run:
  `spec-kitty agent action implement WP01 --agent claude`
  from the main checkout to enter the correct worktree.

## Context

### Key code locations

**`record_analysis()` entry point** — `src/specify_cli/cli/commands/agent/mission.py` around line 1753:

```python
@app.command(name="record-analysis")
def record_analysis(
    feature: Annotated[str | None, typer.Option("--mission", ...)] = None,
    ...
) -> None:
    ...
    repo_root = get_main_repo_root(repo_root)
    feature_dir = _find_feature_directory(repo_root, Path.cwd().resolve(), explicit_feature=feature)
    placement_ref = _resolve_record_analysis_placement_ref(repo_root, feature_dir)
    _enforce_analysis_report_write_preflight(cwd_repo_root, json_output=json_output, placement_ref=placement_ref)
    ...
    result = write_analysis_report(
        feature_dir=feature_dir,   # ← BUG: may be coord path
        repo_root=repo_root,
        body=body,
        analyzer_agent=analyzer_agent,
    )
```

**CRITICAL — use the topology-BLIND primitive.** `candidate_feature_dir_for_mission`
is **topology-aware**: it routes through `resolve_mission_read_path`, which returns the
**coord worktree** whenever one exists — so it would reproduce the bug, not fix it. The
correct primitive is `primary_feature_dir_for_mission`, which is "deliberately
topology-blind" and always returns the PRIMARY-checkout mission dir. It is already the
sanctioned anchor used elsewhere in `mission.py` (e.g. lines ~811 and ~2754):

```python
from specify_cli.missions._read_path_resolver import primary_feature_dir_for_mission
# (also re-exported from specify_cli.missions.feature_dir_resolver)

_primary_dir = primary_feature_dir_for_mission(repo_root, mission_slug)
```

`primary_feature_dir_for_mission` takes the mission slug. After `_find_feature_directory()`
resolves `feature_dir` (coord-aware), `feature_dir.name` is the canonical mission-dir
basename (the slug) for both topologies — the coord worktree path is
`.worktrees/<slug>-coord/kitty-specs/<slug>/`, so `.name == <slug>`. Pass `feature_dir.name`.

## Subtask Guidance

### T001 — Override write destination in `record_analysis()`

**Purpose**: Decouple the write path from the coord-aware read path by computing
a `write_feature_dir` with the **topology-blind** `primary_feature_dir_for_mission`
primitive, so the write always targets the primary checkout regardless of coord topology.

**Steps**:

1. Locate `record_analysis()` in `src/specify_cli/cli/commands/agent/mission.py`
   (search for `@app.command(name="record-analysis")`).

2. After the existing `feature_dir = _find_feature_directory(...)` call, and after
   `placement_ref = _resolve_record_analysis_placement_ref(repo_root, feature_dir)`
   and the preflight call, add (import locally to match the existing call sites at
   lines ~811 / ~2754):
   ```python
   from specify_cli.missions._read_path_resolver import primary_feature_dir_for_mission
   write_feature_dir = primary_feature_dir_for_mission(repo_root, feature_dir.name)
   ```
   Do NOT use `candidate_feature_dir_for_mission` here — it is topology-aware and would
   return the coord worktree, reproducing the bug.

3. Replace the `write_analysis_report()` call's `feature_dir=feature_dir` argument
   with `feature_dir=write_feature_dir`.

4. The `dossier_sync` call below `write_analysis_report()` also passes `feature_dir`
   to `trigger_feature_dossier_sync_if_enabled`. Update that call to use
   `write_feature_dir` too (it expects the main-checkout path).

**The complete change in context**:
```python
# BEFORE (existing code, buggy):
result = write_analysis_report(
    feature_dir=feature_dir,
    repo_root=repo_root,
    body=body,
    analyzer_agent=analyzer_agent,
)
with contextlib.suppress(Exception):
    trigger_feature_dossier_sync_if_enabled(
        feature_dir,              # ← coord path
        result.mission_slug,
        repo_root,
    )

# AFTER (fixed):
from specify_cli.missions._read_path_resolver import primary_feature_dir_for_mission
write_feature_dir = primary_feature_dir_for_mission(repo_root, feature_dir.name)
result = write_analysis_report(
    feature_dir=write_feature_dir,
    repo_root=repo_root,
    body=body,
    analyzer_agent=analyzer_agent,
)
with contextlib.suppress(Exception):
    trigger_feature_dossier_sync_if_enabled(
        write_feature_dir,        # ← primary-checkout path
        result.mission_slug,
        repo_root,
    )
```

5. `feature_dir` (the coord-aware path) still flows into `placement_ref` and
   `_enforce_analysis_report_write_preflight()`. Do NOT change those uses.

**Files**: `src/specify_cli/cli/commands/agent/mission.py`

**Validation**:
- [ ] `write_analysis_report` receives the main-checkout path when coord worktree exists
- [ ] `_find_feature_directory` result is still used for placement ref and preflight
- [ ] `ruff check src/specify_cli/cli/commands/agent/mission.py` passes
- [ ] `mypy --strict src/specify_cli/cli/commands/agent/mission.py` passes

---

### T002 — Unit test: `write_analysis_report` called with main-checkout path

**Purpose**: Assert that the write destination is the primary-checkout path
(`primary_feature_dir_for_mission(...)`) even when `_find_feature_directory()` would
return a coord-worktree path.

**Steps**:

1. Create `tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py`.

2. Write a test that:
   - Sets up a `tmp_path` with a fake main-checkout structure:
     `tmp_path/kitty-specs/my-mission/` with `spec.md`, `plan.md`, `tasks.md`
   - Sets up a fake coord-worktree structure:
     `tmp_path/.worktrees/my-mission-coord/kitty-specs/my-mission/` with only `plan.md` (no `spec.md`)
   - Monkeypatches `_find_feature_directory` to return the coord path
   - Monkeypatches `write_analysis_report` to capture `feature_dir`
   - Invokes the `record_analysis` function with `feature="my-mission"`
   - Asserts `write_analysis_report` was called with the main-checkout path, not the coord path

3. Use `monkeypatch` for `locate_project_root`, `get_main_repo_root`, and other I/O.

**Files**: `tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py`

**Validation**:
- [ ] Test fails before T001 fix is applied
- [ ] Test passes after T001 fix is applied
- [ ] `pytest tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py -v` passes

---

### T003 — Integration test: `record-analysis` succeeds when coord worktree lacks `spec.md`

**Purpose**: End-to-end verification that the command completes successfully under the
exact topology that caused the original bug.

**Steps**:

1. In the same test file as T002, add a test that:
   - Creates a realistic `tmp_path` with main checkout containing `spec.md`, `plan.md`, `tasks.md`
   - Creates a coord-worktree directory WITHOUT `spec.md` (only `plan.md`)
   - Monkeypatches `_find_feature_directory` to return the coord path (simulating coord topology)
   - Provides a valid `analysis-findings/v1` carrier body as stdin
   - Invokes the command via typer test client or direct function call
   - Asserts the command exits successfully (exit code 0)
   - Asserts `analysis-report.md` is written to the **main-checkout** path

**Files**: `tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py`

**Validation**:
- [ ] Test verifies `analysis-report.md` appears in main checkout, not coord path
- [ ] Test verifies `artifact_type: spec-kitty.analysis-report` in the written file
- [ ] `pytest tests/.../test_record_analysis_coord_worktree.py::test_succeeds_with_coord_worktree -v` passes

---

### T004 — Regression test: `record-analysis` works without coord worktree

**Purpose**: Verify the fix does not break the no-coord-worktree path.

**Steps**:

1. In the same test file, add a regression test where `_find_feature_directory` returns
   the main-checkout path directly (no coord worktree). Assert the command still writes
   `analysis-report.md` to the main-checkout path with the correct format.

**Files**: `tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py`

**Validation**:
- [ ] Existing `test_record_analysis_command_persists_report` in `test_analysis_report.py` still passes
- [ ] New regression test passes
- [ ] `pytest tests/specify_cli/test_analysis_report.py -v` passes (no regressions)

---

## Definition of Done

- [ ] T001: `record_analysis()` passes `write_feature_dir` (main checkout) to `write_analysis_report()` and dossier sync
- [ ] T002: Unit test asserts write destination is main checkout, not coord path
- [ ] T003: Integration test confirms success under coord-worktree topology
- [ ] T004: Regression test confirms no-coord-worktree path is unchanged
- [ ] `ruff check` and `mypy --strict` pass with zero issues on modified files
- [ ] `pytest tests/specify_cli/test_analysis_report.py tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py` all pass

## Risks

- **Use the topology-BLIND primitive (resolved A1)**: `candidate_feature_dir_for_mission` is topology-aware and returns the coord worktree when one exists — using it here would reproduce the bug. Use `primary_feature_dir_for_mission` (topology-blind, primary checkout). This is the same primitive already used in `mission.py` at lines ~811 and ~2754 for primary-anchored reads.
- **Placement-ref still needs coord-aware `feature_dir`**: Do not change the `feature_dir` passed to `_resolve_record_analysis_placement_ref()` or `_enforce_analysis_report_write_preflight()`. Only the downstream `write_analysis_report()` and dossier-sync calls should receive `write_feature_dir`.
- **`feature_dir.name` is the slug**: The resolved `feature_dir` basename equals the mission slug in both topologies (`.worktrees/<slug>-coord/kitty-specs/<slug>/` → `.name == <slug>`), so `primary_feature_dir_for_mission(repo_root, feature_dir.name)` is correct. If a future caller passes a `mid8` handle, `primary_feature_dir_for_mission` still resolves it correctly via its slug argument.

## Reviewer Guidance

- **Confirm `primary_feature_dir_for_mission` (NOT `candidate_feature_dir_for_mission`) is used for the write path** — this is the crux of the fix.
- Verify `feature_dir` (coord-aware) is still used for preflight and placement-ref.
- Verify `write_feature_dir` is used for `write_analysis_report()` and dossier sync.
- Confirm tests cover both coord and no-coord topologies.
- Check mypy annotations — `write_feature_dir` should be `Path`.
