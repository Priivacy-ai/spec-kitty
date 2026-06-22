"""WP05 / T028 — status READ-contract routes through the STORED topology (FR-009, SC-001).

``_read_contract_from_transaction_target`` decides the coord-vs-primary read
SHAPE from the WP02 topology SSOT (``classify_topology`` over the stored
``coordination_branch`` value), NOT from a bare ``coordination_branch is None``
SURFACE re-inference. The transient on-disk arms (worktree-exists /
branch-deleted / coord-empty) stay probe-discriminated (C-006: #1718
create-window / #1848 coord-deleted).

This file witnesses BOTH halves:

* the stored-topology SHAPE classification (a coord-shaped mission reads the
  coordination contract; a single-branch mission reads the primary contract);
* the transient probe arms still discriminate the materialized-yet / deleted-now
  states for a coord-shaped mission (the SHAPE decision does NOT subsume them).

It also pins SC-001: the ``coordination_branch is None`` SURFACE-decision arm is
RETIRED from ``_read_contract_from_transaction_target`` (only the C-006 transient
arms may still read ``coordination_branch``).
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination import status_transition as st
from specify_cli.coordination.status_service import EventLogReadContract
from specify_cli.status.models import TransitionRequest

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

_FULL_ULID = "01KVPR00WP05READ000000000A"
_MID8 = _FULL_ULID[:8]
_SLUG = f"read-contract-shape-{_MID8}"
_DIRNAME = _SLUG  # slug already embeds the mid8
_COORD_BRANCH = f"kitty/mission-{_DIRNAME}"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _make_repo(tmp_path: Path, *, coord: bool) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    feature_dir = repo / "kitty-specs" / _DIRNAME
    feature_dir.mkdir(parents=True)
    meta: dict[str, object] = {
        "mission_slug": _SLUG,
        "mission_id": _FULL_ULID,
        "mid8": _MID8,
    }
    if coord:
        meta["coordination_branch"] = _COORD_BRANCH
    (feature_dir / "meta.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "seed mission")
    if coord:
        _git(repo, "branch", _COORD_BRANCH)
    return repo


def _identity(repo: Path) -> st._TransactionIdentity:
    return st._identity_for_request(
        TransitionRequest(
            feature_dir=repo / "kitty-specs" / _DIRNAME,
            mission_slug=_SLUG,
            wp_id="WP01",
            to_lane="claimed",
            actor="wp05-read-contract-test",
            repo_root=repo,
        )
    )


# ---------------------------------------------------------------------------
# Stored-topology SHAPE classification
# ---------------------------------------------------------------------------


def test_coord_shaped_mission_classifies_coordination_from_stored_topology(
    tmp_path: Path,
) -> None:
    """A coord-shaped mission routes the read SHAPE through the stored topology → coord."""
    repo = _make_repo(tmp_path, coord=True)
    identity = _identity(repo)
    assert st._read_contract_routes_through_coordination(identity) is True


def test_single_branch_mission_classifies_primary_from_stored_topology(
    tmp_path: Path,
) -> None:
    """A coord-less mission routes the read SHAPE through the stored topology → primary."""
    repo = _make_repo(tmp_path, coord=False)
    identity = _identity(repo)
    assert st._read_contract_routes_through_coordination(identity) is False


def test_read_contract_reads_stored_topology_over_coord_value_relay(
    tmp_path: Path,
) -> None:
    """randy #2: the STORED topology disposes the SHAPE, not a coord-value relay.

    A mission carrying BOTH a ``coordination_branch`` value AND a stored
    ``topology: single_branch`` (a flattened mission whose coord branch ref was not
    yet stripped from meta) must route the read contract to PRIMARY (False) — the
    STORED shape wins. Before WP09 the helper relayed
    ``classify_topology(identity.coordination_branch, …)``, which would have
    classified COORD (True) from the lingering value. Proving False here proves the
    relocated read site READS the stored value rather than relaying the inference.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    feature_dir = repo / "kitty-specs" / _DIRNAME
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": _SLUG,
                "mission_id": _FULL_ULID,
                "mid8": _MID8,
                "coordination_branch": _COORD_BRANCH,  # lingering value …
                "topology": "single_branch",  # … but stored shape is flattened
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "seed flattened-with-lingering-coord")
    _git(repo, "branch", _COORD_BRANCH)

    identity = _identity(repo)
    assert st._read_contract_routes_through_coordination(identity) is False, (
        "the stored single_branch topology must dispose the SHAPE to primary even "
        "with a lingering coordination_branch value — the read site reads the "
        "stored value, it does not relay classify_topology(coord_value, …)"
    )


def test_shape_helper_does_not_persist_a_topology_backfill(tmp_path: Path) -> None:
    """The SHAPE helper is PURE: it derives the topology via ``classify_topology``
    (no ``ensure_topology`` persist), so calling it never writes ``meta.json``.

    Snapshots ``meta.json`` AFTER identity construction (which has its own, separate
    write-target resolution) so this assertion isolates the helper's own purity:
    the helper MUST NOT mutate the file beyond whatever identity construction did.
    """
    repo = _make_repo(tmp_path, coord=True)
    identity = _identity(repo)
    meta_path = repo / "kitty-specs" / _DIRNAME / "meta.json"
    before = meta_path.read_bytes()

    st._read_contract_routes_through_coordination(identity)

    assert meta_path.read_bytes() == before, (
        "the SHAPE helper mutated meta.json — it must derive the topology purely "
        "via classify_topology, never persist an ensure_topology back-fill "
        "(read-must-not-write)"
    )


# ---------------------------------------------------------------------------
# Transient probe arms still discriminate (C-006) for a coord-shaped mission
# ---------------------------------------------------------------------------


def test_coord_branch_deleted_transient_falls_back_to_primary(tmp_path: Path) -> None:
    """#1848: a coord-shaped mission whose coord BRANCH was deleted reads primary.

    The SHAPE is coord (stored topology), but the transient branch-deleted probe
    arm — NOT the stored topology — sends the read to the primary checkout so a
    dangling ref does not report every WP as genesis.
    """
    repo = _make_repo(tmp_path, coord=True)
    # Delete the coordination branch (post-merge cleanup), leaving the stored
    # coord topology intact in meta.json.
    _git(repo, "branch", "-D", _COORD_BRANCH)
    identity = _identity(repo)
    # SHAPE is still coord …
    assert st._read_contract_routes_through_coordination(identity) is True
    # … but the transient probe routes the actual contract to the primary checkout.
    contract = st._read_contract_from_transaction_target(identity, _SLUG)
    assert contract == EventLogReadContract.primary_checkout(identity.feature_dir), (
        "the #1848 coord-deleted transient arm must keep routing to primary even "
        "though the stored topology shape is coord"
    )


def test_coord_worktree_materialised_transient_reads_coordination(tmp_path: Path) -> None:
    """A coord-shaped mission with a materialised coord worktree reads the coord worktree."""
    repo = _make_repo(tmp_path, coord=True)
    worktree = repo / ".worktrees" / f"{_DIRNAME}-coord"
    _git(repo, "worktree", "add", "-q", str(worktree), _COORD_BRANCH)
    identity = _identity(repo)
    contract = st._read_contract_from_transaction_target(identity, _SLUG)
    # The materialised-worktree transient arm wins (not the primary checkout).
    assert contract != EventLogReadContract.primary_checkout(identity.feature_dir)


# ---------------------------------------------------------------------------
# SC-001 — the coordination_branch-is-None SURFACE decision is retired
# ---------------------------------------------------------------------------


def test_read_contract_function_has_no_coordination_branch_surface_decision() -> None:
    """SC-001: ``_read_contract_from_transaction_target`` carries no ``coordination_branch is None`` test.

    AST-scoped to the read-contract function so a docstring mention elsewhere does
    not mask a live re-inference. The coord-vs-primary SHAPE must come from the
    stored-topology helper, never from a bare ``coordination_branch is None`` arm.
    """
    source = Path(st.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    target = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_read_contract_from_transaction_target"
    )
    for node in ast.walk(target):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Attribute):
            attr = node.left
            if attr.attr == "coordination_branch":
                pytest.fail(
                    "_read_contract_from_transaction_target still tests "
                    "identity.coordination_branch directly — the SURFACE decision "
                    "(SC-001) must be retired in favour of the stored-topology shape."
                )
