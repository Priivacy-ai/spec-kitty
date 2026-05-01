"""Performance / NFR enforcement tests for the custom-mission loader.

Two tests guard the NFR budgets the WP07 charter committed to:

* :func:`test_load_p95_under_250ms` — NFR-001. 50 invocations of
  :func:`validate_custom_mission` against the ERP fixture; the p95
  latency must come in under 250 ms locally (375 ms on CI runners,
  which carry more noise).
* :func:`test_erp_load_under_2s` — NFR-004 sub-portion. Drives the
  public ``run_custom_mission`` surface with the runtime bridge mocked
  out so the test isolates the loader+CLI start phase from the engine.
  A 2-second budget is well inside the 10-second walk envelope WP06's
  integration suite already exercises end-to-end. Duplicating the full
  walk here would be redundant and brittle.

Run locally::

    UV_PYTHON=3.13.9 uv run --no-sync pytest tests/perf/test_loader_perf.py -q

These tests live outside the per-module ``fast`` marker filter so they
are explicitly opt-in. They are NOT wired into the default CI pytest
selectors -- the per-package coverage gate in ``ci-quality.yml`` is the
canonical regression catch -- but they remain runnable in any developer
shell to reproduce the NFR budgets on demand.
"""

from __future__ import annotations

import os
import shutil
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from specify_cli.mission_loader.command import run_custom_mission
from specify_cli.mission_loader.registry import get_runtime_contract_registry
from specify_cli.mission_loader.validator import validate_custom_mission
from specify_cli.next._internal_runtime.discovery import DiscoveryContext
from specify_cli.next._internal_runtime.engine import MissionRunRef


_FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "missions"


def _setup_erp_project(tmp_path: Path) -> Path:
    """Copy the ERP fixture into a tmp ``.kittify/missions/erp-integration``.

    Mirrors ``tests/integration/test_custom_mission_runtime_walk.py::_setup_project``
    so the perf path exercises the same discovery shape integration tests
    use. Returns the project root.
    """
    src = _FIXTURES_ROOT / "erp-integration" / "mission.yaml"
    if not src.is_file():
        raise FileNotFoundError(f"ERP fixture missing: {src}")
    project_missions_dir = tmp_path / ".kittify" / "missions" / "erp-integration"
    project_missions_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, project_missions_dir / "mission.yaml")
    return tmp_path


def _isolated_context(repo_root: Path) -> DiscoveryContext:
    """Build a DiscoveryContext that ignores the user's real ``~/.kittify``."""
    fake_home = repo_root / ".fake-home"
    fake_home.mkdir(exist_ok=True)
    return DiscoveryContext(
        project_dir=repo_root,
        user_home=fake_home,
        builtin_roots=[],
    )


@pytest.fixture(autouse=True)
def _reset_registry() -> Iterator[None]:
    """Clear the singleton runtime-contract registry between tests."""
    get_runtime_contract_registry().clear()
    yield
    get_runtime_contract_registry().clear()


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip discovery env vars so tests cannot pull in side-channel paths."""
    monkeypatch.delenv("SPEC_KITTY_MISSION_PATHS", raising=False)


# ---------------------------------------------------------------------------
# T035 — Loader p95 < 250 ms (NFR-001)
# ---------------------------------------------------------------------------


def test_load_p95_under_250ms(tmp_path: Path) -> None:
    """NFR-001: 50 invocations of validate_custom_mission, p95 < 250 ms.

    The slack on CI (1.5x) absorbs runner-noise variance; the local
    threshold is the contract value documented in the spec.
    """
    repo_root = _setup_erp_project(tmp_path)
    ctx = _isolated_context(repo_root)

    # Warm-up: the first call pays one-time import + Pydantic schema
    # initialization costs. Excluding it from the sample makes p95
    # representative of steady-state operator usage.
    warmup = validate_custom_mission("erp-integration", ctx)
    assert warmup.ok, warmup.errors

    times: list[float] = []
    for _ in range(50):
        t0 = time.perf_counter()
        report = validate_custom_mission("erp-integration", ctx)
        times.append(time.perf_counter() - t0)
        assert report.ok, report.errors

    p95 = sorted(times)[int(0.95 * len(times))]
    threshold = 0.25 if os.environ.get("CI") != "true" else 0.375
    assert p95 < threshold, f"p95={p95 * 1000:.1f}ms exceeds {threshold * 1000:.0f}ms (samples: min={min(times) * 1000:.1f}ms, max={max(times) * 1000:.1f}ms)"


# ---------------------------------------------------------------------------
# T036 — ERP load wall-clock budget (NFR-004 sub-portion)
# ---------------------------------------------------------------------------


def test_erp_load_under_2s(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """NFR-004 sub-portion: ``run_custom_mission`` start phase < 2 s.

    The full ERP walk (discovery -> validate -> synthesize -> register ->
    runtime engine handoff -> 7 steps -> retrospective marker) carries a
    10-second NFR-004 envelope, asserted end-to-end by WP06's
    ``test_erp_full_walk``. Re-running that flow inside a perf test would
    duplicate ~150 lines of scaffolding and double-count the same
    invariant.

    Instead this test isolates the loader/CLI start phase only -- discovery,
    validation, contract synthesis, registry registration, and the runtime
    bridge handoff. The runtime bridge is mocked so no real run state is
    written; that path is already covered by the integration suite. The
    2-second budget here proves the loader portion of the 10-second walk
    is well below 1/5 of the total envelope, leaving headroom for the
    engine-driven steps.
    """
    repo_root = _setup_erp_project(tmp_path)
    fake_run_dir = tmp_path / "runs" / "fake-run-id"
    fake_run_dir.mkdir(parents=True)

    def _fake_get_or_start_run(*, mission_slug: str, repo_root: Path, mission_type: str) -> MissionRunRef:
        return MissionRunRef(
            run_id="fake-run-id",
            run_dir=str(fake_run_dir),
            mission_key=mission_type,
        )

    from specify_cli.next import runtime_bridge

    monkeypatch.setattr(runtime_bridge, "get_or_start_run", _fake_get_or_start_run)

    t0 = time.perf_counter()
    result = run_custom_mission(
        "erp-integration",
        "erp-walk",
        repo_root,
        discovery_context=_isolated_context(repo_root),
    )
    elapsed = time.perf_counter() - t0

    assert result.exit_code == 0, result.envelope
    # Local budget: 2s. CI gets 3x slack because cold-start + io variance.
    threshold = 2.0 if os.environ.get("CI") != "true" else 6.0
    assert elapsed < threshold, f"run_custom_mission start phase took {elapsed:.2f}s (threshold: {threshold:.2f}s)"
