"""Tests for the ``spec-kitty reconcile`` CLI surface + stable library API (WP04).

Executable contract for FR-007 and NFR-002 of mission
``dossier-parity-reconciler-01KXYXVP``.

WP04 exposes the pure WP03 :class:`DossierReconciler` as:

  (a) a CLI operation — ``spec-kitty reconcile --mission <slug>`` — that exits
      ``0`` on PARITY and non-zero on DIVERGENCE, NAMING the differing
      artifact(s) in its output (FR-007), with a ``--json`` machine surface;
  (b) a stable, narrow library API — :func:`reconcile_mission_dossier` returning
      a WP03 :class:`ReconciliationResult` — that import-history (#2262) gates
      materialization on (a contract, never reconciler internals).

These tests drive the wrapper only: the hash/compare authority stays in WP01/WP03
(C-001) and is never re-implemented here. The mission dossier is seeded on disk,
a recorded snapshot is persisted, and the mission-dir read seam is monkeypatched
so the test never depends on the topology resolver.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

pytestmark = [pytest.mark.integration]


# ── Helpers ─────────────────────────────────────────────────────────────────


def _seed_mission(feature_dir: Path, *, extra_artifacts: int = 0) -> str:
    """Create a mission dossier on disk and persist its recorded snapshot.

    Returns the mission slug (the feature-dir name). After this call, a fresh
    reconcile of ``feature_dir`` against the saved snapshot is PARITY until a
    source file is mutated.
    """
    from specify_cli.dossier.indexer import Indexer
    from specify_cli.dossier.manifest import ManifestRegistry
    from specify_cli.dossier.snapshot import compute_snapshot, save_snapshot

    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n\nreconciler mission\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n\nrebuild + verify\n", encoding="utf-8")
    tasks = feature_dir / "tasks"
    tasks.mkdir(exist_ok=True)
    (tasks / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Seed\ntask_type: implement\n---\nbody\n",
        encoding="utf-8",
    )
    for i in range(extra_artifacts):
        (feature_dir / f"note-{i:04d}.md").write_text(f"# Note {i}\n", encoding="utf-8")

    dossier = Indexer(ManifestRegistry()).index_feature(feature_dir, "software-dev")
    snapshot = compute_snapshot(dossier)
    save_snapshot(snapshot, feature_dir)
    return feature_dir.name


def _patch_feature_dir(monkeypatch: pytest.MonkeyPatch, feature_dir: Path) -> None:
    """Point the reconcile module's mission-dir read seam at ``feature_dir``."""
    import specify_cli.cli.commands.reconcile as reconcile_module

    monkeypatch.setattr(
        reconcile_module,
        "candidate_feature_dir_for_mission",
        lambda repo_root, mission_slug, **kw: feature_dir,
    )


# ── T017: stable library API contract ────────────────────────────────────────


class TestLibraryApi:
    def test_returns_reconciliation_result_on_parity(self, tmp_path, monkeypatch):
        from specify_cli.cli.commands.reconcile import reconcile_mission_dossier
        from specify_cli.dossier.reconciler import ReconciliationResult, ReconciliationStatus

        feature_dir = tmp_path / "demo-mission-01AAAA"
        slug = _seed_mission(feature_dir)
        _patch_feature_dir(monkeypatch, feature_dir)

        result = reconcile_mission_dossier(slug, repo_root=tmp_path)

        assert isinstance(result, ReconciliationResult)
        assert result.status is ReconciliationStatus.PARITY
        assert result.is_parity
        assert bool(result) is True  # fail-closed truthiness: parity-only
        assert result.differing_artifacts == ()

    def test_names_divergent_artifact_after_source_mutation(self, tmp_path, monkeypatch):
        from specify_cli.cli.commands.reconcile import reconcile_mission_dossier

        feature_dir = tmp_path / "demo-mission-01BBBB"
        slug = _seed_mission(feature_dir)
        _patch_feature_dir(monkeypatch, feature_dir)

        # Mutate source AFTER the snapshot was recorded → divergence on spec.md.
        (feature_dir / "spec.md").write_text("# Spec\n\nMUTATED\n", encoding="utf-8")

        result = reconcile_mission_dossier(slug, repo_root=tmp_path)

        assert result.is_divergence
        assert bool(result) is False
        assert "spec.md" in result.differing_paths

    def test_missing_snapshot_is_fail_closed_error(self, tmp_path, monkeypatch):
        from specify_cli.cli.commands.reconcile import reconcile_mission_dossier

        feature_dir = tmp_path / "demo-mission-01CCCC"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
        _patch_feature_dir(monkeypatch, feature_dir)

        result = reconcile_mission_dossier("demo-mission-01CCCC", repo_root=tmp_path)

        # No recorded snapshot to verify against — never a default parity.
        assert result.is_error
        assert bool(result) is False
        assert result.error


# ── T015/T016: CLI exit codes + named divergence ─────────────────────────────


class TestCli:
    def _run(self, args, monkeypatch, feature_dir):
        from specify_cli import app

        _patch_feature_dir(monkeypatch, feature_dir)
        return CliRunner().invoke(app, args)

    def test_command_is_wired_into_the_app(self):
        """Integration-wiring: ``reconcile`` is a live, callable command.

        Runs --help in an isolated filesystem so the readiness banner (emitted
        for a connected-but-logged-out teamspace, e.g. the CI checkout) doesn't
        pre-empt help rendering — this asserts wiring, not auth state.
        """
        import re

        from specify_cli import app

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["reconcile", "--help"])
        assert result.exit_code == 0
        # Strip ANSI so the assertion survives Rich colorizing the help in CI
        # (the flag renders as `\x1b[..m--mission\x1b[0m`, breaking a raw substring).
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "--mission" in plain

    def test_exits_zero_on_parity(self, tmp_path, monkeypatch):
        feature_dir = tmp_path / "demo-mission-01DDDD"
        slug = _seed_mission(feature_dir)
        result = self._run(["reconcile", "--mission", slug], monkeypatch, feature_dir)
        assert result.exit_code == 0

    def test_nonzero_and_names_artifact_on_divergence(self, tmp_path, monkeypatch):
        feature_dir = tmp_path / "demo-mission-01EEEE"
        slug = _seed_mission(feature_dir)
        (feature_dir / "plan.md").write_text("# Plan\n\nMUTATED\n", encoding="utf-8")
        result = self._run(["reconcile", "--mission", slug], monkeypatch, feature_dir)
        assert result.exit_code != 0
        assert "plan.md" in result.output  # divergence NAMES the artifact (NFR-004)

    def test_json_output_is_machine_readable(self, tmp_path, monkeypatch):
        feature_dir = tmp_path / "demo-mission-01FFFF"
        slug = _seed_mission(feature_dir)
        (feature_dir / "spec.md").write_text("# Spec\n\nMUTATED\n", encoding="utf-8")
        result = self._run(["reconcile", "--mission", slug, "--json"], monkeypatch, feature_dir)
        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["status"] == "divergence"
        assert "spec.md" in [d["artifact_path"] for d in payload["differing_artifacts"]]

    def test_error_status_exits_nonzero(self, tmp_path, monkeypatch):
        feature_dir = tmp_path / "demo-mission-01GGGG"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
        result = self._run(["reconcile", "--mission", "demo-mission-01GGGG"], monkeypatch, feature_dir)
        assert result.exit_code != 0  # no snapshot → fail-closed, non-zero


# ── T018: NFR-002 — reconcile one mission dossier ≤ 2 s ──────────────────────


class TestNfr002:
    def test_single_mission_reconciles_under_two_seconds(self, tmp_path, monkeypatch):
        from specify_cli.cli.commands.reconcile import reconcile_mission_dossier

        feature_dir = tmp_path / "demo-mission-01HHHH"
        slug = _seed_mission(feature_dir, extra_artifacts=50)
        _patch_feature_dir(monkeypatch, feature_dir)

        start = time.perf_counter()
        result = reconcile_mission_dossier(slug, repo_root=tmp_path)
        elapsed = time.perf_counter() - start

        assert result.is_parity
        assert elapsed <= 2.0, f"NFR-002 breached: {elapsed:.3f}s > 2.0s"

    def test_scaling_is_roughly_linear_in_artifact_count(self, tmp_path, monkeypatch):
        from specify_cli.cli.commands.reconcile import reconcile_mission_dossier

        def _time(n: int, name: str) -> float:
            feature_dir = tmp_path / name
            slug = _seed_mission(feature_dir, extra_artifacts=n)
            _patch_feature_dir(monkeypatch, feature_dir)
            start = time.perf_counter()
            reconcile_mission_dossier(slug, repo_root=tmp_path)
            return time.perf_counter() - start

        small = _time(20, "scale-small-01IIII")
        large = _time(80, "scale-large-01JJJJ")

        # 4x the artifacts must stay well under a quadratic blow-up. Generous
        # bound (10x) keeps the linearity signal without CI-timing flakiness.
        assert large <= max(small * 10.0, 2.0)
