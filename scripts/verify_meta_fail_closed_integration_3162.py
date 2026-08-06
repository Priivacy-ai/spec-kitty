#!/usr/bin/env python3
"""Re-derive mission ``meta-fail-closed-3162-01KZ7FSQ``'s integration counts.

WP08 / T049 step 9. This is the re-runnable form of the integration verdict: a
reviewer gets every number in ``contracts/integration-verification.md`` §5 from
**one** command instead of reconstructing it from prose.

**It authors no second way to count.** ``NFR-002``'s kept clause forbids a
second predicate answering one question, so every count below is delegated to
``scripts/verify_meta_routing_manifest_3162.py`` (WP01's verifier) and to the
gate's own AST scanners in ``tests/architectural/test_inline_meta_read_gate.py``.
This script composes them and adds only what WP01's verifier does not report:
``SC-006``'s **two** deltas, separated (widening vs code), and an explicit
control for the ``_rel()`` relocation trap described below.

**The ``_rel()`` relocation trap (why the inline exclusion is restated here).**
``test_inline_meta_read_gate._rel`` (``:424``) makes paths relative to
``_REPO_ROOT``, derived from the **gate file's own** ``__file__`` -- not from the
``src_root`` argument. ``EXCLUDED_REL_PATHS`` (``:75``) is matched against that
value, so scanning a relocated tree silently stops excluding
``mission_metadata.py`` and the inline census reads **+1** too high. Measured:
8 on a ``git archive`` copy where the real tree reports 7. This script therefore
matches the exclusion by **path suffix**, which survives relocation, and prints
the known-answer control proving the corrected probe reproduces the real tree's
figure.

Usage::

    scripts/verify_meta_fail_closed_integration_3162.py [TREE_ROOT] [--no-deltas]

Exits non-zero when a live count falls outside the band derived from the floors
read off the measured tree.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_REL = "scripts/verify_meta_routing_manifest_3162.py"
GATE_REL = "tests/architectural/test_inline_meta_read_gate.py"
CENSUS_REL = "tests/specify_cli/test_meta_fail_closed_full_census_contract.py"
RATCHET_REL = "tests/architectural/_ratchet_keys.py"

#: ``git merge-base HEAD main``. NOT ``upstream/main``'s tip -- that ref carries
#: commits this branch never had and is the wrong ref for attribution.
BASELINE_REF = "96494e5ec"

#: ``EXCLUDED_REL_PATHS`` (gate ``:75``) restated as suffixes so the exclusion
#: survives tree relocation. See the ``_rel()`` trap in the module docstring.
EXCLUDED_SUFFIXES = (
    "src/specify_cli/mission_metadata.py",
    "src/specify_cli/task_utils/support.py",
)

RULE = "=" * 78


def _load_module(name: str, path: Path) -> ModuleType:
    """Import *path* under *name* without requiring it to be on ``sys.path``."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        msg = f"cannot load {path}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _print_environment(tree_root: Path) -> None:
    print(RULE)
    print("verify_meta_fail_closed_integration_3162 — mission meta-fail-closed-3162-01KZ7FSQ")
    print(RULE)
    print(f"TREE measured : {tree_root}")
    print(f"SRC_ROOT      : {tree_root / 'src'}")
    print(f"PYTHONPATH    : {os.environ.get('PYTHONPATH') or '<unset>'}")
    print(f"sys.executable: {sys.executable}")
    print(f"baseline ref  : {BASELINE_REF} (git merge-base HEAD main)")
    if tree_root != REPO_ROOT:
        print(f"NOTE          : measuring a tree OTHER than this script's root {REPO_ROOT}")


def _corrected_inline_sites(gate: ModuleType, src_root: Path) -> list[object]:
    """Inline sites with the exclusion applied by suffix (relocation-proof)."""
    sites = gate.scan_inline_meta_reads(src_root)
    return [
        site
        for site in sites
        if not any(site.rel_path.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)
    ]


def _report_counts(manifest: ModuleType, gate: ModuleType, tree_root: Path) -> tuple[int, int, dict[str, int]]:
    src_root = tree_root / "src"
    consts = manifest.gate_constants(tree_root / GATE_REL)
    walked = len(manifest.python_files(src_root))
    routed = len(gate.scan_routed_load_meta_calls(src_root))
    inline_raw = len(gate.scan_inline_meta_reads(src_root))
    inline = len(_corrected_inline_sites(gate, src_root))
    low, high = manifest.routed_band(consts)

    print("== LIVE COUNTS (the gate's own AST scanners; no second predicate) ==")
    print(f"  INPUT .py files walked        : {walked}")
    print(f"  ROUTED live (AST walk)        : {routed}")
    print(f"  INLINE live, exclusion by suffix: {inline}")
    print(f"  INLINE live, gate's own _rel()  : {inline_raw}"
          f"{'   <-- RELOCATED: _rel() trap, see docstring' if inline_raw != inline else ''}")
    for name in ("INLINE_META_READ_FLOOR", "FLOOR_MARGIN",
                 "ROUTED_LOAD_META_FLOOR", "ROUTED_LOAD_META_FLOOR_MARGIN"):
        print(f"  const {name} = {consts[name]}")
    floor = consts["ROUTED_LOAD_META_FLOOR"]
    print(f"  DERIVED routed band           : [{low}, {high}] (two-sided; {floor} is RED)")
    return routed, inline, consts


def _report_ledger(manifest: ModuleType, tree_root: Path) -> int:
    census_path = tree_root / CENSUS_REL
    rows = manifest.ledger_pending_rows(census_path)
    candidates = manifest.pending_grep_lines(census_path)
    legend = manifest.legend_lines(census_path, rows)
    print("== LEDGER `pending-batch-a` ROWS (baseline was 12 rows / 13 candidates) ==")
    print(f"  grep -c 'pending-batch-a' candidates in : {len(candidates)}")
    print(f"  legend/prose hits dropped              : {len(legend)} at line(s) {legend}")
    print(f"  ledger ROWS out                        : {len(rows)}")
    print(f"  DELTA                                  : 12 -> {len(rows)}")
    return len(rows)


def _archive_src(tree_root: Path, ref: str, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "-C", str(tree_root), "archive", ref, "src"],
        check=True, capture_output=True,
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    return dest / "src"


def _gate_at_ref(tree_root: Path, ref: str, dest: Path, name: str) -> ModuleType:
    dest.mkdir(parents=True, exist_ok=True)
    text = subprocess.run(
        ["git", "-C", str(tree_root), "show", f"{ref}:{GATE_REL}"],
        check=True, capture_output=True, text=True,
    ).stdout
    path = dest / "gate.py"
    path.write_text(text, encoding="utf-8")
    return _load_module(name, path)


def _report_deltas(tree_root: Path) -> None:
    """``SC-006``'s TWO deltas, as a 2x2. One number cannot separate them."""
    print("== SC-006 — the TWO deltas, measured as a 2x2 (predicate x tree) ==")
    shared = subprocess.run(
        ["git", "-C", str(tree_root), "diff", "--stat", f"{BASELINE_REF}..HEAD", "--", RATCHET_REL],
        check=False, capture_output=True, text=True,
    ).stdout.strip()
    print(f"  control: shared helper {RATCHET_REL} changed in-branch? "
          f"{'YES — CONFOUND' if shared else 'no (byte-identical; sharing it is sound)'}")

    if str(tree_root) not in sys.path:
        sys.path.insert(0, str(tree_root))
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        gates = {
            "BASE": _gate_at_ref(tree_root, BASELINE_REF, tmp / "gate_base", "_g3162_base"),
            "HEAD": _gate_at_ref(tree_root, "HEAD", tmp / "gate_head", "_g3162_head"),
        }
        trees = {
            "BASE": _archive_src(tree_root, BASELINE_REF, tmp / "src_base"),
            "HEAD": _archive_src(tree_root, "HEAD", tmp / "src_head"),
        }
        cell = {
            (g, t): len(_corrected_inline_sites(gates[g], trees[t]))
            for g in gates
            for t in trees
        }
        live = len(_corrected_inline_sites(gates["HEAD"], tree_root / "src"))
        ok = cell[("HEAD", "HEAD")] == live
        print(f"  CONTROL known answer: corrected(HEAD,HEAD)={cell[('HEAD', 'HEAD')]} vs "
              f"live tree={live} -> {'PASS' if ok else 'FAIL (do not trust the deltas)'}")
        print(f"  {'':>16}{'tree=BASE':>11}{'tree=HEAD':>11}")
        for g in ("BASE", "HEAD"):
            print(f"  predicate={g:<6}{cell[(g, 'BASE')]:>11}{cell[(g, 'HEAD')]:>11}")
        wide = cell[("HEAD", "BASE")] - cell[("BASE", "BASE")]
        code = cell[("HEAD", "HEAD")] - cell[("HEAD", "BASE")]
        print(f"  WIDENING delta (predicate BASE->HEAD, tree fixed at BASE): {wide:+d}")
        print(f"  CODE     delta (tree BASE->HEAD, predicate fixed at HEAD): {code:+d}")
        print("  Reported as TWO numbers: one cannot distinguish 'the widening found a")
        print("  real site' from 'a new unrouted read landed'. They cancel here.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree_root", nargs="?", default=str(REPO_ROOT),
                        help="tree to measure (default: this script's repository root)")
    parser.add_argument("--no-deltas", action="store_true",
                        help="skip the SC-006 2x2 (which needs git history)")
    args = parser.parse_args(argv)
    tree_root = Path(args.tree_root).resolve()

    _print_environment(tree_root)
    manifest = _load_module("_manifest3162", tree_root / MANIFEST_REL)
    gate = manifest.import_gate(tree_root)

    routed, inline, consts = _report_counts(manifest, gate, tree_root)
    _report_ledger(manifest, tree_root)
    if not args.no_deltas:
        _report_deltas(tree_root)

    ok = manifest.check_bounds(routed, inline, consts)
    print(RULE)
    print(f"VERDICT: {'PASS' if ok else 'FAIL'}")
    print(RULE)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
