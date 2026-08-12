"""Kernel domain-agnostic sibling-path-resolution gate (FR-004, SC-002, NFR-002).

The documented dependency direction is::

    kernel (root) <- doctrine <- charter <- glossary/runtime <- specify_cli

so no module under ``src/kernel/`` may hold a string identifying ``doctrine``,
``specify_cli``, or any mission-type name -- kernel must not know the
vocabulary of the layers above it.

Why this gate exists, given ``test_layer_rules.py`` already owns a pytestarch
``LayerRule`` for the same direction (``test_kernel_does_not_import_doctrine``):
**that rule is vacuous against the violation this gate targets.** pytestarch's
``LayerRule`` resolves *import edges* — it cannot see a string-literal
``importlib.resources.files("doctrine")`` call, which is exactly the shape
``kernel.paths.get_package_asset_root()`` used before FR-004 (mission
``doctrine-consumer-surface-missions-extraction-01KZ6G6H``). Likewise
``test_charter_no_specify_cli_import.py`` (scoped to ``src/charter/``) and
``test_doctrine_wheel_closure.py`` (scoped to ``pyproject.toml`` manifest
declarations) do not cover a kernel-string-literal edge either (NFR-002) — a
gate that cannot fail on the one real violation it is nominally guarding is
worse than no gate, since it manufactures false confidence.

This module therefore mirrors ``collect_specify_cli_imports`` from
``test_charter_no_specify_cli_import.py``: it walks the **full AST**
(``ast.walk``), so an in-function, in-``try``, or f-string-embedded
occurrence is caught, not merely a module-level ``import`` statement.

Scope of the claim this gate proves (read this before citing it): it proves
zero occurrences of the literal strings ``"doctrine"``, ``"specify_cli"``, or
a mission-type name, in *code* positions (import statements, call arguments,
and f-string components) anywhere under ``src/kernel/``. Docstrings and
comments are explicitly out of scope -- ``ast`` does not expose comments at
all, and a docstring is excluded by position (the first statement of a
module/class/function body) rather than by content, so prose explaining the
boundary (e.g. "kernel/ must not import specify_cli") is never flagged. This
gate does not prove the absence of runtime coupling by other indirection
(``__import__``, environment-variable-supplied strings, etc.) -- those are
out of scope here by construction, same as the charter gate this mirrors.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_SRC = Path(__file__).resolve().parents[2] / "src"
_KERNEL_ROOT = _SRC / "kernel"

#: The exact forbidden literals (SC-002 / the mission's kernel-resolution-
#: primitive.md contract): the two upward-layer package names, plus the four
#: mission-type identifiers kernel.paths used to hard-code.
_FORBIDDEN_STRINGS = frozenset(
    {
        "doctrine",
        "specify_cli",
        "software-dev",
        "documentation",
        "research",
        "plan",
    }
)

#: Import-statement module roots that are always forbidden regardless of the
#: exact-string check above (``import doctrine.x`` never has a bare
#: ``"doctrine"`` string node, but is exactly as much of a violation).
_FORBIDDEN_IMPORT_ROOTS = frozenset({"doctrine", "specify_cli"})

#: Pre-existing violations this gate discovers but that are OUT OF SCOPE for
#: FR-004 (mission doctrine-consumer-surface-missions-extraction-01KZ6G6H,
#: WP04 -- owned_files: src/kernel/paths.py, src/doctrine/pack_paths.py,
#: src/doctrine/missions/repository.py). ``schema_utils.py`` was promoted to
#: kernel by an unrelated, already-merged mission
#: (charter-mediated-doctrine-selection-01KRTZCA, WP07); its
#: ``_resolve_schema_path`` helper names "doctrine" at BOTH exempted sites
#: below -- this gate's segment-aware ``ast.Constant`` matcher (``value ==
#: root or value.startswith(root + ".")``) now catches both, where the
#: original exact-equality matcher only caught the second:
#:
#: * line 88 -- ``files("doctrine.schemas")``, the installed-wheel resource
#:   lookup. A dotted-module-path string literal (the string-literal
#:   equivalent of ``import doctrine.schemas``) -- exactly the shape an
#:   exact-equality match cannot see, since ``"doctrine.schemas" !=
#:   "doctrine"``.
#: * line 96 -- the dev-checkout fallback path segment
#:   (``Path(__file__).resolve().parent.parent / "doctrine" / "schemas"``),
#:   an exact ``"doctrine"`` literal, already caught before this gate's
#:   segment-aware upgrade.
#:
#: This is real, disclosed, pre-existing coupling: a kernel schema-loading
#: utility loads doctrine-owned schema files, and full decoupling (relocating
#: the schemas themselves out of ``doctrine``, or injecting the resolved root
#: from a caller above kernel) is a deferred design decision -- NOT resolved
#: by this gate. Exempted here (not silently fixed, not hidden by weakening
#: the gate) so the gate stays non-vacuous for *new* violations. Full
#: decoupling is tracked as Follow-up: #3206 (retire these two exemptions once
#: the schemas are relocated or the root is injected); do not widen this set
#: for any file this WP or a future one actually owns.
_PRE_EXISTING_EXEMPTIONS = frozenset(
    {
        ("kernel/schema_utils.py", 88),
        ("kernel/schema_utils.py", 96),
    }
)


def _matches_forbidden_vocabulary(value: str) -> bool:
    """True if ``value`` IS a forbidden root, or dot-segments into one.

    Segment/prefix-aware: catches both an exact forbidden literal
    (``"doctrine"``) and a dotted-module-path literal rooted in one
    (``"doctrine.schemas"``) -- the string-literal shape
    ``importlib.resources.files("doctrine.schemas")`` uses, which is the
    literal-string equivalent of ``import doctrine.schemas`` already caught
    by the ``ast.Import``/``ast.ImportFrom`` branches below via
    ``_module_root``. A bare exact-equality check (``value in
    _FORBIDDEN_STRINGS``) misses this dotted form entirely -- exactly the
    escape this gate exists to close (see ``src/kernel/schema_utils.py:88``).
    """
    return any(value == root or value.startswith(f"{root}.") for root in _FORBIDDEN_STRINGS)


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """Return ``id()`` of every AST node that is a docstring (excluded from the scan).

    A docstring is the first statement of a Module/ClassDef/FunctionDef/
    AsyncFunctionDef body, expressed as ``ast.Expr(value=ast.Constant(str))``.
    ``ast`` does not expose comments at all, so only docstrings need explicit
    exclusion here.
    """
    docstring_ids: set[int] = set()
    scopes = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, scopes):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            docstring_ids.add(id(first.value))
    return docstring_ids


def _module_root(name: str) -> str:
    return name.split(".", 1)[0]


def _scan_file(path: Path, relative_to: Path) -> list[tuple[str, int, str]]:
    """Return ``(relative_path, lineno, detail)`` violations found in a single file."""
    found: list[tuple[str, int, str]] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstring_ids = _docstring_nodes(tree)
    rel = str(path.relative_to(relative_to))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _module_root(alias.name) in _FORBIDDEN_IMPORT_ROOTS:
                    found.append((rel, node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            if node.module and _module_root(node.module) in _FORBIDDEN_IMPORT_ROOTS:
                found.append((rel, node.lineno, f"from {node.module} import ..."))
        elif isinstance(node, ast.Constant):
            if id(node) in docstring_ids:
                continue
            if isinstance(node.value, str) and _matches_forbidden_vocabulary(node.value):
                found.append((rel, node.lineno, f"string literal {node.value!r}"))
    return found


def collect_forbidden_vocabulary(root: Path, *, relative_to: Path | None = None) -> list[tuple[str, int, str]]:
    """Return ``(relative_path, lineno, detail)`` for every violation under ``root``.

    Walks the full AST (``ast.walk``) so lazy in-function imports and
    call-argument/f-string string literals are all caught, excluding
    docstring positions. ``relative_path`` is relative to ``relative_to``
    (default: ``src/``), so this stays usable against a synthetic
    ``tmp_path`` tree in the non-vacuity tests below.
    """
    anchor = relative_to if relative_to is not None else _SRC
    found: list[tuple[str, int, str]] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        found.extend(_scan_file(path, anchor))
    return found


def test_kernel_holds_no_doctrine_or_specify_cli_vocabulary() -> None:
    """FR-004 / SC-002: no ``src/kernel/**`` module names doctrine/specify_cli/mission-types.

    This is the FR-004 / SC-002 / NFR-002 gate. It fails on module-level
    imports, in-function imports, and any exact string literal (including as
    a call argument or f-string component) matching the forbidden vocabulary.
    See ``test_walker_catches_in_function_call_argument`` for the committed
    proof that the string-literal leg is real (mirrors the charter gate's own
    NFR-004-style self-mutation discipline).

    ``_PRE_EXISTING_EXEMPTIONS`` filters out exactly one already-tracked,
    out-of-scope pre-existing site (see its own docstring) -- any *other*
    violation, including a new one at a different line of the same file,
    still reds this gate.
    """
    violations = [(rel, lineno, detail) for rel, lineno, detail in collect_forbidden_vocabulary(_KERNEL_ROOT) if (rel, lineno) not in _PRE_EXISTING_EXEMPTIONS]

    assert violations == [], (
        "src/kernel/** must hold no doctrine-/specify_cli-identifying string or "
        "mission-type vocabulary, at any scope (kernel is the root layer; "
        "FR-004, SC-002, NFR-002).\nResolve via the domain-agnostic "
        "kernel.sibling_paths.resolve_installed_sibling primitive instead, "
        "with the caller supplying its own __file__ and sibling-relative "
        "path.\nViolations:\n" + "\n".join(f"  {rel}:{lineno} — {detail}" for rel, lineno, detail in violations)
    )


def test_pre_existing_exemption_is_still_a_real_violation() -> None:
    """Anti-vacuity for the exemption itself: it must exempt a REAL finding.

    Guards against ``_PRE_EXISTING_EXEMPTIONS`` silently becoming a no-op
    (e.g. if the exempted line ever moves or the violation is fixed) without
    anyone noticing -- if that happens, this test fails as a prompt to shrink
    the exemption set, not the other way around.
    """
    unfiltered = collect_forbidden_vocabulary(_KERNEL_ROOT)
    exempted_sites = {(rel, lineno) for rel, lineno, _detail in unfiltered}

    assert exempted_sites >= _PRE_EXISTING_EXEMPTIONS, (
        "Every entry in _PRE_EXISTING_EXEMPTIONS must correspond to an actual "
        "violation collect_forbidden_vocabulary() finds today; shrink the "
        "exemption set instead of leaving a stale, vacuous entry."
    )


def test_walker_catches_in_function_call_argument(tmp_path: Path) -> None:
    """Non-vacuity (NFR-002/NFR-004): a call-argument string literal IS detected.

    Reproduces the exact shape ``kernel.paths.get_package_asset_root()`` used
    before FR-004 -- ``importlib.resources.files("doctrine")`` nested inside a
    function -- and asserts the walker flags it. Were the walker downgraded to
    a module-body-only or import-only scan (what the pre-existing pytestarch
    ``LayerRule`` effectively does), this test goes red, proving that rule's
    vacuity against this exact shape.
    """
    module = tmp_path / "paths.py"
    module.write_text(
        'import importlib.resources\n\n\ndef get_package_asset_root():\n    resource = importlib.resources.files("doctrine") / "missions"\n    return resource\n',
        encoding="utf-8",
    )

    violations = collect_forbidden_vocabulary(tmp_path, relative_to=tmp_path)

    assert violations == [("paths.py", 5, "string literal 'doctrine'")]


def test_walker_ignores_docstrings_and_prose(tmp_path: Path) -> None:
    """No false positives: docstrings/comments explaining the boundary are prose.

    Mirrors the mission's own trap #3 -- ``src/kernel/paths.py`` legitimately
    mentions "doctrine" and "specify_cli" in docstrings/comments explaining
    the layering rule (e.g. "kernel/ must not import specify_cli"); those are
    explanatory prose, not code, and must never be flagged.
    """
    (tmp_path / "clean.py").write_text(
        '"""This module about doctrine and specify_cli lives in kernel.\n\n'
        "kernel/ must not import specify_cli (architectural layer rule).\n"
        '"""\n'
        "from __future__ import annotations\n"
        "\n"
        "# import doctrine  <- a comment, not an import\n"
        "# Mirrors specify_cli.paths.render_runtime_path with identical semantics.\n"
        "\n"
        "\n"
        "def helper() -> None:\n"
        '    """Also mentions doctrine and specify_cli, but is a docstring."""\n'
        "    return None\n",
        encoding="utf-8",
    )

    assert collect_forbidden_vocabulary(tmp_path, relative_to=tmp_path) == []
