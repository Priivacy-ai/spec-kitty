"""Issue #90 diagnostics -- TEMPORARY, remove in the fix round (TODO(triage): #90).

``tests/charter/test_mission_type_profiles.py::TestMissionCreatePropagatesEmptyActionSequenceError``
reds only under the 16-cpu runner's parallel shard (same-worker pollution,
flakiness-policy Tier 2) and never off it: three full ``-n 16 --dist loadfile``
passes on an 8-cpu VM stayed green while a post-teardown census over every
watched dimension found zero drift. Two sufficient leak shapes ARE proven
(each reds this node deterministically when present): ambient CWD left inside
a ``.worktrees/`` path by an earlier test in the worker (the victim reads
``Path.cwd()``, not its explicit ``repo_root``), and any stale rebinding of
``charter.mission_type_profiles.resolve_mission_type_context`` (the mock used
by the runtime-bridge composition suites raises
``UnknownMissionTypeError('qa')`` verbatim).

This module makes the next runner-side failure self-describing. For every
other test the cost is one ``deque`` append per call report; around the victim
node it snapshots the ambient chain state at setup and, if the call fails,
emits a RuntimeWarning carrying (a) the setup-vs-failure diff across every
value the resolution chain reads, (b) this worker's immediately preceding
nodes -- the co-resident predecessor files a same-worker polluter must be
among. Both land in the run's warnings summary, so the CI comment on the PR
carries them without any harness change.

Everything here is keyed to the exact victim nodeid and inert elsewhere.
"""

from __future__ import annotations

import os
import warnings
from collections import deque

import pytest

_VICTIM_NODEID = (
    "tests/charter/test_mission_type_profiles.py::TestMissionCreatePropagatesEmptyActionSequenceError::test_create_mission_propagates_named_exception_type"
)

_PREDECESSOR_LIMIT = 40

#: Call-phase nodeids most recently finished by THIS worker process. A Tier-2
#: same-worker polluter must appear among these when the victim reds.
_predecessors: deque[str] = deque(maxlen=_PREDECESSOR_LIMIT)

_setup_state: dict[str, str] | None = None


def _chain_state() -> dict[str, str]:
    """Snapshot every ambient value the victim's resolution chain reads."""
    try:
        cwd = os.getcwd()
    except OSError:  # noqa: BLE001 — a polluter can delete cwd (tmp_path teardown); diagnose, don't crash the worker
        cwd = "<vanished>"
    state: dict[str, str] = {"cwd": cwd}
    for var in (
        "SPEC_KITTY_PACKS_ROOT",
        "SPEC_KITTY_TEMPLATE_ROOT",
        "SPEC_KITTY_HOME",
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_CONFIG_GLOBAL",
    ):
        state[f"env:{var}"] = repr(os.environ.get(var))
    import charter.mission_type_profiles as mtp
    import charter.pack_context as pc

    state["module:charter.pack_context"] = repr(pc)
    state["module:charter.mission_type_profiles"] = repr(mtp)
    state["attr:PackContext.from_config"] = repr(getattr(pc.PackContext, "from_config", None))
    state["attr:mtp.existing_mission_types"] = repr(getattr(mtp, "existing_mission_types", None))
    state["attr:mtp.resolve_mission_type_context"] = repr(getattr(mtp, "resolve_mission_type_context", None))
    try:
        from doctrine.missions.mission_type_repository import resolve_layered_mission_types

        state["attr:resolve_layered_mission_types"] = repr(resolve_layered_mission_types)
        state["cache:layered_roster"] = str(resolve_layered_mission_types.cache_info())
    except Exception as exc:  # noqa: BLE001 — diagnostics must never raise into the report path
        state["module:doctrine.missions.mission_type_repository"] = f"<import failed: {exc!r}>"
    try:
        from doctrine.missions.repository import MissionTemplateRepository

        state["missions_root"] = str(MissionTemplateRepository.default_missions_root())
    except Exception as exc:  # noqa: BLE001 — a raised resolver IS the pollution signal
        state["missions_root"] = f"<raised {type(exc).__name__}: {exc}>"
    return state


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    rep = outcome.get_result()
    # Predecessor trail: recorded here rather than in pytest_runtest_logreport
    # so the trail and the warning share one code path whose firing is proven.
    if rep.when == "call":
        _predecessors.append(item.nodeid)
    if item.nodeid != _VICTIM_NODEID:
        return
    global _setup_state
    if rep.when == "setup":
        _setup_state = _chain_state()
    elif rep.when == "call" and rep.failed and _setup_state is not None:
        current = _chain_state()
        # Absolute values, not just a diff: pollution may predate this node's
        # own setup phase, and a stale double's repr (e.g.
        # ``_mock_resolve_mission_type_context``) is itself the diagnosis.
        changed = [f"{key}: setup={_setup_state.get(key)!r} -> failure={current.get(key)!r}" for key in current if current.get(key) != _setup_state.get(key)]
        absolute = [f"{key}={value!r}" for key, value in sorted(current.items())]
        worker = os.environ.get("PYTEST_XDIST_WORKER", "controller")
        warnings.warn(
            "#90 victim failed; worker="
            + worker
            + "; predecessors="
            + " | ".join(_predecessors)
            + "; changed-setup-to-failure=["
            + "; ".join(changed)
            + "]"
            + "; absolute-state={"
            + "; ".join(absolute)
            + "}",
            RuntimeWarning,
            stacklevel=1,
        )
