"""Direct tests for kernel.sibling_paths — the shared sibling-path-resolution
primitive (FR-004, mission doctrine-consumer-surface-missions-extraction-01KZ6G6H).

Before this file the primitive had NO direct test coverage: it was exercised
only transitively through its three callers' own tests
(``kernel.paths.get_package_asset_root``, ``charter.offering.pack_paths._resolve_built_in``,
``charter.offering.missions.repository.MissionTemplateRepository.default_missions_root``).
That gap is exactly why two regressions (a wheel-unresolvable sibling pattern,
and a checkout-root env-var ordering bug) both shipped past review in cycle 1
without a single test catching either — see review-cycle-1.md. This module
tests the primitive itself, isolated from any caller's own pattern choices.
"""

from __future__ import annotations

import uuid
from pathlib import Path, PurePosixPath

import pytest

import kernel.paths as kernel_paths
from kernel.sibling_paths import SiblingPathNotFound, resolve_installed_sibling

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# env_override branch
# ---------------------------------------------------------------------------


class TestEnvOverride:
    """The env_override parameter wins outright when it is an existing directory."""

    def test_existing_env_override_wins_without_touching_the_filesystem_walk(
        self, tmp_path: Path
    ) -> None:
        """An existing env_override directory is returned verbatim.

        The anchor_file and sibling_relative_path point at locations that do
        NOT exist anywhere, proving the env_override branch short-circuits
        before any ancestor walk is attempted.
        """
        override_dir = tmp_path / "overridden" / "assets"
        override_dir.mkdir(parents=True)

        result = resolve_installed_sibling(
            anchor_file=tmp_path / "nonexistent" / "module.py",
            env_override=override_dir,
            sibling_relative_path=PurePosixPath("never") / "matches" / "anything",
        )

        assert result == override_dir

    def test_none_env_override_falls_through_to_the_ancestor_walk(
        self, tmp_path: Path
    ) -> None:
        """env_override=None proceeds to the ancestor walk."""
        anchor = tmp_path / "src" / "pkg" / "module.py"
        anchor.parent.mkdir(parents=True)
        sibling = tmp_path / "src" / "other" / "assets"
        sibling.mkdir(parents=True)

        result = resolve_installed_sibling(
            anchor_file=anchor,
            env_override=None,
            sibling_relative_path=PurePosixPath("*") / "assets",
        )

        assert result == sibling

    def test_nonexistent_env_override_falls_through_to_the_ancestor_walk(
        self, tmp_path: Path
    ) -> None:
        """A non-existent env_override directory does not win; the walk still runs."""
        anchor = tmp_path / "src" / "pkg" / "module.py"
        anchor.parent.mkdir(parents=True)
        sibling = tmp_path / "src" / "other" / "assets"
        sibling.mkdir(parents=True)

        result = resolve_installed_sibling(
            anchor_file=anchor,
            env_override=tmp_path / "does" / "not" / "exist",
            sibling_relative_path=PurePosixPath("*") / "assets",
        )

        assert result == sibling


# ---------------------------------------------------------------------------
# Wheel-shaped anchor — the fix-1 regression (no src/ anywhere in the tree)
# ---------------------------------------------------------------------------


def build_wheel_shaped_site_packages(tmp_path: Path) -> tuple[Path, Path]:
    """Build a synthetic installed-wheel layout: site-packages/{pkg,pkg2}, no src/.

    This is the exact shape that broke with the pre-fix ``"src/*/missions"``-style
    pattern (SC-001 regression: the wheel install has no ``src/`` directory at any
    level because the root ``pyproject.toml``'s wheel-target ``packages`` mapping
    maps ``src/doctrine`` -> ``doctrine``, dropping the ``src/`` segment).

    Shared across ``tests/kernel/test_sibling_paths.py`` (the primitive's own
    tests, below) and ``tests/kernel/test_paths.py`` (the caller-pattern pin) so
    both exercise the identical tree shape.
    """
    site = tmp_path / "site-packages"
    doctrine_assets = site / "doctrine" / "missions"
    doctrine_assets.mkdir(parents=True)
    anchor = site / "kernel" / "paths.py"
    anchor.parent.mkdir(parents=True)
    return site, anchor


def build_post_relocation_wheel_shaped_site_packages(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Build a synthetic post-relocation installed-wheel layout.

    Mission ``doctrine-consumer-surface-missions-extraction-01KZ6G6H``
    (FR-005) moved the missions DATA subdirectories from
    ``src/doctrine/missions`` to ``packs/built-in/missions``. This fixture
    contains BOTH:

    * the now data-less ``site-packages/doctrine/missions`` directory (the
      ``.py`` logic modules' own containing directory stays there and still
      physically exists post-relocation) -- the exact self-match trap a
      generic ``"*/missions"`` wildcard sibling pattern would still match,
      one ancestor level up from ``repository.py``'s own file, before ever
      considering the real data;
    * the real data at ``site-packages/packs/built-in/missions`` (``packs/built-in``
      ships as a site-packages-level sibling of every top-level package, per
      the root ``pyproject.toml``'s
      ``force-include = {"packs/built-in" = "packs/built-in"}``).

    A caller-level test using this fixture only passes if the resolver finds
    the SECOND location -- proving both that the real (relocated) data
    resolves correctly, and that the still-existing data-less sibling is not
    mistakenly preferred. Returns ``(site, kernel_anchor, repository_anchor)``
    so both ``kernel.paths.get_package_asset_root()`` and
    ``charter.offering.missions.repository.MissionTemplateRepository.default_missions_root()``
    caller-pattern tests can share one fixture shape.
    """
    site = tmp_path / "site-packages"
    doctrine_missions = site / "doctrine" / "missions"
    doctrine_missions.mkdir(parents=True)  # data-less: no data files inside

    real_missions = site / "packs" / "built-in" / "missions"
    real_missions.mkdir(parents=True)
    (real_missions / "README.md").write_text("# missions\n", encoding="utf-8")

    kernel_anchor = site / "kernel" / "paths.py"
    kernel_anchor.parent.mkdir(parents=True)

    # repository.py's own anchor sits INSIDE the (now data-less) doctrine
    # missions directory, matching its real post-relocation location.
    repository_anchor = doctrine_missions / "repository.py"

    return site, kernel_anchor, repository_anchor


class TestWheelShapedAnchor:
    """A synthetic installed-wheel layout: site-packages/{pkg,pkg2}, no src/ anywhere."""

    def test_no_src_directory_exists_anywhere_in_the_synthetic_tree(
        self, tmp_path: Path
    ) -> None:
        """Sanity-check the fixture itself: it must contain no 'src' directory."""
        site, _anchor = build_wheel_shaped_site_packages(tmp_path)
        assert not any(p.name == "src" for p in site.rglob("*"))

    def test_bare_wildcard_pattern_resolves_the_installed_sibling(
        self, tmp_path: Path
    ) -> None:
        """'*/missions' (no leading src/) resolves in a wheel-shaped layout."""
        site, anchor = build_wheel_shaped_site_packages(tmp_path)

        result = resolve_installed_sibling(
            anchor_file=anchor,
            env_override=None,
            sibling_relative_path=PurePosixPath("*") / "missions",
        )

        assert result == site / "doctrine" / "missions"

    def test_src_prefixed_pattern_cannot_resolve_in_a_wheel_layout(
        self, tmp_path: Path
    ) -> None:
        """Regression pin for the fix-1 bug: 'src/*/missions' fails closed here.

        This is the exact pattern shape that shipped in WP04 cycle 1
        (``PurePosixPath("src") / "*" / "missions"``) and made
        ``get_package_asset_root()`` unresolvable in an installed wheel. It
        must never resolve in a layout with no ``src/`` directory anywhere.
        """
        _site, anchor = build_wheel_shaped_site_packages(tmp_path)

        with pytest.raises(SiblingPathNotFound):
            resolve_installed_sibling(
                anchor_file=anchor,
                env_override=None,
                sibling_relative_path=PurePosixPath("src") / "*" / "missions",
            )

    def test_wheel_sibling_is_found_via_the_ancestor_walk_not_a_distinct_step(
        self, tmp_path: Path
    ) -> None:
        """The site-packages level is reached as an ordinary ancestor.

        Pins the item-4 finding: there is no separate "installed wheel" probe
        distinct from the ancestor walk — anchor.parent.parent (site-packages)
        is always a member of anchor.parents, so the walk alone must resolve
        this case with no other candidate present anywhere.
        """
        site, anchor = build_wheel_shaped_site_packages(tmp_path)
        assert anchor.parent.parent == site

        result = resolve_installed_sibling(
            anchor_file=anchor,
            env_override=None,
            sibling_relative_path=PurePosixPath("*") / "missions",
        )

        assert result == site / "doctrine" / "missions"


# ---------------------------------------------------------------------------
# Editable-checkout-shaped anchor
# ---------------------------------------------------------------------------


class TestEditableCheckoutShapedAnchor:
    """A synthetic editable checkout: <repo>/src/{pkg,sibling_pkg}/..."""

    def test_ancestor_walk_finds_a_sibling_package_directory(
        self, tmp_path: Path
    ) -> None:
        repo = tmp_path / "repo"
        anchor = repo / "src" / "kernel" / "paths.py"
        anchor.parent.mkdir(parents=True)
        sibling = repo / "src" / "doctrine" / "missions"
        sibling.mkdir(parents=True)

        result = resolve_installed_sibling(
            anchor_file=anchor,
            env_override=None,
            sibling_relative_path=PurePosixPath("*") / "missions",
        )

        assert result == sibling

    def test_resolve_happens_before_the_parents_walk_for_symlinked_checkouts(
        self, tmp_path: Path
    ) -> None:
        """A dir-symlinked package still resolves the real repo-root sibling.

        Pins the contract's ``.resolve()``-before-``.parents`` ordering:
        without it, a symlinked editable install would walk the symlink's own
        parents (which do not contain the real sibling) instead of the real
        repository tree's parents.
        """
        real_repo = tmp_path / "real-repo"
        real_pkg = real_repo / "src" / "kernel"
        real_pkg.mkdir(parents=True)
        sibling = real_repo / "src" / "doctrine" / "missions"
        sibling.mkdir(parents=True)

        # Symlinked "site" view onto the real package dir; the symlink's own
        # parent chain does NOT contain the sibling.
        symlink_root = tmp_path / "symlinked-view"
        symlink_root.mkdir()
        linked_pkg = symlink_root / "kernel"
        linked_pkg.symlink_to(real_pkg, target_is_directory=True)
        anchor = linked_pkg / "paths.py"

        result = resolve_installed_sibling(
            anchor_file=anchor,
            env_override=None,
            sibling_relative_path=PurePosixPath("*") / "missions",
        )

        assert result == sibling


# ---------------------------------------------------------------------------
# _first_match determinism: multiple glob matches -> stable, sorted pick
# ---------------------------------------------------------------------------


class TestDeterministicMultiMatch:
    """When a pattern matches more than one sibling, the sorted-first one wins."""

    def test_multiple_matching_siblings_pick_the_alphabetically_first(
        self, tmp_path: Path
    ) -> None:
        repo = tmp_path / "repo"
        anchor = repo / "src" / "kernel" / "paths.py"
        anchor.parent.mkdir(parents=True)

        # Three sibling packages under src/, all matching "*/missions".
        zeta_missions = repo / "src" / "zeta" / "missions"
        zeta_missions.mkdir(parents=True)
        alpha_missions = repo / "src" / "alpha" / "missions"
        alpha_missions.mkdir(parents=True)
        mid_missions = repo / "src" / "mid" / "missions"
        mid_missions.mkdir(parents=True)

        result = resolve_installed_sibling(
            anchor_file=anchor,
            env_override=None,
            sibling_relative_path=PurePosixPath("*") / "missions",
        )

        assert result == alpha_missions

    def test_pick_is_stable_across_repeated_calls(self, tmp_path: Path) -> None:
        """Determinism means the same inputs always yield the same output."""
        repo = tmp_path / "repo"
        anchor = repo / "src" / "kernel" / "paths.py"
        anchor.parent.mkdir(parents=True)
        for name in ("bravo", "alpha", "charlie"):
            (repo / "src" / name / "missions").mkdir(parents=True)

        results = {
            resolve_installed_sibling(
                anchor_file=anchor,
                env_override=None,
                sibling_relative_path=PurePosixPath("*") / "missions",
            )
            for _ in range(5)
        }

        assert len(results) == 1
        assert next(iter(results)) == repo / "src" / "alpha" / "missions"


# ---------------------------------------------------------------------------
# Fail-closed: SiblingPathNotFound
# ---------------------------------------------------------------------------


class TestFailClosed:
    """No candidate anywhere -> SiblingPathNotFound, never a nonexistent path.

    The ancestor walk in ``resolve_installed_sibling`` climbs all the way to
    the real filesystem root, so a fail-closed test must seek a pattern
    guaranteed not to exist anywhere on the real disk -- a plain word like
    ``"missions"`` can (and, on at least one development machine, did)
    collide with an unrelated real directory several levels above
    ``tmp_path``. Each pattern below is namespaced with a fresh UUID to rule
    that out.
    """

    def test_raises_sibling_path_not_found_when_nothing_matches(
        self, tmp_path: Path
    ) -> None:
        anchor = tmp_path / "isolated" / "kernel" / "paths.py"
        anchor.parent.mkdir(parents=True)
        nonce = f"does-not-exist-anywhere-{uuid.uuid4().hex}"

        with pytest.raises(SiblingPathNotFound):
            resolve_installed_sibling(
                anchor_file=anchor,
                env_override=None,
                sibling_relative_path=PurePosixPath("*") / nonce,
            )

    def test_exception_carries_sibling_relative_path_and_anchor_file(
        self, tmp_path: Path
    ) -> None:
        """The raised exception names both what was sought and where."""
        anchor = tmp_path / "isolated" / "kernel" / "paths.py"
        anchor.parent.mkdir(parents=True)
        nonce = f"nope-{uuid.uuid4().hex}"
        pattern = PurePosixPath("*") / nonce

        with pytest.raises(SiblingPathNotFound) as excinfo:
            resolve_installed_sibling(
                anchor_file=anchor,
                env_override=None,
                sibling_relative_path=pattern,
            )

        assert excinfo.value.sibling_relative_path == pattern
        assert excinfo.value.anchor_file == anchor
        # The exception message must name both facts, human-readably.
        message = str(excinfo.value)
        assert f"*/{nonce}" in message
        assert str(anchor) in message

    def test_never_returns_a_nonexistent_path(self, tmp_path: Path) -> None:
        """A directory that exists but does not match the pattern is not returned."""
        anchor = tmp_path / "repo" / "src" / "kernel" / "paths.py"
        anchor.parent.mkdir(parents=True)
        nonce = f"missions-{uuid.uuid4().hex}"
        # A directory exists here, but it does not match the sought pattern.
        (tmp_path / "repo" / "src" / "unrelated").mkdir(parents=True)

        with pytest.raises(SiblingPathNotFound):
            resolve_installed_sibling(
                anchor_file=anchor,
                env_override=None,
                sibling_relative_path=PurePosixPath("*") / nonce,
            )

    def test_broken_install_without_a_recognizable_boundary_fails_closed(
        self, tmp_path: Path
    ) -> None:
        """Bounded walk: an unrelated match several ancestors up is NOT climbed to.

        Simulates a broken install whose anchor sits under a chain of
        ordinary (non-``src``/``site-packages``/``dist-packages``-named)
        directories -- no recognizable package/installation boundary
        anywhere in its ancestry. An unrelated directory matching the sought
        pattern exists several levels further up the tree (beyond the
        primitive's fail-safe cap of ``_MAX_ANCESTORS_WITHOUT_BOUNDARY``
        ancestors). Before the bounded stop-condition, the unbounded walk
        would keep climbing past the anchor's own package structure and
        return this unrelated match -- exactly the "arbitrary tree" the
        primitive's own contract (kernel-resolution-primitive.md, step 4)
        forbids returning. The bounded walk must fail closed instead.
        """
        anchor = (
            tmp_path / "alpha" / "beta" / "gamma" / "delta" / "epsilon" / "kernel" / "module.py"
        )
        anchor.parent.mkdir(parents=True)
        # Matches "*/missions" when checked from tmp_path/alpha/beta -- five
        # ancestor hops above the anchor's own containing directory, well
        # past the fail-safe cap.
        unrelated = tmp_path / "alpha" / "beta" / "x" / "missions"
        unrelated.mkdir(parents=True)

        with pytest.raises(SiblingPathNotFound):
            resolve_installed_sibling(
                anchor_file=anchor,
                env_override=None,
                sibling_relative_path=PurePosixPath("*") / "missions",
            )


# ---------------------------------------------------------------------------
# MissionsRootNotFound — the fail-closed path in a real consumer
# ---------------------------------------------------------------------------


class TestMissionsRootNotFoundFailClosedPath:
    """default_missions_root() fails closed with MissionsRootNotFound.

    Re-pinned for mission ``resolution-activation-foundation-01KZ9FKG`` WP02
    (charter DIRECTIVE_041 re-pin discipline): ``default_missions_root()`` no
    longer calls ``resolve_installed_sibling`` directly, so it no longer
    translates a ``SiblingPathNotFound`` itself. It now delegates to
    :func:`charter.offering.pack_paths.built_in_missions_root` (a thin join onto the
    single built-in-pack-root authority) and raises ``MissionsRootNotFound``
    directly from its own ``.is_dir()`` check on the joined ``missions`` leaf.
    These tests re-point at that mechanism: monkeypatching
    ``repository_module.built_in_missions_root`` to answer a path with no
    ``missions`` leaf on disk is the equivalent fail-closed trigger in the new
    implementation -- this is the new fail-closed path introduced by FR-004 in
    ``charter.offering.missions.repository.MissionTemplateRepository``; cycle-1 review
    noted it was never reached by any test.
    """

    def test_missing_missions_leaf_raises_missions_root_not_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from charter.offering.missions import repository as repository_module
        from charter.offering.missions.repository import (
            MissionsRootNotFound,
            MissionTemplateRepository,
        )

        nonexistent_missions = tmp_path / "built-in" / "missions"
        assert not nonexistent_missions.exists()
        monkeypatch.setattr(
            repository_module, "built_in_missions_root", lambda: nonexistent_missions
        )

        with pytest.raises(MissionsRootNotFound):
            MissionTemplateRepository.default_missions_root()

    def test_default_classmethod_propagates_missions_root_not_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """MissionTemplateRepository.default() also fails closed, via the same path."""
        from charter.offering.missions import repository as repository_module
        from charter.offering.missions.repository import (
            MissionsRootNotFound,
            MissionTemplateRepository,
        )

        nonexistent_missions = tmp_path / "built-in" / "missions"
        assert not nonexistent_missions.exists()
        monkeypatch.setattr(
            repository_module, "built_in_missions_root", lambda: nonexistent_missions
        )

        with pytest.raises(MissionsRootNotFound):
            MissionTemplateRepository.default()


# ---------------------------------------------------------------------------
# _MISSIONS_ROOT_SIBLING_PATTERN — bind the caller's own pattern, not one
# written inside the test (cycle-2 review, equivalent treatment to the
# kernel.paths pin in test_paths.py::TestGetPackageAssetRoot)
# ---------------------------------------------------------------------------


class TestDefaultMissionsRootWheelLayout:
    """default_missions_root() resolves via the kernel authority's OWN committed pattern.

    ``TestWheelShapedAnchor`` above proves the shared primitive resolves
    correctly *given* a pattern the test supplies. This class instead
    monkeypatches ``kernel.paths``'s own ``__file__`` and calls the real
    public entry point, exercising the actual committed
    ``BUILT_IN_PACK_SIBLING_PATTERN`` module constant -- the constant mission
    #3091's WP05 is chartered to repoint (see ``MissionsRootNotFound``'s
    docstring). Binding it now means a future regression to that constant
    (e.g. an accidental ``src/``-prefixed shape that can never match an
    installed wheel, the same defect class WP04 cycle 1 shipped in
    ``kernel.paths``) reds here instead of shipping silently.

    Re-pinned for mission ``resolution-activation-foundation-01KZ9FKG`` WP02
    (charter DIRECTIVE_041 re-pin discipline): before this mission,
    ``default_missions_root()`` performed its own ancestor walk anchored on
    ``repository.py``'s own ``__file__``. WP02 collapsed that onto
    :func:`kernel.paths.get_built_in_pack_root`, so the anchor the ancestor
    walk actually starts from is now ``kernel.paths.__file__`` -- patching
    ``repository_module.__file__`` (as this test used to) no longer has any
    effect on the walk at all. The behavior under test (the wheel-shaped
    resolution reaching the real relocated data, not the data-less decoy) is
    unchanged and still meaningful, so this test is re-pointed at the
    relocated anchor rather than dropped.
    """

    def test_resolves_in_a_wheel_layout_via_the_kernel_s_own_pattern(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The caller-level wheel test for mission #3091's own thesis (WP05).

        Mission ``doctrine-consumer-surface-missions-extraction-01KZ6G6H``
        (FR-005) relocated the missions data from ``src/doctrine/missions``
        to ``packs/built-in/missions``, falsifying this test's own pre-move
        fixture (a lone data-less ``doctrine/missions`` directory with
        nothing else to find). Uses
        :func:`build_post_relocation_wheel_shaped_site_packages` instead,
        which plants BOTH the real relocated data (``packs/built-in/missions``)
        AND the still-existing, now data-less ``doctrine/missions`` package
        directory side by side -- proving the kernel's own committed
        ``BUILT_IN_PACK_SIBLING_PATTERN`` resolves the real data, not the
        decoy. This test reds if that pattern ever regresses to a bare/
        wildcard ``"missions"`` shape (which would match the data-less decoy
        one ancestor level above this module's own file, before ever reaching
        ``packs/built-in``) -- see ``MissionsRootNotFound``'s docstring.
        """
        from charter.offering.missions.repository import MissionTemplateRepository

        site, kernel_anchor, repository_anchor = build_post_relocation_wheel_shaped_site_packages(
            tmp_path
        )

        monkeypatch.setattr(kernel_paths, "__file__", str(kernel_anchor))

        result = MissionTemplateRepository.default_missions_root()

        assert result == site / "packs" / "built-in" / "missions"
        assert result != repository_anchor.parent, (
            "default_missions_root() self-matched its own (data-less) "
            "containing directory instead of the relocated real data -- the "
            "exact self-match trap this mission's WP05 exists to close."
        )
