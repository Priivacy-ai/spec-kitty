#!/usr/bin/env python3
"""Regenerate every number in mission 3162's routing manifest.

Deliverable of ``WP01`` (mission ``meta-fail-closed-3162-01KZ7FSQ``). The two
contract documents

* ``kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/routing-manifest.md``
* ``kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/headroom-allocation.md``

quote this script's output next to each count. Run it instead of reconstructing
a command out of prose::

    .venv/bin/python scripts/verify_meta_routing_manifest_3162.py [TREE_ROOT]

``TREE_ROOT`` defaults to the repository root (this file's grandparent), so the
script can be pointed at a lane worktree to take that tree's numbers. It prints
the tree and the ``PYTHONPATH`` it measured, because the editable install's
``.pth`` pins ``specify_cli`` imports to the tree ``.venv`` was installed from
while the gate's ``SRC_ROOT`` is derived from the test file's own location — in
any other tree the AST census and the behavioural imports disagree silently.

Exit status is ``1`` when the live routed count falls outside the band derived
from ``test_routed_load_meta_floor``'s three assertions, when the live inline
count breaches its own ceiling, or when a control does not reproduce its known
answer. A measurement whose control failed is not a measurement.
"""

from __future__ import annotations

import ast
import importlib
import os
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

GATE_REL = "tests/architectural/test_inline_meta_read_gate.py"
CENSUS_REL = "tests/specify_cli/test_meta_fail_closed_full_census_contract.py"
GATE_MODULE = "tests.architectural.test_inline_meta_read_gate"

PENDING_REASON = "pending-batch-a"
TARGET = "load_meta"

GATE_CONSTANTS = (
    "INLINE_META_READ_FLOOR",
    "FLOOR_MARGIN",
    "ROUTED_LOAD_META_FLOOR",
    "ROUTED_LOAD_META_FLOOR_MARGIN",
)

#: Known answers the probes below are controlled against. A probe that does not
#: reproduce its control is reported as FAIL and fails the run.
CONTROL_ROUTED_GREP = 296
CONTROL_ROUTED_AST = 129
CONTROL_EXCEPT_GREP_POP6 = 9
CONTROL_EXCEPT_GREP_POPALL = 10
CONTROL_EXCEPT_AST = 6
CONTROL_ARMS = {"DEGRADE": 4, "REFUSE-raw": 7, "REFUSE-typed": 2}

#: The inherited trap population (the one under which the documented answer of
#: 9 reproduces) is the 9 distinct census files MINUS this one. Retained
#: explicitly so the documented 9 stays reproducible; the fully-derived
#: population (all 9 census files) returns 10 and names a FOURTH spurious hit
#: that no upstream artifact names. Note the inherited population is 8 files,
#: not six -- "the six files" in the WP prompt counts the six HANDLERS, which
#: live in only four files.
POP6_EXCLUDED = "src/specify_cli/bulk_edit/gate.py"

#: Arms known by reading, used to control the AST classifier before the census.
ARM_CONTROL: tuple[tuple[str, str, str], ...] = (
    ("src/specify_cli/core/paths.py", "load_meta_fail_closed", "REFUSE-typed"),
    ("src/specify_cli/mission_metadata.py", "load_meta_or_empty", "REFUSE-raw"),
)


# --------------------------------------------------------------------------- #
# AST helpers
# --------------------------------------------------------------------------- #
def parse(path: Path) -> ast.Module:
    """Parse *path* as Python source."""
    return ast.parse(path.read_text(encoding="utf-8"))


def find_function(tree: ast.Module, qualname: str) -> ast.AST | None:
    """Return the def/class node whose dotted qualname equals *qualname*."""
    hit: list[ast.AST] = []

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qual = f"{prefix}.{child.name}" if prefix else child.name
                if qual == qualname:
                    hit.append(child)
                walk(child, qual)
            else:
                walk(child, prefix)

    walk(tree, "")
    return hit[0] if hit else None


def load_meta_bindings(tree: ast.Module) -> set[str]:
    """Local names in *tree* bound to a ``load_meta`` (import/alias/def)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(a.asname or a.name for a in node.names if a.name == TARGET)
        elif isinstance(node, ast.FunctionDef) and node.name == TARGET:
            names.add(TARGET)
    return names


def load_meta_calls(fn: ast.AST, bindings: set[str]) -> list[ast.Call]:
    """Every ``load_meta`` Call node inside *fn*, in source order."""
    out: list[ast.Call] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Name) and func.id in bindings) or (
            isinstance(func, ast.Attribute) and func.attr == TARGET
        ):
            out.append(node)
    return sorted(out, key=lambda n: n.lineno)


def catches_value_error(handler: ast.ExceptHandler) -> bool:
    """True when *handler* catches ValueError by name, in a tuple, or bare."""
    typ = handler.type
    if typ is None:
        return True
    if isinstance(typ, ast.Name):
        return typ.id == "ValueError"
    if isinstance(typ, ast.Attribute):
        return typ.attr == "ValueError"
    if isinstance(typ, ast.Tuple):
        return any(catches_value_error(ast.ExceptHandler(type=e)) for e in typ.elts)
    return False


# --------------------------------------------------------------------------- #
# The ledger (_ACCOUNTED_SITES)
# --------------------------------------------------------------------------- #
def ledger_pending_rows(census_path: Path) -> list[tuple[str, str, int]]:
    """AST-read the ``pending-batch-a`` rows as ``(relpath, qualname, count)``."""
    tree = parse(census_path)
    rows: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values, strict=True):
            if not (isinstance(key, ast.Tuple) and isinstance(value, ast.Tuple)):
                continue
            try:
                rel, qual = (ast.literal_eval(e) for e in key.elts)
                count, reason = (ast.literal_eval(e) for e in value.elts)
            except ValueError:
                continue
            if reason == PENDING_REASON:
                rows.append((rel, qual, count))
    return sorted(rows)


def pending_grep_lines(census_path: Path) -> list[int]:
    """Line numbers where the literal ``pending-batch-a`` appears (grep shape)."""
    lines = census_path.read_text(encoding="utf-8").splitlines()
    return [i for i, text in enumerate(lines, 1) if PENDING_REASON in text]


def legend_lines(census_path: Path, rows: list[tuple[str, str, int]]) -> list[int]:
    """The grep hits that are prose, not ledger rows (the ``:185`` legend)."""
    lines = census_path.read_text(encoding="utf-8").splitlines()
    row_quals = {qual for _rel, qual, _n in rows}
    out: list[int] = []
    for lineno in pending_grep_lines(census_path):
        text = lines[lineno - 1]
        if not any(qual in text for qual in row_quals):
            out.append(lineno)
    return out


# --------------------------------------------------------------------------- #
# Arm classification (AST, not grep)
# --------------------------------------------------------------------------- #
def classify_arms(root: Path, rel: str, qual: str) -> list[tuple[int, str, int]]:
    """Return ``(call_line, arm, handler_line)`` per ``load_meta`` call in *qual*."""
    tree = parse(root / rel)
    fn = find_function(tree, qual)
    if fn is None:
        return [(-1, "NO-SUCH-FUNCTION", -1)]
    bindings = load_meta_bindings(tree)
    rows: list[tuple[int, str, int]] = []
    for call in load_meta_calls(fn, bindings):
        rows.append((call.lineno, *_arm_for_call(fn, call)))
    return rows


def _arm_for_call(fn: ast.AST, call: ast.Call) -> tuple[str, int]:
    """The arm a single *call* takes inside *fn*, and its handler line."""
    for node in ast.walk(fn):
        if not isinstance(node, ast.Try):
            continue
        if not any(call in set(ast.walk(stmt)) for stmt in node.body):
            continue
        for handler in node.handlers:
            if catches_value_error(handler):
                raises = any(isinstance(n, ast.Raise) for n in ast.walk(handler))
                return ("REFUSE-typed" if raises else "DEGRADE", handler.lineno)
    return ("REFUSE-raw", -1)


def value_error_handlers(root: Path, census: list[tuple[str, str, int]]) -> list[tuple[str, int, str]]:
    """The authoritative ``except ValueError`` handlers, by AST, one per site."""
    out: list[tuple[str, int, str]] = []
    for rel, qual, _count in census:
        for _call, arm, hline in classify_arms(root, rel, qual):
            if hline > 0 and arm in {"DEGRADE", "REFUSE-typed"}:
                out.append((rel, hline, qual))
    return sorted(set(out))


# --------------------------------------------------------------------------- #
# Traps (regex probes, shown as controlled negatives)
# --------------------------------------------------------------------------- #
def grep_line_hits(paths: list[Path], pattern: str) -> list[tuple[Path, int, str]]:
    """Line-granular regex hits, i.e. what ``grep -n`` would print."""
    rx = re.compile(pattern)
    hits: list[tuple[Path, int, str]] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        hits.extend((path, i, t.strip()) for i, t in enumerate(lines, 1) if rx.search(t))
    return hits


def python_files(src_root: Path) -> list[Path]:
    """Every ``*.py`` under *src_root*, sorted — the scanners' file population."""
    return sorted(src_root.rglob("*.py"))


# --------------------------------------------------------------------------- #
# Gate constants and the derived band
# --------------------------------------------------------------------------- #
def gate_constants(gate_path: Path) -> dict[str, int]:
    """AST-read the four module-level gate constants out of *gate_path*."""
    tree = parse(gate_path)
    out: dict[str, int] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in GATE_CONSTANTS:
                out[target.id] = int(ast.literal_eval(node.value))
    missing = sorted(set(GATE_CONSTANTS) - set(out))
    if missing:
        raise SystemExit(f"gate constants not found in {gate_path}: {missing}")
    return out


def routed_band(consts: dict[str, int]) -> tuple[int, int]:
    """The two-sided admissible routed band derived from the three assertions.

    ``len >= FLOOR`` and ``len > FLOOR`` together give ``FLOOR + 1`` as the low
    bound (the strict clause dominates), and ``len - FLOOR <= MARGIN`` gives
    ``FLOOR + MARGIN`` as the high bound. ``FLOOR`` itself is RED.
    """
    floor = consts["ROUTED_LOAD_META_FLOOR"]
    return floor + 1, floor + consts["ROUTED_LOAD_META_FLOOR_MARGIN"]


def import_gate(tree_root: Path) -> ModuleType:
    """Import *tree_root*'s own gate module so its scanners measure that tree."""
    if str(tree_root) not in sys.path:
        sys.path.insert(0, str(tree_root))
    return importlib.import_module(GATE_MODULE)


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def _verdict(label: str, got: Any, want: Any) -> bool:
    ok = got == want
    print(f"  CONTROL {label}: got {got} want {want} -> {'PASS' if ok else 'FAIL'}")
    return ok


def _snapshot(label: str, got: Any, want: Any, *, graded: bool) -> bool:
    """Compare against a WP01 freeze-point snapshot.

    These controls attest *the freeze point*, not the live tree: they drift by
    construction as the mission's own allocated routing lands. Grading them
    unconditionally made the script exit 1 on every progressed tree — including
    WP05's own allocated post-value of 130, the row ``headroom-allocation.md``
    tells downstream WPs to print. So they are graded only under
    ``--freeze-check``; otherwise drift is reported and excluded from the verdict.
    The live band check in :func:`check_bounds` is the downstream signal.
    """
    ok = got == want
    if graded:
        print(f"  CONTROL[freeze] {label}: got {got} want {want} -> {'PASS' if ok else 'FAIL'}")
        return ok
    state = "AT FREEZE" if ok else f"DRIFTED from freeze-point {want}"
    print(f"  SNAPSHOT {label}: got {got} ({state}; not graded — pass --freeze-check to grade)")
    return True


def report_arms(root: Path, census: list[tuple[str, str, int]], *, freeze_check: bool = False) -> bool:
    """Print the arm control, then the arm census; return the control verdict.

    The ARM_CONTROL pairs are a structural invariant — the classifier must keep
    classifying two known sites correctly — and stay graded. The arm *tally* is
    not: it counts the sites still pending in the ledger, which shrinks by design
    as each WP routes its rows. Grading it made the script fail on every tree
    where the mission had made progress, and it failed *silently*, printing no
    FAIL line of its own. It is now reported and graded only under --freeze-check.
    """
    print("== §1 ARMS (AST classifier, not grep) ==")
    print(f"  CONTROL pairs in: {len(ARM_CONTROL)}")
    ok = True
    for rel, qual, expected in ARM_CONTROL:
        for line, arm, hline in classify_arms(root, rel, qual):
            ok = ok and arm == expected
            print(f"  CONTROL {rel}::{qual} call@{line} arm={arm} want={expected} handler@{hline}")
    print(f"  CONTROL verdict: {'ALL PASS' if ok else 'FAILED'}")
    print(f"  INPUT rows (ledger {PENDING_REASON}): {len(census)}")
    tally: dict[str, int] = {"DEGRADE": 0, "REFUSE-raw": 0, "REFUSE-typed": 0}
    for rel, qual, _count in census:
        for line, arm, hline in classify_arms(root, rel, qual):
            tally[arm] = tally.get(arm, 0) + 1
            print(f"  SITE {rel}::{qual} call@{line} arm={arm} handler@{hline}")
    total = sum(tally.values())
    print(
        f"  DERIVED call sites: {total} / DEGRADE: {tally['DEGRADE']} / "
        f"REFUSE-raw: {tally['REFUSE-raw']} / REFUSE-typed: {tally['REFUSE-typed']}"
    )
    tally_ok = _snapshot(
        "arm tally over the PENDING ledger (shrinks as WPs route)",
        tally, CONTROL_ARMS, graded=freeze_check,
    )
    return ok and tally_ok


def report_ledger(census_path: Path, census: list[tuple[str, str, int]]) -> None:
    """Print the row count, the call-site expansion, and the legend exclusion."""
    print("== §1 LEDGER ROWS ==")
    grep_hits = pending_grep_lines(census_path)
    legend = legend_lines(census_path, census)
    sites = sum(count for _rel, _qual, count in census)
    print(f"  grep -c '{PENDING_REASON}' {census_path.name}: {len(grep_hits)} (candidates in)")
    print(f"  legend/prose hits dropped: {len(legend)} at line(s) {legend}")
    print(f"  ledger ROWS out: {len(census)}  (convention: ledger row)")
    print(f"  CALL SITES out: {sites}  (convention: call site; expanded from row counts)")
    for rel, qual, count in census:
        if count != 1:
            print(f"  multi-count row: {rel}::{qual} count={count}")


def _triage(
    root: Path, population: list[Path], handlers: list[tuple[str, int, str]], label: str
) -> int:
    """Print an ``N in -> M dropped -> K out`` triage over *population*."""
    hits = grep_line_hits(population, r"except ValueError")
    authoritative = {(rel, line) for rel, line, _qual in handlers}
    dropped = [
        (p.relative_to(root).as_posix(), n, t)
        for p, n, t in hits
        if (p.relative_to(root).as_posix(), n) not in authoritative
    ]
    print(f"  [{label}] population = {len(population)} files")
    print(f"  [{label}] {len(hits)} candidates in -> {len(dropped)} dropped -> {len(handlers)} out")
    for rel, line, text in sorted(dropped):
        kind = "COMMENT" if text.lstrip().startswith("#") else "UNRELATED-HANDLER"
        print(f"    [{label}] DROP {rel}:{line} [{kind}] {text}")
    return len(hits)


def report_traps(
    root: Path,
    src_root: Path,
    census: list[tuple[str, str, int]],
    handlers: list[tuple[str, int, str]],
    *,
    freeze_check: bool = False,
) -> bool:
    """Print both documented traps as controlled negatives, populations named."""
    print("== TRAPS (regex probes, controlled negatives) ==")
    routed_grep = grep_line_hits(python_files(src_root), r"load_meta")
    ok_a = _snapshot(
        "routed naive regex (grep -rn 'load_meta' src)",
        len(routed_grep),
        CONTROL_ROUTED_GREP,
        graded=freeze_check,
    )

    census_files = sorted({rel for rel, _qual, _n in census})
    pop_all = [root / rel for rel in census_files]
    pop_six = [root / rel for rel in census_files if rel != POP6_EXCLUDED]
    n_all = _triage(root, pop_all, handlers, "POP-ALL (9 census files, fully derived)")
    n_six = _triage(root, pop_six, handlers, f"POP-INHERITED (8 files = POP-ALL minus {POP6_EXCLUDED})")
    # The two regex counts are freeze-point snapshots, not invariants: widening a
    # handler to ``except (MissionMetaReadError, ValueError, OSError)`` — which WP02
    # had to do, because MissionMetaReadError is a RuntimeError — moves the regex
    # count while leaving the AST count untouched. That drift *is* this trap's
    # thesis, so it is reported rather than graded. The AST control stays graded:
    # it is the invariant the trap exists to contrast against.
    ok_b = _snapshot(
        "'except ValueError' regex over POP-INHERITED (freeze-point trap = 9)",
        n_six, CONTROL_EXCEPT_GREP_POP6, graded=freeze_check,
    )
    ok_c = _snapshot(
        "'except ValueError' regex over POP-ALL (freeze-point trap = 10)",
        n_all, CONTROL_EXCEPT_GREP_POPALL, graded=freeze_check,
    )
    # Also a freeze-point snapshot, and my earlier note here calling it "the
    # invariant the trap exists to contrast against" was WRONG. It counts
    # ``except ValueError`` handlers over the census files -- and widening or
    # deleting those handlers is exactly what this mission does. WP02's four
    # widenings and WP03's routing took it 6 -> 4 on correct work. Nothing that
    # counts a population the mission edits can be a verdict-bearing invariant.
    # What remains graded is the arm CLASSIFIER control (does the AST classifier
    # still classify two known sites correctly) and the live two-sided bounds.
    ok_d = _snapshot(
        "'except ValueError' AST-authoritative (freeze-point population = 6)",
        len(handlers), CONTROL_EXCEPT_AST, graded=freeze_check,
    )
    return ok_a and ok_b and ok_c and ok_d


def report_counts(gate: ModuleType, src_root: Path, consts: dict[str, int]) -> tuple[int, int]:
    """Print the routed and inline counts with their input file counts."""
    print("== §4 LIVE COUNTS (gate's own AST scanners) ==")
    files = python_files(src_root)
    routed = len(gate.scan_routed_load_meta_calls(src_root))
    inline = len(gate.scan_inline_meta_reads(src_root))
    print(f"  INPUT .py files walked: {len(files)}")
    print(f"  ROUTED live (AST walk): {routed}")
    print(f"  INLINE live (AST walk): {inline}")
    for name in GATE_CONSTANTS:
        print(f"  const {name} = {consts[name]}")
    low, high = routed_band(consts)
    print(f"  DERIVED routed band: [{low}, {high}] (two-sided; {consts['ROUTED_LOAD_META_FLOOR']} is RED)")
    return routed, inline


def check_bounds(routed: int, inline: int, consts: dict[str, int]) -> bool:
    """Verify the live counts sit inside their gates; print each verdict."""
    low, high = routed_band(consts)
    ok_routed = low <= routed <= high
    ceiling = consts["INLINE_META_READ_FLOOR"]
    ok_inline = inline <= ceiling and ceiling - inline <= consts["FLOOR_MARGIN"]
    print("== BOUNDS ==")
    print(f"  routed {routed} in [{low}, {high}]: {'OK' if ok_routed else 'OUT OF BAND'}")
    print(f"  inline {inline} <= {ceiling} and gap <= {consts['FLOOR_MARGIN']}: {'OK' if ok_inline else 'BREACH'}")
    return ok_routed and ok_inline


def main(argv: list[str]) -> int:
    """Measure *argv[1]* (default: the repository root) and report."""
    default_root = Path(__file__).resolve().parents[1]
    freeze_check = "--freeze-check" in argv
    positionals = [a for a in argv[1:] if not a.startswith("--")]
    root = Path(positionals[0]).resolve() if positionals else default_root
    src_root = root / "src"
    print("=" * 78)
    print("verify_meta_routing_manifest_3162 — mission meta-fail-closed-3162-01KZ7FSQ")
    print("=" * 78)
    print(f"TREE measured : {root}")
    print(f"SRC_ROOT      : {src_root}")
    print(f"PYTHONPATH    : {os.environ.get('PYTHONPATH', '<unset>')}")
    print(f"sys.executable: {sys.executable}")
    print(f"freeze-check  : {'ON (freeze-point snapshots graded)' if freeze_check else 'off (band-only verdict)'}")
    if not src_root.is_dir():
        raise SystemExit(f"no src/ under {root}")

    gate_path = root / GATE_REL
    census_path = root / CENSUS_REL
    consts = gate_constants(gate_path)
    census = ledger_pending_rows(census_path)

    report_ledger(census_path, census)
    arms_ok = report_arms(root, census, freeze_check=freeze_check)
    handlers = value_error_handlers(root, census)
    print("== §2 AUTHORITATIVE HANDLERS (AST) ==")
    for rel, line, qual in handlers:
        print(f"  {rel}:{line}  ({qual})")
    traps_ok = report_traps(root, src_root, census, handlers, freeze_check=freeze_check)
    gate = import_gate(root)
    routed, inline = report_counts(gate, src_root, consts)
    bounds_ok = check_bounds(routed, inline, consts)
    routed_ast_ok = _snapshot("routed AST authoritative", routed, CONTROL_ROUTED_AST, graded=freeze_check)

    verdict = arms_ok and traps_ok and bounds_ok and routed_ast_ok
    print("=" * 78)
    print(f"VERDICT: {'PASS' if verdict else 'FAIL'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
