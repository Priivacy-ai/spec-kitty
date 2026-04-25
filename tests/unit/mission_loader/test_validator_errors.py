"""Validator error-code coverage tests (T011 / NFR-002).

Locks the closed enum: every operator-facing :class:`LoaderErrorCode`
EXCEPT ``MISSION_CONTRACT_REF_UNRESOLVED`` is reachable from
:func:`validate_custom_mission` and produces the documented ``details``
keys per ``contracts/validation-errors.md``.

``MISSION_CONTRACT_REF_UNRESOLVED`` is intentionally excluded -- that
check happens at run-start in WP05 (the validator does NOT load the
on-disk ``MissionStepContractRepository``). See validator docstring.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from specify_cli.mission_loader import (
    LoaderErrorCode,
    validate_custom_mission,
)
from specify_cli.next._internal_runtime.discovery import DiscoveryContext


def _isolated_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> DiscoveryContext:
    """Build a DiscoveryContext that ONLY sees ``tmp_path`` as the project.

    - empty ``builtin_roots`` -> no built-in tier
    - ``user_home`` pointed at an empty subdir -> no user-global tier
    - ``SPEC_KITTY_MISSION_PATHS`` unset -> no env tier
    """
    monkeypatch.delenv("SPEC_KITTY_MISSION_PATHS", raising=False)
    user_home = tmp_path / "fake-home"
    user_home.mkdir()
    return DiscoveryContext(
        project_dir=tmp_path,
        user_home=user_home,
        builtin_roots=[],
    )


def _write_mission(tmp_path: Path, key: str, body: str, *, layer: str = "missions") -> Path:
    """Write a mission YAML file under ``.kittify/<layer>/<key>/mission.yaml``."""
    mission_dir = tmp_path / ".kittify" / layer / key
    mission_dir.mkdir(parents=True, exist_ok=True)
    file = mission_dir / "mission.yaml"
    file.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return file


# ---------------------------------------------------------------------------
# MISSION_KEY_UNKNOWN
# ---------------------------------------------------------------------------


def test_unknown_mission_key_yields_MISSION_KEY_UNKNOWN(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _isolated_context(tmp_path, monkeypatch)
    report = validate_custom_mission("does-not-exist", ctx)
    assert report.template is None
    assert report.errors[0].code is LoaderErrorCode.MISSION_KEY_UNKNOWN
    details = report.errors[0].details
    assert details["mission_key"] == "does-not-exist"
    assert "tiers_searched" in details


# ---------------------------------------------------------------------------
# MISSION_YAML_MALFORMED
# ---------------------------------------------------------------------------


def test_malformed_yaml_yields_MISSION_YAML_MALFORMED(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Real YAML parse error: bare ``<<<`` is invalid YAML.
    _write_mission(tmp_path, "broken", "<<<: not yaml\n  - this: [is broken\n")
    ctx = _isolated_context(tmp_path, monkeypatch)
    report = validate_custom_mission("broken", ctx)
    assert report.errors, "expected an error for malformed YAML"
    assert report.errors[0].code is LoaderErrorCode.MISSION_YAML_MALFORMED
    details = report.errors[0].details
    assert details["mission_key"] == "broken"
    assert "file" in details
    assert "parse_error" in details


def test_yaml_not_a_mapping_yields_MISSION_YAML_MALFORMED(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A YAML list at the root parses fine but fails the "must be a mapping"
    # rule inside ``load_mission_template_file`` -> MissionRuntimeError ->
    # MISSION_YAML_MALFORMED.
    _write_mission(tmp_path, "list-root", "- 1\n- 2\n")
    ctx = _isolated_context(tmp_path, monkeypatch)
    report = validate_custom_mission("list-root", ctx)
    assert report.errors[0].code is LoaderErrorCode.MISSION_YAML_MALFORMED


# ---------------------------------------------------------------------------
# MISSION_REQUIRED_FIELD_MISSING
# ---------------------------------------------------------------------------


def test_missing_required_field_yields_MISSION_REQUIRED_FIELD_MISSING(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Top-level ``mission:`` block missing required ``name``. The shorthand
    # path takes ``key`` from raw['key'] OR raw['name'] OR parent dir name.
    # We provide an explicit ``mission`` block missing required ``name`` so
    # the Pydantic validator reports a 'missing' error.
    body = """
    mission:
      key: incomplete
      version: "1.0.0"
    steps:
      - id: do
        title: Do
        agent_profile: doer
      - id: retrospective
        title: Retrospective
        agent_profile: retro
    """
    _write_mission(tmp_path, "incomplete", body)
    ctx = _isolated_context(tmp_path, monkeypatch)
    report = validate_custom_mission("incomplete", ctx)
    assert report.errors, "expected required-field-missing error"
    assert report.errors[0].code is LoaderErrorCode.MISSION_REQUIRED_FIELD_MISSING
    details = report.errors[0].details
    assert "field" in details
    assert details["mission_key"] == "incomplete"


# ---------------------------------------------------------------------------
# MISSION_KEY_RESERVED
# ---------------------------------------------------------------------------


def test_reserved_key_under_project_legacy_yields_MISSION_KEY_RESERVED(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = """
    mission:
      key: software-dev
      name: Custom Software Dev
      version: "1.0.0"
    steps:
      - id: do
        title: Do
        agent_profile: doer
      - id: retrospective
        title: Retro
        agent_profile: retro
    """
    _write_mission(tmp_path, "software-dev", body)
    ctx = _isolated_context(tmp_path, monkeypatch)
    report = validate_custom_mission("software-dev", ctx)
    assert report.errors[0].code is LoaderErrorCode.MISSION_KEY_RESERVED
    details = report.errors[0].details
    assert details["mission_key"] == "software-dev"
    assert details["tier"] == "project_legacy"
    assert "reserved_keys" in details
    assert "software-dev" in details["reserved_keys"]
    # Validator must NOT load when reserved -> no template attached.
    assert report.template is None


# ---------------------------------------------------------------------------
# MISSION_RETROSPECTIVE_MISSING
# ---------------------------------------------------------------------------


def test_missing_retrospective_yields_MISSION_RETROSPECTIVE_MISSING(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = """
    mission:
      key: noretro
      name: No Retrospective
      version: "1.0.0"
    steps:
      - id: plan
        title: Plan
        agent_profile: planner
      - id: ship
        title: Ship
        agent_profile: shipper
    """
    _write_mission(tmp_path, "noretro", body)
    ctx = _isolated_context(tmp_path, monkeypatch)
    report = validate_custom_mission("noretro", ctx)
    codes = [e.code for e in report.errors]
    assert LoaderErrorCode.MISSION_RETROSPECTIVE_MISSING in codes
    err = next(e for e in report.errors if e.code is LoaderErrorCode.MISSION_RETROSPECTIVE_MISSING)
    assert err.details["actual_last_step_id"] == "ship"
    assert err.details["expected"] == "retrospective"
    assert err.details["mission_key"] == "noretro"


# ---------------------------------------------------------------------------
# MISSION_STEP_NO_PROFILE_BINDING
# ---------------------------------------------------------------------------


def test_step_without_binding_yields_MISSION_STEP_NO_PROFILE_BINDING(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = """
    mission:
      key: nobind
      name: No Binding
      version: "1.0.0"
    steps:
      - id: orphan
        title: Orphan
        # no agent_profile, no contract_ref, no requires_inputs
      - id: retrospective
        title: Retro
        agent_profile: retro
    """
    _write_mission(tmp_path, "nobind", body)
    ctx = _isolated_context(tmp_path, monkeypatch)
    report = validate_custom_mission("nobind", ctx)
    codes = [e.code for e in report.errors]
    assert LoaderErrorCode.MISSION_STEP_NO_PROFILE_BINDING in codes
    err = next(
        e for e in report.errors if e.code is LoaderErrorCode.MISSION_STEP_NO_PROFILE_BINDING
    )
    assert err.details["step_id"] == "orphan"
    assert err.details["mission_key"] == "nobind"


# ---------------------------------------------------------------------------
# MISSION_STEP_AMBIGUOUS_BINDING
# ---------------------------------------------------------------------------


def test_step_with_both_bindings_yields_MISSION_STEP_AMBIGUOUS_BINDING(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = """
    mission:
      key: ambig
      name: Ambiguous
      version: "1.0.0"
    steps:
      - id: do-it
        title: Do it
        agent_profile: doer
        contract_ref: shared:do
      - id: retrospective
        title: Retro
        agent_profile: retro
    """
    _write_mission(tmp_path, "ambig", body)
    ctx = _isolated_context(tmp_path, monkeypatch)
    report = validate_custom_mission("ambig", ctx)
    codes = [e.code for e in report.errors]
    assert LoaderErrorCode.MISSION_STEP_AMBIGUOUS_BINDING in codes
    err = next(
        e for e in report.errors if e.code is LoaderErrorCode.MISSION_STEP_AMBIGUOUS_BINDING
    )
    assert err.details["step_id"] == "do-it"
    assert err.details["mission_key"] == "ambig"


# ---------------------------------------------------------------------------
# MISSION_KEY_AMBIGUOUS
# ---------------------------------------------------------------------------


def test_ambiguous_code_string_is_stable() -> None:
    """``MISSION_KEY_AMBIGUOUS`` is reserved for future use (per
    ``contracts/validation-errors.md``: "extreme edge case; default precedence
    picks one. Reserved for future use"). Validator never raises it today
    because the discoverer's deterministic precedence always picks one
    selected entry. Lock the wire spelling so future tranches can fire it
    without breaking consumers.
    """
    assert LoaderErrorCode.MISSION_KEY_AMBIGUOUS.value == "MISSION_KEY_AMBIGUOUS"


# ---------------------------------------------------------------------------
# MISSION_CONTRACT_REF_UNRESOLVED -- DEFERRED to WP05 run-start
# ---------------------------------------------------------------------------

# TODO(WP05): MISSION_CONTRACT_REF_UNRESOLVED is checked at run-start in
# the runtime bridge, NOT here in the validator. The validator does not
# load MissionStepContractRepository (per the WP02 boundary). When WP05
# wires the run-start contract resolution, add a parametrized case here
# OR a dedicated test in tests/unit/mission_loader/test_runtime_run_start.py
# (whichever surface owns the resolution). Tracking note: the wire spelling
# is locked by the LoaderErrorCode enum so consumers depending on the
# string value will not break when the case fires.


def test_contract_ref_unresolved_code_string_is_stable() -> None:
    assert (
        LoaderErrorCode.MISSION_CONTRACT_REF_UNRESOLVED.value
        == "MISSION_CONTRACT_REF_UNRESOLVED"
    )
