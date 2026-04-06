"""Tests for acceptance matrix, evidence validation, and negative invariants."""

from specify_cli.acceptance_matrix import (
    AcceptanceCriterion,
    AcceptanceMatrix,
    NegativeInvariant,
    enforce_negative_invariants,
    read_acceptance_matrix,
    validate_manual_evidence,
    validate_matrix_evidence,
    write_acceptance_matrix,
)


class TestAcceptanceCriterion:
    def test_default_pending(self):
        c = AcceptanceCriterion(criterion_id="AC-01", description="Test", proof_type="automated_test")
        assert c.pass_fail == "pending"


class TestAcceptanceMatrix:
    def test_verdict_all_pass(self):
        m = AcceptanceMatrix(
            feature_slug="test",
            criteria=[
                AcceptanceCriterion("AC-01", "Test", "automated_test", pass_fail="pass"),
            ],
        )
        assert m.overall_verdict == "pass"

    def test_verdict_any_fail(self):
        m = AcceptanceMatrix(
            feature_slug="test",
            criteria=[
                AcceptanceCriterion("AC-01", "Test", "automated_test", pass_fail="pass"),
                AcceptanceCriterion("AC-02", "Test", "manual_qa", pass_fail="fail"),
            ],
        )
        assert m.overall_verdict == "fail"

    def test_verdict_pending(self):
        m = AcceptanceMatrix(
            feature_slug="test",
            criteria=[
                AcceptanceCriterion("AC-01", "Test", "automated_test", pass_fail="pass"),
                AcceptanceCriterion("AC-02", "Test", "manual_qa", pass_fail="pending"),
            ],
        )
        assert m.overall_verdict == "pending"

    def test_verdict_invariant_still_present(self):
        m = AcceptanceMatrix(
            feature_slug="test",
            criteria=[
                AcceptanceCriterion("AC-01", "Test", "automated_test", pass_fail="pass"),
            ],
            negative_invariants=[
                NegativeInvariant("NI-01", "Old route gone", "grep_absence", result="still_present"),
            ],
        )
        assert m.overall_verdict == "fail"

    def test_empty_matrix_pending(self):
        m = AcceptanceMatrix(feature_slug="test")
        assert m.overall_verdict == "pending"


class TestPersistence:
    def test_round_trip(self, tmp_path):
        matrix = AcceptanceMatrix(
            feature_slug="010-feat",
            criteria=[
                AcceptanceCriterion("AC-01", "Test passes", "automated_test", pass_fail="pass"),
            ],
            negative_invariants=[
                NegativeInvariant("NI-01", "No legacy route", "grep_absence",
                                  verification_command="/old-route", result="confirmed_absent"),
            ],
        )
        write_acceptance_matrix(tmp_path, matrix)
        restored = read_acceptance_matrix(tmp_path)
        assert restored is not None
        assert restored.feature_slug == "010-feat"
        assert len(restored.criteria) == 1
        assert len(restored.negative_invariants) == 1
        assert restored.overall_verdict == "pass"

    def test_missing_returns_none(self, tmp_path):
        assert read_acceptance_matrix(tmp_path) is None


class TestManualEvidence:
    def test_valid_manual_qa(self):
        c = AcceptanceCriterion(
            "AC-01", "Check dashboard", "manual_qa",
            evidence="http://localhost:8000/dashboard",
            verified_at="2026-04-03T12:00:00Z",
            verified_by="qa-operator",
            pass_fail="pass",
        )
        assert validate_manual_evidence(c) == []

    def test_missing_evidence(self):
        c = AcceptanceCriterion("AC-01", "Check dashboard", "manual_qa")
        errors = validate_manual_evidence(c)
        assert len(errors) == 3
        assert any("evidence" in e for e in errors)
        assert any("verified_at" in e for e in errors)
        assert any("verified_by" in e for e in errors)

    def test_non_manual_qa_ignored(self):
        c = AcceptanceCriterion("AC-01", "Test", "automated_test")
        assert validate_manual_evidence(c) == []

    def test_matrix_level_validation(self):
        m = AcceptanceMatrix(
            feature_slug="test",
            criteria=[
                AcceptanceCriterion("AC-01", "Auto", "automated_test"),
                AcceptanceCriterion("AC-02", "Manual", "manual_qa"),  # Missing evidence
            ],
        )
        errors = validate_matrix_evidence(m)
        assert len(errors) == 3  # evidence, verified_at, verified_by


class TestNegativeInvariants:
    def test_grep_absence_confirmed(self, tmp_path):
        # Create a repo dir with a file that does NOT contain the pattern
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("def main(): pass\n")

        invariants = [
            NegativeInvariant(
                "NI-01", "No legacy route",
                "grep_absence",
                verification_command="old_legacy_route",
            ),
        ]
        results = enforce_negative_invariants(tmp_path, invariants)
        assert results[0].result == "confirmed_absent"

    def test_grep_absence_still_present(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("old_legacy_route = '/old'\n")

        invariants = [
            NegativeInvariant(
                "NI-01", "No legacy route",
                "grep_absence",
                verification_command="old_legacy_route",
            ),
        ]
        results = enforce_negative_invariants(tmp_path, invariants)
        assert results[0].result == "still_present"

    def test_custom_command_pass(self, tmp_path):
        invariants = [
            NegativeInvariant(
                "NI-01", "No stale files",
                "custom_command",
                verification_command="true",  # always exits 0
            ),
        ]
        results = enforce_negative_invariants(tmp_path, invariants)
        assert results[0].result == "confirmed_absent"

    def test_custom_command_fail(self, tmp_path):
        invariants = [
            NegativeInvariant(
                "NI-01", "Check fails",
                "custom_command",
                verification_command="false",  # always exits 1
            ),
        ]
        results = enforce_negative_invariants(tmp_path, invariants)
        assert results[0].result == "still_present"
