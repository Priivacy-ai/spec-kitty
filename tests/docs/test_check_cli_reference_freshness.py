"""Tests for ``scripts/docs/check_cli_reference_freshness.py``.

Covers the seven rule IDs, the fixture-driven happy path, and the CLI
entry-point behavior (exit codes 0/1/2/3).
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import typer

os.environ.setdefault("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
os.environ.setdefault("SPEC_KITTY_NO_UPGRADE_CHECK", "1")

from scripts.docs import check_cli_reference_freshness as freshness
from scripts.docs._typer_walker import CommandPathEntry

pytestmark = [pytest.mark.unit, pytest.mark.fast]


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Synthetic live tree
# ---------------------------------------------------------------------------


def _entries_for_fixtures() -> list[CommandPathEntry]:
    """Live entries that match the ``sample_cli_reference.md`` fixture."""
    return [
        CommandPathEntry(
            path=("foo",),
            kind="command",
            hidden=False,
            deprecated=False,
            help_summary="Run the foo command",
            source_file=None,
            source_function=None,
            requires_saas_sync=False,
        ),
        CommandPathEntry(
            path=("bar",),
            kind="group",
            hidden=False,
            deprecated=False,
            help_summary="Bar subcommand",
            source_file=None,
            source_function=None,
            requires_saas_sync=False,
        ),
        CommandPathEntry(
            path=("bar", "baz"),
            kind="command",
            hidden=False,
            deprecated=False,
            help_summary="Baz of bar",
            source_file=None,
            source_function=None,
            requires_saas_sync=False,
        ),
        CommandPathEntry(
            path=("legacy-cmd",),
            kind="command",
            hidden=False,
            deprecated=True,
            help_summary="Deprecated: replaced by foo",
            source_file=None,
            source_function=None,
            requires_saas_sync=False,
        ),
        CommandPathEntry(
            path=("tracker",),
            kind="group",
            hidden=False,
            deprecated=False,
            help_summary="Tracker root",
            source_file=None,
            source_function=None,
            requires_saas_sync=True,
        ),
        CommandPathEntry(
            path=("tracker", "list"),
            kind="command",
            hidden=False,
            deprecated=False,
            help_summary="List tracker items",
            source_file=None,
            source_function=None,
            requires_saas_sync=True,
        ),
    ]


# ---------------------------------------------------------------------------
# Reference parsing
# ---------------------------------------------------------------------------


class TestExtractReferencedPaths:
    def test_extracts_headings(self) -> None:
        text = "## spec-kitty foo\n\nsome text\n\n## spec-kitty bar baz\n\n"
        paths = freshness.extract_referenced_paths(text)
        assert ("foo",) in paths
        assert ("bar", "baz") in paths

    def test_extracts_inline_code(self) -> None:
        text = "See `spec-kitty mission switch` for details.\n"
        paths = freshness.extract_referenced_paths(text)
        assert ("mission", "switch") in paths

    def test_extracts_classification_flags(self) -> None:
        text = (
            "## spec-kitty old\n\n"
            "> **Deprecated**: replaced by new\n\n"
            "## spec-kitty internal\n\n"
            "> **Internal**: dev only\n\n"
        )
        paths = freshness.extract_referenced_paths(text)
        assert paths[("old",)]["classified_deprecated"] is True
        assert paths[("internal",)]["classified_internal"] is True

    def test_extracts_summary_line(self) -> None:
        text = "## spec-kitty foo\n\n_Run the foo command_\n\n```\nUsage\n```\n"
        paths = freshness.extract_referenced_paths(text)
        assert paths[("foo",)]["summary"] == "Run the foo command"

    def test_extracts_nothing_from_empty(self) -> None:
        assert freshness.extract_referenced_paths("") == {}

    def test_normalize_path_strips_options_and_args(self) -> None:
        text = "## spec-kitty foo bar [OPTIONS] <ARG>\n"
        paths = freshness.extract_referenced_paths(text)
        assert ("foo", "bar") in paths


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------


class TestRules:
    def _clean_reference(self) -> str:
        return (FIXTURES_DIR / "sample_cli_reference.md").read_text(encoding="utf-8")

    def _missing_reference(self) -> str:
        return (FIXTURES_DIR / "sample_cli_reference_missing.md").read_text(
            encoding="utf-8"
        )

    def _extra_reference(self) -> str:
        return (FIXTURES_DIR / "sample_cli_reference_extra.md").read_text(
            encoding="utf-8"
        )

    def test_clean_reference_produces_no_findings(self) -> None:
        findings = freshness.evaluate_reference(
            entries=_entries_for_fixtures(),
            main_reference_text=self._clean_reference(),
            agent_reference_text="",
            saas_sync_enabled=True,
        )
        errors = [f for f in findings if f.severity == "error"]
        assert errors == []

    def test_missing_reference_emits_ref_missing(self) -> None:
        findings = freshness.evaluate_reference(
            entries=_entries_for_fixtures(),
            main_reference_text=self._missing_reference(),
            agent_reference_text="",
            saas_sync_enabled=True,
        )
        missing = [f for f in findings if f.rule_id == "REF-MISSING"]
        assert len(missing) == 1
        assert missing[0].path == ("bar", "baz")

    def test_extra_reference_emits_ref_extra(self) -> None:
        findings = freshness.evaluate_reference(
            entries=_entries_for_fixtures(),
            main_reference_text=self._extra_reference(),
            agent_reference_text="",
            saas_sync_enabled=True,
        )
        extra = [f for f in findings if f.rule_id == "REF-EXTRA"]
        assert len(extra) == 1
        assert extra[0].path == ("ghost-cmd",)

    def test_saas_sync_off_short_circuits(self) -> None:
        findings = freshness.evaluate_reference(
            entries=_entries_for_fixtures(),
            main_reference_text=self._clean_reference(),
            agent_reference_text="",
            saas_sync_enabled=False,
        )
        assert len(findings) == 1
        assert findings[0].rule_id == "REF-SAAS-SYNC-OFF"

    def test_deprecated_unclassified(self) -> None:
        ref = (
            "## spec-kitty foo\n\n_Run foo_\n\n## spec-kitty legacy-cmd\n\n"
            "_No banner here_\n\n## spec-kitty bar\n\n## spec-kitty bar baz\n"
            "## spec-kitty tracker\n## spec-kitty tracker list\n"
        )
        findings = freshness.evaluate_reference(
            entries=_entries_for_fixtures(),
            main_reference_text=ref,
            agent_reference_text="",
            saas_sync_enabled=True,
        )
        assert any(
            f.rule_id == "REF-DEPRECATED-UNCLASSIFIED" and f.path == ("legacy-cmd",)
            for f in findings
        )

    def test_internal_leak(self) -> None:
        entries = [
            CommandPathEntry(
                path=("foo",),
                kind="command",
                hidden=False,
                deprecated=False,
                help_summary="Internal - dev only",
                source_file=None,
                source_function=None,
                requires_saas_sync=False,
            )
        ]
        ref = "## spec-kitty foo\n\n_No banner_\n"
        findings = freshness.evaluate_reference(
            entries=entries,
            main_reference_text=ref,
            agent_reference_text="",
            saas_sync_enabled=True,
        )
        assert any(f.rule_id == "REF-INTERNAL-LEAK" for f in findings)

    def test_hidden_leak(self) -> None:
        entries = [
            CommandPathEntry(
                path=("ghost",),
                kind="command",
                hidden=True,
                deprecated=False,
                help_summary="Hidden command",
                source_file=None,
                source_function=None,
                requires_saas_sync=False,
            )
        ]
        ref = "## spec-kitty ghost\n\n_Leaked_\n"
        findings = freshness.evaluate_reference(
            entries=entries,
            main_reference_text=ref,
            agent_reference_text="",
            saas_sync_enabled=True,
        )
        assert any(f.rule_id == "REF-HIDDEN-LEAK" for f in findings)

    def test_hidden_in_internal_appendix_is_allowed(self) -> None:
        entries = [
            CommandPathEntry(
                path=("ghost",),
                kind="command",
                hidden=True,
                deprecated=False,
                help_summary="Hidden command",
                source_file=None,
                source_function=None,
                requires_saas_sync=False,
            )
        ]
        ref = "## spec-kitty ghost\n\n> **Internal**: appendix entry\n"
        findings = freshness.evaluate_reference(
            entries=entries,
            main_reference_text=ref,
            agent_reference_text="",
            saas_sync_enabled=True,
        )
        assert not any(f.rule_id == "REF-HIDDEN-LEAK" for f in findings)

    def test_help_drift_warning_by_default(self) -> None:
        entries = [
            CommandPathEntry(
                path=("foo",),
                kind="command",
                hidden=False,
                deprecated=False,
                help_summary="The new summary",
                source_file=None,
                source_function=None,
                requires_saas_sync=False,
            )
        ]
        ref = "## spec-kitty foo\n\n_The old summary_\n"
        findings = freshness.evaluate_reference(
            entries=entries,
            main_reference_text=ref,
            agent_reference_text="",
            saas_sync_enabled=True,
        )
        drift = [f for f in findings if f.rule_id == "HELP-DRIFT"]
        assert len(drift) == 1
        assert drift[0].severity == "warning"

    def test_help_drift_error_in_strict_mode(self) -> None:
        entries = [
            CommandPathEntry(
                path=("foo",),
                kind="command",
                hidden=False,
                deprecated=False,
                help_summary="The new summary",
                source_file=None,
                source_function=None,
                requires_saas_sync=False,
            )
        ]
        ref = "## spec-kitty foo\n\n_The old summary_\n"
        findings = freshness.evaluate_reference(
            entries=entries,
            main_reference_text=ref,
            agent_reference_text="",
            saas_sync_enabled=True,
            strict_mode=True,
        )
        drift = [f for f in findings if f.rule_id == "HELP-DRIFT"]
        assert drift[0].severity == "error"

    def test_agent_subtree_uses_agent_reference(self) -> None:
        entries = [
            CommandPathEntry(
                path=("agent", "tasks"),
                kind="command",
                hidden=False,
                deprecated=False,
                help_summary="Agent tasks",
                source_file=None,
                source_function=None,
                requires_saas_sync=False,
            )
        ]
        # In main but NOT in agent — REF-MISSING (wrong file)
        findings = freshness.evaluate_reference(
            entries=entries,
            main_reference_text="## spec-kitty agent tasks\n\n_Agent tasks_\n",
            agent_reference_text="",
            saas_sync_enabled=True,
        )
        assert any(
            f.rule_id == "REF-MISSING" and f.path == ("agent", "tasks") for f in findings
        )

    def test_agent_path_in_agent_reference_is_clean(self) -> None:
        entries = [
            CommandPathEntry(
                path=("agent", "tasks"),
                kind="command",
                hidden=False,
                deprecated=False,
                help_summary="Agent tasks",
                source_file=None,
                source_function=None,
                requires_saas_sync=False,
            )
        ]
        findings = freshness.evaluate_reference(
            entries=entries,
            main_reference_text="",
            agent_reference_text="## spec-kitty agent tasks\n\n_Agent tasks_\n",
            saas_sync_enabled=True,
        )
        errors = [f for f in findings if f.severity == "error"]
        assert errors == []


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


class TestCli:
    @pytest.fixture()
    def stub_specify_cli(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> Iterator[None]:
        import sys
        import types

        synthetic = typer.Typer()

        @synthetic.command("foo", help="Run the foo command")
        def foo_cmd() -> None: ...

        @synthetic.command(
            "legacy-cmd", help="Deprecated: replaced by foo", deprecated=True
        )
        def legacy_cmd() -> None: ...

        bar_app = typer.Typer()

        @bar_app.command("baz", help="Baz of bar")
        def baz_cmd() -> None: ...

        synthetic.add_typer(bar_app, name="bar", help="Bar subcommand")

        tracker_app = typer.Typer()

        @tracker_app.command("list", help="List tracker items")
        def tracker_list() -> None: ...

        synthetic.add_typer(tracker_app, name="tracker", help="Tracker root")

        fake = types.ModuleType("specify_cli")
        fake.app = synthetic  # type: ignore[attr-defined]
        fake_cmds = types.ModuleType("specify_cli.cli.commands")

        def register_commands(_app: typer.Typer) -> None:
            return None

        fake_cmds.register_commands = register_commands  # type: ignore[attr-defined]
        fake_cli = types.ModuleType("specify_cli.cli")
        monkeypatch.setitem(sys.modules, "specify_cli", fake)
        monkeypatch.setitem(sys.modules, "specify_cli.cli", fake_cli)
        monkeypatch.setitem(sys.modules, "specify_cli.cli.commands", fake_cmds)
        yield

    def test_main_returns_2_for_missing_reference(self, tmp_path: Path) -> None:
        rc = freshness.main(
            [
                "--reference",
                str(tmp_path / "absent.md"),
                "--agent-reference",
                str(tmp_path / "agent.md"),
            ]
        )
        assert rc == 2

    def test_main_returns_2_for_missing_agent_reference(
        self, tmp_path: Path
    ) -> None:
        ref = tmp_path / "ref.md"
        ref.write_text("# ref\n", encoding="utf-8")
        rc = freshness.main(
            [
                "--reference",
                str(ref),
                "--agent-reference",
                str(tmp_path / "absent.md"),
            ]
        )
        assert rc == 2

    def test_main_clean_returns_0(
        self,
        tmp_path: Path,
        stub_specify_cli: None,
    ) -> None:
        ref = tmp_path / "ref.md"
        ref.write_text(
            (FIXTURES_DIR / "sample_cli_reference.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        agent_ref = tmp_path / "agent.md"
        agent_ref.write_text("# agent\n", encoding="utf-8")
        rc = freshness.main(
            [
                "--reference",
                str(ref),
                "--agent-reference",
                str(agent_ref),
            ]
        )
        assert rc == 0

    def test_main_missing_returns_1(
        self,
        tmp_path: Path,
        stub_specify_cli: None,
    ) -> None:
        ref = tmp_path / "ref.md"
        ref.write_text(
            (FIXTURES_DIR / "sample_cli_reference_missing.md").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        agent_ref = tmp_path / "agent.md"
        agent_ref.write_text("# agent\n", encoding="utf-8")
        rc = freshness.main(
            [
                "--reference",
                str(ref),
                "--agent-reference",
                str(agent_ref),
            ]
        )
        assert rc == 1

    def test_main_extra_returns_1(
        self,
        tmp_path: Path,
        stub_specify_cli: None,
    ) -> None:
        ref = tmp_path / "ref.md"
        ref.write_text(
            (FIXTURES_DIR / "sample_cli_reference_extra.md").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        agent_ref = tmp_path / "agent.md"
        agent_ref.write_text("# agent\n", encoding="utf-8")
        rc = freshness.main(
            [
                "--reference",
                str(ref),
                "--agent-reference",
                str(agent_ref),
            ]
        )
        assert rc == 1

    def test_main_no_saas_returns_3(
        self,
        tmp_path: Path,
        stub_specify_cli: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Force the SAAS check off via the internal flag.
        monkeypatch.setattr(freshness, "_SAAS_SYNC_PRESET", False)
        monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

        ref = tmp_path / "ref.md"
        ref.write_text(
            (FIXTURES_DIR / "sample_cli_reference_no_saas.md").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        agent_ref = tmp_path / "agent.md"
        agent_ref.write_text("# agent\n", encoding="utf-8")
        rc = freshness.main(
            [
                "--reference",
                str(ref),
                "--agent-reference",
                str(agent_ref),
                "--saas-sync-was-set",
            ]
        )
        assert rc == 3

    def test_main_writes_json_report(
        self,
        tmp_path: Path,
        stub_specify_cli: None,
    ) -> None:
        ref = tmp_path / "ref.md"
        ref.write_text(
            (FIXTURES_DIR / "sample_cli_reference_extra.md").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        agent_ref = tmp_path / "agent.md"
        agent_ref.write_text("# agent\n", encoding="utf-8")
        report = tmp_path / "report.json"
        rc = freshness.main(
            [
                "--reference",
                str(ref),
                "--agent-reference",
                str(agent_ref),
                "--report",
                str(report),
            ]
        )
        assert rc == 1
        data = json.loads(report.read_text(encoding="utf-8"))
        assert "findings" in data
        assert any(f["rule_id"] == "REF-EXTRA" for f in data["findings"])

    def test_main_ci_mode_writes_to_stdout(
        self,
        tmp_path: Path,
        stub_specify_cli: None,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        ref = tmp_path / "ref.md"
        ref.write_text(
            (FIXTURES_DIR / "sample_cli_reference_extra.md").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        agent_ref = tmp_path / "agent.md"
        agent_ref.write_text("# agent\n", encoding="utf-8")
        rc = freshness.main(
            [
                "--reference",
                str(ref),
                "--agent-reference",
                str(agent_ref),
                "--ci",
            ]
        )
        assert rc == 1
        out = capsys.readouterr().out
        assert "REF-EXTRA" in out


# ---------------------------------------------------------------------------
# Real-Typer-app smoke test (integration)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_real_typer_app_visible_count_within_tolerance() -> None:
    """The walker against the live ``specify_cli.app`` should match audit.

    Expected from ``cli-audit-3-2.md``: 214 visible / 5 hidden / 2 deprecated.
    Tolerance: ±10% on the visible count (193..235) to allow natural growth.
    """
    os.environ["SPEC_KITTY_ENABLE_SAAS_SYNC"] = "1"
    os.environ["SPEC_KITTY_NO_UPGRADE_CHECK"] = "1"

    import sys

    saved = sys.argv[:]
    sys.argv = ["spec-kitty", "--help"]
    try:
        from specify_cli import app
        from specify_cli.cli.commands import register_commands

        register_commands(app)
    finally:
        sys.argv = saved

    from scripts.docs._typer_walker import walk

    entries = walk(app)
    visible = [e for e in entries if not e.hidden]
    deprecated = [e for e in entries if e.deprecated]
    assert 193 <= len(visible) <= 235, (
        f"visible count {len(visible)} is outside the ±10% tolerance band "
        "around the audit baseline of 214"
    )
    assert len(deprecated) >= 1
