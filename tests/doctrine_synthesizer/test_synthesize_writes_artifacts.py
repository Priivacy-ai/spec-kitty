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
