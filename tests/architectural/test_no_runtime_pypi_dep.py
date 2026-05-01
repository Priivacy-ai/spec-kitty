"""Architectural: no production dep on retired ``spec-kitty-runtime`` package.

WP05 of mission ``stability-and-hygiene-hardening-2026-04-01KQ4ARB``
implements FR-025 (a constraint reaffirming the
``shared-package-boundary-cutover`` decision). The standalone
``spec-kitty-runtime`` PyPI package was retired; the runtime is now
internal under ``src/specify_cli/next/_internal_runtime/``.

This test asserts:

1. ``pyproject.toml`` does NOT list ``spec-kitty-runtime`` in
   ``[project.dependencies]`` or any production-flavored entry under
   ``[project.optional-dependencies]`` (test/lint/dev/docs extras are
   permitted; they are dev-only).
2. ``specify_cli.next.decision`` imports cleanly in a sub-process where
   ``spec_kitty_runtime`` has been hidden from ``sys.modules`` and
   ``sys.path``. This proves the production code path does not require
   the retired package even when one happens to be present in the dev
   venv.

Companion: ``tests/architectural/test_pyproject_shape.py`` covers the
related ``[tool.uv.sources]`` invariants from the cutover mission.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_SRC = _REPO_ROOT / "src"

# Optional-dependency groups that are dev-only and may legitimately mention
# the runtime package (e.g. for migration tests).
_DEV_OPTIONAL_GROUPS = frozenset({"test", "tests", "testing", "dev", "lint", "docs", "doc"})


def _dep_name(spec: str) -> str:
    """Pull the PEP-508 distribution name out of a dependency spec string."""
    head = spec.strip()
    for sep in (" ", ";", "=", "<", ">", "!", "~", "["):
        idx = head.find(sep)
        if idx != -1:
            head = head[:idx]
    return head.strip().lower()


def test_pyproject_does_not_list_spec_kitty_runtime_in_production_deps() -> None:
    """FR-025: ``spec-kitty-runtime`` is not a production dependency."""
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies", []) or []
    offending = [d for d in deps if _dep_name(d) == "spec-kitty-runtime"]
    assert not offending, (
        "pyproject.toml [project.dependencies] lists spec-kitty-runtime "
        f"({offending}). Per FR-025 / C-003 the retired runtime package must "
        "not be a production dependency. Remove the line; the internal "
        "runtime under src/specify_cli/next/_internal_runtime/ is the only "
        "authoritative source."
    )


def test_pyproject_optional_dep_groups_do_not_smuggle_runtime_into_production() -> None:
    """No production-flavored optional-deps group lists ``spec-kitty-runtime``.

    Dev / test / lint / docs groups are intentionally exempt: those are
    developer-only environments and may need the package for migration
    coverage.
    """
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    optional = data.get("project", {}).get("optional-dependencies", {}) or {}
    offenders: list[str] = []
    for group, entries in optional.items():
        if group in _DEV_OPTIONAL_GROUPS:
            continue
        for entry in entries or []:
            if _dep_name(entry) == "spec-kitty-runtime":
                offenders.append(f"[optional-dependencies.{group}] -> {entry}")
    assert not offenders, (
        "pyproject.toml smuggles spec-kitty-runtime into a production "
        "optional-dependency group. Dev-only groups "
        f"({sorted(_DEV_OPTIONAL_GROUPS)}) are permitted. Offenders:\n  " + "\n  ".join(offenders)
    )


def test_cli_next_decision_imports_without_spec_kitty_runtime() -> None:
    """The CLI's next-decision entry point must import without ``spec_kitty_runtime``.

    Even when a developer venv has ``spec_kitty_runtime`` installed, the
    production code path under ``specify_cli.next`` must not depend on it.
    This sub-process test hides the package via a sitecustomize-style
    ``sys.modules`` block and verifies the import still succeeds.
    """
    snippet = textwrap.dedent(
        """
        import sys

        # Block any future import of spec_kitty_runtime in this child.
        class _Block:
            def find_spec(self, name, path=None, target=None):
                if name == "spec_kitty_runtime" or name.startswith("spec_kitty_runtime."):
                    raise ImportError(
                        "spec_kitty_runtime is intentionally blocked by FR-025 "
                        "test_no_runtime_pypi_dep."
                    )
                return None

        sys.meta_path.insert(0, _Block())

        # Drop any pre-imported copy.
        for mod_name in list(sys.modules):
            if mod_name == "spec_kitty_runtime" or mod_name.startswith("spec_kitty_runtime."):
                del sys.modules[mod_name]

        # The actual import we are pinning. ``decide_next`` is the public
        # production entry point used by the next CLI command.
        from specify_cli.next.decision import decide_next, Decision, DecisionKind

        # Sanity-touch the symbol so static analyzers cannot elide the import.
        assert callable(decide_next)
        assert Decision is not None
        assert DecisionKind is not None
        print("OK")
        """
    )

    # Prepend the repo's ``src/`` to ``PYTHONPATH`` so the child resolves
    # ``specify_cli`` from the working tree before any host site-packages
    # entry. That hardens the test against a developer environment whose
    # site-packages contains a stale editable-install reference (e.g. a
    # ``.pth`` line pointing at a previously-active worktree directory that
    # has since been removed by a mission merge). The CI clean-install gate
    # remains authoritative; this prepend only affects local runs where the
    # host venv is shared across worktrees.
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{_SRC}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(_SRC)
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        env=env,
        timeout=60,
    )
    assert result.returncode == 0, (
        "specify_cli.next.decision failed to import without spec_kitty_runtime.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
        "FR-025 requires the production code path to be runtime-package-free."
    )
    assert "OK" in result.stdout, f"Sub-process did not print OK marker; stdout={result.stdout!r}"
