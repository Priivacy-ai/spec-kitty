"""TOML shape assertions for the shared-package boundary cutover.

These tests enforce the pyproject-level constraints documented in
``kitty-specs/shared-package-boundary-cutover-01KQ22DS/spec.md``:

* **R4 / C-004**: ``[project.dependencies]`` MUST NOT exact-pin
  (``==X.Y.Z``) the shared packages ``spec-kitty-events`` or
  ``spec-kitty-tracker``. Exact pins live in ``uv.lock``; pyproject uses
  compatible ranges (``>=X.Y,<X+1``) so downstream consumers can roll
  forward without coordinated CLI releases.

* **R5 / C-005**: ``[tool.uv.sources]`` MUST NOT contain a ``path`` or
  ``editable`` entry for any of ``spec-kitty-events``,
  ``spec-kitty-tracker``, or ``spec-kitty-runtime``. Editable / path
  sources belong in developer-only configuration (e.g. ``uv.toml``
  overrides), never in the committed pyproject -- see ADR notes in
  ``contracts/events_consumer_surface.md``.

* **R6 / FR-006**: ``[project.dependencies]`` MUST NOT list
  ``spec-kitty-runtime``. The runtime PyPI surface is retired in this
  mission; the internalized runtime under
  ``src/specify_cli/next/_internal_runtime/`` is the only authoritative
  source.

These tests are TOML-shape assertions that run independently of the
import-graph rules in ``test_shared_package_boundary.py``.

NFR-006 caps total architectural-test runtime at ≤30 seconds; these tests
parse a single TOML file and run in milliseconds.

WP08 (``Cut over pyproject metadata``) lands the pyproject changes that
satisfy R4, R5, and R6. Until then, the live assertions are
``xfail``-marked with a clear reason. WP08's subtask T030 explicitly
removes those markers as part of its acceptance criteria.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"

_WP08_XFAIL_REASON = (
    "WP08 lands the pyproject metadata cutover (compatible ranges, "
    "removal of editable sources, removal of spec-kitty-runtime). "
    "WP08's subtask T030 MUST remove this xfail marker as part of its "
    "acceptance criteria. See "
    "kitty-specs/shared-package-boundary-cutover-01KQ22DS/tasks/WP08-*.md."
)


def _load_pyproject() -> dict:
    return tomllib.loads(_PYPROJECT_PATH.read_text(encoding="utf-8"))


def test_pyproject_file_exists_and_parses() -> None:
    """Sanity guard: the file we are asserting against must exist and parse.

    If pyproject.toml gets renamed or relocated, the rest of these tests
    would silently no-op; this guard prevents that.
    """
    assert _PYPROJECT_PATH.is_file(), f"pyproject.toml not found at {_PYPROJECT_PATH}"
    data = _load_pyproject()
    assert "project" in data, "pyproject.toml is missing the [project] table"
    assert "dependencies" in data["project"], "pyproject.toml [project] is missing dependencies"


# ---------------------------------------------------------------------------
# R6 -- FR-006: spec-kitty-runtime MUST NOT appear in [project.dependencies]
# ---------------------------------------------------------------------------


def test_pyproject_does_not_list_spec_kitty_runtime() -> None:
    """R6 / FR-006: ``spec-kitty-runtime`` must not be a declared dependency.

    This rule is LIVE today: pyproject already excludes spec-kitty-runtime
    (the dependency comment in pyproject.toml documents that the runtime
    is supplied via the internalized surface, not the PyPI package). The
    test guards against future regressions.
    """
    data = _load_pyproject()
    deps = data["project"]["dependencies"]
    offending = [d for d in deps if _dep_name(d) == "spec-kitty-runtime"]
    assert not offending, (
        f"pyproject.toml lists spec-kitty-runtime: {offending}. "
        "Per FR-006, the CLI must not depend on the retired runtime PyPI "
        "package. Remove the dependency line; the internalized runtime at "
        "src/specify_cli/next/_internal_runtime/ replaces it."
    )


# ---------------------------------------------------------------------------
# R4 -- C-004: shared packages must use compatible ranges, not exact pins
# ---------------------------------------------------------------------------


def test_pyproject_uses_compatible_ranges_for_shared_packages() -> None:
    """R4 / C-004: ``spec-kitty-events`` / ``spec-kitty-tracker`` use ranges.

    Both packages MUST appear in ``[project.dependencies]`` and MUST use
    compatible ranges (``>=X.Y,<X+1``) rather than exact pins
    (``==X.Y.Z``). Exact pins belong in ``uv.lock``.
    """
    data = _load_pyproject()
    deps = data["project"]["dependencies"]
    failures: list[str] = []
    for pkg in ("spec-kitty-events", "spec-kitty-tracker"):
        matching = [d for d in deps if _dep_name(d) == pkg]
        if not matching:
            failures.append(f"pyproject.toml does not list {pkg}")
            continue
        for entry in matching:
            spec = entry[len(pkg) :].strip()
            if "==" in spec:
                failures.append(
                    f"pyproject.toml pins {pkg} exactly: {entry!r}. Per C-004, exact pins live in uv.lock; pyproject.toml uses compatible ranges (>=X.Y,<X+1)."
                )
    assert not failures, "\n".join(failures)


# ---------------------------------------------------------------------------
# R5 -- C-005: no committed editable / path sources for shared packages
# ---------------------------------------------------------------------------


def test_pyproject_has_no_committed_editable_sources_for_shared_packages() -> None:
    """R5 / C-005: ``[tool.uv.sources]`` must not pin shared packages to local
    paths or editable installs.

    Editable / path sources are developer-only overrides; committing them
    in ``pyproject.toml`` makes the published wheel un-buildable for
    downstream consumers and silently drags in private trees in CI.
    """
    data = _load_pyproject()
    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    offending: list[str] = []
    for pkg in ("spec-kitty-events", "spec-kitty-tracker", "spec-kitty-runtime"):
        if pkg in sources:
            offending.append(
                f"[tool.uv.sources] contains {pkg}: {sources[pkg]!r}. "
                "Per C-005, editable / path sources for shared packages must "
                "live in developer-only configuration, not committed pyproject.toml."
            )
    assert not offending, "\n".join(offending)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# PEP 508 marker / extras / version specifiers begin with one of these chars.
_DEP_NAME_TERMINATORS = "[=<>!~;@ "


def _dep_name(entry: str) -> str:
    """Extract the bare package name from a PEP 508 dependency string.

    >>> _dep_name("spec-kitty-events==4.0.0")
    'spec-kitty-events'
    >>> _dep_name("typer>=0.24.1")
    'typer'
    >>> _dep_name("httpx[socks]>=0.28.1")
    'httpx'
    """
    for i, ch in enumerate(entry):
        if ch in _DEP_NAME_TERMINATORS:
            return entry[:i].strip()
    return entry.strip()
