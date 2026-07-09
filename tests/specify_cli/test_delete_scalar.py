"""Unit tests for :func:`task_utils.delete_scalar` (#2512).

``delete_scalar`` removes a scalar key-value line from WP frontmatter without
disturbing other content.  It is a companion to ``set_scalar``/``extract_scalar``
and is used by the move-task rollback path to clear stale claim fields.
"""

from __future__ import annotations

import pytest

from specify_cli.task_utils import delete_scalar, extract_scalar

pytestmark = [pytest.mark.fast]

_FRONTMATTER_WITH_CLAIM = """\
work_package_id: WP03
title: "Engine Telemetry"
agent: "claude-code"
shell_pid: "41417"
dependencies: []
"""

_FRONTMATTER_WITHOUT_CLAIM = """\
work_package_id: WP03
title: "Engine Telemetry"
dependencies: []
"""


def test_delete_removes_agent_key() -> None:
    result = delete_scalar(_FRONTMATTER_WITH_CLAIM, "agent")
    assert extract_scalar(result, "agent") is None
    # Other keys survive.
    assert extract_scalar(result, "work_package_id") == "WP03"
    assert extract_scalar(result, "shell_pid") == "41417"


def test_delete_removes_shell_pid_key() -> None:
    result = delete_scalar(_FRONTMATTER_WITH_CLAIM, "shell_pid")
    assert extract_scalar(result, "shell_pid") is None
    assert extract_scalar(result, "agent") == "claude-code"


def test_delete_both_claim_fields() -> None:
    """Removing agent + shell_pid leaves the rest of frontmatter intact."""
    after_agent = delete_scalar(_FRONTMATTER_WITH_CLAIM, "agent")
    after_both = delete_scalar(after_agent, "shell_pid")
    assert extract_scalar(after_both, "agent") is None
    assert extract_scalar(after_both, "shell_pid") is None
    assert extract_scalar(after_both, "work_package_id") == "WP03"
    assert extract_scalar(after_both, "title") == "Engine Telemetry"


def test_delete_noop_when_key_absent() -> None:
    result = delete_scalar(_FRONTMATTER_WITHOUT_CLAIM, "agent")
    assert result == _FRONTMATTER_WITHOUT_CLAIM


def test_delete_does_not_leave_blank_line() -> None:
    """Deleted lines must not leave an empty line in their place."""
    result = delete_scalar(_FRONTMATTER_WITH_CLAIM, "agent")
    assert "\n\n" not in result


def test_delete_preserves_exact_surrounding_text() -> None:
    before = "work_package_id: WP01\nagent: \"x\"\ntitle: \"Y\"\n"
    after = delete_scalar(before, "agent")
    assert after == "work_package_id: WP01\ntitle: \"Y\"\n"
