#!/usr/bin/env python3
"""Validate candidate wheel metadata against a downstream consumer contract."""

from __future__ import annotations

import argparse
import email
import json
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--package", required=True)
    parser.add_argument("--consumer-contract", required=True)
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


def load_contract(path: Path) -> Dict[str, object]:
    if not path.exists():
        raise SystemExit(f"Consumer contract not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("Consumer contract must be a JSON object")
    return data


def parse_requirement(raw: str) -> Requirement:
    try:
        return Requirement(raw)
    except Exception as exc:  # pragma: no cover - error path exercised via CLI
        raise SystemExit(f"Unable to parse requirement metadata: {raw}") from exc


def exact_pin(requirement: Requirement) -> str | None:
    if requirement.url:
        return None
    specs = list(requirement.specifier)
    if len(specs) != 1:
        return None
    spec = specs[0]
    if spec.operator != "==" or spec.version.endswith(".*"):
        return None
    return spec.version


def extract_requirements(requires_dist: Iterable[str]) -> Dict[str, Requirement]:
    requirements: Dict[str, Requirement] = {}
    for raw in requires_dist:
        req = parse_requirement(raw)
        if req.name.startswith("spec-kitty-"):
            requirements[req.name] = req
    return requirements


def main() -> int:
    args = parse_args()
    dist_dir = Path(args.dist_dir)
    if not dist_dir.exists():
        raise SystemExit(f"Distribution directory not found: {dist_dir}")

    wheel_path = locate_wheel(dist_dir, args.package)
    metadata = read_wheel_metadata(wheel_path)
    contract = load_contract(Path(args.consumer_contract))

    requires_dist = metadata.get_all("Requires-Dist", [])
    requirements = extract_requirements(requires_dist)

    families = contract.get("contract_families")
    if not isinstance(families, list):
        raise SystemExit("Consumer contract missing contract_families list")

    summary: List[str] = [
        f"candidate: {metadata.get('Name', args.package)}=={metadata.get('Version', 'unknown')}",
        f"consumer: {contract.get('consumer', 'unknown')}",
    ]
    issues: List[str] = []

    for entry in families:
        if not isinstance(entry, dict):
            raise SystemExit("Each contract family entry must be an object")
        package = entry.get("package")
        supported_range = entry.get("supported_range")
        if not isinstance(package, str) or not isinstance(supported_range, str):
            raise SystemExit("Contract family entries must include package and supported_range")

        requirement = requirements.get(package)
        if supported_range == "vendored":
            summary.append(f"{package}: vendored by consumer, skipped")
            continue

        if requirement is None:
            issues.append(f"Candidate wheel is missing required dependency metadata for {package}")
            continue

        pinned = exact_pin(requirement)
        if pinned is None:
            issues.append(
                f"{package}: candidate must carry an exact == pin, found {requirement}"
            )
            continue

        specifier = SpecifierSet(supported_range)
        if Version(pinned) not in specifier:
            issues.append(
                f"{package}: pinned version {pinned} is outside consumer-supported range {supported_range}"
            )
            continue

        summary.append(f"{package}: {pinned} satisfies {supported_range}")

    print("Candidate Consumer Compatibility Summary")
    print("----------------------------------------")
    for line in summary:
        print(f"- {line}")

    if issues:
        print("\nConsumer compatibility violations:")
        for idx, issue in enumerate(issues, start=1):
            print(f"  {idx}. {issue}")
        return 1

    print("\nCandidate consumer compatibility check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
