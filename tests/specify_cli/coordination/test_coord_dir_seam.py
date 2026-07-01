"""WP06 byte-identical seam-delegation oracle (mission 01KV6510, #1878 slice).

Every duplicate compose/parse algorithm in ``coordination/`` AND ``missions/``
now delegates to the single WP01 naming seam (``lanes.branch_naming``). This
module is the binding regression: it pins that the six delegated composers emit
names **byte-identical** to their pre-WP06 hand-rolled algorithm for both the
embedded ``<slug>-<mid8>`` and legacy/bare slugs — there must be exactly ONE
algorithm for the grammar (FR-010), so routing the call sites to the seam must
cause zero on-disk churn (no orphaned coord worktrees, no broken status reads,
no broken ``mission create``).

The reference algorithms below are the EXACT pre-WP06 bodies, frozen here as the
oracle. If a delegation diverges from these, this test fails — that is the
"fake delegation" trap the squad called out (a second algorithm surviving, or a
name drifting because the seam's NNN-strip bites a caller that passed an
NNN-prefixed slug).
"""

from __future__ import annotations

import pytest

from specify_cli.coordination import status_transition as st
from specify_cli.coordination import transaction as txn
from specify_cli.coordination import workspace as ws
from specify_cli.lanes import branch_naming as bn
from specify_cli.missions import _create as mc
from specify_cli.missions import _read_path_resolver as rpr

# Reuse WP01's binding golden table so the byte-identical contract has a single
# source of truth (NFR-003).
from tests.lanes.test_branch_naming_seam import GOLDEN_ROWS, MID8, MISSION_ID

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Frozen reference algorithms — the EXACT pre-WP06 bodies (the oracle).
# ---------------------------------------------------------------------------


def _ref_compose_mission_dir(mission_slug: str, mid8: str) -> str:
    """Pre-WP06 ``workspace._compose_mission_dir`` / ``transaction`` / ``status_transition``."""
    if mission_slug.endswith(f"-{mid8}"):
        return mission_slug
    return f"{mission_slug}-{mid8}"


def _ref_read_path_compose_mission_dir(mission_slug: str, mid8: str) -> str:
    """Pre-WP06 ``_read_path_resolver._compose_mission_dir`` (empty-mid8 = verbatim)."""
    if mid8 and mission_slug.endswith(f"-{mid8}"):
        return mission_slug
    if mid8:
        return f"{mission_slug}-{mid8}"
    return mission_slug


def _ref_coordination_branch_name(mission_slug: str, mission_id: str) -> str:
    """Pre-WP06 ``_create.coordination_branch_name``."""
    mid8_token = mission_id[:8]
    suffix = f"-{mid8_token}"
    human_part = (
        mission_slug
        if mission_slug.endswith(suffix)
        else f"{bn.strip_numeric_prefix(mission_slug)}{suffix}"
    )
    return f"kitty/mission-{human_part}"


# Slugs that flow through these coordination composers. Includes the on-disk
# formatted ``<slug>-<mid8>`` form, the bare human slug, AND — crucially — a
# legacy ``NNN-``-prefixed slug. The coordination READ/TRANSACTION path reads
# ``meta.json.mission_slug`` VERBATIM, so an NNN- slug DOES reach these composers
# (the #1589 counter-example). They must reconstruct the EXISTING on-disk name
# verbatim (NO NNN- strip), byte-identical to the pre-WP06 algorithm — the prior
# oracle wrongly excluded NNN- and so missed the byte-level drift.
_FORMATTED_SLUGS = ("foo-01KV6510", "foo", "my-feature-01KV6510", "060-test")

# A legacy NNN- slug + a SEPARATELY supplied mid8 — exactly the live coordination
# read/transaction input. ``MID8`` here is a foreign/separate mid8 (not embedded
# in the slug), so the verbatim composers must keep ``060-test`` intact and append.
_NNN_SLUG = "060-test"


# ---------------------------------------------------------------------------
# T025 — coordination/workspace composers delegate (mission dir + coord path + branch).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", _FORMATTED_SLUGS)
def test_workspace_compose_mission_dir_byte_identical(slug: str) -> None:
    assert ws._compose_mission_dir(slug, MID8) == _ref_compose_mission_dir(slug, MID8)


@pytest.mark.parametrize("slug", _FORMATTED_SLUGS)
def test_workspace_worktree_path_byte_identical(tmp_path, slug: str) -> None:
    got = ws.CoordinationWorkspace.worktree_path(tmp_path, slug, MID8)
    expected_dir = f"{_ref_compose_mission_dir(slug, MID8)}-coord"
    assert got == tmp_path / ".worktrees" / expected_dir
    # And byte-identical to the seam's coord_dir_name.
    assert got.name == bn.coord_dir_name(slug, mid8=MID8)


@pytest.mark.parametrize("slug", _FORMATTED_SLUGS)
def test_workspace_branch_name_byte_identical(slug: str) -> None:
    got = ws.CoordinationWorkspace.branch_name(slug, MID8)
    assert got == f"kitty/mission-{_ref_compose_mission_dir(slug, MID8)}"


def test_workspace_sparse_checkout_patterns_byte_identical() -> None:
    got = ws.lane_sparse_checkout_patterns("foo-01KV6510", MID8)
    mission_dir = _ref_compose_mission_dir("foo-01KV6510", MID8)
    assert got == [
        "/*",
        f"!kitty-specs/{mission_dir}/status.events.jsonl",
        f"!kitty-specs/{mission_dir}/status.json",
    ]


# ---------------------------------------------------------------------------
# T026 — coordination/transaction._mission_specs_dir_name delegates.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", _FORMATTED_SLUGS)
def test_transaction_specs_dir_byte_identical(slug: str) -> None:
    assert txn._mission_specs_dir_name(slug, MID8) == _ref_compose_mission_dir(slug, MID8)


def test_transaction_specs_dir_empty_mid8_trailing_dash_preserved() -> None:
    """Pre-WP06 empty-mid8 quirk: ``f"{slug}-"`` (trailing dash). Must be preserved."""
    assert txn._mission_specs_dir_name("foo", "") == _ref_compose_mission_dir("foo", "")


# ---------------------------------------------------------------------------
# T027 — coordination/status_transition._transaction_dir_name delegates.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", _FORMATTED_SLUGS)
def test_status_transition_dir_byte_identical(slug: str) -> None:
    assert st._transaction_dir_name(slug, MID8) == _ref_compose_mission_dir(slug, MID8)


def test_status_transition_dir_empty_mid8_trailing_dash_preserved() -> None:
    """The legacy/flattened path passes ``effective_mid8=""``; preserve ``f"{slug}-"``."""
    assert st._transaction_dir_name("foo", "") == _ref_compose_mission_dir("foo", "")


# ---------------------------------------------------------------------------
# T028 — coordination/surface_resolver._coord_mid8 routes through resolve_mid8.
# ---------------------------------------------------------------------------


def test_coord_mid8_prefers_declared_meta_mid8() -> None:
    from specify_cli.coordination import surface_resolver as sr

    meta = {"mid8": MID8}
    assert sr._coord_mid8(meta, "foo-01KV6510", repo_root=_DUMMY_ROOT) == MID8


def test_coord_mid8_derives_from_declared_mission_id() -> None:
    from specify_cli.coordination import surface_resolver as sr

    meta = {"mission_id": MISSION_ID}
    # Authoritative resolve_mid8 must derive from the declared mission_id, NOT a
    # coincidental slug tail.
    assert sr._coord_mid8(meta, "foo", repo_root=_DUMMY_ROOT) == MID8


def test_coord_mid8_declared_mission_id_governs_over_slug_tail() -> None:
    from specify_cli.coordination import surface_resolver as sr

    # Slug carries a divergent tail; the declared mission_id must win (#1918).
    meta = {"mission_id": MISSION_ID}
    assert sr._coord_mid8(meta, "foo-DEADBEE1", repo_root=_DUMMY_ROOT) == MID8


# ---------------------------------------------------------------------------
# T039 — missions/_create.coordination_branch_name delegates to coord_branch_name.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "slug",
    ("foo-01KV6510", "foo", "057-foo"),  # embedded, bare, and legacy NNN-.
)
def test_coordination_branch_name_byte_identical(slug: str) -> None:
    got = mc.coordination_branch_name(slug, MISSION_ID)
    assert got == _ref_coordination_branch_name(slug, MISSION_ID)


def test_coordination_branch_name_embedded_idempotent() -> None:
    assert mc.coordination_branch_name("foo-01KV6510", MISSION_ID) == "kitty/mission-foo-01KV6510"


def test_coordination_branch_name_legacy_strips_numeric_prefix() -> None:
    # The pre-WP06 body stripped the NNN- prefix and appended the mid8.
    assert mc.coordination_branch_name("057-foo", MISSION_ID) == "kitty/mission-foo-01KV6510"


# ---------------------------------------------------------------------------
# T040 — missions/_read_path_resolver._compose_mission_dir + feature_dir mirror.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", _FORMATTED_SLUGS)
def test_read_path_compose_byte_identical(slug: str) -> None:
    assert rpr._compose_mission_dir(slug, MID8) == _ref_read_path_compose_mission_dir(slug, MID8)


@pytest.mark.parametrize("slug", _FORMATTED_SLUGS)
def test_read_path_compose_empty_mid8_verbatim(slug: str) -> None:
    """Read-path composer's empty-mid8 contract returns the slug VERBATIM (no dash)."""
    assert rpr._compose_mission_dir(slug, "") == slug
    assert rpr._compose_mission_dir(slug, "") == _ref_read_path_compose_mission_dir(slug, "")


def test_compose_meta_json_path_uses_seam(tmp_path) -> None:
    # mid8_from_slug("foo-01KV6510") == "01KV6510" → dir "foo-01KV6510".
    got = rpr.compose_meta_json_path(tmp_path, "foo-01KV6510")
    assert got == tmp_path / "kitty-specs" / "foo-01KV6510" / "meta.json"
    # Bare slug → empty mid8 → verbatim dir.
    got_bare = rpr.compose_meta_json_path(tmp_path, "foo")
    assert got_bare == tmp_path / "kitty-specs" / "foo" / "meta.json"


# ---------------------------------------------------------------------------
# Golden-table cross-check: the seam primitives themselves match the table.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row", [r for r in GOLDEN_ROWS if r.mission_id is not None], ids=lambda r: r.label)
def test_golden_table_mission_and_coord(row) -> None:
    # Each row's mid8 is the first 8 chars of its OWN mission_id, not a shared
    # constant — the NNN- regression row uses a distinct mid8 (#1589).
    row_mid8 = row.mission_id[:8]
    # CANONICAL grammar (NNN- stripped) — the merge path (WP02 / #1978).
    assert bn.mission_dir_name(row.mission_slug, mid8=row_mid8) == row.mission_dir
    # VERBATIM coordination grammar (NNN- preserved) — the read/transaction path.
    assert bn.coord_mission_dir_name(row.mission_slug, mid8=row_mid8) == row.coord_mission_dir
    assert bn.coord_dir_name(row.mission_slug, mid8=row_mid8) == row.coord_dir
    # coord_branch_name is the mission-create (canonical, NNN-stripping) composer.
    assert bn.coord_branch_name(row.mission_slug, mission_id=row.mission_id) == row.mission_branch
    # coord_reconstruct_branch is the verbatim read-path composer.
    assert bn.coord_reconstruct_branch(row.mission_slug, mid8=row_mid8) == row.coord_branch
    # The delegated coordination read composer (verbatim) must equal the golden row.
    assert ws._compose_mission_dir(row.mission_slug, row_mid8) == row.coord_mission_dir
    assert ws.CoordinationWorkspace.branch_name(row.mission_slug, row_mid8) == row.coord_branch
    # mission-create (T039) composes the canonical, NNN-stripped branch.
    assert mc.coordination_branch_name(row.mission_slug, row.mission_id) == row.mission_branch


# ---------------------------------------------------------------------------
# #1589 regression: NNN- slug + SEPARATE mid8 (the live coordination input).
# The cycle-0 oracle excluded NNN- slugs and so missed the byte-level drift that
# orphaned the coord worktree (test_coordination_branch_persists_seed_events
# went PASS->FAIL). These pin EACH coordination read/transaction composer
# byte-identical to the pre-WP06 algorithm for an NNN- slug.
# ---------------------------------------------------------------------------

# A distinct mid8 NOT embedded in the slug — the live ``meta.json`` shape where
# ``mission_slug`` is the verbatim NNN- handle and ``mid8`` is supplied separately.
_NNN_SEPARATE_MID8 = "01COORD0"


def test_1589_workspace_compose_nnn_verbatim() -> None:
    got = ws._compose_mission_dir(_NNN_SLUG, _NNN_SEPARATE_MID8)
    assert got == _ref_compose_mission_dir(_NNN_SLUG, _NNN_SEPARATE_MID8)
    assert got == "060-test-01COORD0"  # VERBATIM — NNN- preserved.


def test_1589_workspace_worktree_path_nnn_verbatim(tmp_path) -> None:
    got = ws.CoordinationWorkspace.worktree_path(tmp_path, _NNN_SLUG, _NNN_SEPARATE_MID8)
    expected_dir = f"{_ref_compose_mission_dir(_NNN_SLUG, _NNN_SEPARATE_MID8)}-coord"
    assert got == tmp_path / ".worktrees" / expected_dir
    assert got.name == "060-test-01COORD0-coord"


def test_1589_workspace_branch_name_nnn_verbatim() -> None:
    got = ws.CoordinationWorkspace.branch_name(_NNN_SLUG, _NNN_SEPARATE_MID8)
    assert got == f"kitty/mission-{_ref_compose_mission_dir(_NNN_SLUG, _NNN_SEPARATE_MID8)}"
    assert got == "kitty/mission-060-test-01COORD0"  # VERBATIM — the on-disk branch.


def test_1589_transaction_specs_dir_nnn_verbatim() -> None:
    got = txn._mission_specs_dir_name(_NNN_SLUG, _NNN_SEPARATE_MID8)
    assert got == _ref_compose_mission_dir(_NNN_SLUG, _NNN_SEPARATE_MID8)
    assert got == "060-test-01COORD0"


def test_1589_status_transition_dir_nnn_verbatim() -> None:
    got = st._transaction_dir_name(_NNN_SLUG, _NNN_SEPARATE_MID8)
    assert got == _ref_compose_mission_dir(_NNN_SLUG, _NNN_SEPARATE_MID8)
    assert got == "060-test-01COORD0"


def test_1589_read_path_compose_nnn_verbatim() -> None:
    got = rpr._compose_mission_dir(_NNN_SLUG, _NNN_SEPARATE_MID8)
    assert got == _ref_read_path_compose_mission_dir(_NNN_SLUG, _NNN_SEPARATE_MID8)
    assert got == "060-test-01COORD0"


_DUMMY_ROOT = __import__("pathlib").Path("/nonexistent-test-root")
