"""FR-009 smoke test: fresh clone + deleted derivatives -> chokepoint
auto-refreshes without any explicit ``spec-kitty charter sync`` call.

Simulates the exact scenario a new contributor hits: clone the repo,
``charter.md`` is tracked, derivatives are gitignored and therefore not
on disk. Any FR-004 reader invocation must trigger the chokepoint and
auto-materialize the derivatives.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


_GITIGNORE_BODY = """\
.kittify/charter/directives.yaml
.kittify/charter/governance.yaml
.kittify/charter/metadata.yaml
"""

_CHARTER_BODY = """\
# Project Charter

## Policy Summary

- Baseline assumptions are explicit.
- Derivatives regenerate automatically.
"""


def _fresh_clone_fixture(repo_root: Path) -> Path:
    """Build a 'fresh clone' fixture:

    * git repo with charter.md tracked,
    * derivatives NOT on disk (matching .gitignore behavior).
    """
    subprocess.run(["git", "init", "--quiet", str(repo_root)], check=True)
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email", "fresh@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.name", "Fresh Clone"],
        check=True,
    )

    (repo_root / ".gitignore").write_text(_GITIGNORE_BODY, encoding="utf-8")
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    (charter_dir / "charter.md").write_text(_CHARTER_BODY, encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo_root), "add", ".gitignore", ".kittify/charter/charter.md"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-q", "-m", "fresh-clone fixture"],
        check=True,
    )

    # Ensure derivatives are NOT on disk.
    for name in ("governance.yaml", "directives.yaml", "metadata.yaml"):
        derived = charter_dir / name
        if derived.exists():
            derived.unlink()

    return repo_root


def _assert_derivatives_exist(repo_root: Path) -> None:
    charter_dir = repo_root / ".kittify" / "charter"
    for name in ("governance.yaml", "directives.yaml", "metadata.yaml"):
        derived = charter_dir / name
        assert derived.exists(), f"derivative missing after reader invocation: {name}"


def _clear_resolver_cache() -> None:
    from charter.resolution import resolve_canonical_repo_root

    resolve_canonical_repo_root.cache_clear()


def test_build_charter_context_auto_syncs_on_fresh_clone(tmp_path: Path) -> None:
    """FR-004 reader: ``build_charter_context`` auto-materializes derivatives."""
    from charter.context import build_charter_context

    repo_root = _fresh_clone_fixture(tmp_path).resolve()
    _clear_resolver_cache()

    result = build_charter_context(repo_root, action="specify")
    assert result is not None
    assert result.action == "specify"
    _assert_derivatives_exist(repo_root)


def test_resolve_project_charter_path_auto_syncs_on_fresh_clone(tmp_path: Path) -> None:
    """FR-004 reader: dashboard ``resolve_project_charter_path`` goes through chokepoint."""
    from specify_cli.dashboard.charter_path import resolve_project_charter_path

    repo_root = _fresh_clone_fixture(tmp_path).resolve()
    _clear_resolver_cache()

    charter_path = resolve_project_charter_path(repo_root)
    assert charter_path is not None, "charter_path resolved to None despite charter.md present"
    assert charter_path.exists()
    # Dashboard reader invocation should have materialized derivatives too.
    _assert_derivatives_exist(repo_root)


def test_load_governance_config_auto_syncs_on_fresh_clone(tmp_path: Path) -> None:
    """FR-004 reader: chokepoint-fronted loader regenerates derivatives."""
    from charter.sync import load_governance_config

    repo_root = _fresh_clone_fixture(tmp_path).resolve()
    _clear_resolver_cache()

    # Before invoking: derivatives absent.
    assert not (repo_root / ".kittify" / "charter" / "governance.yaml").exists()

    governance = load_governance_config(repo_root)
    assert governance is not None
    _assert_derivatives_exist(repo_root)


def test_charter_status_cli_auto_syncs_on_fresh_clone(tmp_path: Path) -> None:
    """FR-004 reader: ``spec-kitty charter status`` handler flips through chokepoint."""
    import os

    from typer.testing import CliRunner

    from specify_cli.cli.commands.charter import app as charter_app

    repo_root = _fresh_clone_fixture(tmp_path).resolve()
    _clear_resolver_cache()

    runner = CliRunner()
    cwd = os.getcwd()
    os.chdir(repo_root)
    try:
        result = runner.invoke(charter_app, ["status", "--json"])
    finally:
        os.chdir(cwd)

    assert result.exit_code == 0, f"charter status failed: {result.output!r}"
    _assert_derivatives_exist(repo_root)


def test_no_importerror_or_repo_errors_on_fresh_clone(tmp_path: Path) -> None:
    """Sanity check: readers do not raise ``NotInsideRepositoryError`` on a
    well-formed fresh clone, and we do not hit import-time breakage.
    """
    from charter.context import build_charter_context
    from charter.resolution import (
        GitCommonDirUnavailableError,
        NotInsideRepositoryError,
    )

    repo_root = _fresh_clone_fixture(tmp_path).resolve()
    _clear_resolver_cache()

    try:
        build_charter_context(repo_root, action="plan")
    except (NotInsideRepositoryError, GitCommonDirUnavailableError) as exc:
        pytest.fail(f"Unexpected resolver error on fresh clone: {exc}")
