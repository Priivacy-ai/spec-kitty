"""Unit tests for the ``MissionResolver`` port (mission-resolver-port-01KX1C05 WP02).

Covers the behavioral contract (CT-1..CT-7) from
``kitty-specs/mission-resolver-port-01KX1C05/contracts/mission-resolver.md``:

- CT-1: priority ladder (ULID / mid8 / numbered slug / human slug / numeric prefix).
- CT-2: ambiguous handle raises ``AmbiguousHandleError`` (never first-match-wins).
- CT-3: cold-miss raises ``MissionNotFoundError`` naming
  ``spec-kitty migrate backfill-identity``.
- CT-4: ``all_missions()`` skips ``mission_id``-less dirs.
- CT-5: ``FakeMissionResolver`` satisfies CT-1..CT-4 with **zero** filesystem
  access (no ``kitty-specs/`` tree present at all).
- CT-7: no module/process-level cache — independent resolver instances see
  independent state.

Fixtures use realistic, valid 26-char Crockford-base32 ULID-shaped mission
ids (matching the convention already established in
``tests/context/test_mission_resolver.py``), not toy handles.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from specify_cli.context import mission_resolver as mission_resolver_module
from specify_cli.context.mission_resolver import (
    AmbiguousHandleError,
    FakeMissionResolver,
    FsMissionResolver,
    MissionNotFoundError,
    ResolvedMission,
    resolve_mission,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Realistic ULID-shaped fixture ids (26-char Crockford base32, distinct mid8)
# ---------------------------------------------------------------------------

MISSION_ID_ALPHA = "01K9C7H4NBRW2QATZX8G6M3D5F"  # mid8: 01K9C7H4
MISSION_ID_BETA = "01K9C7QT8YEJM2WVN4XR7B0KDG"  # mid8: 01K9C7QT
MISSION_ID_GAMMA = "01K9C8B1SXH6P3TLW9RQ2NDMFC"  # mid8: 01K9C8B1
MISSION_ID_DELTA = "01K9C8ZK4VDGM7XQE1NRT6SPWB"  # mid8: 01K9C8ZK


def _make_mission_dir(specs_dir: Path, slug: str, mission_id: str | None) -> Path:
    """Create a ``kitty-specs/<slug>/meta.json`` fixture on disk."""
    feature_dir = specs_dir / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {"mission_slug": slug}
    if mission_id is not None:
        meta["mission_id"] = mission_id
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return feature_dir


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    """Temp repo with 5 missions on disk:

    - 090-alpha-service    (MISSION_ID_ALPHA, unique numeric prefix 090)
    - 091-beta-flow        (MISSION_ID_BETA, prefix 091 — ambiguous with 091-beta-gate)
    - 091-beta-gate        (MISSION_ID_GAMMA, prefix 091 — ambiguous with 091-beta-flow)
    - 095-delta-unique     (MISSION_ID_DELTA, unique prefix 095)
    - 100-legacy-no-id     (mission_id missing — legacy/orphan, silently skipped)
    """
    specs = tmp_path / "kitty-specs"
    _make_mission_dir(specs, "090-alpha-service", MISSION_ID_ALPHA)
    _make_mission_dir(specs, "091-beta-flow", MISSION_ID_BETA)
    _make_mission_dir(specs, "091-beta-gate", MISSION_ID_GAMMA)
    _make_mission_dir(specs, "095-delta-unique", MISSION_ID_DELTA)
    _make_mission_dir(specs, "100-legacy-no-id", mission_id=None)
    return tmp_path


def _in_memory_missions() -> list[ResolvedMission]:
    """Canonical-shaped ``ResolvedMission`` fixtures with no disk backing.

    Deliberately does NOT create any ``feature_dir`` on disk — the whole
    point of CT-5 is that ``FakeMissionResolver`` needs none.
    """
    return [
        ResolvedMission(
            mission_id=MISSION_ID_ALPHA,
            mission_slug="090-alpha-service",
            feature_dir=Path("/nonexistent/kitty-specs/090-alpha-service"),
            mid8=MISSION_ID_ALPHA[:8],
        ),
        ResolvedMission(
            mission_id=MISSION_ID_BETA,
            mission_slug="091-beta-flow",
            feature_dir=Path("/nonexistent/kitty-specs/091-beta-flow"),
            mid8=MISSION_ID_BETA[:8],
        ),
        ResolvedMission(
            mission_id=MISSION_ID_GAMMA,
            mission_slug="091-beta-gate",
            feature_dir=Path("/nonexistent/kitty-specs/091-beta-gate"),
            mid8=MISSION_ID_GAMMA[:8],
        ),
        ResolvedMission(
            mission_id=MISSION_ID_DELTA,
            mission_slug="095-delta-unique",
            feature_dir=Path("/nonexistent/kitty-specs/095-delta-unique"),
            mid8=MISSION_ID_DELTA[:8],
        ),
    ]


# ---------------------------------------------------------------------------
# CT-1: priority ladder, via FsMissionResolver
# ---------------------------------------------------------------------------


class TestFsMissionResolverPriorityLadder:
    """CT-1 over :class:`FsMissionResolver` (the real, filesystem-backed adapter)."""

    def test_resolve_by_full_ulid(self, repo_root: Path) -> None:
        resolver = FsMissionResolver(repo_root)
        result = resolver.resolve(MISSION_ID_ALPHA)
        assert result.mission_id == MISSION_ID_ALPHA
        assert result.mission_slug == "090-alpha-service"

    def test_resolve_by_mid8(self, repo_root: Path) -> None:
        resolver = FsMissionResolver(repo_root)
        result = resolver.resolve(MISSION_ID_DELTA[:8])
        assert result.mission_id == MISSION_ID_DELTA

    def test_resolve_by_numbered_slug(self, repo_root: Path) -> None:
        resolver = FsMissionResolver(repo_root)
        result = resolver.resolve("090-alpha-service")
        assert result.mission_id == MISSION_ID_ALPHA

    def test_resolve_by_human_slug(self, repo_root: Path) -> None:
        resolver = FsMissionResolver(repo_root)
        result = resolver.resolve("delta-unique")
        assert result.mission_id == MISSION_ID_DELTA

    def test_resolve_by_numeric_prefix(self, repo_root: Path) -> None:
        resolver = FsMissionResolver(repo_root)
        result = resolver.resolve("095")
        assert result.mission_id == MISSION_ID_DELTA


# ---------------------------------------------------------------------------
# CT-2 / CT-3: fail-closed-loud
# ---------------------------------------------------------------------------


class TestFailClosedLoud:
    def test_ambiguous_numeric_prefix_raises(self, repo_root: Path) -> None:
        """CT-2: two missions share prefix 091 -> AmbiguousHandleError, never first-match."""
        resolver = FsMissionResolver(repo_root)
        with pytest.raises(AmbiguousHandleError) as exc_info:
            resolver.resolve("091")
        slugs = {c.mission_slug for c in exc_info.value.candidates}
        assert slugs == {"091-beta-flow", "091-beta-gate"}

    def test_cold_miss_raises_not_found(self, repo_root: Path) -> None:
        """CT-3: an unknown handle raises MissionNotFoundError."""
        resolver = FsMissionResolver(repo_root)
        with pytest.raises(MissionNotFoundError):
            resolver.resolve("999-does-not-exist")

    def test_cold_miss_message_names_backfill_identity(self, repo_root: Path) -> None:
        """CT-3: the error message names the migrate-backfill-identity remediation.

        No ``is None`` / ``or slug`` silent fallback exists anywhere in the
        resolution path (ADR 2026-07-01-1) -- a miss always raises.
        """
        resolver = FsMissionResolver(repo_root)
        with pytest.raises(MissionNotFoundError) as exc_info:
            resolver.resolve("999-does-not-exist")
        assert "spec-kitty migrate backfill-identity" in str(exc_info.value)

    def test_no_fallback_branch_in_resolution_source(self) -> None:
        """Structural guard: no reflexive ``is None`` / ``or slug`` fallback (D-05).

        The motivating incident (PR #2277) was exactly this shape of bug; this
        pins its absence at the source-text level so it cannot silently
        reappear in this module.
        """
        source = inspect.getsource(mission_resolver_module)
        assert "mission_id or slug" not in source
        assert "or self.mission_slug" not in source


# ---------------------------------------------------------------------------
# CT-4: all_missions() skips mission_id-less dirs
# ---------------------------------------------------------------------------


class TestAllMissionsSkipsIdentityLess:
    def test_fs_all_missions_skips_legacy_no_id(self, repo_root: Path) -> None:
        resolver = FsMissionResolver(repo_root)
        slugs = {m.mission_slug for m in resolver.all_missions()}
        assert slugs == {
            "090-alpha-service",
            "091-beta-flow",
            "091-beta-gate",
            "095-delta-unique",
        }
        assert "100-legacy-no-id" not in slugs

    def test_fs_all_missions_count(self, repo_root: Path) -> None:
        resolver = FsMissionResolver(repo_root)
        assert len(resolver.all_missions()) == 4


# ---------------------------------------------------------------------------
# CT-5: FakeMissionResolver satisfies CT-1..CT-4 with ZERO filesystem access
# ---------------------------------------------------------------------------


class TestFakeMissionResolverFsFree:
    """CT-5: same contract as FsMissionResolver, but backed by an in-memory list.

    None of these tests write to ``tmp_path`` or reference any
    ``kitty-specs/`` tree -- the fixtures point at a ``/nonexistent`` path
    that is never touched, proving the Fake performs no I/O.
    """

    def test_resolve_by_full_ulid(self) -> None:
        resolver = FakeMissionResolver(_in_memory_missions())
        result = resolver.resolve(MISSION_ID_ALPHA)
        assert result.mission_slug == "090-alpha-service"

    def test_resolve_by_mid8(self) -> None:
        resolver = FakeMissionResolver(_in_memory_missions())
        result = resolver.resolve(MISSION_ID_DELTA[:8])
        assert result.mission_id == MISSION_ID_DELTA

    def test_resolve_by_numbered_slug(self) -> None:
        resolver = FakeMissionResolver(_in_memory_missions())
        result = resolver.resolve("090-alpha-service")
        assert result.mission_id == MISSION_ID_ALPHA

    def test_resolve_by_human_slug(self) -> None:
        resolver = FakeMissionResolver(_in_memory_missions())
        result = resolver.resolve("delta-unique")
        assert result.mission_id == MISSION_ID_DELTA

    def test_resolve_by_numeric_prefix(self) -> None:
        resolver = FakeMissionResolver(_in_memory_missions())
        result = resolver.resolve("095")
        assert result.mission_id == MISSION_ID_DELTA

    def test_ambiguous_raises(self) -> None:
        resolver = FakeMissionResolver(_in_memory_missions())
        with pytest.raises(AmbiguousHandleError):
            resolver.resolve("091")

    def test_cold_miss_raises_with_backfill_guidance(self) -> None:
        resolver = FakeMissionResolver(_in_memory_missions())
        with pytest.raises(MissionNotFoundError) as exc_info:
            resolver.resolve("999-nope")
        assert "spec-kitty migrate backfill-identity" in str(exc_info.value)

    def test_all_missions_returns_exactly_the_fixture_set(self) -> None:
        """CT-4 analogue: the Fake has no identity-less dirs to skip, but the
        fixture list is returned faithfully (no silent filtering surprises)."""
        missions = _in_memory_missions()
        resolver = FakeMissionResolver(missions)
        assert {m.mission_id for m in resolver.all_missions()} == {
            MISSION_ID_ALPHA,
            MISSION_ID_BETA,
            MISSION_ID_GAMMA,
            MISSION_ID_DELTA,
        }

    def test_no_kitty_specs_tree_required(self, tmp_path: Path) -> None:
        """The defining Fake property: works with no kitty-specs/ dir at all.

        ``tmp_path`` here is a bare empty directory -- deliberately never
        populated with a ``kitty-specs/`` tree -- to prove the Fake's
        resolution does not depend on ``repo_root`` in any way.
        """
        assert not (tmp_path / "kitty-specs").exists()
        resolver = FakeMissionResolver(_in_memory_missions())
        result = resolver.resolve(MISSION_ID_ALPHA)
        assert result.mission_slug == "090-alpha-service"
        assert not (tmp_path / "kitty-specs").exists()  # still doesn't exist


# ---------------------------------------------------------------------------
# CT-7: no module/process-level cache
# ---------------------------------------------------------------------------


class TestNoCache:
    def test_independent_instances_see_independent_state(self, repo_root: Path) -> None:
        """Two FsMissionResolver instances over the same repo_root each see
        live state -- a mission created after the first instance is
        constructed is visible to a second instance's resolve(), proving
        there is no process/module-level cache of the walk (C-005)."""
        first = FsMissionResolver(repo_root)
        assert len(first.all_missions()) == 4

        new_id = "01K9C9G2QWM4T8XN3RVB6HZDLP"
        _make_mission_dir(repo_root / "kitty-specs", "096-epsilon-new", new_id)

        second = FsMissionResolver(repo_root)
        assert len(second.all_missions()) == 5
        assert second.resolve(new_id).mission_slug == "096-epsilon-new"

        # The FIRST instance also observes the new mission on a fresh call --
        # it holds no cached index from its earlier all_missions() call either.
        assert len(first.all_missions()) == 5

    def test_no_lru_cache_or_module_cache_in_source(self) -> None:
        """Structural guard: no ``@lru_cache`` / module-level cache (C-005)."""
        source = inspect.getsource(mission_resolver_module)
        assert "lru_cache" not in source
        assert "@cache" not in source

    def test_fake_instances_are_independent(self) -> None:
        """A FakeMissionResolver mutated via its own list does not leak into
        a sibling instance constructed from a separately-built fixture list."""
        first_missions = _in_memory_missions()
        first = FakeMissionResolver(first_missions)

        second_missions = _in_memory_missions()[:1]  # only MISSION_ID_ALPHA
        second = FakeMissionResolver(second_missions)

        assert len(first.all_missions()) == 4
        assert len(second.all_missions()) == 1
        with pytest.raises(MissionNotFoundError):
            second.resolve(MISSION_ID_DELTA)


# ---------------------------------------------------------------------------
# T009: the free `resolve_mission` gains an optional `resolver` param
# ---------------------------------------------------------------------------


class TestResolveMissionResolverParam:
    def test_default_behavior_unchanged_without_resolver(self, repo_root: Path) -> None:
        """Callers passing no resolver get exactly the previous behavior."""
        result = resolve_mission(MISSION_ID_ALPHA, repo_root)
        assert result.mission_id == MISSION_ID_ALPHA

    def test_injected_resolver_is_actually_used(self, tmp_path: Path) -> None:
        """Passing a FakeMissionResolver bypasses the filesystem walk entirely.

        ``tmp_path`` has no ``kitty-specs/`` tree; if ``resolve_mission``
        silently ignored ``resolver`` and fell back to a fresh
        ``FsMissionResolver(repo_root)``, this would raise
        ``MissionNotFoundError`` instead of succeeding.
        """
        fake = FakeMissionResolver(_in_memory_missions())
        result = resolve_mission(MISSION_ID_ALPHA, tmp_path, resolver=fake)
        assert result.mission_slug == "090-alpha-service"

    def test_injected_resolver_preserves_fail_closed_contract(self, tmp_path: Path) -> None:
        fake = FakeMissionResolver(_in_memory_missions())
        with pytest.raises(AmbiguousHandleError):
            resolve_mission("091", tmp_path, resolver=fake)
