# Contract: Internalized Runtime Public Surface

**Mission**: `shared-package-boundary-cutover-01KQ22DS`
**Module**: `specify_cli.next._internal_runtime`
**Status**: New module; surface frozen for this cutover.

This contract defines the exact public symbols the new internalized runtime
exposes. The surface mirrors what the CLI currently imports from
`spec_kitty_runtime` 0.4.3. WP01 builds this surface; WP02 cuts every CLI
production import over to it; WP03 architecturally enforces that no production
code path reaches into `spec_kitty_runtime` afterward.

---

## Public symbols (re-exported by `specify_cli.next._internal_runtime.__init__`)

```python
from specify_cli.next._internal_runtime import (
    DiscoveryContext,
    MissionPolicySnapshot,
    MissionRunRef,
    NextDecision,
    NullEmitter,
    next_step,
    provide_decision_answer,
    start_mission_run,
)
```

| Symbol | Kind | Replaces |
|--------|------|----------|
| `DiscoveryContext` | dataclass | `spec_kitty_runtime.DiscoveryContext` |
| `MissionPolicySnapshot` | dataclass | `spec_kitty_runtime.MissionPolicySnapshot` |
| `MissionRunRef` | dataclass | `spec_kitty_runtime.MissionRunRef` |
| `NextDecision` | dataclass | `spec_kitty_runtime.NextDecision` |
| `NullEmitter` | class | `spec_kitty_runtime.NullEmitter` |
| `next_step` | callable | `spec_kitty_runtime.next_step` (callers usually alias as `runtime_next_step`) |
| `provide_decision_answer` | callable | `spec_kitty_runtime.provide_decision_answer` |
| `start_mission_run` | callable | `spec_kitty_runtime.start_mission_run` |

## Sub-module symbols

### `specify_cli.next._internal_runtime.schema`

| Symbol | Kind | Replaces |
|--------|------|----------|
| `ActorIdentity` | dataclass | `spec_kitty_runtime.schema.ActorIdentity` |
| `load_mission_template_file` | callable | `spec_kitty_runtime.schema.load_mission_template_file` |
| `MissionRuntimeError` | exception | `spec_kitty_runtime.schema.MissionRuntimeError` |

### `specify_cli.next._internal_runtime.engine`

| Symbol | Kind | Replaces |
|--------|------|----------|
| `_read_snapshot` | callable | `spec_kitty_runtime.engine._read_snapshot` |
| (module reference; `runtime_bridge.py` imports `engine` as a module) | module | `spec_kitty_runtime.engine` |

The `_read_snapshot` underscore prefix is preserved because every existing
caller already imports it by that name. Renaming would expand the diff surface
without architectural benefit.

### `specify_cli.next._internal_runtime.planner`

| Symbol | Kind | Replaces |
|--------|------|----------|
| `plan_next` | callable | `spec_kitty_runtime.planner.plan_next` |

---

## Behavior contract

For every symbol above, the post-cutover behavior MUST be identical to the
pre-cutover behavior of `spec_kitty_runtime` 0.4.3 against the reference fixture
mission, byte-for-byte where output is JSON, and structurally where output is
Python objects.

WP01 captures golden snapshots:

- `tests/fixtures/runtime_parity/snapshot_next_step.json` — output of
  `next_step(...)` against the reference mission at three sequential steps.
- `tests/fixtures/runtime_parity/snapshot_start_mission_run.json` — output of
  `start_mission_run(...)` for the fixture.
- `tests/fixtures/runtime_parity/snapshot_provide_decision_answer.json` —
  output of `provide_decision_answer(...)` after a planted decision moment.

The internalized implementation passes all three with byte-equal JSON modulo
documented timestamp / path normalization (the same normalization
`runtime-mission-execution-extraction-01KPDYGW` uses).

---

## Internalization strategy

The internalized runtime is **derived from**, not **copied verbatim from**, the
upstream `spec-kitty-runtime` 0.4.3 source. WP01 imports the runtime mission's
public-API inventory (from
`spec-kitty-runtime/kitty-specs/runtime-standalone-package-retirement-01KQ20Z8/`)
as the authoritative list of symbols and behaviors to internalize. Behaviors
not on the inventory are not internalized; if a CLI caller uses such a behavior,
the inventory is wrong and a delta is filed back to the runtime mission rather
than expanding scope locally.

Implementation detail freedom: the internalized code MAY restructure the
sub-module layout, rename internal helpers, or simplify private code paths
**as long as** the public surface above is preserved and the parity snapshots
pass.

---

## Forbidden patterns

- The internalized runtime MUST NOT import `spec_kitty_runtime` at any layer
  (top-level, lazy, or conditional). The whole point is independence.
- The internalized runtime MUST NOT depend on `rich.*` or `typer.*` directly;
  presentation belongs to the CLI layer (consistent with the layer rules in
  `tests/architectural/test_layer_rules.py`).
- External Python importers MUST NOT reach into
  `specify_cli.next._internal_runtime` directly; the underscore prefix marks it
  internal. The public CLI surface for "next step" remains
  `specify_cli.next.runtime_bridge` and the `spec-kitty next` command.
