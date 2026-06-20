"""WP04 (FR-008) — aggregate surface-resolution negative + create-window tests.

These tests lock in the two behaviors WP04 consolidates in
``specify_cli.status.aggregate.MissionStatus``:

T016-a — **No silent first-match on an ambiguous mid8.** A bare ``mid8`` handle
that prefixes more than one mission's ``mission_id`` resolves to a *structured*
error (:class:`MissionSelectorAmbiguous`, ``error_code ==
MISSION_AMBIGUOUS_SELECTOR``) — never a lexically-first ``sorted(glob(...))``
pick. Mutation: re-introducing a silent-pick path that returns one of the two
candidate dirs makes ``MissionStatus.load`` return an aggregate instead of
raising, and ``test_ambiguous_mid8_handle_raises_typed_error`` fails.

T016-b — **The no-coord create→first-write window resolves PRIMARY.** A mission
whose primary checkout carries the spec dir + ``meta.json`` but declares **no**
``coordination_branch`` is in the create→first-write window: the primary checkout
is authoritative and ``MissionStatus.load`` must resolve ``read_dir`` to the
primary mission dir — NOT hard-fail. This is asserted as a cell DISTINCT from the
coord-empty hard-fail (a materialised-but-empty coord worktree → WP06's
``CoordAuthorityUnavailable``), because conflating the two would regress
first-write. Mutation: hard-failing the create-window (e.g. dropping the
``on_missing_meta`` primary fallback) makes ``load`` raise and
``test_create_window_no_coord_resolves_primary`` fails.

Fixtures are production-shaped: a real 26-char ULID (Mission Identity Model 083+),
the first 8 chars as the ``mid8`` disambiguator, and the real on-disk
``kitty-specs/<slug>-<mid8>/`` + ``.worktrees/<slug>-<mid8>-coord/`` layout.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.missions._read_path_resolver import (
    MISSION_AMBIGUOUS_SELECTOR_CODE,
    MissionSelectorAmbiguous,
    primary_feature_dir_for_mission,
)
from specify_cli.status.aggregate import (
    MissionMetadataUnavailable,
    MissionStatus,
)

pytestmark = [pytest.mark.unit]

# Production-shaped identity: a real 26-char ULID, mid8 = first 8 chars.
MISSION_ID = "01KVGCE8R8QJ3K5ZJ9E5008ABC"
MID8 = MISSION_ID[:8]  # "01KVGCE8"
MISSION_SLUG = "single-mission-surface"
SLUG_WITH_MID8 = f"{MISSION_SLUG}-{MID8}"

# Two distinct missions whose mission_ids share the SAME mid8 prefix → an
# ambiguous bare-mid8 handle (the FR-008 no-silent-first-match row).
_AMBIG_MID8 = "01KVAMBG"
_AMBIG_ID_A = _AMBIG_MID8 + "0AAAAAAAAAAAAAAAAA"  # 26-char ULID-shaped
_AMBIG_ID_B = _AMBIG_MID8 + "0BBBBBBBBBBBBBBBBB"


def _write_meta(feature_dir: Path, **fields: object) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(json.dumps(fields), encoding="utf-8")


# ---------------------------------------------------------------------------
# T016-a — ambiguous mid8 → MISSION_AMBIGUOUS_SELECTOR (no silent first-match)
# ---------------------------------------------------------------------------


def test_ambiguous_mid8_handle_raises_typed_error(tmp_path: Path) -> None:
    """A bare ambiguous mid8 raises MissionSelectorAmbiguous, never a silent pick.

    FR-008 — ``MissionStatus.load`` routes mid8 disambiguation through the ONE
    canonical handle resolver, which raises a *structured* error on ambiguity.
    The old ``sorted(specs_dir.glob(f"{slug}-*/meta.json"))`` first-match path is
    gone; re-introducing any silent-pick path (returning one of the two candidate
    dirs) would make ``load`` succeed instead of raising — and fail this test.
    """
    _write_meta(tmp_path / "kitty-specs" / "alpha-surface", mission_id=_AMBIG_ID_A)
    _write_meta(tmp_path / "kitty-specs" / "beta-surface", mission_id=_AMBIG_ID_B)

    with pytest.raises(MissionSelectorAmbiguous) as excinfo:
        MissionStatus.load(repo_root=tmp_path, mission_slug=_AMBIG_MID8)

    # The stable routing code — asserted explicitly so a type-only divergence
    # (a different exception that happens to subclass the same base) is caught.
    assert excinfo.value.error_code == MISSION_AMBIGUOUS_SELECTOR_CODE
    assert excinfo.value.error_code == "MISSION_AMBIGUOUS_SELECTOR"
    # Both colliding candidates are named in the structured error (operator can
    # disambiguate) — proof the resolver saw BOTH and refused to pick one.
    assert set(excinfo.value.candidates) == {"alpha-surface", "beta-surface"}
    assert excinfo.value.handle == _AMBIG_MID8


def test_ambiguous_mid8_does_not_resolve_to_a_directory(tmp_path: Path) -> None:
    """The ambiguous handle yields NO aggregate at all (mutation tripwire).

    A silent first-match regression would return a populated
    :class:`MissionStatus` whose ``read_dir`` is one of the two colliding
    primary dirs. Asserting that ``load`` raises (rather than returning either
    candidate) is the direct mutation kill for the deleted glob.
    """
    dir_a = tmp_path / "kitty-specs" / "alpha-surface"
    dir_b = tmp_path / "kitty-specs" / "beta-surface"
    _write_meta(dir_a, mission_id=_AMBIG_ID_A)
    _write_meta(dir_b, mission_id=_AMBIG_ID_B)

    resolved: MissionStatus | None = None
    try:
        resolved = MissionStatus.load(repo_root=tmp_path, mission_slug=_AMBIG_MID8)
    except MissionSelectorAmbiguous:
        resolved = None

    assert resolved is None, (
        "ambiguous mid8 must not resolve to a MissionStatus pointing at "
        f"{dir_a} or {dir_b} (FR-008 no silent first-match)"
    )


def test_find_meta_path_propagates_ambiguous_selector(tmp_path: Path) -> None:
    """``_find_meta_path`` propagates ambiguity instead of swallowing it.

    The deleted code caught ``MissionSelectorAmbiguous`` (``candidate_dir =
    None``) and fell through to the silent glob. Calling the private helper
    directly proves the suppression is gone: an ambiguous bare mid8 raises the
    typed error straight out of ``_find_meta_path``. Mutation: re-adding the
    ``except MissionSelectorAmbiguous: candidate_dir = None`` swallow makes this
    return a ``(meta_path, dir)`` tuple instead of raising → this test fails.
    """
    _write_meta(tmp_path / "kitty-specs" / "alpha-surface", mission_id=_AMBIG_ID_A)
    _write_meta(tmp_path / "kitty-specs" / "beta-surface", mission_id=_AMBIG_ID_B)

    with pytest.raises(MissionSelectorAmbiguous) as excinfo:
        MissionStatus._find_meta_path(tmp_path, _AMBIG_MID8)

    assert excinfo.value.error_code == "MISSION_AMBIGUOUS_SELECTOR"
    assert set(excinfo.value.candidates) == {"alpha-surface", "beta-surface"}


# ---------------------------------------------------------------------------
# T016-b — no-coord create→first-write window resolves PRIMARY (NOT hard-fail)
# ---------------------------------------------------------------------------


def test_create_window_no_coord_resolves_primary(tmp_path: Path) -> None:
    """Create→first-write (no coordination_branch) resolves to the PRIMARY dir.

    The primary checkout carries the spec dir + ``meta.json`` but declares NO
    ``coordination_branch`` — the create→first-write window. The primary checkout
    is authoritative; ``load`` must resolve ``read_dir`` to the primary mission
    dir and classify the topology as ``legacy``, NOT hard-fail. This is a DISTINCT
    cell from coord-empty (see ``test_coord_empty_is_a_separate_hard_fail_cell``):
    a regression that hard-failed here would break first-write.
    """
    primary_dir = tmp_path / "kitty-specs" / SLUG_WITH_MID8
    _write_meta(primary_dir, mission_id=MISSION_ID)  # no coordination_branch

    ms = MissionStatus.load(repo_root=tmp_path, mission_slug=SLUG_WITH_MID8)

    assert ms.read_dir.resolve() == primary_dir.resolve(), (
        "create→first-write window must resolve to the primary checkout, not a "
        "coord path or a hard-fail (WP04 T016)"
    )
    assert ms.topology == "legacy"
    assert ms.mission_id == MISSION_ID
    assert ms.mid8 == MID8
    assert ms.coordination_branch is None


def test_create_window_bare_human_slug_resolves_primary(tmp_path: Path) -> None:
    """The create-window also resolves for the canonical literal dir name.

    The literal ``<slug>-<mid8>`` dir already names the canonical directory, so
    the meta read short-circuits on the pure-path happy path (no handle
    disambiguation, no git read) — proving the create-window resolution does not
    depend on a materialised git repo.
    """
    primary_dir = tmp_path / "kitty-specs" / SLUG_WITH_MID8
    _write_meta(primary_dir, mission_id=MISSION_ID, mission_slug=SLUG_WITH_MID8)

    ms = MissionStatus.load(repo_root=tmp_path, mission_slug=SLUG_WITH_MID8)

    assert ms.read_dir.resolve() == primary_dir.resolve()
    assert ms.topology == "legacy"


def test_missing_mission_dir_resolves_primary_via_on_missing_meta(
    tmp_path: Path,
) -> None:
    """A mission with NO dir at all resolves to PRIMARY (on_missing_meta path).

    This exercises the thin adapter's ``on_missing_meta = primary_candidate``
    contract directly: when neither ``meta.json`` nor the mission dir exists, the
    canonical surface raises ``FileNotFoundError`` and the delegator returns the
    caller-supplied primary directory (so the caller can render its own
    "directory not found" diagnostic) rather than letting the bare
    ``FileNotFoundError`` crash ``load``. Mutation: dropping the
    ``on_missing_meta`` fallback (letting ``FileNotFoundError`` escape) makes
    ``load`` raise here → this test fails.
    """
    # NB: ``kitty-specs/`` is created but the mission dir is NOT — neither the
    # dir nor meta.json exists, so the surface authority raises FileNotFoundError.
    (tmp_path / "kitty-specs").mkdir(parents=True)
    expected_primary = (tmp_path / "kitty-specs" / "ghost-mission").resolve()

    ms = MissionStatus.load(repo_root=tmp_path, mission_slug="ghost-mission")

    assert ms.read_dir.resolve() == expected_primary
    assert ms.topology == "legacy"
    assert ms.mission_id is None
    assert ms.mid8 == ""


def test_coord_empty_is_a_separate_hard_fail_cell(tmp_path: Path) -> None:
    """coord-empty (materialised coord worktree, no mission dir) HARD-FAILS.

    This is the cell that MUST stay distinct from the create-window above:
    ``coordination_branch`` is declared AND the coord worktree root is
    materialised, but it carries no mission dir → reading the primary would
    expose a stale, split-brain surface, so ``load`` raises
    :class:`CoordAuthorityUnavailable` (FR-006, WP06 owns the cross-resolver
    error-type convergence). Asserting this here proves the re-gate removal in
    ``_resolve_read_dir`` did NOT collapse coord-empty into the primary fallback.
    """
    from specify_cli.coordination.workspace import CoordinationWorkspace
    from specify_cli.status.aggregate import CoordAuthorityUnavailable

    coord_branch = f"kitty/mission-{SLUG_WITH_MID8}"
    primary_dir = tmp_path / "kitty-specs" / SLUG_WITH_MID8
    _write_meta(
        primary_dir,
        mission_id=MISSION_ID,
        coordination_branch=coord_branch,
    )
    # Materialise the coord worktree ROOT but NOT its mission dir (coord-empty).
    coord_root = CoordinationWorkspace.worktree_path(tmp_path, SLUG_WITH_MID8, MID8)
    coord_root.mkdir(parents=True)

    with pytest.raises(CoordAuthorityUnavailable) as excinfo:
        MissionStatus.load(repo_root=tmp_path, mission_slug=SLUG_WITH_MID8)

    assert excinfo.value.mission_slug == SLUG_WITH_MID8


def test_unmaterialized_coord_create_window_resolves_primary(tmp_path: Path) -> None:
    """Coord declared but worktree NOT materialised → primary still authoritative.

    The companion to the coord-empty hard-fail: when ``coordination_branch`` is
    declared but the coord worktree root does NOT yet exist (the pre-first-write
    window), the aggregate keeps the PRIMARY checkout authoritative — the canonical
    surface composes the coord path as-is and defers the authority decision to the
    aggregate call site, which holds the create-window gate. A regression that
    routed this to the composed (non-existent) coord dir would break first-write
    on a freshly-created coord mission.
    """
    primary_dir = tmp_path / "kitty-specs" / SLUG_WITH_MID8
    _write_meta(
        primary_dir,
        mission_id=MISSION_ID,
        coordination_branch=f"kitty/mission-{SLUG_WITH_MID8}",
    )
    # NB: no coord worktree root created → unmaterialised.

    ms = MissionStatus.load(repo_root=tmp_path, mission_slug=SLUG_WITH_MID8)

    assert ms.read_dir.resolve() == primary_dir.resolve(), (
        "declared-but-unmaterialised coord must keep the primary checkout "
        "authoritative until the worktree exists (create→first-write window)"
    )


# ---------------------------------------------------------------------------
# T014 structural guard — no second mid8 silent-glob path remains in aggregate
# ---------------------------------------------------------------------------


def test_aggregate_has_no_silent_first_match_glob() -> None:
    """Static guard: ``aggregate.py`` makes no ``glob(...)`` CALL for selection.

    The deleted FR-008 violation was a ``sorted(specs_dir.glob(f"{slug}-*/
    meta.json"))`` first-match in ``_find_meta_path``. This guard parses the
    module AST and asserts no ``.glob(...)`` call node remains, so no second mid8
    selection path is silently re-introduced into the aggregate — all
    disambiguation must route through the canonical handle resolver. (An AST
    check, not a substring scan, so prose that *describes* the removed glob does
    not trip the guard.)
    """
    import ast

    source = Path(MissionStatus.load.__globals__["__file__"]).read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    glob_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "glob"
    ]
    assert not glob_calls, (
        "aggregate.py must not perform its own glob-based mission selection; "
        "route through candidate_feature_dir_for_mission (FR-008). Found "
        f"{len(glob_calls)} glob call(s)."
    )


# ---------------------------------------------------------------------------
# WP01 raw-bypass — save() diagnostic path routes through the blessed
# path-constructor (no raw ``repo_root / KITTY_SPECS_DIR / <slug>`` even on
# the identity-missing error path)
# ---------------------------------------------------------------------------


def test_save_without_identity_raises_via_blessed_path_constructor(
    tmp_path: Path,
) -> None:
    """``save()`` on an identity-less aggregate raises through the resolver.

    When a ``MissionStatus`` carries no ``mission_id`` (legacy/un-minted
    mission), ``save()`` cannot persist via ``BookkeepingTransaction`` and must
    raise :class:`MissionMetadataUnavailable`. WP01 routes the *diagnostic*
    ``primary_candidate`` / ``meta_path`` through the blessed
    ``primary_feature_dir_for_mission`` constructor rather than a raw
    ``repo_root / KITTY_SPECS_DIR / <slug>`` self-composition — even on this
    error path. This test executes that branch (the function-local import + the
    ``diag_primary = primary_feature_dir_for_mission(...)`` call) and asserts the
    payload is exactly what the constructor yields. Mutation: re-inlining a raw
    path here (or dropping the guard) makes the payload diverge or the call not
    raise → this test fails.
    """
    expected_primary = primary_feature_dir_for_mission(tmp_path, MISSION_SLUG)

    aggregate = MissionStatus(
        mission_slug=MISSION_SLUG,
        mission_id=None,
        mid8="",
        topology="legacy",
        read_dir=tmp_path / "kitty-specs" / MISSION_SLUG,
        repo_root=tmp_path,
    )

    with pytest.raises(MissionMetadataUnavailable) as excinfo:
        aggregate.save(operation="status transition")

    err = excinfo.value
    assert err.mission_slug == MISSION_SLUG
    assert err.primary_candidate.resolve() == expected_primary.resolve()
    assert err.meta_path.resolve() == (expected_primary / "meta.json").resolve()
    assert "mission_id is required" in str(err)


def test_save_with_blank_mid8_raises_via_blessed_path_constructor(
    tmp_path: Path,
) -> None:
    """A present ``mission_id`` but blank ``mid8`` also hits the diagnostic path.

    The guard is ``mission_id is None or not self.mid8`` — a (data-corruption)
    aggregate with an identity but an empty ``mid8`` disambiguator likewise
    cannot acquire a ``BookkeepingTransaction`` and must raise through the same
    blessed-path diagnostic branch. Covering this second disjunct arm keeps the
    guard from silently narrowing to ``mission_id is None`` alone.
    """
    expected_primary = primary_feature_dir_for_mission(tmp_path, MISSION_SLUG)

    aggregate = MissionStatus(
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        mid8="",  # corrupt: identity present but disambiguator missing
        topology="legacy",
        read_dir=tmp_path / "kitty-specs" / MISSION_SLUG,
        repo_root=tmp_path,
    )

    with pytest.raises(MissionMetadataUnavailable) as excinfo:
        aggregate.save(operation="status transition")

    assert excinfo.value.primary_candidate.resolve() == expected_primary.resolve()
