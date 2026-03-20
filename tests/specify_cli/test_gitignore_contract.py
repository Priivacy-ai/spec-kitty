"""Integration tests: gitignore policy stays aligned with the state contract."""

from pathlib import Path


def test_repo_gitignore_covers_local_runtime():
    """Every LOCAL_RUNTIME project surface has a matching .gitignore entry."""
    from specify_cli.state_contract import (
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
    from specify_cli.state_contract import get_runtime_gitignore_entries

    contract_entries = get_runtime_gitignore_entries()
    assert set(RUNTIME_PROTECTED_ENTRIES) == set(contract_entries), (
        f"Drift detected. Manager has {set(RUNTIME_PROTECTED_ENTRIES) - set(contract_entries)} extra, "
        f"contract has {set(contract_entries) - set(RUNTIME_PROTECTED_ENTRIES)} extra"
    )


def test_contract_runtime_entries_complete():
    """Contract runtime entries are non-empty and contain known patterns."""
    from specify_cli.state_contract import get_runtime_gitignore_entries

    entries = get_runtime_gitignore_entries()
    assert len(entries) >= 4, f"Expected at least 4 runtime entries, got {len(entries)}"  # noqa: PLR2004
    assert ".kittify/.dashboard" in entries
    assert ".kittify/merge-state.json" in entries
    assert ".kittify/runtime/" in entries
    assert ".kittify/events/" in entries
    assert ".kittify/dossiers/" in entries
