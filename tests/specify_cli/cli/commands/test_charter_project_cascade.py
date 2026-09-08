"""Direct project authoring must reach activation without pre-seeded graphs."""
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app
from tests.charter.test_project_registration import author_guidance

pytestmark = [pytest.mark.unit, pytest.mark.fast]
runner = CliRunner()


def test_cascade_activates_all_project_reference_kinds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    author_guidance(tmp_path)
    (tmp_path / '.kittify/config.yaml').write_text(
        'activated_agent_profiles: []\nactivated_directives: []\nactivated_procedures: []\n'
        'activated_tactics: []\nactivated_styleguides: []\n', encoding='utf-8',
    )
    result = runner.invoke(app, ['activate', 'agent-profile', 'ops-responder', '--cascade', 'all'])
    assert result.exit_code == 0, result.output
    from charter.activation.pack_context import PackContext
    context = PackContext.from_config(tmp_path)
    assert context.activated_agent_profiles == frozenset({'ops-responder'})
    assert context.activated_procedures == frozenset({'incident-runbook'})
    assert context.activated_directives == frozenset({'CHANGE_FREEZE'})
    assert context.activated_tactics == frozenset({'verify-rollback'})
    assert context.activated_styleguides == frozenset({'incident-notes'})


def test_cascade_warns_about_missing_project_reference(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    sources = author_guidance(tmp_path)
    sources['procedure'].unlink()
    result = runner.invoke(app, ['activate', 'agent-profile', 'ops-responder', '--cascade', 'all'])
    assert result.exit_code == 0, result.output
    assert 'Warning' in result.output and 'procedure:incident-runbook' in result.output
