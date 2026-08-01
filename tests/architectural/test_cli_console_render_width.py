"""FR-003 (#3115): no live ``CliConsole`` renders narrower than the identifiers
under assertion, and a future test cannot reintroduce a narrow surface silently.

WP02's ``_plain_cli_console_seam`` (``tests/conftest.py:307-...``) pins the two
named module-level singletons -- ``specify_cli.cli.console.console`` /
``err_console`` (``console.py:126-127``) -- to an explicit ``(width, height)``
so ``rich.console.Console.size``'s ``is_dumb_terminal`` early return (which
hard-codes ``ConsoleDimensions(80, 25)``, ignoring ``COLUMNS`` entirely) never
fires for them. This module is the durable guard that a *future* change
cannot silently narrow that pin back down, or remove it, without a red build.

Design decision, stated plainly (the mission text describes the check as
"renders narrower than the longest identifier under assertion", which taken
as a bare numeric comparison against ``len(identifier)`` can never fire in
practice -- ``rich``'s own floor for a non-explicit-size console is 80
columns in every reachable code path (``is_dumb_terminal`` -> hard-coded 80;
the OS-terminal-size/``COLUMNS`` fallback -> ``width or 80``), and 80 is
never narrower than the current 36-character identifier. A guard that only
ever compares ``size.width >= 36`` therefore could not distinguish the seam
being on from the seam being off -- both leave every singleton comfortably
above 36, so a numeric-only check would be a guard that can never legitimately
red, which fails the mission's own "red first" requirement (T008) before it
starts. Instead this guard operationalises "renders narrower than the
identifier" the way the actual defect operationalises it: it asks whether the
identifier SURVIVES a render, at the console's own measured size, shaped like
the row that actually folds it (``sync.py:1429-1436``'s ``Project`` column,
``overflow="fold"``, sitting beside narrower sibling columns) -- a functional
fold-check rather than a bare inequality. `_render_identifier_survives`'s own
non-vacuity test below proves this discriminates the measured failing width
(80) from the FR-002 shipped width (240) before anything else here is
trusted (the "control your diagnostic" standing rule). The check never
touches the live console under test -- it clones its measured ``(width,
height)`` onto a throwaway, file-backed ``Console`` -- so inspecting a
console never mutates it (H8: this guard detects and fails, it does not
repair).
"""

from __future__ import annotations

import importlib
import warnings
from io import StringIO
from typing import Any

import pytest
from rich.console import Console
from rich.table import Table

pytestmark = pytest.mark.architectural

# The longest identifier any live #3115 test asserts a contiguous substring
# match on today -- the 36-character project uuid
# (`tests/cli/commands/test_sync_status_per_project_3030.py` /
# `test_sync_doctor_per_project_3030.py`). A module constant, not derived from
# scanning the live test tree: deriving it automatically would make this
# guard's own behaviour depend on every future test file's content, which is
# the opposite of a stable regression guard. Grows only when a future FR
# raises the bar, by editing this line.
_LONGEST_ASSERTED_IDENTIFIER = "aaaaaaaa-0000-0000-0000-000000000001"
assert len(_LONGEST_ASSERTED_IDENTIFIER) == 36, (  # golden-count: cardinality-is-contract
    "the identifier fixture drifted from the documented 36-character length"
)

# Two `CliConsole` instances constructed INSIDE FUNCTIONS -- they come into
# existence only when their owning function actually runs, so no setup-time
# walk of `CliConsole._instances` (this guard's own mechanism, or WP02's
# seam) can ever reach them. Printed as a NAMED gap on every run, pass or
# fail (FR-003: "the gap is printed on the passing path, so it is visible in
# a green run rather than only in a red one").
_UNREACHABLE_FUNCTION_CONSTRUCTED_CONSOLES = (
    "src/specify_cli/cli/helpers.py:234 -- CliConsole(stderr=True, "
    "color_system=_color) constructed inside the compat-nag renderer",
    "src/specify_cli/cli/logging_bootstrap.py:92 -- CliConsole(stderr=True, "
    "highlight=False) constructed inside _build_handler()",
)


def _render_identifier_survives(width: int, height: int) -> tuple[bool, str]:
    """Would a console measuring ``(width, height)`` keep the identifier intact?

    Reproduces the SHAPE of the measured #3115 defect (``sync.py:1429-1436``
    ``_per_project_store_table``: a ``Project`` column with
    ``overflow="fold"`` beside three narrower columns) on a throwaway
    ``Console`` sized like the instance under test, using representative
    stand-in content (an event count, an ISO timestamp, a consent label) --
    not ``sync.py``'s real report objects, so this guard stays decoupled from
    ``sync``/``delivery`` internals whose own tests (FR-001/FR-004) already
    exercise the real path directly.
    """
    buf = StringIO()
    probe = Console(
        file=buf, width=width, height=height, no_color=True, legacy_windows=False
    )
    table = Table(show_header=True, box=None)
    table.add_column("Project", style="dim", overflow="fold")
    table.add_column("Events", justify="right")
    table.add_column("Oldest", overflow="fold")
    table.add_column("Consent", overflow="fold")
    table.add_row(
        _LONGEST_ASSERTED_IDENTIFIER, "7", "2026-07-01T00:00:00Z", "denied (opted_out)"
    )
    probe.print(table)
    rendered = buf.getvalue()
    return _LONGEST_ASSERTED_IDENTIFIER in rendered, rendered


def _rot_control_errors(console_module: Any) -> list[str]:
    """Diagnose whether the reach mechanism this guard depends on is intact.

    Rot control (FR-003): if ``CliConsole._instances`` (the same weak set
    ``set_all_plain`` walks, ``console.py:49``) or either named singleton is
    renamed, moved or deleted, this guard must not silently report "0
    consoles inspected, nothing to fail on" -- it must say exactly what
    broke. Pure function (no ``pytest.fail`` inside) so it is directly
    testable against a planted stand-in, per the "control your diagnostic"
    standing rule -- see ``test_rot_control_bites_on_a_planted_rotted_module``.
    """
    errors: list[str] = []
    cli_console_cls = getattr(console_module, "CliConsole", None)
    if cli_console_cls is None or not hasattr(cli_console_cls, "_instances"):
        errors.append(
            "CliConsole._instances is absent -- the WeakSet this guard walks "
            "(console.py:49) was renamed, moved or deleted."
        )
    for name in ("console", "err_console"):
        if not hasattr(console_module, name):
            errors.append(
                f"specify_cli.cli.console.{name} is absent -- the named "
                "singleton the positive control asserts on by identity was "
                "renamed, moved or deleted."
            )
    return errors


def _report(request: pytest.FixtureRequest, lines: list[str]) -> None:
    """Emit report lines so they survive CI's actual invocation, not just `-s`.

    T009 requires the gap/inspected-count/specials report "printed on the
    passing path, so it is visible in a green run rather than only in a red
    one" -- but the arch-adversarial job runs `-q --tb=short -n auto --dist
    loadfile` (``ci-quality.yml:2031-2039``), and BOTH a bare ``print()`` AND
    a direct ``terminalreporter.write_line()`` call are lost under that
    invocation: a bare ``print`` is swallowed by pytest's per-test output
    capture under ``-q`` (only surfaces locally with ``-rA``/``-s``, not what
    CI passes), and ``write_line`` reaches only the process that owns it --
    under ``-n auto`` each test runs in an ``xdist`` WORKER subprocess, which
    has no terminal of its own and forwards only structured reports (test
    outcomes, warnings) back to the master over IPC, not raw terminal
    writes, so a worker-side ``write_line`` call is silently dropped
    (measured directly: 0 occurrences under ``-n auto --dist loadfile -q
    --tb=short``, confirming the concern raised in review). ``warnings.warn``
    IS one of the structured channels xdist forwards -- pytest's warning
    plugin collects warnings per-worker and replays them into the master's
    "warnings summary" -- so it is the one mechanism measured to survive
    every CI-shaped invocation (single-process AND ``-n auto``).
    """
    reporter = request.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        for line in lines:
            reporter.write_line(line)
    else:  # pragma: no cover - fallback when the reporter plugin is disabled
        for line in lines:
            print(line)
    warnings.warn("\n".join(lines), stacklevel=1)


def _known_specials(console_module: Any) -> dict[int, tuple[str, int, Any]]:
    """Import the three deliberately-sized specials and map them by identity.

    They are module-level singletons, constructed at import time -- importing
    their owning modules here is the only way to guarantee they are present
    in ``CliConsole._instances`` when this file is run standalone (the shape
    ``T009``'s evidence-gathering command uses). Keyed by ``id(instance)``
    rather than by declared width: ``glossary.py`` and ``docs.py`` both
    declare ``width=120``, so width alone cannot disambiguate them.
    """
    list_cmd = importlib.import_module("specify_cli.cli.commands.charter.list_cmd")
    glossary = importlib.import_module("specify_cli.cli.commands.glossary")
    docs = importlib.import_module("specify_cli.cli.commands.docs")
    return {
        id(list_cmd._wide_console): (
            "src/specify_cli/cli/commands/charter/list_cmd.py:26",
            200,
            list_cmd._wide_console,
        ),
        id(glossary.console): (
            "src/specify_cli/cli/commands/glossary.py:46",
            120,
            glossary.console,
        ),
        id(docs.console): (
            "src/specify_cli/cli/commands/docs.py:43",
            120,
            docs.console,
        ),
    }


def test_render_identifier_survives_discriminates_width_80_from_240() -> None:
    """Control the diagnostic before trusting it (standing rule).

    The fold-detector must bite at the measured failing width -- 80, the
    hard-coded floor ``is_dumb_terminal`` returns whenever a console has no
    explicit size -- and clear the FR-002 shipped width (240). A detector
    that cannot separate these two cannot discriminate anything downstream.
    """
    survives_80, rendered_80 = _render_identifier_survives(80, 25)
    assert not survives_80, (
        "the fold-detector did not bite at width 80 -- it cannot discriminate "
        f"anything. Rendered:\n{rendered_80}"
    )
    survives_240, rendered_240 = _render_identifier_survives(240, 50)
    assert survives_240, (
        "the fold-detector rejected the FR-002 shipped width (240) -- false "
        f"positive. Rendered:\n{rendered_240}"
    )


def test_rot_control_bites_on_a_planted_rotted_module() -> None:
    """Non-vacuity for the rot control: a stand-in missing the reach mechanism
    must be flagged, and the real module must not be.
    """

    class _RottedConsoleModule:
        """Stands in for `specify_cli.cli.console` with everything renamed away."""

    rotted_errors = _rot_control_errors(_RottedConsoleModule())
    assert rotted_errors == [
        "CliConsole._instances is absent -- the WeakSet this guard walks "
        "(console.py:49) was renamed, moved or deleted.",
        "specify_cli.cli.console.console is absent -- the named singleton "
        "the positive control asserts on by identity was renamed, moved or "
        "deleted.",
        "specify_cli.cli.console.err_console is absent -- the named "
        "singleton the positive control asserts on by identity was renamed, "
        "moved or deleted.",
    ]

    real_module = importlib.import_module("specify_cli.cli.console")
    assert _rot_control_errors(real_module) == []


def _name_for(instance: Any, console_module: Any) -> str:
    """Best-effort identifying label for a live ``CliConsole`` under the
    strict check. The two named singletons get their canonical dotted path;
    anything else (today: nothing -- see the review note above the strict
    loop below) gets an id/file-based label so a FUTURE narrow console still
    reds with something a reader can trace, rather than reporting a bare
    number nobody can act on.
    """
    if instance is console_module.console:
        return "specify_cli.cli.console.console"
    if instance is console_module.err_console:
        return "specify_cli.cli.console.err_console"
    return f"<unnamed live CliConsole id={id(instance)} file={instance.file!r}>"


def test_no_named_singleton_renders_narrower_than_the_longest_asserted_identifier(
    request: pytest.FixtureRequest,
) -> None:
    """The guard proper (FR-003).

    Positive control (T009): asserts BY OBJECT IDENTITY that
    ``specify_cli.cli.console.console`` and ``err_console`` were both found in
    ``CliConsole._instances`` -- a non-zero inspected count alone is
    satisfiable by the three exempted specials with both singletons absent
    (post-plan squad, F1), so the identity check is the load-bearing
    assertion, not the count.

    Reports (emitted through the terminal reporter on BOTH the passing and
    the failing path, per FR-003 -- see ``_report``'s docstring for why a
    bare ``print`` does not survive CI's actual ``-q`` invocation): the
    inspected count; the longest asserted identifier length; the exempted
    specials by ``module:line`` with their EFFECTIVE ``size.width`` (not
    their declared ``_width`` -- the residual finding recorded in
    ``kitty-specs/verification-trust-3115-01KYVYWM/notes/residual-render-width-coverage.md``:
    all three specials carry ``_height=None``, so rich's explicit-size early
    return never fires for them and they render at 80 columns under
    ``TERM=dumb FORCE_COLOR=1`` regardless of their declared width; a guard
    reading declared ``_width`` would print a healthy-looking 200/120/120
    while being vacuous about exactly the consoles the residual is about --
    on a normal invocation with no ``FORCE_COLOR`` set, declared and
    effective happen to coincide, since nothing then overrides the explicit
    width); and the two function-constructed consoles this guard cannot
    reach, as a named gap.

    Disposition of the exempted specials (design decision, stated plainly):
    they are reported, never asserted on -- and ONLY the three of them are
    exempt, by object identity, not "everything except two singletons". FR-002
    and the post-plan squad's F1 finding both require these three specifically
    to be exempt from the seam's own pin, and the residual above records --
    as a DEFERRED, known-red consequence outside this mission's scope (C-001
    forbids the `src/` change that would give them an explicit height) --
    that they are genuinely narrow on the failing path. Folding them into
    this guard's pass/fail predicate would either (a) make this guard red
    permanently for a defect this mission explicitly declines to fix here,
    which teaches "ignore this guard's red", or (b) require this guard to
    special-case away exactly the residual it exists to keep honest.
    Reporting their true effective width, unconditionally, is the version of
    "detect, don't repair" that fits a console this WP is not allowed to
    widen either. Every OTHER live instance -- today none, but a FUTURE
    module-level ``CliConsole()`` would join the WeakSet -- is NOT exempt:
    the strict loop below iterates `snapshot` minus the three id-pinned
    specials, not a hard-coded 2-tuple, so a fourth narrow console reds
    instead of silently moving the printed count.
    """
    console_module = importlib.import_module("specify_cli.cli.console")
    rot_errors = _rot_control_errors(console_module)
    assert not rot_errors, (
        "FR-003 rot control tripped -- no verdict about console width may be "
        "drawn from this run:\n" + "\n".join(rot_errors)
    )

    specials = _known_specials(console_module)
    exempt_special_ids = set(specials.keys())

    snapshot = list(console_module.CliConsole._instances)
    inspected_count = len(snapshot)
    snapshot_ids = {id(instance) for instance in snapshot}

    seen_console = id(console_module.console) in snapshot_ids
    seen_err_console = id(console_module.err_console) in snapshot_ids

    # --- Report: emitted unconditionally, pass or fail, through the
    # terminal reporter so it survives CI's `-q --tb=short -n auto` capture
    # (a bare `print()` would not -- see `_report`).
    report_lines = [
        f"FR-003 width guard: {inspected_count} live CliConsole instance(s) inspected",
        "FR-003 width guard: longest asserted identifier length = "
        f"{len(_LONGEST_ASSERTED_IDENTIFIER)}",
    ]
    for special_id, (location, declared_width, instance) in specials.items():
        found = special_id in snapshot_ids
        effective_width, effective_height = instance.size
        report_lines.append(
            f"FR-003 width guard: exempted special {location} -- declared "
            f"width={declared_width}, EFFECTIVE size=({effective_width}, "
            f"{effective_height}), in _instances={found}"
        )
    for gap in _UNREACHABLE_FUNCTION_CONSTRUCTED_CONSOLES:
        report_lines.append(
            f"FR-003 width guard: named gap (unreachable by any setup-time walk) -- {gap}"
        )
    _report(request, report_lines)

    # --- Positive control (T009): named singletons, not a count --------
    assert seen_console, (
        "FR-003: specify_cli.cli.console.console was NOT found in "
        f"CliConsole._instances ({inspected_count} instance(s) inspected total). "
        "A non-zero inspected count is not sufficient -- the positive control "
        "requires seeing THIS singleton by object identity (post-plan squad, F1)."
    )
    assert seen_err_console, (
        "FR-003: specify_cli.cli.console.err_console was NOT found in "
        f"CliConsole._instances ({inspected_count} instance(s) inspected total). "
        "A non-zero inspected count is not sufficient -- the positive control "
        "requires seeing THIS singleton by object identity (post-plan squad, F1)."
    )

    # --- The width guard itself: detect and fail, never repair (H8) ----
    # Every live instance EXCEPT the three id-pinned specials is strictly
    # checked -- not a hard-coded (console, err_console) pair. Today the
    # difference set is exactly {console, err_console} (`grep -rn
    # "CliConsole(" src/` finds exactly 7 sites, all seven accounted for
    # between the two singletons, the three specials and the two named
    # gaps), so this changes no behaviour today; it means a FUTURE
    # module-level `CliConsole()` reds here instead of silently widening the
    # unasserted remainder of `_instances`.
    failures: list[str] = []
    for instance in snapshot:
        if id(instance) in exempt_special_ids:
            continue
        width, height = instance.size
        survives, rendered = _render_identifier_survives(width, height)
        if not survives:
            name = _name_for(instance, console_module)
            failures.append(
                f"{name} measures size.width={width} (size.height={height}); "
                f"the {len(_LONGEST_ASSERTED_IDENTIFIER)}-character identifier "
                "it was compared against does not survive a representative "
                f"render at that width intact (folds across lines):\n{rendered}"
            )

    assert not failures, (
        "FR-003: the following non-exempt CliConsole instance(s) render "
        "narrower than the longest identifier under assertion. Detected, "
        "not repaired (H8) -- this guard does not widen the console(s) it "
        "is watching:\n\n" + "\n\n".join(failures)
    )
