"""GitHub Codex invoker.

Implements the AgentInvoker protocol for GitHub Codex CLI.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.orchestrator.agents.base import BaseInvoker, InvocationResult


class CodexInvoker(BaseInvoker):
    """Invoker for GitHub Codex CLI (codex).

    Codex uses `codex exec -` to read prompts from stdin.
    It supports JSON output and fully autonomous execution.
    """

    agent_id = "codex"
    command = "codex"
    uses_stdin = True

    def build_command(
        self,
        prompt: str,
        working_dir: Path,
        role: str,
    ) -> list[str]:
        """Build Codex command.

        Args:
            prompt: Task prompt (passed via stdin with `-`).
            working_dir: Directory for execution.
            role: "implementation" or "review".

        Returns:
            Command arguments list.
        """
        cmd = [
            "codex", "exec",
            "-",  # Read prompt from stdin
            "--json",  # JSON output format
            "--full-auto",  # Fully autonomous mode
        ]

        # Add role-specific flags if needed
        if role == "review":
            # Codex doesn't have a built-in review mode,
            # but we can hint via the prompt structure
            pass

        return cmd

    def parse_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_seconds: float,
    ) -> InvocationResult:
        """Parse Codex JSON output.

        Codex outputs structured JSON with execution results.
        """
        success = exit_code == 0
        data = self._parse_json_output(stdout)

        files_modified = []
        commits_made = []
        errors = []
        warnings = []

        if data:
            # Codex-specific JSON structure
            if isinstance(data, dict):
                # Extract modified files
                files_modified = self._extract_files_from_output(data)

                # Extract commits if any
                commits_made = self._extract_commits_from_output(data)

                # Check for execution errors
                if "status" in data and data["status"] == "error":
                    errors.append(data.get("message", "Unknown error"))
                elif "error" in data:
                    errors.append(str(data["error"]))

                # Extract any warnings
                warnings = self._extract_warnings_from_output(data, stderr)

        # Fall back to stderr for errors
        if not errors and stderr.strip() and not success:
            errors = self._extract_errors_from_output(None, stderr)

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
