"""Tests for supporting governance reference diagnostics."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from charter.governance_references import (
    collect_governance_reference_status,
    render_governance_references,
)

pytestmark = pytest.mark.fast


def test_collect_governance_references_reports_missing_doc(tmp_path: Path) -> None:
    statuses = collect_governance_reference_status(
        tmp_path,
        ["spec/constitution.md"],
    )

    assert len(statuses) == 1
    assert statuses[0].exists is False
    assert statuses[0].safe is True
    assert "Missing governance reference spec/constitution.md" in str(statuses[0].warning)
    assert statuses[0].to_dict()["path"] == "spec/constitution.md"


def test_collect_governance_references_rejects_escape(tmp_path: Path) -> None:
    statuses = collect_governance_reference_status(
        tmp_path,
        ["../outside.md"],
    )

    assert len(statuses) == 1
    assert statuses[0].safe is False
    assert "parent-directory traversal is not allowed" in str(statuses[0].warning)


def test_collect_governance_references_ignores_blank_entries(tmp_path: Path) -> None:
    statuses = collect_governance_reference_status(
        tmp_path,
        ["  ", "spec/constitution.md"],
    )

    assert [status.path for status in statuses] == ["spec/constitution.md"]


def test_collect_governance_references_rejects_absolute_path(tmp_path: Path) -> None:
    statuses = collect_governance_reference_status(
        tmp_path,
        [str(tmp_path / "constitution.md")],
    )

    assert len(statuses) == 1
    assert statuses[0].safe is False
    assert "not absolute" in str(statuses[0].warning)


def test_collect_governance_references_reports_directory(tmp_path: Path) -> None:
    (tmp_path / "spec").mkdir()

    statuses = collect_governance_reference_status(
        tmp_path,
        ["spec"],
    )

    assert len(statuses) == 1
    assert statuses[0].exists is True
    assert statuses[0].safe is True
    assert "is not a file" in str(statuses[0].warning)


@pytest.mark.requires_symlinks
def test_collect_governance_references_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-governance.md"
    outside.write_text("# Outside\n", encoding="utf-8")
    link = tmp_path / "linked-governance.md"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")

    statuses = collect_governance_reference_status(
        tmp_path,
        ["linked-governance.md"],
    )

    assert len(statuses) == 1
    assert statuses[0].safe is False
    assert "escapes the repository root" in str(statuses[0].warning)


def test_render_governance_references_returns_empty_without_references(tmp_path: Path) -> None:
    assert render_governance_references(tmp_path, []) == ""


def test_render_governance_references_includes_warnings(tmp_path: Path) -> None:
    text = render_governance_references(tmp_path, ["docs/missing.md"])

    assert "Required Governance Reading:" in text
    assert "WARNING: Missing governance reference docs/missing.md" in text
