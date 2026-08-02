"""Hatchling custom build hook for the standalone ``spec-kitty-doctrine``
wheel: places the ``doctrine`` package correctly and carries the
repo-root sibling ``packs/`` alongside it (FR-010, D7).

Context -- why a build hook is needed at all
---------------------------------------------
``packs/`` is a top-level directory living at the *repository root*, one
level above ``src/`` -- it is a sibling of ``src/doctrine``, not a
descendant of it. ``pack_paths._resolve_built_in`` (step 3, "installed
wheel") expects ``packs/built-in`` to land as a site-packages sibling of
the installed ``doctrine`` package:
``files("doctrine").parent / "packs" / "built-in"``.

The monorepo root wheel (built from the repository-root
``pyproject.toml``) already achieves this with a declarative
``force-include = { "packs" = "packs" }`` entry, because ``packs/`` is a
direct child of *that* project's root.

The **nested** ``src/doctrine/pyproject.toml`` describes a standalone
``spec-kitty-doctrine`` wheel whose project root is ``src/doctrine/``
itself. From that root, ``packs/`` is reached only via ``../../packs`` --
a relative path that escapes the project root. Hatchling's declarative
``force-include`` refuses any source path that resolves outside the
project root, so the same declarative mechanism used by the root
pyproject cannot be reused here. This hook computes the **absolute**
path to the repo-root ``packs/`` directory at build time and injects it
into ``build_data["force_include"]`` programmatically -- hatchling's
*programmatic* ``force_include`` accepts any absolute source path
regardless of project-root containment; only the declarative
pyproject.toml form is root-bound.

Why the ``doctrine`` package itself is force-included too
-----------------------------------------------------------
This project's root (``src/doctrine/``) directly contains the package's
own files (``__init__.py``, ``resolver.py``, ``agent_profiles/``, ...) --
there is no nested ``src/doctrine/doctrine/`` subdirectory the way the
repo-root pyproject's ``packages = [..., "src/doctrine", ...]`` expects.
A declarative ``packages = ["src/doctrine"]`` in *this* pyproject.toml
(copy-pasted from the repo-root shape before this hook existed) matched
nothing, and a global ``sources = {"" = "doctrine"}`` rename collides
with this hook's own ``packs`` force_include entry (the rename applies
uniformly to *every* distribution path hatchling computes, force-included
or not, re-nesting ``packs/`` under ``doctrine/`` instead of alongside
it). The T004 executed ``hatch build`` caught both failure modes -- see
``research.md`` §D7 for the two before/after wheel-content diffs. The fix
here is to drive *all* wheel content through this hook's own
``force_include`` entries with fully explicit destination paths, so no
hatchling ``sources``/``packages`` rename logic is in play at all: each
top-level child of this project's root (except its own build-only files)
is force-included under ``doctrine/<name>``, and the repo-root ``packs/``
is force-included under ``packs`` (a true ``doctrine`` sibling).

Wired via ``[tool.hatch.build.hooks.custom]`` in
``src/doctrine/pyproject.toml`` (default script name ``hatch_build.py``,
auto-discovered by hatchling since this module defines exactly one
``BuildHookInterface`` subclass). Injecting *any* non-empty
``force_include`` here also makes hatchling suppress its normal
project-file walk (see ``BuilderConfig.default_file_selection_options``'s
``bypass_selection`` check) once the dynamic ``force_include`` from this
hook is merged in, which is why this pyproject.toml's own
``[tool.hatch.build.targets.wheel]`` table carries no ``packages`` /
``sources`` / ``include`` keys -- all wheel content is force-included.

Groundwork scope (C-002): this hook only takes effect when someone runs
``hatch build`` (or ``python -m build``) *from inside* ``src/doctrine/``.
No CI job in this repository does that today -- the root pyproject's
``packages`` list still includes ``src/doctrine`` and the monorepo wheel
remains the only wheel any CI job builds. See
``tests/architectural/test_doctrine_wheel_closure.py`` for the pinned
CI-workflow guard and ``research.md`` §D7 for the executed
``hatch build`` verification of this exact hook.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_PACKS_DIRNAME = "packs"
_DOCTRINE_DISTRIBUTION_PREFIX = "doctrine"

# This project's own build-tooling files/directories: never force-included
# under doctrine/ (they are not part of the importable doctrine package).
_NON_PACKAGE_ENTRIES = frozenset(
    {
        "pyproject.toml",
        "hatch_build.py",
        "dist",
        "__pycache__",
        ".git",
    }
)


class DoctrinePacksSiblingBuildHook(BuildHookInterface[Any]):
    """Force-includes the ``doctrine`` package tree and the sibling ``packs/``.

    Only acts on the ``wheel`` build target; sdist packaging is handled
    separately by the repo-root pyproject.toml, which already covers the
    monorepo distribution.
    """

    PLUGIN_NAME = "doctrine-packs-sibling"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        """Called immediately before each build; mutates ``build_data``.

        ``version`` is unused here but is a required part of
        ``BuildHookInterface.initialize``'s signature (hatchling calls it
        positionally for every configured version); it cannot be renamed
        or dropped without breaking the interface hatchling invokes.
        """
        if self.target_name != "wheel":
            return

        force_include = build_data.setdefault("force_include", {})
        force_include.update(self._doctrine_package_entries())

        packs_dir = self._repo_root_packs_dir()
        if packs_dir is not None:
            force_include[str(packs_dir)] = _PACKS_DIRNAME
        # Groundwork-only: if packs/ is absent (e.g. a sparse checkout that
        # doesn't include repo-root siblings), skip silently rather than
        # fail the build -- this hook does not gate C-002's "no CI job
        # builds this wheel" invariant on packs/ existing.

    def _doctrine_package_entries(self) -> dict[str, str]:
        """Map each top-level package child to ``doctrine/<name>``.

        ``self.root`` (this project's root, ``src/doctrine/``) directly
        *is* the doctrine package's file layout -- iterating its immediate
        children and force-including each one under ``doctrine/`` achieves
        the same "doctrine" import root the monorepo root wheel produces,
        without relying on any hatchling ``sources`` rename that would
        also (incorrectly) rewrite this hook's own ``packs`` entry.
        """
        root = Path(self.root)
        entries: dict[str, str] = {}
        for child in sorted(root.iterdir()):
            if child.name in _NON_PACKAGE_ENTRIES:
                continue
            entries[str(child)] = f"{_DOCTRINE_DISTRIBUTION_PREFIX}/{child.name}"
        return entries

    def _repo_root_packs_dir(self) -> Path | None:
        """Resolve the repo-root ``packs/`` directory as an absolute path.

        ``self.root`` is the project root passed to hatchling for this
        build (``.../src/doctrine`` when building the nested package).
        The repository root is two levels up: ``src/doctrine`` -> ``src``
        -> repo root.
        """
        repo_root = Path(self.root).resolve().parent.parent
        packs_dir = repo_root / _PACKS_DIRNAME
        return packs_dir if packs_dir.is_dir() else None
