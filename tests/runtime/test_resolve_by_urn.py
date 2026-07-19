"""Tests for the resolve-by-URN lane (WP07/T032, FR-010, C-004).

Covers:
- US3.2: for an authored template, by-URN resolution resolves to the SAME
  file as by-name resolution.
- US3.3: a ``.kittify/overrides/templates/<file>`` override wins on the URN
  lane too, proving it honours the same 5-tier precedence as the name lane.
- C-001 fail-closed behaviour: absent/blank/malformed/unresolvable URNs
  raise :class:`TemplateURNError` rather than silently defaulting the
  mission segment to ``"software-dev"``.

``contracts/name-urn-resolution.md`` is the authoritative source for these
invariants.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.runtime.resolver import (
    ResolutionTier,
    TemplateURNError,
    resolve_template,
    resolve_template_by_urn,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _create_file(path: Path, content: str = "placeholder") -> Path:
    """Create a file (and any missing parent dirs), return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# US3.2 -- Equivalence: by-URN resolves to the same file as by-name
# ---------------------------------------------------------------------------


class TestEquivalence:
    """For an authored template, by-URN and by-name resolve to the same file."""

    def test_urn_and_name_resolve_to_the_same_package_default_file(
        self, tmp_path: Path
    ) -> None:
        """A real, shipped authored template (``software-dev/spec-template.md``)
        resolves to the same on-disk path whether reached by name (Lane 1's
        underlying :func:`resolve_template`) or by URN (Lane 2,
        :func:`resolve_template_by_urn`). Both lanes fall through every
        project-scoped tier to the same PACKAGE_DEFAULT file, proving they
        converge on the same Stage-2 resolver rather than drifting.
        """
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        empty_home = tmp_path / "empty_home"

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=empty_home,
            ),
            patch("doctrine.resolver.get_kittify_home", return_value=empty_home),
        ):
            name_result = resolve_template(
                "spec-template.md", project, mission="software-dev"
            )
            urn_result = resolve_template_by_urn(
                "template:software-dev/spec-template.md", project
            )

        assert urn_result.path == name_result.path
        assert urn_result.path.is_file()
        assert urn_result.tier == ResolutionTier.PACKAGE_DEFAULT
        assert name_result.tier == ResolutionTier.PACKAGE_DEFAULT

    def test_urn_and_name_agree_when_neither_side_has_customization(
        self, tmp_path: Path
    ) -> None:
        """Same as above for a second real content template, guarding
        against a coincidental match on a single filename.
        """
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        empty_home = tmp_path / "empty_home"

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=empty_home,
            ),
            patch("doctrine.resolver.get_kittify_home", return_value=empty_home),
        ):
            name_result = resolve_template(
                "tasks-template.md", project, mission="software-dev"
            )
            urn_result = resolve_template_by_urn(
                "template:software-dev/tasks-template.md", project
            )

        assert urn_result.path == name_result.path
        assert urn_result.path.is_file()


# ---------------------------------------------------------------------------
# US3.3 -- Override wins on the URN lane too
# ---------------------------------------------------------------------------


class TestOverrideWinsOnUrnLane:
    """A project override wins for the URN lane, exactly as for the name lane."""

    def test_project_override_wins_over_package_default_on_urn_lane(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "project"
        override_path = _create_file(
            project / ".kittify" / "overrides" / "templates" / "spec-template.md",
            content="# Project-customized spec template",
        )

        result = resolve_template_by_urn(
            "template:software-dev/spec-template.md", project
        )

        assert result.tier == ResolutionTier.OVERRIDE
        assert result.path == override_path
        assert result.path.read_text() == "# Project-customized spec template"

    def test_override_wins_matches_the_name_lane_for_the_same_project(
        self, tmp_path: Path
    ) -> None:
        """The override-tier winner is identical on both lanes for the same
        project + filename -- the URN lane doesn't just happen to find *an*
        override, it finds the *same* one the name lane would.
        """
        project = tmp_path / "project"
        override_path = _create_file(
            project / ".kittify" / "overrides" / "templates" / "spec-template.md",
            content="# Shared override content",
        )

        name_result = resolve_template(
            "spec-template.md", project, mission="software-dev"
        )
        urn_result = resolve_template_by_urn(
            "template:software-dev/spec-template.md", project
        )

        assert name_result.path == override_path
        assert urn_result.path == override_path
        assert name_result.tier == urn_result.tier == ResolutionTier.OVERRIDE

    def test_legacy_tier_also_wins_over_package_default_on_urn_lane(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sanity: the URN lane honours the *full* 5-tier chain, not just
        override -- legacy still beats package default.
        """
        project = tmp_path / "project"
        legacy_path = _create_file(
            project / ".kittify" / "templates" / "spec-template.md",
            content="# Legacy customization",
        )

        # ``_warn_legacy_asset`` emits the DeprecationWarning only when NO global
        # runtime is configured; when ``_is_global_runtime_configured()`` is True
        # (``get_kittify_home()/cache/version.lock`` exists) it SUPPRESSES the
        # warning and prints a one-time stderr nudge instead. On a dev box / CI
        # where the real ``~/.kittify`` is bootstrapped, that predicate is True and
        # the assertion captures 0 warnings (the #2812 flake). Point SPEC_KITTY_HOME
        # -- the env seam ``get_kittify_home`` reads FIRST and uncached -- at a
        # fresh empty dir so the emit branch runs deterministically. Using the env
        # (not a ``patch(...)``) makes this immune to the module-reload / patch-
        # binding ordering that defeated a predicate patch in full-suite runs.
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "empty_home"))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = resolve_template_by_urn(
                "template:software-dev/spec-template.md", project
            )

        assert result.tier == ResolutionTier.LEGACY
        assert result.path == legacy_path
        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) == 1
        assert "Legacy asset resolved" in str(deprecation_warnings[0].message)


# ---------------------------------------------------------------------------
# C-001 -- fail-closed on malformed / unresolvable URNs
# ---------------------------------------------------------------------------


class TestFailClosed:
    """Malformed or unresolvable URNs raise TemplateURNError; never inferred."""

    @pytest.mark.parametrize("urn", ["", "   "], ids=["empty", "whitespace"])
    def test_blank_urn_fails_closed(self, tmp_path: Path, urn: str) -> None:
        with pytest.raises(TemplateURNError, match="absent or blank"):
            resolve_template_by_urn(urn, tmp_path)

    @pytest.mark.parametrize(
        "urn",
        [
            "software-dev/spec-template.md",
            "urn:template:software-dev/spec-template.md",
            "artifact:software-dev/spec-template.md",
        ],
        ids=["no-prefix", "wrong-prefix-order", "wrong-kind-prefix"],
    )
    def test_missing_template_prefix_fails_closed(
        self, tmp_path: Path, urn: str
    ) -> None:
        with pytest.raises(TemplateURNError, match="template:"):
            resolve_template_by_urn(urn, tmp_path)

    def test_unqualified_urn_never_defaults_mission_to_software_dev(
        self, tmp_path: Path
    ) -> None:
        """C-001 / no #2660 inference: a URN with no ``<mission>/`` segment
        must fail closed rather than silently resolving under
        ``mission="software-dev"``.
        """
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        # If mission inference were (wrongly) reintroduced, this bare name
        # would resolve against software-dev's real package-default file.
        with pytest.raises(TemplateURNError):
            resolve_template_by_urn("template:spec-template.md", project)

    def test_urn_with_blank_mission_segment_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(TemplateURNError):
            resolve_template_by_urn("template:/spec-template.md", tmp_path)

    def test_urn_with_blank_name_segment_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(TemplateURNError):
            resolve_template_by_urn("template:software-dev/", tmp_path)

    def test_unresolvable_urn_fails_closed(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        empty_home = tmp_path / "empty_home"

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=empty_home,
            ),
            patch("doctrine.resolver.get_kittify_home", return_value=empty_home),
            pytest.raises(TemplateURNError, match="could not be resolved"),
        ):
            resolve_template_by_urn(
                "template:software-dev/does-not-exist-anywhere.md", project
            )
