# Contract — `spec-kitty-events` envelope

**Owning WP**: WP05
**Backing FR**: FR-022, FR-023, FR-024
**Authority**: `spec_kitty_events.*` public imports at the version resolved
by `pyproject.toml` + `uv.lock`.

## Required envelope fields (per resolved version)

The contract test reads the resolved version of `spec-kitty-events` and
loads its public schema. The fields below are the **stable minimum** that the
test asserts against; the snapshot file under
`tests/contract/snapshots/spec-kitty-events-<version>.json` carries the full
authoritative shape.

| Field | Type | Stability |
|-------|------|-----------|
| `event_id` | str (ULID) | stable across versions |
| `event_type` | str (kebab-case) | stable across versions |
| `event_version` | int | stable across versions |
| `emitted_at` | str (ISO 8601 UTC) | stable across versions |
| `actor` | str | stable across versions |
| `mission_id` | str (ULID) | stable across versions |
| `payload` | dict | shape governed by `event_type` × `event_version` |

## Test-suite pinning rule

Tests under `spec-kitty/tests/contract/test_events_envelope_*.py` MUST:

1. Resolve the actual `spec-kitty-events` version from `uv.lock` via
   `tomllib`. If the lockfile is missing, fall back to
   `importlib.metadata.version("spec-kitty-events")` and emit a warning.
2. Load the snapshot at
   `tests/contract/snapshots/spec-kitty-events-<resolved-version>.json`.
3. Assert that emitted envelopes match the snapshot field-by-field for every
   event_type currently produced by `spec-kitty`.

If `spec-kitty-events` is bumped in `pyproject.toml`/`uv.lock` and the
snapshot is missing, the test fails with a structured message including:

- The resolved version found.
- The expected snapshot path.
- A pointer to `scripts/snapshot_events_envelope.py`.

## Public-import freeze

The following imports are the stable public surface. A breaking change
requires a SemVer major bump and a written ADR:

```python
from spec_kitty_events import EventEnvelope
from spec_kitty_events.types import EventType, EventVersion
from spec_kitty_events.validators import validate_envelope
```

`tests/architectural/test_events_tracker_public_imports.py` asserts no caller
in `spec-kitty` reaches into `spec_kitty_events._internal.*`.

## Mission-review gate

`/spec-kitty-mission-review` MUST run `pytest tests/contract/ -v` and treat
failures as hard blockers (FR-023). The mission cannot be accepted with red
contract tests.
