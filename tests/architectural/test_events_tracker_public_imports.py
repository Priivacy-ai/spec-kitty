"""Keep CLI consumers on the public events/tracker package boundary."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src" / "specify_cli"
_PACKAGES = ("spec_kitty_events", "spec_kitty_tracker")


def _private_imports(paths: list[Path]) -> list[str]:
    offenders: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
                lineno = node.lineno
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
                lineno = node.lineno
            else:
                continue
            for module in modules:
                if any(
                    module == f"{package}._internal"
                    or module.startswith(f"{package}._internal.")
                    for package in _PACKAGES
                ):
                    offenders.append(f"{path}:{lineno} -> {module}")
    return offenders


def test_cli_never_imports_private_events_or_tracker_modules(tmp_path: Path) -> None:
    """Scan the live CLI and prove the same oracle rejects a planted bypass."""
    corpus = sorted(_SRC_ROOT.rglob("*.py"))
    assert corpus
    assert _private_imports(corpus) == []

    control = tmp_path / "control.py"
    control.write_text("from spec_kitty_events import Event\n", encoding="utf-8")
    assert _private_imports([control]) == []

    fault = tmp_path / "fault.py"
    fault.write_text(
        "from spec_kitty_tracker._internal.store import TrackerStore\n",
        encoding="utf-8",
    )
    assert _private_imports([fault]) == [f"{fault}:1 -> spec_kitty_tracker._internal.store"]
