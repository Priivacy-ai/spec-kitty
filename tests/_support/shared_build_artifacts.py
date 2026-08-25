"""Run-scoped sharing of the session wheel/sdist build across xdist workers.

Session-scoped fixtures execute once per *worker process*, so before #80 every
xdist worker collecting a ``distribution`` test ran its own ``python -m build``
into its own temp tree — up to sixteen concurrent builds on the CI runner,
each spending a minute of CPU and leaving its own scratch tree behind at
exactly the moment ``tests/e2e``'s retained tmp_path trees are pushing the
runner's free disk toward zero (the #80 crash mechanism).

This module gives those fixtures one build per RUN instead of one build per
worker. The shared location is derived from pytest's own basetemp, which makes
it automatically scoped to a single run:

* under xdist each worker's basetemp is ``<run>/popen-gwN``, so ``<run>`` —
  the parent — is shared by exactly this run's workers and touched by no
  other run;
* serially the basetemp itself is already run-scoped, and a serial session
  builds once anyway;
* two concurrent pytest processes get distinct basetemps, so their caches
  never meet (they merely each build, as before).

A ``filelock`` lock serialises the first build; later workers validate what was
published and reuse it without building. Publication is atomic — the builder
fills a staging directory, then renames it into place while holding the lock —
and a crashed builder's staging directory is swept by the next claimant, so an
interrupted run cannot poison later ones.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from filelock import FileLock

_REPO_ROOT = Path(__file__).resolve().parents[2]

_SHARED_BUILD_DIR_NAME = "shared-build-artifacts"
_STAGING_GLOB = _SHARED_BUILD_DIR_NAME + ".staging-*"
#: One full ``python -m build`` takes on the order of a minute; every other
#: worker of the run queues behind that single holder, hence the generous bound.
_LOCK_TIMEOUT_S = 1200.0


def default_wheel_sdist_builder(outdir: Path) -> None:
    """Build this repository's wheel + sdist into ``outdir`` (#80's real builder).

    Lives beside the sharing protocol so the session ``build_artifacts``
    fixture in ``tests/conftest.py`` stays a thin shell with no nested
    definitions (the conftest definition-order guard pins that file's
    definition names).
    """
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", str(outdir)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SharedBuildError(f"Build failed: {result.stderr}")


class SharedBuildError(RuntimeError):
    """The wheel/sdist build itself failed; callers turn this into a skip."""


def run_scoped_shared_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return the temp directory shared by every xdist worker of this run.

    Workers nest their basetemp under the run's own basetemp (``popen-gwN``),
    so the parent of a worker's basetemp is this run's shared root. A serial
    session has no nesting, and its basetemp is already private to the run.
    """
    base = tmp_path_factory.getbasetemp()
    if os.environ.get("PYTEST_XDIST_WORKER"):
        return base.parent
    return base


def published_build_artifacts(shared_dir: Path) -> dict[str, Path] | None:
    """Return the run's published artifacts, or ``None`` if they are absent/incomplete."""
    wheels = sorted(shared_dir.glob("spec_kitty_cli-*.whl"))
    sdists = sorted(shared_dir.glob("spec_kitty_cli-*.tar.gz"))
    if not wheels or not sdists:
        return None
    artifacts = {"wheel": wheels[-1], "sdist": sdists[-1]}
    if all(path.is_file() and path.stat().st_size > 0 for path in artifacts.values()):
        return artifacts
    return None


def ensure_shared_build_artifacts(
    run_root: Path,
    build: Callable[[Path], None],
    *,
    lock_timeout_s: float = _LOCK_TIMEOUT_S,
) -> dict[str, Path]:
    """Return the run's wheel/sdist, building them once under a lock.

    ``build(outdir)`` must create the artifacts into ``outdir`` or raise
    :class:`SharedBuildError`. The first caller builds into a staging
    directory and publishes atomically; concurrent callers either queue on the
    lock and then reuse the publication, or find it already present and return
    immediately. Paths are always returned from the published location, never
    from the staging directory the caller happened to fill.
    """
    shared_dir = run_root / _SHARED_BUILD_DIR_NAME
    published = published_build_artifacts(shared_dir)
    if published is not None:
        return published
    with FileLock(str(run_root / (_SHARED_BUILD_DIR_NAME + ".lock")), timeout=lock_timeout_s):
        published = published_build_artifacts(shared_dir)
        if published is not None:
            return published
        for stale in run_root.glob(_STAGING_GLOB):
            shutil.rmtree(stale, ignore_errors=True)
        staging = run_root / f"{_SHARED_BUILD_DIR_NAME}.staging-{os.getpid()}"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True)
        try:
            build(staging)
            built = published_build_artifacts(staging)
            if built is None:
                raise SharedBuildError("Build did not produce expected wheel/sdist artifacts")
            if shared_dir.exists():
                shutil.rmtree(shared_dir)
            os.replace(staging, shared_dir)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    published_after_rename = published_build_artifacts(shared_dir)
    if published_after_rename is None:
        raise SharedBuildError("Published artifacts did not survive publication")
    return published_after_rename
