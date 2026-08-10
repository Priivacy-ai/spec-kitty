"""Tests for ``tracker_egress_verdict`` (#3108 WP03).

Covers T015-T020 of the WP03 work-package prompt:

* T015 -- module shape: ``EgressDestination`` (closed two-member set), the verdict value
  object (no ``binding_kind``), the module docstring carrying its required literal strings
  (the classifier's own docstring pin retired alongside its deletion -- egress-single-authority
  mission, WP03), and the no-import-time-``specify_cli.sync`` pin.
* T016 -- Channel 2's ``isinstance``-guarded resolver, observed red (as a ``TypeError``, not an
  ``AssertionError``) then green.
* T017 -- ``_JOIN``: the 8-cell table, both the structural (``len(_JOIN) == 8``) and the
  behavioural (a parametrised test over all 8 cells) pins.
* T018 -- (egress-single-authority mission, WP03) the former Channel-1 classifier
  (``_classify_channel1``) and its two non-authoritativeness pins are retired: the classifier
  is deleted, not migrated, and ``TestReportingSplitNeverFlipsEnforcement`` is rebuilt as a
  structural one-resolution-each proof (NFR-004/SC-003) plus the classifier's symbol-absence
  (SC-004), rather than re-pointed onto a monkeypatched disagreement that no longer has a
  second authority to disagree with.
* T019 -- message composition: the ``root=None`` byte-identity pin (both destinations), the
  fault message naming the offending value and both legal values, and the
  message-not-recomposed pin.
* T020 -- the never-raises contract over NFR-003's twelve shapes x two destinations (24 cases),
  and the exhaustiveness/two-site-change pin the WP02 reviewer asked for.
"""

from __future__ import annotations

import ast
import contextlib
import inspect
import os
import subprocess
import sys
import uuid as uuid_module
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import pytest

from specify_cli.tracker import config as tracker_config
from specify_cli.tracker.config import _EGRESS_LEGAL_VALUES, EGRESS_ABSENT, TrackerConfigError
from specify_cli.egress import UNDETERMINED_PROJECT_REFUSAL, project_egress_refusal
from specify_cli.tracker.local_service import LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS
from specify_cli.tracker.saas_client import TRACKER_EGRESS_IDENTIFIER_KINDS
from specify_cli.tracker.egress_verdict import (
    CHANNEL1_GRANTED,
    CHANNEL1_NO_RECORD,
    CHANNEL1_NOT_CONSENTABLE,
    CHANNEL1_RECORDED_REFUSAL,
    CHANNEL1_UNCLASSIFIED,
    CHANNEL1_UNDETERMINED,
    CHANNEL2_ABSENT,
    CHANNEL2_FAULT,
    CHANNEL_1,
    CHANNEL_2,
    OUTCOME_DEFER,
    OUTCOME_DEFER_REPORTED_NOOP,
    OUTCOME_PERMIT,
    OUTCOME_REFUSE,
    EgressDestination,
    TrackerEgressVerdict,
    _channel1_decided_message,
    _channel2_decided_message,
    _JOIN,
    _permit_message,
    _resolve_channel1,
    _resolve_channel2,
    tracker_egress_verdict,
)

# `integration`, not `[unit, fast]`. Both original markers were wrong by the registry's own
# definitions: `unit` is "no subprocess", and Rule 2 of `test_pytest_marker_correctness.py`
# forbids `fast` on any file invoking `subprocess.*` -- this one shells out at the
# no-import-time-`specify_cli.sync` pin below. The mission was adding a violator to an
# always-on CI gate (WP07 review, MEDIUM-3). The test itself is genuinely quick (~0.17s), but
# Rule 2 has no per-file escape hatch and the honest label is the one that matches behaviour.
pytestmark = [pytest.mark.integration]

DESTINATIONS = [EgressDestination.LOCAL_SUBPROCESS, EgressDestination.HOSTED_SERVICE]

#: The identifier-set fragment each destination's **owning transport** passes, imported from
#: those transports rather than restated here so a fragment reworded in production cannot
#: leave this suite asserting the old text. Bundle B made ``identifiers`` a required
#: parameter of ``project_egress_refusal``, and ``tracker_egress_verdict`` threads it into
#: Channel 1, so every call below must name one. Tests pass the *owning transport's*
#: fragment because that is what the enforcing gate passes -- the FR-016 byte-identity pins
#: in this file are only meaningful if the suite renders the string the gate renders.
_IDENTIFIERS_FOR = {
    EgressDestination.LOCAL_SUBPROCESS: LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS,
    EgressDestination.HOSTED_SERVICE: TRACKER_EGRESS_IDENTIFIER_KINDS,
}


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_config(root: Path, tracker_block: str = "", *, project_block: str | None = None) -> Path:
    """Write a minimal ``.kittify/config.yaml``.

    ``project_block`` supplies the ``project:`` section verbatim (indented already) when the
    scenario needs a resolvable identity; omitted entirely for the "not consentable" scenario.
    """
    config_path = root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    parts = []
    if project_block is not None:
        parts.append(project_block)
    if tracker_block:
        parts.append(tracker_block)
    config_path.write_text("".join(parts), encoding="utf-8")
    return config_path


def _project_block(project_uuid: str | None = None) -> str:
    # A *fresh* uuid per call, never a shared constant: `_answer_project_local` reconciles a
    # readable decision into the machine-global, uuid-keyed consent index
    # (`consent.py::_reconcile_index`), which outlives any single test's tmp_path. Two builders
    # sharing one uuid across tests would let one test's recorded decision leak into another's
    # "no record" fixture as a stale machine-index hit -- exactly the cross-test contamination
    # this suite's own FR-007 leak guard warns about for `set_project_consent`.
    project_uuid = project_uuid or str(uuid_module.uuid4())
    return (
        "project:\n"
        f"  uuid: {project_uuid}\n"
        "  slug: wp03-suite\n"
        "  node_id: node00000001\n"
        "  repo_slug: spec-kitty-tests/wp03-suite\n"
        f"  build_id: {project_uuid}\n"
    )


def _no_record_root(tmp_path: Path, name: str = "no-record") -> Path:
    """A checkout with a resolvable identity but no Channel-1 record at all."""
    root = tmp_path / name
    _write_config(root, project_block=_project_block())
    return root


def _recorded_refusal_root(tmp_path: Path, name: str = "recorded-refusal") -> Path:
    """A checkout with an identity and an explicit ``sync.enabled: false``."""
    root = tmp_path / name
    _write_config(root, "sync:\n  enabled: false\n", project_block=_project_block())
    return root


def _recorded_grant_root(tmp_path: Path, name: str = "recorded-grant") -> Path:
    """A checkout with an identity and an explicit ``sync.enabled: true`` (Channel 1 permits)."""
    root = tmp_path / name
    _write_config(root, "sync:\n  enabled: true\n", project_block=_project_block())
    return root


def _not_consentable_root(tmp_path: Path, name: str = "not-consentable") -> Path:
    """A checkout with no ``project:`` block at all -- identity never resolves."""
    root = tmp_path / name
    _write_config(root)
    return root


def _with_tracker_egress(root: Path, egress_line: str) -> None:
    """Append a ``tracker: {egress: ...}`` block onto an already-written config."""
    config_path = root / ".kittify" / "config.yaml"
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    config_path.write_text(existing + "tracker:\n" + egress_line, encoding="utf-8")


# ---------------------------------------------------------------------------
# T015 -- module shape, docstrings, no-import-time-sync pin
# ---------------------------------------------------------------------------


class TestModuleShape:
    def test_egress_destination_is_closed_two_member_set(self) -> None:
        assert {m.name for m in EgressDestination} == {"LOCAL_SUBPROCESS", "HOSTED_SERVICE"}

    def test_destination_is_required_keyword_only(self) -> None:
        sig = inspect.signature(tracker_egress_verdict)
        destination_param = sig.parameters["destination"]
        assert destination_param.kind is inspect.Parameter.KEYWORD_ONLY
        assert destination_param.default is inspect.Parameter.empty

    def test_destination_cannot_be_passed_positionally(self) -> None:
        # The keyword-only contract is a *runtime* property this test proves at runtime.
        # Re-typed as a deliberately arity-erased ``Callable[..., object]`` before the call so
        # this passes ``mypy --strict`` both when this file is checked alone (where this
        # project's ``follow_imports = "skip"`` override for ``specify_cli.*`` already erases
        # the real signature to ``Any``) and when checked together with the source module
        # (where mypy sees the real keyword-only signature and would otherwise correctly
        # reject this call statically -- which is not the property under test here).
        call_any_arity: Callable[..., TrackerEgressVerdict] = tracker_egress_verdict
        with pytest.raises(TypeError):
            call_any_arity(None, EgressDestination.LOCAL_SUBPROCESS)

    def test_verdict_has_no_binding_kind_field(self) -> None:
        field_names = set(TrackerEgressVerdict.__dataclass_fields__)
        assert "binding_kind" not in field_names
        assert field_names == {
            "refused",
            "refusing_channels",
            "destination",
            "channel1_state",
            "channel2_state",
            "channel2_raw",
            "message",
            "remedies",
        }

    def test_module_docstring_carries_the_four_required_literals(self) -> None:
        import specify_cli.tracker.egress_verdict as mod

        doc = mod.__doc__ or ""
        assert "invocation/adapters.py:81" in doc
        assert "Q3" in doc
        assert "delete" in doc
        assert "not migrate" in doc

    def test_module_docstring_states_the_import_form_rule(self) -> None:
        import specify_cli.tracker.egress_verdict as mod

        doc = mod.__doc__ or ""
        assert "EgressDestination" in doc
        assert "aliased" in doc

    def test_egress_destination_docstring_names_the_third_transport_requirement(self) -> None:
        doc = EgressDestination.__doc__ or ""
        assert "operator decision" in doc
        assert "FR-004" in doc

    def test_module_imports_cleanly_without_specify_cli_sync(self) -> None:
        """No import-time dependency on ``specify_cli.sync`` (NFR-003).

        Run in a subprocess with ``specify_cli.sync`` blocked at import time, so a stale
        ``sys.modules`` cache in *this* process cannot hide a real dependency.
        """
        script = (
            "import sys\n"
            "class _Blocker:\n"
            "    def find_module(self, name, path=None):\n"
            "        if name == 'specify_cli.sync' or name.startswith('specify_cli.sync.'):\n"
            "            raise ImportError('specify_cli.sync is blocked for this probe')\n"
            "        return None\n"
            "sys.meta_path.insert(0, _Blocker())\n"
            "import specify_cli.tracker.egress_verdict\n"
            "print('IMPORTED_OK')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if "IMPORTED_OK" in result.stdout:
            return

        # The probe failed -- but distinguish a real ``specify_cli.sync`` import-edge
        # regression from an interpreter that simply has no editable install on its path
        # (#3291). Under ``uv run``, ``sys.executable`` can resolve to a bare pyenv
        # interpreter that lacks the package entirely, so the probe dies on
        # ``ModuleNotFoundError: specify_cli`` (the whole package) without ever reaching
        # the ``specify_cli.sync`` edge under test. Positive control: the SAME interpreter
        # importing the module with NO blocker. If even that cannot import the package,
        # the probe was never meaningful here -- skip rather than report a false red.
        control = subprocess.run(
            [sys.executable, "-c", "import specify_cli.tracker.egress_verdict; print('CONTROL_OK')"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if "CONTROL_OK" not in control.stdout:
            pytest.skip(
                f"interpreter {sys.executable!r} cannot import specify_cli even without the "
                f"sync blocker (no editable install on its path) -- the import-isolation probe "
                f"is not meaningful here; control stderr={control.stderr!r}"
            )
        # The package imports fine WITHOUT the blocker but fails WITH it: a genuine
        # import-time dependency on ``specify_cli.sync`` (the exact regression this guards).
        pytest.fail(
            f"module import failed with specify_cli.sync blocked yet imports fine without it "
            f"-- a real import-time dependency on specify_cli.sync. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    def test_no_module_level_import_of_specify_cli_sync_by_source_inspection(self) -> None:
        """Belt-and-suspenders: no top-level ``import specify_cli.sync`` statement at all."""
        import specify_cli.tracker.egress_verdict as mod

        source = inspect.getsource(mod)
        # Only occurrences of "specify_cli.sync" outside the guarded, function-local imports
        # (which are indented) are a module-level dependency.
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import specify_cli.sync", "from specify_cli.sync")):
                # Must be indented (i.e. inside a function), never at column 0.
                assert line[0] in (" ", "\t"), f"module-level sync import found: {line!r}"


# ---------------------------------------------------------------------------
# T016 -- Channel 2's isinstance-guarded decode, red first
# ---------------------------------------------------------------------------


class TestChannel2Decode:
    @pytest.mark.parametrize(
        ("yaml_body", "expected_raw"),
        [
            ("tracker:\n  egress:\n    a: b\n", {"a": "b"}),
            ("tracker:\n  egress:\n  - a\n  - b\n", ["a", "b"]),
        ],
        ids=["mapping", "list"],
    )
    def test_unhashable_raw_would_red_the_naive_implementation(
        self, tmp_path: Path, yaml_body: str, expected_raw: object
    ) -> None:
        """Hazard A, observed: a bare ``raw in _LEGAL`` raises TypeError for an unhashable raw.

        Review round 2, LOW-2: this previously built its own ``frozenset`` and its own dict
        literal, so it asserted Python's ``in`` semantics and never touched this module -- it
        could not fail for any reason related to the code under test (proven: with the
        ``isinstance`` guard dropped, 10 tests red and neither of these was among them).

        It now takes the raw value **from the shipped resolver** and demonstrates the naive
        membership test against the module's own legal-value set. So it reds if
        ``_resolve_channel2`` ever stops surfacing the unhashable value it extracted -- which
        is the precondition that makes the guard necessary in the first place. The guard's own
        behaviour is pinned by the two ``is_green_as_fault`` cases below.
        """
        _write_config(tmp_path, yaml_body)
        _state, raw = _resolve_channel2(tmp_path)
        assert raw == expected_raw, "the resolver must surface the raw unhashable value verbatim"
        with pytest.raises(TypeError, match="unhashable type"):
            _ = raw in _EGRESS_LEGAL_VALUES  # the naive, unguarded implementation this WP does not ship

    def test_mapping_at_key_is_green_as_fault_on_the_shipped_resolver(self, tmp_path: Path) -> None:
        """The fix: ``_resolve_channel2`` never raises for the same input -- it faults."""
        _write_config(tmp_path, "tracker:\n  egress:\n    a: b\n")
        state, raw = _resolve_channel2(tmp_path)
        assert state == CHANNEL2_FAULT
        assert raw == {"a": "b"}

    def test_list_at_key_is_green_as_fault(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "tracker:\n  egress:\n  - a\n  - b\n")
        state, raw = _resolve_channel2(tmp_path)
        assert state == CHANNEL2_FAULT
        assert raw == ["a", "b"]

    def test_absent_key_defers(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "tracker:\n  provider: beads\n")
        state, raw = _resolve_channel2(tmp_path)
        assert state == CHANNEL2_ABSENT
        assert raw is EGRESS_ABSENT

    def test_no_tracker_block_at_all_defers(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "")
        state, raw = _resolve_channel2(tmp_path)
        assert state == CHANNEL2_ABSENT

    def test_non_mapping_tracker_block_is_absence_not_fault(self, tmp_path: Path) -> None:
        for block in ('tracker: "yes"\n', "tracker: 3\n", "tracker:\n"):
            root = tmp_path / f"case-{hash(block) & 0xFFFF}"
            _write_config(root, block)
            state, _raw = _resolve_channel2(root)
            assert state == CHANNEL2_ABSENT, f"{block!r} must be absence, not a fault"

    def test_present_null_is_fault_distinct_from_absence(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "tracker:\n  egress: null\n")
        state, raw = _resolve_channel2(tmp_path)
        assert state == CHANNEL2_FAULT
        assert raw is None

    def test_refused_and_permitted_decode_to_themselves(self, tmp_path: Path) -> None:
        refused_root = tmp_path / "r"
        _write_config(refused_root, "tracker:\n  egress: refused\n")
        assert _resolve_channel2(refused_root) == ("refused", "refused")

        permitted_root = tmp_path / "p"
        _write_config(permitted_root, "tracker:\n  egress: permitted\n")
        assert _resolve_channel2(permitted_root) == ("permitted", "permitted")

    def test_unreadable_config_is_a_fault_not_a_raise(self, tmp_path: Path) -> None:
        if os.geteuid() == 0:
            pytest.skip("root bypasses file permission checks")
        config_path = _write_config(tmp_path, "tracker:\n  egress: refused\n")
        config_path.chmod(0o000)
        try:
            state, _raw = _resolve_channel2(tmp_path)
        finally:
            config_path.chmod(0o644)
        assert state == CHANNEL2_FAULT

    def test_reads_config_exactly_once(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_config(tmp_path, "tracker:\n  egress: refused\n")
        calls = []
        real = tracker_config.load_tracker_config

        def _counting(root: Path) -> object:
            calls.append(root)
            return real(root)

        monkeypatch.setattr(
            "specify_cli.tracker.egress_verdict.load_tracker_config", _counting
        )
        _resolve_channel2(tmp_path)
        assert len(calls) == 1  # golden-count: cardinality-is-contract


# ---------------------------------------------------------------------------
# T017 -- the 8-cell join
# ---------------------------------------------------------------------------

#: Cell keys ``test_all_8_cells`` actually executed, asserted against ``_JOIN`` by
#: ``test_all_8_cells_ran``. Module-level rather than a fixture because the point is to
#: observe execution *across* the parametrised run, not within one case (review round 2,
#: LOW-3). ``test_all_8_cells_ran`` is declared after ``test_all_8_cells`` so pytest's
#: definition-order execution within the class populates it first.
_CELLS_EXERCISED: set[tuple[str, EgressDestination]] = set()


class TestJoinTable:
    def test_join_has_exactly_8_entries_structurally(self) -> None:
        """Survives a test being deleted -- a structural pin, not a test-local counter."""
        assert len(_JOIN) == 8  # golden-count: cardinality-is-contract

    @pytest.mark.parametrize(
        "channel2_state,destination,expected_outcome",
        [
            (CHANNEL2_FAULT, EgressDestination.LOCAL_SUBPROCESS, OUTCOME_REFUSE),
            (CHANNEL2_FAULT, EgressDestination.HOSTED_SERVICE, OUTCOME_REFUSE),
            ("refused", EgressDestination.LOCAL_SUBPROCESS, OUTCOME_REFUSE),
            ("refused", EgressDestination.HOSTED_SERVICE, OUTCOME_REFUSE),
            ("permitted", EgressDestination.LOCAL_SUBPROCESS, OUTCOME_PERMIT),
            ("permitted", EgressDestination.HOSTED_SERVICE, OUTCOME_DEFER_REPORTED_NOOP),
            (CHANNEL2_ABSENT, EgressDestination.LOCAL_SUBPROCESS, OUTCOME_DEFER),
            (CHANNEL2_ABSENT, EgressDestination.HOSTED_SERVICE, OUTCOME_DEFER),
        ],
    )
    def test_all_8_cells(self, channel2_state: str, destination: EgressDestination, expected_outcome: str) -> None:
        assert _JOIN[(channel2_state, destination)] == expected_outcome
        _CELLS_EXERCISED.add((channel2_state, destination))

    def test_all_8_cells_ran(self) -> None:
        """The behavioural half: asserts the parametrised cells actually *executed*.

        Review round 2, LOW-3: this previously re-walked ``_JOIN.items()`` and asserted the
        count was 8, which is ``len(_JOIN) == 8`` restated -- it would have passed even if
        ``test_all_8_cells`` had been skipped or collected away entirely. It now counts the
        keys ``test_all_8_cells`` recorded as it ran, and asserts that set is exactly
        ``_JOIN``'s key set, so a parametrisation that silently stops covering a cell reds
        here instead of passing.
        """
        print(f"8-cell join: ran {len(_CELLS_EXERCISED)} cells")
        assert set(_JOIN) == _CELLS_EXERCISED, (
            f"parametrised cells executed {sorted(map(str, _CELLS_EXERCISED))} "
            f"but _JOIN declares {sorted(map(str, _JOIN))}"
        )
        assert len(_CELLS_EXERCISED) == 8  # golden-count: cardinality-is-contract

    def test_join_is_data_not_branches(self) -> None:
        """``_JOIN`` is a plain module-level dict -- no function wraps it in control flow."""
        assert isinstance(_JOIN, dict)
        for key in _JOIN:
            assert isinstance(key, tuple)
            assert len(key) == 2  # golden-count: cardinality-is-contract

    def test_permit_at_local_subprocess_grants_independently_of_channel1(self, tmp_path: Path) -> None:
        """FR-004: Channel 2 ``permitted`` at LOCAL_SUBPROCESS is a grant even when Channel 1
        would refuse (no ``sync.enabled`` record at all -- not consentable)."""
        root = _not_consentable_root(tmp_path)
        _with_tracker_egress(root, "  egress: permitted\n")
        verdict = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS])
        assert verdict.refused is False
        assert verdict.refusing_channels == frozenset()

    def test_permit_at_hosted_service_is_a_reported_noop_channel1_absent_refuses(
        self, tmp_path: Path
    ) -> None:
        """FR-005: the same recorded grant is a no-op at HOSTED_SERVICE -- Channel 1 decides,
        and here Channel 1 has no record, so it refuses."""
        root = _not_consentable_root(tmp_path)
        _with_tracker_egress(root, "  egress: permitted\n")
        verdict = tracker_egress_verdict(root, destination=EgressDestination.HOSTED_SERVICE, identifiers=_IDENTIFIERS_FOR[EgressDestination.HOSTED_SERVICE])
        assert verdict.refused is True
        assert verdict.channel2_state == "permitted"
        assert CHANNEL_1 in verdict.refusing_channels
        assert CHANNEL_2 not in verdict.refusing_channels

    def test_permit_at_hosted_service_with_channel1_granted_permits(self, tmp_path: Path) -> None:
        """The other half of the no-op cell: when Channel 1 also grants, the overall verdict
        permits, but the grant is still recorded as a no-op (SC-014 checkout 6)."""
        root = _recorded_grant_root(tmp_path)
        _with_tracker_egress(root, "  egress: permitted\n")
        verdict = tracker_egress_verdict(root, destination=EgressDestination.HOSTED_SERVICE, identifiers=_IDENTIFIERS_FOR[EgressDestination.HOSTED_SERVICE])
        assert verdict.refused is False
        assert verdict.channel2_state == "permitted"

    def test_two_different_answers_on_two_rows_same_checkout(self, tmp_path: Path) -> None:
        """SC-014's discriminating scenario: one checkout, two different answers."""
        root = _not_consentable_root(tmp_path)
        _with_tracker_egress(root, "  egress: permitted\n")
        local = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS])
        hosted = tracker_egress_verdict(root, destination=EgressDestination.HOSTED_SERVICE, identifiers=_IDENTIFIERS_FOR[EgressDestination.HOSTED_SERVICE])
        assert local.refused is False
        assert hosted.refused is True

    def test_refused_refuses_at_both_destinations_regardless_of_channel1(self, tmp_path: Path) -> None:
        root = _recorded_grant_root(tmp_path)  # Channel 1 permits
        _with_tracker_egress(root, "  egress: refused\n")
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            assert verdict.refused is True
            assert CHANNEL_2 in verdict.refusing_channels
            assert CHANNEL_1 not in verdict.refusing_channels  # channel 1 permits here
            # HIGH-2 regression (review round 1): Channel 1 genuinely permits here, so the
            # reported state must be CHANNEL1_GRANTED, never one of the refusal labels
            # (the original defect reported "recorded_refusal" on exactly this fixture).
            assert verdict.channel1_state == CHANNEL1_GRANTED

    def test_both_channels_refuse_names_both(self, tmp_path: Path) -> None:
        root = _recorded_refusal_root(tmp_path)  # Channel 1 refuses
        _with_tracker_egress(root, "  egress: refused\n")  # Channel 2 also refuses
        verdict = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS])
        assert verdict.refused is True
        assert verdict.refusing_channels == frozenset({CHANNEL_1, CHANNEL_2})

    def test_absent_defers_to_channel1_no_record(self, tmp_path: Path) -> None:
        root = _no_record_root(tmp_path)
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            assert verdict.refused is True
            assert verdict.refusing_channels == frozenset({CHANNEL_1})

    def test_absent_defers_to_channel1_granted(self, tmp_path: Path) -> None:
        root = _recorded_grant_root(tmp_path)
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            assert verdict.refused is False
            assert verdict.refusing_channels == frozenset()
            # HIGH-2 regression (review round 1): this is the exact fixture the reviewer used
            # to demonstrate `channel1_state == 'recorded_refusal'` while the verdict permitted.
            assert verdict.channel1_state == CHANNEL1_GRANTED

    def test_both_channels_always_evaluated_no_channel1_first_shortcircuit(
        self, tmp_path: Path
    ) -> None:
        """A Channel-1-first short circuit would refuse a project Channel 2 permits."""
        root = _recorded_refusal_root(tmp_path)  # Channel 1 refuses
        _with_tracker_egress(root, "  egress: permitted\n")  # Channel 2 grants (local only)
        verdict = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS])
        assert verdict.refused is False, "Channel 2's grant must not be short-circuited by Channel 1"


# ---------------------------------------------------------------------------
# T018 -- retired (egress-single-authority mission, WP03): the Channel-1 classifier and its
# two non-authoritativeness pins are deleted, not migrated (C-002) -- see
# TestReportingSplitNeverFlipsEnforcement below for the rebuilt guarantee.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Rebuilt (not re-pointed), egress-single-authority mission WP03, Decision 4 --
# supersedes the PR #3135 adversarial-squad pin (HIGH-2) that used to live here.
# ---------------------------------------------------------------------------


class TestReportingSplitNeverFlipsEnforcement:
    """Structural proof that there is no second authority left to disagree with the first.

    PR #3135's adversarial squad (robertDouglass) originally flagged HIGH-2 here: Channel 1
    was *enforced* through the single canonical authority (``_resolve_channel1`` ->
    ``project_egress_refusal``), but its diagnostic *state* was independently re-resolved by
    ``_classify_channel1`` through a second, separate read of ``specify_cli.sync.consent`` /
    ``specify_cli.sync.routing``. The original two tests here forced that classifier to
    disagree with the enforcing read and proved the enforced answer did not move.

    That premise is gone (research.md Decision 4): ``_classify_channel1`` is **delete**d, **not
    migrate**d -- ``channel1_state``/``generic`` are now sourced directly off the same
    :func:`~specify_cli.egress._egress_decision` evaluation that decides ``permits``
    (:func:`~specify_cli.tracker.egress_verdict._resolve_channel1`). There is no longer a
    second, independent resolution to force into disagreement, so this class is rebuilt as the
    structural claim that makes that true: exactly one ``resolve_checkout_sync_routing_readonly``
    and one ``resolve_project_consent`` call happen per gated verdict (NFR-004/SC-003), and the
    ``_classify_channel1`` symbol itself no longer exists (SC-004). The full
    enforcement-equivalence matrix (the permit row and every consent-precedence level) is
    WP01's own C-001 certifier
    (``tests/sync/tracker/test_egress_single_authority.py::TestT001EnforcementEquivalenceMatrix``)
    and is intentionally not re-duplicated here.
    """

    def test_classify_channel1_symbol_is_absent(self) -> None:
        """SC-004: the classifier is gone, not merely unused."""
        import specify_cli.tracker.egress_verdict as mod

        assert not hasattr(mod, "_classify_channel1"), (
            "_classify_channel1 must be deleted, not migrated, once channel1_state is sourced "
            "from the single authority (C-002)"
        )

    def test_gated_verdict_resolves_routing_and_consent_exactly_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NFR-004/SC-003: a refusing root reaches the registered enforcing resolver's own
        routing/consent resolution exactly once each -- there is no second, independent read
        of either left to run alongside it."""
        from specify_cli.sync import consent as consent_module
        from specify_cli.sync import routing as routing_module

        routing_calls: list[Path] = []
        real_routing = routing_module.resolve_checkout_sync_routing_readonly

        def _counting_routing(root: Path) -> Any:
            routing_calls.append(root)
            return real_routing(root)

        consent_calls: list[tuple[Any, ...]] = []
        real_consent = consent_module.resolve_project_consent

        def _counting_consent(*args: Any, **kwargs: Any) -> Any:
            consent_calls.append(args)
            return real_consent(*args, **kwargs)

        monkeypatch.setattr(routing_module, "resolve_checkout_sync_routing_readonly", _counting_routing)
        monkeypatch.setattr(consent_module, "resolve_project_consent", _counting_consent)

        root = _recorded_refusal_root(tmp_path)  # Channel 1 genuinely refuses
        verdict = tracker_egress_verdict(
            root,
            destination=EgressDestination.LOCAL_SUBPROCESS,
            identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS],
        )

        assert verdict.refused is True
        assert verdict.channel1_state == CHANNEL1_RECORDED_REFUSAL
        assert len(routing_calls) == 1, (
            f"NFR-004/SC-003: expected exactly one checkout-routing resolution per gated "
            f"verdict, got {len(routing_calls)}"
        )
        assert len(consent_calls) == 1, (
            f"NFR-004/SC-003: expected exactly one project-consent resolution per gated "
            f"verdict, got {len(consent_calls)}"
        )


# ---------------------------------------------------------------------------
# T016 -- the message composer stays total over a degraded channel1_state (post-plan M2).
# A direct, unit-level replacement for the deleted non-authoritativeness pin 2 (a raising
# classifier could reach this same branch before; now a degraded EgressConsent member does).
# ---------------------------------------------------------------------------


class TestMessageComposerTotalOverDegradedState:
    """``_channel1_decided_message`` must check ``channel1_generic`` *before* indexing
    ``_CHANNEL1_DESCRIPTIONS``/``_CHANNEL1_REMEDIES`` -- both dicts are keyed only on the three
    named refusal states, so a degraded ``channel1_label`` (e.g. the reused
    ``CHANNEL1_UNCLASSIFIED``) would ``KeyError`` if the generic branch were not checked first.
    Exercised directly against the composer, at both destinations, rather than only through
    ``tracker_egress_verdict`` -- so a regression here fails at the unit that owns the
    total/never-raise contract, not only at the integration harness (WP01 T004) that also pins
    it end to end.
    """

    @pytest.mark.parametrize("destination", DESTINATIONS, ids=["local_subprocess", "hosted_service"])
    def test_degraded_label_renders_generic_wording_never_keyerror(
        self, destination: EgressDestination
    ) -> None:
        message, remedies = _channel1_decided_message(
            destination=destination,
            channel1_permits=False,
            channel1_label=CHANNEL1_UNCLASSIFIED,
            channel1_generic=True,
            noop=False,
        )
        assert "could not be determined in detail" in message
        if destination is EgressDestination.LOCAL_SUBPROCESS:
            # LOCAL_SUBPROCESS always offers the Channel-2 grant remedy, independently of
            # channel1_generic -- it is not one of the state-keyed `_CHANNEL1_REMEDIES`.
            assert len(remedies) == 1 and "permitted" in remedies[0]
        else:
            assert remedies == ()

    def test_non_generic_label_still_indexes_the_specific_description(self) -> None:
        """Control: a non-degraded label still renders its specific wording, so the generic
        branch is proven to be a real fork rather than the only path ever taken."""
        message, remedies = _channel1_decided_message(
            destination=EgressDestination.LOCAL_SUBPROCESS,
            channel1_permits=False,
            channel1_label=CHANNEL1_NO_RECORD,
            channel1_generic=False,
            noop=False,
        )
        assert "no record" in message
        assert remedies != ()


# ---------------------------------------------------------------------------
# T019 -- message composition
# ---------------------------------------------------------------------------


class TestPinnedVocabulary:
    """The exact wording tokens WP04/WP05's acceptance harness asserts on (coordinator
    addendum, dated after WP01's acceptance-harness review completed). Recorded here as pins
    of their own so a later edit to this module's message wording cannot silently drop a
    token those downstream harnesses depend on."""

    def test_channel2_refusal_names_channel2_or_tracker_egress(self, tmp_path: Path) -> None:
        root = tmp_path / "c2-refused"
        _write_config(root, "tracker:\n  egress: refused\n")
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            assert "Channel 2" in verdict.message or "tracker.egress" in verdict.message

    def test_channel1_refusal_names_channel1(self, tmp_path: Path) -> None:
        """The ``Channel 1`` token is pinned at ``LOCAL_SUBPROCESS`` only.

        ``HOSTED_SERVICE`` is excluded deliberately, not overlooked: FR-016 requires that path
        to reproduce `#3030`'s shipped refusal byte for byte, and that string predates this
        mission's channel vocabulary -- it says "has not consented to hosted sync" and never
        names a channel. WP01's hosted cells anticipated this and assert the disjunction
        ``"Channel 1" in msg or "has not consented to hosted sync" in msg``; the assertion
        below is its hosted half, so the token is still pinned *somewhere* for that path.
        """
        root = _no_record_root(tmp_path)
        local = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS])
        assert "Channel 1" in local.message

        hosted = tracker_egress_verdict(root, destination=EgressDestination.HOSTED_SERVICE, identifiers=_IDENTIFIERS_FOR[EgressDestination.HOSTED_SERVICE])
        assert "Channel 1" in hosted.message or "has not consented to hosted sync" in hosted.message

    def test_hosted_noop_cell_says_noop_or_does_not_apply(self, tmp_path: Path) -> None:
        """Hosted destination, Channel 1 permits, tracker grant recorded -- the no-op cell."""
        root = _recorded_grant_root(tmp_path)
        _with_tracker_egress(root, "  egress: permitted\n")
        verdict = tracker_egress_verdict(root, destination=EgressDestination.HOSTED_SERVICE, identifiers=_IDENTIFIERS_FOR[EgressDestination.HOSTED_SERVICE])
        assert verdict.refused is False
        assert "no-op" in verdict.message or "does not apply" in verdict.message

    def test_no_record_state_says_no_record(self, tmp_path: Path) -> None:
        root = _no_record_root(tmp_path)
        verdict = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS])
        assert verdict.channel1_state == CHANNEL1_NO_RECORD
        assert "no record" in verdict.message

    def test_recorded_refusal_state_says_refus_not_no_record(self, tmp_path: Path) -> None:
        root = _recorded_refusal_root(tmp_path)
        verdict = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS])
        assert verdict.channel1_state == CHANNEL1_RECORDED_REFUSAL
        assert "refus" in verdict.message
        assert "no record" not in verdict.message

    def test_not_consentable_state_says_not_consentable_or_identity(self, tmp_path: Path) -> None:
        root = _not_consentable_root(tmp_path)
        verdict = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS])
        assert verdict.channel1_state == CHANNEL1_NOT_CONSENTABLE
        assert "not consentable" in verdict.message or "identity" in verdict.message

    def test_near_miss_fault_quotes_offending_value_and_both_legal_spellings(self, tmp_path: Path) -> None:
        root = tmp_path / "near-miss-yes"
        _write_config(root, "tracker:\n  egress: yes\n")
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            assert "refused" in verdict.message
            assert "permitted" in verdict.message
            assert "yes" in verdict.message

    def test_three_channel1_states_are_distinguishable(self, tmp_path: Path) -> None:
        """A single undifferentiated 'Channel 1 denies' string is explicitly insufficient --
        the three states must remain distinguishable in the composed message."""
        no_record = tracker_egress_verdict(
            _no_record_root(tmp_path),
            destination=EgressDestination.LOCAL_SUBPROCESS,
            identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS],
        )
        recorded_refusal = tracker_egress_verdict(
            _recorded_refusal_root(tmp_path), destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS]
        )
        not_consentable = tracker_egress_verdict(
            _not_consentable_root(tmp_path), destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS]
        )
        messages = {no_record.message, recorded_refusal.message, not_consentable.message}
        assert len(messages) == 3, "the three Channel-1 states must produce three distinct messages"  # golden-count: cardinality-is-contract


class TestMessageComposition:
    def test_root_none_byte_identical_to_undetermined_at_both_destinations(self) -> None:
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(None, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            assert verdict.message == UNDETERMINED_PROJECT_REFUSAL
            assert verdict.refused is True
            assert verdict.remedies == ()

    def test_root_none_channel1_state_is_undetermined_and_reachable_only_there(self) -> None:
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(None, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            assert verdict.channel1_state == CHANNEL1_UNDETERMINED

    def test_undetermined_state_not_reachable_with_a_real_root(self, tmp_path: Path) -> None:
        for builder in (_no_record_root, _recorded_refusal_root, _not_consentable_root, _recorded_grant_root):
            root = builder(tmp_path, name=f"undetermined-check-{builder.__name__}")
            for destination in DESTINATIONS:
                verdict = tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
                assert verdict.channel1_state != CHANNEL1_UNDETERMINED

    NEAR_MISS_FAULTS: list[tuple[str, str, object]] = [
        ("Refused", "  egress: Refused\n", "Refused"),
        ("REFUSED", "  egress: REFUSED\n", "REFUSED"),
        ("refuse", "  egress: refuse\n", "refuse"),
        ("deny", "  egress: deny\n", "deny"),
        ("true", "  egress: true\n", True),
        ("false", "  egress: false\n", False),
        ("0", "  egress: 0\n", 0),
        ("null", "  egress: null\n", None),
        ("empty string", '  egress: ""\n', ""),
        ("mapping", "  egress:\n    a: b\n", {"a": "b"}),
        ("list", "  egress:\n  - a\n  - b\n", ["a", "b"]),
    ]

    @pytest.mark.parametrize(
        "label,egress_line,_expected_raw",
        NEAR_MISS_FAULTS,
        ids=[c[0] for c in NEAR_MISS_FAULTS],
    )
    def test_fault_message_names_offending_value_and_both_legal_values(
        self, tmp_path: Path, label: str, egress_line: str, _expected_raw: object
    ) -> None:
        root = tmp_path / f"fault-{label.replace(' ', '_')}"
        _write_config(root, "tracker:\n" + egress_line)
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            assert verdict.refused is True, f"{label} must refuse at {destination}"
            assert verdict.channel2_state == CHANNEL2_FAULT
            assert "refused" in verdict.message
            assert "permitted" in verdict.message
            assert str(_expected_raw) in verdict.message or repr(_expected_raw) in verdict.message

    def test_message_is_never_recomposed_it_equals_the_composition_helper(self, tmp_path: Path) -> None:
        """No path-local message strings: the verdict's message equals what the module's own
        composition helper produces for the same inputs.

        Recomputes against the *real* Channel-1 answer for this root (rather than assuming
        one) so the assertion cannot pass by coincidence.
        """
        root = tmp_path / "refused-both"
        _write_config(root, "tracker:\n  egress: refused\n")
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            channel1_permits, channel1_refusal_text, _channel1_state, _channel1_generic = _resolve_channel1(
                root, _IDENTIFIERS_FOR[destination]
            )
            expected = _channel2_decided_message(
                destination=destination,
                channel2_state="refused",
                channel2_raw="refused",
                channel1_permits=channel1_permits,
                channel1_refusal_text=channel1_refusal_text,
            )
            assert verdict.message == expected

    def test_permit_message_matches_composition_helper(self, tmp_path: Path) -> None:
        root = _not_consentable_root(tmp_path)
        _with_tracker_egress(root, "  egress: permitted\n")
        verdict = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS])
        assert verdict.message == _permit_message(EgressDestination.LOCAL_SUBPROCESS)

    def test_local_subprocess_message_offers_the_channel2_grant_remedy(self, tmp_path: Path) -> None:
        root = _no_record_root(tmp_path)
        verdict = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS])
        assert verdict.refused is True
        assert any("tracker.egress: 'permitted'" in r or "permitted" in r for r in verdict.remedies)

    def test_hosted_channel1_refusal_is_byte_identical_to_the_shipped_text(self, tmp_path: Path) -> None:
        """FR-016: the hosted gate's Channel-1 refusal text is the **shipped** `#3030` string,
        byte for byte, with no recomposition and no added note.

        Supersedes an earlier pin here that required a prospective "would not apply" note on
        this cell. That note was review round 1's MEDIUM-2 fix, and WP05 measured that it
        *changed operator-visible text on a path `#3030` already shipped* -- which FR-016
        forbids in terms: "A Mission that closes the local gap while perturbing the shipped
        hosted gate has traded one leak for another." Operator decision: FR-016 wins.

        MEDIUM-2's actual complaint is still answered, and more cleanly. Its defect was that
        the absent case asserted a *recorded* grant the operator does not have. Passing the
        shipped text through means the absent case now says nothing at all about a key that is
        not there, while a genuinely recorded grant still gets ``_HOSTED_GRANT_NOTE_RECORDED``
        (pinned below). Neither message asserts an untruth, and they remain plainly distinct.
        """
        root = _no_record_root(tmp_path)
        verdict = tracker_egress_verdict(root, destination=EgressDestination.HOSTED_SERVICE, identifiers=_IDENTIFIERS_FOR[EgressDestination.HOSTED_SERVICE])
        assert verdict.refused is True
        assert verdict.message == project_egress_refusal(root, TRACKER_EGRESS_IDENTIFIER_KINDS), (
            "FR-016: the hosted Channel-1 refusal must be `project_egress_refusal`'s own string, verbatim"
        )
        # The recomposition and the prospective note are both gone from this cell.
        assert "would not apply" not in verdict.message
        assert not verdict.message.startswith(CHANNEL_1)

    def test_hosted_channel1_refusal_matches_the_shipped_bytes_literally(self, tmp_path: Path) -> None:
        """The literal half of FR-016 (WP05 review, MEDIUM-2).

        The pin above compares the verdict against ``project_egress_refusal`` *at runtime*, so
        it proves **passthrough** -- exactly the property the amendment is about -- but both
        sides move together if that function is ever reworded, and byte-identity with what
        `#3030` shipped would break silently. No literal pin on this text existed anywhere in
        the tree (`#3030`'s own suite asserts ``error_code`` and one substring), so the claim
        was stronger than its evidence. This is that evidence.
        """
        root = _no_record_root(tmp_path, name="shipped-bytes")
        verdict = tracker_egress_verdict(root, destination=EgressDestination.HOSTED_SERVICE, identifiers=_IDENTIFIERS_FOR[EgressDestination.HOSTED_SERVICE])
        assert verdict.message == (
            f"the project at {root} has not consented to hosted sync, so its mission and "
            "engagement identifiers must not be transmitted; record a decision in the "
            "project's own .kittify/config.yaml (sync.enabled) or run `spec-kitty sync "
            "opt-in` for it"
        )

    def test_hosted_recorded_grant_still_gets_the_noop_note(self, tmp_path: Path) -> None:
        """The recorded-grant cell is **not** one of FR-016's three measured outcomes (all of
        which are Channel-2-absent), so it keeps the no-op note. Saying nothing there would
        leave the operator believing their key did something -- FR-005's named failure."""
        recorded_root = _no_record_root(tmp_path, name="recorded-grant-note")
        _with_tracker_egress(recorded_root, "  egress: permitted\n")
        recorded_verdict = tracker_egress_verdict(
            recorded_root,
            destination=EgressDestination.HOSTED_SERVICE,
            identifiers=_IDENTIFIERS_FOR[EgressDestination.HOSTED_SERVICE],
        )
        assert "recorded" in recorded_verdict.message
        assert "no-op" in recorded_verdict.message

        # ...and the absent cell is still plainly distinct from it, which is what MEDIUM-2 asked
        # for -- now by carrying no note at all rather than by carrying a different one.
        absent_root = _no_record_root(tmp_path, name="absent-grant-note")
        absent_verdict = tracker_egress_verdict(
            absent_root,
            destination=EgressDestination.HOSTED_SERVICE,
            identifiers=_IDENTIFIERS_FOR[EgressDestination.HOSTED_SERVICE],
        )
        assert "no-op" not in absent_verdict.message
        assert absent_verdict.message != recorded_verdict.message

    def test_recorded_refusal_and_not_consentable_have_distinct_wording(self, tmp_path: Path) -> None:
        refusal_root = _recorded_refusal_root(tmp_path)
        not_consentable_root = _not_consentable_root(tmp_path)
        refusal_verdict = tracker_egress_verdict(
            refusal_root,
            destination=EgressDestination.LOCAL_SUBPROCESS,
            identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS],
        )
        not_consentable_verdict = tracker_egress_verdict(
            not_consentable_root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS]
        )
        assert refusal_verdict.message != not_consentable_verdict.message
        assert refusal_verdict.channel1_state == CHANNEL1_RECORDED_REFUSAL
        assert not_consentable_verdict.channel1_state == CHANNEL1_NOT_CONSENTABLE


# ---------------------------------------------------------------------------
# T020 -- the never-raises contract (24 cases) and the quality gates
# ---------------------------------------------------------------------------


def _shape_unreadable(tmp_path: Path) -> Path:
    root = tmp_path / "shape-unreadable"
    config_path = _write_config(root, "tracker:\n  egress: refused\n")
    if os.geteuid() != 0:
        config_path.chmod(0o000)
    return root


def _shape_unparseable(tmp_path: Path) -> Path:
    root = tmp_path / "shape-unparseable"
    config_path = root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("tracker: [unclosed\n  egress: refused\n", encoding="utf-8")
    return root


def _shape_wrong_shape(tmp_path: Path) -> Path:
    root = tmp_path / "shape-wrong-shape"
    config_path = root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("- a\n- b\n", encoding="utf-8")
    return root


def _shape_tracker_non_mapping(tmp_path: Path) -> Path:
    root = tmp_path / "shape-tracker-non-mapping"
    _write_config(root, "tracker: yes\n")
    return root


def _shape_mapping_at_egress_key(tmp_path: Path) -> Path:
    root = tmp_path / "shape-mapping-at-key"
    _write_config(root, "tracker:\n  egress:\n    a: b\n")
    return root


def _shape_list_at_egress_key(tmp_path: Path) -> Path:
    root = tmp_path / "shape-list-at-key"
    _write_config(root, "tracker:\n  egress:\n  - a\n  - b\n")
    return root


def _shape_empty_file(tmp_path: Path) -> Path:
    root = tmp_path / "shape-empty-file"
    config_path = root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("", encoding="utf-8")
    return root


def _shape_comments_only(tmp_path: Path) -> Path:
    root = tmp_path / "shape-comments-only"
    config_path = root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("# just a comment\n# another\n", encoding="utf-8")
    return root


def _shape_chmod_000(tmp_path: Path) -> Path:
    root = tmp_path / "shape-chmod-000"
    config_path = _write_config(root, "tracker:\n  egress: permitted\n")
    if os.geteuid() != 0:
        config_path.chmod(0o000)
    return root


def _shape_absent_file(tmp_path: Path) -> Path:
    root = tmp_path / "shape-absent-file"
    (root / ".kittify").mkdir(parents=True)
    return root


def _shape_repo_root_not_a_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "shape-not-a-project-root"
    root.mkdir(parents=True)
    return root


def _shape_unreadable_kittify_dir(tmp_path: Path) -> Path:
    """HIGH-1 regression (review round 1): an unreadable **enclosing directory**, not an
    unreadable file. ``load_tracker_config``'s ``if not config_path.exists(): ...`` pre-check
    runs *ahead of* its own guarded open/parse block, and ``Path.exists()`` re-raises
    ``PermissionError`` (``EACCES`` is not in pathlib's ``_ignore_error`` set) rather than
    swallowing it -- so this shape reached a bare ``PermissionError`` straight out of
    ``_resolve_channel2`` on the pre-fix code, which caught only ``TrackerConfigError``."""
    root = tmp_path / "shape-unreadable-kittify-dir"
    _write_config(root, "tracker:\n  egress: refused\n")
    if os.geteuid() != 0:
        (root / ".kittify").chmod(0o000)
    return root


def _restore_permissions(root: Path) -> None:
    """Undo whatever a shape builder chmod'd, so pytest's own ``tmp_path`` teardown can walk
    and remove the tree. Order matters: the directory must be restored before its children are
    reachable again."""
    with contextlib.suppress(Exception):
        (root / ".kittify").chmod(0o755)
    config_path = root / ".kittify" / "config.yaml"
    if config_path.exists():
        with contextlib.suppress(Exception):
            config_path.chmod(0o644)


# 12 shapes; ``root=None`` is handled specially since it has no tmp_path-built fixture.
_FILE_LEVEL_SHAPES: list[tuple[str, Callable[[Path], Path]]] = [
    ("unreadable", _shape_unreadable),
    ("unreadable-kittify-dir", _shape_unreadable_kittify_dir),
    ("unparseable", _shape_unparseable),
    ("wrong-shape", _shape_wrong_shape),
    ("tracker-non-mapping", _shape_tracker_non_mapping),
    ("mapping-at-egress-key", _shape_mapping_at_egress_key),
    ("list-at-egress-key", _shape_list_at_egress_key),
    ("empty-file", _shape_empty_file),
    ("comments-only", _shape_comments_only),
    ("chmod-000", _shape_chmod_000),
    ("absent-file", _shape_absent_file),
    ("repo-root-not-a-project-root", _shape_repo_root_not_a_project_root),
]


class TestNeverRaises:
    @pytest.mark.parametrize("shape_name,builder", _FILE_LEVEL_SHAPES, ids=[s[0] for s in _FILE_LEVEL_SHAPES])
    @pytest.mark.parametrize("destination", DESTINATIONS, ids=["local_subprocess", "hosted_service"])
    def test_twelve_file_level_shapes_never_raise(
        self,
        tmp_path: Path,
        shape_name: str,
        builder: Callable[[Path], Path],
        destination: EgressDestination,
    ) -> None:
        root = builder(tmp_path)
        try:
            verdict = tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
        finally:
            _restore_permissions(root)
        assert isinstance(verdict, TrackerEgressVerdict)
        assert isinstance(verdict.refused, bool)

    @pytest.mark.parametrize("destination", DESTINATIONS, ids=["local_subprocess", "hosted_service"])
    def test_root_none_never_raises(self, destination: EgressDestination) -> None:
        verdict = tracker_egress_verdict(None, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
        assert isinstance(verdict, TrackerEgressVerdict)
        assert verdict.refused is True

    def test_never_raises_ran_exactly_26_cases(self, tmp_path: Path) -> None:
        """The full enumeration in one place: 12 shapes x 2 destinations + 2 (``root=None``) =
        26, counted and printed rather than assumed from the parametrisation above. Raised from
        24 to 26 in review round 1 (HIGH-1): the unreadable-``.kittify``-directory shape is a
        12th file-level shape, distinct from "unreadable" (an unreadable *file*), so the
        file-level count grew from 11 to 12."""
        ran = 0
        for shape_name, builder in _FILE_LEVEL_SHAPES:
            for destination in DESTINATIONS:
                root = builder(tmp_path / f"count-{shape_name}-{destination.value}")
                try:
                    verdict = tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
                except Exception as exc:  # pragma: no cover - the failure this test exists to catch
                    pytest.fail(f"{shape_name}/{destination}: raised {type(exc).__name__}: {exc}")
                else:
                    assert isinstance(verdict, TrackerEgressVerdict)
                finally:
                    _restore_permissions(root)
                ran += 1
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(None, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            assert isinstance(verdict, TrackerEgressVerdict)
            ran += 1
        print(f"never-raises contract: ran {ran} cases")
        assert ran == 26

    def test_never_propagates_trackerconfigerror(self, tmp_path: Path) -> None:
        root = _shape_unparseable(tmp_path)
        for destination in DESTINATIONS:
            try:
                tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            except TrackerConfigError:
                pytest.fail("TrackerConfigError must never propagate out of tracker_egress_verdict")


# ---------------------------------------------------------------------------
# Exhaustiveness / two-site-change pin (WP02 reviewer addendum)
# ---------------------------------------------------------------------------


class TestChannel1StateLiterals:
    """LOW-6 (review round 2): pin the six ``channel1_state`` literals by *value*.

    This closes the only mutant that survived the round-2 battery. Every other assertion in
    this file compares ``verdict.channel1_state`` against the module constant, so collapsing a
    constant's value (``CHANNEL1_GRANTED = CHANNEL1_NO_RECORD``) moved both sides of every
    comparison together and the whole suite stayed green.

    The values are a contract, not an implementation detail: WP06 renders them, a ``--json``
    surface would expose them verbatim, and a collapsed ``granted`` would leak the token
    ``no record`` into output for a project that *has* consented -- which WP01's harness pins
    negatively. Same reasoning as Channel 2's spelling being pinned in ``tracker/config.py``.
    """

    def test_six_literals_are_exactly_as_specified(self) -> None:
        assert (
            CHANNEL1_GRANTED,
            CHANNEL1_NO_RECORD,
            CHANNEL1_RECORDED_REFUSAL,
            CHANNEL1_NOT_CONSENTABLE,
            CHANNEL1_UNCLASSIFIED,
            CHANNEL1_UNDETERMINED,
        ) == ("granted", "no_record", "recorded_refusal", "not_consentable", "unclassified", "undetermined")

    def test_six_literals_are_mutually_distinct(self) -> None:
        """A collapse is the specific failure this guards: two states sharing one value would
        make the verdict's reported state ambiguous while every constant-vs-constant assertion
        in this file still passed."""
        states = [
            CHANNEL1_GRANTED,
            CHANNEL1_NO_RECORD,
            CHANNEL1_RECORDED_REFUSAL,
            CHANNEL1_NOT_CONSENTABLE,
            CHANNEL1_UNCLASSIFIED,
            CHANNEL1_UNDETERMINED,
        ]
        assert len(set(states)) == 6, f"channel1_state literals collapsed: {states}"  # golden-count: cardinality-is-contract

    def test_granted_does_not_contain_the_negatively_pinned_no_record_token(self) -> None:
        """WP01 asserts ``"no record" not in output`` for non-no-record states, so the granted
        label must not carry that token even as a substring."""
        assert "no record" not in CHANNEL1_GRANTED.replace("_", " ")
        assert "no record" not in CHANNEL1_RECORDED_REFUSAL.replace("_", " ")


class TestUnreadableSentinelRepr:
    """LOW-5 regression (review round 1): the unreadable-config sentinel is reachable from the
    public ``channel2_raw`` field, so it must not print as a bare ``object()`` repr."""

    def test_repr_is_legible(self) -> None:
        from specify_cli.tracker.egress_verdict import _UNREADABLE

        assert repr(_UNREADABLE) == "<tracker config unreadable>"
        assert "object object at 0x" not in repr(_UNREADABLE)

    def test_reachable_from_channel2_raw_on_an_unreadable_kittify_dir(self, tmp_path: Path) -> None:
        if os.geteuid() == 0:
            pytest.skip("root bypasses file permission checks")
        root = tmp_path / "unreadable-repr-check"
        _write_config(root, "tracker:\n  egress: refused\n")
        (root / ".kittify").chmod(0o000)
        try:
            verdict = tracker_egress_verdict(root, destination=EgressDestination.LOCAL_SUBPROCESS, identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS])
        finally:
            (root / ".kittify").chmod(0o755)
        assert repr(verdict.channel2_raw) == "<tracker config unreadable>"


class TestExhaustivenessOverLegalValues:
    def test_a_third_value_added_upstream_without_updating_this_module_still_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Simulates the two-site-change hazard: a hypothetical third legal value is added to
        ``tracker/config.py``'s ``_EGRESS_LEGAL_VALUES`` (so ``egress_fault`` there reports
        "not a fault"), but this module's own ``_LEGAL_CHANNEL2_VALUES``/``_JOIN`` are not
        updated to match. The verdict must still refuse -- not silently permit."""
        monkeypatch.setattr(
            tracker_config,
            "_EGRESS_LEGAL_VALUES",
            frozenset({"refused", "permitted", "draft"}),
        )
        root = tmp_path / "future-third-value"
        _write_config(root, "tracker:\n  egress: draft\n")

        # Upstream (config.py) now considers "draft" legal -- not a fault.
        config = tracker_config.load_tracker_config(root)
        assert config.egress_fault is False, "the patch must make config.py consider it legal"

        # This module was not updated to know about "draft"; it must still refuse.
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            assert verdict.refused is True, "an unmapped-here value must refuse, never silently permit"
            assert verdict.channel2_state == CHANNEL2_FAULT


# ---------------------------------------------------------------------------
# Zero blast radius / no call sites created
# ---------------------------------------------------------------------------


class TestZeroBlastRadius:
    #: Expected number of real ``tracker_egress_verdict`` **call sites** per file, and the WP
    #: that wires each. WP04 has landed three (``sync_pull``/``sync_push``/``sync_run``);
    #: WP05 adds ``saas_client.py``; WP06 adds ``cli/commands/sync.py`` for ``sync doctor``.
    #: ``cli/commands/tracker.py`` gained **one** direct call site at the 2026-08-10 landing
    #: pass (PR #3135, HIGH-1 / #3108 follow-up): ``_check_sync_readiness`` consults the hosted
    #: verdict ahead of the readiness network probe so "refusal precedes any HTTP attempt" holds
    #: at the CLI pre-flight, not only inside ``SaaSTrackerClient._request``. It also *mentions*
    #: the symbol in amended docstrings, which is why this pin counts AST nodes rather than
    #: substrings (see the docstring below). Kept in step with G4's census in
    #: ``tests/architectural/test_tracker_egress_guards_3108.py`` (6 enclosing / 7 expressions).
    _EXPECTED_CALL_SITES: ClassVar[dict[str, int]] = {
        "src/specify_cli/tracker/local_service.py": 3,  # WP04, landed: pull, push, run
        "src/specify_cli/tracker/saas_client.py": 1,  # WP05, landed: _request
        "src/specify_cli/cli/commands/tracker.py": 1,  # PR #3135 HIGH-1: _check_sync_readiness pre-flight
        "src/specify_cli/cli/commands/sync.py": 2,  # WP06, landed: one per destination
    }

    @staticmethod
    def _count_call_sites(source: str) -> int:
        """Count real calls to ``tracker_egress_verdict``, resolving **both** ``ast.Name`` and
        ``ast.Attribute`` func nodes -- a module-qualified ``ev.tracker_egress_verdict(...)``
        defeated an earlier guard in this very mission, so a matcher that resolves only bare
        names is known-insufficient here."""
        tree = ast.parse(source)
        return sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                getattr(node.func, "id", None) == "tracker_egress_verdict"
                or getattr(node.func, "attr", None) == "tracker_egress_verdict"
            )
        )

    def test_production_call_sites_are_exactly_the_expected_inventory(self) -> None:
        """The call-site inventory is exactly what the mission has wired so far.

        Originally ``test_module_has_no_production_callers_yet``, asserting *zero* callers --
        true when WP03 was approved, and made false **by design** the moment WP04 wired the
        local gate. Amended by the mission owner rather than by WP04, which correctly declined
        to edit an approved file to make its own change look clean.

        The rewrite is strictly stronger than a "not yet" snapshot. It catches the real hazard
        -- an **unaudited** file calling the verdict, anywhere under ``src/`` -- and it also
        asserts the expected wiring is *present* and *complete*, so a WP that wires one entry
        point and silently skips another (a gate on ``sync_push`` but not
        ``sync_pull``/``sync_run``) reds here instead of passing. Each landing WP updates its
        own count.

        **It counts AST call nodes, not substrings.** The first draft of this pin matched text
        and immediately mis-flagged ``cli/commands/tracker.py``, whose two amended docstrings
        *mention* the symbol without importing or calling it -- the same mention-versus-does
        confusion that a substring matcher always makes and that this mission has already been
        bitten by once.

        Authoritative guards (G4 counts the sites, G5 pins ``destination`` as a caller-supplied
        literal) land in WP07 and supersede this pin; until then this is the only thing
        watching the inventory.
        """
        repo_root = Path(__file__).resolve().parents[3]

        # Every file in the inventory must still exist, or an expectation is silently unpinned.
        for rel in self._EXPECTED_CALL_SITES:
            assert (repo_root / rel).exists(), f"{rel} must exist for this pin to mean anything"

        # Sweep all of src/ rather than only the inventory's own keys. The first draft iterated
        # the four expected paths, so a *fifth* file calling the verdict was invisible to it --
        # which is precisely the "unaudited caller" hazard this pin claims to catch (review of
        # WP04, LOW-2). Scanning everything makes the claim true instead of aspirational.
        scanned = 0
        observed: dict[str, int] = {}
        for path in sorted((repo_root / "src").rglob("*.py")):
            scanned += 1
            try:
                count = self._count_call_sites(path.read_text(encoding="utf-8"))
            except SyntaxError:  # a file that does not parse cannot be calling anything
                continue
            if count:
                observed[path.relative_to(repo_root).as_posix()] = count

        expected = {rel: n for rel, n in self._EXPECTED_CALL_SITES.items() if n}
        print(f"call-site inventory: scanned {scanned} src files, {sum(observed.values())} call sites in {len(observed)}")
        assert scanned > 100, f"the sweep must actually have walked src/ (scanned {scanned})"
        assert observed == expected, (
            f"call-site inventory drifted: observed {observed}, expected {expected}. "
            "A newly-wired gate must update its own count; a caller outside the inventory is a finding."
        )

    def test_the_landed_local_gate_is_a_positive_control(self) -> None:
        """Non-vacuity: the inventory must assert some real wiring, or it would pass against a
        tree where no gate was ever wired at all."""
        assert sum(self._EXPECTED_CALL_SITES.values()) > 0, "the inventory must assert real wiring"

    def test_the_matcher_resolves_qualified_calls(self) -> None:
        """The counter itself must not be blind to its subject (mission hazard: a
        module-qualified sixth call site once passed two guards while the input count rose).

        Also pins the mention-versus-call distinction that the substring draft got wrong.
        """
        assert self._count_call_sites("x = tracker_egress_verdict(r, destination=d)\n") == 1
        assert self._count_call_sites("x = ev.tracker_egress_verdict(r, destination=d)\n") == 1
        assert self._count_call_sites("x = a.b.tracker_egress_verdict(r, destination=d)\n") == 1
        assert self._count_call_sites('"""prose naming tracker_egress_verdict only."""\n') == 0
        assert self._count_call_sites("from m import tracker_egress_verdict\n") == 0
