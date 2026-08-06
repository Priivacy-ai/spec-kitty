"""Scope: #2804 (P0) -- ``spec-kitty merge`` clobbers filled coordination gate
artifacts (``acceptance-matrix.json`` / ``issue-matrix.json``) back to their
empty placeholder scaffold, on the integration branch, AFTER the done-gate has
already consumed their filled contents.

**WP11 (FR-008) campsite note:** originally fixtured with the retired
``issue-matrix.md`` shape. WP05 migrated ``issue-matrix`` to the structured
``.json`` artifact (C-008; no ``.md`` is written by any canonical path any
more) and WP11 repointed the merge-driver registration to match
(``kitty-specs/**/issue-matrix.json``) -- the ``.md`` fixture below would
silently stop exercising ANY reconcile driver (falling through to git's
default ``-X theirs`` text merge), so it is updated to the real ``.json``
row schema here. This file is not WP11-owned, but no other work package
references it (checked); the update is a direct, necessary consequence of
the T041 registration repoint, not unrelated scope creep. WP11 also
replaces the acceptance/issue-matrix drivers' whole-file "more-filled-side"
heuristic with a row-aware, base-aware (3-way) reconciler (FR-008) -- the
assertions below were updated to require that the real, accepted evidence
is never silently discarded (the #2804 invariant), matching the new
driver's behavior verified against this exact fixture.

**WP07 (mission ``meta-fail-closed-3162-01KZ7FSQ``, FR-009/FR-010/FR-011)
re-pin.** This module was previously framed as "intentionally FAILING until the
product defect is fixed". That framing is now FALSE and has been removed: the
red was an **inverted red** -- honestly red on ``main``, but the *assertions*
were wrong, not the product. Both assertions under the single
``# --- CONTRACT (RED on base) ---`` banner have been re-pinned to what the
current merge design actually guarantees. ``Q10`` is **settled: keep the
marker.**

What the two assertions pin NOW:

1. **Admissible verdict.** ``overall_verdict`` is one of the design's
   admissible values (:data:`ADMISSIBLE_MERGED_VERDICTS`); the scaffold's
   placeholder must never win outright. It deliberately **admits** ``pending``.
2. **Evidence survival.** The accepted evidence handle
   (:data:`ACCEPTED_EVIDENCE_HANDLE`) must still appear in the merged document
   -- including inside a structured conflict marker. Negatively controlled
   against the take-theirs / scaffold-clobber shape by
   :func:`test_widened_2804_assertion_rejects_wrong_verdict`.

**Why the shape changed.** Assertion 1 was ``overall_verdict == "pass"`` and
assertion 2 was ``SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)``. Under
the **row-union authority model** shipped as ``#3076``'s FR-008 the union
admits BOTH sides' rows, so the merged document legitimately contains the
scaffold row -- whose ``description``/``notes`` *are* the marker -- and
legitimately computes ``pending``. The cross-file sibling
``tests/specify_cli/cli/commands/test_row_aware_merge_driver.py::
test_merge_driver_acceptance_matrix_writes_result_to_ours`` pins
``merged["overall_verdict"] == "pending"`` for exactly this union shape; that
sibling is **correct and untouched**. The marker moved, not the design.

**The product defect is FILED, NOT FIXED here** (mission constraint ``C-006``;
filed per ``C-009``). One admitted scaffold row makes the aggregate
``overall_verdict`` ``pending`` (``src/specify_cli/acceptance/matrix.py:263``,
``any(v == "pending")`` dominates), and
``src/specify_cli/acceptance/gates_core.py:525``
(``verdict = acc_matrix.overall_verdict``) feeds that straight into the
acceptance gate, where ``:528-529`` turns it into a blocking activity issue. The
candidate fix -- a scaffold-row suppression rule in the reconciler -- was
**rejected for this mission**: the driver has zero scaffold awareness today and
the rule would amend the ``#3076`` FR-008 authority model.
Product defect: https://github.com/Priivacy-ai/spec-kitty/issues/3231.
Superseding issue for #2804:
https://github.com/Priivacy-ai/spec-kitty/issues/3232. Original tracking issue:
https://github.com/Priivacy-ai/spec-kitty/issues/2804 (**superseded, not
reopened**). Returning-red bisect: #3138.

Do NOT xfail/skip/quarantine this module to green, and do NOT delete assertion
2 -- its content is the only remaining executable statement of the real #2804
contract. The unit gate that used to hold this invariant,
``tests/merge/test_gate_artifact_merge_drivers_2804.py``, was deleted in
``b04da00e1`` (-249 lines); no requirement currently owns its absence, which is
cited in the superseding issue and deliberately NOT restored here.

Root-cause mechanism (confirmed by replaying the real incident's git history --
mission ``charter-deadcode-noop-campsite-01KXW0NY``, reflog entries
``aa9126844`` "Record acceptance commit for ..." -> ``2be339a0c`` "squash merge
of mission" -> the operator's manual recovery commit "restore terminal
issue-matrix + acceptance-matrix (merge reset them to placeholders)"):

``acceptance-matrix.json`` / ``issue-matrix.json`` are COORD-partition kinds
(``mission_runtime.artifacts._PLACEMENT_ARTIFACT_KINDS``). ``finalize-tasks``
scaffolds their placeholder INSIDE the mission-branch checkout (the
finalize-tasks / lane-provisioning step runs there), while ``spec-kitty
accept``'s residual-artifact commit lands them on the PRIMARY checkout
(target_branch) -- a *different* branch, per the sibling, already-open #2404
("accept reads/writes acceptance-matrix.json via the primary checkout, not the
coordination surface"). Because the file is introduced FOR THE FIRST TIME
independently on each side (an add/add divergence -- the mission branch never
carries the accept-authored fill, and the target branch never carried the
placeholder), ``spec-kitty merge``'s mission->target squash step
(``specify_cli.lanes.merge._merge_branch_into``, ``git merge --squash -X
theirs <mission_branch>``) resolves the add/add conflict by taking "theirs"
(the mission branch's stale placeholder) -- silently discarding the target's
already-filled, already-accepted content. This is orthogonal to the
``finalize-tasks`` scaffolder itself, which is idempotent and never touches an
existing file (``scaffold_acceptance_matrix``/``scaffold_issue_matrix``: "if
path.exists(): return path") -- the reset happens purely through ``-X theirs``
conflict resolution during the REAL merge branch-integration step, not through
any scaffold call.

This module reproduces the clobber through the real, pre-existing merge entry
point (``specify_cli.cli.commands.merge._run_lane_based_merge`` ->
``specify_cli.merge.executor`` -> ``specify_cli.lanes.merge.
integrate_mission_into_target`` -> the real ``git merge --squash -X theirs``
subprocess), never a hand-rolled reimplementation of the merge or of git's
conflict resolution. The harness mirrors the proven coord-topology
lane-based-merge fixture in ``tests/merge/
test_issue_2711_merge_rollback_resume_coherence.py`` (mocking only side
effects that are irrelevant to git content -- dossier sync, stale-assertion
scan, merge-gate policy, baseline-commit bookkeeping, done-transition
recording) while leaving the git plumbing (branch creation, lane merge,
mission->target squash merge) entirely real.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Import the status package before any coordination submodule -- mirrors the
# production CLI entrypoint's import order (see test_issue_2711's identical
# guard) so this module stays importable under ``PYTHONPATH=src``.
import specify_cli.status  # noqa: F401  # import-order guard

from specify_cli.acceptance.matrix import (
    SCAFFOLD_TODO_MARKER,
    VERDICT_PASS_PENDING_CONSOLIDATION,
    AcceptanceMatrix,
)
from specify_cli.cli.commands.merge import _run_lane_based_merge
from specify_cli.cli.commands.merge_driver import reconcile_acceptance_matrix_documents
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json
from specify_cli.merge.config import MergeStrategy

pytestmark = [pytest.mark.regression, pytest.mark.git_repo, pytest.mark.non_sandbox]

MID8 = "01KXW0NY"
MISSION_ID = f"01KXW0NY0000000000000000{MID8[-2:]}"
MISSION_SLUG = f"charter-deadcode-noop-campsite-{MID8}"
MISSION_BRANCH = f"kitty/mission-{MISSION_SLUG}"
LANE_ID = "lane-a"
LANE_CODE = "src/charter/generator.py"
WP_ID = "WP01"

# --- WP07 (FR-009): the design's admissible post-merge verdicts -------------
# ``overall_verdict`` is a COMPUTED property, never a stored/merged field
# (``src/specify_cli/acceptance/matrix.py:248-271``,
# ``AcceptanceMatrix.overall_verdict``), with domain
# {``pass``, ``pending``, ``fail``, ``pass_pending_consolidation``}.
#
# ``"fail"`` IS a concrete disallowed verdict and is reachable from a
# one-criterion fixture (``matrix.py:259``, ``if any(v == "fail" for v in
# criterion_results)``), so this predicate is genuinely falsifiable -- see
# ``test_widened_2804_assertion_rejects_wrong_verdict``.
#
# **But ``"fail"`` alone is INSUFFICIENT evidence of non-vacuity.** ``pending``
# is the #2804 defect's own signature and must nevertheless be ADMITTED here,
# because the cross-file sibling
# ``tests/specify_cli/cli/commands/test_row_aware_merge_driver.py::
# test_merge_driver_acceptance_matrix_writes_result_to_ours`` pins
# ``merged["overall_verdict"] == "pending"`` for exactly this union shape.
# A predicate of the form ``verdict in {"pass", "pending"}`` therefore passes
# with the regression fully present. Assertion 2 (evidence survival) is what
# carries the falsifiability; see ``_assert_2804_acceptance_contract``.
ADMISSIBLE_MERGED_VERDICTS: frozenset[str] = frozenset(
    {"pass", "pending", VERDICT_PASS_PENDING_CONSOLIDATION}
)

# --- Realistic, production-shaped acceptance-matrix.json ------------------
# Mirrors the real (pre-clobber) evidence recorded for the incident mission
# that surfaced #2804 -- multiple genuinely-verified FR criteria, real
# reviewer/evidence text, ``overall_verdict: pass`` -- not a toy placeholder.
FILLED_ACCEPTANCE_MATRIX: dict[str, object] = {
    "mission_slug": MISSION_SLUG,
    "mission_number": "",
    "mission_type": "software-dev",
    "overall_verdict": "pass",
    "criteria": [
        {
            "criterion_id": "FR-001",
            "description": (
                "Delete charter.generator module (CharterDraft/"
                "build_charter_draft/write_charter) + its __init__ import "
                "and __all__ entries."
            ),
            "proof_type": "automated_test",
            "evidence": (
                "WP01 (commit d5b8324f9): src/charter/generator.py deleted; "
                "src/charter/__init__.py import (was line 31) + 3 __all__ "
                "entries removed. git grep finds zero live src refs. "
                "uv run pytest tests/charter/test_generator.py "
                "tests/architectural/test_no_dead_modules.py -> 6 passed. "
                "Net -156 LOC."
            ),
            "pass_fail": "pass",
            "verified_by": "reviewer-renata/opus (per-WP) + orchestrator synthesis",
            "verified_at": "2026-07-19T03:20:00+00:00",
            "notes": "LM-4 clear: no charter.md scaffold path dropped.",
        },
        {
            "criterion_id": "FR-003",
            "description": (
                "Delete charter.extractor module + its test-only references "
                "(dedicated tests retired; incidental fixtures reconstructed)."
            ),
            "proof_type": "automated_test",
            "evidence": (
                "WP02 (commit 8a0a1fcf2): src/charter/extractor.py (577 LOC) "
                "+ 5 dedicated test files deleted. 2 incidental fixtures "
                "reconstructed inline so live assertions survive (31 passed)."
            ),
            "pass_fail": "pass",
            "verified_by": "reviewer-renata/opus (per-WP) + orchestrator synthesis",
            "verified_at": "2026-07-19T03:20:00+00:00",
            "notes": "Net -1685/+55 LOC.",
        },
    ],
    "negative_invariants": [],
}

FILLED_ISSUE_MATRIX: dict[str, object] = {
    "schema_version": 1,
    "rows": {
        "#2373": {
            "verdict": "verified-already-fixed",
            "evidence_ref": "commit d5b8324f9 (WP01)",
            "title": "dead-code baseline noop-stability",
            "scope": None,
            "wp": None,
            "fr": None,
            "nfr": None,
            "sc": None,
            "repo": None,
        }
    },
}

# --- The empty scaffold placeholder produced by ``scaffold_acceptance_matrix``
# / ``scaffold_issue_matrix`` at finalize-tasks time (byte-identical shape to
# the real product scaffolder -- this is what the mission branch still
# carries, since it never sees the later accept-authored fill). ---
PLACEHOLDER_ACCEPTANCE_MATRIX: dict[str, object] = {
    "mission_slug": MISSION_SLUG,
    "criteria": [
        {
            "criterion_id": "AC-001",
            "description": SCAFFOLD_TODO_MARKER,
            "proof_type": "automated_test",
            "pass_fail": "pending",
            "evidence": None,
            "notes": SCAFFOLD_TODO_MARKER,
        }
    ],
    "negative_invariants": [],
}
PLACEHOLDER_ISSUE_MATRIX: dict[str, object] = {
    "schema_version": 1,
    "rows": {
        "#2373": {
            "verdict": "unknown",
            "evidence_ref": "<link or commit>",
            "title": "<fill at WP-implementation time>",
            "scope": None,
            "wp": None,
            "fr": None,
            "nfr": None,
            "sc": None,
            "repo": None,
        }
    },
}


# --- WP07 (FR-009): the accepted-evidence handle, and the ONE shared predicate
# both the marker and its falsifiability companion call ------------------------
#
# The handle is the commit already carried by ``FILLED_ACCEPTANCE_MATRIX``'s
# ``FR-001`` evidence (``:117-124`` above) -- the acceptance-matrix twin of the
# ``"verified-already-fixed"`` handle the issue-matrix sibling at the bottom of
# this module already uses. It appears nowhere in
# ``PLACEHOLDER_ACCEPTANCE_MATRIX``, which is what makes the take-theirs
# negative control meaningful.
ACCEPTED_EVIDENCE_HANDLE = "d5b8324f9"


def _assert_evidence_handle_fixture_self_control() -> None:
    """Two-way fixture self-control for :data:`ACCEPTED_EVIDENCE_HANDLE`.

    Neither direction is catchable by the merged-document assertion alone:
    a handle **absent** from the filled side makes the evidence-survival pin
    unsatisfiable (a permanent false red), while a handle **present** on the
    placeholder side makes it vacuous (it would survive even a total
    take-theirs clobber). Asserted on every call so the pin can never go
    silently vacuous through a later fixture edit.
    """
    assert ACCEPTED_EVIDENCE_HANDLE in json.dumps(FILLED_ACCEPTANCE_MATRIX), (
        f"fixture self-control: the accepted evidence handle "
        f"{ACCEPTED_EVIDENCE_HANDLE!r} is no longer present in "
        "FILLED_ACCEPTANCE_MATRIX -- the evidence-survival pin below is "
        "unsatisfiable by construction, not red because of a product defect."
    )
    assert ACCEPTED_EVIDENCE_HANDLE not in json.dumps(PLACEHOLDER_ACCEPTANCE_MATRIX), (
        f"fixture self-control: the accepted evidence handle "
        f"{ACCEPTED_EVIDENCE_HANDLE!r} leaked into PLACEHOLDER_ACCEPTANCE_MATRIX "
        "-- the evidence-survival pin below would then be VACUOUS: it would "
        "survive even a total take-theirs clobber of the accepted content."
    )


def _assert_2804_acceptance_contract(post_matrix: Mapping[str, Any]) -> None:
    """The re-pinned #2804 acceptance-matrix contract, as ONE shared predicate.

    Called by :func:`test_merge_resets_filled_gate_artifacts_to_placeholder`
    (the marker, against the document a REAL squash merge left on the
    integration branch) and by
    :func:`test_widened_2804_assertion_rejects_wrong_verdict` (the
    falsifiability companion, against the defect's own fixture). The companion
    must exercise **this** predicate, not a paraphrase of it -- a copy proves a
    copy falsifiable and the marker nothing at all.

    Assertion 1 -- the merged verdict is one of the design's admissible values
    (:data:`ADMISSIBLE_MERGED_VERDICTS`); the scaffold's placeholder must never
    win outright.

    Assertion 2 -- **evidence survival**: the accepted evidence handle must
    appear somewhere in the merged document, INCLUDING inside a structured
    conflict marker. This is the clause that carries falsifiability, because
    ``pending`` (the #2804 defect's own signature) is deliberately admitted by
    assertion 1.
    """
    _assert_evidence_handle_fixture_self_control()
    verdict = post_matrix.get("overall_verdict")
    assert verdict in ADMISSIBLE_MERGED_VERDICTS, (
        "#2804 (assertion 1, re-pinned): spec-kitty merge left "
        f"acceptance-matrix.json's overall_verdict at {verdict!r}, outside the "
        f"design's admissible verdicts {sorted(ADMISSIBLE_MERGED_VERDICTS)!r} -- "
        "the scaffold placeholder won outright over the target's "
        f"already-accepted fill. Post-merge content: {post_matrix!r}"
    )
    assert ACCEPTED_EVIDENCE_HANDLE in json.dumps(post_matrix), (
        "#2804 (assertion 2, evidence survival): spec-kitty merge discarded the "
        f"target's real, accepted evidence ({ACCEPTED_EVIDENCE_HANDLE!r}) "
        "without leaving any trace of it -- not even inside a structured "
        f"conflict marker. Post-merge content: {post_matrix!r}"
    )


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), check=True, capture_output=True, text=True)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", "-C", str(repo), *args], cwd=repo)


def _init_git_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-qb", "main", str(repo)], cwd=repo)
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")


def _write_meta(feature_dir: Path) -> None:
    meta = {
        "mission_slug": MISSION_SLUG,
        "mission_id": MISSION_ID,
        "mid8": MID8,
        "mission_number": None,
        "mission_type": "software-dev",
        "target_branch": "main",
        "purpose_tldr": "dead-code burndown + #2373/#1914 no-op-stability",
        "purpose_context": "regression fixture for #2804",
    }
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_manifest(feature_dir: Path) -> LanesManifest:
    manifest = LanesManifest(
        version=1,
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_SLUG,
        mission_branch=MISSION_BRANCH,
        target_branch="main",
        lanes=[
            ExecutionLane(
                lane_id=LANE_ID,
                wp_ids=(WP_ID,),
                write_scope=(LANE_CODE,),
                predicted_surfaces=("code",),
                depends_on_lanes=(),
                parallel_group=0,
            )
        ],
        computed_at=datetime.now(UTC).isoformat(),
        computed_from="test-fixture",
    )
    write_lanes_json(feature_dir, manifest)
    return manifest


def _write_wp_file(feature_dir: Path) -> None:
    (feature_dir / "tasks" / f"{WP_ID}-work.md").write_text(
        "---\n"
        f"work_package_id: {WP_ID}\n"
        f"title: {WP_ID} retire charter.generator\n"
        "agent: implementer-bot\n"
        "review_status: approved\n"
        "reviewed_by: reviewer-renata\n"
        "---\n"
        f"# {WP_ID}\n",
        encoding="utf-8",
    )


def _approved_event() -> dict[str, object]:
    return {
        "actor": "reviewer-renata",
        "at": datetime.now(UTC).isoformat(),
        "event_id": "01HXYZAPPR000000000000002804A",
        "evidence": None,
        "execution_mode": "worktree",
        "feature_slug": MISSION_SLUG,
        "force": False,
        "from_lane": "in_review",
        "reason": None,
        "review_ref": f"review-{WP_ID}",
        "to_lane": "approved",
        "wp_id": WP_ID,
    }


def _bootstrap_mission(repo: Path) -> Path:
    """Build the real #2804 divergence: mission branch and target each
    introduce ``acceptance-matrix.json`` / ``issue-matrix.json`` INDEPENDENTLY
    (an add/add divergence), matching the real incident's history:

    1. Shared ancestor WITHOUT either gate artifact (meta/lanes/WP/status only).
    2. Mission branch (+ lane) fork here, then the mission branch commits its
       OWN ``finalize-tasks``-style placeholder scaffold (mirrors finalize-
       tasks running against the mission-branch checkout).
    3. The PRIMARY checkout (still on target_branch ``main`` -- never switched
       to the mission branch) commits the FILLED, accept-authored matrix
       DIRECTLY onto ``main`` -- the first time main ever sees these files at
       all (mirrors #2404: accept's residual-artifact commit lands on the
       primary checkout, a branch distinct from the mission integration
       branch).
    """
    feature_dir = repo / "kitty-specs" / MISSION_SLUG
    (feature_dir / "tasks").mkdir(parents=True)
    _write_meta(feature_dir)
    _write_manifest(feature_dir)
    _write_wp_file(feature_dir)
    (feature_dir / "status.events.jsonl").write_text(
        json.dumps(_approved_event(), sort_keys=True) + "\n", encoding="utf-8"
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", f"chore({MISSION_SLUG}): bootstrap (no gate artifacts yet)")

    # --- mission branch + lane fork BEFORE the gate artifacts exist anywhere ---
    _git(repo, "branch", MISSION_BRANCH)
    _git(repo, "checkout", MISSION_BRANCH)
    (feature_dir / "acceptance-matrix.json").write_text(
        json.dumps(PLACEHOLDER_ACCEPTANCE_MATRIX, indent=2) + "\n", encoding="utf-8"
    )
    (feature_dir / "issue-matrix.json").write_text(
        json.dumps(PLACEHOLDER_ISSUE_MATRIX, indent=2) + "\n", encoding="utf-8"
    )
    _git(repo, "add", "kitty-specs")
    _git(
        repo,
        "commit",
        "-m",
        f"tasks({MISSION_SLUG}): finalize -- scaffold acceptance/issue matrix",
    )

    lane_branch = f"{MISSION_BRANCH}-{LANE_ID}"
    _git(repo, "branch", lane_branch, MISSION_BRANCH)
    _git(repo, "checkout", lane_branch)
    code_path = repo / LANE_CODE
    code_path.parent.mkdir(parents=True, exist_ok=True)
    code_path.write_text("# generator module removed by WP01\n", encoding="utf-8")
    _git(repo, "add", LANE_CODE)
    _git(repo, "commit", "-m", f"feat({MISSION_SLUG}): {WP_ID} retire charter.generator")
    _git(repo, "checkout", "main")

    # --- primary checkout (still on target_branch) authors + accepts the
    # FILLED matrix directly onto main; the mission branch never sees this. ---
    (feature_dir / "acceptance-matrix.json").write_text(
        json.dumps(FILLED_ACCEPTANCE_MATRIX, indent=2) + "\n", encoding="utf-8"
    )
    (feature_dir / "issue-matrix.json").write_text(
        json.dumps(FILLED_ISSUE_MATRIX, indent=2) + "\n", encoding="utf-8"
    )
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-m", f"Finalize acceptance artifacts for {MISSION_SLUG}")

    return feature_dir


def _merge_external_mocks() -> ExitStack:
    """Mock ONLY side effects that are irrelevant to git tree content: merge
    gates/policy (no policy config in this minimal fixture), the stale-
    assertion advisory scan, dossier sync (external SaaS I/O), diff-summary /
    mission-closed emission (cosmetic), baseline-commit bookkeeping, and
    done-transition recording (a legacy-topology status-write concern
    unrelated to the #2804 file-content clobber under test). The git
    plumbing under test -- lane consolidation and the mission->target squash
    merge with ``-X theirs`` -- is left completely real.
    """
    patches = {
        "run_check": patch("specify_cli.merge.executor.run_check"),
        "sparse": patch("specify_cli.merge.executor.require_no_sparse_checkout"),
        "preflight": patch("specify_cli.cli.commands.merge._enforce_git_preflight"),
        "review_consistency": patch(
            "specify_cli.merge.executor._enforce_review_artifact_consistency"
        ),
        "status_history": patch(
            "specify_cli.merge.executor._enforce_canonical_status_history"
        ),
        "hollow": patch("specify_cli.merge.executor._warn_or_confirm_hollow_reviews"),
        "baseline_record": patch(
            "specify_cli.merge.executor._record_baseline_merge_commit", return_value=None
        ),
        "baseline_assert": patch(
            "specify_cli.merge.executor._assert_baseline_merge_commit_on_target"
        ),
        "done_on_target": patch(
            "specify_cli.merge.executor._assert_merged_wps_done_on_target"
        ),
        "record_done": patch(
            "specify_cli.merge.executor._record_merged_wps_done_for_merge"
        ),
        "dossier": patch(
            "specify_cli.merge.executor.trigger_feature_dossier_sync_if_enabled"
        ),
        "mission_closed": patch("specify_cli.merge.executor.emit_mission_closed"),
        "diff_summary": patch("specify_cli.merge.executor._emit_merge_diff_summary"),
        "gates": patch("specify_cli.policy.merge_gates.evaluate_merge_gates"),
        "policy": patch("specify_cli.policy.config.load_policy_config"),
        "remote": patch("specify_cli.merge.executor.has_remote", return_value=False),
    }
    stack = ExitStack()
    mocks = {name: stack.enter_context(p) for name, p in patches.items()}
    gate_eval = MagicMock()
    gate_eval.overall_pass = True
    gate_eval.gates = []
    mocks["gates"].return_value = gate_eval
    policy = MagicMock()
    policy.merge_gates = []
    policy.risk = MagicMock()
    mocks["policy"].return_value = policy
    stale_report = MagicMock()
    stale_report.findings = []
    mocks["run_check"].return_value = stale_report
    return stack


def test_merge_resets_filled_gate_artifacts_to_placeholder(tmp_path: Path) -> None:
    """Real-merge reproduction of #2804, re-pinned by WP07.

    ``spec-kitty merge`` must NEVER discard an already-filled, already-accepted
    ``acceptance-matrix.json`` / ``issue-matrix.json``. Under the row-union
    authority model (``#3076`` FR-008) "must not discard" no longer means "the
    placeholder must be absent" -- the union legitimately admits the scaffold
    row -- so the contract is pinned as: the merged verdict stays inside the
    design's admissible values, AND the accepted evidence survives somewhere in
    the merged document, including inside a structured conflict marker. See
    :func:`_assert_2804_acceptance_contract` (the shared predicate) and the
    module docstring for why the shape changed and where the product defect is
    filed. Do NOT xfail/skip/quarantine to green.
    """
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    feature_dir = _bootstrap_mission(repo)

    # --- Precondition witnesses (BEFORE the act): the primary checkout
    # genuinely carries the FILLED, non-placeholder artifacts pre-merge --
    # so any post-merge placeholder can only be the merge's own doing, never
    # a fixture that started out empty. ---
    pre_matrix = json.loads((feature_dir / "acceptance-matrix.json").read_text(encoding="utf-8"))
    assert pre_matrix["overall_verdict"] == "pass", "precondition: fixture must start FILLED"
    assert SCAFFOLD_TODO_MARKER not in json.dumps(pre_matrix), (
        "precondition: fixture must start FILLED, not the scaffold placeholder"
    )
    pre_issue_matrix = json.loads((feature_dir / "issue-matrix.json").read_text(encoding="utf-8"))
    assert pre_issue_matrix["rows"]["#2373"]["verdict"] == "verified-already-fixed", (
        "precondition: fixture must start with a real terminal verdict row"
    )

    with _merge_external_mocks():
        _run_lane_based_merge(
            repo_root=repo,
            mission_slug=MISSION_SLUG,
            push=False,
            delete_branch=False,
            remove_worktree=True,
            strategy=MergeStrategy.SQUASH,
            allow_sparse_checkout=True,
        )

    # --- Non-vacuity witness: the merge genuinely ran to completion and
    # advanced main with a real squash-merge commit (mission_number assigned,
    # the code file landed) -- so a placeholder result below is the merge's
    # own reset, not a merge that silently no-op'd or failed. ---
    code_landed = (repo / LANE_CODE).exists()
    assert code_landed, (
        "precondition: the merge must have genuinely integrated the mission "
        "branch into main (lane code file missing -- merge did not run)"
    )
    meta_after = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta_after.get("mission_number") == 1, (
        "precondition: merge must have assigned a mission_number on target "
        f"(merge did not complete the mission->target integration); got {meta_after.get('mission_number')!r}"
    )

    # --- CONTRACT (RED on base): the permanent record left on the
    # integration branch must still be the FILLED content, not the reset
    # scaffold placeholder. On buggy main, the ``-X theirs`` squash-merge
    # conflict resolution takes the mission branch's stale placeholder over
    # target's already-accepted fill. ---
    post_matrix = json.loads((feature_dir / "acceptance-matrix.json").read_text(encoding="utf-8"))
    # WP07 (FR-009): re-pinned. Under the row-union authority model (`#3076`
    # FR-008) a genuine same-key divergence with no base to arbitrate is a
    # structured conflict, NEVER a silent pick either way -- so, exactly as the
    # issue-matrix sibling below already says, both clauses are satisfied
    # whether the merge cleanly resolves to the real verdict or surfaces it
    # inside a structured conflict marker. What must never happen is the
    # scaffold's placeholder verdict winning OUTRIGHT, or the accepted evidence
    # vanishing without a trace.
    #
    # Assertion 2 was `SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)`. It
    # is RE-PINNED, NOT DELETED: under the row-union it is unsatisfiable BY
    # DESIGN -- the union admits the scaffold row, whose `description` and
    # `notes` ARE the marker (see PLACEHOLDER_ACCEPTANCE_MATRIX above). Measured
    # through the reconciler, control first:
    #     CONTROL filled fixture contains marker?  False
    #     merged criterion_ids: ['AC-001', 'FR-001', 'FR-003']
    #     overall_verdict: pending
    #     POST contains SCAFFOLD_TODO_MARKER?      True
    # Its CONTENT is the real #2804 contract, so it moves to evidence survival
    # rather than being dropped. Both clauses live in ONE shared predicate that
    # the falsifiability companion calls too.
    _assert_2804_acceptance_contract(post_matrix)

    post_issue_matrix = json.loads((feature_dir / "issue-matrix.json").read_text(encoding="utf-8"))
    merged_row = post_issue_matrix["rows"]["#2373"]
    # WP11 (FR-008): the row-aware driver reconciles the SAME row key (#2373)
    # present with genuinely differing content on both sides (an add/add, no
    # common base -- exactly this fixture's shape). Per the algorithm contract
    # (contracts/merge-driver-algorithm.md), a genuine same-key divergence with
    # no base to arbitrate is a structured conflict, NEVER a silent pick either
    # way -- so the assertion is deliberately narrower than "byte-identical to
    # FILLED": the scaffold's placeholder verdict must never win OUTRIGHT, and
    # the real, accepted evidence must never be silently discarded (both are
    # satisfied whether the merge cleanly resolves to the real verdict or
    # surfaces it inside a structured conflict marker).
    assert merged_row["verdict"] != "unknown", (
        "#2804 (row-aware, FR-008): spec-kitty merge let the mission branch's "
        f"scaffold verdict ('unknown') win outright over the target's real, "
        f"accepted verdict. Post-merge row: {merged_row!r}"
    )
    assert "verified-already-fixed" in json.dumps(merged_row), (
        "#2804 (row-aware, FR-008): spec-kitty merge discarded the target's "
        "real, accepted verdict ('verified-already-fixed') without leaving any "
        f"trace of it (not even in a structured conflict marker). Post-merge "
        f"row: {merged_row!r}"
    )


# ---------------------------------------------------------------------------
# WP07 (SC-010) -- falsifiability companion for the re-pinned pair above.
# ---------------------------------------------------------------------------


def _take_theirs_acceptance_document() -> dict[str, Any]:
    """The #2804 defect's **own** fixture: the take-theirs / scaffold-clobber
    document.

    This is exactly the shape the pre-fix merge produced -- the mission
    branch's placeholder winning outright, so the criteria are reset to
    ``PLACEHOLDER_ACCEPTANCE_MATRIX`` alone. Built through the real
    :class:`AcceptanceMatrix` so ``overall_verdict`` is COMPUTED (``pending``),
    not hand-asserted, and the accepted evidence handle is **absent**.
    """
    return dict(AcceptanceMatrix.from_dict(PLACEHOLDER_ACCEPTANCE_MATRIX).to_dict())


def _row_union_merged_acceptance_document() -> dict[str, Any]:
    """The positive twin: what the shipped row-aware reconciler actually
    produces for this fixture pair (FILLED as *ours*, PLACEHOLDER as *theirs*,
    empty base -- the add/add divergence #2804 is about)."""
    return dict(
        reconcile_acceptance_matrix_documents(
            {}, FILLED_ACCEPTANCE_MATRIX, PLACEHOLDER_ACCEPTANCE_MATRIX
        )
    )


def _one_criterion_fail_document() -> dict[str, Any]:
    """A one-criterion document whose single criterion is ``pass_fail: "fail"``,
    so ``overall_verdict`` computes ``"fail"`` (``matrix.py:259``)."""
    doc: dict[str, Any] = {
        "mission_slug": MISSION_SLUG,
        "criteria": [
            {
                "criterion_id": "FR-001",
                "description": "one-criterion disallowed-verdict witness",
                "proof_type": "automated_test",
                "evidence": f"WP01 (commit {ACCEPTED_EVIDENCE_HANDLE}): witness",
                "pass_fail": "fail",
                "notes": None,
            }
        ],
        "negative_invariants": [],
    }
    return dict(AcceptanceMatrix.from_dict(doc).to_dict())


def test_widened_2804_assertion_rejects_wrong_verdict() -> None:
    """SC-010: the re-pinned #2804 pair is falsifiable **by the defect it
    exists to catch**, not by an unrelated disallowed value.

    **Anti-vacuity argument (this is the whole point of the test).**
    ``overall_verdict`` has domain {``pass``, ``pending``, ``fail``,
    ``pass_pending_consolidation``}. The cross-file sibling
    ``test_merge_driver_acceptance_matrix_writes_result_to_ours`` pins
    ``pending`` for exactly this union shape, so the widened predicate MUST
    admit ``pending`` -- and ``pending`` is the #2804 defect's **own
    signature**. A predicate of the form ``verdict in {"pass", "pending"}``
    therefore passes with the regression fully present, and a companion test
    fed only a ``"fail"`` fixture reports "non-vacuous" about a value that has
    nothing to do with the defect. That is precisely how ``SC-010`` passed
    while the defect was fully present. So the failing case here is the
    **defect's own fixture** -- the take-theirs / scaffold-clobber document, in
    which the criteria are reset to the placeholder and the accepted evidence
    handle is absent -- and it is **assertion 2 (evidence survival)** that
    carries the falsifiability.

    The ``"fail"`` case below is a **secondary witness, explicitly insufficient
    on its own**: it records that ``"fail"`` is a concrete, reachable
    disallowed verdict for assertion 1, and nothing more. It is NOT ``SC-010``
    evidence.

    Fast by construction: this exercises the shared predicate and the
    reconciler directly and never runs the squash-merge harness.
    """
    # --- POSITIVE TWIN: the shared predicate passes on the real merged
    # document. A negative with no positive twin is the vacuous gate the
    # charter's architectural-gate-non-vacuity standing order forbids. ---
    merged = _row_union_merged_acceptance_document()
    assert merged["overall_verdict"] == "pending", (
        "positive twin precondition: the row-union merged document computes "
        f"'pending' for this fixture pair; got {merged['overall_verdict']!r}"
    )
    _assert_2804_acceptance_contract(merged)

    # --- THE SC-010 CASE: the defect's own fixture. ---
    take_theirs = _take_theirs_acceptance_document()
    assert take_theirs["overall_verdict"] == "pending", (
        "defect-fixture precondition: the take-theirs clobber computes the "
        f"defect's own signature 'pending'; got {take_theirs['overall_verdict']!r}"
    )
    assert ACCEPTED_EVIDENCE_HANDLE not in json.dumps(take_theirs), (
        "defect-fixture precondition: the accepted evidence handle must be "
        "ABSENT from the take-theirs clobber -- that absence IS the defect"
    )
    with pytest.raises(AssertionError) as excinfo:
        _assert_2804_acceptance_contract(take_theirs)

    # The pair must fail, and the failure must be attributable to the
    # EVIDENCE-SURVIVAL clause -- so a future edit that moves the failure to
    # some other clause (or to the fixture self-control) is visible here.
    message = str(excinfo.value)
    assert "assertion 2, evidence survival" in message, (
        "SC-010: the re-pinned pair must fail on the defect's own fixture via "
        "the EVIDENCE-SURVIVAL clause. It failed via some other clause "
        f"instead, which is not SC-010 evidence. Raised: {message!r}"
    )
    assert ACCEPTED_EVIDENCE_HANDLE in message, (
        "SC-010: the failure message must name the discarded evidence handle; "
        f"raised: {message!r}"
    )
    assert "assertion 1" not in message, (
        "SC-010: 'pending' is the defect's own signature and MUST be ADMITTED "
        "by assertion 1 (the cross-file row-aware sibling pins it). Assertion 1 "
        f"fired on the defect fixture instead. Raised: {message!r}"
    )

    # --- SECONDARY, EXPLICITLY INSUFFICIENT WITNESS: "fail" is a concrete
    # disallowed verdict for assertion 1, reachable from a one-criterion
    # fixture (matrix.py:259). On its own this proves NOTHING about #2804:
    # the defect's signature is 'pending', not 'fail'. ---
    fail_doc = _one_criterion_fail_document()
    assert fail_doc["overall_verdict"] == "fail", (
        "'fail' witness precondition: a one-criterion 'fail' fixture must "
        f"compute 'fail'; got {fail_doc['overall_verdict']!r}"
    )
    with pytest.raises(AssertionError, match="assertion 1"):
        _assert_2804_acceptance_contract(fail_doc)
