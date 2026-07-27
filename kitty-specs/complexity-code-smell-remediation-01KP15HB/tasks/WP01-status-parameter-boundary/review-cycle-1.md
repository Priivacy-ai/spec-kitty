**Issue 1: `validate_transition()` migration is incomplete in `tests/status/test_transitions.py`.**

The WP definition requires the validator surface to move to `(from_lane, to_lane, ctx: GuardContext)` and explicitly says all `validate_transition` call-site files must construct `GuardContext(...)`. `tests/status/test_transitions.py` still exercises the old two-argument form at multiple locations, including `validate_transition(from_lane, to_lane)` at [tests/status/test_transitions.py](/home/stijnd/Documents/code/forks/spec-kitty/.worktrees/complexity-code-smell-remediation-01KP15HB-lane-a/tests/status/test_transitions.py:196), [tests/status/test_transitions.py](/home/stijnd/Documents/code/forks/spec-kitty/.worktrees/complexity-code-smell-remediation-01KP15HB-lane-a/tests/status/test_transitions.py:243), [tests/status/test_transitions.py](/home/stijnd/Documents/code/forks/spec-kitty/.worktrees/complexity-code-smell-remediation-01KP15HB-lane-a/tests/status/test_transitions.py:253), and [tests/status/test_transitions.py](/home/stijnd/Documents/code/forks/spec-kitty/.worktrees/complexity-code-smell-remediation-01KP15HB-lane-a/tests/status/test_transitions.py:259). This means the old API shape is still being preserved instead of fully migrating to the new context object.

Required remediation:
- Update every remaining `validate_transition(...)` call in `tests/status/test_transitions.py` to pass an explicit `GuardContext(...)`, even when it is empty.
- Re-run the targeted transition test suite after the migration.

**Issue 2: `validate_transition()` uses a shared `GuardContext()` default instance.**

`validate_transition()` is currently defined as `ctx: GuardContext = GuardContext()` at [src/specify_cli/status/transitions.py](/home/stijnd/Documents/code/forks/spec-kitty/.worktrees/complexity-code-smell-remediation-01KP15HB-lane-a/src/specify_cli/status/transitions.py:273). That creates one shared dataclass instance at import time and reuses it across calls. Even though the current implementation does not mutate `ctx`, this is a fragile boundary for a new public refactor record and undermines the goal of making the context object an explicit input. It should not ship with a shared mutable object default.

Required remediation:
- Change the signature to require an explicit `GuardContext`, or default `ctx` to `None` and instantiate a fresh `GuardContext()` inside the function.
- Keep the tests aligned with that explicit contract so future callers do not accidentally depend on a reused default instance.

Rebase warning:
- `WP02` depends on `WP01`. Because this review requests changes, the `WP02` lane owner should rebase after the fixes land.
