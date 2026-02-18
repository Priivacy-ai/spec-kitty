# Mission-Next Compatibility Matrix

## Canonical Pins

1. `spec-kitty-events==2.3.1`
2. `spec-kitty-runtime @ git+https://github.com/Priivacy-ai/spec-kitty-runtime.git@v0.2.0a0`

These pins are required to keep the deterministic `next()` loop contract aligned across CLI, runtime, and events.

## Why These Versions

1. `spec-kitty-events==2.3.1` publishes canonical mission-next payload models, reducer semantics, JSON schemas, and replay fixtures used for cross-repo conformance.
2. `spec-kitty-runtime@v0.2.0a0` implements the breaking payload-object emitter API that matches the mission-next contracts in `spec-kitty-events` v2.3.1.
3. `spec-kitty` relies on both for runtime-backed `next` behavior:
   - deterministic run state transitions,
   - canonical event payload shapes,
   - replay compatibility with mission-next fixture streams.

## Contract Expectations

1. CLI must route `next` planning through runtime, including `--result failed|blocked`.
2. Runtime must emit canonical mission-next event names/payloads only.
3. Replay fixture `mission-next-replay-full-lifecycle` must continue to reduce successfully in `spec-kitty` integration tests.
