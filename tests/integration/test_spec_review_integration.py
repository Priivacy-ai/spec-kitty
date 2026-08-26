"""Offline end-to-end coverage for the advisory specification-review flow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from kernel.clock import UTC, datetime
from hashlib import sha256  # noqa: TID251 - exact spec-byte integrity, not charter freshness
from pathlib import Path
import subprocess
from time import perf_counter
from typing import cast

import pytest
import typer
from typer.testing import CliRunner
import yaml

from mission_runtime import CommitTarget, TopologySurface
from mission_runtime import ResolvedSurface
from specify_cli.context.mission_resolver import ResolvedMission
from specify_cli.spec_review import runner as runner_module
from specify_cli.spec_review import storage as storage_module
from specify_cli.spec_review.models import (
    DiagnosticCode,
    DisclosureComponent,
    DisclosureManifest,
    LineEvidence,
    ReviewResponse,
    ReviewStatus,
    ReviewSummary,
    SpecReviewFinding,
    SpecReviewRun,
)
from specify_cli.spec_review.preflight import (
    MAX_SPEC_BYTES,
    MissionSpecContext,
    PreflightRefusal,
    ReviewPromptTemplate,
    ReviewResponseSchema,
    ReviewRubric,
)
from specify_cli.spec_review.runner import (
    HttpResponse,
    InvalidProviderResponseError,
    LOOPBACK_RESPONSE_LIMIT,
    LoopbackTimeoutError,
    LoopbackTransportError,
    ModelNotFreeError,
    OpenCodeHeadlessServer,
    OpenCodeLoopbackClient,
    OpenCodeLoopbackRunner,
    OpenCodePricingProbe,
    PricingPermit,
    SessionCleanupError,
)
from specify_cli.spec_review.service import SpecReviewOutcome, SpecReviewService, load_default_review_materials
from specify_cli.spec_review.storage import SpecReviewWriteError, StoredSpecReview, store_spec_review


_MISSION = "synthetic-spec-review"
_SPEC = """# Synthetic label sorter

## Goal
Return user-supplied labels in alphabetical order.

## Requirement
The output must preserve duplicate labels.
"""


class _FakeRunner:
    def __init__(self, *, pricing_state: str = "free", error: RuntimeError | None = None) -> None:
        self.pricing_state = pricing_state
        self.error = error
        self.events: list[str] = []
        self.prompts: list[bytes] = []

    def authorize(self, route: str) -> PricingPermit:
        self.events.append(f"authorize:{self.pricing_state}")
        if self.pricing_state != "free":
            raise ModelNotFreeError(route)
        return PricingPermit(route=route, _issuer=self)

    def run(
        self,
        *,
        permit: PricingPermit,
        prompt: bytes,
        validate_response: Callable[[bytes], ReviewResponse],
    ) -> ReviewResponse:
        self.events.append("run")
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return validate_response(
            b'{"schema":"review-response/v1","findings":[{"id":"F-1",'
            b'"lens":"completeness","severity":3,"title":"Define ordering",'
            b'"evidence":{"line_start":3,"line_end":4},'
            b'"claim":"The ordering rule needs a locale boundary.",'
            b'"remediation":"State the comparison and locale rules."}]}'
        )


def _mission(tmp_path: Path) -> tuple[Path, Path]:
    mission = tmp_path / "kitty-specs" / _MISSION
    mission.mkdir(parents=True)
    spec = mission / "spec.md"
    spec.write_text(_SPEC, encoding="utf-8", newline="\n")
    return mission, spec


def _route_storage(monkeypatch: pytest.MonkeyPatch, mission: Path) -> None:
    monkeypatch.setattr(
        "specify_cli.spec_review.storage.resolve_artifact_surface",
        lambda repo, slug, kind: ResolvedSurface(mission, TopologySurface.PRIMARY),
    )
    monkeypatch.setattr(
        "specify_cli.spec_review.storage.placement_seam",
        lambda repo, slug: type(
            "Seam",
            (),
            {"write_target": lambda self, kind: CommitTarget("codex/synthetic-spec-review")},
        )(),
    )


def _service(
    tmp_path: Path,
    runner: _FakeRunner,
    *,
    store: Callable[..., StoredSpecReview] | None = None,
) -> SpecReviewService:
    rubric, response_schema, prompt_template = load_default_review_materials()
    return SpecReviewService(
        repo_root=tmp_path,
        mission_slug=_MISSION,
        rubric=rubric,
        response_schema=response_schema,
        prompt_template=prompt_template,
        runner=runner,
        store=store or store_spec_review,
    )


def _completed_run() -> SpecReviewRun:
    return SpecReviewRun(
        run_id="run-coverage",
        mission=_MISSION,
        spec_sha256="a" * 64,
        transport="opencode-loopback",
        requested_model_route="opencode/synthetic",
        actual_model="unverified",
        rubric_version="v1",
        started_at=datetime(2026, 8, 24, tzinfo=UTC),
        completed_at=datetime(2026, 8, 24, tzinfo=UTC),
        status=ReviewStatus.COMPLETED,
        diagnostic_code=None,
        findings=(),
    )


@pytest.mark.integration
@pytest.mark.performance
def test_preflight_disclosure_stays_under_two_seconds_at_size_limit(tmp_path: Path) -> None:
    _, spec = _mission(tmp_path)
    prefix = b"# Synthetic performance fixture\n"
    spec.write_bytes(prefix + (b"x" * (MAX_SPEC_BYTES - len(prefix))))
    service = _service(tmp_path, _FakeRunner())

    started = perf_counter()
    disclosure = service.prepare()
    elapsed = perf_counter() - started

    assert disclosure.spec.size_bytes == MAX_SPEC_BYTES
    assert elapsed < 2.0


@pytest.mark.integration
def test_preview_then_two_separately_confirmed_runs_persist_distinct_host_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, spec = _mission(tmp_path)
    _route_storage(monkeypatch, mission)
    before = spec.read_bytes()
    runner = _FakeRunner()
    service = _service(tmp_path, runner)

    preview = service.prepare()

    assert runner.events == []
    assert preview.spec.sha256 == sha256(before).hexdigest()
    assert preview.spec_path == "spec.md"
    outcomes = [
        service.execute(confirm_digest=service.prepare().manifest_sha256, preview=False),
        service.execute(confirm_digest=service.prepare().manifest_sha256, preview=False),
    ]

    assert [outcome.exit_code for outcome in outcomes] == [0, 0]
    assert [outcome.status for outcome in outcomes] == [ReviewStatus.COMPLETED, ReviewStatus.COMPLETED]
    assert runner.events == ["authorize:free", "run", "authorize:free", "run"]
    assert len(runner.prompts) == 2
    artifacts = [outcome.artifact for outcome in outcomes]
    assert all(artifact is not None for artifact in artifacts)
    paths = [cast(StoredSpecReview, artifact).path for artifact in artifacts]
    assert paths[0] != paths[1]

    documents = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in paths]
    assert all(document["schema"] == "spec-review-run/v1" for document in documents)
    assert all(document["spec_sha256"] == preview.spec.sha256 for document in documents)
    assert all(document["summary"] == {
        "total": 1,
        "severity_1": 0,
        "severity_2": 0,
        "severity_3": 1,
        "severity_4": 0,
        "severity_5": 0,
    } for document in documents)
    assert all(document["findings"][0]["evidence"] == {"line_start": 3, "line_end": 4} for document in documents)
    assert spec.read_bytes() == before
    assert sorted(path.name for path in mission.iterdir()) == ["reviews", "spec.md"]


@pytest.mark.integration
@pytest.mark.parametrize("pricing_state", ["paid", "unknown", "stale"])
def test_unverified_free_pricing_refuses_before_prompt_or_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pricing_state: str,
) -> None:
    _mission(tmp_path)
    runner = _FakeRunner(pricing_state=pricing_state)
    service = _service(tmp_path, runner)
    monkeypatch.setattr(
        "specify_cli.spec_review.service.build_prompt",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("prompt must not be composed")),
    )

    outcome = service.execute(confirm_digest=service.prepare().manifest_sha256, preview=False)

    assert outcome.exit_code == 4
    assert outcome.status is ReviewStatus.REFUSED
    assert outcome.diagnostic_code == "SPEC_REVIEW_MODEL_NOT_FREE"
    assert runner.events == [f"authorize:{pricing_state}"]
    assert runner.prompts == []


@pytest.mark.integration
@pytest.mark.parametrize(
    ("error", "status", "diagnostic", "exit_code"),
    [
        (LoopbackTransportError(), ReviewStatus.PROVIDER_ERROR, "SPEC_REVIEW_PROVIDER_ERROR", 4),
        (LoopbackTimeoutError(), ReviewStatus.TIMEOUT, "SPEC_REVIEW_TIMEOUT", 5),
        (InvalidProviderResponseError(), ReviewStatus.INVALID_OUTPUT, "SPEC_REVIEW_INVALID_OUTPUT", 6),
    ],
    ids=["provider-429-no-retry", "timeout", "invalid-output"],
)
def test_runner_failures_are_single_attempt_and_persist_metadata_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: RuntimeError,
    status: ReviewStatus,
    diagnostic: str,
    exit_code: int,
) -> None:
    mission, spec = _mission(tmp_path)
    _route_storage(monkeypatch, mission)
    before = spec.read_bytes()
    runner = _FakeRunner(error=error)
    service = _service(tmp_path, runner)

    outcome = service.execute(confirm_digest=service.prepare().manifest_sha256, preview=False)

    assert outcome.exit_code == exit_code
    assert outcome.status is status
    assert outcome.diagnostic_code == diagnostic
    assert runner.events == ["authorize:free", "run"]
    assert len(runner.prompts) == 1
    assert outcome.artifact is not None
    document = yaml.safe_load(outcome.artifact.path.read_text(encoding="utf-8"))
    assert document["status"] == status.value
    assert document["diagnostic_code"] == diagnostic
    assert document["findings"] == []
    assert spec.read_bytes() == before


@pytest.mark.integration
def test_write_failure_does_not_repeat_the_external_run(tmp_path: Path) -> None:
    _mission(tmp_path)
    runner = _FakeRunner()

    def fail_store(**kwargs: object) -> StoredSpecReview:
        raise SpecReviewWriteError("SPEC_REVIEW_WRITE_FAILED", tmp_path / "review.yaml")

    service = _service(tmp_path, runner, store=fail_store)

    outcome = service.execute(confirm_digest=service.prepare().manifest_sha256, preview=False)

    assert outcome.exit_code == 7
    assert outcome.status is ReviewStatus.WRITE_FAILED
    assert outcome.diagnostic_code == "SPEC_REVIEW_WRITE_FAILED"
    assert outcome.artifact is None
    assert runner.events == ["authorize:free", "run"]
    assert len(runner.prompts) == 1


@pytest.mark.integration
def test_service_preview_manifest_drift_and_failure_store_refusal(tmp_path: Path) -> None:
    _mission(tmp_path)
    runner = _FakeRunner()
    service = _service(tmp_path, runner)

    preview = service.execute(confirm_digest=None, preview=True)

    assert preview.exit_code == 0
    assert preview.status is ReviewStatus.REFUSED
    assert runner.events == []

    class DriftingRunner(_FakeRunner):
        def authorize(self, route: str) -> PricingPermit:
            permit = super().authorize(route)
            (tmp_path / "kitty-specs" / _MISSION / "spec.md").write_text("# changed\n", encoding="utf-8")
            return permit

    drifting = DriftingRunner()
    drift_service = _service(tmp_path, drifting)
    digest = drift_service.prepare().manifest_sha256
    drift = drift_service.execute(confirm_digest=digest, preview=False)

    assert drift.exit_code == 3
    assert drift.diagnostic_code == "SPEC_REVIEW_INPUT_REFUSED"
    assert drifting.events == ["authorize:free"]

    (tmp_path / "kitty-specs" / _MISSION / "spec.md").write_text(_SPEC, encoding="utf-8")
    cleanup_runner = _FakeRunner(error=SessionCleanupError())

    def fail_store(**kwargs: object) -> StoredSpecReview:
        raise OSError("synthetic write refusal")

    cleanup_service = _service(tmp_path, cleanup_runner, store=fail_store)
    failed = cleanup_service.execute(confirm_digest=cleanup_service.prepare().manifest_sha256, preview=False)

    assert failed.exit_code == 7
    assert failed.status is ReviewStatus.WRITE_FAILED
    assert cleanup_runner.events == ["authorize:free", "run"]


@pytest.mark.integration
@pytest.mark.parametrize(
    "factory",
    [
        lambda: DisclosureComponent("", 0, "a" * 64),
        lambda: DisclosureManifest.create(
            transport="",
            requested_model_route="route/model",
            spec_path="spec.md",
            spec=DisclosureComponent.from_bytes("spec", b"x"),
            rubric=DisclosureComponent.from_bytes("rubric", b"x"),
            response_schema=DisclosureComponent.from_bytes("schema", b"x"),
            prompt_template=DisclosureComponent.from_bytes("template", b"x"),
            rubric_version="v1",
        ),
        lambda: SpecReviewFinding("bad id", "lens", 3, "title", LineEvidence(1, 1), "claim", "fix"),
        lambda: SpecReviewFinding("F-1", "", 3, "title", LineEvidence(1, 1), "claim", "fix"),
        lambda: SpecReviewFinding("F-1", "lens", 3, "", LineEvidence(1, 1), "claim", "fix"),
        lambda: SpecReviewFinding("F-1", "lens", 3, "title", LineEvidence(1, 1), "", "fix"),
        lambda: ReviewResponse(schema="other/v1", findings=()),
        lambda: ReviewSummary(1, -1, 0, 0, 0, 0),
        lambda: ReviewSummary(2, 1, 0, 0, 0, 0),
        lambda: replace(_completed_run(), run_id="bad id"),
        lambda: replace(_completed_run(), summary=ReviewSummary(1, 1, 0, 0, 0, 0)),
        lambda: replace(_completed_run(), diagnostic_code=DiagnosticCode.PROVIDER_ERROR),
        lambda: replace(
            _completed_run(),
            status=ReviewStatus.TIMEOUT,
            diagnostic_code=None,
        ),
    ],
)
def test_host_models_fail_closed_on_invalid_contract_branches(factory: Callable[[], object]) -> None:
    with pytest.raises(ValueError):
        factory()


@pytest.mark.integration
def test_preflight_value_objects_and_outside_mission_fail_closed(tmp_path: Path) -> None:
    invalid_factories: tuple[Callable[[], object], ...] = (
        lambda: ReviewRubric(version="", serialized=b"rubric", scanner_version="v1"),
        lambda: ReviewResponseSchema(version="v1", serialized=b""),
        lambda: ReviewPromptTemplate(version="v1", serialized=b""),
    )
    for factory in invalid_factories:
        with pytest.raises(ValueError):
            factory()

    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    with pytest.raises(PreflightRefusal):
        MissionSpecContext.create(repo_root=repo, mission_dir=outside)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("operation", "response", "error_type"),
    [
        ("create", HttpResponse(200, b'{"id":""}'), LoopbackTransportError),
        ("create", HttpResponse(500, b"ignored"), LoopbackTransportError),
        ("create", HttpResponse(200, b"not-json"), InvalidProviderResponseError),
        ("create", HttpResponse(200, b"[]"), InvalidProviderResponseError),
        ("send", HttpResponse(200, b"{}"), InvalidProviderResponseError),
        ("send", HttpResponse(200, b'{"parts":[]}'), InvalidProviderResponseError),
        (
            "send",
            HttpResponse(200, b'{"parts":[{"type":"text","text":"a"},{"type":"text","text":"b"}]}'),
            InvalidProviderResponseError,
        ),
        ("create", HttpResponse(200, b"x" * (LOOPBACK_RESPONSE_LIMIT + 1)), InvalidProviderResponseError),
    ],
)
def test_loopback_client_rejects_malformed_session_and_message_envelopes(
    operation: str,
    response: HttpResponse,
    error_type: type[RuntimeError],
) -> None:
    client = OpenCodeLoopbackClient("http://127.0.0.1:4096", request=lambda *args: response)

    with pytest.raises(error_type):
        if operation == "create":
            client.create_session()
        else:
            client.send_review("session", route="provider/model", prompt=b"synthetic")


@pytest.mark.integration
def test_loopback_client_rejects_invalid_route_prompt_and_delete_failure() -> None:
    client = OpenCodeLoopbackClient(
        "http://127.0.0.1:4096",
        request=lambda *args: (_ for _ in ()).throw(LoopbackTransportError()),
    )

    with pytest.raises(LoopbackTransportError):
        client.send_review("session", route="invalid", prompt=b"synthetic")
    with pytest.raises(InvalidProviderResponseError):
        client.send_review("session", route="provider/model", prompt=b"\xff")
    assert client.delete_session("session") is False
    assert client.close() is True


@pytest.mark.integration
@pytest.mark.parametrize(
    ("route", "result"),
    [
        ("invalid", subprocess.CompletedProcess([], 0, b"", b"")),
        ("provider/model", OSError("missing")),
        ("provider/model", subprocess.CompletedProcess([], 1, b"", b"")),
        ("provider/model", subprocess.CompletedProcess([], 0, b"\xff", b"")),
        ("provider/model", subprocess.CompletedProcess([], 0, b"{bad}{\"id\":1}", b"")),
        (
            "provider/model",
            subprocess.CompletedProcess(
                [],
                0,
                b'{"id":"model","providerID":"provider","cost":{"input":true}}',
                b"",
            ),
        ),
        (
            "provider/model",
            subprocess.CompletedProcess(
                [],
                0,
                b'{"id":"model","providerID":"provider","cost":{"input":"free"}}',
                b"",
            ),
        ),
    ],
)
def test_pricing_probe_fails_closed_for_unverifiable_metadata(route: str, result: object) -> None:
    def run_process(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if isinstance(result, BaseException):
            raise result
        return cast(subprocess.CompletedProcess[bytes], result)

    assert OpenCodePricingProbe(run_process=run_process).check(route).is_free is False


@pytest.mark.integration
def test_pricing_probe_accepts_nested_zero_lists_and_rejects_duplicate_route_records() -> None:
    zero = subprocess.CompletedProcess(
        [],
        0,
        b'{"id":"model","providerID":"provider","cost":{"tiers":[0,0]}}',
        b"",
    )
    duplicate = subprocess.CompletedProcess(
        [],
        0,
        (
            b'{"id":"model","providerID":"provider","cost":{"input":0}}\n'
            b'{"id":"model","providerID":"provider","cost":{"input":0}}'
        ),
        b"",
    )

    assert OpenCodePricingProbe(run_process=lambda *args, **kwargs: zero).check("provider/model").is_free is True
    assert OpenCodePricingProbe(run_process=lambda *args, **kwargs: duplicate).check("provider/model").is_free is False


class _FakeProcess:
    def __init__(self, *, returncode: int | None = None, fail_kill: bool = False) -> None:
        self.pid = 4242
        self.returncode = returncode
        self.fail_kill = fail_kill
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float) -> int:
        self.returncode = 0
        return 0

    def kill(self) -> None:
        if self.fail_kill:
            raise OSError("synthetic kill failure")
        self.killed = True
        self.returncode = 0


@pytest.mark.integration
def test_headless_server_windows_close_success_refusal_and_kill_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "os", type("WindowsOs", (), {"name": "nt"})())
    process = _FakeProcess()
    server = OpenCodeHeadlessServer(port=4096)
    server._process = cast("subprocess.Popen[bytes]", process)
    monkeypatch.setattr(
        runner_module.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 0, b"", b""),
    )
    assert server.close() is True
    assert server.close() is True

    refused = _FakeProcess()
    server._process = cast("subprocess.Popen[bytes]", refused)
    monkeypatch.setattr(
        runner_module.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 1, b"", b""),
    )
    assert server.close() is False

    fallback = _FakeProcess()
    server._process = cast("subprocess.Popen[bytes]", fallback)
    monkeypatch.setattr(
        runner_module.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("taskkill failed")),
    )
    assert server.close() is True
    assert fallback.killed is True

    unkillable = _FakeProcess(fail_kill=True)
    server._process = cast("subprocess.Popen[bytes]", unkillable)
    assert server.close() is False


@pytest.mark.integration
def test_headless_server_configuration_start_and_health_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError):
        OpenCodeHeadlessServer(port=0)

    missing = OpenCodeHeadlessServer(
        port=4096,
        run_process=lambda *args, **kwargs: (_ for _ in ()).throw(OSError("missing")),
    )
    with pytest.raises(LoopbackTransportError):
        missing.create_session()

    exited_process = _FakeProcess(returncode=1)
    exited = OpenCodeHeadlessServer(
        port=4096,
        run_process=lambda *args, **kwargs: cast("subprocess.Popen[bytes]", exited_process),
        request=lambda *args: HttpResponse(503, b"{}"),
        startup_timeout_seconds=0.1,
    )
    with pytest.raises(LoopbackTransportError):
        exited.create_session()

    invalid_health = OpenCodeHeadlessServer(
        port=4096,
        request=lambda *args: HttpResponse(200, b"not-json"),
    )
    assert invalid_health._is_healthy() is False


@pytest.mark.integration
def test_loopback_runner_rejects_foreign_permit_and_failed_start_cleanup() -> None:
    events: list[str] = []

    class Client:
        def create_session(self) -> str:
            events.append("create")
            raise LoopbackTransportError()

        def send_review(self, session_id: str, *, route: str, prompt: bytes) -> bytes:
            raise AssertionError

        def delete_session(self, session_id: str) -> bool:
            raise AssertionError

        def close(self) -> bool:
            events.append("close")
            return False

    probe = OpenCodePricingProbe(
        run_process=lambda *args, **kwargs: subprocess.CompletedProcess(
            [],
            0,
            b'{"id":"model","providerID":"provider","cost":{"input":0}}',
            b"",
        )
    )
    runner = OpenCodeLoopbackRunner(probe, Client())
    with pytest.raises(ModelNotFreeError):
        runner.run(
            permit=PricingPermit("provider/model", object()),
            prompt=b"synthetic",
            validate_response=lambda payload: payload,
        )
    with pytest.raises(SessionCleanupError):
        runner.run(
            permit=runner.authorize("provider/model"),
            prompt=b"synthetic",
            validate_response=lambda payload: payload,
        )
    assert events == ["create", "close"]


@pytest.mark.integration
def test_storage_refuses_wrong_mission_missing_surface_and_exhausted_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _completed_run()
    with pytest.raises(ValueError, match="mission"):
        store_spec_review(repo_root=tmp_path, mission_slug="other", run=run)

    missing = tmp_path / "missing"
    monkeypatch.setattr(
        storage_module,
        "resolve_artifact_surface",
        lambda repo, slug, kind: ResolvedSurface(missing, TopologySurface.PRIMARY),
    )
    monkeypatch.setattr(
        storage_module,
        "placement_seam",
        lambda repo, slug: type("Seam", (), {"write_target": lambda self, kind: CommitTarget("codex/test")})(),
    )
    with pytest.raises(SpecReviewWriteError, match="INVALID_SURFACE"):
        store_spec_review(repo_root=tmp_path, mission_slug=_MISSION, run=run)

    mission = tmp_path / "mission"
    mission.mkdir()
    monkeypatch.setattr(
        storage_module,
        "resolve_artifact_surface",
        lambda repo, slug, kind: ResolvedSurface(mission, TopologySurface.PRIMARY),
    )
    monkeypatch.setattr(
        storage_module,
        "_publish_exclusive",
        lambda *args: (_ for _ in ()).throw(FileExistsError()),
    )
    with pytest.raises(SpecReviewWriteError, match="COLLISION"):
        store_spec_review(
            repo_root=tmp_path,
            mission_slug=_MISSION,
            run=run,
            next_run_id=lambda: "run-collision",
        )


@pytest.mark.integration
def test_storage_wraps_publish_error_and_rejects_non_directory_reviews(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = tmp_path / "mission"
    mission.mkdir()
    _route_storage(monkeypatch, mission)
    monkeypatch.setattr(
        storage_module,
        "_publish_exclusive",
        lambda *args: (_ for _ in ()).throw(OSError("disk")),
    )
    with pytest.raises(SpecReviewWriteError, match="WRITE_FAILED"):
        store_spec_review(repo_root=tmp_path, mission_slug=_MISSION, run=_completed_run())

    monkeypatch.undo()
    mission = tmp_path / "other-mission"
    mission.mkdir()
    (mission / "reviews").write_text("not a directory", encoding="utf-8")
    _route_storage(monkeypatch, mission)
    with pytest.raises(SpecReviewWriteError, match="INVALID_SURFACE"):
        store_spec_review(repo_root=tmp_path, mission_slug=_MISSION, run=_completed_run())


def _cli_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> typer.Typer:
    from specify_cli.cli.commands.spec_review import spec_review

    mission = tmp_path / "kitty-specs" / "demo"
    mission.mkdir(parents=True)
    (mission / "spec.md").write_text("# Synthetic\nOnly anonymous content.\n", encoding="utf-8")
    resolved = ResolvedMission("01KQTEST000000000000000000", "demo", mission, "01KQTEST")
    monkeypatch.setattr("specify_cli.cli.commands.spec_review.find_repo_root", lambda: tmp_path)
    monkeypatch.setattr("specify_cli.cli.commands.spec_review.resolve_mission_handle", lambda handle, root: resolved)
    app = typer.Typer()
    app.command()(spec_review)
    return app


@pytest.mark.integration
def test_cli_interactive_cancel_and_nonzero_outcome_rendering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.cli.commands.spec_review as cli_module

    app = _cli_app(tmp_path, monkeypatch)
    fake_sys = type("FakeSys", (), {"stdin": type("FakeStdin", (), {"isatty": lambda self: True})()})()
    monkeypatch.setattr(cli_module, "sys", fake_sys)
    monkeypatch.setattr(cli_module.typer, "confirm", lambda prompt: False)

    cancelled = CliRunner().invoke(app, ["--mission", "demo"])

    assert cancelled.exit_code == 0
    assert "отменено" in cancelled.output

    manifest = cli_module.prepare_default_disclosure(repo_root=tmp_path, mission_slug="demo")
    artifact = StoredSpecReview(tmp_path / "review.yaml", "run-cli", CommitTarget("codex/demo"))

    class FakeService:
        def execute(self, *, confirm_digest: str | None, preview: bool) -> SpecReviewOutcome:
            return SpecReviewOutcome(
                exit_code=4,
                diagnostic_code="SPEC_REVIEW_PROVIDER_ERROR",
                manifest=manifest,
                status=None,
                artifact=artifact,
            )

    monkeypatch.setattr(cli_module, "_build_service", lambda *args: FakeService())
    failed = CliRunner().invoke(app, ["--mission", "demo", "--confirm-digest", manifest.manifest_sha256])

    assert failed.exit_code == 4
    assert "Статус: unknown" in failed.output
    assert "SPEC_REVIEW_PROVIDER_ERROR" in failed.output
    assert "Артефакт:" in failed.output


@pytest.mark.integration
def test_cli_build_service_and_port_reservation_are_local_only(tmp_path: Path) -> None:
    from specify_cli.cli.commands.spec_review import _build_service, _reserve_loopback_port

    _mission(tmp_path)
    port = _reserve_loopback_port()
    service = _build_service(tmp_path, _MISSION, "provider/model", 42)

    assert 1 <= port <= 65535
    assert service.prepare().requested_model_route == "provider/model"
