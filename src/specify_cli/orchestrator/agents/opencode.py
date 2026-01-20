"""OpenCode invoker.

Implements the AgentInvoker protocol for OpenCode CLI.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.orchestrator.agents.base import BaseInvoker, InvocationResult


class OpenCodeInvoker(BaseInvoker):
    """Invoker for OpenCode CLI (opencode).

    OpenCode is a multi-provider agent that supports various LLM backends.
    Uses `opencode run` subcommand with stdin for prompts.
    """

    agent_id = "opencode"
    command = "opencode"
    uses_stdin = True

    def build_command(
        self,
        prompt: str,
        working_dir: Path,
        role: str,
    ) -> list[str]:
        """Build OpenCode command.

        Args:
            prompt: Task prompt (passed via stdin).
            working_dir: Directory for execution.
            role: "implementation" or "review".

        Returns:
            Command arguments list.
        """
        cmd = [
            "opencode", "run",
            "--agent", "build",  # Use build agent with broad permissions
            "--format", "json",  # JSON output format
        ]

        return cmd

    def parse_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_seconds: float,
    ) -> InvocationResult:
        """Parse OpenCode JSON streaming output.

        OpenCode outputs one JSON event per line with types:
        - step_start, step_finish: workflow markers
        - text: assistant messages
        - tool_use: tool invocations
        - error: error events
        """
        import json

        success = exit_code == 0
        files_modified = []
        commits_made = []
        errors = []
        warnings = []

        # Parse all JSON lines to find errors and extract data
        if stdout.strip():
            for line in stdout.strip().split("\n"):
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    event = json.loads(line)
                    event_type = event.get("type", "")

                    # Check for error events
                    if event_type == "error":
                        error_info = event.get("error", {})
                        error_name = error_info.get("name", "UnknownError")
                        error_data = error_info.get("data", {})
                        error_msg = error_data.get("message", str(error_info))
                        errors.append(f"{error_name}: {error_msg}")
                        success = False

                    # Extract tool results for file modifications
                    elif event_type == "tool_use":
                        part = event.get("part", {})
                        state = part.get("state", {})
                        tool = part.get("tool", "")

                        # Track file edits
                        if tool in ("edit", "write"):
                            input_data = state.get("input", {})
                            file_path = input_data.get("filePath") or input_data.get("file_path")
                            if file_path and file_path not in files_modified:
                                files_modified.append(file_path)

                        # Track commits
                        elif tool == "bash":
                            output = state.get("output", "")
                            if "commit" in state.get("input", {}).get("command", ""):
                                # Extract commit hash if present
                                for word in output.split():
                                    if len(word) == 40 and all(c in "0123456789abcdef" for c in word):
                                        commits_made.append(word[:8])
                                        break

                except json.JSONDecodeError:
                    continue

        # Fall back to stderr for errors
        if not errors and stderr.strip() and not success:
            errors = self._extract_errors_from_output(None, stderr)

        warnings = self._extract_warnings_from_output(None, stderr)

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
