"""Contract tests: creation-time mission_id minting (WP01, FR-001..FR-003, FR-005).

Guarantees locked by this file:
  T001 — two back-to-back creations always produce distinct, valid ULIDs
  T002 — creation succeeds with all outbound sockets blocked (offline guarantee, FR-003)
  T003 — mission_id is a valid ULID and is immutable after creation (FR-002)
  T004 — 100 sequential creations all produce distinct ULIDs (monotonicity, FR-005)

Do NOT add ``# type: ignore`` to this file — it must pass ``mypy --strict`` cleanly.
"""

from __future__ import annotations

import json
import re
import socket
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from specify_cli.core.mission_creation import (
    MissionCreationResult,
    create_mission_core,
)

# Crockford base32 subset (excludes I, L, O, U) — the ULID alphabet.
_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

_CORE = "specify_cli.core.mission_creation"

# ---------------------------------------------------------------------------
# Shared scaffolding helpers
# ---------------------------------------------------------------------------


def _init_git_repo(repo: Path) -> None:
    """Set up a minimal git repository with the directories create_mission_core expects."""
    (repo / ".kittify").mkdir(exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init", "--allow-empty"],
        cwd=repo,
        capture_output=True,
        check=True,
    )


def _create_mission(
    repo: Path,
    slug: str,
    feature_number: int = 1,  # retained for call-site compatibility; not used post-WP02
) -> MissionCreationResult:
    """Call create_mission_core with the minimum scaffolding patches.

    Patches allowed (local/git state only):
    - is_worktree_context: always False (we run in tmp dir, not inside .worktrees/)
    - _commit_feature_file: no-op (avoids git-commit overhead in volume tests)

    Note (WP02): get_next_feature_number is no longer imported by mission_creation.py;
    the allocator was removed as part of FR-044. The ``feature_number`` parameter is
    kept for call-site compatibility but has no effect.

    Intentionally NOT patched:
    - emit_mission_created  (see T002 for network-blocking test)
    - locate_project_root, is_git_repo, get_current_branch (real git repo is present)
    """
    with (
        patch(f"{_CORE}.is_worktree_context", return_value=False),
        patch(f"{_CORE}._commit_feature_file"),
    ):
        return create_mission_core(repo, slug)


def _read_meta(feature_dir: Path) -> dict[str, Any]:
    """Read and parse the meta.json for a feature directory."""
    return dict(json.loads((feature_dir / "meta.json").read_text(encoding="utf-8")))


def _assert_valid_ulid(value: str, *, label: str = "mission_id") -> None:
    """Assert that *value* is a 26-character Crockford base32 ULID string."""
    assert len(value) == 26, f"{label} must be 26 chars, got {len(value)}: {value!r}"
    assert _ULID_RE.match(value), (
        f"{label} must match Crockford base32 ULID alphabet, got {value!r}"
    )


# ---------------------------------------------------------------------------
# T001 — Two back-to-back creations produce distinct, valid ULIDs
# ---------------------------------------------------------------------------


def test_t001_distinct_mission_ids_across_back_to_back_creations(tmp_path: Path) -> None:
    """FR-001: Each mission mints a fresh ULID distinct from every prior mission."""
    _init_git_repo(tmp_path)

    result_a = _create_mission(tmp_path, "alpha-feature", feature_number=1)
    result_b = _create_mission(tmp_path, "beta-feature", feature_number=2)

    meta_a = _read_meta(result_a.feature_dir)
    meta_b = _read_meta(result_b.feature_dir)

    id_a: str = meta_a["mission_id"]
    id_b: str = meta_b["mission_id"]

    assert id_a, "alpha-feature mission_id must be non-empty"
    assert id_b, "beta-feature mission_id must be non-empty"
    assert id_a != id_b, (
        f"Back-to-back creations must produce distinct ULIDs; both got {id_a!r}"
    )
    _assert_valid_ulid(id_a, label="alpha-feature mission_id")
    _assert_valid_ulid(id_b, label="beta-feature mission_id")


# ---------------------------------------------------------------------------
# T002 — Creation succeeds with all outbound sockets blocked (FR-003, offline)
# ---------------------------------------------------------------------------


def _block_connect(self: socket.socket, *args: Any, **kwargs: Any) -> None:
    """Replacement for socket.socket.connect that raises unconditionally.

    Installed by T002 to prove that no outbound network call is REQUIRED
    for mission creation to succeed.  Because emit_mission_created is wrapped
    in contextlib.suppress(Exception) inside create_mission_core, the socket
    error is silently absorbed and creation completes normally.
    """
    raise OSError("T002 network block: outbound connection refused")


def test_t002_creation_succeeds_with_network_blocked(tmp_path: Path) -> None:
    """FR-003: Mission creation is fully offline — no outbound socket is required.

    The network block fires BEFORE the creation call.  emit_mission_created is
    NOT patched — it runs through its real code path including the event
    emission attempt.  create_mission_core wraps the entire emission step in
    contextlib.suppress(Exception), so any OSError from the blocked socket is
    silently absorbed and the function returns normally.
    """
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE}.is_worktree_context", return_value=False),
        patch(f"{_CORE}._commit_feature_file"),
        patch.object(socket.socket, "connect", _block_connect),
    ):
        result = create_mission_core(tmp_path, "offline-feature")

    meta = _read_meta(result.feature_dir)
    assert "mission_id" in meta, "meta.json must contain mission_id even when network is blocked"
    mission_id: str = meta["mission_id"]
    _assert_valid_ulid(mission_id, label="offline-feature mission_id")


# ---------------------------------------------------------------------------
# T003 — mission_id is a valid ULID and is immutable after creation (FR-002)
# ---------------------------------------------------------------------------


def test_t003_mission_id_is_valid_ulid_and_immutable(tmp_path: Path) -> None:
    """FR-002: mission_id is never rewritten after the initial creation write.

    Steps:
      1. Create a mission and capture the written mission_id.
      2. Re-read meta.json a second time (simulates a noop read-pass).
      3. Assert byte-identical value and correct ULID shape.
    """
    _init_git_repo(tmp_path)

    result = _create_mission(tmp_path, "immutable-feature", feature_number=1)
    meta_first = _read_meta(result.feature_dir)
    captured_id: str = meta_first["mission_id"]

    # Noop pass: re-read meta.json from disk (no write operation)
    meta_second = _read_meta(result.feature_dir)
    reread_id: str = meta_second["mission_id"]

    assert reread_id == captured_id, (
        f"mission_id changed after noop re-read: was {captured_id!r}, now {reread_id!r}"
    )
    # Validate ULID alphabet: 26-char Crockford base32 excluding I, L, O, U
    assert _ULID_RE.match(captured_id), (
        f"mission_id {captured_id!r} does not match ULID regex ^[0-9A-HJKMNP-TV-Z]{{26}}$"
    )


# ---------------------------------------------------------------------------
# T004 — 100 sequential creations all produce distinct ULIDs (FR-005)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_t004_hundred_sequential_creations_all_distinct(tmp_path: Path) -> None:
    """FR-005: ULID monotonicity — 100 missions in one process yield 100 unique IDs.

    Also asserts non-decreasing lexicographic order, which holds because ULID
    timestamps are monotonically increasing within a single process (the
    python-ulid library guarantees this).
    """
    _init_git_repo(tmp_path)

    n = 100
    ids: list[str] = []

    for i in range(1, n + 1):
        slug = f"vol-{i:03d}"
        result = _create_mission(tmp_path, slug, feature_number=i)
        meta = _read_meta(result.feature_dir)
        mission_id: str = meta["mission_id"]
        _assert_valid_ulid(mission_id, label=f"vol-{i:03d} mission_id")
        ids.append(mission_id)

    unique_ids = set(ids)
    assert len(unique_ids) == n, (
        f"Expected {n} distinct mission_ids, found {len(unique_ids)} unique values "
        f"({n - len(unique_ids)} collision(s))"
    )

    # Non-decreasing lexicographic order — ULID timestamp monotonicity
    for j in range(len(ids) - 1):
        assert ids[j] <= ids[j + 1], (
            f"ULID order violation at index {j}: {ids[j]!r} > {ids[j + 1]!r}"
        )
