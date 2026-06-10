"""InvocationWriter: append-only JSONL writer for invocation audit trail records."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING

from specify_cli.invocation.errors import AlreadyClosedError, InvocationError, InvocationWriteError
from specify_cli.invocation.record import OpCompletedEvent, OpStartedEvent

if TYPE_CHECKING:
    from glossary.chokepoint import GlossaryObservationBundle

EVENTS_DIR = "kitty-ops"
INDEX_PATH = "kitty-ops/ops-index.jsonl"


def normalise_ref(ref: str, repo_root: Path) -> str:
    """Repo-relative when resolved path is under repo_root; absolute fallback.

    Note: ``Path(ref).resolve()`` follows symlinks. If the caller supplies a
    symlink that points outside the repository, the resolved target will be
    recorded as an absolute path. Operators supplying ``--artifact`` flags are
    responsible for knowing what their links resolve to; the invocation trail
    faithfully records the resolved target.

    See data-model.md §6.
    """
    try:
        path = Path(ref)
        candidate = path if path.is_absolute() else repo_root / path
        resolved = candidate.resolve()
    except (OSError, RuntimeError, ValueError):
        # ValueError can occur on paths with embedded null bytes (Python 3.14+)
        return ref
    root = repo_root.resolve()
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        return str(resolved)


class InvocationWriter:
    """Append-only JSONL writer for per-invocation audit trail files.

    Append-only invariant:
    - ``write_started`` uses exclusive-create mode (``"x"``) — raises on ULID collision.
    - ``write_completed`` uses append mode (``"a"``).
    - No existing line is ever mutated.
    - The already-closed check prevents double-completion without mutating records.
    """

    def __init__(self, repo_root: Path) -> None:
        self._dir = repo_root / EVENTS_DIR

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def invocation_path(self, invocation_id: str) -> Path:
        """Return the JSONL file path for a given invocation_id.

        Filename is invocation_id ONLY — no profile_id prefix.
        This allows profile-invocation complete to work with --invocation-id alone.
        """
        return self._dir / f"{invocation_id}.jsonl"

    def _append_to_index(self, record: OpStartedEvent) -> None:
        """Append a lightweight entry to the invocation index.

        The index at ``kitty-ops/ops-index.jsonl`` stores
        ``{invocation_id, profile_id, started_at}`` per line, newest last.
        It powers the O(limit) reverse-scan in ``invocations list`` so that
        command meets NFR-008 (< 200 ms at 10 K files).

        Errors are silenced — the index is a performance aid.  A missing or
        truncated index causes ``invocations list`` to fall back to directory
        scanning, which is correct but slower.
        """
        index_path = self._dir / "ops-index.jsonl"
        try:
            index_path.parent.mkdir(parents=True, exist_ok=True)
            entry = json.dumps(
                {
                    "invocation_id": record.invocation_id,
                    "profile_id": record.profile_id,
                    "started_at": record.started_at,
                }
            )
            with index_path.open("a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except OSError:
            pass  # index is a performance aid; silently degrade

    def write_started(self, record: OpStartedEvent) -> Path:
        """Write the ``started`` event. Returns the JSONL file path.

        Uses exclusive-create (``"x"`` mode) to detect ULID collision
        (extremely rare but deterministically safe).

        Also appends a lightweight entry to the invocation index at
        ``kitty-ops/ops-index.jsonl`` for fast reverse-scanning
        by ``spec-kitty invocations list``.
        """
        self._ensure_dir()
        path = self.invocation_path(record.invocation_id)
        try:
            # Use "x" mode (exclusive create) to detect ULID collision (extremely rare).
            # None fields (router_confidence, mission_id, wp_id) are omitted.
            with path.open("x", encoding="utf-8") as f:
                f.write(record.to_jsonl_line() + "\n")
        except FileExistsError:
            raise InvocationWriteError(
                f"ULID collision on {path} — retry with a new invocation_id"
            )
        except OSError as e:
            raise InvocationWriteError(f"Failed to write invocation record: {e}") from e
        self._append_to_index(record)
        return path

    def write_completed(self, record: OpCompletedEvent) -> Path:
        """Append the ``completed`` event to an existing invocation file.

        Raises ``AlreadyClosedError`` if a completed event already exists (idempotent guard).
        Raises ``InvocationError`` if the invocation file is not found.
        Raises ``InvocationWriteError`` on filesystem failure.
        """
        path = self.invocation_path(record.invocation_id)
        if not path.exists():
            raise InvocationError(f"Invocation record not found: {record.invocation_id}")

        raw = path.read_text(encoding="utf-8")
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        existing = [json.loads(line) for line in lines]
        if any(entry.get("event") == "completed" for entry in existing):
            raise AlreadyClosedError(record.invocation_id)

        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(record.to_jsonl_line() + "\n")
        except OSError as e:
            raise InvocationWriteError(f"Failed to append completed event: {e}") from e
        return path

    def append_correlation_link(
        self,
        invocation_id: str,
        *,
        kind: str = "artifact",
        ref: str | None = None,
        sha: str | None = None,
        at: str | None = None,
    ) -> None:
        """Append an artifact_link or commit_link event to the invocation JSONL.

        Exactly one of ``ref`` or ``sha`` must be provided:
        - ``ref`` → ``{"event": "artifact_link", "kind": <kind>, "ref": <ref>, ...}``
        - ``sha`` → ``{"event": "commit_link", "sha": <sha>, ...}``

        Raises:
            InvocationError: if the invocation JSONL does not exist.
            ValueError: if neither or both of ref/sha are supplied.
            InvocationWriteError: on filesystem write failure.
        """
        if (ref is None) == (sha is None):
            raise ValueError("Exactly one of ref or sha must be provided")
        path = self.invocation_path(invocation_id)
        if not path.exists():
            raise InvocationError(f"Invocation record not found: {invocation_id}")
        at_ts = at or datetime.datetime.now(datetime.UTC).isoformat()
        entry: dict[str, object] = {
            "event": "artifact_link" if ref is not None else "commit_link",
            "invocation_id": invocation_id,
            "at": at_ts,
        }
        if ref is not None:
            entry["kind"] = kind
            entry["ref"] = ref
        else:
            entry["sha"] = sha
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as e:
            raise InvocationWriteError(
                f"Failed to append correlation event: {e}"
            ) from e

    def write_glossary_observation(
        self, invocation_id: str, bundle: GlossaryObservationBundle
    ) -> None:
        """Append glossary_checked event to invocation file. Best-effort only.

        This event is ONLY written when ``all_conflicts`` is non-empty OR
        ``error_msg`` is set. Clean invocations (no conflicts, no error) produce
        NO ``glossary_checked`` line in the trail — keeping Tier 1 files minimal.

        Readers that encounter an unknown event type may safely skip this line.
        """
        # Skip clean invocations (no conflicts and no error)
        if not bundle.all_conflicts and bundle.error_msg is None:
            return
        try:
            path = self.invocation_path(invocation_id)
            if not path.exists():
                return
            entry: dict[str, object] = {
                "event": "glossary_checked",
                "invocation_id": invocation_id,
            }
            entry.update(bundle.to_dict())
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass
