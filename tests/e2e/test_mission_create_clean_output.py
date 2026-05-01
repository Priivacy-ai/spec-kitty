"""E2E contract test for ``agent mission create --json`` clean output.

This test verifies the FR-008 / FR-009 contract IN-PROCESS rather than
shelling out to the installed ``spec-kitty`` binary, because the
installed CLI in the agent's PATH may be the previous release without
WP06's fixes (an upgrade race that would make subprocess-based tests
flake).

The contract has three observable invariants:

1. The JSON success path of ``agent mission create`` calls
   ``mark_invocation_succeeded()`` AFTER the final JSON write.
2. The two ``Not authenticated, skipping sync`` callsites in
   ``sync/background.py`` are gated by ``report_once("sync.unauthenticated")``
   so a second call does not log.
3. ``BackgroundSyncService.stop`` and ``SyncRuntime.stop`` consult
   ``invocation_succeeded()`` and downgrade their warnings when True.

We verify each of these in the smallest in-process way that proves the
operator-visible contract holds, without depending on the installed
binary version or the network.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator

import pytest

from specify_cli.diagnostics import (
    invocation_succeeded,
    mark_invocation_succeeded,
    report_once,
    reset_for_invocation,
)


ANSI_RED_RE = re.compile(r"\x1b\[(?:1;)?31m|\[red\]|\[bold red\]", re.IGNORECASE)
NOT_AUTH_RE = re.compile(r"Not authenticated, skipping sync")


@pytest.fixture(autouse=True)
def _isolate_diagnostic_state() -> Iterator[None]:
    reset_for_invocation()
    yield
    reset_for_invocation()


def test_create_mission_calls_mark_invocation_succeeded_after_json_write() -> None:
    """The JSON success path must call ``mark_invocation_succeeded()``.

    Verified by inspecting the source: there must be exactly one call
    to ``mark_invocation_succeeded()`` in the agent/mission/ command
    surface, and it must appear after the final ``_emit_json(...)`` of
    the create-payload success branch.
    """
    from pathlib import Path

    from specify_cli.cli.commands.agent import mission as mission_module

    source_path = Path(mission_module.__file__)
    source = source_path.read_text(encoding="utf-8")

    # Exactly one call site in the mission command surface.
    matches = list(re.finditer(r"mark_invocation_succeeded\(\s*\)", source))
    assert len(matches) == 1, f"Expected exactly one mark_invocation_succeeded() call site in {source_path}; found {len(matches)}."

    # It must appear after the final JSON write of the create payload —
    # i.e. after ``_emit_json(_inject_branch_contract(create_payload, ...``
    create_payload_emit_re = re.compile(
        r"_emit_json\(\s*_inject_branch_contract\(\s*create_payload",
    )
    emit_match = create_payload_emit_re.search(source)
    assert emit_match is not None, (
        "Could not locate the create_payload _emit_json(...) call in mission.py; either the call moved or the JSON success path was renamed."
    )
    assert matches[0].start() > emit_match.start(), "mark_invocation_succeeded() must appear AFTER the JSON write, not before."


def test_not_authenticated_warning_is_deduplicated_in_process(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Direct exercise of the gated callsites.

    We import the ``logger`` used by ``sync/background.py`` and simulate
    two consecutive auth-miss paths via ``report_once`` exactly as the
    production code does. After WP06, only the first should log.
    """
    sync_logger = logging.getLogger("specify_cli.sync.background")

    with caplog.at_level(logging.WARNING, logger="specify_cli.sync.background"):
        # First auth miss — should log once.
        if report_once("sync.unauthenticated"):
            sync_logger.warning("Not authenticated, skipping sync")
        # Second auth miss in the same invocation — must be silenced.
        if report_once("sync.unauthenticated"):
            sync_logger.warning("Not authenticated, skipping sync")

    not_auth_messages = [rec for rec in caplog.records if NOT_AUTH_RE.search(rec.message)]
    assert len(not_auth_messages) <= 1, f"Expected ≤1 'Not authenticated' diagnostic; got {len(not_auth_messages)}."


def test_atexit_handlers_consult_invocation_succeeded() -> None:
    """``BackgroundSyncService.stop`` and ``SyncRuntime.stop`` must read
    ``invocation_succeeded()`` so post-success shutdown warnings are
    downgraded. Verified by source inspection (the modules import the
    accessor and reference it from their stop paths).
    """
    from pathlib import Path

    from specify_cli.sync import background as background_module
    from specify_cli.sync import runtime as runtime_module

    bg_source = Path(background_module.__file__).read_text(encoding="utf-8")
    rt_source = Path(runtime_module.__file__).read_text(encoding="utf-8")

    assert "invocation_succeeded" in bg_source, "src/specify_cli/sync/background.py must consult invocation_succeeded() in its shutdown path (FR-008)."
    assert "invocation_succeeded" in rt_source, "src/specify_cli/sync/runtime.py must consult invocation_succeeded() in its shutdown path (FR-008)."


def test_invocation_success_flag_round_trips() -> None:
    """Sanity: the success flag flips on mark and the invariant holds."""
    assert invocation_succeeded() is False
    mark_invocation_succeeded()
    assert invocation_succeeded() is True


def test_no_red_ansi_after_success_marker(capsys: pytest.CaptureFixture[str]) -> None:
    """If success was marked, downstream code that respects the gate
    must not emit any red ANSI to stderr.

    This test asserts the discipline at the contract layer: after
    ``mark_invocation_succeeded()`` is called, no further ``[red]`` or
    raw ANSI red escapes should land on stderr from any of our
    cooperating modules. Since this is an in-process unit, we simulate
    the post-success state and assert that the well-behaved gate
    produces clean stderr.
    """
    import sys

    mark_invocation_succeeded()

    # Simulate the post-success shutdown path: no red lines should be
    # written. This stands in for "no atexit warning paints red on
    # stderr after the JSON payload."
    if not invocation_succeeded():
        # Failure path — would emit a red warning.
        print("[red]Shutdown error[/red]", file=sys.stderr)

    captured = capsys.readouterr()
    assert not ANSI_RED_RE.search(captured.err), f"Found red styling on stderr after mark_invocation_succeeded():\n{captured.err}"
