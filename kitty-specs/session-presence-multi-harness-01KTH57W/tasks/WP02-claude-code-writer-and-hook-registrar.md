---
work_package_id: WP02
title: Claude Code Writer and Hook Registrar
dependencies:
- WP01
requirement_refs:
- C-002
- C-003
- FR-001
- FR-002
- FR-007
- FR-008
- NFR-003
tracker_refs: []
planning_base_branch: pr/session-presence-multi-harness
merge_target_branch: pr/session-presence-multi-harness
branch_strategy: Planning artifacts for this mission were generated on pr/session-presence-multi-harness. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/session-presence-multi-harness unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "89046"
history:
- date: '2026-06-07'
  status: planned
  note: Initial WP creation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/session_presence/writers/
execution_mode: code_change
owned_files:
- src/specify_cli/session_presence/writers/markdown_rules.py
- src/specify_cli/session_presence/writers/claude_code.py
- src/specify_cli/session_presence/hooks/base.py
- src/specify_cli/session_presence/hooks/claude_code_hook.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Implement the Claude Code-specific session presence writers and hook registrar. By the end of this WP: `MarkdownRulesWriter` handles all Markdown-based harnesses (section append/replace/remove); `ClaudeCodeWriter` extends it and additionally manages the `SessionStart` hook in `.claude/settings.json`; `ClaudeCodeHookRegistrar` reads/merges/writes settings.json atomically while preserving all unrelated hooks.

**Note**: This WP also updates `writers/registry.py` (owned by WP01 skeleton) to wire `claude → ClaudeCodeWriter()`. Since WP01 is merged before this WP starts, the file is safe to modify.

## Context

No existing `settings.json` management infrastructure exists in the codebase. `ClaudeCodeHookRegistrar` is entirely new. The file format and merge semantics are specified in `contracts/settings-json-hook.md`.

**References**:
- `kitty-specs/session-presence-multi-harness-01KTH57W/contracts/claude-md-section.md`
- `kitty-specs/session-presence-multi-harness-01KTH57W/contracts/settings-json-hook.md`
- Spec: FR-001, FR-002, FR-007, FR-008, C-002, C-003, NFR-003

**Implementation command**:
```bash
spec-kitty agent action implement WP02 --agent claude
```

---

## Branch Strategy

- **Planning base branch**: `pr/session-presence-multi-harness`
- **Merge target**: `pr/session-presence-multi-harness`
- **Execution**: Worktree allocated by `lanes.json`. WP01 must be merged before this WP's worktree can branch from the correct base.

---

## Subtask T007 — MarkdownRulesWriter

**Purpose**: Generic writer that manages a `<!-- spec-kitty:orientation --> … <!-- /spec-kitty:orientation -->` section in a Markdown file. Used by Pattern B harnesses and as the base for `ClaudeCodeWriter`.

**File**: `src/specify_cli/session_presence/writers/markdown_rules.py`

**Two modes**:
- `append_mode=True`: section lives within a larger existing file (e.g., CLAUDE.md, GEMINI.md). Append on first write; replace in-place on subsequent writes.
- `append_mode=False`: the file IS the section (e.g., `.cursor/rules/spec-kitty.mdc`). Write the full rendered block as the file's entire content.

```python
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from ..content import SessionPresenceContent, SECTION_OPEN, SECTION_CLOSE

@dataclass
class MarkdownRulesWriter:
    harness_key: str
    rules_path: str       # relative to project_root
    append_mode: bool     # True = section within file; False = own file

    def can_write(self, project_root: Path) -> bool:
        return (project_root / self.rules_path).parent.exists()

    def has_presence(self, project_root: Path) -> bool:
        target = project_root / self.rules_path
        if not target.exists():
            return False
        try:
            return SECTION_OPEN in target.read_text(encoding="utf-8")
        except OSError:
            return False

    def write(self, project_root: Path, content: SessionPresenceContent) -> None:
        target = project_root / self.rules_path
        rendered = content.render()
        if self.append_mode:
            if target.exists():
                existing = target.read_text(encoding="utf-8")
                if SECTION_OPEN in existing:
                    # Replace existing section in-place
                    new_text = _replace_section(existing, rendered)
                else:
                    # Append
                    new_text = existing.rstrip("\n") + "\n\n" + rendered
            else:
                new_text = rendered
        else:
            new_text = rendered
        _atomic_write(target, new_text)

    def remove(self, project_root: Path) -> None:
        target = project_root / self.rules_path
        if not target.exists():
            return
        if self.append_mode:
            existing = target.read_text(encoding="utf-8")
            if SECTION_OPEN not in existing:
                return
            new_text = _remove_section(existing)
            _atomic_write(target, new_text)
        else:
            target.unlink(missing_ok=True)


def _atomic_write(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _replace_section(text: str, replacement: str) -> str:
    """Replace the block from SECTION_OPEN to SECTION_CLOSE (inclusive)."""
    start = text.find(SECTION_OPEN)
    end = text.find(SECTION_CLOSE, start)
    if start == -1 or end == -1:
        return text + "\n\n" + replacement
    end += len(SECTION_CLOSE) + 1  # include the trailing newline
    return text[:start] + replacement + text[end:]


def _remove_section(text: str) -> str:
    start = text.find(SECTION_OPEN)
    end = text.find(SECTION_CLOSE, start)
    if start == -1 or end == -1:
        return text
    end += len(SECTION_CLOSE) + 1
    # Remove preceding blank line if present
    prefix = text[:start].rstrip("\n")
    return (prefix + "\n" + text[end:]).strip("\n") + "\n" if prefix else text[end:]
```

**Atomic writes**: Always use `_atomic_write()` — temp file in same directory, then `os.replace()`. Never write directly to the target.

**Validation**: After `write()`, `has_presence()` returns `True`. After `write()` called twice, file contains exactly one `SECTION_OPEN` marker.

---

## Subtask T008 — ClaudeCodeWriter

**Purpose**: Extends `MarkdownRulesWriter` targeting `.claude/CLAUDE.md` (append_mode=True). Additionally calls `ClaudeCodeHookRegistrar` to register/unregister the SessionStart hook.

**File**: `src/specify_cli/session_presence/writers/claude_code.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from .markdown_rules import MarkdownRulesWriter
from ..content import SessionPresenceContent
from ..hooks.claude_code_hook import ClaudeCodeHookRegistrar

SESSION_START_CMD = "spec-kitty session-start"

@dataclass
class ClaudeCodeWriter(MarkdownRulesWriter):
    harness_key: str = field(default="claude")
    rules_path: str = field(default=".claude/CLAUDE.md")
    append_mode: bool = field(default=True)

    def write(self, project_root: Path, content: SessionPresenceContent) -> None:
        super().write(project_root, content)
        ClaudeCodeHookRegistrar().register(project_root, SESSION_START_CMD)

    def remove(self, project_root: Path) -> None:
        super().remove(project_root)
        ClaudeCodeHookRegistrar().unregister(project_root, SESSION_START_CMD)

    def has_presence(self, project_root: Path) -> bool:
        """Present only when BOTH the CLAUDE.md section AND the hook exist."""
        return (
            super().has_presence(project_root)
            and ClaudeCodeHookRegistrar().is_registered(project_root, SESSION_START_CMD)
        )
```

**Key point**: `has_presence()` requires BOTH artefacts. This means the Phase 1 migration's `detect()` returns True when either is missing.

---

## Subtask T009 — HookRegistrar Protocol

**Purpose**: Protocol for hook registration/unregistration, enabling future harnesses to implement their own hook mechanisms.

**File**: `src/specify_cli/session_presence/hooks/base.py`

```python
from __future__ import annotations
from typing import Protocol
from pathlib import Path

class HookRegistrar(Protocol):
    def register(self, project_root: Path, command: str) -> None: ...
    def unregister(self, project_root: Path, command: str) -> None: ...
    def is_registered(self, project_root: Path, command: str) -> bool: ...
```

---

## Subtask T010 — ClaudeCodeHookRegistrar

**Purpose**: Reads `.claude/settings.json`, merges the spec-kitty `SessionStart` hook entry idempotently (never touches other hooks), writes atomically.

**File**: `src/specify_cli/session_presence/hooks/claude_code_hook.py`

**Contract** (from `contracts/settings-json-hook.md`):
- Hook entry to add: `{"hooks": [{"type": "command", "command": "spec-kitty session-start"}]}`
- Nested under `hooks.SessionStart` list
- `is_registered()` checks for `{"type": "command", "command": cmd}` in any `SessionStart` entry's `hooks` list
- `unregister()` removes only the spec-kitty entry; leaves list as `[]` if empty (never deletes the key)

```python
from __future__ import annotations
import json, os
from pathlib import Path

_SETTINGS_PATH = ".claude/settings.json"
_SESSION_START_KEY = "SessionStart"

class ClaudeCodeHookRegistrar:

    def _settings_path(self, project_root: Path) -> Path:
        return project_root / _SETTINGS_PATH

    def _load(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp, path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def is_registered(self, project_root: Path, command: str) -> bool:
        data = self._load(self._settings_path(project_root))
        for entry in data.get("hooks", {}).get(_SESSION_START_KEY, []):
            for hook in entry.get("hooks", []):
                if hook.get("type") == "command" and hook.get("command") == command:
                    return True
        return False

    def register(self, project_root: Path, command: str) -> None:
        if self.is_registered(project_root, command):
            return
        path = self._settings_path(project_root)
        data = self._load(path)
        data.setdefault("hooks", {}).setdefault(_SESSION_START_KEY, []).append(
            {"hooks": [{"type": "command", "command": command}]}
        )
        self._save(path, data)

    def unregister(self, project_root: Path, command: str) -> None:
        path = self._settings_path(project_root)
        data = self._load(path)
        session_start = data.get("hooks", {}).get(_SESSION_START_KEY, [])
        new_entries = []
        for entry in session_start:
            filtered_hooks = [
                h for h in entry.get("hooks", [])
                if not (h.get("type") == "command" and h.get("command") == command)
            ]
            new_entry = {**entry, "hooks": filtered_hooks}
            new_entries.append(new_entry)
        if "hooks" in data and _SESSION_START_KEY in data["hooks"]:
            data["hooks"][_SESSION_START_KEY] = new_entries
            self._save(path, data)
```

**Edge cases to handle**:
- File absent → treat as `{}` → register creates it
- File exists but contains invalid JSON → treat as `{}` → register creates valid structure
- File exists with other `SessionStart` entries → preserve all of them
- `unregister()` on a file where the command doesn't exist → no-op (no write)

---

## Subtask T011 — Wire claude in Registry

**Purpose**: Update `writers/registry.py` to replace the placeholder for `claude` with `ClaudeCodeWriter()`.

**File**: `src/specify_cli/session_presence/writers/registry.py` (update from WP01 skeleton)

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from .null_writer import NullWriter
from .claude_code import ClaudeCodeWriter

if TYPE_CHECKING:
    from .base import Writer

WRITER_REGISTRY: dict[str, "Writer"] = {
    "claude": ClaudeCodeWriter(),
    # Phase 2 entries added by WP05
}

def get_writer(agent_key: str) -> "Writer":
    return WRITER_REGISTRY.get(agent_key, NullWriter(agent_key))

__all__ = ["WRITER_REGISTRY", "get_writer"]
```

---

## Definition of Done

- [ ] `MarkdownRulesWriter(..., append_mode=True).write()` appends section; second call replaces, not duplicates
- [ ] `MarkdownRulesWriter(..., append_mode=False).write()` writes section as entire file
- [ ] `MarkdownRulesWriter.remove()` strips section; leaves file otherwise intact when append_mode=True
- [ ] `ClaudeCodeWriter().write(root, content)` writes both `.claude/CLAUDE.md` section AND `.claude/settings.json` hook
- [ ] `ClaudeCodeWriter().has_presence(root)` returns False when either artefact is absent
- [ ] `ClaudeCodeHookRegistrar().register()` is idempotent — calling twice produces one entry
- [ ] `ClaudeCodeHookRegistrar().unregister()` removes only the spec-kitty entry; other hooks preserved
- [ ] `ClaudeCodeHookRegistrar()` handles missing settings.json (creates it)
- [ ] `ClaudeCodeHookRegistrar()` handles malformed settings.json (recovers gracefully)
- [ ] `get_writer("claude")` returns a `ClaudeCodeWriter` instance
- [ ] All writes are atomic (temp file + `os.replace()`)
- [ ] Zero ruff issues, zero mypy --strict issues

## Risks

- `os.replace()` on Windows may behave unexpectedly if the target is locked by another process. Wrap in try/except and document that the write may fail silently in this edge case.
- `dataclass` inheritance: `ClaudeCodeWriter` inherits from `MarkdownRulesWriter` using `field(default=...)`. Verify that `dataclasses` handles mutable default field inheritance correctly. Use `field(default_factory=...)` if needed.

## Activity Log

- 2026-06-07T14:59:49Z – claude:sonnet:implementer:implementer – shell_pid=73526 – Assigned agent via action command
- 2026-06-07T15:05:42Z – claude:sonnet:implementer:implementer – shell_pid=73526 – Ready for review
- 2026-06-07T15:06:04Z – claude:sonnet:reviewer:reviewer – shell_pid=89046 – Started review via action command
