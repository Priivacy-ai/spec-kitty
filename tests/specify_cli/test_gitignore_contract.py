"""Integration tests: gitignore policy stays aligned with the state contract."""

import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


def test_repo_gitignore_covers_local_runtime():
    """Every LOCAL_RUNTIME project surface has a matching .gitignore entry."""
    from specify_cli.state.contract import (
        STATE_SURFACES,
        AuthorityClass,
        GitClass,
        StateRoot,
    )

    repo_root = Path(__file__).resolve().parents[2]  # up to repo root
    gitignore_path = repo_root / ".gitignore"
    gitignore_content = gitignore_path.read_text()
    gitignore_lines = [
        line.strip() for line in gitignore_content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    # All project-rooted surfaces that must be ignored
    local_runtime_project = [
        s for s in STATE_SURFACES
        if s.root == StateRoot.PROJECT
        and (s.authority == AuthorityClass.LOCAL_RUNTIME
             or s.git_class == GitClass.IGNORED)
    ]

    assert local_runtime_project, "Expected at least one LOCAL_RUNTIME project surface"

    missing = []
    for surface in local_runtime_project:
        pattern = surface.path_pattern
        # Check if pattern or a parent directory pattern is in gitignore
        if not any(
            pattern.startswith(line.rstrip("/"))
            or line.rstrip("/").startswith(pattern.rstrip("/"))
            or pattern in line
            for line in gitignore_lines
        ):
            missing.append(f"{surface.name}: {pattern}")

    assert not missing, f"Local runtime surfaces not in .gitignore: {missing}"


def test_runtime_entries_match_contract():
    """GitignoreManager entries are derived from state contract."""
    from specify_cli.gitignore_manager import RUNTIME_PROTECTED_ENTRIES
    from specify_cli.state.contract import get_runtime_gitignore_entries

    contract_entries = get_runtime_gitignore_entries()
    assert set(RUNTIME_PROTECTED_ENTRIES) == set(contract_entries), (
        f"Drift detected. Manager has {set(RUNTIME_PROTECTED_ENTRIES) - set(contract_entries)} extra, "
        f"contract has {set(contract_entries) - set(RUNTIME_PROTECTED_ENTRIES)} extra"
    )


def test_contract_runtime_entries_complete():
    """Contract runtime entries are non-empty and contain known patterns."""
    from specify_cli.state.contract import get_runtime_gitignore_entries

    entries = get_runtime_gitignore_entries()
    assert len(entries) >= 4, f"Expected at least 4 runtime entries, got {len(entries)}"  # noqa: PLR2004
    assert ".kittify/.dashboard" in entries
    assert ".kittify/merge-state.json" in entries
    assert ".kittify/encoding-provenance/" in entries
    assert ".kittify/runtime/" in entries
    assert ".kittify/events/" in entries
    assert ".kittify/dossiers/" in entries


def test_gitignore_manager_protects_encoding_provenance(tmp_path: Path) -> None:
    """Fresh init protection hides the global encoding provenance log."""
    from specify_cli.gitignore_manager import GitignoreManager

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    result = GitignoreManager(tmp_path).protect_all_agents()

    assert result.success
    assert _is_ignored(tmp_path, ".kittify/encoding-provenance/global.jsonl")


def test_contract_runtime_entries_include_skill_projection_surfaces():
    """#2412: the shared skill projection root and the per-machine install
    ledger are runtime-ignored contract entries, so fresh init gitignores
    both (machine-local absolute symlinks + per-machine manifest state)."""
    from specify_cli.state.contract import get_runtime_gitignore_entries

    entries = get_runtime_gitignore_entries()
    assert ".agents/skills/" in entries
    assert ".kittify/skills-manifest.json" in entries


def test_gitignore_manager_protects_skill_projection(tmp_path: Path) -> None:
    """Fresh init protection hides a projected skill symlink and the manifest."""
    from specify_cli.gitignore_manager import GitignoreManager

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    result = GitignoreManager(tmp_path).protect_all_agents()

    assert result.success
    assert _is_ignored(tmp_path, ".agents/skills/spec-kitty.implement/SKILL.md")
    assert _is_ignored(tmp_path, ".kittify/skills-manifest.json")


def test_contract_runtime_entries_include_ops_index():
    """The Op-index performance cache is a runtime-ignored contract entry."""
    from specify_cli.state.contract import get_runtime_gitignore_entries

    entries = get_runtime_gitignore_entries()
    # File-level entry -- NOT collapsed to kitty-ops/, because the durable
    # per-Op records under kitty-ops/ are tracked.
    assert "kitty-ops/ops-index.jsonl" in entries
    assert "kitty-ops/" not in entries


def test_gitignore_manager_protects_ops_index(tmp_path: Path) -> None:
    """Fresh init protection hides the Op-index cache but not durable records."""
    from specify_cli.gitignore_manager import GitignoreManager

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    result = GitignoreManager(tmp_path).protect_all_agents()

    assert result.success
    assert _is_ignored(tmp_path, "kitty-ops/ops-index.jsonl")
    # Durable per-Op audit records stay trackable.
    assert not _is_ignored(tmp_path, "kitty-ops/01HXYZ.jsonl")


def test_research_evidence_logs_are_trackable():
    """Investigation evidence logs under research/ are not masked by *.log."""

    repo_root = Path(__file__).resolve().parents[2]

    evidence = "kitty-specs/example-mission/research/evidence.log"
    non_research = "kitty-specs/example-mission/runtime.log"
    generic = "tmp/dev.log"

    assert not _is_ignored(repo_root, evidence)
    assert _is_ignored(repo_root, non_research)
    assert _is_ignored(repo_root, generic)


def test_charter_synthesis_artifacts_are_trackable():
    """KD-2 charter synthesis artifacts must be commit-ready."""

    repo_root = Path(__file__).resolve().parents[2]

    assert not _is_ignored(repo_root, ".kittify/charter/synthesis-manifest.yaml")
    assert not _is_ignored(repo_root, ".kittify/charter/provenance/directive-demo.yaml")
    assert not _is_ignored(repo_root, ".kittify/doctrine/graph.yaml")


def _is_ignored(repo_root: Path, path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", path],
        cwd=repo_root,
        check=False,
    )
    return result.returncode == 0


def test_derived_views_dir_is_gitignored():
    """#2369: .kittify/derived/ (regenerable materialize output) must be in the
    runtime gitignore set so `spec-kitty materialize` never dirties the tree /
    fails accept's git_dirty check. Registry-driven — the derived_mission_views
    StateSurface (root=PROJECT, git_class=IGNORED) collapses to this entry."""
    from specify_cli.state.contract import get_runtime_gitignore_entries

    entries = get_runtime_gitignore_entries()
    assert ".kittify/derived/" in entries, entries
