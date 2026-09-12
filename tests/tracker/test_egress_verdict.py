"""Tests for ``tracker_egress_verdict`` after Channel 1 (hosted-sync consent) retired (#5).

Replaces the coverage lost when ``tests/sync/tracker/test_tracker_egress_verdict_3108.py`` and
``test_tracker_egress_refusal_3108.py`` were deleted with the sync transport -- both pinned the
old two-channel (``_JOIN``) behaviour and imported ``specify_cli.egress``/``specify_cli.sync``,
which no longer exist. This file pins the single-channel replacement: Channel 2 (the project's
own committed ``tracker.egress`` key) is two-way at ``LOCAL_SUBPROCESS`` and narrowing-only at
``HOSTED_SERVICE`` -- it may refuse a hosted request, but a ``permitted`` value or its absence
can never grant one; that always falls through to the authenticated-session default.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.tracker.config import TrackerProjectConfig, save_tracker_config
from specify_cli.tracker.egress_verdict import (
    CHANNEL_2,
    EgressDestination,
    tracker_egress_verdict,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _write_egress(root: Path, value: str) -> None:
    save_tracker_config(root, TrackerProjectConfig(provider="beads", egress=value))


class TestLocalSubprocessIsTwoWay:
    def test_refused_key_refuses(self, tmp_path: Path) -> None:
        _write_egress(tmp_path, "refused")
        verdict = tracker_egress_verdict(tmp_path, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers="issue-1")
        assert verdict.refused is True
        assert verdict.refusing_channels == frozenset({CHANNEL_2})

    def test_permitted_key_permits(self, tmp_path: Path) -> None:
        _write_egress(tmp_path, "permitted")
        verdict = tracker_egress_verdict(tmp_path, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers="issue-1")
        assert verdict.refused is False
        assert verdict.refusing_channels == frozenset()

    def test_absent_key_refuses_with_grant_remedy(self, tmp_path: Path) -> None:
        verdict = tracker_egress_verdict(tmp_path, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers="issue-1")
        assert verdict.refused is True
        assert verdict.remedies

    def test_illegal_value_refuses_as_fault(self, tmp_path: Path) -> None:
        _write_egress(tmp_path, "sometimes")
        verdict = tracker_egress_verdict(tmp_path, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers="issue-1")
        assert verdict.refused is True

    def test_no_root_refuses(self) -> None:
        verdict = tracker_egress_verdict(None, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers="issue-1")
        assert verdict.refused is True


class TestHostedServiceIsNarrowingOnly:
    """A committed ``tracker.egress`` key may refuse a hosted request; it may never grant one."""

    def test_refused_key_still_refuses(self, tmp_path: Path) -> None:
        _write_egress(tmp_path, "refused")
        verdict = tracker_egress_verdict(tmp_path, destination=EgressDestination.HOSTED_SERVICE, identifiers="issue-1")
        assert verdict.refused is True
        assert verdict.refusing_channels == frozenset({CHANNEL_2})

    def test_fault_value_still_refuses(self, tmp_path: Path) -> None:
        _write_egress(tmp_path, "sometimes")
        verdict = tracker_egress_verdict(tmp_path, destination=EgressDestination.HOSTED_SERVICE, identifiers="issue-1")
        assert verdict.refused is True
        assert verdict.refusing_channels == frozenset({CHANNEL_2})

    def test_permitted_key_does_not_grant_but_does_not_block(self, tmp_path: Path) -> None:
        _write_egress(tmp_path, "permitted")
        verdict = tracker_egress_verdict(tmp_path, destination=EgressDestination.HOSTED_SERVICE, identifiers="issue-1")
        assert verdict.refused is False

    def test_absent_key_falls_through_to_permit(self, tmp_path: Path) -> None:
        verdict = tracker_egress_verdict(tmp_path, destination=EgressDestination.HOSTED_SERVICE, identifiers="issue-1")
        assert verdict.refused is False
        assert verdict.refusing_channels == frozenset()

    def test_no_root_falls_through_to_permit(self) -> None:
        """No checkout to read Channel 2 out of -- nothing left to narrow with."""
        verdict = tracker_egress_verdict(None, destination=EgressDestination.HOSTED_SERVICE, identifiers="issue-1")
        assert verdict.refused is False


def test_never_raises_on_unreadable_config(tmp_path: Path) -> None:
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("not: [valid: yaml", encoding="utf-8")
    for destination in EgressDestination:
        verdict = tracker_egress_verdict(tmp_path, destination=destination, identifiers="issue-1")
        assert isinstance(verdict.refused, bool)
