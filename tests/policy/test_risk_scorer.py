"""Tests for parallelization risk scorer."""

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.policy.config import RiskPolicyConfig
from specify_cli.policy.risk_scorer import compute_risk_report


def _lane(lane_id, wp_ids, write_scope, parallel_group=0):
    return ExecutionLane(
        lane_id=lane_id,
        wp_ids=tuple(wp_ids),
        write_scope=tuple(write_scope),
        predicted_surfaces=(),
        depends_on_lanes=(),
        parallel_group=parallel_group,
    )


def _manifest(lanes, mission_slug="test"):
    return LanesManifest(
        version=1,
        mission_slug=mission_slug,
        mission_id=mission_slug,
        mission_branch=f"kitty/mission-{mission_slug}",
        target_branch="main",
        lanes=lanes,
        computed_at="2026-04-03T12:00:00Z",
        computed_from="test",
    )


class TestSharedParentDirs:
    def test_same_parent_directory(self):
        """Lanes touching src/views/dashboard.py and src/views/workspace.py share src/views."""
        manifest = _manifest(
            [
                _lane("lane-a", ["WP01"], ["src/views/dashboard.py"]),
                _lane("lane-b", ["WP02"], ["src/views/workspace.py"]),
            ]
        )
        report = compute_risk_report(manifest)
        assert report.overall_score > 0
        assert any("src/views" in d for r in report.lane_pair_risks for d in r.shared_parent_dirs)

    def test_no_shared_parent(self):
        """Lanes in completely different directories have no parent overlap."""
        manifest = _manifest(
            [
                _lane("lane-a", ["WP01"], ["src/core/models.py"]),
                _lane("lane-b", ["WP02"], ["templates/dashboard.html"]),
            ]
        )
        report = compute_risk_report(manifest)
        assert len(report.lane_pair_risks) == 1
        assert report.lane_pair_risks[0].shared_parent_dirs == ()


class TestImportCoupling:
    def test_cross_lane_import_detected(self):
        """Lane-a's WP body references a module owned by lane-b."""
        manifest = _manifest(
            [
                _lane("lane-a", ["WP01"], ["src/specify_cli/views/**"]),
                _lane("lane-b", ["WP02"], ["src/specify_cli/core/models.py"]),
            ]
        )
        wp_bodies = {
            "WP01": "Import the model: from specify_cli.core.models import Feature",
            "WP02": "Define the Feature model class",
        }
        report = compute_risk_report(manifest, wp_bodies=wp_bodies)
        assert any(r.import_coupling for r in report.lane_pair_risks)

    def test_no_cross_references(self):
        manifest = _manifest(
            [
                _lane("lane-a", ["WP01"], ["src/specify_cli/views/**"]),
                _lane("lane-b", ["WP02"], ["src/specify_cli/merge/**"]),
            ]
        )
        wp_bodies = {
            "WP01": "Build the dashboard view",
            "WP02": "Fix the merge engine",
        }
        report = compute_risk_report(manifest, wp_bodies=wp_bodies)
        assert all(len(r.import_coupling) == 0 for r in report.lane_pair_risks)


class TestSharedTestSurface:
    def test_shared_test_file_reference(self):
        """Both lanes' WPs mention the same test file."""
        manifest = _manifest(
            [
                _lane("lane-a", ["WP01"], ["src/views/**"]),
                _lane("lane-b", ["WP02"], ["src/merge/**"]),
            ]
        )
        wp_bodies = {
            "WP01": "Update tests/test_views.py to cover new dashboard",
            "WP02": "Update tests/test_views.py to cover merge changes",
        }
        report = compute_risk_report(manifest, wp_bodies=wp_bodies)
        assert any(r.shared_test_surfaces for r in report.lane_pair_risks)

    def test_test_dirs_in_write_scope(self):
        """Both lanes own test directories."""
        manifest = _manifest(
            [
                _lane("lane-a", ["WP01"], ["src/views/**", "tests/views/**"]),
                _lane("lane-b", ["WP02"], ["src/merge/**", "tests/views/**"]),
            ]
        )
        report = compute_risk_report(manifest)
        assert any(r.shared_test_surfaces for r in report.lane_pair_risks)


class TestOverallScore:
    def test_zero_risk_for_single_lane(self):
        manifest = _manifest([_lane("lane-a", ["WP01"], ["src/**"])])
        report = compute_risk_report(manifest)
        assert report.overall_score == 0.0
        assert report.lane_pair_risks == []

    def test_zero_risk_for_different_parallel_groups(self):
        """Lanes in different parallel groups don't conflict."""
        manifest = _manifest(
            [
                _lane("lane-a", ["WP01"], ["src/views/**"], parallel_group=0),
                _lane("lane-b", ["WP02"], ["src/views/**"], parallel_group=1),
            ]
        )
        report = compute_risk_report(manifest)
        assert report.overall_score == 0.0

    def test_threshold_comparison(self):
        manifest = _manifest(
            [
                _lane("lane-a", ["WP01"], ["src/views/a.py"]),
                _lane("lane-b", ["WP02"], ["src/views/b.py"]),
            ]
        )
        low = compute_risk_report(manifest, policy=RiskPolicyConfig(threshold=0.01))
        high = compute_risk_report(manifest, policy=RiskPolicyConfig(threshold=0.99))
        assert low.exceeds_threshold is True
        assert high.exceeds_threshold is False

    def test_score_bounded_at_one(self):
        """Score never exceeds 1.0 even with many overlapping signals."""
        manifest = _manifest(
            [
                _lane(
                    "lane-a",
                    ["WP01"],
                    [
                        "src/a/x.py",
                        "src/b/x.py",
                        "src/c/x.py",
                        "src/d/x.py",
                        "src/e/x.py",
                        "src/f/x.py",
                        "tests/a/**",
                        "tests/b/**",
                    ],
                ),
                _lane(
                    "lane-b",
                    ["WP02"],
                    [
                        "src/a/y.py",
                        "src/b/y.py",
                        "src/c/y.py",
                        "src/d/y.py",
                        "src/e/y.py",
                        "src/f/y.py",
                        "tests/a/**",
                        "tests/b/**",
                    ],
                ),
            ]
        )
        report = compute_risk_report(manifest)
        assert report.overall_score <= 1.0
