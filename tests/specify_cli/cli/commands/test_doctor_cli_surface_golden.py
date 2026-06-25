"""Golden characterization of the ``spec-kitty doctor`` CLI surface (WP01, #2059).

This is the single objective proof that the public ``doctor`` surface stays
byte-identical across the god-module decomposition (FR-001, FR-002, C-005, I-1).
It MUST pass at HEAD against the un-refactored ``doctor.py`` and is re-run by
every subsequent extraction WP.

It pins, independently of the implementation source:

* the exact set of 16 registered subcommand names (set-equality, order-free);
* each subcommand's option flags + arity (flag/value/multi);
* each subcommand's ``--help`` body (whitespace-normalized snapshot);
* the documented exit-code contracts, including the three load-bearing names
  (``skills``, ``restart-daemon``, ``sparse-checkout``) that ``compat`` safety
  predicates and ``__init__`` argv fast-paths key on (I-7).

The help snapshots are normalized (box-drawing stripped, lines trimmed, blanks
dropped) so they are deterministic across terminal widths while still failing
on any usage/description/flag/help-text drift.
"""

from __future__ import annotations

import os
import re

import click
import pytest
from typer.main import get_command
from typer.testing import CliRunner

from specify_cli.cli.commands.doctor import app

pytestmark = [pytest.mark.fast]

# --- Frozen contract: the 16 subcommand names (cli-surface-contract.md) -------

FROZEN_SUBCOMMANDS: frozenset[str] = frozenset(
    {
        "command-files",
        "skills",
        "tool-surfaces",
        "state-roots",
        "workspaces",
        "identity",
        "topology",
        "sparse-checkout",
        "shim-registry",
        "invocation-pairing",
        "ops",
        "orphan-daemons",
        "restart-daemon",
        "mission-state",
        "doctrine",
        "coordination",
    }
)

# Frozen option contract per subcommand: name -> {flag: ("flag" | "value" | "multi")}.
# "flag" = boolean switch (is_flag), "value" = takes one value, "multi" = repeatable.
EXPECTED_OPTIONS: dict[str, dict[str, str]] = {
    "command-files": {"--json": "flag"},
    "skills": {"--fix": "flag", "--json": "flag"},
    "tool-surfaces": {
        "--kind": "multi",
        "--tool": "value",
        "--fix": "flag",
        "--json": "flag",
    },
    "state-roots": {"--json": "flag"},
    "workspaces": {"--fix": "flag", "--json": "flag"},
    "identity": {"--json": "flag", "--mission": "value", "--fail-on": "value"},
    "topology": {"--json": "flag", "--mission": "value"},
    "sparse-checkout": {"--fix": "flag"},
    "shim-registry": {"--json": "flag"},
    "invocation-pairing": {"--json": "flag"},
    "ops": {"--json": "flag", "--close-stale": "flag", "--threshold": "value"},
    "orphan-daemons": {"--json": "flag"},
    "restart-daemon": {"--json": "flag"},
    "mission-state": {
        "--audit": "flag",
        "--fix": "flag",
        "--teamspace-dry-run": "flag",
        "--json": "flag",
        "--mission": "value",
        "--fail-on": "value",
        "--fixture-dir": "value",
        "--include-fixtures": "flag",
        "--manifest-path": "value",
        "--allow-dirty": "flag",
    },
    "doctrine": {"--json": "flag"},
    "coordination": {"--json": "flag"},
}

# Golden ``--help`` snapshots (whitespace-normalized) per subcommand.
EXPECTED_HELP: dict[str, list[str]] = {
    'command-files': [
        'Usage: doctor command-files [OPTIONS]',
        'Check all agent command files for correctness.',
        'Verifies that every configured agent has the correct command files:',
        '- Full rendered prompts for prompt-driven commands (specify, plan, tasks, ...)',
        '- Thin shims for CLI-driven commands (implement, review, merge, ...)',
        '- Current version markers on all files',
        'Examples:',
        'spec-kitty doctor command-files',
        'spec-kitty doctor command-files --json',
        'Options',
        '--json          Machine-readable JSON output',
        '--help          Show this message and exit.',
    ],
    'skills': [
        'Usage: doctor skills [OPTIONS]',
        'Check command-skill manifest drift for Codex, Vibe, Pi, and Letta.',
        'Options',
        '--fix           Repair missing command-skill files',
        '--json          Machine-readable JSON output',
        '--help          Show this message and exit.',
    ],
    'tool-surfaces': [
        'Usage: doctor tool-surfaces [OPTIONS]',
        'Audit (and optionally repair) every configured tool surface.',
        'Examples:',
        'spec-kitty doctor tool-surfaces --json',
        'spec-kitty doctor tool-surfaces --kind command-skill --json',
        'spec-kitty doctor tool-surfaces --tool codex --fix',
        'Options',
        '--kind        TEXT  Filter to surface kind(s), e.g. command-skill',
        '--tool        TEXT  Filter to a single configured tool key',
        '--fix               Repair missing or stale surfaces',
        '--json              Machine-readable JSON output',
        '--help              Show this message and exit.',
    ],
    'state-roots': [
        'Usage: doctor state-roots [OPTIONS]',
        'Show state roots, surface classification, and safety warnings.',
        'Displays the three state roots with resolved paths, all registered',
        'state surfaces grouped by root with authority and Git classification,',
        'and warnings for any runtime surfaces not covered by .gitignore.',
        'Examples:',
        'spec-kitty doctor state-roots',
        'spec-kitty doctor state-roots --json',
        'Options',
        '--json          Machine-readable JSON output',
        '--help          Show this message and exit.',
    ],
    'workspaces': [
        'Usage: doctor workspaces [OPTIONS]',
        'Report .worktrees/ husk directories (entries lacking a .git entry).',
        'A husk is not a usable git worktree: git commands run inside it fall',
        'through to the primary repository (#1833). Workspace resolution refuses',
        'husks with a structured error; this check is the recovery path.',
        'Examples:',
        'spec-kitty doctor workspaces',
        'spec-kitty doctor workspaces --fix',
        'spec-kitty doctor workspaces --json',
        'Options',
        '--fix           Remove husks that are NOT registered in `git worktree list` (registered',
        'worktrees are never removed)',
        '--json          Machine-readable JSON output',
        '--help          Show this message and exit.',
    ],
    'identity': [
        'Usage: doctor identity [OPTIONS]',
        'Report mission-identity health across kitty-specs/.',
        'Classifies every mission into one of four states (FR-045):',
        '\\b',
        '- assigned: mission_id present AND mission_number non-null (fully migrated)',
        '- pending:  mission_id present AND mission_number null (pre-merge)',
        '- legacy:   mission_id missing AND mission_number present (needs backfill)',
        '- orphan:   both fields missing or meta.json unreadable (needs triage)',
        'Also reports duplicate numeric prefixes (FR-011) and ambiguous selectors',
        'that would resolve to multiple missions (FR-012).',
        'Examples:',
        'spec-kitty doctor identity',
        'spec-kitty doctor identity --json',
        'spec-kitty doctor identity --mission 083-foo',
        'spec-kitty doctor identity --fail-on legacy,orphan',
        'Options',
        '--json                 Emit structured JSON output (suitable for CI)',
        '--mission        TEXT  Scope report to a single mission slug',
        '--fail-on        TEXT  Exit non-zero if any mission is in the given state(s). Comma-separated',
        'list of: assigned, pending, legacy, orphan.',
        '--help                 Show this message and exit.',
    ],
    'topology': [
        'Usage: doctor topology [OPTIONS]',
        "Report each mission's STORED topology across kitty-specs/.",
        'Reads the authoritative ``topology`` value persisted in ``meta.json`` WITHOUT',
        're-inferring from disk/git. Missions not yet backfilled surface',
        '``topology: null`` — run ``spec-kitty migrate backfill-topology`` to persist',
        'the computed value.',
        'Examples:',
        'spec-kitty doctor topology',
        'spec-kitty doctor topology --json',
        'spec-kitty doctor topology --mission 083-foo',
        'Options',
        '--json                 Emit structured JSON output (suitable for CI)',
        '--mission        TEXT  Scope report to a single mission slug',
        '--help                 Show this message and exit.',
    ],
    'sparse-checkout': [
        'Usage: doctor sparse-checkout [OPTIONS]',
        'Detect and optionally remediate legacy sparse-checkout state.',
        'Without ``--fix``: scans the repo and prints a warning finding',
        'describing any active sparse-checkout state (primary + lane',
        'worktrees). Exits 0 when clean, 1 when state is present.',
        'With ``--fix``: in an interactive TTY, prints a step-by-step plan,',
        "prompts once for consent, and calls WP03's ``remediate()``. In",
        'non-interactive / CI environments, prints a remediation pointer and',
        'exits non-zero without mutating state (FR-023).',
        'Examples:',
        'spec-kitty doctor sparse-checkout',
        'spec-kitty doctor sparse-checkout --fix',
        'Options',
        '--fix           Apply remediation (disable sparse-checkout on primary + worktrees).',
        '--help          Show this message and exit.',
    ],
    'shim-registry': [
        'Usage: doctor shim-registry [OPTIONS]',
        'Check for overdue compatibility shims in the shim registry.',
        "Reads architecture/2.x/shim-registry.yaml and compares each entry's",
        'removal_target_release against the current project version. Fails with',
        'exit code 1 if any shim is overdue (removal release has shipped but',
        'shim file still exists on disk).',
        'Exit codes:',
        '0  All entries are pending, removed, or grandfathered.',
        '1  At least one entry is overdue — shim must be deleted or window extended.',
        '2  Configuration error (registry file or pyproject.toml missing/invalid).',
        'Examples:',
        'spec-kitty doctor shim-registry',
        'spec-kitty doctor shim-registry --json',
        'Options',
        '--json          Machine-readable JSON output',
        '--help          Show this message and exit.',
    ],
    'invocation-pairing': [
        'Usage: doctor invocation-pairing [OPTIONS]',
        'List orphan profile-invocation lifecycle records.',
        'WP05 (#843) wiring: scans',
        '``.kittify/events/profile-invocation-lifecycle.jsonl`` for ``started``',
        'records with no paired ``completed`` or ``failed`` partner. Mid-cycle',
        'agent crashes show up here. The check observes; it does not remediate.',
        'Exit codes:',
        '0  No orphans observed.',
        '1  At least one orphan found.',
        'Examples:',
        'spec-kitty doctor invocation-pairing',
        'spec-kitty doctor invocation-pairing --json',
        'Options',
        '--json          Machine-readable JSON output',
        '--help          Show this message and exit.',
    ],
    'ops': [
        'Usage: doctor ops [OPTIONS]',
        'List orphan Op records; --close-stale sweeps stale ones closed as abandoned.',
        'Options',
        '--json                      Machine-readable JSON output',
        '--close-stale               Close open Ops older than --threshold as abandoned',
        '(closed_by=doctor_sweep)',
        '--threshold          FLOAT  Staleness threshold in hours (default 24; 0 closes all). Requires',
        '--close-stale.',
        '--help                      Show this message and exit.',
    ],
    'orphan-daemons': [
        'Usage: doctor orphan-daemons [OPTIONS]',
        'List orphan daemon owner records and emit retirement hints.',
        'Implements FR-010 of the identity-boundary mission: an orphan',
        'daemon owner record is one whose recorded PID is dead OR whose',
        'recorded executable path no longer exists on disk. Each orphan',
        'is printed with a copy-pasteable retirement command that removes',
        'the on-disk ``owner.json`` so the next ``sync status --check``',
        'returns clean.',
        'Exit codes:',
        '0  No orphan records.',
        '1  At least one orphan record found.',
        'Examples:',
        'spec-kitty doctor orphan-daemons',
        'spec-kitty doctor orphan-daemons --json',
        'Options',
        '--json          Machine-readable JSON output',
        '--help          Show this message and exit.',
    ],
    'restart-daemon': [
        'Usage: doctor restart-daemon [OPTIONS]',
        'Stop the registered sync daemon and respawn it at the foreground.',
        'Composes the existing daemon stop + launch primitives so the operator',
        'has a one-shot remedy when the foreground process and the registered',
        'daemon disagree on any of the six canonical D-3 fields (version,',
        'executable, source, server URL, team/user, or queue DB path).',
        'Exit codes:',
        '0  Daemon restarted (or stale owner record cleaned and respawned).',
        '1  No registered daemon — run ``spec-kitty sync now`` to launch one.',
        '2  Daemon stop succeeded but respawn failed; system is stopped.',
        '3  Daemon stop failed (unresponsive); owner record left intact.',
        'Examples:',
        'spec-kitty doctor restart-daemon',
        'spec-kitty doctor restart-daemon --json',
        'Options',
        '--json          Emit a single JSON object instead of human-readable text.',
        '--help          Show this message and exit.',
    ],
    'mission-state': [
        'Usage: doctor mission-state [OPTIONS]',
        'Audit, repair, or TeamSpace-validate mission-state shapes.',
        'Options',
        '--audit                          Run mission-state audit (required to proceed)',
        '--fix                            Repair mission-state artifacts in place and write a migration',
        'manifest',
        '--teamspace-dry-run              Synthesize canonical TeamSpace envelopes from local state and',
        'validate them',
        '--json                           Emit JSON report to stdout',
        '--mission                  TEXT  Scope to a single mission handle',
        '--fail-on                  TEXT  Exit 1 if findings meet a gate',
        '(error|warning|info|teamspace-blocker)',
        '--fixture-dir              PATH  Override scan root (for testing)',
        '--include-fixtures               Audit the bundled mission-state survey fixtures',
        '--manifest-path            PATH  Path for --fix migration manifest',
        '--allow-dirty                    Allow --fix when relevant git paths are already dirty',
        '--help                           Show this message and exit.',
    ],
    'doctrine': [
        'Usage: doctor doctrine [OPTIONS]',
        'Check org doctrine snapshot status and list installed pack artifacts.',
        'Exit code reflects health (WP01, operator directive: loud over hidden): the',
        'command exits **1 when the report is unhealthy** and 0 only when healthy',
        '(``report.healthy`` drives the code on every output path). A clear RC=1 with',
        'a surfaced error is preferred over an RC=0 that hides a defect.  It',
        'enumerates each configured org pack (from ``.kittify/config.yaml``), prints',
        'its on-disk version (``git describe`` for git-managed packs, otherwise the',
        '``pack-manifest.yaml`` ``pack_version``), per-artifact YAML counts, and',
        '``org-charter.yaml`` policy status when present.',
        'Examples:',
        'spec-kitty doctor doctrine',
        'spec-kitty doctor doctrine --json',
        'Options',
        '--json          Machine-readable JSON output',
        '--help          Show this message and exit.',
    ],
    'coordination': [
        'Usage: doctor coordination [OPTIONS]',
        'Run the WP04 #1348 coordination + sparse-checkout health checks.',
        'Iterates over every mission under ``kitty-specs/`` whose ``meta.json``',
        'declares a ``coordination_branch`` field, runs the coord-worktree',
        'and lane-sparse-checkout health checks, and prints findings.',
        'Also runs the minimum git-version (RR-01) check.',
        'Exits with code 1 if any ``error`` finding is emitted; ``warning``',
        'findings exit 0 but are still printed.',
        'Options',
        '--json          Machine-readable JSON output',
        '--help          Show this message and exit.',
    ],
}


def _normalize_help(text: str) -> list[str]:
    """Strip box-drawing chars and blank lines so help is terminal-width robust."""
    out: list[str] = []
    for line in text.splitlines():
        cleaned = re.sub(r"[│╭╮╰╯─]", "", line).strip()
        if cleaned:
            out.append(cleaned)
    return out


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _fixed_terminal_width(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin terminal width so ``--help`` wrapping is deterministic in the snapshot."""
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "dumb")


# --- T001: names + per-subcommand params ------------------------------------


def test_registered_command_names_are_exactly_the_frozen_sixteen() -> None:
    cli = get_command(app)
    assert isinstance(cli, click.Group)
    registered = frozenset(cli.commands.keys())
    assert registered == FROZEN_SUBCOMMANDS
    assert len(registered) == 16


def _option_arity(opt: click.Option) -> str:
    if opt.multiple:
        return "multi"
    if opt.is_flag:
        return "flag"
    return "value"


@pytest.mark.parametrize("name", sorted(FROZEN_SUBCOMMANDS))
def test_subcommand_option_contract(name: str) -> None:
    cli = get_command(app)
    assert isinstance(cli, click.Group)
    command = cli.commands[name]
    actual: dict[str, str] = {}
    for param in command.params:
        if isinstance(param, click.Option):
            # The contract pins the long flags only; --help is implicit.
            for flag in param.opts:
                if flag == "--help":
                    continue
                actual[flag] = _option_arity(param)
    assert actual == EXPECTED_OPTIONS[name]


# --- T002: per-subcommand --help snapshot ------------------------------------


@pytest.mark.parametrize("name", sorted(FROZEN_SUBCOMMANDS))
def test_subcommand_help_snapshot(name: str, runner: CliRunner) -> None:
    result = runner.invoke(app, [name, "--help"])
    assert result.exit_code == 0
    assert _normalize_help(result.output) == EXPECTED_HELP[name]


# --- T003: exit-code contracts + load-bearing names --------------------------


def test_ops_threshold_without_close_stale_is_bad_parameter(
    runner: CliRunner,
) -> None:
    result = runner.invoke(app, ["ops", "--threshold", "5"])
    # BadParameter surfaces as a usage error (exit code 2) through the CLI.
    assert result.exit_code == 2
    assert "--threshold requires --close-stale" in result.output


def test_skills_name_is_invokable_and_returns_documented_exit_code(
    runner: CliRunner,
) -> None:
    # Load-bearing name (compat safety predicate + __init__ argv fast-path).
    # Outside a project the contract returns 2 (not-in-project); inside, 0/1.
    result = runner.invoke(app, ["skills", "--json"])
    assert result.exit_code in {0, 1, 2}


def test_restart_daemon_name_is_invokable_with_four_state_contract(
    runner: CliRunner,
) -> None:
    # Load-bearing name (__init__ argv fast-path). Four-state restart contract.
    result = runner.invoke(app, ["restart-daemon", "--json"])
    assert result.exit_code in {0, 1, 2, 3}


def test_sparse_checkout_fix_reaches_refusal_or_clean_path(
    runner: CliRunner,
) -> None:
    # Load-bearing name (compat safety predicate). In a non-interactive runner
    # --fix reaches the CI-refusal (non-zero) or clean (0) path, never crashes.
    prior = os.environ.get("CI")
    os.environ["CI"] = "1"
    try:
        result = runner.invoke(app, ["sparse-checkout", "--fix"])
    finally:
        if prior is None:
            os.environ.pop("CI", None)
        else:
            os.environ["CI"] = prior
    assert result.exit_code in {0, 1}
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_public_and_load_bearing_symbols_are_importable() -> None:
    # I-5 anchor: the public surface must remain importable from the shim.
    from specify_cli.cli.commands.doctor import SlashCommandGap as _gap
    from specify_cli.cli.commands.doctor import app as _app

    assert _app is app
    assert _gap is not None


# --- T004: cross-surface name coupling (#2059, GAP 1) ------------------------
#
# FROZEN_SUBCOMMANDS pins the live Typer names, but three OTHER string-keyed
# surfaces hard-code a subset of those names and are NOT cross-checked by the
# golden snapshots above:
#
#   1. the ``compat.safety_modes`` SAFETY_REGISTRY tuples
#      (e.g. ``("doctor", "skills")``, ``("doctor", "sparse-checkout")``);
#   2. the ``__init__`` argv fast-path predicates that key on the literal
#      ``"skills"`` / ``"restart-daemon"`` tokens; and
#   3. the ``cli.commands`` registration fast-path predicate for
#      ``"restart-daemon"``.
#
# A rename that updates FROZEN_SUBCOMMANDS + doctor.py but forgets one of these
# surfaces silently desyncs: the mode-gate tests monkeypatch sys.argv to the
# hard-coded literal, so they stay green. These tests derive expected values
# from the LIVE app + the real registry/predicate symbols (no second copy of
# the literal), so such a rename FAILS here.


def _live_doctor_subcommand_names() -> frozenset[str]:
    cli = get_command(app)
    assert isinstance(cli, click.Group)
    return frozenset(cli.commands.keys())


def test_safety_registry_doctor_names_are_live_subcommands() -> None:
    """Every ``("doctor", <name>)`` tuple in the safety registry must be a
    live registered subcommand.

    Teeth: rename a doctor subcommand in ``doctor.py`` (which flows into the
    live app + must be mirrored into FROZEN_SUBCOMMANDS) WITHOUT updating
    ``safety_modes.py`` and the stale registered name is no longer live →
    this assertion fails. The mode-gate tests would not catch it because they
    monkeypatch ``sys.argv`` to the hard-coded literal.
    """
    from specify_cli.compat.safety import SAFETY_REGISTRY
    from specify_cli.compat.safety_modes import register_mode_predicates

    # Idempotent; ensures the doctor subcommand tuples are present.
    register_mode_predicates()

    registered_doctor_names = {
        path[1]
        for path in SAFETY_REGISTRY
        if len(path) == 2 and path[0] == "doctor"
    }
    # Sanity: the registry actually carries the load-bearing names so this
    # test cannot pass vacuously if the registry is ever emptied.
    assert {"skills", "sparse-checkout"} <= registered_doctor_names

    live = _live_doctor_subcommand_names()
    orphaned = registered_doctor_names - live
    assert not orphaned, (
        "safety_modes.py registers doctor subcommand name(s) that are no "
        f"longer live in the Typer app: {sorted(orphaned)}. A subcommand was "
        "renamed in doctor.py without updating compat/safety_modes.py."
    )


def test_init_skills_fast_path_predicate_keys_on_a_live_name() -> None:
    """The ``__init__`` ``doctor skills`` fast-path predicate must recognise
    the LIVE ``skills`` subcommand name.

    Teeth: rename ``skills`` in ``doctor.py`` + FROZEN_SUBCOMMANDS but leave the
    ``args[1] == "skills"`` literal in ``__init__._is_doctor_skills_invocation``
    untouched and this predicate stops matching the live name → fails.
    """
    from specify_cli import _is_doctor_skills_invocation

    live = _live_doctor_subcommand_names()
    assert "skills" in live, "golden contract guarantees a 'skills' subcommand"

    # Build argv from the LIVE name, not a copied literal.
    argv = ["spec-kitty", "doctor", "skills", "--json"]
    assert _is_doctor_skills_invocation(argv) is True
    # Negative control: a different live subcommand must NOT match the
    # skills-specific predicate (proves the predicate keys on the name).
    other = next(name for name in sorted(live) if name != "skills")
    assert _is_doctor_skills_invocation(["spec-kitty", "doctor", other]) is False


def test_restart_daemon_fast_path_predicates_key_on_a_live_name() -> None:
    """The three ``restart-daemon`` argv fast-path predicates (two in
    ``__init__`` + one in ``cli.commands``) must recognise the LIVE
    ``restart-daemon`` subcommand name.

    Teeth: rename ``restart-daemon`` in ``doctor.py`` + FROZEN_SUBCOMMANDS but
    leave the ``["doctor", "restart-daemon"]`` literals in the predicates
    untouched and they stop matching the live name → fails.
    """
    from specify_cli import (
        _is_doctor_restart_daemon_invocation,
        _is_doctor_restart_daemon_process_fast_path,
    )
    from specify_cli.cli.commands import _is_doctor_restart_daemon_fast_path

    live = _live_doctor_subcommand_names()
    assert "restart-daemon" in live, (
        "golden contract guarantees a 'restart-daemon' subcommand"
    )

    # Build argv from the LIVE name, not a copied literal.
    argv = ["spec-kitty", "doctor", "restart-daemon"]
    argv_json = ["spec-kitty", "doctor", "restart-daemon", "--json"]
    assert _is_doctor_restart_daemon_invocation(argv) is True
    assert _is_doctor_restart_daemon_process_fast_path(argv_json) is True
    assert _is_doctor_restart_daemon_fast_path(argv_json) is True

    # Negative control: another live subcommand must NOT trip the
    # restart-daemon-specific predicates (proves they key on the name).
    other = next(name for name in sorted(live) if name != "restart-daemon")
    other_argv = ["spec-kitty", "doctor", other]
    assert _is_doctor_restart_daemon_invocation(other_argv) is False
    assert _is_doctor_restart_daemon_process_fast_path(other_argv) is False
    assert _is_doctor_restart_daemon_fast_path(other_argv) is False
