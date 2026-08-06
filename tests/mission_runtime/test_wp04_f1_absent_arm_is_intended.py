"""WP04 / ledger item F1 — the ABSENT-arm class, recorded as INTENDED and pinned.

Mission ``meta-fail-closed-3162-01KZ7FSQ``, residual-ledger item **F1**.

The finding
-----------
Two commands read the primary ``meta.json`` a second time, later, at a site
guarded by **no** ``except`` arm at all. Re-derived by instrumented traceback
(exactly one escaping raise per command; the other raises on the same run are
absorbed inside ``lifecycle_phase._read_baseline_merge_commit``)::

    check-prerequisites -> mission_branch_context._resolve_feature_target_branch
                        -> core.paths.read_target_branch_from_meta
                        -> core.paths.load_meta_fail_closed      [no arm]

    finalize-tasks -> mission_finalize._validate_occurrence_map_ready
                   -> bulk_edit.gate.ensure_occurrence_classification_ready
                   -> core.paths.load_meta_fail_closed           [no arm]

This is an **absent**-arm class, distinct from a *stranded* arm (an existing
``except`` that stops matching once the raised type changes).

Why it is INTENDED, and therefore pinned rather than "fixed"
------------------------------------------------------------
1. **``read_target_branch_from_meta`` mandates the absent arm.** Its docstring
   (``src/specify_cli/core/paths.py``, the ``Raises:`` section) states:
   *"Callers MUST NOT silently swallow this -- the error must propagate so
   corruption is visible (fail-closed doctrine)."* Adding an absorbing arm at
   ``_resolve_feature_target_branch`` would make ``check-prerequisites`` report
   ``target_branch = get_current_branch(repo_root) or "main"`` on a corrupt
   file -- a plausible-but-wrong value, silently. That is strictly worse than a
   visible refusal, and it is what the authority forbids in as many words.

2. **This mission did not cause it.** ``read_target_branch_from_meta``'s body is
   byte-identical ``load_meta_fail_closed(feature_dir)`` at the mission's
   measurement baseline / merge-base ``96494e5ec`` and at ``upstream/main`` tip
   ``98198e980``; it has
   been fail-closed since #2139. For the gate,
   ``ensure_occurrence_classification_ready`` read ``load_meta(feature_dir)``
   with **no arm** at baseline, raising a bare ``ValueError`` that was equally
   unabsorbed and landed in the very same top-level ``except Exception``. WP02's
   routing changed only the exception *type*, not whether an arm exists.

3. **The payload is not a raw crash.** Both commands exit ``1`` with structured
   JSON that names the corrupt file and says ``-- fail-closed``. What it lacks
   are ``error_code`` / ``mission_flag`` / ``available_missions`` -- the
   *mission-detection* keys, which describe "could not work out which mission you
   meant". They are not meaningful for "found your mission, its meta.json is
   corrupt". Calling this payload "degraded" conflates two different failures.

So the decision recorded here is: **the fail-closed refusal at these sites is
intended behaviour**, and ``C-001``'s degrade contract is not violated, because
there was never an arm at these sites to change.

What these tests are for
------------------------
They stop the *other* outcome from being introduced quietly. If a future editor
adds an absorbing arm at either site -- making the command default a branch or
pass a gate on a corrupt ``meta.json`` -- these tests go red and say why. That is
the "tested decision" the fold required, rather than a prose note that rots.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from specify_cli.bulk_edit.gate import ensure_occurrence_classification_ready
from specify_cli.cli.commands.agent.mission_branch_context import (
    _resolve_feature_target_branch,
)
from specify_cli.core.paths import MissionMetaReadError

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_MALFORMED_META = '{"mission_id":'


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _mission_dir(tmp_path: Path, meta_text: str | None) -> tuple[Path, Path]:
    """Return ``(repo_root, mission_dir)`` with *meta_text* written (or absent)."""
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "wp04-f1@example.test")
    _git(root, "config", "user.name", "WP04 F1")
    _git(root, "commit", "--allow-empty", "-qm", "init")
    (root / ".kittify").mkdir()
    mission_dir = root / "kitty-specs" / "wp04-f1-absent-arm"
    mission_dir.mkdir(parents=True)
    if meta_text is not None:
        (mission_dir / "meta.json").write_text(meta_text, encoding="utf-8")
    (mission_dir / "spec.md").write_text("# f1\n", encoding="utf-8")
    return root, mission_dir


def test_f1_target_branch_read_refuses_on_corruption_rather_than_defaulting(
    tmp_path: Path,
) -> None:
    """``_resolve_feature_target_branch`` must RAISE, not fall back, on corrupt meta.

    The fallback chain at this site (``get_current_branch(repo_root) or "main"``)
    is deliberate for the *field-absent* case only. Reaching it on **corruption**
    would report a wrong ``target_branch`` silently, which
    ``read_target_branch_from_meta``'s own contract forbids.

    If this test goes red because the value came back instead of raising, an
    absorbing arm has been added and ``check-prerequisites`` is now capable of
    committing to the wrong branch on a corrupt ``meta.json``. That is a
    regression, not a simplification.
    """
    root, mission_dir = _mission_dir(tmp_path, _MALFORMED_META)

    with pytest.raises(MissionMetaReadError) as excinfo:
        _resolve_feature_target_branch(mission_dir, root)

    assert "meta.json" in str(excinfo.value)
    assert "fail-closed" in str(excinfo.value), (
        "the refusal must remain diagnosable -- it is the only signal the operator "
        f"gets that the file is corrupt: {str(excinfo.value)!r}"
    )


def test_f1_target_branch_read_still_falls_back_when_the_field_is_merely_absent(
    tmp_path: Path,
) -> None:
    """Positive control: the *absent* arm is untouched by the refusal above.

    Without this, the test above would be satisfied by a site that raises on
    everything -- including the ordinary "no meta.json yet" case, which must keep
    degrading to the current branch. This is the assertion that distinguishes
    "fail-closed on corruption" from "fail-closed on absence", the exact
    distinction ``core/paths.py``'s reader owns.
    """
    root, mission_dir = _mission_dir(tmp_path, None)

    result = _resolve_feature_target_branch(mission_dir, root)

    assert isinstance(result, str) and result, (
        "the absent-file arm must still resolve a branch string, not raise or "
        f"return empty: {result!r}"
    )


def test_f1_occurrence_gate_refuses_on_corruption_rather_than_passing(
    tmp_path: Path,
) -> None:
    """``ensure_occurrence_classification_ready`` must RAISE, not pass, on corrupt meta.

    The gate's ``meta is None`` branch returns ``GateResult(passed=True)`` -- the
    correct answer for a mission with no ``meta.json``. If an absorbing arm were
    added, a **corrupt** ``meta.json`` would take that same branch and the
    bulk-edit occurrence gate would report **passed** for a mission whose
    ``change_mode`` could not be read. That is a fail-open on a guardrail, which
    is why the absent arm here is intended.
    """
    _, mission_dir = _mission_dir(tmp_path, _MALFORMED_META)

    with pytest.raises(MissionMetaReadError):
        ensure_occurrence_classification_ready(mission_dir)


def test_f1_occurrence_gate_still_passes_for_absent_and_non_bulk_edit_meta(
    tmp_path: Path,
) -> None:
    """Positive control for the gate: absent and valid-non-bulk-edit still pass.

    Pins that the refusal above is specific to corruption and has not become a
    blanket refusal, which would block finalize-tasks for every ordinary mission.
    """
    _, absent_dir = _mission_dir(tmp_path / "absent", None)
    absent_result = ensure_occurrence_classification_ready(absent_dir)
    assert absent_result.passed is True
    assert absent_result.change_mode is None

    payload: dict[str, Any] = {
        "mission_id": "01KWP04F1GATEPIN7X9QZTBVKM",
        "mission_slug": "wp04-f1-absent-arm",
    }
    _, valid_dir = _mission_dir(tmp_path / "valid", json.dumps(payload))
    valid_result = ensure_occurrence_classification_ready(valid_dir)
    assert valid_result.passed is True, (
        "an ordinary non-bulk-edit mission with valid meta must still pass the gate"
    )
