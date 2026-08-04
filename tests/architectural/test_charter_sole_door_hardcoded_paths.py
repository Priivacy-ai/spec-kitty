"""Missions-root hardcode gate — FR-004 / FR-007 (Gate 4, mission-wide).

Mission ``charter-sole-door-bypass-closure-01KZ3WAA`` / WP06. This mission
absorbed the former WP09 Gate 4 into WP06 (post-tasks squad restructure —
the gate only ever guarded WP06's own surface).

WP06 closed 2 of 3 duplicate hardcodes that independently reconstructed the
shipped ``src/doctrine/missions`` root via a ``Path(__file__)``-relative
literal containing ``"doctrine"`` immediately followed by ``"missions"`` as
adjacent path-join components:

* ``charter.mission_type_profile_repository.builtin_missions_root()`` (T022)
* ``specify_cli.runtime.home.get_package_asset_root()``'s ``dev_roots``
  fallback tuple (T023)

Both now delegate to the ONE promoted authority,
:meth:`~doctrine.missions.repository.MissionTemplateRepository.default_missions_root`.
This gate makes that closure durable: it is a **zero-tolerance** scan (no
allow-list) for that exact literal shape anywhere in ``src/`` outside the one
promoted authority module, ``src/doctrine/missions/repository.py``.

Scope note (named residual, not silently fixed): a post-tasks squad pass
found 3 MORE missions-root constructions this gate does NOT police, because
they are a **different literal shape** — root-relative from a different
anchor (e.g. ``repo_root / "src" / "doctrine" / "missions"``), not
``Path(__file__)``-relative:

* ``src/kernel/paths.py`` (around lines 89-90)
* ``src/specify_cli/template/manager.py`` (around lines 45, 126)
* ``src/specify_cli/cli/commands/charter/list_cmd.py`` (around lines 66, 79)

Closing those is out of this WP's scope (see WP06's task file T025); this
gate's job is narrowly the two ``Path(__file__)``-relative shapes T022/T023
closed, proven non-vacuous by the self-mutation test below.
"""

from __future__ import annotations

import ast
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[2]
SRC_ROOT = _REPO_ROOT / "src"

#: The ONE module entitled to construct the missions-root path natively.
#: Every other module must call
#: ``MissionTemplateRepository.default_missions_root()`` instead of
#: reconstructing the literal itself.
AUTHORITY_REL_PATH = "src/doctrine/missions/repository.py"

#: The two path-join components this gate looks for, adjacent, in that order.
_GUARDED_COMPONENTS = ("doctrine", "missions")


@dataclass(frozen=True)
class MissionsRootHardcodeSite:
    """One discovered ``Path(__file__)``-relative missions-root literal."""

    rel_path: str
    qualname: str
    lineno: int


def _rel(path: Path) -> str:
    try:
        return path.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_source_files(src_root: Path) -> list[Path]:
    return [p for p in sorted(src_root.rglob("*.py")) if "__pycache__" not in p.parts]


def _parent_map(tree: ast.Module) -> dict[int, ast.AST]:
    parents: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _qualname_from_parents(parents: dict[int, ast.AST], target: ast.AST) -> str:
    chain: list[str] = []
    cur: ast.AST | None = target
    while cur is not None:
        cur = parents.get(id(cur))
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            chain.append(cur.name)
    return ".".join(reversed(chain)) if chain else "<module>"


def _is_path_call(call: ast.Call) -> bool:
    """True for a ``Path(...)`` / ``pathlib.Path(...)`` construction."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id == "Path"
    return isinstance(func, ast.Attribute) and func.attr == "Path"


def _is_dunder_file_path_call(node: ast.expr) -> bool:
    """True for ``Path(__file__)`` (bare, unwrapped)."""
    return (
        isinstance(node, ast.Call)
        and _is_path_call(node)
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "__file__"
    )


def _unwrap_to_base(node: ast.expr) -> ast.expr:
    """Descend through ``.attr``, ``[subscript]`` and ``.method()`` wrappers.

    Handles the two live pre-fix shapes:
    ``Path(__file__).resolve().parents[1]`` and ``Path(__file__).parents[2]``
    — stripping ``.resolve()``, ``.parents``, and the ``[N]`` index to reach
    the base ``Path(__file__)`` call.
    """
    while True:
        if isinstance(node, (ast.Subscript, ast.Attribute)):
            node = node.value
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            node = node.func.value
        else:
            return node


def _root_is_dunder_file_path(node: ast.expr) -> bool:
    return _is_dunder_file_path_call(_unwrap_to_base(node))


def _collect_join_chain(node: ast.expr) -> tuple[ast.expr, list[str]]:
    """Return ``(root_expr, [literal_components_in_join_order])``.

    Walks a left-associative ``/`` (``BinOp`` / ``Div``) chain, collecting
    each string-literal right-hand operand in order. ``root_expr`` is the
    non-``BinOp`` base the chain bottoms out on.
    """
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        root, literals = _collect_join_chain(node.left)
        if isinstance(node.right, ast.Constant) and isinstance(node.right.value, str):
            literals.append(node.right.value)
        return root, literals
    return node, []


def _has_adjacent_guarded_components(literals: list[str]) -> bool:
    guarded_first, guarded_second = _GUARDED_COMPONENTS
    return any(
        a == guarded_first and b == guarded_second
        for a, b in zip(literals, literals[1:], strict=False)
    )


def _is_outermost_join(parents: dict[int, ast.AST], node: ast.BinOp) -> bool:
    """True when *node* is not itself the left operand of an enclosing ``/`` join.

    Prevents double-counting the same literal join chain once per nested
    ``BinOp`` — only the single outermost node in a chain is scored.
    """
    parent = parents.get(id(node))
    return not (isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Div))


def _scan_file(path: Path, rel: str) -> list[MissionsRootHardcodeSite]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    parents = _parent_map(tree)

    found: list[MissionsRootHardcodeSite] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
            continue
        if not _is_outermost_join(parents, node):
            continue
        root, literals = _collect_join_chain(node)
        if not _root_is_dunder_file_path(root):
            continue
        if not _has_adjacent_guarded_components(literals):
            continue
        found.append(
            MissionsRootHardcodeSite(rel, _qualname_from_parents(parents, node), node.lineno)
        )
    return found


def scan_missions_root_hardcodes(src_root: Path) -> list[MissionsRootHardcodeSite]:
    """AST-walk ``<src_root>/**/*.py`` for ``Path(__file__)``-relative missions-root literals.

    Excludes :data:`AUTHORITY_REL_PATH` — that module IS the promoted
    authority, so its own resolution logic is the definition, not a
    violation.
    """
    sites: list[MissionsRootHardcodeSite] = []
    for path in _iter_source_files(src_root):
        rel = _rel(path)
        if rel == AUTHORITY_REL_PATH:
            continue
        sites.extend(_scan_file(path, rel))
    return sites


def check_missions_root_hardcode_gate(src_root: Path) -> list[str]:
    """Return violation strings — zero-tolerance, no allow-list."""
    return [
        f"{site.rel_path}:{site.lineno} ({site.qualname}) reconstructs the "
        "missions-root path via a Path(__file__)-relative "
        '"doctrine" / "missions" literal instead of calling '
        "MissionTemplateRepository.default_missions_root() (FR-004) — route "
        "it through the promoted authority"
        for site in scan_missions_root_hardcodes(src_root)
    ]


# =========================================================================== #
# TESTS
# =========================================================================== #


# --- unit: detector shape ----------------------------------------------------
@pytest.mark.parametrize(
    "snippet",
    [
        'from pathlib import Path\ndef f():\n    return Path(__file__).resolve().parents[1] / "doctrine" / "missions"\n',
        'from pathlib import Path\ndef f():\n    return Path(__file__).parents[2] / "doctrine" / "missions"\n',
        'from pathlib import Path\ndef f():\n    return Path(__file__).parent.parent / "doctrine" / "missions"\n',
    ],
)
def test_detector_flags_dunder_file_relative_shape(snippet: str, tmp_path: Path) -> None:
    mod = tmp_path / "snippet.py"
    mod.write_text(snippet, encoding="utf-8")
    sites = _scan_file(mod, "snippet.py")
    assert len(sites) == 1
    assert sites[0].qualname == "f"


@pytest.mark.parametrize(
    "snippet",
    [
        # Only "missions", no adjacent "doctrine" component — the OTHER,
        # legitimate dev_roots fallback entry (specify_cli/missions legacy
        # layout) must not be flagged.
        'from pathlib import Path\ndef f():\n    return Path(__file__).parent.parent / "missions"\n',
        # Root-relative, not Path(__file__)-relative — out of THIS gate's
        # scope (a different literal shape; see module docstring residuals).
        'def f(repo_root):\n    return repo_root / "src" / "doctrine" / "missions"\n',
        # Adjacent components in the wrong order.
        'from pathlib import Path\ndef f():\n    return Path(__file__).parent / "missions" / "doctrine"\n',
        # importlib.resources-based — the promoted authority's OWN shape,
        # never Path(__file__)-relative.
        'from importlib.resources import files\ndef f():\n    return files("doctrine") / "missions"\n',
    ],
)
def test_detector_ignores_non_matching_shapes(snippet: str, tmp_path: Path) -> None:
    mod = tmp_path / "snippet.py"
    mod.write_text(snippet, encoding="utf-8")
    assert _scan_file(mod, "snippet.py") == []


def test_scan_excludes_the_promoted_authority_module() -> None:
    """``doctrine/missions/repository.py`` owns the resolution and is never a violation."""
    sites = scan_missions_root_hardcodes(SRC_ROOT)
    assert all(s.rel_path != AUTHORITY_REL_PATH for s in sites)


# --- zero-tolerance real-tree gate -------------------------------------------
def test_gate_is_zero_tolerance_against_the_live_tree() -> None:
    """T022 + T023 closed both Path(__file__)-relative sites: the live tree is clean.

    No allow-list: any future reintroduction of this exact literal shape
    (outside the promoted authority) fails this test immediately.
    """
    violations = check_missions_root_hardcode_gate(SRC_ROOT)
    assert violations == [], "\n".join(violations)


# --- NFR-004 self-mutation proof ---------------------------------------------
def test_injected_hardcode_is_flagged_naming_the_exact_line(tmp_path: Path) -> None:
    """Self-mutation proof: a re-introduced hardcode goes RED, naming its line.

    Injects into a scratch module (never the real, already-closed sites) so
    the RED-on-demand property is proven fresh on every run, not eyeballed
    once at review time.
    """
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True)
    regressed = pkg / "regressed.py"
    regressed.write_text(
        "from pathlib import Path\n"
        "\n"
        "\n"
        "class Regressed:\n"
        "    def load(self):\n"
        '        return Path(__file__).resolve().parents[1] / "doctrine" / "missions"\n',
        encoding="utf-8",
    )
    scratch_src = tmp_path / "src"

    violations = check_missions_root_hardcode_gate(scratch_src)
    assert violations, "self-mutation: a re-introduced missions-root hardcode must be flagged"
    assert any("regressed.py:6" in v and "Regressed.load" in v for v in violations), violations


def test_gate_runs_under_fast_tier_budget() -> None:
    """The scan completes well under the 30 s fast-tier ceiling."""
    start = time.monotonic()
    scan_missions_root_hardcodes(SRC_ROOT)
    elapsed = time.monotonic() - start
    assert elapsed < 30.0, f"missions-root hardcode scan took {elapsed:.2f}s (>30s budget)"
