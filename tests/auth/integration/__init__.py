"""End-to-end integration tests for the spec-kitty auth CLI surface.

Every test in this package drives the real Typer ``app`` from
``specify_cli.cli.commands.auth`` via :class:`typer.testing.CliRunner`
(or via ``subprocess.run``). Tests that import flow classes without
also using ``CliRunner`` or ``subprocess`` are caught by the T063 audit
in :mod:`test_audit_clirunner`.
"""
