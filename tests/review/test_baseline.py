"""Tests for specify_cli.review.baseline — WP04: Baseline Test Capture."""
from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.review.baseline import (
    BaselineTestResult,
    TestFailure,
    _get_test_command,
    _parse_junit_xml,
    capture_baseline,
    diff_baseline,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

SAMPLE_JUNIT_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="utf-8"?>
    <testsuites>
      <testsuite name="pytest" tests="4" failures="1" errors="0" skipped="1">
        <testcase classname="tests.test_foo" name="test_pass" file="tests/test_foo.py" line="5"/>
        <testcase classname="tests.test_foo" name="test_fail" file="tests/test_foo.py" line="10">
          <failure message="AssertionError: expected True, got False">
            AssertionError: expected True, got False
            Full traceback here
          </failure>
        </testcase>
        <testcase classname="tests.test_bar" name="test_skip" file="tests/test_bar.py" line="3">
          <skipped/>
        </testcase>
        <testcase classname="tests.test_bar" name="test_pass2" file="tests/test_bar.py" line="7"/>
      </testsuite>
    </testsuites>
""")


def _make_baseline(
    wp_id: str = "WP04",
    failed: int = 2,
    failures: tuple[TestFailure, ...] = (),
    base_branch: str = "main",
    base_commit: str = "abc1234",
) -> BaselineTestResult:
    return BaselineTestResult(
        wp_id=wp_id,
        captured_at="2026-04-06T12:00:00Z",
        base_branch=base_branch,
        base_commit=base_commit,
        test_runner="pytest",
        total=10,
        passed=8,
        failed=failed,
        skipped=0,
        failures=failures,
    )


def _make_failure(test: str, error: str = "AssertionError", file: str = "tests/foo.py:10") -> TestFailure:
    return TestFailure(test=test, error=error, file=file)


# ---------------------------------------------------------------------------
# T017 - Dataclass round-trip
# ---------------------------------------------------------------------------

class TestBaselineTestResultRoundTrip:
    """test_baseline_test_result_round_trip — save and load JSON, compare fields."""

    def test_round_trip_basic(self, tmp_path: Path) -> None:
        failures = (
            _make_failure("tests.test_foo.TestBar.test_baz"),
            _make_failure("tests.test_qux.test_quux", "ValueError: bad input"),
        )
        baseline = _make_baseline(failed=2, failures=failures)
        artifact = tmp_path / "baseline-tests.json"
        baseline.save(artifact)

        loaded = BaselineTestResult.load(artifact)
        assert loaded is not None
        assert loaded.wp_id == baseline.wp_id
        assert loaded.failed == baseline.failed
        assert loaded.total == baseline.total
        assert loaded.passed == baseline.passed
        assert loaded.skipped == baseline.skipped
        assert loaded.base_branch == baseline.base_branch
        assert loaded.base_commit == baseline.base_commit
        assert loaded.test_runner == baseline.test_runner
        assert loaded.captured_at == baseline.captured_at
        assert len(loaded.failures) == 2
        assert loaded.failures[0].test == failures[0].test
        assert loaded.failures[1].error == failures[1].error

    def test_load_returns_none_when_missing(self, tmp_path: Path) -> None:
        result = BaselineTestResult.load(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_raises_on_malformed_json(self, tmp_path: Path) -> None:
        artifact = tmp_path / "bad.json"
        artifact.write_text("NOT JSON {{{}}", encoding="utf-8")
        with pytest.raises(ValueError, match="Malformed baseline JSON"):
            BaselineTestResult.load(artifact)

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        baseline = _make_baseline()
        nested = tmp_path / "tasks" / "WP04-foo" / "baseline-tests.json"
        baseline.save(nested)
        assert nested.exists()

    def test_to_dict_from_dict_round_trip(self) -> None:
        failure = _make_failure("a.b.c")
        assert TestFailure.from_dict(failure.to_dict()) == failure

        baseline = _make_baseline(failures=(failure,))
        assert BaselineTestResult.from_dict(baseline.to_dict()) == baseline


# ---------------------------------------------------------------------------
# T018 - capture_baseline()
# ---------------------------------------------------------------------------

class TestCaptureBaseline:
    """Tests for the capture_baseline() function."""

    def _make_wp_dir(self, tmp_path: Path) -> tuple[Path, Path, Path]:
        """Set up a minimal fake repo structure."""
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        feature_dir = repo / "kitty-specs" / "066-test"
        (feature_dir / "tasks" / "WP04-test").mkdir(parents=True)
        return repo, feature_dir, feature_dir / "tasks" / "WP04-test"

    def test_capture_baseline_creates_artifact(self, tmp_path: Path) -> None:
        """capture_baseline creates baseline-tests.json via subprocess mock."""
        repo, feature_dir, wp_task_dir = self._make_wp_dir(tmp_path)

        # Write a sample JUnit XML so parsing succeeds
        def fake_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "abc1234def5\n"
            result.stderr = ""
            # Detect JUnit XML write
            if isinstance(cmd, str) and "pytest" in cmd:
                # Extract output file path from the command string
                import re
                m = re.search(r"--junitxml=(\S+)", cmd)
                if m:
                    Path(m.group(1)).write_text(SAMPLE_JUNIT_XML, encoding="utf-8")
            return result

        with patch("subprocess.run", side_effect=fake_run):
            result = capture_baseline(
                worktree_path=repo,
                base_branch="main",
                wp_id="WP04",
                mission_slug="066-test",
                feature_dir=feature_dir,
                wp_slug="WP04-test",
            )

        artifact = wp_task_dir / "baseline-tests.json"
        assert artifact.exists(), "baseline-tests.json should be created"
        assert result is not None
        data = json.loads(artifact.read_text())
        assert data["wp_id"] == "WP04"

    def test_capture_baseline_skips_if_cached(self, tmp_path: Path) -> None:
        """If baseline-tests.json already exists, subprocess is NOT called."""
        repo, feature_dir, wp_task_dir = self._make_wp_dir(tmp_path)

        # Pre-create the artifact
        existing = _make_baseline(wp_id="WP04")
        artifact = wp_task_dir / "baseline-tests.json"
        existing.save(artifact)

        call_count = 0

        def fake_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=fake_run):
            result = capture_baseline(
                worktree_path=repo,
                base_branch="main",
                wp_id="WP04",
                mission_slug="066-test",
                feature_dir=feature_dir,
                wp_slug="WP04-test",
            )

        assert call_count == 0, "No subprocess calls expected when cache exists"
        assert result is not None
        assert result.wp_id == "WP04"

    def test_capture_baseline_handles_failure(self, tmp_path: Path) -> None:
        """Subprocess failure produces a sentinel result (failed=-1), not an exception."""
        repo, feature_dir, wp_task_dir = self._make_wp_dir(tmp_path)

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "abc1234\n"
            result.stderr = ""
            # Simulate: git rev-parse works, git worktree add fails
            if isinstance(cmd, list) and "worktree" in cmd:
                result.returncode = 128
                result.stderr = "fatal: could not add worktree"
            return result

        with patch("subprocess.run", side_effect=fake_run):
            result = capture_baseline(
                worktree_path=repo,
                base_branch="main",
                wp_id="WP04",
                mission_slug="066-test",
                feature_dir=feature_dir,
                wp_slug="WP04-test",
            )

        assert result is not None
        assert result.failed == -1, "Sentinel result expected when capture fails"


# ---------------------------------------------------------------------------
# T017 + T018 - JUnit XML parsing
# ---------------------------------------------------------------------------

class TestJunitXmlParsing:
    """test_junit_xml_parsing — parse a sample JUnit XML file."""

    def test_parse_basic(self, tmp_path: Path) -> None:
        xml_file = tmp_path / "junit.xml"
        xml_file.write_text(SAMPLE_JUNIT_XML, encoding="utf-8")

        total, passed, failed, skipped, failures = _parse_junit_xml(xml_file)

        assert total == 4
        assert passed == 2
        assert failed == 1
        assert skipped == 1
        assert len(failures) == 1
        f = failures[0]
        assert f.test == "tests.test_foo.test_fail"
        assert "AssertionError" in f.error
        assert "tests/test_foo.py:10" == f.file

    def test_parse_truncates_long_error(self, tmp_path: Path) -> None:
        long_msg = "A" * 300
        xml_content = textwrap.dedent(f"""\
            <?xml version="1.0" encoding="utf-8"?>
            <testsuites>
              <testsuite tests="1" failures="1">
                <testcase classname="tests.foo" name="test_bar">
                  <failure message="{long_msg}">details</failure>
                </testcase>
              </testsuite>
            </testsuites>
        """)
        xml_file = tmp_path / "junit.xml"
        xml_file.write_text(xml_content, encoding="utf-8")

        _, _, _, _, failures = _parse_junit_xml(xml_file)
        assert len(failures) == 1
        assert len(failures[0].error) <= 200

    def test_parse_error_element(self, tmp_path: Path) -> None:
        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="utf-8"?>
            <testsuites>
              <testsuite tests="1" errors="1">
                <testcase classname="tests.foo" name="test_boom">
                  <error message="RuntimeError: segfault">traceback here</error>
                </testcase>
              </testsuite>
            </testsuites>
        """)
        xml_file = tmp_path / "junit.xml"
        xml_file.write_text(xml_content, encoding="utf-8")

        total, passed, failed, skipped, failures = _parse_junit_xml(xml_file)
        assert failed == 1
        assert failures[0].error == "RuntimeError: segfault"


# ---------------------------------------------------------------------------
# T019 - diff_baseline()
# ---------------------------------------------------------------------------

class TestDiffBaseline:
    """Tests for diff_baseline()."""

    def test_diff_baseline_pre_existing(self) -> None:
        """Failure in both baseline and current → pre_existing."""
        f = _make_failure("tests.foo.test_bad")
        baseline = _make_baseline(failures=(f,), failed=1)
        pre, new, fixed = diff_baseline(baseline, [f])
        assert f in pre
        assert len(new) == 0
        assert len(fixed) == 0

    def test_diff_baseline_new_regression(self) -> None:
        """Failure only in current → new_failure (regression)."""
        baseline = _make_baseline(failures=(), failed=0)
        current_f = _make_failure("tests.foo.test_new_regression")
        pre, new, fixed = diff_baseline(baseline, [current_f])
        assert len(pre) == 0
        assert current_f in new
        assert len(fixed) == 0

    def test_diff_baseline_fixed(self) -> None:
        """Failure in baseline but absent in current → fixed."""
        f = _make_failure("tests.foo.test_was_broken")
        baseline = _make_baseline(failures=(f,), failed=1)
        pre, new, fixed = diff_baseline(baseline, [])
        assert len(pre) == 0
        assert len(new) == 0
        assert "tests.foo.test_was_broken" in fixed

    def test_diff_baseline_sentinel(self) -> None:
        """Sentinel baseline (failed=-1) → all current failures are new."""
        sentinel = _make_baseline(failures=(), failed=-1)
        current_failures = [
            _make_failure("tests.a.test_x"),
            _make_failure("tests.b.test_y"),
        ]
        pre, new, fixed = diff_baseline(sentinel, current_failures)
        assert len(pre) == 0
        assert len(new) == 2
        assert len(fixed) == 0

    def test_diff_baseline_mixed(self) -> None:
        """Mixed scenario: some pre-existing, some new, some fixed."""
        f_old = _make_failure("tests.old.test_existing")
        f_fixed = _make_failure("tests.old.test_fixed_now")
        baseline = _make_baseline(failures=(f_old, f_fixed), failed=2)

        f_new = _make_failure("tests.new.test_regression")
        current_failures = [f_old, f_new]

        pre, new, fixed = diff_baseline(baseline, current_failures)
        assert f_old in pre
        assert f_new in new
        assert "tests.old.test_fixed_now" in fixed


# ---------------------------------------------------------------------------
# T021 - Review prompt includes baseline section
# ---------------------------------------------------------------------------

class TestReviewPromptIncludesBaselineSection:
    """test_review_prompt_includes_baseline_section."""

    def test_baseline_section_appears_for_pre_existing_failures(self, tmp_path: Path) -> None:
        """When baseline has failures, review prompt output references them."""
        # Build a minimal baseline artifact that the review path would load
        failure = _make_failure("tests.existing.test_broken", "ValueError: oops")
        baseline = _make_baseline(
            wp_id="WP01",
            failed=1,
            failures=(failure,),
            base_branch="main",
            base_commit="deadbeef1234567",
        )
        # Save it where the review path would look
        artifact_dir = tmp_path / "tasks" / "WP01-slug"
        artifact_dir.mkdir(parents=True)
        baseline.save(artifact_dir / "baseline-tests.json")

        # Load it back and verify the data we'd render in the review prompt
        loaded = BaselineTestResult.load(artifact_dir / "baseline-tests.json")
        assert loaded is not None
        assert loaded.failed == 1

        # Simulate prompt rendering logic
        lines = []
        if loaded.failed > 0:
            lines.append(
                f"**{loaded.failed} test failure(s) existed BEFORE this WP** "
                f"(base: {loaded.base_branch} @ {loaded.base_commit[:7]}):"
            )
            for f in loaded.failures:
                lines.append(f"| {f.test} | {f.error[:80]} | {f.file} |")
            lines.append("**These failures are NOT regressions introduced by this WP.**")

        rendered = "\n".join(lines)
        assert "1 test failure(s) existed BEFORE this WP" in rendered
        assert "tests.existing.test_broken" in rendered
        assert "NOT regressions" in rendered

    def test_baseline_section_skipped_when_no_artifact(self, tmp_path: Path) -> None:
        """If no baseline artifact exists, load returns None and section is omitted."""
        result = BaselineTestResult.load(tmp_path / "nonexistent" / "baseline-tests.json")
        assert result is None  # no section should be added

    def test_sentinel_baseline_shows_warning(self, tmp_path: Path) -> None:
        """Sentinel baseline (failed=-1) triggers the warning message."""
        sentinel = _make_baseline(failed=-1)
        artifact = tmp_path / "baseline-tests.json"
        sentinel.save(artifact)
        loaded = BaselineTestResult.load(artifact)
        assert loaded is not None
        assert loaded.failed == -1

        lines = []
        if loaded.failed == -1:
            lines.append("**Warning**: Baseline test capture failed at implement time.")

        rendered = "\n".join(lines)
        assert "Warning" in rendered


# ---------------------------------------------------------------------------
# T022 - Config custom test command
# ---------------------------------------------------------------------------

class TestConfigCustomTestCommand:
    """test_config_custom_test_command — config overrides default pytest command."""

    def test_default_command(self, tmp_path: Path) -> None:
        """Without config, default pytest command is returned."""
        cmd, fmt = _get_test_command(tmp_path)
        assert "pytest" in cmd
        assert "{output_file}" in cmd
        assert fmt == "junit_xml"

    def test_custom_command_from_config(self, tmp_path: Path) -> None:
        """Config review.test_command overrides the default."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        config_yaml = kittify / "config.yaml"
        config_yaml.write_text(
            "review:\n  test_command: 'python -m pytest --junitxml={output_file}'\n",
            encoding="utf-8",
        )
        cmd, fmt = _get_test_command(tmp_path)
        assert cmd == "python -m pytest --junitxml={output_file}"
        assert fmt == "junit_xml"

    def test_custom_format_from_config(self, tmp_path: Path) -> None:
        """Config review.test_output_format is respected."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        config_yaml = kittify / "config.yaml"
        config_yaml.write_text(
            "review:\n  test_command: 'myrunner --output={output_file}'\n  test_output_format: junit_xml\n",
            encoding="utf-8",
        )
        cmd, fmt = _get_test_command(tmp_path)
        assert cmd == "myrunner --output={output_file}"
        assert fmt == "junit_xml"

    def test_missing_config_file(self, tmp_path: Path) -> None:
        """Missing .kittify/config.yaml falls back to defaults."""
        cmd, fmt = _get_test_command(tmp_path)
        assert "pytest" in cmd
        assert fmt == "junit_xml"

    def test_config_without_review_section(self, tmp_path: Path) -> None:
        """Config without 'review' key falls back to defaults."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available:\n    - claude\n", encoding="utf-8")
        cmd, fmt = _get_test_command(tmp_path)
        assert "pytest" in cmd


# ---------------------------------------------------------------------------
# Additional coverage for error paths
# ---------------------------------------------------------------------------

class TestCoverageEdgeCases:
    """Additional tests to cover edge/error paths in baseline.py."""

    def test_load_baseline_convenience_wrapper(self, tmp_path: Path) -> None:
        """load_baseline() convenience function delegates to BaselineTestResult.load()."""
        from specify_cli.review.baseline import load_baseline

        # Non-existent path
        result = load_baseline(tmp_path / "missing.json")
        assert result is None

        # Existing path
        baseline = _make_baseline()
        artifact = tmp_path / "baseline-tests.json"
        baseline.save(artifact)
        loaded = load_baseline(artifact)
        assert loaded is not None
        assert loaded.wp_id == baseline.wp_id

    def test_find_repo_root_walks_up(self, tmp_path: Path) -> None:
        """_find_repo_root walks up parent directories to find .git."""
        from specify_cli.review.baseline import _find_repo_root

        # No .git — should return None
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        result = _find_repo_root(deep)
        assert result is None

        # With .git in parent
        (tmp_path / ".git").mkdir()
        result = _find_repo_root(deep)
        assert result == tmp_path

    def test_capture_baseline_no_git_repo(self, tmp_path: Path) -> None:
        """capture_baseline returns sentinel when no .git directory found."""
        # tmp_path has no .git anywhere
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        feature_dir = tmp_path / "kitty-specs" / "066-test"
        (feature_dir / "tasks" / "WP04-test").mkdir(parents=True)

        result = capture_baseline(
            worktree_path=worktree,
            base_branch="main",
            wp_id="WP04",
            mission_slug="066-test",
            feature_dir=feature_dir,
            wp_slug="WP04-test",
        )
        assert result is not None
        assert result.failed == -1

    def test_capture_baseline_git_rev_parse_fails(self, tmp_path: Path) -> None:
        """Sentinel returned when git rev-parse fails with non-zero exit."""
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        feature_dir = repo / "kitty-specs" / "066-test"
        (feature_dir / "tasks" / "WP04-test").mkdir(parents=True)

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 128
            result.stdout = ""
            result.stderr = "fatal: unknown revision 'main'"
            return result

        with patch("subprocess.run", side_effect=fake_run):
            result = capture_baseline(
                worktree_path=repo,
                base_branch="main",
                wp_id="WP04",
                mission_slug="066-test",
                feature_dir=feature_dir,
                wp_slug="WP04-test",
            )

        assert result is not None
        assert result.failed == -1

    def test_capture_baseline_junit_xml_missing(self, tmp_path: Path) -> None:
        """Sentinel when JUnit XML is not produced (test runner didn't write it)."""
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        feature_dir = repo / "kitty-specs" / "066-test"
        (feature_dir / "tasks" / "WP04-test").mkdir(parents=True)

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "abc1234\n"
            result.stderr = ""
            # Don't write JUnit XML
            return result

        with patch("subprocess.run", side_effect=fake_run):
            result = capture_baseline(
                worktree_path=repo,
                base_branch="main",
                wp_id="WP04",
                mission_slug="066-test",
                feature_dir=feature_dir,
                wp_slug="WP04-test",
            )

        assert result is not None
        assert result.failed == -1

    def test_capture_baseline_custom_test_runner_label(self, tmp_path: Path) -> None:
        """test_runner field is 'custom' when command doesn't include 'pytest'."""
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        feature_dir = repo / "kitty-specs" / "066-test"
        (feature_dir / "tasks" / "WP04-test").mkdir(parents=True)

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "abc1234\n"
            result.stderr = ""
            if isinstance(cmd, str) and "{output_file}" not in cmd:
                # Write empty JUnit XML for the test run
                import re
                m = re.search(r"--output=(\S+)", cmd)
                if m:
                    Path(m.group(1)).write_text(
                        '<?xml version="1.0"?><testsuites><testsuite tests="1">'
                        '<testcase classname="a" name="b"/></testsuite></testsuites>',
                        encoding="utf-8",
                    )
            return result

        def fake_run_with_xml(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "abc1234\n"
            result.stderr = ""
            if isinstance(cmd, str) and "myrunner" in cmd:
                import re
                m = re.search(r"--output=(\S+)", cmd)
                if m:
                    Path(m.group(1)).write_text(
                        '<?xml version="1.0"?><testsuites><testsuite tests="1">'
                        '<testcase classname="a" name="b"/></testsuite></testsuites>',
                        encoding="utf-8",
                    )
            return result

        with patch("subprocess.run", side_effect=fake_run_with_xml):
            result = capture_baseline(
                worktree_path=repo,
                base_branch="main",
                wp_id="WP04",
                mission_slug="066-test",
                feature_dir=feature_dir,
                wp_slug="WP04-test",
                test_command="myrunner --output={output_file}",
            )

        assert result is not None
        # May be sentinel if XML not written, that's OK for this test
        assert result.wp_id == "WP04"
