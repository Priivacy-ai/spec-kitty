"""CLI-level test that the ``--acknowledge-not-bulk-edit`` flag is wired.

This test addresses RISK-1 from the bulk-edit guardrail mission review:
the inference acknowledgement flag was unit-tested via
``tests/specify_cli/bulk_edit/test_inference.py`` but had no contract-level
check that the option actually reached the CLI.
"""

from __future__ import annotations

from typer.testing import CliRunner

from specify_cli.cli.commands.implement import implement as implement_fn


def test_implement_declares_acknowledge_flag() -> None:
    """The ``--acknowledge-not-bulk-edit`` option must be declared on the
    implement command. If a refactor removes or renames it, users who have
    been relying on the flag will see their invocations break with an
    "unexpected extra argument" error rather than a clean behavioral change.
    """
    # Most direct check: inspect the function signature for the parameter name.
    import inspect

    sig = inspect.signature(implement_fn)
    assert "acknowledge_not_bulk_edit" in sig.parameters, (
        "implement() must declare an 'acknowledge_not_bulk_edit' parameter "
        "so the --acknowledge-not-bulk-edit CLI option stays wired."
    )

    param = sig.parameters["acknowledge_not_bulk_edit"]
    # Default must be False so the warning fires unless explicitly suppressed.
    assert param.default is False or (
        hasattr(param.default, "default") and param.default.default is False
    ), "acknowledge_not_bulk_edit must default to False"


def test_implement_help_advertises_acknowledge_flag() -> None:
    """The CLI help text must include --acknowledge-not-bulk-edit so users
    can discover it via ``spec-kitty agent action implement --help``.
    """
    # The implement function is registered on the top-level ``action`` Typer
    # app in ``specify_cli.cli.commands.action``. We render its help via a
    # standalone Typer runner so this test does not depend on the full CLI
    # tree wiring being importable.
    import typer
    from specify_cli.cli.commands.implement import implement as implement_fn

    helper = typer.Typer()
    helper.command(name="implement")(implement_fn)

    # terminal_width prevents Rich from truncating the long option name with
    # an ellipsis; without this the option appears as "--acknowledge-not-bulk…".
    runner = CliRunner(env={"COLUMNS": "200", "TERM": "dumb"})
    result = runner.invoke(helper, ["implement", "--help"], terminal_width=200)
    assert result.exit_code == 0, f"help invocation failed: {result.output}"
    # Accept either the full flag or its distinctive prefix (Rich may still
    # truncate on very narrow widths; the prefix is unique enough).
    assert (
        "--acknowledge-not-bulk-edit" in result.output
        or "--acknowledge-not-bulk" in result.output
    ), (
        "CLI help must advertise --acknowledge-not-bulk-edit so users can "
        "discover it; current output:\n" + result.output
    )
    # The option's help string should be present so users know what it does.
    assert "inference warning" in result.output.lower(), (
        "Help text for --acknowledge-not-bulk-edit must describe the "
        "inference-warning suppression behavior; current output:\n" + result.output
    )
