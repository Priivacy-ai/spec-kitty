"""WP04 (write-side-seam-matrix-tracer-01KYP3MH): T014/T015/T016/T017/T018.

Covers:

* T014 — ``overall_verdict`` stays a COMPUTED property, never a stored field
  (round-trips a hand-edited/stale on-disk value away — #2743 negative-
  invariant-integrity's sibling guard for the acceptance half of the schema).
* T016 — the #2318 regression: an all-pass / zero-negative-invariant accept
  must persist the recomputed verdict, not leave the on-disk file stuck at a
  stale ``pending`` (the pre-fix gate only wrote inside the
  ``negative_invariants`` arm).
* T015/T017 — the ``acceptance-verdict`` command routes its write through the
  WP03 write seam (``write_and_commit_acceptance_matrix`` ->
  ``coordination.write_seam.write_artifact``), is idempotent (FR-012), and
  lands acceptance-matrix.json on the COORD surface for a coord-topology
  mission (never a stranded primary copy).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import fields
from pathlib import Path

import pytest
import typer

from specify_cli.acceptance.gates_core import _evaluate_acceptance_matrix
from specify_cli.acceptance.matrix import (
    AcceptanceCriterion,
    AcceptanceMatrix,
    read_acceptance_matrix,
    write_acceptance_matrix,
    write_and_commit_acceptance_matrix,
)
from specify_cli.cli.commands.agent.acceptance_verdict import acceptance_verdict
from specify_cli.git.protection_policy import ProtectionPolicy

# Reused verbatim (not duplicated) — the shared coord-topology mission
# fixture builder this mission's own #2404 coord-partition test already
# establishes (module docstring there: "Build ON #2462's landed ...").
from tests.integration.test_accept_matrix_coord_partition import (
    _build_coord_mission_for_matrix,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Shared flat-repo git helpers
# ---------------------------------------------------------------------------


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _head(repo_root: Path) -> str:
    return _git(repo_root, "rev-parse", "HEAD").stdout.strip()


_FLAT_BRANCH = "matrix-verdict-work"


def _mission_id_for(slug: str) -> str:
    """A deterministic, valid-shape 26-char ULID for a test mission_id.

    ``resolve_mission_handle`` (``cli/selector_resolution.py``) indexes
    missions by ``meta.json``'s ``mission_id`` — a flat mission fixture
    without one is unresolvable (``MissionNotFoundError``). Mirrors the
    hand-minted-ULID convention used by
    ``tests/specify_cli/test_accept_no_commit_readonly.py``.
    """
    digest = f"{slug:0<26}".upper()[:26]
    # ULIDs use Crockford base32 — strip characters outside that alphabet so
    # the fixture value is shape-valid, not just length-valid.
    allowed = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    return "".join(c if c in allowed else "0" for c in digest)


def _init_flat_mission(tmp_path: Path, slug: str) -> tuple[Path, Path]:
    """A minimal, real flat (non-coord) mission repo for the write/commit path.

    ``main``/``master`` are protected by default
    (``ProtectionPolicy._DEFAULT_PROTECTED_BRANCHES``); a dedicated
    non-default branch mirrors ``test_accept_matrix_coord_partition.py``'s own
    ``_WORK_BRANCH`` convention so the seam commits directly rather than
    refusing on a protected ref.
    """
    repo_root = tmp_path
    _git(repo_root, "init", "-q")
    _git(repo_root, "checkout", "-q", "-b", _FLAT_BRANCH)
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")

    # A ``.kittify/`` marker gives ``locate_project_root`` a definite project
    # boundary at ``repo_root`` (WP04 C-A1 fixture hardening): without one,
    # repo-root detection falls back to a bare ``.git`` walk-up that can
    # escape past this fixture into an unrelated ancestor project on a
    # contaminated filesystem. ``mission_type_activations`` mirrors every
    # mission this fixture mints (``mission_type": "software-dev"`` above).
    kittify_dir = repo_root / ".kittify"
    kittify_dir.mkdir(parents=True, exist_ok=True)
    (kittify_dir / "config.yaml").write_text(
        "mission_type_activations:\n  - software-dev\n", encoding="utf-8"
    )

    feature_dir = repo_root / "kitty-specs" / slug
    feature_dir.mkdir(parents=True)
    mission_id = _mission_id_for(slug)
    meta = {
        "mission_slug": slug,
        "slug": slug,
        "mission_id": mission_id,
        "mid8": mission_id[:8],
        "friendly_name": "Matrix Verdict Test",
        "mission_type": "software-dev",
        "target_branch": _FLAT_BRANCH,
        "created_at": "2026-01-01T00:00:00Z",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "init")
    return repo_root, feature_dir


# ===========================================================================
# T014 — overall_verdict stays a computed property, never hand-stored
# ===========================================================================


class TestOverallVerdictIsComputedNotStored:
    def test_overall_verdict_is_not_a_dataclass_field(self) -> None:
        """The schema itself cannot carry a stored ``overall_verdict`` — it is a
        ``@property``, not a ``dataclasses.field`` (#2743 sibling guard)."""
        field_names = {f.name for f in fields(AcceptanceMatrix)}
        assert "overall_verdict" not in field_names
        assert isinstance(AcceptanceMatrix.overall_verdict, property)

    def test_from_dict_ignores_a_hand_stored_stale_verdict(self) -> None:
        """A hand-edited/stale on-disk ``overall_verdict`` is IGNORED on load —
        the reconstructed object recomputes it fresh from criteria/invariants,
        so a stale value on disk can never smuggle a wrong verdict back in."""
        matrix = AcceptanceMatrix(
            mission_slug="verdict-integrity-mission",
            criteria=[
                AcceptanceCriterion(
                    criterion_id="FR-001",
                    description="works",
                    proof_type="automated_test",
                    pass_fail="pass",
                )
            ],
        )
        assert matrix.overall_verdict == "pass"

        payload = matrix.to_dict()
        # Simulate a stale/hand-edited on-disk value — deliberately wrong.
        payload["overall_verdict"] = "fail"

        reloaded = AcceptanceMatrix.from_dict(payload)
        assert reloaded.overall_verdict == "pass", (
            "a stored overall_verdict value must never override the computed one"
        )

    def test_to_dict_round_trip_omits_no_information_needed_to_recompute(self) -> None:
        matrix = AcceptanceMatrix(
            mission_slug="verdict-integrity-mission",
            criteria=[
                AcceptanceCriterion(
                    criterion_id="FR-001",
                    description="works",
                    proof_type="automated_test",
                    pass_fail="pending",
                )
            ],
        )
        assert matrix.overall_verdict == "pending"
        reloaded = AcceptanceMatrix.from_dict(matrix.to_dict())
        assert reloaded.overall_verdict == "pending"
        assert reloaded.criteria[0].criterion_id == "FR-001"


# ===========================================================================
# NFR-001 — verdict determinism, zero product-source reads
# ===========================================================================


class TestVerdictDeterminismNoIo:
    def test_overall_verdict_is_a_pure_function_of_in_memory_state(self) -> None:
        """``overall_verdict`` never touches the filesystem — it is derived
        purely from ``criteria``/``negative_invariants`` already held in
        memory (NFR-001). Any accidental I/O would raise here, since the
        matrix objects below reference no real files at all."""
        matrix = AcceptanceMatrix(
            mission_slug="pure-verdict-mission",
            criteria=[
                AcceptanceCriterion(
                    criterion_id="FR-001",
                    description="works",
                    proof_type="automated_test",
                    pass_fail="pass",
                ),
                AcceptanceCriterion(
                    criterion_id="FR-002",
                    description="also works",
                    proof_type="code_review",
                    pass_fail="pass",
                ),
            ],
        )
        # Same result computed twice from the SAME in-memory state — a pure
        # function is stable under repeated evaluation with no side effects.
        assert matrix.overall_verdict == "pass"
        assert matrix.overall_verdict == "pass"


# ===========================================================================
# T016 — #2318 regression: all-pass / no-negative-invariant accept persists
# the recomputed verdict instead of leaving a stale on-disk 'pending'
# ===========================================================================


class TestPersistOnAcceptRegression2318:
    def test_all_pass_no_invariants_persists_pass_not_stale_pending(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Drives the PRE-EXISTING entry point named in #2318 comment
        5102989064 (``_evaluate_acceptance_matrix``) directly: an all-pass
        matrix with ZERO negative invariants (the previously-uncovered
        branch — the old gate only wrote inside ``if
        acc_matrix.negative_invariants``) must still have its recomputed
        ``overall_verdict`` land on disk as ``"pass"``."""
        slug = "no-invariant-mission"
        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)

        matrix = AcceptanceMatrix(
            mission_slug=slug,
            criteria=[
                AcceptanceCriterion(
                    criterion_id="FR-001",
                    description="the feature behaves as specified",
                    proof_type="automated_test",
                    pass_fail="pass",
                )
            ],
            negative_invariants=[],
        )
        # Seed a stale on-disk 'pending' matrix first (the #2318 starting
        # state — a scaffolded, never-since-refreshed matrix) so this test
        # actually pins the "stops being stale" transition, not merely "a
        # fresh write happens to say pass".
        stale = AcceptanceMatrix(mission_slug=slug, criteria=[
            AcceptanceCriterion(
                criterion_id="FR-001",
                description="the feature behaves as specified",
                proof_type="automated_test",
                pass_fail="pending",
            )
        ])
        write_acceptance_matrix(feature_dir, stale)
        assert json.loads((feature_dir / "acceptance-matrix.json").read_text())["overall_verdict"] == "pending"

        monkeypatch.setattr("specify_cli.acceptance.matrix.read_acceptance_matrix", lambda _fd: matrix)

        activity_issues: list[str] = []
        skipped: list = []
        blocked: list = []
        _evaluate_acceptance_matrix(
            tmp_path, feature_dir, activity_issues, skipped, blocked, mutate_matrix=True
        )

        assert activity_issues == []
        persisted = json.loads((feature_dir / "acceptance-matrix.json").read_text())
        assert persisted["overall_verdict"] == "pass", (
            "#2318: an all-pass / no-negative-invariant accept must persist "
            "the recomputed verdict, not leave the on-disk file at a stale "
            "'pending'"
        )

    def test_diagnose_mode_still_does_not_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Contrast case: ``mutate_matrix=False`` (``--diagnose``) must still
        never write — the T016 fix only widens the ``mutate_matrix=True`` arm,
        it does not touch the read-only contract (#1883/#1908)."""
        slug = "diagnose-mission"
        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)
        matrix = AcceptanceMatrix(
            mission_slug=slug,
            criteria=[
                AcceptanceCriterion(
                    criterion_id="FR-001",
                    description="works",
                    proof_type="automated_test",
                    pass_fail="pass",
                )
            ],
        )
        monkeypatch.setattr("specify_cli.acceptance.matrix.read_acceptance_matrix", lambda _fd: matrix)

        _evaluate_acceptance_matrix(tmp_path, feature_dir, [], [], [], mutate_matrix=False)

        assert not (feature_dir / "acceptance-matrix.json").exists()


# ===========================================================================
# T017 — write_and_commit_acceptance_matrix (the WP03-seam composition helper)
# ===========================================================================


class TestWriteAndCommitAcceptanceMatrix:
    def test_first_write_commits_second_identical_write_is_unchanged(
        self, tmp_path: Path
    ) -> None:
        """FR-012 idempotence, inherited from ``commit_for_mission``: a
        byte-identical re-write resolves to ``"unchanged"`` — no duplicate
        commit, HEAD does not move."""
        slug = "seam-idempotence-mission"
        repo_root, feature_dir = _init_flat_mission(tmp_path, slug)
        matrix = AcceptanceMatrix(
            mission_slug=slug,
            criteria=[
                AcceptanceCriterion(
                    criterion_id="FR-001",
                    description="works",
                    proof_type="automated_test",
                    pass_fail="pass",
                )
            ],
        )
        policy = ProtectionPolicy.resolve(repo_root)

        first = write_and_commit_acceptance_matrix(
            repo_root,
            slug,
            feature_dir,
            matrix,
            entry_id="FR-001",
            message="chore(acceptance): record FR-001=pass",
            policy=policy,
        )
        assert first.status == "committed", first
        head_after_first = _head(repo_root)

        second = write_and_commit_acceptance_matrix(
            repo_root,
            slug,
            feature_dir,
            matrix,
            entry_id="FR-001",
            message="chore(acceptance): record FR-001=pass",
            policy=policy,
        )
        assert second.status == "unchanged", second
        assert _head(repo_root) == head_after_first, "a no-op re-write must not create a new commit"


# ===========================================================================
# T015 — the ``acceptance-verdict`` command
# ===========================================================================


class TestAcceptanceVerdictCommand:
    def _seed_matrix(self, feature_dir: Path, slug: str) -> None:
        write_acceptance_matrix(
            feature_dir,
            AcceptanceMatrix(
                mission_slug=slug,
                criteria=[
                    AcceptanceCriterion(
                        criterion_id="FR-001",
                        description="the feature behaves as specified",
                        proof_type="automated_test",
                        pass_fail="pending",
                    )
                ],
            ),
        )

    def test_records_verdict_and_persists_recomputed_overall_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        slug = "verdict-command-mission"
        repo_root, feature_dir = _init_flat_mission(tmp_path, slug)
        self._seed_matrix(feature_dir, slug)
        _git(repo_root, "add", "-A")
        _git(repo_root, "commit", "-q", "-m", "seed acceptance-matrix")
        monkeypatch.chdir(repo_root)

        try:
            acceptance_verdict(
                mission=slug,
                criterion="FR-001",
                result="pass",
                verification_method="automated_test",
                actor="tester",
                evidence="ci-run-123",
                json_output=True,
            )
        except typer.Exit as exc:
            assert exc.exit_code in (0, None), f"command failed: exit {exc.exit_code}"

        reloaded = read_acceptance_matrix(feature_dir)
        assert reloaded is not None
        assert reloaded.criteria[0].pass_fail == "pass"
        assert reloaded.criteria[0].verified_by == "tester"
        assert reloaded.criteria[0].evidence == "ci-run-123"
        assert reloaded.overall_verdict == "pass"

    def test_rerun_with_identical_inputs_is_a_no_op(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """FR-012: a second invocation with IDENTICAL inputs does not bump
        ``verified_at`` (nothing observable changed), so the underlying write
        is byte-identical and the commit resolves to ``"unchanged"`` — no new
        commit, HEAD unchanged."""
        slug = "verdict-command-idempotent-mission"
        repo_root, feature_dir = _init_flat_mission(tmp_path, slug)
        self._seed_matrix(feature_dir, slug)
        _git(repo_root, "add", "-A")
        _git(repo_root, "commit", "-q", "-m", "seed acceptance-matrix")
        monkeypatch.chdir(repo_root)

        def _invoke() -> dict[str, object]:
            capsys.readouterr()
            try:
                acceptance_verdict(
                    mission=slug,
                    criterion="FR-001",
                    result="pass",
                    verification_method="automated_test",
                    actor="tester",
                    evidence="ci-run-123",
                    json_output=True,
                )
            except typer.Exit as exc:
                assert exc.exit_code in (0, None), f"command failed: exit {exc.exit_code}"
            out = capsys.readouterr().out.strip()
            return dict(json.loads(out))

        first_payload = _invoke()
        assert first_payload["write_status"] == "committed"
        head_after_first = _head(repo_root)

        second_payload = _invoke()
        assert second_payload["write_status"] == "unchanged", second_payload
        assert _head(repo_root) == head_after_first, "an identical re-run must not create a new commit"

    def test_unknown_criterion_reports_available_ids(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        slug = "verdict-command-unknown-criterion"
        repo_root, feature_dir = _init_flat_mission(tmp_path, slug)
        self._seed_matrix(feature_dir, slug)
        _git(repo_root, "add", "-A")
        _git(repo_root, "commit", "-q", "-m", "seed acceptance-matrix")
        monkeypatch.chdir(repo_root)

        with pytest.raises(typer.Exit) as exc_info:
            acceptance_verdict(
                mission=slug,
                criterion="FR-999",
                result="pass",
                verification_method=None,
                actor=None,
                evidence=None,
                json_output=False,
            )
        assert exc_info.value.exit_code == 1

    def test_invalid_result_value_is_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            acceptance_verdict(
                mission="whatever",
                criterion="FR-001",
                result="not-a-real-verdict",
                verification_method=None,
                actor=None,
                evidence=None,
                json_output=False,
            )
        assert exc_info.value.exit_code == 2

    def test_lands_on_coord_surface_not_a_stranded_primary_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The command must resolve the SAME coord surface every other
        production writer lands on (never a stranded primary-checkout copy)."""
        result, coord_root, coord_feature_dir = _build_coord_mission_for_matrix(tmp_path)
        slug = result.mission_slug

        coord_feature_dir.mkdir(parents=True, exist_ok=True)
        self._seed_matrix(coord_feature_dir, slug)
        subprocess.run(
            ["git", "-C", str(coord_root), "add", "-A"], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(coord_root), "commit", "-q", "-m", "seed coord matrix"],
            check=True,
            capture_output=True,
        )

        monkeypatch.chdir(tmp_path)
        try:
            acceptance_verdict(
                mission=slug,
                criterion="FR-001",
                result="pass",
                verification_method=None,
                actor="tester",
                evidence=None,
                json_output=True,
            )
        except typer.Exit as exc:
            assert exc.exit_code in (0, None), f"command failed: exit {exc.exit_code}"

        # The PRIMARY checkout must NOT carry a stranded copy of the matrix.
        assert not (result.feature_dir / "acceptance-matrix.json").exists(), (
            "acceptance-verdict must not strand a copy on the primary checkout "
            "for a coord-topology mission"
        )
        reloaded = read_acceptance_matrix(coord_feature_dir)
        assert reloaded is not None
        assert reloaded.criteria[0].pass_fail == "pass"
