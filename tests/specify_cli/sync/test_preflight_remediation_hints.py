"""Hint-coverage + wording-uniformity tests for the sync remediation registry.

Pins invariants in CI so a future change to
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
3. **Full-registry coverage (#2674)** — the guard must resolve every
   command mentioned anywhere in ``ALL_REMEDIATION_TEXTS``, not just the
   commands that happen to appear in ``_REMEDIATION_HINTS``. Three
   commands (``doctor orphan-daemons``, ``sync migrate``, ``auth login``)
   only ever appeared inline in ``_build_remediation_lines()`` and were
   invisible to the dict-only guard before this WP.

The hint surface deliberately also mentions ``spec-kitty auth login`` and
``spec-kitty auth logout`` for the auth-class mismatches; both are
exercised by the coverage test.
"""

from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import auth as auth_module
from specify_cli.cli.commands import doctor as doctor_module
from specify_cli.cli.commands import sync as sync_module
from specify_cli.sync.preflight import (
    ALL_REMEDIATION_TEXTS,
    MismatchField,
    OwnerMismatch,
    _build_remediation_lines,
    _REMEDIATION_HINTS,
)

pytestmark = pytest.mark.fast


# Group sub-apps by name so we can dispatch ``spec-kitty <group> <subcmd>``
# through the appropriate Typer app without booting the full root callback
# (which pulls in runtime bootstrap, schema gates, etc.).
_SUBAPPS = {
    "doctor": doctor_module.app,
    "sync": sync_module.app,
    "auth": auth_module.app,
}


# Commands that intentionally appear in remediation text but are not part
# of the spec-kitty CLI surface. Each entry must have a justification.
# No non-spec-kitty commands appear in the current registry
# (``ALL_REMEDIATION_TEXTS``, #2674) — every ``spec-kitty …`` token, whether
# dict-keyed or inline-only, is expected to resolve.
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


def _registry_command_tokens(texts: tuple[str, ...]) -> set[tuple[str, ...]]:
    """Extract every ``spec-kitty …`` command token from *texts*.

    Placeholder-bearing texts (``{count}``, ``{rows}``) are formatted with
    dummy values first — the placeholders never appear inside a
    ``spec-kitty …`` command token, so this is purely to let the regex
    walk clean text.
    """
    tokens: set[tuple[str, ...]] = set()
    for text in texts:
        rendered = text.format(count=1, rows=1) if "{" in text else text
        for extracted in _extract_spec_kitty_commands(rendered):
            tokens.add(tuple(extracted))
    return tokens


def test_full_registry_guard_resolves_inline_only_commands() -> None:
    """RED for #2674 (T030): the dict-only guard misses inline-only typos.

    Today (before T031-T033), ``test_no_unknown_commands_in_hints`` and
    ``test_every_hint_command_resolves_under_help`` iterate ONLY
    ``_REMEDIATION_HINTS.items()``. Three commands live exclusively inside
    ``_build_remediation_lines()`` and are never seen by that guard:
    ``spec-kitty doctor orphan-daemons``, ``spec-kitty sync migrate``, and
    ``spec-kitty auth login`` (the standalone auth-required bullet). A typo
    in any of them would ship green.

    This test asserts a full-text registry (``ALL_REMEDIATION_TEXTS``,
    introduced in T031) exists and spans BOTH surfaces — every command
    token found in it, including the three inline-only ones, must resolve
    under ``--help``. It fails today with ``AttributeError`` because
    ``ALL_REMEDIATION_TEXTS`` does not exist yet; it passes once T031-T033
    land.

    The final assertion proves the *mechanism*: a hand-typo'd variant of
    an inline-only command (``orphan-daemon``, missing the trailing ``s``)
    fails ``--help`` resolution — exactly what a full-registry guard would
    surface as a failure if the typo were real, and exactly what the
    dict-only guard above would never catch.
    """
    from specify_cli.sync import preflight as preflight_module

    registry = preflight_module.ALL_REMEDIATION_TEXTS  # AttributeError before T031

    inline_only_commands = {
        ("doctor", "orphan-daemons"),
        ("sync", "migrate"),
        ("auth", "login"),
    }
    found_commands = _registry_command_tokens(tuple(registry))

    missing = inline_only_commands - found_commands
    assert not missing, (
        f"ALL_REMEDIATION_TEXTS is missing inline-only commands: {sorted(missing)} "
        "— the #2674 coverage gap is still open."
    )

    for tokens in sorted(found_commands):
        exit_code, output = _invoke_help(list(tokens))
        assert exit_code == 0, (
            f"registry command `spec-kitty {' '.join(tokens)}` failed "
            f"--help resolution (exit={exit_code}):\n{output}"
        )

    # Prove a typo would be caught: the dict-only guard never sees this
    # token at all (it isn't in `_REMEDIATION_HINTS`), but a resolution
    # check against it correctly fails.
    dict_only_tokens = _registry_command_tokens(tuple(_REMEDIATION_HINTS.values()))
    assert ("doctor", "orphan-daemon") not in dict_only_tokens
    exit_code, _output = _invoke_help(["doctor", "orphan-daemon"])
    assert exit_code != 0, "expected the typo'd command to fail --help resolution"


def test_every_hint_command_resolves_under_help() -> None:
    """Every ``spec-kitty …`` command in the FULL registry exits 0 on ``--help``.

    Before WP03 T012 landed, this test FAILED for
    ``spec-kitty doctor restart-daemon`` because the subcommand did not
    exist. After T012 it must pass.

    Widened for #2674 (T033): scans ``ALL_REMEDIATION_TEXTS`` — the
    canonical registry spanning both ``_REMEDIATION_HINTS`` (dict-keyed)
    and the inline-only commands (``doctor orphan-daemons``,
    ``sync migrate``, ``auth login``) — instead of ``_REMEDIATION_HINTS``
    alone, so a typo in an inline-only command fails here too.
    """
    seen: set[tuple[str, ...]] = set()
    for text in ALL_REMEDIATION_TEXTS:
        rendered = text.format(count=1, rows=1) if "{" in text else text
        for tokens in _extract_spec_kitty_commands(rendered):
            key = tuple(tokens)
            if key in seen:
                continue
            seen.add(key)
            exit_code, output = _invoke_help(tokens)
            assert exit_code == 0, (
                f"Remediation text references "
                f"`spec-kitty {' '.join(tokens)}` but `--help` exited "
                f"{exit_code}. Output:\n{output}"
            )

    # Sanity: at least one command was discovered. A regression that
    # accidentally drops all ``spec-kitty`` references should fail loud.
    assert seen, (
        "No `spec-kitty …` commands extracted from ALL_REMEDIATION_TEXTS — "
        "this looks like a regression in the remediation surface."
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
    """Every group head (``doctor``/``sync``/``auth``) in the FULL registry
    is one we know how to dispatch in this test module. A new group would
    require adding it to ``_SUBAPPS`` (or the allowlist) deliberately.

    Widened for #2674 (T033): scans ``ALL_REMEDIATION_TEXTS`` instead of
    ``_REMEDIATION_HINTS`` alone, so an inline-only command referencing an
    unknown group is caught too.
    """
    for text in ALL_REMEDIATION_TEXTS:
        rendered = text.format(count=1, rows=1) if "{" in text else text
        for tokens in _extract_spec_kitty_commands(rendered):
            head = tokens[0]
            if head not in _SUBAPPS and " ".join(tokens) not in _NON_SPEC_KITTY_ALLOWLIST:
                pytest.fail(
                    f"Remediation text mentions unknown group "
                    f"{head!r}. Tokens={tokens!r}."
                )


def test_byte_identical_remediation_output() -> None:
    """Byte-identical proof (#2674 / T032): hoisting remediation sentences
    into shared named constants must not change a single rendered byte.

    Snapshots the pre-refactor verbatim text for the two previously
    duplicated dict entries (``daemon_server_url`` / ``daemon_team_or_user``)
    and for ``_build_remediation_lines()`` with every branch active
    (restart-class mismatches, the two auth-class mismatches, and all
    three inline-only bullets), asserting the hoisted-constant
    implementation renders identically to the pre-WP04 literal strings.
    """
    assert _REMEDIATION_HINTS["daemon_server_url"] == (
        "Reauthenticate (`spec-kitty auth login`) or restart the daemon "
        "against the matching server."
    )
    assert _REMEDIATION_HINTS["daemon_team_or_user"] == (
        "Re-authenticate as the foreground team/user (`spec-kitty auth "
        "logout` then `spec-kitty auth login`) and then run `spec-kitty "
        "doctor restart-daemon`."
    )

    mismatches = tuple(
        OwnerMismatch(
            field=field_name,
            foreground_value="fg",
            daemon_value="daemon",
            remediation_hint=_REMEDIATION_HINTS[field_name],
        )
        for field_name in (
            "daemon_package_version",
            "daemon_server_url",
            "daemon_team_or_user",
        )
    )
    lines = _build_remediation_lines(
        mismatches,
        orphan_count=2,
        legacy_rows=5,
        auth_required=True,
        auth_present=False,
    )
    assert lines == [
        "  • Run `spec-kitty doctor restart-daemon` to restart the daemon "
        "at the foreground version/source, then verify with `spec-kitty "
        "sync status --check`.",
        "  • Reauthenticate (`spec-kitty auth login`) or restart the "
        "daemon against the matching server.",
        "  • Re-authenticate as the foreground team/user (`spec-kitty "
        "auth logout` then `spec-kitty auth login`) and then run "
        "`spec-kitty doctor restart-daemon`.",
        "  • Run `spec-kitty doctor orphan-daemons` to clean up 2 orphan "
        "daemon record(s).",
        "  • Run `spec-kitty sync migrate` to migrate 5 legacy queue "
        "row(s) into the event journal so the boundary becomes coherent.",
        "  • Run `spec-kitty auth login` — SaaS sync enabled but no "
        "authenticated identity is available.",
    ]


def test_legacy_rows_remediation_points_to_sync_migrate():
    """Regression for #2665: the legacy-rows remediation must point to
    ``spec-kitty sync migrate`` — which actually migrates legacy queue rows
    into the event journal — and NOT ``spec-kitty sync now``. ``sync now`` is
    itself gated on legacy rows, so the old wording was a circular dead-end.
    """
    lines = _build_remediation_lines(
        (),
        orphan_count=0,
        legacy_rows=3,
        auth_required=False,
        auth_present=False,
    )
    joined = "\n".join(lines)
    assert "spec-kitty sync migrate" in joined
    assert "spec-kitty sync now" not in joined
