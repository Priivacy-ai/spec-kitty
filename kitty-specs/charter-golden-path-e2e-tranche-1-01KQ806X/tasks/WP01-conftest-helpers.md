---
work_package_id: WP01
title: E2E conftest helpers
dependencies: []
requirement_refs:
- FR-003
- FR-017
- FR-018
- FR-019
- FR-020
- NFR-004
planning_base_branch: test/charter-e2e-827-tranche-1
merge_target_branch: test/charter-e2e-827-tranche-1
branch_strategy: Planning artifacts for this feature were generated on test/charter-e2e-827-tranche-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into test/charter-e2e-827-tranche-1 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-golden-path-e2e-tranche-1-01KQ806X
base_commit: dbfae30a977c7e0451290b206274430b465452f4
created_at: '2026-04-27T18:27:35.534603+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1
assignee: ''
agent: claude
shell_pid: '49552'
history:
- at: '2026-04-27T18:15:53Z'
  actor: spec-kitty.tasks
  action: Generated
agent_profile: python-pedro
authoritative_surface: tests/e2e/conftest.py
execution_mode: code_change
owned_files:
- tests/e2e/conftest.py
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# Work Package WP01 — E2E conftest helpers

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this file, load your agent profile so you adopt the correct identity, scope, and boundaries for this work package:

```
/ad-hoc-profile-load python-pedro implementer
```

If `/ad-hoc-profile-load` is unavailable in your environment, read `src/doctrine/agent_profiles/shipped/python-pedro.agent.yaml` directly and adopt the implementer role and Python conventions described there before continuing.

## Objective

Add three additive helpers to `tests/e2e/conftest.py` that WP02's golden-path test will consume:

1. A `fresh_e2e_project` pytest fixture that boots a temp project from scratch via the public `spec-kitty init` CLI, **without** copying `.kittify` from the source checkout.
2. A pair of source-checkout pollution-guard helpers that capture a baseline before the test runs and assert no drift after.
3. A `format_subprocess_failure` helper that produces rich diagnostic strings for use in assertion messages (FR-019, NFR-004).

Do not modify the existing `e2e_project` fixture, the existing `REPO_ROOT` constant, or any other existing behaviour in `tests/e2e/conftest.py`. This WP is strictly additive.

## Branch Strategy

- **Planning / base branch**: `test/charter-e2e-827-tranche-1`
- **Final merge target**: `test/charter-e2e-827-tranche-1`
- Worktree allocation is computed by `finalize-tasks` from `lanes.json` and resolved at `implement` time. Do not branch manually; use `spec-kitty agent action implement WP01 --agent <name>` to enter the correct workspace.
- Branch strategy is `already-confirmed` (the user has explicitly chosen this branch — see `start-here.md` and the planning branch contract).

## Context

- **Mission spec**: `kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/spec.md`
- **Implementation plan**: `kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/plan.md`
- **Research record**: `kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/research.md` — read R-005 (pollution guard rationale) and R-007 (fresh-project fixture shape) carefully.
- **CLI flow contract**: `kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/contracts/cli-flow-contract.md` — describes the forbidden surface; do not import or reference any of the listed private symbols even from helpers.
- **Existing reference fixture**: `tests/e2e/conftest.py:24-120` — the existing `e2e_project` fixture, which copies `.kittify` from `REPO_ROOT`. **Do NOT copy this approach.** The whole point of WP01 is to avoid it.
- **Existing CLI helper**: `tests/conftest.py:344-364` — the `run_cli` fixture (60 s per-call timeout, isolated env). WP02 uses this; WP01 needs it transitively for the fixture's bootstrap subprocess calls.

## Subtask Details

### T001 — Add `fresh_e2e_project` fixture

**Purpose.** Provide WP02 with a temp project initialized solely through public `spec-kitty init`. Spec FR-003, FR-020. Plan R-007.

**Steps.**

1. Append (do not replace any existing code) a function-scoped pytest fixture to `tests/e2e/conftest.py`:

   ```python
   @pytest.fixture()
   def fresh_e2e_project(tmp_path: Path) -> Path:
       """Create a temp Spec Kitty project from scratch via public CLI.

       Unlike `e2e_project`, this fixture does NOT copy `.kittify` from the
       source checkout. It runs `spec-kitty init` against a brand-new git
       repo so the test exercises the operator path from a truly clean
       starting state.
       """
       project = tmp_path / "fresh-e2e-project"
       project.mkdir()

       # Step 1: bare git init + config (spec-kitty init does NOT do this).
       subprocess.run(["git", "init", "-b", "main"], cwd=project, check=True, capture_output=True)
       subprocess.run(
           ["git", "config", "user.email", "fresh-e2e@example.com"],
           cwd=project, check=True, capture_output=True,
       )
       subprocess.run(
           ["git", "config", "user.name", "Fresh E2E Test"],
           cwd=project, check=True, capture_output=True,
       )

       # Step 2: drive `spec-kitty init` via the same isolated invocation
       # path used by the `run_cli` fixture (PYTHONPATH → source `src/`,
       # SPEC_KITTY_TEMPLATE_ROOT → REPO_ROOT, SPEC_KITTY_TEST_MODE=1).
       result = run_cli_subprocess(
           project,
           "init", ".", "--ai", "codex", "--non-interactive",
       )
       if result.returncode != 0:
           raise AssertionError(
               f"spec-kitty init failed for fresh fixture:\n"
               f"  rc={result.returncode}\n"
               f"  stdout: {result.stdout}\n"
               f"  stderr: {result.stderr}"
           )

       # Step 3: commit the freshly seeded project state so subsequent
       # CLI commands see a clean working tree.
       subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
       subprocess.run(
           ["git", "commit", "-m", "Initial spec-kitty init"],
           cwd=project, check=True, capture_output=True,
       )

       return project
   ```

2. Add the import for `run_cli_subprocess` at the top of the file (it lives at `tests/test_isolation_helpers.py:93`). The existing conftest already imports from `tests.test_isolation_helpers`; add `run_cli_subprocess` to that import.

3. Validate by running:

   ```
   uv run pytest --collect-only tests/e2e/ -q
   ```

   The collection must succeed and continue to list the existing `test_cli_smoke.py` tests.

**Files.** Modifies `tests/e2e/conftest.py` (additive only). Estimated +35 lines.

**Validation.**

- [ ] `pytest --collect-only tests/e2e/` succeeds.
- [ ] `ruff check tests/e2e/conftest.py` exits 0.
- [ ] `mypy --strict tests/e2e/conftest.py` exits 0.
- [ ] No existing fixture in `tests/e2e/conftest.py` is renamed, deleted, or behaviourally altered.

**Edge cases.**

- `spec-kitty init` writing files outside the project (it should not, but defensive: the fixture's `tmp_path` cleanup is automatic, so no explicit teardown is needed beyond pytest's standard `tmp_path` lifecycle).
- A future commit changing the default agent for `spec-kitty init` — the fixture pins `--ai codex` explicitly to make this stable.

### T002 — Add source-checkout pollution-guard helpers

**Purpose.** Provide WP02 with a pre/post pollution check that catches both git-visible and `.gitignore`-masked writes into the source checkout (`REPO_ROOT`). Spec FR-017, FR-018. Plan R-005.

**Steps.**

1. At the top of `tests/e2e/conftest.py` (after existing imports, near `REPO_ROOT`), define a small dataclass:

   ```python
   from dataclasses import dataclass

   @dataclass(frozen=True)
   class SourcePollutionBaseline:
       git_status_short: str
       inventory: dict[str, dict[str, tuple[int, int]]]
       """Inventory shape: {watched_root: {relative_path_str: (size, mtime_ns)}}.

       Watched roots: kitty-specs/, .kittify/, .worktrees/, docs/, plus any
       directory whose name is "profile-invocations" anywhere in the tree.
       """
   ```

2. Add `capture_source_pollution_baseline(repo_root: Path) -> SourcePollutionBaseline`:

   ```python
   _WATCHED_ROOTS = ("kitty-specs", ".kittify", ".worktrees", "docs")

   def capture_source_pollution_baseline(repo_root: Path) -> SourcePollutionBaseline:
       """Snapshot the source checkout's pollution-relevant state.

       Layer 1: `git status --short` output. Catches anything visible to git.
       Layer 2: recursive inventory of watched roots, plus any
       `**/profile-invocations/` directory anywhere in the tree. Catches
       writes that .gitignore would mask.
       """
       status = subprocess.run(
           ["git", "status", "--short"],
           cwd=repo_root, capture_output=True, text=True, check=True,
       ).stdout

       inventory: dict[str, dict[str, tuple[int, int]]] = {}
       for root_name in _WATCHED_ROOTS:
           root = repo_root / root_name
           inventory[root_name] = _walk_inventory(root) if root.exists() else {}

       # Find every `profile-invocations` directory anywhere under repo_root.
       pi_inventory: dict[str, tuple[int, int]] = {}
       for path in repo_root.rglob("profile-invocations"):
           if path.is_dir():
               pi_inventory.update(_walk_inventory(path, anchor=repo_root))
       inventory["**/profile-invocations"] = pi_inventory

       return SourcePollutionBaseline(git_status_short=status, inventory=inventory)


   def _walk_inventory(
       root: Path,
       *,
       anchor: Path | None = None,
   ) -> dict[str, tuple[int, int]]:
       inv: dict[str, tuple[int, int]] = {}
       base = anchor if anchor is not None else root
       for path in root.rglob("*"):
           if path.is_file():
               st = path.stat()
               inv[str(path.relative_to(base))] = (st.st_size, st.st_mtime_ns)
       return inv
   ```

3. Add `assert_no_source_pollution(baseline: SourcePollutionBaseline, repo_root: Path) -> None`:

   ```python
   def assert_no_source_pollution(
       baseline: SourcePollutionBaseline, repo_root: Path
   ) -> None:
       """Compare current source-checkout state against the baseline; raise on drift."""
       current = capture_source_pollution_baseline(repo_root)

       if current.git_status_short != baseline.git_status_short:
           raise AssertionError(
               "Source-checkout polluted (FR-017 / git status drift):\n"
               f"  before: {baseline.git_status_short!r}\n"
               f"  after:  {current.git_status_short!r}"
           )

       for watched, before in baseline.inventory.items():
           after = current.inventory.get(watched, {})
           added = sorted(set(after) - set(before))
           removed = sorted(set(before) - set(after))
           modified = sorted(
               p for p in set(before) & set(after) if before[p] != after[p]
           )
           if added or removed or modified:
               raise AssertionError(
                   f"Source-checkout polluted (FR-018 / {watched} drift):\n"
                   f"  added:    {added}\n"
                   f"  removed:  {removed}\n"
                   f"  modified: {modified}"
               )
   ```

**Files.** Modifies `tests/e2e/conftest.py` (additive only). Estimated +75 lines.

**Validation.**

- [ ] Calling `capture_source_pollution_baseline(REPO_ROOT)` twice in succession with no intervening writes returns equal objects (round-trip stability — verify manually).
- [ ] `ruff check` and `mypy --strict` pass.
- [ ] Helpers are defined at module level; no fixtures own them.

**Edge cases.**

- `repo_root` not being a git repo — `git status --short` will fail. The helpers assume a git repo; document this in the docstring.
- Symlinks in watched roots — `rglob("*")` follows directory symlinks by default in some Python versions. Using `path.is_file()` is sufficient because the symlink target's `stat()` is what's recorded.
- Watched root absent (e.g. no `.worktrees/` yet) — handled by the existence check before walking.

### T003 — Add subprocess-failure diagnostic helper

**Purpose.** Give WP02 a single source of truth for the FR-019 / NFR-004 failure-message format. Without this, every step would inline its own copy.

**Steps.**

1. Add to `tests/e2e/conftest.py`:

   ```python
   def format_subprocess_failure(
       *,
       command: list[str] | tuple[str, ...],
       cwd: Path,
       completed: subprocess.CompletedProcess[str],
   ) -> str:
       """Produce a multi-line diagnostic for a failed subprocess.

       FR-019 / NFR-004: any failed subprocess invocation in the
       golden-path test must surface command, cwd, return code, stdout,
       and stderr in the assertion message so a single failed run is
       diagnosable without rerunning.
       """
       return (
           "Subprocess failed.\n"
           f"  command: {list(command)!r}\n"
           f"  cwd:     {cwd}\n"
           f"  rc:      {completed.returncode}\n"
           f"  stdout:  {completed.stdout!r}\n"
           f"  stderr:  {completed.stderr!r}"
       )
   ```

**Files.** Modifies `tests/e2e/conftest.py` (additive only). Estimated +20 lines.

**Validation.**

- [ ] Function is importable from `tests.e2e.conftest`.
- [ ] `mypy --strict` accepts the type signature.

## Definition of Done

- [ ] All three helpers (T001, T002, T003) are present in `tests/e2e/conftest.py`.
- [ ] `ruff check tests/e2e/conftest.py` exits 0.
- [ ] `mypy --strict tests/e2e/conftest.py` exits 0.
- [ ] `pytest --collect-only tests/e2e/` exits 0 and lists the existing `test_cli_smoke.py` tests unchanged.
- [ ] `pytest tests/e2e/test_cli_smoke.py -q` (existing smoke) still passes — no regression.
- [ ] No private helper from the forbidden list (C-001/C-002 in spec; full list in `contracts/cli-flow-contract.md`) is imported or referenced.
- [ ] No existing code in `tests/e2e/conftest.py` is modified or removed.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Helper code accidentally imports `decide_next_via_runtime` or another forbidden symbol "for convenience" | Reviewer greps the diff for forbidden names; reject on hit. |
| `capture_source_pollution_baseline` fails on a non-git directory | Documented in docstring; WP01's runtime contract is that it's only called against `REPO_ROOT` which is always a git repo. |
| Future Python pathlib change to `rglob` symlink semantics | Acceptable; the inventory still detects the most important class of pollution (file additions). If symlink-only writes become relevant, that's a follow-up. |
| The existing `e2e_project` fixture inadvertently broken by file ordering | `mypy --strict` and `pytest --collect-only` catch this before commit. |

## Reviewer Checklist

- [ ] No existing code in `tests/e2e/conftest.py` modified.
- [ ] Helpers do not import or reference any forbidden private symbol.
- [ ] `fresh_e2e_project` does not copy `.kittify` from `REPO_ROOT`.
- [ ] Pollution baseline records both git-visible AND `.gitignore`-masked state (layer 1 + layer 2).
- [ ] `format_subprocess_failure` includes command, cwd, rc, stdout, stderr.
- [ ] `mypy --strict` and `ruff check` pass on the modified file.
- [ ] No new external dependencies introduced.

## Implementation Command

```
spec-kitty agent action implement WP01 --agent <name>
```

This resolves the lane workspace and enters it. Do not branch manually.

## Activity Log

- 2026-04-27T18:31:59Z – claude – shell_pid=49552 – Ready for review: three additive helpers in tests/e2e/conftest.py per WP01 prompt; ruff + mypy --strict + pytest --collect-only all green
