"""Ledger F3 — the chain-local degrade-arm sweep must be exercised by a CI gate.

Mission ``meta-fail-closed-3162-01KZ7FSQ``, WP08.

``scripts/sweep_degrade_arms_on_routed_chain_3162.py`` is this mission's
calibrated instrument for the one defect class its routing creates: routing a
read site onto ``specify_cli.core.paths.load_meta_fail_closed`` changes the
exception escaping that site from ``ValueError`` to
:class:`specify_cli.core.paths.MissionMetaReadError`, whose MRO is
``MissionMetaReadError -> RuntimeError -> Exception`` — no ``ValueError``, no
``OSError``. Every pre-existing ``except (ValueError, OSError)`` on a
*transitive caller* of a routed site therefore stops absorbing corruption the
moment the site is routed, silently converting a degrade path into a raising
path. That is the arm change ``C-001`` forbids.

``SC-002`` structurally cannot see this class (ledger F4): its subject is the
routed **site**, and a stranded arm is by construction at a **caller** that
never appears in a site-scoped enumeration. The sweep is the only instrument
that covers it.

Ledger F3: **no CI gate ran the script at all.** A calibrated instrument no gate
runs will rot — its call graph, its ``ABSORBING`` / ``STRANDABLE`` vocabulary and
its propagation rule can all drift out from under the mission that depends on
them, with nothing going red. This module is that gate, and it lives beside the
routed-count gate it complements (``test_inline_meta_read_gate.py``, same
directory).

What runs in CI, and what does not
----------------------------------
1. :func:`test_sweep_detects_a_stranded_arm_on_a_synthetic_chain` — the
   **positive control**. A three-module chain carrying exactly one
   ``except (ValueError, OSError)`` on the caller must be reported as exactly
   one hazard, at that caller. This is the anti-vacuity assertion: a sweep
   mutated to report nothing fails here, so a CLEAN verdict from assertion 3
   below is never the silence of a broken instrument.
2. :func:`test_sweep_reports_clean_when_the_arm_is_widened` — the **negative
   control** on the same chain with the arm widened. Without it, "always finds
   a hazard" would also pass assertion 1.
3. :func:`test_live_src_has_no_stranded_arm_on_the_missions_routed_chains` — the
   **regression guard**. The live ``src/`` tree must be CLEAN on the mission's
   four routed seeds. Re-stranding an arm anywhere on those chains reds this.

``--self-check`` — the script's own recorded known-answer replay at
:data:`CONTROL_BASE_REV` — is driven by
:func:`test_self_check_replays_the_recorded_control_when_the_base_rev_is_present`
**when that commit is present in the checkout**, and skipped with the reason
named when it is not: it shells out to ``git archive <rev> src``, and
``actions/checkout`` defaults to ``fetch-depth: 1`` (the arch pole does not
override it), so a CI runner usually holds no history to read. Assertions 1-3
carry the calibration in CI and need no git history at all — which is why the
gate does not rest on that one test.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

# ``git_repo`` because the ``--self-check`` row drives real ``git`` via
# ``subprocess`` (marker-correctness Rule 1, file-scoped); ``architectural``
# because this is a repo-invariant gate over an instrument, not a product test.
# Both are selected by the always-on arch pole
# (``-m '<arch_shard_N> and not windows_ci and (git_repo or integration or
# architectural) and not timing'``).
pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "sweep_degrade_arms_on_routed_chain_3162.py"

#: The mission's routed read chains, as **dotted qualnames**. A bare name is a
#: documented trap: ``--seed _resolve_mission_id`` resolves to
#: ``mission_runtime.resolution._resolve_mission_id``, a different function on a
#: different chain (WP03 evidence; the sweep's own ``--help`` says so).
_MISSION_SEEDS: tuple[str, ...] = (
    "specify_cli.missions._read_path_resolver.read_primary_meta",
    "specify_cli.context.resolver._read_meta_json",
    "specify_cli.decisions.service._resolve_mission_id",
    "specify_cli.missions._resolve_planning_branch.load_mission_target_branch",
)

#: ``mission_runtime.resolution._resolve_mission_id`` /
#: ``_resolve_coordination_branch`` are deliberately **absent** from
#: :data:`_MISSION_SEEDS`. Their chain carries ledger item **F11** —
#: ``safe_commit_cmd.py``'s ``except (FileNotFoundError, ValueError)`` in
#: ``_resolve_mission_aware_target`` — which WP04 measured as leaking identically
#: at the mission's baseline ``96494e5ec``, at pre-routing ``45b278823`` and at
#: HEAD. It is pre-existing, out of this mission's remit, and recorded in
#: ``residual-ledger.md``. Sweeping it here would pin a known-open finding as
#: this gate's expected answer and turn its eventual fix into a false red.
_SEEDS_EXCLUDED_AS_PRE_EXISTING = "mission_runtime.resolution._resolve_mission_id"

#: Expected hazard count for the recorded control replayed by ``--self-check``.
#: Pinned so an emptied ``CONTROL_EXPECT`` cannot silently degrade the control
#: into "expect clean": an empty ``--expect`` makes the script's own comparison
#: vacuous (no token is missing, and ``len(hazards) != 0`` is the only check
#: left), which is exactly the uncalibrated silence ``--self-check`` exists to
#: prevent.
_CONTROL_HAZARD_COUNT = 6

#: The sweep's "the control did not reproduce, the run is refused" exit status.
_SELF_CHECK_REFUSED = 2

_READER_SRC = '''\
"""Stand-in for ``specify_cli.core.paths`` — the routed fail-closed seam."""


class MissionMetaReadError(RuntimeError):
    """Same MRO shape as the real one: RuntimeError, never ValueError/OSError."""


def load_meta_fail_closed(path):
    raise MissionMetaReadError(path)
'''

_MID_SRC = '''\
"""Stand-in for a routed read site — raises the typed error at the seam."""

from pkg.reader import load_meta_fail_closed


def read_primary_meta(path):
    return load_meta_fail_closed(path)
'''

_CALLER_STRANDED_SRC = '''\
"""A transitive caller whose degrade arm the routing strands."""

from pkg.mid import read_primary_meta


def resolve(path):
    try:
        return read_primary_meta(path)
    except (ValueError, OSError):
        return None
'''

_CALLER_WIDENED_SRC = '''\
"""The same caller with the arm widened — the degrade is restored."""

from pkg.mid import read_primary_meta
from pkg.reader import MissionMetaReadError


def resolve(path):
    try:
        return read_primary_meta(path)
    except (ValueError, OSError, MissionMetaReadError):
        return None
'''

_SYNTHETIC_SEED = "pkg.mid.read_primary_meta"
_SYNTHETIC_CALLER = "pkg.caller.resolve"


def _load_sweep_module() -> ModuleType:
    """Import the sweep script by path (``scripts/`` is not an importable package)."""
    spec = importlib.util.spec_from_file_location(
        "sweep_degrade_arms_on_routed_chain_3162", _SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build an import spec for {_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


#: ``Any`` because the module is loaded by path, so no static type is available.
SWEEP: Any = _load_sweep_module()


def _build_synthetic_src(root: Path, caller_source: str) -> Path:
    """Write the three-module chain under ``root/src`` and return that ``src``."""
    src = root / "src"
    pkg = src / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "reader.py").write_text(_READER_SRC, encoding="utf-8")
    (pkg / "mid.py").write_text(_MID_SRC, encoding="utf-8")
    (pkg / "caller.py").write_text(caller_source, encoding="utf-8")
    return src


def _sweep_synthetic(root: Path, caller_source: str) -> tuple[list[Any], set[str]]:
    """Build the synthetic chain and sweep it from the synthetic seed."""
    src = _build_synthetic_src(root, caller_source)
    graph = SWEEP.CallGraph(src)
    seeds = graph.resolve_seed(_SYNTHETIC_SEED)
    assert seeds == {_SYNTHETIC_SEED}, (
        f"the synthetic seed {_SYNTHETIC_SEED!r} did not resolve to itself "
        f"(got {sorted(seeds)}) — the fixture, not the sweep, is wrong"
    )
    hazards, raising = SWEEP.sweep(graph, seeds)
    return list(hazards), set(raising)


def _hazard_identities(
    hazards: list[Any],
) -> set[tuple[str, str, tuple[str, ...], str]]:
    """Content-addressed hazard identity set: (file, function, caught, guarded).

    Deliberately a SET of identities rather than a count, so an assertion cannot
    pass on a hazard reported at the wrong frame or catching the wrong exceptions.
    ``caught`` is sorted because the sweep's ``_caught_names`` order follows the
    handler's AST, which is not the authored tuple order.
    """
    return {
        (
            Path(h.path).name,
            h.function,
            tuple(sorted(h.caught)),
            h.guarded_callee,
        )
        for h in hazards
    }


def test_the_script_under_test_exists() -> None:
    """The instrument this gate exercises must be on disk (ledger F3's subject)."""
    assert _SCRIPT_PATH.is_file(), (
        f"{_SCRIPT_PATH} is missing — this gate exists because ledger F3 found "
        "the script exercised by nothing in CI; deleting it silently is worse."
    )


def test_sweep_detects_a_stranded_arm_on_a_synthetic_chain(tmp_path: Path) -> None:
    """Positive control: one stranded caller arm is reported as exactly one hazard.

    Anti-vacuity for :func:`test_live_src_has_no_stranded_arm_on_the_missions_routed_chains`.
    A sweep that reported nothing would pass a CLEAN assertion on the live tree
    while seeing nothing at all; it fails here.
    """
    hazards, raising = _sweep_synthetic(tmp_path, _CALLER_STRANDED_SRC)

    # A set-equality over hazard IDENTITY, not `len(hazards) == 1`: a bare
    # cardinality passes when the sweep reports one hazard at the WRONG place,
    # which is the failure mode that matters for an instrument whose whole job is
    # naming the frontier frame (FR-014 / test_golden_count_ban's `convert` class).
    assert _hazard_identities(hazards) == {
        ("caller.py", _SYNTHETIC_CALLER, ("OSError", "ValueError"), _SYNTHETIC_SEED)
    }, (
        "the synthetic chain's stranded arm was not reported as the single hazard "
        f"at {_SYNTHETIC_CALLER}: got {sorted(_hazard_identities(hazards))}"
    )
    hazard = hazards[0]
    assert "except (ValueError, OSError)" in hazard.except_source
    assert hazard.try_line < hazard.except_line, (
        "the try: line must precede its handler — a swapped pair would make the "
        "--expect control's either-line matching meaningless"
    )
    assert raising == {_SYNTHETIC_SEED}, (
        "the arm absorbs at the caller, so no frame ABOVE the seed should be "
        f"recorded as raising; got {sorted(raising)}"
    )


def test_sweep_reports_clean_when_the_arm_is_widened(tmp_path: Path) -> None:
    """Negative control: widening the same arm makes the same chain CLEAN.

    Without this, an instrument that flagged every ``try`` on a routed chain
    would satisfy the positive control above.
    """
    hazards, _ = _sweep_synthetic(tmp_path, _CALLER_WIDENED_SRC)
    assert hazards == [], (
        "widening the arm to include MissionMetaReadError must absorb the typed "
        f"error, but the sweep still reports {len(hazards)} hazard(s): "
        f"{[(Path(h.path).name, h.except_line, h.caught) for h in hazards]}"
    )


def test_the_synthetic_controls_disagree() -> None:
    """The two controls must be a real discrimination, not the same tree twice."""
    assert _CALLER_STRANDED_SRC != _CALLER_WIDENED_SRC
    assert "MissionMetaReadError" not in _CALLER_STRANDED_SRC.split("def resolve")[1]
    assert "MissionMetaReadError" in _CALLER_WIDENED_SRC.split("def resolve")[1]


def test_live_src_has_no_stranded_arm_on_the_missions_routed_chains() -> None:
    """The regression guard: the live ``src/`` is CLEAN on the four routed seeds.

    This is what ledger F3 buys. WP02 cycle 2 widened four arms in
    ``src/specify_cli/cli/commands/agent/`` that this mission's routing had
    stranded several call hops from the edit; nothing in CI held that closed.
    Re-stranding any arm on these chains — by narrowing a handler, or by routing
    a new site whose callers still catch ``ValueError``/``OSError`` — reds here.
    """
    src_root = _REPO_ROOT / "src"
    assert src_root.is_dir(), f"no src/ at {src_root}"
    graph = SWEEP.CallGraph(src_root)

    seeds: set[str] = set()
    for seed in _MISSION_SEEDS:
        resolved = graph.resolve_seed(seed)
        assert resolved, (
            f"seed {seed!r} resolved to nothing — the routed function moved or "
            "was renamed. Re-point this seed rather than dropping it: an "
            "unresolvable seed sweeps zero chains and reports CLEAN vacuously."
        )
        seeds |= resolved

    hazards, raising = SWEEP.sweep(graph, seeds)

    # Anti-vacuity on the LIVE tree, independent of the synthetic controls: the
    # typed error must actually propagate somewhere. A graph that resolved no
    # caller edges would report CLEAN with nothing swept.
    assert len(raising) > len(seeds), (
        f"the typed error escapes only the {len(seeds)} seed frame(s) themselves "
        "— no transitive caller was resolved, so a CLEAN verdict would be "
        "vacuous. The call graph, not the tree, is what regressed."
    )
    assert hazards == [], (
        f"{len(hazards)} degrade arm(s) are stranded on the mission's routed "
        "chains — a corrupt meta.json now raises where it used to degrade "
        "(C-001). Widen the handler to include MissionMetaReadError:\n"
        + "\n".join(
            f"  {Path(h.path).name}:{h.except_line} in {h.function} "
            f"catches {h.caught} guarding {h.guarded_callee}"
            for h in hazards
        )
    )


def test_the_recorded_control_is_not_empty() -> None:
    """``--self-check``'s control string must still name its six known hazards.

    An emptied ``CONTROL_EXPECT`` degrades the script's own comparison into
    "expect clean" without failing anything — the uncalibrated silence the
    ``--self-check`` flag exists to prevent.
    """
    tokens = [tok.strip() for tok in SWEEP.CONTROL_EXPECT.split(",") if tok.strip()]
    assert len(tokens) == _CONTROL_HAZARD_COUNT, (
        f"the recorded control names {len(tokens)} location(s), expected "
        f"{_CONTROL_HAZARD_COUNT}: {tokens}"
    )
    assert all(":" in tok and tok.endswith(tuple("0123456789")) for tok in tokens), (
        f"every control token must be file.py:LINE, got {tokens}"
    )
    assert SWEEP.CONTROL_BASE_REV.strip(), "CONTROL_BASE_REV is empty"


def _control_rev_is_present() -> bool:
    """True when ``CONTROL_BASE_REV`` is a commit this checkout actually holds."""
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{SWEEP.CONTROL_BASE_REV}^{{commit}}"],
        cwd=_REPO_ROOT,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def test_self_check_replays_the_recorded_control_when_the_base_rev_is_present(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--self-check`` must reproduce its recorded 6-arm known answer.

    Scoped to the **calibration**, not to the live verdict. ``--self-check``
    replays the control and then sweeps the working tree, so its exit status is
    ``1`` whenever the live tree has a hazard — a condition
    :func:`test_live_src_has_no_stranded_arm_on_the_missions_routed_chains`
    already reports, with the hazard printed. Asserting ``status == 0`` here
    would make a live-tree finding read as "the known answer did not reproduce",
    which is a failure for the wrong reason. So this asserts the control's own
    verdict lines and only that the run was not **refused** (exit ``2``).

    Skipped — with the reason named, never silently — when the checkout has no
    history for ``git archive``: ``actions/checkout`` defaults to
    ``fetch-depth: 1`` and the arch pole does not override it. The synthetic
    controls above are what keep this gate non-vacuous in that case.
    """
    if not _control_rev_is_present():
        pytest.skip(
            f"control rev {SWEEP.CONTROL_BASE_REV} is not in this checkout "
            "(shallow clone: actions/checkout defaults to fetch-depth 1), so "
            "`git archive` cannot materialize it. The synthetic positive and "
            "negative controls in this module carry the calibration instead."
        )
    status = SWEEP.main(["--self-check"])
    captured = capsys.readouterr()
    assert status != _SELF_CHECK_REFUSED, (
        "--self-check REFUSED the run: the recorded known answer at "
        f"{SWEEP.CONTROL_BASE_REV} did not reproduce. Every CLEAN verdict from "
        f"this instrument is meaningless until that is resolved.\n"
        f"{captured.out[-4000:]}"
    )
    assert "CONTROL: PASS - known answer reproduced exactly" in captured.out, (
        "--self-check did not print its control verdict — the calibration did "
        f"not run.\n{captured.out[-4000:]}"
    )
    assert "the 6 HAZARD(S) above are the *control's* known answer" in captured.out, (
        "the control found a different number of hazards than the recorded "
        f"six.\n{captured.out[-4000:]}"
    )


def test_the_pre_existing_f11_chain_is_excluded_deliberately() -> None:
    """F11's chain is named as excluded, so its absence reads as a decision.

    A reviewer comparing the sweep's ``--help`` (whose recorded control names
    the ``safe_commit_cmd`` arm) against :data:`_MISSION_SEEDS` must be able to
    tell "deliberately out of scope" from "forgotten".
    """
    assert _SEEDS_EXCLUDED_AS_PRE_EXISTING not in _MISSION_SEEDS
    assert _SEEDS_EXCLUDED_AS_PRE_EXISTING.startswith("mission_runtime.")
    assert not any(seed.startswith("mission_runtime.") for seed in _MISSION_SEEDS), (
        "every asserted seed must be a specify_cli chain this mission routed; a "
        "mission_runtime seed reaches the pre-existing F11 arm and would pin a "
        "known-open finding as this gate's expected answer"
    )
