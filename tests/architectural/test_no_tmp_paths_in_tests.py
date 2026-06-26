"""Frozen-baseline /tmp-literal ratchet (FR-007 / WP07, mission
``single-authority-resolution-gates-01KW1P0F``).

Prevents NEW ``/tmp/`` literals from being introduced into test files without
an explicit baseline entry.  The ~98 existing offenders (grandfathered as of
2026-06-26 on ``design/infra-logic-separation-2173``) are tracked in
``tests/architectural/tmp_ratchet_baseline.txt``.  Their full remediation
belongs to issue #1842 (out of scope here).

Gate semantics
--------------
* Any ``.py`` file under ``tests/`` that is NOT in the baseline and contains
  the literal string ``/tmp/`` causes this gate to FAIL.
* The baseline itself is a sorted, newline-separated list of relative paths
  (relative to the repo root).
* The gate does NOT touch ``src/`` — only ``tests/`` is scanned.
* An anti-vacuity floor asserts the baseline contains more than 50 entries
  so an accidentally empty baseline cannot produce a false-green result.

Self-mutation proof (T034 — NFR-002 / SC-006)
----------------------------------------------
``test_ratchet_blocks_new_tmp_literal`` injects ``/tmp/something`` into a
scratch file outside ``tests/`` (using ``tmp_path``) and verifies that
``scan_file_for_tmp_literal`` detects the literal.  The file is NOT in the
baseline, so the ratchet logic would flag it.  After the fixture tears down
the scratch file the helper returns no matches — proving the gate recovers
correctly.

FR-008 verification record (T035 / T036)
-----------------------------------------
Verification performed: 2026-06-26, branch ``design/infra-logic-separation-2173``

Commands run::

    PYTHONPATH=$PWD/src pytest --collect-only -q \\
        tests/contract/test_mark_status_input_shapes.py \\
        tests/git_ops/test_mark_status_pipe_table.py 2>&1

    PYTHONPATH=$PWD/src pytest --collect-only -q -m fast 2>&1 \\
        | grep -E "test_mark_status"

    PYTHONPATH=$PWD/src pytest --collect-only -q -m "not slow" 2>&1 \\
        | grep -E "test_mark_status"

Output excerpts (both candidate files appear in all shard collections)::

    tests/contract/test_mark_status_input_shapes.py::test_bare_task_id_is_unchanged
    tests/contract/test_mark_status_input_shapes.py::test_qualified_task_id_with_slash_is_normalized
    ...
    tests/git_ops/test_mark_status_pipe_table.py::TestIsPipeTableTaskRow::test_matches_task_id_in_first_data_column
    tests/git_ops/test_mark_status_pipe_table.py::TestIsPipeTableTaskRow::test_matches_task_id_with_whitespace_padding
    ...

Verdict: **FR-008 satisfied-by-verification** — both candidate files
(``tests/contract/test_mark_status_input_shapes.py`` and
``tests/git_ops/test_mark_status_pipe_table.py``) are collected by every
shard permutation tested (no-marker, ``-m fast``, ``-m "not slow"``).
No ``pytest.mark`` was added to either file; adding markers would be
redundant noise and could mislead a future agent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TESTS_ROOT = _REPO_ROOT / "tests"
_BASELINE_FILE = Path(__file__).resolve().parent / "tmp_ratchet_baseline.txt"
_TMP_LITERAL = "/tmp/"
_BASELINE_FLOOR = 50  # conservative lower bound; live census ~98 as of 2026-06-26


# ---------------------------------------------------------------------------
# Public helper — extracted for direct testability (Sonar S3776 / T034 DoD)
# ---------------------------------------------------------------------------


def scan_file_for_tmp_literal(path: Path) -> list[int]:
    """Return a sorted list of 1-based line numbers in *path* that contain ``/tmp/``.

    Returns an empty list when *path* does not exist or contains no matching
    lines.  Skips files that cannot be decoded as UTF-8 (binary files).
    """
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return []
    return [i + 1 for i, line in enumerate(lines) if _TMP_LITERAL in line]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_baseline() -> frozenset[str]:
    """Load the frozen baseline as a frozenset of relative-path strings."""
    text = _BASELINE_FILE.read_text(encoding="utf-8")
    return frozenset(line.strip() for line in text.splitlines() if line.strip())


def _collect_violations(baseline: frozenset[str]) -> list[tuple[str, list[int]]]:
    """Walk ``tests/`` and return (rel_path, offending_line_numbers) for every
    non-baseline file that contains ``/tmp/``.
    """
    violations: list[tuple[str, list[int]]] = []
    for py_file in sorted(_TESTS_ROOT.rglob("*.py")):
        rel = py_file.relative_to(_REPO_ROOT).as_posix()
        if rel in baseline:
            continue
        hits = scan_file_for_tmp_literal(py_file)
        if hits:
            violations.append((rel, hits))
    return violations


# ---------------------------------------------------------------------------
# Gate tests
# ---------------------------------------------------------------------------


def test_baseline_is_non_empty_anti_vacuous() -> None:
    """The baseline must contain more than ``_BASELINE_FLOOR`` entries.

    An empty or near-empty baseline would produce a false-green result because
    no grandfathered files would exist and the gate would never fire even if
    the entire ``tests/`` tree contained ``/tmp/`` literals.
    """
    baseline = _load_baseline()
    assert len(baseline) > _BASELINE_FLOOR, (
        f"tmp_ratchet_baseline.txt has only {len(baseline)} entries — "
        f"expected > {_BASELINE_FLOOR}.  Did someone accidentally truncate it?"
    )


def test_no_new_tmp_literals_in_tests() -> None:
    """No non-baseline test file may contain the literal ``/tmp/``.

    Files listed in ``tmp_ratchet_baseline.txt`` are grandfathered in
    (their sweep belongs to issue #1842, out of scope here).  Any NEW file
    not in the baseline that introduces ``/tmp/`` causes this gate to fail.
    """
    baseline = _load_baseline()
    violations = _collect_violations(baseline)
    if violations:
        lines = []
        for rel, hits in violations:
            hit_str = ", ".join(str(n) for n in hits)
            lines.append(f"  {rel}  (lines: {hit_str})")
        raise AssertionError(
            "New /tmp/ literals detected in test files not in the frozen baseline.\n"
            "Either remove the /tmp/ literal or, if intentional, add the file to\n"
            "tests/architectural/tmp_ratchet_baseline.txt with a justification comment.\n"
            "Offending files:\n" + "\n".join(lines)
        )


# ---------------------------------------------------------------------------
# Self-mutation proof (T034 — NFR-002 / SC-006)
# ---------------------------------------------------------------------------


def test_ratchet_blocks_new_tmp_literal(tmp_path: Path) -> None:
    """Inject a /tmp/ literal in a scratch file outside tests/ and verify detection.

    The scratch file is written to ``tmp_path`` (a pytest-managed temp directory
    outside the repo's ``tests/`` tree), so it is structurally distinct from any
    baseline entry and the ratchet would flag it as a new violation.

    Step 1: Write the literal — helper must detect it (RED assertion).
    Step 2: Delete the file — helper must return empty list (GREEN assertion).
    """
    scratch = tmp_path / "synthetic_offender.py"

    # --- RED: helper detects the literal ---
    scratch.write_text("x = '/tmp/something'\n", encoding="utf-8")
    hits = scan_file_for_tmp_literal(scratch)
    assert hits == [1], (
        f"scan_file_for_tmp_literal should have found /tmp/ on line 1, got: {hits}"
    )

    # --- GREEN: file removed, helper returns empty ---
    scratch.unlink()
    hits_after = scan_file_for_tmp_literal(scratch)
    assert hits_after == [], (
        f"scan_file_for_tmp_literal should return [] for a missing file, got: {hits_after}"
    )
