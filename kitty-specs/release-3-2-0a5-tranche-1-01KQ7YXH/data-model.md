# Data Model: 3.2.0a5 Tranche 1

This tranche has minimal data-model surface — no databases, no migrations
beyond what already exists, no new persisted entities. The "entities" below
are the file-shaped contracts that this tranche enforces or modifies.

## E1 — Project metadata file (`.kittify/metadata.yaml`)

Authoritative source for the compat-planner gate
(`src/specify_cli/compat/planner.py`). Read by every `spec-kitty agent ...`
command.

| Field | Type | Cardinality | Owner | Invariant |
|-------|------|-------------|-------|-----------|
| `spec_kitty.version` | string (PEP 440) | 1 | `ProjectMetadata` dataclass | Must equal CLI's bundled version after a successful `spec-kitty upgrade`. |
| `spec_kitty.schema_version` | int | 1 | `_stamp_schema_version` (raw YAML round-trip) | Must equal `MIN_SUPPORTED_SCHEMA == MAX_SUPPORTED_SCHEMA` (currently `3`) after a successful upgrade. **Invariant violated today** by FR-002. |
| `spec_kitty.initialized_at` | ISO-8601 timestamp | 1 | `ProjectMetadata.save` | Set once at `init`. Must not be overwritten by `upgrade`. |
| `spec_kitty.last_upgraded_at` | ISO-8601 timestamp | 1 | `ProjectMetadata.save` | Updated on every successful `upgrade` run. |
| `environment.python_version` | string | 1 | `ProjectMetadata.save` | Recorded at init/upgrade for diagnostics. |
| `environment.platform` | string | 1 | `ProjectMetadata.save` | As above. |
| `environment.platform_version` | string | 1 | `ProjectMetadata.save` | As above. |
| `migrations.applied[]` | list of migration records | 0..N | `ProjectMetadata.record_migration` | Append-only ledger. |

**FR-002 invariant restored after fix**: After
`spec-kitty upgrade --yes` returns exit code 0, all of the following must
hold simultaneously: `spec_kitty.version` matches the CLI version,
`spec_kitty.schema_version == REQUIRED_SCHEMA_VERSION`, and a subsequent
`spec-kitty agent mission branch-context --json` exits 0 (no
`PROJECT_MIGRATION_NEEDED`).

## E2 — Bulk-edit occurrence map (`occurrence_map.yaml`)

Required by DIRECTIVE_035 because `meta.json::change_mode == "bulk_edit"`.
Materialized at the same level as `plan.md`. Schema:

```yaml
mission_id: <ULID>
mission_slug: <slug>
target_string: "/spec-kitty.checklist"
related_strings:
  - "checklist.md"   # template / snapshot filename
  - "spec-kitty.checklist.md"  # generated agent copy filename
generated_at: <ISO-8601>
categories:
  code_symbols: { remove: [...], keep: [...] }
  import_paths: { remove: [...], keep: [...] }
  filesystem_paths: { remove: [...], keep: [...] }
  serialized_keys: { remove: [...], keep: [...] }
  cli_commands: { remove: [...], keep: [...] }
  user_facing_strings: { remove: [...], keep: [...] }
  tests_fixtures: { remove: [...], keep: [...] }
  logs_telemetry: { remove: [...], keep: [...] }
totals:
  remove_count: 27
  keep_count: 6
```

Every `remove` entry is a `{path, line, reason}` triple; every `keep`
entry is the same plus an explicit `keep_reason`. Implementing agents
MUST produce a diff that matches the occurrence map exactly — anything
extra is gated.

## E3 — Diagnostic dedup state (in-process)

New module `src/specify_cli/diagnostics/dedup.py` (introduced by FR-009
work). Does not persist to disk.

```python
# Module shape (illustrative, not normative):

import contextvars
from typing import Final

_REPORTED: Final[contextvars.ContextVar[set[str]]] = contextvars.ContextVar(
    "spec_kitty_diagnostics_reported",
    default=frozenset(),
)

def report_once(cause_key: str) -> bool:
    """Return True if `cause_key` has not been reported yet in this
    invocation, and record it as reported. Return False otherwise.
    Safe under asyncio (ContextVar)."""

def reset_for_invocation() -> None:
    """Reset the dedup state. Called by tests in `setup`; not called by
    production code paths (one CLI invocation == one dedup window)."""
```

| Field | Type | Cardinality | Lifecycle |
|-------|------|-------------|-----------|
| `cause_key` | string | unbounded set per invocation | Set on first report; never cleared inside an invocation. |

The keys are short stable identifiers like
`"sync.unauthenticated"`, `"auth.token_refresh_failed"`. The exact key
schema is finalized during WP06 implementation.

## E4 — Atexit success flag (in-process)

A single module-level boolean (or threading.Event) carried by
`src/specify_cli/diagnostics/dedup.py` or a sibling
`shutdown_state.py`:

```python
def mark_invocation_succeeded() -> None:
    """Called by JSON-payload-emitting commands after their final write."""

def invocation_succeeded() -> bool:
    """Read by atexit handlers in sync/background.py and sync/runtime.py
    to decide whether to log shutdown warnings (when False) or skip them
    (when True)."""
```

## Entities NOT introduced

This tranche does NOT introduce:

- New mission types
- New mission step contracts
- New CLI subcommands
- New persisted artifacts under `kitty-specs/<mission>/`
- New rows in any database (no databases involved)
