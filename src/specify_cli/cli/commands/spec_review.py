"""Metadata-only preview for an advisory external specification review."""

from __future__ import annotations

import socket
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated

import typer

from specify_cli.cli.console import console
from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.spec_review.models import DisclosureManifest, PaidPricingDisclosure
from specify_cli.spec_review.preflight import PreflightRefusal
from specify_cli.spec_review.runner import (
    PAID_GLM53_ROUTE,
    OpenCodeHeadlessServer,
    OpenCodeLoopbackRunner,
    OpenCodePricingProbe,
    PaidPricingError,
)
from specify_cli.spec_review.service import (
    DEFAULT_MODEL_ROUTE,
    SpecReviewOutcome,
    SpecReviewService,
    load_default_review_materials,
    prepare_default_disclosure,
)
from specify_cli.task_utils import find_repo_root


def spec_review(
    mission: Annotated[str, typer.Option("--mission", help="Миссия для ревью спецификации.")],
    model: Annotated[
        str,
        typer.Option("--model", help="Точный маршрут модели; paid preview использует только его metadata."),
    ] = DEFAULT_MODEL_ROUTE,
    max_estimated_cost_usd: Annotated[
        str | None,
        typer.Option(
            "--max-estimated-cost-usd",
            help="Локальный порог advertised-оценки для opt-in paid route; не лимит фактического счёта.",
        ),
    ] = None,
    preview: Annotated[
        bool,
        typer.Option("--preview", help="Показать состав раскрытия и завершиться без внешнего обращения."),
    ] = False,
    confirm_digest: Annotated[
        str | None,
        typer.Option("--confirm-digest", help="Одноразовый digest согласия из текущего manifest."),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Таймаут ответа OpenCode в секундах: 10–600."),
    ] = 180,
) -> None:
    """Запустить только явно подтверждённое консультативное ревью Mission-спеки."""
    threshold = _validate_paid_threshold(model, max_estimated_cost_usd)
    if not 10 <= timeout <= 600:
        console.print("[red]Ошибка:[/red] --timeout должен быть в диапазоне 10–600 секунд.")
        raise typer.Exit(2)
    repo_root = find_repo_root()
    resolved = resolve_mission_handle(mission, repo_root)
    paid_pricing: PaidPricingDisclosure | None = None
    if threshold is not None:
        try:
            paid_pricing = OpenCodePricingProbe().quote_paid(
                model,
                max_estimated_cost_usd=threshold,
            )
        except PaidPricingError as error:
            console.print(error.code)
            raise typer.Exit(4) from None
    try:
        manifest = prepare_default_disclosure(
            repo_root=repo_root,
            mission_slug=resolved.mission_slug,
            model_route=model,
            paid_pricing=paid_pricing,
        )
    except PreflightRefusal as error:
        category = error.sensitive_category.value if error.sensitive_category is not None else error.diagnostic.value
        console.print(f"SPEC_REVIEW_INPUT_REFUSED: {category}")
        raise typer.Exit(3) from None
    _render_manifest(resolved.mission_slug, manifest)
    if preview:
        if manifest.paid_pricing is None:
            console.print("Preview завершён: pricing, prompt и модель не запускались.")
        else:
            console.print("Paid preview завершён: проверены только metadata; prompt, сессия и модель не запускались.")
        return
    confirmed_digest = confirm_digest
    if confirmed_digest is None:
        if not sys.stdin.isatty():
            console.print("SPEC_REVIEW_CONSENT_REQUIRED: передайте --confirm-digest из текущего manifest.")
            raise typer.Exit(2)
        if not typer.confirm("Подтвердить одну внешнюю передачу именно этого пакета?"):
            console.print("Ревью отменено: внешний вызов не выполнялся.")
            return
        confirmed_digest = manifest.manifest_sha256
    outcome = _build_service(
        repo_root,
        resolved.mission_slug,
        model,
        timeout,
        manifest.paid_pricing,
    ).execute(
        confirm_digest=confirmed_digest,
        preview=False,
    )
    _render_outcome(outcome)
    if outcome.exit_code:
        raise typer.Exit(outcome.exit_code)


def _build_service(
    repo_root: Path,
    mission_slug: str,
    model_route: str,
    timeout: int,
    paid_pricing: PaidPricingDisclosure | None = None,
) -> SpecReviewService:
    """Construct the isolated runner only after consent has been supplied."""
    rubric, response_schema, prompt_template = load_default_review_materials()
    server = OpenCodeHeadlessServer(port=_reserve_loopback_port(), request_timeout_seconds=float(timeout))
    return SpecReviewService(
        repo_root=repo_root,
        mission_slug=mission_slug,
        rubric=rubric,
        response_schema=response_schema,
        prompt_template=prompt_template,
        runner=OpenCodeLoopbackRunner(OpenCodePricingProbe(), server),
        model_route=model_route,
        paid_pricing=paid_pricing,
    )


def _reserve_loopback_port() -> int:
    """Reserve a numeric loopback port for the immediately following local server start."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _render_manifest(mission_slug: str, manifest: DisclosureManifest) -> None:
    """Render only fixed metadata about a future disclosure, never its content."""
    console.print(f"Миссия: {mission_slug}")
    console.print(f"Транспорт: {manifest.transport}")
    console.print(f"Маршрут модели: {manifest.requested_model_route}")
    for component in (manifest.spec, manifest.rubric, manifest.response_schema, manifest.prompt_template):
        console.print(f"{component.name}: {component.size_bytes} байт, sha256={component.sha256}")
    console.print(f"Размер раскрытия: {manifest.total_payload_bytes} байт")
    if manifest.paid_pricing is not None:
        pricing = manifest.paid_pricing
        console.print(f"Порог локальной оценки: {pricing.max_estimated_cost_usd} USD")
        console.print(f"Advertised maximum estimate: {pricing.advertised_max_estimate_usd} USD")
        console.print(f"Pricing metadata sha256: {pricing.metadata_sha256}")
        console.print(f"Лимиты metadata: context={pricing.context_limit}, output={pricing.output_limit}")
        console.print("Предупреждение: это не provider-side cap; фактический billing может отличаться.")
    console.print(f"Digest согласия: {manifest.manifest_sha256}")
    console.print("Внимание: доступность, цена, владение, retention и обезличивание не подтверждены этим manifest.")


def _validate_paid_threshold(model_route: str, raw_value: str | None) -> str | None:
    """Validate paid opt-in before mission resolution or any metadata probe."""
    if model_route != PAID_GLM53_ROUTE:
        if raw_value is not None:
            console.print("[red]Ошибка:[/red] --max-estimated-cost-usd допустим только для exact GLM 5.3 route.")
            raise typer.Exit(2)
        return None
    if raw_value is None:
        console.print(f"[red]Ошибка:[/red] {PAID_GLM53_ROUTE} требует --max-estimated-cost-usd.")
        raise typer.Exit(2)
    try:
        value = Decimal(raw_value)
    except InvalidOperation:
        value = Decimal("NaN")
    if not value.is_finite() or value <= 0 or value > 5:
        console.print("[red]Ошибка:[/red] --max-estimated-cost-usd: требуется 0 < значение <= 5 USD.")
        raise typer.Exit(2)
    return format(value.normalize(), "f")


def _render_outcome(outcome: SpecReviewOutcome) -> None:
    """Render the host-owned result without provider output or prompt text."""
    status = outcome.status.value if outcome.status is not None else "unknown"
    console.print(f"Статус: {status}")
    if outcome.diagnostic_code is not None:
        console.print(f"Диагностика: {outcome.diagnostic_code}")
    if outcome.summary is not None:
        summary = outcome.summary
        console.print(
            "Замечания: "
            f"{summary.total} (S1={summary.severity_1}, S2={summary.severity_2}, "
            f"S3={summary.severity_3}, S4={summary.severity_4}, S5={summary.severity_5})"
        )
    if outcome.artifact is not None:
        console.print(f"Артефакт: {outcome.artifact.path}")
