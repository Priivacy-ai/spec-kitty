"""Compatibility planner for spec-kitty CLI upgrade-nag and project-migration gate.

This module implements:
- All core dataclasses (T021): Decision, Fr023Case, ProjectState, CliStatus,
  ProjectStatus, MigrationStep, Plan, Invocation.
- ``decide()`` — pure truth-table function (T023).
- ``plan()`` — the main entry point that assembles a Plan (T024).

Design notes
------------
- ``decide()`` is pure (no I/O).
- ``plan()`` body is wrapped in a fail-closed try/except that returns a
  BLOCK_PROJECT_CORRUPT Plan on any unexpected exception.
- ``Invocation.from_argv()`` is a best-effort parser; it never raises.
"""

from __future__ import annotations

import contextlib
import os
import sys
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from collections.abc import Callable

# StrEnum is stdlib 3.11+
from enum import StrEnum

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# CI environment helper (single source of truth for all call sites)
# ---------------------------------------------------------------------------


def is_ci_env() -> bool:
    """Return True if the current environment indicates CI / non-interactive mode.

    Used by the planner, the typer callback, and the gate. Single source of truth
    so all call sites agree on what 'CI' means.
    """
    raw = os.environ.get("CI", "")
    return bool(raw and raw.strip().lower() not in ("0", "false", "no", "off", ""))


# ---------------------------------------------------------------------------
# Migration registry auto-load guard
# ---------------------------------------------------------------------------

_REGISTRY_AUTOLOADED = False


def _ensure_registry_loaded() -> None:
    """Auto-discover migrations once per process, fail-open on any error."""
    global _REGISTRY_AUTOLOADED
    if _REGISTRY_AUTOLOADED:
        return
    try:
        from specify_cli.upgrade.migrations import auto_discover_migrations

        auto_discover_migrations()
    except Exception:  # noqa: BLE001 — fail-open: empty pending_migrations is preferable to crash
        pass
    finally:
        _REGISTRY_AUTOLOADED = True


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Decision(StrEnum):
    """Planner decision; maps 1:1 to an exit-code policy and an FR-023 case."""

    ALLOW = "ALLOW"
    ALLOW_WITH_NAG = "ALLOW_WITH_NAG"
    BLOCK_PROJECT_MIGRATION = "BLOCK_PROJECT_MIGRATION"
    BLOCK_CLI_UPGRADE = "BLOCK_CLI_UPGRADE"
    BLOCK_PROJECT_CORRUPT = "BLOCK_PROJECT_CORRUPT"
    BLOCK_INCOMPATIBLE_FLAGS = "BLOCK_INCOMPATIBLE_FLAGS"


class Fr023Case(StrEnum):
    """Stable JSON token for the FR-023 case.

    See data-model §1.9.  These values appear in ``rendered_json["case"]``
    and golden test files.  Adding a new case requires a minor-version bump.
    """

    NONE = "none"
    CLI_UPDATE_AVAILABLE = "cli_update_available"
    PROJECT_MIGRATION_NEEDED = "project_migration_needed"
    PROJECT_TOO_NEW_FOR_CLI = "project_too_new_for_cli"
    PROJECT_NOT_INITIALIZED = "project_not_initialized"
    PROJECT_METADATA_CORRUPT = "project_metadata_corrupt"
    INSTALL_METHOD_UNKNOWN = "install_method_unknown"


class ProjectState(StrEnum):
    """State of the project detected by the planner.

    See data-model §1.4.
    """

    NO_PROJECT = "no_project"
    UNINITIALIZED = "uninitialized"
    LEGACY = "legacy"
    STALE = "stale"
    COMPATIBLE = "compatible"
    TOO_NEW = "too_new"
    CORRUPT = "corrupt"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CliStatus:
    """Snapshot of the CLI's version status.

    Attributes:
        installed_version: Version string from importlib.metadata.
        latest_version: Latest version from provider, or None.
        latest_source: Where the latest version came from.
        is_outdated: True iff parse(latest) > parse(installed).
        fetched_at: When the latest lookup completed, or None.
    """

    installed_version: str
    latest_version: str | None
    latest_source: Literal["pypi", "none"]
    is_outdated: bool
    fetched_at: datetime | None


@dataclass(frozen=True)
class ProjectStatus:
    """Snapshot of the project's schema compatibility state.

    Attributes:
        state: Computed ProjectState.
        project_root: Absolute path to project root, or None.
        schema_version: Integer from .kittify/metadata.yaml, or None.
        min_supported: MIN_SUPPORTED_SCHEMA at this build.
        max_supported: MAX_SUPPORTED_SCHEMA at this build.
        metadata_error: Short human description when state == CORRUPT.
    """

    state: ProjectState
    project_root: Path | None
    schema_version: int | None
    min_supported: int
    max_supported: int
    metadata_error: str | None


@dataclass(frozen=True)
class MigrationStep:
    """One step in the pending migration plan.

    Attributes:
        migration_id: Stable slug (e.g. ``"m_3_0_0_canonical_context"``).
        target_schema_version: Schema version this migration targets.
        description: One-line human description.
        files_modified: Files this migration would touch, or None.
    """

    migration_id: str
    target_schema_version: int
    description: str
    files_modified: tuple[Path, ...] | None


@dataclass(frozen=True)
class Plan:
    """Immutable result of ``plan()``.

    Every CLI surface consumes this object.  See data-model §1.1.

    Attributes:
        decision: Planner decision.
        cli_status: CLI version snapshot.
        project_status: Project schema snapshot.
        safety: Safety classification of the invocation.
        pending_migrations: Ordered migration steps (non-empty iff
            decision == BLOCK_PROJECT_MIGRATION).
        install_method: Detected install method.
        upgrade_hint: Upgrade hint for the detected install method.
        fr023_case: Stable FR-023 JSON token.
        exit_code: Exit code the CLI should use.
        rendered_human: Ready-for-stdout single message (≤4 lines).
        rendered_json: Ready-for-``--json``; matches compat-planner.json.
    """

    decision: Decision
    cli_status: CliStatus
    project_status: ProjectStatus
    safety: Any  # Safety enum from compat.safety (avoid circular import)
    pending_migrations: tuple[MigrationStep, ...]
    install_method: Any  # InstallMethod enum from compat._detect
    upgrade_hint: Any  # UpgradeHint dataclass from compat.upgrade_hint
    fr023_case: Fr023Case
    exit_code: int
    rendered_human: str
    rendered_json: dict[str, Any]


@dataclass(frozen=True)
class Invocation:
    """Parsed representation of a single CLI invocation.

    Attributes:
        command_path: Tuple of path segments, e.g. ``("upgrade",)``.
        raw_args: Post-parse argv excluding the program name.
        is_help: ``--help`` / ``-h`` was present.
        is_version: ``--version`` was present.
        flag_no_nag: ``--no-nag`` was present.
        env_ci: ``CI`` env var is set and truthy.
        stdout_is_tty: ``sys.stdout.isatty()`` at invocation time.
    """

    command_path: tuple[str, ...]
    raw_args: tuple[str, ...]
    is_help: bool
    is_version: bool
    flag_no_nag: bool
    env_ci: bool
    stdout_is_tty: bool

    # ------------------------------------------------------------------
    # Classmethods
    # ------------------------------------------------------------------

    @classmethod
    def from_argv(cls, argv: list[str] | None = None) -> Invocation:
        """Best-effort parse of an argv list into an Invocation.

        Parses the first non-flag positional tokens as ``command_path``.
        All remaining tokens become ``raw_args``.

        Args:
            argv: Argument list to parse.  Defaults to ``sys.argv[1:]``.

        Returns:
            A new :class:`Invocation`.  Never raises.
        """
        if argv is None:
            argv = sys.argv[1:]

        args = list(argv)
        is_help = "--help" in args or "-h" in args
        is_version = "--version" in args or "-v" in args
        flag_no_nag = "--no-nag" in args
        env_ci = is_ci_env()

        try:
            stdout_is_tty = sys.stdout.isatty()
        except Exception:  # noqa: BLE001
            stdout_is_tty = False

        # Extract command path: leading tokens that don't start with '-'
        command_parts: list[str] = []
        rest: list[str] = []
        passed_command = False
        for token in args:
            if not passed_command and not token.startswith("-"):
                command_parts.append(token)
            else:
                passed_command = True
                rest.append(token)

        return cls(
            command_path=tuple(command_parts),
            raw_args=tuple(rest),
            is_help=is_help,
            is_version=is_version,
            flag_no_nag=flag_no_nag,
            env_ci=env_ci,
            stdout_is_tty=stdout_is_tty,
        )

    # ------------------------------------------------------------------
    # Predicates
    # ------------------------------------------------------------------

    def suppresses_nag(self) -> bool:
        """Return True if nag output should be suppressed for this invocation.

        Suppression conditions (any one is sufficient):
        - ``--no-nag`` flag is present.
        - ``CI`` environment variable is set.
        - stdout is not a TTY.
        - ``--help`` or ``--version`` is present.
        """
        return self.flag_no_nag or self.env_ci or (not self.stdout_is_tty) or self.is_help or self.is_version

    def suppresses_network(self) -> bool:
        """Return True if network requests should be suppressed for this invocation.

        Used to select NoNetworkProvider in ``plan()`` defaults.

        Suppression conditions:
        - ``CI`` environment variable is set.
        - stdout is not a TTY.
        - ``--no-nag`` flag is present.
        """
        return self.env_ci or (not self.stdout_is_tty) or self.flag_no_nag


# ---------------------------------------------------------------------------
# Pure decision function (T023)
# ---------------------------------------------------------------------------

_EXIT_CODE_MAP: dict[Decision, int] = {
    Decision.ALLOW: 0,
    Decision.ALLOW_WITH_NAG: 0,
    Decision.BLOCK_PROJECT_MIGRATION: 4,
    Decision.BLOCK_CLI_UPGRADE: 5,
    Decision.BLOCK_PROJECT_CORRUPT: 6,
    Decision.BLOCK_INCOMPATIBLE_FLAGS: 2,
}


def decide(
    project: ProjectStatus,
    safety: Any,
    cli: CliStatus,
    invocation: Invocation,
) -> tuple[Decision, Fr023Case]:
    """Pure truth-table function implementing data-model §2.

    Rows are checked top-to-bottom; the first matching row wins.

    Args:
        project: Project status snapshot.
        safety: Safety classification from ``compat.safety.classify``.
        cli: CLI version snapshot.
        invocation: Current invocation context.

    Returns:
        A ``(Decision, Fr023Case)`` tuple.
    """
    from specify_cli.compat.safety import Safety

    state = project.state

    # Row 1: CORRUPT (any safety) → block
    if state == ProjectState.CORRUPT:
        return Decision.BLOCK_PROJECT_CORRUPT, Fr023Case.PROJECT_METADATA_CORRUPT

    # Row 2: TOO_NEW + UNSAFE → block CLI upgrade
    if state == ProjectState.TOO_NEW and safety == Safety.UNSAFE:
        return Decision.BLOCK_CLI_UPGRADE, Fr023Case.PROJECT_TOO_NEW_FOR_CLI

    # Row 3: STALE or LEGACY + UNSAFE → block project migration
    if state in (ProjectState.STALE, ProjectState.LEGACY) and safety == Safety.UNSAFE:
        return Decision.BLOCK_PROJECT_MIGRATION, Fr023Case.PROJECT_MIGRATION_NEEDED

    # Row 4: UNINITIALIZED or NO_PROJECT + UNSAFE → allow with PROJECT_NOT_INITIALIZED label.
    # Decision stays ALLOW (do not block — the user can still init or use --cli);
    # the case label lets JSON consumers distinguish this from a generic ALLOW.
    if state in (ProjectState.NO_PROJECT, ProjectState.UNINITIALIZED) and safety == Safety.UNSAFE:
        return Decision.ALLOW, Fr023Case.PROJECT_NOT_INITIALIZED

    # Row 5: nag / allow check
    if cli.is_outdated and not invocation.suppresses_nag():
        return Decision.ALLOW_WITH_NAG, Fr023Case.CLI_UPDATE_AVAILABLE

    return Decision.ALLOW, Fr023Case.NONE


# ---------------------------------------------------------------------------
# plan() entry point (T024)
# ---------------------------------------------------------------------------

_MAX_METADATA_BYTES = 262_144  # 256 KiB


def _get_schema_bounds() -> tuple[int, int]:
    """Return (min_supported, max_supported) schema version bounds.

    Defensively reads from ``specify_cli.migration.schema_version``.
    Falls back gracefully if WP07 has not added the new attrs yet.
    """
    try:
        from specify_cli.migration import schema_version as sv

        min_s = getattr(sv, "MIN_SUPPORTED_SCHEMA", None)
        max_s = getattr(sv, "MAX_SUPPORTED_SCHEMA", None)

        if min_s is None or max_s is None:
            # Fall back to REQUIRED_SCHEMA_VERSION
            req = getattr(sv, "REQUIRED_SCHEMA_VERSION", None)
            if req is not None:
                return (int(req), int(req))
            return (0, 999)

        return (int(min_s), int(max_s))

    except Exception:  # noqa: BLE001
        return (0, 999)


def _get_installed_version() -> str:
    """Return the installed spec-kitty-cli version, or 'unknown'."""
    try:
        from importlib.metadata import version

        return version("spec-kitty-cli")
    except Exception:  # noqa: BLE001
        return "unknown"


def _version_is_outdated(installed: str, latest: str | None) -> bool:
    """Return True iff parse(latest) > parse(installed).

    Never raises; returns False on any parse error.
    """
    if latest is None:
        return False
    try:
        from packaging.version import Version

        return Version(latest) > Version(installed)
    except Exception:  # noqa: BLE001
        return False


def _scan_project(
    project_root_resolver: Callable[[Path], Path | None],
    min_supported: int,
    max_supported: int,
) -> ProjectStatus:
    """Scan the project state by walking from cwd upward.

    Args:
        project_root_resolver: Callable(start: Path) → Path | None.
        min_supported: Minimum supported schema version.
        max_supported: Maximum supported schema version.

    Returns:
        A :class:`ProjectStatus`.
    """
    try:
        project_root = project_root_resolver(Path.cwd())
    except Exception:  # noqa: BLE001
        return ProjectStatus(
            state=ProjectState.NO_PROJECT,
            project_root=None,
            schema_version=None,
            min_supported=min_supported,
            max_supported=max_supported,
            metadata_error=None,
        )

    if project_root is None:
        return ProjectStatus(
            state=ProjectState.NO_PROJECT,
            project_root=None,
            schema_version=None,
            min_supported=min_supported,
            max_supported=max_supported,
            metadata_error=None,
        )

    metadata_path = project_root / ".kittify" / "metadata.yaml"

    # No .kittify/ or missing metadata → UNINITIALIZED
    if not metadata_path.exists():
        return ProjectStatus(
            state=ProjectState.UNINITIALIZED,
            project_root=project_root,
            schema_version=None,
            min_supported=min_supported,
            max_supported=max_supported,
            metadata_error=None,
        )

    # Size guard: refuse > 256 KiB (CHK020)
    try:
        file_size = metadata_path.stat().st_size
    except OSError as exc:
        return ProjectStatus(
            state=ProjectState.CORRUPT,
            project_root=project_root,
            schema_version=None,
            min_supported=min_supported,
            max_supported=max_supported,
            metadata_error=f"stat failed: {exc}",
        )

    if file_size > _MAX_METADATA_BYTES:
        return ProjectStatus(
            state=ProjectState.CORRUPT,
            project_root=project_root,
            schema_version=None,
            min_supported=min_supported,
            max_supported=max_supported,
            metadata_error="oversized",
        )

    # Read schema version
    try:
        from specify_cli.migration.schema_version import get_project_schema_version

        schema_version = get_project_schema_version(project_root)
    except Exception as exc:  # noqa: BLE001
        return ProjectStatus(
            state=ProjectState.CORRUPT,
            project_root=project_root,
            schema_version=None,
            min_supported=min_supported,
            max_supported=max_supported,
            metadata_error=f"read error: {exc}",
        )

    # No schema_version field → LEGACY
    if schema_version is None:
        return ProjectStatus(
            state=ProjectState.LEGACY,
            project_root=project_root,
            schema_version=None,
            min_supported=min_supported,
            max_supported=max_supported,
            metadata_error=None,
        )

    # Validate integer in [0, 1000] (CHK021)
    if not isinstance(schema_version, int) or not (0 <= schema_version <= 1000):
        return ProjectStatus(
            state=ProjectState.CORRUPT,
            project_root=project_root,
            schema_version=None,
            min_supported=min_supported,
            max_supported=max_supported,
            metadata_error=f"schema_version out of range: {schema_version!r}",
        )

    # Map to ProjectState
    if schema_version < min_supported:
        state = ProjectState.STALE
    elif schema_version > max_supported:
        state = ProjectState.TOO_NEW
    else:
        state = ProjectState.COMPATIBLE

    return ProjectStatus(
        state=state,
        project_root=project_root,
        schema_version=schema_version,
        min_supported=min_supported,
        max_supported=max_supported,
        metadata_error=None,
    )


def _pending_migrations_for(project: ProjectStatus) -> tuple[MigrationStep, ...]:
    """Return pending migration steps for a STALE/LEGACY project.

    Returns an empty tuple if the registry does not expose the needed data
    (WP07 may not have landed yet).

    Args:
        project: Project status snapshot.

    Returns:
        Tuple of :class:`MigrationStep` instances.
    """
    _ensure_registry_loaded()
    try:
        from specify_cli.upgrade.registry import MigrationRegistry

        migrations = MigrationRegistry.get_all()
        steps: list[MigrationStep] = []
        for m in migrations:
            try:
                from packaging.version import Version

                target_v = Version(m.target_version)
                # Only include schema-changing migrations targeting > current schema
                current = project.schema_version or 0
                # Convert packaging version to schema int best-effort
                # (use major.minor.micro → schema int mapping via description)
                schema_int: int | None = getattr(m, "target_schema_version", None)
                if schema_int is None:
                    # Attempt to infer: if target version > REQUIRED_SCHEMA_VERSION
                    schema_int = int(target_v.major) if target_v else 0

                if isinstance(schema_int, int) and schema_int > current:
                    files_raw = getattr(m, "files_modified", None)
                    files: tuple[Path, ...] | None = None
                    if files_raw is not None:
                        try:
                            files = tuple(Path(f) for f in files_raw)
                        except Exception:  # noqa: BLE001
                            files = None

                    steps.append(
                        MigrationStep(
                            migration_id=str(m.migration_id),
                            target_schema_version=schema_int,
                            description=str(getattr(m, "description", "")),
                            files_modified=files,
                        )
                    )
            except Exception:  # noqa: BLE001, S112
                continue
        return tuple(steps)
    except Exception:  # noqa: BLE001
        return ()


def plan(
    invocation: Invocation,
    *,
    latest_version_provider: Any = None,
    nag_cache: Any = None,
    config: Any = None,
    now: datetime | None = None,
    project_root_resolver: Callable[[Path], Path | None] | None = None,
) -> Plan:
    """Build the compatibility plan for this invocation.

    This is the main entry point for the planner.  The entire body is wrapped
    in a fail-closed try/except that returns a BLOCK_PROJECT_CORRUPT Plan on
    any unexpected exception.

    Args:
        invocation: The parsed invocation context.
        latest_version_provider: Override for the version provider.
            Defaults to :class:`NoNetworkProvider` when
            ``invocation.suppresses_network()`` else :class:`PyPIProvider`.
        nag_cache: Override for the nag cache.
            Defaults to ``NagCache.default()``.
        config: Override for the upgrade configuration.
            Defaults to ``UpgradeConfig.load()``.
        now: Override for the current UTC datetime (for testing).
            Defaults to ``datetime.now(timezone.utc)``.
        project_root_resolver: Override for the project root resolver.
            Defaults to ``locate_project_root`` from
            ``specify_cli.core.project_resolver``.

    Returns:
        A :class:`Plan`.  Never raises.
    """
    try:
        return _plan_impl(
            invocation,
            latest_version_provider=latest_version_provider,
            nag_cache=nag_cache,
            config=config,
            now=now,
            project_root_resolver=project_root_resolver,
        )
    except Exception:  # noqa: BLE001 — fail-closed
        # Build the minimal fail-closed plan
        from specify_cli.compat._detect.install_method import InstallMethod
        from specify_cli.compat.safety import Safety
        from specify_cli.compat.upgrade_hint import build_upgrade_hint

        try:
            install_method = InstallMethod.UNKNOWN
            upgrade_hint = build_upgrade_hint(install_method)
        except Exception:  # noqa: BLE001
            from specify_cli.compat.upgrade_hint import UpgradeHint

            install_method = InstallMethod.UNKNOWN
            upgrade_hint = UpgradeHint(
                install_method=InstallMethod.UNKNOWN,
                command=None,
                note="Install method unknown.",
            )

        minimal_cli = CliStatus(
            installed_version=_get_installed_version(),
            latest_version=None,
            latest_source="none",
            is_outdated=False,
            fetched_at=None,
        )
        minimal_project = ProjectStatus(
            state=ProjectState.CORRUPT,
            project_root=None,
            schema_version=None,
            min_supported=0,
            max_supported=999,
            metadata_error="planner_error",
        )
        human = "Spec Kitty internal error in compatibility planner; refusing to run unsafe commands."
        rendered_json: dict[str, Any] = {
            "schema_version": 1,
            "case": Fr023Case.PROJECT_METADATA_CORRUPT,
            "decision": Decision.BLOCK_PROJECT_CORRUPT,
            "exit_code": 6,
            "cli": {
                "installed_version": minimal_cli.installed_version,
                "latest_version": None,
                "latest_source": "none",
                "is_outdated": False,
                "fetched_at": None,
            },
            "project": {
                "state": ProjectState.CORRUPT,
                "project_root": None,
                "schema_version": None,
                "min_supported": 0,
                "max_supported": 999,
                "metadata_error": "planner_error",
            },
            "safety": Safety.UNSAFE,
            "install_method": install_method,
            "upgrade_hint": {
                "install_method": install_method,
                "command": upgrade_hint.command,
                "note": upgrade_hint.note,
            },
            "pending_migrations": [],
            "rendered_human": human,
        }
        return Plan(
            decision=Decision.BLOCK_PROJECT_CORRUPT,
            cli_status=minimal_cli,
            project_status=minimal_project,
            safety=Safety.UNSAFE,
            pending_migrations=(),
            install_method=install_method,
            upgrade_hint=upgrade_hint,
            fr023_case=Fr023Case.PROJECT_METADATA_CORRUPT,
            exit_code=6,
            rendered_human=human,
            rendered_json=rendered_json,
        )


def _plan_impl(
    invocation: Invocation,
    *,
    latest_version_provider: Any,
    nag_cache: Any,
    config: Any,
    now: datetime | None,
    project_root_resolver: Callable[[Path], Path | None] | None,
) -> Plan:
    """Inner implementation of plan() — may raise; caller wraps in try/except."""
    from specify_cli.compat._detect.install_method import detect_install_method
    from specify_cli.compat.cache import NagCache, NagCacheRecord
    from specify_cli.compat.config import UpgradeConfig
    from specify_cli.compat.provider import (
        FakeLatestVersionProvider,  # noqa: F401
        NoNetworkProvider,
        PyPIProvider,
    )
    from specify_cli.compat.safety import classify
    from specify_cli.compat.upgrade_hint import build_upgrade_hint

    # Defaults
    if now is None:
        now = datetime.now(UTC)

    if config is None:
        config = UpgradeConfig.load()

    if nag_cache is None:
        nag_cache = NagCache.default()

    if project_root_resolver is None:
        from specify_cli.core.project_resolver import locate_project_root

        project_root_resolver = locate_project_root

    if latest_version_provider is None:
        latest_version_provider = NoNetworkProvider() if invocation.suppresses_network() else PyPIProvider()  # noqa: SIM108

    # --- Step 1: Build CliStatus ---
    installed_version = _get_installed_version()

    # Fresh-cache fast path (NFR-001): read cache first; only call the provider
    # if the version data in the cache is stale or absent.  This avoids a
    # network round-trip on every interactive invocation.
    #
    # Two separate predicates are used:
    # - has_fresh_data: "should we skip the provider call?" (uses fetched_at)
    # - is_fresh: "should we suppress the nag display?" (uses last_shown_at)
    #
    # The distinction matters for the "fully up-to-date" case: when
    # installed == latest there is no nag to show, so last_shown_at stays None
    # forever.  The old is_fresh predicate would return False (never shown →
    # not fresh), causing every invocation to hit the provider even though the
    # cached version data was recent.  has_fresh_data checks fetched_at instead
    # and correctly returns True in that case (FIX C, P2).
    cache_record: NagCacheRecord | None = nag_cache.read()

    # Invalidate cache if CLI version changed (FR-025)
    if cache_record is not None and cache_record.cli_version_key != installed_version:
        cache_record = None

    # Check whether the cached VERSION DATA is fresh enough to trust (skip provider).
    cache_data_fresh = NagCache.has_fresh_data(
        cache_record,
        throttle_seconds=config.throttle_seconds,
        now=now,
        current_cli_version=installed_version,
    )

    # Separately, check whether the NAG should be suppressed (throttle display).
    cache_is_fresh = NagCache.is_fresh(
        cache_record,
        throttle_seconds=config.throttle_seconds,
        now=now,
        current_cli_version=installed_version,
    )

    if cache_data_fresh:
        # Cache data is fresh — trust it; no network call.
        latest_version: str | None = cache_record.latest_version if cache_record is not None else None
        cli_source: Literal["pypi", "none"] = cache_record.latest_source if cache_record is not None else "none"
        fetched_at: datetime | None = None  # not fetched this run
    else:
        # Cache stale or missing — fetch from provider.
        latest_result = latest_version_provider.get_latest("spec-kitty-cli")
        fetched_at = now if latest_result.source == "pypi" else None
        latest_version = latest_result.version

        # If we got a version from the provider, update the cache (preserve last_shown_at).
        if latest_result.source == "pypi" and latest_version is not None:
            new_record = NagCacheRecord(
                cli_version_key=installed_version,
                latest_version=latest_version,
                latest_source="pypi",
                fetched_at=now,
                last_shown_at=cache_record.last_shown_at if cache_record is not None else None,
            )
            with contextlib.suppress(Exception):
                nag_cache.write(new_record)
        elif cache_record is not None and cache_record.latest_version is not None:
            # Provider returned nothing useful — fall back to cached version.
            latest_version = cache_record.latest_version
            fetched_at = None  # not fetched this run

        cli_source = latest_result.source if latest_result.source == "pypi" else "none"
        if cache_record is not None and latest_result.source != "pypi":
            cli_source = cache_record.latest_source

    is_outdated = _version_is_outdated(installed_version, latest_version)

    # Respect config.nag_enabled: if nag disabled globally, treat as not outdated
    if not config.nag_enabled:
        is_outdated = False

    # Fresh cache means nag was recently shown — suppress.
    if cache_is_fresh:
        is_outdated = False

    cli_status = CliStatus(
        installed_version=installed_version,
        latest_version=latest_version,
        latest_source=cli_source,
        is_outdated=is_outdated,
        fetched_at=fetched_at,
    )

    # --- Step 2: Scan project ---
    min_supported, max_supported = _get_schema_bounds()
    project_status = _scan_project(project_root_resolver, min_supported, max_supported)

    # --- Step 3: Classify safety ---
    safety = classify(invocation)

    # --- Step 4: Detect install method ---
    install_method = detect_install_method()

    # --- Step 5: Build upgrade hint ---
    upgrade_hint = build_upgrade_hint(install_method)

    # --- Step 6: Decide ---
    decision, fr023_case = decide(project_status, safety, cli_status, invocation)

    # --- Step 7/8: Override fr023_case for UNKNOWN install method ---
    from specify_cli.compat._detect.install_method import InstallMethod

    if install_method == InstallMethod.UNKNOWN and decision in (Decision.ALLOW_WITH_NAG, Decision.BLOCK_CLI_UPGRADE, Decision.BLOCK_PROJECT_MIGRATION):
        fr023_case = Fr023Case.INSTALL_METHOD_UNKNOWN

    # --- Step 9: Pending migrations ---
    pending_migrations = _pending_migrations_for(project_status) if decision == Decision.BLOCK_PROJECT_MIGRATION else ()  # noqa: SIM108

    # --- Step 10: Exit code ---
    exit_code = _EXIT_CODE_MAP.get(decision, 0)

    # --- Step 11/12: Render messages (deferred import to avoid circular) ---
    from specify_cli.compat import messages as _messages

    # Assemble partial plan for rendering (rendered_human / rendered_json populated after)
    partial_plan = Plan(
        decision=decision,
        cli_status=cli_status,
        project_status=project_status,
        safety=safety,
        pending_migrations=pending_migrations,
        install_method=install_method,
        upgrade_hint=upgrade_hint,
        fr023_case=fr023_case,
        exit_code=exit_code,
        rendered_human="",
        rendered_json={},
    )

    rendered_human = _messages.render_human(partial_plan)
    rendered_json = _messages.render_json(partial_plan)

    # --- Step 13: Return final Plan ---
    return Plan(
        decision=decision,
        cli_status=cli_status,
        project_status=project_status,
        safety=safety,
        pending_migrations=pending_migrations,
        install_method=install_method,
        upgrade_hint=upgrade_hint,
        fr023_case=fr023_case,
        exit_code=exit_code,
        rendered_human=rendered_human,
        rendered_json=rendered_json,
    )


__all__ = [
    "Decision",
    "Fr023Case",
    "ProjectState",
    "CliStatus",
    "ProjectStatus",
    "MigrationStep",
    "Plan",
    "Invocation",
    "decide",
    "plan",
    "is_ci_env",
]
