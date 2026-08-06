"""WP03 row 9: ``decisions/service._resolve_mission_id`` routed fail-closed.

Census row 9 routes ``specify_cli.decisions.service._resolve_mission_id`` onto
:func:`specify_cli.core.paths.load_meta_fail_closed`.

Two couplings are pinned here.

**Coupling 3** — the ``if meta is None:`` arm must carry the MISSING-FILE cause.
Every arm in ``_resolve_mission_id`` raises ``DecisionError(MISSION_NOT_FOUND)``,
so a type-only assertion is green at baseline, green after routing, and green
under arm-deletion.  The assertions below are on the MESSAGE.

**Coupling 4 / C-002** — ``MissionMetaReadError`` is a ``RuntimeError``, not a
``ValueError``.  The moment the call is routed, the pre-existing
``except ValueError`` stops catching corruption and the wrapper leaks where
``DecisionError`` is contracted (``SC-003``).  The malformed-file guard is the
executable form of that coupling: it is RED on a tree where the site is routed
but the handler is not yet widened.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from specify_cli.decisions.models import DecisionErrorCode, DecisionOpenResponse, OriginFlow
from specify_cli.decisions.service import DecisionError, open_decision

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_MISSION_SLUG = "test-mission"
_MISSION_ID = "01KTEST_MISSION_ID_000009"

_SERVICE_SOURCE = Path(__file__).resolve().parents[3] / "src" / "specify_cli" / "decisions" / "service.py"


def _mission_dir(repo_root: Path) -> Path:
    return repo_root / "kitty-specs" / _MISSION_SLUG


def _setup_mission(repo_root: Path, *, meta_text: str | None) -> Path:
    """Materialize the mission directory; ``meta_text=None`` leaves meta.json absent."""
    mission_dir = _mission_dir(repo_root)
    mission_dir.mkdir(parents=True, exist_ok=True)
    if meta_text is not None:
        (mission_dir / "meta.json").write_text(meta_text, encoding="utf-8")
    return mission_dir


def _open(repo_root: Path) -> DecisionOpenResponse:
    return open_decision(
        repo_root,
        _MISSION_SLUG,
        origin_flow=OriginFlow.CHARTER,
        step_id="step-1",
        input_key="team_size",
        actor="alice",
        question="How large is the team?",
    )


class TestRow09ServiceFailClosed:
    """Behavioural contract of the routed ``_resolve_mission_id`` site."""

    def test_absent_meta_json_names_the_missing_file(self, tmp_path: Path) -> None:
        """The ``if meta is None:`` arm reports the MISSING-FILE cause.

        Asserted on the message, not the type.  ``DecisionError`` with code
        ``MISSION_NOT_FOUND`` is also what the field-absent path raises
        ("has no mission_id field"), so a type-only guard is satisfied by the
        wrong cause and stays green when this arm is deleted.
        """
        _setup_mission(tmp_path, meta_text=None)

        with pytest.raises(DecisionError, match="meta.json not found for mission"):
            _open(tmp_path)

    def test_absent_meta_json_is_not_reported_as_a_missing_field(self, tmp_path: Path) -> None:
        """Absence must NOT be reported as the field-absent cause."""
        _setup_mission(tmp_path, meta_text=None)

        with pytest.raises(DecisionError) as excinfo:
            _open(tmp_path)

        assert "has no mission_id field" not in str(excinfo.value), (
            "absent meta.json was reported with the field-absent cause; the "
            "if-None arm is missing or has been bypassed"
        )
        assert excinfo.value.code is DecisionErrorCode.MISSION_NOT_FOUND

    def test_malformed_meta_json_stays_a_decision_error(self, tmp_path: Path) -> None:
        """C-002 / coupling 4: the handler must catch the ROUTED exception type.

        ``load_meta_fail_closed`` raises ``MissionMetaReadError`` (a
        ``RuntimeError``) where ``load_meta`` raised ``ValueError``.  An
        un-widened ``except ValueError`` lets it leak, and this test is the red
        that catches it.
        """
        _setup_mission(tmp_path, meta_text="{ not valid json")

        with pytest.raises(DecisionError, match="Failed to read meta.json for mission"):
            _open(tmp_path)

    def test_valid_meta_json_resolves_cleanly(self, tmp_path: Path) -> None:
        """SC-003 negative control: a valid read must not fail closed."""
        _setup_mission(
            tmp_path,
            meta_text=json.dumps({"mission_id": _MISSION_ID, "mission_slug": _MISSION_SLUG}),
        )

        response = _open(tmp_path)

        assert response.mission_id == _MISSION_ID


class TestRow09HandlerShape:
    """C-002: catch ``MissionMetaReadError`` by name, never ``except Exception``."""

    def test_resolve_mission_id_handler_names_mission_meta_read_error(self) -> None:
        tree = ast.parse(_SERVICE_SOURCE.read_text(encoding="utf-8"))
        target = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_resolve_mission_id"
        )

        caught: list[str] = []
        for handler in (h for n in ast.walk(target) if isinstance(n, ast.Try) for h in n.handlers):
            assert handler.type is not None, "bare except in _resolve_mission_id"
            nodes = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
            caught.extend(n.id for n in nodes if isinstance(n, ast.Name))

        assert "MissionMetaReadError" in caught, (
            "specify_cli.decisions.service._resolve_mission_id must catch "
            f"MissionMetaReadError by name; caught {caught}"
        )
        assert "Exception" not in caught, "except Exception is banned by C-002"
        assert "BaseException" not in caught, "except BaseException is banned by C-002"


class TestRow09RoutedCallBudget:
    """Structural budget: exactly one routed call, matched on the exact callee."""

    def test_resolve_mission_id_body_has_one_fail_closed_call_and_no_load_meta(self) -> None:
        """``_resolve_mission_id``'s own body: 1 ``load_meta_fail_closed``, 0 ``load_meta``.

        Scoped to the function AND named to the module: ``_resolve_mission_id``
        is defined in four modules on this tree, two of them this mission's own
        sites with opposite arms.  Matched on the exact callee name, never as a
        substring — ``load_meta_fail_closed(`` contains ``load_meta(``.
        """
        tree = ast.parse(_SERVICE_SOURCE.read_text(encoding="utf-8"))
        target = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_resolve_mission_id"
        )

        callee_names = [
            node.func.id
            for node in ast.walk(target)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]

        assert callee_names.count("load_meta_fail_closed") == 1, (
            "specify_cli.decisions.service._resolve_mission_id (NOT the "
            "_resolve_mission_id in mission_runtime.resolution, context.resolver "
            "or elsewhere) must contain exactly one load_meta_fail_closed() call; "
            f"found {callee_names.count('load_meta_fail_closed')}"
        )
        assert callee_names.count("load_meta") == 0, (
            "specify_cli.decisions.service._resolve_mission_id must contain zero "
            f"load_meta() calls after routing; found {callee_names.count('load_meta')}"
        )
