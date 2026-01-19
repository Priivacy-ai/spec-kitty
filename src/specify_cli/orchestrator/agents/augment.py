"""Augment Code invoker.

Implements the AgentInvoker protocol for Augment Code CLI (auggie).
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.orchestrator.agents.base import BaseInvoker, InvocationResult


class AugmentInvoker(BaseInvoker):
    """Invoker for Augment Code CLI (auggie).

    Auggie uses --acp for autonomous coding prompt mode.
    Does not support JSON output - relies on exit code only.
    """

    agent_id = "augment"
    command = "auggie"
    uses_stdin = False  # Prompt passed as argument

    def build_command(
        self,
        prompt: str,
        working_dir: Path,
        role: str,
    ) -> list[str]:
        """Build Auggie command.

        Args:
            prompt: Task prompt (passed as argument).
            working_dir: Directory for execution.
            role: "implementation" or "review".

        Returns:
            Command arguments list.
        """
        cmd = [
            "auggie",
            "--acp",  # Autonomous coding prompt mode
            prompt,  # Prompt as positional argument
        ]

        return cmd

    def parse_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_seconds: float,
    ) -> InvocationResult:
        """Parse Auggie output.

        Auggie doesn't support JSON output, so we rely primarily
        on exit code and parse stdout/stderr for useful information.
        """
        success = exit_code == 0

        # No JSON output - extract what we can from text
        files_modified = self._extract_files_from_text(stdout)
        commits_made = []
        errors = []
        warnings = []

        # Check stderr for errors
        if stderr.strip():
            if not success:
                errors = self._extract_errors_from_output(None, stderr)
            warnings = self._extract_warnings_from_output(None, stderr)

        # Check stdout for error indicators
        if not success and not errors:
            stdout_lower = stdout.lower()
            if "error" in stdout_lower or "failed" in stdout_lower:
                error_lines = [
                    line.strip()
                    for line in stdout.split("\n")
                    if "error" in line.lower() or "failed" in line.lower()
                ]
                errors.extend(error_lines[:3])

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

    def _extract_files_from_text(self, text: str) -> list[str]:
        """Extract file paths mentioned in unstructured text output."""
        files = []
        import re

        # Patterns like "Created file.py", "Modified src/foo.py", etc.
        patterns = [
            r"(?:created|modified|updated|wrote|edited)\s+['\"]?([^\s'\"]+\.\w+)['\"]?",
            r"(?:writing to|saving)\s+['\"]?([^\s'\"]+\.\w+)['\"]?",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            files.extend(matches)

        return list(set(files))
