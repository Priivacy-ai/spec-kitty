"""WP05 — guards for the extracted ``merge/baseline.py`` cluster (#2027).

These tests lock the relocation invariants:

* the public API is importable from BOTH the canonical ``specify_cli.merge``
  surface AND the relocated ``specify_cli.merge.baseline`` module;
* the legacy ``cli.commands.merge`` back-compat private aliases remain
  importable (6 pre-existing suites depend on the ``_``-prefixed names);
* a record -> assert round-trip behaves identically through the new module.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_MISSION_ID = "01KVCGQCBASELINEMODULE00000"
_MISSION_SLUG = "baseline-module-roundtrip-01kvcgqc"
_TARGET_BRANCH = "main"


def test_public_api_importable_from_merge_package() -> None:
    from specify_cli.merge import (
        BaselineMergeCommitError,
        assert_baseline_merge_commit_on_target,
        record_baseline_merge_commit,
    )

    assert issubclass(BaselineMergeCommitError, RuntimeError)
    assert callable(record_baseline_merge_commit)
    assert callable(assert_baseline_merge_commit_on_target)


def test_public_api_importable_from_baseline_module() -> None:
    from specify_cli.merge.baseline import (
        BaselineMergeCommitError,
        assert_baseline_merge_commit_on_target,
        record_baseline_merge_commit,
    )

    assert issubclass(BaselineMergeCommitError, RuntimeError)
    assert callable(record_baseline_merge_commit)
    assert callable(assert_baseline_merge_commit_on_target)


def test_legacy_private_aliases_importable_from_merge_py() -> None:
    """6 pre-existing suites import these ``_``-prefixed names directly."""
    from specify_cli.cli.commands.merge import (
        BaselineMergeCommitError as LegacyError,
        _assert_baseline_merge_commit_on_target,
        _read_committed_meta_json,
        _record_baseline_merge_commit,
        _recorded_baseline_from_working_meta,
    )
    from specify_cli.merge.baseline import BaselineMergeCommitError as CanonicalError

    # The legacy surface re-exports the canonical symbol (identity preserved).
    assert LegacyError is CanonicalError
    assert callable(_record_baseline_merge_commit)
    assert callable(_assert_baseline_merge_commit_on_target)
    assert callable(_recorded_baseline_from_working_meta)
    assert callable(_read_committed_meta_json)


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_record_then_assert_roundtrip(tmp_path: Path) -> None:
    """A modern-mission record -> commit -> assert round-trip succeeds."""
    from specify_cli.merge.baseline import (
        assert_baseline_merge_commit_on_target,
        record_baseline_merge_commit,
    )

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _git(repo_root, "init", "-b", _TARGET_BRANCH)
    _git(repo_root, "config", "user.email", "pedro@example.com")
    _git(repo_root, "config", "user.name", "Python Pedro")

    feature_dir = repo_root / "kitty-specs" / _MISSION_SLUG
    feature_dir.mkdir(parents=True)
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(
        json.dumps({"mission_id": _MISSION_ID, "mission_slug": _MISSION_SLUG}),
        encoding="utf-8",
    )
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-m", "seed")
    baseline_sha = _git(repo_root, "rev-parse", "HEAD")

    written = record_baseline_merge_commit(
        feature_dir, baseline_sha, mission_id=_MISSION_ID
    )
    assert written == meta_path
    assert json.loads(meta_path.read_text())["baseline_merge_commit"] == baseline_sha

    # Idempotent: a second record with the value already set is a no-op.
    assert (
        record_baseline_merge_commit(feature_dir, baseline_sha, mission_id=_MISSION_ID)
        is None
    )

    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-m", "record baseline")

    # Durable-in-git verification passes.
    assert_baseline_merge_commit_on_target(
        repo_root,
        _MISSION_SLUG,
        _TARGET_BRANCH,
        baseline_sha,
        feature_dir=feature_dir,
        mission_id=_MISSION_ID,
    )
