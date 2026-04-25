"""Command registration helpers for Spec Kitty CLI."""

from __future__ import annotations

import sys

import typer


def _is_next_fast_path(argv: list[str]) -> bool:
    """Return True when argv directly invokes the startup-sensitive next command."""
    for arg in argv[1:]:
        if arg in {"--help", "-h"}:
            return False
        if arg == "next":
            return True
        if not arg.startswith("-"):
            return False
    return False


def register_commands(app: typer.Typer) -> None:
    """Attach all extracted commands to the root Typer application."""
    if _is_next_fast_path(sys.argv):
        from . import next_cmd as next_cmd_module

        app.command(name="next")(next_cmd_module.next_step)
        return

    from . import accept as accept_module
    from . import advise as advise_module
    from . import agent as agent_module
    from . import auth as auth_module
    from . import charter as charter_module
    from . import config_cmd as config_cmd_module
    from . import context as context_module
    from . import dashboard as dashboard_module
    from . import do_cmd as do_cmd_module
    from . import doctor as doctor_module
    from . import glossary as glossary_module
    from . import implement as implement_module
    from . import intake as intake_module
    from . import invocations_cmd as invocations_cmd_module
    from . import lifecycle as lifecycle_module
    from . import materialize as materialize_module
    from . import merge as merge_module
    from . import merge_driver as merge_driver_module
    from . import migrate_cmd as migrate_module
    from . import mission as mission_module
    from . import mission_type as mission_type_module
    from . import next_cmd as next_cmd_module
    from . import ops as ops_module
    from . import profiles_cmd as profiles_cmd_module
    from . import repair as repair_module
    from . import research as research_module
    from . import sync as sync_module
    from . import upgrade as upgrade_module
    from . import validate_encoding as validate_encoding_module
    from . import validate_tasks as validate_tasks_module
    from . import verify as verify_module
    from specify_cli import orchestrator_api as orchestrator_api_module
    from specify_cli.saas.rollout import is_saas_sync_enabled

    if is_saas_sync_enabled():
        from . import tracker as tracker_module
    else:  # pragma: no cover - deterministic environment gate
        tracker_module = None

    app.command()(accept_module.accept)
    app.add_typer(agent_module.app, name="agent")
    app.command()(config_cmd_module.config)
    app.add_typer(auth_module.app, name="auth", help="Authentication commands")
    app.add_typer(charter_module.app, name="charter")
    app.add_typer(context_module.app, name="context")
    app.command()(dashboard_module.dashboard)
    app.add_typer(doctor_module.app, name="doctor", help="Project health diagnostics")
    app.add_typer(glossary_module.app, name="glossary", help="Glossary management commands")
    app.command()(implement_module.implement)
    app.command()(intake_module.intake)
    app.command()(lifecycle_module.specify)
    app.command()(lifecycle_module.plan)
    app.command()(lifecycle_module.tasks)
    app.command(name="materialize")(materialize_module.materialize)
    app.command()(merge_module.merge)
    app.command(name="merge-driver-event-log", hidden=True)(merge_driver_module.merge_driver_event_log)
    app.add_typer(migrate_module.app, name="migrate")
    app.add_typer(mission_module.app, name="mission")
    app.command(name="next")(next_cmd_module.next_step)
    app.add_typer(mission_type_module.app, name="mission-type")
    app.add_typer(ops_module.app, name="ops")
    app.add_typer(orchestrator_api_module.app, name="orchestrator-api")
    app.add_typer(repair_module.app, name="repair", help="Repair broken templates")
    app.command()(research_module.research)
    app.add_typer(sync_module.app, name="sync", help="Synchronization commands")
    if tracker_module is not None:
        app.add_typer(tracker_module.app, name="tracker", help="Task tracker commands")
        app.command(name="issue-search", help="Search tracker issues via the hosted read path")(
            tracker_module.issue_search_command
        )
    app.command()(upgrade_module.upgrade)
    app.command(name="list-legacy-features")(upgrade_module.list_legacy_features)
    app.command(name="validate-encoding")(validate_encoding_module.validate_encoding)
    app.command(name="validate-tasks")(validate_tasks_module.validate_tasks)
    app.command()(verify_module.verify_setup)
    app.add_typer(profiles_cmd_module.app, name="profiles")
    app.command(name="advise", help="Get governance context for a request (opens an invocation record).")(advise_module.advise)
    app.command(name="ask", help="Invoke a named profile directly.")(advise_module.ask)
    app.add_typer(advise_module.profile_invocation_app, name="profile-invocation")
    app.command(name="do", help="Route a request to the best-matching profile (anonymous dispatch).")(do_cmd_module.do)
    app.add_typer(invocations_cmd_module.app, name="invocations")


__all__ = ["register_commands"]
