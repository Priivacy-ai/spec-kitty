"""Enumerate every inline relationship-bearing field under ``packs/built-in/``.

Mission ``doctrine-canonical-structure-remediation-01KYEYSD`` (FR-013/FR-015).

**Why this exists as a script rather than a number in a spec.** The migration
inventory was measured by hand twice and was wrong both times: the first pass read
only top-level ``references:`` (missing 15 step-level entries in 13 step positions,
4 of whose files carry *no* top-level block at all, so a file-driven migration would
never have opened them), and neither pass counted the five sibling surfaces
(``directive_refs``, ``tactic_refs``, ``tactic-references``, ``directive-references``,
``context-sources.*``). A spec that hardcodes a count an implementer cannot reproduce
makes the completion gate unfalsifiable — it pins whatever someone counted that day.
So the count is *derived*, here, and the gate imports this module rather than
restating a literal.

**The classification that matters.** Not every inline entry denotes an artefact
relationship, and conflating them is what made the earlier reading hazardous:

* ``MIGRATE`` — denotes an artefact→artefact relationship that the extractor turns
  into a DRG edge. These move to the authored-edge tier.
* ``GOVERNANCE`` — ``directive-references`` / ``context-sources.*`` on agent
  profiles. These produce **zero** DRG edges but seed the charter governance
  closure (``src/charter/resolver.py`` reads ``profile.directive_references`` as the
  transitive-resolution seed set). Deleting them empties profile-routed prompts
  while every graph-shaped assertion stays green. They are NOT relationship
  residue and must not be swept into the migration.
* ``RAW_MATERIAL`` — path strings pointing at non-artefact files (READMEs, ADRs,
  templates). ``_resolve_path_ref`` fails closed on them by design, they produce no
  edge, and the doctrine README sanctions carrying them. They stay.

Run ``python scripts/doctrine/inline_reference_inventory.py --json`` for machine
output, or without flags for the operator table.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
#: The relationship-bearing built-in artefacts (agent profiles, styleguides,
#: directives, …) relocated from ``src/charter/offering/<kind>/built-in`` to the
#: top-level ``packs/built-in/<kind>`` pack root (mission
#: relocate-builtin-doctrine-packs); the inline-reference inventory enumerates
#: them there. Schemas/templates/missions stay under ``src/doctrine`` and carry
#: no governance/relationship fields, so they are not scanned.
_DOCTRINE_ROOT = _REPO_ROOT / "packs" / "built-in"

#: Disposition classes. See the module docstring for why the split is load-bearing.
MIGRATE = "MIGRATE"
GOVERNANCE = "GOVERNANCE"
RAW_MATERIAL = "RAW_MATERIAL"

#: Sibling bare-id list fields that the extractor also turns into edges.
#: ``tactic_refs`` is included deliberately even though it is currently empty: its
#: extractor passes still exist (dead code), so a future re-introduction would
#: silently reopen the surface. Counting it at 0 makes that visible.
_BARE_ID_FIELDS: tuple[str, ...] = ("directive_refs", "tactic_refs")

#: Agent-profile fields. ``tactic-references`` DOES produce edges;
#: ``directive-references`` does NOT but seeds governance resolution.
_PROFILE_EDGE_FIELDS: tuple[str, ...] = ("tactic-references",)
_PROFILE_GOVERNANCE_FIELDS: tuple[str, ...] = ("directive-references",)


@dataclass
class Entry:
    """One inline reference occurrence."""

    path: str
    field_name: str
    disposition: str
    detail: str = ""


@dataclass
class Inventory:
    entries: list[Entry] = field(default_factory=list)

    def add(self, entry: Entry) -> None:
        self.entries.append(entry)

    def by_field(self) -> Counter[str]:
        return Counter(e.field_name for e in self.entries)

    def by_disposition(self) -> Counter[str]:
        return Counter(e.disposition for e in self.entries)

    def files_touched(self) -> set[str]:
        return {e.path for e in self.entries}

    def migrate_count(self) -> int:
        return sum(1 for e in self.entries if e.disposition == MIGRATE)


def _resolve_path_ref_or_none(path_str: str) -> tuple[str, str] | None:
    """Delegate to the extractor's own resolver — never re-implement the rule."""
    from charter.offering.drg.migration.extractor import _resolve_path_ref

    return _resolve_path_ref(path_str)


def _classify_reference_entry(raw: Any) -> tuple[str, str]:
    """Return ``(disposition, detail)`` for one ``references:`` list entry."""
    if isinstance(raw, dict) and "type" in raw and "id" in raw:
        return MIGRATE, f"{raw.get('type')}:{raw.get('id')}"
    if isinstance(raw, str):
        resolved = _resolve_path_ref_or_none(raw)
        if resolved is not None:
            return MIGRATE, f"path->{resolved[0]}:{resolved[1]}"
        return RAW_MATERIAL, raw
    return RAW_MATERIAL, f"unrecognised:{type(raw).__name__}"


def _iter_doctrine_yaml(root: Path) -> list[Path]:
    return [
        p
        for p in sorted(root.rglob("*.yaml"))
        if "__pycache__" not in p.parts and not p.name.endswith(".graph.yaml")
    ]


def _collect_reference_lists(inv: Inventory, rel: str, data: dict[str, Any]) -> None:
    """Top-level ``references:`` plus the step-level lists the first count missed."""
    for raw in data.get("references") or []:
        disposition, detail = _classify_reference_entry(raw)
        inv.add(Entry(rel, "references", disposition, detail))

    for index, step in enumerate(data.get("steps") or []):
        if not isinstance(step, dict):
            continue
        for raw in step.get("references") or []:
            disposition, detail = _classify_reference_entry(raw)
            inv.add(
                Entry(rel, "steps[].references", disposition, f"step{index}:{detail}")
            )


def _collect_bare_id_lists(inv: Inventory, rel: str, data: dict[str, Any]) -> None:
    """``directive_refs`` / ``tactic_refs`` — bare id lists that still mint edges."""
    for field_name in _BARE_ID_FIELDS:
        for raw in data.get(field_name) or []:
            inv.add(Entry(rel, field_name, MIGRATE, str(raw)))


def _collect_profile_fields(inv: Inventory, rel: str, data: dict[str, Any]) -> None:
    """Agent-profile surfaces: one mints edges, one seeds governance."""
    for field_name in _PROFILE_EDGE_FIELDS:
        for raw in data.get(field_name) or []:
            ident = raw.get("id") if isinstance(raw, dict) else raw
            inv.add(Entry(rel, field_name, MIGRATE, str(ident)))

    for field_name in _PROFILE_GOVERNANCE_FIELDS:
        for raw in data.get(field_name) or []:
            code = raw.get("code") if isinstance(raw, dict) else raw
            inv.add(Entry(rel, field_name, GOVERNANCE, str(code)))


def _collect_context_sources(inv: Inventory, rel: str, data: dict[str, Any]) -> None:
    """``context-sources.directives`` mints edges; every sibling key does not."""
    context_sources = data.get("context-sources")
    if not isinstance(context_sources, dict):
        return
    for key, values in context_sources.items():
        if not isinstance(values, list):
            continue
        disposition = MIGRATE if key == "directives" else GOVERNANCE
        for raw in values:
            inv.add(Entry(rel, f"context-sources.{key}", disposition, str(raw)))


def collect(root: Path = _DOCTRINE_ROOT) -> Inventory:
    """Walk the doctrine tree and classify every inline relationship entry."""
    inv = Inventory()
    for path in _iter_doctrine_yaml(root):
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        rel = path.relative_to(root).as_posix()
        _collect_reference_lists(inv, rel, data)
        _collect_bare_id_lists(inv, rel, data)
        _collect_profile_fields(inv, rel, data)
        _collect_context_sources(inv, rel, data)
    return inv


def _render_table(inv: Inventory) -> str:
    lines: list[str] = []
    lines.append(f"files touched: {len(inv.files_touched())}")
    lines.append(f"total entries: {len(inv.entries)}")
    lines.append("")
    lines.append(f"{'field':34s} {'MIGRATE':>8s} {'GOVERNANCE':>11s} {'RAW':>5s}")
    per_field: dict[str, Counter[str]] = {}
    for entry in inv.entries:
        per_field.setdefault(entry.field_name, Counter())[entry.disposition] += 1
    for field_name in sorted(per_field):
        counts = per_field[field_name]
        lines.append(
            f"{field_name:34s} {counts[MIGRATE]:8d} "
            f"{counts[GOVERNANCE]:11d} {counts[RAW_MATERIAL]:5d}"
        )
    lines.append("")
    totals = inv.by_disposition()
    lines.append(
        f"{'TOTAL':34s} {totals[MIGRATE]:8d} "
        f"{totals[GOVERNANCE]:11d} {totals[RAW_MATERIAL]:5d}"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--doctrine-root", type=Path, default=_DOCTRINE_ROOT, help="tree to scan"
    )
    args = parser.parse_args(argv)

    inv = collect(args.doctrine_root)
    if args.json:
        payload = {
            "files_touched": len(inv.files_touched()),
            "total_entries": len(inv.entries),
            "by_field": dict(inv.by_field()),
            "by_disposition": dict(inv.by_disposition()),
            "migrate_count": inv.migrate_count(),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_render_table(inv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
