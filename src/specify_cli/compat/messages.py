"""Human and JSON message rendering for the compat planner.

Public surface
--------------
MESSAGES       -- dict[Fr023Case, str] — format strings per case.
render_human   -- render the human-readable message for a Plan.
render_json    -- render the JSON-contract dict for a Plan.

Security properties
-------------------
CHK016  All interpolated values are sanitised against
        ``^[A-Za-z0-9.\\-+_ /:]{1,256}$`` before insertion.
        Values that do not pass the regex are replaced with
        ``<unavailable>``.
NFR-007 Rendered human message is at most 4 lines.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from specify_cli.compat.planner import Plan

# ---------------------------------------------------------------------------
# Safe-value regex for all interpolated fields (CHK016)
# ---------------------------------------------------------------------------

_SAFE_VALUE_RE = re.compile(r"^[A-Za-z0-9.\-+_ /:]{1,256}$")
_UNAVAILABLE = "<unavailable>"


def _safe(value: object) -> str:
    """Sanitise *value* for interpolation into user-visible strings.

    Returns the string representation if it matches the safe-value regex, or
    ``"<unavailable>"`` otherwise.

    Args:
        value: Any value to sanitise.

    Returns:
        A safe string.
    """
    if value is None:
        return _UNAVAILABLE
    s = str(value)
    if _SAFE_VALUE_RE.match(s):
        return s
    return _UNAVAILABLE


# ---------------------------------------------------------------------------
# Message catalog (T022)
# ---------------------------------------------------------------------------

from specify_cli.compat.planner import Fr023Case  # noqa: E402

MESSAGES: dict[Fr023Case, str] = {
    Fr023Case.NONE: "",
    Fr023Case.CLI_UPDATE_AVAILABLE: ("Spec Kitty {latest} is available; you have {installed}.\n{hint_command_or_note}"),
    Fr023Case.PROJECT_MIGRATION_NEEDED: (
        "This project needs Spec Kitty project migrations before this command can run.\nRun: spec-kitty upgrade\nPreview first: spec-kitty upgrade --dry-run"
    ),
    Fr023Case.PROJECT_TOO_NEW_FOR_CLI: (
        "This project uses Spec Kitty project schema {schema_version}, but this CLI supports up to schema {max_supported}.\nUpgrade the CLI: {hint_command_or_note}"
    ),
    Fr023Case.PROJECT_NOT_INITIALIZED: "",
    Fr023Case.PROJECT_METADATA_CORRUPT: ("This project's .kittify/metadata.yaml is unreadable: {metadata_error}.\nRun: spec-kitty doctor"),
    Fr023Case.INSTALL_METHOD_UNKNOWN: ("Spec Kitty {latest} is available; you have {installed}.\n{hint_command_or_note}"),
}


# ---------------------------------------------------------------------------
# render_human (T022)
# ---------------------------------------------------------------------------


def render_human(plan: Plan) -> str:
    """Render the human-readable message for *plan*.

    All interpolated values are sanitised; the result is at most 4 lines
    (NFR-007).  Trailing whitespace is stripped from each line.

    Args:
        plan: The :class:`Plan` to render.

    Returns:
        A string suitable for printing directly to stdout.  May be empty.
    """
    template = MESSAGES.get(plan.fr023_case, "")
    if not template:
        return ""

    hint_command_or_note = _safe(plan.upgrade_hint.command if plan.upgrade_hint.command is not None else plan.upgrade_hint.note)

    replacements: dict[str, str] = {
        "latest": _safe(plan.cli_status.latest_version),
        "installed": _safe(plan.cli_status.installed_version),
        "hint_command_or_note": hint_command_or_note,
        "schema_version": _safe(plan.project_status.schema_version),
        "max_supported": _safe(plan.project_status.max_supported),
        "metadata_error": _safe(plan.project_status.metadata_error),
    }

    try:
        text = template.format(**replacements)
    except (KeyError, ValueError):
        text = template

    # Trim trailing whitespace from each line and enforce ≤4 lines (NFR-007)
    lines = [line.rstrip() for line in text.splitlines()]
    lines = lines[:4]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# render_json (T022)
# ---------------------------------------------------------------------------


def render_json(plan: Plan) -> dict[str, Any]:
    """Render the JSON-contract dict for *plan*.

    The returned dict matches ``contracts/compat-planner.json``.

    Args:
        plan: The :class:`Plan` to render.

    Returns:
        A JSON-serialisable dict.
    """
    cli = plan.cli_status
    proj = plan.project_status
    hint = plan.upgrade_hint

    fetched_at_iso: str | None = None
    if cli.fetched_at is not None:
        try:
            fetched_at_iso = cli.fetched_at.isoformat()
        except Exception:  # noqa: BLE001
            fetched_at_iso = None

    pending: list[dict[str, Any]] = []
    for step in plan.pending_migrations:
        files_modified: list[str] | None = None
        if step.files_modified is not None:
            files_modified = [str(f) for f in step.files_modified]
        pending.append(
            {
                "migration_id": str(step.migration_id),
                "target_schema_version": int(step.target_schema_version),
                "description": str(step.description),
                "files_modified": files_modified,
            }
        )

    # Safety value as string
    safety_str = str(plan.safety)
    if hasattr(plan.safety, "value"):
        safety_str = plan.safety.value

    # Install method as string
    install_method_str = str(plan.install_method)
    if hasattr(plan.install_method, "value"):
        install_method_str = plan.install_method.value

    hint_install_method_str = str(hint.install_method)
    if hasattr(hint.install_method, "value"):
        hint_install_method_str = hint.install_method.value

    # Project root as str or null
    project_root_str: str | None = None
    if proj.project_root is not None:
        project_root_str = str(proj.project_root)

    rendered_human_str = ""
    if hasattr(plan, "rendered_human") and isinstance(plan.rendered_human, str):
        rendered_human_str = plan.rendered_human

    return {
        "schema_version": 1,
        "case": str(plan.fr023_case),
        "decision": str(plan.decision),
        "exit_code": int(plan.exit_code),
        "cli": {
            "installed_version": str(cli.installed_version),
            "latest_version": cli.latest_version,
            "latest_source": str(cli.latest_source),
            "is_outdated": bool(cli.is_outdated),
            "fetched_at": fetched_at_iso,
        },
        "project": {
            "state": str(proj.state),
            "project_root": project_root_str,
            "schema_version": proj.schema_version,
            "min_supported": int(proj.min_supported),
            "max_supported": int(proj.max_supported),
            "metadata_error": proj.metadata_error,
        },
        "safety": safety_str,
        "install_method": install_method_str,
        "upgrade_hint": {
            "install_method": hint_install_method_str,
            "command": hint.command,
            "note": hint.note,
        },
        "pending_migrations": pending,
        "rendered_human": rendered_human_str,
    }


__all__ = ["MESSAGES", "render_human", "render_json"]
