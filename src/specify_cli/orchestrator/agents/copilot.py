"""GitHub Copilot invoker.

Implements the AgentInvoker protocol for GitHub Copilot CLI.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.orchestrator.agents.base import BaseInvoker, InvocationResult


class CopilotInvoker(BaseInvoker):
    """Invoker for GitHub Copilot CLI (gh copilot).

    Copilot takes prompts as command-line arguments (not stdin).
    It uses the gh CLI extension and runs in autonomous mode with --yolo.
    """

    agent_id = "copilot"
    command = "gh"  # Uses gh CLI with copilot extension
    uses_stdin = False  # Prompt passed as argument

    def is_installed(self) -> bool:
        """Check if gh CLI with copilot extension is available."""
        import shutil
        import subprocess

        # First check if gh is installed
        if not shutil.which("gh"):
            return False

        # Then check if copilot extension is installed
        try:
            result = subprocess.run(
                ["gh", "extension", "list"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            return "copilot" in result.stdout.lower()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

    def build_command(
        self,
        prompt: str,
        working_dir: Path,
        role: str,
    ) -> list[str]:
        """Build Copilot command.

        Args:
            prompt: Task prompt (passed as -p argument).
            working_dir: Directory for execution.
            role: "implementation" or "review".

        Returns:
            Command arguments list.
        """
        cmd = [
            "gh", "copilot",
            "-p", prompt,  # Prompt as argument
            "--yolo",  # Autonomous mode (no confirmations)
            "--silent",  # Minimal output noise
        ]

        return cmd

    def parse_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_seconds: float,
    ) -> InvocationResult:
        """Parse Copilot output.

        Copilot doesn't output structured JSON, so we rely primarily
        on exit code and parse stdout/stderr for useful information.
        """
        success = exit_code == 0

        # Copilot doesn't have structured JSON output
        # We can try to extract file info from stdout text
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
                # Extract error lines from stdout
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
        # Look for common patterns indicating file modifications
        import re

        # Patterns like "Created file.py", "Modified src/foo.py", etc.
        patterns = [
            r"(?:created|modified|updated|wrote|edited)\s+['\"]?([^\s'\"]+\.\w+)['\"]?",
            r"(?:writing to|saving)\s+['\"]?([^\s'\"]+\.\w+)['\"]?",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            files.extend(matches)

        return list(set(files))  # Remove duplicates
