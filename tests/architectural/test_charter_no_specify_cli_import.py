"""Non-vacuous charter -> specify_cli import gate (FR-008, NFR-004, SC-004).

The documented dependency direction is::

    kernel (root) <- doctrine <- charter <- glossary/runtime <- specify_cli

so no module under ``src/charter/`` may import ``specify_cli`` at **any**
scope.

Why this file exists at all, given ``test_layer_rules.py`` already owns the
pytestarch ``LayerRule`` for the same direction: **the pytestarch rule is green
with the violation present.** pytestarch resolves module-level imports only, so
the lazy in-function ``import specify_cli`` that lived in
``charter/synthesizer/synthesize_pipeline.py`` (a ``__version__`` fallback
inside ``_get_synthesizer_version``) never registered as an edge. A gate that
cannot fail on the one real violation it is nominally guarding is a vacuous
gate, which is worse than no gate — it manufactures false confidence.

This module therefore mirrors ``_collect_specify_cli_imports`` from the
``mission_runtime`` boundary ledger in ``test_layer_rules.py``: it walks the
**full AST** (``ast.walk``) rather than only the module body, so in-function,
in-class, in-``try`` and conditionally-guarded imports are all caught.

Scope of the claim this gate proves (read this before citing it): it proves
**zero static ``specify_cli`` import edges** out of ``src/charter/**``. It does
not prove the absence of runtime coupling by other means — ``importlib``
string-indirection, ``__import__``, entry points, or duck-typed objects handed
in as data. Those are out of scope here by construction.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_SRC = Path(__file__).resolve().parents[2] / "src"
_CHARTER_ROOT = _SRC / "charter"

#: The forbidden top-level package. ``src/charter/**`` sits *below* it in the
#: layer chain, so any edge in this direction is an upward (illegal) edge.
_FORBIDDEN_ROOT = "specify_cli"


def _is_specify_cli_module(module: str) -> bool:
    """True when ``module`` is ``specify_cli`` itself or one of its subpackages.

    Matches on package boundaries, so a same-prefix-different-package name such
    as ``specify_client`` is correctly *not* treated as a violation.
    """
    return module == _FORBIDDEN_ROOT or module.startswith(f"{_FORBIDDEN_ROOT}.")


def collect_specify_cli_imports(root: Path) -> list[tuple[str, int, str]]:
    """Return ``(relative_path, lineno, imported_module)`` for every violation.

    Walks the full AST via :func:`ast.walk`, so *lazy, in-function* imports are
    included. A module-body-only scan (which is what the pytestarch layer rule
    performs) misses exactly the kind of import this gate exists to catch, and
    would pass vacuously.

    ``relative_path`` is relative to ``src/`` when *root* is inside the source
    tree, and otherwise to *root* itself, so the function stays usable against
    a synthetic tree in the non-vacuity tests below.
    """
    anchor = _SRC if _SRC in root.parents or root == _SRC else root
    found: list[tuple[str, int, str]] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = str(path.relative_to(anchor))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # ``node.module`` is None for a relative ``from . import x``,
                # which can never reach specify_cli from inside charter.
                if node.module and _is_specify_cli_module(node.module):
                    found.append((rel, node.lineno, node.module))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_specify_cli_module(alias.name):
                        found.append((rel, node.lineno, alias.name))
    return found


def test_charter_never_imports_specify_cli() -> None:
    """No ``src/charter/**`` module imports ``specify_cli`` at any scope.

    This is the FR-008 / SC-004 gate. It fails on module-level *and*
    in-function imports; see ``test_walker_catches_in_function_import`` for the
    committed proof that the in-function leg is real.
    """
    violations = collect_specify_cli_imports(_CHARTER_ROOT)

    assert violations == [], (
        "src/charter/** must not import specify_cli at any scope "
        "(kernel <- doctrine <- charter <- specify_cli; FR-008, SC-004).\n"
        "Resolve the package version via importlib.metadata, or accept the "
        "value as data from a specify_cli-layer caller.\nViolations:\n" + "\n".join(f"  {rel}:{lineno} imports {mod}" for rel, lineno, mod in violations)
    )


def test_walker_catches_in_function_import(tmp_path: Path) -> None:
    """Non-vacuity (NFR-004): an in-function import IS detected.

    This is the committed counterpart to the manual self-mutation check. It
    reproduces the exact shape of the deleted ``_get_synthesizer_version``
    fallback — an ``import specify_cli`` nested inside a function, inside a
    ``try``, inside an ``except`` handler — and asserts the walker flags it.
    Were the walker downgraded to a module-body scan, this test goes red.
    """
    module = tmp_path / "synthesize_pipeline.py"
    module.write_text(
        "def _get_synthesizer_version() -> str:\n"
        "    try:\n"
        "        from importlib.metadata import version\n"
        '        return version("spec-kitty-cli")\n'
        "    except Exception:\n"
        "        try:\n"
        "            import specify_cli\n"
        "            return str(specify_cli.__version__)\n"
        "        except Exception:\n"
        '            return "0.0.0-dev"\n',
        encoding="utf-8",
    )

    violations = collect_specify_cli_imports(tmp_path)

    assert violations == [("synthesize_pipeline.py", 7, "specify_cli")]


def test_walker_ignores_non_violating_imports(tmp_path: Path) -> None:
    """No false positives: prose, relative imports, and same-prefix packages.

    ``specify_client`` shares the ``specify_cli`` string prefix but is a
    different package; a naive ``startswith`` check would flag it.
    """
    (tmp_path / "clean.py").write_text(
        '"""Docstring mentioning specify_cli, which is not an import."""\n'
        "from __future__ import annotations\n"
        "\n"
        "import specify_client\n"
        "from charter.offering.artifact_kinds import ArtifactKind\n"
        "from . import sibling\n"
        "\n"
        "# import specify_cli  <- a comment, not an import\n"
        'PATH = "src/specify_cli/missions"\n',
        encoding="utf-8",
    )

    assert collect_specify_cli_imports(tmp_path) == []
