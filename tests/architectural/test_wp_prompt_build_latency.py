"""Latency regression gate for `_build_wp_prompt` (NFR-002).

Mission `wp-prompt-governance-payload-01KRR8HS` enforced a non-functional
requirement: *"the augmented `build_charter_context` MUST not regress the
perceived latency of the WP-prompt build … `_build_wp_prompt` end-to-end
runtime stays within 1.5× of the baseline measured before this mission."*

The mission shipped a character-count baseline but no wall-clock regression
gate. This file is that gate.

The threshold is intentionally generous — the goal is to catch a 10x slowdown
(e.g. an accidental N+1 doctrine fetch or a synchronous network call slipping
in), not to police small fluctuations. CI noise will not trip this.

Mission `wp-prompt-latency-flake-isolation-01KWWWAC` (closes #2032): the two
tests below used to take a **single cold** ``time.perf_counter()`` sample on
the parallel ``-n auto --dist loadfile`` arch-adversarial shard. Co-scheduled
CPU contention on that shard inflated the one measured sample past the budget
with no code regression (#2032's decisive evidence: a CHANGELOG-only diff
flipped PASSED→FAILED across two commits). The fix is **serial isolation**,
not a wider budget or a retry plugin: the two tests now carry the canonical
``@pytest.mark.timing`` marker (`pytest.ini:49`), are excluded from the
parallel arch-adversarial selectors via ``and not timing``
(`.github/workflows/ci-quality.yml`), and run ONLY in a new always-on serial
``-n0 -m timing`` CI step where no concurrent load can corrupt the sample.
"""

from __future__ import annotations

import subprocess
import textwrap
import time
from pathlib import Path
from typing import Any

import pytest

from runtime.next.prompt_builder import _build_wp_prompt
from tests.lane_test_utils import write_single_lane_manifest


pytestmark = [pytest.mark.architectural, pytest.mark.git_repo, pytest.mark.timing]


# Wall-clock budget for a single _build_wp_prompt invocation under a realistic
# fixture (one WP, single lane, minimal charter declaring resolver inputs).
#
# Serial isolation (mission wp-prompt-latency-flake-isolation-01KWWWAC, #2032)
# removed the concurrent-CPU-contention corruption at the root: the tests now
# run alone in a dedicated ``-n0 -m timing`` CI step, so the budget no longer
# needs to absorb co-scheduled-worker noise. What it still must absorb is the
# ~1.5s warm steady-state cost measured on a stock developer laptop (see
# ``_measure_warm_call`` below) plus a real multiple of headroom for a slower
# CI runner. NFR-001 pins that headroom at roughly 4x the warm baseline.
# Raised 8.0 -> 10.0 (pre-isolation) after a shared CI runner measured 8.50s
# with no code regression; that history no longer applies once the root
# cause (contention) is removed, so the budget is retightened here rather
# than carried forward as an ever-widening number (FR-003).
_LATENCY_BUDGET_SECONDS = 6.0


_CHARTER_MD = textwrap.dedent(
    """\
    # Perf Project Charter

    > Version: 1.0.0

    ## Purpose

    Minimal charter used by the WP-prompt latency regression gate.

    ## Technical Standards

    Python 3.11+, pytest, mypy.

    ## Terminology Canon

    - The canonical term for a unit of governed work is **Mission**.

    ## Code Review Checklist

    - The WP diff respects the agent profile's directive-references.
    - Terminology in code and docs aligns with the project glossary
      (DIRECTIVE_032 — Conceptual Alignment).

    ## Charter Resolution Hints

    ```yaml
    template_set: software-dev-default
    available_tools: [git, spec-kitty]
    ```
    """
)


_WP_MD = textwrap.dedent(
    """\
    ---
    work_package_id: WP01
    title: Perf gate fixture WP
    dependencies: []
    requirement_refs: [FR-001]
    subtasks: [T001]
    agent: claude
    agent_profile: python-pedro
    role: implementer
    authoritative_surface: src/perf/
    owned_files: [src/perf/]
    execution_mode: code_change
    history: []
    ---
    # WP01 — Perf gate fixture WP
    """
)


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, capture_output=True)
    for k, v in (("user.email", "perf@example.com"), ("user.name", "Perf"), ("commit.gpgsign", "false")):
        subprocess.run(["git", "config", k, v], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def perf_project(tmp_path: Path) -> tuple[Path, Path, str]:
    repo_root = tmp_path
    _git_init(repo_root)
    slug = "999-perf"
    feature_dir = repo_root / "kitty-specs" / slug
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "tasks" / "WP01.md").write_text(_WP_MD, encoding="utf-8")
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",))
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    (charter_dir / "charter.md").write_text(_CHARTER_MD, encoding="utf-8")
    return repo_root, feature_dir, slug


def _measure_warm_call(**kwargs: Any) -> tuple[str, float]:
    """Warm-up call + one warm wall-clock sample of ``_build_wp_prompt``.

    A single COLD sample conflates two costs: the one-time process/interpreter
    overhead (module imports, the charter's first-load "bootstrap" governance
    payload, which is measurably larger/slower than the compact payload every
    later call renders once that state is primed) and the steady-state cost
    the NFR actually wants to police. Discarding a warm-up call isolates the
    latter: measured on a stock developer laptop this drops the sample from
    ~2.0-2.6s (cold, bootstrap payload) to a stable ~1.5s (warm, steady state)
    across repeated calls.

    Wall-clock (`time.perf_counter`) stays the oracle, NOT CPU-time
    (`time.process_time`): `_build_wp_prompt` shells out via
    `subprocess.run` (git log, for the review action) and does blocking
    `Path.read_text` I/O, so a CPU-time oracle would miss a new synchronous
    network call or blocking I/O regression that doesn't burn CPU cycles.
    """
    _build_wp_prompt(**kwargs)  # warm-up: discarded, primes caches/state
    start = time.perf_counter()
    prompt = _build_wp_prompt(**kwargs)
    elapsed = time.perf_counter() - start
    return prompt, elapsed


def test_build_wp_prompt_implement_stays_under_latency_budget(
    perf_project: tuple[Path, Path, str],
) -> None:
    """`_build_wp_prompt(action='implement', ...)` MUST complete within the budget.

    Runs ONLY in the dedicated serial ``-n0 -m timing`` CI step (excluded from
    the parallel arch-adversarial shard via ``and not timing``) — no
    co-scheduled CPU contention can corrupt the sample there. If this fails on
    real hardware, investigate before bumping the budget — the budget is the
    gate, not the regression.
    """
    repo_root, feature_dir, slug = perf_project
    prompt, elapsed = _measure_warm_call(
        action="implement",
        feature_dir=feature_dir,
        mission_slug=slug,
        wp_id="WP01",
        agent="claude",
        repo_root=repo_root,
        mission_type="software-dev",
    )
    assert prompt, "prompt must be non-empty"
    assert elapsed < _LATENCY_BUDGET_SECONDS, (
        f"_build_wp_prompt(implement) took {elapsed:.2f}s (warm sample), "
        f"exceeding the {_LATENCY_BUDGET_SECONDS:.1f}s NFR-002 latency "
        "budget. Investigate before raising the budget — likely cause is a "
        "new synchronous network call, an N+1 doctrine walk, or unbounded "
        "charter section iteration."
    )


def test_build_wp_prompt_review_stays_under_latency_budget(
    perf_project: tuple[Path, Path, str],
) -> None:
    """Same budget for the review action."""
    repo_root, feature_dir, slug = perf_project
    prompt, elapsed = _measure_warm_call(
        action="review",
        feature_dir=feature_dir,
        mission_slug=slug,
        wp_id="WP01",
        agent="claude",
        repo_root=repo_root,
        mission_type="software-dev",
    )
    assert prompt, "prompt must be non-empty"
    assert elapsed < _LATENCY_BUDGET_SECONDS, (
        f"_build_wp_prompt(review) took {elapsed:.2f}s (warm sample), "
        f"exceeding the {_LATENCY_BUDGET_SECONDS:.1f}s NFR-002 latency budget."
    )
