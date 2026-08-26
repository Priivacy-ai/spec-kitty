"""Explicit, synthetic-only live smoke for the OpenCode review adapter."""

from __future__ import annotations

import os
from pathlib import Path
import socket

import pytest

from mission_runtime import CommitTarget, TopologySurface
from mission_runtime.resolution import ResolvedSurface
from specify_cli.spec_review.runner import OpenCodeHeadlessServer, OpenCodeLoopbackRunner, OpenCodePricingProbe
from specify_cli.spec_review.service import DEFAULT_MODEL_ROUTE, SpecReviewService, load_default_review_materials


_LIVE_ENABLE_ENV = "SPEC_KITTY_RUN_SPEC_REVIEW_LIVE"
_LIVE_CONFIRM_ENV = "SPEC_KITTY_SPEC_REVIEW_LIVE_CONFIRM_DIGEST"
_MISSION = "synthetic-live-spec-review"
_SPEC = """# Synthetic note sorter

## Goal
Sort anonymous note labels alphabetically.

## Acceptance
Duplicate labels remain present in the output.
"""


def _unused_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@pytest.mark.integration
def test_live_review_uses_only_built_in_synthetic_spec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if os.environ.get(_LIVE_ENABLE_ENV) != "1":
        pytest.skip(f"set {_LIVE_ENABLE_ENV}=1 for the explicit live smoke")

    mission = tmp_path / "kitty-specs" / _MISSION
    mission.mkdir(parents=True)
    spec = mission / "spec.md"
    spec.write_text(_SPEC, encoding="utf-8", newline="\n")
    before = spec.read_bytes()
    monkeypatch.setattr(
        "specify_cli.spec_review.storage.resolve_artifact_surface",
        lambda repo, slug, kind: ResolvedSurface(mission, TopologySurface.PRIMARY),
    )
    monkeypatch.setattr(
        "specify_cli.spec_review.storage.placement_seam",
        lambda repo, slug: type(
            "Seam",
            (),
            {"write_target": lambda self, kind: CommitTarget("codex/synthetic-live-spec-review")},
        )(),
    )
    rubric, response_schema, prompt_template = load_default_review_materials()
    server = OpenCodeHeadlessServer(port=_unused_loopback_port())
    service = SpecReviewService(
        repo_root=tmp_path,
        mission_slug=_MISSION,
        rubric=rubric,
        response_schema=response_schema,
        prompt_template=prompt_template,
        runner=OpenCodeLoopbackRunner(OpenCodePricingProbe(), server),
        model_route=DEFAULT_MODEL_ROUTE,
    )
    manifest = service.prepare()
    disclosure = f"route={manifest.requested_model_route} manifest_sha256={manifest.manifest_sha256}"
    print(disclosure)
    if os.environ.get(_LIVE_CONFIRM_ENV) != manifest.manifest_sha256:
        pytest.skip(f"inspect {disclosure}, then set {_LIVE_CONFIRM_ENV} to that exact digest")

    outcome = service.execute(confirm_digest=manifest.manifest_sha256, preview=False)

    assert outcome.exit_code == 0
    assert outcome.artifact is not None
    assert outcome.artifact.path.is_file()
    assert spec.read_bytes() == before
