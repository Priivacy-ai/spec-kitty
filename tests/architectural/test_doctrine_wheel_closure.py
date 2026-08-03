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


def test_kernel_pyproject_exists_and_parses() -> None:
    """Sanity guard: if the file is renamed/moved this must fail loudly."""
    assert _KERNEL_PYPROJECT.is_file(), (
        f"{_KERNEL_PYPROJECT} not found. FR-009 requires a "
        "spec-kitty-kernel package definition at src/kernel/pyproject.toml "
        "-- the true root of the wheel dependency chain "
        "(kernel <- doctrine <- charter <- specify_cli)."
    )
    data = _load_toml(_KERNEL_PYPROJECT)
    assert data.get("project", {}).get("name") == _KERNEL_PACKAGE_NAME, (
        f"src/kernel/pyproject.toml [project].name must be "
        f"{_KERNEL_PACKAGE_NAME!r}, got {data.get('project', {}).get('name')!r}."
    )


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


def test_kernel_version_satisfies_doctrine_declared_specifier() -> None:
    """FR-010 closure: the kernel's OWN declared version must satisfy the
    specifier doctrine's pyproject.toml pins for ``spec-kitty-kernel``.

    ``test_doctrine_pyproject_declares_kernel_dependency`` only asserts that
    the dependency NAME is present -- it never checks whether the two
    manifests' version numbers are actually compatible. This test makes the
    two manifests mutually enforcing: a future version bump on either side
    that breaks compatibility (e.g. kernel cutting a ``2.0.0`` while
    doctrine's upper bound stays ``<2.0.0``, or doctrine tightening its lower
    bound past kernel's current version) fails this gate today, instead of
    only failing silently at the actual future wheel cutover (#3163).

    Self-mutation proof: bumping src/kernel/pyproject.toml's ``version`` to
    ``"2.0.0"`` (or any version outside the specifier doctrine currently
    declares) turns this red.
    """
    from packaging.requirements import Requirement
    from packaging.version import Version

    doctrine_data = _load_toml(_DOCTRINE_PYPROJECT)
    doctrine_deps = doctrine_data.get("project", {}).get("dependencies", [])
    kernel_dep_specs = [d for d in doctrine_deps if _dep_name(d) == _KERNEL_PACKAGE_NAME]
    assert kernel_dep_specs, (
        f"src/doctrine/pyproject.toml does not declare a {_KERNEL_PACKAGE_NAME} "
        "dependency -- see test_doctrine_pyproject_declares_kernel_dependency."
    )
    requirement = Requirement(kernel_dep_specs[0])

    kernel_data = _load_toml(_KERNEL_PYPROJECT)
    kernel_version_str = kernel_data.get("project", {}).get("version")
    assert kernel_version_str, (
        "src/kernel/pyproject.toml has no [project].version to check "
        "against doctrine's declared specifier."
    )
    kernel_version = Version(kernel_version_str)

    assert kernel_version in requirement.specifier, (
        f"src/kernel/pyproject.toml declares version {kernel_version_str!r}, "
        f"which does NOT satisfy src/doctrine/pyproject.toml's declared "
        f"specifier {str(requirement.specifier)!r} for {_KERNEL_PACKAGE_NAME}. "
        "The two manifests must stay mutually compatible: bumping either "
        "side without checking the other would silently break the future "
        "wheel cutover."
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
    hooks = (
        data.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("hooks", {})
        .get("custom", None)
    )
    assert hooks is not None, (
        "src/doctrine/pyproject.toml is missing "
        "[tool.hatch.build.hooks.custom]. D7 requires a hatchling custom "
        "build hook to inject an absolute force_include for the "
        "repo-root sibling packs/ directory (a naive relative "
        "force-include escapes the project root and hatchling refuses "
        "it)."
    )
    assert _DOCTRINE_HATCH_BUILD.is_file(), (
        f"{_DOCTRINE_HATCH_BUILD} not found. D7's build hook "
        "implementation must live at src/doctrine/hatch_build.py."
    )
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
# C-002 -- no CI job builds/installs the nested doctrine wheel standalone
# ---------------------------------------------------------------------------


def test_no_ci_workflow_builds_nested_doctrine_wheel_standalone() -> None:
    """C-002: this WP is groundwork only -- no CI job may cut over to it.

    Every ``hatch build`` / ``python -m build`` invocation across
    .github/workflows/ must run from the repository root (building
    spec-kitty-cli via the root pyproject.toml's ``packages =
    [...,"src/doctrine",...]`` + root force-include), never from inside
    src/doctrine/ (which would build the standalone spec-kitty-doctrine
    wheel this WP is only laying groundwork for). The kernel dependency
    is unresolvable until a future PyPI publish, so building the nested
    wheel in CI today would break.
    """
    workflows_dir = _REPO_ROOT / ".github" / "workflows"
    offending: list[str] = []
    for workflow_path in sorted(workflows_dir.glob("*.yml")):
        text = workflow_path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if "src/doctrine" not in stripped:
                continue
            if any(marker in stripped for marker in ("hatch build", "python -m build")):
                offending.append(f"{workflow_path.name}:{lineno}: {stripped}")
    assert not offending, (
        "CI workflow(s) appear to build the nested doctrine wheel "
        f"standalone, violating C-002: {offending}"
    )
