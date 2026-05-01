"""Tests for EvidenceOrchestrator and load_url_list_from_config."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import ruamel.yaml

from charter.evidence.orchestrator import (
    EvidenceOrchestrator,
    EvidenceResult,
    load_url_list_from_config,
)

# Marked for mutmut sandbox skip — see ADR 2026-04-20-1.
# Reason: trampoline bug: python -m specify_cli subprocess
pytestmark = pytest.mark.non_sandbox


def test_full_collection_returns_bundle(tmp_path: Path) -> None:
    """With a Python project, both code signals and corpus are populated."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "main.py").write_text("# main\n")
    orch = EvidenceOrchestrator(repo_root=tmp_path, url_list=("https://example.com",))
    result = orch.collect()
    assert isinstance(result, EvidenceResult)
    assert result.bundle.code_signals is not None
    assert result.bundle.code_signals.primary_language == "python"
    assert result.bundle.url_list == ("https://example.com",)
    assert result.bundle.corpus_snapshot is not None  # generic fallback at minimum
    assert result.warnings == []


def test_code_failure_emits_warning(tmp_path: Path) -> None:
    """Code-reading failure -> warning, synthesis proceeds with None code_signals."""
    orch = EvidenceOrchestrator(repo_root=tmp_path / "nonexistent")
    result = orch.collect()
    assert result.bundle.code_signals is None
    assert any("code-reading" in w.lower() for w in result.warnings)


def test_skip_code_evidence(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("")
    orch = EvidenceOrchestrator(repo_root=tmp_path, skip_code=True)
    result = orch.collect()
    assert result.bundle.code_signals is None
    assert result.warnings == [] or all("corpus" in w.lower() for w in result.warnings)


def test_skip_corpus(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("")
    orch = EvidenceOrchestrator(repo_root=tmp_path, skip_corpus=True)
    result = orch.collect()
    assert result.bundle.corpus_snapshot is None


def test_url_list_assembled(tmp_path: Path) -> None:
    urls = ("https://a.example.com", "https://b.example.com")
    orch = EvidenceOrchestrator(repo_root=tmp_path, url_list=urls)
    result = orch.collect()
    assert result.bundle.url_list == urls


def test_load_url_list_absent(tmp_path: Path) -> None:
    assert load_url_list_from_config(tmp_path) == ()


def test_load_url_list_present(tmp_path: Path) -> None:
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    yaml = ruamel.yaml.YAML()
    config = {"charter": {"synthesis_inputs": {"url_list": ["https://x.com", "https://y.com"]}}}
    with (kittify / "config.yaml").open("w") as fh:
        yaml.dump(config, fh)
    result = load_url_list_from_config(tmp_path)
    assert set(result) == {"https://x.com", "https://y.com"}


def test_bundle_is_empty_when_all_skipped(tmp_path: Path) -> None:
    orch = EvidenceOrchestrator(repo_root=tmp_path, skip_code=True, skip_corpus=True)
    result = orch.collect()
    assert result.bundle.code_signals is None
    assert result.bundle.corpus_snapshot is None
    assert result.bundle.url_list == ()
    assert result.bundle.is_empty


@pytest.mark.integration
def test_dry_run_evidence_on_spec_kitty_repo() -> None:
    """charter synthesize --adapter fixture --dry-run-evidence exits 0 and detects a language.

    spec-kitty has both Python indicators (pyproject.toml, src/specify_cli/) and JavaScript
    indicators (package.json for Playwright/test tooling), so the heuristic detector may
    legitimately select either 'python' or 'javascript' as the primary language.  The test
    verifies that the detector commits to a specific, non-unknown language rather than
    checking for a particular one — either is acceptable (acceptance criterion #9).
    """
    import os

    repo_root = Path(__file__).parent.parent.parent.parent  # root of spec-kitty repo in worktree
    src_path = str(repo_root / "src")
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_path}:{existing_pythonpath}" if existing_pythonpath else src_path
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "specify_cli",
            "charter",
            "synthesize",
            "--adapter",
            "fixture",
            "--dry-run-evidence",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    assert "Evidence dry-run summary" in result.stdout
    assert "Code signals:" in result.stdout
    # spec-kitty has both pyproject.toml (Python) and package.json (JavaScript tooling),
    # so either language is a valid detection outcome — but "unknown" is not acceptable.
    assert "lang=python" in result.stdout or "lang=javascript" in result.stdout, f"Expected lang=python or lang=javascript in output, got:\n{result.stdout}"
