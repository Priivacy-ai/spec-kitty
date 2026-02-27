#!/usr/bin/env python3
"""Release readiness validator for Spec Kitty PyPI automation.

The script validates three core conditions before allowing a release:

1. The release version declared in pyproject.toml is well-formed and
   PEP 440-compatible (`X.Y.Z`, `X.Y.ZaN`, `X.Y.ZbN`, or `X.Y.ZrcN`).
2. CHANGELOG.md contains a populated section for the target version.
3. Version progression is monotonic relative to existing git tags and, in tag
   mode, matches the release tag that triggered the workflow.

It is intentionally dependency-light so it can run both locally and in CI
without additional bootstrapping beyond Python 3.11.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for older interpreters
    import tomli as tomllib  # type: ignore

from packaging.version import InvalidVersion, Version

CHANGELOG_HEADING_RE = re.compile(
    r"^##\s*(?:\[\s*)?(?P<version>\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?)(?:\s*\]|)(?:\s*-.*)?$"
)


@dataclass
class ValidationIssue:
    message: str
    hint: Optional[str] = None

    def format(self) -> str:
        if self.hint:
            return f"{self.message} (Hint: {self.hint})"
        return self.message


@dataclass
class ValidationResult:
    ok: bool
    mode: str
    pyproject_path: Path
    changelog_path: Path
    version: str
    tag: Optional[str]
    issues: List[ValidationIssue] = field(default_factory=list)

    def report(self) -> None:
        header = "Release Validator Summary"
        print(header)
        print("-" * len(header))
        print(f"Mode: {self.mode}")
        print(f"pyproject.toml: {self.pyproject_path}")
        print(f"CHANGELOG.md: {self.changelog_path}")
        print(f"Version: {self.version or 'N/A'}")
        print(f"Tag: {self.tag or 'N/A'}")
        if not self.ok:
            print("\nIssues detected:")
            for idx, issue in enumerate(self.issues, start=1):
                print(f"  {idx}. {issue.format()}")
        else:
            print("\nAll required checks passed.")


class ReleaseValidatorError(Exception):
    """Base exception for validator failures."""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate release readiness for Spec Kitty PyPI automation"
    )
    parser.add_argument(
        "--mode",
        choices=("branch", "tag"),
        default="branch",
        help="Validation mode. 'branch' expects a version bump without a tag. "
        "'tag' enforces tag-version parity and monotonic progression.",
    )
    parser.add_argument(
        "--tag",
        help="Explicit tag (e.g., v1.2.3 or v1.2.3rc1). Defaults to the detected "
        "GITHUB_REF or GITHUB_REF_NAME in tag mode.",
    )
    parser.add_argument(
        "--pyproject",
        default="pyproject.toml",
        help="Path to pyproject.toml (default: %(default)s)",
    )
    parser.add_argument(
        "--changelog",
        default="CHANGELOG.md",
        help="Path to changelog file (default: %(default)s)",
    )
    parser.add_argument(
        "--tag-pattern",
        default="v*",
        help="Git tag glob pattern used for version progression checks "
        "(default: %(default)s).",
    )
    parser.add_argument(
        "--fail-on-missing-tag",
        action="store_true",
        help="Treat missing tag detection as a hard failure (defaults to failure in tag mode).",
    )
    return parser.parse_args(argv)


def load_pyproject_version(path: Path) -> str:
    if not path.exists():
        raise ReleaseValidatorError(
            f"pyproject.toml not found at {path} – ensure you run from repository root."
        )
    with path.open("rb") as fp:
        data = tomllib.load(fp)
    try:
        version = data["project"]["version"]
    except KeyError as exc:  # pragma: no cover - defensive; unlikely if file well-formed
        raise ReleaseValidatorError(
            "Unable to locate [project].version in pyproject.toml."
        ) from exc
    if not isinstance(version, str):
        raise ReleaseValidatorError("pyproject version must be a string.")
    parse_release_version(version)
    return version


def read_changelog(path: Path) -> str:
    if not path.exists():
        raise ReleaseValidatorError(f"CHANGELOG not found at {path}.")
    return path.read_text(encoding="utf-8-sig")


def changelog_has_entry(changelog: str, version: str) -> bool:
    lines = changelog.splitlines()
    capture = False
    content: List[str] = []
    for line in lines:
        heading = CHANGELOG_HEADING_RE.match(line)
        if heading:
            if capture:
                break
            capture = heading.group("version") == version
            continue
        if capture:
            content.append(line.strip())
    if not capture:
        return False
    return any(fragment for fragment in content if fragment)


def git(*args: str, cwd: Optional[Path] = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise ReleaseValidatorError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def find_repo_root(start: Path) -> Path:
    try:
        output = git("rev-parse", "--show-toplevel", cwd=start)
    except ReleaseValidatorError as exc:
        raise ReleaseValidatorError(
            "Unable to locate git repository root. Ensure git is installed and run this script "
            "inside the Spec Kitty repository."
        ) from exc
    return Path(output)


def discover_release_tags(
    repo_root: Path, tag_pattern: str, exclude: Optional[str] = None
) -> List[str]:
    output = git("tag", "--list", tag_pattern, cwd=repo_root)
    tags = [line.strip() for line in output.splitlines() if line.strip()]
    filtered: List[str] = []
    for tag in tags:
        if tag == exclude:
            continue
        candidate = tag.lstrip("v")
        try:
            parse_release_version(candidate)
        except ReleaseValidatorError:
            continue
        else:
            filtered.append(tag)
    filtered.sort(key=lambda tag: parse_release_version(tag.lstrip("v")), reverse=True)
    return filtered


def parse_release_version(value: str) -> Version:
    """Parse and validate a supported release version string.

    Accepted forms:
    - X.Y.Z
    - X.Y.ZaN
    - X.Y.ZbN
    - X.Y.ZrcN
    """
    try:
        parsed = Version(value)
    except InvalidVersion as exc:
        raise ReleaseValidatorError(
            f"Value '{value}' is not a valid PEP 440 release version."
        ) from exc

    if parsed.epoch != 0:
        raise ReleaseValidatorError(f"Version '{value}' must not use an epoch.")
    if parsed.local is not None:
        raise ReleaseValidatorError(f"Version '{value}' must not include a local segment.")
    if parsed.post is not None:
        raise ReleaseValidatorError(f"Version '{value}' must not include a post-release segment.")
    if parsed.dev is not None:
        raise ReleaseValidatorError(f"Version '{value}' must not include a dev-release segment.")
    if len(parsed.release) != 3:
        raise ReleaseValidatorError(f"Version '{value}' must use three release components (X.Y.Z).")
    if parsed.pre is not None and parsed.pre[0] not in {"a", "b", "rc"}:
        raise ReleaseValidatorError(
            f"Version '{value}' has unsupported pre-release segment '{parsed.pre[0]}'."
        )

    return parsed


def detect_tag_from_env() -> Optional[str]:
    ref_name = os.getenv("GITHUB_REF_NAME")
    if ref_name and ref_name.startswith("v"):
        try:
            parse_release_version(ref_name[1:])
            return ref_name
        except ReleaseValidatorError:
            pass
    ref = os.getenv("GITHUB_REF")
    if ref and ref.startswith("refs/tags/"):
        candidate = ref.rsplit("/", maxsplit=1)[-1]
        if candidate.startswith("v"):
            try:
                parse_release_version(candidate[1:])
                return candidate
            except ReleaseValidatorError:
                pass
    return None


def validate_version_progression(
    current_version: str,
    existing_tags: Sequence[str],
    *,
    same_major_only: bool = False,
    require_strict_progression: bool = True,
) -> Optional[ValidationIssue]:
    current_version_parsed = parse_release_version(current_version)
    comparable_tags = list(existing_tags)
    if same_major_only:
        current_major = current_version_parsed.release[0]
        comparable_tags = [
            tag
            for tag in existing_tags
            if parse_release_version(tag.lstrip("v")).release[0] == current_major
        ]

    if not comparable_tags:
        return None

    comparable_tags.sort(
        key=lambda tag: parse_release_version(tag.lstrip("v")),
        reverse=True,
    )
    latest_version_parsed = parse_release_version(comparable_tags[0].lstrip("v"))
    if require_strict_progression:
        if current_version_parsed <= latest_version_parsed:
            return ValidationIssue(
                message=f"Version {current_version} does not advance beyond latest tag {comparable_tags[0]}.",
                hint="Select a release version greater than previously published tags.",
            )
    elif current_version_parsed < latest_version_parsed:
        return ValidationIssue(
            message=f"Version {current_version} is behind latest tag {comparable_tags[0]}.",
            hint="Select a release version equal to or greater than previously published tags in this major stream.",
        )
    return None


def ensure_tag_matches_version(version: str, tag: Optional[str]) -> Optional[ValidationIssue]:
    expected = f"v{version}"
    if not tag:
        return ValidationIssue(
            message="No release tag detected.",
            hint="Pass --tag, set GITHUB_REF_NAME, or run in branch mode.",
        )
    if tag != expected:
        return ValidationIssue(
            message=f"Tag {tag} does not match project version {version}.",
            hint=f"Retag the commit as {expected} or bump the version in pyproject.toml.",
        )
    return None


def run_validation(args: argparse.Namespace) -> ValidationResult:
    pyproject_path = Path(args.pyproject).resolve()
    changelog_path = Path(args.changelog).resolve()
    version = ""
    tag: Optional[str] = None
    issues: List[ValidationIssue] = []

    try:
        version = load_pyproject_version(pyproject_path)
        changelog_text = read_changelog(changelog_path)
    except ReleaseValidatorError as exc:
        issues.append(ValidationIssue(str(exc)))
        return ValidationResult(
            ok=False,
            mode=args.mode,
            pyproject_path=pyproject_path,
            changelog_path=changelog_path,
            version=version,
            tag=tag,
            issues=issues,
        )

    repo_root = find_repo_root(pyproject_path.parent)

    if not changelog_has_entry(changelog_text, version):
        issues.append(
            ValidationIssue(
                message=f"CHANGELOG.md lacks a populated section for {version}.",
                hint="Add release notes under a '## {version}' heading.",
            )
        )

    if args.mode == "tag":
        tag = args.tag or detect_tag_from_env()
        if not tag:
            issues.append(
                ValidationIssue(
                    message="No tag supplied and none detected from environment.",
                    hint="Use --tag vX.Y.Z (or vX.Y.ZaN / vX.Y.ZbN / vX.Y.ZrcN), or set GITHUB_REF_NAME in CI.",
                )
            )
        else:
            mismatch = ensure_tag_matches_version(version, tag)
            if mismatch:
                issues.append(mismatch)

        existing_tags = discover_release_tags(
            repo_root, tag_pattern=args.tag_pattern, exclude=tag
        )
        progression_issue = validate_version_progression(
            version,
            existing_tags,
            same_major_only=True,
            require_strict_progression=True,
        )
        if progression_issue:
            issues.append(progression_issue)
    else:
        existing_tags = discover_release_tags(repo_root, tag_pattern=args.tag_pattern)
        progression_issue = validate_version_progression(
            version,
            existing_tags,
            same_major_only=True,
            require_strict_progression=False,
        )
        if progression_issue:
            issues.append(progression_issue)

    ok = len(issues) == 0
    return ValidationResult(
        ok=ok,
        mode=args.mode,
        pyproject_path=pyproject_path,
        changelog_path=changelog_path,
        version=version,
        tag=tag,
        issues=issues,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    result = run_validation(args)
    result.report()
    if result.ok:
        return 0
    for issue in result.issues:
        print(f"ERROR: {issue.format()}", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
