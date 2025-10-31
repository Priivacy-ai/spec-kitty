from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest

from tests.utils import REPO_ROOT, run, run_tasks_cli, write_wp


@pytest.fixture()
def temp_repo(tmp_path: Path) -> Iterator[Path]:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    run(["git", "init"], cwd=repo_dir)
    run(["git", "config", "user.name", "Spec Kitty"], cwd=repo_dir)
    run(["git", "config", "user.email", "spec@example.com"], cwd=repo_dir)
    yield repo_dir


@pytest.fixture()
def feature_repo(temp_repo: Path) -> Path:
    feature_slug = "001-demo-feature"
    feature_dir = temp_repo / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks").mkdir(exist_ok=True)
    (feature_dir / "spec.md").write_text("Spec content", encoding="utf-8")
    (feature_dir / "plan.md").write_text("Plan content", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("- [x] Initial task", encoding="utf-8")
    (feature_dir / "quickstart.md").write_text("Quickstart", encoding="utf-8")
    (feature_dir / "data-model.md").write_text("Data model", encoding="utf-8")
    (feature_dir / "research.md").write_text("Research", encoding="utf-8")
    write_wp(temp_repo, feature_slug, "planned", "WP01")
    run(["git", "add", "."], cwd=temp_repo)
    run(["git", "commit", "-m", "Initial commit"], cwd=temp_repo)
    return temp_repo


@pytest.fixture()
def feature_slug() -> str:
    return "001-demo-feature"


@pytest.fixture()
def ensure_imports():
    # Import helper modules so tests can reference them directly.
    import task_helpers  # noqa: F401
    import acceptance_support  # noqa: F401
