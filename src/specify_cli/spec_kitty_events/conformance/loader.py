"""Canonical fixture loading for spec-kitty-events conformance testing.

Provides FixtureCase (frozen dataclass) and load_fixtures() for data-driven
conformance tests. Reads from the bundled manifest.json and fixture JSON files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_MANIFEST_PATH = _FIXTURES_DIR / "manifest.json"

_VALID_CATEGORIES = frozenset({
    "events", "lane_mapping", "edge_cases",
    "collaboration", "glossary", "mission_next",
    "analytics",
    "dossier", "mission_audit", "decisionpoint",
    "connector", "sync",
    "profile_invocation", "retrospective",  # 3.1.0
})

# Replay stream fixture type sentinel
_REPLAY_STREAM_TYPE = "replay_stream"

# Known special fixture types that load_fixtures() skips.
# Typos in manifest fixture_type values will raise ValueError.
_SPECIAL_FIXTURE_TYPES: frozenset[str] = frozenset({
    "replay_stream",
    "reducer_output",
})


@dataclass(frozen=True)
class FixtureCase:
    """A single fixture test case loaded from the manifest."""

    id: str
    payload: Any
    expected_valid: bool
    event_type: str
    notes: str
    min_version: str


def load_fixtures(category: str) -> List[FixtureCase]:
    """Load canonical fixture cases for a category.

    Args:
        category: One of ``"events"``, ``"lane_mapping"``, ``"edge_cases"``,
            ``"collaboration"``, ``"glossary"``, ``"mission_next"``, ``"dossier"``,
            ``"analytics"``, ``"mission_audit"``, ``"decisionpoint"``, ``"connector"``, ``"sync"``,
            ``"profile_invocation"``, or ``"retrospective"``.

    Returns:
        List of :class:`FixtureCase` instances with payloads loaded from JSON.

    Raises:
        ValueError: If *category* is not one of the recognised categories.
        FileNotFoundError: If the manifest or a referenced fixture file is missing.
    """
    if category not in _VALID_CATEGORIES:
        raise ValueError(
            f"Unknown fixture category: {category!r}. "
            f"Valid categories: {sorted(_VALID_CATEGORIES)}"
        )

    with open(_MANIFEST_PATH, "r", encoding="utf-8") as fh:
        manifest: Dict[str, Any] = json.load(fh)

    fixtures: List[FixtureCase] = []

    entries: List[Dict[str, Any]] = manifest["fixtures"]
    for entry in entries:
        fixture_path: str = entry["path"]
        # Filter by category prefix in path
        if not fixture_path.startswith(category + "/"):
            continue

        # Skip entries with a known special fixture_type (e.g. replay_stream,
        # reducer_output) — only regular event fixtures are loaded here.
        # Raise on unknown fixture_type to catch manifest typos early.
        ft: str | None = entry.get("fixture_type")
        if ft is not None:
            if ft not in _SPECIAL_FIXTURE_TYPES:
                raise ValueError(
                    f"Unknown fixture_type {ft!r} in manifest entry "
                    f"{entry.get('id', '?')!r}. "
                    f"Known types: {sorted(_SPECIAL_FIXTURE_TYPES)}"
                )
            continue

        # Resolve full path to the fixture JSON file
        full_path = _FIXTURES_DIR / fixture_path
        if not full_path.exists():
            raise FileNotFoundError(
                f"Fixture file referenced in manifest does not exist: {full_path}"
            )

        with open(full_path, "r", encoding="utf-8") as fh:
            payload: Any = json.load(fh)

        fixtures.append(
            FixtureCase(
                id=entry["id"],
                payload=payload,
                expected_valid=entry["expected_result"] == "valid",
                event_type=entry["event_type"],
                notes=entry["notes"],
                min_version=entry["min_version"],
            )
        )

    return fixtures


def load_replay_stream(fixture_id: str) -> List[Dict[str, Any]]:
    """Load a replay stream fixture as a list of raw event dicts.

    Replay streams are stored as newline-delimited JSON (JSONL) files.
    Each line is a complete event dictionary.

    Args:
        fixture_id: The manifest ``id`` of the replay stream entry
            (e.g. ``"dossier-replay-happy-path"`` or
            ``"mission-next-replay-full-lifecycle"``).

    Returns:
        List of raw event dictionaries, one per line in the JSONL file.

    Raises:
        ValueError: If *fixture_id* is not found or is not a replay_stream entry.
        FileNotFoundError: If the JSONL file does not exist on disk.
    """
    with open(_MANIFEST_PATH, "r", encoding="utf-8") as fh:
        manifest: Dict[str, Any] = json.load(fh)

    entry: Dict[str, Any] | None = None
    for candidate in manifest["fixtures"]:
        if candidate["id"] == fixture_id:
            entry = candidate
            break

    if entry is None:
        raise ValueError(
            f"Replay stream fixture not found in manifest: {fixture_id!r}"
        )

    if entry.get("fixture_type") != _REPLAY_STREAM_TYPE:
        raise ValueError(
            f"Fixture {fixture_id!r} is not a replay_stream "
            f"(fixture_type={entry.get('fixture_type')!r}). "
            f"Use load_fixtures() for regular fixture cases."
        )

    full_path = _FIXTURES_DIR / entry["path"]
    if not full_path.exists():
        raise FileNotFoundError(
            f"Replay stream file referenced in manifest does not exist: {full_path}"
        )

    events: List[Dict[str, Any]] = []
    with open(full_path, "r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            event_dict: Dict[str, Any] = json.loads(stripped)
            events.append(event_dict)

    return events
