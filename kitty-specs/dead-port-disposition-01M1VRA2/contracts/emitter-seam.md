# Contract: Runtime Emitter Seam (factory, registry, null implementation)

**Module**: `src/runtime/next/_internal_runtime/events.py` (re-exported by `_internal_runtime/emitter.py`)
**Consumers**: `runtime_bridge.py` (2 construction sites), `runtime_bridge_engine.py` (types only), future E3 producer, tests.

## Public surface

```python
class RuntimeEventEmitter(Protocol):        # unchanged: eight emit_*(payload) -> None
class NullEmitter:                          # existing
    def __init__(self, correlation_id: str = "") -> None                  # unchanged signature
    @classmethod
    def for_mission(cls, *, feature_dir: Path, mission_slug: str, mission_type: str) -> "NullEmitter"
    def seed_from_snapshot(self, snapshot: Any) -> None                    # no-op

def runtime_emitter_for_mission(*, feature_dir: Path, mission_slug: str, mission_type: str) -> RuntimeEventEmitter
def register_runtime_emitter_factory(factory: Callable[..., RuntimeEventEmitter]) -> None
def reset_runtime_emitter_factory() -> None
```

`__all__` gains: `"runtime_emitter_for_mission"`, `"register_runtime_emitter_factory"`, `"reset_runtime_emitter_factory"` (both in `events.py` and the `emitter.py` shim).

## Behavioral rules

| # | Rule | Test |
|---|---|---|
| S1 | `runtime_emitter_for_mission` returns a `NullEmitter` when no factory is registered. | `test_internal_runtime_coverage` (new) |
| S2 | When `SPEC_KITTY_SYNC_MINIMAL_IMPORT` is truthy (per `is_truthy`), it returns a `NullEmitter` even if a factory is registered, and does not call the registered factory. Env is read at call time. | same |
| S3 | When a factory is registered and the env gate is off, the registered callable is invoked with the same keyword arguments and its return is passed through unmodified. | same |
| S4 | `reset_runtime_emitter_factory()` restores S1. | same |
| S5 | `NullEmitter.for_mission` resolves `mission_id` via `specify_cli.mission_metadata.resolve_mission_identity(feature_dir).mission_id`; any exception degrades to `None`. Never raises. | same |
| S6 | Every `NullEmitter` method, including `seed_from_snapshot`, is a no-op and never raises. | existing NullEmitter tests + new |
| S7 | Exactly one class named `RuntimeEventEmitter` exists under `src/runtime/next/`; `runtime.next.event_emitter` is not importable. | `tests/architectural/test_runtime_emitter_seam.py` (new) |
| S8 | The bridge obtains the seam only by calling `runtime_emitter_for_mission` (imported by name), never by constructing a concrete class. | same guard (source grep) |

## Registration contract for a future producer (E3, out of scope here)

A producer registers once at import tail, mirroring `status/adapters.py:364-365`:
```python
if not is_truthy(os.environ.get("SPEC_KITTY_SYNC_MINIMAL_IMPORT")):
    register_runtime_emitter_factory(MyProducer.for_mission)
```
The registered callable must accept `feature_dir`, `mission_slug`, `mission_type` as keywords and return an object satisfying the Protocol. It *should* also provide `seed_from_snapshot(snapshot)`; the bridge calls it inside a `try` and logs on failure.

## Test substitution contract

Tests replace the seam by patching the **name on the bridge module**:
```python
monkeypatch.setattr(runtime_bridge, "runtime_emitter_for_mission", lambda **_: fake)
```
or by wrapping it (oracle spy pattern). Tests that exercise the registry call `register_runtime_emitter_factory` and must `reset_runtime_emitter_factory()` in teardown.
