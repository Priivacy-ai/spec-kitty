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
"""

from __future__ import annotations

import subprocess
import textwrap
import time
from pathlib import Path

import pytest

from runtime.next.prompt_builder import _build_wp_prompt
from tests.lane_test_utils import write_single_lane_manifest


pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]


# Wall-clock budget for a single _build_wp_prompt invocation under a realistic
# fixture (one WP, single lane, minimal charter declaring resolver inputs).
# Baseline measured on a stock developer laptop is ~0.6–1.5s; the budget
# tolerates roughly 7–15x that to absorb CI runner variance while still catching
# a regression that pulls in a synchronous network call or an N+1 walk.
#
# This is a hard-threshold budget gate, NOT a nondeterministic-race flake, so the
# correct lever for CI variance is a wider budget — not a retry plugin
# (pytest-rerunfailures / flaky), which would mask a genuine latency regression
# that is merely "sometimes under the line". A real regression adds seconds
# *consistently* and still trips the 10s gate. Raised 8.0 → 10.0 after a shared
# CI runner measured 8.50s (no code regression: the path was unchanged).
_LATENCY_BUDGET_SECONDS = 10.0


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


def test_build_wp_prompt_implement_stays_under_latency_budget(
    perf_project: tuple[Path, Path, str],
) -> None:
    """`_build_wp_prompt(action='implement', ...)` MUST complete within the budget.

    The budget tolerates ~6x the baseline to absorb CI variance while still
    catching a regression that introduces a synchronous network call or an
    N+1 doctrine walk. If this fails on real hardware, investigate before
    bumping the budget — the budget is the gate, not the regression.
    """
    repo_root, feature_dir, slug = perf_project
    start = time.perf_counter()
    prompt = _build_wp_prompt(
        action="implement",
        feature_dir=feature_dir,
        mission_slug=slug,
        wp_id="WP01",
        agent="claude",
        repo_root=repo_root,
        mission_type="software-dev",
    )
    elapsed = time.perf_counter() - start
    assert prompt, "prompt must be non-empty"
    assert elapsed < _LATENCY_BUDGET_SECONDS, (
        f"_build_wp_prompt(implement) took {elapsed:.2f}s, exceeding the "
        f"{_LATENCY_BUDGET_SECONDS:.1f}s NFR-002 latency budget. Investigate "
        "before raising the budget — likely cause is a new synchronous "
        "network call, an N+1 doctrine walk, or unbounded charter section "
        "iteration."
    )


def test_build_wp_prompt_review_stays_under_latency_budget(
    perf_project: tuple[Path, Path, str],
) -> None:
    """Same budget for the review action."""
    repo_root, feature_dir, slug = perf_project
    start = time.perf_counter()
    prompt = _build_wp_prompt(
        action="review",
        feature_dir=feature_dir,
        mission_slug=slug,
        wp_id="WP01",
        agent="claude",
        repo_root=repo_root,
        mission_type="software-dev",
    )
    elapsed = time.perf_counter() - start
    assert prompt, "prompt must be non-empty"
    assert elapsed < _LATENCY_BUDGET_SECONDS, (
        f"_build_wp_prompt(review) took {elapsed:.2f}s, exceeding the "
        f"{_LATENCY_BUDGET_SECONDS:.1f}s NFR-002 latency budget."
    )
