"""Hash-unification pin across the real freshness surfaces (WP04 / FR-008b, C2-d).

C2-d already landed: ``sync``, ``charter status``, and the freshness computer
all route content hashing through the one ``charter.hasher.hash_content`` path.
This pin guards against a surface *stopping* routing through it (e.g. a
reintroduced local ``hashlib.sha256``).

Anti-tautology (F1): the test invokes the ACTUAL surface functions — the
``charter status`` collector (``_collect_charter_sync_status`` → ``is_stale``),
the ``sync`` staleness primitive (``is_stale`` as ``sync`` calls it on content),
and ``computer._charter_hash_of`` — and asserts they agree on the SAME content.
It does NOT call ``hash_content`` N times (that would be ``assert x == x``).
The mutate-and-diverge negative guard proves all three read the same content
through the same normalization.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from charter.hasher import is_stale
from specify_cli.charter_runtime.freshness import compute_freshness
from specify_cli.charter_runtime.freshness import computer as freshness_computer
from specify_cli.cli.commands.charter._status_collectors import (
    _collect_charter_sync_status,
)

pytestmark = [pytest.mark.integration]

_CHARTER_BODY = "# Spec Kitty Charter\n\nGovernance body with real-shaped content.\n"


def _seed_bundle(repo: Path, *, body: str = _CHARTER_BODY) -> tuple[Path, Path]:
    """Materialise a real charter bundle: charter.md + metadata.yaml.

    The stored ``charter_hash`` is the canonical ``hash_content`` of the body so
    the bundle is in a fresh (non-stale) state.
    """
    from charter.hasher import hash_content  # noqa: PLC0415

    charter_dir = repo / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_path = charter_dir / "charter.md"
    metadata_path = charter_dir / "metadata.yaml"
    charter_path.write_text(body, encoding="utf-8")
    stored = hash_content(body)  # "sha256:<hex>"
    metadata_path.write_text(
        dedent(
            f"""\
            charter_hash: {stored}
            timestamp_utc: 2026-06-18T00:00:00+00:00
            """
        ),
        encoding="utf-8",
    )
    return charter_path, metadata_path


def _surface_hashes(repo: Path, charter_path: Path, metadata_path: Path) -> dict[str, str]:
    """Collect the *current-content* hash each real surface computes."""
    # Surface 1 — ``charter status`` collector (routes through is_stale).
    status = _collect_charter_sync_status(repo)
    assert status["available"] is True
    status_hash = str(status["current_hash"])

    # Surface 2 — the ``sync`` staleness primitive, called exactly as sync()
    # calls it: on the charter content read from disk.
    content = charter_path.read_text(encoding="utf-8")
    _stale, sync_hash, _stored = is_stale(None, metadata_path, content=content)

    # Surface 3 — the freshness computer's charter hash.
    computer_hash = freshness_computer._charter_hash_of(charter_path)
    assert computer_hash is not None

    return {
        "status": status_hash,
        "sync": str(sync_hash),
        "computer": computer_hash,
    }


def test_real_surfaces_agree_on_charter_hash(tmp_path: Path) -> None:
    """status / sync / computer agree on the current-content hash (sha256: prefix)."""
    charter_path, metadata_path = _seed_bundle(tmp_path)

    hashes = _surface_hashes(tmp_path, charter_path, metadata_path)

    # status and sync carry the canonical ``sha256:`` prefix and are byte-equal.
    assert hashes["status"] == hashes["sync"]
    assert hashes["status"].startswith("sha256:")
    assert hashes["sync"].startswith("sha256:")

    # The computer strips the prefix (it compares against a normalized stored
    # hash); after normalization it is the SAME digest as the prefixed surfaces.
    assert hashes["status"] == f"sha256:{hashes['computer']}"

    # The bundle is fresh: stored hash equals current → status reports synced.
    status = _collect_charter_sync_status(tmp_path)
    assert status["status"] == "synced"
    assert status["current_hash"] == status["stored_hash"]


def test_mutation_diverges_all_surfaces_identically(tmp_path: Path) -> None:
    """Negative guard: mutating the body shifts all three surfaces in lockstep.

    Proves the surfaces read the same content through the same normalization —
    if one surface stopped routing through ``hash_content`` (e.g. a local
    ``hashlib.sha256`` without the strip/normalize), the cross-surface equality
    below would break.
    """
    charter_path, metadata_path = _seed_bundle(tmp_path)
    before = _surface_hashes(tmp_path, charter_path, metadata_path)

    # Mutate the charter body (do NOT update metadata → now stale).
    charter_path.write_text(_CHARTER_BODY + "\n## Amendment\n\nNew clause.\n", encoding="utf-8")
    after = _surface_hashes(tmp_path, charter_path, metadata_path)

    # Every surface's hash changed.
    for surface in ("status", "sync", "computer"):
        assert after[surface] != before[surface], surface

    # And after mutation the surfaces STILL agree with each other (same content,
    # same normalization) — the divergence is from the content, not the surface.
    assert after["status"] == after["sync"]
    assert after["status"] == f"sha256:{after['computer']}"

    # The status collector now reports stale (current != stored).
    status = _collect_charter_sync_status(tmp_path)
    assert status["status"] == "stale"
    assert status["current_hash"] != status["stored_hash"]


# ---------------------------------------------------------------------------
# FR-009 (C2-e): the "noop-despite-stale" drift — line-ending / BOM agnostic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "raw_bytes"),
    [
        ("crlf", b"# Charter\r\n\r\nBody with CRLF line endings.\r\n"),
        ("bom", b"\xef\xbb\xbf# Charter\n\nBody with a UTF-8 BOM.\n"),
        ("bom_crlf", b"\xef\xbb\xbf# Charter\r\n\r\nBOM + CRLF.\r\n"),
    ],
)
def test_c2e_no_noop_despite_stale_for_crlf_or_bom(
    tmp_path: Path, label: str, raw_bytes: bytes
) -> None:
    """C2-e live-reproduced drift: ``sync`` noop while status/freshness stale.

    Root cause: ``charter sync`` reads via the encoding chokepoint
    (``read_bytes().decode()`` — strips BOM, preserves CRLF) while ``status`` /
    the freshness computer read via ``read_text`` (keeps BOM, collapses CRLF).
    Pre-fix the two hashed different content, so a charter that a prior sync
    wrote stored a chokepoint-shaped hash that the ``read_text`` surfaces did
    not match → status/freshness "stale" while sync "noop".

    The ``hash_content`` normalization (drop leading BOM + canonicalise line
    endings) makes every surface agree. This pins that all three surfaces
    report the SAME staleness on a CRLF/BOM charter — no noop-despite-stale.
    """
    from charter._io import load_charter_file  # noqa: PLC0415
    from charter.hasher import hash_content  # noqa: PLC0415

    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_path = charter_dir / "charter.md"
    metadata_path = charter_dir / "metadata.yaml"
    for name in ("governance.yaml", "directives.yaml", "references.yaml"):
        (charter_dir / name).write_text("schema_version: '1'\n", encoding="utf-8")
    charter_path.write_bytes(raw_bytes)

    # Store the hash of the chokepoint-decoded text — exactly what a successful
    # ``charter sync`` writes into metadata.yaml.
    choke_text = load_charter_file(charter_path).text
    stored = hash_content(choke_text)
    metadata_path.write_text(
        f"charter_hash: {stored}\ntimestamp_utc: 2026-06-18T00:00:00+00:00\n",
        encoding="utf-8",
    )

    # sync's staleness primitive (on chokepoint content) → would-be noop.
    sync_stale, _, _ = is_stale(None, metadata_path, content=choke_text)
    # status's staleness primitive (on charter_path via read_text).
    status = _collect_charter_sync_status(tmp_path)
    # freshness computer's independent view.
    fresh_state = compute_freshness(tmp_path).charter_source.state

    # All three AGREE the bundle is fresh (the stored hash matches), so there is
    # no "sync noop while status/freshness stale" drift, regardless of label.
    assert sync_stale is False, label
    assert status["status"] == "synced", label
    assert fresh_state == "fresh", label
    assert status["current_hash"] == status["stored_hash"], label
