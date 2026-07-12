# Quickstart / Validation: Implement-Loop Friction Quick-Wins II

How to validate each concern once implemented. Run from the mission clone with `uv run`.

## Prerequisites

```bash
cd /path/to/spec-kitty          # mission clone, on feat/loop-friction-quickwins-2
uv run ruff check . && uv run mypy src/
PWHEADLESS=1 uv run pytest tests/ -n auto --dist loadfile -p no:cacheprovider
```

## Per-concern checks

### IC-01 — guards self-stable
```bash
# Sequential lane allocation must need 0 inter-allocation commits:
uv run pytest tests/agent/test_orchestrator_lane_allocation.py -q
# mark-status on a pipe-table tasks.md must not re-stale the analysis report:
uv run pytest tests/specify_cli/test_analysis_report.py -q -k "pipe_table or churn"
```

### IC-02 — pre-review gate runner
```bash
# Interpreter resolution + pytest-lacking regression (the one that unmasks #2570.3):
uv run pytest tests/review/test_pre_review_gate_engine.py -q
# Manual: in a uv checkout, confirm `sys.executable -m pytest` fails but the gate still returns a verdict.
```

### IC-03 — papercuts
```bash
uv run pytest tests/specify_cli/tool_surface/profiles/test_manifest.py -q          # relative + legacy-tolerant
uv run pytest tests/specify_cli/cli/commands/agent/test_tasks_parsing_validation.py -q  # schema-drift message
uv run pytest tests/specify_cli/bulk_edit/test_inference.py -q                      # verbs vs genuine bulk
# Cross-machine manifest check: run `spec-kitty upgrade` on a second clone/path → expect 0 manifest diff.
```

### IC-04 — scaffold-block ergonomics
```bash
uv run pytest tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py -q
# Manual: fresh mission → first `setup-plan` returns non-blocked scaffold state, not `blocked`.
```

### IC-05 — move-task coord-lane recovery (coordination-aware)
```bash
# Coord-topology move-task regression; assert STATUS_STATE placement unchanged + no lane kitty-specs/ commit.
uv run pytest tests/ -q -k "move_task and coord"
```

## Definition of Done (mission)

- All FRs implemented; every new branch/helper has a focused test in-WP (NFR-007).
- Guard true-positive regressions pass (NFR-005): substantive change stales; genuine bulk trips;
  insufficient plan blocks; gate enforces by default.
- SC-001..SC-006 demonstrably met; `ruff`+`mypy` zero-issue; terminology guard green.
- Issues #2570/#2493/#2555/#2566/#2589 updated; epics #2017/#2093/#2160 stay open with children linked.
- Tracer files on the coordination branch assessed at close (#2095).
