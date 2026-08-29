"""Acceptance contract for the opt-in GLM 5.3 advertised-cost gate."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess
from typing import cast

import pytest
import typer
from typer.testing import CliRunner
import yaml
from jsonschema import validate

from mission_runtime import CommitTarget
from kernel.clock import UTC, datetime
from specify_cli.cli.commands.spec_review import spec_review
from specify_cli.spec_review import models
from specify_cli.spec_review.models import (
    DisclosureComponent,
    DisclosureManifest,
    PaidPricingDisclosure,
    ReviewResponse,
    ReviewStatus,
    SpecReviewRun,
)
from specify_cli.spec_review.preflight import ReviewPromptTemplate, ReviewResponseSchema, ReviewRubric
from specify_cli.spec_review.runner import (
    PAID_PRICING_DRIFT,
    OpenCodeLoopbackRunner,
    OpenCodePricingProbe,
    PaidPricingError,
    PricingPermit,
)
from specify_cli.spec_review.service import SpecReviewService
from specify_cli.spec_review.storage import StoredSpecReview
from specify_cli.spec_review.storage import _serialize_run


pytestmark = [pytest.mark.unit, pytest.mark.fast]
PAID_ROUTE = "openrouter/z-ai/glm-5.3"


def _completed(payload: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(["opencode"], 0, stdout=payload, stderr=b"")


def _paid_model(*, output_price: str = "4", include_context: bool = True) -> bytes:
    limit = '"limit":{"context":1000000,"output":100000}' if include_context else '"limit":{"output":100000}'
    return (
        "openrouter/z-ai/glm-5.3\n"
        '{"id":"z-ai/glm-5.3","providerID":"openrouter",'
        f'"cost":{{"input":1.2,"output":{output_price},"cache":{{"read":0.12}}}},{limit}}}\n'
    ).encode()


def _paid_disclosure(*, threshold: str = "2") -> object:
    contract = getattr(models, "PaidPricingDisclosure", None)
    assert contract is not None, "paid pricing consent contract is not implemented"
    return contract.create(
        route=PAID_ROUTE,
        max_estimated_cost_usd=threshold,
        price_leaves=(("cache.read", "0.12"), ("input", "1.2"), ("output", "4")),
        context_limit=1_000_000,
        output_limit=100_000,
    )


def _free_manifest() -> DisclosureManifest:
    component = DisclosureComponent.from_bytes
    return DisclosureManifest.create(
        transport="opencode-loopback",
        requested_model_route="opencode/x-preview-f-free",
        spec_path="spec.md",
        spec=component("spec", b"# Synthetic\n"),
        rubric=component("rubric", b"{}"),
        response_schema=component("response_schema", b"{}"),
        prompt_template=component("prompt_template", b"{}"),
        rubric_version="v1",
    )


def test_paid_cli_requires_explicit_threshold_before_mission_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    app = typer.Typer()
    app.command()(spec_review)
    monkeypatch.setattr(
        "specify_cli.cli.commands.spec_review.find_repo_root",
        lambda: (_ for _ in ()).throw(AssertionError("mission resolution must not run")),
    )

    result = CliRunner().invoke(app, ["--mission", "demo", "--model", PAID_ROUTE, "--preview"])

    assert result.exit_code == 2
    assert "--max-estimated-cost-usd" in result.output


@pytest.mark.parametrize("value", ["NaN", "Infinity", "0", "-0.01", "5.000001"])
def test_paid_cli_rejects_unsafe_threshold_before_mission_resolution(
    value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = typer.Typer()
    app.command()(spec_review)
    monkeypatch.setattr(
        "specify_cli.cli.commands.spec_review.find_repo_root",
        lambda: (_ for _ in ()).throw(AssertionError("mission resolution must not run")),
    )

    result = CliRunner().invoke(
        app,
        ["--mission", "demo", "--model", PAID_ROUTE, "--max-estimated-cost-usd", value, "--preview"],
    )

    assert result.exit_code == 2
    assert "0 < значение <= 5" in result.output


def test_paid_disclosure_uses_full_context_and_output_and_binds_digest() -> None:
    paid = _paid_disclosure()

    assert paid.advertised_max_estimate_usd == "1.720000"
    assert len(paid.metadata_sha256) == 64
    free = _free_manifest()
    first = DisclosureManifest.create(
        transport=free.transport,
        requested_model_route=PAID_ROUTE,
        spec_path=free.spec_path,
        spec=free.spec,
        rubric=free.rubric,
        response_schema=free.response_schema,
        prompt_template=free.prompt_template,
        rubric_version=free.rubric_version,
        paid_pricing=paid,
    )
    second = replace(first, paid_pricing=_paid_disclosure(threshold="3"))

    assert first.has_valid_digest()
    assert second.has_valid_digest() is False
    assert first.manifest_sha256 != DisclosureManifest.create(
        transport=free.transport,
        requested_model_route=PAID_ROUTE,
        spec_path=free.spec_path,
        spec=free.spec,
        rubric=free.rubric,
        response_schema=free.response_schema,
        prompt_template=free.prompt_template,
        rubric_version=free.rubric_version,
        paid_pricing=_paid_disclosure(threshold="3"),
    ).manifest_sha256


def test_paid_probe_requires_complete_exact_metadata_and_computes_quote() -> None:
    probe = OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(_paid_model()))
    quote_paid = getattr(probe, "quote_paid", None)
    assert callable(quote_paid), "paid metadata quote probe is not implemented"

    quote = quote_paid(PAID_ROUTE, max_estimated_cost_usd="2")

    assert quote.advertised_max_estimate_usd == "1.720000"
    assert quote.context_limit == 1_000_000
    with pytest.raises(RuntimeError):
        OpenCodePricingProbe(
            run_process=lambda *args, **kwargs: _completed(_paid_model(include_context=False))
        ).quote_paid(PAID_ROUTE, max_estimated_cost_usd="2")


@pytest.mark.parametrize(
    "payload",
    [
        _paid_model().replace(b'"cache":{"read":0.12}}', b'"cache":{"read":0.12},"other":1}'),
        _paid_model().replace(b'"input":1.2', b'"input":-1.2'),
        _paid_model().replace(b'"output":100000', b'"other":100000'),
        _paid_model() + _paid_model(),
    ],
    ids=["unknown-price-leaf", "negative-price", "missing-output-limit", "duplicate-route"],
)
def test_paid_probe_refuses_ambiguous_or_incomplete_metadata(payload: bytes) -> None:
    probe = OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(payload))

    with pytest.raises(PaidPricingError):
        probe.quote_paid(PAID_ROUTE, max_estimated_cost_usd="2")


def test_paid_probe_refuses_estimate_above_local_threshold_and_other_paid_routes() -> None:
    probe = OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(_paid_model()))

    with pytest.raises(PaidPricingError):
        probe.quote_paid(PAID_ROUTE, max_estimated_cost_usd="1")
    with pytest.raises(PaidPricingError):
        probe.quote_paid("openrouter/other-paid-model", max_estimated_cost_usd="5")


def test_paid_execution_refuses_metadata_drift_before_session_creation() -> None:
    preview_probe = OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(_paid_model()))
    quote_paid = getattr(preview_probe, "quote_paid", None)
    assert callable(quote_paid), "paid metadata quote probe is not implemented"
    preview_quote = quote_paid(PAID_ROUTE, max_estimated_cost_usd="2")
    events: list[str] = []

    class SessionClient:
        def create_session(self) -> str:
            events.append("create")
            return "session"

        def send_review(self, session_id: str, *, route: str, prompt: bytes) -> bytes:
            events.append("send")
            return b"{}"

        def delete_session(self, session_id: str) -> bool:
            events.append("delete")
            return True

        def close(self) -> bool:
            events.append("close")
            return True

    runner = OpenCodeLoopbackRunner(
        OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(_paid_model(output_price="4.1"))),
        SessionClient(),
    )
    authorize_paid = getattr(runner, "authorize_paid", None)
    assert callable(authorize_paid), "paid runner authorization is not implemented"

    with pytest.raises(RuntimeError):
        authorize_paid(preview_quote)

    assert events == []


def test_paid_execution_refuses_prompt_larger_than_authorized_bound_before_session() -> None:
    probe = OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(_paid_model()))
    quote = probe.quote_paid(PAID_ROUTE, max_estimated_cost_usd="2")
    events: list[str] = []

    class SessionClient:
        def create_session(self) -> str:
            events.append("create")
            return "session"

        def send_review(self, session_id: str, *, route: str, prompt: bytes) -> bytes:
            events.append("send")
            return b"{}"

        def delete_session(self, session_id: str) -> bool:
            events.append("delete")
            return True

        def close(self) -> bool:
            events.append("close")
            return True

    runner = OpenCodeLoopbackRunner(probe, SessionClient())
    permit = runner.authorize_paid(quote, max_prompt_bytes=3)

    with pytest.raises(PaidPricingError):
        runner.run(permit=permit, prompt=b"four", validate_response=lambda payload: payload)

    assert events == []


def test_free_manifest_and_yaml_remain_byte_compatible() -> None:
    assert _free_manifest().manifest_sha256 == "ccc1dddc0dfecce2d5b2102ba01480139a1edf65aa28344dae185c4d3e42804a"
    run = SpecReviewRun(
        run_id="run-golden",
        mission="demo",
        spec_sha256="a" * 64,
        transport="opencode-loopback",
        requested_model_route="opencode/x-preview-f-free",
        actual_model="unverified",
        rubric_version="v1",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, tzinfo=UTC),
        status=ReviewStatus.COMPLETED,
        diagnostic_code=None,
        findings=(),
    )
    expected = """schema: spec-review-run/v1
run_id: run-golden
mission: demo
spec_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
transport: opencode-loopback
requested_model_route: opencode/x-preview-f-free
actual_model: unverified
rubric_version: v1
started_at: '2026-01-01T00:00:00+00:00'
completed_at: '2026-01-01T00:00:00+00:00'
status: completed
diagnostic_code: null
findings: []
summary:
  total: 0
  severity_1: 0
  severity_2: 0
  severity_3: 0
  severity_4: 0
  severity_5: 0
"""

    assert _serialize_run(run) == expected
    assert "paid_pricing" not in expected


def test_paid_service_authorizes_before_prompt_and_persists_v2_provenance(tmp_path: Path) -> None:
    mission = tmp_path / "kitty-specs" / "demo"
    mission.mkdir(parents=True)
    (mission / "spec.md").write_text("# Synthetic\nOnly public data.\n", encoding="utf-8")
    paid = cast(PaidPricingDisclosure, _paid_disclosure())
    events: list[str] = []
    stored_runs: list[SpecReviewRun] = []

    class Runner:
        def authorize(self, route: str) -> PricingPermit:
            raise AssertionError("free authorization must not run")

        def authorize_paid(
            self,
            expected: PaidPricingDisclosure,
            *,
            max_prompt_bytes: int,
        ) -> PricingPermit:
            events.append("authorize_paid")
            assert expected == paid
            assert max_prompt_bytes > 0
            return PricingPermit(expected.route, self, expected, max_prompt_bytes)

        def run(self, **kwargs: object) -> ReviewResponse:
            events.append("run")
            return ReviewResponse.create(())

    def store(**kwargs: object) -> StoredSpecReview:
        stored_runs.append(cast(SpecReviewRun, kwargs["run"]))
        return StoredSpecReview(tmp_path / "paid.yaml", "run-paid", CommitTarget("codex/demo"))

    service = SpecReviewService(
        repo_root=tmp_path,
        mission_slug="demo",
        rubric=ReviewRubric(version="v1", serialized=b"rubric", scanner_version="v1"),
        response_schema=ReviewResponseSchema(version="v1", serialized=b"schema"),
        prompt_template=ReviewPromptTemplate(version="v1", serialized=b"template"),
        runner=Runner(),
        model_route=PAID_ROUTE,
        paid_pricing=paid,
        store=store,
    )

    outcome = service.execute(confirm_digest=service.prepare().manifest_sha256, preview=False)

    assert outcome.exit_code == 0
    assert events == ["authorize_paid", "run"]
    assert stored_runs[0].schema == "spec-review-run/v2"
    document = yaml.safe_load(_serialize_run(stored_runs[0]))
    assert document["paid_pricing"] == paid.consent_document()
    schema_path = Path(__file__).resolve().parents[3] / "src/specify_cli/spec_review/assets/spec-review-run-v2.schema.yaml"
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    validate(document, schema)
    assert schema["properties"]["schema"]["const"] == "spec-review-run/v2"
    assert "paid_pricing" in schema["required"]


def test_paid_service_reports_quote_drift_before_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mission = tmp_path / "kitty-specs" / "demo"
    mission.mkdir(parents=True)
    (mission / "spec.md").write_text("# Synthetic\nOnly public data.\n", encoding="utf-8")
    paid = cast(PaidPricingDisclosure, _paid_disclosure())

    class Runner:
        def authorize(self, route: str) -> PricingPermit:
            raise AssertionError("free authorization must not run")

        def authorize_paid(
            self,
            expected: PaidPricingDisclosure,
            *,
            max_prompt_bytes: int,
        ) -> PricingPermit:
            raise PaidPricingError(expected.route, PAID_PRICING_DRIFT)

        def run(self, **kwargs: object) -> ReviewResponse:
            raise AssertionError("run must not start")

    monkeypatch.setattr(
        "specify_cli.spec_review.service.build_prompt",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("prompt must not be built")),
    )
    service = SpecReviewService(
        repo_root=tmp_path,
        mission_slug="demo",
        rubric=ReviewRubric(version="v1", serialized=b"rubric", scanner_version="v1"),
        response_schema=ReviewResponseSchema(version="v1", serialized=b"schema"),
        prompt_template=ReviewPromptTemplate(version="v1", serialized=b"template"),
        runner=Runner(),
        model_route=PAID_ROUTE,
        paid_pricing=paid,
    )

    outcome = service.execute(confirm_digest=service.prepare().manifest_sha256, preview=False)

    assert outcome.exit_code == 4
    assert outcome.diagnostic_code == PAID_PRICING_DRIFT
