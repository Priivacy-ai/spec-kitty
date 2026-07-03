"""Architectural guard: the charter_runtime umbrella canonical paths import.

Re-homed from the retired lock-gate ``test_charter_runtime_shim_paths.py``
(mission unshim-wave2 / WP06, FR-006p2 + FR-007). That file was the 6-test
"cannot silently remove the shim" gate introduced by LD-5 / FR-014 / C-008.
Wave 2 deletes the three legacy charter shim packages
(``specify_cli.charter_lint`` / ``charter_freshness`` / ``charter_preflight``),
so five of the six lock-gate tests became moot *by design* — they pinned the
legacy re-export identity that is now intentionally gone.

The one surviving invariant is that the **canonical** umbrella sub-packages
still import. That invariant is real and refactor-stable, so it is re-homed
here (C-006 convert-or-delete, never a silent drop). It keeps the
``architectural`` marker and stays CI-selected exactly as before.

Per-test disposition of the retired ``test_charter_runtime_shim_paths.py``
(6 tests; C-006 refactor-stable doctrine — convert-or-delete, never a silent drop):

Row 1 — test_canonical_paths_import
  Invariant: the 4+1 canonical umbrella sub-packages import
    (charter_runtime, .lint, .freshness, .preflight, .facade).
  Disposition: RE-HOMED.
  Surviving coverage: this file, test_canonical_paths_import — identical
    assertion, architectural marker preserved, CI-selected exactly as before.

Row 2 — test_legacy_paths_still_import
  Invariant: legacy top-level paths specify_cli.charter_lint /
    charter_freshness / charter_preflight re-import via the shim.
  Disposition: RETIRED-WITH-DELETION.
  Surviving coverage: MOOT by design — WP06 deletes legacy importability.
    The inverse is now pinned live by test_legacy_charter_paths_are_gone below.

Row 3 — test_legacy_submodules_resolve_via_shim
  Invariant: legacy dotted submodule imports return the *identical* module
    object (mock.patch correctness).
  Disposition: RETIRED-WITH-DELETION.
  Surviving coverage: MOOT by design — no shim, so no legacy identity to
    preserve. Canonical mock.patch targets are exercised live by the preflight
    suites tests/agent/cli/commands/test_next_preflight.py and
    test_implement_preflight.py, which patch charter_runtime.preflight.hook.

Row 4 — test_all_canonical_lint_checks_have_legacy_aliases
  Invariant: every canonical lint checker had a same-identity legacy alias.
  Disposition: RETIRED-WITH-DELETION.
  Surviving coverage: MOOT by design — legacy check aliases deleted with the
    shim. Canonical checks are exercised by
    tests/specify_cli/charter_lint/test_engine.py (imports charter_runtime.lint).

Row 5 — test_legacy_lint_checks_parent_has_package_metadata
  Invariant: the synthetic legacy parent package
    specify_cli.charter_lint.checks kept a discoverable importlib spec.
  Disposition: RETIRED-WITH-DELETION.
  Surviving coverage: MOOT by design — the synthetic legacy parent package is
    deleted; there is no legacy parent whose metadata could be asserted.

Row 6 — test_missing_legacy_lint_check_alias_fails_loudly
  Invariant: guard #1459 — a dropped nested legacy alias must raise
    ModuleNotFoundError, not re-discover the canonical file via the legacy parent.
  Disposition: RETIRED-WITH-DELETION.
  Surviving coverage: MOOT/SUBSUMED — with the shim gone, ALL legacy paths raise
    ModuleNotFoundError permanently. The stronger contract is pinned live by
    test_legacy_charter_paths_are_gone below.
"""

from __future__ import annotations

import importlib

import pytest


pytestmark = [pytest.mark.architectural]


def test_canonical_paths_import() -> None:
    """All umbrella sub-packages exist at the canonical charter_runtime paths."""
    for path in (
        "specify_cli.charter_runtime",
        "specify_cli.charter_runtime.lint",
        "specify_cli.charter_runtime.freshness",
        "specify_cli.charter_runtime.preflight",
        "specify_cli.charter_runtime.facade",
    ):
        mod = importlib.import_module(path)
        assert mod is not None, f"{path} failed to import"


def test_legacy_charter_paths_are_gone() -> None:
    """The three legacy charter shim packages are deleted (FR-006p2).

    Positive lock on the *post-deletion* invariant: importing any of the
    retired legacy top-level packages must raise ``ModuleNotFoundError``.
    This is the inverse of the retired ``test_legacy_paths_still_import`` and
    subsumes the #1459 nested-alias guard (rows 2 and 6 above).
    """
    for path in (
        "specify_cli.charter_lint",
        "specify_cli.charter_freshness",
        "specify_cli.charter_preflight",
    ):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(path)
