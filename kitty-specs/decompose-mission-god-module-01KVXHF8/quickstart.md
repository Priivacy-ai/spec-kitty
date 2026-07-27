# Quickstart — Verifying the `agent/mission.py` decomposition (#2056)

This is a behavior-preserving refactor. "Verification" means proving the CLI surface, import edges, and
behavior are byte-for-byte unchanged while the module topology and complexity improve.

## 1. Golden CLI contract (the safety net — captured in WP01)

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py -q
```

Asserts: `agent mission --help` lists exactly 8 commands; each subcommand's `--help` lists exact flags;
representative success/error JSON envelopes match. Must pass on base AND after every WP.

## 2. Full mission-touching suite (zero patch-target churn)

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ tests/integration/test_json_envelope_strict.py \
  tests/tasks/ -n auto --dist loadfile -p no:cacheprovider
```

Every `@patch("specify_cli.cli.commands.agent.mission.<name>")` must still resolve via shim re-export —
no test edits.

## 3. Per-seam focused tests (≥90%)

```bash
PWHEADLESS=1 pytest \
  tests/specify_cli/cli/commands/agent/test_mission_feature_resolution.py \
  tests/specify_cli/cli/commands/agent/test_mission_parsing.py \
  tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py \
  -q
```

Pure parsers/resolvers exercised DIRECTLY (not only via the command path).

## 4. `--validate-only` zero-mutation invariant (INV-6)

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_finalize_tasks_validate_only_readonly.py -q
```

## 5. Complexity ceiling + static analysis (NFR-001/003/004)

```bash
ruff check src/specify_cli/cli/commands/agent/ src/specify_cli/coordination/commit_router.py
mypy --strict src/specify_cli/cli/commands/agent/mission.py \
  src/specify_cli/cli/commands/agent/mission_*.py \
  src/specify_cli/coordination/commit_router.py
```

`ruff` C901 must report zero functions over complexity 15. Zero new suppressions.

## 6. Planning-commit relocation + tasks.py repoint (FR-007 / INV-5/7)

```bash
grep -n "_planning_commit_worktree" src/specify_cli/coordination/commit_router.py   # now defined here
grep -n "_planning_commit_worktree" src/specify_cli/cli/commands/agent/tasks.py     # import repointed
PWHEADLESS=1 pytest tests/tasks/ -q                                                 # tasks.py behavior unchanged
```

`_planning_commit_worktree` / `_resolve_planning_placement` /
`_stage_finalize_artifacts_in_coord_worktree` live in `commit_router.py`; `tasks.py` imports them from
there. They are LIVE on this base — relocated, never deleted.
