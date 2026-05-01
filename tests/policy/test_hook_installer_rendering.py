"""Tests for pre-commit hook rendering shape (T035).

Verifies the generated hook has the correct structure: #!/bin/sh shebang,
a single quoted exec line with the absolute interpreter, LF line endings,
and mode 0o700.  No windows_ci marker — pure-Python rendering check.
"""

import os
import stat
import sys
from pathlib import Path

from specify_cli.policy.hook_installer import HOOK_MODE, HookInstallRecord, install


def test_hook_rendering_shape(tmp_path: Path) -> None:
    """Install into a fake repo .git dir and assert the rendered hook shape."""
    # Fake repo with .git dir (not a real git repo — install() only needs the dir)
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)

    record = install(repo)
    hook = repo / ".git" / "hooks" / "pre-commit"
    assert hook.is_file(), "pre-commit hook file must exist after install"

    content = hook.read_text(encoding="utf-8")

    # LF line endings — no CRLF allowed (Git for Windows sh.exe fails on CRLF shebang)
    assert "\r\n" not in content, "Hook must use LF line endings, not CRLF"

    lines = content.splitlines()
    assert lines[0] == "#!/bin/sh", f"First line must be #!/bin/sh, got {lines[0]!r}"

    exec_lines = [line for line in lines if line.startswith("exec ")]
    assert len(exec_lines) == 1, f"Expected exactly one 'exec ' line, found {len(exec_lines)}: {exec_lines}"
    exec_line = exec_lines[0]

    # Interpreter must appear in double quotes (handles paths with spaces).
    # Symlinks are intentionally preserved (issue #669) so venv/pipx interpreters
    # keep their sys.prefix — so we expect the abspath of sys.executable, not its
    # resolved target.
    expected = os.path.abspath(sys.executable)
    assert f'"{expected}"' in exec_line, f'Expected quoted interpreter "{expected}" in exec line: {exec_line!r}'
    assert "-m specify_cli.policy.commit_guard_hook" in exec_line, f"Expected module invocation in exec line: {exec_line!r}"
    assert '"$@"' in exec_line, f'Expected "$@" in exec line: {exec_line!r}'

    # No PATH-based python/python3/py literals (the whole point of this WP)
    assert "python3 " not in content, "Hook must not contain bare 'python3 ' lookup"
    assert "python " not in content, "Hook must not contain bare 'python ' lookup"

    # Mode 0o700
    mode = stat.S_IMODE(os.stat(hook).st_mode)
    assert mode == HOOK_MODE, f"Expected mode {oct(HOOK_MODE)}, got {oct(mode)}"

    # HookInstallRecord fields
    assert isinstance(record, HookInstallRecord)
    assert record.shebang == "#!/bin/sh"
    assert record.module == "specify_cli.policy.commit_guard_hook"
    assert record.interpreter == Path(os.path.abspath(sys.executable))
    assert record.mode == HOOK_MODE
    assert record.hook_path == hook
