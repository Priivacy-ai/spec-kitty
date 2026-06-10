"""ClaudeCodeHookRegistrar — manages lifecycle hooks in .claude/settings.json.

Reads the existing settings.json (if any), merges the spec-kitty hook entry
for a given lifecycle event (``SessionStart`` or ``Stop``) idempotently, and
writes the result back atomically.  All unrelated keys and hook entries are
preserved.

Contract (from contracts/settings-json-hook.md):

Target structure after ``register()``::

    {
      "hooks": {
        "<event_key>": [
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
- File exists with other entries for the same event → all preserved.
- ``unregister()`` on a file where the command is not present → no-op, no
  write performed.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import uuid4

from specify_cli.core.utils import write_text_within_directory

__all__ = ["ClaudeCodeHookRegistrar", "SESSION_START_EVENT", "STOP_EVENT"]

_SETTINGS_PATH = ".claude/settings.json"
_SETTINGS_PATH_PARTS = (".claude", "settings.json")
SESSION_START_EVENT = "SessionStart"
STOP_EVENT = "Stop"
_logger = logging.getLogger(__name__)


class ClaudeCodeHookRegistrar:
    """Read/merge/write ``.claude/settings.json`` for one lifecycle hook event.

    ``event_key`` selects the hook event this registrar manages
    (``"SessionStart"`` by default, or ``"Stop"``).  All writes are atomic: a
    sibling temp file is written and then swapped into place with
    ``os.replace()``.
    """

    def __init__(self, event_key: str = SESSION_START_EVENT) -> None:
        self._event_key = event_key

    def _settings_path(self, project_root: Path) -> Path:
        root = project_root.expanduser().resolve()
        path = root.joinpath(*_SETTINGS_PATH_PARTS)
        try:
            path.resolve(strict=False).relative_to(root)
        except ValueError as exc:
            msg = "Claude settings path escapes project root"
            raise ValueError(msg) from exc
        return path

    def _event_entries(self, data: dict[str, object]) -> list[object] | None:
        hooks_section = data.get("hooks")
        if not isinstance(hooks_section, dict):
            return None
        entries = hooks_section.get(self._event_key)
        if not isinstance(entries, list):
            return None
        return entries

    def _iter_command_hooks(self, entries: list[object]) -> list[dict[str, object]]:
        command_hooks: list[dict[str, object]] = []
        for entry in entries:
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
        backup = path.parent / f"{path.name}.invalid.{uuid4().hex}"
        write_text_within_directory(backup, text, root=path.parent)
        _logger.warning("Preserved invalid Claude settings JSON at %s", backup)

    def _save(self, path: Path, data: dict[str, object]) -> None:
        """Write *data* as JSON to *path* atomically."""
        write_text_within_directory(
            path,
            json.dumps(data, indent=2) + "\n",
            root=path.parent,
        )

    def is_registered(self, project_root: Path, command: str) -> bool:
        """Return ``True`` when *command* is present in any entry for the event."""
        data = self._load(self._settings_path(project_root))
        entries = self._event_entries(data)
        if entries is None:
            return False
        return any(
            hook.get("type") == "command" and hook.get("command") == command
            for hook in self._iter_command_hooks(entries)
        )

    def register(self, project_root: Path, command: str) -> None:
        """Add *command* as a hook entry for the configured event (idempotent).

        If the command is already registered, returns immediately without
        writing.  Otherwise appends a new entry and writes atomically.
        """
        if self.is_registered(project_root, command):
            return
        path = self._settings_path(project_root)
        data = self._load(path, preserve_invalid=True)
        # Ensure hooks → <event_key> list exists, then append.
        hooks_section = data.get("hooks")
        if not isinstance(hooks_section, dict):
            hooks_section = {}
            data["hooks"] = hooks_section
        entries = hooks_section.get(self._event_key)
        if not isinstance(entries, list):
            entries = []
            hooks_section[self._event_key] = entries
        entries.append(
            {"hooks": [{"type": "command", "command": command}]}
        )
        self._save(path, data)

    def unregister(self, project_root: Path, command: str) -> None:
        """Remove the spec-kitty *command* entry from the configured event hooks.

        Preserves all other entries and keys.  If the command is not present,
        returns without writing.  If removal empties the list, the key is kept
        with an empty list (never deleted).
        """
        path = self._settings_path(project_root)
        data = self._load(path)
        entries = self._event_entries(data)
        if entries is None:
            return

        new_entries: list[object] = []
        found = False
        for entry in entries:
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
        hooks_section[self._event_key] = new_entries
        self._save(path, data)
