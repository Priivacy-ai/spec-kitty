# Quickstart — Execution-State Canonical Domain Surface

## For consumers (after the strangle lands)

Resolve execution context through the one canonical surface:

```python
from mission_runtime import resolve_action_context, ExecutionMode

ctx = resolve_action_context(repo_root, mission_slug, wp_id="WP01")
ctx.feature_dir      # topology-aware mission dir
ctx.target_branch    # mode-correct authorized write branch
ctx.mode             # ExecutionMode.planning | direct_to_target | worktree
```

Access status through the facade / aggregate — never deep submodule imports:

```python
from specify_cli.status import MissionStatus          # ✅ facade
status = MissionStatus.load(repo_root, mission_slug)
status.claim("WP01")
# from specify_cli.status.emit import build_status_event   ❌ boundary violation
```

## Verifying the mission

```bash
# 1. Layer guard accepts the new umbrella
pytest tests/architectural/test_layer_rules.py -q

# 2. Sole-resolver enforcement
pytest tests/architectural/test_mission_runtime_surface.py -q

# 3. Repo-wide status boundary (expect zero non-exempt violations)
pytest tests/architectural/test_status_module_boundary.py -q
grep -rn "from specify_cli\.status\.\|import specify_cli\.status\." src/ --include="*.py" | grep -v "src/specify_cli/status/"

# 4. Full-sequence parity ratchet across all three modes
pytest tests/architectural/test_execution_context_parity.py -q

# 5. Path-builder residue eliminated (SC-004)
grep -rn 'kitty-specs.*mission_slug\|main_repo_root.*kitty' src/specify_cli --include="*.py" \
  | grep -v 'status/' | grep -v 'mission_runtime/'

# 6. Quality gates
ruff check src/ && mypy src/mission_runtime src/specify_cli/status
```

## Guardrails (operator ruling 2026-06-07)

- Planning → coordination branch. Direct-to-target → declared target branch, **no worktree**.
- The gate never resolves mainline as a write target without explicit operator authorization (C-001).
- Bulk-edit: consult `occurrence_map.yaml` before touching any `specify_cli.status.*` import.
