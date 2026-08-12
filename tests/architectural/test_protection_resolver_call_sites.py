"""Keep protected-branch decisions behind their accepted authority seam."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALLOWED_CALLERS = frozenset(
    {
        "src/specify_cli/git/protection_policy.py",
        "src/specify_cli/git/commit_helpers.py",
    }
)


def _bare_call_violations(root: Path) -> tuple[int, dict[str, list[int]]]:
    corpus = sorted((root / "src").rglob("*.py"))
    violations: dict[str, list[int]] = {}
    for path in corpus:
        relative = path.relative_to(root).as_posix()
        if relative in _ALLOWED_CALLERS:
            continue
        lines = [
            node.lineno
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "protected_branches"
        ]
        if lines:
            violations[relative] = lines
    return len(corpus), violations


def test_protected_branch_resolution_has_one_live_authority(
    tmp_path: Path,
) -> None:
    live_corpus, live_violations = _bare_call_violations(_REPO_ROOT)
    assert live_corpus > 0
    assert live_violations == {}

    bad = tmp_path / "src" / "new_bypass.py"
    good = tmp_path / "src" / "uses_resolved_policy.py"
    delegate = tmp_path / "src" / "specify_cli" / "git" / "commit_helpers.py"
    for path in (bad, good, delegate):
        path.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("protected_branches(repo)\n", encoding="utf-8")
    good.write_text("policy.protected_branches\n", encoding="utf-8")
    delegate.write_text("protected_branches(repo)\n", encoding="utf-8")

    control_corpus, planted_violations = _bare_call_violations(tmp_path)
    assert control_corpus == 3
    assert planted_violations == {"src/new_bypass.py": [1]}
