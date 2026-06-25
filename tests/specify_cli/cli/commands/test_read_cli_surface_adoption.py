"""WP06 / T022 / T024 — per-CLI bare-slug coord e2e proof (SC-002, FR-004).

These tests are the CLI-level end-to-end proof that the equivalence matrix
(01KVGCE8) CANNOT give: the matrix exercises resolver *primitives* in isolation;
only a CLI-level test proves that each read-CLI routes through the seam and
reaches the COORDINATION WORKTREE when one is materialised on disk.

**Fixture design (NFR-005)**

Real 26-char Crockford ULID for ``mission_id``.  The on-disk layout is:

::

    <repo_root>/
      kitty-specs/<slug>/            ← PRIMARY checkout dir (bare slug, no mid8 suffix)
        meta.json                    ← declares mission_id + mid8 + coordination_branch
        tasks/WP01-work.md
      .worktrees/<slug>-<mid8>-coord/
        kitty-specs/<slug>-<mid8>/   ← COORD mission dir (T022 resolver MUST return this)
          status.events.jsonl

The bare slug `<slug>` (no mid8 suffix) is what the operator types.
``resolve_handle_to_read_path`` probes the PRIMARY meta to derive ``mid8``,
then selects the COORD dir because the coord worktree exists on disk.

**Anti-born-green guarantee**

On the pre-adoption tree the CLI composed ``kitty-specs/<slug>`` (primary)
WITHOUT probing the primary meta for a mid8 — the coord worktree was never
consulted.  Every assertion below names the COORD dir; it would FAIL on the
pre-adoption tree that returned the primary dir.

**T022** — Covered per CLI:
- ``agent tasks status`` — mandatory headline proof (tasks.py:4047 flagship)
- ``agent context`` — via ``_find_feature_directory``
- ``agent mission`` — via ``_find_feature_directory``
- ``decision verify`` — via ``resolve_handle_to_read_path``
- ``acceptance._status_read_feature_dir`` — via the canonical helper

**T024** — Traversal rejection via ``assert_safe_path_segment``.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app as tasks_app
from tests.mocked_env import setup_mocked_env

pytestmark = [pytest.mark.fast]

runner = CliRunner()

# ---------------------------------------------------------------------------
# Realistic test constants (NFR-005 — no short fake slugs)
# ---------------------------------------------------------------------------
# Full 26-character Crockford base-32 ULID (production-shaped).
_FULL_ULID: str = "01KVJPEQ7M3K8N2QXR4VBZ9HCD"
# The 8-character mid8 disambiguator.
_MID8: str = _FULL_ULID[:8]          # "01KVJPEQ"
# The bare human slug (no mid8 suffix — this is what the operator types).
_BARE_SLUG: str = "e2e-coord-proof"
# The canonical ``<slug>-<mid8>`` directory name used for the coord worktree.
_MISSION_DIR: str = f"{_BARE_SLUG}-{_MID8}"
# The coordination branch name embedded in ``meta.json``.
_COORD_BRANCH: str = f"kitty/mission-{_MISSION_DIR}"
# Surface-distinguishing WP ids: the primary checkout carries
# ``_PRIMARY_ONLY_WP`` and the coord worktree carries ``_COORD_ONLY_WP``.
# Post-#2090, WP task files are PRIMARY artifacts while lane status remains
# STATUS-owned. ``tasks status`` must list the primary WP while reducing lane
# state from the coord event log.
_PRIMARY_ONLY_WP: str = "WP01"
_COORD_ONLY_WP: str = "WP02"


# ---------------------------------------------------------------------------
# Shared fixture builder
# ---------------------------------------------------------------------------

def _build_coord_fresh_mission(repo_root: Path) -> Path:
    """Materialise a coord-fresh mission on disk; return the COORD mission dir.

    Primary dir uses the BARE slug (no mid8 suffix) — matching the scenario where
    the operator types a bare human slug. The primary meta carries the full
    identity (mission_id + mid8 + coordination_branch) so ``resolve_handle_to_read_path``
    can derive mid8 from ``meta.json`` and then select the coord worktree.

    Layout:
      <repo_root>/
        kitty-specs/<slug>/                        ← primary (bare slug, EXISTS)
          meta.json                                 ← carries mission_id + mid8 + coord branch
          tasks/WP01-work.md
        .worktrees/<slug>-<mid8>-coord/           ← coord worktree root (EXISTS)
          kitty-specs/<slug>-<mid8>/              ← coord mission dir ← RESOLVER MUST RETURN THIS
            status.events.jsonl
    """
    # Primary checkout: bare slug name, full identity in meta.json.
    primary_dir = repo_root / "kitty-specs" / _BARE_SLUG
    primary_dir.mkdir(parents=True)
    meta = {
        "mission_id": _FULL_ULID,
        "mission_slug": _BARE_SLUG,
        "mid8": _MID8,
        "coordination_branch": _COORD_BRANCH,
        "mission_type": "software-dev",
    }
    (primary_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    tasks_dir = primary_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / f"{_PRIMARY_ONLY_WP}-work.md").write_text(
        textwrap.dedent(f"""\
            ---
            work_package_id: {_PRIMARY_ONLY_WP}
            title: Primary-only work package
            execution_mode: code_change
            ---
            # {_PRIMARY_ONLY_WP}
        """),
        encoding="utf-8",
    )

    # Coordination worktree: STATUS-authoritative read surface.
    coord_root = repo_root / ".worktrees" / f"{_MISSION_DIR}-coord"
    coord_mission_dir = coord_root / "kitty-specs" / _MISSION_DIR
    coord_mission_dir.mkdir(parents=True)
    coord_tasks_dir = coord_mission_dir / "tasks"
    coord_tasks_dir.mkdir()
    (coord_tasks_dir / f"{_COORD_ONLY_WP}-coord.md").write_text(
        textwrap.dedent(f"""\
            ---
            work_package_id: {_COORD_ONLY_WP}
            title: Coord-only work package
            execution_mode: code_change
            ---
            # {_COORD_ONLY_WP}
        """),
        encoding="utf-8",
    )
    status_event = {
        "event_id": "01KVJPEQ7M3K8N2QXR4VBZ9HCE",
        "mission_slug": _BARE_SLUG,
        "mission_id": _FULL_ULID,
        "wp_id": _PRIMARY_ONLY_WP,
        "from_lane": "genesis",
        "to_lane": "in_progress",
        "at": "2026-06-25T00:00:00+00:00",
        "actor": "test",
        "force": True,
        "execution_mode": "code_change",
    }
    (coord_mission_dir / "status.events.jsonl").write_text(
        json.dumps(status_event) + "\n",
        encoding="utf-8",
    )

    return coord_mission_dir


# ---------------------------------------------------------------------------
# T022a — agent tasks status (MANDATORY headline proof)
# ---------------------------------------------------------------------------

class TestAgentTasksStatusCoordResolution:
    """T022a: ``agent tasks status --mission <bare-slug>`` resolves the coord dir.

    ``agent tasks status`` is the spec's primary-scenario exemplar (SC-002) AND
    the tasks.py:4047 F7 flagship whose adoption is otherwise CLI-unproven (the
    equivalence matrix tests the primitive, not the CLI invocation).

    Spy strategy: patch ``specify_cli.missions._read_path_resolver.resolve_handle_to_read_path``
    (the module-level function that the local import inside ``status()`` binds to) — this
    still executes the REAL resolver but also captures its return value, so we confirm:
    (a) the CLI calls the seam (not a stub), and (b) the seam returns the coord dir.

    Anti-born-green: on the pre-adoption tree, ``status`` used the blind
    ``resolve_mid8(slug, mission_id=None)`` path (always returning ``""``), so
    the bare-slug read landed on the PRIMARY dir without consulting the coord
    worktree.  The assertion names the COORD dir and would FAIL on the pre-adoption tree.
    """

    def test_bare_slug_resolves_coord_dir(self, tmp_path: Path) -> None:
        """T022a (SC-002): bare slug via tasks status → coord worktree dir, not primary."""
        coord_dir = _build_coord_fresh_mission(tmp_path)
        primary_dir = tmp_path / "kitty-specs" / _BARE_SLUG

        captured: dict[str, Path] = {}

        # Import the REAL seam once; spy wraps it without replacing the logic.
        from specify_cli.missions._read_path_resolver import (
            resolve_handle_to_read_path as _real_seam,
        )

        def _spy(repo_root: Path, handle: str, **kw: object) -> Path:
            result: Path = _real_seam(repo_root, handle, **kw)
            captured["resolved"] = result
            return result

        workspace = SimpleNamespace(
            execution_mode="code_change", resolution_kind="lane_workspace"
        )
        with (
            setup_mocked_env(
                tmp_path,
                mission_slug=_BARE_SLUG,
                workspace_resolution=workspace,
            ),
            patch(
                "specify_cli.missions._read_path_resolver.resolve_handle_to_read_path",
                side_effect=_spy,
            ),
        ):
            result = runner.invoke(
                tasks_app,
                ["status", "--mission", _BARE_SLUG, "--json"],
            )

        # The CLI must have called the seam and received the coord dir.
        assert "resolved" in captured, (
            "resolve_handle_to_read_path was never called — "
            "the CLI did not route through the seam"
        )
        resolved_dir = captured["resolved"]

        # Core coord assertion: the seam returned the COORD dir, not the primary.
        # This assertion would FAIL on the pre-adoption tree (which returned primary).
        assert resolved_dir == coord_dir, (
            f"Bare slug resolved primary instead of coord worktree dir.\n"
            f"  Expected (coord):   {coord_dir}\n"
            f"  Got:                {resolved_dir}\n"
            f"  Primary (must NOT): {primary_dir}"
        )
        assert resolved_dir != primary_dir, (
            "Resolved dir equals the PRIMARY checkout — coord was not selected"
        )

        # Observable-behavior assertions. Proving the seam is CALLED is not
        # enough — ``status()`` must consume coord STATUS while reading PRIMARY
        # tasks.
        assert result.exit_code == 0, (
            "agent tasks status did NOT exit 0 — status() did not consume the "
            f"coord feature_dir.\n  stdout: {result.stdout}\n"
            f"  exc: {result.exception!r}"
        )
        # (b) PRIMARY task signal + coord STATUS signal.
        assert _PRIMARY_ONLY_WP in result.stdout, (
            f"Primary work package {_PRIMARY_ONLY_WP!r} absent from status output.\n"
            f"  stdout: {result.stdout}"
        )
        assert _COORD_ONLY_WP not in result.stdout, (
            f"Coord-only work package {_COORD_ONLY_WP!r} present in status output — "
            "status() consumed tasks from the STATUS surface.\n"
            f"  stdout: {result.stdout}"
        )
        assert "in_progress" in result.stdout, (
            "Coord event-log lane was not reflected in status output.\n"
            f"  stdout: {result.stdout}"
        )

    def test_full_handle_resolves_same_coord_dir(self, tmp_path: Path) -> None:
        """T022a no-regression: ``<slug>-<mid8>`` (full handle) also resolves coord dir."""
        coord_dir = _build_coord_fresh_mission(tmp_path)

        captured: dict[str, Path] = {}

        from specify_cli.missions._read_path_resolver import (
            resolve_handle_to_read_path as _real_seam,
        )

        def _spy(repo_root: Path, handle: str, **kw: object) -> Path:
            result: Path = _real_seam(repo_root, handle, **kw)
            captured["resolved"] = result
            return result

        workspace = SimpleNamespace(
            execution_mode="code_change", resolution_kind="lane_workspace"
        )
        with (
            setup_mocked_env(
                tmp_path,
                mission_slug=_MISSION_DIR,
                workspace_resolution=workspace,
            ),
            patch(
                "specify_cli.missions._read_path_resolver.resolve_handle_to_read_path",
                side_effect=_spy,
            ),
        ):
            runner.invoke(
                tasks_app,
                ["status", "--mission", _MISSION_DIR],
            )

        assert "resolved" in captured, "resolve_handle_to_read_path not called"
        assert captured["resolved"] == coord_dir, (
            f"Full handle resolved {captured['resolved']!r} instead of coord dir {coord_dir!r}"
        )


# ---------------------------------------------------------------------------
# T022b — agent context (via _find_feature_directory)
# ---------------------------------------------------------------------------

class TestAgentContextCoordResolution:
    """T022b: ``agent context._find_feature_directory`` resolves the coord dir.

    Anti-born-green: the pre-adoption tree's ``_find_feature_directory`` in
    context.py performed a raw ``KITTY_SPECS_DIR / slug`` join without probing
    the primary meta for a mid8, so a bare slug always landed in the primary
    checkout.  The assertion below names the coord dir specifically.
    """

    def test_bare_slug_resolves_coord_dir(self, tmp_path: Path) -> None:
        """T022b (SC-002): bare slug via context._find_feature_directory → coord dir."""
        from specify_cli.cli.commands.agent.context import _find_feature_directory

        coord_dir = _build_coord_fresh_mission(tmp_path)
        primary_dir = tmp_path / "kitty-specs" / _BARE_SLUG

        resolved = _find_feature_directory(
            tmp_path, tmp_path, explicit_mission=_BARE_SLUG
        )

        # Must be the coord dir, not the primary.
        assert resolved == coord_dir, (
            f"Bare slug resolved primary instead of coord dir.\n"
            f"  Expected (coord):   {coord_dir}\n"
            f"  Got:                {resolved}\n"
            f"  Primary (must NOT): {primary_dir}"
        )
        assert resolved != primary_dir

    def test_full_handle_resolves_same_coord_dir(self, tmp_path: Path) -> None:
        """T022b no-regression: full ``<slug>-<mid8>`` handle resolves coord dir."""
        from specify_cli.cli.commands.agent.context import _find_feature_directory

        coord_dir = _build_coord_fresh_mission(tmp_path)

        resolved = _find_feature_directory(
            tmp_path, tmp_path, explicit_mission=_MISSION_DIR
        )

        assert resolved == coord_dir, (
            f"Full handle resolved {resolved!r} instead of coord dir {coord_dir!r}"
        )


# ---------------------------------------------------------------------------
# T022c — agent mission (via _find_feature_directory)
# ---------------------------------------------------------------------------

class TestAgentMissionCoordResolution:
    """T022c: ``agent mission._find_feature_directory`` resolves the coord dir.

    The mission.py ``_find_feature_directory`` is a parallel of context.py's
    function (WP02/WP03 migrated both).  This test drives it independently.
    """

    def test_bare_slug_resolves_coord_dir(self, tmp_path: Path) -> None:
        """T022c (SC-002): bare slug via mission._find_feature_directory → coord dir."""
        from specify_cli.cli.commands.agent.mission import _find_feature_directory

        coord_dir = _build_coord_fresh_mission(tmp_path)
        primary_dir = tmp_path / "kitty-specs" / _BARE_SLUG

        resolved = _find_feature_directory(
            tmp_path, tmp_path, explicit_feature=_BARE_SLUG
        )

        assert resolved == coord_dir, (
            f"Bare slug resolved primary instead of coord dir.\n"
            f"  Expected (coord):   {coord_dir}\n"
            f"  Got:                {resolved}\n"
            f"  Primary (must NOT): {primary_dir}"
        )
        assert resolved != primary_dir

    def test_full_handle_resolves_same_coord_dir(self, tmp_path: Path) -> None:
        """T022c no-regression: full ``<slug>-<mid8>`` handle resolves coord dir."""
        from specify_cli.cli.commands.agent.mission import _find_feature_directory

        coord_dir = _build_coord_fresh_mission(tmp_path)

        resolved = _find_feature_directory(
            tmp_path, tmp_path, explicit_feature=_MISSION_DIR
        )

        assert resolved == coord_dir, (
            f"Full handle resolved {resolved!r} instead of coord dir {coord_dir!r}"
        )


# ---------------------------------------------------------------------------
# T022d — decision verify (via resolve_handle_to_read_path directly)
# ---------------------------------------------------------------------------

class TestDecisionCoordResolution:
    """T022d: ``decision.cmd_verify`` routes through the seam to the coord dir.

    ``decision.py`` calls ``resolve_handle_to_read_path`` directly (WP02/D-6).
    We test the seam function itself (the same one ``cmd_verify`` calls) with
    the coord-fresh fixture, proving the code path resolves correctly.

    Anti-born-green: the pre-adoption D-6 bootstrap did a raw ``KITTY_SPECS_DIR /
    slug`` join before probing meta — a bare slug always resolved the primary.
    """

    def test_bare_slug_resolves_coord_dir(self, tmp_path: Path) -> None:
        """T022d (SC-002): resolve_handle_to_read_path with bare slug → coord dir."""
        from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path

        coord_dir = _build_coord_fresh_mission(tmp_path)
        primary_dir = tmp_path / "kitty-specs" / _BARE_SLUG

        resolved = resolve_handle_to_read_path(tmp_path, _BARE_SLUG)

        assert resolved == coord_dir, (
            f"Bare slug resolved primary instead of coord dir.\n"
            f"  Expected (coord):   {coord_dir}\n"
            f"  Got:                {resolved}\n"
            f"  Primary (must NOT): {primary_dir}"
        )
        assert resolved != primary_dir

    def test_full_handle_resolves_same_coord_dir(self, tmp_path: Path) -> None:
        """T022d no-regression: full handle resolves the same coord dir."""
        from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path

        coord_dir = _build_coord_fresh_mission(tmp_path)

        resolved = resolve_handle_to_read_path(tmp_path, _MISSION_DIR)

        assert resolved == coord_dir, (
            f"Full handle resolved {resolved!r} instead of coord dir {coord_dir!r}"
        )


# ---------------------------------------------------------------------------
# T022e — acceptance._status_read_feature_dir (coord resolution)
# ---------------------------------------------------------------------------

class TestAcceptanceCoordResolution:
    """T022e: ``acceptance._status_read_feature_dir`` resolves the coord dir.

    ``_status_read_feature_dir`` derives mid8 via ``resolve_declared_mid8``
    (WP03/T013 migration) then calls ``resolve_mission_read_path``.  This test
    proves that a coord-fresh mission returns the coord dir rather than the
    primary anchor.

    Anti-born-green: the pre-adoption body used a bespoke
    ``meta.mid8`` → ``mid8_from_slug`` selection that omitted the tier-2
    ``resolve_mid8(mission_id)`` step.  For a bare slug whose meta declares
    ``mission_id`` the correct coord resolution would still work (the mid8 field
    is explicit in meta), but this test additionally confirms that the WP03
    migration's tier-2 improvement does not break coord resolution when the meta
    carries an explicit ``mid8`` field (tier-1 win path).

    The function takes ``(repo_root, feature, feature_dir)`` where ``feature``
    is the slug and ``feature_dir`` is the primary anchor.  The acceptance-specific
    fallback ``status_dir if exists else feature_dir`` means the coord dir is
    returned when it exists.
    """

    def test_bare_slug_resolves_coord_dir(self, tmp_path: Path) -> None:
        """T022e (SC-002): bare slug via acceptance._status_read_feature_dir → coord dir."""
        from specify_cli.acceptance import _status_read_feature_dir

        coord_dir = _build_coord_fresh_mission(tmp_path)
        primary_dir = tmp_path / "kitty-specs" / _BARE_SLUG

        # _status_read_feature_dir reads meta from feature_dir (primary_dir),
        # derives mid8 from the meta, calls resolve_mission_read_path, and returns
        # the coord dir when it exists on disk.
        resolved = _status_read_feature_dir(tmp_path, _BARE_SLUG, primary_dir)

        # Must equal the coord dir, not the primary.
        assert resolved == coord_dir, (
            f"Bare slug resolved primary instead of coord dir.\n"
            f"  Expected (coord):   {coord_dir}\n"
            f"  Got:                {resolved}\n"
            f"  Primary (must NOT): {primary_dir}"
        )
        assert resolved != primary_dir

    def test_full_handle_resolves_same_coord_dir(self, tmp_path: Path) -> None:
        """T022e no-regression: full handle resolves the same coord dir."""
        from specify_cli.acceptance import _status_read_feature_dir

        coord_dir = _build_coord_fresh_mission(tmp_path)
        primary_dir = tmp_path / "kitty-specs" / _BARE_SLUG

        resolved = _status_read_feature_dir(tmp_path, _MISSION_DIR, primary_dir)

        assert resolved == coord_dir, (
            f"Full handle resolved {resolved!r} instead of coord dir {coord_dir!r}"
        )


# ---------------------------------------------------------------------------
# T024 — traversal rejection (FR-004, NFR-002)
# ---------------------------------------------------------------------------

class TestTraversalRejection:
    """T024: traversal handles are rejected before any path composition.

    ``assert_safe_path_segment`` fires FIRST inside ``resolve_handle_to_read_path``
    (step 1 of the seam — FR-004 / NFR-002).  A traversal payload must never
    reach a ``KITTY_SPECS_DIR`` join.
    """

    @pytest.mark.parametrize("handle", ["../etc", "a/b", "../sneaky"])
    def test_traversal_handle_raises_value_error(
        self, tmp_path: Path, handle: str
    ) -> None:
        """A ``/`` or leading ``..`` in the handle raises ValueError (no path composed)."""
        from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path

        with pytest.raises(ValueError, match="safe path segment"):
            resolve_handle_to_read_path(tmp_path, handle)

    @pytest.mark.parametrize("handle", ["../etc", "a/b"])
    def test_context_find_feature_directory_rejects_traversal(
        self, tmp_path: Path, handle: str
    ) -> None:
        """``agent context._find_feature_directory`` rejects traversal payloads."""
        from mission_runtime import ActionContextError
        from specify_cli.cli.commands.agent.context import _find_feature_directory

        # Traversal in the input handle must surface as an ActionContextError
        # (the function translates ValueError from the seam into a structured error).
        with pytest.raises((ValueError, ActionContextError)):
            _find_feature_directory(tmp_path, tmp_path, explicit_mission=handle)

    @pytest.mark.parametrize("handle", ["../etc", "a/b"])
    def test_mission_find_feature_directory_rejects_traversal(
        self, tmp_path: Path, handle: str
    ) -> None:
        """``agent mission._find_feature_directory`` rejects traversal payloads."""
        from mission_runtime import ActionContextError
        from specify_cli.cli.commands.agent.mission import _find_feature_directory

        with pytest.raises((ValueError, ActionContextError)):
            _find_feature_directory(tmp_path, tmp_path, explicit_feature=handle)
