#!/usr/bin/env python3
"""Validate built distribution metadata for explicit MIT licensing."""

from __future__ import annotations

import argparse
import email
import tarfile
import zipfile
from pathlib import Path
from typing import List


MIT_CLASSIFIER = "License :: OSI Approved :: MIT License"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--package", default="spec-kitty-cli")
    return parser.parse_args()


def read_wheel_metadata(wheel_path: Path) -> email.message.Message:
    with zipfile.ZipFile(wheel_path) as zf:
        metadata_names = [
            name for name in zf.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if not metadata_names:
            raise SystemExit(f"No METADATA file found in wheel: {wheel_path}")
        content = zf.read(metadata_names[0]).decode("utf-8", errors="replace")
    return email.message_from_string(content)


def assert_mit_metadata(metadata: email.message.Message, label: str) -> List[str]:
    issues: List[str] = []
    classifiers = metadata.get_all("Classifier", [])
    license_value = metadata.get("License", "")
    license_expr = metadata.get("License-Expression", "")
    license_files = metadata.get_all("License-File", [])

    has_mit_classifier = MIT_CLASSIFIER in classifiers
    has_mit_text = "mit" in (license_value or "").lower() or "mit" in (
        license_expr or ""
    ).lower()

    if not (has_mit_classifier or has_mit_text):
        issues.append(f"{label}: METADATA must declare MIT via classifier/license fields")

    if "LICENSE" not in license_files:
        issues.append(f"{label}: METADATA must include 'License-File: LICENSE'")

    return issues


def assert_sdist_contains_license(sdist_path: Path) -> List[str]:
    issues: List[str] = []
    with tarfile.open(sdist_path, "r:gz") as tf:
        names = tf.getnames()
    if not any(name.endswith("/LICENSE") or name == "LICENSE" for name in names):
        issues.append(f"{sdist_path.name}: source distribution must include LICENSE file")
    return issues


def main() -> int:
    args = parse_args()
    dist_dir = Path(args.dist_dir)
    if not dist_dir.exists():
        raise SystemExit(f"Distribution directory not found: {dist_dir}")

    package_prefix = args.package.replace("-", "_")
    wheels = sorted(
        wheel
        for wheel in dist_dir.glob("*.whl")
        if wheel.name.startswith(package_prefix)
    )
    sdists = sorted(
        sdist
        for sdist in dist_dir.glob("*.tar.gz")
        if sdist.name.startswith(package_prefix)
    )

    if not wheels:
        raise SystemExit("No wheel files found in dist directory")
    if not sdists:
        raise SystemExit("No source distributions (.tar.gz) found in dist directory")

    issues: List[str] = []

    for wheel in wheels:
        metadata = read_wheel_metadata(wheel)
        issues.extend(assert_mit_metadata(metadata, wheel.name))

    for sdist in sdists:
        issues.extend(assert_sdist_contains_license(sdist))

    print("Distribution Metadata Summary")
    print("-----------------------------")
    for wheel in wheels:
        print(f"- wheel: {wheel.name}")
    for sdist in sdists:
        print(f"- sdist: {sdist.name}")

    if issues:
        print("\nMetadata validation failures:")
        for idx, issue in enumerate(issues, start=1):
            print(f"  {idx}. {issue}")
        return 1

    print("\nDistribution metadata check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
