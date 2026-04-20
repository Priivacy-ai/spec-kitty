"""Integration tests for ``spec-kitty charter bundle validate``.

Invokes the Typer sub-app directly via ``typer.testing.CliRunner``. The
sub-app is not yet registered into the main ``charter`` CLI — WP03 does
that — so these tests target ``charter_bundle.app`` via import.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import charter_bundle


runner = CliRunner()

# The three derived files mirror src/charter/sync.py :: _SYNC_OUTPUT_FILES.
_DERIVED = [
    ".kittify/charter/governance.yaml",
    ".kittify/charter/directives.yaml",
    ".kittify/charter/metadata.yaml",
]
_TRACKED = ".kittify/charter/charter.md"
_GITIGNORE_REQUIRED = sorted(_DERIVED)


def _git_init(repo_root: Path) -> None:
    subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=str(repo_root),
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(repo_root),
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(repo_root),
        check=True,
    )


def _write_compliant_bundle(repo_root: Path) -> None:
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text("# charter\n", encoding="utf-8")
    for rel in _DERIVED:
        (repo_root / rel).write_text("# derived\n", encoding="utf-8")
    gitignore = repo_root / ".gitignore"
    gitignore.write_text(
        "\n".join(_GITIGNORE_REQUIRED) + "\n", encoding="utf-8"
    )
    # Track charter.md.
    subprocess.run(
        ["git", "add", _TRACKED, ".gitignore"],
        cwd=str(repo_root),
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"],
        cwd=str(repo_root),
        check=True,
    )


@pytest.fixture
def compliant_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _git_init(tmp_path)
    _write_compliant_bundle(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def non_repo_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # A plain directory that is NOT inside any git repository.
    bare = tmp_path / "not-a-repo"
    bare.mkdir()
    monkeypatch.chdir(bare)
    # Disable any parent-directory git discovery.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    return bare


def _invoke_validate_json() -> CliRunner.Result:
    return runner.invoke(charter_bundle.app, ["validate", "--json"])


def test_validate_passes_on_compliant_bundle(compliant_repo: Path) -> None:
    result = _invoke_validate_json()
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["bundle_compliant"] is True
    assert payload["result"] == "success"
    assert payload["manifest_schema_version"] == "1.0.0"
    assert payload["tracked_files"]["missing"] == []
    assert payload["derived_files"]["missing"] == []
    assert payload["gitignore"]["missing_entries"] == []


def test_validate_reports_out_of_scope_files_as_warnings(
    compliant_repo: Path,
) -> None:
    # Drop a references.yaml and a context-state.json; both are out of scope.
    (compliant_repo / ".kittify" / "charter" / "references.yaml").write_text(
        "# references\n", encoding="utf-8"
    )
    (compliant_repo / ".kittify" / "charter" / "context-state.json").write_text(
        "{}\n", encoding="utf-8"
    )
    result = _invoke_validate_json()
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["bundle_compliant"] is True
    out_of_scope = payload["out_of_scope_files"]
    assert ".kittify/charter/references.yaml" in out_of_scope
    assert ".kittify/charter/context-state.json" in out_of_scope
    assert len(payload["warnings"]) >= 2


def test_validate_fails_on_missing_tracked_file(compliant_repo: Path) -> None:
    (compliant_repo / _TRACKED).unlink()
    result = _invoke_validate_json()
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["bundle_compliant"] is False
    assert _TRACKED in payload["tracked_files"]["missing"]


def test_validate_fails_on_missing_gitignore_entry(compliant_repo: Path) -> None:
    # Remove one required entry from .gitignore.
    gitignore_path = compliant_repo / ".gitignore"
    lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if line != ".kittify/charter/metadata.yaml"]
    gitignore_path.write_text("\n".join(kept) + "\n", encoding="utf-8")

    result = _invoke_validate_json()
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["bundle_compliant"] is False
    assert ".kittify/charter/metadata.yaml" in payload["gitignore"][
        "missing_entries"
    ]


def test_validate_exits_2_on_non_repo_path(non_repo_path: Path) -> None:
    result = runner.invoke(charter_bundle.app, ["validate", "--json"])
    assert result.exit_code == 2


def test_validate_fails_when_charter_md_is_untracked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reproduces cycle-1 Finding 1: charter.md exists but is not git-tracked.

    The contract treats ``tracked_files`` as a git-tracking assertion; a
    file that exists on disk but was never ``git add``ed must be surfaced
    as missing, and the bundle must be non-compliant.
    """
    _git_init(tmp_path)
    # Populate the charter bundle *without* ever staging charter.md.
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text("# charter\n", encoding="utf-8")
    for rel in _DERIVED:
        (tmp_path / rel).write_text("# derived\n", encoding="utf-8")
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(
        "\n".join(_GITIGNORE_REQUIRED) + "\n", encoding="utf-8"
    )
    # Commit .gitignore only, so charter.md is present but untracked.
    subprocess.run(
        ["git", "add", ".gitignore"], cwd=str(tmp_path), check=True
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"], cwd=str(tmp_path), check=True
    )
    monkeypatch.chdir(tmp_path)

    result = _invoke_validate_json()
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["bundle_compliant"] is False
    assert _TRACKED in payload["tracked_files"]["missing"], (
        "untracked charter.md must be surfaced as missing, not present"
    )
    assert _TRACKED not in payload["tracked_files"]["present"]


def test_validate_reports_arbitrary_undeclared_file_as_warning(
    compliant_repo: Path,
) -> None:
    """Reproduces cycle-1 Finding 2: arbitrary undeclared file surfaced.

    The contract requires every undeclared file under ``.kittify/charter/``
    to be enumerated as an informational warning, not just the two
    producer-specific cases (references.yaml, context-state.json).
    """
    custom = compliant_repo / ".kittify" / "charter" / "custom-notes.txt"
    custom.write_text("freeform operator notes\n", encoding="utf-8")

    result = _invoke_validate_json()
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    # The bundle itself is still compliant — undeclared files are warnings,
    # not failures.
    assert payload["bundle_compliant"] is True
    rel = ".kittify/charter/custom-notes.txt"
    assert rel in payload["out_of_scope_files"], (
        f"arbitrary undeclared file must appear in out_of_scope_files; "
        f"got {payload['out_of_scope_files']!r}"
    )
    # And a matching warning must have been emitted.
    assert any(rel in w for w in payload["warnings"]), (
        f"no warning message references {rel!r}; warnings={payload['warnings']!r}"
    )


def test_validate_json_shape_matches_contract(compliant_repo: Path) -> None:
    result = _invoke_validate_json()
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    # Required keys per contracts/bundle-validate-cli.contract.md.
    required_keys = {
        "result",
        "canonical_root",
        "manifest_schema_version",
        "bundle_compliant",
        "tracked_files",
        "derived_files",
        "gitignore",
        "out_of_scope_files",
        "warnings",
    }
    assert required_keys <= set(payload.keys())
    for section in ("tracked_files", "derived_files"):
        assert {"expected", "present", "missing"} <= set(payload[section].keys())
    assert {"expected_entries", "present_entries", "missing_entries"} <= set(
        payload["gitignore"].keys()
    )
