"""CLI consent paths remain local until the injected service is invoked."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
import typer
from typer.testing import CliRunner

from charter.hasher import hash_content
from specify_cli.cli.commands.spec_review import spec_review
from specify_cli.context.mission_resolver import ResolvedMission
from specify_cli.spec_review.models import ReviewStatus, ReviewSummary
from specify_cli.spec_review.service import SpecReviewOutcome, prepare_default_disclosure


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _setup_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[typer.Typer, Path]:
    mission = tmp_path / "kitty-specs" / "demo"
    mission.mkdir(parents=True)
    (mission / "spec.md").write_text("# Синтетическая спека\nТолько тестовые данные.\n", encoding="utf-8")
    resolved = ResolvedMission(
        mission_id="01KQTEST000000000000000000",
        mission_slug="demo",
        feature_dir=mission,
        mid8="01KQTEST",
    )
    monkeypatch.setattr("specify_cli.cli.commands.spec_review.find_repo_root", lambda: tmp_path)
    monkeypatch.setattr("specify_cli.cli.commands.spec_review.resolve_mission_handle", lambda handle, root: resolved)
    app = typer.Typer()
    app.command()(spec_review)
    return app, mission


def test_preview_prints_manifest_and_stops_before_external_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app, _mission = _setup_cli(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["--mission", "demo", "--preview"])

    assert result.exit_code == 0, result.output
    assert "Digest согласия:" in result.output
    assert "pricing, prompt и модель не запускались" in result.output


def test_noninteractive_execution_requires_exact_digest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app, _mission = _setup_cli(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["--mission", "demo"])

    assert result.exit_code == 2
    assert "SPEC_REVIEW_CONSENT_REQUIRED" in result.output


def test_confirmed_execution_uses_injected_service_without_open_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _mission = _setup_cli(tmp_path, monkeypatch)
    calls: list[tuple[str | None, bool]] = []
    manifest = prepare_default_disclosure(repo_root=tmp_path, mission_slug="demo")

    class FakeService:
        def execute(self, *, confirm_digest: str | None, preview: bool) -> SpecReviewOutcome:
            calls.append((confirm_digest, preview))
            return SpecReviewOutcome(
                exit_code=0,
                diagnostic_code=None,
                manifest=manifest,
                status=ReviewStatus.COMPLETED,
                summary=ReviewSummary.from_findings(()),
            )

    monkeypatch.setattr("specify_cli.cli.commands.spec_review._build_service", lambda *args: FakeService())

    result = CliRunner().invoke(app, ["--mission", "demo", "--confirm-digest", "a" * 64])

    assert result.exit_code == 0, result.output
    assert calls == [("a" * 64, False)]
    assert "Статус: completed" in result.output
    assert "Замечания: 0" in result.output


def test_timeout_is_validated_before_mission_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    app = typer.Typer()
    app.command()(spec_review)
    monkeypatch.setattr("specify_cli.cli.commands.spec_review.find_repo_root", lambda: (_ for _ in ()).throw(AssertionError()))

    result = CliRunner().invoke(app, ["--mission", "demo", "--timeout", "9"])

    assert result.exit_code == 2
    assert "10–600" in result.output


def test_preflight_refusal_is_safe_and_does_not_construct_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, mission = _setup_cli(tmp_path, monkeypatch)
    sentinel = "secret=DO-NOT-LEAK"
    (mission / "spec.md").write_text(f"# Синтетическая спека\n{sentinel}\n", encoding="utf-8")
    monkeypatch.setattr(
        "specify_cli.cli.commands.spec_review._build_service",
        lambda *args: (_ for _ in ()).throw(AssertionError("runner must not be constructed")),
    )

    result = CliRunner().invoke(app, ["--mission", "demo", "--preview"])

    assert result.exit_code == 3
    assert "SPEC_REVIEW_INPUT_REFUSED: token_assignment" in result.output
    assert sentinel not in result.output


def test_preview_and_missing_consent_leave_mission_files_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, mission = _setup_cli(tmp_path, monkeypatch)
    (mission / "meta.json").write_text('{"mission_id":"01KQTEST000000000000000000"}', encoding="utf-8")
    (mission / "lanes.json").write_text('{"version":1}', encoding="utf-8")
    tracked = (mission / "spec.md", mission / "meta.json", mission / "lanes.json")
    before = {path.name: hash_content(path.read_text(encoding="utf-8")) for path in tracked}

    preview = CliRunner().invoke(app, ["--mission", "demo", "--preview"])
    missing_consent = CliRunner().invoke(app, ["--mission", "demo"])

    after = {path.name: hash_content(path.read_text(encoding="utf-8")) for path in tracked}
    assert preview.exit_code == 0, preview.output
    assert missing_consent.exit_code == 2, missing_consent.output
    assert after == before


def test_next_fast_path_does_not_import_spec_review_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    import typer

    from specify_cli.cli.commands import register_commands

    monkeypatch.delitem(sys.modules, "specify_cli.spec_review.runner", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "next", "--mission", "demo"])
    app = typer.Typer()

    register_commands(app)

    assert "specify_cli.spec_review.runner" not in sys.modules


def test_existing_review_remains_a_leaf_with_its_public_options() -> None:
    from specify_cli import _build_app

    result = CliRunner().invoke(_build_app(), ["review", "--help"])

    assert result.exit_code == 0, result.output
    assert "--mission" in result.output
    assert "--mode" in result.output
    assert "--check-residual" in result.output
