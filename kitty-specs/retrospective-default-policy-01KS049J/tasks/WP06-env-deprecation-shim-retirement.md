---
work_package_id: WP06
title: Env-var deprecation + shim retirement
dependencies:
- WP01
requirement_refs:
- FR-015
- FR-016
- FR-023
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts were generated on main; completed changes must merge back into main. Execution worktrees are allocated per computed lane from lanes.json after finalize-tasks.
subtasks:
- T030
- T031
- T032
- T033
- T034
phase: Surface
assignee: ''
agent: claude
history:
- timestamp: '2026-05-19T13:29:59Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/retrospective/deprecation.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/retrospective/config.py
- src/specify_cli/retrospective/mode.py
- src/specify_cli/retrospective/deprecation.py
- tests/retrospective/test_env_deprecation.py
role: implementer
tags: []
---

# Work Package Prompt: WP06 — Env-Var Deprecation + Shim Retirement

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Demote `SPEC_KITTY_RETROSPECTIVE` and `SPEC_KITTY_MODE` to test/dev-only overrides. Implement a one-warning-per-process deprecation notice. Refactor existing retrospective tests to inject `RetrospectivePolicy` directly. Resolve the fate of legacy `retrospective/config.py` and `retrospective/mode.py` per FR-023 — fold-and-delete OR retain as documented shim with explicit retirement plan.

This WP is the carrier for **bulk-edit shape A** (env-var deprecation messaging). Coordinate with the `occurrence_map.yaml` produced at finalize-tasks.

## Context

- FR-015: deprecate as test/dev overrides; durable replacements are `retrospective.enabled` and `retrospective.timing` + `retrospective.failure_policy`.
- FR-016: tests prefer injected policy; one dedicated test module for deprecation behavior.
- FR-023: `config.py` + `mode.py` must end in one of two terminal states — folded+deleted OR documented compat shim with retirement plan. "Half-deleted" is not acceptable.
- NFR-006: one warning per process, not per command invocation.

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Execution worktree resolved via `lanes.json` after `finalize-tasks`.

## Subtasks

### T030 — `DeprecationWarning` + Rich stderr notice with one-per-process budget

**Purpose**: When either env var is set, emit exactly ONE warning per process via both the Python `warnings` module and a Rich stderr notice.

**Steps**:

1. Create `src/specify_cli/retrospective/deprecation.py`:
   ```python
   _EMITTED: set[str] = set()

   def warn_env_var_deprecated(var_name: str, replacement_key: str, docs_url: str) -> None:
       if var_name in _EMITTED:
           return
       _EMITTED.add(var_name)
       msg = (
           f"{var_name} is a test/dev override only and will be removed. "
           f"Set durable policy via {replacement_key} in .kittify/config.yaml "
           f"or charter frontmatter. Docs: {docs_url}"
       )
       warnings.warn(msg, DeprecationWarning, stacklevel=2)
       _emit_rich_stderr_notice(var_name, replacement_key, docs_url)

   def _emit_rich_stderr_notice(var_name, replacement_key, docs_url):
       if os.environ.get("SPEC_KITTY_NO_DEPRECATION_WARNINGS") == "1":
           return
       from rich.console import Console
       Console(stderr=True).print(f"[yellow]DEPRECATED:[/yellow] {var_name} is a test/dev override only. Set {replacement_key} instead.")
   ```
2. Wire into the resolver (WP01's `policy.py`): when env vars are observed (T005 of WP01), call `warn_env_var_deprecated()` exactly when the var is set in the environment. The resolver imports from `deprecation.py`.
3. Replacement-key mapping (data only):
   - `SPEC_KITTY_RETROSPECTIVE` → `retrospective.enabled`
   - `SPEC_KITTY_MODE` → `retrospective.timing + retrospective.failure_policy`
4. `docs_url`: `docs/how-to/use-retrospective-learning.md` (relative path; WP07 ensures this doc exists).

**Files**:
- `src/specify_cli/retrospective/deprecation.py` (new, ~90 lines)

**Validation**:
- [ ] Set env var twice within a single test → warning emitted exactly once
- [ ] Rich stderr notice fires unless `SPEC_KITTY_NO_DEPRECATION_WARNINGS=1`
- [ ] Python `warnings.warn` captured by pytest's `recwarn` fixture in the dedicated test module

---

### T031 — `SPEC_KITTY_NO_DEPRECATION_WARNINGS` suppression flag

**Purpose**: CI and test environments can suppress the Rich stderr notice without re-enabling the deprecated env var behavior.

**Steps**:

1. Already partially implemented in T030's `_emit_rich_stderr_notice`. Verify the env var name matches what's documented in WP07's CONTRIBUTING/docs.
2. The Python `warnings.warn` path is NOT suppressed by this var — it's only the Rich stderr notice. Rationale: `warnings.warn` is captured by pytest and other test runners; suppressing it would hide real signal.
3. Document this distinction in the function docstring of `_emit_rich_stderr_notice`.

**Files**:
- `src/specify_cli/retrospective/deprecation.py` (light additions, ~10 lines)

**Validation**:
- [ ] `SPEC_KITTY_NO_DEPRECATION_WARNINGS=1` suppresses Rich stderr but NOT the `DeprecationWarning`
- [ ] Documented in code comments

---

### T032 — Refactor existing tests to inject `RetrospectivePolicy`

**Purpose**: Tests prefer dependency injection over `os.environ` mutation. Keep one dedicated test module for the deprecation behavior itself.

**Steps**:

1. Grep for `monkeypatch.setenv` and `os.environ[...]` mutations involving `SPEC_KITTY_RETROSPECTIVE` or `SPEC_KITTY_MODE` in `tests/`:
   ```bash
   grep -rn "SPEC_KITTY_RETROSPECTIVE\|SPEC_KITTY_MODE" tests/
   ```
2. For each match outside `tests/retrospective/test_env_deprecation.py`:
   - Replace the env mutation with direct `RetrospectivePolicy(...)` construction passed via fixture or argument.
   - If a test relies on env-var semantics (rare), move it to `test_env_deprecation.py`.
3. The dedicated test module is the only place that exercises the deprecation env-var pathway.
4. Tests that pre-existed and now don't use env vars MUST stay green after the refactor.

**Files**:
- Various `tests/retrospective/test_*.py` (existing files — WP06 only owns the test files that exclusively cover env-var behavior; for other tests, surface the refactor as a coordination point in WP06's commit message)
- `tests/retrospective/test_env_deprecation.py` (new, owns the env-var test cases)

**Coordination note**: Many test files belong to other WPs' owned_files. The refactor of *existing* test files that mutate env vars is a cross-cutting concern. Resolution: WP06 lands the new `deprecation.py` and `test_env_deprecation.py`. The refactor of other test files happens opportunistically as those WPs are implemented (WP02's tests, WP03's tests, etc.) — each WP's reviewer enforces "no env-var mutation in non-deprecation tests" as part of the DoD.

**Files** (revised — only this WP's own scope):
- `tests/retrospective/test_env_deprecation.py` (new, ~180 lines for T034)

**Validation**:
- [ ] No env mutation in tests outside `test_env_deprecation.py` (audited at mission-review)
- [ ] Coverage on `src/specify_cli/retrospective/deprecation.py` ≥ 90%

---

### T033 — Resolve shim fate for `config.py` + `mode.py` per FR-023

**Purpose**: Terminate the "half-deleted" risk. Pick (a) or (b) and execute decisively.

**Steps**:

1. **Decision**: pick one of:
   - **(a) Fold and delete.** Move any unique logic from `config.py` / `mode.py` into `policy.py` (most of it is env-var reading that `policy.py` already handles via T005 + T030). Delete `config.py` and `mode.py`. Update every import site:
     ```bash
     grep -rn "from specify_cli.retrospective.config\|from specify_cli.retrospective.mode\|specify_cli.retrospective.config\|specify_cli.retrospective.mode" src/ tests/
     ```
     Replace with imports from `specify_cli.retrospective` or `specify_cli.retrospective.policy`. Commit the rename as part of WP06.
   - **(b) Retain as compat shim.** Replace the contents of `config.py` and `mode.py` with thin re-exports plus a module docstring:
     ```python
     """Compatibility shim for the legacy `retrospective.config` surface.

     This module is retained to preserve back-compat for callers that import from
     `specify_cli.retrospective.config`. The canonical surface is
     `specify_cli.retrospective.policy`.

     **Retirement plan:**
     - Deprecation target: spec-kitty 3.3.0
     - Follow-up issue: https://github.com/Priivacy-ai/spec-kitty/issues/<N>
     - Rationale: <one-sentence reason for keeping the shim through 3.2.x>
     """
     from specify_cli.retrospective.policy import resolve_policy, RetrospectivePolicy  # noqa: F401
     # ... re-export every public name that used to be exposed
     ```

2. Recommended: **(a) fold and delete** is cleaner and matches the "no half-deleted state" spirit of FR-023. Only choose (b) if the import-site survey reveals deep external coupling that would be disruptive to update in one PR.

3. Whichever path is chosen, document it in this WP's commit message and in the mission-review report.

4. If choosing (b), open the follow-up issue in the GitHub repo and link it from the module docstring.

**Files**:
- `src/specify_cli/retrospective/config.py` (delete or replace)
- `src/specify_cli/retrospective/mode.py` (delete or replace)
- Various import sites across `src/` and `tests/` (update to new path) — these are coordinated as part of WP06's commit

**Validation**:
- [ ] No "half-deleted" state: either both files gone with import sites updated, OR both files exist as documented shims with retirement plan
- [ ] `uv run pytest tests/ -q` exits 0 after the change (no broken imports)
- [ ] If (a): `grep -rn 'from specify_cli.retrospective.config\|specify_cli.retrospective.mode' src/ tests/` returns no hits

---

### T034 — Tests for deprecation behavior

**Purpose**: Cover one-warn-per-process, durable-wins, and suppression flag.

**Steps**:

1. Create `tests/retrospective/test_env_deprecation.py` with classes:
   - `TestOneWarningPerProcess` — set env var twice; assert exactly one `DeprecationWarning`
   - `TestDurableConfigWinsOverEnvVar` — env var set + charter says opposite; assert charter wins; assert warning still fires
   - `TestRichStderrSuppression` — `SPEC_KITTY_NO_DEPRECATION_WARNINGS=1` suppresses the Rich notice but not the `DeprecationWarning`
   - `TestEnvVarObservationInSourceMap` — verify WP01's T005 records `<env:...>` source attribution correctly when env is the only opinion
2. Use `pytest.warns(DeprecationWarning)` and `capsys` / `capfd` for stderr capture. Reset `_EMITTED` between tests via a fixture.
3. The `_EMITTED` reset fixture should be the ONLY place tests mutate process-global state related to deprecation tracking.

**Files**:
- `tests/retrospective/test_env_deprecation.py` (new, ~200 lines)

**Validation**:
- [ ] All 4 test classes pass
- [ ] `pytest.warns(DeprecationWarning)` catches the expected warning
- [ ] Stderr suppression assertion works

---

## Definition of Done

- [ ] All 5 subtasks complete
- [ ] `uv run pytest tests/retrospective/ -q` exits 0
- [ ] `uv run ruff check src/specify_cli/retrospective/ tests/retrospective/test_env_deprecation.py` exits 0
- [ ] FR-023 terminated cleanly: either (a) or (b), documented in commit message + mission-review
- [ ] No `monkeypatch.setenv("SPEC_KITTY_RETROSPECTIVE", ...)` outside `test_env_deprecation.py` (audited)
- [ ] No edits outside `owned_files`

## Risks & Reviewer Guidance

- **Bulk-edit shape A**: env-var references span code, tests, docs, and skills. `occurrence_map.yaml` (finalize-tasks output) enumerates every occurrence. The reviewer cross-checks the occurrence map against actual changes — any occurrence with action `change` or `remove` MUST have a corresponding diff hunk.
- **Process-global state**: `_EMITTED` is module-level. Tests that share a process must reset it explicitly. Document this in the test module's docstring.
- **Shim retirement decision (T033)**: this is a permanent decision for 3.2.x. Reviewer should verify the chosen path's rationale is in the commit message AND that the follow-up issue (if (b)) is created and linked.

## Next

After this WP merges, WP07 (Docs/Skills) writes the user-facing deprecation guidance.

Implementation command:

```bash
spec-kitty agent action implement WP06 --agent claude
```
