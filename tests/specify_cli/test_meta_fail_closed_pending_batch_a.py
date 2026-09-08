"""ATDD: pending-batch-a fail-closed routing for meta.json corruption (FR-007 / #3162).

Exercises the REAL entry points of every site the ``pending-batch-a`` bucket
named — not ``load_meta``/``load_meta_fail_closed`` directly — so this test is
genuinely red if a routed call site regresses back to the unwrapped
``mission_metadata.load_meta`` call (a raw ``ValueError`` escaping to the
caller). Companion to ``test_meta_fail_closed_batch_a.py`` (which covered
WP08's owned subsystems); this file covers the remainder that neither WP08 nor
WP09 ever claimed, routed by the #3162 pass:

- ``mission_runtime/resolution.py`` probes (``_mid8_from_primary_meta``,
  ``_resolve_coordination_branch``, ``_resolve_mission_id``) — degrade sites:
  the typed :class:`MissionMetaReadError` is absorbed into each probe's
  historical sentinel answer, mirroring the
  ``lifecycle_phase._read_baseline_merge_commit`` carve-out.
- ``runtime/next`` (``planner._resolve_workflow_for_mission``,
  ``runtime_bridge_io._workflow_runtime_template``) — typed raise.
- ``bulk_edit/gate.py`` — typed raise.
- ``context/resolver.py`` (``_read_meta_json``) — typed raise.
- ``decisions/service.py`` (``_resolve_mission_id``) — typed read failure
  wrapped into the domain's ``DecisionError(MISSION_NOT_FOUND)``.
- ``missions/_read_path_resolver.py`` (``read_primary_meta``) — typed raise.
- ``missions/_resolve_planning_branch.py`` (``load_mission_target_branch``) —
  typed read failure wrapped into ``PlanningBranchResolutionFailed``.
- ``upgrade/feature_meta.py`` (``load_feature_meta``) — degrade to ``None``.

Both corrupt-meta and non-dict-meta cases are driven — the two shapes
``mission_metadata._parse_meta_text`` treats as "malformed" (json.JSONDecodeError
and non-object top level).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.paths import MissionMetaReadError

pytestmark = [pytest.mark.integration]

#: Corrupt: truncated, syntactically invalid JSON — genuinely unparseable.
_CORRUPT_META = '{"mission_id": "01JABCDEFGHJKMNPQRSTVWXYZ", '
#: Non-dict: parses cleanly but the top level is a list, not an object.
_NON_DICT_META = "[1, 2, 3]"

_SLUG = "probe-mission"

_CASES = [_CORRUPT_META, _NON_DICT_META]
_CASE_IDS = ["corrupt-json", "non-dict-json"]


def _seed(root: Path, meta_text: str) -> Path:
    """Create a minimal mission directory with a raw ``meta.json`` body."""
    mission_dir = root / "kitty-specs" / _SLUG
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(meta_text, encoding="utf-8")
    return mission_dir


# ---------------------------------------------------------------------------
# mission_runtime/resolution.py — the three divergent-wrapper probes degrade
# to their historical sentinels via the typed error (never a raw ValueError).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_mid8_from_primary_meta_degrades_to_empty(tmp_path: Path, meta_text: str) -> None:
    """Corrupt primary meta → ``""`` (the historical malformed→empty degrade)."""
    from mission_runtime.resolution import _mid8_from_primary_meta

    _seed(tmp_path, meta_text)
    assert _mid8_from_primary_meta(tmp_path, _SLUG) == ""


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_resolve_coordination_branch_degrades_to_none(tmp_path: Path, meta_text: str) -> None:
    """Corrupt primary meta → ``None`` (coordination topology undeclared)."""
    from mission_runtime.resolution import _resolve_coordination_branch

    _seed(tmp_path, meta_text)
    assert _resolve_coordination_branch(tmp_path, _SLUG) is None


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_resolve_mission_id_degrades_to_legacy_sentinel(tmp_path: Path, meta_text: str) -> None:
    """Corrupt primary meta → the ``legacy-<slug>`` bootstrap sentinel."""
    from mission_runtime.resolution import _resolve_mission_id

    _seed(tmp_path, meta_text)
    assert _resolve_mission_id(tmp_path, _SLUG) == f"legacy-{_SLUG}"


# ---------------------------------------------------------------------------
# runtime/next — route-unwrapped sites now surface the typed error.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_planner_resolve_workflow_raises_typed(tmp_path: Path, meta_text: str) -> None:
    """``planner._resolve_workflow_for_mission`` raises MissionMetaReadError.

    A raw ``ValueError`` would also satisfy ``pytest.raises(Exception)``;
    ``MissionMetaReadError`` is a ``RuntimeError`` subclass, NOT a
    ``ValueError``, so this genuinely fails on a regression to the unwrapped
    ``load_meta(...)`` call.
    """
    from runtime.next._internal_runtime.planner import _resolve_workflow_for_mission

    mission_dir = _seed(tmp_path, meta_text)
    with pytest.raises(MissionMetaReadError, match="fail-closed"):
        _resolve_workflow_for_mission(mission_dir)


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_runtime_bridge_workflow_template_raises_typed(tmp_path: Path, meta_text: str) -> None:
    """``runtime_bridge_io._workflow_runtime_template`` raises MissionMetaReadError.

    The corrupt meta is hit either at this module's own routed read or at the
    read-side seam it resolves through (``read_primary_meta``, routed in the
    same pass) — both raise the same typed error, never a raw ``ValueError``.
    """
    from runtime.next.runtime_bridge_io import _workflow_runtime_template

    _seed(tmp_path, meta_text)
    with pytest.raises(MissionMetaReadError, match="fail-closed"):
        _workflow_runtime_template(_SLUG, "software-dev", tmp_path, "software-dev")


# ---------------------------------------------------------------------------
# bulk_edit/gate.py — typed raise (the gate must not crash raw).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_is_bulk_edit_mission_raises_typed(tmp_path: Path, meta_text: str) -> None:
    from specify_cli.bulk_edit.gate import _is_bulk_edit_mission

    mission_dir = _seed(tmp_path, meta_text)
    with pytest.raises(MissionMetaReadError, match="fail-closed"):
        _is_bulk_edit_mission(mission_dir)


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_ensure_occurrence_classification_ready_raises_typed(tmp_path: Path, meta_text: str) -> None:
    from specify_cli.bulk_edit.gate import ensure_occurrence_classification_ready

    mission_dir = _seed(tmp_path, meta_text)
    with pytest.raises(MissionMetaReadError, match="fail-closed"):
        ensure_occurrence_classification_ready(mission_dir)


# ---------------------------------------------------------------------------
# context/resolver.py — the missing-file guard is preserved; malformed
# propagates the typed error instead of a raw ValueError.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_context_read_meta_json_raises_typed(tmp_path: Path, meta_text: str) -> None:
    from specify_cli.context.errors import MissingIdentityError
    from specify_cli.context.resolver import _read_meta_json

    mission_dir = _seed(tmp_path, meta_text)
    with pytest.raises(MissionMetaReadError, match="fail-closed"):
        _read_meta_json(mission_dir, tmp_path)
    # Missing meta.json keeps its own guard: MissingIdentityError, not the
    # typed read error (a missing file is field-absent, not a read failure).
    empty_root = tmp_path / "elsewhere"
    empty_root.mkdir()
    bare_dir = empty_root / "kitty-specs" / "bare-mission"
    bare_dir.mkdir(parents=True)
    with pytest.raises(MissingIdentityError, match="meta.json not found"):
        _read_meta_json(bare_dir, empty_root)


# ---------------------------------------------------------------------------
# decisions/service.py — typed read failure wraps into the domain error.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_decisions_resolve_mission_id_wraps_typed_into_domain(tmp_path: Path, meta_text: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """The service's own read wraps the typed failure into MISSION_NOT_FOUND.

    ``_mission_dir`` is pinned to the seeded dir because the placement seam it
    normally routes through has its OWN routed meta readers (``read_primary_
    meta``, routed in the same pass) — driven end-to-end below, they surface
    the same typed error before the service read fires.
    """
    from specify_cli.decisions import service as decisions_service
    from specify_cli.decisions.models import DecisionErrorCode
    from specify_cli.decisions.service import DecisionError

    mission_dir = _seed(tmp_path, meta_text)
    monkeypatch.setattr(decisions_service, "_mission_dir", lambda repo_root, slug: mission_dir)
    with pytest.raises(DecisionError) as excinfo:
        decisions_service._resolve_mission_id(tmp_path, _SLUG)
    assert excinfo.value.code == DecisionErrorCode.MISSION_NOT_FOUND
    assert excinfo.value.details == {"mission_slug": _SLUG}
    assert not isinstance(excinfo.value, ValueError)


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_decisions_resolve_mission_id_end_to_end_never_raw_valueerror(tmp_path: Path, meta_text: str) -> None:
    """End-to-end (no seam patching): corrupt meta surfaces typed, never raw.

    The placement seam's own routed readers raise ``MissionMetaReadError``
    before the service read is reached — a typed error either way, which is
    the NFR-003 contract; the raw ``ValueError`` this path leaked before the
    #3162 routing is gone.
    """
    from specify_cli.decisions.service import _resolve_mission_id

    _seed(tmp_path, meta_text)
    with pytest.raises(MissionMetaReadError, match="fail-closed"):
        _resolve_mission_id(tmp_path, _SLUG)


# ---------------------------------------------------------------------------
# missions/_read_path_resolver.py — typed raise at the shared read primitive.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_read_primary_meta_raises_typed(tmp_path: Path, meta_text: str) -> None:
    from specify_cli.missions._read_path_resolver import read_primary_meta

    _seed(tmp_path, meta_text)
    with pytest.raises(MissionMetaReadError, match="fail-closed"):
        read_primary_meta(tmp_path, _SLUG)


# ---------------------------------------------------------------------------
# missions/_resolve_planning_branch.py — typed read failure wraps into the
# domain error with the --target-branch escape hatch preserved.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_load_mission_target_branch_wraps_typed_into_domain(tmp_path: Path, meta_text: str) -> None:
    from specify_cli.missions._resolve_planning_branch import (
        PlanningBranchResolutionFailed,
        load_mission_target_branch,
    )

    mission_dir = _seed(tmp_path, meta_text)
    with pytest.raises(PlanningBranchResolutionFailed, match="unreadable"):
        load_mission_target_branch(mission_dir)


def test_load_mission_target_branch_missing_keeps_not_found_diagnostic(
    tmp_path: Path,
) -> None:
    """A missing meta.json keeps its own diagnostic (not the unreadable one)."""
    from specify_cli.missions._resolve_planning_branch import (
        PlanningBranchResolutionFailed,
        load_mission_target_branch,
    )

    mission_dir = tmp_path / "kitty-specs" / "absent-mission"
    mission_dir.mkdir(parents=True)
    with pytest.raises(PlanningBranchResolutionFailed, match="not found"):
        load_mission_target_branch(mission_dir)


# ---------------------------------------------------------------------------
# upgrade/feature_meta.py — degrade site: unreadable meta reads as "needs
# repair" (None), same as missing.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_load_feature_meta_degrades_to_none(tmp_path: Path, meta_text: str) -> None:
    from specify_cli.upgrade.feature_meta import load_feature_meta

    mission_dir = _seed(tmp_path, meta_text)
    assert load_feature_meta(mission_dir) is None
