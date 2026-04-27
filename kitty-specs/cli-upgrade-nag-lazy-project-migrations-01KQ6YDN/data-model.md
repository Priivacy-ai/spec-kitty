# Data Model: CLI Upgrade Nag and Lazy Project Migration

**Mission**: `cli-upgrade-nag-lazy-project-migrations-01KQ6YDN`
**Phase**: 1 (Design)
**Inputs**: [`spec.md`](spec.md), [`research.md`](research.md)

This document defines the entities, value types, state machines, and validation rules for the new `compat/` package. Entities are described at the level needed for implementation; field-level Python types are illustrative.

---

## 1. Entities

### 1.1 `Plan`

The single immutable result of `compat.planner.plan(...)`. Every CLI surface consumes this.

```python
@dataclass(frozen=True)
class Plan:
    decision: Decision                          # see §1.2
    cli_status: CliStatus                       # see §1.3
    project_status: ProjectStatus               # see §1.4
    safety: Safety                              # see §1.5
    pending_migrations: tuple[MigrationStep, ...]   # see §1.6
    install_method: InstallMethod               # see §1.7
    upgrade_hint: UpgradeHint                   # see §1.8
    fr023_case: Fr023Case                       # see §1.9 — stable JSON token
    rendered_human: str                         # ready-for-stdout single message
    rendered_json: dict[str, Any]               # ready-for---json; matches contracts/compat-planner.json
```

Validation rules:
- `decision` and `fr023_case` are bijective when `decision != ALLOW`. (See §1.2 mapping.)
- `pending_migrations` is non-empty iff `decision == BLOCK_PROJECT_MIGRATION`.
- `rendered_human` is at most 4 lines (NFR-007).
- `rendered_json` validates against `contracts/compat-planner.json`.

### 1.2 `Decision`

Enum returned by the planner. Each value maps 1:1 to an exit-code policy and an FR-023 case.

| Decision | Meaning | Exit code | FR-023 case |
|---|---|---|---|
| `ALLOW` | Command may run, no nag. | passthrough | (none) |
| `ALLOW_WITH_NAG` | Command may run; print throttled nag first. | passthrough | `cli_update_available` |
| `BLOCK_PROJECT_MIGRATION` | Command refused; project too old. | 4 | `project_migration_needed` |
| `BLOCK_CLI_UPGRADE` | Command refused; project too new for CLI. | 5 | `project_too_new_for_cli` |
| `BLOCK_PROJECT_CORRUPT` | Command refused; project metadata unreadable. | 6 | `project_not_initialized` (when missing) or a corrupt-flagged variant |
| `BLOCK_INCOMPATIBLE_FLAGS` | User passed mutually-exclusive flags. | 2 | (none — usage error, surfaced via typer) |

(See R-08 for exit-code rationale.)

### 1.3 `CliStatus`

```python
@dataclass(frozen=True)
class CliStatus:
    installed_version: str                     # e.g. "2.0.11", from importlib.metadata
    latest_version: str | None                 # None when unknown / network suppressed
    latest_source: Literal["pypi", "none"]
    is_outdated: bool                          # True iff parse(latest) > parse(installed)
    fetched_at: datetime | None                # None when not fetched this run
```

Validation:
- `installed_version` is sanitised to `^[A-Za-z0-9.\-+]{1,64}$`.
- If `latest_version` is set, it is sanitised the same way.
- `is_outdated` uses `packaging.version.parse` comparison; never raises (returns `False` on parse error).

### 1.4 `ProjectStatus`

```python
@dataclass(frozen=True)
class ProjectStatus:
    state: ProjectState                        # see below
    project_root: Path | None                  # None when no project detected
    schema_version: int | None                 # None for no-project / unreadable
    min_supported: int                         # MIN_SUPPORTED_SCHEMA at runtime
    max_supported: int                         # MAX_SUPPORTED_SCHEMA at runtime
    metadata_error: str | None                 # human description when state == CORRUPT
```

`ProjectState` is an enum:

| State | Means |
|---|---|
| `NO_PROJECT` | No `.kittify/` found while walking up from cwd. |
| `UNINITIALIZED` | `.kittify/` exists but `metadata.yaml` is missing. |
| `LEGACY` | `metadata.yaml` exists but lacks `spec_kitty.schema_version`. |
| `STALE` | schema_version < MIN_SUPPORTED_SCHEMA. |
| `COMPATIBLE` | MIN ≤ schema_version ≤ MAX. |
| `TOO_NEW` | schema_version > MAX_SUPPORTED_SCHEMA. |
| `CORRUPT` | Parse error, oversized file, ownership refusal, alias-bomb, etc. |

### 1.5 `Safety`

```python
class Safety(Enum):
    SAFE = "safe"
    UNSAFE = "unsafe"
```

Returned by `compat.safety.classify(invocation)`. The planner combines `Safety` with `ProjectState` per §2.

### 1.6 `MigrationStep`

```python
@dataclass(frozen=True)
class MigrationStep:
    migration_id: str                          # e.g. "m_3_0_0_canonical_context"
    target_schema_version: int
    description: str                           # one-line human description
    files_modified: tuple[Path, ...] | None    # populated in dry-run when computable
```

Sourced from the existing `upgrade.registry`. The planner does not invent migrations; it lists what the registry already knows about.

> **Implementation note (DRIFT-3):**
> `target_schema_version` is currently **inferred** from the migration's semver `target_version`
> major component (e.g. `"3.0.0"` → `3`) rather than declared explicitly on the migration class.
> Future migrations may add an explicit `target_schema_version` attribute; the planner already
> reads it via `getattr(m, "target_schema_version", None)` with a fallback to the inference path.
>
> `files_modified` is currently always `null` because the migration registry does not expose
> this metadata at registration time. Future migrations may declare it; the JSON contract
> will surface it when available.

### 1.7 `InstallMethod`

```python
class InstallMethod(Enum):
    PIPX = "pipx"
    PIP_USER = "pip-user"
    PIP_SYSTEM = "pip-system"
    BREW = "brew"
    SYSTEM_PACKAGE = "system-package"
    SOURCE = "source"
    UNKNOWN = "unknown"
```

Detected once per process; cached on the planner (see R-03 for algorithm).

### 1.8 `UpgradeHint`

```python
@dataclass(frozen=True)
class UpgradeHint:
    install_method: InstallMethod
    command: str | None                        # e.g. "pipx upgrade spec-kitty-cli". None for SOURCE / UNKNOWN.
    note: str | None                           # multi-line manual instructions for SOURCE / UNKNOWN
```

Validation:
- `command` is sanitised (regex `^[A-Za-z0-9 .\-+_/=:]{1,128}$`); ANSI escapes / shell metacharacters are rejected (CHK028 / CHK031).
- Exactly one of `command` or `note` is non-None.

### 1.9 `Fr023Case`

```python
class Fr023Case(StrEnum):
    NONE                          = "none"                            # ALLOW
    CLI_UPDATE_AVAILABLE          = "cli_update_available"            # ALLOW_WITH_NAG
    PROJECT_MIGRATION_NEEDED      = "project_migration_needed"        # BLOCK_PROJECT_MIGRATION
    PROJECT_TOO_NEW_FOR_CLI       = "project_too_new_for_cli"         # BLOCK_CLI_UPGRADE
    PROJECT_NOT_INITIALIZED       = "project_not_initialized"         # ProjectState in {NO_PROJECT, UNINITIALIZED}
    PROJECT_METADATA_CORRUPT      = "project_metadata_corrupt"        # BLOCK_PROJECT_CORRUPT
    INSTALL_METHOD_UNKNOWN        = "install_method_unknown"          # any decision when InstallMethod == UNKNOWN
```

These tokens are **stable JSON tokens** (CHK057). They appear in `rendered_json["case"]` and in test golden files. Adding new cases requires a minor-version bump and CHANGELOG entry.

### 1.10 `NagCacheRecord`

```python
@dataclass(frozen=True)
class NagCacheRecord:
    cli_version_key: str                       # the installed CLI version when this record was written
    latest_version: str | None
    latest_source: Literal["pypi","none"]
    fetched_at: datetime                       # iso 8601 UTC
    last_shown_at: datetime | None
```

Persistence:
- Path: `<user_cache_dir>/spec-kitty/upgrade-nag.json`.
- Mode: `0o600` (POSIX). Parent dir `0o700`.
- Symlink-resistant read/write (R-02).
- Invalidated when the installed CLI version differs from `cli_version_key` on read (FR-025).
- Throttle predicate: `(now - last_shown_at) >= throttle_seconds`. Out-of-range throttle values fall back to default.

### 1.11 `LatestVersionResult`

Returned by every `LatestVersionProvider`. Never raises.

```python
@dataclass(frozen=True)
class LatestVersionResult:
    version: str | None
    source: Literal["pypi","none"]
    error: str | None                          # short non-PII description for debug logs
```

### 1.12 `Invocation`

```python
@dataclass(frozen=True)
class Invocation:
    command_path: tuple[str, ...]              # e.g. ("upgrade",) or ("agent","mission","branch-context")
    raw_args: tuple[str, ...]                  # post-typer-callback view of argv (excluding program name)
    is_help: bool
    is_version: bool
    flag_no_nag: bool
    env_ci: bool
    stdout_is_tty: bool
```

Built by `cli/helpers.py` once; passed to `compat.planner.plan(...)` and `compat.safety.classify(...)`.

---

## 2. State machine — planner's decision logic

Pseudocode for `compat.planner.plan(invocation, *, latest_version_provider, nag_cache, now)`:

```
1.  cli_status        := build_cli_status(latest_version_provider, nag_cache, invocation, now)
2.  project_status    := scan_project(invocation.cwd)
3.  safety            := compat.safety.classify(invocation)         # SAFE | UNSAFE
4.  install_method    := detect_install_method()
5.  upgrade_hint      := upgrade_hint_for(install_method, cli_status)
6.  decision          := decide(project_status, safety, cli_status)
7.  pending           := registry.pending_migrations(project_status) if decision == BLOCK_PROJECT_MIGRATION else ()
8.  fr023_case        := case_for(decision, project_status, install_method)
9.  rendered_human    := messages.render_human(fr023_case, ...)
10. rendered_json     := messages.render_json(fr023_case, ...)
11. return Plan(decision, cli_status, project_status, safety, pending, install_method, upgrade_hint, fr023_case, rendered_human, rendered_json)
```

`decide(...)` follows this table (rows checked top-to-bottom):

| `project_status.state` | `safety` | Decision |
|---|---|---|
| `CORRUPT` | * | `BLOCK_PROJECT_CORRUPT` |
| `TOO_NEW` | `UNSAFE` | `BLOCK_CLI_UPGRADE` |
| `STALE` or `LEGACY` | `UNSAFE` | `BLOCK_PROJECT_MIGRATION` |
| any | * | continue to nag / allow check |
| | | `ALLOW_WITH_NAG` if `cli_status.is_outdated` AND `not invocation.suppresses_nag()` AND throttle elapsed |
| | | `ALLOW` otherwise |

`invocation.suppresses_nag()` = `flag_no_nag OR env_ci OR (not stdout_is_tty) OR is_help OR is_version`.

`UNSAFE` + `COMPATIBLE` = `ALLOW` (with optional nag) — schema is fine, command can mutate.
`SAFE` + `STALE/TOO_NEW/CORRUPT` = `ALLOW` (with optional nag) — safe commands always pass.

---

## 3. Configuration surface

Two configuration knobs, env var > config file > default precedence.

| Key | Env var | Config file path / key | Default |
|---|---|---|---|
| Throttle window (seconds) | `SPEC_KITTY_NAG_THROTTLE_SECONDS` | `$XDG_CONFIG_HOME/spec-kitty/upgrade.yaml`, key `nag.throttle_seconds` | `86400` (24 h) |
| Disable nag entirely | `SPEC_KITTY_NO_NAG` (truthy) | `nag.enabled: false` | enabled |

Both are validated:
- Throttle: integer, `60 ≤ x ≤ 31_536_000`. Out-of-range → fall back to default + debug-level note.
- `SPEC_KITTY_NO_NAG`: string in `{1,true,yes,on}` → suppress.

Environment values always win over file values; flag values (`--no-nag`) always win over env.

---

## 4. Validation rules summary (cross-cutting)

| Rule | Source FR/NFR / checklist |
|---|---|
| YAML safe-load only for `.kittify/metadata.yaml`. | CHK019 |
| File-size cap of 256 KB before YAML parse. | CHK020 |
| `schema_version` must be `int` in `[0, 1000]`. | CHK021 |
| `latest_version` must match `^[A-Za-z0-9.\-+]{1,64}$`. | CHK016, CHK028 |
| `upgrade_hint.command` must match `^[A-Za-z0-9 .\-+_/=:]{1,128}$`. | CHK028, CHK031 |
| Cache file: `0o600`, parent dir `0o700`, no symlinks followed. | CHK006, CHK009, CHK010 |
| Latest-version provider: 2 s timeout, 1 MB body cap, no redirects, single hostname (`pypi.org`). | NFR-002, CHK011, CHK012, CHK013, CHK014 |
| User-Agent on outbound request: `spec-kitty-cli/<version>` (no PII). | CHK018, CHK048, CHK049 |
| CI/non-interactive predicate: `CI` env var ∪ `SPEC_KITTY_NO_NAG` ∪ `--no-nag` ∪ no-TTY. | A-007, R-07 |
| Unregistered command path → `Safety.UNSAFE`. | R-10, Q3 refinement |
| Throttle integer range `[60, 31_536_000]`. | CHK025, R-06 |
| `--yes` and `--force` are mutually compatible synonyms; neither bypasses schema-incompatibility blocks. | CHK037, A-006 |

---

## 5. Public API of `compat/`

The package's public surface (importable as `from specify_cli.compat import ...`):

```python
from specify_cli.compat import (
    Plan,
    Decision,
    Safety,
    Fr023Case,
    plan,                          # the planner entry point
    classify,                      # safety classification
    register_safety,               # for command modules that need mode predicates
    LatestVersionProvider,         # Protocol
    PyPIProvider,                  # default
    NoNetworkProvider,             # CI default
    NagCache,                      # for tests / advanced callers
    InstallMethod,
    detect_install_method,
)
```

Everything in `compat._adapters/` and `compat._detect/` is private (leading underscore, not re-exported).

---

## 6. Migration of existing call sites

| Existing symbol | Disposition | Notes |
|---|---|---|
| `specify_cli.migration.gate.check_schema_version` | shim → `compat.planner.plan(...)` then enforce decision | The typer callback in `cli/helpers.py` calls the planner directly; the gate function remains as a stable import path that delegates. |
| `specify_cli.migration.schema_version.REQUIRED_SCHEMA_VERSION` | deprecated alias of `MIN_SUPPORTED_SCHEMA` | Documented in CHANGELOG. |
| `specify_cli.migration.schema_version.check_compatibility` | kept; planner uses it via `_adapters.version_checker` | No behavior change. |
| `specify_cli.upgrade.detector.UpgradeDetector` | kept; planner uses it via `_adapters.detector` | No behavior change. |
| `specify_cli.core.version_checker.*` | kept; planner uses it via `_adapters.version_checker` | The legacy module continues to work as a thin re-export. |

A CI architectural test (`tests/architectural/test_compat_shims.py`) asserts that shim modules contain no logic beyond delegation, so no future change can put compatibility logic in two places.
