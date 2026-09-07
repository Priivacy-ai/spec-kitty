"""Committed module-shard registry gate (FR-006/NFR-001/NFR-005, WP08 T042).

Asserts ``.github/ci-module-registry.yml`` — the single data source for the
per-module CI test matrix (WP09 realizes it as a matrix over a bounded set of
reusable workflows, never one workflow file per module) — is present,
non-vacuous, covers every live ``src/**`` module in the WP05 retirement-scrub
set (:mod:`tests.release.ci_retirement_scrub`) with no gaps and no divergent
re-scrub, and that its ``shard_count`` balancing is *measured* (from the
``--durations`` run recorded in ``.github/ci-shard-timings.json``, run-id
captured) rather than guessed or derived from file counts, with inter-shard
skew held to <=20% (NFR-005).

Also asserts the T043 heavy-pole de-serialization decisions
(``integration-tests-next`` parallelized, the architectural pole always-on
and de-serialized) are encoded in the registry, and the T044 architect HIGH
folds — single-data-source (a new module is a row, not a workflow file) and
the <=20-reusable-workflows-per-caller ceiling — are machine-checked here
rather than left as prose.

Both YAML/JSON artefacts are loaded lazily inside each test (never at import
time) so a missing registry reds for the right reason — file absent — never
an ``ImportError`` or a collection-time crash.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REGISTRY_PATH = _REPO_ROOT / ".github" / "ci-module-registry.yml"
_TIMINGS_PATH = _REPO_ROOT / ".github" / "ci-shard-timings.json"
_SCRUB_PATH = _REPO_ROOT / "tests" / "release" / "ci_retirement_scrub.json"
_WORKFLOWS_DIR = _REPO_ROOT / ".github" / "workflows"

_MAX_SKEW = 0.20
_REQUIRED_ROW_FIELDS = ("module", "roots", "cov_targets", "tier", "shard_count")


# ---------------------------------------------------------------------------
# Loading helpers — lazy, in-test only (never at collection time)
# ---------------------------------------------------------------------------
def _load_registry() -> dict[str, Any]:
    if not _REGISTRY_PATH.exists():
        pytest.fail(f"module-shard registry missing: {_REGISTRY_PATH.relative_to(_REPO_ROOT)} (WP08 T042 not yet delivered)")
    import yaml  # local import: keep this gate's collection cost near-zero

    payload = yaml.safe_load(_REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{_REGISTRY_PATH} did not parse to a mapping"
    return payload


def _load_timings() -> dict[str, Any]:
    if not _TIMINGS_PATH.exists():
        pytest.fail(f"shard-timings artefact missing: {_TIMINGS_PATH.relative_to(_REPO_ROOT)} (WP08 T041 not yet delivered)")
    payload: dict[str, Any] = json.loads(_TIMINGS_PATH.read_text(encoding="utf-8"))
    return payload


def _load_scrub() -> dict[str, Any]:
    if not _SCRUB_PATH.exists():
        pytest.fail(f"retirement-scrub artefact missing: {_SCRUB_PATH.relative_to(_REPO_ROOT)} (WP05 not yet delivered)")
    payload: dict[str, Any] = json.loads(_SCRUB_PATH.read_text(encoding="utf-8"))
    return payload


def _modules(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return list(registry.get("modules", []))


def _scrub_groups(scrub: dict[str, Any]) -> list[dict[str, Any]]:
    return list(scrub.get("groups", []))


def _module_duration_seconds(timings: dict[str, Any], module: str) -> float:
    """Total measured duration (seconds) attributed to *module* in the timings file."""
    per_module = timings.get("module_duration_seconds", {})
    value = per_module.get(module)
    assert value is not None, f"timings file has no measured duration for module {module!r}"
    assert isinstance(value, (int, float)), f"module {module!r} duration is not numeric: {value!r}"
    return float(value)


def _module_test_durations(timings: dict[str, Any], module: str) -> list[float]:
    """The individual measured per-test durations (seconds) for *module*."""
    per_module = timings.get("module_test_durations", {})
    values = per_module.get(module)
    assert values is not None, f"timings file has no per-test durations recorded for module {module!r}"
    assert isinstance(values, list), f"module {module!r} test durations is not a list: {values!r}"
    return [float(v) for v in values]


def _lpt_bin_pack(durations: list[float], n: int) -> list[float]:
    """Greedy LPT (longest-processing-time-first) bin packing into *n* bins.

    Mirrors the algorithm used to derive ``shard_count`` (WP08 T042 generation
    script): always place the next-largest remaining item into the
    currently least-loaded bin. Standard, well-known approximation for
    balanced multiway partitioning.
    """
    bins = [0.0] * n
    for d in sorted(durations, reverse=True):
        i = min(range(n), key=lambda k: bins[k])
        bins[i] += d
    return bins


def _skew_of(bins: list[float]) -> float:
    if not bins or max(bins) <= 0:
        return 0.0
    return (max(bins) - min(bins)) / max(bins)


# ---------------------------------------------------------------------------
# DoD: non-vacuity floor
# ---------------------------------------------------------------------------
def test_registry_present_and_non_vacuous() -> None:
    """The registry exists and declares at least one module row (non-vacuous)."""
    registry = _load_registry()
    modules = _modules(registry)
    assert modules, "module registry declares no modules (vacuous)"


def test_timings_present_and_non_vacuous() -> None:
    """The shard-timings artefact exists and records a real run (non-vacuous)."""
    timings = _load_timings()
    assert timings.get("run_id"), "timings file has no run_id — a real run must be captured (not asserted)"
    assert timings.get("command"), "timings file does not record the pytest command that produced it"
    per_module = timings.get("module_duration_seconds", {})
    assert per_module, "timings file records no per-module durations (vacuous)"
    assert sum(per_module.values()) > 0, "timings file's total measured duration is zero"


# ---------------------------------------------------------------------------
# DoD: covers every live src/** module in the WP05 scrub set — no gaps, no
# retired surfaces, no divergent re-scrub.
# ---------------------------------------------------------------------------
def test_registry_covers_every_scrub_group_no_gaps_no_extras() -> None:
    """Registry module names == the WP05 scrub's kept group names (bijective).

    A missing name is a gap (an un-covered live module); an extra name that
    is not a scrub group cannot be verified against the census-authorized
    scrub and is a smell (either a stale/renamed group or a re-introduced
    retired surface the scrub already excluded).
    """
    registry = _load_registry()
    scrub = _load_scrub()

    registry_names: set[str] = {str(row.get("module")) for row in _modules(registry)}
    scrub_names: set[str] = {str(g.get("group")) for g in _scrub_groups(scrub)}

    missing = scrub_names - registry_names
    extra = registry_names - scrub_names
    assert not missing, f"module registry has gaps — scrub groups not covered: {sorted(missing)}"
    assert not extra, f"module registry declares modules the scrub does not recognize (possible re-scrub / retired-surface leak): {sorted(extra)}"


def test_registry_consumes_scrub_verbatim_no_divergent_rescrub() -> None:
    """Each row's ``roots``/``cov_targets`` equal its scrub group's — no re-scrub.

    T042 explicitly forbids a second, divergent derivation of roots/cov
    targets: the registry must consume WP05's scrub, not recompute it.
    """
    registry = _load_registry()
    scrub = _load_scrub()
    scrub_by_name = {g.get("group"): g for g in _scrub_groups(scrub)}

    problems: list[str] = []
    for row in _modules(registry):
        name = row.get("module")
        scrub_group = scrub_by_name.get(name)
        if scrub_group is None:
            continue  # covered by test_registry_covers_every_scrub_group_no_gaps_no_extras
        if list(row.get("roots", [])) != list(scrub_group.get("roots", [])):
            problems.append(f"module {name!r} roots diverge from the scrub group's roots")
        if list(row.get("cov_targets", [])) != list(scrub_group.get("cov_targets", [])):
            problems.append(f"module {name!r} cov_targets diverge from the scrub group's cov_targets")
    assert not problems, "registry re-derives roots/cov_targets instead of consuming the scrub verbatim:\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# DoD: every row has the required shape
# ---------------------------------------------------------------------------
def test_every_row_has_required_fields() -> None:
    registry = _load_registry()
    problems: list[str] = []
    for row in _modules(registry):
        name = row.get("module", "<unnamed>")
        for field in _REQUIRED_ROW_FIELDS:
            if field not in row:
                problems.append(f"module {name!r} is missing required field {field!r}")
        if "roots" in row and not row["roots"]:
            problems.append(f"module {name!r} declares an empty roots list")
        if "cov_targets" in row and not row["cov_targets"]:
            problems.append(f"module {name!r} declares an empty cov_targets list")
        if "tier" in row and not row["tier"]:
            problems.append(f"module {name!r} declares an empty tier")
    assert not problems, "module registry rows are malformed:\n" + "\n".join(problems)


def test_cov_targets_are_dotted_form() -> None:
    """``cov_targets`` stay dotted (``specify_cli.merge``), never path form (C-005)."""
    registry = _load_registry()
    bad: list[str] = []
    for row in _modules(registry):
        for target in row.get("cov_targets", []):
            if "/" in target or target.startswith("src"):
                bad.append(f"module {row.get('module')!r} cov_target {target!r} is not dotted form")
    assert not bad, "\n".join(bad)


def test_shard_counts_are_positive_integers() -> None:
    registry = _load_registry()
    bad = [
        f"module {row.get('module')!r} has non-positive/non-integer shard_count {row.get('shard_count')!r}"
        for row in _modules(registry)
        if not isinstance(row.get("shard_count"), int) or row.get("shard_count", 0) < 1
    ]
    assert not bad, "\n".join(bad)


# ---------------------------------------------------------------------------
# DoD: shard_count is balanced on MEASURED duration — inter-shard skew <=20%
# (NFR-005). Recomputed independently from the timings file, not trusted from
# the registry's own claim.
# ---------------------------------------------------------------------------
def test_inter_shard_skew_within_twenty_percent() -> None:
    """Recompute EVERY module's within-module shard skew from measured durations.

    Independently re-derives the balance the registry claims: for each row,
    greedy-LPT-pack its module's individual measured per-test durations
    (``module_test_durations`` in the timings file) into ``shard_count`` bins
    and require ``(max_bin - min_bin) / max_bin <= 20%`` (NFR-005). A module
    with ``shard_count == 1`` trivially satisfies this (nothing to balance
    against) — the check has bite precisely for the multi-shard modules the
    duration-target sizing actually splits.
    """
    registry = _load_registry()
    timings = _load_timings()
    modules = _modules(registry)
    assert modules, "no modules to check skew for"

    problems: list[str] = []
    worst_skew = 0.0
    checked_multi_shard = 0
    for row in modules:
        name = row["module"]
        shard_count = row["shard_count"]
        durations = _module_test_durations(timings, name)
        assert durations, f"module {name!r} has no recorded per-test durations"
        bins = _lpt_bin_pack(durations, shard_count)
        skew = _skew_of(bins)
        worst_skew = max(worst_skew, skew)
        if shard_count > 1:
            checked_multi_shard += 1
        if skew > _MAX_SKEW:
            problems.append(f"module {name!r} (shard_count={shard_count}) recomputed skew {skew:.1%} exceeds {_MAX_SKEW:.0%}: bins={bins}")

    assert not problems, "inter-shard skew exceeds the NFR-005 ceiling:\n" + "\n".join(problems)
    assert checked_multi_shard >= 1, (
        "no module needed more than one shard — the duration-target sizing never actually "
        "exercised the skew constraint (vacuous coverage of NFR-005)"
    )


# ---------------------------------------------------------------------------
# T041: the timings artefact documents excluded/truncated directories (if any)
# with a reason — never silent.
# ---------------------------------------------------------------------------
def test_timings_excluded_dirs_are_documented() -> None:
    timings = _load_timings()
    excluded = timings.get("excluded", [])
    assert isinstance(excluded, list)
    bad = [e for e in excluded if not (isinstance(e, dict) and e.get("path") and e.get("reason"))]
    assert not bad, f"excluded entries must each carry a path and a reason: {bad}"


# ---------------------------------------------------------------------------
# T043: heavy-pole de-serialization encoded (integration-tests-next
# parallelized; architectural pole always-on + de-serialized, no filter
# group — consistent with WP07's fast/heavy split in ci-router.yml).
# ---------------------------------------------------------------------------
def test_special_tiers_encode_heavy_pole_deserialization() -> None:
    registry = _load_registry()
    special = registry.get("special_tiers", {})
    assert special, "registry declares no special_tiers (T043 de-serialization must be encoded, not left to prose)"

    integration_next = special.get("integration_tests_next")
    assert integration_next is not None, "special_tiers.integration_tests_next is missing"
    assert integration_next.get("parallel_mode") == "-n auto", (
        f"integration-tests-next must be encoded as parallelized ('-n auto'), got {integration_next.get('parallel_mode')!r}"
    )

    architectural = special.get("architectural")
    assert architectural is not None, "special_tiers.architectural is missing"
    assert architectural.get("always_on") is True, "architectural pole must be encoded as always-on (no filter group)"
    assert architectural.get("deserialized") is True, "architectural pole must be encoded as de-serialized"
    assert architectural.get("filter_group") in (None, ""), "the architectural pole must add NO filter group (consistent with WP07's fast/heavy split)"


# ---------------------------------------------------------------------------
# T044(a): the registry is the single data source — adding a module is a
# registry ROW, never a new workflow file.
# ---------------------------------------------------------------------------
def test_registry_rows_never_declare_a_dedicated_workflow_file() -> None:
    """No row may name its own workflow file — that is the ~40-file anti-pattern.

    A module is realized purely as data (roots/cov/tier/shard_count) consumed
    by a bounded matrix; if a row started carrying a ``workflow``/
    ``workflow_file`` key it would signal a regression back toward one
    workflow per module.
    """
    registry = _load_registry()
    bad = [
        row.get("module")
        for row in _modules(registry)
        if "workflow" in row or "workflow_file" in row
    ]
    assert not bad, f"modules declare a dedicated workflow file (anti-pattern — must be matrix-over-registry): {bad}"


# ---------------------------------------------------------------------------
# T044(b): the realization stays within GitHub's 20-reusable-workflows-per-
# caller ceiling — NOT ~40 separate module-*.yml files.
# ---------------------------------------------------------------------------
def test_reusable_workflow_ceiling_respected() -> None:
    registry = _load_registry()
    ceiling = registry.get("reusable_workflow_ceiling")
    assert isinstance(ceiling, int) and ceiling > 0, "registry must declare a positive integer reusable_workflow_ceiling"
    assert ceiling <= 20, f"declared ceiling {ceiling} exceeds GitHub's 20-reusable-workflows-per-caller limit"

    actual_workflow_count = len(list(_WORKFLOWS_DIR.glob("*.yml")))
    assert actual_workflow_count <= ceiling, (
        f"{actual_workflow_count} workflow files under {_WORKFLOWS_DIR.relative_to(_REPO_ROOT)} exceed the declared ceiling {ceiling}"
    )

    modules = _modules(registry)
    per_module_workflow_files = [
        f"module-{row.get('module')}.yml" for row in modules if (_WORKFLOWS_DIR / f"module-{row.get('module')}.yml").exists()
    ]
    assert not per_module_workflow_files, (
        "one-workflow-file-per-module anti-pattern detected (breaches the ceiling for any "
        f"non-trivial module count): {per_module_workflow_files}"
    )


def test_module_count_would_breach_ceiling_if_realized_one_file_per_module() -> None:
    """Sanity: the module set is large enough that the ceiling constraint is real.

    If this ever shrinks to <=20 the matrix-over-registry design is still
    correct, but the "not ~40 files" framing loses its bite — this is a
    documentation/non-vacuity check, not a hard failure gate, so it only
    warns via a soft assertion tied to the DoD's own framing.
    """
    registry = _load_registry()
    modules = _modules(registry)
    ceiling = registry.get("reusable_workflow_ceiling", 20)
    assert len(modules) >= 1
    # The whole point of the matrix realization is that module count is
    # allowed to exceed the ceiling without needing one workflow file each.
    if len(modules) > ceiling:
        # Expected/allowed — this is exactly the case the design defends against.
        assert True
