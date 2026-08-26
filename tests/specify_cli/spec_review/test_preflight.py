"""Acceptance tests for canonical input and sensitive-content preflight."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from specify_cli.spec_review.preflight import (
    MAX_SPEC_BYTES,
    MissionSpecContext,
    PreflightRefusal,
    PreflightDisclosure,
    ReviewPromptTemplate,
    ReviewResponseSchema,
    ReviewRubric,
    SCANNER_VERSION,
    SensitiveCategory,
    build_disclosure,
    confirm_and_load_spec,
    scan_sensitive_markers,
)


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _context(tmp_path: Path, contents: bytes = b"# Synthetic mission\n") -> MissionSpecContext:
    mission_dir = tmp_path / "missions" / "synthetic"
    mission_dir.mkdir(parents=True)
    (mission_dir / "spec.md").write_bytes(contents)
    return MissionSpecContext.create(repo_root=tmp_path, mission_dir=mission_dir)


def _disclosure(context: MissionSpecContext) -> PreflightDisclosure:
    return build_disclosure(
        context=context,
        transport="opencode-loopback",
        requested_model_route="opencode/synthetic",
        rubric=ReviewRubric(version="v1", serialized=b'{"scanner":"heuristic-v1"}', scanner_version=SCANNER_VERSION),
        response_schema=ReviewResponseSchema(version="review-response/v1", serialized=b"schema: review-response/v1\n"),
        prompt_template=ReviewPromptTemplate(version="review-template/v1", serialized=b"Review only the supplied spec."),
    )


def test_confirmation_uses_one_rechecked_immutable_snapshot(tmp_path: Path) -> None:
    context = _context(tmp_path)
    disclosure = _disclosure(context)

    snapshot = confirm_and_load_spec(disclosure, disclosure.manifest.manifest_sha256)

    assert snapshot.payload == b"# Synthetic mission\n"
    assert snapshot.line_count == 1
    assert snapshot.scanner_version == SCANNER_VERSION


@pytest.mark.parametrize(
    "change",
    [
        lambda disclosure: replace(
            disclosure,
            manifest=replace(disclosure.manifest, transport="other-transport"),
        ),
        lambda disclosure: replace(
            disclosure,
            manifest=replace(disclosure.manifest, requested_model_route="opencode/other"),
        ),
        lambda disclosure: replace(
            disclosure,
            manifest=replace(disclosure.manifest, spec=replace(disclosure.manifest.spec, sha256="0" * 64)),
        ),
        lambda disclosure: replace(
            disclosure,
            rubric=ReviewRubric(version="v2", serialized=b'{"scanner":"heuristic-v1"}', scanner_version=SCANNER_VERSION),
        ),
        lambda disclosure: replace(
            disclosure,
            response_schema=ReviewResponseSchema(version="review-response/v2", serialized=b"schema: review-response/v2\n"),
        ),
        lambda disclosure: replace(
            disclosure,
            prompt_template=ReviewPromptTemplate(version="review-template/v2", serialized=b"Different prompt."),
        ),
    ],
)
def test_each_manifest_component_drift_invalidates_consent(
    tmp_path: Path,
    change: Callable[[PreflightDisclosure], PreflightDisclosure],
) -> None:
    context = _context(tmp_path)
    disclosure = _disclosure(context)
    changed = change(disclosure)

    with pytest.raises(PreflightRefusal) as error:
        confirm_and_load_spec(changed, disclosure.manifest.manifest_sha256)

    assert error.value.diagnostic.value == "manifest_drift"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda path: path.write_bytes(b"# changed\n"),
        lambda path: path.unlink(),
    ],
)
def test_manifest_drift_or_missing_spec_refuses_before_send(
    tmp_path: Path,
    mutator: Callable[[Path], object],
) -> None:
    context = _context(tmp_path)
    disclosure = _disclosure(context)
    mutator(context.mission_dir / "spec.md")

    with pytest.raises(PreflightRefusal) as error:
        confirm_and_load_spec(disclosure, disclosure.manifest.manifest_sha256)

    assert "Synthetic mission" not in str(error.value)


def test_path_escape_symlink_and_size_limit_are_refused(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("# outside\n", encoding="utf-8")
    mission_dir = tmp_path / "missions" / "synthetic"
    mission_dir.mkdir(parents=True)
    link = mission_dir / "spec.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable in this local test environment")

    context = MissionSpecContext.create(repo_root=tmp_path, mission_dir=mission_dir)
    with pytest.raises(PreflightRefusal):
        _disclosure(context)

    oversized = _context(tmp_path / "large", b"x" * (MAX_SPEC_BYTES + 1))
    with pytest.raises(PreflightRefusal):
        _disclosure(oversized)


def test_scanner_returns_only_safe_positions_and_warning() -> None:
    findings = scan_sensitive_markers(
        b"\xef\xbb\xbfAPI_TOKEN = 'not-reported'\r\nuser@example.test\r\n-----BEGIN PRIVATE KEY-----\r\n"
    )

    assert {finding.category.value for finding in findings} >= {"token_assignment", "email", "private_key"}
    assert all(not hasattr(finding, "matched_value") for finding in findings)


def test_scanner_ignores_iso_dates_but_keeps_real_phone_markers() -> None:
    findings = scan_sensitive_markers(b"Date: 2026-08-23\nPhone: +7 999 123-45-67\n")

    assert [(finding.category, finding.line) for finding in findings] == [(SensitiveCategory.PHONE, 2)]


def test_sensitive_refusal_exposes_only_the_safe_category(tmp_path: Path) -> None:
    secret = b"API_TOKEN = 'never-expose-this-value'\n"
    context = _context(tmp_path, secret)

    with pytest.raises(PreflightRefusal) as error:
        _disclosure(context)

    assert error.value.sensitive_category is SensitiveCategory.TOKEN_ASSIGNMENT
    assert "token_assignment" in str(error.value)
    assert secret.decode("utf-8") not in str(error.value)
