#!/usr/bin/env python3
"""Validate spec-kitty library dependency policy before release."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument(
        "--matrix", default="docs/releases/dependency-compatibility-matrix.toml"
    )
    parser.add_argument(
        "--libraries",
        default="spec-kitty-events,spec-kitty-runtime,spec-kitty-tracker",
        help="Comma-separated library names to validate.",
    )
    parser.add_argument(
        "--allow-prerelease",
        action="store_true",
        help="Allow prerelease pins for this run.",
    )
    parser.add_argument(
        "--allow-direct-reference",
        action="store_true",
        help="Allow direct-reference dependency URLs for this run.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Allow libraries that are neither dependencies nor train entries.",
    )
    return parser.parse_args()


def load_toml(path: Path) -> Dict[str, object]:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load_dependencies(pyproject_data: Dict[str, object]) -> List[str]:
    deps = pyproject_data.get("project", {}).get("dependencies")
    if not isinstance(deps, list):
        raise SystemExit("Invalid pyproject.toml: [project].dependencies must be a list")
    return [str(dep) for dep in deps]


def load_project_version(pyproject_data: Dict[str, object]) -> str:
    version = pyproject_data.get("project", {}).get("version")
    if not isinstance(version, str):
        raise SystemExit("Invalid pyproject.toml: missing [project].version")
    return version


def parse_requirement(raw: str) -> Optional[Requirement]:
    try:
        return Requirement(raw)
    except Exception:
        return None


def lookup_dependency(dependencies: List[str], package: str) -> List[str]:
    matches: List[str] = []
    for dep in dependencies:
        req = parse_requirement(dep)
        if req and req.name.lower() == package.lower():
            matches.append(dep)
            continue
        if dep.lower().startswith(f"{package.lower()} "):
            matches.append(dep)
    return matches


def exact_pin(req: Requirement) -> Optional[str]:
    specs = list(req.specifier)
    if len(specs) != 1:
        return None
    spec = specs[0]
    if spec.operator != "==" or spec.version.endswith(".*"):
        return None
    return spec.version


def fetch_pypi_info(package: str, version: str) -> Dict[str, object]:
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise SystemExit(f"Pinned version not found on PyPI: {package}=={version}")
        raise
    except urllib.error.URLError as exc:
        raise SystemExit(f"Unable to reach PyPI for {package}=={version}: {exc}") from exc

    info = payload.get("info")
    if not isinstance(info, dict):
        raise SystemExit(f"Unexpected PyPI payload for {package}=={version}")
    return info


def has_mit_metadata(info: Dict[str, object]) -> bool:
    classifiers = info.get("classifiers")
    classifier_ok = isinstance(classifiers, list) and any(
        isinstance(c, str) and c.strip() == "License :: OSI Approved :: MIT License"
        for c in classifiers
    )

    license_field = info.get("license")
    license_expr = info.get("license_expression")
    license_ok = isinstance(license_field, str) and "mit" in license_field.lower()
    license_expr_ok = isinstance(license_expr, str) and "mit" in license_expr.lower()

    return classifier_ok or license_ok or license_expr_ok


def parse_train_versions(matrix_data: Dict[str, object], version: str) -> Dict[str, str]:
    cli = matrix_data.get("cli")
    if not isinstance(cli, dict):
        return {}

    entry = cli.get(version)
    if not isinstance(entry, dict):
        return {}

    train = entry.get("train")
    if not isinstance(train, dict):
        return {}

    parsed: Dict[str, str] = {}
    for key, value in train.items():
        if isinstance(key, str) and isinstance(value, str):
            parsed[key] = value.strip()
    return parsed


def validate_pinned_version(
    library: str,
    pinned: str,
    *,
    allow_prerelease: bool,
    issues: List[str],
    summary: List[str],
    source: str,
) -> None:
    try:
        parsed = Version(pinned)
    except InvalidVersion:
        issues.append(f"{library}: invalid pinned version '{pinned}' ({source}).")
        return

    if parsed.is_prerelease and not allow_prerelease:
        issues.append(
            f"{library}: prerelease pin '{pinned}' is not allowed without explicit approval."
        )

    try:
        info = fetch_pypi_info(library, pinned)
    except SystemExit as exc:
        issues.append(str(exc))
        return
    if not has_mit_metadata(info):
        issues.append(
            f"{library}=={pinned}: missing clear MIT metadata on PyPI "
            "(classifier/license/license_expression)."
        )

    summary.append(f"{library}: validated {pinned} ({source})")


def main() -> int:
    args = parse_args()

    pyproject_data = load_toml(Path(args.pyproject))
    dependencies = load_dependencies(pyproject_data)
    version = load_project_version(pyproject_data)

    matrix_path = Path(args.matrix)
    matrix_data = load_toml(matrix_path) if matrix_path.exists() else {}
    train_versions = parse_train_versions(matrix_data, version)

    libraries = [lib.strip() for lib in args.libraries.split(",") if lib.strip()]

    issues: List[str] = []
    summary: List[str] = []

    for library in libraries:
        matches = lookup_dependency(dependencies, library)

        if len(matches) > 1:
            issues.append(f"Multiple dependency entries found for {library}: {matches}")
            continue

        if matches:
            raw = matches[0]
            req = parse_requirement(raw)
            if req is None:
                issues.append(f"Unable to parse dependency requirement: {raw}")
                continue

            if req.url:
                if args.allow_direct_reference:
                    summary.append(f"{library}: direct reference approved ({req.url}).")
                    continue
                issues.append(
                    f"{library}: direct reference is not allowed ({raw}). "
                    "Publish to PyPI and pin with == instead."
                )
                continue

            pinned_version = exact_pin(req)
            if not pinned_version:
                issues.append(
                    f"{library}: dependency must be exact-pinned with == (found: {raw})."
                )
                continue

            train_value = train_versions.get(library)
            if train_value and train_value.lower() not in {"n/a", "na", "not-used", "not used"}:
                if train_value != pinned_version:
                    issues.append(
                        f"{library}: dependency pin {pinned_version} does not match release-train entry {train_value}."
                    )

            validate_pinned_version(
                library,
                pinned_version,
                allow_prerelease=args.allow_prerelease,
                issues=issues,
                summary=summary,
                source="dependency pin",
            )
            continue

        train_value = train_versions.get(library, "").strip()
        if train_value and train_value.lower() not in {"n/a", "na", "not-used", "not used"}:
            validate_pinned_version(
                library,
                train_value,
                allow_prerelease=args.allow_prerelease,
                issues=issues,
                summary=summary,
                source="release-train matrix",
            )
            continue

        if not args.allow_missing:
            issues.append(
                f"Missing required library entry for {library} (dependency or release-train matrix)."
            )

    print("Dependency Policy Summary")
    print("-------------------------")
    for line in summary:
        print(f"- {line}")

    if issues:
        print("\nDependency policy violations:")
        for idx, issue in enumerate(issues, start=1):
            print(f"  {idx}. {issue}")
        return 1

    print("\nAll dependency policy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
