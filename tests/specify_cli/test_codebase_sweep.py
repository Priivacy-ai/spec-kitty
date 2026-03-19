"""T025: Codebase sweep -- verify no direct meta.json writes outside feature_metadata.py.

This test greps ``src/specify_cli/`` for code patterns that write meta.json
directly (e.g. ``json.dump(meta, ...)``, ``meta_path.write_text(...)``)
instead of going through the canonical single-writer API in
``feature_metadata.py``.

Migration files (``src/specify_cli/upgrade/migrations/``) are excluded
because they are frozen historical code that uses the compatibility wrapper.

The sweep also excludes ``feature_metadata.py`` itself (it *is* the writer).

Calls to ``write_meta()`` or ``write_feature_meta()`` are NOT violations --
those are the public API.  Only raw ``json.dump`` / ``json.dumps`` + file
write patterns that bypass the single writer are flagged.
"""

from __future__ import annotations

import re
from pathlib import Path


# Patterns that indicate direct meta.json writes outside the public API.
# We look for the combination of json serialization + file write in the
# same function / close proximity, specifically for "meta" dicts.
_WRITE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # json.dump(meta, fh) -- writing a meta dict directly to a file handle
    ("json.dump(meta, ...)", re.compile(r"json\.dump\s*\(\s*meta\b")),
    # meta_path.write_text( -- writing to a variable named meta_path
    ("meta_path.write_text(", re.compile(r"meta_path\.write_text\s*\(")),
    # "meta.json" ... .write_text(  -- writing to a path containing "meta.json"
    ("'meta.json' ... write_text", re.compile(
        r"""["']meta\.json["'].*\.write_text\s*\("""
    )),
]

# Files that ARE the single writer (not violations).
_ALLOWED_FILES: frozenset[str] = frozenset({
    "feature_metadata.py",
})

# Directories whose contents are excluded from the sweep.
_EXCLUDED_DIRS: frozenset[str] = frozenset({
    "migrations",
})


def _src_dir() -> Path:
    """Return the ``src/specify_cli`` directory relative to the repo root."""
    # Walk up from this test file to find the repo root.
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        candidate = parent / "src" / "specify_cli"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Could not locate src/specify_cli from test file")


def test_no_direct_meta_json_writes_outside_feature_metadata() -> None:
    """No code outside feature_metadata.py writes meta.json directly.

    This is the automated guard from T025 -- it will catch any future
    regressions that bypass the single metadata writer.
    """
    src_dir = _src_dir()
    violations: list[str] = []

    for py_file in sorted(src_dir.rglob("*.py")):
        # Skip the canonical writer itself
        if py_file.name in _ALLOWED_FILES:
            continue

        # Skip frozen migration code
        if any(excluded in py_file.parts for excluded in _EXCLUDED_DIRS):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        relative = py_file.relative_to(src_dir)
        for description, pattern in _WRITE_PATTERNS:
            if pattern.search(content):
                violations.append(f"{relative}: matches '{description}'")

    assert not violations, (
        "Direct meta.json writes found outside feature_metadata.py:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nAll meta.json writes must go through feature_metadata.write_meta()."
    )
