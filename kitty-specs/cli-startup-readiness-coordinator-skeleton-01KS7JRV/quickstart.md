# Quickstart: Using the Readiness Coordinator from a Subcommand

This quickstart shows the patterns downstream missions (WS2 auth, WS3 upgrade UX, WS5 tracker) will use to consume the coordinator's result from inside a subcommand handler.

---

## Reading the cached result

```python
import typer
from specify_cli.readiness import OutputPolicy, get_readiness


def my_subcommand(ctx: typer.Context) -> None:
    readiness = get_readiness(ctx)

    if not readiness.enabled:
        # Hosted mode is off. Fall back to local-only behavior.
        # Do NOT mention Teamspace in any output.
        run_local_only()
        return

    if readiness.output_policy == OutputPolicy.MACHINE_OUTPUT:
        # JSON / quiet path. Do not prompt. Emit structured output only.
        emit_json(...)
        return

    if readiness.output_policy == OutputPolicy.NON_INTERACTIVE:
        # Non-TTY / CI / help / version. Stable single-line stderr is OK.
        # Prompts are forbidden.
        emit_stderr_advisory(...)
        run_local_only()
        return

    # Interactive path. Prompts and rich rendering permitted.
    run_with_prompts()
```

---

## Triggering the coordinator (this is the root callback's job)

This mission writes the only call site that triggers the coordinator. Downstream missions do NOT call `evaluate_readiness`; they call `get_readiness`.

```python
# In src/specify_cli/cli/helpers.py callback() (after this mission's hook):
def callback(ctx: typer.Context) -> None:
    # ... banner block ...

    from specify_cli.readiness import evaluate_readiness
    evaluate_readiness(ctx)

    # ... maybe_emit_no_upgrade_notice block ...
```

The coordinator caches the result on `ctx.obj["readiness"]`. Subcommand handlers below the root callback read the cached result via `get_readiness(ctx)`.

---

## What this mission does NOT do (handed off to follow-ups)

- **Auth probe**: the `AuthStatus.NOT_CHECKED` value is a stub. WS2 wires `detect_logged_out_with_connected_teamspace` into the enabled path of `_evaluate_uncached`.
- **Upgrade UX prompts**: snooze cadence, "Always keep me up to date", "Not now", "Never ask again" — WS3 extends `_invoke_nag` with these.
- **Tracker registration alignment**: WS5 wires tracker commands through `get_readiness` so hosted tracker paths share the same suppression contract.

---

## Verifying the coordinator is wired

After this mission lands, the seam can be smoke-tested by:

```bash
# Hosted mode off — coordinator should be a no-op for all suppression rows.
unset SPEC_KITTY_ENABLE_SAAS_SYNC
spec-kitty --help 2>&1 | grep -i teamspace && echo "LEAK" || echo "ok"
spec-kitty --version 2>&1 | grep -i teamspace && echo "LEAK" || echo "ok"

# Hosted mode on — coordinator should run once per invocation.
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
spec-kitty --help 2>&1 | grep -i teamspace && echo "LEAK (this is OK for help in hosted mode if/when WS2 adds it)" || echo "ok"
```

The 7-row suppression-matrix test under `tests/readiness/test_coordinator_suppression_matrix.py` is the authoritative check.
