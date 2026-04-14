"""Tests for m_3_2_3_unified_bundle migration (WP04).

Covers the FR-013 fixture matrix (5 cases) plus:

* JSON-report schema validation against
  ``kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/migration-report.schema.json``
* No-worktree-touch invariant (C-011 carve-out for
  ``src/specify_cli/core/worktree.py`` plus the operational rule that the
  migration never walks a worktree).
* No-``.gitignore``-touch invariant (D-12 / v1.0.0 manifest already matches
  current ``.gitignore``).
* No-``.kittify/memory``-and-``.kittify/AGENTS.md``-symlink touch
  invariant (C-011 documented-intentional sharing).
* NFR-006 wall-time bound (``duration_ms <= 2000`` on the fixture).

All fixtures are built as ephemeral git repositories so the canonical-root
resolver in ``charter.resolution`` can compute the correct root via
``git rev-parse --git-common-dir``. Fixtures intentionally do NOT mock
``charter.sync`` — the tests invoke the real chokepoint to catch wiring
regressions.

Ref: kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/tasks/WP04-migration-unified-bundle.md
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# A realistic (but small) charter that the extractor can parse into the
# three v1.0.0 derivatives without heavy CI cost.
_CHARTER_MD = """# Project Charter

## Mission
Test fixture for the unified bundle migration.

## Values
- Clarity
- Safety

## Governance

### Principles
- Principle A: Keep migrations idempotent.

### Standards
- Python 3.11+

### Anti-patterns
- Fallback handlers.

## Directives

### Current Directives
- D001: Exercise the chokepoint end-to-end in tests.

## Metadata
- Project: spec-kitty
"""

_CONTRACTS_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "kitty-specs"
    / "unified-charter-bundle-chokepoint-01KP5Q2G"
    / "contracts"
    / "migration-report.schema.json"
)


@pytest.fixture
def migration() -> Any:
    """Return a fresh migration instance (registration is side-effect-safe)."""
    from specify_cli.upgrade.migrations.m_3_2_3_unified_bundle import (
        UnifiedBundleMigration,
    )

    return UnifiedBundleMigration()


def _init_git_repo(root: Path) -> None:
    """Initialise a git repo with a single commit so ``rev-parse`` works."""
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit",
         "--allow-empty", "-m", "init"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _write_charter(root: Path, body: str = _CHARTER_MD) -> Path:
    charter_dir = root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_md = charter_dir / "charter.md"
    charter_md.write_text(body, encoding="utf-8")
    return charter_md


def _sync_charter(root: Path) -> None:
    """Pre-populate derivatives by invoking the real sync pipeline."""
    from charter.sync import sync

    charter_dir = root / ".kittify" / "charter"
    sync(charter_dir / "charter.md", charter_dir, force=True)


def _clear_resolver_cache() -> None:
    """Reset the ``resolve_canonical_repo_root`` LRU between fixtures."""
    from charter.resolution import resolve_canonical_repo_root

    resolve_canonical_repo_root.cache_clear()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Fixture matrix builders
# ---------------------------------------------------------------------------


@pytest.fixture
def fixture_a_with_full_derivatives(tmp_path: Path) -> Path:
    """(a) charter.md + all three derivatives present, hashes matching."""
    _init_git_repo(tmp_path)
    _write_charter(tmp_path)
    _sync_charter(tmp_path)
    _clear_resolver_cache()
    return tmp_path


@pytest.fixture
def fixture_b_no_derivatives(tmp_path: Path) -> Path:
    """(b) charter.md present, NO derivatives on disk."""
    _init_git_repo(tmp_path)
    _write_charter(tmp_path)
    _clear_resolver_cache()
    return tmp_path


@pytest.fixture
def fixture_c_phase_2_shaped(tmp_path: Path) -> Path:
    """(c) post-Phase-2 state (equivalent shape to (a))."""
    _init_git_repo(tmp_path)
    _write_charter(tmp_path)
    _sync_charter(tmp_path)
    _clear_resolver_cache()
    return tmp_path


@pytest.fixture
def fixture_d_stale_metadata(tmp_path: Path) -> Path:
    """(d) metadata.yaml hash does NOT match charter.md content."""
    _init_git_repo(tmp_path)
    _write_charter(tmp_path)
    _sync_charter(tmp_path)

    # Mutate charter.md so its hash no longer matches metadata.
    charter_md = tmp_path / ".kittify" / "charter" / "charter.md"
    charter_md.write_text(
        _CHARTER_MD + "\n## Appendix\nAdded after sync.\n",
        encoding="utf-8",
    )

    _clear_resolver_cache()
    return tmp_path


@pytest.fixture
def fixture_e_no_charter(tmp_path: Path) -> Path:
    """(e) no charter.md at all."""
    _init_git_repo(tmp_path)
    _clear_resolver_cache()
    return tmp_path


# ---------------------------------------------------------------------------
# Report decoding helper
# ---------------------------------------------------------------------------


def _decode_report(result: Any) -> dict[str, Any]:
    assert result.changes_made, "migration did not emit a report"
    data: dict[str, Any] = json.loads(result.changes_made[0])
    return data


# ---------------------------------------------------------------------------
# FR-013 fixture matrix
# ---------------------------------------------------------------------------


def test_fixture_a_passes_bundle_validation_no_chokepoint_refresh(
    fixture_a_with_full_derivatives: Path, migration: Any
) -> None:
    """(a) derivatives already present → applied=False, chokepoint_refreshed=False."""
    result = migration.apply(fixture_a_with_full_derivatives)
    report = _decode_report(result)

    assert report["charter_present"] is True
    assert report["applied"] is False
    assert report["chokepoint_refreshed"] is False
    assert report["bundle_validation"]["passed"] is True
    assert report["bundle_validation"]["missing_tracked"] == []
    assert report["bundle_validation"]["missing_derived"] == []
    assert report["errors"] == []


def test_fixture_b_chokepoint_refreshes_derivatives(
    fixture_b_no_derivatives: Path, migration: Any
) -> None:
    """(b) no derivatives → chokepoint runs, applied=True, post-refresh empty missing."""
    result = migration.apply(fixture_b_no_derivatives)
    report = _decode_report(result)

    assert report["charter_present"] is True
    assert report["applied"] is True
    assert report["chokepoint_refreshed"] is True
    assert report["bundle_validation"]["missing_derived"] == []
    assert report["bundle_validation"]["passed"] is True
    # Every derivative materialised on disk.
    for rel in (
        ".kittify/charter/governance.yaml",
        ".kittify/charter/directives.yaml",
        ".kittify/charter/metadata.yaml",
    ):
        assert (fixture_b_no_derivatives / rel).exists(), rel


def test_fixture_c_second_apply_is_no_op(
    fixture_c_phase_2_shaped: Path, migration: Any
) -> None:
    """(c) already-applied fixture: second apply must be applied=False, no errors."""
    # First apply (may or may not refresh — depends on pre-state).
    first = migration.apply(fixture_c_phase_2_shaped)
    first_report = _decode_report(first)
    # Even first apply against an already-sync'd fixture should not refresh.
    assert first_report["applied"] is False
    assert first_report["chokepoint_refreshed"] is False

    # Second apply — the real idempotency gate.
    second = migration.apply(fixture_c_phase_2_shaped)
    second_report = _decode_report(second)
    assert second_report["applied"] is False
    assert second_report["chokepoint_refreshed"] is False
    assert second_report["errors"] == []
    assert second_report["bundle_validation"]["passed"] is True


def test_fixture_d_stale_metadata_triggers_refresh(
    fixture_d_stale_metadata: Path, migration: Any
) -> None:
    """(d) stale hash → chokepoint refreshes."""
    result = migration.apply(fixture_d_stale_metadata)
    report = _decode_report(result)

    assert report["charter_present"] is True
    assert report["chokepoint_refreshed"] is True
    assert report["applied"] is True
    assert report["bundle_validation"]["passed"] is True


def test_fixture_e_no_charter_is_clean_no_op(
    fixture_e_no_charter: Path, migration: Any
) -> None:
    """(e) no charter.md → charter_present=False, applied=False, validation trivial."""
    result = migration.apply(fixture_e_no_charter)
    report = _decode_report(result)

    assert report["charter_present"] is False
    assert report["applied"] is False
    assert report["chokepoint_refreshed"] is False
    # Bundle validation is the default trivial-pass shape.
    assert report["bundle_validation"]["passed"] is True
    assert report["bundle_validation"]["missing_tracked"] == []
    assert report["bundle_validation"]["missing_derived"] == []


# ---------------------------------------------------------------------------
# Schema conformance
# ---------------------------------------------------------------------------


def test_report_matches_schema(fixture_b_no_derivatives: Path, migration: Any) -> None:
    """Emitted JSON matches contracts/migration-report.schema.json."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_CONTRACTS_SCHEMA_PATH.read_text("utf-8"))
    result = migration.apply(fixture_b_no_derivatives)
    report = _decode_report(result)
    # Raises on failure — preferred over a bare True assertion.
    jsonschema.validate(instance=report, schema=schema)


def test_report_matches_schema_for_no_charter(
    fixture_e_no_charter: Path, migration: Any
) -> None:
    """The no-charter shape also satisfies the schema."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_CONTRACTS_SCHEMA_PATH.read_text("utf-8"))
    result = migration.apply(fixture_e_no_charter)
    report = _decode_report(result)
    jsonschema.validate(instance=report, schema=schema)


# ---------------------------------------------------------------------------
# Out-of-scope safety invariants (C-011, C-012, D-12)
# ---------------------------------------------------------------------------


def test_migration_does_not_touch_worktree(
    fixture_b_no_derivatives: Path, migration: Any
) -> None:
    """A pre-existing worktree directory is untouched by the migration."""
    worktree_dir = fixture_b_no_derivatives / ".worktrees" / "dummy-lane-a"
    worktree_dir.mkdir(parents=True)
    sentinel = worktree_dir / "ledger.txt"
    sentinel.write_text("do not touch me", encoding="utf-8")
    before_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()

    migration.apply(fixture_b_no_derivatives)

    # File content unchanged.
    after_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()
    assert before_hash == after_hash
    # Nothing added underneath the worktree.
    descendants = sorted(p.name for p in worktree_dir.rglob("*"))
    assert descendants == ["ledger.txt"]


def test_migration_does_not_touch_gitignore(
    fixture_b_no_derivatives: Path, migration: Any
) -> None:
    """``.gitignore`` is not read or written by the v1.0.0 migration."""
    gitignore = fixture_b_no_derivatives / ".gitignore"
    gitignore.write_text("# sentinel\nfoo/\n", encoding="utf-8")
    before = gitignore.read_text("utf-8")
    before_mtime = gitignore.stat().st_mtime_ns

    migration.apply(fixture_b_no_derivatives)

    after = gitignore.read_text("utf-8")
    assert before == after
    assert gitignore.stat().st_mtime_ns == before_mtime


def test_migration_does_not_touch_memory_symlinks(
    fixture_b_no_derivatives: Path, migration: Any
) -> None:
    """``.kittify/memory`` and ``.kittify/AGENTS.md`` are left alone (C-011).

    On filesystems that refuse symlinks (Windows CI, etc.) the test falls
    back to regular files — the migration must not touch them either.
    """
    kittify = fixture_b_no_derivatives / ".kittify"
    memory_target = kittify / "_memory_source"
    memory_target.mkdir()
    (memory_target / "note.md").write_text("m", encoding="utf-8")
    agents_target = kittify / "_agents_source.md"
    agents_target.write_text("a", encoding="utf-8")

    memory_link = kittify / "memory"
    agents_link = kittify / "AGENTS.md"
    try:
        memory_link.symlink_to(memory_target, target_is_directory=True)
        agents_link.symlink_to(agents_target)
        using_symlinks = True
    except OSError:
        memory_link.mkdir()
        (memory_link / "note.md").write_text("m", encoding="utf-8")
        agents_link.write_text("a", encoding="utf-8")
        using_symlinks = False

    migration.apply(fixture_b_no_derivatives)

    if using_symlinks:
        assert memory_link.is_symlink()
        assert agents_link.is_symlink()
    assert memory_link.exists()
    assert agents_link.exists()
    assert agents_link.read_text("utf-8") == "a"


def test_duration_ms_under_2000(
    fixture_b_no_derivatives: Path, migration: Any
) -> None:
    """NFR-006: wall-time must stay at or under 2 s on the reference fixture."""
    result = migration.apply(fixture_b_no_derivatives)
    report = _decode_report(result)
    assert report["duration_ms"] >= 0
    assert report["duration_ms"] <= 2000, report["duration_ms"]


# ---------------------------------------------------------------------------
# Registry & metadata wiring
# ---------------------------------------------------------------------------


def test_registry_discovers_migration() -> None:
    """The new migration is registered under the canonical id."""
    from specify_cli.upgrade.registry import MigrationRegistry

    ids = [m.migration_id for m in MigrationRegistry.get_all()]
    assert "m_3_2_3_unified_bundle" in ids


# ---------------------------------------------------------------------------
# CLI integration (review-cycle-1, Findings 1 + 2)
# ---------------------------------------------------------------------------

_METADATA_YAML_3_2_2 = """\
# Spec Kitty Project Metadata
# Auto-generated by spec-kitty init/upgrade
# DO NOT EDIT MANUALLY

spec_kitty:
  version: 3.2.2
  initialized_at: '2026-01-01T00:00:00'
environment:
  python_version: '3.11'
  platform: darwin
migrations:
  applied: []
"""


def _make_322_project(root: Path) -> None:
    """Build a minimal 3.2.2 fixture project rooted at *root*.

    The fixture has:
        - an initialised git repo (required by charter.resolution)
        - ``.kittify/metadata.yaml`` stamped at 3.2.2
        - a charter.md at the canonical path with derivatives already synced
          (so the migration ends up in the "present + fresh" case — the
          bug-prone path for cycle-1 Finding 1 where the old narrow detect()
          would have silently skipped).
    """
    _init_git_repo(root)
    _write_charter(root)
    _sync_charter(root)

    kittify = root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "metadata.yaml").write_text(_METADATA_YAML_3_2_2, encoding="utf-8")

    _clear_resolver_cache()


def test_upgrade_cli_json_includes_migration_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`spec-kitty upgrade --json` exposes the schema-shaped migration report.

    Cycle-1 Finding 2: the CLI must plumb per-migration
    ``MigrationResult.changes_made[0]`` (JSON-encoded schema-shaped report)
    through the ``--json`` output under ``migration_reports.<migration_id>``.

    Cycle-1 Finding 1 regression: running through the live ``MigrationRunner``
    on a 3.2.2 project whose derivatives are already fresh must still invoke
    ``m_3_2_3_unified_bundle`` and emit a report. Previously the narrow
    ``detect()`` caused the runner to silently skip.
    """
    from typer import Typer
    from typer.testing import CliRunner

    from specify_cli.cli.commands import upgrade as upgrade_module

    project = tmp_path / "proj"
    project.mkdir()
    _make_322_project(project)

    monkeypatch.chdir(project)

    app = Typer()
    app.command()(upgrade_module.upgrade)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["--target", "3.2.3", "--force", "--no-worktrees", "--json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.stdout
    payload: dict[str, Any] = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["success"] is True, payload

    # Finding 2: the report must appear under migration_reports keyed by id.
    reports = payload.get("migration_reports")
    assert isinstance(reports, dict), f"missing migration_reports: {payload}"
    unified = reports.get("m_3_2_3_unified_bundle")
    assert unified is not None, f"missing unified-bundle report: {reports}"

    # Finding 1 regression: the migration ran through the live runner path
    # (not skipped by the narrow detect()) and produced a schema-shaped
    # report with charter_present=True.
    assert unified["migration_id"] == "m_3_2_3_unified_bundle"
    assert unified["target_version"] == "3.2.3"
    assert unified["charter_present"] is True
    assert "bundle_validation" in unified
    assert unified["bundle_validation"]["passed"] is True
    assert unified["errors"] == []


def test_upgrade_cli_json_reports_no_charter_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 1 regression (fixture e): no-charter project still emits a report.

    Before the fix, the narrow ``detect()`` returned False on projects without
    a charter.md, so the migration was silently skipped by the runner and no
    report was emitted. The live upgrade must now emit
    ``charter_present=False`` through the ``--json`` surface.
    """
    from typer import Typer
    from typer.testing import CliRunner

    from specify_cli.cli.commands import upgrade as upgrade_module

    project = tmp_path / "proj_no_charter"
    project.mkdir()
    _init_git_repo(project)
    kittify = project / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "metadata.yaml").write_text(_METADATA_YAML_3_2_2, encoding="utf-8")
    _clear_resolver_cache()

    monkeypatch.chdir(project)

    app = Typer()
    app.command()(upgrade_module.upgrade)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["--target", "3.2.3", "--force", "--no-worktrees", "--json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.stdout
    payload: dict[str, Any] = json.loads(result.stdout.strip().splitlines()[-1])
    reports = payload.get("migration_reports", {})
    unified = reports.get("m_3_2_3_unified_bundle")
    assert unified is not None, f"missing report for no-charter case: {reports}"
    assert unified["charter_present"] is False
    assert unified["applied"] is False
    assert unified["chokepoint_refreshed"] is False
    assert unified["bundle_validation"]["passed"] is True


def test_upgrade_runner_invokes_migration_on_stale_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 1 repro: stale-metadata fixture goes THROUGH the runner.

    The old narrow ``detect()`` returned False when derivatives were present
    (even if stale), so ``MigrationRunner._apply_migration`` skipped the
    migration entirely. We exercise the live runner and assert the migration
    was invoked (present in ``migrations_applied`` or ``migrations_skipped``
    with a recorded ``migration_results`` payload).
    """
    from specify_cli.upgrade.runner import MigrationRunner

    project = tmp_path / "proj_stale"
    project.mkdir()

    # Build a 3.2.2 project with derivatives pre-synced, then mutate the
    # charter so metadata.yaml hash no longer matches.
    _init_git_repo(project)
    _write_charter(project)
    _sync_charter(project)

    kittify = project / ".kittify"
    (kittify / "metadata.yaml").write_text(_METADATA_YAML_3_2_2, encoding="utf-8")

    charter_md = project / ".kittify" / "charter" / "charter.md"
    charter_md.write_text(
        _CHARTER_MD + "\n## Appendix\nAdded after sync.\n",
        encoding="utf-8",
    )

    _clear_resolver_cache()
    monkeypatch.chdir(project)

    runner = MigrationRunner(project)
    result = runner.upgrade("3.2.3", include_worktrees=False, force=True)

    assert result.success is True, result.errors

    # The migration must be visible to the runner (either applied or skipped),
    # NOT absent — absence is the cycle-1 bug signature.
    migration_ids_seen = set(result.migrations_applied) | set(result.migrations_skipped)
    assert "m_3_2_3_unified_bundle" in migration_ids_seen, (
        "m_3_2_3_unified_bundle was not invoked by the runner on a stale "
        "fixture — regression of review-cycle-1 Finding 1"
    )

    # And its structured payload must be captured for the CLI --json surface.
    assert "m_3_2_3_unified_bundle" in result.migration_results
    report_json = result.migration_results["m_3_2_3_unified_bundle"].changes_made[0]
    report = json.loads(report_json)
    assert report["charter_present"] is True
    assert report["chokepoint_refreshed"] is True
    assert report["applied"] is True


# ---------------------------------------------------------------------------
# Post-merge reviewer regression: worktree-skip semantics (P2)
# ---------------------------------------------------------------------------


def test_detect_returns_false_inside_linked_worktree(tmp_path: Path) -> None:
    """``detect()`` must return False for a linked worktree so the runner
    records a clean ``skipped`` there instead of marking the migration as
    applied in the worktree's own ``.kittify/metadata.yaml``.

    Regression guard for a post-merge reviewer finding: the runner's
    ``_upgrade_worktrees`` loop iterates ``.worktrees/*`` on the default
    upgrade path. Before this fix ``detect()`` returned True
    unconditionally, so the runner recorded ``m_3_2_3_unified_bundle`` as
    applied inside every worktree even though the chokepoint correctly
    materializes derivatives only at the canonical main-checkout root.
    That violates the migration's "NO worktree scanning, NO worktree
    mutation" contract (§C-011 / §C-012).
    """
    from specify_cli.upgrade.migrations.m_3_2_3_unified_bundle import (
        UnifiedBundleMigration,
    )

    main_root = tmp_path / "main"
    main_root.mkdir()
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=main", str(main_root)],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(main_root), "config", "user.email", "t@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(main_root), "config", "user.name", "T"],
        check=True,
    )
    (main_root / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(main_root), "add", "seed.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(main_root), "commit", "-q", "-m", "seed"],
        check=True,
    )

    worktree = tmp_path / "worktree-skip"
    subprocess.run(
        [
            "git",
            "-C",
            str(main_root),
            "worktree",
            "add",
            "-b",
            "feature/worktree-skip",
            str(worktree),
        ],
        check=True,
    )

    # In a linked worktree, ``.git`` is a FILE pointing at the shared
    # common dir. In the main checkout, ``.git`` is a directory. The
    # migration's detect() uses that distinction.
    assert (worktree / ".git").is_file()
    assert (main_root / ".git").is_dir()

    migration = UnifiedBundleMigration()
    assert migration.detect(main_root) is True, (
        "detect(main_checkout) must be True so the migration runs on 3.2.3 upgrades"
    )
    assert migration.detect(worktree) is False, (
        "detect(linked_worktree) must be False so the runner's worktree loop "
        "skips the migration (no worktree scanning / mutation per §C-011/§C-012)"
    )
