"""Upgrade command implementation for Spec Kitty CLI.

This module exposes ``spec-kitty upgrade`` with the following flag surface
(C-006 — all existing flags preserved, new flags are additive):

Existing flags (preserved unchanged):
  --dry-run           Preview changes without applying.
  --force             Skip confirmation prompts.
  --target VERSION    Target version (defaults to current CLI version).
  --json              Output results as JSON (project-upgrade contract).
  --verbose / -v      Show detailed migration information.
  --no-worktrees      Skip upgrading worktrees.

New flags (WP09):
  --cli               Restrict to CLI guidance only (FR-014).  Works outside
                      any project; skip project-side flow entirely.
  --project           Restrict to current-project compat + migrations (FR-015).
                      Errors when invoked outside a project.
  --yes / -y          Non-interactive confirmation; alias for --force (FR-017).
  --no-nag            Suppress upgrade-nag output explicitly.

Mutual exclusion:
  --cli + --project together → exit 2 (BLOCK_INCOMPATIBLE_FLAGS).

JSON contract (--json with --cli or --project):
  Emits the compat-planner contract from
  ``contracts/compat-planner.json`` (schema_version: 1).  See R-09.

Exit codes (R-08):
  0  ALLOW / ALLOW_WITH_NAG / dry-run always 0
  2  BLOCK_INCOMPATIBLE_FLAGS (--cli + --project)
  4  BLOCK_PROJECT_MIGRATION
  5  BLOCK_CLI_UPGRADE (project too new — not overridable by --yes)
  6  BLOCK_PROJECT_CORRUPT

See also: docs/guides/install-and-upgrade.md
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from specify_cli.tool_surface.repair import DriftPolicySummary
    from specify_cli.upgrade.runner import UpgradeResult
from rich.panel import Panel
from rich.table import Table

from mission_runtime import CommitTarget
from specify_cli.cli.helpers import console, show_banner
from specify_cli.cli.commands._teamspace_mission_state_gate import (
    offer_teamspace_mission_state_migration,
)
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.git.commit_helpers import safe_commit


_PROJECT_COMPAT_CHECK_COMMAND = ("__project_compat_check__",)


def _git_status_paths(repo_path: Path) -> set[str] | None:
    """Return git status paths for *repo_path* using porcelain -z output.

    Returns ``None`` when ``git status`` fails (e.g. not a git repo) so
    callers can distinguish "no dirty files" from "unable to determine".
    """
    result = subprocess.run(
        ["git", "status", "--porcelain", "-z"],
        cwd=repo_path,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    entries = result.stdout.decode("utf-8", errors="replace").split("\0")
    paths: set[str] = set()

    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry or len(entry) < 4:
            continue

        status = entry[:2]
        path = entry[3:]

        # With -z format, renames/copies include a second NUL-separated
        # path.  We take the *destination* (new name); the source (old name)
        # is intentionally discarded because we care about "what exists now".
        if ("R" in status or "C" in status) and i < len(entries) and entries[i]:
            path = entries[i]
            i += 1

        normalized = path.strip().replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]

        if normalized:
            paths.add(normalized)

    return paths


def _is_upgrade_commit_eligible(path: str, project_path: Path) -> bool:
    """Return True when a changed file should be included in upgrade auto-commit."""
    normalized = path.strip().replace("\\", "/")
    if not normalized:
        return False

    # Ignore paths that are outside the repo and root-level files.
    if normalized.startswith("../") or "/" not in normalized:
        return False

    # Never auto-commit ~/.kittify when users run inside their home directory.
    return not (project_path.resolve() == Path.home().resolve() and normalized.startswith(".kittify/"))


def _expand_upgrade_commit_path(project_path: Path, relative_path: str) -> list[Path]:
    """Expand a changed path into the concrete file paths git will stage.

    ``git status --porcelain -z`` may report untracked directories as a single
    path (for example ``.agents/skills/new-skill``). ``git add <dir>`` stages
    the files inside that directory, but ``safe_commit``'s backstop compares the
    staged file paths against the requested path list. Expand directories here
    so the expected set matches what git will actually stage.
    """
    normalized = relative_path.strip().replace("\\", "/")
    absolute_path = project_path / normalized

    if absolute_path.exists() and absolute_path.is_dir() and not absolute_path.is_symlink():
        return sorted(child.relative_to(project_path) for child in absolute_path.rglob("*") if not child.is_dir())

    return [Path(normalized)]


def _prepare_upgrade_commit_files(
    project_path: Path,
    baseline_paths: set[str] | None,
) -> list[Path]:
    """Collect newly changed project-directory files after an upgrade run.

    Returns an empty list when *baseline_paths* is ``None`` (git status
    failed at baseline time) to avoid accidentally committing unrelated work.
    """
    if baseline_paths is None:
        return []

    current_paths = _git_status_paths(project_path)
    if current_paths is None:
        return []

    new_paths = sorted(path for path in current_paths if path not in baseline_paths and _is_upgrade_commit_eligible(path, project_path))
    files_to_commit: list[Path] = []
    seen_paths: set[str] = set()
    for path in new_paths:
        for expanded_path in _expand_upgrade_commit_path(project_path, path):
            normalized = str(expanded_path).replace("\\", "/")
            if normalized in seen_paths:
                continue
            seen_paths.add(normalized)
            files_to_commit.append(Path(normalized))
    return files_to_commit


def _collect_manual_review_paths(migration_results: dict[str, object]) -> list[str]:
    """Return sorted preserved/archive paths that require operator review."""
    manual_review_paths: set[str] = set()
    for result in migration_results.values():
        if not getattr(result, "manual_review_required", False):
            continue
        manual_review_paths.update(getattr(result, "preserved_paths", []))
    return sorted(manual_review_paths)


def _auto_commit_upgrade_changes(
    project_path: Path,
    from_version: str,
    to_version: str,
    baseline_paths: set[str] | None,
) -> tuple[bool, list[str], str | None]:
    """Auto-commit newly introduced project-directory upgrade changes."""
    files_to_commit = _prepare_upgrade_commit_files(project_path, baseline_paths)
    if not files_to_commit:
        return False, [], None

    commit_message = f"chore: apply spec-kitty upgrade changes ({from_version} -> {to_version})"
    committed_paths = [str(path).replace("\\", "/") for path in files_to_commit]
    try:
        destination_ref = subprocess.check_output(
            ["git", "-C", str(project_path), "branch", "--show-current"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip() or "main"
    except Exception:
        destination_ref = "main"

    # The upgrade flow runs outside any mission, so there is no coordination
    # split to reconcile: the current branch is landing == coordination ==
    # target. Construct a ref-only CommitTarget (C-007) for it and assert the
    # upgrade bookkeeping capability explicitly (T009 / FR-008). The old reliance
    # on the "chore: apply spec-kitty upgrade changes" message-prefix exception is
    # now irrelevant — the message is just a message; the capability carries the
    # authorization to land on a protected branch (e.g. the operator's main).
    upgrade_target = CommitTarget(ref=destination_ref)

    try:
        safe_commit(
            repo_root=project_path,
            worktree_root=project_path,
            target=upgrade_target,
            message=commit_message,
            paths=tuple(files_to_commit),
            capability=GuardCapability.UPGRADE_BOOKKEEPING,
        )
    except Exception:
        return (
            False,
            committed_paths,
            "Could not auto-commit upgrade changes; please review and commit manually.",
        )

    return True, committed_paths, None


# ---------------------------------------------------------------------------
# T035 — --cli mode helper
# ---------------------------------------------------------------------------


def _run_cli_mode(
    *,
    json_output: bool,
    dry_run: bool,
    no_nag: bool,
    latest_version_provider: object = None,
) -> None:
    """Execute the --cli mode: emit CLI guidance without touching the project.

    Builds an Invocation with command_path=("upgrade",), calls compat.plan(),
    and either prints rendered_human (default) or renders_json (--json).

    This path is project-agnostic; it succeeds even outside any Spec Kitty
    project (FR-014).

    Args:
        json_output: When True, emit JSON instead of human text.
        dry_run: Passed through to exit-code logic (dry-run → always exit 0).
        no_nag: When True, set flag_no_nag in the Invocation.
        latest_version_provider: Optional override for tests.
    """
    from specify_cli.compat.planner import Invocation, is_ci_env, plan

    raw_args: tuple[str, ...] = ("--cli",)
    if dry_run:
        raw_args = raw_args + ("--dry-run",)

    # Read the real environment so that CI=1 spec-kitty upgrade --cli
    # correctly suppresses the network call (RISK-3 fix).
    invocation = Invocation(
        command_path=("upgrade",),
        raw_args=raw_args,
        is_help=False,
        is_version=False,
        flag_no_nag=no_nag,
        env_ci=is_ci_env(),
        stdout_is_tty=sys.stdout.isatty(),
    )

    kwargs: dict[str, object] = {}
    if latest_version_provider is not None:
        kwargs["latest_version_provider"] = latest_version_provider

    result = plan(invocation, **kwargs)  # type: ignore[arg-type]

    if json_output:
        exit_code = 0 if dry_run else result.exit_code
        payload = dict(result.rendered_json)
        print(json.dumps(payload, indent=2))
        raise typer.Exit(exit_code)

    if result.rendered_human:
        print(result.rendered_human)

    raise typer.Exit(0)


# ---------------------------------------------------------------------------
# Agent-host upgrade prompt helpers
# ---------------------------------------------------------------------------


def _version_is_newer(latest: str | None, installed: str) -> bool:
    if latest is None:
        return False
    try:
        from packaging.version import Version

        return Version(latest) > Version(installed)
    except Exception:  # noqa: BLE001
        return False


def _is_truthy(raw: str | None) -> bool:
    if not raw:
        return False
    return raw.strip().casefold() in {"1", "true", "yes", "on"}


def _agent_check_payload() -> dict[str, object]:
    """Return machine-readable upgrade readiness for agent prompt preambles."""
    from specify_cli.compat import (
        Invocation,
        NagCache,
        UpgradeConfig,
        build_upgrade_hint,
        detect_runtime,
        is_ci_env,
        plan as compat_plan,
    )
    from specify_cli.compat._detect.install_method import is_safe_for_auto_upgrade
    from specify_cli.readiness.upgrade_ux import (
        ENV_UPGRADE_DISABLED,
        is_currently_snoozed,
        needs_reset,
        resolve_effective_preference,
    )

    now = datetime.now(UTC)
    invocation = Invocation(
        command_path=("upgrade",),
        raw_args=("--agent-check", "--json"),
        is_help=False,
        is_version=False,
        flag_no_nag=False,
        env_ci=is_ci_env(),
        stdout_is_tty=True,
    )
    result = compat_plan(invocation, now=now)
    cli_status = result.cli_status
    install_method = detect_runtime().install_method
    latest_version = cli_status.latest_version
    hint = build_upgrade_hint(install_method, target_version=latest_version)

    payload: dict[str, object] = {
        "schema_version": 1,
        "action": "none",
        "installed_version": cli_status.installed_version,
        "latest_version": cli_status.latest_version,
        "latest_source": cli_status.latest_source,
        "install_method": str(install_method),
        "upgrade_command": hint.command,
        "upgrade_note": hint.note,
        "reason": "up_to_date",
    }

    config = UpgradeConfig.load()
    if not config.nag_enabled:
        payload["reason"] = "nag_disabled"
        return payload

    if not _version_is_newer(latest_version, cli_status.installed_version):
        return payload

    if _is_truthy(os.environ.get(ENV_UPGRADE_DISABLED)):
        payload["reason"] = "upgrade_disabled"
        return payload

    cache = NagCache.default()
    existing = cache.read()
    remote_version_seen = existing.remote_version_seen if existing is not None else None
    reset_anchor = needs_reset(record_remote_version=remote_version_seen, current_latest=latest_version)
    snoozed_until = None if reset_anchor or existing is None else existing.snoozed_until
    persisted_never_ask = False if reset_anchor or existing is None else existing.never_ask
    persisted_always_upgrade = False if existing is None else existing.always_upgrade

    pref = resolve_effective_preference(
        persisted_never_ask=persisted_never_ask,
        persisted_always_upgrade=persisted_always_upgrade,
    )
    if pref.disabled:
        payload["reason"] = "upgrade_disabled"
        return payload
    if pref.never_ask:
        payload["reason"] = "never_ask"
        return payload
    if is_currently_snoozed(snoozed_until=snoozed_until, now=now):
        payload["reason"] = "snoozed"
        return payload

    safe = is_safe_for_auto_upgrade(install_method)
    if pref.always_upgrade:
        payload["action"] = "auto_upgrade" if safe and hint.command is not None else "guidance"
        payload["reason"] = "always_upgrade"
        return payload

    if hint.command is None:
        payload["action"] = "guidance"
        payload["reason"] = "manual_upgrade_required"
        return payload

    payload["action"] = "prompt"
    payload["reason"] = "upgrade_available"
    return payload


def _run_agent_check(*, json_output: bool) -> None:
    payload = _agent_check_payload()
    if json_output:
        print(json.dumps(payload, indent=2))
    elif payload.get("action") != "none":
        latest = payload.get("latest_version") or "unknown"
        installed = payload.get("installed_version") or "unknown"
        print(f"Spec Kitty upgrade available: {installed} -> {latest}")
    raise typer.Exit(0)


def _record_agent_choice(
    *,
    choice_raw: str,
    latest_version: str | None,
    json_output: bool,
) -> None:
    from specify_cli import __version__
    from specify_cli.compat import NagCache, NagCacheRecord
    from specify_cli.readiness.upgrade_ux import UpgradeChoice, apply_choice, needs_reset

    try:
        choice = UpgradeChoice(choice_raw)
    except ValueError:
        payload = {"status": "error", "error": "invalid_agent_choice", "choice": choice_raw}
        print(json.dumps(payload) if json_output else "Error: invalid agent choice")
        raise typer.Exit(2) from None

    if not latest_version:
        payload = {"status": "error", "error": "missing_agent_latest"}
        print(json.dumps(payload) if json_output else "Error: --agent-latest is required")
        raise typer.Exit(2)

    now = datetime.now(UTC)
    cache = NagCache.default()
    existing = cache.read()
    reset_anchor = existing is not None and needs_reset(
        record_remote_version=existing.remote_version_seen,
        current_latest=latest_version,
    )
    record_kwargs: dict[str, object] = {
        "cli_version_key": __version__,
        "latest_version": latest_version,
        "latest_source": "pypi",
        "fetched_at": now,
        "last_shown_at": now,
        "remote_version_seen": None if reset_anchor or existing is None else existing.remote_version_seen,
        "snooze_step": None if reset_anchor or existing is None else existing.snooze_step,
        "snoozed_until": None if reset_anchor or existing is None else existing.snoozed_until,
        "always_upgrade": False if existing is None else existing.always_upgrade,
        "never_ask": False if reset_anchor or existing is None else existing.never_ask,
    }
    updated = apply_choice(record_kwargs, choice=choice, current_latest=latest_version, now=now)
    cache.write(NagCacheRecord(**updated))

    payload = {"status": "recorded", "choice": choice.value, "latest_version": latest_version}
    print(json.dumps(payload, indent=2) if json_output else f"Recorded {choice.value}")
    raise typer.Exit(0)


# ---------------------------------------------------------------------------
# T036 — helpers for project mode (skip CLI nag in output)
# ---------------------------------------------------------------------------


def _is_in_project(project_path: Path) -> bool:
    """Return True when *project_path* appears to be a Spec Kitty project."""
    return (project_path / ".kittify").exists() or (project_path / ".specify").exists()


def _repair_stale_command_manifest(project_path: Path, *, json_output: bool) -> None:
    """Self-heal a stale command-skill manifest during upgrade.

    FR-030: a manifest whose entry count is behind the canonical command set
    (e.g. an rc44-era 11-entry manifest) is auto-repaired to the canonical
    count without prompting. FR-032: unsafe symlink artifacts under
    ``.agents/skills/`` are removed. Drifted (user-edited) generated files are
    NOT touched here — they flow through the drift policy in
    ``run_surface_repair``. Failures are non-fatal: upgrade must never abort
    because of manifest repair.
    """
    manifest_path = project_path / ".kittify" / "command-skills-manifest.json"
    if not manifest_path.exists():
        return
    try:
        from specify_cli.skills.command_installer import CANONICAL_COMMANDS
        from specify_cli.skills.manifest_store import (
            remove_unsafe_symlinks,
            repair_stale_manifest,
        )

        symlink_result = remove_unsafe_symlinks(project_path)
        repair_result = repair_stale_manifest(
            project_path,
            canonical_commands=list(CANONICAL_COMMANDS),
        )
        if json_output:
            return
        if repair_result.added or repair_result.removed:
            console.print(
                f"[dim]Repaired command-skill manifest "
                f"(+{len(repair_result.added)}/-{len(repair_result.removed)} entries)[/dim]"
            )
        if symlink_result.symlinks_removed:
            console.print(
                f"[dim]Removed {len(symlink_result.symlinks_removed)} unsafe symlink artifact(s)[/dim]"
            )
    except Exception as manifest_exc:  # noqa: BLE001
        if not json_output:
            console.print(
                f"[dim]Note: Could not repair command-skill manifest: {manifest_exc}[/dim]"
            )


def _run_upgrade_surface_repair(
    project_path: Path,
    *,
    confirm: bool,
    dry_run: bool,
    json_output: bool,
) -> DriftPolicySummary | None:
    """Run tool-surface repair after an upgrade and report the outcome.

    FR-001/FR-002 wiring: this MUST run on every ``upgrade`` invocation —
    including the "already up to date" path where no migrations are pending —
    so that missing or stale generated surfaces (agent profiles, command-skill
    manifests) are healed even when the project version is unchanged.

    NFR-007: ``--yes``/``--force`` sets ``interactive=False``, which triggers
    Rule 4 (report-only) for drifted files — NOT Rule 5 (overwrite). Overwrite
    requires an explicit ``--repair-drift=overwrite`` flag (not yet exposed,
    defaults False). FR-006: a non-interactive run exits non-zero when drift is
    detected and was not explicitly overwritten.
    """
    if dry_run:
        return None
    try:
        _repair_stale_command_manifest(project_path, json_output=json_output)

        from specify_cli.tool_surface.repair import (
            render_surface_summary_lines,
            run_surface_repair,
        )

        summary = run_surface_repair(
            project_path,
            interactive=not confirm,
            repair_drift=False,
        )
        if not json_output:
            for line in render_surface_summary_lines(summary):
                console.print(line)
            if summary.drifted_reported and confirm:
                raise typer.Exit(1)
        return summary
    except typer.Exit:
        raise
    except Exception as surf_exc:  # noqa: BLE001
        # Never fail upgrade due to surface repair errors; report and continue.
        if not json_output:
            console.print(
                f"[dim]Note: Could not run tool surface repair: {surf_exc}[/dim]"
            )
        return None


def _surface_repair_payload(
    summary: DriftPolicySummary | None,
) -> dict[str, list[str]]:
    """Return a machine-readable drift-policy summary for upgrade JSON."""
    if summary is None:
        return {
            "created": [],
            "repaired": [],
            "drifted_overwritten": [],
            "drifted_reported": [],
            "skipped": [],
        }
    return {
        "created": [str(path) for path in summary.created],
        "repaired": [str(path) for path in summary.repaired],
        "drifted_overwritten": [str(path) for path in summary.drifted_overwritten],
        "drifted_reported": [str(path) for path in summary.drifted_reported],
        "skipped": [str(path) for path in summary.skipped],
    }


def _surface_drift_exit_required(
    summary: DriftPolicySummary | None,
    *,
    confirm: bool,
) -> bool:
    """Return True when non-interactive upgrade reported unresolved drift."""
    return bool(confirm and summary is not None and summary.drifted_reported)


def _surface_drift_error(summary: DriftPolicySummary) -> str:
    return (
        f"Unresolved tool-surface drift in {len(summary.drifted_reported)} "
        "file(s); run 'spec-kitty doctor tool-surfaces' to review."
    )


def _check_project_not_too_new(
    project_path: Path,
    *,
    json_output: bool,
) -> None:
    """Exit 5 if the project schema is newer than this CLI supports.

    CHK037 / A-006: ``--yes`` and ``--force`` do NOT bypass this check.
    A too-new project cannot be migrated downward from the project side;
    the only fix is to upgrade the CLI.  The function always exits 5 on a
    too-new project regardless of ``--dry-run`` (see WP09 T036 spec).

    Args:
        project_path: Path to the current project directory.
        json_output: When True, emit a JSON error payload.
    """
    try:
        from specify_cli.migration.schema_version import (
            MAX_SUPPORTED_SCHEMA,
            get_project_schema_version,
        )

        schema_v = get_project_schema_version(project_path)
        if schema_v is None:
            return  # No schema_version field → LEGACY; handled elsewhere
        if not isinstance(schema_v, int):
            return  # Corrupt; handled by MigrationRunner

        if schema_v > MAX_SUPPORTED_SCHEMA:
            if json_output:
                from specify_cli.compat.planner import Invocation, plan as _plan

                inv = Invocation(
                    # This JSON describes current-project compatibility, not
                    # the safe remediation command itself.
                    command_path=_PROJECT_COMPAT_CHECK_COMMAND,
                    raw_args=("--project",),
                    is_help=False,
                    is_version=False,
                    flag_no_nag=True,
                    env_ci=False,
                    stdout_is_tty=False,
                )
                result = _plan(inv)
                print(json.dumps(result.rendered_json, indent=2))
            else:
                from specify_cli.compat._detect.runtime import detect_runtime as _detect_runtime
                from specify_cli.compat.upgrade_hint import build_upgrade_hint

                method = _detect_runtime().install_method
                hint = build_upgrade_hint(method)
                hint_str = hint.command if hint.command is not None else hint.note or "Upgrade your CLI."
                console.print(
                    f"[red]Error:[/red] This project uses Spec Kitty project schema {schema_v}, "
                    f"but this CLI supports up to schema {MAX_SUPPORTED_SCHEMA}."
                )
                console.print(f"[cyan]Upgrade your CLI:[/cyan] {hint_str}")
            raise typer.Exit(5)
    except typer.Exit:
        raise
    except Exception:  # noqa: BLE001 — fail-open; let the runner handle other errors
        pass


# ---------------------------------------------------------------------------
# Main upgrade command
# ---------------------------------------------------------------------------


def upgrade(  # noqa: C901
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompts"),
    target: str | None = typer.Option(None, "--target", help="Target version (defaults to current CLI version)"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed migration information"),
    no_worktrees: bool = typer.Option(False, "--no-worktrees", help="Skip upgrading worktrees"),
    # --- WP09 new flags (T034) ---
    cli: bool = typer.Option(False, "--cli", help="Restrict to CLI guidance only; works outside any project (FR-014)"),
    project: bool = typer.Option(False, "--project", help="Restrict to current-project compat + migrations (FR-015)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Non-interactive confirmation; alias for --force (FR-017)"),
    no_nag: bool = typer.Option(False, "--no-nag", help="Suppress upgrade-nag output explicitly"),
    agent_check: bool = typer.Option(False, "--agent-check", help="Emit agent-host upgrade prompt JSON", hidden=True),
    agent_choice: str | None = typer.Option(None, "--agent-choice", help="Record an agent-host upgrade choice", hidden=True),
    agent_latest: str | None = typer.Option(None, "--agent-latest", help="Latest version for --agent-choice", hidden=True),
) -> None:
    """Upgrade a Spec Kitty project to the current version.

    Detects the project's current version and applies all necessary migrations
    to bring it up to date with the installed CLI version.

    **New flags (WP09)**:
      ``--cli``     Emit CLI upgrade guidance only.  No project detection;
                    succeeds outside any project (FR-014).
      ``--project`` Run project migrations only; suppresses CLI nag.
                    Errors outside a project.
      ``--yes``/``-y``  Non-interactive confirmation (alias for ``--force``).
                        Does NOT bypass schema-incompatibility blocks (CHK037/A-006).
      ``--no-nag``  Suppress upgrade-nag banner even when a CLI update exists.

    Mutual exclusion: ``--cli`` and ``--project`` together exit 2.

    **Exit codes** (R-08):
      0  Success / ALLOW / ALLOW_WITH_NAG / any ``--dry-run``
      2  ``--cli --project`` flag conflict
      4  Project migration required (BLOCK_PROJECT_MIGRATION)
      5  Project is too new for this CLI (BLOCK_CLI_UPGRADE) — not bypassable
      6  Project metadata corrupt (BLOCK_PROJECT_CORRUPT)
      1  General error

    See also: ``docs/guides/install-and-upgrade.md``

    Examples:
        spec-kitty upgrade              # Upgrade to current version
        spec-kitty upgrade --dry-run    # Preview changes
        spec-kitty upgrade --target 0.6.5  # Upgrade to specific version
        spec-kitty upgrade --cli        # Show CLI upgrade hint, no project needed
        spec-kitty upgrade --project    # Project migrations only
        spec-kitty upgrade --yes        # Non-interactive (same as --force)
        spec-kitty upgrade --dry-run --json  # Machine-readable plan
    """
    if agent_check and agent_choice is not None:
        console.print("[red]Error:[/red] --agent-check and --agent-choice are mutually exclusive.")
        raise typer.Exit(2)
    if agent_check:
        _run_agent_check(json_output=json_output)
        return
    if agent_choice is not None:
        _record_agent_choice(
            choice_raw=agent_choice,
            latest_version=agent_latest,
            json_output=json_output,
        )
        return

    # T034 — mutual exclusion check
    if cli and project:
        console.print("[red]Error:[/red] --cli and --project are mutually exclusive.")
        console.print("[dim]Use --cli for CLI guidance only, or --project for project migrations only.[/dim]")
        raise typer.Exit(2)

    # T034 — --yes aliases --force (both remain functional)
    confirm = (yes is True) or (force is True)

    # T035 — --cli mode: project-agnostic CLI guidance
    if cli:
        _run_cli_mode(
            json_output=json_output,
            dry_run=dry_run,
            no_nag=no_nag,
        )
        return  # _run_cli_mode always raises typer.Exit; belt-and-suspenders

    # --- Project-mode and default upgrade flow ---

    # T036 — in --project mode, fail fast outside a project
    project_path = Path.cwd()
    kittify_dir = project_path / ".kittify"
    specify_dir = project_path / ".specify"  # Old name

    if not kittify_dir.exists() and not specify_dir.exists():
        if project:
            # --project was explicit; surface a clear "no project" error
            if json_output:
                print(json.dumps({"error": "Not a Spec Kitty project", "case": "project_not_initialized"}))
            else:
                console.print("[red]Error:[/red] Not a Spec Kitty project.")
                console.print("[dim]Run 'spec-kitty init' to initialize a project.[/dim]")
                console.print("[dim]Tip: use 'spec-kitty upgrade --cli' for CLI guidance outside a project.[/dim]")
            raise typer.Exit(1)
        else:
            # Default mode (bare `spec-kitty upgrade` outside any project):
            # FR-014 says this should fall through to CLI guidance behavior
            # rather than erroring.  Only error when --project is explicit.
            _run_cli_mode(
                json_output=json_output,
                dry_run=dry_run,
                no_nag=no_nag,
            )
            return  # _run_cli_mode always raises typer.Exit; belt-and-suspenders

    # CHK037 / A-006 — Check if project is too new for this CLI.
    # This check runs BEFORE the existing upgrade flow so that
    # --yes / --force do NOT bypass the block.
    # The upgrade command is SAFE (remediation path), so the planner's
    # decide() would ALLOW it, but the command itself must refuse to
    # run migrations against a project with schema > MAX_SUPPORTED.
    _check_project_not_too_new(project_path, json_output=json_output)

    # T037 — --json with compat-planner contract (for --project or default with --json)
    # When --json is passed (with or without --dry-run), we emit the contract
    # from contracts/compat-planner.json in addition to (or instead of) the
    # old project-upgrade JSON.  For --project mode, the planner is always
    # consulted; for default mode, the planner runs only when --json is used.
    if json_output and (project or dry_run):
        # Emit compat-planner contract
        _run_planner_json(
            dry_run=dry_run,
            no_nag=no_nag,
        )
        return  # _run_planner_json always raises typer.Exit

    if not json_output:
        show_banner()

    baseline_changed_paths = _git_status_paths(project_path)

    # Import upgrade system (lazy to avoid circular imports)
    from specify_cli.upgrade.detector import VersionDetector
    from specify_cli.upgrade.registry import MigrationRegistry
    from specify_cli.upgrade.runner import MigrationRunner, validate_upgrade_target

    from specify_cli.upgrade.migrations import auto_discover_migrations

    auto_discover_migrations()

    # Detect current version
    detector = VersionDetector(project_path)
    current_version = detector.detect_version()

    # Determine target version
    if target is None:
        from specify_cli import __version__

        target_version = __version__
    else:
        target_version = target

    validation_error = validate_upgrade_target(current_version, target_version)
    if validation_error:
        if json_output:
            print(
                json.dumps(
                    {
                        "status": "failed",
                        "current_version": current_version,
                        "target_version": target_version,
                        "success": False,
                        "errors": [validation_error],
                        "warnings": [],
                        "auto_committed": False,
                        "auto_commit_paths": [],
                    }
                )
            )
        else:
            console.print(f"[red]Error:[/red] {validation_error}")
        raise typer.Exit(1)

    if not json_output:
        console.print(f"[cyan]Current version:[/cyan] {current_version}")
        console.print(f"[cyan]Target version:[/cyan]  {target_version}")
        console.print()

    # Get needed migrations
    # Handle "unknown" version by treating it as very old (0.0.0)
    version_for_migration = "0.0.0" if current_version == "unknown" else current_version
    migrations_needed = MigrationRegistry.get_applicable(version_for_migration, target_version, project_path=project_path)

    if not migrations_needed:
        auto_committed = False
        auto_commit_paths: list[str] = []
        auto_commit_warning: str | None = None
        worktree_warnings: list[str] = []

        # Still stamp the version even when no migrations are needed
        from specify_cli.upgrade.metadata import ProjectMetadata

        metadata = ProjectMetadata.load(kittify_dir)
        if metadata and metadata.version != target_version and not dry_run:
            metadata.version = target_version
            metadata.last_upgraded_at = datetime.now()
            metadata.save(kittify_dir)

        if not dry_run:
            from specify_cli.migration.schema_version import REQUIRED_SCHEMA_VERSION

            if REQUIRED_SCHEMA_VERSION is not None:
                MigrationRunner._stamp_schema_version(kittify_dir, REQUIRED_SCHEMA_VERSION)

        if not no_worktrees and current_version == target_version:
            worktrees_result = MigrationRunner(project_path, console)._upgrade_worktrees(
                target_version,
                [],
                dry_run,
            )
            worktree_warnings.extend(worktrees_result.get("warnings", []))
            if worktrees_result.get("errors"):
                worktree_warnings.extend(worktrees_result["errors"])
                worktree_warnings.append("Some worktrees had issues - check errors above")

        if not dry_run:
            auto_committed, auto_commit_paths, auto_commit_warning = _auto_commit_upgrade_changes(
                project_path=project_path,
                from_version=current_version,
                to_version=target_version,
                baseline_paths=baseline_changed_paths,
            )

        if not json_output:
            offer_teamspace_mission_state_migration(
                project_path,
                console=console,
                dry_run=dry_run,
                assume_yes=confirm,
            )

        # FR-001/FR-002: heal generated surfaces even when no migrations are
        # pending. Missing agent profiles or stale manifests on an already
        # up-to-date project would otherwise never be repaired.
        surface_repair_summary = _run_upgrade_surface_repair(
            project_path,
            confirm=confirm,
            dry_run=dry_run,
            json_output=json_output,
        )
        surface_drift_failed = _surface_drift_exit_required(
            surface_repair_summary,
            confirm=confirm,
        )

        if json_output:
            warnings = list(worktree_warnings)
            if auto_commit_warning:
                warnings.append(auto_commit_warning)
            errors: list[str] = []
            if surface_drift_failed and surface_repair_summary is not None:
                errors.append(_surface_drift_error(surface_repair_summary))
            print(
                json.dumps(
                    {
                        "status": "failed" if surface_drift_failed else "up_to_date",
                        "current_version": current_version,
                        "target_version": target_version,
                        "success": not surface_drift_failed,
                        "errors": errors,
                        "auto_committed": auto_committed,
                        "auto_commit_paths": auto_commit_paths,
                        "warnings": warnings,
                        "surface_repair": _surface_repair_payload(
                            surface_repair_summary
                        ),
                    }
                )
            )
            if surface_drift_failed:
                raise typer.Exit(1)
        else:
            console.print("[green]Project is already up to date![/green]")
            for warning in worktree_warnings:
                console.print(f"[yellow]Warning:[/yellow] {warning}")
            if auto_committed:
                console.print(f"[cyan]→ Auto-committed upgrade changes ({len(auto_commit_paths)} files)[/cyan]")
            if auto_commit_warning:
                console.print(f"[yellow]Warning:[/yellow] {auto_commit_warning}")
        return

    # Show migration plan
    if not json_output:
        table = Table(title="Migration Plan", show_lines=False, header_style="bold cyan")
        table.add_column("Migration", style="bright_white")
        table.add_column("Description", style="dim")
        table.add_column("Target", style="cyan")

        for migration in migrations_needed:
            table.add_row(
                migration.migration_id,
                migration.description,
                migration.target_version,
            )

        console.print(table)
        console.print()

        if verbose:
            # Show detection results
            console.print("[dim]Detection results:[/dim]")
            for migration in migrations_needed:
                detected = migration.detect(project_path)
                can_apply, reason = migration.can_apply(project_path)
                status = "[green]ready[/green]" if detected and can_apply else "[yellow]skipped[/yellow]"
                console.print(f"  {migration.migration_id}: {status}")
                if not can_apply and reason:
                    console.print(f"    [dim]{reason}[/dim]")
            console.print()

    # T034 — confirm uses `confirm` (yes or force) instead of bare `force`
    if not dry_run and not confirm:
        proceed = typer.confirm(
            f"Apply {len(migrations_needed)} migration(s)?",
            default=True,
        )
        if not proceed:
            console.print("[yellow]Upgrade cancelled.[/yellow]")
            raise typer.Exit(0)

    # Run migrations
    runner = MigrationRunner(project_path, console)
    result = runner.upgrade(
        target_version,
        dry_run=dry_run,
        force=confirm,  # pass the unified confirm flag
        include_worktrees=not no_worktrees,
    )

    auto_committed = False
    auto_commit_paths_list: list[str] = []
    auto_commit_warning: str | None = None
    manual_review_paths = _collect_manual_review_paths(result.migration_results)
    if result.success and not dry_run:
        if manual_review_paths:
            auto_commit_warning = "Skipped auto-commit because the upgrade preserved customized files that require manual review."
            result.warnings.append(auto_commit_warning)
        else:
            auto_committed, auto_commit_paths_list, auto_commit_warning = _auto_commit_upgrade_changes(
                project_path=project_path,
                from_version=result.from_version,
                to_version=result.to_version,
                baseline_paths=baseline_changed_paths,
            )
            if auto_commit_warning:
                result.warnings.append(auto_commit_warning)

    if result.success and not json_output:
        offer_teamspace_mission_state_migration(
            project_path,
            console=console,
            dry_run=dry_run,
            assume_yes=confirm,
        )

    # Run tool-surface repair after migrations have been applied.
    surface_repair_summary = None
    if result.success:
        surface_repair_summary = _run_upgrade_surface_repair(
            project_path,
            confirm=confirm,
            dry_run=dry_run,
            json_output=json_output,
        )
    surface_drift_failed = _surface_drift_exit_required(
        surface_repair_summary,
        confirm=confirm,
    )
    errors = list(result.errors)
    if surface_drift_failed and surface_repair_summary is not None:
        errors.append(_surface_drift_error(surface_repair_summary))
    success = result.success and not surface_drift_failed

    if json_output:
        # Build detailed migrations array
        migrations_detail = []
        for migration in migrations_needed:
            if migration.migration_id in result.migrations_applied:
                status = "applied"
            elif migration.migration_id in result.migrations_skipped:
                status = "skipped"
            else:
                status = "pending"
            migrations_detail.append(
                {
                    "id": migration.migration_id,
                    "description": migration.description,
                    "target_version": migration.target_version,
                    "status": status,
                    "manual_review_required": (
                        result.migration_results.get(migration.migration_id).manual_review_required if migration.migration_id in result.migration_results else False
                    ),
                    "preserved_paths": (
                        result.migration_results.get(migration.migration_id).preserved_paths if migration.migration_id in result.migration_results else []
                    ),
                }
            )

        # Surface per-migration schema-shaped JSON reports (e.g. the
        # 3.2.0rc35_unified_bundle contract-shaped payload). Each migration
        # emits its report as a single JSON string inside
        # ``MigrationResult.changes_made[0]``; decode it so operators see a
        # structured object rather than an opaque string.
        migration_reports: dict[str, object] = {}
        for mid, mres in result.migration_results.items():
            if not mres.changes_made:
                continue
            payload = mres.changes_made[0]
            try:
                migration_reports[mid] = json.loads(payload)
            except (TypeError, ValueError):
                # Migration emitted a non-JSON change string; skip rather
                # than break the operator contract.
                continue

        output = {
            "status": "success" if success else "failed",
            "current_version": result.from_version,
            "target_version": result.to_version,
            "dry_run": result.dry_run,
            "migrations": migrations_detail,
            "migrations_applied": result.migrations_applied,
            "migrations_skipped": result.migrations_skipped,
            "migration_reports": migration_reports,
            "success": success,
            "errors": errors,
            "warnings": result.warnings,
            "manual_review_required": bool(manual_review_paths),
            "manual_review_paths": manual_review_paths,
            "auto_committed": auto_committed,
            "auto_commit_paths": auto_commit_paths_list,
            "surface_repair": _surface_repair_payload(surface_repair_summary),
        }
        print(json.dumps(output))
        if surface_drift_failed:
            raise typer.Exit(1)
        return

    # Display results
    _display_upgrade_results(
        result,
        manual_review_paths=manual_review_paths,
        auto_committed=auto_committed,
        auto_commit_paths=auto_commit_paths_list,
    )


def _print_upgrade_section(header: str, items: list[str], item_prefix: str) -> None:
    """Print a titled list section, emitting nothing when *items* is empty."""
    if not items:
        return
    console.print(header)
    for item in items:
        console.print(f"{item_prefix}{item}")


def _display_upgrade_results(
    result: UpgradeResult,
    *,
    manual_review_paths: list[str],
    auto_committed: bool,
    auto_commit_paths: list[str],
) -> None:
    """Render the human-readable upgrade outcome.

    WP02 / FR-013 (#1784 P3 crumb): a ``--dry-run`` invocation must never print
    a success line implying changes were applied — the closing line is
    dry-run-specific ("Dry run complete — no changes applied."), while a real
    successful run keeps the "Upgrade complete!" line unchanged.

    Raises:
        typer.Exit: with code 1 when ``result.success`` is False.
    """
    console.print()

    if result.dry_run:
        console.print(
            Panel(
                "[yellow]DRY RUN[/yellow] - No changes were made",
                border_style="yellow",
            )
        )

    _print_upgrade_section(
        "[green]Migrations applied:[/green]", result.migrations_applied, "  [green]✓[/green] "
    )
    _print_upgrade_section(
        "[dim]Migrations skipped (already applied or not needed):[/dim]",
        result.migrations_skipped,
        "  [dim]○[/dim] ",
    )
    _print_upgrade_section("[yellow]Warnings:[/yellow]", result.warnings, "  [yellow]![/yellow] ")
    _print_upgrade_section("[red]Errors:[/red]", result.errors, "  [red]✗[/red] ")
    _print_upgrade_section(
        "[yellow]Manual review required:[/yellow]", manual_review_paths, "  [yellow]![/yellow] "
    )

    console.print()
    if not result.success:
        console.print("[bold red]Upgrade failed.[/bold red]")
        raise typer.Exit(1)
    if result.dry_run:
        # Honest dry-run: nothing was applied, so do not imply it was.
        console.print(
            "[bold yellow]Dry run complete[/bold yellow] — no changes applied. "
            f"({result.from_version} -> {result.to_version} previewed)"
        )
    else:
        console.print(f"[bold green]Upgrade complete![/bold green] {result.from_version} -> {result.to_version}")
        if auto_committed:
            console.print(f"[cyan]→ Auto-committed upgrade changes ({len(auto_commit_paths)} files)[/cyan]")


# ---------------------------------------------------------------------------
# T037 — planner JSON helper (emits compat-planner.json contract)
# ---------------------------------------------------------------------------


def _run_planner_json(
    *,
    dry_run: bool,
    no_nag: bool,
    latest_version_provider: object = None,
) -> None:
    """Emit the compat-planner JSON contract to stdout and raise typer.Exit.

    Suppresses all human output.  Exit code follows R-08 unless ``dry_run``
    is True, in which case exit code is always 0.

    Args:
        dry_run: When True, always exit 0.
        no_nag: Suppress nag flag passed to the Invocation.
        latest_version_provider: Optional override for tests.
    """
    from specify_cli.compat.planner import Invocation, is_ci_env, plan

    raw_args: tuple[str, ...] = ("--project",)
    if dry_run:
        raw_args = raw_args + ("--dry-run",)

    # Read the real environment so that CI=1 spec-kitty upgrade --json
    # correctly suppresses the network call (RISK-3 fix).
    invocation = Invocation(
        # Emit the compatibility plan for normal project-mutating commands.
        # ``upgrade`` itself is registered SAFE so users can remediate stale
        # schemas; using it here would hide project_migration_needed.
        command_path=_PROJECT_COMPAT_CHECK_COMMAND,
        raw_args=raw_args,
        is_help=False,
        is_version=False,
        flag_no_nag=no_nag,
        env_ci=is_ci_env(),
        stdout_is_tty=sys.stdout.isatty(),
    )

    kwargs: dict[str, object] = {}
    if latest_version_provider is not None:
        kwargs["latest_version_provider"] = latest_version_provider

    result = plan(invocation, **kwargs)  # type: ignore[arg-type]

    exit_code = 0 if dry_run else result.exit_code
    print(json.dumps(result.rendered_json, indent=2))
    raise typer.Exit(exit_code)


__all__ = ["upgrade"]
