"""Service ordering contracts: price gate precedes prompt creation and model run."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from mission_runtime import CommitTarget
from specify_cli.spec_review.models import (
    DiagnosticCode,
    LineEvidence,
    ReviewResponse,
    ReviewStatus,
    SpecReviewFinding,
    SpecReviewRun,
)
from specify_cli.spec_review.preflight import ReviewPromptTemplate, ReviewResponseSchema, ReviewRubric
from specify_cli.spec_review.runner import (
    AuthRequiredError,
    InvalidProviderResponseError,
    LoopbackTimeoutError,
    LoopbackTransportError,
    ModelNotFreeError,
    PricingPermit,
)
from specify_cli.spec_review.service import SpecReviewService
from specify_cli.spec_review.storage import SpecReviewWriteError, StoredSpecReview


pytestmark = [pytest.mark.unit, pytest.mark.fast]


class _PaidRunner:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def authorize(self, route: str) -> PricingPermit:
        self.calls.append("authorize")
        raise ModelNotFreeError(route)

    def run(self, **kwargs: object) -> object:
        self.calls.append("run")
        raise AssertionError("paid route must not reach runner")


def test_paid_route_stops_before_prompt_or_runner(tmp_path: Path) -> None:
    mission = tmp_path / "kitty-specs" / "demo"
    mission.mkdir(parents=True)
    (mission / "spec.md").write_text("# Synthetic\nOnly anonymous content.\n", encoding="utf-8")
    runner = _PaidRunner()
    service = SpecReviewService(
        repo_root=tmp_path,
        mission_slug="demo",
        rubric=ReviewRubric(version="v1", serialized=b"rubric", scanner_version="v1"),
        response_schema=ReviewResponseSchema(version="v1", serialized=b"schema"),
        prompt_template=ReviewPromptTemplate(version="v1", serialized=b"template"),
        runner=runner,
    )
    digest = service.prepare().manifest_sha256

    outcome = service.execute(confirm_digest=digest, preview=False)

    assert outcome.exit_code == 4
    assert outcome.diagnostic_code == "SPEC_REVIEW_MODEL_NOT_FREE"
    assert runner.calls == ["authorize"]


def test_mismatched_consent_digest_stops_before_pricing_or_runner(tmp_path: Path) -> None:
    runner = _PaidRunner()
    service = _service(tmp_path, runner, lambda **kwargs: (_ for _ in ()).throw(AssertionError()))

    outcome = service.execute(confirm_digest="not-the-current-manifest", preview=False)

    assert outcome.exit_code == 2
    assert outcome.diagnostic_code == "SPEC_REVIEW_CONSENT_REQUIRED"
    assert runner.calls == []


class _FailingRunner:
    def __init__(self, error: RuntimeError) -> None:
        self.error = error
        self.calls: list[str] = []

    def authorize(self, route: str) -> PricingPermit:
        self.calls.append("authorize")
        return PricingPermit(route, object())

    def run(self, **kwargs: object) -> ReviewResponse:
        self.calls.append("run")
        raise self.error


def _service(tmp_path: Path, runner: object, store: object) -> SpecReviewService:
    mission = tmp_path / "kitty-specs" / "demo"
    mission.mkdir(parents=True)
    (mission / "spec.md").write_text("# Synthetic\nOnly anonymous content.\n", encoding="utf-8")
    return SpecReviewService(
        repo_root=tmp_path,
        mission_slug="demo",
        rubric=ReviewRubric(version="v1", serialized=b"rubric", scanner_version="v1"),
        response_schema=ReviewResponseSchema(version="v1", serialized=b"schema"),
        prompt_template=ReviewPromptTemplate(version="v1", serialized=b"template"),
        runner=runner,  # type: ignore[arg-type]
        store=store,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code", "expected_exit"),
    [
        (AuthRequiredError(), ReviewStatus.PROVIDER_ERROR, DiagnosticCode.AUTH_REQUIRED, 4),
        (LoopbackTransportError(), ReviewStatus.PROVIDER_ERROR, DiagnosticCode.PROVIDER_ERROR, 4),
        (LoopbackTimeoutError(), ReviewStatus.TIMEOUT, DiagnosticCode.TIMEOUT, 5),
        (InvalidProviderResponseError(), ReviewStatus.INVALID_OUTPUT, DiagnosticCode.INVALID_OUTPUT, 6),
    ],
)
def test_runner_failures_are_persisted_without_raw_output(
    tmp_path: Path,
    error: RuntimeError,
    expected_status: ReviewStatus,
    expected_code: DiagnosticCode,
    expected_exit: int,
) -> None:
    stored_runs: list[SpecReviewRun] = []

    def store(**kwargs: object) -> StoredSpecReview:
        stored_runs.append(cast(SpecReviewRun, kwargs["run"]))
        return StoredSpecReview(path=tmp_path / "review.yaml", run_id="run-test", commit_target=CommitTarget("codex/demo"))

    runner = _FailingRunner(error)
    service = _service(tmp_path, runner, store)
    outcome = service.execute(confirm_digest=service.prepare().manifest_sha256, preview=False)

    assert outcome.exit_code == expected_exit
    assert outcome.diagnostic_code == expected_code.value
    assert runner.calls == ["authorize", "run"]
    assert len(stored_runs) == 1
    run = stored_runs[0]
    assert run.status is expected_status
    assert run.diagnostic_code is expected_code


def test_write_failure_does_not_repeat_the_runner(tmp_path: Path) -> None:
    class CompleteRunner:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def authorize(self, route: str) -> PricingPermit:
            self.calls.append("authorize")
            return PricingPermit(route, object())

        def run(self, **kwargs: object) -> ReviewResponse:
            self.calls.append("run")
            return ReviewResponse.create(())

    runner = CompleteRunner()

    def fail_store(**kwargs: object) -> StoredSpecReview:
        raise SpecReviewWriteError("SPEC_REVIEW_WRITE_FAILED", tmp_path / "review.yaml")

    service = _service(tmp_path, runner, fail_store)
    outcome = service.execute(confirm_digest=service.prepare().manifest_sha256, preview=False)

    assert outcome.exit_code == 7
    assert outcome.diagnostic_code == DiagnosticCode.WRITE_FAILED.value
    assert runner.calls == ["authorize", "run"]


def test_completed_review_returns_host_computed_summary(tmp_path: Path) -> None:
    class CompleteRunner:
        def authorize(self, route: str) -> PricingPermit:
            return PricingPermit(route, object())

        def run(self, **kwargs: object) -> ReviewResponse:
            return ReviewResponse.create(
                (
                    SpecReviewFinding(
                        identifier="finding-1",
                        lens="clarity",
                        severity=3,
                        title="Ambiguous criterion",
                        evidence=LineEvidence(1, 1),
                        claim="A criterion is ambiguous.",
                        remediation="State the measurable threshold.",
                    ),
                )
            )

    def store(**kwargs: object) -> StoredSpecReview:
        return StoredSpecReview(path=tmp_path / "review.yaml", run_id="run-test", commit_target=CommitTarget("codex/demo"))

    service = _service(tmp_path, CompleteRunner(), store)
    outcome = service.execute(confirm_digest=service.prepare().manifest_sha256, preview=False)

    assert outcome.exit_code == 0
    assert outcome.summary is not None
    assert outcome.summary.total == 1
    assert outcome.summary.severity_3 == 1
