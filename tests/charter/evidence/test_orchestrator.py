"""Tests for EvidenceOrchestrator and load_url_list_from_config."""
from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import ruamel.yaml

from charter.evidence.orchestrator import (    EvidenceOrchestrator,
    EvidenceResult,
    load_url_list_from_config,
)

# Marked for mutmut sandbox skip — see ADR 2026-04-20-1.
# Reason: trampoline bug: python -m specify_cli subprocess
pytestmark = pytest.mark.non_sandbox

# ANSI SGR escape sequence, e.g. "\x1b[33m" / "\x1b[1;36m" / "\x1b[0m".
_ANSI_SGR_RE = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture
def _synthesis_manifest_guard() -> Iterator[Path]:
    """Snapshot + restore the repo's REAL synthesis manifest around a CLI subprocess test.

    ``charter synthesize`` writes ``.kittify/charter/synthesis-manifest.yaml`` at a
    path fixed relative to the resolved repo root — no CLI flag exposes a target
    override (see ``src/charter/synthesizer/manifest.py::MANIFEST_PATH``), so this
    test cannot simply redirect the write to a ``tmp_path`` sandbox. It guards the
    on-disk bytes instead: snapshot before, restore in a ``finally`` block after —
    so a future regression that reintroduces a real-manifest write (or any
    exception mid-test) never leaves the working tree dirty (#2672).
    """
    repo_root = Path(__file__).parent.parent.parent.parent
    manifest_path = repo_root / ".kittify" / "charter" / "synthesis-manifest.yaml"
    original = manifest_path.read_bytes() if manifest_path.exists() else None
    try:
        yield manifest_path
    finally:
        if original is None:
            if manifest_path.exists():
                manifest_path.unlink()
        elif not manifest_path.exists() or manifest_path.read_bytes() != original:
            manifest_path.write_bytes(original)


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
def test_dry_run_evidence_on_spec_kitty_repo(
    _synthesis_manifest_guard: Path,
) -> None:
    """charter synthesize --adapter fixture --dry-run-evidence exits 0 and detects a language.

    spec-kitty has both Python indicators (pyproject.toml, src/specify_cli/) and JavaScript
    indicators (package.json for Playwright/test tooling), so the heuristic detector may
    legitimately select either 'python' or 'javascript' as the primary language.  The test
    verifies that the detector commits to a specific, non-unknown language rather than
    checking for a particular one — either is acceptable (acceptance criterion #9).

    Determinism (#2672): this test drives the CLI as a *subprocess*, so an in-process
    ``CliConsole.set_plain()``/``set_all_plain()`` call would never reach the child. The
    ``CliConsole`` seam (``src/specify_cli/cli/console.py``) documents that "determinism
    is a property of the object, not the environment" — for a subprocess, the object-level
    seam is driven by handing the child its own colour-free environment. Rich's
    ``Console`` already honours ``NO_COLOR`` at construction time (reads
    ``os.environ["NO_COLOR"]`` when ``no_color`` isn't explicitly passed), so setting it
    in the ``env`` dict built below is TEST-LOCAL to the child process — it never mutates
    the real ``os.environ`` and cannot leak into sibling tests or subprocesses. ``FORCE_COLOR``
    is also forced here so the assertion is pinned against the worst case (the Claude Code
    harness exports ``FORCE_COLOR=3``, which splices ANSI SGR codes into the
    ``lang=<value>`` token via Rich's automatic repr-highlighter — reproducible, not
    hypothetical) — ``NO_COLOR`` must win over an inherited ``FORCE_COLOR``. The stdout
    match is additionally ANSI-stripped as a second, independent layer of insensitivity.
    """
    import os

    repo_root = Path(__file__).parent.parent.parent.parent  # root of spec-kitty repo in worktree
    src_path = str(repo_root / "src")
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_path}:{existing_pythonpath}" if existing_pythonpath else src_path
    # Test-local env for the CHILD process only — never mutates the real os.environ.
    env["FORCE_COLOR"] = "3"  # pin the worst case: harnesses that force color on.
    env["NO_COLOR"] = "1"  # NO_COLOR must win; Rich's Console honors it at construction.

    manifest_path = _synthesis_manifest_guard
    manifest_before = manifest_path.read_bytes() if manifest_path.exists() else None

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

    # Auth-env guard: `charter synthesize` performs a connected-teamspace auth check.
    # In a logged-out environment (e.g. CI without credentials) the child emits a
    # `logged_out_on_connected_teamspace` banner and exits non-zero before doing real
    # work — that is an environment condition, not a product regression, so skip rather
    # than red the suite. Detection mirrors the canonical banner check used elsewhere
    # (e.g. tests/specify_cli/invocation/cli/test_profiles.py).
    if "logged_out_on_connected_teamspace" in result.stderr:
        pytest.skip(
            "charter synthesize requires connected-teamspace auth; skipping in a "
            "logged-out environment (e.g. CI without credentials)."
        )

    # Structural guard (#2672 mode b): the real repo manifest must never be mutated by
    # this --dry-run-evidence invocation. Checked eagerly here (in addition to the
    # fixture's unconditional restore) so a regression fails LOUDLY with a clear message
    # rather than silently self-healing via teardown.
    manifest_after = manifest_path.read_bytes() if manifest_path.exists() else None
    assert manifest_after == manifest_before, (
        "charter synthesize --dry-run-evidence must never mutate the real repo manifest "
        f"at {manifest_path}"
    )

    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    # ANSI-insensitive (#2672 mode a): strip SGR escapes before every substring match so
    # the assertions hold whether or not the child emitted color.
    stdout_plain = _ANSI_SGR_RE.sub("", result.stdout)
    assert "Evidence dry-run summary" in stdout_plain
    assert "Code signals:" in stdout_plain
    # spec-kitty has both pyproject.toml (Python) and package.json (JavaScript tooling),
    # so either language is a valid detection outcome — but "unknown" is not acceptable.
    assert "lang=python" in stdout_plain or "lang=javascript" in stdout_plain, (
        f"Expected lang=python or lang=javascript in output, got:\n{result.stdout}"
    )
