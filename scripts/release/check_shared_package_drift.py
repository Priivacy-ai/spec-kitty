#!/usr/bin/env python3
"""Validate contract-bearing package pins stay aligned across the release stack."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from packaging.requirements import Requirement

PACKAGES = (
    "spec-kitty-events",
    "spec-kitty-runtime",
    "spec-kitty-tracker",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument("--saas-pyproject")
    parser.add_argument("--runtime-pyproject")
    return parser.parse_args()


def load_toml(path: str | None) -> Dict[str, object] | None:
    if path is None:
        return None
    source = Path(path)
    if not source.exists():
        raise SystemExit(f"TOML file not found: {source}")
    return tomllib.loads(source.read_text(encoding="utf-8"))


def parse_requirement(raw: str) -> Requirement:
    try:
        return Requirement(raw)
    except Exception as exc:  # pragma: no cover - error path exercised via CLI
        raise SystemExit(f"Unable to parse dependency requirement: {raw}") from exc


def exact_pin(raw: str) -> str | None:
    req = parse_requirement(raw)
    if req.url:
        return None
    specs = list(req.specifier)
    if len(specs) != 1:
        return None
    spec = specs[0]
    if spec.operator != "==" or spec.version.endswith(".*"):
        return None
    return spec.version


def extract_dependencies(pyproject: Dict[str, object]) -> List[str]:
    project = pyproject.get("project")
    if not isinstance(project, dict):
        raise SystemExit("Invalid pyproject.toml: missing [project] table")
    deps = project.get("dependencies")
    if not isinstance(deps, list):
        raise SystemExit("Invalid pyproject.toml: [project].dependencies must be a list")
    return [str(dep) for dep in deps]


def extract_pins(
    dependencies: Iterable[str], *, packages: Iterable[str]
) -> Dict[str, str]:
    pins: Dict[str, str] = {}
    issues: List[str] = []

    for raw in dependencies:
        req = parse_requirement(raw)
        name = req.name.lower()
        if name not in {package.lower() for package in packages}:
            continue
        if req.url:
            issues.append(f"{req.name}: direct references are forbidden ({raw})")
            continue
        pinned = exact_pin(raw)
        if pinned is None:
            issues.append(f"{req.name}: dependency must be exact-pinned with == ({raw})")
            continue
        if req.name in pins:
            issues.append(f"{req.name}: duplicate dependency entries found")
            continue
        pins[req.name] = pinned

    expected = set(packages)
    missing = sorted(expected - set(pins))
    for package in missing:
        issues.append(f"{package}: missing exact dependency pin")

    if issues:
        raise SystemExit("\n".join(issues))

    return pins


def extract_overrides(pyproject: Dict[str, object]) -> List[str]:
    tool = pyproject.get("tool")
    if not isinstance(tool, dict):
        return []
    uv = tool.get("uv")
    if not isinstance(uv, dict):
        return []
    overrides = uv.get("override-dependencies", [])
    if not isinstance(overrides, list):
        raise SystemExit("Invalid pyproject.toml: [tool.uv].override-dependencies must be a list")
    return [str(entry) for entry in overrides]


def collect_override_issues(overrides: Iterable[str]) -> List[str]:
    issues: List[str] = []
    for entry in overrides:
        req = parse_requirement(entry)
        if req.name.startswith("spec-kitty-"):
            issues.append(
                f"Emergency override still present for {req.name}: {entry}. "
                "Release pins must align without tool.uv override-dependencies."
            )
    return issues


def main() -> int:
    args = parse_args()
    cli_pyproject = load_toml(args.pyproject)
    assert cli_pyproject is not None
    cli_pins = extract_pins(extract_dependencies(cli_pyproject), packages=PACKAGES)

    issues = collect_override_issues(extract_overrides(cli_pyproject))
    summary: List[str] = [
        f"cli spec-kitty-events: {cli_pins['spec-kitty-events']}",
        f"cli spec-kitty-runtime: {cli_pins['spec-kitty-runtime']}",
        f"cli spec-kitty-tracker: {cli_pins['spec-kitty-tracker']}",
    ]

    saas_pyproject = load_toml(args.saas_pyproject)
    if saas_pyproject is not None:
        saas_pins = extract_pins(
            extract_dependencies(saas_pyproject),
            packages=("spec-kitty-events", "spec-kitty-tracker"),
        )
        summary.append(
            f"saas spec-kitty-events: {saas_pins['spec-kitty-events']}"
        )
        summary.append(
            f"saas spec-kitty-tracker: {saas_pins['spec-kitty-tracker']}"
        )
        if saas_pins["spec-kitty-events"] != cli_pins["spec-kitty-events"]:
            issues.append(
                "spec-kitty-events pin mismatch between CLI and SaaS: "
                f"{cli_pins['spec-kitty-events']} vs {saas_pins['spec-kitty-events']}"
            )
        if saas_pins["spec-kitty-tracker"] != cli_pins["spec-kitty-tracker"]:
            issues.append(
                "spec-kitty-tracker pin mismatch between CLI and SaaS: "
                f"{cli_pins['spec-kitty-tracker']} vs {saas_pins['spec-kitty-tracker']}"
            )

    runtime_pyproject = load_toml(args.runtime_pyproject)
    if runtime_pyproject is not None:
        runtime_pins = extract_pins(
            extract_dependencies(runtime_pyproject),
            packages=("spec-kitty-events",),
        )
        summary.append(
            f"runtime spec-kitty-events: {runtime_pins['spec-kitty-events']}"
        )
        if runtime_pins["spec-kitty-events"] != cli_pins["spec-kitty-events"]:
            issues.append(
                "spec-kitty-events pin mismatch between CLI and runtime: "
                f"{cli_pins['spec-kitty-events']} vs {runtime_pins['spec-kitty-events']}"
            )

    print("Shared Package Drift Summary")
    print("----------------------------")
    for line in summary:
        print(f"- {line}")

    if issues:
        print("\nShared package drift violations:")
        for idx, issue in enumerate(issues, start=1):
            print(f"  {idx}. {issue}")
        return 1

    print("\nShared package drift check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
