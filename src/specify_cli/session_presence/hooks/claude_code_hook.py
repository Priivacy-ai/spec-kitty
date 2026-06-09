"""ClaudeCodeHookRegistrar — manages SessionStart hooks in .claude/settings.json.

Reads the existing settings.json (if any), merges the spec-kitty
``SessionStart`` hook entry idempotently, and writes the result back
atomically.  All unrelated keys and hook entries are preserved.

Contract (from contracts/settings-json-hook.md):

Target structure after ``register()``::

    {
      "hooks": {
        "SessionStart": [
          {
            "hooks": [
              {"type": "command", "command": "<cmd>"}
            ]
          }
        ]
      }
    }

Edge cases handled:
- File absent → treated as ``{}`` → ``register()`` creates it.
- File exists but contains invalid JSON or non-object JSON → original content is
  copied to ``settings.json.invalid*`` before ``register()`` creates a valid
  structure.
- File exists with other ``SessionStart`` entries → all preserved.
- ``unregister()`` on a file where the command is not present → no-op, no
  write performed.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

__all__ = ["ClaudeCodeHookRegistrar"]

_SETTINGS_PATH = ".claude/settings.json"
_SETTINGS_PATH_PARTS = (".claude", "settings.json")
_SESSION_START_KEY = "SessionStart"
_logger = logging.getLogger(__name__)


class ClaudeCodeHookRegistrar:
    """Read/merge/write ``.claude/settings.json`` for the SessionStart hook.

    All writes are atomic: a sibling temp file is written and then swapped
    into place with ``os.replace()``.
    """

    def _settings_path(self, project_root: Path) -> Path:
        root = project_root.expanduser().resolve()
        path = root.joinpath(*_SETTINGS_PATH_PARTS)
        try:
            path.resolve(strict=False).relative_to(root)
        except ValueError as exc:
            msg = "Claude settings path escapes project root"
            raise ValueError(msg) from exc
        return path

    def _create_temp_file(
        self,
        path: Path,
        *,
        suffix: str = "",
        prefix: str | None = None,
    ) -> tuple[Path, int]:
        fd, temp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=path.name if prefix is None else prefix,
            suffix=suffix,
            text=True,
        )
        temp = Path(temp_path)
        temp.relative_to(path.parent)
        return temp, fd

    def _write_fd_text(self, fd: int, text: str) -> None:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)

    def _session_start_entries(self, data: dict[str, object]) -> list[object] | None:
        hooks_section = data.get("hooks")
        if not isinstance(hooks_section, dict):
            return None
        session_start = hooks_section.get(_SESSION_START_KEY)
        if not isinstance(session_start, list):
            return None
        return session_start

    def _iter_command_hooks(self, session_start: list[object]) -> list[dict[str, object]]:
        command_hooks: list[dict[str, object]] = []
        for entry in session_start:
            if not isinstance(entry, dict):
                continue
            entry_hooks = entry.get("hooks")
            if not isinstance(entry_hooks, list):
                continue
            command_hooks.extend(
                hook for hook in entry_hooks if isinstance(hook, dict)
            )
        return command_hooks

    def _load(self, path: Path, *, preserve_invalid: bool = False) -> dict[str, object]:
        """Load JSON object from *path*, returning ``{}`` on absence or invalid data.

        When ``preserve_invalid`` is true, existing malformed/non-object content
        is copied to a sibling ``.invalid`` backup before callers overwrite the
        settings file.  Backup failures are re-raised to prevent silent data loss.
        """
        if not path.exists():
            return {}
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return {}
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            if preserve_invalid:
                self._preserve_invalid(path, text)
            return {}
        if not isinstance(data, dict):
            if preserve_invalid:
                self._preserve_invalid(path, text)
            return {}
        return data

    def _preserve_invalid(self, path: Path, text: str) -> None:
        """Copy invalid settings content to a sibling backup before overwrite."""
        backup, fd = self._create_temp_file(path, prefix=f"{path.name}.invalid.")
        try:
            self._write_fd_text(fd, text)
        except Exception:
            backup.unlink(missing_ok=True)
            raise
        _logger.warning("Preserved invalid Claude settings JSON at %s", backup)

    def _save(self, path: Path, data: dict[str, object]) -> None:
        """Write *data* as JSON to *path* atomically."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp, fd = self._create_temp_file(path, suffix=".tmp")
        try:
            self._write_fd_text(fd, json.dumps(data, indent=2) + "\n")
            os.replace(tmp, path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def is_registered(self, project_root: Path, command: str) -> bool:
        """Return ``True`` when *command* is present in any SessionStart entry."""
        data = self._load(self._settings_path(project_root))
        session_start = self._session_start_entries(data)
        if session_start is None:
            return False
        return any(
            hook.get("type") == "command" and hook.get("command") == command
            for hook in self._iter_command_hooks(session_start)
        )

    def register(self, project_root: Path, command: str) -> None:
        """Add *command* as a SessionStart hook entry (idempotent).

        If the command is already registered, returns immediately without
        writing.  Otherwise appends a new entry and writes atomically.
        """
        if self.is_registered(project_root, command):
            return
        path = self._settings_path(project_root)
        data = self._load(path, preserve_invalid=True)
        # Ensure hooks → SessionStart list exists, then append.
        hooks_section = data.get("hooks")
        if not isinstance(hooks_section, dict):
            hooks_section = {}
            data["hooks"] = hooks_section
        session_start = hooks_section.get(_SESSION_START_KEY)
        if not isinstance(session_start, list):
            session_start = []
            hooks_section[_SESSION_START_KEY] = session_start
        session_start.append(
            {"hooks": [{"type": "command", "command": command}]}
        )
        self._save(path, data)

    def unregister(self, project_root: Path, command: str) -> None:
        """Remove the spec-kitty *command* entry from SessionStart hooks.

        Preserves all other entries and keys.  If the command is not present,
        returns without writing.  If removal empties the list, the key is kept
        with an empty list (never deleted).
        """
        path = self._settings_path(project_root)
        data = self._load(path)
        session_start = self._session_start_entries(data)
        if session_start is None:
            return

        new_entries: list[object] = []
        found = False
        for entry in session_start:
            if not isinstance(entry, dict):
                new_entries.append(entry)
                continue
            entry_hooks = entry.get("hooks")
            if not isinstance(entry_hooks, list):
                new_entries.append(entry)
                continue
            # Filter out the specific command hook from this entry's hooks list.
            filtered: list[object] = [
                h
                for h in entry_hooks
                if not (
                    isinstance(h, dict)
                    and h.get("type") == "command"
                    and h.get("command") == command
                )
            ]
            if len(filtered) < len(entry_hooks):
                found = True
            new_entry: dict[str, object] = {**entry, "hooks": filtered}
            new_entries.append(new_entry)

        if not found:
            # Command was not present — no-op, do not write.
            return

        hooks_section = data.get("hooks")
        if not isinstance(hooks_section, dict):
            msg = "Expected hooks section to be a dict"
            raise TypeError(msg)
        hooks_section[_SESSION_START_KEY] = new_entries
        self._save(path, data)
