"""Tests for supporting governance reference diagnostics."""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.governance_references import collect_governance_reference_status

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


def test_collect_governance_references_rejects_escape(tmp_path: Path) -> None:
    statuses = collect_governance_reference_status(
        tmp_path,
        ["../outside.md"],
    )

    assert len(statuses) == 1
    assert statuses[0].safe is False
    assert "parent-directory traversal is not allowed" in str(statuses[0].warning)
