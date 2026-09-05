"""Behavioral pin for FR-004's discrimination-control gate.

Mission skill-trigger-routing-suite-01KYVRB9, WP03/WP04. The gate script
(``conformance/scripts/check-control-discrimination.mjs``) shipped with no
test of its own; every proof of its behavior lived in a commit message. This
file is that proof, re-expressed as something a CI gate selects.

Like ``test_check_sop_extract_drift.py`` (this directory's existing
convention for pinning a conformance script), everything here runs the REAL
script via ``node`` against report files built in ``tmp_path`` — never
against a mocked-out reimplementation of its logic.

The base input is a GENUINE live capture of ``muster skills run
<manifest> --json`` (``tests/fixtures/skill_trigger_routing/
report-healthy-live.json``, gpt-4o-mini via api.openai.com, the same suite
and the same shape as the committed evidence artifact under
``conformance/skills/trigger-evidence/``). Each rejection case is a
MUTATION of that real report, so the healthy direction is never proven with
a hand-built "healthy" fixture.

What this pins:

- the real healthy control (shouldTrigger 0.083 / nearMiss 0.000) is
  accepted in ``--mode healthy`` (exit 0);
- a PERMANENTLY-TRIGGERING control — a model that calls the single offered
  tool on every query — is REJECTED (exit 1). This is the vacuity this
  suite's own control exists to catch, and the one the first implementation
  of the gate accepted: muster computes ``passed = shouldTriggerAxis.passed
  && nearMissAxis.passed`` over two axes with opposite predicates on the
  same rate, so rate 1.0 yields ``passed: false, runsErrored: 0`` — byte
  for byte the shape of a healthy discriminating run;
- a control that ``passed: true`` is rejected (exit 1);
- a report with no ``isControl`` case is rejected (exit 2);
- a dead-endpoint report is accepted in ``--mode dead-endpoint`` and
  rejected in ``--mode healthy``, and vice versa.

Gate routing: ``tests/cross_cutting/**`` is already routed to ci-quality's
``e2e`` path filter, so the ``e2e-cross-cutting`` job selects this file on
every push and on any PR touching ``tests/**``. Residual gap, inherited from
``test_check_sop_extract_drift.py`` and not closed here: ``conformance/**``
is not in ci-quality's own trigger paths, so a PR that edits ONLY the
``.mjs`` script (and no test) does not re-run this file. Closing it means
routing ``conformance/scripts/**`` the way ``crosslayer.yml`` was routed
into the ``e2e`` filter.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.utils import REPO_ROOT

pytestmark = [pytest.mark.integration]

_SCRIPT = REPO_ROOT / "conformance" / "scripts" / "check-control-discrimination.mjs"
_LIVE_REPORT = REPO_ROOT / "tests" / "fixtures" / "skill_trigger_routing" / "report-healthy-live.json"


def _live_report() -> dict[str, Any]:
    return json.loads(_LIVE_REPORT.read_text(encoding="utf-8"))


#: The fixture's control case, pinned by IDENTITY rather than by count. A bare
#: ``len(controls) == 1`` is satisfied by any single control, so a fixture whose
#: control was swapped for a different (or accidentally passing) case still reads
#: as well-formed -- the failure mode this whole module exists to detect. Naming
#: the id makes the substitution a red.
_CONTROL_ID = "rigged-impossible-control"


def _control_case(report: dict[str, Any]) -> dict[str, Any]:
    controls = [c for c in report["results"] if c.get("isControl") is True]
    assert [c["id"] for c in controls] == [_CONTROL_ID], (
        f"fixture must carry exactly the control case {_CONTROL_ID!r}; "
        f"got {[c.get('id') for c in controls]!r}"
    )
    return controls[0]


def _write(tmp_path: Path, report: dict[str, Any], name: str = "report.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def _mutated_report(mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    """The real live report with ``mutate`` applied to its control case."""
    report = _live_report()
    mutate(_control_case(report))
    return report


def _regrade_axis(axis: dict[str, Any]) -> None:
    """Recompute an axis verdict exactly as muster does (trigger.ts:242-250,
    commit 16f0d34c3126fab5df2ee0b6e1e304a4d9bcb8e3 / tag v1.2.1):
    ``triggerRate = triggered / total`` (0 when there are no runs), with
    should-trigger passing on ``>= threshold`` and near-miss on ``<``.
    """
    total = sum(q["runsTotal"] for q in axis["queryBreakdown"])
    triggered = sum(q["runsTriggered"] for q in axis["queryBreakdown"])
    axis["triggerRate"] = triggered / total if total > 0 else 0
    if axis["axis"] == "should-trigger":
        axis["passed"] = axis["triggerRate"] >= axis["threshold"]
    else:
        axis["passed"] = axis["triggerRate"] < axis["threshold"]


def _regrade_case(case: dict[str, Any]) -> None:
    """Recompute the case verdict as muster does (trigger.ts:468, same SHA)."""
    _regrade_axis(case["shouldTriggerAxis"])
    _regrade_axis(case["nearMissAxis"])
    case["passed"] = case["shouldTriggerAxis"]["passed"] and case["nearMissAxis"]["passed"]


def _make_permanently_triggering(case: dict[str, Any]) -> None:
    """Every run on both axes calls the single offered tool, nothing errors."""
    for axis in (case["shouldTriggerAxis"], case["nearMissAxis"]):
        for query in axis["queryBreakdown"]:
            query["runsTriggered"] = query["runsTotal"]
            query["runsErrored"] = 0
    _regrade_case(case)


def _run(report_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(_SCRIPT), str(report_path), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_permanently_triggering_control_is_rejected(tmp_path: Path) -> None:
    """A model that triggers on EVERY query must not pass as a healthy control.

    Issue #25 §8, the reason FR-004's control exists at all: "a
    permanently-triggering model+prompt combination would look like a healthy
    suite". It looks healthy through ``passed``/``runsErrored`` alone —
    ``passed: false, runsErrored: 0``, identical to the real healthy run — so
    the gate must read the near-miss axis verdict, which is the only field
    that tells the two apart (near-miss rate 1.0 fails; the healthy run's
    0.000 passes).
    """
    report = _mutated_report(_make_permanently_triggering)
    control = _control_case(report)
    # Guard the fixture itself: this must be the deceptive shape, or the test
    # proves nothing.
    assert control["passed"] is False
    assert control["shouldTriggerAxis"]["triggerRate"] == 1.0
    assert control["nearMissAxis"]["triggerRate"] == 1.0
    assert control["nearMissAxis"]["passed"] is False

    result = _run(_write(tmp_path, report), "--mode", "healthy")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "near-miss" in result.stdout


def test_permanently_triggering_control_is_rejected_in_dead_endpoint_mode(
    tmp_path: Path,
) -> None:
    """The near-miss condition is mode-independent, so --mode dead-endpoint
    cannot be used as an escape hatch around it. A dead endpoint errors every
    run, which drives the near-miss rate to 0 and passes that axis — so
    requiring it costs the dead-endpoint proof nothing (see
    test_dead_endpoint_report_is_accepted_in_dead_endpoint_mode).
    """
    report = _mutated_report(_make_permanently_triggering)

    result = _run(_write(tmp_path, report), "--mode", "dead-endpoint")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "nearMissAxis.passed=false" in result.stdout


def test_real_healthy_control_is_accepted(tmp_path: Path) -> None:
    """The genuine live capture (should-trigger 0.083 / near-miss 0.000) passes.

    Uses the unmodified fixture: the accept direction must be proven with
    real measured data, never with a hand-built "healthy" report shaped to
    whatever the gate happens to check.
    """
    report = _live_report()
    control = _control_case(report)
    assert control["shouldTriggerAxis"]["triggerRate"] == pytest.approx(0.0833, abs=1e-3)
    assert control["nearMissAxis"]["triggerRate"] == 0

    result = _run(_write(tmp_path, report), "--mode", "healthy")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "shouldTriggerRate=0.083" in result.stdout
    assert "nearMissRate=0.000" in result.stdout


def test_control_that_passed_is_rejected(tmp_path: Path) -> None:
    """A control the model actually satisfied is not a control (pre-existing)."""

    def _mark_passed(case: dict[str, Any]) -> None:
        case["passed"] = True

    result = _run(_write(tmp_path, _mutated_report(_mark_passed)), "--mode", "healthy")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "passed=true" in result.stdout


def test_report_without_a_control_case_is_rejected(tmp_path: Path) -> None:
    """No isControl case means there is nothing to grade (pre-existing, exit 2)."""
    report = _live_report()
    report["results"] = [c for c in report["results"] if c.get("isControl") is not True]

    result = _run(_write(tmp_path, report), "--mode", "healthy")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "found 0" in result.stdout


def _make_dead_endpoint(case: dict[str, Any]) -> None:
    """Every run throws before it can trigger anything (muster#76)."""
    for axis in (case["shouldTriggerAxis"], case["nearMissAxis"]):
        for query in axis["queryBreakdown"]:
            query["runsTriggered"] = 0
            query["runsErrored"] = query["runsTotal"]
    _regrade_case(case)


def test_dead_endpoint_report_is_accepted_in_dead_endpoint_mode(tmp_path: Path) -> None:
    report = _mutated_report(_make_dead_endpoint)
    assert _control_case(report)["nearMissAxis"]["passed"] is True

    result = _run(_write(tmp_path, report), "--mode", "dead-endpoint")

    assert result.returncode == 0, result.stdout + result.stderr


def test_dead_endpoint_report_is_rejected_in_healthy_mode(tmp_path: Path) -> None:
    result = _run(_write(tmp_path, _mutated_report(_make_dead_endpoint)), "--mode", "healthy")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "expected 0" in result.stdout


def test_real_healthy_report_is_rejected_in_dead_endpoint_mode(tmp_path: Path) -> None:
    result = _run(_write(tmp_path, _live_report()), "--mode", "dead-endpoint")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "runsErrored=0" in result.stdout
