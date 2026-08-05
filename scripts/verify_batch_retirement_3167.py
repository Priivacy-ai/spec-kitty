#!/usr/bin/env python
"""Deletion-manifest closure for the retirement of sync/batch.py's queue-backed senders.

Run from the repository root:  .venv/bin/python scripts/verify_batch_retirement_3167.py

Run it from the REPOSITORY ROOT CHECKOUT, not from a .worktrees/ path: a
dot-prefixed path segment makes some of this repo's architectural collectors
discover zero files and pass vacuously.

WHY THIS IS A SCRIPT AND NOT A PARAGRAPH
The first attempt at this manifest used ``git grep -w <bare name>`` and got two
buckets wrong in opposite directions, because a bare grep cannot distinguish:

  1. a CALL from a mention in a comment or docstring, and
  2. this module's symbol from a DIFFERENT module's same-named symbol
     (``EventEmitter._current_team_slug`` at sync/emitter.py:870 is not
     ``batch._current_team_slug``; body_transport.py defines its own
     ``_body_mentions_missing_private_team``).

Both errors were caught by an adversarial squad. The remedy is a closure that
resolves references *module-qualified* and classifies them CODE / STR-TARGET /
PROSE, emitted as a table so the manifest is reviewable rather than re-argued.
Two implementers running this get the same set.

ALGORITHM
  1. AST-parse the target module. Enumerate top-level functions, classes,
     constants (Assign/AnnAssign) and imported names.
  2. Build the intra-module referrer graph from ``ast.Name`` / ``ast.Attribute``.
  3. For every other file under src/ tests/ scripts/, resolve references
     module-qualified:
       - names imported ``from ...sync.batch import X``      -> CODE
       - attribute access via a module alias, ``batch_mod.X`` -> CODE
       - string literals containing ``...sync.batch.X``       -> STR-TARGET
                                                               (monkeypatch/patch)
       - the token appears but matched none of the above      -> PROSE
     PROSE never keeps a symbol alive. STR-TARGET keeps it alive only for the
     purposes of *test* disposition, never for production liveness.
  4. Iterate to a fixpoint from the seed senders. The seeds themselves are NOT
     granted deadness -- they join the dead set only if they too have no
     production CODE reference, and the run REFUSES (exit 1) if one does. A
     closure that assumes its own premise cannot certify it.
     Every other symbol joins the dead set when every intra-module referrer is
     already dead AND it has no external CODE reference from src/.
  5. Report tiers:
       first  - dead, no external reference at all           -> delete now
       second - dead in src/, held only by test CODE/STR      -> delete once
                those tests retire (their disposition is a separate decision)
       alive  - has a production CODE reference, or is
                advertised through the package's public API
"""

from __future__ import annotations

import ast
import sys
import tokenize
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

TARGET = Path("src/specify_cli/sync/batch.py")
TARGET_MODULE_TAIL = "sync.batch"
SEEDS = {"batch_sync", "sync_all_queued_events"}
SEARCH_ROOTS = (Path("src"), Path("tests"), Path("scripts"))
# Names advertised through specify_cli.sync's lazy map / __all__ are API-alive
# even with no in-repo caller. Determined from src/specify_cli/sync/__init__.py.
API_ALIVE: set[str] = set()


def _api_alive() -> set[str]:
    init = Path("src/specify_cli/sync/__init__.py")
    if not init.exists():
        return set()
    tree = ast.parse(init.read_text())
    out: set[str] = set()
    for node in ast.walk(tree):
        # the lazy map's values are ("(.batch", "NAME") tuples
        if isinstance(node, ast.Tuple) and len(node.elts) == 2:
            mod, name = node.elts
            if (
                isinstance(mod, ast.Constant)
                and isinstance(mod.value, str)
                and mod.value.endswith(".batch")
                and isinstance(name, ast.Constant)
                and isinstance(name.value, str)
            ):
                out.add(name.value)
    return out


def _declarations(tree: ast.Module) -> tuple[dict[str, ast.AST], set[str], set[str]]:
    """Top-level callables/classes, module constants, imported names."""
    decls: dict[str, ast.AST] = {}
    consts: set[str] = set()
    imported: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            decls[node.name] = node
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            consts.add(node.target.id)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    consts.add(t.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                if a.name != "*":
                    imported.add(a.asname or a.name.split(".")[0])
    return decls, consts, imported


def _referenced_names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _classify_external(path: Path, symbols: set[str]) -> dict[str, str]:
    """Return {symbol: 'CODE'|'STR-TARGET'|'PROSE'} for symbols referenced in path."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return {}
    present = {s for s in symbols if s in text}
    if not present:
        return {}

    result: dict[str, str] = {}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return dict.fromkeys(present, "PROSE")

    # names imported directly from the target module, and module aliases for it
    direct: set[str] = set()
    aliases: set[str] = set()
    # A sibling module inside src/specify_cli/sync/ reaches the target as the
    # RELATIVE ``from .batch import X`` (node.module == "batch", level >= 1).
    # Missing this case reported every production consumer as having no
    # reference at all -- including run_final_sync_with_retries, which
    # sync/background.py imports exactly that way.
    in_target_package = str(path.parent).endswith("specify_cli/sync")

    def _is_target(node: ast.ImportFrom) -> bool:
        mod = node.module or ""
        if mod.endswith(TARGET_MODULE_TAIL):
            return True
        return bool(node.level) and mod == "batch" and (in_target_package or node.level >= 2)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and _is_target(node):
            for a in node.names:
                direct.add(a.asname or a.name)
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.endswith("specify_cli.sync"):
            for a in node.names:
                if a.name == "batch":
                    aliases.add(a.asname or a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.endswith(TARGET_MODULE_TAIL):
                    aliases.add(a.asname or a.name.split(".")[0])

    code_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attr_on_alias = {
        n.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in aliases
    }
    # string literals naming the module path (monkeypatch/patch targets)
    str_targets: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and TARGET_MODULE_TAIL in n.value:
            str_targets.add(n.value.rsplit(".", 1)[-1])

    # tokens appearing only in comments -> prose. (docstrings are ast.Constant,
    # already excluded from code_names)
    comment_tokens: set[str] = set()
    try:
        for tok in tokenize.tokenize(BytesIO(text.encode()).readline):
            if tok.type == tokenize.COMMENT:
                for s in present:
                    if s in tok.string:
                        comment_tokens.add(s)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass

    for s in present:
        if (s in direct and s in code_names) or s in attr_on_alias:
            result[s] = "CODE"
        elif s in str_targets:
            result[s] = "STR-TARGET"
        else:
            result[s] = "PROSE"
    return result


def _test_file_dispositions(
    dead: set[str], external: dict[str, dict[str, str]]
) -> tuple[dict[str, set[str]], set[str]]:
    """Split test files touching a dead symbol into code-coupled and prose-only.

    Code-coupled files import or monkeypatch a dead symbol and therefore need real
    work when it goes. Prose-only files merely *mention* it; the fix there is the
    sentence, not the code. Keeping the split mechanical is the point -- it is the
    distinction a bare grep cannot draw.
    """
    coupled: dict[str, set[str]] = {}
    for s in dead:
        for f, k in external.get(s, {}).items():
            if f.startswith("tests/") and k in {"CODE", "STR-TARGET"}:
                coupled.setdefault(f, set()).add(s)
    prose_only = {
        f
        for s in dead
        for f, k in external.get(s, {}).items()
        if f.startswith("tests/") and k == "PROSE" and f not in coupled
    }
    return coupled, prose_only


def _print_tiers(
    first: list[str],
    second: list[str],
    alive: list[str],
    prod_code_refs: Callable[[str], list[str]],
    test_refs: Callable[[str], list[str]],
) -> None:
    """Emit the three tiers with per-symbol referrer sets.

    The referrer sets are printed rather than summarised so a name-collision error
    is visible on the face of the report instead of buried in a total.
    """
    print(f"== FIRST TIER — delete now ({len(first)}) ==")
    for s in first:
        print(f"   {s}")
    print(f"\n== SECOND TIER — dead in src/, held only by tests ({len(second)}) ==")
    for s in second:
        print(f"   {s:44} tests: {sorted(test_refs(s))}")
    print(f"\n== ALIVE — must survive ({len(alive)}) ==")
    for s in alive:
        prod = prod_code_refs(s)
        tag = "API-alive" if (s in API_ALIVE and not prod) else f"prod CODE refs: {prod}"
        print(f"   {s:44} {tag}")


def main() -> int:
    root = Path.cwd()
    if not (root / TARGET).exists():
        print(f"run from the repository root; {TARGET} not found", file=sys.stderr)
        return 2

    global API_ALIVE
    API_ALIVE = _api_alive()

    tree = ast.parse((root / TARGET).read_text())
    decls, consts, _imported = _declarations(tree)
    symbols = set(decls) | consts

    # intra-module referrer graph
    uses: dict[str, set[str]] = {
        name: (_referenced_names(node) & symbols) - {name} for name, node in decls.items()
    }

    # external classification, once per file
    external: dict[str, dict[str, str]] = {}
    scanned = 0
    for r in SEARCH_ROOTS:
        if not (root / r).exists():
            continue
        for p in (root / r).rglob("*.py"):
            rel = p.relative_to(root)
            if rel == TARGET:
                continue
            scanned += 1
            hits = _classify_external(p, symbols)
            for sym, kind in hits.items():
                external.setdefault(sym, {})[str(rel)] = kind

    def prod_code_refs(sym: str) -> list[str]:
        return [f for f, k in external.get(sym, {}).items() if k == "CODE" and f.startswith(("src/", "scripts/"))]

    def test_refs(sym: str) -> list[str]:
        return [f for f, k in external.get(sym, {}).items() if k in {"CODE", "STR-TARGET"} and f.startswith("tests/")]

    # fixpoint
    # SEEDS must EARN their place in the dead set, not be granted it. The first
    # version wrote ``dead = set(SEEDS)``; because the loop below skips anything
    # already in ``dead``, the two symbols this mission proposes to delete were
    # the only two whose absence of a production caller the closure could not
    # test. An injected ``from .batch import batch_sync`` in sync/diagnose.py
    # produced a byte-identical report -- the resolver was blind to a caller of
    # exactly the symbol whose callerlessness is the mission's premise.
    # Seeding is still required (``sync_all_queued_events`` has no intra-module
    # referrer, so the ``referrers <= dead`` rule can never derive it), but it is
    # now conditional on the same evidence every other symbol must supply.
    dead = {s for s in SEEDS if s not in API_ALIVE and not prod_code_refs(s)}
    unproven_seeds = sorted(SEEDS - dead)
    changed = True
    while changed:
        changed = False
        for sym in symbols:
            if sym in dead or sym in API_ALIVE:
                continue
            referrers = {n for n, u in uses.items() if sym in u}
            # A symbol with NO intra-module referrer is an ENTRY POINT, and an empty
            # referrer set satisfies ``referrers <= dead`` vacuously: its liveness
            # rests entirely on external evidence. The first version demanded
            # ``referrers and referrers <= dead``, so an entry point could never be
            # derived dead however the external evidence fell --
            # run_final_sync_with_retries stayed ALIVE even with background.py's
            # ``from .batch import`` block deleted, which made the ALIVE tier an
            # artifact of the rule rather than a finding. Unreferenced CONSTANTS keep
            # the original carve-out (deferred to ruff / dead-symbol review) so this
            # correction cannot silently widen the deletion set.
            if sym in consts and not referrers:
                continue
            if referrers <= dead and not prod_code_refs(sym):
                dead.add(sym)
                changed = True

        # constants referenced only from dead functions
        for c in consts - dead:
            if c in API_ALIVE or prod_code_refs(c):
                continue
            referrers = {n for n, node in decls.items() if c in _referenced_names(node)}
            if referrers and referrers <= dead:
                dead.add(c)
                changed = True

    first = sorted(s for s in dead if not test_refs(s))
    second = sorted(s for s in dead if test_refs(s))
    alive = sorted(symbols - dead)

    print(f"target: {TARGET}   seeds: {sorted(SEEDS)}")
    print(f"declared symbols: {len(symbols)}  (callables/classes {len(decls)}, constants {len(consts)})")
    print(f"files scanned for references: {scanned}  (roots: {[str(r) for r in SEARCH_ROOTS]})")
    print(f"API-alive via specify_cli.sync lazy map: {sorted(API_ALIVE)}")
    # The seed premise, tested rather than assumed. Printed with the evidence so a
    # reader can see WHICH seed earned deletion and on what basis.
    for s in sorted(SEEDS):
        verdict = "no production CODE ref -> deletable" if s in dead else f"HAS production CODE refs {prod_code_refs(s)}"
        print(f"seed premise: {s:32} {verdict}")
    print()

    _print_tiers(first, second, alive, prod_code_refs, test_refs)

    print(f"\nTOTALS  dead={len(dead)} (first={len(first)} second={len(second)})  alive={len(alive)}")
    print("\n== test files with CODE/STR-TARGET coupling to any dead symbol ==")
    coupled, prose_only = _test_file_dispositions(dead, external)
    for f in sorted(coupled):
        print(f"   {f}\n        {sorted(coupled[f])}")
    print(f"\ncode-coupled test files: {len(coupled)}")

    print(f"prose-only test files (no code work; correct the prose): {len(prose_only)}")
    for f in sorted(prose_only):
        print(f"   {f}")

    if unproven_seeds:
        print(
            "\n*** REFUSED: the mission premise is false for "
            f"{unproven_seeds} -- a production caller exists, so this symbol must NOT be deleted. ***",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
