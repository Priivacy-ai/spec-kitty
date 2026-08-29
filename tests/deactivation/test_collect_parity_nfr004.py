"""NFR-004 / SC-004 — opt-in collection parity for the sync test surface.

Mission ``sync-deactivate-by-default`` (WP07 / T020). WP04 flipped the suite
default to sync-**OFF** and WP05 gated ``tests/sync`` + ``tests/specify_cli/sync``
behind a collection-time ``skipif``. This guard proves the OPT-IN contract
(NFR-004): with ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` the exact same node-id set is
collected as the WP01-frozen baseline — no previously-green sync test silently
vanished or was newly skipped under opt-in.

SC-004 is satisfied *without a second full execution*: this is a
``--collect-only`` diff against the frozen baseline file, never a re-run of the
sync suite. The guard itself runs on the DEFAULT (sync-off) push path — it is
marked ``fast`` and is NOT sync-gated; it only sets the opt-in env for the
subprocess it spawns.

The canonical ``tests._support.coverage_safety.collection_equivalence`` helper is
deliberately NOT reused here for two reasons: (1) it takes no ``env``, and we must
inject the opt-in flag for the child process; (2) its ``_looks_like_nodeid``
strips leading whitespace before matching, which would misclassify the indented
``tests/sync/conftest.py`` FR-007 leak-guard banner (printed during collection) as
node-ids. We parse strictly instead — a real ``pytest --collect-only -q`` node-id
line has no leading whitespace and contains ``"::"``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE = _REPO_ROOT / "tests" / "architectural" / "census" / "sync_deactivate_collect_baseline.txt"
#: The two roots frozen in the WP01 baseline (relative to the repo root so the
#: emitted node-ids are relative and compare against the baseline verbatim).
_SYNC_SURFACE = ("tests/sync", "tests/specify_cli/sync")
_ENABLE_FLAG = "SPEC_KITTY_ENABLE_SAAS_SYNC"
#: Escape hatches that would mask the opt-in even with the enable flag set; the
#: child must collect with a clean opt-in posture.
_SYNC_DISABLE_VARS = ("SPEC_KITTY_SYNC_DISABLE", "SPEC_KITTY_SYNC_MINIMAL_IMPORT")
_COLLECT_TIMEOUT_S = 300


def _parse_nodeids(stdout: str) -> set[str]:
    """Strict node-id parse, robust to the ``tests/sync`` leak-guard banner.

    A ``--collect-only -q`` node-id line has no leading whitespace and contains
    ``"::"``; the banner lines are indented or carry no ``"::"``, and the trailing
    ``"N tests collected"`` summary carries no ``"::"`` either.
    """
    return {line for line in stdout.splitlines() if line and not line[0].isspace() and "::" in line}


def _collect_optin_nodeids() -> set[str]:
    """Collect the sync-surface node-id set under the opt-in flag (subprocess)."""
    env = dict(os.environ)
    env[_ENABLE_FLAG] = "1"
    for var in _SYNC_DISABLE_VARS:
        env.pop(var, None)
    completed = subprocess.run(  # noqa: S603 — fixed pytest selector, not shell input
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            *_SYNC_SURFACE,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=_REPO_ROOT,
        env=env,
        timeout=_COLLECT_TIMEOUT_S,
    )
    # 0 = collected ok, 5 = no tests collected (would fail the parity assert with a
    # clear diff); anything else is a hard collection/usage error worth surfacing.
    if completed.returncode not in (0, 5):
        raise AssertionError(
            f"pytest --collect-only failed for {list(_SYNC_SURFACE)} "
            f"(exit {completed.returncode}).\n"
            f"stdout tail:\n{completed.stdout[-2000:]}\n"
            f"stderr tail:\n{completed.stderr[-2000:]}"
        )
    return _parse_nodeids(completed.stdout)


def _load_baseline() -> set[str]:
    return {line.strip() for line in _BASELINE.read_text(encoding="utf-8").splitlines() if line.strip()}


def test_optin_collection_matches_frozen_baseline() -> None:
    """NFR-004 / SC-004: opt-in node-id set == WP01 baseline (diff = 0)."""
    baseline = _load_baseline()
    assert baseline, "WP01 baseline is empty — regenerate it before trusting parity"
    live = _collect_optin_nodeids()
    newly_skipped = baseline - live
    unexpected = live - baseline
    assert not (newly_skipped or unexpected), (
        "opt-in collection drifted from the WP01 baseline "
        f"({len(baseline)} baseline vs {len(live)} live; NFR-004 diff != 0):\n"
        + "".join(f"  newly-skipped: {nid}\n" for nid in sorted(newly_skipped))
        + "".join(f"  unexpected: {nid}\n" for nid in sorted(unexpected))
    )


def test_baseline_parser_is_not_vacuous() -> None:
    """Bite proof: the strict parser keeps node-ids and drops the banner noise."""
    sample = (
        "tests/sync/test_x.py::test_a\n"
        "tests/specify_cli/sync/test_y.py::TestC::test_b\n"
        "  - carry-forward: written across tests/sync/ files (consent.py:447-451)\n"
        "[FR-007 leak guard] 0 node(s) are pinned to a known leak\n"
        "3607 tests collected in 1.23s\n"
    )
    assert _parse_nodeids(sample) == {
        "tests/sync/test_x.py::test_a",
        "tests/specify_cli/sync/test_y.py::TestC::test_b",
    }
