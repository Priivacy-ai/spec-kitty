"""Contract tests for the ``build_operational_context`` pure assembler and the
``OperationalContext`` guards (WP13, FR-017 builder / FR-018).

These tests pin three invariants:

1. ``build_operational_context`` is a *pure explicit-parameter assembler*: it
   packages exactly the values the caller passes, with no hidden state access
   and no upward imports (C-006).
2. The all-None stub behaviour is gone — the assembler now accepts and reflects
   explicit values.
3. ``require_active_profile`` / ``require_active_role`` raise
   ``ContextPreconditionError`` with *actionable* remediation text when the
   field is absent, and return the value when present.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

import charter.invocation_context as invocation_context
from charter.invocation_context import (
    ContextPreconditionError,
    OperationalContext,
    build_operational_context,
)


class TestBuildOperationalContextAssembler:
    """``build_operational_context`` packages explicit args as data."""

    def test_packages_all_explicit_values(self) -> None:
        ctx = build_operational_context(
            active_model="opus",
            active_profile="python-pedro",
            active_role="implementer",
            current_activity="implement",
            tech_stack=frozenset({"python", "pytest"}),
        )
        assert isinstance(ctx, OperationalContext)
        assert ctx.active_model == "opus"
        assert ctx.active_profile == "python-pedro"
        assert ctx.active_role == "implementer"
        assert ctx.current_activity == "implement"
        assert ctx.tech_stack == frozenset({"python", "pytest"})

    def test_partial_values_only(self) -> None:
        ctx = build_operational_context(
            active_profile="reviewer-renata", active_role="reviewer"
        )
        assert ctx.active_profile == "reviewer-renata"
        assert ctx.active_role == "reviewer"
        assert ctx.active_model is None
        assert ctx.current_activity is None
        assert ctx.tech_stack == frozenset()

    def test_tech_stack_none_normalised_to_empty_frozenset(self) -> None:
        ctx = build_operational_context(active_profile="x", tech_stack=None)
        assert ctx.tech_stack == frozenset()

    def test_tech_stack_accepts_iterable_and_freezes(self) -> None:
        ctx = build_operational_context(tech_stack=frozenset({"rust"}))
        assert ctx.tech_stack == frozenset({"rust"})

    def test_keyword_only_signature(self) -> None:
        # All parameters are keyword-only — positional calls must fail.
        with pytest.raises(TypeError):
            build_operational_context("opus")  # type: ignore[misc]

    def test_no_arg_call_returns_all_none(self) -> None:
        # Pure assembler with no inputs yields an empty context (not a hidden
        # default fetched from runtime state).
        ctx = build_operational_context()
        assert ctx.active_model is None
        assert ctx.active_profile is None
        assert ctx.active_role is None
        assert ctx.current_activity is None
        assert ctx.tech_stack == frozenset()


class TestAssemblerPurity:
    """The assembler must not reach into runtime/global state (C-006)."""

    def test_module_does_not_import_specify_cli(self) -> None:
        # Inspect actual import statements (not docstring prose) for any
        # reference to specify_cli — the charter layer must never depend
        # upward on the CLI runtime (C-006 / C-001).
        source = Path(invocation_context.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.append(node.module)
        offending = [m for m in imported_modules if m.split(".")[0] == "specify_cli"]
        assert not offending, (
            "charter.invocation_context must not import specify_cli (C-006): "
            f"{offending}"
        )

    def test_assembler_body_has_no_attribute_state_reads(self) -> None:
        # The assembler must only construct OperationalContext from its
        # parameters; it must not call into modules/objects to fetch state.
        src = inspect.getsource(build_operational_context)
        func_tree = ast.parse(src.lstrip())
        func_def = func_tree.body[0]
        assert isinstance(func_def, ast.FunctionDef)
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                callee = node.func
                # Allowed: frozenset(...) and the OperationalContext(...) ctor.
                allowed = {"frozenset", "OperationalContext"}
                if isinstance(callee, ast.Name):
                    assert callee.id in allowed, (
                        f"unexpected call to {callee.id!r} in pure assembler"
                    )
                else:  # pragma: no cover - any attribute call is a violation
                    raise AssertionError(
                        "pure assembler must not call object/module methods"
                    )


class TestGuardsActionable:
    """Guards raise ContextPreconditionError with actionable text or return."""

    def test_require_active_profile_returns_when_present(self) -> None:
        ctx = build_operational_context(active_profile="python-pedro")
        assert ctx.require_active_profile() == "python-pedro"

    def test_require_active_profile_raises_with_actionable_hint(self) -> None:
        ctx = build_operational_context()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_active_profile()
        err = exc_info.value
        assert err.field == "active_profile"
        assert err.context_type == "OperationalContext"
        # Actionable: names the field and how to provide it.
        message = str(err)
        assert "active_profile" in message
        assert "build_operational_context" in message
        assert err.hint is not None

    def test_require_active_role_returns_when_present(self) -> None:
        ctx = build_operational_context(active_role="implementer")
        assert ctx.require_active_role() == "implementer"

    def test_require_active_role_raises_with_actionable_hint(self) -> None:
        ctx = build_operational_context()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_active_role()
        err = exc_info.value
        assert err.field == "active_role"
        assert err.context_type == "OperationalContext"
        message = str(err)
        assert "active_role" in message
        assert "build_operational_context" in message
        assert err.hint is not None

    def test_error_is_runtime_error(self) -> None:
        ctx = build_operational_context()
        with pytest.raises(RuntimeError):
            ctx.require_active_profile()

    def test_hint_optional_for_other_guards(self) -> None:
        # Errors raised without a hint keep the base message unchanged.
        err = ContextPreconditionError(field="x", context_type="Y")
        assert err.hint is None
        assert str(err) == (
            "Context precondition failed: 'x' is required but absent in Y"
        )
