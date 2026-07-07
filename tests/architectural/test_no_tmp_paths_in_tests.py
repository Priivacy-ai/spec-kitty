"""Hard gate: no shared-temp-directory path literal in test files (see
``_TMP_LITERAL`` below) may appear anywhere under ``tests/`` (mission
``tmp-literal-offender-burndown-01KWWRW2``, closes #1842).

Background
----------
PR #2181 landed a frozen-baseline ratchet (mission
``single-authority-resolution-gates-01KW1P0F``, FR-007/WP07) that prevented
NEW occurrences of the literal from being introduced into test files, while
grandfathering ~98 existing offenders into
``tests/architectural/tmp_ratchet_baseline.txt`` and deferring their
remediation to this issue. All grandfathered files have since been converted
off the literal (category-A leaks routed through ``tmp_path``/fixtures with
teardown; category-B path-literals replaced with non-shared-temp-dir absolute
sentinels) — the baseline is now empty and this file enforces a genuine hard
gate: an empty baseline is the only healthy state, not a floor to clear.

Gate semantics
--------------
* Any ``.py`` file under ``tests/`` that contains the literal tracked by
  ``_TMP_LITERAL`` (a leading slash, ``tmp``, trailing slash) causes this
  gate to FAIL — no baseline entries, no grandfathering.
* ``tmp_ratchet_baseline.txt`` is retained as an empty, comment-header-only
  file so a future accidental re-population is visible in review;
  ``test_baseline_is_empty`` guards against it silently regrowing (FR-003) —
  a still-populated baseline would yield 0 violations for every listed file
  and pass every other test in this module while quietly re-grandfathering it.
* This gate file is itself scanned by the walk below, so the needle and the
  self-test payload are string-fragment-constructed rather than written as
  bare literals (mirroring the precedent ``test_no_legacy_terminology.py``).
  Fragment-constructing only the needle while leaving prose occurrences as
  bare literals would let this file's own tests pass green while a raw
  substring scan of the file still finds matches elsewhere in it — a
  split-brain false-green. ``test_gate_file_itself_is_literal_free`` proves
  the whole file is clean, independent of ``_collect_violations``'s
  (secondary, belt-and-suspenders) ``__file__`` self-exclude.

Self-mutation proof (T034 — NFR-002 / SC-006)
----------------------------------------------
``test_ratchet_blocks_new_tmp_literal`` injects the literal into a scratch
file outside ``tests/`` and verifies that ``scan_file_for_tmp_literal``
detects it. The file is NOT in the baseline, so the ratchet logic would flag
it. After the fixture tears down the scratch file the helper returns no
matches — proving the gate recovers correctly.

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

Known limitations (follow-up: #2441)
--------------------------------------
This gate is a *substring* gate; it cannot police shared-temp writes that
arrive via runtime resolution rather than source literals.  Two categories
escape detection:

* ``tempfile.gettempdir()`` and ``tempfile.mkdtemp()`` (without immediate
  teardown or a ``with``-context) resolve to the system temp directory at
  runtime — the exact shared, world-writable location this gate exists to
  eliminate — but carry no ``/tmp`` + ``/`` substring in source and sail through
  ``test_no_new_tmp_literals_in_tests``.  Pre-existing uses exist in-tree
  (e.g. ``tests/agent/test_workflow_feedback_pointer_2x_unit.py``).
* Evasion literals assembled via ``os.path.join`` or string concatenation
  (not a single quoted literal) are not caught by
  ``_line_has_evasion_root_literal``.

Closing the class by construction requires AST-level detection.  Any
addition of ``tempfile.gettempdir()`` / ``mkdtemp()`` to test code should
route through a ``tmp_path``-backed fixture instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TESTS_ROOT = _REPO_ROOT / "tests"
_BASELINE_FILE = Path(__file__).resolve().parent / "tmp_ratchet_baseline.txt"
_SELF_PATH = Path(__file__).resolve()

# Fragment-constructed so this module does not itself contain the literal it
# polices (see the module docstring's self-reference-trap note above).
_TMP_LITERAL = "/" + "tmp" + "/"

# Substring-evasion vectors (FR-007): swapping the shared-temp literal for
# another shared, world-writable path still leaks state between runs — it
# merely dodges the ratchet above. ``/var/`` + ``tmp/`` is split across two
# fragments so this line does not itself contain the ``_TMP_LITERAL`` needle.
_EVASION_LITERALS: tuple[str, ...] = (
    "/dev/shm/",
    "/scratch/",
    "/var/" + "tmp/",
)


# ---------------------------------------------------------------------------
# Public helper — extracted for direct testability (Sonar S3776 / T034 DoD)
# ---------------------------------------------------------------------------


def scan_file_for_tmp_literal(path: Path) -> list[int]:
    """Return a sorted list of 1-based line numbers in *path* that contain the literal.

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
    """Load the frozen baseline as a frozenset of relative-path strings.

    Blank lines and ``#``-prefixed comment lines (e.g. the empty-baseline
    header) are ignored — only genuine path entries count as members.
    """
    text = _BASELINE_FILE.read_text(encoding="utf-8")
    return frozenset(
        line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")
    )


def _collect_violations(
    baseline: frozenset[str],
    *,
    tests_root: Path | None = None,
    repo_root: Path | None = None,
) -> list[tuple[str, list[int]]]:
    """Walk *tests_root* and return (rel_path, offending_line_numbers) for every
    non-baseline file that contains the literal.

    *tests_root*/*repo_root* default to the real repo tree but are injectable
    so a test can point this at a seeded synthetic tree instead of
    monkeypatching module globals (FR-006's "cleanest" option). This gate
    file is always excluded from the walk — belt-and-suspenders (secondary;
    the primary defense is that this file no longer contains the literal at
    all — see ``test_gate_file_itself_is_literal_free``).
    """
    root = repo_root if repo_root is not None else _REPO_ROOT
    scan_root = tests_root if tests_root is not None else _TESTS_ROOT
    violations: list[tuple[str, list[int]]] = []
    for py_file in sorted(scan_root.rglob("*.py")):
        if py_file.resolve() == _SELF_PATH:
            continue
        rel = py_file.relative_to(root).as_posix()
        if rel in baseline:
            continue
        hits = scan_file_for_tmp_literal(py_file)
        if hits:
            violations.append((rel, hits))
    return violations


# ---------------------------------------------------------------------------
# Gate tests
# ---------------------------------------------------------------------------


def test_baseline_is_empty() -> None:
    """FR-003: the frozen baseline must be empty — the hard-gate healthy state.

    A still-populated baseline yields 0 violations for every listed file and
    passes every other test in this module while silently re-grandfathering
    it; this guard exists so that class of false-green cannot recur. If a
    residual entry is ever genuinely unconvertible, C-003 requires it stay
    documented with a rationale — narrow this assertion deliberately, do not
    just delete it to force green.
    """
    baseline = _load_baseline()
    assert baseline == frozenset(), (
        f"tmp_ratchet_baseline.txt is no longer empty — entries: {sorted(baseline)}. "
        "Mission tmp-literal-offender-burndown-01KWWRW2 converted every grandfathered "
        "offender off the literal; re-adding an entry silently re-grandfathers a file "
        "unless documented with a C-003 rationale."
    )


def test_no_new_tmp_literals_in_tests() -> None:
    """No test file under ``tests/`` may contain the shared-temp-directory literal.

    With the baseline empty (see ``test_baseline_is_empty``) this is a true
    hard gate: any file that contains the literal fails the build —
    grandfathering is no longer available.
    """
    baseline = _load_baseline()
    violations = _collect_violations(baseline)
    if violations:
        lines = []
        for rel, hits in violations:
            hit_str = ", ".join(str(n) for n in hits)
            lines.append(f"  {rel}  (lines: {hit_str})")
        raise AssertionError(
            "Shared-temp-directory path literals detected in test files.\n"
            "Route the write through tmp_path/a teardown fixture (category A) or replace\n"
            "the bare path with a non-shared-temp-dir absolute sentinel (category B) — see\n"
            "FR-001/FR-002 of kitty-specs/tmp-literal-offender-burndown-01KWWRW2/spec.md.\n"
            "Offending files:\n" + "\n".join(lines)
        )


def test_gate_file_itself_is_literal_free() -> None:
    """FR-004 acceptance: this gate file is itself genuinely free of the literal it polices.

    Scans this exact file directly with the same line-scanner SC-001's raw
    grep enforces — no grep ``--exclude`` escape hatch, and independent of
    ``_collect_violations``'s ``__file__`` self-exclude (that exclude is
    secondary belt-and-suspenders; this test is the primary proof of
    literal-freedom — see the module docstring's self-reference-trap note).
    """
    hits = scan_file_for_tmp_literal(_SELF_PATH)
    assert hits == [], (
        "This gate file must not contain the raw literal it polices anywhere — "
        f"fragment-construct any needle/payload instead of writing it directly. Found matches at line(s): {hits}"
    )


def test_collect_violations_flags_synthetic_offender_with_empty_baseline(
    tmp_path: Path,
) -> None:
    """FR-006: the positive self-test — proven via the REAL gate path.

    ``_collect_violations`` normally walks the repo ``tests/`` root, so a
    plain pytest ``tmp_path`` offender is invisible to it. This seeds a
    synthetic ``tests/`` tree under ``tmp_path`` and points
    ``_collect_violations`` at it via the injectable ``tests_root``/
    ``repo_root`` parameters, proving the empty-baseline gate path itself —
    not ``scan_file_for_tmp_literal``, which would bypass the baseline-skip/
    walk logic this test exists to cover.
    """
    scratch_tests = tmp_path / "tests"
    scratch_tests.mkdir()
    offender = scratch_tests / "test_synthetic_offender.py"
    offender.write_text(f"x = '{_TMP_LITERAL}something'\n", encoding="utf-8")

    violations = _collect_violations(frozenset(), tests_root=scratch_tests, repo_root=tmp_path)
    assert violations == [("tests/test_synthetic_offender.py", [1])], f"Expected the synthetic offender to be flagged, got: {violations}"

    offender.unlink()
    violations_after = _collect_violations(frozenset(), tests_root=scratch_tests, repo_root=tmp_path)
    assert violations_after == [], f"Expected zero violations once the offender is removed, got: {violations_after}"


def _line_has_evasion_root_literal(line: str) -> str | None:
    """Return the matched evasion literal if *line* uses it as an absolute-path root.

    Anchored on the literal appearing immediately after a quote character
    (``"/dev/shm/...`` or ``'/dev/shm/...``) — the exact shape a converted
    category-B path-literal takes (e.g. a shared-temp-directory config path
    becoming ``Path("/dev/shm/config.toml")``). A bare substring scan would also flag
    unrelated relative paths that merely happen to contain one of these
    segment names (e.g. a git worktree literally named ``scratch``, as in
    ``".worktrees/scratch/"`` — not a temp-directory evasion at all).
    """
    for literal in _EVASION_LITERALS:
        if f'"{literal}' in line or f"'{literal}" in line:
            return literal
    return None


def test_no_evasion_vector_literals_in_tests() -> None:
    """FR-007: a category-A fix must be genuine isolation, not a literal swap.

    Swapping the shared-temp literal for another shared, world-writable path
    — a dev-shm mount, a scratch directory, or the var-tmp variant — still
    leaks state between runs; it merely dodges the substring this gate
    polices. Reds if any test file adopts one of these evasion vectors as an
    absolute-path-literal root.
    """
    violations: list[tuple[str, str, int]] = []
    for py_file in sorted(_TESTS_ROOT.rglob("*.py")):
        if py_file.resolve() == _SELF_PATH:
            continue
        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        rel = py_file.relative_to(_REPO_ROOT).as_posix()
        for lineno, line in enumerate(lines, start=1):
            matched = _line_has_evasion_root_literal(line)
            if matched is not None:
                violations.append((rel, matched, lineno))

    assert not violations, (
        "Evasion-vector literal(s) detected — these dodge the shared-temp-directory "
        "ratchet while still leaking shared, world-writable path state:\n"
        + "\n".join(f"  {rel}: {literal!r} (line {lineno})" for rel, literal, lineno in violations)
    )


def test_line_has_evasion_root_literal_positive_and_negative() -> None:
    """FR-007 detector unit proof — pins the positive-match branch.

    ``test_no_evasion_vector_literals_in_tests`` only walks the already-clean
    repo tree, so ``_line_has_evasion_root_literal``'s TRUE branch (line 277)
    never fires under that test.  MUT: replacing the helper with ``return None``
    keeps every other gate test green; this test is the mutation pin (Debbie
    MUT2).
    """
    # Positive: every evasion literal must be detected when quote-preceded.
    for literal in _EVASION_LITERALS:
        assert _line_has_evasion_root_literal(f'x = "{literal}foo"') == literal, (
            f"Expected {literal!r} to be detected in a double-quoted path literal"
        )
        assert _line_has_evasion_root_literal(f"x = '{literal}foo'") == literal, (
            f"Expected {literal!r} to be detected in a single-quoted path literal"
        )
    # Negative: the .worktrees/scratch/ false-positive the docstring claims to avoid.
    assert _line_has_evasion_root_literal('x = ".worktrees/scratch/"') is None
    # Negative: bare substring in a comment must not match (not quote-preceded).
    assert _line_has_evasion_root_literal("# see /dev/shm/ for rationale") is None


# ---------------------------------------------------------------------------
# Self-mutation proof (T034 — NFR-002 / SC-006)
# ---------------------------------------------------------------------------


def test_ratchet_blocks_new_tmp_literal(tmp_path: Path) -> None:
    """Inject the literal into a scratch file outside ``tests/`` and verify detection.

    The scratch file is written to ``tmp_path`` (a pytest-managed temp
    directory outside the repo's ``tests/`` tree), so it is structurally
    distinct from any baseline entry and the ratchet would flag it as a
    violation — this is a pure unit check of the line-scanner, not a
    ``_collect_violations`` walk (see
    ``test_collect_violations_flags_synthetic_offender_with_empty_baseline``
    for that).

    Step 1: Write the literal — helper must detect it (RED assertion).
    Step 2: Delete the file — helper must return empty list (GREEN assertion).
    """
    scratch = tmp_path / "synthetic_offender.py"

    # --- RED: helper detects the literal ---
    payload = f"x = '{_TMP_LITERAL}something'\n"
    scratch.write_text(payload, encoding="utf-8")
    hits = scan_file_for_tmp_literal(scratch)
    assert hits == [1], f"scan_file_for_tmp_literal should have found the literal on line 1, got: {hits}"

    # --- GREEN: file removed, helper returns empty ---
    scratch.unlink()
    hits_after = scan_file_for_tmp_literal(scratch)
    assert hits_after == [], f"scan_file_for_tmp_literal should return [] for a missing file, got: {hits_after}"
