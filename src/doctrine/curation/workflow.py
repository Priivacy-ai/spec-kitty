"""Curation workflow orchestration — business logic with no I/O dependencies.

The CLI (specify_cli.cli.commands.doctrine) delegates to these functions and
supplies I/O via CurationIO. Tests can inject stub implementations of CurationIO
without needing a terminal or Rich console.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from collections.abc import Callable

from doctrine.curation.engine import (
    ProposedArtifact,
    depth_first_order,
    discover_proposed,
    discover_shipped,
    drop_artifact,
    extract_refs,
    promote_artifact,
    seed_session,
)
from doctrine.curation.state import (
    CurationSession,
    CurationVerdict,
    load_session,
    save_session,
)

# Sentinel returned by CurationIO.prompt_verdict to signal user quit.
_QUIT = "quit"
VerdictOrQuit = CurationVerdict | Literal["quit"]


class CurationAborted(Exception):
    """Raised when the operator quits an active session."""


@dataclass
class CurationIO:
    """I/O callbacks injected by the CLI layer.

    The workflow never writes to stdout or reads from stdin directly — all
    interaction is routed through these callables so the business logic
    remains testable in isolation.
    """

    present: Callable[[ProposedArtifact, int, int, ProposedArtifact | None], None]
    prompt_verdict: Callable[[], VerdictOrQuit]
    confirm_drop: Callable[[str], bool]
    on_accepted: Callable[[ProposedArtifact, Path], None]
    on_dropped: Callable[[ProposedArtifact], None]
    on_skipped: Callable[[ProposedArtifact], None]
    on_verdict_downgraded: Callable[[ProposedArtifact], None]  # drop → skip (user cancelled)


def load_or_create_session(repo_root: Path, resume: bool) -> tuple[CurationSession, bool]:
    """Return (session, is_resumed).

    Loads from disk when resume=True and a saved session exists; otherwise
    returns a fresh CurationSession.
    """
    if resume:
        existing = load_session(repo_root)
        if existing is not None:
            return existing, True
    return CurationSession(), False


def collect_pending(
    session: CurationSession,
    artifact_type: str | None = None,
) -> tuple[list[ProposedArtifact], dict[tuple[str, str], ProposedArtifact]]:
    """Discover and order proposed artifacts; return those still pending.

    Returns:
        pending: Artifacts with no decision or a ``pending`` verdict, in
            depth-first order.
        parent_map: Maps ``(type, id)`` of a referenced artifact to its
            parent artifact, used for display context.
    """
    proposed = discover_proposed()
    if artifact_type:
        proposed = [a for a in proposed if a.artifact_type == artifact_type]
    ordered = depth_first_order(proposed)

    parent_map: dict[tuple[str, str], ProposedArtifact] = {}
    for art in ordered:
        for ref_key in extract_refs(art):
            if ref_key not in parent_map:
                parent_map[ref_key] = art

    pending = [
        art for art in ordered
        if (dec := session.get_decision(art.artifact_type, art.artifact_id)) is None
        or dec.verdict == "pending"
    ]
    return pending, parent_map


def run_curate_session(
    session: CurationSession,
    repo_root: Path,
    artifact_type: str | None,
    io: CurationIO,
) -> CurationSession:
    """Run the curation interview loop.

    Presents each pending artifact in depth-first order, collects verdicts
    via ``io``, and persists session state after every decision.

    Raises:
        CurationAborted: When the operator chooses to quit. The session is
            saved before raising so it can be resumed.
    """
    session = seed_session(existing=session)
    pending, parent_map = collect_pending(session, artifact_type)

    for i, art in enumerate(pending, 1):
        parent = parent_map.get((art.artifact_type, art.artifact_id))
        io.present(art, i, len(pending), parent)

        raw = io.prompt_verdict()
        if raw == _QUIT:
            save_session(repo_root, session)
            raise CurationAborted

        verdict: CurationVerdict = raw  # type: ignore[assignment]

        if verdict == "accepted":
            dest = promote_artifact(art)
            io.on_accepted(art, dest)
        elif verdict == "dropped":
            if io.confirm_drop(art.filename):
                drop_artifact(art)
                io.on_dropped(art)
            else:
                verdict = "skipped"
                io.on_verdict_downgraded(art)
        else:
            io.on_skipped(art)

        session.record(
            artifact_type=art.artifact_type,
            artifact_id=art.artifact_id,
            filename=art.filename,
            verdict=verdict,
        )
        save_session(repo_root, session)

    return session


def get_status_counts() -> dict[str, dict[str, int]]:
    """Return proposed and shipped counts per artifact type.

    Example return value::

        {
            "directives": {"proposed": 27, "shipped": 0},
            "tactics":    {"proposed": 13, "shipped": 0},
        }
    """
    counts: dict[str, dict[str, int]] = {}
    for art in discover_proposed():
        counts.setdefault(art.artifact_type, {"proposed": 0, "shipped": 0})
        counts[art.artifact_type]["proposed"] += 1
    for art in discover_shipped():
        counts.setdefault(art.artifact_type, {"proposed": 0, "shipped": 0})
        counts[art.artifact_type]["shipped"] += 1
    return counts


def promote_single(
    artifact_id: str,
    artifact_type: str,
    repo_root: Path,
) -> tuple[ProposedArtifact, Path]:
    """Find and promote one artifact by ID and type.

    Updates the active curation session if one exists.

    Raises:
        ValueError: When no matching artifact is found in ``_proposed/``.
    """
    proposed = discover_proposed()
    match = [
        a for a in proposed
        if a.artifact_id == artifact_id and a.artifact_type == artifact_type
    ]
    if not match:
        raise ValueError(f"{artifact_type}/{artifact_id} not found in _proposed/")

    art = match[0]
    dest = promote_artifact(art)

    session = load_session(repo_root)
    if session:
        session.record(
            artifact_type=art.artifact_type,
            artifact_id=art.artifact_id,
            filename=art.filename,
            verdict="accepted",
        )
        save_session(repo_root, session)

    return art, dest


__all__ = [
    "CurationAborted",
    "CurationIO",
    "collect_pending",
    "get_status_counts",
    "load_or_create_session",
    "promote_single",
    "run_curate_session",
]
