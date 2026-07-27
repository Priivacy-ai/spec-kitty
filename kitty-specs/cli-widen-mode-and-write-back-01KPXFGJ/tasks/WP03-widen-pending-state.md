---
work_package_id: WP03
title: Widen Pending State (JSONL Sidecar)
dependencies:
- WP02
requirement_refs:
- C-010
- C-011
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
agent: "claude:sonnet-4-7:python-reviewer:reviewer"
shell_pid: "71588"
history:
- date: '2026-04-23T15:43:52Z'
  event: created
agent_profile: python-implementer
authoritative_surface: src/specify_cli/widen/state.py
execution_mode: code_change
mission_slug: cli-widen-mode-and-write-back-01KPXFGJ
model: claude-sonnet-4-7
owned_files:
- src/specify_cli/widen/state.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-implementer
```

---

## Objective

Implement `WidenPendingStore` in `src/specify_cli/widen/state.py` — the per-mission JSONL sidecar that tracks widened questions in `pending-external-input` state (user chose `[c]`ontinue). This store must survive process crashes and support CRUD operations.

---

## Context

**File location:** `kitty-specs/<mission_slug>/widen-pending.jsonl`
**Format:** One `WidenPendingEntry` JSON object per line (newline-delimited JSON).
**Invariants:**
- `decision_id` is unique per file (C-010: duplicate widen disallowed).
- A missing file is equivalent to an empty file (no pending entries).
- Entries are written atomically to avoid partial writes.
**Schema version:** `schema_version: 1`. Validate against `contracts/widen-state.schema.json`.

---

## Branch Strategy

Depends on WP02. Implementation command:
```bash
spec-kitty agent action implement WP03 --agent claude
```

---

## Subtask T011 — Implement `WidenPendingStore` Class

**Purpose:** Core store class backed by a JSONL file in the mission's kitty-specs directory.

**File:** `src/specify_cli/widen/state.py`

```python
from __future__ import annotations
from pathlib import Path
from specify_cli.widen.models import WidenPendingEntry

class WidenPendingStore:
    """JSONL-backed store for pending-external-input widened decisions.

    File path: kitty-specs/<mission_slug>/widen-pending.jsonl
    """

    def __init__(self, repo_root: Path, mission_slug: str) -> None:
        self._path = repo_root / "kitty-specs" / mission_slug / "widen-pending.jsonl"

    @property
    def path(self) -> Path:
        return self._path
```

**Atomic writes:** Use Python's write-then-rename pattern when rewriting the file:
```python
import tempfile, os

def _write_all(self, entries: list[WidenPendingEntry]) -> None:
    self._path.parent.mkdir(parents=True, exist_ok=True)
    tmp = self._path.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(e.model_dump_json() for e in entries) + ("\n" if entries else ""))
    os.replace(tmp, self._path)
```

---

## Subtask T012 — Implement `add_pending()` + `list_pending()`

**Purpose:** Write a new pending entry; read all pending entries.

**Methods:**

```python
def add_pending(self, entry: WidenPendingEntry) -> None:
    """Append entry. Raises ValueError if decision_id already present (C-010)."""
    existing = self.list_pending()
    if any(e.decision_id == entry.decision_id for e in existing):
        raise ValueError(f"Decision {entry.decision_id!r} already pending (duplicate widen disallowed)")
    existing.append(entry)
    self._write_all(existing)

def list_pending(self) -> list[WidenPendingEntry]:
    """Return all pending entries. Returns [] if file absent or empty."""
    if not self._path.exists():
        return []
    entries = []
    for line in self._path.read_text().splitlines():
        line = line.strip()
        if line:
            entries.append(WidenPendingEntry.model_validate_json(line))
    return entries
```

**Error handling in `list_pending()`:** If a line fails to parse (corrupted file), skip it with a warning log rather than crashing. The interview must remain functional even with a corrupted sidecar (C-007).

---

## Subtask T013 — Implement `remove_pending()` + `clear()`

**Purpose:** Remove a resolved entry; empty the store.

```python
def remove_pending(self, decision_id: str) -> None:
    """Remove entry by decision_id. No-op if not present."""
    existing = [e for e in self.list_pending() if e.decision_id != decision_id]
    self._write_all(existing)

def clear(self) -> None:
    """Remove all entries (e.g. at interview completion)."""
    if self._path.exists():
        self._path.unlink()
```

**Note:** `remove_pending()` uses `_write_all()` for atomicity, not append-based deletion. For V1 workloads (at most ~20 entries), full-rewrite is fine.

---

## Subtask T014 — Schema Validation Against JSON Schema

**Purpose:** Provide a validation helper that confirms a serialized entry matches `contracts/widen-state.schema.json`, ensuring schema_version=1 compliance.

**Implementation in `state.py`:**

```python
import json
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "kitty-specs" / "cli-widen-mode-and-write-back-01KPXFGJ" / "contracts" / "widen-state.schema.json"

def validate_entry_schema(entry: WidenPendingEntry) -> None:
    """Validate entry against the bundled JSON Schema. Raises jsonschema.ValidationError on failure.

    For use in tests and the add_pending() path (optional strict mode).
    """
    try:
        import jsonschema
    except ImportError:
        return  # jsonschema optional; skip validation if not installed

    schema = json.loads(_SCHEMA_PATH.read_text())
    data = json.loads(entry.model_dump_json())
    jsonschema.validate(data, schema)
```

**Note:** Schema validation is advisory in production (jsonschema may not be in the runtime deps). It is used in tests to assert compliance. Do NOT add `jsonschema` as a hard production dependency; gate it with `try/except ImportError`.

---

## Definition of Done

- [ ] `WidenPendingStore` in `state.py` with all four public methods.
- [ ] `add_pending()` raises `ValueError` on duplicate `decision_id`.
- [ ] `list_pending()` returns `[]` when file absent.
- [ ] Atomic write-then-rename implemented.
- [ ] `validate_entry_schema()` helper present (gated on jsonschema import).
- [ ] `tests/specify_cli/widen/test_state.py` — round-trip test: add → list → remove → list → verify empty.
- [ ] `mypy src/specify_cli/widen/state.py` exits 0.
- [ ] `ruff check src/specify_cli/widen/state.py` exits 0.

## Risks

- **Corrupted JSONL file:** Handle by skipping malformed lines in `list_pending()` with a logged warning. The interview proceeds without the unreadable entries.
- **Concurrent writes:** V1 assumption: single CLI process per mission. No locking needed.

## Reviewer Guidance

Verify the atomic write uses `os.replace()` (POSIX-atomic on same filesystem). Verify `list_pending()` returns `[]` (not raises) when file is missing. Check that the test does a full JSONL round-trip: serialize, write to disk, read back, deserialize, compare.

## Activity Log

- 2026-04-23T16:21:29Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=71039 – Started implementation via action command
- 2026-04-23T16:25:31Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=71039 – Ready for review: WidenPendingStore JSONL sidecar implemented with add/list/remove/clear + validate_entry_schema; 21 tests pass (ruff+mypy clean)
- 2026-04-23T16:26:20Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=71588 – Started review via action command
- 2026-04-23T16:27:39Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=71588 – Review passed: atomic write (mkstemp+os.replace in same dir, cleanup on BaseException), C-010 duplicate guard verified, corrupted-line recovery tested with WARNING assertion, missing-file returns [] without creation, schema validation gated on ImportError, method signatures match downstream WP contracts. 21/21 tests pass, ruff clean, mypy clean.
