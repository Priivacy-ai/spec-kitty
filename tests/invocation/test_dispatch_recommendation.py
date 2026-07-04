"""Red-first ATDD for FR-004: advisory model-routing recommendation on the dispatch payload.

WP03 wires the WP01 loader + WP02 evaluator into ``ProfileInvocationExecutor.invoke()``
so the governed dispatch seam surfaces an advisory, non-fatal model-routing
recommendation (spec.md FR-004, NFR-001, NFR-002, C-001).

Load-bearing traps this file guards against:

* **NFR-001 / real entry point**: every assertion goes through ``invoke()`` or the
  ``spec-kitty dispatch`` CLI payload -- never the evaluator/Pydantic model in
  isolation.
* **SC-001 / anti-fake**: ``test_recommendation_varies_with_catalog_scoring_via_invoke``
  proves the recommendation is *computed*, not a stub, by writing two fixture
  catalogs that differ only in ``task_fit`` scores and asserting the winning
  ``model_id`` flips between them.
* **NFR-002 / advisory, non-fatal**: missing/stale/unmatched catalog and
  unmapped-verb cases all assert the recommendation is absent (``None``) while
  ``invoke()``/``dispatch`` still succeeds -- never raises.
* **T019 / WP01<->WP05 integration**: with NO catalog-path override, the loader's
  default (``importlib.resources``) path must agree with WP05's shipped
  ``model-to-task_type.yaml`` file location.
"""

from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import Result
from typer import Typer
from typer.testing import CliRunner

from doctrine.model_task_routing import loader as real_loader
from doctrine.model_task_routing.evaluator import RoutingCandidate, RoutingRecommendation
from specify_cli import app as cli_app
from specify_cli.cli.commands.dispatch import _render_rich_payload
from specify_cli.invocation.executor import InvocationPayload, ProfileInvocationExecutor

pytestmark = [pytest.mark.unit]

FIXTURES_DIR = Path(__file__).parent.parent / "specify_cli" / "invocation" / "fixtures" / "profiles"

_COMPACT_CTX = MagicMock()
_COMPACT_CTX.mode = "compact"
_COMPACT_CTX.text = "compact governance context"


class ArgvCliRunner(CliRunner):
    """CliRunner that also patches ``sys.argv`` (mirrors ``cli/test_dispatch.py``).

    Several readiness/output-policy checks read ``sys.argv`` directly (not the
    args CliRunner passes to the click command), so without this, ``--json``
    is invisible to them and they emit interactive nag/auth-recovery text that
    corrupts the captured JSON payload.
    """

    def invoke(  # type: ignore[override]
        self,
        app: Typer,
        args: str | Sequence[str] | None = None,
        **kwargs: Any,
    ) -> Result:
        argv = ["spec-kitty", *(list(args) if args is not None and not isinstance(args, str) else [])]
        with patch.object(sys, "argv", argv):
            return super().invoke(app, args, **kwargs)


runner = ArgvCliRunner()


def _setup_project(tmp_path: Path) -> Path:
    """Copy the shared implementer/reviewer profile fixtures into a project skeleton."""
    profiles_dir = tmp_path / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)
    return tmp_path


# ---------------------------------------------------------------------------
# Fixture catalog builder — schema-legal ``ModelToTaskType`` YAML with two
# models whose scores are parameterized so tests can flip the winner.
# ---------------------------------------------------------------------------

_CATALOG_TEMPLATE = """\
schema_version: "1.0"
generated_at: "{generated_at}"
source_snapshot: {snapshot}
task_types:
  - id: {task_type}
    title: Fixture Task Type
models:
  - id: model-alpha
    provider: test-fixture
    task_fit:
      - task_type: {task_type}
        score: {alpha_score}
        confidence: high
    cost:
      tier: low
  - id: model-beta
    provider: test-fixture
    task_fit:
      - task_type: {task_type}
        score: {beta_score}
        confidence: high
    cost:
      tier: low
routing_policy:
  objective: quality_first
  weights:
    quality: 1.0
    cost: 0.0
    risk: 0.0
    latency: 0.0
  override_policy:
    mode: advisory
    require_reason: false
  {freshness_block}
sources:
  - name: fixture
    url: https://example.invalid/fixture
    access_method: manual
    snapshot_at: "{generated_at}"
"""

_FRESHNESS_STALE = "freshness_policy:\n    max_catalog_age_hours: 1\n"


def _write_catalog(
    tmp_path: Path,
    name: str,
    *,
    task_type: str = "code-review",
    alpha_score: float,
    beta_score: float,
    generated_at: str = "2026-01-01T00:00:00Z",
    stale: bool = False,
) -> Path:
    path = tmp_path / name
    text = _CATALOG_TEMPLATE.format(
        generated_at=generated_at,
        snapshot=name,
        task_type=task_type,
        alpha_score=alpha_score,
        beta_score=beta_score,
        freshness_block=_FRESHNESS_STALE if stale else "",
    )
    path.write_text(text, encoding="utf-8")
    return path


# Captured ONCE at module-import time, before any test patches
# ``doctrine.model_task_routing.loader.load``. ``_compute_recommendation``
# imports ``doctrine.model_task_routing.loader`` FUNCTION-LOCALLY (the
# runtime -> charter -> doctrine boundary forbids a module-level `from
# doctrine.*` import from specify_cli/, see
# tests/architectural/test_runtime_charter_doctrine_boundary.py), so each
# call re-resolves the *same* live module object -- patching
# ``doctrine.model_task_routing.loader.load`` directly (rather than an
# attribute on ``specify_cli.invocation.executor``) is what actually takes
# effect. ``_load_from`` below must call this captured reference rather
# than ``real_loader.load`` directly, or a patch installed via one of this
# file's own helpers would recurse into itself instead of reaching the
# real loader.
_REAL_LOAD = real_loader.load


def _load_from(fixture_path: Path) -> Callable[..., real_loader.CatalogLoadResult | None]:
    """Build a ``doctrine.model_task_routing.loader.load`` replacement pinned at *fixture_path*.

    Uses the real, injectable ``load(catalog_path=...)`` override (WP01) --
    the point is to exercise the actual loader against a fixture file, not to
    stub the loader itself.
    """

    def _fake_load(*_args: object, **_kwargs: object) -> real_loader.CatalogLoadResult | None:
        return _REAL_LOAD(catalog_path=fixture_path)

    return _fake_load


# ---------------------------------------------------------------------------
# T012 / SC-001 — anti-fake: recommendation VARIES with catalog scoring
# ---------------------------------------------------------------------------


def test_recommendation_varies_with_catalog_scoring_via_invoke(tmp_path: Path) -> None:
    """Two fixture catalogs differing only in task_fit scores flip the winner.

    This is the anti-fake proof required by SC-001: a hardcoded or
    always-identical recommendation would fail this test even though it is
    green on a single-catalog check.
    """
    _setup_project(tmp_path)
    catalog_alpha_wins = _write_catalog(tmp_path, "catalog-alpha-wins.yaml", alpha_score=0.9, beta_score=0.2)
    catalog_beta_wins = _write_catalog(tmp_path, "catalog-beta-wins.yaml", alpha_score=0.2, beta_score=0.9)

    with patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX):
        executor = ProfileInvocationExecutor(tmp_path)

        with patch(
            "doctrine.model_task_routing.loader.load",
            side_effect=_load_from(catalog_alpha_wins),
        ):
            payload_alpha = executor.invoke(
                "review the diff", profile_hint="reviewer-fixture", action_hint="review"
            )

        with patch(
            "doctrine.model_task_routing.loader.load",
            side_effect=_load_from(catalog_beta_wins),
        ):
            payload_beta = executor.invoke(
                "review the diff", profile_hint="reviewer-fixture", action_hint="review"
            )

    rec_alpha = payload_alpha.recommendation
    rec_beta = payload_beta.recommendation
    assert rec_alpha is not None
    assert rec_beta is not None
    assert rec_alpha.catalog_candidate is not None
    assert rec_beta.catalog_candidate is not None
    assert rec_alpha.catalog_candidate.model_id == "model-alpha"
    assert rec_beta.catalog_candidate.model_id == "model-beta"
    assert rec_alpha.catalog_candidate.model_id != rec_beta.catalog_candidate.model_id


# ---------------------------------------------------------------------------
# T016 / NFR-002 — non-fatal envelope: absent recommendation, dispatch succeeds
# ---------------------------------------------------------------------------


def test_recommendation_absent_when_catalog_missing_dispatch_still_succeeds(tmp_path: Path) -> None:
    _setup_project(tmp_path)
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX):
        executor = ProfileInvocationExecutor(tmp_path)
        with patch("doctrine.model_task_routing.loader.load", return_value=None):
            payload = executor.invoke(
                "review the diff", profile_hint="reviewer-fixture", action_hint="review"
            )

    assert payload.recommendation is None
    # dispatch still succeeded -- an Op was opened, no exception propagated.
    assert payload.invocation_id


def test_recommendation_absent_when_catalog_stale(tmp_path: Path) -> None:
    _setup_project(tmp_path)
    stale_catalog = _write_catalog(
        tmp_path,
        "catalog-stale.yaml",
        alpha_score=0.9,
        beta_score=0.2,
        generated_at="2000-01-01T00:00:00Z",
        stale=True,
    )

    with patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX):
        executor = ProfileInvocationExecutor(tmp_path)
        with patch(
            "doctrine.model_task_routing.loader.load",
            side_effect=_load_from(stale_catalog),
        ):
            payload = executor.invoke(
                "review the diff", profile_hint="reviewer-fixture", action_hint="review"
            )

    assert payload.recommendation is None
    assert payload.invocation_id


def test_recommendation_absent_when_task_type_unmatched(tmp_path: Path) -> None:
    """The catalog loads fine but carries no task_fit entries for the resolved task_type."""
    _setup_project(tmp_path)
    unmatched_catalog = _write_catalog(
        tmp_path,
        "catalog-unmatched.yaml",
        task_type="unrelated-task",
        alpha_score=0.9,
        beta_score=0.2,
    )

    with patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX):
        executor = ProfileInvocationExecutor(tmp_path)
        with patch(
            "doctrine.model_task_routing.loader.load",
            side_effect=_load_from(unmatched_catalog),
        ):
            payload = executor.invoke(
                "review the diff", profile_hint="reviewer-fixture", action_hint="review"
            )

    assert payload.recommendation is None
    assert payload.invocation_id


def test_recommendation_absent_when_action_has_no_task_type_mapping(tmp_path: Path) -> None:
    """An action verb outside task_class_map's maintained namespace degrades to absent."""
    _setup_project(tmp_path)
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX):
        executor = ProfileInvocationExecutor(tmp_path)
        payload = executor.invoke(
            "do something custom",
            profile_hint="reviewer-fixture",
            action_hint="some-custom-verb-outside-the-map",
        )

    assert payload.recommendation is None
    assert payload.invocation_id


# ---------------------------------------------------------------------------
# T019 — integration proof: no override, real shipped WP05 catalog via the
# loader's default (importlib.resources) path.
# ---------------------------------------------------------------------------


def test_invoke_produces_recommendation_from_real_shipped_catalog_default_path(tmp_path: Path) -> None:
    """No fixture override: WP01's default loader path must agree with WP05's
    shipped ``src/doctrine/model_task_routing/catalog/model-to-task_type.yaml``.
    """
    _setup_project(tmp_path)
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX):
        executor = ProfileInvocationExecutor(tmp_path)
        payload = executor.invoke(
            "review the diff", profile_hint="reviewer-fixture", action_hint="review"
        )

    assert payload.recommendation is not None
    assert payload.recommendation.task_type == "code-review"
    assert payload.recommendation.catalog_candidate is not None


def test_invoke_produces_recommendation_for_non_review_verb_real_catalog(tmp_path: Path) -> None:
    """Fix 2 regression guard: the real shipped catalog must cover more than
    the single ``review`` -> ``code-review`` verb. Proves the feature fires
    end-to-end (through ``invoke()``, the real loader default path, and the
    real evaluator) for an "implement" -> "code-implementation" verb --
    before Fix 2, every task_type but ``code-review`` was uncovered and this
    would have resolved to ``None``.
    """
    _setup_project(tmp_path)
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX):
        executor = ProfileInvocationExecutor(tmp_path)
        payload = executor.invoke(
            "implement the fix", profile_hint="implementer-fixture", action_hint="implement"
        )

    assert payload.recommendation is not None
    assert payload.recommendation.task_type == "code-implementation"
    assert payload.recommendation.catalog_candidate is not None


def test_dispatch_cli_recommendation_present_for_audit_verb_real_catalog(tmp_path: Path) -> None:
    """CLI-level proof against the REAL shipped catalog: reviewer-fixture's
    default canonical verb ("audit" -> "quality-audit") IS now covered by
    the catalog (Fix 2's hard-judgment tier expansion, mission #2364
    aggregate-review remediation, #2369) -- the recommendation is present
    end-to-end through the CLI dispatch, not just through ``invoke()`` with
    an explicit ``action_hint``.

    Before Fix 2, this asserted the OPPOSITE (recommendation absent) --
    that was the exact vocabulary-drift gap the aggregate review found:
    20 of the 21 task_class_map task_types had zero catalog coverage.
    """
    project = _setup_project(tmp_path)
    with (
        patch("specify_cli.cli.commands.dispatch.find_repo_root", return_value=project),
        patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX),
    ):
        result = runner.invoke(
            cli_app,
            ["dispatch", "review the diff", "--profile", "reviewer-fixture", "--json"],
        )

    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output)
    assert envelope["action"] == "audit"
    assert envelope["recommendation"] is not None
    assert envelope["recommendation"]["task_type"] == "quality-audit"
    assert envelope["recommendation"]["candidates"]


# ---------------------------------------------------------------------------
# T013 — InvocationPayload.to_dict() serializes the recommendation slot and
# stays JSON-safe both when present and absent.
# ---------------------------------------------------------------------------


def _sample_payload(recommendation: RoutingRecommendation | None) -> InvocationPayload:
    return InvocationPayload(
        invocation_id="01HXYZABCDEFGH1JK2MN3PQRST",
        profile_id="reviewer-fixture",
        profile_friendly_name="Reviewer (fixture)",
        action="review",
        governance_context_text="compact governance context",
        governance_context_hash="deadbeef01234567",
        governance_context_available=True,
        router_confidence=None,
        glossary_observations=None,
        mode_of_work="task_execution",
        recommendation=recommendation,
    )


def test_to_dict_serializes_recommendation_and_is_json_safe() -> None:
    recommendation = RoutingRecommendation(
        task_type="code-review",
        objective="quality_first",
        override_mode="advisory",
        candidates=(
            RoutingCandidate(model_id="model-alpha", source="catalog", score=0.87, rationale="fixture"),
        ),
    )
    payload = _sample_payload(recommendation)

    data = payload.to_dict()
    parsed = json.loads(json.dumps(data))  # must not raise -- fully JSON-safe

    assert parsed["recommendation"]["task_type"] == "code-review"
    assert parsed["recommendation"]["candidates"][0]["model_id"] == "model-alpha"


def test_to_dict_recommendation_absent_serializes_to_none() -> None:
    payload = _sample_payload(None)

    data = payload.to_dict()
    json.dumps(data)  # must not raise

    assert data["recommendation"] is None


# ---------------------------------------------------------------------------
# T015 — rich render carries the same recommendation data as --json.
# ---------------------------------------------------------------------------


def test_render_rich_payload_includes_recommendation_line(capsys: pytest.CaptureFixture[str]) -> None:
    recommendation = RoutingRecommendation(
        task_type="code-review",
        objective="quality_first",
        override_mode="advisory",
        candidates=(
            RoutingCandidate(model_id="model-alpha", source="catalog", score=0.87, rationale="fixture pick"),
        ),
    )
    payload = _sample_payload(recommendation)

    _render_rich_payload(payload)

    captured = capsys.readouterr()
    assert "model-alpha" in captured.out
    assert "code-review" in captured.out
