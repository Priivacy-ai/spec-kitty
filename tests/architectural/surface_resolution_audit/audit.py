#!/usr/bin/env python3
"""Mission-surface-resolution callsite audit (WP01 / FR-003).

Run directly::

    python tests/architectural/surface_resolution_audit/audit.py

Exit code ``0`` means the live source tree still matches the committed
inventory; any non-zero exit is an audit failure a reviewer must read.

What this does
--------------
1. AST-walks every ``*.py`` under ``src/specify_cli`` and ``src/mission_runtime``.
2. Discovers two classes of interesting callsite:

   (a) **Internal calls within known resolver files**: resolver function calls
       and topology-blind primitives within the canonical seam modules
       (``RESOLVER_SOURCE_FILES``). These are tracked to ensure the seam files'
       own surface-resolution calls remain correct.

   (b) **Raw-bypass joins**: inline ``KITTY_SPECS_DIR / slug`` path compositions
       outside the canonical resolver itself — i.e. callsites that bypass the
       resolver entirely. These are FR-001 targets.

3. Cross-checks the machine-discovered candidate *files* against the
   hand-curated dispositions in ``inventory.md`` and fails closed if either the
   row count drifts or a known candidate disappears.

Explicitly NOT tracked per-callsite: the hundreds of downstream callers that
legitimately call ``resolve_feature_dir_for_mission`` /
``candidate_feature_dir_for_mission`` / ``resolve_feature_dir_for_slug`` / etc.
These are all "routed-through-resolver" by definition — the inventory's
"Routed caller summary" section covers them in aggregate. The matcher's job
here is to make undercounting of *bypasses* and *resolver-seam internals*
impossible, not to enumerate every blessed call.

Disposition vocabulary (see ``RULESET.md``):
  ``routed-through-resolver``     — goes through the canonical resolver or a
                                    blessed delegator (cite it).
  ``topology-blind-by-design``    — deliberately primary-only; legitimate
                                    (e.g. meta.json reads that must avoid the
                                    coord surface). NAME the reason.
  ``raw-bypass``                  — composes the path itself, bypassing the
                                    resolver. These are FR-001 targets.

Explicitly OUT of scope: ``WorktreeTopology`` / ``classify_worktree_topology``
/ ``read_worktree_registry`` machinery (correct git-registry authority) — do
NOT flag these.

See ``RULESET.md`` for the full seed-set, sink predicate, and known
false-negative classes.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------- #
# Locate the source trees relative to this file (repo-root independent).
# this file: <root>/tests/architectural/surface_resolution_audit/audit.py
# --------------------------------------------------------------------------- #
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[3]
SRC_SPECIFY_CLI = _REPO_ROOT / "src" / "specify_cli"
SRC_MISSION_RUNTIME = _REPO_ROOT / "src" / "mission_runtime"
INVENTORY_PATH = _THIS.parent / "inventory.md"

# --------------------------------------------------------------------------- #
# Canonical resolver / seam source files. Callsites WITHIN these files are
# tracked to ensure the seam implementations themselves remain correct.
# Callsites OUTSIDE these files that call the blessed resolver functions are
# summarized in inventory.md's "Routed caller summary" section, not tracked
# row-by-row. This keeps the inventory manageable while still preventing
# bypass under-counting.
# --------------------------------------------------------------------------- #
_RESOLVER_SOURCE_STEMS: frozenset[str] = frozenset(
    {
        "specify_cli/missions/_read_path_resolver.py",
        # ``feature_dir_resolver.py`` retired in WP07/FR-007: the shim was
        # collapsed into ``_read_path_resolver.py``; its resolvers
        # (``resolve_feature_dir_for_slug`` etc.) now live in that module.
        "specify_cli/coordination/surface_resolver.py",
        "specify_cli/coordination/status_transition.py",
        "specify_cli/status/aggregate.py",
        "mission_runtime/resolution.py",
    }
)

# The read-side SELECTION seam is the SINGLE ``resolve_handle_to_read_path``
# home — only ``_read_path_resolver.py`` legitimately owns the coord-vs-primary
# selection authority. The broader ``_RESOLVER_SOURCE_STEMS`` above stays for the
# RAW-JOIN axis, where ``surface_resolver.py`` / ``status_transition.py`` /
# ``aggregate.py`` / ``mission_runtime/resolution.py`` legitimately *define*
# resolvers — but they are NOT the selection seam. A future direct
# ``resolve_mission_read_path`` call in any of those four must be allowlisted
# (honest) rather than auto-blessed as seam-internal.
_SELECTION_SEAM_STEMS: frozenset[str] = frozenset(
    {
        "specify_cli/missions/_read_path_resolver.py",
    }
)

# --------------------------------------------------------------------------- #
# Seed-set: all blessed resolver function names.
# --------------------------------------------------------------------------- #
RESOLVER_CALLS: frozenset[str] = frozenset(
    {
        "resolve_mission_read_path",
        "candidate_feature_dir_for_mission",
        "resolve_status_surface",
        "resolve_status_surface_with_anchor",
        "resolve_feature_dir_for_slug",
        "resolve_feature_dir_for_mission",
    }
)

# ``primary_feature_dir_for_mission`` is topology-blind-by-design:
# it deliberately targets the primary checkout. Tracked in seam files.
TOPOLOGY_BLIND_CALLS: frozenset[str] = frozenset(
    {
        "primary_feature_dir_for_mission",
    }
)

# --------------------------------------------------------------------------- #
# Read SELECTION authority (FR-006a). ``resolve_mission_read_path`` is the
# existence-gated topology resolver that PICKS the coord-vs-primary read
# surface. The canonical adopted seam ``resolve_handle_to_read_path`` is the
# ONLY sanctioned entry point that callers should reach for; a DIRECT
# ``resolve_mission_read_path(...)`` call in a read path bypasses that seam's
# guard (``assert_safe_path_segment``) + fail-closed coord gate, re-acquiring
# the selection authority outside the single owner.
#
# This is a DIFFERENT discriminator from the raw-path-JOIN scanner above: a
# direct ``resolve_mission_read_path`` call composes NO ``KITTY_SPECS_DIR /
# slug`` path of its own (the resolver does that internally), so the raw-join
# scanner is BLIND to it. ``discover_selection_callsites()`` catches it by
# name, regardless of whether a ``KITTY_SPECS_DIR`` join is present.
# --------------------------------------------------------------------------- #
SELECTION_READ_CALLS: frozenset[str] = frozenset(
    {
        # WP01 (01KVN754) privatized the worker ``resolve_mission_read_path`` →
        # ``_resolve_mission_read_path`` and #2048 retired the historical
        # ``mission_read_path`` shim alias.
        # The discriminator tracks BOTH names so a direct selection call cannot
        # slip the guard by importing the private worker or recreating the old
        # public spelling.
        "resolve_mission_read_path",
        "_resolve_mission_read_path",
    }
)

ALL_BLESSED_CALLS: frozenset[str] = RESOLVER_CALLS | TOPOLOGY_BLIND_CALLS

# --------------------------------------------------------------------------- #
# Raw-bypass seed: local variable names that carry a mission slug and appear
# in a KITTY_SPECS_DIR path join without going through a resolver.
# --------------------------------------------------------------------------- #
SLUG_NAMES: frozenset[str] = frozenset(
    {
        "mission_slug",
        "feature_slug",
        "slug",
        "mission_slug_formatted",
        # ``raw_handle`` / ``handle`` carry the operator-supplied mission handle
        # at the read-CLI primary-meta bootstrap sites (e.g. ``agent/context.py``,
        # ``agent/mission.py``). Omitting them blinded ``discover_rows()`` to three
        # real raw-bypass joins that probe the primary checkout BEFORE the canonical
        # resolver — the same FS-touching shape as the allowlisted ``decision.py``
        # bootstrap (read-side-desync residual; consolidation deferred).
        "raw_handle",
        "handle",
    }
)

# KITTY_SPECS_DIR variable aliases.
KITTY_SPECS_NAMES: frozenset[str] = frozenset(
    {
        "KITTY_SPECS_DIR",
        "kitty_specs_dir",
        "_KITTY_SPECS_DIR",
    }
)


@dataclass(frozen=True)
class ResolutionRow:
    """One discovered mission-surface-resolution callsite."""

    rel_path: str  # relative to _REPO_ROOT/src
    line: int
    call_name: str  # resolver function name or "raw-path-join"
    handle_source: str  # what slug/handle the call uses

    def key(self) -> str:
        return f"{self.rel_path}:{self.line}"


def _rel(path: Path) -> str:
    """Return the path relative to ``_REPO_ROOT/src``."""
    try:
        return path.relative_to(_REPO_ROOT / "src").as_posix()
    except ValueError:
        return path.as_posix()


def _names_in(node: ast.expr) -> set[str]:
    """All ``Name`` ids referenced anywhere inside *node*."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _slug_on_right(node: ast.BinOp) -> str | None:
    """If the right-hand side of a ``/`` op is a slug name, return it."""
    if not isinstance(node.op, ast.Div):
        return None
    if isinstance(node.right, ast.Name) and node.right.id in SLUG_NAMES:
        return node.right.id
    if isinstance(node.right, ast.Attribute) and node.right.attr in SLUG_NAMES:
        return node.right.attr
    return None


def _contains_kitty_specs(node: ast.expr) -> bool:
    """Recursively check if the left subtree has a KITTY_SPECS_DIR reference."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        right_names = _names_in(node.right)
        if right_names & KITTY_SPECS_NAMES:
            return True
        if isinstance(node.right, ast.Constant) and node.right.value == "kitty-specs":
            return True
        return _contains_kitty_specs(node.left)
    return False


def _find_blessed_calls_in_seam(tree: ast.AST, rel_path: str) -> list[ResolutionRow]:
    """Return rows for every blessed resolver call within a seam source file."""
    rows: list[ResolutionRow] = []
    seen: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name: str | None = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name is None or name not in ALL_BLESSED_CALLS:
            continue
        # Derive handle_source from the first positional arg (slug param).
        handle_source = "unknown"
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Name):
                handle_source = first_arg.id
            elif isinstance(first_arg, ast.Attribute):
                handle_source = ast.unparse(first_arg)
            elif isinstance(first_arg, ast.Constant):
                handle_source = repr(first_arg.value)
            else:
                handle_source = ast.unparse(first_arg)
        # resolve_mission_read_path: slug is the second positional arg.
        if name == "resolve_mission_read_path" and len(node.args) >= 2:
            slug_arg = node.args[1]
            handle_source = slug_arg.id if isinstance(slug_arg, ast.Name) else ast.unparse(slug_arg)
        row = ResolutionRow(rel_path, node.lineno, name, handle_source)
        if row.key() not in seen:
            seen.add(row.key())
            rows.append(row)
    return rows


def _find_raw_bypasses(tree: ast.AST, rel_path: str) -> list[ResolutionRow]:
    """Return rows for raw ``KITTY_SPECS_DIR / slug`` path joins in any file.

    A join is a raw bypass when it composes a mission-surface directory from a
    slug variable WITHOUT the IMMEDIATE call going through a resolver function.
    The join is flagged when the slug appears on the RHS of a ``/`` and the
    left subtree contains a ``KITTY_SPECS_DIR`` reference.
    """
    rows: list[ResolutionRow] = []
    seen: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
            continue
        slug = _slug_on_right(node)
        if slug is None:
            continue
        if not _contains_kitty_specs(node.left):
            continue
        row = ResolutionRow(rel_path, node.lineno, "raw-path-join", slug)
        if row.key() not in seen:
            seen.add(row.key())
            rows.append(row)
    return rows


def _audit_file(path: Path) -> list[ResolutionRow]:
    """Audit one source file; return discovered resolution callsites."""
    rel = _rel(path)
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, OSError):
        return []

    rows: list[ResolutionRow] = []
    # Track blessed resolver calls only within the canonical seam source files.
    if rel in _RESOLVER_SOURCE_STEMS:
        rows.extend(_find_blessed_calls_in_seam(tree, rel))
    # Track raw-bypass joins in ALL files (the exhaustive bypass check).
    rows.extend(_find_raw_bypasses(tree, rel))

    # Deduplicate by key.
    seen: set[str] = set()
    result: list[ResolutionRow] = []
    for r in rows:
        if r.key() not in seen:
            seen.add(r.key())
            result.append(r)
    return result


def discover_rows() -> list[ResolutionRow]:
    """AST-walk the source trees and return every discovered row, sorted."""
    rows: list[ResolutionRow] = []
    for src_root in (SRC_SPECIFY_CLI, SRC_MISSION_RUNTIME):
        if not src_root.exists():
            continue
        for path in sorted(src_root.rglob("*.py")):
            rows.extend(_audit_file(path))
    rows.sort(key=lambda r: (r.rel_path, r.line))
    return rows


# --------------------------------------------------------------------------- #
# FR-006a — read SELECTION callsite discriminator.
#
# Distinct from the raw-path-JOIN scanner: this walks for DIRECT calls to the
# read-selection authority (``resolve_mission_read_path``) regardless of any
# ``KITTY_SPECS_DIR`` join. A direct call is a SELECTION-authority acquisition
# outside the ``resolve_handle_to_read_path`` seam.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SelectionRow:
    """One discovered direct read-SELECTION callsite (``resolve_mission_read_path``)."""

    rel_path: str  # relative to _REPO_ROOT/src
    line: int
    call_name: str
    in_seam_file: bool  # True when the callsite is inside a RESOLVER_SOURCE_STEMS file

    def key(self) -> str:
        return f"{self.rel_path}:{self.line}"


def _find_selection_calls(tree: ast.AST, rel_path: str) -> list[SelectionRow]:
    """Return rows for every direct read-SELECTION call in *one* file."""
    in_seam = rel_path in _SELECTION_SEAM_STEMS
    rows: list[SelectionRow] = []
    seen: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name: str | None = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name is None or name not in SELECTION_READ_CALLS:
            continue
        row = SelectionRow(rel_path, node.lineno, name, in_seam)
        if row.key() not in seen:
            seen.add(row.key())
            rows.append(row)
    return rows


def discover_selection_callsites() -> list[SelectionRow]:
    """AST-walk the source trees for DIRECT read-SELECTION calls, sorted.

    Returns every direct ``resolve_mission_read_path(...)`` callsite — the
    read-side SELECTION authority — across ``src/specify_cli`` and
    ``src/mission_runtime``. Callers should reach the selection authority ONLY
    through the ``resolve_handle_to_read_path`` seam (which adds the traversal
    guard + fail-closed coord gate); a direct call re-acquires the authority
    outside the single owner. The ``in_seam_file`` flag distinguishes the
    legitimate seam-internal definitions from external bypasses.
    """
    rows: list[SelectionRow] = []
    for src_root in (SRC_SPECIFY_CLI, SRC_MISSION_RUNTIME):
        if not src_root.exists():
            continue
        for path in sorted(src_root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, OSError):
                continue
            rows.extend(_find_selection_calls(tree, _rel(path)))
    rows.sort(key=lambda r: (r.rel_path, r.line))
    return rows


# --------------------------------------------------------------------------- #
# Known-candidate presence (anti-undercount tripwire). Each file listed here
# MUST surface at least one discovered row, OR carry an explicit disposition
# row in the inventory. Exit non-zero if any is missing from both.
# --------------------------------------------------------------------------- #
KNOWN_CANDIDATE_FILES: tuple[str, ...] = (
    "specify_cli/missions/_read_path_resolver.py",
    # ``feature_dir_resolver.py`` retired in WP07/FR-007 (shim collapsed into
    # ``_read_path_resolver.py``) — no longer a tracked candidate file.
    "specify_cli/coordination/surface_resolver.py",
    "specify_cli/coordination/status_transition.py",
    "specify_cli/status/aggregate.py",
    "mission_runtime/resolution.py",
)


# --------------------------------------------------------------------------- #
# FR-006a — blessed EXTERNAL read-SELECTION callsites (outside the seam files).
#
# Seam-internal ``resolve_mission_read_path`` calls (``in_seam_file``) are
# auto-blessed (they ARE the seam definitions). Direct calls OUTSIDE the seam
# files re-acquire the read-selection authority and MUST be justified here by
# ``<rel_path>:<line>``. Every external selection callsite not listed here is a
# bypass of the ``resolve_handle_to_read_path`` seam (FR-006a regression).
# --------------------------------------------------------------------------- #
# WP01 (01KVN754) DRAINED both formerly-blessed external selection callsites by
# rerouting them onto the ``resolve_handle_to_read_path`` seam:
#   * ``specify_cli/acceptance/__init__.py`` (``_status_read_feature_dir``) now
#     calls ``resolve_handle_to_read_path`` directly; the lenient
#     ``status_dir if status_dir.exists() else feature_dir`` fallback is
#     preserved AROUND the seam call (the seam's ``require_exists=False`` default
#     keeps the byte-identical not-found→primary-candidate behaviour).
#   * ``mission_runtime/resolution.py`` (``_resolve_mission_slug``) now calls
#     ``resolve_handle_to_read_path`` and keeps its StatusReadPathNotFound /
#     MissionSelectorAmbiguous → ActionContextError boundary translation.
# With both rerouted, there are ZERO external direct selection callsites — the
# allowlist is intentionally empty (every direct call is now seam-internal).
ALLOWLISTED_SELECTION_CALLSITES: dict[str, str] = {}


# --------------------------------------------------------------------------- #
# Inventory parser.
# --------------------------------------------------------------------------- #

VALID_DISPOSITIONS: frozenset[str] = frozenset(
    {
        "routed-through-resolver",
        "topology-blind-by-design",
        "raw-bypass",
    }
)


def _parse_inventory_rows(text: str) -> list[dict[str, str]]:
    """Parse the markdown table in ``inventory.md`` into row dicts.

    The table has the header:
    ``| file:line | handle source | sink | disposition | rationale |``
    """
    rows: list[dict[str, str]] = []
    in_table = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("| file:line "):
            in_table = True
            continue
        if in_table and line.replace(" ", "").startswith("|---"):
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 5:
                continue
            rows.append(
                {
                    "locator": cells[0],
                    "handle_source": cells[1],
                    "sink": cells[2],
                    "disposition": cells[3],
                    "rationale": cells[4],
                }
            )
    return rows


def _fail(messages: list[str]) -> int:
    print("AUDIT FAILED", file=sys.stderr)
    for msg in messages:
        print(f"  - {msg}", file=sys.stderr)
    return 1


def main() -> int:  # noqa: C901 — linear validation block; each check is flat
    errors: list[str] = []

    discovered = discover_rows()
    discovered_files = {r.rel_path for r in discovered}

    if not INVENTORY_PATH.exists():
        return _fail([f"inventory.md missing at {INVENTORY_PATH}"])

    inventory_rows = _parse_inventory_rows(INVENTORY_PATH.read_text(encoding="utf-8"))

    # ---- Check 1: every row carries exactly one valid disposition. -----------
    for row in inventory_rows:
        disp = row["disposition"]
        if disp not in VALID_DISPOSITIONS:
            errors.append(
                f"row {row['locator']!r} has invalid/missing disposition {disp!r} "
                f"(must be one of: {', '.join(sorted(VALID_DISPOSITIONS))})"
            )

    # ---- Check 2: every AST-discovered row appears in the inventory. ---------
    inventory_keys = {r["locator"] for r in inventory_rows}
    for sink in discovered:
        locator = f"{sink.rel_path}:{sink.line}"
        if not any(locator == k or k.startswith(locator) for k in inventory_keys):
            errors.append(
                f"discovered callsite {locator} "
                f"({sink.call_name}, handle={sink.handle_source}) "
                f"is MISSING from inventory.md (undercount tripwire)"
            )

    # ---- Check 3: known-candidate presence (self-asserting tripwire). --------
    for cand in KNOWN_CANDIDATE_FILES:
        in_discovered = cand in discovered_files
        in_inventory = any(r["locator"].startswith(cand) for r in inventory_rows)
        if not (in_discovered or in_inventory):
            errors.append(
                f"known candidate {cand!r} absent from BOTH discovered rows and inventory"
            )

    # ---- Check 4: read-SELECTION authority outside the seam (FR-006a). -------
    # Every direct ``resolve_mission_read_path`` call outside the seam files
    # must be allowlisted; seam-internal calls are auto-blessed.
    for sel in discover_selection_callsites():
        if sel.in_seam_file:
            continue
        if sel.key() not in ALLOWLISTED_SELECTION_CALLSITES:
            errors.append(
                f"direct read-SELECTION call {sel.key()} ({sel.call_name}) "
                "outside the resolve_handle_to_read_path seam and not in "
                "ALLOWLISTED_SELECTION_CALLSITES (FR-006a bypass)"
            )

    if errors:
        return _fail(errors)

    routed = sum(1 for r in inventory_rows if r["disposition"] == "routed-through-resolver")
    blind = sum(1 for r in inventory_rows if r["disposition"] == "topology-blind-by-design")
    bypass = sum(1 for r in inventory_rows if r["disposition"] == "raw-bypass")
    print(
        f"AUDIT OK: {len(inventory_rows)} inventory rows "
        f"({len(discovered)} AST-discovered); "
        f"routed-through-resolver={routed} "
        f"topology-blind-by-design={blind} "
        f"raw-bypass={bypass}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
