# Quickstart: verifying the agent/tasks.py decomposition

How a reviewer (or the implementer) confirms the refactor is correct and complete.

## 1. Contract preserved (FR-001 / SC-006)

```bash
# Golden CLI characterization tests must pass unchanged before AND after refactor:
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py -q
# Full existing tasks suite stays green:
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ -q -p no:cacheprovider
```

## 2. Complexity ceiling met (NFR-001 / SC-002)

```bash
# No function over maxCC 15 anywhere in the agent tasks surface:
ruff check src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_*.py
# Residual shim size (target ≤ ~1200 LOC, from 4633):
wc -l src/specify_cli/cli/commands/agent/tasks.py
```

## 3. Seams independently testable (FR-003 / FR-004 / SC-004)

```bash
PWHEADLESS=1 pytest \
  tests/specify_cli/cli/commands/agent/test_tasks_outline.py \
  tests/specify_cli/cli/commands/agent/test_tasks_materialization.py \
  tests/specify_cli/cli/commands/agent/test_tasks_dependency_readiness.py -q
# Each seam imports without pulling in the shim (INV-2 — one-way imports):
python -c "import specify_cli.cli.commands.agent.tasks_outline; import specify_cli.cli.commands.agent.tasks_parsing_validation; print('seams import standalone OK')"
```

## 4. Commit routing centralized + output-preserving (FR-006/007/008 / SC-003)

```bash
# No residual direct git calls / dead pre-checks in the shim:
grep -nE "safe_commit\(|_planning_commit_worktree|_skip_target_branch_commit|_protected_branch_status_commit_error" \
  src/specify_cli/cli/commands/agent/tasks.py || echo "OK: tails routed, pre-checks deleted"
# Protected-primary message-preservation regression:
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_wp03_bypass_writers_fr008.py -q
```

## 5. Gates (NFR-002 / NFR-003 / FR-002)

```bash
mypy --strict src/specify_cli/cli/commands/agent/
# Pointer comment present:
head -3 src/specify_cli/cli/commands/agent/tasks.py | grep -q "2058" && echo "OK: #2058 pointer present"
# Terminology guard (CI-only gate — run before pushing):
pytest tests/architectural/test_no_legacy_terminology.py -q
```

## Done when

All five sections pass: contract byte-identical, maxCC ≤15 everywhere, seams import + test standalone,
commit tails routed with verbatim messages, and all gates green.
