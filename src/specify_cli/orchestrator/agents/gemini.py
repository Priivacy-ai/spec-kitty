"""Google Gemini invoker.

Implements the AgentInvoker protocol for Google Gemini CLI.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.orchestrator.agents.base import BaseInvoker, InvocationResult


# Gemini-specific exit codes
GEMINI_EXIT_SUCCESS = 0
GEMINI_EXIT_AUTH_ERROR = 41
GEMINI_EXIT_RATE_LIMIT = 42
GEMINI_EXIT_GENERAL_ERROR = 52
GEMINI_EXIT_INTERRUPTED = 130


class GeminiInvoker(BaseInvoker):
    """Invoker for Google Gemini CLI (gemini).

    Gemini accepts prompts via stdin with -p flag for headless mode.
    It supports JSON output and has specific exit codes for different errors.
    """

    agent_id = "gemini"
    command = "gemini"
    uses_stdin = True

    def build_command(
        self,
        prompt: str,
        working_dir: Path,
        role: str,
    ) -> list[str]:
        """Build Gemini command.

        Args:
            prompt: Task prompt (passed via stdin).
            working_dir: Directory for execution.
            role: "implementation" or "review".

        Returns:
            Command arguments list.
        """
        cmd = [
            "gemini",
            "-p",  # Headless/non-interactive mode
            "--yolo",  # Autonomous mode (no confirmations)
            "--output-format", "json",  # Structured output
        ]

        return cmd

    def parse_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_seconds: float,
    ) -> InvocationResult:
        """Parse Gemini JSON output.

        Handles Gemini-specific exit codes and JSON structure.
        """
        success = exit_code == GEMINI_EXIT_SUCCESS
        data = self._parse_json_output(stdout)

        files_modified = []
        commits_made = []
        errors = []
        warnings = []

        # Handle specific exit codes
        if exit_code == GEMINI_EXIT_AUTH_ERROR:
            errors.append("Gemini authentication error - check GOOGLE_API_KEY")
        elif exit_code == GEMINI_EXIT_RATE_LIMIT:
            errors.append("Gemini rate limit exceeded - wait before retrying")
        elif exit_code == GEMINI_EXIT_GENERAL_ERROR:
            errors.append("Gemini general error")
        elif exit_code == GEMINI_EXIT_INTERRUPTED:
            errors.append("Gemini execution was interrupted")

        if data:
            # Extract file and commit information
            if isinstance(data, dict):
                files_modified = self._extract_files_from_output(data)
                commits_made = self._extract_commits_from_output(data)

                # Check for error in JSON response
                if "error" in data:
                    errors.append(str(data["error"]))
                if "status" in data and data.get("status") == "error":
                    msg = data.get("message", "Unknown Gemini error")
                    errors.append(msg)

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
