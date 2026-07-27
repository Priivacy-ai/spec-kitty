# Quickstart — WP Lane FSM

## Exercise the FSM (single authority)

```python
from specify_cli.status.models import Lane
from specify_cli.status.wp_state import wp_state_for
from specify_cli.status.transition_context import TransitionContext

s = wp_state_for(Lane.GENESIS)
s.current_lane                      # Lane.GENESIS
s.may_transition_to(Lane.PLANNED)   # True (structural edge)
s.may_transition_to(Lane.CLAIMED)   # False (must seed first)

# Full transition — edge + guard + force decided by the State object (DM-01KTH03G)
ctx = TransitionContext(actor="claude", ...)
s.transition_to(Lane.PLANNED, ctx)  # -> PlannedState ; raises InvalidTransitionError on reject
```

`validate_transition(from, to, ctx)` now delegates to the state and returns
`(ok, error_message)` — identical results to before, one owner.

## Verify the invariants

```bash
# I1 single source: derived matrix == states' edges; no parallel transition table
PYTHONPATH=src python3 -c "from specify_cli.status.transitions import ALLOWED_TRANSITIONS; print(len(ALLOWED_TRANSITIONS))"

# I2 genesis non-display: absent from CANONICAL_LANES and from a materialized summary
PYTHONPATH=src python3 -c "from specify_cli.status_lanes import CANONICAL_LANES; print('genesis' in CANONICAL_LANES)"  # False

# Targeted suites (NOT the full suite — it is slow)
python -m pytest tests/status/ tests/specify_cli/status/ -q
python -m pytest tests/specify_cli/coordination/ tests/sync/ -q
```

## Validate the mission's acceptance

- `genesis → planned` seed persists and survives `finalize-tasks` (no clobber).
- An unseeded `implement` fails with "run finalize-tasks" and leaves no worktree.
- A genesis seed produces a contract-valid SaaS payload (post `spec_kitty_events` bump).
- `ruff` + `mypy` clean on touched modules; existing transition/guard suites green (behavior preserved).
