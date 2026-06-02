"""ATDD stub for agent_commands.py resolver (WP01 first commit per C-011)."""
from __future__ import annotations


def test_resolver_returns_path_not_none() -> None:
    """Fails until FR-001 is implemented: resolver currently returns None."""
    from specify_cli.runtime.agent_commands import _get_command_templates_dir

    result = _get_command_templates_dir()
    assert result is not None
    assert result.is_absolute()
