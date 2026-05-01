"""Helpers for canonical selector resolution and deprecated aliases.

Mission handle resolution
-------------------------
``resolve_mission_handle`` wraps :func:`~specify_cli.context.mission_resolver.resolve_mission`
and translates resolver exceptions into user-facing error messages.  Call it
after obtaining a raw ``--mission`` / ``--feature`` flag value and before
performing any kitty-specs directory access.

Example::

    from specify_cli.cli.selector_resolution import resolve_mission_handle

    resolved = resolve_mission_handle(raw_handle, repo_root, json_mode=False)
    feature_dir = resolved.feature_dir
    mission_slug = resolved.mission_slug
"""

from __future__ import annotations

import json as _json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
import typer
from rich.console import Console

from specify_cli.context.errors import MissingIdentityError
from specify_cli.context.mission_resolver import (
    AmbiguousHandleError,
    MissionNotFoundError,
    ResolvedMission,
    resolve_mission,
)
from specify_cli.core.paths import require_explicit_feature

_err_console = Console(stderr=True)
_warned: set[tuple[int, str, str]] = set()
_direct_invocation_counter: int = 0


@dataclass(frozen=True, slots=True)
class SelectorResolution:
    """Resolved selector value plus metadata about how it was chosen."""

    canonical_value: str
    canonical_flag: str
    alias_used: bool
    alias_flag: str | None
    warning_emitted: bool

    def __post_init__(self) -> None:
        if self.alias_used and not self.alias_flag:
            raise ValueError("alias_flag is required when alias_used=True")
        if not self.alias_used and self.alias_flag is not None:
            raise ValueError("alias_flag must be None when alias_used=False")
        if not self.canonical_value.strip():
            raise ValueError("canonical_value must be non-empty")


def _doc_path_for(alias_flag: str) -> str:
    return {
        "--feature": "docs/migration/feature-flag-deprecation.md",
        "--mission": "docs/migration/mission-type-flag-deprecation.md",
    }[alias_flag]


def _emit_deprecation_warning(
    canonical_flag: str,
    alias_flag: str,
    suppress_env_var: str,
) -> bool:
    """Emit a single warning per CLI invocation for one canonical/alias pair.

    Inside a click invocation we key on the click context id so the same
    canonical/alias pair only warns once per command. Outside a click context
    (direct programmatic calls) we use a monotonically increasing counter
    instead of ``id(object())`` — the latter can collide because Python may
    reuse memory for short-lived temporaries, which would suppress the warning
    on the second back-to-back call.
    """

    global _direct_invocation_counter
    ctx = click.get_current_context(silent=True)
    if ctx is not None:
        invocation_id = id(ctx)
    else:
        _direct_invocation_counter += 1
        invocation_id = _direct_invocation_counter
    pair = (invocation_id, canonical_flag, alias_flag)
    if pair in _warned:
        return False
    if os.environ.get(suppress_env_var) == "1":
        return False

    _warned.add(pair)
    _err_console.print(
        f"[yellow]Warning:[/yellow] {alias_flag} is deprecated; "
        f"use {canonical_flag}. See: {_doc_path_for(alias_flag)}"
    )
    return True


def _normalize_selector(value: Any | None) -> str | None:
    """Normalize a parsed selector value to a non-empty string or ``None``.

    Typer-decorated command functions can leak ``OptionInfo`` sentinels when
    they are called directly from wrapper commands. Treat non-string values as
    unset so selector resolution fails deterministically instead of crashing on
    ``.strip()``.
    """

    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def resolve_selector(
    *,
    canonical_value: str | None,
    canonical_flag: str,
    alias_value: str | None,
    alias_flag: str,
    suppress_env_var: str,
    command_hint: str | None = None,
) -> SelectorResolution:
    """Resolve a canonical selector plus one deprecated alias."""

    canonical_norm = _normalize_selector(canonical_value)
    alias_norm = _normalize_selector(alias_value)

    if canonical_norm is None and alias_norm is None:
        try:
            require_explicit_feature(None, command_hint=command_hint or f"{canonical_flag} <value>")
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        raise typer.BadParameter("Selector value is required.")

    if canonical_norm and alias_norm and canonical_norm != alias_norm:
        raise typer.BadParameter(
            f"Conflicting selectors: {canonical_flag}={canonical_norm!r} "
            f"and {alias_flag}={alias_norm!r} were both provided with different values. "
            f"{alias_flag} is a hidden deprecated alias for {canonical_flag}; pass only {canonical_flag}."
        )

    if canonical_norm and alias_norm:
        warning_emitted = _emit_deprecation_warning(canonical_flag, alias_flag, suppress_env_var)
        return SelectorResolution(
            canonical_value=canonical_norm,
            canonical_flag=canonical_flag,
            alias_used=True,
            alias_flag=alias_flag,
            warning_emitted=warning_emitted,
        )

    if canonical_norm:
        return SelectorResolution(
            canonical_value=canonical_norm,
            canonical_flag=canonical_flag,
            alias_used=False,
            alias_flag=None,
            warning_emitted=False,
        )

    warning_emitted = _emit_deprecation_warning(canonical_flag, alias_flag, suppress_env_var)
    return SelectorResolution(
        canonical_value=alias_norm or "",
        canonical_flag=canonical_flag,
        alias_used=True,
        alias_flag=alias_flag,
        warning_emitted=warning_emitted,
    )


# ---------------------------------------------------------------------------
# Mission handle resolver (T036 / T037 / T038)
# ---------------------------------------------------------------------------


def resolve_mission_handle(
    handle: str,
    repo_root: Path,
    *,
    json_mode: bool = False,
) -> ResolvedMission:
    """Resolve a user-supplied mission handle to a canonical :class:`~specify_cli.context.mission_resolver.ResolvedMission`.

    Accepted input forms (priority order):

    1. Full 26-char ULID ``mission_id``
    2. 8-char ``mid8`` prefix
    3. Full slug with numeric prefix (e.g. ``"083-foo-bar"``)
    4. Human slug without prefix (e.g. ``"foo-bar"``)
    5. Numeric prefix alone (e.g. ``"083"``)

    On success the :class:`~specify_cli.context.mission_resolver.ResolvedMission`
    is returned.  On failure the appropriate error message is printed to *stderr*
    and :func:`sys.exit` is called with exit code 2.

    Args:
        handle: Raw flag value from ``--mission`` or ``--feature``.
        repo_root: Absolute path to the repository root.
        json_mode: When ``True``, error payloads are emitted as JSON (for
            callers that pass ``--json``).

    Returns:
        The uniquely resolved mission.

    Raises:
        SystemExit(2): On ``AmbiguousHandleError``, ``MissionNotFoundError``, or
            ``MissingIdentityError``.
    """
    try:
        return resolve_mission(handle, repo_root)
    except AmbiguousHandleError as exc:
        if json_mode:
            _err_console.print_json(_json.dumps(exc.to_dict()))
        else:
            _err_console.print(str(exc))
        sys.exit(2)
    except MissionNotFoundError as exc:
        if json_mode:
            payload = {"error": "mission_not_found", "handle": exc.handle}
            _err_console.print_json(_json.dumps(payload))
        else:
            _err_console.print(
                f'[red]Error:[/red] No mission found for handle "{exc.handle}". '
                f"Check that the handle is correct and that the mission exists in kitty-specs/."
            )
        sys.exit(2)
    except MissingIdentityError as exc:
        if json_mode:
            payload = {
                "error": "missing_mission_id",
                "detail": str(exc),
                "remediation": "spec-kitty migrate backfill-identity",
            }
            _err_console.print_json(_json.dumps(payload))
        else:
            _err_console.print(
                f"[red]Error:[/red] {exc}\n"
                f"[yellow]Remediation:[/yellow] Run `spec-kitty migrate backfill-identity` to fix."
            )
        sys.exit(2)
