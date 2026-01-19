"""Cursor invoker.

Implements the AgentInvoker protocol for Cursor CLI with timeout wrapper.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from specify_cli.orchestrator.agents.base import BaseInvoker, InvocationResult


# Exit code from timeout command when process is killed
TIMEOUT_EXIT_CODE = 124


class CursorInvoker(BaseInvoker):
    """Invoker for Cursor CLI (cursor) with timeout wrapper.

    IMPORTANT: Cursor CLI may hang indefinitely, so we ALWAYS wrap it
    with a timeout command to ensure the process eventually terminates.

    Uses `cursor agent` subcommand with -p flag for prompts.
    """

    agent_id = "cursor"
    command = "cursor"
    uses_stdin = False  # Prompt passed as -p argument
    default_timeout = 300  # 5 minutes

    def __init__(self, timeout_seconds: int | None = None):
        """Initialize Cursor invoker.

        Args:
            timeout_seconds: Override default timeout (300s). Must be positive.
        """
        if timeout_seconds is not None and timeout_seconds > 0:
            self.timeout = timeout_seconds
        else:
            self.timeout = self.default_timeout

    def is_installed(self) -> bool:
        """Check if Cursor CLI and timeout command are available."""
        # Need both cursor and timeout to be installed
        return (
            shutil.which(self.command) is not None
            and shutil.which("timeout") is not None
        )

    def build_command(
        self,
        prompt: str,
        working_dir: Path,
        role: str,
    ) -> list[str]:
        """Build Cursor command with timeout wrapper.

        Args:
            prompt: Task prompt (passed as -p argument).
            working_dir: Directory for execution.
            role: "implementation" or "review".

        Returns:
            Command arguments list wrapped with timeout.
        """
        # CRITICAL: Always wrap with timeout to prevent hanging
        cmd = [
            "timeout", str(self.timeout),  # Timeout wrapper
            "cursor", "agent",
            "-p", prompt,  # Prompt as argument
            "--force",  # Autonomous mode (no confirmations)
            "--output-format", "json",  # JSON output
        ]

        return cmd

    def parse_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_seconds: float,
    ) -> InvocationResult:
        """Parse Cursor output.

        Handles the special case of timeout (exit code 124) as a failure.
        """
        # Check for timeout
        if exit_code == TIMEOUT_EXIT_CODE:
            return InvocationResult(
                success=False,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration_seconds,
                files_modified=[],
                commits_made=[],
                errors=[
                    f"Cursor execution timed out after {self.timeout} seconds. "
                    "This is a known issue with Cursor CLI."
                ],
                warnings=[],
            )

        success = exit_code == 0
        data = self._parse_json_output(stdout)

        files_modified = []
        commits_made = []
        errors = []
        warnings = []

        if data:
            if isinstance(data, dict):
                files_modified = self._extract_files_from_output(data)
                commits_made = self._extract_commits_from_output(data)

                # Check for error in JSON response
                if "error" in data:
                    errors.append(str(data["error"]))

        # Fall back to stderr for errors
        if not errors and stderr.strip() and not success:
            errors = self._extract_errors_from_output(None, stderr)

        warnings = self._extract_warnings_from_output(data, stderr)

        return InvocationResult(
            success=success,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration_seconds,
            files_modified=files_modified,
            commits_made=commits_made,
            errors=errors,
            warnings=warnings,
        )
