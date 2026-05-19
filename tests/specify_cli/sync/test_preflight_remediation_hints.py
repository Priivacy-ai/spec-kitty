"""Hint-coverage + wording-uniformity tests for ``_REMEDIATION_HINTS``.

Pins two invariants in CI so a future change to
``src/specify_cli/sync/preflight.py`` cannot regress operator UX:

1. **Hint coverage** — every ``spec-kitty …`` command mentioned in any
   ``_REMEDIATION_HINTS`` entry must resolve on the installed CLI
   (i.e. ``<cmd> --help`` exits 0). The fix for #1124 (WP03 T012) makes
   ``spec-kitty doctor restart-daemon`` resolve; this test pins that
   surface so it cannot disappear.
2. **Wording uniformity** — the four "restart-class" hint entries
   (package_version, executable_path, source_path, queue_db_path) all
   use the same canonical remedy phrase. A grep stays consistent and
   future authors are nudged into reusing ``_RESTART_DAEMON_REMEDY``.

The hint surface deliberately also mentions ``spec-kitty auth login``
and ``spec-kitty auth switch`` for the auth-class mismatches; both are
exercised by the coverage test.
"""

from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import auth as auth_module
from specify_cli.cli.commands import doctor as doctor_module
from specify_cli.cli.commands import sync as sync_module
from specify_cli.sync.preflight import MismatchField, _REMEDIATION_HINTS

pytestmark = pytest.mark.fast


# Group sub-apps by name so we can dispatch ``spec-kitty <group> <subcmd>``
# through the appropriate Typer app without booting the full root callback
# (which pulls in runtime bootstrap, schema gates, etc.).
_SUBAPPS = {
    "doctor": doctor_module.app,
    "sync": sync_module.app,
    "auth": auth_module.app,
}


# Commands that intentionally appear in hint strings but are not part of
# the spec-kitty CLI surface. Each entry must have a justification.
# No non-spec-kitty commands appear in the current hint set. The remediation
# surface in ``PreflightResult.render`` may mention non-spec-kitty commands,
# but that lives outside ``_REMEDIATION_HINTS`` and outside this test's scope.
_NON_SPEC_KITTY_ALLOWLIST: set[str] = set()


_SPEC_KITTY_COMMAND_RE = re.compile(r"`spec-kitty\s+([^`]+)`")


def _extract_spec_kitty_commands(hint: str) -> list[list[str]]:
    """Return tokenised ``spec-kitty …`` invocations found in *hint*.

    Each invocation is returned as a list of argv tokens (excluding
    ``spec-kitty``). Trailing example-style placeholders (``...``) are
    dropped so the command resolves under ``--help``.
    """
    out: list[list[str]] = []
    for match in _SPEC_KITTY_COMMAND_RE.finditer(hint):
        raw = match.group(1).strip()
        tokens = [t for t in raw.split() if t != "..."]
        if tokens:
            out.append(tokens)
    return out


def _invoke_help(tokens: list[str]) -> tuple[int, str]:
    """Invoke ``<tokens> --help`` via the appropriate Typer sub-app.

    Returns ``(exit_code, output)``. Drops any flag-form trailing
    argument tokens (e.g. ``--check``) before resolving the subcommand
    path, because help resolution stops at the first sub-app/subcommand.
    """
    # Click 8.2+ removed the ``mix_stderr`` kwarg; the default suffices.
    runner = CliRunner()
    if not tokens:
        pytest.fail("Empty command token list")

    head, rest = tokens[0], tokens[1:]
    if head not in _SUBAPPS:
        if " ".join(tokens) in _NON_SPEC_KITTY_ALLOWLIST:
            return 0, "<allowlisted-non-spec-kitty>"
        pytest.fail(
            f"Hint references unknown spec-kitty group {head!r} "
            f"(tokens={tokens!r}). Update _SUBAPPS or _NON_SPEC_KITTY_ALLOWLIST."
        )

    app = _SUBAPPS[head]
    # Strip flag tokens so resolution lands on the subcommand itself.
    positional = [t for t in rest if not t.startswith("-")]
    result = runner.invoke(app, [*positional, "--help"])
    return result.exit_code, result.stdout


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_every_hint_command_resolves_under_help() -> None:
    """Every ``spec-kitty …`` command in any hint must exit 0 on ``--help``.

    Before WP03 T012 landed, this test FAILED for
    ``spec-kitty doctor restart-daemon`` because the subcommand did not
    exist. After T012 it must pass.
    """
    seen: set[tuple[str, ...]] = set()
    for field_name, hint in _REMEDIATION_HINTS.items():
        for tokens in _extract_spec_kitty_commands(hint):
            key = tuple(tokens)
            if key in seen:
                continue
            seen.add(key)
            exit_code, output = _invoke_help(tokens)
            assert exit_code == 0, (
                f"Hint for {field_name!r} references "
                f"`spec-kitty {' '.join(tokens)}` but `--help` exited "
                f"{exit_code}. Output:\n{output}"
            )

    # Sanity: at least one command was discovered. A regression that
    # accidentally drops all ``spec-kitty`` references should fail loud.
    assert seen, (
        "No `spec-kitty …` commands extracted from _REMEDIATION_HINTS — "
        "this looks like a regression in the hint surface."
    )


def test_doctor_restart_daemon_appears_in_hint_surface() -> None:
    """At least one hint must reference ``doctor restart-daemon`` —
    the primary remedy for the four restart-class mismatches."""
    found = False
    for hint in _REMEDIATION_HINTS.values():
        if "doctor restart-daemon" in hint:
            found = True
            break
    assert found, (
        "No _REMEDIATION_HINTS entry references `spec-kitty doctor "
        "restart-daemon` — the primary remedy for D-3 mismatches is missing."
    )


def test_restart_class_hints_share_canonical_phrase() -> None:
    """The four restart-class hints must use identical wording.

    A future grep should find one canonical phrase, not four near-duplicates.
    Per the WP03 plan, the four entries point at the
    ``_RESTART_DAEMON_REMEDY`` constant so they are guaranteed identical.
    """
    restart_class_fields: tuple[MismatchField, ...] = (
        "daemon_package_version",
        "daemon_executable_path",
        "daemon_source_path",
        "daemon_queue_db_path",
    )
    phrases = {field: _REMEDIATION_HINTS[field] for field in restart_class_fields}
    canonical = phrases[restart_class_fields[0]]
    for field, phrase in phrases.items():
        assert phrase == canonical, (
            f"Hint for {field!r} differs from the canonical restart-class "
            f"phrase. Got:\n  {phrase!r}\nExpected:\n  {canonical!r}"
        )
    # And the canonical phrase actually references the subcommand.
    assert "doctor restart-daemon" in canonical
    assert "sync status --check" in canonical


def test_no_unknown_commands_in_hints() -> None:
    """Every group head (``doctor``/``sync``/``auth``) in the hint set is
    one we know how to dispatch in this test module. A new group would
    require adding it to ``_SUBAPPS`` (or the allowlist) deliberately."""
    for field_name, hint in _REMEDIATION_HINTS.items():
        for tokens in _extract_spec_kitty_commands(hint):
            head = tokens[0]
            if head not in _SUBAPPS and " ".join(tokens) not in _NON_SPEC_KITTY_ALLOWLIST:
                pytest.fail(
                    f"Hint for {field_name!r} mentions unknown group "
                    f"{head!r}. Tokens={tokens!r}."
                )
