"""Shared pytest fixtures for conformance tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the conformance fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def manifest(fixtures_dir: Path) -> Dict[str, Any]:
    """Loaded manifest.json contents."""
    manifest_path = fixtures_dir / "manifest.json"
    return json.loads(manifest_path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


@pytest.fixture
def fixture_cases(manifest: Dict[str, Any], fixtures_dir: Path) -> List[Dict[str, Any]]:
    """All fixture cases with loaded payloads."""
    cases: List[Dict[str, Any]] = []
    for entry in manifest["fixtures"]:
        if entry.get("fixture_type") == "replay_stream":
            continue
        fixture_path = fixtures_dir / entry["path"]
        payload: Any = json.loads(fixture_path.read_text(encoding="utf-8"))
        cases.append({
            **entry,
            "payload": payload,
        })
    return cases
