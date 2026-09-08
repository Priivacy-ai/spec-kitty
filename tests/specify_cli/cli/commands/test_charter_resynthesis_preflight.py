"""Resynthesis prerequisites must fail before activation is persisted (#4101)."""
from pathlib import Path
import subprocess

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app
from tests.charter.test_project_registration import author_guidance

pytestmark = [pytest.mark.unit, pytest.mark.fast]
runner = CliRunner()


def test_resynthesis_missing_interview_preserves_activation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    author_guidance(tmp_path)
    config = tmp_path / '.kittify/config.yaml'
    config.write_text('activated_agent_profiles: []\n', encoding='utf-8')
    before = config.read_bytes()
    result = runner.invoke(app, ['activate', 'agent-profile', 'ops-responder', '--cascade', 'all', '--resynthesize'])
    assert result.exit_code == 1, result.output
    assert config.read_bytes() == before
    assert not (tmp_path / '.kittify/charter/synthesis-manifest.yaml').exists()
    assert 'interview' in result.output.lower()
