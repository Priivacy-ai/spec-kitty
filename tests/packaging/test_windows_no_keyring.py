"""Packaging assertion: keyring must not be declared as a project dependency."""

from __future__ import annotations

from pathlib import Path
import tomllib


def test_keyring_not_declared_in_project_dependencies():
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    dependencies = data["project"]["dependencies"]
    assert all(not dep.startswith("keyring") for dep in dependencies), (
        "CLI auth should use only the encrypted file store under ~/.spec-kitty/auth/, so pyproject.toml must not declare keyring."
    )
