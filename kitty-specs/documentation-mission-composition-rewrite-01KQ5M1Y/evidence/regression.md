# T028 — Regression Sweep Evidence

Mission: `documentation-mission-composition-rewrite-01KQ5M1Y` (#502)
Subtask: T028 (NFR-002 — protected-suite regression sweep)
Run by: claude:opus-4.7:reviewer-renata:implementer (WP07)

## HEAD SHA at run time

```
0fc53df3d77cb257325a862111a061e3331c8d34
```

(branch: `kitty/mission-documentation-mission-composition-rewrite-01KQ5M1Y-lane-a`,
last commit: `feat(WP06): real-runtime integration walk for documentation mission (#502)`)

## Command (verbatim)

```bash
uv run --python 3.13 --extra test python -m pytest \
    tests/specify_cli/mission_step_contracts/ \
    tests/specify_cli/next/test_runtime_bridge_composition.py \
    tests/specify_cli/next/test_runtime_bridge_research_composition.py \
    tests/integration/test_research_runtime_walk.py \
    tests/integration/test_custom_mission_runtime_walk.py \
    tests/integration/test_mission_run_command.py \
    tests/integration/test_documentation_runtime_walk.py \
    tests/specify_cli/next/test_runtime_bridge_documentation_composition.py \
    tests/specify_cli/test_documentation_drg_nodes.py \
    tests/specify_cli/test_documentation_template_resolution.py \
    tests/specify_cli/mission_step_contracts/test_documentation_composition.py \
    -q --timeout=120
```

Working directory: the lane worktree
`/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260426-184741-CfhGXa/spec-kitty/.worktrees/documentation-mission-composition-rewrite-01KQ5M1Y-lane-a`.

## Verbatim stdout

```
============================= test session starts ==============================
platform darwin -- Python 3.13.1, pytest-9.0.3, pluggy-1.6.0
rootdir: /private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260426-184741-CfhGXa/spec-kitty/.worktrees/documentation-mission-composition-rewrite-01KQ5M1Y-lane-a
configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)
plugins: cov-7.1.0, timeout-2.4.0, asyncio-1.3.0, respx-0.23.1, anyio-4.13.0
timeout: 120.0s
timeout method: signal
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 169 items

tests/specify_cli/mission_step_contracts/test_documentation_composition.py . [  0%]
.....                                                                    [  3%]
tests/specify_cli/mission_step_contracts/test_executor.py ....           [  5%]
tests/specify_cli/mission_step_contracts/test_research_composition.py .. [  7%]
...................                                                      [ 18%]
tests/specify_cli/mission_step_contracts/test_software_dev_composition.py . [ 18%]
...........                                                              [ 25%]
tests/specify_cli/next/test_runtime_bridge_composition.py .............. [ 33%]
........................                                                 [ 47%]
tests/specify_cli/next/test_runtime_bridge_research_composition.py ..... [ 50%]
...........................                                              [ 66%]
tests/integration/test_research_runtime_walk.py .....                    [ 69%]
tests/integration/test_custom_mission_runtime_walk.py .....              [ 72%]
tests/integration/test_mission_run_command.py ....                       [ 75%]
tests/integration/test_documentation_runtime_walk.py ......              [ 78%]
tests/specify_cli/next/test_runtime_bridge_documentation_composition.py . [ 79%]
....................                                                     [ 91%]
tests/specify_cli/test_documentation_drg_nodes.py .............          [ 98%]
tests/specify_cli/test_documentation_template_resolution.py ..           [100%]

=============================== warnings summary ===============================
tests/specify_cli/mission_step_contracts/test_executor.py: 3 warnings
tests/specify_cli/mission_step_contracts/test_software_dev_composition.py: 9 warnings
  /private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260426-184741-CfhGXa/spec-kitty/.worktrees/documentation-mission-composition-rewrite-01KQ5M1Y-lane-a/.venv/lib/python3.13/site-packages/pydantic/main.py:732: DeprecationWarning: Profile 'reviewer-fixture': the scalar 'role:' field is deprecated. Replace with: roles: [reviewer]
    return cls.__pydantic_validator__.validate_python(

tests/specify_cli/mission_step_contracts/test_executor.py: 3 warnings
tests/specify_cli/mission_step_contracts/test_software_dev_composition.py: 9 warnings
  /private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260426-184741-CfhGXa/spec-kitty/.worktrees/documentation-mission-composition-rewrite-01KQ5M1Y-lane-a/.venv/lib/python3.13/site-packages/pydantic/main.py:732: DeprecationWarning: Profile 'implementer-fixture': the scalar 'role:' field is deprecated. Replace with: roles: [implementer]
    return cls.__pydantic_validator__.validate_python(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 169 passed, 24 warnings in 20.32s =======================
```

(Trailing `Not authenticated, skipping sync` lines from the local invocation
projection are unrelated to the protected suites and follow the SaaS sync gate
documented in #735.)

## Result summary

| Metric | Count |
|---|---|
| Passed | **169** |
| Failed | **0** |
| Skipped | **0** |
| Errors | **0** |
| Warnings (pre-existing pydantic deprecation, not introduced by #502) | 24 |
| Wall time | 20.32 s (well under the per-test 120 s cap) |

All 11 protected suites listed in the task spec pass:

1. `tests/specify_cli/mission_step_contracts/` (suite directory — covers
   `test_documentation_composition.py` (6), `test_executor.py` (4),
   `test_research_composition.py` (21), `test_software_dev_composition.py` (12))
2. `tests/specify_cli/next/test_runtime_bridge_composition.py` (38)
3. `tests/specify_cli/next/test_runtime_bridge_research_composition.py` (32)
4. `tests/integration/test_research_runtime_walk.py` (5)
5. `tests/integration/test_custom_mission_runtime_walk.py` (5)
6. `tests/integration/test_mission_run_command.py` (4)
7. `tests/integration/test_documentation_runtime_walk.py` (6) — **WP06 SC-001/SC-003/SC-004**
8. `tests/specify_cli/next/test_runtime_bridge_documentation_composition.py` (21)
9. `tests/specify_cli/test_documentation_drg_nodes.py` (13)
10. `tests/specify_cli/test_documentation_template_resolution.py` (2)
11. `tests/specify_cli/mission_step_contracts/test_documentation_composition.py` (already counted in 1; explicit re-run requested by spec)

NFR-002 satisfied: zero protected-suite regressions.
