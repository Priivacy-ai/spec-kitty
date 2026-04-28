"""On-disk artifact assertion for ``charter synthesize --adapter fixture --json``.

WP03 / T014 — verifies that with ``SPEC_KITTY_FIXTURE_AUTO_STUB=1`` the
real synthesize path materializes ``.kittify/doctrine/`` artifacts plus the
synthesis manifest, **without** the test pre-seeding any of the asserted
paths. This locks Direction A from research.md R2: the env-var-gated
fixture stub mode unblocks the write-pipeline end-to-end.

The canonical artifact layout after a successful promote (per
``src/charter/synthesizer/write_pipeline.py:236-436``) is:

    .kittify/doctrine/<kind-subdir>/<artifact>.<kind>.yaml      # content
    .kittify/charter/provenance/<kind>-<slug>.yaml              # provenance
    .kittify/charter/synthesis-manifest.yaml                    # manifest (last)
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from charter.synthesizer import synthesize
from charter.synthesizer.fixture_adapter import FixtureAdapter
from charter.synthesizer.request import SynthesisRequest, SynthesisTarget

pytestmark = pytest.mark.fast


@pytest.fixture
def fixture_auto_stub_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Activate SPEC_KITTY_FIXTURE_AUTO_STUB for the duration of one test."""
    monkeypatch.setenv("SPEC_KITTY_FIXTURE_AUTO_STUB", "1")
    yield


def _build_minimal_request() -> SynthesisRequest:
    """Build a minimal SynthesisRequest equivalent to a fresh-project interview."""
    interview_snapshot = {
        "mission_type": "software_dev",
        "testing_philosophy": "test-driven",
        "neutrality_posture": "balanced",
        "risk_appetite": "moderate",
        "selected_directives": [],
        "selected_paradigms": [],
    }
    target = SynthesisTarget(
        kind="directive",
        slug="mission-type-scope-directive",
        title="Mission Type Scope Directive",
        artifact_id="PROJECT_001",
        source_section="mission_type",
    )
    return SynthesisRequest(
        target=target,
        interview_snapshot=interview_snapshot,
        doctrine_snapshot={"directives": {}, "tactics": {}, "styleguides": {}},
        drg_snapshot={"nodes": [], "edges": [], "schema_version": "1"},
        run_id="01KAUTOSTUBTEST00000000000",
    )


class TestSynthesizeAutoStubWritesArtifacts:
    def test_doctrine_dir_did_not_pre_exist(self, tmp_path: Path) -> None:
        """Sanity: no pre-seeding of asserted paths."""
        assert not (tmp_path / ".kittify" / "doctrine").exists()
        assert not (tmp_path / ".kittify" / "charter").exists()

    def test_synthesize_with_auto_stub_creates_doctrine_artifacts(
        self,
        tmp_path: Path,
        fixture_auto_stub_env: None,
    ) -> None:
        """End-to-end: env-gated stub fixture → on-disk doctrine artifacts."""
        # Pre-condition: nothing on disk yet.
        assert not (tmp_path / ".kittify").exists()
        assert os.environ.get("SPEC_KITTY_FIXTURE_AUTO_STUB") == "1"

        request = _build_minimal_request()
        adapter = FixtureAdapter()  # default fixture_root → repo's tests/charter/fixtures

        # Run the real production-shape synthesize path. The fixture-corpus
        # gap is filled by the env-gated stub mode in FixtureAdapter.generate().
        result = synthesize(request, adapter=adapter, repo_root=tmp_path)
        assert result.effective_adapter_id == "fixture"

        # Manifest is the canonical commit marker (KD-2) — must exist last.
        manifest_path = tmp_path / ".kittify" / "charter" / "synthesis-manifest.yaml"
        assert manifest_path.exists(), (
            f"Expected synthesis manifest at {manifest_path} after a successful "
            "promote; did write_pipeline.promote() complete?"
        )

        # Doctrine subdir must exist with at least one artifact file.
        doctrine_dir = tmp_path / ".kittify" / "doctrine"
        assert doctrine_dir.is_dir(), f"Expected {doctrine_dir} to be created"

        # Iterate kind subdirs; at least one of them must hold the directive
        # the canonical fresh-project interview produces.
        artifact_files: list[Path] = []
        for kind_subdir in ("directives", "tactics", "styleguides"):
            sub = doctrine_dir / kind_subdir
            if sub.is_dir():
                artifact_files.extend(sub.glob("*.yaml"))
        assert artifact_files, (
            f"No artifact YAML files materialized under {doctrine_dir}; "
            "the auto-stub fixture mode failed to land on disk."
        )

        # Provenance sidecars live alongside the charter dir.
        provenance_dir = tmp_path / ".kittify" / "charter" / "provenance"
        assert provenance_dir.is_dir()
        provenance_files = list(provenance_dir.glob("*.yaml"))
        assert provenance_files, (
            f"No provenance sidecars under {provenance_dir}; promote step "
            "completed without sidecar persistence."
        )

    def test_without_auto_stub_env_var_raises(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Without SPEC_KITTY_FIXTURE_AUTO_STUB the missing fixture still raises."""
        monkeypatch.delenv("SPEC_KITTY_FIXTURE_AUTO_STUB", raising=False)
        request = _build_minimal_request()
        adapter = FixtureAdapter()

        from charter.synthesizer.errors import FixtureAdapterMissingError

        with pytest.raises(FixtureAdapterMissingError):
            synthesize(request, adapter=adapter, repo_root=tmp_path)


# ---------------------------------------------------------------------------
# Post-review (PR #855): success envelope contract + dry-run/real path parity
# ---------------------------------------------------------------------------


class TestSynthesizeSuccessEnvelopeContract:
    """Locks the `result/adapter/written_artifacts` contract from
    contracts/charter-synthesize.json. Pre-fix the success branch emitted
    only `target_kind/target_slug/inputs_hash/adapter_id/adapter_version`,
    silently violating the documented contract."""

    def test_read_written_artifacts_from_manifest_returns_path_and_kind(
        self, tmp_path: Path, fixture_auto_stub_env: None
    ) -> None:
        """After a real synthesize, the manifest yields {path, kind} entries."""
        from specify_cli.cli.commands.charter import _read_written_artifacts_from_manifest

        request = _build_minimal_request()
        adapter = FixtureAdapter()
        synthesize(request, adapter=adapter, repo_root=tmp_path)

        written = _read_written_artifacts_from_manifest(tmp_path)
        assert written, "Expected manifest-derived written_artifacts to be non-empty"
        for entry in written:
            assert isinstance(entry, dict)
            assert {"path", "kind"} <= set(entry.keys())
            assert entry["path"].startswith(".kittify/doctrine/")
            assert entry["kind"] in {"directive", "tactic", "styleguide"}

    def test_success_envelope_carries_contract_fields(
        self, tmp_path: Path, fixture_auto_stub_env: None
    ) -> None:
        """`result`, `adapter`, and `written_artifacts` MUST be present.

        Drives `charter synthesize --adapter fixture --json` (no --dry-run)
        through the Typer CliRunner with the auto-stub env var set so the
        real promote path materializes a manifest. The envelope MUST carry
        the three contract-required fields.
        """
        import json as _json
        from unittest.mock import patch

        from typer.testing import CliRunner

        from specify_cli.cli.commands.charter import app

        # Seed minimal interview answers so the request can be built.
        answers_path = tmp_path / ".kittify" / "charter" / "interview" / "answers.yaml"
        answers_path.parent.mkdir(parents=True, exist_ok=True)
        answers_path.write_text(
            "schema_version: '1'\n"
            "mission: software-dev\n"
            "profile: minimal\n"
            "answers:\n"
            "  mission_type: software_dev\n"
            "  testing_philosophy: test-driven\n"
            "  neutrality_posture: balanced\n"
            "  risk_appetite: moderate\n"
            "  language_scope: python\n"
            "selected_paradigms: []\n"
            "selected_directives:\n"
            "  - DIRECTIVE_003\n"
            "available_tools: []\n",
            encoding="utf-8",
        )

        runner = CliRunner()
        with patch(
            "specify_cli.cli.commands.charter.find_repo_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(
                app,
                ["synthesize", "--adapter", "fixture", "--json"],
            )

        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        # Contract: contracts/charter-synthesize.json requires these keys.
        assert payload.get("result") == "success"
        assert "adapter" in payload, (
            f"Pre-fix envelope missing `adapter` field. payload={payload!r}"
        )
        assert "written_artifacts" in payload, (
            f"Pre-fix envelope missing `written_artifacts` field. payload={payload!r}"
        )
        assert isinstance(payload["written_artifacts"], list)
        assert len(payload["written_artifacts"]) >= 1, (
            "Expected at least one written artifact in success envelope"
        )
        for entry in payload["written_artifacts"]:
            assert isinstance(entry, dict)
            assert {"path", "kind"} <= set(entry.keys())
            assert entry["path"].startswith(".kittify/doctrine/")


class TestDryRunPathParityWithRealSynthesize:
    """Locks parity between dry-run planned paths and real synthesize output.

    Pre-fix `_staged_to_planned_artifacts` invented `PROJECT_000` for every
    directive, so dry-run claimed `.kittify/doctrine/directives/000-...`
    while real synthesize wrote `001-...`. Post-fix, the helper derives the
    artifact_id from the provenance `artifact_urn`, matching the real path.
    """

    def test_dry_run_directive_path_matches_real_synthesize(
        self, tmp_path: Path, fixture_auto_stub_env: None
    ) -> None:
        from specify_cli.cli.commands.charter import (
            _provenance_to_planned_artifacts,
        )
        from charter.synthesizer.synthesize_pipeline import run_all

        request = _build_minimal_request()
        adapter = FixtureAdapter()

        # 1. Real synthesize: writes artifacts to disk. The on-disk filename
        #    is the truth (e.g., `001-mission-type-scope-directive.directive.yaml`).
        synthesize(request, adapter=adapter, repo_root=tmp_path)
        directives_dir = tmp_path / ".kittify" / "doctrine" / "directives"
        real_files = sorted(p.name for p in directives_dir.glob("*.directive.yaml"))
        assert real_files, "Real synthesize must produce at least one directive"

        # 2. Provenance-derived dry-run paths: same numeric prefix as real files.
        results = run_all(request, adapter=adapter)
        planned = _provenance_to_planned_artifacts(results)
        directive_planned = [e for e in planned if e["kind"] == "directive"]
        assert directive_planned, "Expected at least one planned directive"

        for entry in directive_planned:
            planned_basename = entry["path"].rsplit("/", 1)[-1]
            assert planned_basename in real_files, (
                "Dry-run planned path does not match real synthesize output.\n"
                f"  planned : {entry['path']}\n"
                f"  real_files: {real_files}\n"
                "Pre-fix bug: dry-run invented PROJECT_000 → 000-..., but real "
                "synthesize uses provenance.artifact_urn → 001-..."
            )
            # Belt-and-suspenders: planned path MUST NOT carry the legacy
            # 000- placeholder prefix (the pre-fix behavior).
            assert "/000-" not in entry["path"], (
                f"Dry-run path still uses placeholder PROJECT_000 prefix: "
                f"{entry['path']!r}"
            )
