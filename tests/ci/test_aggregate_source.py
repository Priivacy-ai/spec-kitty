"""Aggregate coverage must score the source PR without executing its checkout."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.fast]
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/ci/aggregate_source.py'


def git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(cwd), *args], text=True).strip()


def source_fixture(tmp_path: Path) -> tuple[Path, dict, str]:
    repo = tmp_path / 'repo'
    repo.mkdir()
    git(repo, 'init', '-q')
    git(repo, 'config', 'user.email', 'test@example.invalid')
    git(repo, 'config', 'user.name', 'Test')
    (repo / '.github').mkdir()
    (repo / '.github/ci-module-registry.yml').write_text('modules: []\n')
    (repo / 'src/kernel').mkdir(parents=True)
    (repo / 'src/kernel/example.py').write_text('value = 1\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'base')
    base = git(repo, 'rev-parse', 'HEAD')
    (repo / 'src/kernel/example.py').write_text('value = 1\nnew_value = 2\n')
    (repo / '.github/ci-module-registry.yml').write_text('modules: [{module: kernel, tier: standard, shard_count: 1}]\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'source')
    head = git(repo, 'rev-parse', 'HEAD')
    git(repo, 'checkout', '-q', base)
    git(repo, 'remote', 'add', 'origin', str(repo))
    run = {'id': 42, 'run_attempt': 1, 'path': '.github/workflows/ci-modules.yml',
           'event': 'pull_request', 'head_sha': head,
           'repository': {'full_name': 'spec-kitty/spec-kitty'},
           'pull_requests': [{'number': 7, 'head': {'sha': head}, 'base': {'sha': base, 'repo': {'full_name': 'spec-kitty/spec-kitty'}}}]}
    return repo, run, base


def run_source(repo: Path, run: dict) -> subprocess.CompletedProcess[str]:
    source = repo / 'source-run.json'
    source.write_text(json.dumps(run))
    return subprocess.run([sys.executable, str(SCRIPT), str(source), '--repository', 'spec-kitty/spec-kitty',
                           '--run-id', '42', '--attempt', '1'], cwd=repo,
                          capture_output=True, text=True, env=dict(os.environ))


def test_source_registry_and_diff_are_from_pr_while_checkout_stays_trusted(tmp_path: Path) -> None:
    repo, run, trusted = source_fixture(tmp_path)
    result = run_source(repo, run)
    assert result.returncode == 0, result.stderr
    out = repo / 'out/aggregate/source'
    assert 'new_value = 2' in (out / 'diff.patch').read_text()
    assert yaml.safe_load((out / 'ci-module-registry.yml').read_text())['modules'][0]['module'] == 'kernel'
    assert json.loads((out / 'source.json').read_text())['head_sha'] == run['head_sha']
    assert git(repo, 'rev-parse', 'HEAD') == trusted


@pytest.mark.parametrize('mutation', ['stale_attempt', 'wrong_run', 'wrong_repo', 'wrong_workflow', 'missing_pr', 'bad_sha'])
def test_source_rejects_ambiguous_or_stale_evidence(tmp_path: Path, mutation: str) -> None:
    repo, run, trusted = source_fixture(tmp_path)
    if mutation == 'stale_attempt': run['run_attempt'] = 2
    elif mutation == 'wrong_run': run['id'] = 43
    elif mutation == 'wrong_repo': run['repository']['full_name'] = 'other/repo'
    elif mutation == 'wrong_workflow': run['path'] = '.github/workflows/untrusted.yml'
    elif mutation == 'missing_pr': run['pull_requests'] = []
    else: run['head_sha'] = '--upload-pack=evil'
    result = run_source(repo, run)
    assert result.returncode != 0
    assert not (repo / 'out/aggregate/source/source.json').exists()
    assert git(repo, 'rev-parse', 'HEAD') == trusted
