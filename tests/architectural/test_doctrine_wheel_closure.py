"""Wheel-packaging groundwork closure for the nested ``src/doctrine`` package.

Mission ``doctrine-charter-split-unification-01KZ0SRB``, WP12 (FR-009,
FR-010, NFR-004, C-002).

The nested ``src/doctrine/pyproject.toml`` describes a standalone
``spec-kitty-doctrine`` wheel that is **not** built by any CI job today
(C-002 forbids that this WP wire it into the release/build path). This
module asserts the *shape* of that nested package definition:

1. **FR-009** -- a sibling ``spec-kitty-kernel`` package exists at
   ``src/kernel/pyproject.toml`` with **zero** first-party dependencies
   (the true root of the wheel dependency chain: ``kernel <- doctrine <-
   charter <- specify_cli``).
2. **FR-010** -- ``src/doctrine/pyproject.toml`` declares a dependency on
   ``spec-kitty-kernel`` (the real import-closure need: ``resolver.py``,
   ``missions/primitives.py``, and ``shared/schema_utils.py`` all import
   from ``kernel``).
3. **FR-010 / D7** -- the chosen out-of-tree mechanism that carries the
   repo-root sibling ``packs/`` directory into the nested doctrine wheel
   as a ``doctrine`` site-packages sibling (the hatchling custom build
   hook at ``src/doctrine/hatch_build.py``) is present and wired via
   ``[tool.hatch.build.hooks.custom]``.

NFR-004 self-mutation proof: each assertion below is written so that
removing the corresponding piece of groundwork (the kernel dependency
line, or the build-hook wiring) turns the test red. This was verified
manually during implementation by temporarily reverting each piece and
confirming failure before restoring; see WP12 report for the transcript.

C-002 guard: this module intentionally does **not** invoke ``hatch
build`` -- doing so from a generic test run would imply CI builds the
nested wheel standalone, which C-002 forbids this mission. The *real*
``hatch build`` execution and wheel-content verification is done once,
by hand, during WP12 implementation and recorded in
``research.md`` §D7; this test only pins the durable pyproject/build-hook
*shape* that made that build succeed.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KERNEL_PYPROJECT = _REPO_ROOT / "src" / "kernel" / "pyproject.toml"
_DOCTRINE_PYPROJECT = _REPO_ROOT / "src" / "doctrine" / "pyproject.toml"
_DOCTRINE_HATCH_BUILD = _REPO_ROOT / "src" / "doctrine" / "hatch_build.py"

_KERNEL_PACKAGE_NAME = "spec-kitty-kernel"

# doctrine-public-api-surface-01KZPDSR WP02 (FR-008): the exact public surface
# the ``spec-kitty-doctrine`` wheel is intended to export — pinned so the
# packaged contract cannot silently drift from ``doctrine/api.py``'s ``__all__``.
# Every entry is a PUBLIC-tagged symbol in the WP01 census disposition
# (``tests/architectural/test_doctrine_census.py::DISPOSITION``). Changing the
# wheel surface is a deliberate diff to BOTH ``doctrine/api.py`` and this literal.
_EXPECTED_DOCTRINE_API_SURFACE: frozenset[str] = frozenset(
    {
        "ArtifactKind",
        "AssetManifest",
        "AssetNotFoundError",
        "AssetPathEscapeError",
        "AssetRepository",
        "AssetResolutionError",
        "CatalogLoadResult",
        "RoutingRecommendation",
        "evaluate",
        "load",
    }
)

# First-party package names that must NEVER appear in kernel's dependency
# list -- kernel is the root of the dependency chain and must stay
# dependency-free of every sibling package.
_FIRST_PARTY_PACKAGES = (
    "spec-kitty-cli",
    "spec-kitty-doctrine",
    "spec-kitty-charter",
    "spec-kitty-kernel",  # a package must not depend on itself
)


def _load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _dep_name(dep_spec: str) -> str:
    """Extract the bare package name from a PEP 508 dependency string."""
    for sep in ("[", ">=", "<=", "==", "!=", "~=", ">", "<", " ", ";"):
        idx = dep_spec.find(sep)
        if idx != -1:
            dep_spec = dep_spec[:idx]
    return dep_spec.strip()


# ---------------------------------------------------------------------------
# FR-009 -- src/kernel/pyproject.toml exists with zero first-party deps
# ---------------------------------------------------------------------------


def test_kernel_pyproject_has_zero_first_party_dependencies() -> None:
    """FR-009: kernel MUST NOT depend on any other spec-kitty-* package.

    Self-mutation proof: adding any first-party dependency to
    src/kernel/pyproject.toml's [project.dependencies] turns this red.
    """
    data = _load_toml(_KERNEL_PYPROJECT)
    deps = data.get("project", {}).get("dependencies", [])
    offending = [d for d in deps if _dep_name(d) in _FIRST_PARTY_PACKAGES]
    assert not offending, (
        f"src/kernel/pyproject.toml declares first-party dependencies: "
        f"{offending}. FR-009 requires kernel to have ZERO first-party "
        "dependencies -- it is the root of the dependency chain."
    )


# ---------------------------------------------------------------------------
# FR-010 -- src/doctrine/pyproject.toml declares the spec-kitty-kernel dep
# ---------------------------------------------------------------------------


def test_doctrine_pyproject_declares_kernel_dependency() -> None:
    """FR-010: doctrine's nested pyproject.toml must depend on the kernel.

    This is a real import-closure need: resolver.py, missions/primitives.py,
    and shared/schema_utils.py all do ``from kernel...`` imports. Without
    this dependency declared, an independently-installed spec-kitty-doctrine
    wheel would ImportError at runtime.

    Self-mutation proof: removing the spec-kitty-kernel dependency line
    from src/doctrine/pyproject.toml's [project.dependencies] turns this
    red.
    """
    data = _load_toml(_DOCTRINE_PYPROJECT)
    deps = data.get("project", {}).get("dependencies", [])
    matching = [d for d in deps if _dep_name(d) == _KERNEL_PACKAGE_NAME]
    assert matching, (
        f"src/doctrine/pyproject.toml does not declare a {_KERNEL_PACKAGE_NAME} "
        "dependency. FR-010 requires this because doctrine's resolver.py, "
        "missions/primitives.py, and shared/schema_utils.py import from "
        "kernel; an independently-built doctrine wheel is unimportable "
        "without it."
    )


# ---------------------------------------------------------------------------
# FR-010 / D7 -- packs/ out-of-tree mechanism (hatchling custom build hook)
# ---------------------------------------------------------------------------


def test_doctrine_pyproject_wires_the_packs_build_hook() -> None:
    """FR-010 / D7: the nested doctrine wheel wires a custom build hook.

    ``packs/`` is a repo-root sibling of ``src/doctrine`` (not under
    ``src/doctrine`` itself), so hatchling's declarative
    ``force-include`` cannot reach it with a relative path that escapes
    the project root ("../../packs" is refused). D7 resolved this via a
    hatchling custom build hook (``BuildHookInterface.initialize``)
    computing an absolute ``force_include`` path at build time. This test
    pins that the hook is present and wired into
    [tool.hatch.build.hooks.custom].

    Self-mutation proof: removing the
    ``[tool.hatch.build.hooks.custom]`` table from
    src/doctrine/pyproject.toml, OR deleting src/doctrine/hatch_build.py,
    turns this red.
    """
    data = _load_toml(_DOCTRINE_PYPROJECT)
    hooks = data.get("tool", {}).get("hatch", {}).get("build", {}).get("hooks", {}).get("custom", None)
    assert hooks is not None, (
        "src/doctrine/pyproject.toml is missing "
        "[tool.hatch.build.hooks.custom]. D7 requires a hatchling custom "
        "build hook to inject an absolute force_include for the "
        "repo-root sibling packs/ directory (a naive relative "
        "force-include escapes the project root and hatchling refuses "
        "it)."
    )
    assert _DOCTRINE_HATCH_BUILD.is_file(), f"{_DOCTRINE_HATCH_BUILD} not found. D7's build hook implementation must live at src/doctrine/hatch_build.py."
    hook_source = _DOCTRINE_HATCH_BUILD.read_text(encoding="utf-8")
    assert "force_include" in hook_source, (
        "src/doctrine/hatch_build.py does not reference force_include. "
        "D7's hook must inject a computed absolute force_include entry "
        "so packs/built-in/ lands as a doctrine sibling in the wheel."
    )
    assert "packs" in hook_source, (
        "src/doctrine/hatch_build.py does not reference packs/. D7's "
        "hook must carry the repo-root sibling packs/ directory into "
        "the nested doctrine wheel."
    )


# ---------------------------------------------------------------------------
# FR-008 -- the wheel pins the REAL public surface (doctrine/api.py __all__),
# not merely the manifest shape (doctrine-public-api-surface-01KZPDSR WP02)
# ---------------------------------------------------------------------------


def test_doctrine_api_pins_the_real_public_surface() -> None:
    """FR-008: ``doctrine/api.py`` enumerates exactly the pinned wheel surface.

    The pre-existing tests above pin the *packaging shape* (kernel dep, build
    hook). This one pins the *content*: the eventual ``spec-kitty-doctrine``
    wheel exports precisely ``_EXPECTED_DOCTRINE_API_SURFACE``. A symbol added to
    or removed from ``doctrine/api.py``'s ``__all__`` without a matching edit to
    the pinned literal turns this red — so the wheel contract cannot drift.

    Self-mutation proof: adding or dropping a name in ``doctrine/api.py``'s
    ``__all__`` (or in ``_EXPECTED_DOCTRINE_API_SURFACE``) without the
    corresponding change on the other side turns this red.
    """
    import doctrine.api as doctrine_api

    actual = frozenset(getattr(doctrine_api, "__all__", []))
    assert actual == _EXPECTED_DOCTRINE_API_SURFACE, (
        "doctrine/api.py __all__ drifted from the pinned wheel surface.\n"
        f"  unexpected (in api, not pinned): {sorted(actual - _EXPECTED_DOCTRINE_API_SURFACE)}\n"
        f"  missing (pinned, not in api):    {sorted(_EXPECTED_DOCTRINE_API_SURFACE - actual)}\n"
        "Update BOTH doctrine/api.py and _EXPECTED_DOCTRINE_API_SURFACE deliberately."
    )


def test_doctrine_api_surface_symbols_are_importable() -> None:
    """FR-001/FR-008: every pinned wheel symbol resolves to a real object.

    Belt-and-braces with test_doctrine_public_surface: the wheel-closure gate
    should not pin a name that the module cannot actually provide.
    """
    import doctrine.api as doctrine_api

    unresolved = [name for name in _EXPECTED_DOCTRINE_API_SURFACE if getattr(doctrine_api, name, None) is None]
    assert not unresolved, f"Pinned doctrine.api surface symbols are unresolvable/None: {sorted(unresolved)}"
