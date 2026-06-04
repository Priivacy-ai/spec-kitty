from __future__ import annotations

import importlib.util
import subprocess
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = [pytest.mark.integration]

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "release"
    / "check_exact_install.py"
)


def load_script_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_exact_install", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_wheel(dist_dir: Path, *, package: str, version: str) -> Path:
    dist_dir.mkdir()
    prefix = package.replace("-", "_")
    wheel = dist_dir / f"{prefix}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr(
            f"{prefix}-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.4\nName: {package}\nVersion: {version}\n",
        )
    return wheel


def test_console_script_smoke_runs_after_exact_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_script_module()
    write_wheel(tmp_path / "dist", package="spec-kitty-cli", version="3.1.10")
    calls: list[list[str]] = []

    def fake_run(
        cmd: list[str], *, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        stdout = "3.1.10\n" if "-c" in cmd else ""
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--dist-dir",
            str(tmp_path / "dist"),
            "--package",
            "spec-kitty-cli",
            "--console-script",
            "spec-kitty",
            "--console-arg=--version",
        ],
    )

    assert module.main() == 0

    assert any(call[-3:] == ["install", "--upgrade", "pip"] for call in calls)
    assert any(
        "spec-kitty" in Path(call[0]).name and call[1:] == ["--version"]
        for call in calls
    )


def test_console_script_smoke_failure_fails_release_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_script_module()
    write_wheel(tmp_path / "dist", package="spec-kitty-cli", version="3.1.10")

    def fake_run(
        cmd: list[str], *, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        if "spec-kitty" in Path(cmd[0]).name:
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="",
                stderr="ModuleNotFoundError: No module named 'click'\n",
            )
        stdout = "3.1.10\n" if "-c" in cmd else ""
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--dist-dir",
            str(tmp_path / "dist"),
            "--package",
            "spec-kitty-cli",
            "--console-script",
            "spec-kitty",
            "--console-arg=--version",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert exc.value.code
    assert "console script smoke test" in str(exc.value)
    assert "No module named 'click'" in str(exc.value)


def test_from_index_installs_exact_version_without_local_wheel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_script_module()
    calls: list[list[str]] = []

    def fake_run(
        cmd: list[str], *, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        stdout = "3.1.10\n" if "-c" in cmd else ""
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--package",
            "spec-kitty-cli",
            "--version",
            "3.1.10",
            "--from-index",
            "--index-url",
            "https://pypi.org/simple",
        ],
    )

    assert module.main() == 0

    assert any(
        call[-3:] == [
            "--index-url",
            "https://pypi.org/simple",
            "spec-kitty-cli==3.1.10",
        ]
        for call in calls
    )


def test_from_index_requires_exact_version(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_script_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--package",
            "spec-kitty-cli",
            "--from-index",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert "--version is required when --from-index is used" in str(exc.value)
