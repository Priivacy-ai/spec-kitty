"""Regression test for issue #101: CLI startup crash on non-UTF-8 Windows code pages.

The root cause was that printing non-ASCII characters (e.g. path separators with
accented names, emoji in banners) would raise ``UnicodeEncodeError`` when
``sys.stdout`` was using a legacy code page such as Windows-1252 (cp1252).

The fix calls ``ensure_utf8_on_windows()`` at CLI import time (T046), which
reconfigures stdout/stderr to UTF-8 with ``errors='replace'``. This test
reproduces the crash class by running a subprocess under an explicit legacy
code page and asserting exit code 0.

Marked ``@pytest.mark.windows_ci`` — runs only on the ``windows-latest`` CI
job (skipped on POSIX CI runners via the ``-m "not windows_ci"`` filter).

Spec IDs: FR-016, FR-017, SC-004
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest


@pytest.mark.windows_ci
def test_cli_startup_under_non_utf8_codepage_does_not_crash(tmp_path: pytest.TempPathFactory) -> None:
    """CLI startup must not crash when stdout is on a non-UTF-8 code page.

    Runs a subprocess that emits non-ASCII characters (accented letters,
    Greek, em-dash) via ``print()``, after calling
    ``ensure_utf8_on_windows()``.  Under ``PYTHONIOENCODING=cp1252`` the
    characters cannot be encoded verbatim, but ``errors='replace'`` must
    convert them to replacement characters rather than raising.
    """
    script = tmp_path / "smoke.py"
    script.write_text(
        'from specify_cli.encoding import ensure_utf8_on_windows\nensure_utf8_on_windows()\nprint("path: \u00f1\u00e1m\u00e9 \u2014 caf\u00e9/\u03a9")\n',
        encoding="utf-8",
    )
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    # Deliberately do NOT set PYTHONUTF8=1 — we are testing the in-process fix.
    env.pop("PYTHONUTF8", None)
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=False,
        env=env,
    )
    # Expect zero exit even though cp1252 can't encode all characters.
    # 'errors=replace' should have produced replacement chars, not a crash.
    assert proc.returncode == 0, f"CLI startup crashed on non-UTF-8 codepage: stderr={proc.stderr!r}"
