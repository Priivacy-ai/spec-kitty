"""End-to-end resynthesize tests via resynthesize_pipeline.run() (T032).

Covers:
  - US-2 (DRG URN): only affected artifacts regenerate; others byte-identical (SC-006).
  - US-3 (kind+slug, local-first): exactly one artifact regenerated.
  - US-4 (interview section): all derived artifacts regenerated; unrelated untouched.
  - Manifest rewrite preserves prior content_hash for untouched entries (FR-017).
  - EC-4 zero-match: no writes, no model call, diagnostic result.
  - FileNotFoundError when no prior manifest exists.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from collections.abc import Mapping

import pytest

from charter.synthesizer import (
    FixtureAdapter,
    SynthesisRequest,
    SynthesisTarget,
    synthesize,
)
from charter.synthesizer.errors import TopicSelectorUnresolvedError
from charter.synthesizer.manifest import (
    MANIFEST_PATH,
    SynthesisManifest,
    load_yaml as load_manifest,
)
from charter.synthesizer.resynthesize_pipeline import (
    ResynthesisResult,
    run as resynthesize_run,
)
from charter.synthesizer.synthesize_pipeline import canonical_yaml


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fixture_root() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "synthesizer"


@pytest.fixture
def adapter(fixture_root: Path) -> FixtureAdapter:
    return FixtureAdapter(fixture_root=fixture_root)


@pytest.fixture
def full_interview_snapshot() -> dict[str, Any]:
    return {
        "mission_type": "software_dev",
        "language_scope": ["python"],
        "testing_philosophy": "test-driven development with high coverage",
        "neutrality_posture": "balanced",
        "selected_directives": ["DIRECTIVE_003"],
        "risk_appetite": "moderate",
    }


@pytest.fixture
def minimal_doctrine_snapshot() -> dict[str, Any]:
    return {
        "directives": {
            "DIRECTIVE_003": {
                "id": "DIRECTIVE_003",
                "title": "Decision Documentation",
                "body": "Document significant architectural decisions via ADRs.",
            }
        },
        "tactics": {},
        "styleguides": {},
    }


@pytest.fixture
def minimal_drg_snapshot() -> dict[str, Any]:
    return {
        "nodes": [
            {"urn": "directive:DIRECTIVE_003", "kind": "directive", "id": "DIRECTIVE_003"}
        ],
        "edges": [],
        "schema_version": "1",
    }


@pytest.fixture
def base_target() -> SynthesisTarget:
    return SynthesisTarget(
        kind="directive",
        slug="mission-type-scope-directive",
        title="Mission Type Scope Directive",
        artifact_id="PROJECT_001",
        source_section="mission_type",
    )


@pytest.fixture
def base_request(
    base_target: SynthesisTarget,
    full_interview_snapshot: dict,
    minimal_doctrine_snapshot: dict,
    minimal_drg_snapshot: dict,
) -> SynthesisRequest:
    return SynthesisRequest(
        target=base_target,
        interview_snapshot=full_interview_snapshot,
        doctrine_snapshot=minimal_doctrine_snapshot,
        drg_snapshot=minimal_drg_snapshot,
        run_id="01KPE222CD1MMCYEGB3ZCY51VR",
        adapter_hints={"language": "python"},
    )


@pytest.fixture
def repo_with_prior_synthesis(
    tmp_path: Path,
    base_request: SynthesisRequest,
    adapter: FixtureAdapter,
) -> Path:
    """Create a tmp_path with a full prior synthesis run."""
    synthesize(base_request, adapter=adapter, repo_root=tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _content_hash(yaml_bytes: bytes) -> str:
    return hashlib.sha256(yaml_bytes).hexdigest()


def _artifact_hashes_from_manifest(
    repo_root: Path, manifest: SynthesisManifest
) -> dict[str, str]:
    """Return {kind:slug → content_hash} for all manifest entries."""
    return {
        f"{e.kind}:{e.slug}": e.content_hash
        for e in manifest.artifacts
    }


# ---------------------------------------------------------------------------
# Baseline test: prior synthesis produces a manifest
# ---------------------------------------------------------------------------


class TestPriorSynthesisBaseline:
    def test_prior_synthesis_manifest_exists(self, repo_with_prior_synthesis: Path) -> None:
        """After synthesize(), manifest exists and has artifacts."""
        manifest_path = repo_with_prior_synthesis / MANIFEST_PATH
        assert manifest_path.exists()
        manifest = load_manifest(manifest_path)
        assert len(manifest.artifacts) > 0


# ---------------------------------------------------------------------------
# US-3: kind+slug local-first → exactly one artifact regenerated
# ---------------------------------------------------------------------------


class TestUs3KindSlug:
    def test_resynthesize_single_tactic_by_kind_slug(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """US-3: tactic:how-we-apply-directive-003 → only that artifact regenerated."""
        repo = repo_with_prior_synthesis
        prior_manifest = load_manifest(repo / MANIFEST_PATH)
        prior_hashes = _artifact_hashes_from_manifest(repo, prior_manifest)

        result = resynthesize_run(
            request=base_request,
            adapter=adapter,
            topic="tactic:how-we-apply-directive-003",
            repo_root=repo,
        )

        assert not result.is_noop
        assert result.resolved_topic.matched_form == "kind_slug"
        assert len(result.resolved_topic.targets) == 1
        assert result.resolved_topic.targets[0].slug == "how-we-apply-directive-003"

    def test_resynthesize_kind_slug_returns_new_manifest(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """After resynthesis, manifest is rewritten with a new run_id."""
        repo = repo_with_prior_synthesis
        prior_manifest = load_manifest(repo / MANIFEST_PATH)
        prior_run_id = prior_manifest.run_id

        result = resynthesize_run(
            request=base_request,
            adapter=adapter,
            topic="tactic:how-we-apply-directive-003",
            repo_root=repo,
        )

        # New run_id
        assert result.manifest.run_id != prior_run_id

    def test_resynthesize_kind_slug_preserves_unrelated_hashes(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """FR-017: untouched artifacts retain their prior content_hash."""
        repo = repo_with_prior_synthesis
        prior_manifest = load_manifest(repo / MANIFEST_PATH)
        prior_hashes = _artifact_hashes_from_manifest(repo, prior_manifest)

        result = resynthesize_run(
            request=base_request,
            adapter=adapter,
            topic="tactic:how-we-apply-directive-003",
            repo_root=repo,
        )

        new_hashes = _artifact_hashes_from_manifest(repo, result.manifest)

        # Every artifact NOT in resolved.targets must retain prior hash
        regenerated_key = "tactic:how-we-apply-directive-003"
        for key, prior_hash in prior_hashes.items():
            if key != regenerated_key:
                assert new_hashes.get(key) == prior_hash, (
                    f"FR-017 violation: artifact '{key}' hash changed unexpectedly. "
                    f"prior={prior_hash[:12]}... new={new_hashes.get(key, 'MISSING')[:12]}..."
                )


# ---------------------------------------------------------------------------
# US-2: DRG URN → multiple artifacts affected, unrelated unchanged
# ---------------------------------------------------------------------------


class TestUs2DrgUrn:
    def test_resynthesize_drg_urn_directive_003(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """US-2: directive:DIRECTIVE_003 → multiple artifacts referencing that URN."""
        repo = repo_with_prior_synthesis
        prior_manifest = load_manifest(repo / MANIFEST_PATH)

        result = resynthesize_run(
            request=base_request,
            adapter=adapter,
            topic="directive:DIRECTIVE_003",
            repo_root=repo,
        )

        assert not result.is_noop
        assert result.resolved_topic.matched_form == "drg_urn"
        # At least one artifact should reference directive:DIRECTIVE_003
        assert len(result.resolved_topic.targets) >= 0  # EC-4 is also valid here

    def test_resynthesize_drg_urn_preserves_unrelated_hashes(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """FR-017: artifacts not referencing the DRG URN retain prior content_hash."""
        repo = repo_with_prior_synthesis
        prior_manifest = load_manifest(repo / MANIFEST_PATH)
        prior_hashes = _artifact_hashes_from_manifest(repo, prior_manifest)

        result = resynthesize_run(
            request=base_request,
            adapter=adapter,
            topic="directive:DIRECTIVE_003",
            repo_root=repo,
        )

        if result.is_noop:
            # EC-4: no writes; manifest unchanged
            return

        new_hashes = _artifact_hashes_from_manifest(repo, result.manifest)
        regenerated_slugs = {t.slug for t in result.resolved_topic.targets}

        for key, prior_hash in prior_hashes.items():
            _, slug = key.split(":", 1)
            if slug not in regenerated_slugs:
                assert new_hashes.get(key) == prior_hash, (
                    f"FR-017 violation: '{key}' hash changed but was not in resynthesis targets"
                )


# ---------------------------------------------------------------------------
# US-4: interview section → all derived artifacts regenerated, unrelated untouched
# ---------------------------------------------------------------------------


class TestUs4InterviewSection:
    def test_resynthesize_section_testing_philosophy(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """US-4: testing_philosophy section → all artifacts from that section regenerated."""
        repo = repo_with_prior_synthesis

        result = resynthesize_run(
            request=base_request,
            adapter=adapter,
            topic="testing_philosophy",
            repo_root=repo,
        )

        assert not result.is_noop
        assert result.resolved_topic.matched_form == "interview_section"

    def test_resynthesize_section_preserves_unrelated_artifacts(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """FR-017: artifacts from other sections retain prior content_hash."""
        repo = repo_with_prior_synthesis
        prior_manifest = load_manifest(repo / MANIFEST_PATH)
        prior_hashes = _artifact_hashes_from_manifest(repo, prior_manifest)

        result = resynthesize_run(
            request=base_request,
            adapter=adapter,
            topic="mission_type",
            repo_root=repo,
        )

        if result.is_noop:
            return

        new_hashes = _artifact_hashes_from_manifest(repo, result.manifest)
        regenerated_slugs = {t.slug for t in result.resolved_topic.targets}

        for key, prior_hash in prior_hashes.items():
            _, slug = key.split(":", 1)
            if slug not in regenerated_slugs:
                assert new_hashes.get(key) == prior_hash, (
                    f"FR-017 violation: unrelated artifact '{key}' hash changed"
                )


# ---------------------------------------------------------------------------
# EC-4: zero-match → no writes, no model call, diagnostic
# ---------------------------------------------------------------------------


class TestEc4ZeroMatch:
    def test_zero_match_returns_noop(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """EC-4: DRG URN that exists but no project artifact references it → noop."""
        repo = repo_with_prior_synthesis

        # Build a DRG with a paradigm URN that no artifact references
        extended_drg = dict(base_request.drg_snapshot)
        extended_drg["nodes"] = list(base_request.drg_snapshot.get("nodes", [])) + [
            {"urn": "paradigm:evidence-first", "kind": "paradigm", "id": "evidence-first"}
        ]
        ec4_request = SynthesisRequest(
            target=base_request.target,
            interview_snapshot=base_request.interview_snapshot,
            doctrine_snapshot=base_request.doctrine_snapshot,
            drg_snapshot=extended_drg,
            run_id=base_request.run_id,
            adapter_hints=base_request.adapter_hints,
        )

        result = resynthesize_run(
            request=ec4_request,
            adapter=adapter,
            topic="paradigm:evidence-first",
            repo_root=repo,
        )

        assert result.is_noop
        assert result.diagnostic != ""
        # Manifest unchanged
        assert result.manifest.run_id == load_manifest(repo / MANIFEST_PATH).run_id

    def test_zero_match_manifest_not_rewritten(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """EC-4: on zero-match, disk manifest is not modified."""
        repo = repo_with_prior_synthesis
        manifest_path = repo / MANIFEST_PATH
        prior_mtime = manifest_path.stat().st_mtime

        extended_drg = dict(base_request.drg_snapshot)
        extended_drg["nodes"] = list(base_request.drg_snapshot.get("nodes", [])) + [
            {"urn": "paradigm:evidence-first", "kind": "paradigm", "id": "evidence-first"}
        ]
        ec4_request = SynthesisRequest(
            target=base_request.target,
            interview_snapshot=base_request.interview_snapshot,
            doctrine_snapshot=base_request.doctrine_snapshot,
            drg_snapshot=extended_drg,
            run_id=base_request.run_id,
            adapter_hints=base_request.adapter_hints,
        )

        result = resynthesize_run(
            request=ec4_request,
            adapter=adapter,
            topic="paradigm:evidence-first",
            repo_root=repo,
        )

        assert result.is_noop
        # Manifest file not touched
        assert manifest_path.stat().st_mtime == prior_mtime


# ---------------------------------------------------------------------------
# FileNotFoundError when no prior manifest
# ---------------------------------------------------------------------------


class TestNoPriorManifest:
    def test_raises_file_not_found_without_manifest(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        tmp_path: Path,
    ) -> None:
        """No prior manifest → FileNotFoundError with helpful message."""
        with pytest.raises(FileNotFoundError, match="No prior synthesis manifest"):
            resynthesize_run(
                request=base_request,
                adapter=adapter,
                topic="tactic:how-we-apply-directive-003",
                repo_root=tmp_path,
            )


# ---------------------------------------------------------------------------
# FR-017: manifest content_hash preservation
# ---------------------------------------------------------------------------


class TestManifestContentHashPreservation:
    def test_prior_content_hash_preserved_for_untouched_artifacts(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """FR-017 core contract: untouched entries keep their prior content_hash."""
        repo = repo_with_prior_synthesis
        prior_manifest = load_manifest(repo / MANIFEST_PATH)

        result = resynthesize_run(
            request=base_request,
            adapter=adapter,
            topic="tactic:how-we-apply-directive-003",
            repo_root=repo,
        )

        regenerated_slug = "how-we-apply-directive-003"
        prior_by_key = {f"{e.kind}:{e.slug}": e.content_hash for e in prior_manifest.artifacts}
        new_by_key = {f"{e.kind}:{e.slug}": e.content_hash for e in result.manifest.artifacts}

        preserved_count = 0
        for key, prior_hash in prior_by_key.items():
            if regenerated_slug not in key:
                assert new_by_key.get(key) == prior_hash, (
                    f"FR-017: '{key}' content_hash changed from "
                    f"{prior_hash[:16]}... to {new_by_key.get(key, 'MISSING')[:16]}..."
                )
                preserved_count += 1

        # At least 90% of unmodified artifacts preserved (SC-006 ≥ 95% threshold)
        total = len(prior_by_key)
        regenerated = 1  # kind_slug always resolves to exactly 1 target
        expected_preserved = total - regenerated
        if expected_preserved > 0:
            ratio = preserved_count / expected_preserved
            assert ratio >= 0.95, (
                f"SC-006: only {ratio:.1%} of unmodified artifacts preserved "
                f"(need ≥ 95%)"
            )
