"""Claude Code invoker.

Implements the AgentInvoker protocol for Claude Code CLI.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.orchestrator.agents.base import BaseInvoker, InvocationResult


class ClaudeInvoker(BaseInvoker):
    """Invoker for Claude Code CLI (claude).

    Claude Code accepts prompts via stdin and supports JSON output format.
    It runs in headless mode with -p flag and can be restricted to specific tools.
    """

    agent_id = "claude-code"
    command = "claude"
    uses_stdin = True

    def build_command(
        self,
        prompt: str,
        working_dir: Path,
        role: str,
    ) -> list[str]:
        """Build Claude Code command.

        Args:
            prompt: Task prompt (passed via stdin, not in command).
            working_dir: Directory for execution.
            role: "implementation" or "review".

        Returns:
            Command arguments list.
        """
        cmd = [
            "claude",
            "-p",  # Headless/print mode (non-interactive)
            "--output-format", "json",  # Structured JSON output
            "--dangerously-skip-permissions",  # Allow all tools without prompts
        ]

        # Restrict tools based on role
        if role == "implementation":
            cmd.extend([
                "--allowedTools",
                "Read,Write,Edit,Bash,Glob,Grep,TodoWrite",
            ])
        elif role == "review":
            # Review should be more read-focused
            cmd.extend([
                "--allowedTools",
                "Read,Glob,Grep,Bash",
            ])

        return cmd

    def parse_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_seconds: float,
    ) -> InvocationResult:
        """Parse Claude Code JSON output.

        Claude outputs conversation turns in JSON format. We extract
        the relevant information from the final state.
        """
        success = exit_code == 0
        data = self._parse_json_output(stdout)

        # Claude-specific JSON structure handling
        files_modified = []
        commits_made = []
        errors = []
        warnings = []

        if data:
            # Check for Claude-specific fields
            if isinstance(data, dict):
                # Extract from result field if present
                result = data.get("result", data)
                if isinstance(result, dict):
                    files_modified = self._extract_files_from_output(result)
                    commits_made = self._extract_commits_from_output(result)

                # Check for error in response
                if "error" in data:
                    errors.append(str(data["error"]))

        # Fall back to stderr for errors
        if not errors and stderr.strip():
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
