"""Tests for CollapseEvent and CollapseReport data models."""

import pytest

from specify_cli.lanes.models import CollapseEvent, CollapseReport

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# CollapseEvent tests
# ---------------------------------------------------------------------------


class TestCollapseEvent:
    def test_serialization(self):
        """CollapseEvent.to_dict() round-trips all fields."""
        event = CollapseEvent(
            wp_a="WP01",
            wp_b="WP02",
            rule="dependency",
            evidence="WP01 depends on WP02",
        )
        d = event.to_dict()
        assert d == {
            "wp_a": "WP01",
            "wp_b": "WP02",
            "rule": "dependency",
            "evidence": "WP01 depends on WP02",
        }

    def test_frozen_is_hashable(self):
        """CollapseEvent is frozen, so it must be usable in sets and as dict keys."""
        event = CollapseEvent(wp_a="WP01", wp_b="WP02", rule="dependency", evidence="x")
        s = {event}
        assert event in s

    def test_frozen_immutable(self):
        """CollapseEvent cannot be mutated after creation."""
        import pytest

        event = CollapseEvent(wp_a="WP01", wp_b="WP02", rule="dependency", evidence="x")
        with pytest.raises((AttributeError, TypeError)):
            event.rule = "other"  # type: ignore[misc]

    def test_equality(self):
        """Two CollapseEvents with identical fields are equal."""
        a = CollapseEvent(wp_a="WP01", wp_b="WP02", rule="dependency", evidence="x")
        b = CollapseEvent(wp_a="WP01", wp_b="WP02", rule="dependency", evidence="x")
        assert a == b

    def test_inequality_different_rule(self):
        a = CollapseEvent(wp_a="WP01", wp_b="WP02", rule="dependency", evidence="x")
        b = CollapseEvent(wp_a="WP01", wp_b="WP02", rule="write_scope_overlap", evidence="x")
        assert a != b


# ---------------------------------------------------------------------------
# CollapseReport tests
# ---------------------------------------------------------------------------


class TestCollapseReport:
    def test_empty_report_serialization(self):
        """Empty report serializes cleanly with zero counts."""
        report = CollapseReport(events=[], independent_wps_collapsed=0)
        d = report.to_dict()
        assert d["events"] == []
        assert d["total_merges"] == 0
        assert d["independent_wps_collapsed"] == 0
        assert d["by_rule"] == {}

    def test_count_by_rule_single_rule(self):
        """CollapseReport._count_by_rule counts correctly for one rule."""
        events = [
            CollapseEvent(wp_a="WP01", wp_b="WP02", rule="dependency", evidence="WP01 depends on WP02"),
            CollapseEvent(wp_a="WP02", wp_b="WP03", rule="dependency", evidence="WP02 depends on WP03"),
        ]
        report = CollapseReport(events=events, independent_wps_collapsed=0)
        counts = report._count_by_rule()
        assert counts == {"dependency": 2}

    def test_count_by_rule_multiple_rules(self):
        """CollapseReport._count_by_rule counts correctly for multiple rules."""
        events = [
            CollapseEvent(wp_a="WP01", wp_b="WP02", rule="dependency", evidence="WP01 depends on WP02"),
            CollapseEvent(wp_a="WP03", wp_b="WP04", rule="write_scope_overlap", evidence="globs: 'src/**' vs 'src/**'"),
            CollapseEvent(wp_a="WP05", wp_b="WP06", rule="surface_heuristic", evidence="shared surfaces ['api']"),
            CollapseEvent(wp_a="WP07", wp_b="WP08", rule="dependency", evidence="WP07 depends on WP08"),
        ]
        report = CollapseReport(events=events, independent_wps_collapsed=2)
        counts = report._count_by_rule()
        assert counts == {
            "dependency": 2,
            "write_scope_overlap": 1,
            "surface_heuristic": 1,
        }

    def test_to_dict_includes_all_keys(self):
        """to_dict() includes events, total_merges, independent_wps_collapsed, by_rule."""
        events = [
            CollapseEvent(wp_a="WP01", wp_b="WP02", rule="dependency", evidence="WP01 depends on WP02"),
        ]
        report = CollapseReport(events=events, independent_wps_collapsed=0)
        d = report.to_dict()
        assert "events" in d
        assert "total_merges" in d
        assert "independent_wps_collapsed" in d
        assert "by_rule" in d

    def test_to_dict_total_merges_matches_events_length(self):
        """total_merges equals len(events)."""
        events = [
            CollapseEvent(wp_a="WP01", wp_b="WP02", rule="dependency", evidence="a"),
            CollapseEvent(wp_a="WP03", wp_b="WP04", rule="write_scope_overlap", evidence="b"),
        ]
        report = CollapseReport(events=events, independent_wps_collapsed=1)
        d = report.to_dict()
        assert d["total_merges"] == 2

    def test_to_dict_events_are_serialized(self):
        """Each event in to_dict()['events'] is a plain dict."""
        event = CollapseEvent(wp_a="WP01", wp_b="WP02", rule="dependency", evidence="WP01 depends on WP02")
        report = CollapseReport(events=[event], independent_wps_collapsed=0)
        d = report.to_dict()
        assert isinstance(d["events"][0], dict)
        assert d["events"][0]["wp_a"] == "WP01"

    def test_independent_wps_collapsed_preserved(self):
        """independent_wps_collapsed value is preserved in to_dict()."""
        report = CollapseReport(events=[], independent_wps_collapsed=5)
        assert report.to_dict()["independent_wps_collapsed"] == 5
