# Contract — `spec-kitty-tracker` public imports

**Owning WP**: WP05
**Backing FR**: FR-024, FR-031, C-008

## Frozen public surface

The following imports are the stable public surface of
`spec-kitty-tracker`. Breaking changes require a SemVer major bump and an
ADR.

```python
from spec_kitty_tracker import TrackerClient
from spec_kitty_tracker.models import (
    TrackerEvent,
    TrackerProject,
    TrackerWorkPackage,
)
from spec_kitty_tracker.errors import (
    TrackerAuthError,
    TrackerNotFound,
    TrackerSyncFailed,
)
```

Internal modules under `spec_kitty_tracker._internal.*` are NOT part of the
public surface and may change without notice.

## Bidirectional sync semantics (FR-031)

`TrackerClient.bidirectional_sync()` MUST:

1. Bound retries by `tracker.sync_max_retries` (default 5) with exponential
   backoff capped at `tracker.sync_max_backoff_seconds` (default 30).
2. On exhausted retries, raise `TrackerSyncFailed` with structured cause
   chain (HTTP status, body excerpt up to 2 KB, retry history).
3. NEVER block indefinitely. The total wall-clock cap is
   `tracker.sync_total_timeout_seconds` (default 300).
4. Emit a single user-facing failure line per invocation (paired with the
   token-refresh dedup behavior in FR-029).

## Auth transport adoption (FR-030)

`TrackerClient` MUST acquire its HTTP transport from
`spec-kitty/src/specify_cli/auth/transport.py:AuthenticatedClient`. It MUST
NOT instantiate `httpx.Client` directly. The architectural test enforces
this.

## Downstream certification

A candidate release of `spec-kitty-tracker` cannot be promoted to stable
until at least one downstream consumer (`spec-kitty`, `spec-kitty-saas`)
runs its integration suite green against the candidate. This rule is encoded
in `release.yml` workflow.
