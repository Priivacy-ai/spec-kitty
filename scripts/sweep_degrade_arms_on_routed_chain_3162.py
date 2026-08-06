#!/usr/bin/env python3
"""Chain-local sweep for degrade arms stranded by a fail-closed meta routing.

Deliverable of ``WP02`` review cycle 2 (mission ``meta-fail-closed-3162-01KZ7FSQ``).

**The defect class this exists to catch.** Routing a read site onto
``load_meta_fail_closed`` changes the exception it raises on a corrupt
``meta.json`` from ``ValueError`` (what ``mission_metadata.load_meta`` emitted) to
``specify_cli.core.paths.MissionMetaReadError``, whose MRO is::

    MissionMetaReadError -> RuntimeError -> Exception -> BaseException -> object

There is no ``ValueError`` and no ``OSError`` on that MRO. Every pre-existing
``except (ValueError, OSError)`` that wrapped the routed call therefore **stops
absorbing corruption the moment the site is routed** — it silently converts a
degrade path into a raising path. That is the arm change ``C-001`` forbids, and
it is invisible to the tests of the routed function itself.

**Why a file-local sweep is not enough.** WP02 routed
``_read_path_resolver.read_primary_meta`` and then swept *its own file* for
newly-stranded arms. The stranded arms are not in that file. They are on the
routed function's **transitive callers** — for mission 3162 the chain

    _find_feature_directory -> resolve_handle_to_read_path -> read_primary_meta

carries four such arms in ``src/specify_cli/cli/commands/agent/``, several call
hops away from the edit. The sweep has to be *chain-local*, not file-local.

**Why ``SC-002``'s existing probe cannot see this class.** That probe is scoped to
the routed **sites** — it asserts each of the 4 degrade sites behaves across 3
shapes. Its subject is the site. A stranded arm is by construction *not* at a
site: it is at a caller that never appears in a site-scoped enumeration. No
number of shapes per site reaches it. The two axes are orthogonal, so a green
``SC-002`` is not evidence about this class at all.

Usage::

    .venv/bin/python scripts/sweep_degrade_arms_on_routed_chain_3162.py [TREE_ROOT]

Useful flags::

    --seed NAME        seed function (bare name or dotted qualname). Repeatable.
                       Default: read_primary_meta
    --rev SHA          sweep a git revision's ``src/`` instead of the working tree
    --expect LOC,...   known-answer control; each LOC is ``file.py:LINE`` and may
                       name either the ``try:`` line or the ``except`` line
    --json             machine-readable output

**A sweep whose control did not reproduce its known answer is not a sweep.** Pass
``--self-check`` (preferred) or ``--expect`` (see ``--help`` for the recorded
mission-3162 control) so a silent result means something.

Exit status: ``0`` on a clean sweep, **and also 0 on a control run whose expected
hazards reproduced exactly** -- a control run is *supposed* to find hazards, so
its exit status reports whether the known answer held, not whether the tree is
clean. ``1`` when an uncontrolled sweep finds hazards or when an ``--expect``
control fails to reproduce. ``2`` when ``--self-check``'s control does not
reproduce (the run is refused outright) or a seed is unresolvable.

**Seeds must be dotted qualnames.** A bare ``--seed _resolve_mission_id`` resolves
to whichever function matches first -- for mission 3162 that is
``mission_runtime.resolution._resolve_mission_id``, a *different* function from
``decisions.service._resolve_mission_id``, and it reports hazards on a chain the
caller never touched.

WP03 and WP04 route further sites into these same callers; run this **before**
claiming a green, seeded with whatever function that work package routes.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import tarfile
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# Exception names that would STILL absorb a MissionMetaReadError if present in an
# ``except`` tuple. If a handler names any of these it is not stranded.
ABSORBING = frozenset({"Exception", "BaseException", "RuntimeError", "MissionMetaReadError"})

# Exception names whose presence signals a pre-routing degrade contract: these are
# what ``load_meta`` used to raise on a corrupt / unreadable meta.
STRANDABLE = frozenset({"ValueError", "OSError", "IOError", "EnvironmentError"})


@dataclass
class ModuleIndex:
    """Name-resolution tables for a single parsed module."""

    name: str
    path: Path
    source_lines: list[str]
    # alias -> dotted module name (``import x as y``; ``from pkg import mod as y``)
    module_aliases: dict[str, str] = field(default_factory=dict)
    # alias -> dotted qualname of an imported symbol (``from mod import sym as y``)
    symbol_aliases: dict[str, str] = field(default_factory=dict)
    # bare name -> qualname, for functions/classes defined in this module
    local_defs: dict[str, str] = field(default_factory=dict)


@dataclass
class Hazard:
    """One ``except`` clause stranded on a routed call chain."""

    path: str
    try_line: int
    except_line: int
    except_source: str
    function: str
    caught: list[str]
    guarded_callee: str
    chain: list[str]


def module_name_for(path: Path, src_root: Path) -> str:
    """Return the dotted module name for ``path`` relative to ``src_root``."""
    rel = path.relative_to(src_root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][: -len(".py")]
    return ".".join(parts)


def _dotted(node: ast.AST) -> str | None:
    """Flatten a dotted ``Name``/``Attribute`` chain to a string, else ``None``."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def _collect_imports(
    body: list[ast.stmt],
    index: ModuleIndex,
    known_modules: set[str],
    module_aliases: dict[str, str],
    symbol_aliases: dict[str, str],
) -> None:
    """Record import aliases from ``body`` into the supplied alias tables.

    Handles module scope and function scope identically, which matters here: this
    codebase routinely imports the seam under test *inside* the function (e.g.
    ``from specify_cli.cli.commands.agent import mission as _mission``), and a
    module-scope-only resolver would miss every one of those edges.
    """
    for node in body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_aliases[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import
                base_parts = index.name.split(".")
                # ``from . import x`` inside a package __init__ resolves differently
                # than inside a module; treat the module's parent package as level 1.
                anchor = base_parts[: len(base_parts) - node.level + 1]
                prefix = ".".join(anchor)
                base = f"{prefix}.{node.module}" if node.module else prefix
            else:
                base = node.module or ""
            for alias in node.names:
                target = f"{base}.{alias.name}" if base else alias.name
                local = alias.asname or alias.name
                if target in known_modules:
                    module_aliases[local] = target
                else:
                    symbol_aliases[local] = target


class CallGraph:
    """Import-resolved call graph over a ``src/`` tree."""

    def __init__(self, src_root: Path) -> None:
        """Parse every module under ``src_root`` and build the call graph."""
        self.src_root = src_root
        self.modules: dict[str, ModuleIndex] = {}
        self.trees: dict[str, ast.Module] = {}
        # qualname -> (function-local module aliases, function-local symbol aliases)
        self.local_tables: dict[str, tuple[dict[str, str], dict[str, str]]] = {}
        # callee qualname -> set of caller qualnames
        self.callers: dict[str, set[str]] = defaultdict(set)
        # qualname -> (module, ast.FunctionDef)
        self.functions: dict[str, tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = {}
        # bare name -> set of qualnames (fallback resolution)
        self.by_bare_name: dict[str, set[str]] = defaultdict(set)
        self._parse_all()
        self._index_defs()
        self._build_edges()

    def _parse_all(self) -> None:
        for path in sorted(self.src_root.rglob("*.py")):
            try:
                text = path.read_text(encoding="utf-8")
                tree = ast.parse(text)
            except (SyntaxError, UnicodeDecodeError):
                continue
            name = module_name_for(path, self.src_root)
            self.modules[name] = ModuleIndex(name=name, path=path, source_lines=text.splitlines())
            self.trees[name] = tree

    def _index_defs(self) -> None:
        known = set(self.modules)
        for name, tree in self.trees.items():
            index = self.modules[name]
            _collect_imports(tree.body, index, known, index.module_aliases, index.symbol_aliases)
            self._walk_defs(tree.body, name, [], index)

    def _walk_defs(
        self, body: list[ast.stmt], module: str, scope: list[str], index: ModuleIndex
    ) -> None:
        for node in body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                qual = ".".join([module, *scope, node.name])
                self.functions[qual] = (module, node)
                self.by_bare_name[node.name].add(qual)
                if not scope:
                    index.local_defs[node.name] = qual
                self._walk_defs(node.body, module, [*scope, node.name], index)
            elif isinstance(node, ast.ClassDef):
                if not scope:
                    index.local_defs[node.name] = ".".join([module, node.name])
                self._walk_defs(node.body, module, [*scope, node.name], index)

    def resolve_call(
        self,
        func: ast.expr,
        module: str,
        local_modules: dict[str, str],
        local_symbols: dict[str, str],
    ) -> str | None:
        """Resolve a call expression to the qualname of the function it invokes."""
        return self.canonicalize(self._resolve_call_raw(func, module, local_modules, local_symbols))

    def _resolve_call_raw(
        self,
        func: ast.expr,
        module: str,
        local_modules: dict[str, str],
        local_symbols: dict[str, str],
    ) -> str | None:
        index = self.modules[module]
        if isinstance(func, ast.Name):
            name = func.id
            for table in (local_symbols, index.symbol_aliases):
                if name in table:
                    return table[name]
            if name in index.local_defs:
                return index.local_defs[name]
            return self._fallback(name)
        if isinstance(func, ast.Attribute):
            base = _dotted(func.value)
            if base is not None:
                for table in (local_modules, index.module_aliases):
                    if base in table:
                        return f"{table[base]}.{func.attr}"
                for table in (local_symbols, index.symbol_aliases):
                    if base in table:
                        return f"{table[base]}.{func.attr}"
                if base in self.modules:
                    return f"{base}.{func.attr}"
            return self._fallback(func.attr)
        return None

    def canonicalize(self, qual: str | None) -> str | None:
        """Follow re-export shims until the qualname lands on a real definition.

        ``mission.py`` re-exports the resolution seam
        (``from ...mission_feature_resolution import _find_feature_directory as
        _find_feature_directory``), so a call written ``_mission._find_feature_directory(...)``
        resolves to a name that is an *alias*, not a def. Without this hop the
        edge is silently dropped and three of mission 3162's four stranded arms
        become invisible — the exact failure mode this instrument exists to
        prevent.
        """
        seen: set[str] = set()
        cursor = qual
        while cursor is not None and cursor not in self.functions and cursor not in seen:
            seen.add(cursor)
            module, _, name = cursor.rpartition(".")
            index = self.modules.get(module)
            if index is None or name not in index.symbol_aliases:
                return cursor
            cursor = index.symbol_aliases[name]
        return cursor

    def _fallback(self, bare: str) -> str | None:
        """Resolve a bare name only when it is unique across the tree.

        Ambiguous names are dropped rather than guessed: a wrong edge would
        manufacture a phantom caller chain, and this instrument's whole value is
        that its silence is trustworthy.
        """
        candidates = self.by_bare_name.get(bare, set())
        if len(candidates) == 1:
            return next(iter(candidates))
        return None

    def _build_edges(self) -> None:
        known = set(self.modules)
        for qual, (module, node) in self.functions.items():
            index = self.modules[module]
            local_modules: dict[str, str] = {}
            local_symbols: dict[str, str] = {}
            for sub in ast.walk(node):
                if isinstance(sub, ast.Import | ast.ImportFrom):
                    _collect_imports([sub], index, known, local_modules, local_symbols)
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    callee = self.resolve_call(sub.func, module, local_modules, local_symbols)
                    if callee is not None:
                        self.callers[callee].add(qual)
            # cache resolved local import tables for the hazard pass
            self.local_tables[qual] = (local_modules, local_symbols)

    def resolve_seed(self, seed: str) -> set[str]:
        """Expand a seed given as a bare name or dotted qualname to qualnames."""
        if seed in self.functions:
            return {seed}
        return set(self.by_bare_name.get(seed.split(".")[-1], set()))

    def reaches(self, seeds: set[str]) -> tuple[set[str], dict[str, str]]:
        """Fixpoint over reverse edges: everything that transitively reaches ``seeds``.

        Returns the reachable set and a parent map (caller -> callee) for chain
        reconstruction.
        """
        taint = set(seeds)
        parent: dict[str, str] = {}
        frontier = list(seeds)
        while frontier:
            current = frontier.pop()
            for caller in self.callers.get(current, set()):
                if caller not in taint:
                    taint.add(caller)
                    parent[caller] = current
                    frontier.append(caller)
        return taint, parent

    def chain_to_seed(self, start: str, parent: dict[str, str], seeds: set[str]) -> list[str]:
        """Reconstruct the shortest recorded call chain from ``start`` to a seed."""
        chain = [start]
        cursor = start
        while cursor not in seeds and cursor in parent:
            cursor = parent[cursor]
            chain.append(cursor)
        return chain


def _caught_names(handler: ast.ExceptHandler) -> list[str]:
    """Return the bare exception class names a handler catches."""
    if handler.type is None:
        return ["<bare>"]
    nodes = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    names: list[str] = []
    for node in nodes:
        dotted = _dotted(node)
        if dotted:
            names.append(dotted.split(".")[-1])
    return names


def _collect_call_sites(
    stmts: list[ast.stmt], stack: list[ast.Try], out: list[tuple[ast.Call, list[ast.Try]]]
) -> None:
    """Collect every ``Call`` with the ``Try`` nodes whose *body* encloses it.

    The stack is innermost-first. Only a ``Try``'s ``body`` protects a call — its
    handlers, ``else`` and ``finally`` clauses do not — so those are recursed with
    the *outer* stack. Nested function and class definitions are skipped: they are
    separate scopes with their own entry in the call graph.
    """
    for st in stmts:
        if isinstance(st, ast.Try):
            _collect_call_sites(st.body, [st, *stack], out)
            for handler in st.handlers:
                _collect_call_sites(handler.body, stack, out)
            _collect_call_sites(st.orelse, stack, out)
            _collect_call_sites(st.finalbody, stack, out)
            continue
        if isinstance(st, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        for _field, value in ast.iter_fields(st):
            if isinstance(value, list) and value and isinstance(value[0], ast.stmt):
                _collect_call_sites(value, stack, out)
            elif isinstance(value, ast.AST):
                out.extend(
                    (n, stack) for n in ast.walk(value) if isinstance(n, ast.Call)
                )
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        out.extend(
                            (n, stack) for n in ast.walk(item) if isinstance(n, ast.Call)
                        )


def _classify(try_node: ast.Try) -> tuple[str, ast.ExceptHandler | None, list[str]]:
    """Classify how a ``Try`` responds to a routed ``MissionMetaReadError``.

    Returns one of ``"absorbed"`` (a handler still catches it), ``"stranded"`` (a
    handler catches the *pre-routing* ``ValueError``/``OSError`` but would no
    longer catch the typed error), or ``"transparent"`` (unrelated handlers — the
    exception passes straight through and propagation continues outward).
    """
    for handler in try_node.handlers:
        caught = set(_caught_names(handler))
        if caught & ABSORBING or "<bare>" in caught:
            return "absorbed", handler, sorted(caught)
    for handler in try_node.handlers:
        caught = set(_caught_names(handler))
        if caught & STRANDABLE:
            return "stranded", handler, sorted(caught)
    return "transparent", None, []


def sweep(graph: CallGraph, seeds: set[str]) -> tuple[list[Hazard], set[str]]:
    """Find the ``except`` clauses a routing would strand, by exception propagation.

    This is deliberately *not* plain reverse reachability. A frame that absorbs the
    exception shields every frame above it, so a reachability sweep reports the
    whole blast radius and drowns the real answer. Instead this propagates the
    typed error outward from the seeds and stops at the **first guarding frame on
    each path** — the frontier you must actually fix. Widen those arms, re-run, and
    the next frontier (if any) surfaces.
    """
    hazards: list[Hazard] = []
    raising = set(seeds)
    parent: dict[str, str] = {}
    worklist = list(seeds)
    seen_sites: set[tuple[str, int]] = set()

    while worklist:
        callee = worklist.pop()
        for caller in sorted(graph.callers.get(callee, set())):
            if caller not in graph.functions:
                continue
            module, node = graph.functions[caller]
            index = graph.modules[module]
            local_modules, local_symbols = graph.local_tables.get(caller, ({}, {}))
            sites: list[tuple[ast.Call, list[ast.Try]]] = []
            _collect_call_sites(node.body, [], sites)
            for call, stack in sites:
                resolved = graph.resolve_call(call.func, module, local_modules, local_symbols)
                if resolved != callee:
                    continue
                verdict = "escapes"
                for try_node in stack:
                    kind, handler, caught = _classify(try_node)
                    if kind == "absorbed":
                        verdict = "absorbed"
                        break
                    if kind == "stranded" and handler is not None:
                        key = (str(index.path), handler.lineno)
                        if key not in seen_sites:
                            seen_sites.add(key)
                            parent.setdefault(callee, callee)
                            hazards.append(
                                Hazard(
                                    path=str(index.path),
                                    try_line=try_node.lineno,
                                    except_line=handler.lineno,
                                    except_source=index.source_lines[handler.lineno - 1],
                                    function=caller,
                                    caught=caught,
                                    guarded_callee=callee,
                                    chain=graph.chain_to_seed(callee, parent, seeds),
                                )
                            )
                        verdict = "stranded"
                        break
                if verdict == "escapes" and caller not in raising:
                    raising.add(caller)
                    parent[caller] = callee
                    worklist.append(caller)
    return hazards, raising


def materialize_rev(repo_root: Path, rev: str) -> Path:
    """Extract ``src/`` at ``rev`` into a temp dir without touching the work tree."""
    tmp = Path(tempfile.mkdtemp(prefix=f"sweep-{rev[:8]}-"))
    archive = tmp / "src.tar"
    with archive.open("wb") as handle:
        subprocess.run(
            ["git", "archive", rev, "src"], cwd=repo_root, stdout=handle, check=True
        )
    with tarfile.open(archive) as tar:
        tar.extractall(tmp, filter="data")
    return tmp / "src"


#: The recorded mission-3162 known answer: SIX stranded arms at base ``f1681bf1`` --
#: the two WP02 fixed file-locally plus the four on the command chain that a
#: file-local sweep structurally cannot see. ``--self-check`` replays this before
#: any sweep so a CLEAN verdict is never reported by an uncalibrated instrument.
CONTROL_BASE_REV = "f1681bf1"
CONTROL_EXPECT = (
    "surface_resolver.py:564,_read_path_resolver.py:1257,"
    "mission_setup_plan.py:301,mission_record_analysis.py:259,"
    "mission_finalize.py:291,mission_check_prerequisites.py:238"
)


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns the process exit status."""
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("tree_root", nargs="?", default=str(repo_root))
    parser.add_argument("--seed", action="append", default=None)
    parser.add_argument("--rev", default=None)
    parser.add_argument(
        "--expect",
        default=None,
        help=(
            "known-answer control, comma-separated file.py:LINE (either the try: "
            "or the except line). Recorded mission-3162 control at base f1681bf1 "
            "is SIX arms -- the two WP02 fixed file-locally plus the four on the "
            "command chain that a file-local sweep cannot see: "
            "'surface_resolver.py:564,_read_path_resolver.py:1257,"
            "mission_setup_plan.py:301,mission_record_analysis.py:259,"
            "mission_finalize.py:291,mission_check_prerequisites.py:238'. "
            "At HEAD after cycle-2 remediation the sweep must be CLEAN."
        ),
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help=(
            "replay the recorded known-answer control at base "
            f"{CONTROL_BASE_REV} before sweeping, and refuse to report CLEAN if it "
            "does not reproduce. Use this instead of hand-typing --expect: an "
            "uncalibrated sweep's silence means nothing, and the control string is "
            "easy to get wrong (it is a list of file.py:LINE, not a count)."
        ),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.self_check:
        if args.expect is not None or args.rev is not None:
            print(
                "ERROR: --self-check drives its own --rev/--expect; do not combine them",
                file=sys.stderr,
            )
            return 2
        print("== SELF-CHECK: replaying the recorded control ==")
        control_status = main(
            [args.tree_root, "--rev", CONTROL_BASE_REV, "--expect", CONTROL_EXPECT]
        )
        if control_status != 0:
            print()
            print(
                "SELF-CHECK FAILED: the known answer did not reproduce. This sweep's "
                "result is meaningless -- do NOT read a CLEAN verdict from it.",
                file=sys.stderr,
            )
            return 2
        print(
            "== SELF-CHECK PASSED: the 6 HAZARD(S) above are the *control's* known "
            f"answer at {CONTROL_BASE_REV}, not your tree. Live sweep follows. =="
        )
        print()

    tree_root = Path(args.tree_root).resolve()
    src_root = materialize_rev(repo_root, args.rev) if args.rev else tree_root / "src"
    if not src_root.is_dir():
        print(f"ERROR: no src/ at {src_root}", file=sys.stderr)
        return 2

    seeds_requested = args.seed or ["read_primary_meta"]
    graph = CallGraph(src_root)
    seeds: set[str] = set()
    for seed in seeds_requested:
        resolved = graph.resolve_seed(seed)
        if not resolved:
            print(f"ERROR: seed {seed!r} resolved to nothing", file=sys.stderr)
            return 2
        seeds |= resolved

    hazards, raising = sweep(graph, seeds)
    taint, _ = graph.reaches(seeds)

    if args.json:
        print(json.dumps([h.__dict__ for h in hazards], indent=2))
    else:
        print("=" * 78)
        print("CHAIN-LOCAL DEGRADE-ARM SWEEP (mission 3162)")
        print("=" * 78)
        print(f"  src tree        : {src_root}")
        print(f"  rev             : {args.rev or '(working tree)'}")
        print(f"  modules parsed  : {len(graph.modules)}")
        print(f"  functions indexed: {len(graph.functions)}")
        print(f"  seeds           : {sorted(seeds)}")
        print(f"  transitive callers reaching seed : {len(taint)}")
        print(f"  frames the typed error escapes   : {len(raising)}")
        print(f"  HAZARDS: {len(hazards)}")
        for haz in hazards:
            rel = Path(haz.path).name
            print()
            print(f"  {rel}:{haz.except_line}  (try at :{haz.try_line})")
            print(f"    {haz.except_source.strip()}")
            print(f"    in      : {haz.function}")
            print(f"    catches : {haz.caught}  (no RuntimeError -> strands MissionMetaReadError)")
            print(f"    guards  : {haz.guarded_callee}")
            print(f"    chain   : {' -> '.join(haz.chain)}")

    status = 0
    if args.expect is not None:
        wanted = {tok.strip() for tok in args.expect.split(",") if tok.strip()}
        got: set[str] = set()
        for haz in hazards:
            base = Path(haz.path).name
            got.add(f"{base}:{haz.try_line}")
            got.add(f"{base}:{haz.except_line}")
        missing = {w for w in wanted if w not in got}
        # one hazard may satisfy either its try or except line; count hazards, not tokens
        print()
        print(f"  CONTROL: expected {sorted(wanted)}")
        print(f"  CONTROL: hazards found {len(hazards)}, locations {sorted(got)}")
        if missing:
            print(f"  CONTROL: FAIL - not reproduced: {sorted(missing)}")
            status = 1
        elif len(hazards) != len(wanted):
            print(f"  CONTROL: FAIL - expected exactly {len(wanted)} hazards, got {len(hazards)}")
            status = 1
        else:
            print("  CONTROL: PASS - known answer reproduced exactly")
    elif hazards:
        status = 1

    print()
    print("VERDICT:", "CLEAN" if not hazards else f"{len(hazards)} HAZARD(S)")
    return status


if __name__ == "__main__":
    sys.exit(main())
