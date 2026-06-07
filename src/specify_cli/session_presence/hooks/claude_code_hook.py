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
- File exists but contains invalid JSON → treated as ``{}`` → ``register()``
  creates a valid structure (previous malformed content is discarded).
- File exists with other ``SessionStart`` entries → all preserved.
- ``unregister()`` on a file where the command is not present → no-op, no
  write performed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

__all__ = ["ClaudeCodeHookRegistrar"]

_SETTINGS_PATH = ".claude/settings.json"
_SESSION_START_KEY = "SessionStart"


class ClaudeCodeHookRegistrar:
    """Read/merge/write ``.claude/settings.json`` for the SessionStart hook.

    All writes are atomic: a sibling temp file is written and then swapped
    into place with ``os.replace()``.
    """

    def _settings_path(self, project_root: Path) -> Path:
        return project_root / _SETTINGS_PATH

    def _load(self, path: Path) -> dict[str, object]:
        """Load JSON from *path*, returning ``{}`` on absence or parse error."""
        if not path.exists():
            return {}
        try:
            return dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, path: Path, data: dict[str, object]) -> None:
        """Write *data* as JSON to *path* atomically."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp, path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def is_registered(self, project_root: Path, command: str) -> bool:
        """Return ``True`` when *command* is present in any SessionStart entry."""
        data = self._load(self._settings_path(project_root))
        hooks_section = data.get("hooks")
        if not isinstance(hooks_section, dict):
            return False
        session_start = hooks_section.get(_SESSION_START_KEY)
        if not isinstance(session_start, list):
            return False
        for entry in session_start:
            if not isinstance(entry, dict):
                continue
            entry_hooks = entry.get("hooks")
            if not isinstance(entry_hooks, list):
                continue
            for hook in entry_hooks:
                if not isinstance(hook, dict):
                    continue
                if hook.get("type") == "command" and hook.get("command") == command:
                    return True
        return False

    def register(self, project_root: Path, command: str) -> None:
        """Add *command* as a SessionStart hook entry (idempotent).

        If the command is already registered, returns immediately without
        writing.  Otherwise appends a new entry and writes atomically.
        """
        if self.is_registered(project_root, command):
            return
        path = self._settings_path(project_root)
        data = self._load(path)
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
        hooks_section = data.get("hooks")
        if not isinstance(hooks_section, dict):
            return
        session_start = hooks_section.get(_SESSION_START_KEY)
        if not isinstance(session_start, list):
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

        hooks_section[_SESSION_START_KEY] = new_entries
        self._save(path, data)
