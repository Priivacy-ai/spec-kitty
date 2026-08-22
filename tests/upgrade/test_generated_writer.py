"""Tests for the canonical generated-file writer (FR-001/002, #3651).

Covers:
- T007: ``write_generated_file`` unit tests — the read-only permission
  lifecycle it owns (restore-before-write, strip-after-write, propagate
  genuine failures, idempotency).
- T004: a mechanical architectural guard so an in-scope generated-command/
  skill migration cannot reintroduce a bare ``write_text`` on a read-only-
  destined path without the guard catching it (prose audits alone silently
  regress).
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from specify_cli.runtime.generated_writer import write_generated_file

pytestmark = pytest.mark.fast

# ---------------------------------------------------------------------------
# T007 — write_generated_file unit tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.getuid() == 0, reason="root ignores file permissions")
def test_write_over_read_only_target_succeeds_and_stays_read_only(tmp_path: Path) -> None:
    """(a) A pre-existing 0o444 target is rewritten and left read-only."""
    target = tmp_path / "command.md"
    target.write_text("stale\n", encoding="utf-8")
    target.chmod(0o444)

    write_generated_file(target, "fresh\n")

    assert target.read_text(encoding="utf-8") == "fresh\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o444


def test_write_over_missing_target_creates_it_read_only(tmp_path: Path) -> None:
    """(b) A missing target is created and left read-only."""
    target = tmp_path / "new-command.md"
    assert not target.exists()

    write_generated_file(target, "content\n")

    assert target.read_text(encoding="utf-8") == "content\n"
    assert stat.S_IMODE(target.stat().st_mode) & 0o222 == 0


def test_read_only_false_leaves_target_writable(tmp_path: Path) -> None:
    """(c) ``read_only=False`` leaves the target writable after the write."""
    target = tmp_path / "writable.md"

    write_generated_file(target, "content\n", read_only=False)

    assert target.read_text(encoding="utf-8") == "content\n"
    assert stat.S_IMODE(target.stat().st_mode) & 0o200 != 0


@pytest.mark.skipif(os.getuid() == 0, reason="root ignores file permissions")
def test_genuine_write_failure_propagates(tmp_path: Path) -> None:
    """(d) A genuine failure (unwritable parent directory) is not swallowed."""
    blocked_dir = tmp_path / "blocked"
    blocked_dir.mkdir()
    target = blocked_dir / "command.md"

    blocked_dir.chmod(0o555)  # read+execute only — cannot create a new file here
    try:
        with pytest.raises(OSError):
            write_generated_file(target, "content\n")
    finally:
        blocked_dir.chmod(0o755)  # restore so tmp_path cleanup can remove it


@pytest.mark.skipif(os.getuid() == 0, reason="root ignores file permissions")
def test_idempotent_double_write(tmp_path: Path) -> None:
    """(e) Writing the same content twice in a row is a clean no-op state."""
    target = tmp_path / "command.md"

    write_generated_file(target, "content\n")
    write_generated_file(target, "content\n")

    assert target.read_text(encoding="utf-8") == "content\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o444


def test_default_encoding_is_utf8(tmp_path: Path) -> None:
    """Non-ASCII content round-trips under the default UTF-8 encoding."""
    target = tmp_path / "unicode.md"

    write_generated_file(target, "spec-kitty 🐱 café\n")

    assert target.read_text(encoding="utf-8") == "spec-kitty 🐱 café\n"


# ---------------------------------------------------------------------------
# T004 — mechanical architectural guard: no bare write_text in in-scope
# migrations (see kitty-specs/.../research.md, "FR-002 write-site
# enumeration" for the classification rule and confirmed in-scope list).
# ---------------------------------------------------------------------------

_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "upgrade" / "migrations"
)

# Every migration confirmed in-scope by research.md's FR-002 enumeration: its
# write target is a generated command/skill file the generation layer later
# makes read-only. Each must route its write(s) through write_generated_file
# instead of a bare Path.write_text(...) call.
_IN_SCOPE_GENERATED_SURFACE_MIGRATIONS = [
    "m_2_1_4_enforce_command_file_state.py",
    "m_2_1_2_install_git_workflow_skill.py",
    "m_2_1_2_install_mission_system_skill.py",
    "m_2_1_3_restore_prompt_commands.py",
    "m_0_10_2_update_slash_commands.py",
    "m_0_10_1_populate_slash_commands.py",
    "m_0_10_14_update_implement_slash_command.py",
    "m_0_11_1_update_implement_slash_command.py",
    "m_0_13_0_update_research_implement_templates.py",
    "m_0_13_5_add_commit_workflow_to_templates.py",
    "m_3_2_0rc35_update_planning_templates.py",
    "m_2_0_1_fix_generated_command_templates.py",
    "m_0_10_0_python_only.py",
    "m_0_10_6_workflow_simplification.py",
    "m_0_11_1_improved_workflow_templates.py",
    "m_0_11_2_improved_workflow_templates.py",
]


@pytest.mark.parametrize("filename", _IN_SCOPE_GENERATED_SURFACE_MIGRATIONS)
def test_in_scope_migration_has_no_bare_write_text(filename: str) -> None:
    """An in-scope generated-surface migration must not reintroduce #3651.

    A bare ``.write_text(`` call on a read-only-destined path is exactly the
    pattern that caused #3651: it bypasses the canonical writer's
    restore-before-write step. Every confirmed in-scope migration must route
    through ``write_generated_file`` instead.
    """
    module_path = _MIGRATIONS_DIR / filename
    assert module_path.is_file(), f"expected migration file at {module_path}"

    source = module_path.read_text(encoding="utf-8")
    assert ".write_text(" not in source, (
        f"{filename} contains a bare '.write_text(' call — route it through "
        "write_generated_file() instead (see FR-002 / #3651)"
    )
    assert "write_generated_file" in source, (
        f"{filename} is in-scope for the canonical writer but does not import/use "
        "write_generated_file — has its write site been converted?"
    )
