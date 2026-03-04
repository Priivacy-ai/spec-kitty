#!/usr/bin/env python3
"""Validate pyproject spec-kitty pins against the compatibility matrix."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from packaging.requirements import Requirement


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument(
        "--matrix", default="docs/releases/dependency-compatibility-matrix.toml"
    )
    return parser.parse_args()


def load_toml(path: Path) -> Dict[str, object]:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def normalize_dep_value(raw: str) -> str:
    req = Requirement(raw)
    if req.url:
        return f"url:{req.url}"
    specs = list(req.specifier)
    if len(specs) == 1 and specs[0].operator == "==" and not specs[0].version.endswith(".*"):
        return specs[0].version
    return raw.strip()


def project_spec_kitty_deps(pyproject_data: Dict[str, object]) -> Dict[str, str]:
    project = pyproject_data.get("project")
    if not isinstance(project, dict):
        raise SystemExit("Invalid pyproject.toml: missing [project]")

    deps = project.get("dependencies")
    if not isinstance(deps, list):
        raise SystemExit("Invalid pyproject.toml: [project].dependencies must be a list")

    result: Dict[str, str] = {}
    for raw in deps:
        req = Requirement(str(raw))
        if req.name.startswith("spec-kitty-") and req.name != "spec-kitty-cli":
            result[req.name] = normalize_dep_value(str(raw))
    return result


def main() -> int:
    args = parse_args()
    pyproject = load_toml(Path(args.pyproject))
    matrix = load_toml(Path(args.matrix))

    project = pyproject.get("project")
    if not isinstance(project, dict):
        raise SystemExit("Invalid pyproject.toml: missing [project]")

    version = project.get("version")
    if not isinstance(version, str):
        raise SystemExit("Invalid pyproject.toml: missing [project].version")

    cli = matrix.get("cli")
    if not isinstance(cli, dict):
        raise SystemExit("Compatibility matrix missing [cli] table")

    entry = cli.get(version)
    if not isinstance(entry, dict):
        raise SystemExit(
            f"Compatibility matrix missing [cli.\"{version}\"] entry for current version"
        )

    expected_deps = entry.get("dependencies")
    if not isinstance(expected_deps, dict):
        raise SystemExit(
            f"Compatibility matrix entry [cli.\"{version}\"] must include .dependencies table"
        )

    expected_train = entry.get("train")
    if not isinstance(expected_train, dict):
        raise SystemExit(
            f"Compatibility matrix entry [cli.\"{version}\"] must include .train table"
        )

    release_train = matrix.get("release_train")
    order = release_train.get("order") if isinstance(release_train, dict) else None
    if not isinstance(order, list):
        raise SystemExit("Compatibility matrix missing [release_train].order list")

    actual = project_spec_kitty_deps(pyproject)

    issues: List[str] = []

    for lib in order:
        if not isinstance(lib, str):
            issues.append(f"release_train.order contains non-string entry: {lib!r}")
            continue
        if lib == "spec-kitty-cli":
            continue
        value = expected_train.get(lib)
        if not isinstance(value, str) or not value.strip():
            issues.append(
                f"Matrix [cli.\"{version}\".train] missing value for {lib}."
            )

    for package, pinned in actual.items():
        expected_pin = expected_deps.get(package)
        if not isinstance(expected_pin, str):
            issues.append(
                f"Matrix missing expected pin for {package} in [cli.\"{version}\".dependencies]"
            )
            continue
        if pinned != expected_pin:
            issues.append(
                f"Pin mismatch for {package}: pyproject='{pinned}' vs matrix='{expected_pin}'"
            )

        train_pin = expected_train.get(package)
        if isinstance(train_pin, str) and train_pin.strip() and train_pin not in {
            "n/a",
            "na",
            "not-used",
            "not used",
        }:
            if train_pin != pinned:
                issues.append(
                    f"Train mismatch for {package}: dependencies table has '{pinned}' but train has '{train_pin}'"
                )

    print("Dependency Matrix Summary")
    print("-------------------------")
    print(f"- CLI version: {version}")
    for package, pinned in sorted(actual.items()):
        print(f"- dependency {package}: {pinned}")
    for lib in order:
        if isinstance(lib, str) and lib != "spec-kitty-cli":
            print(f"- train {lib}: {expected_train.get(lib, '<missing>')}")

    if issues:
        print("\nMatrix validation failures:")
        for idx, issue in enumerate(issues, start=1):
            print(f"  {idx}. {issue}")
        return 1

    print("\nDependency matrix check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
