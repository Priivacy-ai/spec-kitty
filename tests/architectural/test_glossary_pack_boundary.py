"""Architectural guardrail (T011, C-002): the glossary_packs import boundary.

``src/doctrine/glossary_packs/`` MUST NOT import the retiring runtime
``glossary`` package (``src/glossary/``). Mission A ships the pack schema +
repository as static doctrine assets with no seeding into the runtime
glossary — the #1418 ``pack_seed_loader`` ACL (which coupled a doctrine
artifact to `src/glossary/`) is deliberately dropped, not reintroduced
(``contracts/pack-schema.md`` §6).

The guard AST-walks every module under ``src/doctrine/glossary_packs/`` and
flags any import of the runtime ``glossary`` module **at a module boundary**:
``import glossary``, ``import glossary.<x>``, ``from glossary import ...``,
``from glossary.<x> import ...``. It explicitly must NOT match the sibling
package ``glossary_packs`` itself — a naive substring/regex check on
``"glossary"`` would collide with the package's own name, making the guard
vacuous. Non-vacuousness is proven below by a self-test that injects a
forbidden import into a fixture source and confirms it IS flagged, alongside
a fixture ``from glossary_packs import X`` that is confirmed NOT flagged.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_ROOT = _REPO_ROOT / "src" / "doctrine" / "glossary_packs"

# The runtime module this package must never couple to.
_FORBIDDEN_MODULE = "glossary"


def _iter_package_python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def find_forbidden_glossary_imports(source: str) -> list[str]:
    """Return the forbidden-import descriptions found in *source*.

    Matches ``import glossary`` / ``import glossary.<x>`` (module-boundary
    dotted-prefix match on ``ast.Import`` aliases) and
    ``from glossary import ...`` / ``from glossary.<x> import ...``
    (module-boundary match on ``ast.ImportFrom.module``). Never matches the
    sibling package ``glossary_packs`` — the boundary check requires the
    matched name to equal ``"glossary"`` exactly or start with
    ``"glossary."``, which ``"glossary_packs"`` does not (no substring
    collision).
    """
    tree = ast.parse(source)
    offenses: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden_module_boundary(alias.name):
                    offenses.append(f"import {alias.name}")
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and _is_forbidden_module_boundary(node.module)
        ):
            names = ", ".join(alias.name for alias in node.names)
            offenses.append(f"from {node.module} import {names}")
    return offenses


def _is_forbidden_module_boundary(module_name: str) -> bool:
    """True iff *module_name* is ``glossary`` or a dotted submodule of it.

    Module-boundary match: ``module_name == "glossary"`` or
    ``module_name.startswith("glossary.")``. This deliberately excludes
    ``glossary_packs`` (and any other ``glossary<suffix>`` name that is not
    dot-separated) — a plain substring/regex check on ``"glossary"`` would
    incorrectly flag the package's own name.
    """
    return module_name == _FORBIDDEN_MODULE or module_name.startswith(f"{_FORBIDDEN_MODULE}.")


def test_glossary_packs_package_has_no_runtime_glossary_imports() -> None:
    """No module under src/doctrine/glossary_packs/ imports runtime `glossary`."""
    offenders: dict[str, list[str]] = {}
    for path in _iter_package_python_files(_PACKAGE_ROOT):
        offenses = find_forbidden_glossary_imports(path.read_text(encoding="utf-8"))
        if offenses:
            offenders[_rel(path)] = offenses

    assert not offenders, (
        "src/doctrine/glossary_packs/ must not import the retiring runtime "
        f"`glossary` package (C-002): {offenders}. Pack loading is a static "
        "doctrine asset concern; do not reintroduce the #1418 "
        "pack_seed_loader-style coupling to src/glossary/."
    )


# ---------------------------------------------------------------------------
# Non-vacuousness self-tests: prove the guard actually discriminates.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "import glossary\n",
        "import glossary.models\n",
        "from glossary import models\n",
        "from glossary.models import TermSense\n",
    ],
)
def test_guard_flags_injected_runtime_glossary_import(source: str) -> None:
    """An injected `glossary` import IS flagged — the guard is not a tautology."""
    assert find_forbidden_glossary_imports(source), (
        f"Expected the guard to flag {source!r} as a forbidden runtime "
        "glossary import, but it did not — the guard would be vacuous."
    )


@pytest.mark.parametrize(
    "source",
    [
        "import doctrine.glossary_packs\n",
        "from glossary_packs import GlossaryPack\n",
        "from glossary_packs.models import GlossaryTerm\n",
        "from doctrine.glossary_packs.repository import GlossaryPackRepository\n",
    ],
)
def test_guard_does_not_flag_glossary_packs_sibling_package(source: str) -> None:
    """`glossary_packs` imports are NOT flagged — no substring collision."""
    assert not find_forbidden_glossary_imports(source), (
        f"Guard incorrectly flagged a glossary_packs import as forbidden: "
        f"{source!r}. The module-boundary check must not substring-match "
        "'glossary' against 'glossary_packs'."
    )


def test_guard_would_fail_on_a_real_offending_module(tmp_path: Path) -> None:
    """End-to-end proof: an actual file with a forbidden import fails the walk.

    Builds a throwaway fixture tree mirroring the package layout with one
    offending module, and confirms the same walk used by the real guard
    reports it as an offender — demonstrating the guard is wired to real
    file I/O, not just the string-matching helper in isolation.
    """
    fixture_root = tmp_path / "glossary_packs"
    fixture_root.mkdir()
    (fixture_root / "__init__.py").write_text("")
    (fixture_root / "leaky.py").write_text(
        textwrap.dedent(
            """
            from glossary import models  # forbidden: runtime coupling

            def use_it() -> None:
                return models
            """
        )
    )
    (fixture_root / "clean.py").write_text(
        textwrap.dedent(
            """
            from doctrine.glossary_packs.models import GlossaryPack

            __all__ = ["GlossaryPack"]
            """
        )
    )

    offenders = {
        path.name: find_forbidden_glossary_imports(path.read_text(encoding="utf-8"))
        for path in _iter_package_python_files(fixture_root)
        if find_forbidden_glossary_imports(path.read_text(encoding="utf-8"))
    }

    assert offenders == {"leaky.py": ["from glossary import models"]}
