"""Curation session state persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Literal

from doctrine.artifact_kinds import ArtifactKind


CurationVerdict = Literal["accepted", "dropped", "skipped", "pending"]

# All curate-able artifact types (excludes TEMPLATE which has no dedicated glob pattern).
ARTIFACT_TYPES: tuple[str, ...] = tuple(
    kind.plural for kind in ArtifactKind if kind is not ArtifactKind.TEMPLATE
)

STATE_FILE = ".kittify/curation/state.json"


@dataclass
class ArtifactDecision:
    """Record of a curation decision for a single artifact."""

    artifact_type: str
    artifact_id: str
    filename: str
    verdict: CurationVerdict = "pending"
    notes: str = ""
    decided_at: str | None = None

    def decide(self, verdict: CurationVerdict, notes: str = "") -> None:
        self.verdict = verdict
        self.notes = notes
        self.decided_at = datetime.now(UTC).isoformat()


@dataclass
class CurationSession:
    """Tracks curation progress across _proposed/ artifacts."""

    started_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    decisions: dict[str, ArtifactDecision] = field(default_factory=dict)

    def _key(self, artifact_type: str, artifact_id: str) -> str:
        return f"{artifact_type}:{artifact_id}"

    def record(
        self,
        artifact_type: str,
        artifact_id: str,
        filename: str,
        verdict: CurationVerdict = "pending",
        notes: str = "",
    ) -> ArtifactDecision:
        key = self._key(artifact_type, artifact_id)
        decision = ArtifactDecision(
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            filename=filename,
            verdict=verdict,
            notes=notes,
        )
        if verdict != "pending":
            decision.decided_at = datetime.now(UTC).isoformat()
        self.decisions[key] = decision
        self.updated_at = datetime.now(UTC).isoformat()
        return decision

    def get_decision(
        self, artifact_type: str, artifact_id: str
    ) -> ArtifactDecision | None:
        return self.decisions.get(self._key(artifact_type, artifact_id))

    @property
    def pending(self) -> list[ArtifactDecision]:
        return [d for d in self.decisions.values() if d.verdict == "pending"]

    @property
    def accepted(self) -> list[ArtifactDecision]:
        return [d for d in self.decisions.values() if d.verdict == "accepted"]

    @property
    def dropped(self) -> list[ArtifactDecision]:
        return [d for d in self.decisions.values() if d.verdict == "dropped"]

    @property
    def skipped(self) -> list[ArtifactDecision]:
        return [d for d in self.decisions.values() if d.verdict == "skipped"]

    @property
    def progress_percent(self) -> float:
        total = len(self.decisions)
        if total == 0:
            return 0.0
        decided = sum(1 for d in self.decisions.values() if d.verdict != "pending")
        return round(decided / total * 100, 1)


def save_session(repo_root: Path, session: CurationSession) -> Path:
    """Persist curation session to JSON."""
    path = repo_root / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "started_at": session.started_at,
        "updated_at": session.updated_at,
        "decisions": {
            k: {
                "artifact_type": d.artifact_type,
                "artifact_id": d.artifact_id,
                "filename": d.filename,
                "verdict": d.verdict,
                "notes": d.notes,
                "decided_at": d.decided_at,
            }
            for k, d in session.decisions.items()
        },
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def load_session(repo_root: Path) -> CurationSession | None:
    """Load curation session from JSON. Returns None if no session exists."""
    path = repo_root / STATE_FILE
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    session = CurationSession(
        started_at=data.get("started_at", ""),
        updated_at=data.get("updated_at", ""),
    )
    for key, dec in data.get("decisions", {}).items():
        ad = ArtifactDecision(
            artifact_type=dec["artifact_type"],
            artifact_id=dec["artifact_id"],
            filename=dec["filename"],
            verdict=dec.get("verdict", "pending"),
            notes=dec.get("notes", ""),
            decided_at=dec.get("decided_at"),
        )
        session.decisions[key] = ad
    return session


def clear_session(repo_root: Path) -> None:
    """Remove curation session state file."""
    path = repo_root / STATE_FILE
    if path.exists():
        path.unlink()
