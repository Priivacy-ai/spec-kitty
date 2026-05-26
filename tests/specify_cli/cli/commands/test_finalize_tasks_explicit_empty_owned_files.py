"""Lock the fix from commit 0f4e1a383: explicit ``owned_files: []`` is honoured.

When a WP frontmatter EXPLICITLY declares ``owned_files: []`` (e.g. for a
planning-artifact / triage WP that legitimately owns nothing in src/ or
tests/), finalize-tasks MUST NOT auto-populate the field with paths
extracted from the WP body text. Auto-population is reserved for the case
where the field is absent entirely.

Regression test for FR-015 of mission test-stabilization-and-debt-pass-01KSF9HJ.
"""
from __future__ import annotations

from specify_cli.cli.commands.agent.mission import (
    _owned_files_yaml_is_explicit_empty_list,
)


def test_explicit_empty_list_detected():
    """``owned_files: []`` literal returns True."""
    raw = "---\nowned_files: []\n---\nbody\n"
    assert _owned_files_yaml_is_explicit_empty_list(raw) is True


def test_explicit_empty_list_with_padding_detected():
    """``owned_files:  [  ]`` literal returns True (whitespace tolerant)."""
    raw = "---\nowned_files:  [  ]\n---\nbody\n"
    assert _owned_files_yaml_is_explicit_empty_list(raw) is True


def test_absent_owned_files_returns_false():
    """No ``owned_files`` key returns False."""
    raw = "---\ntitle: foo\n---\nbody\n"
    assert _owned_files_yaml_is_explicit_empty_list(raw) is False


def test_populated_owned_files_returns_false():
    """Populated list returns False -- inference NOT skipped."""
    raw = "---\nowned_files:\n- src/foo.py\n---\nbody\n"
    assert _owned_files_yaml_is_explicit_empty_list(raw) is False


def test_no_frontmatter_returns_false():
    """A WP body without frontmatter returns False."""
    raw = "no frontmatter here\nowned_files: []\n"  # not in frontmatter region
    assert _owned_files_yaml_is_explicit_empty_list(raw) is False


def test_body_mention_of_empty_list_ignored():
    """``owned_files: []`` mentioned in body text (not frontmatter) returns False."""
    raw = "---\ntitle: foo\n---\nThe owned_files: [] convention is...\n"
    assert _owned_files_yaml_is_explicit_empty_list(raw) is False
