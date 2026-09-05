"""Non-vacuous ``charter.offering`` -> ``charter.activation`` boundary gate.

Approved topology (MAP-GATE,
``kitty-specs/charter-code-topology-01M152G1/contracts/canonical-operator-surface-map.md``)
splits ``src/charter/`` into two internal seams: ``charter.offering``
(surface/read-model concerns) and ``charter.activation`` (mutation/write
concerns). Per C-004 the dependency direction is one-way::

    charter.activation -> charter.offering   (allowed)
    charter.offering   -> charter.activation  (FORBIDDEN)

i.e. ``offering`` must stay a pure surface that ``activation`` may depend on,
never the reverse. This module is authored in **S1**, *before* the S2
relocation that will actually populate ``src/charter/offering/`` and
``src/charter/activation/`` (265-file move). It must therefore:

1. Arm correctly once those packages exist (real scan).
2. Not vacuously pass-and-forget in the meantime — its logic is proven now,
   against synthetic trees, so S2 cannot silently introduce a violation the
   day the packages appear with nobody having verified the checker works.

Mirrors the shape of ``test_charter_no_specify_cli_import.py``: full-AST walk
(``ast.walk``) so lazy/in-function/in-try imports are caught, plus committed
``tmp_path`` non-vacuity tests.

Net-new logic vs. the copied template
--------------------------------------
The ``specify_cli`` gate explicitly punts on relative imports (see its
``node.module is None`` comment: "can never reach specify_cli from inside
charter"). That shortcut does not hold here — ``offering`` and ``activation``
are *siblings* under ``charter``, so intra-package code can legally write
``from ..activation import X`` or ``from . import activation`` and reach the
forbidden package without ever writing the absolute dotted name. This module
resolves ``ast.ImportFrom.level`` against each source file's own package
location using the same algorithm CPython uses internally
(``importlib._bootstrap._resolve_name`` / the public
``importlib.util.resolve_name``), verified interactively before being
encoded here:

* A regular module ``charter/offering/sub/mod.py`` has dotted name
  ``charter.offering.sub.mod`` and ``__package__`` (the base relative imports
  resolve against) ``charter.offering.sub`` — the package *containing* the
  module, not the module's own dotted name.
* A package's ``__init__.py`` is the one case where dotted name IS the
  package: its own dotted name already equals its ``__package__``.
* ``level`` then walks up from that base: ``level=1`` stays in the same
  package, each additional level strips one more trailing component before
  appending ``node.module`` (or, for ``from . import name`` where
  ``node.module`` is ``None``, each imported alias name is appended instead).

Deviation flagged for the record: two dots (``from ..activation import X``)
from a file *two* directories below ``offering`` (i.e.
``offering/sub/mod.py``) resolves to ``charter.offering.activation``, not
``charter.activation`` — verified against
``importlib.util.resolve_name("..activation", "charter.offering.sub")``.
Reaching ``charter.activation`` from that depth requires three dots. The
non-vacuity tests below cover both: the shallow two-dot case from
``offering/mod.py`` (matches the literal ``from ..activation import X`` shape
most directly) and the deeper three-dot case from ``offering/sub/mod.py``
(proves the resolver is depth-correct, not just level-count-correct).
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_SRC = Path(__file__).resolve().parents[2] / "src"
_CHARTER_ROOT = _SRC / "charter"

#: Does not exist yet as of S1 — populated in S2. The gate must scan it if
#: present and contribute zero violations (not error, not skip) if absent.
_OFFERING_ROOT = _CHARTER_ROOT / "offering"

#: The forbidden target package. ``charter.offering`` sits beside it, and per
#: C-004 may never depend on it (the reverse direction is allowed).
#: Mission ``charter-activation-split-01M16ZSE`` (MAP-D) physically relocated
#: the activation/mutation layer into the real ``src/charter/activation/``
#: package (a 96-file move: 47 modules + 6 subpackages). The subpackage rule
#: in :func:`_is_activation_module` (``module == "charter.activation"`` or
#: ``module.startswith("charter.activation.")``) now catches every activation
#: module through the single package-root entry below — the interim
#: enumerated allowlist (individually-named ``activation_engine`` /
#: ``activations`` / ``cascade`` / ``_activation_render`` entries, kept before
#: the move landed) is retired; no module was left behind to need it.
_FORBIDDEN_MODULE = "charter.activation"
_ACTIVATION_MODULES = frozenset({"charter.activation"})


def _is_activation_module(module: str) -> bool:
    """True when ``module`` is an activation-layer module or a subpackage of one.

    Matches on package boundaries so a same-prefix-different-package name
    (e.g. a hypothetical ``charter.activation_log``) is correctly *not*
    flagged.
    """
    return module in _ACTIVATION_MODULES or any(module.startswith(f"{m}.") for m in _ACTIVATION_MODULES)


def _dotted_module_name(path: Path, package_root: Path) -> str:
    """Dotted module name of *path*, relative to *package_root*.

    ``package_root`` is the directory that itself corresponds to the empty
    dotted prefix — i.e. ``package_root / "charter" / "offering"`` has
    dotted name ``"charter.offering"``. For an ``__init__.py`` the dotted
    name is the *package's* name (the ``__init__.py`` segment is dropped);
    for any other module it is the file's own name with ``.py`` stripped.
    """
    rel_parts = list(path.relative_to(package_root).parts)
    if rel_parts[-1] == "__init__.py":
        rel_parts = rel_parts[:-1]
    else:
        rel_parts[-1] = rel_parts[-1].removesuffix(".py")
    return ".".join(rel_parts)


def _package_of(dotted_module: str, *, is_init: bool) -> str:
    """The ``__package__`` relative imports in this module resolve against.

    A package's ``__init__.py`` resolves relative imports against its own
    dotted name. Any other module resolves against its dotted name with the
    final (module-name) component stripped.
    """
    if is_init:
        return dotted_module
    base, _, _ = dotted_module.rpartition(".")
    return base


def _resolve_relative_module(package: str, level: int, module: str | None) -> str | None:
    """Resolve a relative ``ImportFrom`` to an absolute dotted module name.

    Reimplements ``importlib._bootstrap._resolve_name`` (the algorithm the
    real Python import system uses), so ``level`` is walked the same way
    CPython walks it: ``package.rsplit(".", level - 1)`` — a ``maxsplit`` of
    ``0`` yields the package unsplit for ``level=1`` (import stays in the
    same package), and each further level strips one more trailing
    component. Returns ``None`` if *package* is empty or the import claims
    to walk above the top-level package (both defensive — not expected
    against a well-formed ``src/charter`` tree).
    """
    if not package:
        return None
    bits = package.rsplit(".", level - 1)
    if len(bits) < level:
        return None
    base = bits[0]
    return f"{base}.{module}" if module else base


def collect_activation_imports(scan_root: Path, package_root: Path) -> list[tuple[str, int, str]]:
    """Return ``(relative_path, lineno, resolved_module)`` for every violation.

    ``scan_root`` is the directory to walk (``src/charter/offering`` for the
    real gate). ``package_root`` is the directory that maps to the empty
    dotted prefix (``src/`` for the real gate, so ``charter/offering/x.py``
    resolves to dotted name ``charter.offering.x``) — needed to resolve
    relative imports against each file's own package location.

    Absent-directory is not an error: pre-S2, ``src/charter/offering/``
    does not exist, and this returns ``[]`` rather than raising, so the real
    gate test stays green (vacuously, by construction) until S2 populates
    the package. It does NOT silently skip the module when the directory
    *does* exist with zero ``.py`` files — that case also correctly yields
    ``[]``, but via the same ``rglob`` loop finding nothing, not a short
    circuit.
    """
    found: list[tuple[str, int, str]] = []
    if not scan_root.exists():
        return found
    for path in sorted(scan_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = str(path.relative_to(package_root))
        dotted = _dotted_module_name(path, package_root)
        package = _package_of(dotted, is_init=path.name == "__init__.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                found.extend(_violations_in_import_from(node, package, rel))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_activation_module(alias.name):
                        found.append((rel, node.lineno, alias.name))
    return found


def _violations_in_import_from(node: ast.ImportFrom, package: str, rel: str) -> list[tuple[str, int, str]]:
    """Violations contributed by a single ``ImportFrom`` node.

    Handles both the absolute case (``node.level == 0``) and the relative
    case, including the ``node.module is None`` shape of
    ``from . import activation`` where the imported alias name — not
    ``node.module`` — supplies the final path component.
    """
    if node.level == 0:
        if node.module and _is_activation_module(node.module):
            return [(rel, node.lineno, node.module)]
        return []

    if node.module:
        resolved = _resolve_relative_module(package, node.level, node.module)
        if resolved and _is_activation_module(resolved):
            return [(rel, node.lineno, resolved)]
        return []

    # ``from . import activation`` / ``from .. import activation as act``:
    # node.module is None, so each imported alias supplies the trailing
    # component (or, if the dots already resolve straight to
    # charter.activation, every alias in the list is a violating symbol).
    base = _resolve_relative_module(package, node.level, None)
    if base is None:
        return []
    violations: list[tuple[str, int, str]] = []
    for alias in node.names:
        if _is_activation_module(base):
            violations.append((rel, node.lineno, base))
            continue
        candidate = f"{base}.{alias.name}"
        if _is_activation_module(candidate):
            violations.append((rel, node.lineno, candidate))
    return violations


def test_charter_offering_never_imports_activation() -> None:
    """No ``src/charter/offering/**`` module imports ``charter.activation``.

    This is the C-004 boundary gate. It is authored in S1, before S2 creates
    ``src/charter/offering/`` and ``src/charter/activation/`` (265-file
    relocation), so today it scans a directory that does not exist yet and
    correctly contributes zero violations (see
    ``collect_activation_imports``'s absent-directory handling). Its
    detection logic is proven now — not deferred to S2 — by the committed
    ``tmp_path`` tests below, so S2 cannot introduce a violation that this
    gate silently fails to catch on day one.
    """
    violations = collect_activation_imports(_OFFERING_ROOT, _SRC)

    assert violations == [], (
        "charter.offering must not import charter.activation, at any scope "
        "or via relative import (C-004: offering is a pure surface; "
        "activation may depend on offering, never the reverse).\n"
        "Violations:\n" + "\n".join(f"  {rel}:{lineno} imports {mod}" for rel, lineno, mod in violations)
    )


def test_walker_catches_absolute_activation_import(tmp_path: Path) -> None:
    """Non-vacuity: an absolute ``from charter.activation import X`` IS caught.

    Reproduces the plainest violation shape a post-S2 offering module could
    write, so this gate has committed proof it fires before S2 ever lands.
    """
    offering = tmp_path / "charter" / "offering"
    offering.mkdir(parents=True)
    (offering / "leaf.py").write_text(
        "from charter.activation import ActivationEngine\n",
        encoding="utf-8",
    )

    violations = collect_activation_imports(offering, tmp_path)

    assert violations == [("charter/offering/leaf.py", 1, "charter.activation")]


def test_walker_catches_relative_activation_import(tmp_path: Path) -> None:
    """Non-vacuity: ``from ..activation import X`` (relative, level=2) IS caught.

    ``offering/mod.py`` is one directory below the top-level ``charter``
    package (dotted name ``charter.offering.mod``, resolving package
    ``charter.offering``); two dots from there lands on ``charter``, so
    ``from ..activation import X`` resolves to ``charter.activation`` —
    matching the exact shape called out in this gate's authoring task. A
    module-level scan (matching only ``node.module`` on absolute imports,
    the shape the copied ``specify_cli`` template uses) would silently miss
    this, because ``node.module`` here is ``"activation"``, not
    ``"charter.activation"`` — only level-aware resolution catches it.
    """
    offering = tmp_path / "charter" / "offering"
    offering.mkdir(parents=True)
    (offering / "mod.py").write_text(
        "from ..activation import ActivationEngine\n",
        encoding="utf-8",
    )

    violations = collect_activation_imports(offering, tmp_path)

    assert violations == [("charter/offering/mod.py", 1, "charter.activation")]


def test_walker_catches_deeply_nested_relative_activation_import(tmp_path: Path) -> None:
    """Non-vacuity: a *nested* relative import (``offering/sub/mod.py``) IS caught.

    Two directories below ``charter`` needs three dots, not two, to reach
    ``charter.activation`` (verified against
    ``importlib.util.resolve_name("...activation", "charter.offering.sub")``
    == ``"charter.activation"``; two dots from this depth resolves to
    ``charter.offering.activation`` instead, a different — non-forbidden —
    target). This proves the resolver is depth-correct, not merely counting
    dots: it walks ``level`` against the file's *actual* package location,
    which is exactly what a module-body-only or fixed-level scan would get
    wrong the moment a real offering/ subpackage nests this deep.
    """
    nested = tmp_path / "charter" / "offering" / "sub"
    nested.mkdir(parents=True)
    (nested / "mod.py").write_text(
        "from ...activation import ActivationEngine\n",
        encoding="utf-8",
    )

    violations = collect_activation_imports(tmp_path / "charter" / "offering", tmp_path)

    assert violations == [("charter/offering/sub/mod.py", 1, "charter.activation")]


def test_walker_catches_module_none_relative_alias_import(tmp_path: Path) -> None:
    """Non-vacuity: ``from . import activation`` (module=None, alias) IS caught.

    Covers the ``ast.ImportFrom.module is None`` shape — where the
    forbidden package name only appears as an imported *alias*, not as
    ``node.module`` — that a naive "check ``node.module``" implementation
    would miss entirely.
    """
    charter = tmp_path / "charter"
    charter.mkdir(parents=True)
    (charter / "offering_sibling.py").write_text(
        "from . import activation\n",
        encoding="utf-8",
    )

    violations = collect_activation_imports(charter, tmp_path)

    assert violations == [("charter/offering_sibling.py", 1, "charter.activation")]


def test_walker_ignores_clean_offering_and_activation_imports(tmp_path: Path) -> None:
    """No false positives: offering importing offering, activation importing offering.

    ``charter.activation`` -> ``charter.offering`` is the *allowed*
    direction (C-004); this must never be flagged by a gate that only
    forbids the reverse. Also checks same-package relative imports (which
    stay inside ``offering`` and never touch ``activation``) and an
    unrelated same-prefix package name are not false-flagged.
    """
    offering = tmp_path / "charter" / "offering"
    offering.mkdir(parents=True)
    (offering / "reader.py").write_text(
        '"""Docstring mentioning charter.activation, which is not an import."""\n'
        "from __future__ import annotations\n"
        "\n"
        "from charter.offering.model import Snapshot\n"
        "from . import sibling\n"
        "from .sibling import helper\n"
        "import charter.activation_log\n"
        "\n"
        "# from charter.activation import X  <- a comment, not an import\n"
        'PATH = "src/charter/activation"\n',
        encoding="utf-8",
    )

    activation = tmp_path / "charter" / "activation"
    activation.mkdir(parents=True)
    (activation / "engine.py").write_text(
        "from charter.offering.model import Snapshot\nfrom ..offering import reader\n",
        encoding="utf-8",
    )

    assert collect_activation_imports(offering, tmp_path) == []
    assert collect_activation_imports(activation, tmp_path) == []


def test_importing_offering_does_not_drag_activation_layer() -> None:
    """MAP-B / #3803 invariant: importing ``charter.offering`` must load zero
    ``charter.activation.*`` modules.

    The M2 relocation put ``charter.offering.*`` under the ``charter`` package,
    so importing any offering submodule first runs ``charter/__init__.py``.
    When that ``__init__`` eagerly re-exported the activation API, the first
    parallel import of ``charter.offering.base`` could deadlock
    (``_DeadlockError``, #3803). MAP-B made ``__init__`` lazy (PEP-562), so the
    activation layer is no longer dragged in transitively.

    This is a *direct* guard on that invariant — run in a clean interpreter so
    no earlier test's imports mask a regression. It fails loudly ("activation
    was dragged") rather than through a second-order roster corruption.
    """
    src = Path(__file__).resolve().parents[2] / "src"
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(src), env.get("PYTHONPATH", "")])
    probe = (
        "import sys, charter.offering, charter.offering.base, charter.offering.drg.models;"
        "dragged = sorted(m for m in sys.modules"
        " if m == 'charter.activation' or m.startswith('charter.activation.'));"
        "print('\\n'.join(dragged))"
    )
    result = subprocess.run(  # noqa: S603 — fixed argv, no shell
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    dragged = [line for line in result.stdout.splitlines() if line.strip()]
    assert not dragged, f"importing charter.offering.* dragged in the activation layer (MAP-B/#3803 regression): {dragged}"
