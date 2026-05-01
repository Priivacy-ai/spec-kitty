"""Tests for kernel.glossary_runner — protocol and registry.

Covers:
- Protocol structural check (GlossaryRunnerProtocol)
- register() / get_runner() round-trip
- Idempotent re-registration of the same class
- Conflicting registration raises RuntimeError
- clear_registry() resets state for test isolation
- get_runner() returns None when nothing is registered
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import kernel.glossary_runner as gr
from kernel.glossary_runner import (
    GlossaryRunnerProtocol,
    clear_registry,
    get_runner,
    register,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MinimalRunner:
    """Minimal class satisfying GlossaryRunnerProtocol."""

    def __init__(
        self,
        repo_root: Path,
        runtime_strictness: Any | None = None,
        interaction_mode: str = "interactive",
    ) -> None:
        self.repo_root = repo_root

    def execute(
        self,
        primitive_fn: Any,
        context: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return primitive_fn(context, *args, **kwargs)


class _AnotherRunner(_MinimalRunner):
    """A second distinct runner class for conflict tests."""


@pytest.fixture(autouse=True)
def _clean_registry() -> None:  # type: ignore[return]
    """Ensure the registry is reset before and after every test."""
    clear_registry()
    yield
    clear_registry()


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestGlossaryRunnerProtocol:
    def test_minimal_runner_satisfies_protocol(self) -> None:
        """_MinimalRunner is recognised as a GlossaryRunnerProtocol instance."""
        runner = _MinimalRunner(repo_root=Path("/tmp"))
        assert isinstance(runner, GlossaryRunnerProtocol)

    def test_plain_object_does_not_satisfy_protocol(self) -> None:
        """An object missing execute() is not a valid runner."""

        class _Bad:
            def __init__(self, repo_root: Path, **_kw: Any) -> None:
                pass

        bad = _Bad(repo_root=Path("/tmp"))
        assert not isinstance(bad, GlossaryRunnerProtocol)


# ---------------------------------------------------------------------------
# get_runner before registration
# ---------------------------------------------------------------------------


class TestGetRunnerUnregistered:
    def test_returns_none_when_nothing_registered(self) -> None:
        """get_runner() returns None before any registration."""
        assert get_runner() is None


# ---------------------------------------------------------------------------
# register + get_runner
# ---------------------------------------------------------------------------


class TestRegister:
    def test_register_and_retrieve(self) -> None:
        """Registered class is returned by get_runner()."""
        register(_MinimalRunner)
        assert get_runner() is _MinimalRunner

    def test_register_non_class_raises_type_error(self) -> None:
        """Passing an instance instead of a class raises TypeError."""
        instance = _MinimalRunner(repo_root=Path("/tmp"))
        with pytest.raises(TypeError, match="must be a class"):
            register(instance)  # type: ignore[arg-type]

    def test_idempotent_same_class(self) -> None:
        """Registering the same class twice is a no-op (no error)."""
        register(_MinimalRunner)
        register(_MinimalRunner)  # should not raise
        assert get_runner() is _MinimalRunner

    def test_different_class_raises_runtime_error(self) -> None:
        """Registering a *different* class after one is already registered raises."""
        register(_MinimalRunner)
        with pytest.raises(RuntimeError, match="already registered"):
            register(_AnotherRunner)

    def test_after_clear_new_class_can_be_registered(self) -> None:
        """After clear_registry(), a new class can be registered."""
        register(_MinimalRunner)
        clear_registry()
        register(_AnotherRunner)
        assert get_runner() is _AnotherRunner


# ---------------------------------------------------------------------------
# clear_registry
# ---------------------------------------------------------------------------


class TestClearRegistry:
    def test_clear_resets_to_none(self) -> None:
        """clear_registry() sets registry back to None."""
        register(_MinimalRunner)
        clear_registry()
        assert get_runner() is None

    def test_clear_on_empty_is_safe(self) -> None:
        """Calling clear_registry() when nothing is registered is a no-op."""
        clear_registry()  # should not raise
        assert get_runner() is None


# ---------------------------------------------------------------------------
# Integration: registered runner is callable and executes primitives
# ---------------------------------------------------------------------------


class TestRunnerExecution:
    def test_registered_runner_executes_primitive(self) -> None:
        """Runner obtained from registry correctly executes a primitive."""
        register(_MinimalRunner)
        runner_cls = get_runner()
        assert runner_cls is not None

        calls: list[Any] = []

        def primitive(ctx: Any) -> str:
            calls.append(ctx)
            return "done"

        runner = runner_cls(repo_root=Path("/tmp"))
        result = runner.execute(primitive, "my-context")

        assert result == "done"
        assert calls == ["my-context"]


# ---------------------------------------------------------------------------
# T015: Kill register() TypeError-message survivors (WP03)
# ---------------------------------------------------------------------------


class TestRegisterTypeErrorMessageIdentifiesInput:
    """Pin the TypeError message to identify the actual bad argument.

    Kills __mutmut_3 (type(runner_cls) -> type(None) in the f-string): the
    mutant produces the constant string "<class 'NoneType'>" for every bad
    input, hiding the caller's mistake. The original reports the real
    runtime type of the argument so the caller can see what they passed.
    """

    def test_type_error_reports_string_input_type(self) -> None:
        """Passing a str produces a message mentioning <class 'str'>, not NoneType."""
        with pytest.raises(TypeError) as exc_info:
            register("not-a-class")  # type: ignore[arg-type]

        message = str(exc_info.value)
        assert "<class 'str'>" in message, (
            f"expected str type identifier in error, got {message!r}"
        )
        assert "NoneType" not in message, (
            f"error must not misreport bad input as NoneType; got {message!r}"
        )

    def test_type_error_reports_int_input_type(self) -> None:
        """Passing an int produces a message mentioning <class 'int'>.

        Bi-Directional evidence: a second concrete non-None input further
        proves the type() call uses the runtime argument, not the literal
        None the mutant substitutes.
        """
        with pytest.raises(TypeError) as exc_info:
            register(42)  # type: ignore[arg-type]

        message = str(exc_info.value)
        assert "<class 'int'>" in message, (
            f"expected int type identifier in error, got {message!r}"
        )
        assert "<class 'NoneType'>" not in message

    def test_type_error_reports_instance_input_type(self) -> None:
        """Passing an instance (not a class) shows the instance's class name."""
        instance = _MinimalRunner(repo_root=Path("/tmp"))
        with pytest.raises(TypeError) as exc_info:
            register(instance)  # type: ignore[arg-type]

        message = str(exc_info.value)
        # The instance's runtime type is _MinimalRunner, so the message
        # must include that class's name — not NoneType.
        assert "_MinimalRunner" in message
        assert "NoneType" not in message
