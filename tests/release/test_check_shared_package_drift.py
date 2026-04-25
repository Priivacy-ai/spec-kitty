from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "release"
    / "check_shared_package_drift.py"
)


def write_pyproject(path: Path, *, dependencies: list[str], overrides: list[str] | None = None) -> None:
    override_block = ""
    if overrides is not None:
        lines = "\n".join(f'    "{entry}",' for entry in overrides)
        override_block = f"\n[tool.uv]\noverride-dependencies = [\n{lines}\n]\n"

    path.write_text(
        dedent(
            f"""
            [project]
            name = "example"
            version = "1.0.0"
            dependencies = [
            {chr(10).join(f'    "{dep}",' for dep in dependencies)}
            ]
            {override_block}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def write_lockfile(path: Path, *, versions: dict[str, str]) -> None:
    path.write_text(
        "\n".join(
            [
                "version = 1",
                "revision = 3",
                "requires-python = \">=3.11\"",
                "",
                *[
                    f'[[package]]\nname = "{name}"\nversion = "{version}"\nsource = {{ registry = "https://pypi.org/simple" }}\n'
                    for name, version in versions.items()
                ],
            ]
        ),
        encoding="utf-8",
    )


def run_check(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )


def test_shared_package_drift_passes_with_aligned_sources(tmp_path: Path) -> None:
    cli = tmp_path / "pyproject.toml"
    lockfile = tmp_path / "uv.lock"
    saas = tmp_path / "saas.toml"
    runtime = tmp_path / "runtime.toml"

    write_pyproject(
        cli,
        dependencies=[
            "spec-kitty-events>=4.0.0,<5.0.0",
            "spec-kitty-tracker>=0.4,<0.5",
        ],
    )
    write_lockfile(
        lockfile,
        versions={
            "spec-kitty-events": "4.0.0",
            "spec-kitty-tracker": "0.4.2",
        },
    )
    write_pyproject(
        saas,
        dependencies=[
            "spec-kitty-events==4.0.0",
            "spec-kitty-tracker==0.4.2",
        ],
    )
    write_pyproject(runtime, dependencies=["spec-kitty-events==3.3.0"])

    result = run_check(
        tmp_path,
        "--pyproject",
        str(cli),
        "--lockfile",
        str(lockfile),
        "--saas-pyproject",
        str(saas),
        "--runtime-pyproject",
        str(runtime),
    )

    assert result.returncode == 0, result.stderr
    assert "Shared package drift check passed." in result.stdout


def test_shared_package_drift_fails_on_saas_mismatch(tmp_path: Path) -> None:
    cli = tmp_path / "pyproject.toml"
    lockfile = tmp_path / "uv.lock"
    saas = tmp_path / "saas.toml"
    runtime = tmp_path / "runtime.toml"

    write_pyproject(
        cli,
        dependencies=[
            "spec-kitty-events>=4.0.0,<5.0.0",
            "spec-kitty-tracker>=0.4,<0.5",
        ],
    )
    write_lockfile(
        lockfile,
        versions={
            "spec-kitty-events": "4.0.0",
            "spec-kitty-tracker": "0.4.2",
        },
    )
    write_pyproject(
        saas,
        dependencies=[
            "spec-kitty-events==4.0.0",
            "spec-kitty-tracker==0.4.1",
        ],
    )
    write_pyproject(runtime, dependencies=["spec-kitty-events==3.3.0"])

    result = run_check(
        tmp_path,
        "--pyproject",
        str(cli),
        "--lockfile",
        str(lockfile),
        "--saas-pyproject",
        str(saas),
        "--runtime-pyproject",
        str(runtime),
    )

    assert result.returncode == 1
    assert "spec-kitty-tracker pin mismatch between SaaS and CLI uv.lock" in result.stdout


def test_shared_package_drift_fails_when_override_remains(tmp_path: Path) -> None:
    cli = tmp_path / "pyproject.toml"
    lockfile = tmp_path / "uv.lock"
    runtime = tmp_path / "runtime.toml"

    write_pyproject(
        cli,
        dependencies=[
            "spec-kitty-events>=4.0.0,<5.0.0",
            "spec-kitty-tracker>=0.4,<0.5",
        ],
        overrides=["spec-kitty-events==3.2.0"],
    )
    write_lockfile(
        lockfile,
        versions={
            "spec-kitty-events": "4.0.0",
            "spec-kitty-tracker": "0.4.2",
        },
    )
    write_pyproject(runtime, dependencies=["spec-kitty-events==3.2.0"])

    result = run_check(
        tmp_path,
        "--pyproject",
        str(cli),
        "--lockfile",
        str(lockfile),
        "--runtime-pyproject",
        str(runtime),
    )

    assert result.returncode == 1
    assert "Emergency override still present" in result.stdout


def test_shared_package_drift_fails_when_runtime_dependency_remains(tmp_path: Path) -> None:
    cli = tmp_path / "pyproject.toml"
    lockfile = tmp_path / "uv.lock"

    write_pyproject(
        cli,
        dependencies=[
            "spec-kitty-events>=4.0.0,<5.0.0",
            "spec-kitty-runtime==0.4.5",
            "spec-kitty-tracker>=0.4,<0.5",
        ],
    )
    write_lockfile(
        lockfile,
        versions={
            "spec-kitty-events": "4.0.0",
            "spec-kitty-tracker": "0.4.2",
        },
    )

    result = run_check(
        tmp_path,
        "--pyproject",
        str(cli),
        "--lockfile",
        str(lockfile),
    )

    assert result.returncode == 1
    assert "Retired runtime package must not be a CLI dependency" in result.stdout


def test_shared_package_drift_fails_when_cli_constraint_is_unbounded(tmp_path: Path) -> None:
    cli = tmp_path / "pyproject.toml"
    lockfile = tmp_path / "uv.lock"

    write_pyproject(
        cli,
        dependencies=[
            "spec-kitty-events>=4.0.0",
            "spec-kitty-tracker>=0.4,<0.5",
        ],
    )
    write_lockfile(
        lockfile,
        versions={
            "spec-kitty-events": "4.0.0",
            "spec-kitty-tracker": "0.4.2",
        },
    )

    result = run_check(
        tmp_path,
        "--pyproject",
        str(cli),
        "--lockfile",
        str(lockfile),
    )

    assert result.returncode == 1
    assert "spec-kitty-events: dependency must use a bounded compatible range" in result.stderr
