"""Inline meta.json read ratchet — the FIRST gate over raw ``json.loads``/``json.load``
reads of ``meta.json`` files that bypass the canonical
:func:`specify_cli.mission_metadata.load_meta` family.

Mission ``read-surface-ssot-closeout-01KWZV91`` / WP16.
Requirements: FR-006, NFR-002, SC-002 (IC-06).
Contract: ``kitty-specs/read-surface-ssot-closeout-01KWZV91/contracts/meta-read-ratchet.md``.

Thread B (WP05/06/07 + WP12-15) routed every non-migration, non-charter caller of
inline meta.json JSON parsing onto ``mission_metadata.load_meta`` /
``load_meta_strict`` / ``load_meta_or_empty``. This module stands up the
structural (CI-red on regression) gate that keeps the drained class from
regrowing. **Non-vacuous** — modeled on
``test_resolution_authority_gates.py`` + ``resolution_gate_allowlist.yaml``, this
gate implements the SAME four mechanics (not a weaker shape):

1. **Integer floor** — ``INLINE_META_READ_FLOOR`` is the live post-drain census;
   the live inline-read count MUST be ``<= floor`` (a shrink-only CEILING, unlike
   the canonicalizer's growth-oriented floor: fewer inline reads is progress).
2. **Margin** — ``FLOOR_MARGIN`` bounds how far ABOVE the live count the floor may
   be pinned (``floor - live <= margin``); a floor pinned far above live would
   mask a future regression that grows the inline-read count back up toward it.
3. **Routed-count floor (anti-mass-allow-list)** — mirrors
   ``ROUTED_CANONICALIZER_FLOOR``: the number of call sites routed through
   ``load_meta`` / ``load_meta_strict`` / ``load_meta_or_empty`` has its own
   floor and can only rise. This is independent of the allow-list, so "draining"
   the inline-read floor by mass-allow-listing sites (instead of routing them)
   manufactures zero routed evidence and is structurally distinguishable.
4. **Composite-key allow-list with stale-entry detection** — each deferred site
   is a ``{key, rationale, issue}`` entry; ``allowlist_keys - live_keys``
   non-empty fails the build (a routed-away entry must be evicted, never left
   masking a drained site).

The scanner excludes ``mission_metadata.py`` (the canonical reader's own
implementation, whose internal ``json.loads`` calls ARE the authority, not a
violation of it) and the ``task_utils`` path-signature adapter (a thin,
behavior-preserving wrapper around the canonical reader — see
``task_utils/support.py::load_meta`` docstring).
"""

from __future__ import annotations

import ast
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tests.architectural._ratchet_keys import code_tokens_by_line

pytestmark = pytest.mark.architectural

# --------------------------------------------------------------------------- #
# Source-tree roots (repo-root independent).
# this file: <root>/tests/architectural/test_inline_meta_read_gate.py
# --------------------------------------------------------------------------- #
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[2]
SRC_ROOT = _REPO_ROOT / "src"
ALLOWLIST_PATH = _THIS.parent / "inline_meta_read_allowlist.yaml"

# Per contract: the canonical reader's own internals, and the task_utils
# path-signature adapter, are excluded from the INLINE-READ scan.
EXCLUDED_REL_PATHS: frozenset[str] = frozenset(
    {
        "src/specify_cli/mission_metadata.py",
        "src/specify_cli/task_utils/support.py",
    }
)

# The variable-name heuristic half of the scanner (contract rule: var names
# ``meta_path|meta_file|meta_json|target_meta_path``).
META_PATH_VAR_NAMES: frozenset[str] = frozenset(
    {"meta_path", "meta_file", "meta_json", "target_meta_path"}
)

# The canonical reader family a routed call site targets.
ROUTED_CALLEES: frozenset[str] = frozenset({"load_meta", "load_meta_strict", "load_meta_or_empty"})

# --------------------------------------------------------------------------- #
# Concrete integer floors (NFR-002). Live census measured on this tree via
# scan_inline_meta_reads(SRC_ROOT) / scan_routed_load_meta_calls(SRC_ROOT) — NOT
# ``<= huge`` / ``>= 0`` placeholders (NFR-002 rejects vacuous bounds).
#
# WP16 (mission read-surface-ssot-closeout-01KWZV91): post Thread-B drain
# (WP05/06/07 + WP12-15), the live inline-read census is exactly the 5 known
# deferred files (7 call sites) allow-listed below — 3 migrations that must
# tolerate legacy/malformed meta.json shapes the canonical reader would reject,
# plus 2 ``src/charter/`` sites that would otherwise introduce a cross-package
# dependency on ``specify_cli.mission_metadata`` (Shared Package Boundary ADR).
INLINE_META_READ_FLOOR = 7

# This is a CEILING-type ratchet (fewer inline reads is progress, unlike the
# canonicalizer's growth-oriented floor) so the margin bounds the gap the OTHER
# direction: the floor may not be pinned more than MARGIN calls ABOVE the live
# count (which would mask a future regression that grows the count back toward
# it). At INLINE_META_READ_FLOOR == live == 7 today, the gap is 0.
FLOOR_MARGIN = 2

# WP16 SC-004-equivalent anti-mass-allow-list guard: the number of call sites
# routed through load_meta/load_meta_strict/load_meta_or_empty has its own
# floor and can only rise. Live routed census on this tree is 113 (includes
# mission_metadata.py's own internal call sites — e.g. load_meta_strict/
# load_meta_or_empty delegating to load_meta, and the module's many other
# public helpers reading meta.json through the one canonical primitive; those
# ARE genuine routed-usage evidence, not the read implementation itself, which
# is why mission_metadata.py is excluded from the INLINE scan but NOT from this
# routed-usage census). Floor (112) sits one below the live count, inside the
# MARGIN(4) band (113 - 4 = 109 <= floor < 113).
ROUTED_LOAD_META_FLOOR_MARGIN = 4
ROUTED_LOAD_META_FLOOR = 112


# --------------------------------------------------------------------------- #
# Composite-key allow-list machinery (mechanic 4).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class InlineMetaReadKey:
    """Composite Design-P allow-list key surviving benign line drift.

    ``rel_path`` is the repo-relative source path, ``enclosing_qualname`` is the
    dotted chain of enclosing ``def``/``class`` names (or ``"<module>"`` at file
    scope), and ``token`` is the FROZEN tool-derived ``code_tokens_by_line``
    string of the call's line — the authoritative content comparand, never a raw
    line number.
    """

    rel_path: str
    enclosing_qualname: str
    token: str


class AllowlistEntryError(ValueError):
    """Raised when a YAML allow-list entry is malformed (missing a required field)."""


def _require_str(mapping: dict[str, object], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AllowlistEntryError(
            f"allow-list entry {context} is missing a non-empty {key!r} field "
            f"(got {value!r}); every deferred site needs an explicit {key} — no silent drift"
        )
    return value


def load_allowlist(path: Path) -> list[InlineMetaReadKey]:
    """Load the governance YAML's ``inline_meta_read`` entries.

    Each entry carries ``file:``, ``qualname:``, ``token:`` (the composite key),
    plus mandatory ``rationale:`` and ``issue:`` fields (contract rule 4 — every
    deferred entry is a ``{key, rationale, issue}`` triple) and an optional,
    non-authoritative ``line:`` locator. A missing/empty ``rationale``, ``issue``,
    or ``token`` raises :class:`AllowlistEntryError`.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = raw.get("inline_meta_read") or []
    keys: list[InlineMetaReadKey] = []
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise AllowlistEntryError(f"inline_meta_read[{idx}] is not a mapping (got {entry!r})")
        context = f"inline_meta_read[{idx}]"
        rel_path = _require_str(entry, "file", context)
        qualname = _require_str(entry, "qualname", context)
        token = _require_str(entry, "token", context)
        _require_str(entry, "rationale", context)
        _require_str(entry, "issue", context)
        line = entry.get("line")
        if line is not None and not isinstance(line, int):
            raise AllowlistEntryError(f"{context} ({qualname!r}) has a non-integer line locator {line!r}")
        keys.append(InlineMetaReadKey(rel_path, qualname, token))
    return keys


def load_baseline(path: Path) -> int:
    """Return the recorded pre-sweep baseline scalar (shrink-only governance)."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    value = raw.get("inline_meta_read_baseline")
    if not isinstance(value, int):
        raise AllowlistEntryError(f"inline_meta_read_baseline scalar missing or non-integer in {path.name}")
    return value


def staleness_twin_guard(
    allowlist_keys: set[InlineMetaReadKey], live_keys: set[InlineMetaReadKey]
) -> list[InlineMetaReadKey]:
    """Return allow-list keys with no matching live call site (mechanic 4).

    A non-empty result is a stale-entry failure: the allow-list sanctions a site
    whose frozen token no longer matches any live call site — the entry must be
    evicted (routed away) or re-approved, never left silently masking.
    """
    return sorted(
        allowlist_keys - live_keys, key=lambda k: (k.rel_path, k.enclosing_qualname, k.token)
    )


# --------------------------------------------------------------------------- #
# AST helpers — parent map / qualname / enclosing function.
# --------------------------------------------------------------------------- #
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
        elif isinstance(cur, ast.Lambda):
            chain.append("<lambda>")
    return ".".join(reversed(chain)) if chain else "<module>"


def _enclosing_function(
    parents: dict[int, ast.AST], target: ast.AST
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    cur: ast.AST | None = target
    while cur is not None:
        cur = parents.get(id(cur))
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
    return None


def _callee_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _rel(path: Path) -> str:
    try:
        return path.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_source_files(src_root: Path) -> list[Path]:
    return [p for p in sorted(src_root.rglob("*.py")) if "__pycache__" not in p.parts]


# --------------------------------------------------------------------------- #
# T045 — inline meta-read scanner.
# --------------------------------------------------------------------------- #
def _module_is_json(expr: ast.expr) -> bool:
    """True for a bare ``json`` name or a common alias (``import json as _json``)."""
    return isinstance(expr, ast.Name) and expr.id in ("json", "_json")


def _is_json_loads_call(call: ast.Call) -> bool:
    func = call.func
    return isinstance(func, ast.Attribute) and func.attr == "loads" and _module_is_json(func.value)


def _is_json_load_call(call: ast.Call) -> bool:
    func = call.func
    return isinstance(func, ast.Attribute) and func.attr == "load" and _module_is_json(func.value)


def _assigned_value(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> ast.expr | None:
    """Return the RHS (or ``with ... as name:`` context expr) of *name*'s binding in *fn*.

    Single intra-function hop (contract: def-use tracing is local, not a full
    interprocedural data-flow analysis).
    """
    for node in ast.walk(fn):
        value, targets = _binding_candidate(node)
        for tgt in targets:
            if isinstance(tgt, ast.Name) and tgt.id == name:
                return value
    return None


def _binding_candidate(node: ast.AST) -> tuple[ast.expr | None, list[ast.expr]]:
    """Extract ``(value, targets)`` from an assignment-shaped node, or ``(None, [])``."""
    if isinstance(node, ast.Assign):
        return node.value, list(node.targets)
    if isinstance(node, ast.AnnAssign) and node.value is not None:
        return node.value, [node.target]
    if isinstance(node, ast.With):
        for item in node.items:
            if item.optional_vars is not None:
                return item.context_expr, [item.optional_vars]
    return None, []


def _extract_read_base(expr: ast.expr) -> ast.expr | None:
    """Return the path expression a read call (``.read_text()``/``.open()``/``open()``) reads from."""
    if not isinstance(expr, ast.Call):
        return None
    func = expr.func
    if isinstance(func, ast.Attribute) and func.attr in ("read_text", "open"):
        return func.value
    if isinstance(func, ast.Name) and func.id == "open" and expr.args:
        return expr.args[0]
    return None


def _read_source_base(
    arg: ast.expr, fn: ast.FunctionDef | ast.AsyncFunctionDef | None
) -> ast.expr | None:
    """Resolve *arg* (the sole positional arg to ``json.loads``/``json.load``) to its path base.

    Handles the inline forms (``X.read_text(...)``, ``open(X, ...)``, ``X.open(...)``)
    directly, and a bare ``Name`` resolved one intra-function hop through an
    assignment or a ``with ... as name:`` binding (e.g. ``meta_text =
    meta_path.read_text(...)`` then ``json.loads(meta_text)``, or ``with
    meta_json.open() as f: json.load(f)``).
    """
    resolved = arg
    if isinstance(resolved, ast.Name) and fn is not None:
        bound = _assigned_value(fn, resolved.id)
        if bound is not None:
            resolved = bound
    return _extract_read_base(resolved)


def _is_meta_json_join(expr: ast.expr) -> bool:
    """True for an inline ``<dir> / "meta.json"`` path join."""
    return (
        isinstance(expr, ast.BinOp)
        and isinstance(expr.op, ast.Div)
        and isinstance(expr.right, ast.Constant)
        and expr.right.value == "meta.json"
    )


def is_meta_path_expr(expr: ast.expr) -> bool:
    """True when *expr* is a meta.json path by the contract's two-clause test.

    Either a canonical variable name (``meta_path``/``meta_file``/``meta_json``/
    ``target_meta_path``), or a direct ``<dir> / "meta.json"`` join.
    """
    if isinstance(expr, ast.Name) and expr.id in META_PATH_VAR_NAMES:
        return True
    return _is_meta_json_join(expr)


@dataclass(frozen=True)
class InlineMetaReadSite:
    """One discovered inline ``json.loads``/``json.load`` read of a meta.json path.

    ``lineno`` is a diagnostics locator ONLY — deliberately not part of ``key``.
    """

    rel_path: str
    key: InlineMetaReadKey
    lineno: int


def scan_inline_meta_reads(src_root: Path) -> list[InlineMetaReadSite]:
    """AST-walk ``src/**/*.py`` for inline ``json.loads``/``json.load`` reads of meta.json.

    Excludes :data:`EXCLUDED_REL_PATHS` (the canonical reader's own internals and
    the ``task_utils`` adapter) per the contract.
    """
    sites: list[InlineMetaReadSite] = []
    for path in _iter_source_files(src_root):
        rel = _rel(path)
        if rel in EXCLUDED_REL_PATHS:
            continue
        sites.extend(_scan_file_for_inline_meta_reads(path, rel))
    return sites


def _scan_file_for_inline_meta_reads(path: Path, rel: str) -> list[InlineMetaReadSite]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    parents = _parent_map(tree)
    token_map = code_tokens_by_line(source)
    found: list[InlineMetaReadSite] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not (_is_json_loads_call(node) or _is_json_load_call(node)):
            continue
        fn = _enclosing_function(parents, node)
        base = _read_source_base(node.args[0], fn)
        if base is None or not is_meta_path_expr(base):
            continue
        qualname = _qualname_from_parents(parents, node)
        found.append(
            InlineMetaReadSite(
                rel_path=rel,
                key=InlineMetaReadKey(rel, qualname, token_map.get(node.lineno, "")),
                lineno=node.lineno,
            )
        )
    return found


def check_inline_meta_read_gate(src_root: Path, allowlist: set[InlineMetaReadKey]) -> list[str]:
    """Return violation strings for un-allowlisted inline meta.json reads."""
    violations: list[str] = []
    for site in scan_inline_meta_reads(src_root):
        if site.key in allowlist:
            continue
        violations.append(
            f"{site.rel_path}:{site.lineno} ({site.key.enclosing_qualname}) "
            f"token={site.key.token!r} reads meta.json inline via json.loads/json.load "
            f"instead of mission_metadata.load_meta (or a load_meta_strict/"
            f"load_meta_or_empty adapter) — route it through the canonical reader "
            f"or allow-list it with a rationale + tracked issue"
        )
    return sorted(violations)


def _live_inline_meta_read_keys(src_root: Path) -> set[InlineMetaReadKey]:
    return {site.key for site in scan_inline_meta_reads(src_root)}


# --------------------------------------------------------------------------- #
# Routed-count census (mechanic 3 — anti-mass-allow-list).
# --------------------------------------------------------------------------- #
def scan_routed_load_meta_calls(src_root: Path) -> list[tuple[str, int]]:
    """Return ``[(rel_path, lineno), ...]`` for every call to the routed reader family.

    Deliberately includes ``mission_metadata.py`` — its many internal call sites
    (``load_meta_strict``/``load_meta_or_empty`` delegating to ``load_meta``, and
    its other public helpers reading meta.json through the one canonical
    primitive) ARE genuine routed-usage evidence, distinct from the reader's own
    JSON-parsing implementation (which is what the INLINE scan excludes).
    """
    sites: list[tuple[str, int]] = []
    for path in _iter_source_files(src_root):
        rel = _rel(path)
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node) in ROUTED_CALLEES:
                sites.append((rel, node.lineno))
    return sites


# =========================================================================== #
# TESTS
# =========================================================================== #


# --- unit: composite-key machinery -----------------------------------------
def test_inline_meta_read_key_is_hashable_and_value_keyed() -> None:
    """``InlineMetaReadKey`` compares/hashes by the ``(file, qualname, token)`` triple."""
    a = InlineMetaReadKey("f.py", "Migration.apply", "meta = json . loads ( x )")
    b = InlineMetaReadKey("f.py", "Migration.apply", "meta = json . loads ( x )")
    c = InlineMetaReadKey("f.py", "Migration.apply", "meta = json . loads ( y )")
    assert a == b
    assert hash(a) == hash(b)
    assert a != c
    assert {a, b} == {a}


def test_loader_rejects_entry_without_rationale(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "inline_meta_read:\n"
        "  - file: f.py\n    qualname: foo.bar\n    token: x\n"
        "    line: 10\n    issue: 'https://x/1'\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="rationale"):
        load_allowlist(bad)


def test_loader_rejects_entry_without_issue(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "inline_meta_read:\n"
        "  - file: f.py\n    qualname: foo.bar\n    token: x\n"
        "    line: 10\n    rationale: 'deferred'\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="issue"):
        load_allowlist(bad)


def test_loader_rejects_entry_without_token(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "inline_meta_read:\n"
        "  - file: f.py\n    qualname: foo.bar\n    line: 10\n"
        "    rationale: 'deferred'\n    issue: 'https://x/1'\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="token"):
        load_allowlist(bad)


def test_loader_rejects_non_integer_line(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "inline_meta_read:\n"
        "  - file: f.py\n    qualname: foo.bar\n    token: x\n"
        "    line: not-a-number\n    rationale: 'deferred'\n    issue: 'https://x/1'\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="line locator"):
        load_allowlist(bad)


def test_staleness_twin_guard_flags_stale_entry() -> None:
    live = {InlineMetaReadKey("f.py", "a.b", "t1")}
    stale = staleness_twin_guard({InlineMetaReadKey("f.py", "nonexistent", "gone")}, live)
    assert stale == [InlineMetaReadKey("f.py", "nonexistent", "gone")]


def test_staleness_twin_guard_empty_when_all_live() -> None:
    live = {InlineMetaReadKey("f.py", "a.b", "t1"), InlineMetaReadKey("f.py", "c.d", "t2")}
    assert staleness_twin_guard({InlineMetaReadKey("f.py", "a.b", "t1")}, live) == []


# --- unit: scanner helpers ---------------------------------------------------
def test_is_meta_path_expr_matches_pattern_names() -> None:
    for name in ("meta_path", "meta_file", "meta_json", "target_meta_path"):
        expr = ast.parse(name, mode="eval").body
        assert is_meta_path_expr(expr) is True


def test_is_meta_path_expr_matches_inline_join() -> None:
    expr = ast.parse('feature_dir / "meta.json"', mode="eval").body
    assert is_meta_path_expr(expr) is True


def test_is_meta_path_expr_rejects_unrelated_name() -> None:
    expr = ast.parse("status_path", mode="eval").body
    assert is_meta_path_expr(expr) is False


def test_is_meta_path_expr_rejects_other_join_suffix() -> None:
    expr = ast.parse('feature_dir / "status.json"', mode="eval").body
    assert is_meta_path_expr(expr) is False


def _fn_with_call(src: str) -> tuple[ast.Call, ast.FunctionDef | ast.AsyncFunctionDef | None]:
    tree = ast.parse(src)
    parents = _parent_map(tree)
    call = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and (_is_json_loads_call(n) or _is_json_load_call(n))
    )
    return call, _enclosing_function(parents, call)


def test_read_source_base_direct_read_text() -> None:
    call, fn = _fn_with_call(
        "def f(feature_dir):\n"
        "    meta_path = feature_dir / 'meta.json'\n"
        "    return json.loads(meta_path.read_text(encoding='utf-8'))\n"
    )
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base) is True


def test_read_source_base_direct_open_call() -> None:
    call, fn = _fn_with_call(
        "def f(feature_dir):\n"
        "    meta_path = feature_dir / 'meta.json'\n"
        "    return json.load(open(meta_path, encoding='utf-8'))\n"
    )
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base) is True


def test_read_source_base_traces_named_assignment() -> None:
    """The ``src/charter/_io.py`` shape: a two-hop ``meta_text = meta_path.read_text()``."""
    call, fn = _fn_with_call(
        "def f(feature_dir):\n"
        "    meta_path = feature_dir / 'meta.json'\n"
        "    meta_text = meta_path.read_text(encoding='utf-8')\n"
        "    return json.loads(meta_text)\n"
    )
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base) is True


def test_read_source_base_traces_with_statement_binding() -> None:
    """The migration shape: ``with meta_json.open() as f: json.load(f)``."""
    call, fn = _fn_with_call(
        "def f(feature_dir):\n"
        "    meta_json = feature_dir / 'meta.json'\n"
        "    with meta_json.open() as fh:\n"
        "        return json.load(fh)\n"
    )
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base) is True


def test_read_source_base_returns_none_for_unrelated_read() -> None:
    call, fn = _fn_with_call("def f(status_path):\n    return json.loads(status_path.read_text())\n")
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base) is False


def test_module_is_json_accepts_aliased_import() -> None:
    call, _fn = _fn_with_call(
        "def f(meta_path):\n    return _json.loads(meta_path.read_text())\n"
    )
    assert _is_json_loads_call(call) is True


# --- T045: scanner integration on the real tree -----------------------------
def test_scan_excludes_mission_metadata_and_task_utils() -> None:
    """The scan never reports a site inside the two excluded files."""
    sites = scan_inline_meta_reads(SRC_ROOT)
    assert all(site.rel_path not in EXCLUDED_REL_PATHS for site in sites)


def test_scan_routed_load_meta_calls_counts_call_sites(tmp_path: Path) -> None:
    """Unit check: the routed scanner counts call sites, not definitions or imports."""
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "caller.py").write_text(
        "from specify_cli.mission_metadata import load_meta\n"
        "def load_meta():\n"  # a same-named def is NOT a call
        "    pass\n"
        "def user(feature_dir):\n"
        "    a = load_meta(feature_dir)\n"
        "    b = load_meta_strict(feature_dir)\n"
        "    return a, b\n",
        encoding="utf-8",
    )
    routed = scan_routed_load_meta_calls(tmp_path / "src")
    assert len(routed) == 2  # only the two Call nodes, not the def or the import


# --- T046: gate mechanic 1+2 — concrete floor + margin ----------------------
def test_inline_meta_read_floor() -> None:
    """Concrete CEILING: the live inline-read census stays <= INLINE_META_READ_FLOOR.

    ``INLINE_META_READ_FLOOR`` is a shrink-only ceiling (fewer inline reads is
    progress) — the opposite direction from the canonicalizer's growth-oriented
    floor. A broken scanner returning zero rows trivially satisfies ``<=``, which
    is why mechanic 2 (margin) exists: it independently pins the floor close to
    the live count so it cannot be set to an arbitrarily high, masking value.
    """
    count = len(scan_inline_meta_reads(SRC_ROOT))
    assert count <= INLINE_META_READ_FLOOR, (
        f"inline meta-read census grew to {count}; expected <= {INLINE_META_READ_FLOOR}. "
        "A new inline json.loads/json.load read of meta.json regressed the drain — "
        "route it through mission_metadata.load_meta or allow-list it with a rationale."
    )
    assert INLINE_META_READ_FLOOR - count <= FLOOR_MARGIN, (
        f"INLINE_META_READ_FLOOR ({INLINE_META_READ_FLOOR}) sits more than "
        f"FLOOR_MARGIN ({FLOOR_MARGIN}) above the live count ({count}); tighten the "
        "floor to the honest live census so it cannot mask a future regrowth."
    )


# --- T046: gate mechanic 3 — routed-count floor (anti-mass-allow-list) ------
def test_routed_load_meta_floor() -> None:
    """Concrete floor: routed load_meta*() call sites stay >= ROUTED_LOAD_META_FLOOR.

    Mirrors ``test_routed_count_floor`` in ``test_resolution_authority_gates.py``:
    both bounds are enforced (``live - MARGIN <= floor < live``) so the floor is a
    concrete census integer, never a tautological ``>= len(routed)``.
    """
    routed = scan_routed_load_meta_calls(SRC_ROOT)
    assert len(routed) >= ROUTED_LOAD_META_FLOOR, (
        f"routed load_meta*() census dropped to {len(routed)}; expected "
        f">= {ROUTED_LOAD_META_FLOOR}. A drop means call sites stopped routing "
        "through the canonical reader family."
    )
    assert len(routed) > ROUTED_LOAD_META_FLOOR, (
        "ROUTED_LOAD_META_FLOOR must be a concrete census integer strictly below "
        "the live routed count, not '>= len(routed)' (anti-vacuous)."
    )
    assert len(routed) - ROUTED_LOAD_META_FLOOR <= ROUTED_LOAD_META_FLOOR_MARGIN, (
        f"ROUTED_LOAD_META_FLOOR ({ROUTED_LOAD_META_FLOOR}) is more than "
        f"ROUTED_LOAD_META_FLOOR_MARGIN ({ROUTED_LOAD_META_FLOOR_MARGIN}) below the "
        f"live routed count ({len(routed)}); tighten the floor."
    )


# --- T046: gate mechanic 4 — real-tree allow-list + staleness --------------
def test_inline_meta_read_gate_green_against_seeded_allowlist() -> None:
    """With the seeded allow-list, the gate reports zero violations."""
    allowlist = set(load_allowlist(ALLOWLIST_PATH))
    violations = check_inline_meta_read_gate(SRC_ROOT, allowlist)
    assert violations == [], "\n".join(violations)


def test_allowlist_matches_floor() -> None:
    """The seeded allow-list has exactly ``INLINE_META_READ_FLOOR`` entries.

    Every currently-live inline read is deferred with a rationale — the gate is
    fully accounted for, not merely under the ceiling.
    """
    assert len(load_allowlist(ALLOWLIST_PATH)) == INLINE_META_READ_FLOOR


def test_allowlist_shrink_only() -> None:
    """NFR-003: the seeded allow-list never inflates beyond the pre-sweep baseline."""
    keys = load_allowlist(ALLOWLIST_PATH)
    baseline = load_baseline(ALLOWLIST_PATH)
    assert len(keys) <= baseline, (
        f"inline_meta_read allow-list ({len(keys)}) exceeds baseline ({baseline}) "
        "— entries may only be removed (routed away), never added"
    )


# --- T047 self-test 1/3: a new inline meta read is flagged (plant -> RED) --
def test_new_inline_meta_read_is_flagged(tmp_path: Path) -> None:
    """Gate FAILS on an injected inline read, PASSES once sanctioned (INV-C2)."""
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "planted.py").write_text(
        "class PlantedReader:\n"
        "    def load(self, feature_dir):\n"
        "        meta_path = feature_dir / 'meta.json'\n"
        "        return json.loads(meta_path.read_text(encoding='utf-8'))\n",
        encoding="utf-8",
    )
    scratch_src = tmp_path / "src"

    # Planted, un-sanctioned -> RED.
    violations = check_inline_meta_read_gate(scratch_src, set())
    assert violations, "self-test: a newly-planted inline meta read must be flagged"
    assert any("PlantedReader.load" in v for v in violations)

    # Sanctioned (tool-derived key, never hand-typed) -> GREEN.
    site_key = next(
        s.key
        for s in scan_inline_meta_reads(scratch_src)
        if s.key.enclosing_qualname == "PlantedReader.load"
    )
    assert check_inline_meta_read_gate(scratch_src, {site_key}) == []


# --- T047 self-test 2/3: stale-entry twin-guard on the real allow-list -----
def test_allowlist_entries_are_still_live() -> None:
    """NFR-003 twin-guard: every seeded allow-list entry matches a live site.

    Ships as a self-test per the contract's T047 list: a routed-away entry left
    in the allow-list (masking a drain that already happened) must fail here.
    """
    allowlist = set(load_allowlist(ALLOWLIST_PATH))
    live = _live_inline_meta_read_keys(SRC_ROOT)
    stale = staleness_twin_guard(allowlist, live)
    assert stale == [], f"stale inline_meta_read allow-list entries: {stale}"


# --- T047 self-test 3/3: mass-allow-list attempt is structurally caught ----
def test_routed_count_floor_blocks_mass_allowlist(tmp_path: Path) -> None:
    """Allow-listing every site (instead of routing) manufactures zero routed evidence.

    Simulates the "drain the ceiling by mass-allow-listing" attack: sanction
    every discovered inline-read site in a scratch tree with NO corresponding
    ``load_meta*`` calls. The INLINE gate goes green (every site is
    allow-listed), but the routed-count census computed from the SAME tree
    stays at zero — proving the two mechanics are independent, so a floor tying
    the routed census to the drained count (as ``ROUTED_LOAD_META_FLOOR`` does on
    the real tree) trips RED on this shape of regression.
    """
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "reader.py").write_text(
        "class ScratchReader:\n"
        "    def load(self, feature_dir):\n"
        "        meta_path = feature_dir / 'meta.json'\n"
        "        return json.loads(meta_path.read_text(encoding='utf-8'))\n"
        "    def load_other(self, feature_dir):\n"
        "        meta_file = feature_dir / 'meta.json'\n"
        "        return json.loads(meta_file.read_text(encoding='utf-8'))\n",
        encoding="utf-8",
    )
    scratch_src = tmp_path / "src"

    sites = scan_inline_meta_reads(scratch_src)
    assert len(sites) == 2, "fixture must contain two genuine inline meta reads"

    # "Mass allow-list" the drain: sanction every discovered site instead of
    # routing the code onto load_meta*.
    mass_allowlist = {site.key for site in sites}
    assert check_inline_meta_read_gate(scratch_src, mass_allowlist) == [], (
        "sanity: the mass allow-list must make the INLINE gate green"
    )

    # The routed-count census is INDEPENDENT of the allow-list: mass-allow-listing
    # manufactures zero routing evidence in this fixture.
    routed = scan_routed_load_meta_calls(scratch_src)
    required_routed_floor = len(sites)  # one routed call should replace each drained read
    assert len(routed) < required_routed_floor, (
        "self-test invariant broken: a mass allow-list in this fixture must NOT be "
        "accompanied by genuine routed calls"
    )
    # This is exactly the failure shape ROUTED_LOAD_META_FLOOR catches on the real
    # tree: a floor requiring routed growth reds when routing didn't happen.


# --- timing (fast-tier budget) ----------------------------------------------
def test_gate_runs_under_fast_tier_budget() -> None:
    """Both scans complete well under the 30 s fast-tier ceiling."""
    start = time.monotonic()
    scan_inline_meta_reads(SRC_ROOT)
    scan_routed_load_meta_calls(SRC_ROOT)
    elapsed = time.monotonic() - start
    assert elapsed < 30.0, f"inline meta-read scans took {elapsed:.2f}s (>30s budget)"
