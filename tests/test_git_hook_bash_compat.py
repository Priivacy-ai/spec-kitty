"""Regression tests for bash hook portability (macOS Bash 3.2)."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pytest


def _hook_roots(repo_root: Path) -> list[Path]:
    """Return all hook template directories that exist in this branch."""
    candidates = [
        repo_root / "src" / "doctrine" / "templates" / "git-hooks",
        repo_root / "src" / "specify_cli" / "templates" / "git-hooks",
    ]
    return [p for p in candidates if p.exists()]


def test_hook_templates_avoid_bash4_only_mapfile_readarray() -> None:
    """Hook templates must avoid builtins unavailable in macOS Bash 3.2."""
    repo_root = Path(__file__).parent.parent
    hook_roots = _hook_roots(repo_root)
    if not hook_roots:
        pytest.skip("No hook template directories found")

    pattern = re.compile(r"^\s*(?!#).*\b(mapfile|readarray)\b", re.MULTILINE)
    offenders: list[str] = []

    for hook_root in hook_roots:
        for hook_file in hook_root.iterdir():
            if not hook_file.is_file():
                continue
            content = hook_file.read_text(encoding="utf-8")
            if pattern.search(content):
                offenders.append(str(hook_file.relative_to(repo_root)))

    assert not offenders, (
        "Bash 4+ builtins detected in hook templates. "
        f"Use Bash 3.2-compatible loops instead: {offenders}"
    )


def test_markdown_hook_runs_with_staged_files_using_fake_npx() -> None:
    """Smoke test markdown hook execution without local Node setup."""
    repo_root = Path(__file__).parent.parent
    hook_roots = _hook_roots(repo_root)
    markdown_hooks = [p / "pre-commit-markdown-check" for p in hook_roots if (p / "pre-commit-markdown-check").exists()]
    if not markdown_hooks:
        pytest.skip("No pre-commit-markdown-check hook found in this branch")

    bash_path = shutil.which("bash")
    if bash_path is None:
        pytest.skip("bash is not available in this environment")

    hook_script = markdown_hooks[0]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        repo = tmp_path / "repo"
        repo.mkdir(parents=True)

        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True, text=True)

        (repo / ".markdownlint-cli2.jsonc").write_text("{}", encoding="utf-8")
        (repo / "README.md").write_text("# Title\n", encoding="utf-8")
        subprocess.run(["git", "add", ".markdownlint-cli2.jsonc", "README.md"], cwd=repo, check=True, capture_output=True, text=True)

        fake_bin = tmp_path / "bin"
        fake_bin.mkdir(parents=True)
        fake_npx = fake_bin / "npx"
        fake_npx.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_npx.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
        env.pop("SPEC_KITTY_TEST_MODE", None)

        result = subprocess.run(
            [bash_path, str(hook_script)],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            "Markdown hook should complete successfully for staged markdown files "
            f"with available npx stub. stdout={result.stdout!r} stderr={result.stderr!r}"
        )
