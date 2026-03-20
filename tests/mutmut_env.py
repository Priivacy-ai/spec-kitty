"""Helpers for preparing mutmut's generated ``mutants/`` tree.

mutmut copies only the files it mutates into ``mutants/src``. Large packages in
this repo import sibling modules, so pytest inside ``mutants/`` needs a helper
that fills in missing files without overwriting mutated ones.
"""

from __future__ import annotations

import argparse
import shutil
from collections.abc import Iterable, Sequence
from pathlib import Path

IGNORED_NAMES = {"__pycache__"}


def copy_missing_tree(
    source: Path,
    destination: Path,
    *,
    ignored_names: Iterable[str] = IGNORED_NAMES,
) -> list[Path]:
    """Recursively copy only missing files from ``source`` into ``destination``."""
    ignored = set(ignored_names)
    if source.name in ignored:
        return []

    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        copied: list[Path] = []
        for child in source.iterdir():
            copied.extend(
                copy_missing_tree(
                    child,
                    destination / child.name,
                    ignored_names=ignored,
                )
            )
        return copied

    if destination.exists():
        return []

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return [destination]


def prepare_mutants_environment(repo_root: Path, mutants_root: Path) -> list[Path]:
    """Populate missing ``src/`` files into an existing mutmut ``mutants/`` tree."""
    source_root = repo_root / "src"
    mutants_source_root = mutants_root / "src"

    if not source_root.exists() or not mutants_source_root.exists():
        return []

    copied: list[Path] = []
    for child in source_root.iterdir():
        copied.extend(copy_missing_tree(child, mutants_source_root / child.name))
    return copied


def prepare_mutants_environment_from_cwd(cwd: Path | None = None) -> list[Path]:
    """Prepare mutmut only when the current working directory is ``mutants/``."""
    current = cwd or Path.cwd()
    if current.name != "mutants":
        return []
    return prepare_mutants_environment(current.parent, current)


def missing_required_paths(mutants_root: Path, required_paths: Sequence[str]) -> list[str]:
    """Return required relative paths that are still missing after preparation."""
    missing: list[str] = []
    for rel_path in required_paths:
        if not (mutants_root / rel_path).exists():
            missing.append(rel_path)
    return missing


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser used by the shell helper script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--mutants-root", type=Path, required=True)
    parser.add_argument(
        "--require",
        action="append",
        default=[],
        help="Relative path under mutants/ that must exist after preparation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point used by ``scripts/prepare-mutmut-env.sh``."""
    parser = build_parser()
    args = parser.parse_args(argv)

    copied = prepare_mutants_environment(args.repo_root, args.mutants_root)
    missing = missing_required_paths(args.mutants_root, args.require)

    if missing:
        for rel_path in missing:
            print(f"ERROR: required mutmut path missing: {rel_path}")
        return 1

    print(f"Prepared mutmut environment: copied {len(copied)} missing path(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
