#!/usr/bin/env python3
"""Validate that all @patch() / patch() target strings in test files resolve.

A patch() target like ``patch("a.b.c.attr")`` instructs unittest.mock to
import module ``a.b.c`` and replace its attribute ``attr``.  When packages
are renamed or functions are moved the string becomes stale — the test still
collects but the mock silently patches the wrong object (or raises at runtime).

This script extracts every target string and checks:
  1. The module portion (everything up to the last dot) is importable.
  2. The attribute (last segment) exists on that module.

Exit codes:
  0 — all targets valid
  1 — one or more targets broken

Usage (called by CI):
  python scripts/check_patch_targets.py
  python scripts/check_patch_targets.py tests/specific_dir/
"""
from __future__ import annotations

import importlib
import importlib.util
import re
import sys
from pathlib import Path

# Matches @patch("...") and patch("...") or patch('...')
# Only captures dotted module paths (at least one dot required so plain
# builtins like "open" are excluded from the dotted-path check).
_PATCH_TARGET_RE = re.compile(
    r"""(?:@patch|(?<!\w)patch)\s*\(\s*['"]([A-Za-z_][A-Za-z0-9_.]+\.[A-Za-z_][A-Za-z0-9_]*)['"]"""
)

# Modules that are known external / stdlib and don't need validation.
# These are importable in any environment but may not be installed in the
# linting environment (e.g. httpx may be optional).
_SKIP_MODULE_PREFIXES = frozenset(
    [
        "builtins",
        "os",
        "sys",
        "time",
        "datetime",
        "platform",
        "subprocess",
        "pathlib",
        "socket",
        "threading",
        "logging",
        "json",
        "re",
        "io",
        "shutil",
        "tempfile",
        "unittest",
    ]
)


def _should_skip(module_path: str) -> bool:
    top = module_path.split(".")[0]
    return top in _SKIP_MODULE_PREFIXES


def extract_targets(path: Path) -> list[tuple[str, int]]:
    """Return (target_string, line_number) pairs for all patch() calls."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []
    results = []
    for m in _PATCH_TARGET_RE.finditer(source):
        line = source[: m.start()].count("\n") + 1
        results.append((m.group(1), line))
    return results


def _mock_importer(dotted: str) -> tuple[object | None, str | None]:
    """Resolve a dotted path the same way ``unittest.mock._importer`` does.

    Tries importing progressively shorter module paths and walking the
    remainder via ``getattr``.  This correctly handles patterns like
    ``patch("pkg.module.imported_lib.Symbol")`` where ``imported_lib`` is
    an attribute of ``pkg.module`` (via ``import imported_lib`` inside it)
    but is not a sub-package of ``pkg``.
    """
    components = dotted.split(".")
    # Try longest possible import first, falling back to shorter ones.
    for split in range(len(components), 0, -1):
        module_path = ".".join(components[:split])
        try:
            obj: object = importlib.import_module(module_path)
        except ImportError:
            continue
        # Walk remaining components via getattr.
        try:
            for comp in components[split:]:
                obj = getattr(obj, comp)
            return obj, None
        except AttributeError:
            # Shorter import worked but the getattr chain broke — don't try
            # an even shorter import; the failure is real.
            return None, f"no attribute {components[split]!r} in {dotted!r}"
    return None, f"cannot import any prefix of {dotted!r}"


def validate(target: str) -> str | None:
    """Return an error message if target doesn't resolve, else None."""
    if _should_skip(target):
        return None
    # Split into (module_path, attr) — same as unittest.mock._get_target.
    parts = target.rsplit(".", 1)
    if len(parts) != 2:
        return f"cannot split into module + attr: {target!r}"
    module_path, attr = parts
    obj, err = _mock_importer(module_path)
    if err:
        return err
    if not hasattr(obj, attr):
        return f"{module_path!r} has no attribute {attr!r}"
    return None


def main(argv: list[str] | None = None) -> int:
    roots = [Path(a) for a in (argv or sys.argv[1:])] or [Path("tests")]
    errors: list[str] = []
    checked = 0

    for root in roots:
        for test_file in sorted(root.rglob("*.py")):
            for target, line in extract_targets(test_file):
                checked += 1
                err = validate(target)
                if err:
                    errors.append(f"{test_file}:{line}: {err}")

    if errors:
        print(f"::error::Broken patch() targets ({len(errors)} of {checked} checked):")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"All {checked} patch() targets valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
