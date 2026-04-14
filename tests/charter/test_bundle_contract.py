"""End-to-end bundle contract test: manifest vs on-disk reality.

Builds a fresh tmp-repo fixture with only ``charter.md`` committed,
runs ``ensure_charter_bundle_fresh`` once, then asserts:

* Every ``CANONICAL_MANIFEST.tracked_files`` entry exists on disk and is
  tracked in git (via ``git ls-files``).
* Every ``CANONICAL_MANIFEST.derived_files`` entry exists after the
  chokepoint ran (it materialized them via ``sync()``).
* Every ``CANONICAL_MANIFEST.gitignore_required_entries`` entry is on
  its own line in the project's ``.gitignore``.
* ``SyncResult.canonical_root`` equals the fixture repo root (the
  chokepoint was invoked at the main-checkout level).

This test is the manifest-vs-disk chokepoint contract check for v1.0.0.
See ``kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/chokepoint.contract.md``.
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

- Chokepoint routes every reader.
- Derivatives regenerate on demand.
"""


def _init_fixture(repo_root: Path) -> Path:
    """Initialize a git repo with charter.md tracked; return the root."""
    subprocess.run(["git", "init", "--quiet", str(repo_root)], check=True)
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email", "bundle@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.name", "Bundle Test"],
        check=True,
    )

    (repo_root / ".gitignore").write_text(_GITIGNORE_BODY, encoding="utf-8")
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    (charter_dir / "charter.md").write_text(_CHARTER_BODY, encoding="utf-8")

    # Stage + commit charter.md + .gitignore (the only tracked state).
    subprocess.run(
        ["git", "-C", str(repo_root), "add", ".gitignore", ".kittify/charter/charter.md"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-q", "-m", "fixture: charter.md"],
        check=True,
    )
    return repo_root


def _git_ls_files(repo_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def test_manifest_vs_on_disk_contract(tmp_path: Path) -> None:
    """After a cold chokepoint run on a freshly-seeded repo, the manifest
    must match reality: tracked files tracked in git, derivatives on disk,
    gitignore covers the derivatives, and canonical_root is the repo root.
    """
    from charter.bundle import CANONICAL_MANIFEST
    from charter.resolution import resolve_canonical_repo_root
    from charter.sync import ensure_charter_bundle_fresh

    repo_root = _init_fixture(tmp_path).resolve()
    resolve_canonical_repo_root.cache_clear()

    sync_result = ensure_charter_bundle_fresh(repo_root)
    assert sync_result is not None, "Chokepoint returned None despite charter.md present"
    assert sync_result.canonical_root == repo_root, (
        f"canonical_root mismatch: {sync_result.canonical_root} != {repo_root}"
    )

    # Tracked files exist and are git-tracked.
    tracked_in_git = _git_ls_files(repo_root)
    for rel in CANONICAL_MANIFEST.tracked_files:
        abs_path = repo_root / rel
        assert abs_path.exists(), f"tracked_file missing on disk: {rel}"
        assert str(rel).replace("\\", "/") in tracked_in_git, (
            f"tracked_file not in git: {rel}"
        )

    # Derived files exist post-chokepoint.
    for rel in CANONICAL_MANIFEST.derived_files:
        abs_path = repo_root / rel
        assert abs_path.exists(), (
            f"derived_file missing after chokepoint: {rel} "
            f"(files_written={sync_result.files_written}, error={sync_result.error})"
        )

    # gitignore_required_entries present as own-line entries.
    gitignore_lines = {
        line.strip()
        for line in (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    for entry in CANONICAL_MANIFEST.gitignore_required_entries:
        assert entry in gitignore_lines, (
            f"gitignore entry missing: {entry} (gitignore has: {gitignore_lines})"
        )


def test_derived_files_are_not_git_tracked(tmp_path: Path) -> None:
    """Per the manifest, derivatives are gitignored and should NOT appear
    in ``git ls-files`` after the chokepoint runs.
    """
    from charter.bundle import CANONICAL_MANIFEST
    from charter.resolution import resolve_canonical_repo_root
    from charter.sync import ensure_charter_bundle_fresh

    repo_root = _init_fixture(tmp_path).resolve()
    resolve_canonical_repo_root.cache_clear()

    ensure_charter_bundle_fresh(repo_root)

    tracked_in_git = _git_ls_files(repo_root)
    for rel in CANONICAL_MANIFEST.derived_files:
        rel_str = str(rel).replace("\\", "/")
        assert rel_str not in tracked_in_git, (
            f"derived_file unexpectedly tracked in git: {rel_str}"
        )


def test_second_chokepoint_call_is_noop(tmp_path: Path) -> None:
    """Freshness guard: after a first chokepoint invocation produces the
    bundle, a second call must detect the bundle is complete and not stale,
    and return ``synced=False``.
    """
    from charter.resolution import resolve_canonical_repo_root
    from charter.sync import ensure_charter_bundle_fresh

    repo_root = _init_fixture(tmp_path).resolve()
    resolve_canonical_repo_root.cache_clear()

    first = ensure_charter_bundle_fresh(repo_root)
    assert first is not None
    # First call either synced (if previously empty) or was already fresh —
    # it depends on whether the extractor produced anything. Either way the
    # derived files exist after first call.

    second = ensure_charter_bundle_fresh(repo_root)
    assert second is not None
    assert second.synced is False, "Second chokepoint call must be a no-op on a fresh bundle"
    assert second.canonical_root == repo_root
