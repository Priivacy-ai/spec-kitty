# Quickstart — Software-Dev Mission Composition Rewrite

**Mission**: `software-dev-composition-rewrite-01KQ26CY`
**Audience**: operator running the post-rewrite live path; reviewer verifying the slice landed.

## Operator flow (post-rewrite)

```bash
# 1. Specify
spec-kitty agent action specify --mission <handle>           # composition-driven
# → composes specify.step-contract.yaml; writes spec.md

# 2. Plan
spec-kitty agent action plan --mission <handle>              # composition-driven
# → composes plan.step-contract.yaml; writes plan.md

# 3. Tasks (single public step; internal sub-substructure)
spec-kitty agent action tasks --mission <handle>             # composition-driven (NEW)
# → composes tasks.step-contract.yaml (outline → packages → finalize)
# → writes tasks.md, tasks/WP##.md, validates dependencies

# 4. Implement (per WP)
spec-kitty agent action implement WP01 --mission <handle>    # composition-driven
# → composes implement.step-contract.yaml; runs in WP's worktree

# 5. Review
spec-kitty agent action review WP01 --mission <handle>       # composition-driven
# → composes review.step-contract.yaml; verifies + transitions WP to done
```

The operator-visible UX is identical to pre-rewrite; the internal routing changes.

## Reviewer verification

```bash
# Confirm composition is the live path for software-dev
PYTHONPATH=src python - <<'PY'
from pathlib import Path
from doctrine.mission_step_contracts.repository import MissionStepContractRepository

repo = MissionStepContractRepository(
    project_dir=Path(".kittify/doctrine/mission_step_contracts")
)
for action in ["specify", "plan", "tasks", "implement", "review"]:
    contract = repo.get_by_action("software-dev", action)
    assert contract is not None, f"missing contract for {action}"
    print(f"{action}: {contract.id} (steps: {len(contract.steps)})")
PY

# Confirm profile defaults include tasks
python - <<'PY'
from specify_cli.mission_step_contracts.executor import _ACTION_PROFILE_DEFAULTS
for action in ["specify", "plan", "tasks", "implement", "review"]:
    print(f"({'software-dev'}, {action}) → {_ACTION_PROFILE_DEFAULTS[('software-dev', action)]}")
PY

# Run dedicated composition tests
cd src && pytest tests/specify_cli/mission_step_contracts/test_software_dev_composition.py -v
cd src && pytest tests/specify_cli/next/test_runtime_bridge_composition.py -v

# Confirm legacy template marked deprecated
head -10 src/doctrine/missions/software-dev/mission-runtime.yaml
# → first lines should contain "DEPRECATED (since #503 / phase 6 wp6.2)"
```

## Smoke test on a real mission

```bash
spec-kitty mission create "qs-composition-smoke" --json
# → note the mission_id; capture FEATURE_DIR

spec-kitty agent action specify --mission qs-composition-smoke
# → spec.md written; verify composition by inspecting trail/event log

spec-kitty agent action plan --mission qs-composition-smoke
# → plan.md written

spec-kitty agent action tasks --mission qs-composition-smoke
# → tasks.md + tasks/WP##.md written + dependencies validated
# (this is the path that previously required three legacy steps)

# Optional: continue through implement/review against a tiny synthetic WP.
```

## Expected diffs vs pre-rewrite

| Surface | Pre-rewrite | Post-rewrite |
|---|---|---|
| `software-dev` `specify`/`plan`/`implement`/`review` dispatch | legacy DAG via `mission-runtime.yaml` | `StepContractExecutor.execute` |
| `software-dev` `tasks_outline` / `tasks_packages` / `tasks_finalize` dispatch | three separate legacy DAG steps | one composed `tasks` step with `outline` / `packages` / `finalize` sub-steps |
| `_ACTION_PROFILE_DEFAULTS` keys | 4 entries (no `tasks`) | 5 entries (incl. `("software-dev","tasks") → "architect-alphonso"`) |
| `mission-runtime.yaml` | live source | deprecation header; transitional reference only |
| Action-scoped governance per invocation | mostly legacy guard logic + ad-hoc | strictly `actions/<action>/index.yaml` via `resolve_context(...)` |
| Lane-state substrate | typed (`emit_status_transition`) | unchanged — typed (`emit_status_transition`) |

## Rollback

If a regression slips through review:

1. Revert the runtime-bridge composition dispatch branch (single file change).
2. Leave `tasks.step-contract.yaml`, the `_ACTION_PROFILE_DEFAULTS` entry, and the deprecation header in place — they are inert without the bridge wiring.

The legacy DAG path is intentionally preserved exactly as today, so revert is safe and surgical.
