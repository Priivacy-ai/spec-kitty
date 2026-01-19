"""Qwen Code invoker.

Implements the AgentInvoker protocol for Qwen Code CLI.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.orchestrator.agents.base import BaseInvoker, InvocationResult


class QwenInvoker(BaseInvoker):
    """Invoker for Qwen Code CLI (qwen).

    Qwen is a fork of Gemini CLI with similar flags.
    Accepts prompts via stdin with -p flag for headless mode.
    """

    agent_id = "qwen"
    command = "qwen"
    uses_stdin = True

    def build_command(
        self,
        prompt: str,
        working_dir: Path,
        role: str,
    ) -> list[str]:
        """Build Qwen command.

        Args:
            prompt: Task prompt (passed via stdin).
            working_dir: Directory for execution.
            role: "implementation" or "review".

        Returns:
            Command arguments list.
        """
        cmd = [
            "qwen",
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
        """Parse Qwen JSON output.

        Similar parsing to Gemini since Qwen is a fork.
        """
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
                if "status" in data and data.get("status") == "error":
                    msg = data.get("message", "Unknown Qwen error")
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
