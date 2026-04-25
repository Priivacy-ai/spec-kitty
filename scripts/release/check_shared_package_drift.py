#!/usr/bin/env python3
"""Validate contract-bearing shared package constraints across release metadata."""

from __future__ import annotations

import argparse
from pathlib import Path
from collections.abc import Iterable

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from packaging.requirements import Requirement
from packaging.version import Version

PACKAGES = (
    "spec-kitty-events",
    "spec-kitty-tracker",
)
RETIRED_PACKAGES = ("spec-kitty-runtime",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument("--lockfile", default="uv.lock")
    parser.add_argument("--saas-pyproject")
    parser.add_argument("--runtime-pyproject")
    return parser.parse_args()


def load_toml(path: str | None) -> dict[str, object] | None:
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


def requirement_contains_version(raw: str, version: str) -> bool:
    req = parse_requirement(raw)
    if req.url:
        return False
    if not req.specifier:
        return True
    return req.specifier.contains(Version(version), prereleases=True)


def has_compatible_range(raw: str) -> bool:
    req = parse_requirement(raw)
    specs = list(req.specifier)
    has_lower_bound = any(spec.operator == ">=" for spec in specs)
    has_upper_bound = any(spec.operator == "<" for spec in specs)
    has_exact_pin = any(spec.operator == "==" for spec in specs)
    return has_lower_bound and has_upper_bound and not has_exact_pin


def extract_dependencies(pyproject: dict[str, object]) -> list[str]:
    project = pyproject.get("project")
    if not isinstance(project, dict):
        raise SystemExit("Invalid pyproject.toml: missing [project] table")
    deps = project.get("dependencies")
    if not isinstance(deps, list):
        raise SystemExit("Invalid pyproject.toml: [project].dependencies must be a list")
    return [str(dep) for dep in deps]


def extract_constraints(
    dependencies: Iterable[str], *, packages: Iterable[str], exact_required: bool = False
) -> dict[str, str]:
    constraints: dict[str, str] = {}
    issues: list[str] = []
    canonical = {package.lower(): package for package in packages}

    for raw in dependencies:
        req = parse_requirement(raw)
        name = req.name.lower()
        if name not in canonical:
            continue
        if req.url:
            issues.append(f"{req.name}: direct references are forbidden ({raw})")
            continue
        package = canonical[name]
        pinned = exact_pin(raw)
        if exact_required and pinned is None:
            issues.append(f"{req.name}: dependency must be exact-pinned with == ({raw})")
            continue
        if not exact_required and pinned is not None:
            issues.append(
                f"{req.name}: dependency must use a compatible range, not an exact pin ({raw})"
            )
            continue
        if not exact_required and not has_compatible_range(raw):
            issues.append(
                f"{req.name}: dependency must use a bounded compatible range ({raw})"
            )
            continue
        if package in constraints:
            issues.append(f"{req.name}: duplicate dependency entries found")
            continue
        constraints[package] = raw

    expected = set(packages)
    missing = sorted(expected - set(constraints))
    for package in missing:
        requirement = "exact dependency pin" if exact_required else "dependency constraint"
        issues.append(f"{package}: missing {requirement}")

    if issues:
        raise SystemExit("\n".join(issues))

    return constraints


def extract_absent_packages(dependencies: Iterable[str], *, packages: Iterable[str]) -> list[str]:
    found: list[str] = []
    canonical = {package.lower(): package for package in packages}
    for raw in dependencies:
        req = parse_requirement(raw)
        package = canonical.get(req.name.lower())
        if package:
            found.append(raw)
    return found


def extract_lock_versions(lockfile: dict[str, object], *, packages: Iterable[str]) -> dict[str, str]:
    package_tables = lockfile.get("package")
    if not isinstance(package_tables, list):
        raise SystemExit("Invalid uv.lock: missing [[package]] entries")

    canonical = {package.lower(): package for package in packages}
    versions: dict[str, str] = {}
    for entry in package_tables:
        if not isinstance(entry, dict):
            continue
        raw_name = entry.get("name")
        raw_version = entry.get("version")
        if not isinstance(raw_name, str) or not isinstance(raw_version, str):
            continue
        package = canonical.get(raw_name.lower())
        if package:
            versions[package] = raw_version

    missing = sorted(set(packages) - set(versions))
    if missing:
        raise SystemExit(
            "uv.lock is missing resolved package versions: " + ", ".join(missing)
        )
    return versions


def extract_overrides(pyproject: dict[str, object]) -> list[str]:
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


def collect_override_issues(overrides: Iterable[str]) -> list[str]:
    issues: list[str] = []
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
    cli_dependencies = extract_dependencies(cli_pyproject)
    cli_constraints = extract_constraints(cli_dependencies, packages=PACKAGES)
    retired = extract_absent_packages(cli_dependencies, packages=RETIRED_PACKAGES)

    issues = collect_override_issues(extract_overrides(cli_pyproject))
    if retired:
        issues.append(
            "Retired runtime package must not be a CLI dependency: "
            + ", ".join(retired)
        )

    lockfile = load_toml(args.lockfile)
    assert lockfile is not None
    lock_versions = extract_lock_versions(lockfile, packages=PACKAGES)

    summary: list[str] = [
        f"cli spec-kitty-events: {cli_constraints['spec-kitty-events']} (uv.lock {lock_versions['spec-kitty-events']})",
        f"cli spec-kitty-tracker: {cli_constraints['spec-kitty-tracker']} (uv.lock {lock_versions['spec-kitty-tracker']})",
        "cli spec-kitty-runtime: retired / not a dependency",
    ]
    for package, version in lock_versions.items():
        if not requirement_contains_version(cli_constraints[package], version):
            issues.append(
                f"{package} uv.lock version {version} is outside CLI constraint "
                f"{cli_constraints[package]}"
            )

    saas_pyproject = load_toml(args.saas_pyproject)
    if saas_pyproject is not None:
        saas_constraints = extract_constraints(
            extract_dependencies(saas_pyproject),
            packages=("spec-kitty-events", "spec-kitty-tracker"),
            exact_required=True,
        )
        summary.append(
            f"saas spec-kitty-events: {saas_constraints['spec-kitty-events']}"
        )
        summary.append(
            f"saas spec-kitty-tracker: {saas_constraints['spec-kitty-tracker']}"
        )
        for package, saas_constraint in saas_constraints.items():
            saas_pin = exact_pin(saas_constraint)
            assert saas_pin is not None
            if not requirement_contains_version(cli_constraints[package], saas_pin):
                issues.append(
                    f"{package} SaaS pin {saas_pin} is outside CLI constraint "
                    f"{cli_constraints[package]}"
                )
            if saas_pin != lock_versions[package]:
                issues.append(
                    f"{package} pin mismatch between SaaS and CLI uv.lock: "
                    f"{saas_pin} vs {lock_versions[package]}"
                )

    runtime_pyproject = load_toml(args.runtime_pyproject)
    if runtime_pyproject is not None:
        summary.append(
            "runtime spec-kitty-events: ignored; spec-kitty-runtime is retired for CLI releases"
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
