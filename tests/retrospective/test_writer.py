"""Tests for write_gen_record (WP03 — T013, T014).

Covers:
- T013: Three write modes (error, overwrite, update) with merge semantics.
- T014: Defense-in-depth synthesize_fabricate ⇒ ran_no_findings invariant.
- Atomic write verification (kill-between-tmp-and-rename simulation).

FR-016: No env-var mutation in this test file.
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path

import pytest

from specify_cli.retrospective.schema import (
    GenActor,
    GenEvidenceRef,
    GenFinding,
    GenProposal,
    GenProvenance,
    GenRetrospectiveRecord,
    RecordValidationError,
)
from specify_cli.retrospective.writer import (
    RecordExistsError,
    WriterError,
    _dict_to_gen_record,
    _gen_record_to_dict,
    _merge_gen_records,
    write_gen_record,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Test fixture helpers
# ---------------------------------------------------------------------------

MISSION_ID = "01KS049J4V9CSWBKJHTY2FB69H"
MISSION_SLUG = "test-mission-01KS049J"

_ACTOR = GenActor(kind="runtime", id="spec-kitty-cli@3.2.0", display="spec-kitty runtime")

_PROVENANCE_RUNTIME = GenProvenance(
    kind="runtime_post_completion",
    invoked_at="2026-05-19T10:00:00+00:00",
    policy_resolved_from={"enabled": "<default>", "timing": "<default>"},
)

_PROVENANCE_EXPLICIT = GenProvenance(
    kind="explicit_create",
    invoked_at="2026-05-19T11:00:00+00:00",
    policy_resolved_from={"enabled": ".kittify/config.yaml#retrospective.enabled"},
)


def make_record(
    *,
    mission_id: str = MISSION_ID,
    mission_slug: str = MISSION_SLUG,
    findings_status: str = "ran_no_findings",
    provenance: GenProvenance | None = None,
    helped: list[GenFinding] | None = None,
    not_helpful: list[GenFinding] | None = None,
    gaps: list[GenFinding] | None = None,
    proposals: list[GenProposal] | None = None,
    evidence_refs: list[GenEvidenceRef] | None = None,
    policy_source: dict[str, str] | None = None,
) -> GenRetrospectiveRecord:
    """Build a minimal valid GenRetrospectiveRecord for testing."""
    if provenance is None:
        provenance = _PROVENANCE_RUNTIME
    if helped is None:
        helped = []
    if not_helpful is None:
        not_helpful = []
    if gaps is None:
        gaps = []
    if proposals is None:
        proposals = []
    if evidence_refs is None:
        evidence_refs = []
    if policy_source is None:
        policy_source = {"enabled": "<default>"}
    return GenRetrospectiveRecord(
        schema_version=1,
        mission_id=mission_id,
        mission_slug=mission_slug,
        mission_number=None,
        friendly_name="Test Mission",
        mission_type="software-dev",
        target_branch="main",
        created_at="2026-05-19T10:00:00+00:00",
        created_by=_ACTOR,
        provenance=provenance,
        policy_source=policy_source,
        findings_status=findings_status,
        helped=helped,
        not_helpful=not_helpful,
        gaps=gaps,
        proposals=proposals,
        evidence_refs=evidence_refs,
        generator_version="1.0",
    )


def make_finding(
    fid: str,
    category: str = "process",
    summary: str = "A test finding",
) -> GenFinding:
    return GenFinding(id=fid, category=category, summary=summary)


def make_evidence_ref(eid: str, path: str = "src/foo.py") -> GenEvidenceRef:
    return GenEvidenceRef(id=eid, kind="file", path=path, range="L1-L10")


def make_proposal(pid: str, category: str = "process", summary: str = "A test proposal") -> GenProposal:
    return GenProposal(
        id=pid,
        category=category,
        risk_class="low",
        summary=summary,
        evidence_refs=[],
        suggested_action="Update the process docs.",
        auto_applicable=False,
    )


# ---------------------------------------------------------------------------
# T013: Three write modes
# ---------------------------------------------------------------------------


class TestWriteGenRecordModeError:
    def test_mode_error_writes_when_absent(self, tmp_path: Path) -> None:
        """mode='error' writes successfully when canonical path does not exist."""
        record = make_record()
        canonical = write_gen_record(record, mode="error", repo_root=tmp_path)

        assert canonical.exists()
        assert canonical.name == "retrospective.yaml"
        # FR-006 (#1771): record lands in the tracked feature_dir, not .kittify/missions/.
        assert MISSION_SLUG in str(canonical)
        assert "kitty-specs" in str(canonical)
        assert ".kittify" not in str(canonical)

    def test_mode_error_raises_when_exists(self, tmp_path: Path) -> None:
        """mode='error' raises RecordExistsError when canonical path already exists."""
        record = make_record()
        write_gen_record(record, mode="error", repo_root=tmp_path)

        with pytest.raises(RecordExistsError) as exc_info:
            write_gen_record(record, mode="error", repo_root=tmp_path)

        assert MISSION_SLUG in str(exc_info.value.path)
        assert "overwrite" in str(exc_info.value).lower() or "--overwrite" in str(exc_info.value)

    def test_mode_error_record_exists_error_is_writer_error(self, tmp_path: Path) -> None:
        """RecordExistsError is a subclass of WriterError."""
        record = make_record()
        write_gen_record(record, mode="error", repo_root=tmp_path)

        with pytest.raises(WriterError):
            write_gen_record(record, mode="error", repo_root=tmp_path)


class TestWriteGenRecordModeOverwrite:
    def test_mode_overwrite_replaces_wholesale(self, tmp_path: Path) -> None:
        """mode='overwrite' replaces existing record wholesale."""
        r1 = make_record(
            findings_status="has_findings",
            helped=[make_finding("h-001")],
            evidence_refs=[make_evidence_ref("e-001")],
        )
        r1_findings = dataclasses.replace(r1, helped=[make_finding("h-001")])
        write_gen_record(r1_findings, mode="overwrite", repo_root=tmp_path)

        r2 = make_record(findings_status="ran_no_findings")
        canonical = write_gen_record(r2, mode="overwrite", repo_root=tmp_path)

        # Read back and verify only r2 content survives.
        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        data = yaml.load(canonical.read_text(encoding="utf-8"))
        assert data["findings_status"] == "ran_no_findings"
        assert data["helped"] == []

    def test_mode_overwrite_creates_on_absent(self, tmp_path: Path) -> None:
        """mode='overwrite' creates the file when it does not exist."""
        record = make_record()
        canonical = write_gen_record(record, mode="overwrite", repo_root=tmp_path)
        assert canonical.exists()


class TestWriteGenRecordModeUpdate:
    def test_mode_update_first_write_creates(self, tmp_path: Path) -> None:
        """mode='update' with no existing record behaves like mode='error' (first write)."""
        record = make_record()
        canonical = write_gen_record(record, mode="update", repo_root=tmp_path)
        assert canonical.exists()

    def test_mode_update_merges_findings(self, tmp_path: Path) -> None:
        """mode='update' deduplicates findings by (category, summary.lower())."""
        r1 = make_record(
            findings_status="has_findings",
            helped=[make_finding("h-001", "process", "Deploy automation helped a lot")],
            evidence_refs=[make_evidence_ref("e-001")],
        )
        write_gen_record(r1, mode="error", repo_root=tmp_path)

        # Second record has the same finding (case-insensitive) plus a new one.
        r2 = make_record(
            provenance=_PROVENANCE_EXPLICIT,
            findings_status="has_findings",
            helped=[
                make_finding("h-001b", "process", "Deploy automation helped a LOT"),  # duplicate
                make_finding("h-002", "tooling", "Ruff saved time"),  # new
            ],
            evidence_refs=[make_evidence_ref("e-002", "src/bar.py")],
        )
        canonical = write_gen_record(r2, mode="update", repo_root=tmp_path)

        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        data = yaml.load(canonical.read_text(encoding="utf-8"))
        helped = data["helped"]

        # Should have 2 unique findings: original h-001 + new h-002 (duplicate excluded).
        summaries = [(f["category"], f["summary"].lower()) for f in helped]
        assert ("process", "deploy automation helped a lot") in summaries
        assert ("tooling", "ruff saved time") in summaries
        assert len(summaries) == 2

    def test_mode_update_deduplicates_evidence_refs(self, tmp_path: Path) -> None:
        """mode='update' deduplicates evidence_refs by (kind, path, range, url)."""
        ev1 = make_evidence_ref("e-001", "src/foo.py")

        r1 = make_record(
            findings_status="has_findings",
            helped=[make_finding("h-001")],
            evidence_refs=[ev1],
        )
        write_gen_record(r1, mode="error", repo_root=tmp_path)

        # Second record has the same evidence ref + a new one.
        r2 = make_record(
            provenance=_PROVENANCE_EXPLICIT,
            findings_status="has_findings",
            helped=[make_finding("h-002", "tooling", "New finding")],
            evidence_refs=[
                make_evidence_ref("e-001dup", "src/foo.py"),  # same path/range → duplicate
                make_evidence_ref("e-002", "src/bar.py"),     # new
            ],
        )
        canonical = write_gen_record(r2, mode="update", repo_root=tmp_path)

        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        data = yaml.load(canonical.read_text(encoding="utf-8"))
        evidence_paths = [(e["kind"], e["path"], e.get("range")) for e in data["evidence_refs"]]
        # e-001 and e-001dup have same (file, src/foo.py, L1-L10) → only one survives.
        assert ("file", "src/foo.py", "L1-L10") in evidence_paths
        assert ("file", "src/bar.py", "L1-L10") in evidence_paths
        assert len(evidence_paths) == 2

    def test_mode_update_accumulates_provenance_history(self, tmp_path: Path) -> None:
        """mode='update' prepends prior provenance to provenance_history."""
        r1 = make_record(provenance=_PROVENANCE_RUNTIME)
        write_gen_record(r1, mode="error", repo_root=tmp_path)

        r2 = make_record(provenance=_PROVENANCE_EXPLICIT)
        canonical = write_gen_record(r2, mode="update", repo_root=tmp_path)

        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        data = yaml.load(canonical.read_text(encoding="utf-8"))

        # Active provenance should be the new (explicit_create).
        assert data["provenance"]["kind"] == "explicit_create"
        # History should contain the prior runtime_post_completion entry.
        assert len(data["provenance_history"]) == 1
        assert data["provenance_history"][0]["kind"] == "runtime_post_completion"

    def test_mode_update_recomputes_findings_status(self, tmp_path: Path) -> None:
        """mode='update' recomputes findings_status from final lists."""
        # Start with no findings (ran_no_findings).
        r1 = make_record(findings_status="ran_no_findings")
        write_gen_record(r1, mode="error", repo_root=tmp_path)

        # Update with a real finding.
        r2 = make_record(
            provenance=_PROVENANCE_EXPLICIT,
            findings_status="has_findings",
            helped=[make_finding("h-001")],
        )
        canonical = write_gen_record(r2, mode="update", repo_root=tmp_path)

        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        data = yaml.load(canonical.read_text(encoding="utf-8"))
        assert data["findings_status"] == "has_findings"

    def test_mode_update_policy_source_replaced_wholesale(self, tmp_path: Path) -> None:
        """mode='update' replaces policy_source wholesale."""
        r1 = make_record(policy_source={"enabled": "<default>", "timing": "<default>"})
        write_gen_record(r1, mode="error", repo_root=tmp_path)

        r2 = make_record(
            provenance=_PROVENANCE_EXPLICIT,
            policy_source={"enabled": ".kittify/config.yaml#retrospective.enabled"},
        )
        canonical = write_gen_record(r2, mode="update", repo_root=tmp_path)

        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        data = yaml.load(canonical.read_text(encoding="utf-8"))
        # Old policy_source keys are gone; only new one remains.
        assert data["policy_source"] == {
            "enabled": ".kittify/config.yaml#retrospective.enabled"
        }


class TestAtomicWriteErrorPaths:
    """Tests for _atomic_write_gen OSError and generic Exception recovery paths."""

    def test_os_error_during_write_raises_writer_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OSError during os.replace wraps into WriterError."""
        def fail_replace(src: str, dst: str) -> None:
            raise OSError("Disk full")

        monkeypatch.setattr(os, "replace", fail_replace)

        record = make_record()
        with pytest.raises(WriterError, match="IO error writing retrospective record"):
            write_gen_record(record, mode="error", repo_root=tmp_path)

    def test_generic_exception_during_write_raises_writer_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-OSError exception during write wraps into WriterError."""
        def exploding_replace(src: str, dst: str) -> None:
            raise RuntimeError("Unexpected runtime error")

        monkeypatch.setattr(os, "replace", exploding_replace)

        record = make_record()
        with pytest.raises(WriterError, match="Unexpected error writing retrospective record"):
            write_gen_record(record, mode="error", repo_root=tmp_path)


class TestWriteGenRecordAtomicity:
    """Verify that a crash between tmp write and rename leaves no partial record.

    Simulates an interrupted rename via monkeypatching os.replace.
    """

    def test_first_write_crash_leaves_no_canonical(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Simulated crash on first write: canonical must not exist."""
        canonical = tmp_path / "kitty-specs" / MISSION_SLUG / "retrospective.yaml"

        def crashing_replace(src: str, dst: str) -> None:
            raise OSError("Simulated crash mid-replace")

        monkeypatch.setattr(os, "replace", crashing_replace)

        record = make_record()
        with pytest.raises((WriterError, OSError)):
            write_gen_record(record, mode="error", repo_root=tmp_path)

        assert not canonical.exists(), (
            "Canonical file must not exist after a first-write crash"
        )

    def test_second_write_crash_leaves_prior_canonical(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Simulated crash on second write: canonical must still hold prior version."""
        record_v1 = make_record(findings_status="ran_no_findings")
        canonical = write_gen_record(record_v1, mode="error", repo_root=tmp_path)
        prior_content = canonical.read_bytes()
        assert len(prior_content) > 0

        original_replace = os.replace
        call_count = [0]

        def crashing_replace(src: str, dst: str) -> None:
            call_count[0] += 1
            if call_count[0] >= 1:
                raise OSError("Simulated crash on second write")
            original_replace(src, dst)

        monkeypatch.setattr(os, "replace", crashing_replace)

        record_v2 = make_record(
            provenance=_PROVENANCE_EXPLICIT,
            findings_status="has_findings",
            helped=[make_finding("h-001")],
            evidence_refs=[make_evidence_ref("e-001")],
        )
        with pytest.raises((WriterError, OSError)):
            write_gen_record(record_v2, mode="overwrite", repo_root=tmp_path)

        # Prior version must survive untouched.
        assert canonical.exists()
        assert canonical.read_bytes() == prior_content

    def test_tempfile_in_same_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Tempfile must be created in the same directory as the canonical file."""
        captured_src: list[str] = []
        original_replace = os.replace

        def capturing_replace(src: str, dst: str) -> None:
            captured_src.append(src)
            original_replace(src, dst)

        monkeypatch.setattr(os, "replace", capturing_replace)

        record = make_record()
        canonical = write_gen_record(record, mode="error", repo_root=tmp_path)

        assert len(captured_src) == 1
        tmp_used = Path(captured_src[0])
        assert tmp_used.parent == canonical.parent
        assert "tmp" in tmp_used.name


# ---------------------------------------------------------------------------
# T014: synthesize_fabricate ⇒ ran_no_findings invariant
# ---------------------------------------------------------------------------


class TestSynthesizeFabricateInvariant:
    def test_synthesize_fabricate_with_findings_rejected(self, tmp_path: Path) -> None:
        """Writer rejects synthesize_fabricate + has_findings (T014 defense-in-depth)."""
        bad_provenance = GenProvenance(
            kind="synthesize_fabricate",
            invoked_at="2026-05-19T10:00:00+00:00",
        )
        record = make_record(
            provenance=bad_provenance,
            findings_status="has_findings",
            helped=[make_finding("h-001")],
            evidence_refs=[make_evidence_ref("e-001")],
        )
        with pytest.raises(RecordValidationError) as exc_info:
            write_gen_record(record, mode="error", repo_root=tmp_path)

        assert "synthesize_fabricate" in str(exc_info.value)
        assert "ran_no_findings" in str(exc_info.value)

        # Canonical must not be written.
        canonical = tmp_path / "kitty-specs" / MISSION_SLUG / "retrospective.yaml"
        assert not canonical.exists()


# ---------------------------------------------------------------------------
# Coverage gap tests (T013 edge cases for branch/path coverage)
# ---------------------------------------------------------------------------


class TestWriteGenRecordEdgeCases:
    """Edge-case tests for write_gen_record branch coverage."""

    def test_empty_mission_slug_raises_writer_error(self, tmp_path: Path) -> None:
        """Empty mission_slug must raise WriterError before any IO.

        FR-006 (#1771): the record path is derived from the mission_slug
        (tracked feature_dir), so an empty slug cannot resolve a canonical path.
        """
        record = make_record(mission_slug="")
        with pytest.raises(WriterError, match="mission_slug must be non-empty"):
            write_gen_record(record, mode="error", repo_root=tmp_path)

    def test_unknown_mode_raises_writer_error(self, tmp_path: Path) -> None:
        """An unknown mode string must raise WriterError."""
        record = make_record()
        with pytest.raises(WriterError, match="Unknown write mode"):
            write_gen_record(record, mode="bogus", repo_root=tmp_path)  # type: ignore[arg-type]

    def test_mode_update_with_invalid_yaml_in_existing_record(
        self, tmp_path: Path
    ) -> None:
        """mode='update' with a non-mapping existing YAML raises WriterError."""
        canonical = tmp_path / "kitty-specs" / MISSION_SLUG / "retrospective.yaml"
        canonical.parent.mkdir(parents=True)
        # Write a scalar (not a mapping) to the canonical path.
        canonical.write_text("just a string\n", encoding="utf-8")

        record = make_record(provenance=_PROVENANCE_EXPLICIT)
        with pytest.raises(WriterError, match="not a YAML mapping"):
            write_gen_record(record, mode="update", repo_root=tmp_path)

    def test_mode_update_deduplicates_proposals(self, tmp_path: Path) -> None:
        """mode='update' deduplicates proposals by (category, summary.lower())."""
        r1 = make_record(
            findings_status="has_findings",
            proposals=[make_proposal("p-001", summary="Adopt structured logging")],
        )
        write_gen_record(r1, mode="error", repo_root=tmp_path)

        r2 = make_record(
            provenance=_PROVENANCE_EXPLICIT,
            findings_status="has_findings",
            proposals=[
                # Duplicate (case-insensitive) — should be deduplicated.
                make_proposal("p-002", summary="adopt structured logging"),
                # New proposal — should be appended.
                make_proposal("p-003", summary="Add integration tests"),
            ],
        )
        canonical = write_gen_record(r2, mode="update", repo_root=tmp_path)

        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        data = yaml.load(canonical.read_text(encoding="utf-8"))
        proposal_summaries = [p["summary"] for p in data["proposals"]]
        # Duplicate "adopt structured logging" not re-added; new one appended.
        assert len(proposal_summaries) == 2
        assert "Adopt structured logging" in proposal_summaries
        assert "Add integration tests" in proposal_summaries

    def test_dict_roundtrip_with_proposals_preserves_fields(self) -> None:
        """_gen_record_to_dict / _dict_to_gen_record round-trip preserves proposal fields."""
        record = make_record(
            findings_status="has_findings",
            proposals=[
                GenProposal(
                    id="p-001",
                    category="process",
                    risk_class="medium",
                    summary="Adopt structured logging",
                    evidence_refs=["e-001"],
                    suggested_action="Switch to structlog.",
                    auto_applicable=True,
                    details="See ADR-42.",
                )
            ],
        )
        d = _gen_record_to_dict(record)
        restored = _dict_to_gen_record(d)
        assert len(restored.proposals) == 1
        p = restored.proposals[0]
        assert p.id == "p-001"
        assert p.risk_class == "medium"
        assert p.details == "See ADR-42."
        assert p.auto_applicable is True

    def test_mkdir_failure_raises_writer_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """mkdir failure before write raises WriterError."""
        original_mkdir = Path.mkdir

        def failing_mkdir(self: Path, **kwargs: object) -> None:
            if MISSION_SLUG in str(self):
                raise OSError("Simulated mkdir failure")
            original_mkdir(self, **kwargs)

        monkeypatch.setattr(Path, "mkdir", failing_mkdir)

        record = make_record()
        with pytest.raises(WriterError, match="Cannot create target directory"):
            write_gen_record(record, mode="error", repo_root=tmp_path)

    def test_mode_update_load_exception_raises_writer_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """mode='update' with read_text raising raises WriterError (exception load path)."""
        # First write succeeds.
        record = make_record()
        write_gen_record(record, mode="error", repo_root=tmp_path)

        # Monkeypatch Path.read_text to fail on the existing canonical file.
        original_read_text = Path.read_text

        def failing_read_text(self: Path, *args: object, **kwargs: object) -> str:
            if self.name == "retrospective.yaml":
                raise OSError("Simulated read failure")
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", failing_read_text)

        record2 = make_record(provenance=_PROVENANCE_EXPLICIT)
        with pytest.raises(WriterError, match="Cannot load existing record"):
            write_gen_record(record2, mode="update", repo_root=tmp_path)

    def test_mode_update_with_existing_corrupt_record_raises_writer_error(
        self, tmp_path: Path
    ) -> None:
        """mode='update' with an existing record that fails validation raises WriterError."""
        # Write a YAML dict that is missing required fields so _dict_to_gen_record
        # produces something that fails validate_record.
        canonical = tmp_path / "kitty-specs" / MISSION_SLUG / "retrospective.yaml"
        canonical.parent.mkdir(parents=True)
        # Write a minimal dict that won't fail _dict_to_gen_record (defaults fill in)
        # but sets synthesize_fabricate + has_findings to fail validation.
        from ruamel.yaml import YAML
        yaml = YAML()
        bad_data = {
            "schema_version": 1,
            "mission_id": MISSION_ID,
            "mission_slug": MISSION_SLUG,
            "mission_number": None,
            "friendly_name": "Test",
            "mission_type": "software-dev",
            "target_branch": "main",
            "created_at": "2026-05-19T10:00:00+00:00",
            "created_by": {"kind": "runtime", "id": "spec-kitty@3.2.0"},
            "provenance": {
                "kind": "synthesize_fabricate",
                "invoked_at": "2026-05-19T10:00:00+00:00",
                "policy_resolved_from": {},
            },
            "policy_source": {},
            "findings_status": "has_findings",  # violates synthesize_fabricate invariant
            "helped": [{"id": "h-1", "category": "process", "summary": "x", "evidence_refs": []}],
            "not_helpful": [],
            "gaps": [],
            "proposals": [],
            "evidence_refs": [],
            "generator_version": "1.0",
            "provenance_history": [],
        }
        import io as _io
        buf = _io.StringIO()
        yaml.dump(bad_data, buf)
        canonical.write_text(buf.getvalue(), encoding="utf-8")

        record = make_record(provenance=_PROVENANCE_EXPLICIT)
        with pytest.raises(WriterError, match="fails validation"):
            write_gen_record(record, mode="update", repo_root=tmp_path)

    def test_synthesize_fabricate_with_no_findings_succeeds(self, tmp_path: Path) -> None:
        """synthesize_fabricate + ran_no_findings is valid and writes cleanly."""
        good_provenance = GenProvenance(
            kind="synthesize_fabricate",
            invoked_at="2026-05-19T10:00:00+00:00",
        )
        record = make_record(
            provenance=good_provenance,
            findings_status="ran_no_findings",
        )
        canonical = write_gen_record(record, mode="error", repo_root=tmp_path)
        assert canonical.exists()


# ---------------------------------------------------------------------------
# Serialization / round-trip helpers
# ---------------------------------------------------------------------------


class TestGenRecordSerialisation:
    def test_gen_record_to_dict_and_back(self) -> None:
        """_gen_record_to_dict / _dict_to_gen_record round-trip."""
        record = make_record(
            findings_status="has_findings",
            helped=[make_finding("h-001", "process", "Helped a lot")],
            evidence_refs=[make_evidence_ref("e-001")],
        )
        d = _gen_record_to_dict(record)
        restored = _dict_to_gen_record(d)

        assert restored.mission_id == record.mission_id
        assert restored.findings_status == record.findings_status
        assert len(restored.helped) == 1
        assert restored.helped[0].id == "h-001"

    def test_merge_deduplicates_correctly(self) -> None:
        """_merge_gen_records deduplicates findings and evidence_refs."""
        existing = make_record(
            findings_status="has_findings",
            helped=[make_finding("h-001", "process", "Same Thing")],
            evidence_refs=[make_evidence_ref("e-001", "src/a.py")],
        )
        new_record = make_record(
            provenance=_PROVENANCE_EXPLICIT,
            findings_status="has_findings",
            helped=[
                make_finding("h-001x", "process", "same thing"),  # duplicate by (cat, lower)
                make_finding("h-002", "tooling", "Different finding"),
            ],
            evidence_refs=[
                make_evidence_ref("e-001x", "src/a.py"),   # duplicate by (kind, path, range, url)
                make_evidence_ref("e-002", "src/b.py"),    # new
            ],
        )
        merged = _merge_gen_records(existing, new_record)

        assert len(merged.helped) == 2  # h-001 + h-002 (h-001x deduped)
        assert len(merged.evidence_refs) == 2  # e-001 + e-002 (e-001x deduped)
        assert merged.findings_status == "has_findings"
