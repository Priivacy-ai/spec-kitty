"""Tests for specify_cli.runtime.doctor.check_command_file_health.

Covers the version-marker head-scan logic introduced when the marker
moved from line 1 (legacy) to immediately after the YAML frontmatter
(new layout).  These tests pin the contract that:

- A correct marker is recognized whether it sits on line 1 or on line 4
  (after a ``---\\ndescription: ...\\n---`` frontmatter block).
- A stale marker (different version) yields a warning.
- A missing marker yields a warning.
- The shim length threshold (now <15 non-empty lines) accommodates the
  three extra frontmatter lines.
- Files for unconfigured agents are skipped.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.runtime.doctor import check_command_file_health

pytestmark = pytest.mark.fast


def _bootstrap_project(tmp_path: Path, agent_root: str = ".claude", subdir: str = "commands") -> Path:
    """Create a minimal kittify project with a single configured agent."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    agent_key = agent_root.lstrip(".")
    (kittify / "config.yaml").write_text(
        "project:\n"
        "  uuid: test-uuid-1234\n"
        "agents:\n"
        "  available:\n"
        f"    - {agent_key}\n",
        encoding="utf-8",
    )
    (tmp_path / agent_root / subdir).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _write_full_consumer_file_set(
    project: Path,
    *,
    factory,
    agent_root: str = ".claude",
    subdir: str = "commands",
) -> None:
    """Write every consumer command file using *factory(command, is_prompt) -> str*."""
    from specify_cli.shims.registry import CLI_DRIVEN_COMMANDS, PROMPT_DRIVEN_COMMANDS

    target_dir = project / agent_root / subdir
    for command in PROMPT_DRIVEN_COMMANDS:
        (target_dir / f"spec-kitty.{command}.md").write_text(
            factory(command, True), encoding="utf-8"
        )
    for command in CLI_DRIVEN_COMMANDS:
        (target_dir / f"spec-kitty.{command}.md").write_text(
            factory(command, False), encoding="utf-8"
        )


def _current_marker() -> str:
    from specify_cli.shims.generator import _get_cli_version

    return f"<!-- spec-kitty-command-version: {_get_cli_version()} -->"


def _new_layout_shim() -> str:
    """Shim file using the post-fix layout (frontmatter on line 1)."""
    return (
        "---\n"
        "description: Demo command\n"
        "---\n"
        f"{_current_marker()}\n"
        "Run this exact command and treat its output as authoritative.\n"
        "Do not rediscover context from branches, files, prompt contents, or separate charter loads.\n"
        "When mission selection is required, pass --mission <handle> (mission_id, mid8, or mission_slug).\n"
        "\n"
        "`spec-kitty agent action implement $ARGUMENTS --agent claude`\n"
    )


def _legacy_layout_shim() -> str:
    """Shim file using the pre-fix layout (marker on line 1, no frontmatter)."""
    return (
        f"{_current_marker()}\n"
        "Run this exact command and treat its output as authoritative.\n"
        "Do not rediscover context from branches, files, prompt contents, or separate charter loads.\n"
        "When mission selection is required, pass --mission <handle> (mission_id, mid8, or mission_slug).\n"
        "\n"
        "`spec-kitty agent action implement $ARGUMENTS --agent claude`\n"
    )


def _new_layout_prompt() -> str:
    """Prompt-driven file: long body + frontmatter + marker after frontmatter."""
    body_lines = [f"Body line {i}" for i in range(60)]
    return (
        "---\n"
        "description: Demo prompt\n"
        "---\n"
        f"{_current_marker()}\n"
        + "\n".join(body_lines)
        + "\n"
    )


def test_new_layout_shim_passes_health_check(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)

    def factory(command: str, is_prompt: bool) -> str:
        return _new_layout_prompt() if is_prompt else _new_layout_shim()

    _write_full_consumer_file_set(project, factory=factory)
    issues = check_command_file_health(project)
    # No version-marker warnings, no missing-file errors, no length warnings
    marker_issues = [i for i in issues if "version marker" in i["issue"]]
    length_issues = [i for i in issues if "non-empty lines" in i["issue"]]
    assert marker_issues == [], f"unexpected marker warnings: {marker_issues}"
    assert length_issues == [], f"unexpected length warnings: {length_issues}"


def test_legacy_layout_shim_still_passes(tmp_path: Path) -> None:
    """Backwards-compat: line-1 marker is still considered healthy."""
    project = _bootstrap_project(tmp_path)

    def factory(command: str, is_prompt: bool) -> str:
        if is_prompt:
            body_lines = [f"Body line {i}" for i in range(60)]
            return f"{_current_marker()}\n" + "\n".join(body_lines) + "\n"
        return _legacy_layout_shim()

    _write_full_consumer_file_set(project, factory=factory)
    issues = check_command_file_health(project)
    marker_issues = [i for i in issues if "version marker" in i["issue"]]
    assert marker_issues == [], f"legacy marker not recognized: {marker_issues}"


def test_stale_marker_emits_warning(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)

    def factory(command: str, is_prompt: bool) -> str:
        stale = "<!-- spec-kitty-command-version: 0.0.1-stale -->"
        if is_prompt:
            body_lines = [f"Body line {i}" for i in range(60)]
            return (
                "---\n"
                "description: Demo prompt\n"
                "---\n"
                f"{stale}\n" + "\n".join(body_lines) + "\n"
            )
        return (
            "---\n"
            "description: Demo command\n"
            "---\n"
            f"{stale}\n"
            "Run this exact command and treat its output as authoritative.\n"
            "Do not rediscover context from branches, files, prompt contents, or separate charter loads.\n"
            "When mission selection is required, pass --mission <handle> (mission_id, mid8, or mission_slug).\n"
            "\n"
            "`spec-kitty agent action implement $ARGUMENTS --agent claude`\n"
        )

    _write_full_consumer_file_set(project, factory=factory)
    issues = check_command_file_health(project)
    marker_issues = [i for i in issues if "version marker" in i["issue"]]
    assert marker_issues, "expected at least one stale-marker warning"
    for issue in marker_issues:
        assert issue["severity"] == "warning"


def test_missing_file_emits_error(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    issues = check_command_file_health(project)
    # No files written → every consumer command should report missing
    missing_issues = [i for i in issues if i["issue"] == "missing"]
    assert missing_issues, "expected missing-file errors when no files exist"
    for issue in missing_issues:
        assert issue["severity"] == "error"


def test_unreadable_file_emits_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _bootstrap_project(tmp_path)

    def factory(command: str, is_prompt: bool) -> str:
        return _new_layout_prompt() if is_prompt else _new_layout_shim()

    _write_full_consumer_file_set(project, factory=factory)

    real_read_text = Path.read_text

    def selective_oserror(self: Path, *args, **kwargs) -> str:  # type: ignore[override]
        if self.name == "spec-kitty.implement.md":
            raise OSError("permission denied")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", selective_oserror)
    issues = check_command_file_health(project)
    unreadable = [i for i in issues if "unreadable" in i["issue"]]
    assert unreadable, "expected an unreadable error for the patched file"


def test_unknown_agent_root_skipped(tmp_path: Path) -> None:
    """When an agent root has no AGENT_DIR_TO_KEY mapping, it's skipped silently."""
    project = _bootstrap_project(tmp_path)
    # Create a fake agent dir with no key mapping; doctor must not crash on it.
    (project / ".bogus" / "commands").mkdir(parents=True)
    (project / ".bogus" / "commands" / "spec-kitty.implement.md").write_text(
        _new_layout_shim(), encoding="utf-8"
    )
    # Should still report missing for the configured agent without crashing
    issues = check_command_file_health(project)
    bogus_issues = [i for i in issues if i["agent"] == "bogus"]
    assert bogus_issues == []


def test_returns_empty_when_imports_fail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Defensive guard: ImportError on private deps yields []."""
    import builtins

    real_import = builtins.__import__

    def fail_specific(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "specify_cli.shims.registry":
            raise ImportError("simulated")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_specific)
    assert check_command_file_health(tmp_path) == []


def test_short_shim_under_threshold(tmp_path: Path) -> None:
    """A 9-line non-empty shim (frontmatter + marker + 3 instructions + CLI call) is OK."""
    project = _bootstrap_project(tmp_path)

    def factory(command: str, is_prompt: bool) -> str:
        return _new_layout_prompt() if is_prompt else _new_layout_shim()

    _write_full_consumer_file_set(project, factory=factory)
    issues = check_command_file_health(project)
    # Specifically: no shim should hit the "non-empty lines" length warning.
    length_issues = [
        i for i in issues
        if "non-empty lines" in i["issue"] and "thin shim" in i["issue"]
    ]
    assert length_issues == [], (
        f"new-layout shims (8 non-empty lines) must stay under the 15-line "
        f"threshold; got: {length_issues}"
    )


def test_oversized_shim_emits_warning(tmp_path: Path) -> None:
    """A bloated shim (>=15 non-empty lines) raises a length warning."""
    project = _bootstrap_project(tmp_path)
    bloated = (
        "---\n"
        "description: Demo command\n"
        "---\n"
        f"{_current_marker()}\n"
        + "\n".join([f"extra body line {i}" for i in range(20)])
        + "\n"
    )

    def factory(command: str, is_prompt: bool) -> str:
        return _new_layout_prompt() if is_prompt else bloated

    _write_full_consumer_file_set(project, factory=factory)
    issues = check_command_file_health(project)
    length_issues = [
        i for i in issues if "thin shim" in i["issue"]
    ]
    assert length_issues, "expected length warning for oversized shim"


def test_short_prompt_emits_warning(tmp_path: Path) -> None:
    """A prompt-driven file under 50 non-empty lines raises a length warning."""
    project = _bootstrap_project(tmp_path)
    short_prompt = (
        "---\n"
        "description: Tiny prompt\n"
        "---\n"
        f"{_current_marker()}\n"
        "Just a few lines.\n"
    )

    def factory(command: str, is_prompt: bool) -> str:
        return short_prompt if is_prompt else _new_layout_shim()

    _write_full_consumer_file_set(project, factory=factory)
    issues = check_command_file_health(project)
    length_issues = [
        i for i in issues if "prompt-driven" in i["issue"]
    ]
    assert length_issues, "expected length warning for tiny prompt"
