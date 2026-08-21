---
type: how-to
updated: 2026-08-21
---

# Quickstart: verifying M7 (ExecutionMode consolidation)

How a reviewer confirms the mission landed correctly. Run from the repository root
checkout on the mission branch.

## 1. No class-name clash remains (AC-1, AC-3)

```bash
grep -rn "class ExecutionMode" src/          # expect: ZERO results
python -c "import mission_runtime; assert 'ExecutionMode' not in mission_runtime.__all__"
```

The only surviving live `ExecutionMode` is the external one:

```bash
git grep -n "from spec_kitty_events.status import.*ExecutionMode" src/
# → src/specify_cli/cli/commands/agent/tasks_transition_core.py
```

## 2. Ownership enum renamed, values intact (AC-2)

```bash
python -c "
from specify_cli.ownership.models import WorkProductKind
assert WorkProductKind.CODE_CHANGE.value == 'code_change'
assert WorkProductKind.PLANNING_ARTIFACT.value == 'planning_artifact'
print('WorkProductKind OK; values unchanged')
"
# The old symbol must NOT resolve:
python -c "from specify_cli.ownership.models import ExecutionMode" 2>&1 | grep -q ImportError \
  && echo "old name gone (expected)" || echo "FAIL: old name still resolves"
```

## 3. Frontmatter still parses (AC-2, AC-4)

```bash
.venv/bin/python -m pytest tests/integration/test_planning_artifact_wp.py \
  tests/specify_cli/ownership/test_inference.py -q
```

## 4. Consumers behave identically (AC-4)

```bash
.venv/bin/python -m pytest \
  tests/specify_cli/ownership/ tests/lanes/ \
  tests/specify_cli/lanes/ tests/specify_cli/core/test_worktree.py -q
```

## 5. Governance gate + re-drift guard (AC-1, AC-5)

```bash
.venv/bin/python -m pytest \
  tests/architectural/test_mission_runtime_surface.py \
  tests/architectural/test_execution_mode_no_redrift.py -q
```

The guard PERMITS M6 later adding a non-diff completion-mode member to
`WorkProductKind`; it goes RED only if a local `worktree`+`code_change` enum or the
retired symbol reappears.

## 6. Static gates (AC-6)

```bash
ruff check .
.venv/bin/python -m mypy --strict src/
```

## Baseline-red attribution

This is a behavior-preservation mission. Capture the targeted suites GREEN on the
mission base (`upstream/main @ c44b4bcf87`, minus the new guard test which is RED
by design) before applying, so any post-change red is correctly attributed. Known
pre-existing P0 reds (per ADR `2026-07-17-1`) are not this mission's.
