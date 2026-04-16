"""Baseline test capture for Spec Kitty review loop stabilization.

Captures baseline test results at implement time (before the agent starts
coding) when the project explicitly configures a baseline-capable test
command. Results are cached as a committed artifact (baseline-tests.json).
At review time, the review prompt includes a "Baseline Context" section
showing which failures are pre-existing vs. newly introduced.

Design decisions:
- Capture timing: implement time, not claim time.
- Baseline capture is opt-in via ``review.test_command`` in ``.kittify/config.yaml``.
- Supported output formats are parser-specific; JUnit XML is supported today.
- Artifact format: structured JSON with test name, status, one-line error for failures only.
"""
from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BaselineFailure:
    """A single test failure recorded in the baseline."""

    test: str   # fully qualified test name
    error: str  # one-line error summary (max 200 chars)
    file: str   # file:line

    def to_dict(self) -> dict[str, Any]:
        return {"test": self.test, "error": self.error, "file": self.file}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaselineFailure:
        return cls(
            test=data["test"],
            error=data["error"],
            file=data["file"],
        )


@dataclass(frozen=True)
class BaselineTestResult:
    """Baseline test results captured at implement time."""

    wp_id: str
    captured_at: str      # ISO 8601 UTC
    base_branch: str
    base_commit: str      # 7-40 hex chars
    test_runner: str      # "pytest", "custom"
    total: int
    passed: int
    failed: int           # -1 means capture failed (sentinel)
    skipped: int
    failures: tuple[BaselineFailure, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "wp_id": self.wp_id,
            "captured_at": self.captured_at,
            "base_branch": self.base_branch,
            "base_commit": self.base_commit,
            "test_runner": self.test_runner,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "failures": [f.to_dict() for f in self.failures],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaselineTestResult:
        failures = tuple(BaselineFailure.from_dict(f) for f in data.get("failures", []))
        return cls(
            wp_id=data["wp_id"],
            captured_at=data["captured_at"],
            base_branch=data["base_branch"],
            base_commit=data["base_commit"],
            test_runner=data["test_runner"],
            total=data["total"],
            passed=data["passed"],
            failed=data["failed"],
            skipped=data["skipped"],
            failures=failures,
        )

    @classmethod
    def load(cls, path: Path) -> BaselineTestResult | None:
        """Load from JSON file.  Returns None if file doesn't exist.

        Raises ValueError on malformed JSON.
        """
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed baseline JSON at {path}: {exc}") from exc
        return cls.from_dict(data)

    def save(self, path: Path) -> None:
        """Write baseline result as JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def _get_test_command(repo_root: Path) -> tuple[str | None, str | None]:
    """Return configured ``(command_template, output_format)`` or ``(None, None)``.

    The command template may use ``{output_file}`` as a placeholder that will
    be substituted at runtime with the path to the parser-specific output file.
    Baseline capture is intentionally opt-in; when no command is configured,
    callers should skip baseline capture silently.
    """
    config_path = repo_root / ".kittify" / "config.yaml"
    if config_path.exists():
        try:
            from ruamel.yaml import YAML
            yaml = YAML()
            config = yaml.load(config_path)
            if config:
                review_config = config.get("review", {}) or {}
                if "test_command" in review_config:
                    return (
                        review_config["test_command"],
                        review_config.get("test_output_format", "junit_xml"),
                    )
        except Exception as exc:
            logger.warning("Could not read config.yaml: %s", exc)

    return (None, None)


def _parse_junit_xml(junit_xml_path: Path) -> tuple[int, int, int, int, list[BaselineFailure]]:
    """Parse a JUnit XML file and return (total, passed, failed, skipped, failures).

    Handles nested <testsuite> elements via ``root.iter("testcase")``.
    """
    tree = ET.parse(str(junit_xml_path))  # nosec B314 — XML comes from local test-runner output, not network input
    root = tree.getroot()

    failures: list[BaselineFailure] = []
    total = passed = failed = skipped = 0

    for testcase in root.iter("testcase"):
        total += 1
        failure_el = testcase.find("failure")
        error_el = testcase.find("error")
        skip_el = testcase.find("skipped")

        if failure_el is not None or error_el is not None:
            failed += 1
            active_el = failure_el if failure_el is not None else error_el
            assert active_el is not None
            msg = active_el.get("message", "Unknown error") or ""
            # Truncate to one line, max 200 chars
            msg = msg.split("\n")[0][:200]
            classname = testcase.get("classname", "") or ""
            name = testcase.get("name", "") or ""
            test_name = f"{classname}.{name}" if classname else name
            file_attr = testcase.get("file", "unknown") or "unknown"
            line_attr = testcase.get("line", "?") or "?"
            failures.append(BaselineFailure(
                test=test_name,
                error=msg,
                file=f"{file_attr}:{line_attr}",
            ))
        elif skip_el is not None:
            skipped += 1
        else:
            passed += 1

    return total, passed, failed, skipped, failures


def capture_baseline(
    worktree_path: Path,
    base_branch: str,
    wp_id: str,
    mission_slug: str,
    feature_dir: Path,
    wp_slug: str,
    test_command: str | None = None,
) -> BaselineTestResult | None:
    """Capture baseline test results at implement time.

    Creates a temporary git worktree on the base branch, runs the test
    suite, parses JUnit XML output, and saves the result to
    ``feature_dir/tasks/{wp_slug}/baseline-tests.json``.

    Returns the BaselineTestResult on success, or a sentinel result
    (``failed=-1``) if the test suite cannot be run.  Returns the cached
    result if the artifact already exists.

    Args:
        worktree_path: Path to the execution worktree (used to find repo root).
        base_branch: The git branch to run tests against.
        wp_id: Work package ID (e.g. "WP04").
        mission_slug: Mission slug (e.g. "066-review-loop-stabilization").
        feature_dir: Path to the feature directory in kitty-specs/.
        wp_slug: Slug of the WP task file (e.g. "WP04-baseline-test-capture").
        test_command: Optional override for the test command.  If None, reads
            from config; without config, baseline capture is skipped.
    """
    artifact_dir = feature_dir / "tasks" / wp_slug
    artifact_path = artifact_dir / "baseline-tests.json"

    # Return cached result if it already exists (idempotent)
    cached = BaselineTestResult.load(artifact_path)
    if cached is not None:
        logger.info("Baseline already captured for %s — skipping re-capture.", wp_id)
        return cached

    # Locate repo root (parent of .git)
    repo_root = _find_repo_root(worktree_path)
    if repo_root is None:
        logger.warning("Could not find repo root from %s; skipping baseline capture.", worktree_path)
        return _make_sentinel(wp_id, base_branch, "")

    # Determine test command
    if test_command is None:
        test_command, output_format = _get_test_command(repo_root)
    else:
        output_format = "junit_xml"

    if not test_command:
        logger.info("No review.test_command configured; skipping baseline capture for %s.", wp_id)
        return None

    if output_format != "junit_xml":
        logger.info(
            "Baseline capture configured with unsupported output format %r; skipping baseline capture for %s.",
            output_format,
            wp_id,
        )
        return None

    # Resolve base commit hash
    try:
        rev_result = subprocess.run(
            ["git", "rev-parse", base_branch],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if rev_result.returncode != 0:
            logger.warning("Could not resolve base branch %s: %s", base_branch, rev_result.stderr)
            return _make_sentinel(wp_id, base_branch, "")
        base_commit = rev_result.stdout.strip()
    except Exception as exc:
        logger.warning("git rev-parse failed: %s", exc)
        return _make_sentinel(wp_id, base_branch, "")

    # Create temp dir for the worktree and JUnit output
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_worktree = Path(tmp_dir) / "baseline-worktree"
        junit_xml_path = Path(tmp_dir) / "junit.xml"

        # Add temporary worktree on base branch
        try:
            wt_result = subprocess.run(
                ["git", "worktree", "add", str(tmp_worktree), base_branch, "--detach"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if wt_result.returncode != 0:
                logger.warning(
                    "Could not create baseline worktree for %s: %s", base_branch, wt_result.stderr
                )
                return _make_sentinel(wp_id, base_branch, base_commit)
        except Exception as exc:
            logger.warning("git worktree add failed: %s", exc)
            return _make_sentinel(wp_id, base_branch, base_commit)

        try:
            # Build the final command string with output_file substituted
            cmd_str = test_command.format(output_file=str(junit_xml_path))
            try:
                run_result = subprocess.run(
                    cmd_str,
                    shell=True,  # nosec B602 — test_command is user-authored config string, shell required for pipes/redirects
                    cwd=str(tmp_worktree),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=300,  # 5 minute timeout
                )
            except Exception as exc:
                logger.warning("Test command failed to execute: %s", exc)
                return _make_sentinel(wp_id, base_branch, base_commit)

            # Parse JUnit XML (test runners often exit non-zero when tests fail — that's OK)
            if not junit_xml_path.exists():
                logger.warning(
                    "JUnit XML not produced by baseline test run (exit=%d). stderr: %s",
                    run_result.returncode,
                    run_result.stderr[:500],
                )
                return _make_sentinel(wp_id, base_branch, base_commit)

            try:
                total, passed, failed, skipped, failures = _parse_junit_xml(junit_xml_path)
            except Exception as exc:
                logger.warning("Failed to parse JUnit XML: %s", exc)
                return _make_sentinel(wp_id, base_branch, base_commit)

        finally:
            # Always remove the temporary worktree
            try:
                subprocess.run(
                    ["git", "worktree", "remove", str(tmp_worktree), "--force"],
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except Exception as exc:
                logger.warning("Could not remove temporary worktree: %s", exc)

    # Build result
    result = BaselineTestResult(
        wp_id=wp_id,
        captured_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        base_branch=base_branch,
        base_commit=base_commit,
        test_runner="pytest" if "pytest" in test_command else "custom",
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        failures=tuple(failures),
    )
    result.save(artifact_path)
    return result


def load_baseline(path: Path) -> BaselineTestResult | None:
    """Convenience wrapper — delegates to BaselineTestResult.load()."""
    return BaselineTestResult.load(path)


def diff_baseline(
    baseline: BaselineTestResult,
    current_failures: list[BaselineFailure],
) -> tuple[list[BaselineFailure], list[BaselineFailure], list[str]]:
    """Compare baseline failures against current failures.

    Args:
        baseline: The pre-captured baseline result.
        current_failures: List of failures from the current test run.

    Returns:
        A 3-tuple of:
          - pre_existing: failures that existed in the baseline
          - new_failures: failures NOT in baseline (regressions)
          - fixed: test names that failed in baseline but pass now
    """
    # Sentinel baseline: no baseline data — treat everything as new
    if baseline.failed == -1:
        return [], list(current_failures), []

    baseline_test_names = {f.test for f in baseline.failures}
    current_test_names = {f.test for f in current_failures}

    pre_existing: list[BaselineFailure] = []
    new_failures: list[BaselineFailure] = []

    for failure in current_failures:
        if failure.test in baseline_test_names:
            pre_existing.append(failure)
        else:
            new_failures.append(failure)

    fixed: list[str] = [
        f.test for f in baseline.failures if f.test not in current_test_names
    ]

    return pre_existing, new_failures, fixed


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_repo_root(start: Path) -> Path | None:
    """Walk up from start until we find a .git directory or file."""
    current = start.resolve()
    for _ in range(20):  # limit depth
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _make_sentinel(wp_id: str, base_branch: str, base_commit: str) -> BaselineTestResult:
    """Return a sentinel BaselineTestResult indicating capture failure."""
    return BaselineTestResult(
        wp_id=wp_id,
        captured_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        base_branch=base_branch,
        base_commit=base_commit,
        test_runner="pytest",
        total=0,
        passed=0,
        failed=-1,
        skipped=0,
        failures=(),
    )
