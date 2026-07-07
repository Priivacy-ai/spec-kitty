"""Preflight helpers for local pre-PR / pre-review CI parity.

See: src/specify_cli/cli/commands/review/ERROR_CODES.md for the
MISSION_REVIEW_TEST_EXTRA_MISSING and MISSION_REVIEW_ENV_SKEW diagnostic
bodies.

Three preflight concerns live here:

* ``assert_pytest_available`` -- pytest must be importable from the active
  interpreter (pre-existing).
* The typer/click lock-parity check (FR-001, issue #2283 Phase 3) -- reads
  the LOCKED versions from ``uv.lock`` and compares them to the installed
  versions, warning (default) or raising ``EnvSkew`` (opt-in fail-closed) on
  divergence. A local ``.venv`` built without ``--frozen`` can drift onto a
  ``typer`` release that vendors ``click`` internally and stops re-exporting
  it (see the TID251 Gap-5 ban in pyproject.toml), so local CLI-shard runs
  can silently diverge from CI without this check.
* The local CI-residual selection runner (FR-002) -- single-sources the
  ``-m`` marker expression from the live ``unit-contract-residual`` CI job
  (``.github/workflows/ci-quality.yml``) rather than a hand-copied string,
  so a contributor can run the same selection locally before pushing.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, cast

import yaml

from specify_cli.core.env import is_truthy

# ---------------------------------------------------------------------------
# assert_pytest_available (pre-existing)
# ---------------------------------------------------------------------------


class TestExtraMissing(Exception):
    """Raised when `pytest` cannot be imported from the active venv."""

    # Prevent pytest from treating this exception class as a test class.
    __test__ = False


def assert_pytest_available(project_root: Path) -> None:
    """Assert that `python -c 'import pytest'` succeeds in the project venv.

    Raises TestExtraMissing on failure, carrying the
    MISSION_REVIEW_TEST_EXTRA_MISSING diagnostic code in args[0].
    """
    result = subprocess.run(
        [sys.executable, "-c", "import pytest"],
        cwd=project_root,
        capture_output=True,
    )
    if result.returncode != 0:
        raise TestExtraMissing("MISSION_REVIEW_TEST_EXTRA_MISSING")


# ---------------------------------------------------------------------------
# T001 -- typer/click lock-parity check (FR-001)
# ---------------------------------------------------------------------------

ENV_SKEW_DIAGNOSTIC_CODE = "MISSION_REVIEW_ENV_SKEW"
ENV_SKEW_REMEDIATION = "uv sync --frozen --all-extras"
ENV_SKEW_FAIL_CLOSED_ENV_VAR = "SPEC_KITTY_ENV_SKEW_FAIL_CLOSED"

# Packages this preflight guards against local/CI venv skew. typer>=0.26
# vendors click and stops re-exporting it (pyproject.toml TID251 Gap-5 ban;
# the typer>=0.26 compat CI step at ci-quality.yml). A local .venv built
# without --frozen can pull a newer typer/click than CI's exact pins.
GUARDED_LOCK_PACKAGES: tuple[str, ...] = ("typer", "click")


class EnvSkew(Exception):
    """Raised (fail-closed mode only) when typer/click diverge from uv.lock."""

    __test__ = False


@dataclass(frozen=True)
class PackageSkew:
    """One package's uv.lock-pinned version vs. what's actually installed."""

    package: str
    locked: str
    installed: str | None


def _read_uv_lock_versions(
    uv_lock_path: Path, packages: tuple[str, ...] = GUARDED_LOCK_PACKAGES
) -> dict[str, str]:
    """Parse ``uv.lock`` (TOML) and return ``{package: locked_version}``.

    Reads the lockfile LIVE via :mod:`tomllib` -- the single source of truth
    for pinned versions (NFR-002) -- never a hardcoded copy that could
    silently diverge from the lock. Packages absent from the lock are
    omitted from the result.
    """
    data = tomllib.loads(uv_lock_path.read_text(encoding="utf-8"))
    entries = cast("list[dict[str, Any]]", data.get("package", []))
    locked: dict[str, str] = {}
    for entry in entries:
        name = entry.get("name")
        version = entry.get("version")
        if name in packages and isinstance(version, str):
            locked[name] = version
    return locked


def _installed_version(package: str) -> str | None:
    """Return the installed version of ``package`` in the active interpreter."""
    try:
        return importlib_metadata.version(package)
    except importlib_metadata.PackageNotFoundError:
        return None


def check_typer_click_lock_parity(
    project_root: Path, *, packages: tuple[str, ...] = GUARDED_LOCK_PACKAGES
) -> list[PackageSkew]:
    """Compare uv.lock-pinned typer/click versions to the installed ones.

    Returns the list of mismatches (empty if none, or if ``uv.lock`` is
    absent -- e.g. a `uv tool install` consumer whose wheel never ships the
    lockfile). Does not raise; callers (``assert_typer_click_lock_parity``)
    decide whether to warn or fail-closed.
    """
    uv_lock_path = project_root / "uv.lock"
    if not uv_lock_path.is_file():
        return []
    locked_versions = _read_uv_lock_versions(uv_lock_path, packages)
    mismatches: list[PackageSkew] = []
    for package in packages:
        locked = locked_versions.get(package)
        if locked is None:
            # Not pinned in this lock (unrelated lock-shape concern) --
            # nothing to compare against.
            continue
        installed = _installed_version(package)
        if installed != locked:
            mismatches.append(PackageSkew(package, locked, installed))
    return mismatches


def format_env_skew_message(mismatches: list[PackageSkew]) -> str:
    """Render a human-readable, diagnostic-coded skew report for ``mismatches``."""
    rows = "\n".join(
        f"  - {m.package}: locked={m.locked}, "
        f"installed={m.installed if m.installed is not None else '<not installed>'}"
        for m in mismatches
    )
    return (
        f"{ENV_SKEW_DIAGNOSTIC_CODE}: local typer/click versions diverge from "
        f"uv.lock:\n{rows}\n"
        f"Run `{ENV_SKEW_REMEDIATION}` to restore parity with CI."
    )


def assert_typer_click_lock_parity(
    project_root: Path, *, fail_closed: bool | None = None
) -> list[PackageSkew]:
    """Preflight: warn (default) or raise ``EnvSkew`` (opt-in) on lock drift.

    ``fail_closed`` defaults to the truthiness of
    ``SPEC_KITTY_ENV_SKEW_FAIL_CLOSED`` so a legitimately forward-compat dev
    loop (testing ``typer>=0.26``) is never bricked unless the developer
    explicitly opts in -- warn-loud is the default (SC-001).

    Returns the mismatch list either way (empty when parity holds) so
    warn-mode callers can still surface the divergence.
    """
    if fail_closed is None:
        fail_closed = is_truthy(os.environ.get(ENV_SKEW_FAIL_CLOSED_ENV_VAR))
    mismatches = check_typer_click_lock_parity(project_root)
    if mismatches and fail_closed:
        raise EnvSkew(ENV_SKEW_DIAGNOSTIC_CODE, format_env_skew_message(mismatches))
    return mismatches


# ---------------------------------------------------------------------------
# T002 -- local CI-residual selection runner (FR-002)
# ---------------------------------------------------------------------------

CI_RESIDUAL_WORKFLOW_RELATIVE_PATH = Path(".github/workflows/ci-quality.yml")
CI_RESIDUAL_JOB_NAME = "unit-contract-residual"

# Matches the double-quoted `-m "<expr>"` argument of a pytest invocation --
# the same shape the CI job's `run:` script uses.
_MARKER_EXPR_RE = re.compile(r'-m\s+"(?P<expr>[^"]*)"')


class ResidualSelectorNotFound(Exception):
    """Raised when the CI residual job or its ``-m`` expression can't be found."""

    __test__ = False


def read_ci_residual_marker_expr(
    workflow_path: Path, *, job_name: str = CI_RESIDUAL_JOB_NAME
) -> str:
    """Extract the pytest ``-m`` marker expression from the CI residual job.

    Reads *workflow_path* LIVE and parses it with ``yaml.safe_load`` -- this
    is the single source for the residual selection (NFR-002): the
    expression can never silently diverge from CI because it is never
    hand-copied into this module.
    """
    if not workflow_path.is_file():
        raise ResidualSelectorNotFound(f"CI workflow not found at {workflow_path}")
    raw = workflow_path.read_text(encoding="utf-8")
    data = cast("dict[str, Any]", yaml.safe_load(raw) or {})
    jobs = cast("dict[str, Any]", data.get("jobs") or {})
    job = jobs.get(job_name)
    if not isinstance(job, dict):
        raise ResidualSelectorNotFound(
            f"job {job_name!r} not found in {workflow_path}"
        )
    steps = cast("list[Any]", job.get("steps") or [])
    for step in steps:
        if not isinstance(step, dict):
            continue
        run_script = step.get("run")
        if not isinstance(run_script, str) or "pytest" not in run_script:
            continue
        match = _MARKER_EXPR_RE.search(run_script)
        if match is not None:
            expr: str = match.group("expr")
            return expr
    raise ResidualSelectorNotFound(
        f"no pytest -m expression found in job {job_name!r} of {workflow_path}"
    )


def build_local_residual_command(
    project_root: Path, *, workflow_path: Path | None = None
) -> list[str]:
    """Build the local pytest argv mirroring the CI residual selection.

    The ``-m`` expression is single-sourced from the live CI workflow via
    :func:`read_ci_residual_marker_expr` -- never a hardcoded duplicate
    (NFR-002), so a later change to the CI selector is picked up on the next
    call without any edit here.
    """
    resolved_workflow = workflow_path or (
        project_root / CI_RESIDUAL_WORKFLOW_RELATIVE_PATH
    )
    marker_expr = read_ci_residual_marker_expr(resolved_workflow)
    tests_root = project_root / "tests"
    return [
        sys.executable,
        "-m",
        "pytest",
        str(tests_root),
        "-m",
        marker_expr,
        "-q",
    ]


def run_local_residual_selection(
    project_root: Path,
    *,
    workflow_path: Path | None = None,
    extra_args: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[bytes]:
    """Run the CI residual ``(unit or contract)`` selection locally over tests/.

    Surfaces the unit/contract failures locally that today only reach CI
    (FR-002 / SC-002). Raises ``ResidualSelectorNotFound`` if the ``-m``
    expression cannot be read live from the CI workflow.
    """
    command = build_local_residual_command(project_root, workflow_path=workflow_path)
    return subprocess.run([*command, *extra_args], cwd=project_root)
