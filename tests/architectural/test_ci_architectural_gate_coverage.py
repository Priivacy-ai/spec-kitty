"""Guarded write-side surfaces must trigger the full architectural shard.

Architectural gate keyed on ``core_misc``: a change to any guarded write-side
surface must set ``core_misc=true`` so the sharded integration core-misc suites
run over it. The full tests/architectural/** suite ALSO runs unconditionally in
the standalone always-on ``arch-adversarial`` pole (mission ci-topology-shrink
FR-005/FR-013), so it can never be masked by a filter output.

FR-007 / NFR-004 — the meta-invariant: the CI fix (T020, widened core_misc
filter) must itself be drift-proof so a future filter regression is caught.

Key on filter-name + path-glob membership, NOT line numbers, so the test is
drift-proof against YAML reorderings.

T022 falsification: assert src/specify_cli/status/lifecycle_events.py
(the original _repo_root_for_lifecycle_log regression surface) is covered
by the widened core_misc globs, i.e. the rederivation ratchet would run
on a change to that file.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci-quality.yml"

# Guarded write-side surfaces that MUST appear (via a matching glob) in
# core_misc so a change to any of them sets core_misc=true and the full
# tests/architectural/** shard runs.
_GUARDED_SURFACES: list[str] = [
    "src/specify_cli/status/",
    "src/specify_cli/coordination/",
    "src/specify_cli/core/worktree.py",
    "tests/architectural/",
]

# Over-broad glob that must NOT appear in core_misc — adding it would run
# the heavy architectural shard on every src change.
_OVERBROAD_GLOB = "src/**"


def _load_workflow() -> dict[str, Any]:
    result: dict[str, Any] = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    return result


def _path_filters(data: dict[str, Any]) -> dict[str, list[str]]:
    """Extract the dorny/paths-filter 'filters' map from the changes job."""
    filter_step = next(
        step
        for step in data["jobs"]["changes"]["steps"]
        if step.get("id") == "filter"
    )
    parsed: dict[str, list[str]] = yaml.safe_load(filter_step["with"]["filters"])
    return parsed


def _core_misc_globs(data: dict[str, Any]) -> list[str]:
    filters = _path_filters(data)
    return filters.get("core_misc", [])


def _glob_covers(path_fragment: str, globs: list[str]) -> bool:
    """Return True if any glob in *globs* matches *path_fragment*.

    Uses fnmatch on the normalised fragments so that e.g.
    'src/specify_cli/status/**' covers 'src/specify_cli/status/lifecycle_events.py'.
    Also handles the case where the glob ends with '/**' by checking prefix
    containment (a directory glob covers all files under that directory).
    """
    for glob in globs:
        # Normalise trailing **
        if glob.endswith("/**"):
            prefix = glob[: -len("/**")]
            if path_fragment.startswith(prefix):
                return True
        elif glob.endswith("/**/*"):
            prefix = glob[: -len("/**/*")]
            if path_fragment.startswith(prefix):
                return True
        # Direct fnmatch (handles exact files like 'src/specify_cli/core/worktree.py')
        if fnmatch.fnmatch(path_fragment, glob):
            return True
    return False


def _run_script_for_step(data: dict[str, Any], job_name: str, step_name: str) -> str:
    step = next(
        s
        for s in data["jobs"][job_name]["steps"]
        if s.get("name") == step_name
    )
    return str(step["run"])


# ---------------------------------------------------------------------------
# T021 — guarded-surface → architectural-shard coverage
# ---------------------------------------------------------------------------


def test_guarded_surfaces_in_core_misc_filter() -> None:
    """Each guarded write-side surface must be covered by a core_misc glob.

    Keyed on filter-name + path-glob membership (not line numbers) so this
    test survives YAML reorderings without silently rotting.

    A future edit that drops one of these globs turns this RED — which is
    exactly the NFR-004 drift-proof guarantee.
    """
    data = _load_workflow()
    globs = _core_misc_globs(data)
    missing: list[str] = [
        surface for surface in _GUARDED_SURFACES if not _glob_covers(surface, globs)
    ]

    assert not missing, (
        "The following guarded surfaces are NOT covered by a core_misc glob — "
        "a change to these paths will NOT trigger integration-tests-core-misc "
        "(architectural), masking architectural regressions:\n"
        + "\n".join(f"  {s}" for s in missing)
    )


def test_tests_architectural_stays_in_core_misc() -> None:
    """tests/architectural/** must remain in core_misc.

    Dropping it would silently stop the architectural shard from running when
    a guard is edited, breaking the guard's own self-test loop.
    """
    data = _load_workflow()
    globs = _core_misc_globs(data)
    assert "tests/architectural/**" in globs, (
        "tests/architectural/** was removed from the core_misc filter. "
        "Restore it so architectural-guard edits trigger the shard."
    )


def test_core_misc_filter_not_over_broad() -> None:
    """src/** (or any whole-src glob) must NOT appear in core_misc.

    Adding it would run the heavy architectural shard on every source change,
    defeating the purpose of per-surface scoping.
    """
    data = _load_workflow()
    globs = _core_misc_globs(data)
    assert _OVERBROAD_GLOB not in globs, (
        f"The over-broad glob '{_OVERBROAD_GLOB}' is present in core_misc. "
        "Remove it — use specific surface globs instead."
    )


# ---------------------------------------------------------------------------
# Short-circuit cannot re-mask when core_misc=true
# ---------------------------------------------------------------------------


def test_arch_suite_runs_unconditionally_cannot_be_masked() -> None:
    """No status/path change can mask the architectural suite — it runs always-on.

    Re-pinned for mission ci-topology-shrink (FR-005/FR-013). The OLD mechanism
    this guarded (a ``core_misc != 'true' AND execution_context == 'true'``
    shell short-circuit inside ``integration-tests-core-misc``, which relied on
    a status/** change flipping ``core_misc=true`` to *avoid* being masked) is
    SUPERSEDED. WP03 extracted the architectural shard into the standalone
    ``arch-adversarial`` pole, made it ``if: always()`` with NO dorny
    filter-group gate, and dropped the fast-lane ``needs`` edge. The
    "architectural shard masked by a short-circuit / filter output" failure mode
    is now structurally impossible: the pole runs on every push/PR regardless of
    which filter outputs fire.

    This pins the stronger guarantee at the raw-YAML level (a distinct lens from
    the parse-model differential matrix in
    ``test_arch_unblind_matrix.py::test_no_src_dir_is_architecturally_blind``,
    which asserts 0 arch-blind src dirs, and the de-serialization pinned by
    ``test_arch_pole_deserialized.py``): the ``arch-adversarial`` job's gate is
    literally ``always()`` and is NOT conditioned on any ``needs.changes.outputs``
    filter output. Re-introducing a filter gate here reds this test.
    """
    data = _load_workflow()
    arch_job = data["jobs"]["arch-adversarial"]

    # Gate is exactly always() — not a filter-conditioned expression.
    gate = str(arch_job["if"]).strip()
    assert gate == "always()", (
        f"arch-adversarial gate must be exactly 'always()', got {gate!r}. A "
        "filter-conditioned gate would let a status/path change mask the "
        "architectural suite (the pre-WP03 mask this mission removed)."
    )
    assert "needs.changes.outputs" not in gate, (
        "arch-adversarial gained a dorny filter-output gate — that re-opens the "
        "mask. The pole must stay unconditional (mission ci-topology-shrink "
        "FR-005/FR-013)."
    )

    # No fast-lane serialization or filter-gated needs edge either: the pole
    # depends on nothing (de-serialized). Full de-serialization proof lives in
    # test_arch_pole_deserialized.py; here we assert the pole carries no needs.
    assert "needs" not in arch_job or not arch_job.get("needs"), (
        "arch-adversarial declared a needs edge — it must run standalone so no "
        "upstream skip/failure can mask the architectural suite."
    )

    # The pole positively selects the architectural marker over tests/architectural,
    # so a guard edit still runs its own self-test loop (behavioral intent kept).
    run_script = _run_script_for_step(
        data,
        "arch-adversarial",
        "Run architectural + adversarial suite (always-on pole)",
    )
    assert "git_repo or integration or architectural" in run_script

    # Status/** surfaces remain in core_misc (T020) — that still routes them to
    # the sharded integration suites; the pole's always-on run is the extra,
    # unmaskable safety net on top.
    globs = _core_misc_globs(data)
    assert _glob_covers("src/specify_cli/status/some_module.py", globs), (
        "src/specify_cli/status/** dropped from core_misc — a status change "
        "would stop routing to the integration core-misc shards."
    )


# ---------------------------------------------------------------------------
# T022 — falsification: lifecycle_events.py scenario
# ---------------------------------------------------------------------------


def test_lifecycle_events_covered_by_core_misc() -> None:
    """src/specify_cli/status/lifecycle_events.py must be matched by core_misc.

    This is the original regression surface (_repo_root_for_lifecycle_log fallback
    that passed fast-tests-status but slipped through the architectural shard).
    With T020 applied, a change to this file sets core_misc=true so the
    test_no_write_side_rederivation ratchet runs in-PR.

    The file must exist on HEAD — if it is renamed/removed, update this path.
    """
    lifecycle_events_path = (
        _REPO_ROOT / "src" / "specify_cli" / "status" / "lifecycle_events.py"
    )
    assert lifecycle_events_path.exists(), (
        f"{lifecycle_events_path} does not exist on HEAD. "
        "Update this path if the file was renamed/moved."
    )

    data = _load_workflow()
    globs = _core_misc_globs(data)
    relative_path = "src/specify_cli/status/lifecycle_events.py"
    assert _glob_covers(relative_path, globs), (
        f"core_misc globs do not cover '{relative_path}'. "
        "A change to this file (the original _repo_root_for_lifecycle_log "
        "regression) would NOT trigger the architectural shard, re-opening "
        "the mask. Add 'src/specify_cli/status/**' to core_misc (T020)."
    )
