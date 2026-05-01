"""Widen pending state store.

JSONL-backed store for pending-external-input widened decisions.
Each line is a ``WidenPendingEntry`` serialised to JSON.

File path: ``kitty-specs/<mission_slug>/widen-pending.jsonl``

Design invariants:
- Append-only read/write cycle: ``add_pending()`` reads all entries,
  appends the new one, then atomically rewrites the file via
  ``os.replace()`` (POSIX-atomic on the same filesystem).
- ``remove_pending()`` and ``clear()`` also go through the same
  atomic-rewrite path.
- A missing file is equivalent to an empty store — never raises.
- Corrupted JSONL lines are skipped with a warning; the store remains
  usable (C-007).
- Duplicate ``decision_id`` is rejected at write time (C-010).
- Each write uses a unique tmp filename (``tempfile.mkstemp``) so that
  concurrent callers do not overwrite each other's in-progress tmp file.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path

from specify_cli.widen.models import WidenPendingEntry

logger = logging.getLogger(__name__)

# Path to the bundled JSON Schema for schema-validation helpers (T014).
# Four parents up from state.py → repo root, then into kitty-specs.
_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "kitty-specs"
    / "cli-widen-mode-and-write-back-01KPXFGJ"
    / "contracts"
    / "widen-state.schema.json"
)


class WidenPendingStore:
    """JSONL-backed store for pending-external-input widened decisions.

    File path: ``kitty-specs/<mission_slug>/widen-pending.jsonl``

    Usage::

        store = WidenPendingStore(repo_root=Path("."), mission_slug="my-mission-01ABC")
        store.add_pending(entry)
        entries = store.list_pending()
        store.remove_pending(decision_id)
        store.clear()
    """

    def __init__(self, repo_root: Path, mission_slug: str) -> None:
        self._path = repo_root / "kitty-specs" / mission_slug / "widen-pending.jsonl"

    @property
    def path(self) -> Path:
        """Absolute path to the sidecar JSONL file."""
        return self._path

    # ------------------------------------------------------------------
    # T012 — list_pending / add_pending
    # ------------------------------------------------------------------

    def list_pending(self) -> list[WidenPendingEntry]:
        """Return all entries.  Returns ``[]`` when the file is absent or empty.

        Corrupted lines are skipped with a ``WARNING`` log so the interview
        remains functional even if a line was partially written.
        """
        if not self._path.exists():
            return []
        entries: list[WidenPendingEntry] = []
        raw_text = self._path.read_text(encoding="utf-8")
        for lineno, line in enumerate(raw_text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(WidenPendingEntry.model_validate_json(line))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "widen-pending.jsonl line %d is corrupted and will be skipped: %s",
                    lineno,
                    exc,
                )
        return entries

    def add_pending(self, entry: WidenPendingEntry) -> None:
        """Append *entry* to the store.

        Raises:
            ValueError: if ``entry.decision_id`` is already present (C-010).
        """
        existing = self.list_pending()
        if any(e.decision_id == entry.decision_id for e in existing):
            raise ValueError(
                f"Decision {entry.decision_id!r} already pending "
                "(duplicate widen disallowed per C-010)"
            )
        existing.append(entry)
        self._write_all(existing)

    # ------------------------------------------------------------------
    # T013 — remove_pending / clear
    # ------------------------------------------------------------------

    def remove_pending(self, decision_id: str) -> None:
        """Remove the entry with *decision_id*.  No-op if not present.

        Uses ``_write_all()`` for atomicity (write-then-rename).
        """
        remaining = [e for e in self.list_pending() if e.decision_id != decision_id]
        self._write_all(remaining)

    def clear(self) -> None:
        """Remove *all* entries (e.g. at interview completion)."""
        if self._path.exists():
            self._path.unlink()

    # ------------------------------------------------------------------
    # T011 — _write_all (atomic write-then-rename)
    # ------------------------------------------------------------------

    def _write_all(self, entries: list[WidenPendingEntry]) -> None:
        """Atomically rewrite the sidecar file with *entries*.

        Uses ``tempfile.mkstemp`` in the same directory as the target file
        followed by ``os.replace()`` so:
        - An interrupted process never leaves a partially written file.
        - Each write uses a unique tmp filename, avoiding collisions when two
          callers race (best-effort; full locking is a V2 concern).

        Creates parent directories as needed.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            "\n".join(e.model_dump_json() for e in entries) + "\n" if entries else ""
        )
        fd, tmp_path_str = tempfile.mkstemp(
            dir=self._path.parent, prefix=".widen-pending-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp_path_str, self._path)
        except BaseException:
            # Clean up the orphaned tmp file on any failure
            with contextlib.suppress(OSError):
                os.unlink(tmp_path_str)
            raise


# ------------------------------------------------------------------
# T014 — Schema validation helper (advisory; gated on jsonschema)
# ------------------------------------------------------------------


def validate_entry_schema(entry: WidenPendingEntry) -> None:
    """Validate *entry* against the bundled JSON Schema (``widen-state.schema.json``).

    Raises ``jsonschema.ValidationError`` if validation fails.
    Silently returns if ``jsonschema`` is not installed (optional dep).

    This helper is used in tests and may be called on the ``add_pending()``
    path in strict mode.
    """
    try:
        import jsonschema
    except ImportError:
        return  # jsonschema is optional; skip validation if not installed

    if not _SCHEMA_PATH.exists():
        logger.warning(
            "widen-state.schema.json not found at %s; skipping schema validation",
            _SCHEMA_PATH,
        )
        return

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    data = json.loads(entry.model_dump_json())
    jsonschema.validate(data, schema)
