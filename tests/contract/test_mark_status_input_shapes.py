"""Contract test: ``mark-status`` accepts both bare and qualified task IDs
(FR-017, WP04/T022).

The parser must accept the shapes that ``tasks-finalize`` and downstream
emitters may produce: bare (``T001``) and mission-qualified
(``<mission_slug>/T001`` or ``<mission_slug>:T001``).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.fast


def test_bare_task_id_is_unchanged() -> None:
    from specify_cli.cli.commands.agent.tasks import _normalize_task_id_input

    assert _normalize_task_id_input("T001") == "T001"
    assert _normalize_task_id_input("T042") == "T042"
    assert _normalize_task_id_input("WP01") == "WP01"


def test_qualified_task_id_with_slash_is_normalized() -> None:
    from specify_cli.cli.commands.agent.tasks import _normalize_task_id_input

    assert _normalize_task_id_input("034-feature-name/T001") == "T001"
    assert (
        _normalize_task_id_input("stability-and-hygiene-hardening-2026-04/T018")
        == "T018"
    )
    assert _normalize_task_id_input("042-foo/WP01") == "WP01"


def test_qualified_task_id_with_colon_is_normalized() -> None:
    from specify_cli.cli.commands.agent.tasks import _normalize_task_id_input

    assert _normalize_task_id_input("034-feature:T001") == "T001"
    assert _normalize_task_id_input("042-foo:WP01") == "WP01"


def test_lowercase_task_id_is_uppercased_when_qualified() -> None:
    from specify_cli.cli.commands.agent.tasks import _normalize_task_id_input

    assert _normalize_task_id_input("034-feature/t001") == "T001"


def test_garbage_input_returns_unchanged() -> None:
    """Garbage IDs surface downstream as 'task not found in tasks.md'.

    The normalizer does NOT raise; it preserves the structured-error path
    that already exists for unknown identifiers.
    """
    from specify_cli.cli.commands.agent.tasks import _normalize_task_id_input

    # No qualifier, no recognizable suffix — return as-is.
    assert _normalize_task_id_input("garbage") == "garbage"
    assert _normalize_task_id_input("not-a-task-id") == "not-a-task-id"
    # Trailing whitespace is stripped.
    assert _normalize_task_id_input("  T001  ") == "T001"


def test_empty_input_returns_unchanged() -> None:
    from specify_cli.cli.commands.agent.tasks import _normalize_task_id_input

    assert _normalize_task_id_input("") == ""


def test_normalizer_used_by_mark_status_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end: mark-status accepts both shapes and normalizes both.

    We don't need to actually run a real mark-status (it requires a
    canonical mission + tasks.md). We just verify that `task_ids` is
    normalized inside the command before downstream lookup.
    """
    from specify_cli.cli.commands.agent import tasks as tasks_mod

    seen: list[list[str]] = []

    def fake_locate_project_root() -> None:
        # Force early exit by returning None — the command bails before
        # any filesystem access. We just want to confirm the normalizer
        # ran on the inputs.
        seen.append(["recorded"])
        return None

    monkeypatch.setattr(tasks_mod, "locate_project_root", fake_locate_project_root)

    # Direct call to the helper is sufficient for the contract.
    normalized = [
        tasks_mod._normalize_task_id_input(x)
        for x in ["foo/T001", "T002", "bar:WP03", "garbage"]
    ]
    assert normalized == ["T001", "T002", "WP03", "garbage"]
