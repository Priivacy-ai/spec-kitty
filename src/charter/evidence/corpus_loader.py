"""Corpus loader for charter synthesis evidence."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import ruamel.yaml

from charter.corpus import CORPUS_ROOT
from charter.synthesizer.evidence import CorpusEntry, CorpusSnapshot


class CorpusLoaderError(Exception):
    """Raised when a corpus file cannot be loaded or parsed."""


class CorpusLoader:
    """Load a profile-keyed best-practice corpus snapshot."""

    def __init__(self, corpus_root: Path | None = None) -> None:
        self._root = Path(corpus_root) if corpus_root is not None else CORPUS_ROOT

    def load(self, profile_key: str) -> CorpusSnapshot | None:
        """Return a CorpusSnapshot for the given profile key.

        Matching order: exact primary language -> "generic" fallback -> None.
        """
        primary = profile_key.split("+")[0]
        for candidate in [primary, "generic"]:
            path = self._root / f"{candidate}.corpus.yaml"
            if path.exists():
                return self._load_file(path)
        return None

    def _load_file(self, path: Path) -> CorpusSnapshot:
        try:
            yaml = ruamel.yaml.YAML()
            with path.open("r", encoding="utf-8") as fh:
                data: dict[str, Any] = yaml.load(fh)
            return _parse_snapshot(data)
        except (ValueError, KeyError, TypeError) as exc:
            raise CorpusLoaderError(f"Failed to parse corpus file {path}: {exc}") from exc


def _parse_snapshot(data: dict[str, Any]) -> CorpusSnapshot:
    entries = tuple(
        CorpusEntry(
            topic=str(e["topic"]),
            tags=tuple(str(t) for t in e.get("tags", [])),
            guidance=str(e["guidance"]).strip(),
        )
        for e in data.get("entries", [])
    )
    return CorpusSnapshot(
        snapshot_id=str(data["snapshot_id"]),
        profile_key=str(data["profile_key"]),
        entries=entries,
        loaded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
