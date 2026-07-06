"""Guard against Windows-illegal or shell-expansion-leak characters in tracked filenames.

Mission ``cmd-output-file-leak-guard-01KWVZX7`` (#2169), FR-003 / FR-004. A
test double once regex-parsed a shell-quoted ``--output=`` argument and wrote
the literal string ``"${SPEC_KITTY_CMD_OUTPUT_FILE}"`` as a filename into the
working tree. ``git add -A`` swept the junk file into a commit on PR #2161,
and ``git checkout`` then exited 128 on Windows CI (run 28224079685) because
``"`` is illegal in a Windows path component. This is the class-closing
backstop: it fails on *any* tracked path containing a forbidden character,
whether or not this specific leak (or its emitter) resurfaces.

Two distinct, deliberately-not-conflated forbidden sets:

1. ``WINDOWS_ILLEGAL_CHARS`` -- characters Windows itself refuses in a path
   component: ``< > : " \\ | ? *``. ``"`` is the exact character that broke
   #2161's Windows checkout. ``:`` is only legitimate as a drive-letter
   prefix (e.g. ``C:\\...``); no tracked, repo-relative ``git ls-files`` path
   is expected to carry one, so any ``:`` found here is also flagged.
2. ``SHELL_EXPANSION_TELLTALE_CHARS`` -- ``$ { }``. These are Windows-*legal*
   but their presence in a tracked filename is a shell-substitution-leak
   signature -- exactly this bug's ``"${SPEC_KITTY_CMD_OUTPUT_FILE}"``.

Cheap by construction: a single ``git ls-files`` call, no per-file I/O.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Set 1: characters Windows itself forbids in a path component (the #2161
# CI-breaker class). See module docstring for the `:` drive-prefix caveat.
WINDOWS_ILLEGAL_CHARS: tuple[str, ...] = ("<", ">", ":", '"', "\\", "|", "?", "*")

# Set 2: Windows-legal but a shell-substitution-leak signature (this bug).
SHELL_EXPANSION_TELLTALE_CHARS: tuple[str, ...] = ("$", "{", "}")


def _tracked_paths() -> list[str]:
    # ``-z`` yields NUL-separated, *verbatim* paths — this disables git's default
    # ``core.quotePath`` C-quoting, which would otherwise wrap a non-ASCII path
    # like ``café.txt`` as ``"caf\303\251.txt"`` and inject a spurious ``"``/``\``
    # that false-reds the Windows-illegal guard on a perfectly legal filename.
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [path for path in result.stdout.split("\0") if path]


def _offenders(paths: list[str], forbidden_chars: tuple[str, ...]) -> dict[str, list[str]]:
    offenders: dict[str, list[str]] = {}
    for path in paths:
        hit = sorted({char for char in forbidden_chars if char in path})
        if hit:
            offenders[path] = hit
    return offenders


def test_no_windows_illegal_filenames() -> None:
    """No tracked path may contain a character Windows itself forbids.

    ``"`` is the exact character that exit-128'd Windows checkout on #2161
    (PR #2161's leaked ``"${SPEC_KITTY_CMD_OUTPUT_FILE}"`` file).
    """
    paths = _tracked_paths()
    assert paths, "git ls-files returned no tracked paths -- guard would pass vacuously"

    offenders = _offenders(paths, WINDOWS_ILLEGAL_CHARS)
    assert not offenders, (
        "Tracked path(s) contain Windows-illegal character(s) "
        f"({', '.join(WINDOWS_ILLEGAL_CHARS)}) matched by the WINDOWS_ILLEGAL_CHARS "
        "set -- Windows `git checkout` will exit 128 on these (see #2161):\n"
        + "\n".join(f"  {path!r}: {chars}" for path, chars in sorted(offenders.items()))
    )


def test_no_shell_expansion_telltale_filenames() -> None:
    """No tracked path may contain a shell-substitution-leak telltale.

    ``$``/``{``/``}`` are Windows-*legal*, but their presence in a filename
    is the signature of an unexpanded shell substitution leaking into the
    working tree (this bug's ``"${SPEC_KITTY_CMD_OUTPUT_FILE}"``).
    """
    paths = _tracked_paths()
    assert paths, "git ls-files returned no tracked paths -- guard would pass vacuously"

    offenders = _offenders(paths, SHELL_EXPANSION_TELLTALE_CHARS)
    assert not offenders, (
        "Tracked path(s) contain shell-expansion-leak telltale character(s) "
        f"({', '.join(SHELL_EXPANSION_TELLTALE_CHARS)}) matched by the "
        "SHELL_EXPANSION_TELLTALE_CHARS set -- likely an unexpanded shell "
        "substitution leaked into the working tree:\n"
        + "\n".join(f"  {path!r}: {chars}" for path, chars in sorted(offenders.items()))
    )


def test_windows_legal_nonascii_names_are_not_flagged() -> None:
    """Regression: a Windows-*legal* non-ASCII filename must not false-red.

    With git's default ``core.quotePath`` a path like ``café.txt`` is emitted as
    ``"caf\\303\\251.txt"``; substring-matching that would wrongly flag ``"``/``\\``.
    ``_tracked_paths`` reads ``git ls-files -z`` (verbatim) so names arrive
    decoded; ``_offenders`` must then treat them as clean, while still catching a
    genuinely-illegal name.
    """
    assert _offenders(["café.txt", "docs/naïve-notes.md"], WINDOWS_ILLEGAL_CHARS) == {}
    assert _offenders(['a"b.txt'], WINDOWS_ILLEGAL_CHARS) == {'a"b.txt': ['"']}
