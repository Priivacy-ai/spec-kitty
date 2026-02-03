"""Lamport clock with JSON persistence for causal event ordering."""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import socket
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def generate_node_id() -> str:
    """Generate stable machine identifier from hostname + username.

    Returns first 12 characters of SHA-256 hash for anonymization.
    Same value across CLI restarts, different per user on shared machines.
    """
    hostname = socket.gethostname()
    username = getpass.getuser()
    raw = f"{hostname}:{username}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass
class LamportClock:
    """Persistent Lamport clock for causal ordering of events.

    Persists to ~/.spec-kitty/clock.json using atomic writes (temp file + rename).
    """

    value: int = 0
    node_id: str = field(default_factory=generate_node_id)
    _storage_path: Path = field(
        default_factory=lambda: Path.home() / ".spec-kitty" / "clock.json",
        repr=False,
    )

    def tick(self) -> int:
        """Increment clock for local event emission.

        Returns the new clock value after incrementing.
        Persists the updated value to disk.
        """
        self.value += 1
        self.save()
        return self.value

    def receive(self, remote_clock: int) -> int:
        """Update clock based on received remote event.

        Implements Lamport semantics: value = max(local, remote) + 1.
        Persists the updated value to disk.
        """
        self.value = max(self.value, remote_clock) + 1
        self.save()
        return self.value

    def save(self) -> None:
        """Persist clock state to JSON file using atomic write."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "value": self.value,
            "node_id": self.node_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Atomic write: write to temp file in same directory, then rename
        fd, tmp_path = tempfile.mkstemp(
            dir=self._storage_path.parent,
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self._storage_path)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @classmethod
    def load(cls, storage_path: Path | None = None) -> LamportClock:
        """Load clock state from JSON file.

        Creates a new clock with value=0 if file doesn't exist or is invalid.
        """
        if storage_path is None:
            storage_path = Path.home() / ".spec-kitty" / "clock.json"

        if not storage_path.exists():
            clock = cls(_storage_path=storage_path)
            return clock

        try:
            with open(storage_path) as f:
                data = json.load(f)

            clock = cls(
                value=data.get("value", 0),
                node_id=data.get("node_id", generate_node_id()),
                _storage_path=storage_path,
            )
            return clock
        except (json.JSONDecodeError, KeyError, TypeError):
            # Corrupted file - start fresh
            clock = cls(_storage_path=storage_path)
            return clock
