#!/usr/bin/env python3
"""Recorded converter / freshen tool for the surface-resolution ``inventory.md``.

This is the RECORDED CONVERTER referenced in the inventory header (IC-03 re-key,
mission ``refactor-stable-gate-substrate-01KWK3FY`` / FR-004). It regenerates the
two gated tables (the sink table and the read-SELECTION table) from the LIVE
``discover_rows()`` / ``discover_selection_callsites()`` scan so that every stored
``qualname`` + ``token`` identity is TOOL-DERIVED via ``composite_key_from_file``
— never hand-typed (data-model tool-derivation invariant).

Run to freshen after a legitimate seam edit::

    python tests/architectural/surface_resolution_audit/rekey_inventory.py            # regenerate
    python tests/architectural/surface_resolution_audit/rekey_inventory.py --check    # diff-only

The ``line`` in each locator is a NON-authoritative jump-to convenience; the audit
compares only the drift-proof ``(rel_path, qualname, token)`` composite, so a
``+1`` line drift never trips the tripwire (the #2306 failure class).

Dispositions are the established human judgements encoded as a rule
(``primary_feature_dir_for_mission`` → topology-blind; the ``_coord_mid8`` raise
payloads → raw-bypass diagnostic; the seam-grammar output → routed; everything
else routes through the coord-aware resolver). Spot-check them against source.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_THIS = Path(__file__).resolve()
_AUDIT_PATH = _THIS.parent / "audit.py"
_INVENTORY_PATH = _THIS.parent / "inventory.md"


def _load_audit() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_surface_audit_rekey", _AUDIT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _disposition(rel_path: str, call_name: str) -> str:
    """Encode the established per-callsite disposition judgement as a rule."""
    if call_name == "raw-path-join":
        if rel_path.endswith("coordination/surface_resolver.py"):
            return "raw-bypass"
        if rel_path.endswith("missions/_read_path_resolver.py"):
            return "topology-blind-by-design"
        if rel_path.endswith("core/mission_creation.py"):
            return "routed-through-resolver"
        return "raw-bypass"
    if call_name == "primary_feature_dir_for_mission":
        return "topology-blind-by-design"
    return "routed-through-resolver"


def _rationale(rel_path: str, qualname: str, call_name: str, disposition: str) -> str:
    """Accurate, honest rationale derived from the disposition rule + source facts."""
    if call_name == "raw-path-join" and disposition == "raw-bypass":
        return (
            f"`{qualname}` composes KITTY_SPECS_DIR/slug inline ONLY for a "
            "fail-closed `StatusReadPathNotFound` diagnostic `raise` payload — the "
            "path is never opened (no FS sink; operationally safe)."
        )
    if call_name == "raw-path-join" and rel_path.endswith("_read_path_resolver.py"):
        return (
            f"`{qualname}` IS the topology-blind primitive definition "
            "(`primary_feature_dir_for_mission`); `assert_safe_path_segment` guards "
            "the slug just above the join (NFR-002); deliberately primary-only."
        )
    if call_name == "raw-path-join" and rel_path.endswith("mission_creation.py"):
        return (
            f"`{qualname}` joins `mission_slug_formatted`, the OUTPUT of the canonical "
            "`mission_dir_name` grammar seam (FR-032/FR-044) — not a raw operator "
            "slug; create-time-canonical (the dir is being created here)."
        )
    if disposition == "topology-blind-by-design":
        return (
            f"`{qualname}` composes/reads the PRIMARY checkout through the blessed "
            "topology-blind `primary_feature_dir_for_mission` constructor (the coord "
            "surface carries no `meta.json`; C-GUARD-3a split-brain rationale)."
        )
    return (
        f"`{qualname}` delegates to `{call_name}` — the coord-aware canonical "
        "resolver / surface authority (routed; no inline path composition)."
    )


def _cell(value: str) -> str:
    """Backtick-wrap an identity cell (the audit parser strips the backticks)."""
    return f"`{value}`"


def _render_sink_table(audit: ModuleType) -> tuple[str, dict[str, int]]:
    lines = [
        "| file:line | qualname | token | handle source | sink | disposition | rationale |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    counts = {"routed-through-resolver": 0, "topology-blind-by-design": 0, "raw-bypass": 0}
    for row in audit.discover_rows():
        _rel, qualname, token = audit._composite_from_file(row.rel_path, row.line)
        disp = _disposition(row.rel_path, row.call_name)
        counts[disp] += 1
        rationale = _rationale(row.rel_path, qualname, row.call_name, disp)
        lines.append(
            f"| {row.rel_path}:{row.line} | {_cell(qualname)} | {_cell(token)} "
            f"| {row.handle_source} | {row.call_name} | {disp} | {rationale} |"
        )
    return "\n".join(lines), counts


def _render_selection_table(audit: ModuleType) -> tuple[str, int]:
    lines = [
        "| file:line | qualname | token | in seam file | disposition | notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    count = 0
    for sel in audit.discover_selection_callsites():
        _rel, qualname, token = audit._composite_from_file(sel.rel_path, sel.line)
        count += 1
        in_seam = "yes" if sel.in_seam_file else "no"
        disp = (
            "seam-internal (auto-blessed)"
            if sel.in_seam_file
            else "BLESSED-EXTERNAL (must be allowlisted)"
        )
        note = (
            f"direct `{sel.call_name}` inside `{qualname}` — the seam definition."
            if sel.in_seam_file
            else f"external `{sel.call_name}` in `{qualname}` — allowlist or refactor."
        )
        lines.append(
            f"| {sel.rel_path}:{sel.line} | {_cell(qualname)} | {_cell(token)} "
            f"| {in_seam} | {disp} | {note} |"
        )
    return "\n".join(lines), count


# Preserved, point-in-time documentation sections (NOT gated by the audit).
_ROUTED_CALLER_SUMMARY = """\
## Routed caller summary

The many downstream callers that reach a blessed resolver
(`resolve_feature_dir_for_mission` / `candidate_feature_dir_for_mission` /
`resolve_feature_dir_for_slug` / `resolve_handle_to_read_path` /
`resolve_status_surface`) OUTSIDE the seam files are classified
`routed-through-resolver` by definition — they delegate without inline path
composition. They are covered in aggregate here (a point-in-time reviewer
reference), NOT gated per-row: the audit's job is to make bypass under-counting
and ghost over-documentation impossible, not to enumerate every blessed call.
The heaviest routed callers are the CLI command modules
(`cli/commands/agent/tasks.py`, `cli/commands/agent/workflow.py`,
`cli/commands/merge.py`, `cli/commands/implement.py`) plus `workspace/context.py`
and `acceptance/__init__.py`.

## Audited-surface list anchor

The stable surface list WP08's guard anchors on is maintained as a separate
machine-readable artifact: `audited-surfaces.md`.
"""


def _render_inventory(audit: ModuleType) -> str:
    sink_table, counts = _render_sink_table(audit)
    selection_table, sel_count = _render_selection_table(audit)
    total = sum(counts.values())
    header = f"""\
# Mission-surface-resolution callsite inventory (WP01 / FR-003; IC-03 re-key FR-004)

Generated input: `python tests/architectural/surface_resolution_audit/audit.py`
walks `src/specify_cli` and `src/mission_runtime`. The audit tracks:

1. **All resolver/topology-blind calls inside the canonical seam source files**
   (`RESOLVER_SOURCE_STEMS` in `audit.py`).
2. **All raw-bypass path joins** (`KITTY_SPECS_DIR / slug`) anywhere in the
   source trees.
3. **All direct read-SELECTION callsites** (`resolve_mission_read_path`) via
   `discover_selection_callsites()` (FR-006a).

## Design-P: drift-proof identity + freshen procedure (IC-03)

> **Row identity is the `(rel_path, enclosing_qualname, token)` composite** derived
> by `composite_key_from_file` — NOT the `file:line` locator. The `line` in each
> locator is a NON-authoritative jump-to convenience and is **never compared**;
> a blank/comment-line insertion above a callsite shifts the line but keeps the
> composite identical, so the audit stays GREEN (the #2306 failure class is fixed).
> The `qualname` and `token` columns carry the frozen comparand; both are stored
> backtick-wrapped for readability and the audit parser strips the backticks.
>
> **Both tripwire directions are gated** (per audit, IC-02/03):
> - **Undercount** — every DISCOVERED callsite must match an inventory row by
>   composite identity, else RED.
> - **Overcount / ghost** — every inventory row (minus `[inventory-only]`-tagged
>   rows) must match a LIVE discovered callsite, else RED. A `[inventory-only]`
>   tag in the notes/rationale exempts a row that documents an intentionally
>   removed sink; each tagged row must cite the removing change. Zero rows are
>   tagged at conversion time.
>
> **Freshen procedure** (after a legitimate seam edit shifts these callsites):
> re-run the recorded converter
> `python tests/architectural/surface_resolution_audit/rekey_inventory.py`, which
> re-derives every `qualname`/`token` from live source (tokens are tool-derived,
> never hand-typed) and rewrites the two gated tables below.

**Scope note:** the many downstream callers that legitimately call
`resolve_feature_dir_for_mission` / `candidate_feature_dir_for_mission` /
`resolve_feature_dir_for_slug` outside the seam files are summarized in the
"Routed caller summary" section (aggregate, not gated row-by-row) — the matcher's
job is to make bypass under-counting and ghost over-documentation impossible, not
to enumerate every blessed call.

## Sink table

{sink_table}

## Disposition summary

| disposition | count | meaning |
| --- | --- | --- |
| routed-through-resolver | {counts['routed-through-resolver']} | goes through a canonical blessed resolver (cite it) |
| topology-blind-by-design | {counts['topology-blind-by-design']} | deliberately primary-only; coord surface carries no meta.json (C-GUARD-3a) |
| raw-bypass | {counts['raw-bypass']} | composes KITTY_SPECS_DIR/slug inline for a fail-closed diagnostic `raise` payload (no FS sink) |
| **total** | **{total}** | all AST-discovered ResolutionRow callsites |

## Read-SELECTION callsites (FR-006a)

`discover_selection_callsites()` enumerates every direct
`resolve_mission_read_path(...)` call — the read-side SELECTION authority.
Seam-internal calls are auto-blessed; external calls must be allowlisted in
`audit.py::ALLOWLISTED_SELECTION_CALLSITES`. The table is cross-checked by the
SAME composite undercount/overcount seams as the sink table. On the collapsed
tree all {sel_count} direct selection callsites are seam-internal (zero external).

{selection_table}

{_ROUTED_CALLER_SUMMARY}"""
    return header


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if the regenerated inventory differs.",
    )
    args = parser.parse_args()

    audit = _load_audit()
    rendered = _render_inventory(audit)
    if not rendered.endswith("\n"):
        rendered += "\n"

    if args.check:
        current = _INVENTORY_PATH.read_text(encoding="utf-8")
        if current != rendered:
            print("inventory.md is STALE — re-run without --check to freshen.", file=sys.stderr)
            return 1
        print("inventory.md is fresh.")
        return 0

    _INVENTORY_PATH.write_text(rendered, encoding="utf-8")
    print(f"Wrote {_INVENTORY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
