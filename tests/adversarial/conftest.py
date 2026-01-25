from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest


@dataclass(frozen=True)
class AttackVector:
    name: str
    content: str | bytes
    file_type: str
    handler: str
    description: str


@pytest.fixture
def malformed_csv_factory(tmp_path: Path) -> Callable[[AttackVector, str], Path]:
    """Create malformed CSVs from attack vectors in temp directories."""

    def _factory(vector: AttackVector, filename: str = "malformed.csv") -> Path:
        path = tmp_path / filename
        if isinstance(vector.content, bytes):
            path.write_bytes(vector.content)
        else:
            path.write_text(vector.content, encoding="utf-8")
        return path

    return _factory
