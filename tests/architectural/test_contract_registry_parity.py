"""WP03 — parity proof: the advisory Contract-Registry sweep SUBSUMES the
detection of the merge-blocking ``test_no_legacy_*`` gates, WITHOUT retiring them.

Mission ``contract-ownership-boundary-01KWYRE5`` (#2441 / FR-006, NFR-001,
NFR-004). Depends on WP01 (the seeded registry records) and WP02 (the advisory
``sweep_record`` / :class:`Finding` driver).

What this proves — and, deliberately, what it does NOT touch
------------------------------------------------------------
This file only **proves parity**. It removes / neuters / converts **nothing**.
The two enforcing gates it measures against —

* ``tests/architectural/test_no_legacy_terminology.py``
  ::``test_forbidden_term_does_not_appear`` (``pytest.fail`` on a live
  ``git grep`` hit — merge-blocking today), and
* ``tests/audit/test_no_legacy_path_literals.py``
  ::``test_no_legacy_path_literals_in_cli_commands`` (a hard ``assert`` on a
  CLI-tree literal grep — merge-blocking today)

— are left byte-for-byte unchanged (NFR-004: retiring a blocking gate behind an
advisory driver silently downgrades enforcement, the exact anti-pattern this
mission forbids). The delete-the-assertion retirement is a deferred follow-up
that needs an enforcing driver mode; this WP does not do it.

The driver's detection relationship to the gates: a SUPERSET
------------------------------------------------------------
The advisory driver walks ``rglob("*")`` over ALL files and substring-matches
EVERY line; the enforcing CLI-path gate scans only ``*.py`` and SKIPS comment
lines. So the driver's detection is a **superset** of the gate's — it preserves
all the gate's coverage (NFR-001) AND additionally over-flags comment-line /
non-``.py`` mentions the gate carves out (an advisory-safe over-flag, since the
driver never blocks — NFR-002). Set-equality therefore holds only over a
**curated divergence-free envelope** (non-comment lines in in-scope ``.py``
files); Proof 4 pins the strict-superset relationship (``driver ⊋ gate``) on a
comment-line input. Modeling the gate's comment-skip + ``.py``-scoping in the
driver is a deferred prerequisite to any enforcing flip (Follow-up: #2441) — NOT
done here: this MVP stays additive and the carve-out belongs to that follow-up.

Four independent proofs
-----------------------
1. **Set-equality over a shared fabricated tree — within the divergence-free
   envelope** (NOT the over-flag-blind "both catch one violation" — a trivially
   over-flagging driver would pass that). Each fabricated tree carries BOTH
   planted violations (on NON-comment lines in in-scope ``.py`` files) AND a
   benign-but-identical control living just outside the record's declared
   envelope: an exempted ``docs/adr/`` path for the terminology record, and a
   path outside the ``src/specify_cli/cli`` scan root for the path-literal
   record. The driver's detection set and the enforcing gate's detection set are
   asserted **equal** over that same tree, with the benign control in NEITHER
   set — which rules out an off-envelope over-flag and proves the
   ``scan_roots``-minus-``exemptions`` envelope actually matches. This is
   set-equality over the divergence-free envelope, NOT global exactness (Proof 4).

2. **The old sweep runs against the fabricated tree — not a fakeable source
   grep.** The enforcing sweeps have no injection seam
   (``test_no_legacy_terminology`` hardcodes ``_repo_root()``; the path grep
   hardcodes a ``src/specify_cli/cli`` root off ``__file__``). So the
   terminology parity retargets the gate's OWN ``_grep_for`` at a fabricated git
   repo (the only seam touched is the tree root; the ``git grep`` command, the
   ``--fixed-strings`` matching, ``_SCAN_ROOTS`` and the ``_line_is_excluded``
   exclusion are the gate's unmodified code), and the path parity applies the
   gate's OWN ``LITERAL`` / ``COMMENT`` regexes to a fabricated CLI tree.
   Neither proof greps this repo for the string ``pytest.fail`` — that would be
   fakeable and prove nothing.

3. **The enforcing gates still BLOCK.** Each gate's REAL file is copied verbatim
   into a fabricated repo and executed under a pytest subprocess: a planted
   violation must exit non-zero (the gate fires) and a benign-only tree must
   exit zero (no over-block). If a future change neuters a gate (turns
   ``pytest.fail`` into a warning, drops the ``assert``, renames the test), the
   planted subprocess stops exiting non-zero and reds THIS test.

4. **The driver is a STRICT superset of the CLI-path gate — the comment-line
   control.** On one fabricated CLI tree, a NON-comment literal is caught by BOTH
   (the gate's coverage is preserved — NFR-001) while a COMMENT-line literal
   inside the scan root is flagged ONLY by the driver (the gate's documented
   comment-skip carve-out). So ``driver ⊋ gate``: an advisory-safe over-flag, not
   exact parity — matching the live tree, where the driver flags the comment-line
   home literal at ``src/specify_cli/cli/commands/init.py`` and the gate does not.
   Reds if the driver is ever taught the gate's comment-skip without the
   spec/contract superset claim being updated in step.

Self-flag discipline
--------------------
The forbidden terminology terms and the legacy path literals are NEVER embedded
verbatim here — they are read at runtime from the seeded registry records
(:func:`anchor_needles`) and written into ``tmp_path`` fixtures the live gates
never scan. So this parity file cannot trip the very gates it measures
(mirroring ``test_no_legacy_terminology``'s own fragment-construction defence).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from specify_cli.contracts.registry import ContractRecord, load_registry
from tests.architectural import test_no_legacy_terminology as term_gate
from tests.architectural.test_retired_contracts_absent import (
    Finding,
    anchor_needles,
    sweep_record,
)
from tests.audit import test_no_legacy_path_literals as path_gate

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]


# The two ``retired_literal`` records WP01 seeded, one per enforcing gate.
_TERMINOLOGY_RECORD_ID = "terminology.legacy-status-commit-terms"
_PATH_RECORD_ID = "paths.legacy-home-literals-cli-tree"

# Real gate files + the specific merge-blocking test in each (Proof 3 targets).
_TERMINOLOGY_GATE_TEST = "test_forbidden_term_does_not_appear"
_TERMINOLOGY_GATE_REL = "tests/architectural/test_no_legacy_terminology.py"
_PATH_GATE_TEST = "test_no_legacy_path_literals_in_cli_commands"
_PATH_GATE_REL = "tests/audit/test_no_legacy_path_literals.py"

_CLI_SCAN_ROOT = "src/specify_cli/cli"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    """Resolve the repo root by walking up to a ``.kittify/`` marker."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".kittify").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root (no .kittify/ marker found).")


def _record_by_id(record_id: str) -> ContractRecord:
    """Return the seeded registry record with *record_id* (or fail loudly)."""
    for record in load_registry(_repo_root()):
        if record.id == record_id:
            return record
    raise AssertionError(
        f"seeded record {record_id!r} is missing from the Contract Registry — "
        "WP01 must seed it before WP03 can prove parity against it"
    )


def _write(path: Path, text: str) -> None:
    """Create parents and write *text* to *path* (UTF-8)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _copy_gate(src: Path, dest: Path) -> None:
    """Copy an enforcing gate file verbatim to *dest* (Proof 3 runs the REAL file)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)


def _gate_source_file(module: ModuleType) -> Path:
    """The on-disk path of an imported gate *module* (guards the ``str | None`` type)."""
    file = module.__file__
    assert file is not None, f"gate module {module.__name__!r} has no __file__"
    return Path(file)


def _git(root: Path, *args: str) -> None:
    """Run a ``git`` subcommand inside *root* (quiet, checked)."""
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _init_git_repo(root: Path) -> None:
    """``git init`` *root* and track everything — ``git grep`` searches tracked files."""
    _git(root, "init", "-q")
    _git(root, "add", "-A")


def _driver_paths(record: ContractRecord, root: Path) -> set[str]:
    """The driver's detection set: repo-relative POSIX paths ``sweep_record`` flags."""
    findings: list[Finding] = sweep_record(record, root)
    return {finding.path for finding in findings}


def _pytest_env() -> dict[str, str]:
    """A clean child env: drop ``PYTEST_ADDOPTS`` so an inherited ``-m`` / ``-n``
    filter can't deselect the gate under test and mask a real fail/pass as an
    empty (exit-5) run."""
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    return env


def _run_gate_subprocess(gate_file: Path, test_name: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Execute the REAL gate file's *test_name* under a pytest subprocess rooted at *cwd*."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            f"{gate_file}::{test_name}",
            "-p",
            "no:cacheprovider",
            "-q",
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=_pytest_env(),
        check=False,
    )


# ---------------------------------------------------------------------------
# Proof 1 + 2 — terminology: real set-equality via the gate's OWN _grep_for
# ---------------------------------------------------------------------------


def _terminology_gate_paths(
    needles: tuple[str, ...], fab_root: Path, monkeypatch: pytest.MonkeyPatch
) -> set[str]:
    """Detection set of the terminology gate's OWN ``_grep_for`` over *fab_root*.

    The only seam touched is ``_repo_root`` (retargeted at the fabricated git
    repo). The ``git grep`` command, ``--fixed-strings`` matching, ``_SCAN_ROOTS``
    and the ``_line_is_excluded`` exclusion envelope are the gate's unmodified
    code — so the ``docs/adr/`` benign control is judged by the REAL exclusion
    predicate, not a reimplementation.
    """
    monkeypatch.setattr(term_gate, "_repo_root", lambda: fab_root)
    paths: set[str] = set()
    for needle in needles:
        for hit in term_gate._grep_for(needle):
            paths.add(hit.split(":", 1)[0])  # "path:line:content" -> path
    return paths


def test_terminology_driver_matches_enforcing_gate_over_divergence_free_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Driver set == enforcing terminology-gate set over the divergence-free envelope.

    Set-equality holds over a CURATED tree that stays inside the divergence-free
    envelope (in-scope scan roots, non-exempted paths) — NOT a claim of global
    exactness (the driver's global relationship to the gates is a SUPERSET; see
    Proof 4). Two in-envelope planted violations (``src/`` + ``tests/`` scan roots)
    plus one benign-but-identical control inside the exempted ``docs/adr/`` snapshot
    tree. Parity holds iff both detect the planted pair AND both ignore the exempted
    control (proving the exemption envelope matches — no off-envelope over-flag).
    """
    record = _record_by_id(_TERMINOLOGY_RECORD_ID)
    needles = anchor_needles(record)
    assert needles, "terminology record must carry at least one content anchor"
    term = needles[0]  # runtime value — this source never embeds a forbidden term

    planted_a = "src/pkg/alpha.py"
    planted_b = "tests/pkg/beta.py"
    benign = "docs/adr/3.x/2026-01-01-1-historical.md"
    _write(tmp_path / planted_a, f"label = {term!r}\n")
    _write(tmp_path / planted_b, f"note = {term!r}\n")
    _write(tmp_path / benign, f"Historical snapshot quoting {term} verbatim.\n")
    _init_git_repo(tmp_path)

    driver_paths = _driver_paths(record, tmp_path)
    gate_paths = _terminology_gate_paths(needles, tmp_path, monkeypatch)

    # Non-vacuous: both detect the planted violations ...
    assert {planted_a, planted_b} <= driver_paths, driver_paths
    assert {planted_a, planted_b} <= gate_paths, gate_paths
    # ... both ignore the exempted benign occurrence (no over-flag) ...
    assert benign not in driver_paths
    assert benign not in gate_paths
    # ... and the two detection sets are EQUAL over the shared input (real parity).
    assert driver_paths == gate_paths, (
        "driver and enforcing terminology gate disagree over the same fabricated "
        f"tree:\n  driver={sorted(driver_paths)}\n  gate  ={sorted(gate_paths)}"
    )


# ---------------------------------------------------------------------------
# Proof 1 + 2 — path literals: real set-equality via the gate's OWN regexes
# ---------------------------------------------------------------------------


def _path_gate_paths(cli_root: Path, fab_root: Path) -> set[str]:
    """Detection set of the CLI-tree literal gate's OWN ``LITERAL`` / ``COMMENT`` regexes.

    Applies the gate module's real compiled patterns to the fabricated CLI
    subtree — the same ``rglob('*.py')`` walk plus comment-line skip the gate
    itself performs — so the only thing supplied is the fabricated tree root.
    """
    paths: set[str] = set()
    for py in cli_root.rglob("*.py"):
        for line in py.read_text(encoding="utf-8").splitlines():
            if path_gate.COMMENT.match(line):
                continue
            if path_gate.LITERAL.search(line):
                paths.add(py.relative_to(fab_root).as_posix())
    return paths


def test_path_literal_driver_matches_enforcing_gate_over_divergence_free_envelope(
    tmp_path: Path,
) -> None:
    """Driver set == enforcing CLI-path-gate set over the divergence-free envelope.

    Set-equality holds ONLY over a CURATED tree inside the divergence-free envelope
    (non-comment lines in in-scope ``.py`` files) — NOT global exactness. The driver
    over-flags comment-line / non-``.py`` mentions the gate carves out; that
    strict-superset relationship (``driver ⊋ gate``) is pinned separately by
    :func:`test_path_literal_driver_is_superset_over_comment_line` (Proof 4). Here:
    two in-envelope planted violations on NON-comment lines inside the
    ``src/specify_cli/cli`` scan root plus one benign-but-identical control OUTSIDE
    that scan root. Parity holds iff both detect the planted pair AND both ignore
    the out-of-envelope control (proving the scan-root envelope matches — no
    off-envelope over-flag).
    """
    record = _record_by_id(_PATH_RECORD_ID)
    needles = anchor_needles(record)
    assert needles, "path record must carry at least one content anchor"
    literal = needles[0]  # runtime value — this source never embeds the literal

    planted_a = f"{_CLI_SCAN_ROOT}/commands/show.py"
    planted_b = f"{_CLI_SCAN_ROOT}/commands/init.py"
    benign = "src/specify_cli/runtime/foo.py"
    _write(tmp_path / planted_a, f'console.print("config at {literal}/config.toml")\n')
    _write(tmp_path / planted_b, f'typer.echo("home is {literal}")\n')
    _write(tmp_path / benign, f'console.print("legacy home {literal}")\n')

    driver_paths = _driver_paths(record, tmp_path)
    gate_paths = _path_gate_paths(tmp_path / _CLI_SCAN_ROOT, tmp_path)

    assert {planted_a, planted_b} <= driver_paths, driver_paths
    assert {planted_a, planted_b} <= gate_paths, gate_paths
    assert benign not in driver_paths
    assert benign not in gate_paths
    assert driver_paths == gate_paths, (
        "driver and enforcing CLI-path gate disagree over the same fabricated "
        f"tree:\n  driver={sorted(driver_paths)}\n  gate  ={sorted(gate_paths)}"
    )


# ---------------------------------------------------------------------------
# Proof 4 — the driver is a STRICT superset of the CLI-path gate (comment-line)
# ---------------------------------------------------------------------------


def test_path_literal_driver_is_superset_over_comment_line(tmp_path: Path) -> None:
    """The advisory driver is a STRICT superset of the enforcing CLI-path gate.

    On ONE fabricated CLI tree, a NON-comment literal is caught by BOTH — the
    gate's coverage is preserved (NFR-001) — while a COMMENT-line literal inside
    the ``src/specify_cli/cli`` scan root is flagged ONLY by the driver (the gate's
    documented comment-skip carve-out: ``test_no_legacy_path_literals.py``'s
    ``COMMENT.match`` skip). So the gate's detection set is a STRICT subset of the
    driver's: ``driver ⊋ gate`` — an advisory-safe over-flag, NOT the
    "exactly / set-equality" the artifacts once claimed. This mirrors the live
    tree, where the driver over-flags the comment-line home literal in
    ``src/specify_cli/cli/commands/init.py`` that the gate deliberately skips.

    Guards the corrected superset claim two ways: it reds today if the driver
    stopped over-flagging the comment line (the strict-subset assertion fails), and
    it reds if the driver were later taught the gate's comment-skip WITHOUT the
    spec/contract superset wording being updated in step — forcing the claim and
    the code to move together before any enforcing flip (deferred #2441 follow-up).

    Self-flag discipline: the literal is a runtime value (``anchor_needles``),
    never embedded verbatim, and is written only into ``tmp_path`` the live gates
    never scan — so this control cannot trip the very gate it measures.
    """
    record = _record_by_id(_PATH_RECORD_ID)
    needles = anchor_needles(record)
    assert needles, "path record must carry at least one content anchor"
    literal = needles[0]  # runtime value — this source never embeds the literal

    shared = f"{_CLI_SCAN_ROOT}/commands/show.py"  # non-comment line: caught by BOTH
    comment_only = f"{_CLI_SCAN_ROOT}/commands/legacy_note.py"  # comment line: DRIVER only
    _write(tmp_path / shared, f'console.print("home is {literal}")\n')
    _write(tmp_path / comment_only, f"# legacy default home was {literal}\n")

    driver_paths = _driver_paths(record, tmp_path)
    gate_paths = _path_gate_paths(tmp_path / _CLI_SCAN_ROOT, tmp_path)

    # Shared coverage: the non-comment literal is in BOTH sets (NFR-001 preserved).
    assert shared in driver_paths, driver_paths
    assert shared in gate_paths, gate_paths
    # Divergence: the comment-line literal is flagged ONLY by the advisory driver ...
    assert comment_only in driver_paths, driver_paths
    assert comment_only not in gate_paths, gate_paths
    # ... so the enforcing gate's set is a STRICT subset of the driver's:
    # driver ⊋ gate (advisory-safe over-flag, not exact parity).
    assert gate_paths < driver_paths, (
        "expected the enforcing CLI-path gate's detection set to be a STRICT subset "
        f"of the advisory driver's (driver ⊋ gate):\n  driver={sorted(driver_paths)}"
        f"\n  gate  ={sorted(gate_paths)}"
    )


# ---------------------------------------------------------------------------
# Proof 3 — the enforcing gates still BLOCK (REAL gate file, pytest subprocess)
# ---------------------------------------------------------------------------


def test_terminology_gate_still_blocks_planted_and_passes_benign(tmp_path: Path) -> None:
    """The REAL terminology gate exits non-zero on a planted violation, zero on benign.

    Reds if a future change neuters the gate (``pytest.fail`` -> warning, or the
    test is dropped/renamed): the planted subprocess would stop failing.
    """
    record = _record_by_id(_TERMINOLOGY_RECORD_ID)
    term = anchor_needles(record)[0]
    gate_src = _gate_source_file(term_gate)

    # (a) Planted violation in src/ -> the gate must FIRE (test fails, exit 1).
    planted = tmp_path / "planted"
    (planted / ".kittify").mkdir(parents=True)
    _write(planted / "src/pkg/mod.py", f"value = {term!r}\n")
    _copy_gate(gate_src, planted / _TERMINOLOGY_GATE_REL)
    _init_git_repo(planted)
    fired = _run_gate_subprocess(planted / _TERMINOLOGY_GATE_REL, _TERMINOLOGY_GATE_TEST, planted)
    assert fired.returncode == 1, (
        "enforcing terminology gate did NOT fail on a planted violation — it may "
        f"have been neutered (NFR-004 regression).\n"
        f"exit={fired.returncode}\nstdout:\n{fired.stdout}\nstderr:\n{fired.stderr}"
    )

    # (b) Same term ONLY inside the exempted docs/adr/ tree -> the gate must PASS.
    benign = tmp_path / "benign"
    (benign / ".kittify").mkdir(parents=True)
    _write(benign / "docs/adr/3.x/2026-01-01-1-historical.md", f"quotes {term} as history\n")
    _copy_gate(gate_src, benign / _TERMINOLOGY_GATE_REL)
    _init_git_repo(benign)
    clean = _run_gate_subprocess(benign / _TERMINOLOGY_GATE_REL, _TERMINOLOGY_GATE_TEST, benign)
    assert clean.returncode == 0, (
        "enforcing terminology gate over-blocked a benign exempted occurrence.\n"
        f"exit={clean.returncode}\nstdout:\n{clean.stdout}\nstderr:\n{clean.stderr}"
    )


def test_path_gate_still_blocks_planted_and_passes_benign(tmp_path: Path) -> None:
    """The REAL CLI-path gate exits non-zero on a planted literal, zero on a comment.

    Reds if a future change neuters the gate (drops the ``assert``, or the test is
    dropped/renamed): the planted subprocess would stop failing.
    """
    record = _record_by_id(_PATH_RECORD_ID)
    literal = anchor_needles(record)[0]
    gate_src = _gate_source_file(path_gate)
    show = f"{_CLI_SCAN_ROOT}/commands/show.py"

    # (a) Literal on a NON-comment line in the CLI tree -> the gate must FIRE.
    planted = tmp_path / "planted"
    _write(planted / show, f'console.print("home {literal}")\n')
    _copy_gate(gate_src, planted / _PATH_GATE_REL)
    fired = _run_gate_subprocess(planted / _PATH_GATE_REL, _PATH_GATE_TEST, planted)
    assert fired.returncode == 1, (
        "enforcing CLI-path gate did NOT fail on a planted literal — it may have "
        f"been neutered (NFR-004 regression).\n"
        f"exit={fired.returncode}\nstdout:\n{fired.stdout}\nstderr:\n{fired.stderr}"
    )

    # (b) Same literal only on a COMMENT line -> the gate's comment carve-out PASSES.
    benign = tmp_path / "benign"
    _write(benign / show, f"# legacy default was {literal}\n")
    _copy_gate(gate_src, benign / _PATH_GATE_REL)
    clean = _run_gate_subprocess(benign / _PATH_GATE_REL, _PATH_GATE_TEST, benign)
    assert clean.returncode == 0, (
        "enforcing CLI-path gate over-blocked a comment-line occurrence (its "
        f"documented carve-out).\n"
        f"exit={clean.returncode}\nstdout:\n{clean.stdout}\nstderr:\n{clean.stderr}"
    )
