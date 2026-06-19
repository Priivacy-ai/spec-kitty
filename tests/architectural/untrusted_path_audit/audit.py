#!/usr/bin/env python3
"""Reproducible untrusted-segment -> filesystem-sink audit (WP01 / FR-003, FR-004).

Run directly::

    python tests/architectural/untrusted_path_audit/audit.py

Exit code ``0`` means the live source tree still matches the committed
inventory; any non-zero exit is an audit failure a reviewer must read.

What this does
--------------
1. AST-walks every ``*.py`` under ``src/specify_cli``.
2. Flags a call site as an *untrusted -> FS sink* when an **untrusted path
   segment** (see ``UNTRUSTED_SEGMENT_NAMES`` / ``UNTRUSTED_SOURCE_CALLS``)
   reaches a **filesystem sink** -- either:
     * an inline ``<path-expr> / <untrusted-segment>`` ``BinOp`` join, or
     * a sink method/builtin (``open`` / ``read_text`` / ``write_text`` /
       ``mkdir`` / ``unlink`` / ``shutil.copy|move|rmtree`` / ...) invoked on a
       path that was built from an untrusted segment, including **one hop of
       local-variable aliasing** (``slug = meta.get("mission_slug"); root / slug``).
3. Cross-checks the machine-discovered candidate *files* against the
   hand-curated dispositions in ``inventory.md`` and fails closed if either the
   row count drifts or a known candidate disappears.

The disposition of each row (``routed-through-seam`` / ``routed-through-seam
(TODO)`` / ``trusted-source`` / ``unreachable``) is a human judgement that was
verified against the real source; it lives in ``inventory.md`` and in
``DISPOSITIONS`` below, NOT inferred by the matcher. The matcher's job is to
make undercounting (a thin/circular audit) impossible, not to classify intent.

See ``RULESET.md`` for the seed-set, the sink predicate, and -- importantly --
the *known false-negative classes* (what this matcher does NOT trace).
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------- #
# Locate the source tree relative to this file (repo-root independent).
# this file: <root>/tests/architectural/untrusted_path_audit/audit.py
# --------------------------------------------------------------------------- #
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[3]
SRC_ROOT = _REPO_ROOT / "src" / "specify_cli"
INVENTORY_PATH = _THIS.parent / "inventory.md"

# --------------------------------------------------------------------------- #
# Seed-set: untrusted source symbols (RULESET.md section "Seed-set").
# A *named* segment in this set may NEVER be classified ``trusted-source``
# (T003 Named-untrusted rule / SC-003).
# --------------------------------------------------------------------------- #
UNTRUSTED_SEGMENT_NAMES: frozenset[str] = frozenset(
    {
        "mission_slug",
        "feature_slug",
        "wp_id",
        "wp_slug",
        "slug",
        "run_id",
        "review_ref",
    }
)

# Untrusted source *calls* / attribute reads: ``meta.get("mission_slug")``,
# ``snapshot.mission_slug``, ``lifecycle.mission_slug`` etc. We match by the
# trailing attribute/argument name so the audit stays general.
UNTRUSTED_ATTR_NAMES: frozenset[str] = frozenset(
    {
        "mission_slug",
        "feature_slug",
        "wp_id",
        "wp_slug",
    }
)

# Sink method names invoked on a Path (``path.write_text(...)`` etc.).
SINK_METHODS: frozenset[str] = frozenset(
    {
        "open",
        "read_text",
        "read_bytes",
        "write_text",
        "write_bytes",
        "mkdir",
        "unlink",
        "touch",
        "replace",
    }
)

# Sink free functions / qualified calls (``shutil.copy`` / ``atomic_write`` /
# builtin ``open``). Matched by trailing attribute name OR bare name.
SINK_FUNCTIONS: frozenset[str] = frozenset(
    {
        "open",
        "copy",
        "copy2",
        "copyfile",
        "move",
        "rmtree",
        "atomic_write",
        "write_text_within_directory",
    }
)


@dataclass(frozen=True)
class SinkRow:
    """One discovered untrusted-segment -> FS-sink call site."""

    rel_path: str
    line: int
    untrusted_source: str
    sink_op: str

    def key(self) -> str:
        return f"{self.rel_path}:{self.line}:{self.sink_op}"


def _segment_name(node: ast.expr) -> str | None:
    """Return the untrusted-segment name for *node*, else None.

    Recognises:
      * ``mission_slug`` (a seed Name),
      * ``snapshot.mission_slug`` (Attribute whose attr is untrusted),
      * ``meta.get("mission_slug")`` (Call to ``.get`` with an untrusted literal).
    """
    if isinstance(node, ast.Name) and node.id in UNTRUSTED_SEGMENT_NAMES:
        return node.id
    if isinstance(node, ast.Attribute) and node.attr in UNTRUSTED_ATTR_NAMES:
        return node.attr
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"get", "__getitem__"}
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
        and node.args[0].value in UNTRUSTED_ATTR_NAMES
    ):
        return f'.get({node.args[0].value!r})'
    return None


def _collect_tainted_locals(tree: ast.AST) -> dict[str, str]:
    """One hop of aliasing: ``local = <untrusted-source>`` -> {local: source}.

    Also follows ``local = <untrusted-source> or fallback`` (BoolOp), the
    ``snapshot.mission_slug or feature_dir.name`` idiom used by the derived-view
    writers, because the tainted operand still flows into ``local``.
    """
    tainted: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        source = _segment_name(node.value)
        if source is None and isinstance(node.value, ast.BoolOp):
            for operand in node.value.values:
                source = _segment_name(operand)
                if source is not None:
                    break
        if source is not None:
            tainted[target.id] = source
    return tainted


def _names_in(node: ast.expr) -> set[str]:
    """All ``Name`` ids referenced anywhere inside *node*."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _join_taint(node: ast.expr, tainted: dict[str, str]) -> str | None:
    """Return the untrusted source if *node* is/contains a ``path / segment`` join.

    Matches ``<expr> / <untrusted>`` where ``<untrusted>`` is a direct seed
    segment OR a one-hop tainted local. Recurses into the left operand so
    ``root / a / mission_slug`` and ``root / slug / "meta.json"`` both match.
    """
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
        return None
    # Right operand directly untrusted?
    direct = _segment_name(node.right)
    if direct is not None:
        return direct
    if isinstance(node.right, ast.Name) and node.right.id in tainted:
        return f"{node.right.id}={tainted[node.right.id]}"
    # Recurse left so deeper joins are still caught.
    return _join_taint(node.left, tainted)


def _sink_func_name(call: ast.Call) -> str | None:
    """Return the sink-function name for a free/qualified call, else None."""
    func = call.func
    if isinstance(func, ast.Name) and func.id in SINK_FUNCTIONS:
        return func.id
    if isinstance(func, ast.Attribute) and func.attr in SINK_FUNCTIONS:
        return func.attr
    return None


def _audit_file(path: Path) -> list[SinkRow]:
    rel = path.relative_to(SRC_ROOT).as_posix()
    rows: list[SinkRow] = []
    seen: set[str] = set()
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    tainted = _collect_tainted_locals(tree)
    tainted_locals = set(tainted)

    def _record(line: int, untrusted: str, sink_op: str) -> None:
        row = SinkRow(rel, line, untrusted, sink_op)
        if row.key() not in seen:
            seen.add(row.key())
            rows.append(row)

    for node in ast.walk(tree):
        # (a) ``path / untrusted-segment`` join expressions (the path-build sink).
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            src = _join_taint(node, tainted)
            if src is not None:
                _record(node.lineno, src, "Path-join (/)")

        # (b) sink-method call on a receiver built from an untrusted segment.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in SINK_METHODS
        ):
            recv = node.func.value
            recv_names = _names_in(recv)
            hit = _join_taint(recv, tainted)
            if hit is None and recv_names & tainted_locals:
                local = next(iter(recv_names & tainted_locals))
                hit = f"{local}={tainted[local]}"
            if hit is not None:
                _record(node.lineno, hit, f".{node.func.attr}()")

        # (c) sink free-function / qualified call with an untrusted-built arg.
        if isinstance(node, ast.Call):
            fname = _sink_func_name(node)
            if fname is not None:
                for arg in node.args:
                    src = _join_taint(arg, tainted)
                    if src is None and isinstance(arg, ast.Name) and arg.id in tainted:
                        src = f"{arg.id}={tainted[arg.id]}"
                    if src is not None:
                        _record(node.lineno, src, f"{fname}(...)")
                        break
    return rows


def discover_rows() -> list[SinkRow]:
    """AST-walk the source tree and return every discovered sink row, sorted."""
    rows: list[SinkRow] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        rows.extend(_audit_file(path))
    rows.sort(key=lambda r: (r.rel_path, r.line, r.sink_op))
    return rows


# --------------------------------------------------------------------------- #
# Known candidates (T004 anti-undercount tripwire). Each MUST surface at least
# one discovered row whose rel_path matches, OR carry an explicit
# disposition row in the inventory (the ``meta.json`` write-path is an FS sink
# keyed on ``feature_dir``, not a literal slug join, so it is asserted by
# inventory presence rather than by AST discovery -- see RULESET false-negatives).
# --------------------------------------------------------------------------- #
KNOWN_CANDIDATE_FILES: tuple[str, ...] = (
    # events/decision_log.py — removed from tripwire: WP03 added
    # assert_safe_path_segment before the slug join; no sinks remain.
    # dossier/drift_detector.py — removed from tripwire: WP03 added
    # assert_safe_path_segment in save_baseline/load_baseline; no sinks remain.
    "coordination/surface_resolver.py",
    "missions/_read_path_resolver.py",
    "migration/mission_state.py",
    "review/cycle.py",
    "review/arbiter.py",
    "post_merge/review_artifact_consistency.py",
    "status/store.py",
    "status/views.py",
    "status/lifecycle.py",
    "status/aggregate.py",  # _find_meta_path composed-path reads
)

# The FR-009 meta.json slug source (top-level mission_metadata.py): asserted by
# inventory presence and required to carry the routed-through-seam (TODO) tag.
FR009_META_FILE = "mission_metadata.py"


def _parse_inventory_rows(text: str) -> list[dict[str, str]]:
    """Parse the markdown sink table in inventory.md into row dicts.

    The table has the header ``| file:line | untrusted source | sink op | disposition | rationale |``.
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
                    "source": cells[1],
                    "sink_op": cells[2],
                    "disposition": cells[3],
                    "rationale": cells[4],
                }
            )
    return rows


VALID_DISPOSITIONS = {
    "routed-through-seam",
    "routed-through-seam (TODO)",
    "trusted-source",
    "unreachable",
}

NAMED_UNTRUSTED = {"mission_slug", "feature_slug", "wp_id"}


def _fail(messages: list[str]) -> int:
    print("AUDIT FAILED", file=sys.stderr)
    for msg in messages:
        print(f"  - {msg}", file=sys.stderr)
    return 1


def main() -> int:  # noqa: C901 - linear validation block, each check is flat
    errors: list[str] = []

    discovered = discover_rows()
    discovered_files = {r.rel_path for r in discovered}

    if not INVENTORY_PATH.exists():
        return _fail([f"inventory.md missing at {INVENTORY_PATH}"])

    inventory_rows = _parse_inventory_rows(INVENTORY_PATH.read_text(encoding="utf-8"))

    # ---- Check 1: every row carries exactly one valid disposition (SC-003). ----
    for row in inventory_rows:
        disp = row["disposition"]
        if disp not in VALID_DISPOSITIONS:
            errors.append(
                f"row {row['locator']!r} has invalid/missing disposition {disp!r}"
            )
        # Named-untrusted rule: a named untrusted source may never be trusted-source.
        if disp == "trusted-source":
            src = row["source"]
            named = {n for n in NAMED_UNTRUSTED if n in src}
            # ``feature_dir.name`` / ``mission_dir.name`` are derived/trusted even
            # though the token ``mission`` appears; only a bare named segment trips.
            bare_named = {n for n in named if f"{n}.name" not in src and ".name" not in src}
            if bare_named:
                errors.append(
                    f"row {row['locator']!r} classifies named-untrusted "
                    f"{sorted(bare_named)} as trusted-source (SC-003 violation)"
                )

    # ---- Check 2: count consistency (no silently dropped discovered rows). ----
    # Every AST-discovered row MUST appear in the inventory by locator key.
    inventory_keys = {r["locator"] for r in inventory_rows}
    for sink in discovered:
        locator = f"{sink.rel_path}:{sink.line}"
        # Allow either exact line or the documented "see note" composed forms.
        if not any(locator == k or k.startswith(locator) for k in inventory_keys):
            errors.append(
                f"discovered sink {locator} ({sink.sink_op}, src={sink.untrusted_source}) "
                f"is MISSING from inventory.md (undercount tripwire)"
            )

    # ---- Check 3: known-candidate presence (anti-undercount tripwire). ----
    for cand in KNOWN_CANDIDATE_FILES:
        in_discovered = cand in discovered_files
        in_inventory = any(r["locator"].startswith(cand) for r in inventory_rows)
        if not (in_discovered or in_inventory):
            errors.append(
                f"known candidate {cand!r} absent from BOTH discovered rows and inventory"
            )

    # ---- Check 4: FR-009 meta.json source present + tagged routed-through-seam (TODO). ----
    fr009_rows = [r for r in inventory_rows if r["locator"].startswith(FR009_META_FILE)]
    if not fr009_rows:
        errors.append(
            f"FR-009 candidate {FR009_META_FILE!r} (meta.json slug source) "
            f"absent from inventory"
        )
    elif not any(r["disposition"] == "routed-through-seam (TODO)" for r in fr009_rows):
        errors.append(
            f"FR-009 {FR009_META_FILE!r} row(s) must be tagged "
            f"'routed-through-seam (TODO)' (the write-path bypass WP02 fixes)"
        )

    if errors:
        return _fail(errors)

    todo = sum(1 for r in inventory_rows if r["disposition"] == "routed-through-seam (TODO)")
    safe = sum(1 for r in inventory_rows if r["disposition"] == "routed-through-seam")
    trusted = sum(1 for r in inventory_rows if r["disposition"] == "trusted-source")
    unreachable = sum(1 for r in inventory_rows if r["disposition"] == "unreachable")
    print(
        f"AUDIT OK: {len(inventory_rows)} inventory rows "
        f"({len(discovered)} AST-discovered); "
        f"TODO(fix)={todo} safe={safe} trusted={trusted} unreachable={unreachable}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
