"""Acceptance + unit tests for the one-time snapshot-hash re-baseline (WP05).

Covers FR-009 (recompute recorded snapshot hashes under the canonical
definition so unchanged content is not flagged divergent after the WP02
cutover) and NFR-003 (zero false-divergence across the local backlog).

Key invariants exercised:

- After re-baseline, a reconcile of *unchanged* content reads as PARITY
  (the recorded hash equals a freshly recomputed canonical snapshot hash).
- Content that *genuinely* changed after re-baseline still DIVERGES.
- The re-baseline is idempotent (safe to re-run) and read-only over source
  artifacts (respects the no-dirty-tree invariant #2263).

See: kitty-specs/dossier-parity-reconciler-01KXYXVP/spec.md (FR-009, NFR-003,
A-003) and tasks/WP05-rebaseline-migration.md (T019-T021).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from specify_cli.dossier.indexer import Indexer
from specify_cli.dossier.manifest import ManifestRegistry
from specify_cli.dossier.snapshot import compute_snapshot

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ── helpers ─────────────────────────────────────────────────────────────────


def _reconcile_parity_hash(feature_dir: Path, mission_type: str = "software-dev") -> str:
    """Freshly index + snapshot a feature dir; return its canonical parity hash.

    This is the exact pipeline the live drift/reconcile path uses
    (``Indexer.index_feature`` → ``compute_snapshot``), so equality with a
    recorded hash means a reconcile would read PARITY.
    """
    dossier = Indexer(ManifestRegistry()).index_feature(feature_dir, mission_type)
    return compute_snapshot(dossier).parity_hash_sha256


def _write_source_mission(feature_dir: Path) -> None:
    """Create a representative mission source tree (spec/plan/WP artifacts)."""
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n\nRequirements here.\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n\nImplementation plan.\n", encoding="utf-8")
    tasks = feature_dir / "tasks"
    tasks.mkdir(exist_ok=True)
    # A WP file with runtime-mutable frontmatter — WP01 hashes its static
    # projection, so raw-byte churn in lane/agent/history must not move the hash.
    (tasks / "WP01-first.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: First work package\n"
        "dependencies: []\n"
        "subtasks:\n"
        "- T001\n"
        "lane: in_progress\n"
        "agent: claude\n"
        "shell_pid: '12345'\n"
        "---\n\n# WP01\n\nDo the first thing.\n",
        encoding="utf-8",
    )


def _record_old_form_snapshot(feature_dir: Path, mission_slug: str) -> Path:
    """Write a recorded snapshot in the retired bare-hex (pre-WP02) form.

    Models a snapshot persisted under the OLD concat-of-hashes formula: the
    per-artifact content hashes are joined and SHA256'd, yielding a *bare*
    64-hex digest (no ``sha256:`` prefix).
    """
    dossier = Indexer(ManifestRegistry()).index_feature(feature_dir, "software-dev")
    snapshot = compute_snapshot(dossier)
    data = snapshot.model_dump(mode="json")

    # Old formula: sha256 over the concatenation of the sorted component hashes.
    components = sorted(data.get("parity_hash_components", []))
    # noqa: TID251 — deliberately reproduces the RETIRED pre-WP02 concat/bare-hex
    # formula to model a legacy recorded snapshot; not the canonical hash.
    old_digest = hashlib.sha256("".join(components).encode("utf-8")).hexdigest()  # noqa: TID251
    assert not old_digest.startswith("sha256:")
    data["parity_hash_sha256"] = old_digest

    dossier_dir = feature_dir / ".kittify" / "dossiers" / mission_slug
    dossier_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = dossier_dir / "snapshot-latest.json"
    snapshot_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return snapshot_path


def _recorded_hash(snapshot_path: Path) -> str:
    return json.loads(snapshot_path.read_text(encoding="utf-8"))["parity_hash_sha256"]


# ── T019: acceptance — parity after re-baseline, divergence on real change ────


class TestRebaselineParity:
    def test_recompute_yields_canonical_prefixed_hash(self, tmp_path: Path) -> None:
        """Re-baseline rewrites a bare-hex recorded hash to the canonical form."""
        from specify_cli.dossier.rebaseline import rebaseline_snapshot_file

        feature_dir = tmp_path / "042-example-mission"
        _write_source_mission(feature_dir)
        snapshot_path = _record_old_form_snapshot(feature_dir, "042-example-mission")

        old_hash = _recorded_hash(snapshot_path)
        assert not old_hash.startswith("sha256:")  # precondition: OLD form

        outcome = rebaseline_snapshot_file(snapshot_path)

        assert outcome.changed is True
        assert outcome.old_hash == old_hash
        assert outcome.new_hash.startswith("sha256:")
        # Persisted to disk.
        assert _recorded_hash(snapshot_path) == outcome.new_hash

    def test_unchanged_content_reconciles_as_parity(self, tmp_path: Path) -> None:
        """NFR-003: after re-baseline, unchanged content shows zero divergence."""
        from specify_cli.dossier.rebaseline import rebaseline_snapshot_file

        feature_dir = tmp_path / "042-example-mission"
        _write_source_mission(feature_dir)
        snapshot_path = _record_old_form_snapshot(feature_dir, "042-example-mission")

        rebaseline_snapshot_file(snapshot_path)

        # A reconcile of the UNCHANGED source must equal the recorded hash.
        recorded = _recorded_hash(snapshot_path)
        reconciled = _reconcile_parity_hash(feature_dir)
        assert reconciled == recorded, "unchanged content must read as PARITY"

    def test_genuine_change_still_diverges(self, tmp_path: Path) -> None:
        """Content that genuinely changed after re-baseline must still diverge."""
        from specify_cli.dossier.rebaseline import rebaseline_snapshot_file

        feature_dir = tmp_path / "042-example-mission"
        _write_source_mission(feature_dir)
        snapshot_path = _record_old_form_snapshot(feature_dir, "042-example-mission")

        rebaseline_snapshot_file(snapshot_path)
        recorded = _recorded_hash(snapshot_path)

        # Mutate a source artifact — a real content change.
        (feature_dir / "spec.md").write_text("# Spec\n\nDIFFERENT requirements.\n", encoding="utf-8")

        reconciled = _reconcile_parity_hash(feature_dir)
        assert reconciled != recorded, "genuine content change must DIVERGE"

    def test_wp_runtime_churn_does_not_diverge(self, tmp_path: Path) -> None:
        """Runtime-mutable WP frontmatter churn must NOT read as divergence.

        This is why the re-baseline recomputes from source under the canonical
        (WP01 projection) definition rather than transforming recorded raw-byte
        component hashes.
        """
        from specify_cli.dossier.rebaseline import rebaseline_snapshot_file

        feature_dir = tmp_path / "042-example-mission"
        _write_source_mission(feature_dir)
        snapshot_path = _record_old_form_snapshot(feature_dir, "042-example-mission")

        rebaseline_snapshot_file(snapshot_path)
        recorded = _recorded_hash(snapshot_path)

        # Churn only runtime-mutable frontmatter (lane/agent/shell_pid/history).
        wp = feature_dir / "tasks" / "WP01-first.md"
        wp.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: First work package\n"
            "dependencies: []\n"
            "subtasks:\n"
            "- T001\n"
            "lane: done\n"
            "agent: codex\n"
            "shell_pid: '99999'\n"
            "history:\n"
            "- at: '2026-07-20T00:00:00Z'\n"
            "  actor: system\n"
            "  action: churn\n"
            "---\n\n# WP01\n\nDo the first thing.\n",
            encoding="utf-8",
        )

        reconciled = _reconcile_parity_hash(feature_dir)
        assert reconciled == recorded, "runtime-state churn must not read as divergence"


# ── T020: idempotency + read-only-over-source ─────────────────────────────────


class TestRebaselineIdempotentAndReadOnly:
    def test_idempotent_second_run_is_noop(self, tmp_path: Path) -> None:
        from specify_cli.dossier.rebaseline import rebaseline_snapshot_file

        feature_dir = tmp_path / "042-example-mission"
        _write_source_mission(feature_dir)
        snapshot_path = _record_old_form_snapshot(feature_dir, "042-example-mission")

        first = rebaseline_snapshot_file(snapshot_path)
        assert first.changed is True

        second = rebaseline_snapshot_file(snapshot_path)
        assert second.changed is False, "already-canonical snapshot must be a no-op"
        assert second.old_hash == second.new_hash == first.new_hash
        assert _recorded_hash(snapshot_path) == first.new_hash

    def test_already_canonical_is_left_untouched(self, tmp_path: Path) -> None:
        from specify_cli.dossier.rebaseline import rebaseline_snapshot_file

        feature_dir = tmp_path / "042-example-mission"
        _write_source_mission(feature_dir)
        snapshot_path = _record_old_form_snapshot(feature_dir, "042-example-mission")
        rebaseline_snapshot_file(snapshot_path)

        before = snapshot_path.read_text(encoding="utf-8")
        outcome = rebaseline_snapshot_file(snapshot_path)
        after = snapshot_path.read_text(encoding="utf-8")

        assert outcome.changed is False
        assert before == after, "canonical snapshot must not be rewritten"

    def test_source_artifacts_are_not_mutated(self, tmp_path: Path) -> None:
        """#2263: the re-baseline must be read-only over source artifacts."""
        from specify_cli.dossier.rebaseline import rebaseline_snapshot_file

        feature_dir = tmp_path / "042-example-mission"
        _write_source_mission(feature_dir)
        snapshot_path = _record_old_form_snapshot(feature_dir, "042-example-mission")

        source_files = sorted(p for p in feature_dir.rglob("*") if p.is_file() and ".kittify" not in p.parts)
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}  # noqa: TID251 — file-integrity check, not the dossier hash

        rebaseline_snapshot_file(snapshot_path)

        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}  # noqa: TID251 — file-integrity check, not the dossier hash
        assert before == after, "source artifacts must be untouched"

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        from specify_cli.dossier.rebaseline import rebaseline_snapshot_file

        feature_dir = tmp_path / "042-example-mission"
        _write_source_mission(feature_dir)
        snapshot_path = _record_old_form_snapshot(feature_dir, "042-example-mission")
        before = snapshot_path.read_text(encoding="utf-8")

        outcome = rebaseline_snapshot_file(snapshot_path, dry_run=True)

        assert outcome.changed is True  # it WOULD change
        assert outcome.new_hash.startswith("sha256:")
        assert snapshot_path.read_text(encoding="utf-8") == before, "dry-run must not write"


# ── T021: verify across a representative backlog slice (NFR-003) ──────────────


class TestRebaselineBacklog:
    def test_discovers_recorded_snapshots(self, tmp_path: Path) -> None:
        from specify_cli.dossier.rebaseline import iter_recorded_snapshot_files

        slugs = ["062-alpha", "063-beta", "064-gamma"]
        for slug in slugs:
            feature_dir = tmp_path / slug
            _write_source_mission(feature_dir)
            _record_old_form_snapshot(feature_dir, slug)

        found = list(iter_recorded_snapshot_files(tmp_path))
        assert len(found) == len(slugs)
        assert all(p.name == "snapshot-latest.json" for p in found)

    def test_backlog_zero_false_divergence(self, tmp_path: Path) -> None:
        """NFR-003: across a representative backlog, unchanged content is PARITY."""
        from specify_cli.dossier.rebaseline import rebaseline_recorded_snapshots

        slugs = ["062-alpha", "063-beta", "064-gamma", "065-delta"]
        feature_dirs = {}
        for slug in slugs:
            feature_dir = tmp_path / slug
            _write_source_mission(feature_dir)
            _record_old_form_snapshot(feature_dir, slug)
            feature_dirs[slug] = feature_dir

        outcomes = rebaseline_recorded_snapshots(tmp_path)

        assert len(outcomes) == len(slugs)
        assert all(o.changed for o in outcomes)
        assert all(o.error is None for o in outcomes)

        # Zero false-divergence: every mission reconciles as PARITY unchanged.
        divergent = []
        for o in outcomes:
            reconciled = _reconcile_parity_hash(feature_dirs[o.mission_slug])
            if reconciled != o.new_hash:
                divergent.append(o.mission_slug)
        assert divergent == [], f"false-divergence on: {divergent}"

    def test_backlog_dry_run_reports_without_writing(self, tmp_path: Path) -> None:
        from specify_cli.dossier.rebaseline import rebaseline_recorded_snapshots

        slug = "062-alpha"
        feature_dir = tmp_path / slug
        _write_source_mission(feature_dir)
        snapshot_path = _record_old_form_snapshot(feature_dir, slug)
        before = snapshot_path.read_text(encoding="utf-8")

        outcomes = rebaseline_recorded_snapshots(tmp_path, dry_run=True)

        assert len(outcomes) == 1  # golden-count: cardinality-is-contract
        assert outcomes[0].changed is True
        assert snapshot_path.read_text(encoding="utf-8") == before


# ── Fail-closed error branches (each returns error + changed=False, no write) ─


class TestRebaselineErrorBranches:
    """Every rebaseline failure is captured (error set, changed=False) and never
    rewrites the recorded snapshot — the sweep must not abort or silently pass.
    """

    def test_unreadable_snapshot_is_error_and_left_untouched(self, tmp_path: Path) -> None:
        from specify_cli.dossier.rebaseline import rebaseline_snapshot_file

        dossier_dir = tmp_path / "042-broken" / ".kittify" / "dossiers" / "042-broken"
        dossier_dir.mkdir(parents=True)
        snapshot_path = dossier_dir / "snapshot-latest.json"
        snapshot_path.write_text("{ this is not valid json", encoding="utf-8")
        before = snapshot_path.read_text(encoding="utf-8")

        outcome = rebaseline_snapshot_file(snapshot_path)

        assert outcome.error == "unreadable_snapshot"
        assert outcome.changed is False
        assert snapshot_path.read_text(encoding="utf-8") == before  # not rewritten

    def test_source_missing_is_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import specify_cli.dossier.rebaseline as rb
        from specify_cli.dossier.rebaseline import rebaseline_snapshot_file

        feature_dir = tmp_path / "042-example-mission"
        _write_source_mission(feature_dir)
        snapshot_path = _record_old_form_snapshot(feature_dir, "042-example-mission")
        before = snapshot_path.read_text(encoding="utf-8")

        # Simulate the source tree having vanished between discovery and re-index.
        monkeypatch.setattr(rb, "_resolve_feature_dir", lambda _p: tmp_path / "gone")

        outcome = rebaseline_snapshot_file(snapshot_path)

        assert outcome.error == "source_missing"
        assert outcome.changed is False
        assert snapshot_path.read_text(encoding="utf-8") == before  # not rewritten

    def test_reindex_failure_is_error_and_does_not_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import specify_cli.dossier.rebaseline as rb
        from specify_cli.dossier.rebaseline import rebaseline_snapshot_file

        feature_dir = tmp_path / "042-example-mission"
        _write_source_mission(feature_dir)
        snapshot_path = _record_old_form_snapshot(feature_dir, "042-example-mission")
        before = snapshot_path.read_text(encoding="utf-8")

        def _boom(_dossier):
            raise RuntimeError("indexer exploded")

        monkeypatch.setattr(rb, "compute_snapshot", _boom)

        outcome = rebaseline_snapshot_file(snapshot_path)

        assert outcome.error is not None
        assert outcome.error.startswith("reindex_failed")
        assert outcome.changed is False
        assert snapshot_path.read_text(encoding="utf-8") == before  # not rewritten
