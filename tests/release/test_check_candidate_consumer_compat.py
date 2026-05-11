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


def write_contract(
    path: Path,
    *,
    events_range: str = ">=3.2.0,<4.0",
    tracker_range: str = ">=0.4.0,<0.5",
) -> None:
    payload = {
        "consumer": "spec-kitty-saas",
        "contract_families": [
            {"package": "spec-kitty-events", "supported_range": events_range},
            {"package": "spec-kitty-tracker", "supported_range": tracker_range},
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


def test_candidate_consumer_compat_passes_when_candidate_range_contains_saas_pin(
    tmp_path: Path,
) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    contract = tmp_path / "consumer-compatibility.json"
    write_contract(contract, events_range="==5.0.0", tracker_range="==0.4.3")
    write_wheel(
        dist_dir,
        version="3.2.0rc5",
        requirements=[
            "spec-kitty-events>=5.0.0,<6.0.0",
            "spec-kitty-runtime==0.4.4",
            "spec-kitty-tracker>=0.4,<0.5",
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
    assert "spec-kitty-events: candidate allows SaaS-supported 5.0.0" in result.stdout
    assert "spec-kitty-tracker: candidate allows SaaS-supported 0.4.3" in result.stdout


def test_candidate_consumer_compat_fails_when_candidate_range_excludes_saas_pin(
    tmp_path: Path,
) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    contract = tmp_path / "consumer-compatibility.json"
    write_contract(contract, events_range="==5.0.0", tracker_range="==0.4.3")
    write_wheel(
        dist_dir,
        version="3.2.0rc5",
        requirements=[
            "spec-kitty-events>=4.0.0,<5.0.0",
            "spec-kitty-runtime==0.4.4",
            "spec-kitty-tracker>=0.5,<0.6",
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
    assert (
        "spec-kitty-events: SaaS supports 5.0.0, but candidate metadata "
        "spec-kitty-events<5.0.0,>=4.0.0 does not allow it"
    ) in result.stdout
    assert (
        "spec-kitty-tracker: SaaS supports 0.4.3, but candidate metadata "
        "spec-kitty-tracker<0.6,>=0.5 does not allow it"
    ) in result.stdout


def test_candidate_consumer_compat_fails_when_both_sides_use_broad_ranges(
    tmp_path: Path,
) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    contract = tmp_path / "consumer-compatibility.json"
    write_contract(contract, events_range=">=5.0.0,<6.0.0", tracker_range="==0.4.3")
    write_wheel(
        dist_dir,
        version="3.2.0rc5",
        requirements=[
            "spec-kitty-events>=5.0.0,<6.0.0",
            "spec-kitty-runtime==0.4.4",
            "spec-kitty-tracker>=0.4,<0.5",
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
    assert "compatibility cannot be proven" in result.stdout
