"""JSON Schema artifacts for spec-kitty-events models."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_SCHEMA_DIR = Path(__file__).parent


def schema_path(name: str) -> Path:
    """Return filesystem path to a committed schema file."""
    path = _SCHEMA_DIR / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No schema found for '{name}'. Available: {list_schemas()}"
        )
    return path


def load_schema(name: str) -> Dict[str, Any]:
    """Load a committed JSON Schema by model name."""
    text = schema_path(name).read_text(encoding="utf-8")
    result: Dict[str, Any] = json.loads(text)
    return result


def list_schemas() -> List[str]:
    """List all available schema names."""
    return sorted(
        p.stem.replace(".schema", "") for p in _SCHEMA_DIR.glob("*.schema.json")
    )
