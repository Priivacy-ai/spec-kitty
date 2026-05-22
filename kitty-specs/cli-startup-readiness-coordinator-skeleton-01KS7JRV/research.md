# Research: CLI Startup Readiness Coordinator Skeleton

This mission has no novel technology research surface; all technical choices are forced by the existing codebase. This document captures the design-rationale decisions, alternatives considered, and references.

---

## Decision 1: Coordinator owns the `_render_nag_if_needed` call site (inside vs. parallel)

**Decision**: The coordinator's `evaluate_readiness` function calls `_render_nag_if_needed(ctx)` directly. The inline call to `_render_nag_if_needed` from `callback()` in `helpers.py` is removed and replaced by a single call to `evaluate_readiness(ctx)`.

**Rationale**:
- Single source of ownership: there is exactly one place that decides when the nag fires (the coordinator) and exactly one function that renders it (`_render_nag_if_needed`).
- Future WS3 work (snooze cadence, "Always keep me up to date", "Not now", "Never ask again") plugs in by extending the coordinator's call to `_render_nag_if_needed`, NOT by adding a parallel render path.
- Avoids duplicate side effects (the nag cache update). If the coordinator shadowed the nag, the next mission would have to reason about two paths that both call into NagCache.

**Alternatives considered**:
- *Parallel render*: coordinator runs its own decision logic and emits its own rendering. Rejected — it would duplicate the suppression logic and the cache update.
- *Coordinator gates the nag*: coordinator checks suppression first, then calls `_render_nag_if_needed` only if not suppressed. Rejected — duplicates the gate that `_render_nag_if_needed` already does internally; any drift between the two checks becomes a silent bug. By calling unconditionally, we keep `_render_nag_if_needed` as the sole authority on whether the nag actually fires.

---

## Decision 2: `OutputPolicy` is a 3-bucket StrEnum (vs. a single boolean)

**Decision**: `OutputPolicy` has three values: `INTERACTIVE`, `NON_INTERACTIVE`, `MACHINE_OUTPUT`.

**Rationale**:
- WS2 (auth readiness) needs to distinguish "non-TTY but human is at the keyboard reading the script output later" from "JSON pipe — never put any human text on stdout". Today both are "suppressed" booleans; WS2 will render to stderr in the former case and emit nothing in the latter.
- WS3 (upgrade UX) needs the same distinction for the "Always keep me up to date" / "Not now" prompts: prompts are valid in interactive mode, optional in non-interactive mode (stderr line only), forbidden in machine-output mode.
- Storing the bucket on `ReadinessResult` once per invocation lets every subcommand consult one source of truth.

**Alternatives considered**:
- *Boolean `suppressed`*: same as today, but every downstream consumer would re-derive the 3-bucket distinction. Rejected — defeats the purpose of having a coordinator.
- *2-bucket (interactive vs. not)*: rejected for the same WS3 reason.
- *4-bucket (`INTERACTIVE`, `NON_INTERACTIVE_TTY`, `NON_INTERACTIVE_PIPE`, `MACHINE_OUTPUT`)*: rejected — over-engineered for this mission; can be widened later under the WS2/WS3 evolution.

---

## Decision 3: `_auth_recovery` import is module-scope on `coordinator.py`

**Decision**: `from specify_cli.cli.commands._auth_recovery import detect_logged_out_with_connected_teamspace  # noqa: F401` lives at module scope of `coordinator.py`.

**Rationale**:
- mypy --strict can then verify the symbol still exists and has the expected signature. If a future refactor renames it, the type-checker breaks the coordinator import immediately.
- Provides a grep target: future WS2 implementer searches for `# WS2: auth probe wiring` and finds the exact import + the exact call-site location.
- Import cost is acceptable: `_auth_recovery` only does stdlib imports at top level. (Heavy imports — `TokenManager`, sync routing, `_auth_login` — are all `lazy` inside `_auth_recovery`'s own functions.) Coordinator overhead bounded by NFR-001 (≤1ms p50 when hosted mode is disabled).

**Alternatives considered**:
- *Function-scope import*: defers import cost but loses mypy verification of the symbol's existence. Rejected — type-check loss outweighs the marginal startup-cost win.
- *Don't import at all*: rejected — WS2 hand-off becomes less obvious; the seam isn't typed.

---

## Decision 4: `_render_nag_if_needed` stays in `specify_cli.cli.helpers`

**Decision**: Do NOT move `_render_nag_if_needed` into the readiness package. It remains exported from `specify_cli.cli.helpers` (its current `__all__`).

**Rationale**:
- C-005: external dependents (including out-of-tree code we cannot see) may import from `specify_cli.cli.helpers`. Moving the function would break them.
- Coordinator imports `_render_nag_if_needed` lazily inside `_invoke_nag` to avoid a circular import (coordinator ← helpers ← coordinator would form a cycle if coordinator is imported by helpers' callback).

**Alternatives considered**:
- *Move to `readiness/nag.py`* and re-export from `helpers`: doable but increases diff scope. Rejected — out of scope per C-009.

---

## Decision 5: `ctx.obj` keying is the dict key `"readiness"`

**Decision**: When `ctx.obj` is a dict (the existing convention), the coordinator stores its result under the key `"readiness"`. Sibling key: `"compat_plan_result"` written by `_render_nag_if_needed`.

**Rationale**:
- Existing convention in `_render_nag_if_needed` already uses `ctx.obj` as a dict. Following the same pattern minimizes the cognitive load on reviewers.
- Distinct key prevents accidental overwrites between the two writers.
- A short, descriptive key keeps the public surface clear.

**Alternatives considered**:
- *Attribute on `ctx`*: typer's `Context` doesn't formally support arbitrary attributes; relying on attribute storage would be fragile.
- *Module-level cache keyed by `id(ctx)`*: rejected — leaks across CLI invocations in the same process (which happens in tests).

---

## Decision 6: Exception handling — coordinator never raises

**Decision**: Any exception inside `_evaluate_uncached` is caught in `evaluate_readiness` and replaced with `_NOOP_DISABLED`. The CLI cannot crash because of readiness logic.

**Rationale**:
- Defense in depth. The existing `_render_nag_if_needed` already swallows its own exceptions; preserving that posture at the coordinator level means a single broken inner function cannot ever break the CLI.
- Subcommands consuming `get_readiness(ctx)` always see a valid `ReadinessResult`. No `try/except` boilerplate at every call site.

**Alternatives considered**:
- *Let exceptions propagate*: rejected — would degrade `--help`/`--version` UX if the readiness logic broke.

---

## References

- Existing helpers: `/Users/robert/spec-kitty-dev/teamspace-readiness-plan-20260522-115958-YQygKW/spec-kitty/src/specify_cli/cli/helpers.py`
- Existing rollout gate: `/Users/robert/spec-kitty-dev/teamspace-readiness-plan-20260522-115958-YQygKW/spec-kitty/src/specify_cli/saas/rollout.py`
- Existing auth recovery: `/Users/robert/spec-kitty-dev/teamspace-readiness-plan-20260522-115958-YQygKW/spec-kitty/src/specify_cli/cli/commands/_auth_recovery.py`
- Existing CI-determinism tests: `/Users/robert/spec-kitty-dev/teamspace-readiness-plan-20260522-115958-YQygKW/spec-kitty/tests/cli_gate/test_ci_determinism.py`
- Tracking issue: [Priivacy-ai/spec-kitty#1093](https://github.com/Priivacy-ai/spec-kitty/issues/1093)
- Program plan: `/Users/robert/spec-kitty-dev/teamspace-readiness-plan-20260522-115958-YQygKW/start-me-start-here.md`
