"""Enforces DIRECTIVE_API_DEPENDENCY_DIRECTION.

Doctrine: src/doctrine/directives/shipped/api-dependency-direction.directive.yaml

No transport-side module (FastAPI router, dashboard CLI command body) may
import from specify_cli.dashboard.scanner or specify_cli.scanner directly.
The MissionRegistry in src/dashboard/services/registry.py is the single
sanctioned reader.

Owned by WP05 of mission mission-registry-and-api-boundary-doctrine-01KQPDBB.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_PATHS: tuple[Path, ...] = (
    REPO_ROOT / "src" / "dashboard" / "api" / "routers",
    REPO_ROOT / "src" / "specify_cli" / "cli" / "commands" / "dashboard.py",
)

FORBIDDEN_PREFIXES: tuple[str, ...] = (
    "specify_cli.dashboard.scanner",
    "specify_cli.scanner",
)


def _scan_for_forbidden_imports(paths: list[Path]) -> list[str]:
    """Walk each path; return list of (file:line: import_name) violation strings."""
    violations: list[str] = []
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            module_name = None
            if isinstance(node, ast.ImportFrom) and node.module:
                module_name = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(p) for p in FORBIDDEN_PREFIXES):
                        try:
                            display_path = path.relative_to(REPO_ROOT)
                        except ValueError:
                            display_path = path
                        violations.append(
                            f"{display_path}:{node.lineno}: import '{alias.name}'"
                        )
                continue
            if module_name and any(module_name.startswith(p) for p in FORBIDDEN_PREFIXES):
                try:
                    display_path = path.relative_to(REPO_ROOT)
                except ValueError:
                    display_path = path
                violations.append(
                    f"{display_path}:{node.lineno}: from '{module_name}' import ..."
                )
    return violations


def _collect_files(roots: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(root.rglob("*.py"))
    return files


def test_no_transport_module_imports_scanner_directly() -> None:
    """The main scan: every transport-side file is clean."""
    files = _collect_files(SCAN_PATHS)
    violations = _scan_for_forbidden_imports(files)
    assert violations == [], (
        "Transport-side modules MUST consume mission/WP data via the registry, "
        "not by importing the scanner directly. See "
        "src/doctrine/directives/shipped/api-dependency-direction.directive.yaml.\n\n"
        "Violations:\n  " + "\n  ".join(violations) + "\n\n"
        "Fix: replace `from specify_cli.dashboard.scanner import ...` with "
        "`from dashboard.services.registry import MissionRegistry`."
    )


def test_meta_scanner_detects_synthetic_violator(tmp_path: Path) -> None:
    """Positive meta-test: synthetic forbidden import MUST be detected."""
    fake_router = tmp_path / "synthetic_router.py"
    fake_router.write_text(
        "from specify_cli.dashboard.scanner import scan_all_features\n"
        "router = ...\n",
        encoding="utf-8",
    )
    violations = _scan_for_forbidden_imports([fake_router])
    assert len(violations) == 1
    assert "specify_cli.dashboard.scanner" in violations[0]


def test_meta_scanner_accepts_synthetic_clean_module(tmp_path: Path) -> None:
    """Negative meta-test: synthetic clean module MUST NOT be flagged."""
    clean_router = tmp_path / "synthetic_router.py"
    clean_router.write_text(
        "from dashboard.services.registry import MissionRegistry\n"
        "router = ...\n",
        encoding="utf-8",
    )
    violations = _scan_for_forbidden_imports([clean_router])
    assert violations == []
