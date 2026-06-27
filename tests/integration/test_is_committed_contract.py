"""Caller-contract regression pin for is_committed (FR-010, C-004, closes #2140).

Drives _planning_read_dir(artifact_type="spec") -> is_committed() through the
pre-existing caller chain rather than calling is_committed() directly.

The #2140 vector lives in the CALLER resolving coord vs primary — not in
is_committed's path-handling.  A bare is_committed(husk_path) call always
returns False when the file is absent, so it does not catch a caller regression.
These tests drive _planning_read_dir (the gate-read chokepoint) so the positive
assertion goes RED if the caller is re-routed to the coord husk.

Positive assertion: for a coord-topology mission with spec.md committed on
PRIMARY, the caller resolves PRIMARY → is_committed returns True.

Negative assertion (regression pin): monkeypatching _planning_read_dir to return
the coord husk (STATUS-only, no spec.md) → is_committed returns False.  This is
the exact failure mode the spec gate would expose as spec_committed=False.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.coord_topology_fixture import (
    CoordTopologyContext,
    _git,
    coord_topology_mission,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# Re-export the fixture so pytest discovers it for this module.
__all__ = ["coord_topology_mission"]

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_MINIMAL_SPEC = """\
# Spec: WP08 caller-contract pin

## Functional Requirements

| ID     | Description                               | Priority |
|--------|-------------------------------------------|----------|
| FR-001 | Stub requirement for caller-contract test. | MUST     |
"""


def _commit_spec_on_primary(ctx: CoordTopologyContext, content: str = _MINIMAL_SPEC) -> Path:
    """Write spec.md to the PRIMARY feature dir and commit it to the fixture repo."""
    spec_file = ctx.primary_feature_dir / "spec.md"
    spec_file.write_text(content, encoding="utf-8")
    _git(ctx.repo, "add", ".")
    _git(ctx.repo, "commit", "-m", "test: spec.md for WP08 caller-contract pin")
    return spec_file


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestIsCommittedCallerContract:
    """Caller-contract regression pin for is_committed (FR-010, C-004, #2140).

    Drives the pre-existing caller chain — _planning_read_dir -> is_committed —
    so the positive assertion goes RED if _planning_read_dir is re-routed to the
    coord husk (which carries no spec.md).
    """

    def test_positive_spec_on_primary_resolves_and_is_committed(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """Positive: caller's spec read resolves PRIMARY -> is_committed True.

        Drives _planning_read_dir(artifact_type="spec") -> is_committed() so the
        assertion goes RED if the caller re-routes SPEC reads to the coord husk
        (husk has no spec.md -> is_committed returns False).
        """
        ctx = coord_topology_mission
        _commit_spec_on_primary(ctx)

        from specify_cli.cli.commands.agent.mission_feature_resolution import _planning_read_dir
        from specify_cli.missions._substantive import is_committed

        spec_read_dir = _planning_read_dir(ctx.repo, ctx.slug, artifact_type="spec")
        assert spec_read_dir == ctx.primary_feature_dir, (
            f"Caller's spec read did not resolve to PRIMARY.\n"
            f"  Expected : {ctx.primary_feature_dir}\n"
            f"  Got      : {spec_read_dir}\n"
            "A coord-topology regression routes SPEC reads to the STATUS-only coord husk."
        )

        spec_file = spec_read_dir / "spec.md"
        assert is_committed(spec_file, ctx.repo) is True, (
            f"is_committed returned False for spec.md committed on PRIMARY.\n"
            f"  spec_file : {spec_file}\n"
            "The primary spec is committed but the commit check reports a miss."
        )

    def test_negative_coord_husk_path_is_not_committed_failure_mode(
        self,
        monkeypatch: pytest.MonkeyPatch,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """Failure-mode ILLUSTRATION (not the caller-vector pin — that is the positive test).

        Documents the downstream consequence of a #2140 / pre-#2106 regression: if the
        resolver reverted to coord, the spec read would land on the STATUS-only husk and
        is_committed would return False.  NOTE (reviewer-renata): the genuine caller-vector
        protection lives in ``test_positive_*`` above, which asserts the REAL unpatched
        ``_planning_read_dir(spec) == primary_feature_dir`` (goes RED on a coord re-point).
        This test is illustrative only — the monkeypatch returns a fixed husk dir, so it does
        not itself exercise the production resolver chain; it merely confirms a husk spec path
        (no committed spec.md) is correctly reported uncommitted.
        """
        from specify_cli.cli.commands.agent import mission_feature_resolution
        from specify_cli.missions._substantive import is_committed

        ctx = coord_topology_mission

        # Simulate regression: _planning_read_dir returns coord husk instead of primary.
        monkeypatch.setattr(
            mission_feature_resolution,
            "_planning_read_dir",
            lambda repo_root, slug, *, artifact_type: ctx.coord_feature_dir,
        )

        # Drive through the patched caller — this is what the caller chain would produce.
        spec_read_dir = mission_feature_resolution._planning_read_dir(
            ctx.repo, ctx.slug, artifact_type="spec"
        )
        assert spec_read_dir == ctx.coord_feature_dir, (
            "Monkeypatch did not take effect — test setup error."
        )

        # Coord husk carries no spec.md (STATUS-only surface): the HEAD of the coord
        # branch has no kitty-specs/ tree -> is_committed -> False.
        # This is the failure mode the spec gate would expose as spec_committed=False.
        husk_spec = spec_read_dir / "spec.md"
        assert is_committed(husk_spec, ctx.repo) is False, (
            "REGRESSION: is_committed returned True for a coord husk path.\n"
            f"  husk_spec : {husk_spec}\n"
            "Re-pointing _planning_read_dir to coord would cause the spec gate to\n"
            "block with spec_committed=False (reverting to the #2140 / pre-#2106 failure)."
        )
