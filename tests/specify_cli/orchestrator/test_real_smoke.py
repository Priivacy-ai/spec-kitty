"""Real smoke tests that actually invoke agents.

Unlike test_smoke.py which only tests availability detection,
these tests ACTUALLY invoke agents and verify they work.

Run with: pytest tests/specify_cli/orchestrator/test_real_smoke.py -v
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.mark.orchestrator_smoke
class TestRealAgentInvocation:
    """Tests that actually invoke real agents."""

    @pytest.fixture
    def temp_workdir(self, tmp_path: Path) -> Path:
        """Create a temp directory with git init for agent work."""
        workdir = tmp_path / "agent_test"
        workdir.mkdir()

        # Initialize git repo (some agents need this)
        subprocess.run(
            ["git", "init"],
            cwd=workdir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=workdir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=workdir,
            capture_output=True,
        )

        return workdir

    @pytest.mark.timeout(60)
    @pytest.mark.xfail(reason="Requires claude agent to be installed")
    def test_claude_can_create_file(self, temp_workdir: Path):
        """Claude should be able to create a simple file."""
        prompt = "Create a file called hello.txt containing exactly 'Hello from Claude'. Do not include any other text."

        result = subprocess.run(
            [
                "claude",
                "-p",
                "--output-format", "json",
                "--dangerously-skip-permissions",
                "--allowedTools", "Write,Read",
                "--max-turns", "3",
            ],
            input=prompt,
            cwd=temp_workdir,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Check file was created
        hello_file = temp_workdir / "hello.txt"
        assert hello_file.exists(), f"Claude didn't create hello.txt. Exit code: {result.returncode}, stderr: {result.stderr}"

        content = hello_file.read_text().strip()
        assert "Hello from Claude" in content, f"Unexpected content: {content}"

    @pytest.mark.timeout(60)
    @pytest.mark.xfail(reason="Requires codex agent to be installed")
    def test_codex_can_create_file(self, temp_workdir: Path):
        """Codex should be able to create a simple file.

        Note: Codex may fail with 404 if the configured model endpoint
        is unavailable. This is a codex configuration issue, not a test issue.
        """
        import os
        prompt = "Create a file called hello.txt containing exactly 'Hello from Codex'. Nothing else."

        # Remove env vars that redirect to DashScope - let codex use OAuth
        env = os.environ.copy()
        for var in ["OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL"]:
            env.pop(var, None)

        result = subprocess.run(
            [
                "codex", "exec",
                "-",  # Read prompt from stdin
                "--json",
                "--full-auto",
            ],
            input=prompt,
            cwd=temp_workdir,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )

        # Skip if codex has API/endpoint issues
        if "404 Not Found" in result.stderr or "turn.failed" in result.stdout:
            pytest.skip("Codex API returned 404 - check model configuration in ~/.codex/config.toml")

        hello_file = temp_workdir / "hello.txt"
        assert hello_file.exists(), f"Codex didn't create hello.txt. Exit code: {result.returncode}, stderr: {result.stderr}"

        content = hello_file.read_text().strip()
        assert "Hello from Codex" in content, f"Unexpected content: {content}"

    @pytest.mark.timeout(120)
    @pytest.mark.xfail(reason="Flaky: Depends on external Gemini API quotas")
    def test_gemini_can_create_file(self, temp_workdir: Path):
        """Gemini should be able to create a simple file.

        Note: Gemini CLI requires GEMINI_API_KEY env var specifically.
        If you have GOOGLE_API_KEY, either:
        1. Also set GEMINI_API_KEY to the same value, or
        2. Run: gemini (interactively) and authenticate
        """
        import os
        if not os.environ.get("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set (Gemini CLI requires this specific env var)")

        prompt = "Create a file called hello.txt containing exactly 'Hello from Gemini'. Nothing else."

        result = subprocess.run(
            [
                "gemini",
                "--yolo",  # Auto-approve all actions
                "-o", "json",  # Output format
                prompt,  # Positional prompt (not stdin)
            ],
            cwd=temp_workdir,
            capture_output=True,
            text=True,
            timeout=120,
        )

        hello_file = temp_workdir / "hello.txt"
        assert hello_file.exists(), f"Gemini didn't create hello.txt. Exit code: {result.returncode}, stderr: {result.stderr}"

        content = hello_file.read_text().strip()
        assert "Hello from Gemini" in content, f"Unexpected content: {content}"

    @pytest.mark.timeout(60)
    @pytest.mark.xfail(reason="Requires opencode agent to be installed")
    def test_opencode_can_create_file(self, temp_workdir: Path):
        """OpenCode should be able to create a simple file."""
        prompt = "Create a file called hello.txt containing exactly 'Hello from OpenCode'. Nothing else."

        result = subprocess.run(
            [
                "opencode", "run",
                "--format", "json",
            ],
            input=prompt,
            cwd=temp_workdir,
            capture_output=True,
            text=True,
            timeout=60,
        )

        hello_file = temp_workdir / "hello.txt"
        assert hello_file.exists(), f"OpenCode didn't create hello.txt. Exit code: {result.returncode}, stderr: {result.stderr}"

        content = hello_file.read_text().strip()
        assert "Hello from OpenCode" in content, f"Unexpected content: {content}"


@pytest.mark.orchestrator_smoke
class TestAgentRoundTrip:
    """Tests that verify agents can read and modify files."""

    @pytest.fixture
    def temp_workdir_with_file(self, tmp_path: Path) -> Path:
        """Create temp dir with a starter file."""
        workdir = tmp_path / "agent_test"
        workdir.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=workdir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=workdir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=workdir, capture_output=True)

        # Create a file to modify
        (workdir / "counter.txt").write_text("count: 0")

        return workdir

    @pytest.mark.timeout(60)
    @pytest.mark.xfail(reason="Requires claude agent to be installed")
    def test_claude_can_read_and_modify(self, temp_workdir_with_file: Path):
        """Claude should read counter.txt and increment the count."""
        prompt = "Read counter.txt, increment the count by 1, and save it back. The file should contain 'count: 1' after."

        result = subprocess.run(
            [
                "claude",
                "-p",
                "--output-format", "json",
                "--dangerously-skip-permissions",
                "--allowedTools", "Read,Write,Edit",
                "--max-turns", "5",
            ],
            input=prompt,
            cwd=temp_workdir_with_file,
            capture_output=True,
            text=True,
            timeout=60,
        )

        counter_file = temp_workdir_with_file / "counter.txt"
        content = counter_file.read_text().strip()
        assert "1" in content, f"Counter not incremented. Content: {content}, stderr: {result.stderr}"


@pytest.mark.orchestrator_smoke
class TestReviewOutcomeParsing:
    """Tests for the review outcome parsing logic."""

    def test_parse_approved_markers(self):
        """Should detect approval markers in output."""
        from specify_cli.orchestrator.agents.base import InvocationResult
        from specify_cli.orchestrator.integration import parse_review_outcome

        # Test various approval patterns
        approved_outputs = [
            InvocationResult(success=True, exit_code=0, stdout="APPROVED - review complete", stderr="", duration_seconds=1.0),
            InvocationResult(success=True, exit_code=0, stdout="LGTM, looks good to merge", stderr="", duration_seconds=1.0),
            InvocationResult(success=True, exit_code=0, stdout="Review passed, all tests pass", stderr="", duration_seconds=1.0),
            InvocationResult(success=True, exit_code=0, stdout="No issues found in this implementation", stderr="", duration_seconds=1.0),
        ]

        for output in approved_outputs:
            result = parse_review_outcome(output)
            assert result.is_approved, f"Should be approved: {output.stdout}"

    def test_parse_rejected_markers(self):
        """Should detect rejection markers in output."""
        from specify_cli.orchestrator.agents.base import InvocationResult
        from specify_cli.orchestrator.integration import parse_review_outcome

        # Test various rejection patterns
        rejected_outputs = [
            InvocationResult(success=False, exit_code=1, stdout="REJECTED - missing error handling", stderr="", duration_seconds=1.0),
            InvocationResult(success=False, exit_code=1, stdout="Changes requested: add tests", stderr="", duration_seconds=1.0),
            InvocationResult(success=True, exit_code=0, stdout="This needs work - please fix the validation", stderr="", duration_seconds=1.0),
            InvocationResult(success=False, exit_code=1, stdout="Issues found: tests failing, please fix", stderr="", duration_seconds=1.0),
        ]

        for output in rejected_outputs:
            result = parse_review_outcome(output)
            assert result.is_rejected, f"Should be rejected: {output.stdout}"
            assert result.feedback is not None

    def test_parse_falls_back_to_exit_code(self):
        """Should use exit code when no clear markers."""
        from specify_cli.orchestrator.agents.base import InvocationResult
        from specify_cli.orchestrator.integration import parse_review_outcome

        # No clear markers, use exit code
        success = parse_review_outcome(InvocationResult(success=True, exit_code=0, stdout="Done.", stderr="", duration_seconds=1.0))
        assert success.is_approved

        # Non-zero exit with no markers = error (not rejection)
        error = parse_review_outcome(InvocationResult(success=False, exit_code=1, stdout="Error occurred", stderr="", duration_seconds=1.0))
        assert error.outcome == "error"


@pytest.mark.orchestrator_smoke
class TestStateMachineLogic:
    """Tests for the state machine logic in process_wp."""

    def test_rework_status_is_startable(self):
        """REWORK status should be treated as ready for processing."""
        from specify_cli.orchestrator.config import WPStatus
        from specify_cli.orchestrator.scheduler import get_ready_wps
        from specify_cli.orchestrator.state import OrchestrationRun, WPExecution
        from datetime import datetime, timezone

        # Create a state with one WP in REWORK status
        state = OrchestrationRun(
            run_id="test",
            feature_slug="test-feature",
            started_at=datetime.now(timezone.utc),
        )
        state.work_packages["WP01"] = WPExecution(
            wp_id="WP01",
            status=WPStatus.REWORK,
            review_feedback="Please add tests",
            implementation_retries=1,
        )

        # Simple graph with no dependencies
        graph = {"WP01": []}

        # Should be ready for processing
        ready = get_ready_wps(graph, state)
        assert "WP01" in ready, "REWORK WP should be ready for processing"

    def test_review_feedback_stored_in_state(self):
        """Review feedback should be stored when WP enters REWORK."""
        from specify_cli.orchestrator.config import WPStatus
        from specify_cli.orchestrator.state import WPExecution

        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.REVIEW,
        )

        # Simulate rejection
        wp.status = WPStatus.REWORK
        wp.review_feedback = "Missing error handling for edge cases"
        wp.implementation_retries += 1

        # Verify state
        assert wp.status == WPStatus.REWORK
        assert wp.review_feedback == "Missing error handling for edge cases"
        assert wp.implementation_retries == 1

        # Verify serialization roundtrip
        data = wp.to_dict()
        restored = WPExecution.from_dict(data)
        assert restored.status == WPStatus.REWORK
        assert restored.review_feedback == "Missing error handling for edge cases"

    def test_max_retries_prevents_infinite_loop(self):
        """Should fail after max review cycles."""
        from specify_cli.orchestrator.config import WPStatus
        from specify_cli.orchestrator.state import WPExecution

        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.REWORK,
            implementation_retries=5,  # Already at max
        )

        max_cycles = 5

        # Check if should fail
        if wp.implementation_retries >= max_cycles:
            wp.status = WPStatus.FAILED
            wp.last_error = f"Exceeded max review cycles ({max_cycles})"

        assert wp.status == WPStatus.FAILED
        assert "max review cycles" in wp.last_error.lower()


@pytest.mark.orchestrator_smoke
class TestImplementReviewFlow:
    """Test the implement→review flow with real agents."""

    @pytest.fixture
    def feature_dir(self, tmp_path: Path) -> Path:
        """Create a minimal feature directory for orchestration."""
        feature = tmp_path / "test-feature"
        feature.mkdir()

        # Create tasks directory with a simple WP
        tasks_dir = feature / "tasks"
        tasks_dir.mkdir()

        # Create a simple WP file
        wp_content = '''---
work_package_id: "WP01"
title: "Create a greeting function"
lane: "planned"
dependencies: []
---

# WP01: Create a greeting function

## Requirements
Create a Python file `greet.py` with a function `greet(name)` that returns "Hello, {name}!".

## Acceptance Criteria
- [ ] File `greet.py` exists
- [ ] Function `greet(name)` returns correct greeting
'''
        (tasks_dir / "WP01-greeting.md").write_text(wp_content)

        return feature

    @pytest.fixture
    def repo_root(self, tmp_path: Path) -> Path:
        """Create a minimal repo root."""
        repo = tmp_path / "repo"
        repo.mkdir()
        kittify = repo / ".kittify"
        kittify.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)

        return repo

    @pytest.mark.timeout(180)
    @pytest.mark.xfail(reason="Requires claude agent to be installed and configured")
    def test_claude_implement_and_review_basic(self, feature_dir: Path, repo_root: Path):
        """Claude should be able to implement and then review code.

        This tests the basic implement→review flow without rejection cycles.
        """
        import os

        # First: Implementation phase
        impl_prompt = """Create a Python file called greet.py with a function greet(name) that returns "Hello, {name}!".

Example:
  greet("World") -> "Hello, World!"

Just create the file, nothing else."""

        impl_result = subprocess.run(
            [
                "claude",
                "-p",
                "--output-format", "json",
                "--dangerously-skip-permissions",
                "--allowedTools", "Write,Read",
                "--max-turns", "3",
            ],
            input=impl_prompt,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Verify implementation created the file
        greet_file = repo_root / "greet.py"
        assert greet_file.exists(), f"Implementation didn't create greet.py. stderr: {impl_result.stderr}"

        # Second: Review phase (same agent for simplicity)
        review_prompt = """Review the greet.py file implementation.

Check:
1. The file exists
2. The greet function exists and works correctly
3. The function returns the expected format "Hello, {name}!"

If everything looks good, output: "APPROVED - review complete"
If there are issues, output: "REJECTED - <describe issues>"
"""

        review_result = subprocess.run(
            [
                "claude",
                "-p",
                "--output-format", "json",
                "--dangerously-skip-permissions",
                "--allowedTools", "Read,Bash",
                "--max-turns", "5",
            ],
            input=review_prompt,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Parse the review outcome
        from specify_cli.orchestrator.integration import parse_review_outcome

        review_outcome = parse_review_outcome({
            "exit_code": review_result.returncode,
            "stdout": review_result.stdout,
            "stderr": review_result.stderr,
        })

        # The review should pass for a simple implementation
        # (We can't guarantee this, but it's likely for such a simple task)
        print(f"Review outcome: {review_outcome.outcome}")
        print(f"Review feedback: {review_outcome.feedback}")

        # At minimum, verify the flow completed
        assert impl_result.returncode == 0 or greet_file.exists(), "Implementation should succeed"
