"""Architectural test: safety registry completeness and fail-closed policy.

Policy being enforced
---------------------
Any CLI command that is NOT in SAFETY_REGISTRY must classify as
``Safety.UNSAFE`` — the registry is fail-closed.  This test does NOT
require every command to be registered as SAFE; it only asserts that:

1. Registered commands → Safety.SAFE  (or predicate result if callable)
2. Unregistered commands → Safety.UNSAFE  (fail-closed)
3. A hypothetical ``("explode",)`` path → Safety.UNSAFE

Walking the typer app
---------------------
The root typer app is ``specify_cli.app`` (``src/specify_cli/__init__.py``).
Commands are registered by ``register_commands(app)`` from
``specify_cli.cli.commands``.  We rebuild the full command tree here
without side-effecting the process (no actual CLI invocation).

Entry point: ``specify_cli.app`` — the ``Typer`` instance exported from
``src/specify_cli/__init__.py``, which is the same object invoked by
the ``spec-kitty`` console-script entry point.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest
import typer

from specify_cli.compat.safety import SAFETY_REGISTRY, Safety, classify


# ---------------------------------------------------------------------------
# App fixture — walk once per session for speed
# ---------------------------------------------------------------------------


def _build_app() -> typer.Typer:
    """Return the root typer app with all commands registered.

    We patch sys.argv to avoid the _is_next_fast_path short-circuit that
    would register only the ``next`` command.
    """
    # Import here to avoid module-level side-effects at collection time.
    from specify_cli import app  # type: ignore[attr-defined]
    from specify_cli.cli.commands import register_commands

    # Ensure the full command tree is registered.
    _saved = sys.argv[:]
    sys.argv = ["spec-kitty", "--help"]  # prevents fast-path shortcut
    try:
        register_commands(app)
    finally:
        sys.argv = _saved
    return app


def _walk_commands(
    typer_app: typer.Typer,
    prefix: tuple[str, ...] = (),
) -> list[tuple[str, ...]]:
    """Recursively collect all command paths from a Typer app.

    Deduplicates within each level (typer can register the same command twice
    internally in some configurations).
    """
    paths: list[tuple[str, ...]] = []
    seen_names: set[str] = set()

    for cmd in typer_app.registered_commands:
        name: str | None = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
        if name and name not in seen_names:
            seen_names.add(name)
            paths.append(prefix + (name,))

    for group in typer_app.registered_groups:
        gname: str | None = group.typer_instance.info.name
        if gname:
            paths.extend(_walk_commands(group.typer_instance, prefix + (gname,)))

    return paths


@pytest.fixture(scope="module")
def all_command_paths() -> list[tuple[str, ...]]:
    """All command paths discovered from the live typer app tree."""
    app = _build_app()
    return list(set(_walk_commands(app)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inv(command_path: tuple[str, ...]) -> SimpleNamespace:
    return SimpleNamespace(command_path=command_path, raw_args=())


# ---------------------------------------------------------------------------
# T016: Soft policy — registered ⇒ SAFE, unregistered ⇒ UNSAFE
# ---------------------------------------------------------------------------


class TestSafetyRegistryCompleteness:
    """Walk the live typer app and assert the fail-closed policy holds."""

    def test_registered_commands_in_registry_are_safe(self, all_command_paths: list[tuple[str, ...]]) -> None:
        """Commands present in SAFETY_REGISTRY must classify as SAFE.

        If a command is seeded with ``None`` it should be SAFE.  If it has a
        predicate and the predicate returns UNSAFE, this test will also catch
        that (but no seeded predicates are UNSAFE in the initial registry).
        """
        for path in all_command_paths:
            if path in SAFETY_REGISTRY:
                result = classify(_inv(path))
                assert result == Safety.SAFE, (
                    f"Registered path {path!r} classified as UNSAFE. If you added a predicate, ensure it returns SAFE for normal invocations."
                )

    def test_unregistered_commands_are_unsafe(self, all_command_paths: list[tuple[str, ...]]) -> None:
        """Commands NOT in SAFETY_REGISTRY must classify as UNSAFE (fail-closed).

        This is the core invariant: adding a new command without registering it
        should never silently grant SAFE status under schema mismatch.
        """
        for path in all_command_paths:
            if path not in SAFETY_REGISTRY:
                result = classify(_inv(path))
                assert result == Safety.UNSAFE, (
                    f"Unregistered path {path!r} classified as {result!r} instead of UNSAFE. "
                    "The safety registry is fail-closed: unregistered commands must be UNSAFE."
                )

    def test_at_least_one_safe_command_found(self, all_command_paths: list[tuple[str, ...]]) -> None:
        """Sanity check: the app exposes at least one registered-safe command."""
        safe_paths = [p for p in all_command_paths if p in SAFETY_REGISTRY]
        assert safe_paths, "No registered-safe commands found in the typer app. Either the app walk is broken or SAFETY_REGISTRY is empty."

    def test_at_least_one_unregistered_unsafe_command_found(self, all_command_paths: list[tuple[str, ...]]) -> None:
        """Sanity check: the app has commands not in SAFETY_REGISTRY (realistic)."""
        unsafe_paths = [p for p in all_command_paths if p not in SAFETY_REGISTRY]
        assert unsafe_paths, (
            "Every command in the app is in SAFETY_REGISTRY. This is suspicious — either the registry is over-seeded or the app walk is incomplete."
        )


# ---------------------------------------------------------------------------
# T016: Hypothetical unknown command is UNSAFE (dedicated assertion)
# ---------------------------------------------------------------------------


def test_hypothetical_explode_command_is_unsafe() -> None:
    """A command path not in the registry — (\"explode\",) — must be UNSAFE."""
    assert ("explode",) not in SAFETY_REGISTRY, '("explode",) is unexpectedly in SAFETY_REGISTRY — pick a different sentinel.'
    result = classify(_inv(("explode",)))
    assert result == Safety.UNSAFE


def test_empty_tuple_command_path_is_unsafe() -> None:
    """An empty command path is not in the registry and must be UNSAFE."""
    assert () not in SAFETY_REGISTRY
    result = classify(_inv(()))
    assert result == Safety.UNSAFE
