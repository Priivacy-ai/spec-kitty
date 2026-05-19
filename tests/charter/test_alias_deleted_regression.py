"""Regression tests: resolve_governance alias must be fully deleted (WP04 / DRIFT-1).

AC-5 (slice-f-multi-context-extensibility-01KRX5C8):
  The bare symbol ``resolve_governance`` is a DRIFT-1 back-compat alias that
  was retained after the canonical name ``resolve_project_governance`` was
  introduced.  HiC §5a.1 (C-003) mandates clean removal with no
  DeprecationWarning, no sunset comment, no shim.

These tests are the RED gate:
  - Before WP04 GREEN: both tests fail because the alias still exists.
  - After WP04 GREEN:  both tests pass because the alias is gone and all
    test fixtures have been migrated to the canonical name.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# AC-5 — ImportError gate
# ---------------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
_TESTS_CHARTER_DIR = _THIS_FILE.parent


def test_resolve_governance_import_raises_import_error() -> None:
    """Importing ``resolve_governance`` from ``charter`` must raise ImportError.

    This is the primary AC-5 gate.  If the alias still exists in
    ``charter.resolver`` or ``charter.__init__``, this test fails (RED).
    Once WP04 deletes both the alias assignment and the __init__ export,
    this test turns GREEN.
    """
    import importlib

    with pytest.raises(ImportError):
        importlib.import_module("charter")  # ensure module is fresh-importable
        from charter import resolve_governance  # noqa: F401


# ---------------------------------------------------------------------------
# AC-5 — no lingering fixture usage
# ---------------------------------------------------------------------------

# Matches the alias only when it is actually used as an identifier (import, call, assignment),
# NOT when it appears embedded in a longer identifier such as a test function name
# (e.g. ``def test_resolve_governance_missing_...``).
#
# The positive patterns below capture the three shapes that constitute real usage:
#   1. import line:     ``import resolve_governance`` / ``resolve_governance,``
#   2. call site:       ``resolve_governance(``
#   3. assignment:      ``resolve_governance =``
#
# Lines where ``resolve_governance`` only appears as a prefix of a longer token
# (``resolve_governance_for_profile``, ``resolve_project_governance``, test function names)
# are excluded by the negative lookahead ``(?!_)``.
_ALIAS_USAGE_PATTERN = re.compile(
    r"\bresolve_governance(?!_for_profile\b|_for_profile\(|\w)"
    r"(?:\s*[,(=]|\s*$|\s*#)"
    r"|"
    r"\bresolve_governance\s*\("
)


def test_no_test_fixture_still_imports_legacy_alias() -> None:
    """No file in tests/charter/ (except this one) may import or call ``resolve_governance``.

    The scan looks for actual alias usage (imports, call sites, assignments) and
    excludes:
      - this file itself,
      - occurrences of ``resolve_governance`` only as part of a longer identifier
        (e.g. test function name prefixes like ``test_resolve_governance_missing_...``
        or the canonical ``resolve_governance_for_profile``).

    Any remaining hit is a leaked alias usage that must be migrated to the
    canonical name ``resolve_project_governance`` before this test turns GREEN.
    """
    violations: list[str] = []

    for py_file in sorted(_TESTS_CHARTER_DIR.rglob("*.py")):
        if py_file.resolve() == _THIS_FILE:
            continue  # skip self

        source = py_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), start=1):
            if _ALIAS_USAGE_PATTERN.search(line):
                violations.append(f"{py_file.relative_to(_TESTS_CHARTER_DIR)}:{lineno}: {line.strip()}")

    assert not violations, (
        "Found lingering resolve_governance alias usage(s) in tests/charter/ — "
        "migrate each call-site to resolve_project_governance:\n"
        + "\n".join(violations)
    )
