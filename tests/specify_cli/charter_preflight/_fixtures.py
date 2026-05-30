"""Shared helpers for charter_preflight tests.

These helpers materialise a fake repo with charter / bundle / synthesis
state so each test can describe the *deviation* from a fresh repo rather
than rebuilding the whole layout.

Kept private to ``tests.specify_cli.charter_preflight`` — not part of
the production surface.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent


def init_git_repo(repo: Path) -> None:
    """Initialise a git repo with a single commit so ``git status`` works.

    The preflight runner shells out to ``git status --porcelain`` to detect
    uncommitted artifacts.  Without an actual git repo the call would
    succeed (porcelain output is empty when run outside a repo *and*
    return code 128) — we need a real repo so we can model both clean and
    dirty states.
    """
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    # Need at least one commit so HEAD exists.
    (repo / ".gitignore").write_text("# placeholder\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"],
        cwd=repo,
        check=True,
        env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@x", "PATH": "/usr/bin:/bin"},
    )


def seed_charter(repo: Path, body: str = "# Charter\n\nHello") -> tuple[Path, Path]:
    """Create ``.kittify/charter/charter.md`` and return ``(charter, metadata)``."""
    charter_dir = repo / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_path = charter_dir / "charter.md"
    metadata_path = charter_dir / "metadata.yaml"
    charter_path.write_text(body, encoding="utf-8")
    return charter_path, metadata_path


def write_metadata(metadata_path: Path, charter_path: Path, *, mismatched: bool = False) -> None:
    """Write ``metadata.yaml`` with a charter_hash matching (or not) the charter file."""
    from charter.hasher import hash_content  # noqa: PLC0415
    charter_hash = hash_content(charter_path.read_text(encoding="utf-8"))  # "sha256:<hex>"
    digest = charter_hash.split(":", 1)[1]
    if mismatched:
        digest = "0" * 64
    metadata_path.write_text(
        dedent(
            f"""\
            charter_hash: sha256:{digest}
            timestamp_utc: 2026-01-01T00:00:00+00:00
            """
        ),
        encoding="utf-8",
    )


def seed_bundle_files(repo: Path) -> None:
    """Create the three sibling bundle YAMLs that ``synced_bundle`` expects."""
    charter_dir = repo / ".kittify" / "charter"
    for name in ("governance.yaml", "directives.yaml", "references.yaml"):
        (charter_dir / name).write_text("schema_version: '1'\n", encoding="utf-8")


def seed_manifest(
    repo: Path,
    *,
    built_in_only: bool,
    created_at: str = "2099-01-01T00:00:00+00:00",
) -> Path:
    """Create ``synthesis-manifest.yaml`` with ``built_in_only`` set as desired."""
    manifest_path = repo / ".kittify" / "charter" / "synthesis-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        dedent(
            f"""\
            schema_version: '2'
            mission_id: null
            created_at: '{created_at}'
            run_id: 01JTESTRUNIDXXXXXXXXXXXXXX
            adapter_id: test
            adapter_version: '0.0.0'
            synthesizer_version: '0.0.0'
            manifest_hash: {"a" * 64}
            artifacts: []
            built_in_only: {str(built_in_only).lower()}
            """
        ),
        encoding="utf-8",
    )
    return manifest_path


def seed_graph(repo: Path) -> Path:
    """Create ``.kittify/doctrine/graph.yaml`` (a minimal valid graph)."""
    graph_path = repo / ".kittify" / "doctrine" / "graph.yaml"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text("schema_version: '1.0'\nnodes: []\nedges: []\n", encoding="utf-8")
    return graph_path


def make_fresh_repo(repo: Path) -> None:
    """Materialise a fully-fresh repo: charter + bundle + synthesised graph."""
    init_git_repo(repo)
    charter_path, metadata_path = seed_charter(repo)
    write_metadata(metadata_path, charter_path)
    seed_bundle_files(repo)
    seed_manifest(repo, built_in_only=False)
    seed_graph(repo)
