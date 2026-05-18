"""Convention gate: every module under src/charter/ and src/kernel/ MUST
declare ``__all__`` (C-007 binding via C-004 / FR-121).

This is the "presence" gate that pairs with
``test_no_dead_symbols.py`` (the "no orphan" gate). Together they
enforce a closed public-surface contract on the two architectural
boundary subpackages: every module declares what it exports, and every
export has a non-test caller in ``src/``.

The gate uses static AST inspection: any module-level ``__all__ = ...``
assignment satisfies the check, regardless of whether the value is a
literal list/tuple or a computed expression. Dynamic forms still
declare intent; the membership check (live in ``test_no_dead_symbols``)
gracefully skips dynamic declarations.

Parametrised across every ``*.py`` under ``src/charter/`` and
``src/kernel/`` (including ``__init__.py``). New modules added to those
subpackages are automatically gated.

ATDD anchor: AC-8 (covers: FR-121).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"


def _modules_under(subpackage: str) -> list[Path]:
    """Yield every ``*.py`` file under ``src/<subpackage>/`` (sorted).

    Includes ``__init__.py`` -- package surfaces must also declare
    ``__all__`` so the re-export contract is explicit.
    """
    root = _SRC_ROOT / subpackage
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _has_all_decl(path: Path) -> bool:
    """Return True if *path* has a module-level ``__all__`` assignment.

    Accepts either:

    * ``ast.Assign`` whose target is ``Name(id="__all__")``, including
      computed values (``__all__ = sorted(...)``).
    * ``ast.AnnAssign`` whose target is ``Name(id="__all__")``
      (typed declarations like ``__all__: list[str] = []``).

    The membership check is enforced elsewhere; this gate only requires
    *presence*.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
                return True
        elif isinstance(node, ast.AnnAssign):
            tgt = node.target
            if isinstance(tgt, ast.Name) and tgt.id == "__all__":
                return True
    return False


_CHARTER_MODULES: list[Path] = _modules_under("charter")
_KERNEL_MODULES: list[Path] = _modules_under("kernel")


@pytest.mark.parametrize(
    "path",
    _CHARTER_MODULES,
    ids=lambda p: str(p.relative_to(_REPO_ROOT)),
)
def test_every_charter_module_declares_all(path: Path) -> None:
    """C-007 / FR-121: every ``src/charter/**/*.py`` declares ``__all__``."""
    assert _has_all_decl(path), (
        f"{path.relative_to(_REPO_ROOT)} is missing an `__all__` "
        f"declaration. C-007 (binding via C-004) requires every module "
        f"under `src/charter/` to declare its public surface explicitly. "
        f"Add `__all__ = [...]` near the top of the module after imports, "
        f"listing every name intended to be public."
    )


@pytest.mark.parametrize(
    "path",
    _KERNEL_MODULES,
    ids=lambda p: str(p.relative_to(_REPO_ROOT)),
)
def test_every_kernel_module_declares_all(path: Path) -> None:
    """C-007 / FR-121: every ``src/kernel/**/*.py`` declares ``__all__``."""
    assert _has_all_decl(path), (
        f"{path.relative_to(_REPO_ROOT)} is missing an `__all__` "
        f"declaration. C-007 (binding via C-004) requires every module "
        f"under `src/kernel/` to declare its public surface explicitly. "
        f"Add `__all__ = [...]` near the top of the module after imports, "
        f"listing every name intended to be public."
    )
