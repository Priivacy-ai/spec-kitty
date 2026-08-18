"""Frozen corpus fixture + non-vacuous shrink-only ratchet (#3396, WP08 T037-T040).

``find_bare_prose_requirement_ids`` (``src/specify_cli/requirement_mapping.py``)
is a detector, and per this mission's own founding defect class (a detector
that "counts 0 and calls it clean" is a silent-success failure), the detector
needs a regression net that CANNOT itself be silently green. This module is
that net.

**Frozen snapshot, not a live re-run (charter Standing Order 5 /
``frozen-baseline-shrink-only-ratchet``).** ``tests/fixtures/
bare_prose_corpus_baseline.json`` is a committed, point-in-time snapshot of
the live detector's output against the ``kitty-specs/*/spec.md`` corpus,
re-verified at this WP's implementation time (2026-08-14): ``N=368`` specs
scanned, ``1`` flagged (``kitty-specs/egress-refusal-consolidation-3110-
01KYW895/spec.md``, ids ``C-1``/``C-3`` -- a foreign-id citation, zero true
positives; see ``find_bare_prose_requirement_ids``'s own module docstring for
the full measurement record). This test module deliberately never
recomputes "1/368" or any percentage at CI time -- it only asks, per spec
path: did the flagged *set* grow, and is it still non-empty where the
fixture says it should be. A future, unrelated mission's new
``kitty-specs/*/spec.md`` cannot flip this gate red merely by existing
(assertion 1 passes vacuously for a spec with no bare-prose token); only a
*regression in the detector itself*, or a *newly bare-prose spec*, can.

Four assertions close the non-vacuity gap (PLAN-VERIFY-001 /
``architectural-gate-non-vacuity``) that a shrink-only-allowlist ratchet
alone would leave open -- a fully-collapsed, always-empty detector would
pass a bare subset/no-growth check trivially, reproducing inside this
mission's own regression net the exact silent-success class the mission
exists to fix:

1. **No growth** (``test_specs_outside_the_fixture_have_no_live_bare_prose_ids``):
   every spec NOT in the fixture has an empty live result.
2. **Shrink-or-equal, never grow** (``test_fixture_specs_live_ids_never_exceed_recorded``):
   every spec IN the fixture has a live ``flagged_ids`` result that is a
   subset of (or equal to) its recorded set.
3. **Concrete floor** (``test_fixture_specs_live_result_is_non_empty``): for
   each fixture spec, the live result is non-empty -- this is what a
   collapsed, always-``[]`` detector would fail, where it would pass (1)+(2)
   vacuously.
4. **Self-mutation teeth test**
   (``test_ratchet_fails_when_detector_is_stubbed_to_always_return_empty``):
   stubs the detector to always return ``[]`` and asserts assertion 3 above
   then FAILS (a real ``AssertionError``, not an error or a skip) --
   proving the gate is load-bearing, not merely present.

Growing the fixture requires editing ``tests/fixtures/
bare_prose_corpus_baseline.json`` in the same PR with a recorded reason,
mirroring ``tests/architectural/_baselines.yaml``'s per-PR edit policy
(read directly as this module's precedent) -- adapted from a bare integer
ceiling to a per-spec **signature**, since a bare count cannot distinguish
"the same specs are still flagged" from "different specs are now flagged".

This test walks the real, on-disk ``kitty-specs/*/spec.md`` corpus at run
time (read-only; no network access, no corpus writes) -- it therefore also
carries ``pytest.mark.corpus`` (registered in
``tests/architectural/test_ci_corpus_trigger_completeness.py``'s curated
module registry) so a corpus-only change (a new/edited ``spec.md`` with no
code change) still re-runs this gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.requirement_mapping import find_bare_prose_requirement_ids
from tests.utils import REPO_ROOT

pytestmark = [pytest.mark.architectural, pytest.mark.corpus]

_FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "bare_prose_corpus_baseline.json"


def _load_fixture() -> list[dict[str, Any]]:
    """Load and structurally validate the committed corpus baseline."""
    data = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError(f"{_FIXTURE_PATH} must contain a JSON array; got {type(data).__name__}")
    for entry in data:
        if not isinstance(entry, dict) or "spec_path" not in entry or "flagged_ids" not in entry:
            raise ValueError(
                f"{_FIXTURE_PATH}: every entry must be an object with "
                f"'spec_path' and 'flagged_ids' keys; got {entry!r}"
            )
    return data


def _corpus_spec_paths() -> list[Path]:
    """Every ``kitty-specs/*/spec.md`` in the live corpus, repo-root-relative."""
    return sorted(REPO_ROOT.glob("kitty-specs/*/spec.md"))


def _live_flagged_ids(spec_path: Path) -> list[str]:
    """The live detector's flagged ids for one spec, deduplicated, order-stable."""
    content = spec_path.read_text(encoding="utf-8")
    candidates = find_bare_prose_requirement_ids(content)
    ids: list[str] = []
    for candidate in candidates:
        for requirement_id in candidate.ids:
            if requirement_id not in ids:
                ids.append(requirement_id)
    return ids


def test_fixture_file_exists_and_is_well_formed() -> None:
    """Sanity gate: the committed fixture parses and every recorded path exists."""
    fixture = _load_fixture()
    assert fixture, "the corpus baseline fixture must not be empty for a corpus with real hits"
    missing = [entry["spec_path"] for entry in fixture if not (REPO_ROOT / entry["spec_path"]).is_file()]
    assert not missing, f"fixture entries name spec.md path(s) that no longer exist: {missing}"


def test_specs_outside_the_fixture_have_no_live_bare_prose_ids() -> None:
    """Assertion (1): no spec outside the fixture is newly flagged live."""
    fixture_paths = {entry["spec_path"] for entry in _load_fixture()}
    newly_flagged: list[str] = []
    for spec_path in _corpus_spec_paths():
        rel = spec_path.relative_to(REPO_ROOT).as_posix()
        if rel in fixture_paths:
            continue
        live_ids = _live_flagged_ids(spec_path)
        if live_ids:
            newly_flagged.append(f"{rel}: {live_ids}")
    assert not newly_flagged, (
        "The following spec(s) are flagged by the live detector but are NOT in "
        "tests/fixtures/bare_prose_corpus_baseline.json -- this is growth above "
        "the frozen baseline. If these are genuine new bare-prose requirements, "
        "add a fixture entry (with a recorded reason) in the same PR; if this is "
        "a detector regression, fix the detector instead:\n"
        + "\n".join(newly_flagged)
    )


def test_fixture_specs_live_ids_never_exceed_recorded() -> None:
    """Assertion (2): the live result for a fixture spec never grows past its
    recorded signature -- shrink or stay equal only, never a superset."""
    growth: list[str] = []
    for entry in _load_fixture():
        spec_path = REPO_ROOT / entry["spec_path"]
        recorded_ids = set(entry["flagged_ids"])
        live_ids = set(_live_flagged_ids(spec_path))
        if not live_ids <= recorded_ids:
            growth.append(
                f"{entry['spec_path']}: recorded={sorted(recorded_ids)} "
                f"live={sorted(live_ids)} (new: {sorted(live_ids - recorded_ids)})"
            )
    assert not growth, (
        "The following fixture spec(s) now flag id(s) NOT in the recorded "
        "signature -- growth above the frozen baseline. Re-snapshot "
        "tests/fixtures/bare_prose_corpus_baseline.json with a recorded reason "
        "if this growth is genuine, or fix the detector regression:\n"
        + "\n".join(growth)
    )


def _assert_fixture_specs_have_non_empty_live_result() -> None:
    """Assertion (3), the concrete-floor check, factored out so the teeth test
    (assertion 4) can re-invoke it under a stubbed detector and assert it goes
    RED -- proving this floor is load-bearing, not merely present."""
    empty: list[str] = []
    for entry in _load_fixture():
        spec_path = REPO_ROOT / entry["spec_path"]
        if not _live_flagged_ids(spec_path):
            empty.append(entry["spec_path"])
    assert not empty, (
        "The following fixture spec(s) have an EMPTY live result -- a "
        "fully-collapsed, always-'[]' detector would pass the shrink-only "
        "checks above vacuously (empty is a subset of any recorded set); this "
        "concrete floor is what catches that silent-success class:\n"
        + "\n".join(empty)
    )


def test_fixture_specs_live_result_is_non_empty() -> None:
    """Assertion (3): the non-vacuity floor -- see
    :func:`_assert_fixture_specs_have_non_empty_live_result`."""
    _assert_fixture_specs_have_non_empty_live_result()


def test_ratchet_fails_when_detector_is_stubbed_to_always_return_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assertion (4), the self-mutation ("teeth") test.

    Stubs ``find_bare_prose_requirement_ids`` (as imported into this module)
    to always return ``[]`` and asserts the concrete-floor check above then
    fails with a real ``AssertionError`` -- not an error, not a skip. This is
    the load-bearing proof (charter Standing Order 5 / PLAN-VERIFY-001) that
    the gate above is not vacuous: a detector that regresses to
    always-empty WILL turn this suite red.
    """
    module_globals = globals()
    monkeypatch.setitem(
        module_globals,
        "find_bare_prose_requirement_ids",
        lambda _spec_content: [],
    )
    with pytest.raises(AssertionError, match="EMPTY live result"):
        _assert_fixture_specs_have_non_empty_live_result()
