"""Regression guard for ``test-full``'s fail-fast->aggregate control flow (#340).

``test_makefile_tier_topology.py`` (planning#22) statically parses the
``test-full`` recipe but never *executes* it, so #337's change — three passes
each ``|| touch $(TEST_FULL_STATUS)`` instead of stopping on the first
failure, with the final recipe line aggregating the marker into the target's
exit code (Makefile:52-63) — was verified only by the reviewing squad running
a throwaway, uncommitted Makefile by hand (`[squad]` review of #337). Nothing
committed forces a pass to fail and asserts the later passes still ran and the
target still exits non-zero, so a future edit that drops one of the
``|| touch $(TEST_FULL_STATUS)`` guards (e.g. while refactoring) would go
undetected until a real CI round-trip.

This module runs the REAL ``make test-full`` recipe against the real
``Makefile``, with ``uv`` stubbed out on ``PATH`` so no actual pytest suite
runs — the stub only records how many times ``uv run pytest ...`` was
invoked and fails the invocation(s) named by ``FAIL_ON_CALLS``. That is
enough to prove the aggregation control flow itself, cheaply and
deterministically.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = pytest.mark.architectural

_MARKER_FILE = gc.REPO_ROOT / ".test-full-status"

# Records every `uv run pytest ...` invocation to $CALL_LOG (one line each)
# and fails only the 1-based invocation numbers listed (comma-separated) in
# $FAIL_ON_CALLS -- everything else exits 0, so no real pytest ever runs.
_FAKE_UV_SCRIPT = """#!/bin/sh
echo "$@" >> "$CALL_LOG"
n=$(wc -l < "$CALL_LOG")
case ",$FAIL_ON_CALLS," in
  *",$n,"*) exit 1 ;;
  *) exit 0 ;;
esac
"""

# A synthetic recipe with the exact regression #340 warns about: the first
# pass's `|| touch $(TEST_FULL_STATUS)` guard dropped, reintroducing
# fail-fast. Used only by the meta-test below to prove this harness would
# actually catch that regression if it landed.
_REGRESSED_MAKEFILE = """\
TEST_FULL_STATUS := .test-full-status
test-full:
\t@rm -f $(TEST_FULL_STATUS)
\tuv run pytest tests/ -m "not stress and not timing" -n auto --dist loadfile -q
\tuv run pytest tests/ -m "stress and not windows_ci" -n0 --timeout=240 -q || touch $(TEST_FULL_STATUS)
\tuv run pytest tests/ -m timing -n0 --timeout=240 -q || touch $(TEST_FULL_STATUS)
\t@if [ -f $(TEST_FULL_STATUS) ]; then rm -f $(TEST_FULL_STATUS); exit 1; fi
"""


def _install_fake_uv(bin_dir: Path) -> None:
    fake_uv = bin_dir / "uv"
    fake_uv.write_text(_FAKE_UV_SCRIPT, encoding="utf-8")
    mode = fake_uv.stat().st_mode
    fake_uv.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _run_make_test_full(
    tmp_path: Path,
    fail_on_calls: str,
    *,
    cwd: Path,
    make_args: list[str] | None = None,
) -> tuple[int, list[str]]:
    """Run ``make test-full`` with a stubbed ``uv``.

    Returns ``(returncode, calls)`` where ``calls`` has one entry per
    ``uv run pytest ...`` invocation the recipe actually made.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _install_fake_uv(bin_dir)
    call_log = tmp_path / "calls.log"
    call_log.write_text("", encoding="utf-8")

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["CALL_LOG"] = str(call_log)
    env["FAIL_ON_CALLS"] = fail_on_calls

    proc = subprocess.run(
        ["make", *(make_args or []), "test-full"],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    calls = [line for line in call_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    return proc.returncode, calls


def _run_live(tmp_path: Path, fail_on_calls: str) -> tuple[int, list[str]]:
    if _MARKER_FILE.exists():
        _MARKER_FILE.unlink()
    try:
        return _run_make_test_full(tmp_path, fail_on_calls, cwd=gc.REPO_ROOT)
    finally:
        if _MARKER_FILE.exists():
            _MARKER_FILE.unlink()


@pytest.mark.parametrize("fail_on_calls", ["1", "2", "3"])
def test_full_runs_every_pass_and_reds_when_any_pass_fails_live(tmp_path: Path, fail_on_calls: str) -> None:
    returncode, calls = _run_live(tmp_path, fail_on_calls)
    assert len(calls) == 3, f"expected all 3 test-full passes to run (uv invoked 3x), got {calls}"
    assert all(call.startswith("run --frozen pytest ") for call in calls)
    assert returncode != 0, "test-full must exit non-zero when any pass fails"


def test_full_exits_zero_and_leaves_no_marker_when_every_pass_passes_live(tmp_path: Path) -> None:
    returncode, calls = _run_live(tmp_path, "")
    assert len(calls) == 3, f"expected all 3 test-full passes to run (uv invoked 3x), got {calls}"
    assert returncode == 0
    assert not _MARKER_FILE.exists(), "test-full must not leave its status marker behind on success"


def test_faultinjection_reintroduced_failfast_is_caught_by_this_harness(tmp_path: Path) -> None:
    """Sanity: a Makefile missing the first pass's ``|| touch`` guard — the
    exact regression #340 warns about — stops after one ``uv`` call instead
    of three, proving the live tests above would actually catch it.
    """
    makefile = tmp_path / "Makefile"
    makefile.write_text(_REGRESSED_MAKEFILE, encoding="utf-8")

    returncode, calls = _run_make_test_full(tmp_path, "1", cwd=tmp_path, make_args=["-f", str(makefile)])

    assert len(calls) == 1, f"regressed (fail-fast) Makefile should stop after the first failing pass, got {calls}"
    assert returncode != 0
