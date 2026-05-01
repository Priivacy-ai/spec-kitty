"""Tests for ``spec-kitty glossary show`` subcommand (T032)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli.cli.commands.glossary import app
from specify_cli.glossary.entity_pages import TermNotFoundError

runner = CliRunner()


def _make_page(tmp_path: Path, content: str = "# My Term\n\nDefinition here.") -> Path:
    """Write a temporary entity page file and return its path."""
    page = tmp_path / "glossary-my-term.md"
    page.write_text(content, encoding="utf-8")
    return page


class TestGlossaryShow:
    """Four scenarios for the ``show`` subcommand."""

    def test_success_term_found(self, tmp_path: Path) -> None:
        """Success: generate_one returns a valid page → exit 0, content printed."""
        page_path = _make_page(tmp_path, "# Deployment Target\n\nA target environment.")

        with (
            patch(
                "specify_cli.glossary.entity_pages.GlossaryEntityPageRenderer.generate_one",
                return_value=page_path,
            ) as mock_gen,
            patch("specify_cli.cli.commands.glossary.Path.cwd", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["show", "deployment-target"])

        assert result.exit_code == 0, result.output
        assert "Deployment Target" in result.output or "deployment" in result.output.lower()
        # generate_one was called with the URN form first
        mock_gen.assert_called_once_with("glossary:deployment-target")

    def test_not_found_exits_1(self, tmp_path: Path) -> None:
        """Failure: both generate_one calls raise TermNotFoundError → exit 1 + hint."""
        with (
            patch(
                "specify_cli.glossary.entity_pages.GlossaryEntityPageRenderer.generate_one",
                side_effect=TermNotFoundError("not found"),
            ),
            patch("specify_cli.cli.commands.glossary.Path.cwd", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["show", "unknown-term"])

        assert result.exit_code == 1
        # Error message must contain the term name
        assert "unknown-term" in result.output
        # Hint must appear
        assert "spec-kitty glossary list" in result.output

    def test_urn_input_not_double_prefixed(self, tmp_path: Path) -> None:
        """URN input: 'glossary:foo' must be passed verbatim, not 'glossary:glossary:foo'."""
        page_path = _make_page(tmp_path, "# Foo\n\nFoo definition.")

        with (
            patch(
                "specify_cli.glossary.entity_pages.GlossaryEntityPageRenderer.generate_one",
                return_value=page_path,
            ) as mock_gen,
            patch("specify_cli.cli.commands.glossary.Path.cwd", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["show", "glossary:foo"])

        assert result.exit_code == 0, result.output
        # Must be called with exactly the original URN — no double-prefix
        mock_gen.assert_called_once_with("glossary:foo")

    def test_bare_term_normalized_to_urn(self, tmp_path: Path) -> None:
        """Bare term: first generate_one call must use 'glossary:<term>' form."""
        page_path = _make_page(tmp_path, "# Foo\n\nFoo definition.")

        call_args: list[str] = []

        def _mock_generate_one(term_id: str) -> Path:
            call_args.append(term_id)
            return page_path

        with (
            patch(
                "specify_cli.glossary.entity_pages.GlossaryEntityPageRenderer.generate_one",
                side_effect=_mock_generate_one,
            ),
            patch("specify_cli.cli.commands.glossary.Path.cwd", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["show", "foo"])

        assert result.exit_code == 0, result.output
        assert len(call_args) >= 1
        # The very first call must use the normalized URN form
        assert call_args[0] == "glossary:foo"
