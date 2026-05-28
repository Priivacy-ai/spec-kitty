#!/usr/bin/env python3
"""Build-artifact install smoke test using plain pip in a clean virtualenv."""

from __future__ import annotations

import argparse
import email
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from collections.abc import Sequence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--package", required=True)
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Interpreter used to create the temporary virtualenv.",
    )
    parser.add_argument(
        "--console-script",
        help="Installed console script to smoke-test after wheel installation.",
    )
    parser.add_argument(
        "--console-arg",
        action="append",
        default=None,
        help=(
            "Argument passed to --console-script. May be repeated. Defaults to "
            "--version when --console-script is set."
        ),
    )
    return parser.parse_args()


def package_prefix(package_name: str) -> str:
    return package_name.replace("-", "_")


def locate_wheel(dist_dir: Path, package_name: str) -> Path:
    wheels = sorted(
        wheel
        for wheel in dist_dir.glob("*.whl")
        if wheel.name.startswith(package_prefix(package_name))
    )
    if not wheels:
        raise SystemExit(
            f"No wheel found for {package_name!r} in distribution directory {dist_dir}"
        )
    if len(wheels) > 1:
        raise SystemExit(
            f"Expected exactly one wheel for {package_name!r}, found: "
            + ", ".join(wheel.name for wheel in wheels)
        )
    return wheels[0]


def read_wheel_metadata(wheel_path: Path) -> email.message.Message:
    with zipfile.ZipFile(wheel_path) as zf:
        metadata_files = [
            name for name in zf.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if not metadata_files:
            raise SystemExit(f"No METADATA file found in wheel {wheel_path}")
        payload = zf.read(metadata_files[0]).decode("utf-8", errors="replace")
    return email.message_from_string(payload)


def venv_bin_dir(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts" if os.name == "nt" else "bin")


def console_script_path(venv_dir: Path, script_name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return venv_bin_dir(venv_dir) / f"{script_name}{suffix}"


def run(
    cmd: Sequence[str], *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        text=True,
        capture_output=True,
        env=env,
    )


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode == 0:
        return
    raise SystemExit(
        f"{label} failed with exit code {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def main() -> int:
    args = parse_args()
    dist_dir = Path(args.dist_dir)
    if not dist_dir.exists():
        raise SystemExit(f"Distribution directory not found: {dist_dir}")

    wheel_path = locate_wheel(dist_dir, args.package)
    metadata = read_wheel_metadata(wheel_path)
    expected_version = metadata.get("Version")
    if not expected_version:
        raise SystemExit(f"Wheel metadata missing Version field: {wheel_path}")

    requires_dist = metadata.get_all("Requires-Dist", [])

    temp_dir = Path(tempfile.mkdtemp(prefix="exact-install-"))
    try:
        venv_dir = temp_dir / "venv"
        create_venv = run([args.python, "-m", "venv", str(venv_dir)])
        require_success(create_venv, "virtualenv creation")

        python_bin = venv_bin_dir(venv_dir) / (
            "python.exe" if os.name == "nt" else "python"
        )
        pip_cmd = [str(python_bin), "-m", "pip"]

        upgrade_pip = run([*pip_cmd, "install", "--upgrade", "pip"])
        require_success(upgrade_pip, "pip upgrade")

        install = run([*pip_cmd, "install", "--no-cache-dir", str(wheel_path)])
        require_success(install, "wheel install")

        verify = run(
            [
                str(python_bin),
                "-c",
                (
                    "from importlib.metadata import version; "
                    f"print(version({args.package!r}))"
                ),
            ]
        )
        require_success(verify, "installed version verification")

        installed_version = verify.stdout.strip()
        if installed_version != expected_version:
            raise SystemExit(
                f"Installed version mismatch for {args.package}: "
                f"expected {expected_version}, got {installed_version}"
            )

        console_args = args.console_arg
        if args.console_script:
            if console_args is None:
                console_args = ["--version"]
            smoke_command = [
                str(console_script_path(venv_dir, args.console_script)),
                *console_args,
            ]
            smoke = run(smoke_command)
            require_success(
                smoke,
                "console script smoke test (" + " ".join(smoke_command) + ")",
            )

        print("Exact Install Summary")
        print("---------------------")
        print(f"- wheel: {wheel_path.name}")
        print(f"- package: {args.package}")
        print(f"- version: {installed_version}")
        if args.console_script:
            print(
                "- console-smoke: "
                + " ".join([args.console_script, *(console_args or [])])
            )
        if requires_dist:
            print("- requires-dist:")
            for requirement in requires_dist:
                print(f"  - {requirement}")

        print("\nExact install smoke test passed.")
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
