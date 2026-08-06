"""WP03 row 8: ``context/resolver._read_meta_json`` routed fail-closed.

Census row 8 routes ``specify_cli.context.resolver._read_meta_json`` onto
:func:`specify_cli.core.paths.load_meta_fail_closed`.  That seam returns ``None``
for an absent ``meta.json`` and raises
:class:`specify_cli.core.paths.MissionMetaReadError` for a corrupt one, so the
site carries an explicit ``if result is None:`` arm raising
:class:`~specify_cli.context.errors.MissingIdentityError`.

The absent-file message pin lives in ``test_resolver.py`` (symbol
``TestResolveContextErrors.test_missing_meta_json_raises`` — class at
``tests/specify_cli/context/test_resolver.py:215``, method at ``:251``) and is
green at baseline. This module adds the malformed-file guard, the valid-file
negative control (``SC-003``) and the structural call-count assertion that closes
the routed budget (a substring check on source text is green under a two-call
fold).

Citation correction (WP03 review fold, applied by WP08): this docstring named the
holding class ``TestResolveContext``. That class *does* exist
(``test_resolver.py:125``) — but this method is not in it: ``test_missing_meta_json_raises``
is at ``:251``, inside ``TestResolveContextErrors`` (``:215``). The original
justification ("no such class exists") was itself wrong, produced by a probe window
of ``:215``-``:255`` that structurally could not see ``:125``.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from specify_cli.context.errors import MissingIdentityError
from specify_cli.context.resolver import _read_meta_json, resolve_context
from specify_cli.core.paths import MissionMetaReadError
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_MISSION_SLUG = "057-test-mission"
_MISSION_ID = "01HVXYZTESTMISSION000000000"
_WP_CODE = "WP01"

_RESOLVER_SOURCE = Path(__file__).resolve().parents[3] / "src" / "specify_cli" / "context" / "resolver.py"


def _setup_mission(tmp_path: Path) -> Path:
    """Materialize a minimal project whose mission resolves cleanly."""
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir(parents=True)
    (kittify_dir / "config.yaml").write_text(
        "vcs:\n  type: git\nproject:\n  uuid: test-project-uuid-1234\n"
        "  slug: test-project\n  node_id: abcdef012345\n",
        encoding="utf-8",
    )

    mission_dir = tmp_path / "kitty-specs" / _MISSION_SLUG
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mission_slug": _MISSION_SLUG,
                "friendly_name": "Test Mission",
                "mission": "software-dev",
                "target_branch": "main",
                "created_at": "2026-03-27T16:00:00+00:00",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / f"{_WP_CODE}-test-wp.md").write_text(
        f"---\nwork_package_id: {_WP_CODE}\ntitle: Test WP\nlane: planned\n"
        f"dependencies: []\nexecution_mode: code_change\nowned_files:\n"
        f'- "src/specify_cli/context/**"\n---\n\n# Work Package: {_WP_CODE}\n',
        encoding="utf-8",
    )

    write_lanes_json(
        mission_dir,
        LanesManifest(
            version=1,
            mission_slug=_MISSION_SLUG,
            mission_id=_MISSION_ID,
            mission_branch=f"kitty/mission-{_MISSION_SLUG}",
            target_branch="main",
            lanes=[
                ExecutionLane(
                    lane_id="lane-a",
                    wp_ids=(_WP_CODE,),
                    write_scope=("src/**",),
                    predicted_surfaces=("context",),
                    depends_on_lanes=(),
                    parallel_group=0,
                )
            ],
            computed_at="2026-04-04T10:00:00Z",
            computed_from="test",
        ),
    )
    return tmp_path


class TestRow08ResolverFailClosed:
    """Behavioural contract of the routed ``_read_meta_json`` site."""

    def test_malformed_meta_json_raises_mission_meta_read_error(self, tmp_path: Path) -> None:
        """A corrupt meta.json fails closed at row 8's own site.

        Baseline raised a bare ``ValueError`` from ``mission_metadata.load_meta``;
        after routing the seam wraps it into ``MissionMetaReadError``.

        Asserted against ``_read_meta_json`` directly rather than through
        ``resolve_context``.  The public entry point structurally CANNOT reach
        row 8 with a corrupt file: ``resolve_context`` resolves the mission
        directory first, and that path already routes through
        ``_read_path_resolver.read_primary_meta`` (WP02's census row), which
        raises ``MissionMetaReadError`` at ``core/paths.py:678`` before
        ``_read_meta_json`` is ever entered.  A ``resolve_context``-level
        malformed guard is therefore green at baseline AND after routing — it
        pins WP02's site, not this one.  The ABSENT-file path does reach row 8
        (``resolver.py`` ``_read_meta_json``), which is why the message pin in
        ``test_resolver.py`` remains row 8's real behavioural assertion.
        """
        repo = _setup_mission(tmp_path)
        mission_dir = repo / "kitty-specs" / _MISSION_SLUG
        (mission_dir / "meta.json").write_text("{ not valid json", encoding="utf-8")

        with pytest.raises(MissionMetaReadError, match="meta.json"):
            _read_meta_json(mission_dir, repo)

    def test_absent_meta_json_raises_missing_identity_with_message(self, tmp_path: Path) -> None:
        """The ``if result is None:`` arm carries the missing-file message.

        This is the arm T017's mutation probe deletes.  The assertion is on the
        MESSAGE, not the type: ``MissingIdentityError`` is also what the
        field-absent path raises, so a type-only guard proves nothing.
        """
        repo = _setup_mission(tmp_path)
        meta_path = repo / "kitty-specs" / _MISSION_SLUG / "meta.json"
        meta_path.unlink()

        with pytest.raises(MissingIdentityError, match="meta.json not found"):
            resolve_context(_WP_CODE, _MISSION_SLUG, "claude", repo)

    def test_valid_meta_json_resolves_cleanly(self, tmp_path: Path) -> None:
        """SC-003 negative control: fail-closed must not fail on valid input."""
        repo = _setup_mission(tmp_path)

        context = resolve_context(_WP_CODE, _MISSION_SLUG, "claude", repo)

        assert context.mission_id == _MISSION_ID
        assert context.target_branch == "main"


class TestRow08RoutedCallBudget:
    """Structural budget: exactly one routed call, matched on the exact callee."""

    def test_read_meta_json_body_has_one_fail_closed_call_and_no_load_meta(self) -> None:
        """``_read_meta_json``'s own body: 1 ``load_meta_fail_closed``, 0 ``load_meta``.

        Matched on the exact callee name, never as a substring —
        ``load_meta_fail_closed(`` contains ``load_meta(``, so a substring check
        is green under a fold that collapses two routed calls into one.
        """
        tree = ast.parse(_RESOLVER_SOURCE.read_text(encoding="utf-8"))
        target = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_read_meta_json"
        )

        callee_names = [
            node.func.id
            for node in ast.walk(target)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]

        assert callee_names.count("load_meta_fail_closed") == 1, (
            "specify_cli.context.resolver._read_meta_json must contain exactly one "
            f"load_meta_fail_closed() call; found {callee_names.count('load_meta_fail_closed')}"
        )
        assert callee_names.count("load_meta") == 0, (
            "specify_cli.context.resolver._read_meta_json must contain zero load_meta() "
            f"calls after routing; found {callee_names.count('load_meta')}"
        )
