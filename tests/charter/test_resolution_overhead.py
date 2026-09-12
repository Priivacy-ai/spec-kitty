"""NFR-003: resolver overhead budget (<5 ms warm p95, <=1 git invocation/cold call)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from charter.resolution import resolve_canonical_repo_root

# Marked for mutmut sandbox skip — see ADR 2026-04-20-1.
# Reason: trampoline bug: subprocess
pytestmark = [pytest.mark.non_sandbox, pytest.mark.git_repo]


@pytest.fixture
def tmp_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repo = tmp_path_factory.mktemp("resolver_perf_repo")
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True, capture_output=True)
    resolve_canonical_repo_root.cache_clear()
    return repo


def test_warm_resolver_makes_zero_git_invocations(tmp_repo: Path) -> None:
    resolve_canonical_repo_root(tmp_repo)  # Prime cache.
    with patch("kernel.git_topology.subprocess.run") as spy:
        for _ in range(100):
            resolve_canonical_repo_root(tmp_repo)
    assert spy.call_count == 0, (
        f"Warm resolver invoked subprocess.run {spy.call_count} times; expected 0."
    )


def test_cold_resolver_makes_exactly_one_git_invocation(tmp_repo: Path) -> None:
    resolve_canonical_repo_root.cache_clear()
    real_run = subprocess.run
    spy = MagicMock(side_effect=lambda *a, **kw: real_run(*a, **kw))
    with patch("kernel.git_topology.subprocess.run", spy):
        resolve_canonical_repo_root(tmp_repo)
    assert spy.call_count == 1, (
        f"Cold resolver invoked subprocess.run {spy.call_count} times; expected 1."
    )
