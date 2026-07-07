"""Unit tests for the canonical ``specify_cli.ast_analysis.imports`` primitives.

These pin the exact behavior each of the three former consumers relied on:

* ``module_of_import_from`` — the shared ImportFrom resolver used by both
  architectural dead-code gates.
* ``extract_static_all`` — the dead-symbols gate's whole-module ``__all__``
  reader (``None`` for dynamic, ``frozenset()`` for value-less AnnAssign,
  list/tuple only, AnnAssign-aware).
* ``import_binds_name`` / ``assignment_lists_dunder_all`` — the
  stale-assertion analyzer's per-node predicates (set-literal aware, NOT
  AnnAssign-aware, Import vs ImportFrom binding distinction).
"""

from __future__ import annotations

import ast

import pytest

from specify_cli.ast_analysis.imports import (
    assignment_lists_dunder_all,
    extract_static_all,
    import_binds_name,
    module_of_import_from,
)

pytestmark = [pytest.mark.unit]


def _first(tree: ast.Module) -> ast.stmt:
    return tree.body[0]


# ---------------------------------------------------------------------------
# module_of_import_from
# ---------------------------------------------------------------------------


class TestModuleOfImportFrom:
    def test_absolute_import(self) -> None:
        node = _first(ast.parse("from a.b.c import x"))
        assert isinstance(node, ast.ImportFrom)
        assert module_of_import_from(node, "irrelevant.pkg") == "a.b.c"

    def test_absolute_import_ignores_containing_pkg(self) -> None:
        node = _first(ast.parse("from top import y"))
        assert isinstance(node, ast.ImportFrom)
        assert module_of_import_from(node, "") == "top"

    def test_relative_level_1_from_this_package(self) -> None:
        # ``from . import x`` inside package ``specify_cli.sub`` → ``specify_cli.sub``
        node = _first(ast.parse("from . import x"))
        assert isinstance(node, ast.ImportFrom)
        assert module_of_import_from(node, "specify_cli.sub") == "specify_cli.sub"

    def test_relative_level_1_with_module(self) -> None:
        node = _first(ast.parse("from .clock import tick"))
        assert isinstance(node, ast.ImportFrom)
        assert module_of_import_from(node, "specify_cli.sync") == "specify_cli.sync.clock"

    def test_relative_level_2_trims_parent(self) -> None:
        node = _first(ast.parse("from ..other import z"))
        assert isinstance(node, ast.ImportFrom)
        # level 2 drops one trailing segment from containing pkg, then appends mod
        assert module_of_import_from(node, "a.b.c") == "a.b.other"

    def test_relative_level_2_bare(self) -> None:
        node = _first(ast.parse("from .. import z"))
        assert isinstance(node, ast.ImportFrom)
        assert module_of_import_from(node, "a.b.c") == "a.b"

    def test_relative_with_empty_containing_pkg(self) -> None:
        node = _first(ast.parse("from .mod import q"))
        assert isinstance(node, ast.ImportFrom)
        assert module_of_import_from(node, "") == "mod"


# ---------------------------------------------------------------------------
# extract_static_all (dead-symbols gate semantics)
# ---------------------------------------------------------------------------


class TestExtractStaticAll:
    def test_list_literal(self) -> None:
        tree = ast.parse('__all__ = ["Foo", "Bar"]')
        assert extract_static_all(tree) == frozenset({"Foo", "Bar"})

    def test_tuple_literal(self) -> None:
        tree = ast.parse('__all__ = ("A", "B")')
        assert extract_static_all(tree) == frozenset({"A", "B"})

    def test_typed_annassign_list(self) -> None:
        tree = ast.parse('__all__: list[str] = ["Alpha", "Beta"]')
        assert extract_static_all(tree) == frozenset({"Alpha", "Beta"})

    def test_bare_annassign_returns_empty_frozenset(self) -> None:
        # value-less AnnAssign is treated as dynamic/absent membership → empty set
        tree = ast.parse("__all__: list[str]")
        assert extract_static_all(tree) == frozenset()

    def test_non_all_annassign_before_all_is_skipped(self) -> None:
        tree = ast.parse('MESSAGES: dict[str, str] = {"x": "y"}\n__all__ = ["Foo"]')
        assert extract_static_all(tree) == frozenset({"Foo"})

    def test_dynamic_all_returns_none(self) -> None:
        tree = ast.parse("__all__ = sorted(names)")
        assert extract_static_all(tree) is None

    def test_set_literal_returns_none(self) -> None:
        # A set literal is NOT accepted by this reader (list/tuple only).
        tree = ast.parse('__all__ = {"Foo", "Bar"}')
        assert extract_static_all(tree) is None

    def test_non_string_element_returns_none(self) -> None:
        tree = ast.parse("__all__ = [Foo, Bar]")
        assert extract_static_all(tree) is None

    def test_absent_all_returns_none(self) -> None:
        tree = ast.parse("x = 1\n")
        assert extract_static_all(tree) is None


# ---------------------------------------------------------------------------
# import_binds_name (stale-assertion analyzer semantics)
# ---------------------------------------------------------------------------


class TestImportBindsName:
    @pytest.mark.parametrize(
        ("src", "name", "expected"),
        [
            # ImportFrom: direct re-export
            ("from mod import parse", "parse", True),
            # ImportFrom: renamed on import (local bound name matches)
            ("from mod import parse as _parse", "_parse", True),
            # ImportFrom: original name still matches even when aliased
            ("from mod import parse as _parse", "parse", True),
            # ImportFrom: renamed onto the target name
            ("from mod import other as parse", "parse", True),
            ("from mod import other as parse", "other", True),
            ("from mod import something_else", "parse", False),
            # Import: bare import binds top-level local name only
            ("import parse", "parse", True),
            ("import mod as parse", "parse", True),
            ("import mod as parse", "mod", False),
            # Import: dotted import binds the top-level package, not the leaf
            ("import pkg.sub", "pkg", True),
            ("import pkg.sub", "sub", False),
            ("import pkg.sub", "pkg.sub", False),
        ],
    )
    def test_binding(self, src: str, name: str, expected: bool) -> None:
        node = _first(ast.parse(src))
        assert isinstance(node, (ast.Import, ast.ImportFrom))
        assert import_binds_name(node, name) is expected


# ---------------------------------------------------------------------------
# assignment_lists_dunder_all (stale-assertion analyzer semantics)
# ---------------------------------------------------------------------------


class TestAssignmentListsDunderAll:
    def test_list_membership(self) -> None:
        node = _first(ast.parse('__all__ = ["Foo", "Bar"]'))
        assert isinstance(node, ast.Assign)
        assert assignment_lists_dunder_all(node, "Foo") is True
        assert assignment_lists_dunder_all(node, "Missing") is False

    def test_tuple_membership(self) -> None:
        node = _first(ast.parse('__all__ = ("Foo",)'))
        assert isinstance(node, ast.Assign)
        assert assignment_lists_dunder_all(node, "Foo") is True

    def test_set_membership_is_accepted(self) -> None:
        # Distinct from extract_static_all: this predicate DOES accept sets.
        node = _first(ast.parse('__all__ = {"Foo", "Bar"}'))
        assert isinstance(node, ast.Assign)
        assert assignment_lists_dunder_all(node, "Bar") is True

    def test_non_all_assignment_returns_false(self) -> None:
        node = _first(ast.parse('OTHER = ["Foo"]'))
        assert isinstance(node, ast.Assign)
        assert assignment_lists_dunder_all(node, "Foo") is False

    def test_dynamic_value_returns_false(self) -> None:
        node = _first(ast.parse("__all__ = sorted(names)"))
        assert isinstance(node, ast.Assign)
        assert assignment_lists_dunder_all(node, "Foo") is False
