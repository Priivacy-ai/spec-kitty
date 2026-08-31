"""
GitignoreManager module for protecting AI agent directories.

This module provides a centralized system for managing .gitignore entries
to protect AI agent directories from being accidentally committed to git.
It replaces the fragmented approach where only .codex/ was protected.
"""

import errno
import os
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.state.contract import get_runtime_gitignore_entries


SPEC_KITTY_GITIGNORE_MARKER = "# Added by Spec Kitty CLI (auto-managed)"


class GitignorePathError(Exception):
    """Raised when an ignore file (`.gitignore`, `.claudeignore`) is a symlink.

    `Path.read_text()` / `Path.write_text()` / `Path.exists()` all follow
    symlinks, so an ignore file swapped for a symlink (e.g. by a malicious
    repo checkout) would let a caller's presence/content check, or a write,
    follow it to an arbitrary path. Fail closed instead of following it.
    """


def _open_no_follow(path: Path, flags: int) -> int:
    """Open `path` refusing to follow a symlink at the kernel level.

    An `is_symlink()` check followed by a separate open/read call is a
    check-then-use race: a symlink swapped in between the check and the
    subsequent open would still be followed. `O_NOFOLLOW` (where the
    platform supports it) makes the open itself fail with `ELOOP` when the
    final path component is a symlink, closing that window instead of
    merely detecting it earlier.
    """
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(path, flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise GitignorePathError(f"{path} is a symlink; refusing to read through it") from exc
        raise


def read_ignore_file_text(path: Path, encoding: str = "utf-8-sig") -> str:
    """Read an ignore file's text content, refusing to follow a symlink.

    Used for presence/content checks against `.gitignore`/`.claudeignore`
    (e.g. migration `detect()` logic) that must not be redirected by a
    symlink the way a bare `Path.read_text()`/`.exists()` pair would be.
    Opens through `_open_no_follow()` rather than an `is_symlink()`
    check-then-read, so a symlink swapped in between the check and the read
    cannot be followed either.

    Args:
        path: Path to the ignore file (e.g. `.gitignore` or `.claudeignore`).
        encoding: Text encoding to decode with.

    Returns:
        The file's text content, or `""` if it does not exist.

    Raises:
        GitignorePathError: If `path` is a symlink.
    """
    try:
        fd = _open_no_follow(path, os.O_RDONLY)
    except FileNotFoundError:
        return ""
    with os.fdopen(fd, encoding=encoding) as f:
        return f.read()


def read_gitignore_text(gitignore_path: Path) -> str | None:
    """Read a regular UTF-8 ``.gitignore`` without following a final symlink."""
    if gitignore_path.is_symlink():
        raise GitignorePathError(f"Refusing to read symlinked .gitignore: {gitignore_path}")
    try:
        fd = _open_no_follow(gitignore_path, os.O_RDONLY)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise GitignorePathError(f"Could not safely open .gitignore: {exc}") from exc
    try:
        with os.fdopen(fd, "r", encoding="utf-8-sig", newline="") as handle:
            return handle.read()
    except UnicodeDecodeError as exc:
        raise GitignorePathError(f".gitignore is not valid UTF-8: {exc}") from exc


def write_gitignore_text(gitignore_path: Path, content: str) -> None:
    """Atomically replace a regular ``.gitignore`` without following symlinks."""
    if gitignore_path.is_symlink():
        raise GitignorePathError(f"Refusing to write symlinked .gitignore: {gitignore_path}")

    existing_mode: int | None = None
    if gitignore_path.exists():
        existing_mode = stat.S_IMODE(gitignore_path.stat(follow_symlinks=False).st_mode)
        if not existing_mode & stat.S_IWUSR:
            raise PermissionError(f"Permission denied: {gitignore_path}")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=gitignore_path.parent,
            prefix=".gitignore.spec-kitty-",
            delete=False,
        ) as handle:
            handle.write(content)
            temporary_path = Path(handle.name)
        if existing_mode is not None:
            temporary_path.chmod(existing_mode)
        if gitignore_path.is_symlink():
            raise GitignorePathError(f"Refusing to replace symlinked .gitignore: {gitignore_path}")
        os.replace(temporary_path, gitignore_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@dataclass
class AgentDirectory:
    """Represents a single agent's directory that needs protection."""

    name: str
    """Agent name identifier (e.g., 'claude', 'codex')"""

    directory: str
    """Directory path with trailing slash (e.g., '.claude/')"""

    is_special: bool
    """Indicates if special handling is needed (e.g., .github/)"""

    description: str
    """Human-readable description for documentation"""


@dataclass
class ProtectionResult:
    """Result of a gitignore protection operation."""

    success: bool
    """Whether the operation succeeded"""

    modified: bool
    """Whether .gitignore was modified"""

    entries_added: list[str] = field(default_factory=list)
    """New entries added to .gitignore"""

    entries_skipped: list[str] = field(default_factory=list)
    """Entries already present in .gitignore"""

    errors: list[str] = field(default_factory=list)
    """Error messages if any occurred"""

    warnings: list[str] = field(default_factory=list)
    """Warning messages if any were generated"""


# Registry of all known AI agent directories
AGENT_DIRECTORIES = [
    AgentDirectory("claude", ".claude/", False, "Claude Code CLI"),
    AgentDirectory("codex", ".codex/", False, "Codex (contains auth.json)"),
    AgentDirectory("vibe", ".vibe/", False, "Mistral Vibe (runtime state, config, session logs)"),
    AgentDirectory("pi", ".pi/", False, "Pi (runtime state, auth, session logs)"),
    AgentDirectory("letta", ".letta/", False, "Letta Code (runtime state, auth, memory)"),
    AgentDirectory("opencode", ".opencode/", False, "opencode CLI"),
    AgentDirectory("windsurf", ".windsurf/", False, "Windsurf"),
    AgentDirectory("gemini", ".gemini/", False, "Google Gemini"),
    # Narrow, not blanket .cursor/ (#2498): many teams version-control their
    # own rules under .cursor/rules/, so only Spec Kitty-owned paths under
    # .cursor/ are ignored — mirrors the copilot precedent below. The rules
    # file and the commands dir are written by Spec Kitty today; .cursor/skills/
    # is a *declared* secondary skill root (AGENT_SKILL_CONFIG["cursor"]
    # ["skill_roots"] in core/config.py) that the skill installer does not yet
    # populate (it writes only the primary .agents/skills/ root) — it is ignored
    # for consistency with the canonical config. .cursor/hooks.json is
    # deliberately NOT ignored: it is team-owned and Spec Kitty only writes it
    # on an explicit `agent config set lint_on_edit`.
    AgentDirectory("cursor", ".cursor/rules/spec-kitty.mdc", False, "Cursor (Spec Kitty orientation rule)"),
    AgentDirectory("cursor", ".cursor/commands/", False, "Cursor (Spec Kitty slash commands)"),
    AgentDirectory(
        "cursor",
        ".cursor/skills/",
        False,
        "Cursor (declared Spec Kitty skill root; AGENT_SKILL_CONFIG)",
    ),
    AgentDirectory("qwen", ".qwen/", False, "Qwen"),
    AgentDirectory("kilocode", ".kilocode/", False, "Kilocode"),
    AgentDirectory("auggie", ".augment/", False, "Auggie"),
    # "roo" removed — Roo Code shut down on 2026-05-15 (C-007)
    AgentDirectory("amazonq", ".amazonq/", False, "Amazon Q"),
    AgentDirectory("kiro", ".kiro/", False, "Kiro CLI (rebrand of Amazon Q — registered in PR #626)"),
    AgentDirectory("antigravity", ".agent/", False, "Google Antigravity"),
    AgentDirectory("copilot", ".github/copilot/", True, "GitHub Copilot (user settings)"),
]

# Runtime/generated artifacts that should never be tracked.
# Derived from the state contract -- not hardcoded.
RUNTIME_PROTECTED_ENTRIES = get_runtime_gitignore_entries()


class GitignoreManager:
    """Manages gitignore entries for AI agent directories."""

    def __init__(self, project_path: Path):
        """
        Initialize GitignoreManager with project root path.

        Args:
            project_path: Root directory of the project

        Raises:
            ValueError: If project_path doesn't exist or isn't a directory
        """
        if not isinstance(project_path, Path):
            project_path = Path(project_path)

        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        if not project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")

        self.project_path = project_path
        self.gitignore_path = project_path / ".gitignore"
        self.marker = SPEC_KITTY_GITIGNORE_MARKER
        self._line_ending: str = os.linesep

    def ensure_entries(self, entries: list[str]) -> bool:
        """
        Core method to add entries to .gitignore.

        This method migrates the logic from the original ensure_gitignore_entries
        function, maintaining the same behavior for compatibility.

        Args:
            entries: List of gitignore patterns to add

        Returns:
            True if .gitignore was modified, False otherwise
        """
        if not entries:
            return False

        # Read existing content or start with empty list
        if self.gitignore_path.exists():
            content = self.gitignore_path.read_text(encoding="utf-8-sig")
            # Detect and store line ending style
            self._line_ending = self._detect_line_ending(content)
            lines = content.splitlines()
        else:
            lines = []
            # Use system default for new files
            self._line_ending = os.linesep

        existing = set(lines)
        changed = False

        # Check if any entry needs to be added
        if any(entry not in existing for entry in entries):
            # Add marker if not present
            if self.marker not in existing:
                if lines and lines[-1].strip():
                    lines.append("")  # Add blank line before marker
                lines.append(self.marker)
                existing.add(self.marker)
                changed = True

            # Add missing entries
            for entry in entries:
                if entry not in existing:
                    lines.append(entry)
                    existing.add(entry)
                    changed = True

        # Write back if changed
        if changed:
            # Ensure file ends with newline
            if lines and lines[-1] != "":
                lines.append("")

            # Join with detected line ending
            content = self._line_ending.join(lines)
            self.gitignore_path.write_text(content, encoding="utf-8")

        return changed

    def _detect_line_ending(self, content: str) -> str:
        """
        Detect and return the line ending style used in content.

        Args:
            content: File content to analyze

        Returns:
            Line ending string ('\r\n' for Windows, '\n' for Unix/Mac)
        """
        if "\r\n" in content:
            return "\r\n"
        else:
            return "\n"

    @classmethod
    def get_agent_directories(cls) -> list[AgentDirectory]:
        """
        Get a copy of the registry of all known agent directories.

        Returns:
            List of AgentDirectory objects representing all known agents
        """
        # Return a copy to prevent external modification
        return AGENT_DIRECTORIES.copy()

    def _protect_entries(self, directories: list[str], error_context: str) -> ProtectionResult:
        """
        Shared implementation for adding entries to .gitignore with tracking.

        Args:
            directories: List of gitignore patterns to add
            error_context: Description for error messages (e.g., "agent directories")

        Returns:
            ProtectionResult containing details of the operation
        """
        result = ProtectionResult(success=True, modified=False)

        try:
            # Snapshot existing entries before modification
            existing_before: set[str] = set()
            if self.gitignore_path.exists():
                content = self.gitignore_path.read_text(encoding="utf-8-sig")
                existing_before = set(content.splitlines())

            # Attempt to add entries
            modified = self.ensure_entries(directories)
            result.modified = modified

            # Classify entries as added vs skipped without re-reading the file:
            # ensure_entries() guarantees that after it runs, all requested entries
            # are present. So we just check against the before-snapshot.
            for directory in directories:
                if directory in existing_before:
                    result.entries_skipped.append(directory)
                else:
                    result.entries_added.append(directory)

        except PermissionError:
            result.success = False
            result.errors.append(f"Cannot update .gitignore: Permission denied. Run: chmod u+w {self.gitignore_path}")
        except Exception as exc:
            result.success = False
            result.errors.append(f"Error protecting {error_context}: {exc}")

        return result

    def protect_all_agents(self) -> ProtectionResult:
        """
        Add all known agent directories to .gitignore.

        This is the primary method used during spec-kitty init to ensure
        comprehensive protection of all AI agent directories.

        Also protects runtime-generated files under .kittify/.

        Returns:
            ProtectionResult containing details of the operation
        """
        # Get all agent directories
        all_directories = [agent.directory for agent in AGENT_DIRECTORIES]

        # Add runtime files that should never be tracked
        all_directories.extend(RUNTIME_PROTECTED_ENTRIES)

        return self._protect_entries(all_directories, "agent directories")

    def protect_selected_agents(self, agents: list[str]) -> ProtectionResult:
        """
        Add specific agent directories to .gitignore based on selection.

        Args:
            agents: List of agent names (e.g., ['claude', 'codex', 'opencode'])

        Returns:
            ProtectionResult containing details of the operation
        """
        result = ProtectionResult(success=True, modified=False)

        # Build mapping of agent names to directories. An agent name may own
        # more than one entry (e.g. cursor, #2498), so collect a list per
        # name rather than the last match.
        agent_map: dict[str, list[AgentDirectory]] = {}
        for agent in AGENT_DIRECTORIES:
            agent_map.setdefault(agent.name, []).append(agent)

        # Collect directories for selected agents
        directories_to_add: list[str] = []
        for agent_name in agents:
            if agent_name in agent_map:
                directories_to_add.extend(entry.directory for entry in agent_map[agent_name])
            else:
                result.warnings.append(f"Unknown agent name: {agent_name}")

        if not directories_to_add:
            result.warnings.append("No valid agent directories to add")
            return result

        protection = self._protect_entries(directories_to_add, "selected agents")
        # Merge protection result into result (which may already have warnings)
        result.success = protection.success
        result.modified = protection.modified
        result.entries_added = protection.entries_added
        result.entries_skipped = protection.entries_skipped
        result.errors = protection.errors
        return result
