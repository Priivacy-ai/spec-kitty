# Data Model: Centralize installed CLI runtime + remediation planning

**Mission**: `installed-runtime-domain-01KW0NR6`

---

## §1 — InstalledCliRuntime (FR-001)

```python
# src/specify_cli/compat/_detect/runtime.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

@dataclass(frozen=True)
class UvRequirement:
    """A single requirement entry from a uv receipt.

    Fields mirror the uv receipt TOML schema. Only `name` is required;
    all others are optional depending on the requirement source type.
    """
    name: str
    specifier: str | None = None
    directory: str | None = None
    editable: str | None = None
    path: str | None = None
    git: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class InstalledCliRuntime:
    """Immutable snapshot of a running spec-kitty-cli installation.

    CHK032 / NFR-001: `detect_runtime()` MUST NEVER raise; every probe
    is wrapped in try/except with silent fall-through to defaults.

    Invariant: `receipt_path` is None whenever `install_method` is not
    UV_TOOL, SOURCE, or UNKNOWN; `requirements` is `()` whenever
    `receipt_path` is None.
    """
    install_method: InstallMethod                    # from _detect/install_method.py
    executable: str                                  # sys.executable value
    receipt_path: Path | None                        # absolute path to uv-receipt.toml, or None
    tool_dir: Path | None                            # UV tool env parent dir, or None
    bin_dir: Path | None                             # bin dir carrying the spec-kitty entrypoint, or None
    is_default_tool_dir: bool | None                 # None when not a uv-tool install
    is_default_bin_dir: bool | None                  # None when not a uv-tool install
    python: str | None                               # python version override from receipt, or None
    requirements: tuple[UvRequirement, ...]          # empty tuple when receipt unavailable
    package_source: PackageSource                    # derived provenance enum
    platform: Literal["posix", "windows"]            # platform at runtime
    safe_for_auto_upgrade: bool                      # True iff install_method in _SAFE_AUTO_UPGRADE_METHODS
```

### PackageSource enum

```python
class PackageSource(StrEnum):
    """Derived package provenance from the uv receipt requirements entry."""
    PYPI_SPECIFIER = "pypi-specifier"   # { name = "...", specifier = "..." }
    GIT = "git"                          # { git = "..." }
    URL = "url"                          # { url = "..." }
    DIRECTORY = "directory"              # { directory = "..." }
    EDITABLE = "editable"                # { editable = "..." }
    PATH = "path"                        # { path = "..." }
    UNKNOWN = "unknown"                  # receipt unavailable or no spec-kitty entry
```

### Field invariants

| Field | When None / empty |
|-------|-----------------|
| `receipt_path` | Non-uv-tool installs; malformed/missing receipt |
| `tool_dir` | Non-uv-tool installs |
| `bin_dir` | Non-uv-tool installs; receipt has no entrypoints |
| `is_default_tool_dir` | Non-uv-tool installs (None, not False) |
| `is_default_bin_dir` | Non-uv-tool installs (None, not False) |
| `python` | Receipt has no `tool.python` override |
| `requirements` | Always a tuple (empty, never None) |

---

## §2 — RemediationCommand (FR-004, FR-005)

```python
# src/specify_cli/compat/remediation.py
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from enum import StrEnum
from typing import Literal
import re
import shlex

_COMMAND_RE = re.compile(r"^[A-Za-z0-9 .\-+_/=:]{1,128}$")  # CHK028

class RemediationIntent(StrEnum):
    """What the remediation command is attempting to do."""
    UPGRADE = "upgrade"
    REINSTALL_WITH_TEST = "reinstall_with_test"
    MANUAL_GUIDANCE = "manual_guidance"


@dataclass(frozen=True)
class RemediationCommand:
    """A fully specified remediation action.

    NFR-004: Instances are constructed by `plan_remediation()`, a pure
    function (no I/O). Construction itself does NOT raise on invalid
    content — validation happens in `render()` (NFR-002).

    Invariant: if `intent == MANUAL_GUIDANCE`, `argv` is None and
    `note` is non-None. For UPGRADE and REINSTALL_WITH_TEST, `argv`
    is non-None when the install method supports automated remediation.
    """
    intent: RemediationIntent
    argv: tuple[str, ...] | None                # subprocess-ready args, or None for manual
    env: Mapping[str, str]                       # env vars to prepend (e.g. UV_TOOL_DIR=...)
    note: str | None                             # human-readable note, or None

    def render(self, platform: Literal["posix", "windows"]) -> str:
        """Return a CHK028-validated, env-prefixed, platform-quoted command string.

        Raises:
            ValueError: if the composed string does not match CHK028, or
                if `argv` is None (caller must check `intent` first).
        """
        ...
```

### render() platform behavior

| Platform | Env prefix format | Arg quoting |
|----------|------------------|-------------|
| `"posix"` | `KEY=shlex.quote(value) ` | `shlex.quote(arg)` |
| `"windows"` | `$env:KEY='powershell-quoted-value'; ` | No additional quoting for argv |

PowerShell quoting for `"windows"`: single-quote wrapping with `'` escaped as `''` (matching `_powershell_quote()` in `review/__init__.py` at line 325).

---

## §3 — UvReceiptReader (FR-007)

```python
# src/specify_cli/compat/_adapters/uv_receipt.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class UvReceiptResult:
    """All fields extractable from a uv-receipt.toml for a given executable.

    NFR-003: Any filesystem error, TOML parse error, or schema mismatch
    results in None for the affected field, never a raise.
    """
    receipt_path: Path | None
    tool_dir: Path | None
    bin_dir: Path | None
    is_default_tool_dir: bool | None
    is_default_bin_dir: bool | None
    python: str | None
    requirements: tuple[UvRequirement, ...]
    package_source: PackageSource


class UvReceiptReader:
    """Single authoritative uv-receipt.toml parser.

    Replaces the three independent implementations in:
    - cli/commands/review/__init__.py (Set A)
    - readiness/upgrade_ux.py (Set B)
    - compat/_detect/install_method.py (detection-only probe, not a parsing path)
    """

    @staticmethod
    def read_for_executable(executable: str) -> UvReceiptResult:
        """Read and parse the uv receipt for the running executable.

        Never raises (NFR-003). Returns a result with all fields None/empty
        on any error.
        """
        ...

    @staticmethod
    def exists_for(exe_path: Path) -> bool:
        """Return True if a valid uv receipt exists for this executable.

        Used by the detect_install_method() detection chain as a light probe
        (does not parse the full receipt). Never raises.
        """
        ...
```

---

## §4 — UvToolInstallationVerified Event (FR-012)

```python
# src/specify_cli/compat/install_events.py
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class VerificationConfidence(StrEnum):
    """Confidence level for post-upgrade installation verification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class UvToolInstallationVerified:
    """Event emitted after a uv-tool upgrade attempt completes.

    Emitted by `_default_upgrade_runner` in upgrade_ux.py when
    install_method == UV_TOOL, regardless of outcome.

    NFR-007: No PII. receipt_path is included for auditability
    but the event consumer MUST NOT log or transmit it.

    Confidence derivation:
    - HIGH: exit_code == 0 AND entrypoint_match == True
    - MEDIUM: exit_code == 0 AND entrypoint_match == False
    - LOW: exit_code != 0
    """
    receipt_path: Path | None        # path to uv-receipt.toml post-upgrade
    entrypoint_match: bool           # True if spec-kitty entrypoint is present post-upgrade
    package_binding: str             # package name + specifier from receipt, or "unknown"
    confidence: VerificationConfidence
```

---

## §5 — UpgradeAttemptRecord (FR-013)

```python
# src/specify_cli/compat/history.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class UpgradeAttemptOutcome(StrEnum):
    """Outcome of a single upgrade attempt."""
    SUCCESS = "success"
    FAILURE = "failure"
    ABORTED = "aborted"


@dataclass(frozen=True)
class UpgradeAttemptRecord:
    """A single upgrade attempt entry persisted to the history store.

    NFR-007: No PII. No user paths, project slugs, hostnames, or machine IDs.
    attempt_id is a ULID (time-sortable, collision-resistant, no identity).
    """
    attempt_id: str                  # ULID (26 chars), used as idempotency key
    timestamp: datetime              # UTC datetime of attempt completion
    install_method: InstallMethod    # which install method was used
    intent: str                      # RemediationIntent value
    outcome: UpgradeAttemptOutcome
    exit_code: int | None            # subprocess exit code, or None if aborted
    target_version: str | None       # target version if known, else None
```

---

## §6 — SQLite History Store Schema

File: `~/.cache/spec-kitty/upgrade-history.db` (resolved via `platformdirs.user_cache_dir("spec-kitty")` + `"upgrade-history.db"`).

```sql
CREATE TABLE IF NOT EXISTS upgrade_attempts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id        TEXT    NOT NULL UNIQUE,   -- ULID; idempotency key
    timestamp_utc     TEXT    NOT NULL,           -- ISO-8601 UTC, e.g. "2026-06-26T12:00:00+00:00"
    install_method    TEXT    NOT NULL,           -- InstallMethod str value
    intent            TEXT    NOT NULL,           -- RemediationIntent str value
    outcome           TEXT    NOT NULL,           -- 'success' | 'failure' | 'aborted'
    exit_code         INTEGER,                    -- nullable
    target_version    TEXT,                       -- nullable
    created_at        REAL    NOT NULL            -- Unix timestamp float; used for index ordering
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_upgrade_attempts_attempt_id
    ON upgrade_attempts(attempt_id);

CREATE INDEX IF NOT EXISTS idx_upgrade_attempts_method_created
    ON upgrade_attempts(install_method, created_at DESC);
```

**WAL mode**: The store opens connections with `PRAGMA journal_mode=WAL` to allow concurrent reads while a write is in progress (NFR-006).

**Retention policy (NFR-005)**: On every write, a `DELETE` trims rows beyond the last 200 per `install_method`, keeping the table bounded:

```sql
DELETE FROM upgrade_attempts
WHERE id NOT IN (
    SELECT id FROM upgrade_attempts
    WHERE install_method = ?
    ORDER BY created_at DESC
    LIMIT 200
)
AND install_method = ?;
```

**`INSERT OR IGNORE`**: The `UNIQUE` index on `attempt_id` ensures a second `INSERT` of the same ULID is a no-op, providing write-idempotency.

---

## §7 — UpgradeAttemptStore query interface (FR-015)

```python
class UpgradeAttemptStore:
    """Persistent history store for upgrade attempts.

    Thread-safe for concurrent reads. Writes use WAL mode for
    concurrent-write safety (NFR-006).
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialise. Uses `default_history_db_path()` when db_path is None."""
        ...

    def append(self, record: UpgradeAttemptRecord) -> None:
        """Append a record. Best-effort; swallows all errors (fail-safe).

        Uses INSERT OR IGNORE — duplicate attempt_id is a silent no-op.
        Runs retention trim after each successful write.
        """
        ...

    def is_idempotent(self, attempt: UpgradeAttemptRecord) -> bool:
        """Return True if a successful attempt with same install_method + target_version exists.

        Fail-open: returns False on any store error.
        """
        ...

    def consecutive_failure_count(
        self,
        install_method: InstallMethod,
        *,
        window_seconds: int = 300,
    ) -> int:
        """Return the count of consecutive failures in the recent window.

        Fail-open: returns 0 on any store error.
        Query: the most-recent N records (up to 100) for this install_method
        within window_seconds, counting from the tail until a non-failure.
        """
        ...

    def last_success_timestamp(
        self, install_method: InstallMethod
    ) -> datetime | None:
        """Return UTC datetime of the most recent successful attempt, or None.

        Fail-open: returns None on any store error.
        """
        ...


def default_history_db_path() -> Path:
    """Resolve the default history store path via platformdirs.

    Resolution order:
    1. SPEC_KITTY_HISTORY_DB_PATH env var override.
    2. platformdirs.user_cache_dir("spec-kitty") / "upgrade-history.db".
    3. Manual XDG fallback (same pattern as NagCache._resolve_cache_dir).
    """
    ...
```
