"""Parse upgrade intent from caller-supplied Click definitions without dispatch."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import click


@dataclass(frozen=True)
class UpgradeIntent:
    """Effective routing, prior to target/compatibility validation or bootstrap.

    ``project`` records the explicit project restriction. ``project_available``
    is supplied by the caller's read-only project resolver; this module does
    no discovery. Semantic conflicts remain data for the selected renderer.
    Standalone hidden operations retain their own dispatch and output schemas.
    """

    mode: Literal["preview", "apply", "guidance", "hidden"]
    representation: Literal["human", "legacy", "full", "outcome", "hidden"]
    project: bool
    target: str | None
    include_worktrees: bool
    confirm: bool
    conflicts: tuple[str, ...] = ()
    project_required: bool = False
    hidden_options: tuple[tuple[str, object], ...] = ()


def _parse_values(command: click.Command, argv: Sequence[str]) -> tuple[dict[str, object], frozenset[str]]:
    # Click's parser owns aliases, equals syntax, arity, flags and usage errors.
    # Command.parse_args/Parameter.handle_parse_result would also run callbacks.
    context = click.Context(command, info_name=command.name, resilient_parsing=False)
    values, remaining, _order = command.make_parser(context).parse_args(list(argv))
    if remaining and not command.allow_extra_args:
        raise click.UsageError(f"Got unexpected extra arguments ({' '.join(remaining)})", context)
    supplied = frozenset(values)
    result: dict[str, object] = {}
    for param in command.get_params(context):
        if param.name is None:
            continue
        value = values.get(param.name)
        if param.name not in supplied:
            value = param.value_from_envvar(context)
            if value is None:
                value = param.get_default(context, call=False)
            if callable(value):
                # A parse-only caller cannot safely resolve a dynamic default.
                raise click.UsageError(f"Cannot resolve callable default for {param.name} without dispatch", context)
        if param.required and value is None:
            raise click.MissingParameter(ctx=context, param=param)
        result[param.name] = param.type_cast_value(context, value)
    return result, supplied


def parse_upgrade_intent(
    command: click.Command,
    argv: Sequence[str],
    *,
    project_available: bool,
) -> UpgradeIntent:
    """Parse subcommand arguments using the actual upgrade Click command.

    No root, eager, parameter or command callback is invoked. Missing/unknown
    options raise ordinary Click usage errors. WP10 supplies the real command
    after registering plan-json; this module never registers options itself.
    Target text remains uninterpreted for the existing target validator.
    """
    values, supplied = _parse_values(command, argv)
    project = bool(values.get("project"))
    cli = bool(values.get("cli"))
    full = bool(values.get("plan_json"))
    json_output = bool(values.get("json_output"))
    preview = full or bool(values.get("dry_run")) or (project and json_output)
    hidden_names = ("agent_check", "agent_choice", "agent_latest")
    hidden = tuple((name, values[name]) for name in hidden_names if values.get(name))
    presentation = {"json_output", "verbose", "no_nag", *hidden_names}
    standalone_hidden = bool(hidden) and not (supplied - presentation)
    guidance = cli or (not project_available and not project and not full and not standalone_hidden)
    conflicts: list[str] = []
    if cli and project:
        conflicts.append("--cli and --project are mutually exclusive")
    if full and cli:
        conflicts.append("--plan-json and --cli are mutually exclusive")
    if hidden and (preview or guidance):
        conflicts.append("Hidden agent operations cannot accompany upgrade preview or guidance")
    mode: Literal["preview", "apply", "guidance", "hidden"] = "apply"
    if standalone_hidden:
        mode = "hidden"
    elif guidance:
        mode = "guidance"
    elif preview:
        mode = "preview"
    representation: Literal["human", "legacy", "full", "outcome", "hidden"] = "human"
    if full:
        representation = "full"
    elif mode == "hidden":
        representation = "hidden" if json_output else "human"
    elif json_output:
        representation = "legacy" if mode in {"preview", "guidance"} else "outcome"
    target = values.get("target")
    if target is not None and not isinstance(target, str):
        raise click.BadParameter("Upgrade target definition must produce text", param_hint="--target")
    return UpgradeIntent(
        mode,
        representation,
        project,
        target,
        not bool(values.get("no_worktrees")),
        not (bool(values.get("yes")) or bool(values.get("force"))),
        tuple(conflicts),
        project and not project_available,
        hidden,
    )
