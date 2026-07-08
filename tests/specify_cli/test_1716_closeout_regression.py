"""Regression lock for #2088 — closeout of epic #1716 (WP17).

#2088 fixed `validate_no_overlap` (src/specify_cli/ownership/validation.py) so it
no longer rejects two WPs that share `owned_files` when a dependency edge makes
them strictly sequential (same-lane, never concurrent). Before the fix, ANY two
WPs sharing owned_files were flagged, which made linearized refactor chains
(including this very mission's own 17-WP same-lane decomposition, e.g. WP17
depending on WP03/WP11/WP16) impossible to express without spurious overlap
errors.

This is a thin, standalone lock — deliberately independent of
`tests/specify_cli/ownership/test_validation.py` — so that a change which
accidentally deletes or narrows the dependency-aware exemption in that suite
does not silently drop coverage for the underwriting invariant #1716 relies on.

See: kitty-specs/read-surface-ssot-closeout-01KWZV91/tasks/WP17-closeout-1716-2088-2100.md (T048)
"""

from __future__ import annotations

import pytest

from specify_cli.ownership.models import ExecutionMode, OwnershipManifest
from specify_cli.ownership.validation import validate_no_overlap

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _manifest(owned: tuple[str, ...], surface: str) -> OwnershipManifest:
    return OwnershipManifest(
        execution_mode=ExecutionMode.CODE_CHANGE,
        owned_files=owned,
        authoritative_surface=surface,
    )


class TestOwnershipOverlapStaysDependencyAware:
    """Locks the #2088 fix: dependency/lane-aware overlap exemption must not regress."""

    def test_same_lane_sequential_wps_do_not_falsely_collide(self) -> None:
        """Two sequential WPs (dependency edge) sharing owned_files must NOT error.

        Mirrors this mission's own shape: a downstream WP (like WP17) that
        depends on upstream WPs sharing a surface within the same lane is a
        legitimate, in-order, non-concurrent overlap.
        """
        manifests = {
            "WPa": _manifest(owned=("src/specify_cli/status/**",), surface="src/specify_cli/status/"),
            "WPb": _manifest(owned=("src/specify_cli/status/**",), surface="src/specify_cli/status/"),
        }
        # WPb depends on WPa -> strictly sequential -> sharing owned_files is legitimate.
        errors = validate_no_overlap(manifests, dependencies={"WPb": ["WPa"]})

        assert errors == [], (
            "#2088 regression: dependency-ordered (same-lane sequential) WPs must "
            f"not be flagged as overlapping. Got: {errors}"
        )

    def test_concurrent_wps_with_no_dependency_path_still_collide(self) -> None:
        """The exemption must stay narrow: unrelated (parallel-lane) overlap still errors.

        Without this half of the lock, a broken fix could satisfy the first test
        by disabling the overlap check entirely rather than making it
        dependency-aware — this asserts the guard is still live for genuinely
        concurrent WPs.
        """
        manifests = {
            "WPa": _manifest(owned=("src/specify_cli/status/**",), surface="src/specify_cli/status/"),
            "WPb": _manifest(owned=("src/specify_cli/status/**",), surface="src/specify_cli/status/"),
        }
        # No dependency edge between WPa/WPb -> concurrent -> overlap must still fail.
        errors = validate_no_overlap(manifests, dependencies={})

        assert len(errors) == 1
        assert "WPa" in errors[0] and "WPb" in errors[0]
