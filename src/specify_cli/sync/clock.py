"""Lamport clock with JSON persistence for causal event ordering."""

from __future__ import annotations

import getpass
import hashlib
import json
import socket
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.core.atomic import atomic_write
from specify_cli.core.time_utils import now_utc_iso
from specify_cli.paths import get_runtime_root


def _default_clock_path() -> Path:
    """Return the Lamport clock storage path, honouring ``SPEC_KITTY_HOME``.

    Resolved lazily so environment overrides and test ``HOME`` monkeypatching
    are honoured (WP01 / research.md D5). On POSIX with the env var unset this
    is ``~/.spec-kitty/clock.json`` — byte-identical to the legacy path.
    """
    # ``get_runtime_root`` is seen as ``Any`` here because mypy skips imports
    # for ``specify_cli.*`` (follow_imports=skip); coerce at the typed boundary.
    base: Path = get_runtime_root().base
    return base / "clock.json"


def generate_node_id() -> str:
    """Generate stable machine identifier from hostname + username.

    Returns first 12 characters of SHA-256 hash for anonymization.
    Same value across CLI restarts, different per user on shared machines.
    """
    hostname = socket.gethostname()
    username = getpass.getuser()
    raw = f"{hostname}:{username}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]  # noqa: TID251 - production raw SHA-256 owner


@dataclass
class LamportClock:
    """Persistent Lamport clock for causal ordering of events.

    Persists to ~/.spec-kitty/clock.json using atomic writes (temp file + rename).
    """

    value: int = 0
    node_id: str = field(default_factory=generate_node_id)
    _storage_path: Path = field(
        default_factory=_default_clock_path,
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
        data = {
            "value": self.value,
            "node_id": self.node_id,
            "updated_at": now_utc_iso(),
        }

        content = json.dumps(data, indent=2)
        atomic_write(self._storage_path, content, mkdir=True)

    @classmethod
    def load(cls, storage_path: Path | None = None) -> LamportClock:
        """Load clock state from JSON file.

        Creates a new clock with value=0 if file doesn't exist or is invalid.
        """
        if storage_path is None:
            storage_path = _default_clock_path()

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
