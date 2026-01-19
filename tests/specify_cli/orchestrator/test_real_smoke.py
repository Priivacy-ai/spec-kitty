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
    def test_codex_can_create_file(self, temp_workdir: Path):
        """Codex should be able to create a simple file.

        Note: Codex may fail with 404 if the configured model endpoint
        is unavailable. This is a codex configuration issue, not a test issue.
        """
        prompt = "Create a file called hello.txt containing exactly 'Hello from Codex'. Nothing else."

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
        )

        # Skip if codex has API/endpoint issues
        if "404 Not Found" in result.stderr or "turn.failed" in result.stdout:
            pytest.skip("Codex API returned 404 - check model configuration in ~/.codex/config.toml")

        hello_file = temp_workdir / "hello.txt"
        assert hello_file.exists(), f"Codex didn't create hello.txt. Exit code: {result.returncode}, stderr: {result.stderr}"

        content = hello_file.read_text().strip()
        assert "Hello from Codex" in content, f"Unexpected content: {content}"

    @pytest.mark.timeout(60)
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
            timeout=60,
        )

        hello_file = temp_workdir / "hello.txt"
        assert hello_file.exists(), f"Gemini didn't create hello.txt. Exit code: {result.returncode}, stderr: {result.stderr}"

        content = hello_file.read_text().strip()
        assert "Hello from Gemini" in content, f"Unexpected content: {content}"

    @pytest.mark.timeout(60)
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
