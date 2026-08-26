"""Consent-bound orchestration for one advisory specification review."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from kernel.clock import datetime, now_utc
from specify_cli.missions._read_path_resolver import candidate_feature_dir_for_mission

from .models import DiagnosticCode, DisclosureManifest, ReviewResponse, ReviewStatus, ReviewSummary, SpecReviewRun
from .parser import InvalidReviewResponse, parse_review_response_bytes
from .preflight import (
    MissionSpecContext,
    PreflightDisclosure,
    PreflightRefusal,
    ReviewPromptTemplate,
    ReviewResponseSchema,
    ReviewRubric,
    SCANNER_VERSION,
    build_disclosure,
    confirm_and_load_spec,
)
from .prompt import build_prompt
from .runner import (
    MODEL_NOT_FREE,
    AuthRequiredError,
    InvalidProviderResponseError,
    LoopbackTimeoutError,
    LoopbackTransportError,
    ModelNotFreeError,
    PricingPermit,
    SessionCleanupError,
)
from .storage import SpecReviewWriteError, StoredSpecReview, new_spec_review_run_id, store_spec_review


DEFAULT_MODEL_ROUTE = "opencode/x-preview-f-free"
LOOPBACK_TRANSPORT = "opencode-loopback"
_ASSETS_DIR = Path(__file__).with_name("assets")


class ReviewRunner(Protocol):
    """Runner ordering surface: authorization is intentionally separate from prompt use."""

    def authorize(self, route: str) -> PricingPermit: ...

    def run(
        self,
        *,
        permit: PricingPermit,
        prompt: bytes,
        validate_response: Callable[[bytes], ReviewResponse],
    ) -> ReviewResponse: ...


@dataclass(frozen=True)
class SpecReviewOutcome:
    """Safe operator result; it never holds prompt, spec, or provider response bytes."""

    exit_code: int
    diagnostic_code: str | None
    manifest: DisclosureManifest
    status: ReviewStatus | None = None
    summary: ReviewSummary | None = None
    artifact: StoredSpecReview | None = None


def load_default_review_materials() -> tuple[ReviewRubric, ReviewResponseSchema, ReviewPromptTemplate]:
    """Load the versioned, package-owned bytes that a future review may disclose."""
    return (
        ReviewRubric(
            version="reviewer-renata/v1",
            serialized=(_ASSETS_DIR / "reviewer-rubric-v1.yaml").read_bytes(),
            scanner_version=SCANNER_VERSION,
        ),
        ReviewResponseSchema(
            version="review-response/v1",
            serialized=(_ASSETS_DIR / "review-response-v1.schema.yaml").read_bytes(),
        ),
        ReviewPromptTemplate(
            version="spec-review-prompt/v1",
            serialized=(_ASSETS_DIR / "spec-review-prompt-v1.yaml").read_bytes(),
        ),
    )


def prepare_default_disclosure(
    *,
    repo_root: Path,
    mission_slug: str,
    model_route: str = DEFAULT_MODEL_ROUTE,
) -> DisclosureManifest:
    """Create a metadata-only preview without pricing, prompt construction, or model use."""
    rubric, response_schema, prompt_template = load_default_review_materials()
    context = _mission_spec_context(repo_root, mission_slug)
    manifest: DisclosureManifest = build_disclosure(
        context=context,
        transport=LOOPBACK_TRANSPORT,
        requested_model_route=model_route,
        rubric=rubric,
        response_schema=response_schema,
        prompt_template=prompt_template,
    ).manifest
    return manifest


class SpecReviewService:
    """Coordinates local validation and a single explicitly authorized runner call."""

    def __init__(
        self,
        *,
        repo_root: Path,
        mission_slug: str,
        rubric: ReviewRubric,
        response_schema: ReviewResponseSchema,
        prompt_template: ReviewPromptTemplate,
        runner: ReviewRunner,
        model_route: str = DEFAULT_MODEL_ROUTE,
        store: Callable[..., StoredSpecReview] = store_spec_review,
    ) -> None:
        self._repo_root = repo_root
        self._mission_slug = mission_slug
        self._rubric = rubric
        self._response_schema = response_schema
        self._prompt_template = prompt_template
        self._runner = runner
        self._model_route = model_route
        self._store = store

    def prepare(self) -> DisclosureManifest:
        """Build metadata-only disclosure without consent or an external call."""
        manifest: DisclosureManifest = self._disclosure().manifest
        return manifest

    def execute(self, *, confirm_digest: str | None, preview: bool) -> SpecReviewOutcome:
        """Gate price before prompt construction, then make at most one model call."""
        disclosure = self._disclosure()
        if preview:
            return SpecReviewOutcome(exit_code=0, diagnostic_code=None, manifest=disclosure.manifest, status=ReviewStatus.REFUSED)
        if confirm_digest != disclosure.manifest.manifest_sha256:
            return SpecReviewOutcome(exit_code=2, diagnostic_code="SPEC_REVIEW_CONSENT_REQUIRED", manifest=disclosure.manifest, status=ReviewStatus.REFUSED)
        assert confirm_digest is not None
        try:
            permit = self._runner.authorize(self._model_route)
        except ModelNotFreeError:
            return SpecReviewOutcome(exit_code=4, diagnostic_code=MODEL_NOT_FREE, manifest=disclosure.manifest, status=ReviewStatus.REFUSED)
        try:
            snapshot = confirm_and_load_spec(disclosure, confirm_digest)
        except PreflightRefusal:
            return SpecReviewOutcome(exit_code=3, diagnostic_code="SPEC_REVIEW_INPUT_REFUSED", manifest=disclosure.manifest, status=ReviewStatus.REFUSED)
        prompt = build_prompt(
            snapshot=snapshot,
            rubric=disclosure.rubric,
            response_schema=disclosure.response_schema,
            prompt_template=disclosure.prompt_template,
        )
        started_at = now_utc()
        try:
            response = self._runner.run(
                permit=permit,
                prompt=prompt,
                validate_response=lambda payload: parse_review_response_bytes(
                    payload,
                    line_count=snapshot.line_count,
                    source_text=snapshot.text,
                ),
            )
        except AuthRequiredError:
            return self._store_failure(disclosure.manifest, started_at, ReviewStatus.PROVIDER_ERROR, DiagnosticCode.AUTH_REQUIRED, 4)
        except LoopbackTimeoutError:
            return self._store_failure(disclosure.manifest, started_at, ReviewStatus.TIMEOUT, DiagnosticCode.TIMEOUT, 5)
        except (InvalidProviderResponseError, InvalidReviewResponse):
            return self._store_failure(disclosure.manifest, started_at, ReviewStatus.INVALID_OUTPUT, DiagnosticCode.INVALID_OUTPUT, 6)
        except SessionCleanupError:
            return self._store_failure(
                disclosure.manifest,
                started_at,
                ReviewStatus.PROVIDER_ERROR,
                DiagnosticCode.SESSION_CLEANUP_FAILED,
                4,
            )
        except LoopbackTransportError:
            return self._store_failure(disclosure.manifest, started_at, ReviewStatus.PROVIDER_ERROR, DiagnosticCode.PROVIDER_ERROR, 4)
        now = now_utc()
        run = SpecReviewRun.from_response(
            run_id=new_spec_review_run_id(now),
            mission=self._mission_slug,
            manifest=disclosure.manifest,
            started_at=now,
            completed_at=now,
            response=response,
        )
        try:
            artifact = self._store(repo_root=self._repo_root, mission_slug=self._mission_slug, run=run)
        except (OSError, SpecReviewWriteError):
            return SpecReviewOutcome(
                exit_code=7,
                diagnostic_code=DiagnosticCode.WRITE_FAILED.value,
                manifest=disclosure.manifest,
                status=ReviewStatus.WRITE_FAILED,
            )
        return SpecReviewOutcome(
            exit_code=0,
            diagnostic_code=None,
            manifest=disclosure.manifest,
            status=ReviewStatus.COMPLETED,
            summary=run.summary,
            artifact=artifact,
        )

    def _store_failure(
        self,
        manifest: DisclosureManifest,
        started_at: datetime,
        status: ReviewStatus,
        diagnostic_code: DiagnosticCode,
        exit_code: int,
    ) -> SpecReviewOutcome:
        """Persist the metadata-only result of a runner failure without a retry."""
        completed_at = now_utc()
        run = SpecReviewRun.from_failure(
            run_id=new_spec_review_run_id(completed_at),
            mission=self._mission_slug,
            manifest=manifest,
            started_at=started_at,
            completed_at=completed_at,
            status=status,
            diagnostic_code=diagnostic_code,
        )
        try:
            artifact = self._store(repo_root=self._repo_root, mission_slug=self._mission_slug, run=run)
        except (OSError, SpecReviewWriteError):
            return SpecReviewOutcome(
                exit_code=7,
                diagnostic_code=DiagnosticCode.WRITE_FAILED.value,
                manifest=manifest,
                status=ReviewStatus.WRITE_FAILED,
            )
        return SpecReviewOutcome(
            exit_code=exit_code,
            diagnostic_code=diagnostic_code.value,
            manifest=manifest,
            status=status,
            artifact=artifact,
        )

    def _disclosure(self) -> PreflightDisclosure:
        context = _mission_spec_context(self._repo_root, self._mission_slug)
        return build_disclosure(
            context=context,
            transport=LOOPBACK_TRANSPORT,
            requested_model_route=self._model_route,
            rubric=self._rubric,
            response_schema=self._response_schema,
            prompt_template=self._prompt_template,
        )


def _mission_spec_context(repo_root: Path, mission_slug: str) -> MissionSpecContext:
    """Resolve the spec input through the canonical topology-aware read path."""
    return MissionSpecContext.create(
        repo_root=repo_root,
        mission_dir=candidate_feature_dir_for_mission(repo_root, mission_slug),
    )
