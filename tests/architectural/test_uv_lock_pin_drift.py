"""uv.lock vs installed-package drift detector for governed shared packages.

This architectural test guards against environment drift between the exact
versions pinned in ``uv.lock`` and the versions actually installed in the
developer's active virtualenv. Drift typically arises when a developer
installs an off-version copy of a shared package (e.g. for ad-hoc local
testing) and then forgets to ``uv sync --frozen`` before running the
review gates.

The check is **environment/review-gate hygiene only** -- per Constraint
**C-004** in
``kitty-specs/charter-e2e-827-followups-01KQAJA0/spec.md``, this WP must
not modify ``pyproject.toml``, ``[tool.uv.sources]``, ``uv.lock``, or
introduce any dependency-management abstraction. It only adds this
deterministic, fast pytest plus the documentation page that names the
canonical sync command.

Why this matters:

* The shared-package boundary cutover (mission
  ``shared-package-boundary-cutover-01KQ22DS``) consumes
  ``spec-kitty-events`` and ``spec-kitty-tracker`` from PyPI. Compatibility
  ranges live in ``pyproject.toml``; exact pins live in ``uv.lock``.
* The CI ``clean-install-verification`` job catches drift in CI, but
  pre-PR / pre-review local runs that bypass the CI job can still fail on
  drift in confusing ways unrelated to the developer's actual changes.
* This test surfaces drift with an actionable failure message that
  literally names the offending package(s) and prints the canonical sync
  command (``uv sync --frozen``).

Performance budget: this test parses one TOML file and reads installed
package metadata via :mod:`importlib.metadata`. It runs in well under
NFR-001's 5-second cap and contributes a negligible fraction of the
≤30-second architectural-suite budget (NFR-006 in the shared-package
boundary mission).

See ``docs/development/review-gates.md`` for the operator-facing
explanation of the sync command.
"""
from __future__ import annotations

import re
import tomllib
from importlib import metadata as importlib_metadata
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

# Governed shared packages — adding a new package is a one-line edit.
GOVERNED_PACKAGES: tuple[str, ...] = ("spec-kitty-events", "spec-kitty-tracker")

# The single documented sync command for restoring the environment to
# match ``uv.lock`` without re-resolving the dependency graph. Kept in one
# place so the failure message and the docs cannot drift apart.
SYNC_COMMAND: str = "uv sync --frozen"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_UV_LOCK_PATH = _REPO_ROOT / "uv.lock"
_VENV_DIR = _REPO_ROOT / ".venv"


def _resolve_uv_lock_versions(lock_path: Path) -> dict[str, str]:
    """Parse ``uv.lock`` and return ``{package_name: locked_version}``.

    Only governed packages present in the lock are included. Packages
    absent from the lock file are silently omitted -- that case is
    reported separately by the caller via the installed-version probe.
    """
    data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = data.get("package", [])
    locked: dict[str, str] = {}
    for entry in packages:
        name = entry.get("name")
        version = entry.get("version")
        if name in GOVERNED_PACKAGES and isinstance(version, str):
            locked[name] = version
    return locked


def _venv_site_packages() -> Path | None:
    """Return the project ``.venv`` site-packages dir, or ``None`` if absent.

    The drift check should target ``uv sync --frozen``'s installation
    surface, not whatever ambient interpreter happens to host the pytest
    process. A developer running pytest under a non-``.venv`` interpreter
    (e.g. homebrew Python with stray ``pythonpath`` entries) would
    otherwise see false drift caused by unrelated copies of the package.
    """
    if not _VENV_DIR.is_dir():
        return None
    for candidate in (_VENV_DIR / "lib").glob("python*/site-packages"):
        if candidate.is_dir():
            return candidate
    return None


# Distribution-name normalization mirrors PEP 503: dist-info dir names use
# underscores in place of hyphens, e.g. ``spec_kitty_tracker-0.4.3.dist-info``.
_DIST_INFO_RE = re.compile(r"-(?P<version>[^-]+)\.dist-info$")


def _venv_installed_version(site_packages: Path, pkg: str) -> str | None:
    """Read the installed version of ``pkg`` from a specific ``.venv`` site-packages.

    Resolves the distribution by scanning for ``<dist_name>-<version>.dist-info``
    directories where ``<dist_name>`` matches ``pkg`` after PEP 503 dash-to-
    underscore normalization. Reads ``METADATA`` and parses the ``Version:``
    header.

    Returns the version string, or ``None`` if the package is not installed
    in this site-packages tree.
    """
    dist_name_underscored = pkg.replace("-", "_")
    for candidate in site_packages.glob(f"{dist_name_underscored}-*.dist-info"):
        match = _DIST_INFO_RE.search(candidate.name)
        if not match:
            continue
        metadata_path = candidate / "METADATA"
        if not metadata_path.is_file():
            continue
        for raw_line in metadata_path.read_text(encoding="utf-8").splitlines():
            if raw_line.startswith("Version:"):
                version = raw_line.split(":", 1)[1].strip()
                if version:
                    return version
        # METADATA found but Version header missing — fall back to dir-name parse.
        return match.group("version")
    return None


def _installed_version(pkg: str) -> str | None:
    """Return the installed version of ``pkg``.

    Targets the project ``.venv`` site-packages when one exists, so the
    drift check is independent of which interpreter happens to host the
    pytest process. Falls back to the ambient interpreter's metadata when
    no project ``.venv`` is present (e.g., the ``clean-install-verification``
    CI job which installs into the ambient interpreter).
    """
    site_packages = _venv_site_packages()
    if site_packages is not None:
        return _venv_installed_version(site_packages, pkg)
    try:
        return importlib_metadata.version(pkg)
    except importlib_metadata.PackageNotFoundError:
        return None


def test_uv_lock_file_exists_and_parses() -> None:
    """Sanity guard: the file we are asserting against must exist and parse.

    Mirrors the guard in ``test_pyproject_shape.py`` so a relocation of
    ``uv.lock`` produces a clear failure rather than a silent no-op.
    """
    assert _UV_LOCK_PATH.is_file(), f"uv.lock not found at {_UV_LOCK_PATH}"
    # Round-trip parse to confirm well-formed TOML.
    _ = tomllib.loads(_UV_LOCK_PATH.read_text(encoding="utf-8"))


def test_uv_lock_matches_installed_versions() -> None:
    """Each governed shared package's installed version must match ``uv.lock``.

    Drift detection covers two failure modes:

    1. The package is locked at version ``X.Y.Z`` but the installed
       version differs (``A.B.C != X.Y.Z``).
    2. The package is locked but not installed at all
       (``importlib.metadata`` raises ``PackageNotFoundError``).

    On any drift, the failure message names every offending package
    along with both versions, and instructs the developer to run the
    documented sync command.
    """
    locked_versions = _resolve_uv_lock_versions(_UV_LOCK_PATH)

    mismatches: list[tuple[str, str, str | None]] = []
    for pkg in GOVERNED_PACKAGES:
        locked = locked_versions.get(pkg)
        if locked is None:
            # Locked entry missing entirely -- this is an unrelated lock-shape
            # problem (a different test in test_pyproject_shape.py covers the
            # pyproject side). We surface it here with locked='<absent>' so
            # the developer at least sees something meaningful.
            installed = _installed_version(pkg)
            mismatches.append((pkg, "<absent from uv.lock>", installed))
            continue
        installed = _installed_version(pkg)
        if installed != locked:
            mismatches.append((pkg, locked, installed))

    if mismatches:
        rows = "\n".join(
            f"  - {pkg}: locked={locked}, installed={installed if installed is not None else '<not installed>'}"
            for pkg, locked, installed in mismatches
        )
        pytest.fail(
            "uv.lock vs installed-package drift detected for governed "
            "shared packages:\n"
            f"{rows}\n"
            "Run the documented pre-review/pre-PR sync command from the "
            "repository root:\n"
            f"  {SYNC_COMMAND}\n"
            "This restores the environment to match uv.lock without "
            "re-resolving the graph.\n"
            "See docs/development/review-gates.md for context."
        )
