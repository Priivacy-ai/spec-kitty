from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path
from textwrap import dedent

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "release"
    / "check_candidate_consumer_compat.py"
)


def write_wheel(dist_dir: Path, *, version: str, requirements: list[str]) -> Path:
    wheel_path = dist_dir / f"spec_kitty_cli-{version}-py3-none-any.whl"
    metadata = dedent(
        f"""
        Metadata-Version: 2.4
        Name: spec-kitty-cli
        Version: {version}
        """
    ).lstrip()
    for requirement in requirements:
        metadata += f"Requires-Dist: {requirement}\n"

    with zipfile.ZipFile(wheel_path, "w") as zf:
        zf.writestr("spec_kitty_cli-0.0.0.dist-info/METADATA", metadata)
    return wheel_path


def write_contract(path: Path) -> None:
    payload = {
        "consumer": "spec-kitty-saas",
        "contract_families": [
            {"package": "spec-kitty-events", "supported_range": ">=3.2.0,<4.0"},
            {"package": "spec-kitty-tracker", "supported_range": ">=0.4.0,<0.5"},
            {"package": "spec-kitty-runtime", "supported_range": "vendored"},
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def run_check(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )


def test_candidate_consumer_compat_passes_for_supported_pins(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    contract = tmp_path / "consumer-compatibility.json"
    write_contract(contract)
    write_wheel(
        dist_dir,
        version="3.2.0a2",
        requirements=[
            "spec-kitty-events==3.2.0",
            "spec-kitty-runtime==0.4.4",
            "spec-kitty-tracker==0.4.2",
        ],
    )

    result = run_check(
        tmp_path,
        "--dist-dir",
        str(dist_dir),
        "--package",
        "spec-kitty-cli",
        "--consumer-contract",
        str(contract),
    )

    assert result.returncode == 0, result.stderr
    assert "Candidate consumer compatibility check passed." in result.stdout


def test_candidate_consumer_compat_fails_for_out_of_range_pin(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    contract = tmp_path / "consumer-compatibility.json"
    write_contract(contract)
    write_wheel(
        dist_dir,
        version="3.2.0a2",
        requirements=[
            "spec-kitty-events==3.2.0",
            "spec-kitty-runtime==0.4.4",
            "spec-kitty-tracker==0.5.0",
        ],
    )

    result = run_check(
        tmp_path,
        "--dist-dir",
        str(dist_dir),
        "--package",
        "spec-kitty-cli",
        "--consumer-contract",
        str(contract),
    )

    assert result.returncode == 1
    assert "outside consumer-supported range" in result.stdout
