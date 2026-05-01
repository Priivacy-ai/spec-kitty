"""Atomic round-trip writer for retrospective.yaml.

Uses ruamel.yaml round-trip dumper for stable byte output, and os.replace
for atomic rename so a crash never leaves a partially-written canonical file.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

from ruamel.yaml import YAML

from specify_cli.retrospective.schema import RetrospectiveRecord
import contextlib


class WriterError(Exception):
    """Raised when the writer cannot persist a retrospective record."""


def write_record(record: RetrospectiveRecord, *, repo_root: Path) -> Path:
    """Atomically write a retrospective record to its canonical path.

    Steps:
    1. Validate the record via a Pydantic round-trip.
    2. Compute canonical path: <repo_root>/.kittify/missions/<mission_id>/retrospective.yaml
    3. Create the target directory if needed.
    4. Serialize via ruamel.yaml round-trip dumper to a tempfile in the same directory.
    5. fsync() the tempfile, close.
    6. os.replace(tmp, canonical)  — atomic on POSIX/APFS.
    7. Best-effort fsync() on the parent directory fd.

    Returns the absolute canonical path that was written.

    Raises:
        WriterError: record has status='pending', validation fails, or an IO error occurs.
    """
    # Refuse pending records before doing any I/O.
    if record.status == "pending":
        raise WriterError("Cannot persist a retrospective record with status='pending'. Transition to completed/skipped/failed first.")

    # Pydantic round-trip validation to catch any remaining issues.
    try:
        validated = RetrospectiveRecord.model_validate(record.model_dump())
    except Exception as exc:
        raise WriterError(f"Schema validation failed: {exc}") from exc

    # Canonical path.
    mission_id = validated.mission.mission_id
    target_dir = repo_root / ".kittify" / "missions" / mission_id
    canonical = target_dir / "retrospective.yaml"

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WriterError(f"Cannot create target directory {target_dir}: {exc}") from exc

    # Build a tempfile in the same directory (same filesystem → os.replace is atomic).
    tmp_name = f"retrospective.yaml.tmp.{os.getpid()}.{os.urandom(4).hex()}"
    tmp_path = target_dir / tmp_name

    try:
        yaml = YAML(typ="rt")
        yaml.default_flow_style = False
        yaml.width = 120

        # Convert the model to a plain dict for serialization.
        data = validated.model_dump(mode="python")

        buf = io.BytesIO()
        yaml.dump(data, buf)
        serialized = buf.getvalue()

        # Write tempfile, fsync, close.
        fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            os.write(fd, serialized)
            os.fsync(fd)
        finally:
            os.close(fd)

        # Atomic rename.
        os.replace(str(tmp_path), str(canonical))

        # Best-effort fsync the directory to flush the rename into the inode.
        try:
            dir_fd = os.open(str(target_dir), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            # Non-fatal: directory fsync is best-effort per the spec.
            pass

    except WriterError:
        raise
    except OSError as exc:
        # Clean up tempfile if it still exists.
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        raise WriterError(f"IO error writing retrospective record: {exc}") from exc
    except Exception as exc:
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        raise WriterError(f"Unexpected error writing retrospective record: {exc}") from exc

    return canonical
