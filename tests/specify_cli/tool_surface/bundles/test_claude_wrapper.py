"""Unit tests for the Claude Code plugin runtime bootstrap wrapper (WP05).

Covers:
    - write_wrappers creates bin/spec-kitty-wrapper (bash) and .cmd (Windows)
    - Version placeholder is substituted with the real version
    - bash wrapper is executable (mode 700)
    - wrapper_bash_content / wrapper_cmd_content helper functions
    - Empty version raises ValueError
    - Wrappers are idempotent (second call overwrites cleanly)
    - Wrapper content contains PATH-check and uvx-fallback logic
    - marketplace.json is written by ClaudeBundleProjector.build()
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from specify_cli.tool_surface.bundles.claude_wrapper import (
    write_wrappers,
    wrapper_bash_content,
    wrapper_cmd_content,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# write_wrappers — filesystem tests
# ---------------------------------------------------------------------------


class TestWriteWrappers:
    def test_creates_bash_wrapper(self, tmp_path: Path) -> None:
        write_wrappers(tmp_path, "3.2.0")
        assert (tmp_path / "bin" / "spec-kitty-wrapper").is_file()

    def test_creates_cmd_wrapper(self, tmp_path: Path) -> None:
        write_wrappers(tmp_path, "3.2.0")
        assert (tmp_path / "bin" / "spec-kitty-wrapper.cmd").is_file()

    def test_creates_bin_dir(self, tmp_path: Path) -> None:
        write_wrappers(tmp_path / "bundle", "1.0.0")
        assert (tmp_path / "bundle" / "bin").is_dir()

    def test_bash_version_substituted(self, tmp_path: Path) -> None:
        write_wrappers(tmp_path, "3.2.0")
        content = (tmp_path / "bin" / "spec-kitty-wrapper").read_text(encoding="utf-8")
        assert "3.2.0" in content
        assert "__SPEC_KITTY_VERSION__" not in content

    def test_cmd_version_substituted(self, tmp_path: Path) -> None:
        write_wrappers(tmp_path, "3.2.0")
        content = (tmp_path / "bin" / "spec-kitty-wrapper.cmd").read_text(encoding="utf-8")
        assert "3.2.0" in content
        assert "__SPEC_KITTY_VERSION__" not in content

    def test_bash_wrapper_is_executable(self, tmp_path: Path) -> None:
        write_wrappers(tmp_path, "3.2.0")
        bash_path = tmp_path / "bin" / "spec-kitty-wrapper"
        mode = os.stat(bash_path).st_mode
        # Must be executable by owner (user bit).
        assert mode & stat.S_IXUSR, "bash wrapper must be owner-executable"
        # Must not grant execute access outside the current user.
        assert not (mode & stat.S_IXGRP), "bash wrapper must not be group-executable"
        assert not (mode & stat.S_IXOTH), "bash wrapper must not be world-executable"

    def test_raises_on_empty_version(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            write_wrappers(tmp_path, "")

    def test_idempotent_second_write(self, tmp_path: Path) -> None:
        write_wrappers(tmp_path, "3.2.0")
        first = (tmp_path / "bin" / "spec-kitty-wrapper").read_bytes()
        write_wrappers(tmp_path, "3.2.0")
        second = (tmp_path / "bin" / "spec-kitty-wrapper").read_bytes()
        assert first == second

    def test_second_write_replaces_broad_existing_permissions(self, tmp_path: Path) -> None:
        write_wrappers(tmp_path, "3.2.0")
        bash_path = tmp_path / "bin" / "spec-kitty-wrapper"
        os.chmod(bash_path, 0o755)

        write_wrappers(tmp_path, "3.2.0")

        mode = os.stat(bash_path).st_mode
        assert mode & stat.S_IXUSR
        assert not (mode & stat.S_IXGRP)
        assert not (mode & stat.S_IXOTH)


# ---------------------------------------------------------------------------
# wrapper content helpers (pure, no I/O)
# ---------------------------------------------------------------------------


class TestWrapperBashContent:
    def test_contains_shebang(self) -> None:
        content = wrapper_bash_content("1.0.0")
        assert content.startswith("#!/usr/bin/env bash")

    def test_version_present(self) -> None:
        content = wrapper_bash_content("2.5.3")
        assert "2.5.3" in content

    def test_path_check_present(self) -> None:
        content = wrapper_bash_content("1.0.0")
        assert "command -v spec-kitty" in content

    def test_path_match_must_be_reachable(self) -> None:
        content = wrapper_bash_content("1.0.0")
        assert (
            "command -v spec-kitty >/dev/null 2>&1 "
            "&& spec-kitty --version >/dev/null 2>&1"
        ) in content

    def test_uvx_fallback_present(self) -> None:
        content = wrapper_bash_content("1.0.0")
        assert "command -v uvx" in content
        assert "uvx" in content
        assert "spec-kitty-cli" in content

    def test_error_message_present(self) -> None:
        content = wrapper_bash_content("1.0.0")
        assert "pip install spec-kitty-cli" in content

    def test_exec_delegates_to_spec_kitty(self) -> None:
        content = wrapper_bash_content("1.0.0")
        assert 'exec spec-kitty "$@"' in content

    def test_set_euo_pipefail(self) -> None:
        content = wrapper_bash_content("1.0.0")
        assert "set -euo pipefail" in content


class TestWrapperCmdContent:
    def test_starts_with_echo_off(self) -> None:
        content = wrapper_cmd_content("1.0.0")
        assert content.startswith("@echo off")

    def test_version_present(self) -> None:
        content = wrapper_cmd_content("2.5.3")
        assert "2.5.3" in content

    def test_where_spec_kitty_check(self) -> None:
        content = wrapper_cmd_content("1.0.0")
        assert "where spec-kitty" in content

    def test_where_match_must_be_reachable(self) -> None:
        content = wrapper_cmd_content("1.0.0")
        assert "CALL spec-kitty --version >nul 2>&1" in content

    def test_uvx_fallback_present(self) -> None:
        content = wrapper_cmd_content("1.0.0")
        assert "where uvx" in content
        assert "uvx" in content

    def test_error_message_present(self) -> None:
        content = wrapper_cmd_content("1.0.0")
        assert "pip install spec-kitty-cli" in content

    def test_percent_star_argument_forwarding(self) -> None:
        """Windows CMD uses %* to forward arguments."""
        content = wrapper_cmd_content("1.0.0")
        assert "%*" in content

    def test_exit_b_errorlevel_not_inside_parenthesized_block(self) -> None:
        """EXIT /B %ERRORLEVEL% must never be nested inside `IF ... ( ... )`.

        cmd.exe expands %VAR% in a parenthesized compound statement at parse
        time, so an EXIT /B %ERRORLEVEL% written inside one always reports the
        errorlevel current when the block was entered (the preceding `where`
        probe's 0) rather than the real exit code of the delegated command.
        """
        content = wrapper_cmd_content("1.0.0")
        lines = content.splitlines()
        depth = 0
        for line in lines:
            stripped = line.strip()
            if "EXIT /B %ERRORLEVEL%" in stripped:
                assert depth == 0, (
                    f"EXIT /B %ERRORLEVEL% is nested inside a parenthesized "
                    f"block (depth={depth}): {stripped!r}"
                )
            depth += stripped.count("(") - stripped.count(")")

    def test_no_parenthesized_if_blocks(self) -> None:
        """The wrapper uses GOTO, not `IF ... ( ... )`, around EXIT /B.

        A parenthesized IF block is exactly the construct that causes
        cmd.exe's parse-time %ERRORLEVEL% expansion bug; asserting it is
        gone (rather than only asserting EXIT /B's depth above) prevents a
        future edit from reintroducing it around some other guarded exit.
        """
        content = wrapper_cmd_content("1.0.0")
        assert "IF NOT ERRORLEVEL 1 (" not in content
        assert ") (" not in content

    def test_goto_labels_defined_and_referenced(self) -> None:
        content = wrapper_cmd_content("1.0.0")
        assert "GOTO try_uvx" in content
        assert ":try_uvx" in content
        assert "GOTO no_runtime" in content
        assert ":no_runtime" in content


class TestWrapperRuntimeFallback:
    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell wrapper")
    def test_bash_falls_back_to_uvx_when_path_shim_is_unreachable(
        self, tmp_path: Path
    ) -> None:
        write_wrappers(tmp_path, "9.9.9")
        fake_bin = tmp_path / "fake-bin"
        fake_bin.mkdir()

        stale_spec_kitty = fake_bin / "spec-kitty"
        stale_spec_kitty.write_text("#!/bin/sh\nexit 127\n")
        stale_spec_kitty.chmod(stale_spec_kitty.stat().st_mode | stat.S_IEXEC)

        fake_uvx = fake_bin / "uvx"
        fake_uvx.write_text("#!/bin/sh\nprintf 'uvx %s\\n' \"$*\"\n")
        fake_uvx.chmod(fake_uvx.stat().st_mode | stat.S_IEXEC)

        wrapper = tmp_path / "bin" / "spec-kitty-wrapper"
        bash_path = shutil.which("bash")
        assert bash_path is not None
        result = subprocess.run(
            [bash_path, str(wrapper), "mission", "list"],
            capture_output=True,
            text=True,
            env={"PATH": str(fake_bin)},
        )

        assert result.returncode == 0
        assert result.stdout == "uvx spec-kitty-cli==9.9.9 mission list\n"


# ---------------------------------------------------------------------------
# marketplace.json generation via ClaudeBundleProjector
# ---------------------------------------------------------------------------


class TestMarketplaceJson:
    def _run_build(self, tmp_path: Path) -> Path:
        from specify_cli.tool_surface.bundles.claude import ClaudeBundleProjector

        bundle_dir: Path = ClaudeBundleProjector(tmp_path / "dist").build(
            skip_validate=True
        )
        return bundle_dir

    def test_marketplace_json_exists(self, tmp_path: Path) -> None:
        self._run_build(tmp_path)
        assert (tmp_path / "dist" / "marketplace.json").is_file()

    def test_marketplace_json_schema(self, tmp_path: Path) -> None:
        self._run_build(tmp_path)
        payload = json.loads(
            (tmp_path / "dist" / "marketplace.json").read_text(encoding="utf-8")
        )
        assert payload["name"] == "spec-kitty-plugins"
        assert "plugins" in payload
        assert len(payload["plugins"]) == 1
        plugin = payload["plugins"][0]
        assert plugin["name"] == "spec-kitty"
        assert plugin["source"]["source"] == "git-subdir"
        assert "spec-kitty.git" in plugin["source"]["url"]

    def test_marketplace_json_not_inside_bundle(self, tmp_path: Path) -> None:
        """marketplace.json lives alongside the bundle dir, not inside it."""
        bundle_dir = self._run_build(tmp_path)
        # Must NOT appear inside the claude-code bundle directory.
        assert not (bundle_dir / "marketplace.json").exists()
        # Must appear one level up, in the output_dir.
        assert (bundle_dir.parent / "marketplace.json").is_file()


# ---------------------------------------------------------------------------
# Wrappers generated by ClaudeBundleProjector.build()
# ---------------------------------------------------------------------------


class TestBuildIncludesWrappers:
    def _run_build(self, tmp_path: Path) -> Path:
        from specify_cli.tool_surface.bundles.claude import ClaudeBundleProjector

        bundle_dir: Path = ClaudeBundleProjector(tmp_path / "dist").build(
            skip_validate=True
        )
        return bundle_dir

    def test_bash_wrapper_in_bundle(self, tmp_path: Path) -> None:
        bundle_dir = self._run_build(tmp_path)
        assert (bundle_dir / "bin" / "spec-kitty-wrapper").is_file()

    def test_cmd_wrapper_in_bundle(self, tmp_path: Path) -> None:
        bundle_dir = self._run_build(tmp_path)
        assert (bundle_dir / "bin" / "spec-kitty-wrapper.cmd").is_file()

    def test_wrapper_version_matches_plugin_json(self, tmp_path: Path) -> None:
        bundle_dir = self._run_build(tmp_path)
        plugin_json = json.loads(
            (bundle_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        version = plugin_json["version"]
        bash_content = (bundle_dir / "bin" / "spec-kitty-wrapper").read_text(encoding="utf-8")
        assert version in bash_content

    def test_build_is_still_idempotent_with_wrappers(self, tmp_path: Path) -> None:
        """Second build must produce byte-identical wrapper files."""
        projector_cls = __import__(
            "specify_cli.tool_surface.bundles.claude",
            fromlist=["ClaudeBundleProjector"],
        ).ClaudeBundleProjector
        projector = projector_cls(tmp_path / "dist")
        bd1 = projector.build(skip_validate=True)
        snap1 = {str(f.relative_to(bd1)): f.read_bytes() for f in sorted(bd1.rglob("*")) if f.is_file()}
        bd2 = projector.build(skip_validate=True)
        snap2 = {str(f.relative_to(bd2)): f.read_bytes() for f in sorted(bd2.rglob("*")) if f.is_file()}
        assert snap1 == snap2
