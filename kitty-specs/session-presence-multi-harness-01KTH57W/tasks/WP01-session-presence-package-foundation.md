---
work_package_id: WP01
title: Session Presence Package Foundation
dependencies: []
requirement_refs:
- C-003
- FR-006
- FR-008
- FR-009
- NFR-002
- NFR-003
tracker_refs: []
planning_base_branch: pr/session-presence-multi-harness
merge_target_branch: pr/session-presence-multi-harness
branch_strategy: Planning artifacts for this mission were generated on pr/session-presence-multi-harness. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/session-presence-multi-harness unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: claude
history:
- date: '2026-06-07'
  status: planned
  note: Initial WP creation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/session_presence/
execution_mode: code_change
owned_files:
- src/specify_cli/session_presence/__init__.py
- src/specify_cli/session_presence/content.py
- src/specify_cli/session_presence/upgrade_check.py
- src/specify_cli/session_presence/writers/__init__.py
- src/specify_cli/session_presence/writers/base.py
- src/specify_cli/session_presence/writers/null_writer.py
- src/specify_cli/session_presence/hooks/__init__.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile configures your Python implementation approach for this work package.

---

## Objective

Create the `src/specify_cli/session_presence/` package — the shared foundation for all session presence functionality. By the end of this WP, the package skeleton exists, `SessionPresenceContent` can render an orientation block for all health states, `UpgradeChecker` manages the PyPI version cache (never blocks, never raises), the `Writer` protocol is defined, and `NullWriter` + a skeleton `registry.py` are in place for downstream WPs to build on.

No tests in this WP — WP04 covers all Phase 1 testing. Focus purely on the implementation.

## Context

Spec Kitty has no session presence mechanism. After `spec-kitty init`, AI agents (Claude Code, Cursor, Copilot, etc.) have no awareness that Spec Kitty exists. This package injects an orientation block into each agent's config files so agents know what Spec Kitty is and how to use it from the first session.

This WP creates the foundation. WP02 adds the Claude Code-specific writer. WP03 adds the orchestrating manager and CLI command. Phase 2 (WP05–06) adds the remaining harnesses.

**References**:
- `kitty-specs/session-presence-multi-harness-01KTH57W/spec.md` (FR-006, FR-008, FR-009)
- `kitty-specs/session-presence-multi-harness-01KTH57W/contracts/claude-md-section.md`
- `kitty-specs/session-presence-multi-harness-01KTH57W/contracts/version-cache.md`
- `kitty-specs/session-presence-multi-harness-01KTH57W/data-model.md`

**Implementation command** (no dependencies):
```bash
spec-kitty agent action implement WP01 --agent claude
```

---

## Branch Strategy

- **Planning base branch**: `pr/session-presence-multi-harness`
- **Merge target**: `pr/session-presence-multi-harness`
- **Execution**: Your worktree is allocated by `lanes.json`. Run `spec-kitty agent action implement WP01 --agent claude` from the repo root — it resolves the correct worktree path and branch automatically.

---

## Subtask T001 — Package Init Files

**Purpose**: Create the Python package `__init__.py` files for `session_presence/`, `session_presence/writers/`, and `session_presence/hooks/`. Each must declare `__all__` (C-007).

**Files to create**:
- `src/specify_cli/session_presence/__init__.py`
- `src/specify_cli/session_presence/writers/__init__.py`
- `src/specify_cli/session_presence/hooks/__init__.py`

**`session_presence/__init__.py`** — export the public API:
```python
from __future__ import annotations

from .content import SessionPresenceContent, SECTION_OPEN, SECTION_CLOSE
from .manager import SessionPresenceManager, InstallResult

__all__ = [
    "SessionPresenceContent",
    "SECTION_OPEN",
    "SECTION_CLOSE",
    "SessionPresenceManager",
    "InstallResult",
]
```
(Add exports as other modules are implemented in WP02/WP03.)

**`writers/__init__.py`** and **`hooks/__init__.py`** — minimal with `__all__ = []` initially; downstream WPs will add exports.

**Validation**: `from specify_cli.session_presence import SessionPresenceContent` works after WP01 completes.

---

## Subtask T002 — SessionPresenceContent + render()

**Purpose**: Implement the `SessionPresenceContent` dataclass and its `render()` method. This is the single place where the orientation block text is generated.

**File**: `src/specify_cli/session_presence/content.py`

**Implementation**:
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

SECTION_OPEN  = "<!-- spec-kitty:orientation -->"
SECTION_CLOSE = "<!-- /spec-kitty:orientation -->"

@dataclass(frozen=True)
class SessionPresenceContent:
    version: str
    project_slug: str
    health: Literal["healthy", "upgrade-available", "migration-required"]
    available_version: str | None  # None when cache not yet populated

    def render(self) -> str:
        upgrade_line = (
            f"\n⚠ Upgrade available: {self.available_version} — "
            "run `spec-kitty upgrade --cli` to update."
            if self.health == "upgrade-available" else ""
        )
        migration_line = (
            "\n⚠ Project migration required — run `spec-kitty upgrade` before using missions."
            if self.health == "migration-required" else ""
        )
        return (
            f"{SECTION_OPEN}\n"
            f"**Spec Kitty v{self.version}** — project: {self.project_slug} ({self.health})"
            f"{upgrade_line}{migration_line}\n\n"
            "Two usage patterns:\n"
            "- **Full mission** (spec → plan → tasks → implement → review → merge):\n"
            '  trigger: "spec out", "create a mission", "write a spec", "plan this"\n'
            "  → run `/spec-kitty.specify`\n"
            "- **Lightweight dispatch** (ad-hoc fix, question, or advice — no mission created):\n"
            '  trigger: "hey spec kitty", "use spec kitty to", "spec kitty, fix/do/ask/advise"\n'
            '  → run `spec-kitty do "<request verbatim>"`\n'
            f"{SECTION_CLOSE}\n"
        )
```

**Invariants** (from data-model.md):
- `frozen=True` — value object, never mutated after creation
- `available_version` is `None` only when no cache file exists yet
- When `health == "upgrade-available"`, `available_version` is not `None` and `!= version`

**Validation**: `SessionPresenceContent("3.2.0", "my-project", "healthy", None).render()` produces text starting with `<!-- spec-kitty:orientation -->` and ending with `<!-- /spec-kitty:orientation -->\n`.

---

## Subtask T003 — UpgradeChecker

**Purpose**: Manage the PyPI version cache at `~/.kittify/last-cli-check.json` with a 1-hour TTL. Background refresh only — never blocks the foreground. Never raises on any failure.

**File**: `src/specify_cli/session_presence/upgrade_check.py`

**Cache path and TTL**:
```python
CACHE_PATH = Path.home() / ".kittify" / "last-cli-check.json"
TTL_SECONDS = 3600
```

**`get_available_version() -> str | None`**:
1. Try to read `CACHE_PATH`. If absent or unreadable: return `None`.
2. Parse JSON. If malformed: return `None`.
3. Parse `checked_at` as ISO 8601 datetime. Calculate age in seconds.
4. If age < TTL_SECONDS: return `latest_version` field.
5. If age >= TTL_SECONDS: return last known `latest_version` (stale but better than None).

**`check_in_background() -> None`**:
Spawn a subprocess to refresh the cache. Must be fire-and-forget (never block). Suggested command:
```
uv pip index versions spec-kitty-cli --quiet 2>/dev/null | head -1
```
Fallback: `pip index versions spec-kitty-cli -q 2>/dev/null | head -1`

Implementation sketch:
```python
import subprocess, json, os
from datetime import datetime, timezone
from pathlib import Path

def check_in_background(self) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        script = (
            "import subprocess, json, os; from pathlib import Path; from datetime import datetime, timezone; "
            "r = subprocess.run(['uv','pip','index','versions','spec-kitty-cli','--quiet'], "
            "capture_output=True, text=True, timeout=10); "
            "v = r.stdout.strip().split('\\n')[0] if r.returncode == 0 else None; "
            f"p = Path(r'{CACHE_PATH}'); p.parent.mkdir(parents=True, exist_ok=True); "
            "tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps({'checked_at': datetime.now(timezone.utc).isoformat(), 'latest_version': v})); "
            "os.replace(tmp, p)"
        )
        subprocess.Popen(
            ["python3", "-c", script],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass  # Always silent — background only
```

**Key constraint**: `check_in_background()` must return immediately. The actual network call happens in the child process. Any exception (subprocess not found, permission error, etc.) is swallowed.

**See also**: `contracts/version-cache.md` for the full cache JSON schema.

**Validation**: `UpgradeChecker().get_available_version()` returns `None` (no cache file) without raising; calling `check_in_background()` returns immediately without raising.

---

## Subtask T004 — Writer Protocol

**Purpose**: Define the `Writer` protocol that all harness writers implement. Using `runtime_checkable` allows `isinstance(obj, Writer)` checks in tests.

**File**: `src/specify_cli/session_presence/writers/base.py`

```python
from __future__ import annotations
from typing import Protocol, runtime_checkable
from pathlib import Path
from ..content import SessionPresenceContent

@runtime_checkable
class Writer(Protocol):
    """Protocol for harness-specific session presence writers."""
    harness_key: str

    def can_write(self, project_root: Path) -> bool:
        """Return True when the harness is installed in this project."""
        ...

    def has_presence(self, project_root: Path) -> bool:
        """Return True when session presence is already written for this harness."""
        ...

    def write(self, project_root: Path, content: SessionPresenceContent) -> None:
        """Write the orientation block. Idempotent — safe to call when already present."""
        ...

    def remove(self, project_root: Path) -> None:
        """Remove the orientation block. No-op if not present."""
        ...
```

**`__all__`** in `writers/__init__.py` should include `Writer` after this is created.

---

## Subtask T005 — NullWriter

**Purpose**: No-op `Writer` for harnesses with no known orientation mechanism. Logs at DEBUG level. Returned by `get_writer()` for any unregistered key.

**File**: `src/specify_cli/session_presence/writers/null_writer.py`

```python
from __future__ import annotations
import logging
from dataclasses import dataclass
from pathlib import Path
from .content import SessionPresenceContent  # relative import via writers package

_logger = logging.getLogger(__name__)

@dataclass
class NullWriter:
    """Writer stub for harnesses with no known orientation mechanism."""
    harness_key: str

    def can_write(self, project_root: Path) -> bool:
        return False

    def has_presence(self, project_root: Path) -> bool:
        return False

    def write(self, project_root: Path, content: SessionPresenceContent) -> None:
        _logger.debug("NullWriter: no orientation mechanism for harness %s", self.harness_key)

    def remove(self, project_root: Path) -> None:
        pass
```

Note: Import `SessionPresenceContent` from the parent package (not relative within writers/). Adjust the import path to avoid circular imports: `from specify_cli.session_presence.content import SessionPresenceContent`.

---

## Subtask T006 — Skeleton Registry

**Purpose**: Create `writers/registry.py` with `WRITER_REGISTRY` (all entries → `NullWriter` initially) and `get_writer()`. WP02 updates `claude` → `ClaudeCodeWriter()`. WP05 populates all other harnesses.

**File**: `src/specify_cli/session_presence/writers/registry.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from .null_writer import NullWriter

if TYPE_CHECKING:
    from .base import Writer

# Phase 1 skeleton — WP02 replaces the claude entry
# WP05 populates all remaining entries
WRITER_REGISTRY: dict[str, "Writer"] = {}

def get_writer(agent_key: str) -> "Writer":
    """Return the Writer for the given agent key, or NullWriter if unregistered."""
    return WRITER_REGISTRY.get(agent_key, NullWriter(agent_key))
```

**`__all__`**: `["WRITER_REGISTRY", "get_writer"]`

---

## Definition of Done

- [ ] `src/specify_cli/session_presence/` package structure exists with all `__init__.py` files
- [ ] All `__init__.py` files declare `__all__` (C-007)
- [ ] `SessionPresenceContent.render()` produces correct output for all three health states (validate by inspection)
- [ ] `UpgradeChecker().get_available_version()` returns `None` on first run without raising
- [ ] `UpgradeChecker().check_in_background()` returns immediately without raising
- [ ] `isinstance(NullWriter("x"), Writer)` is `True` (runtime_checkable check)
- [ ] `get_writer("anything")` returns a `NullWriter` instance
- [ ] `ruff check src/specify_cli/session_presence/` passes with zero issues
- [ ] `mypy src/specify_cli/session_presence/` passes with zero issues (mypy --strict)
- [ ] No imports from `src/specify_cli/next/` (C-004)

## Risks

- Circular imports: `session_presence/__init__.py` imports from `manager.py` which doesn't exist yet in WP01. Keep `__init__.py` minimal — only export what this WP creates. WP03 adds `SessionPresenceManager` exports.
- `UpgradeChecker` subprocess: on some platforms (Windows), `start_new_session=True` behaves differently. Use `creationflags=subprocess.DETACHED_PROCESS` on Windows if needed, but wrap in `try/except` regardless.
