"""Base protocol and classes for agent invokers.

This module defines:
    - AgentInvoker Protocol for type checking
    - InvocationResult dataclass for execution results
    - BaseAgentInvoker abstract base class with common functionality
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class InvocationResult:
    """Result of an agent invocation.

    Captures all relevant information from an agent execution including
    success status, output, and any extracted structured data.
    """

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    files_modified: list[str] = field(default_factory=list)
    commits_made: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Telemetry fields (populated by agent invokers when available)
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


@runtime_checkable
class AgentInvoker(Protocol):
    """Protocol defining the interface for agent invokers.

    All agent invokers must implement this protocol to be usable
    by the orchestrator.
    """

    agent_id: str
    command: str
    uses_stdin: bool

    def is_installed(self) -> bool:
        """Check if agent CLI is available on the system."""
        ...

    def build_command(
        self,
        prompt: str,
        working_dir: Path,
        role: str,
    ) -> list[str]:
        """Build the full command with agent-specific flags.

        Args:
            prompt: The task prompt to send to the agent.
            working_dir: Directory where agent should execute.
            role: Either "implementation" or "review".

        Returns:
            List of command arguments for subprocess execution.
        """
        ...

    def parse_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_seconds: float,
    ) -> InvocationResult:
        """Parse agent output into structured result.

        Args:
            stdout: Standard output from the agent process.
            stderr: Standard error from the agent process.
            exit_code: Process exit code.
            duration_seconds: How long the process ran.

        Returns:
            Structured InvocationResult with extracted data.
        """
        ...


class BaseInvoker:
    """Base class with common invoker functionality.

    Provides default implementations for common operations that
    most invokers can inherit.
    """

    agent_id: str = ""
    command: str = ""
    uses_stdin: bool = True

    def is_installed(self) -> bool:
        """Check if agent CLI is available via shutil.which()."""
        return shutil.which(self.command) is not None

    def _parse_json_output(self, stdout: str) -> dict | None:
        """Attempt to parse JSON from agent output.

        Handles both single JSON object and JSONL (one JSON per line) formats.

        Args:
            stdout: Raw stdout from the agent.

        Returns:
            Parsed JSON dict or None if parsing fails.
        """
        if not stdout.strip():
            return None

        # Try parsing as single JSON object
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            pass

        # Try parsing last line as JSON (JSONL format)
        lines = stdout.strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        return None

    def _extract_files_from_output(self, data: dict | None) -> list[str]:
        """Extract list of modified files from parsed JSON output."""
        if not data:
            return []

        # Common field names for file lists
        for key in ["files", "files_modified", "modified_files", "changedFiles"]:
            if key in data and isinstance(data[key], list):
                return [str(f) for f in data[key]]

        return []

    def _extract_commits_from_output(self, data: dict | None) -> list[str]:
        """Extract list of commits from parsed JSON output."""
        if not data:
            return []

        # Common field names for commit lists
        for key in ["commits", "commits_made", "commitShas"]:
            if key in data and isinstance(data[key], list):
                return [str(c) for c in data[key]]

        return []

    def _extract_errors_from_output(
        self, data: dict | None, stderr: str
    ) -> list[str]:
        """Extract errors from parsed JSON output and stderr."""
        errors = []

        if data:
            for key in ["errors", "error"]:
                if key in data:
                    val = data[key]
                    if isinstance(val, list):
                        errors.extend(str(e) for e in val)
                    elif val:
                        errors.append(str(val))

        # Add non-empty stderr lines as potential errors
        if stderr.strip():
            stderr_lines = [
                line.strip()
                for line in stderr.split("\n")
                if line.strip() and not line.startswith("warning")
            ]
            # Only add stderr if it looks like errors (not just logging)
            if any("error" in line.lower() for line in stderr_lines):
                errors.extend(stderr_lines[:5])  # Limit to first 5 lines

        return errors

    def _extract_warnings_from_output(
        self, data: dict | None, stderr: str
    ) -> list[str]:
        """Extract warnings from parsed JSON output and stderr."""
        warnings = []

        if data:
            for key in ["warnings", "warning"]:
                if key in data:
                    val = data[key]
                    if isinstance(val, list):
                        warnings.extend(str(w) for w in val)
                    elif val:
                        warnings.append(str(val))

        # Add warning lines from stderr
        if stderr.strip():
            warnings.extend(
                line.strip()
                for line in stderr.split("\n")
                if line.strip().lower().startswith("warning")
            )

        return warnings

    def parse_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_seconds: float,
    ) -> InvocationResult:
        """Default output parsing implementation.

        Subclasses can override for agent-specific parsing.
        """
        success = exit_code == 0
        data = self._parse_json_output(stdout)

        return InvocationResult(
            success=success,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration_seconds,
            files_modified=self._extract_files_from_output(data),
            commits_made=self._extract_commits_from_output(data),
            errors=self._extract_errors_from_output(data, stderr),
            warnings=self._extract_warnings_from_output(data, stderr),
        )
