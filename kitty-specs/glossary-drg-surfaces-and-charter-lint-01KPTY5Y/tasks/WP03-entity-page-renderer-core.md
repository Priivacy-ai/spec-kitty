---
work_package_id: WP03
title: Entity Page Renderer Core
dependencies: []
requirement_refs:
- C-002
- FR-007
- FR-008
- FR-010
- NFR-004
planning_base_branch: feat/glossary-save-seed-file-and-core-terms
merge_target_branch: feat/glossary-save-seed-file-and-core-terms
branch_strategy: Planning artifacts for this feature were generated on feat/glossary-save-seed-file-and-core-terms. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/glossary-save-seed-file-and-core-terms unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
history:
- date: '2026-04-23'
  event: created
authoritative_surface: src/specify_cli/glossary/
execution_mode: code_change
mission_slug: glossary-drg-surfaces-and-charter-lint-01KPTY5Y
owned_files:
- src/specify_cli/glossary/entity_pages.py
- tests/specify_cli/glossary/test_entity_pages.py
tags: []
---

# WP03 — Entity Page Renderer Core

**Mission**: glossary-drg-surfaces-and-charter-lint-01KPTY5Y  
**Branch**: `main` (planning base) → `main` (merge target)  
**Execute**: `spec-kitty agent action implement WP03 --agent <name>`

## Objective

Build `GlossaryEntityPageRenderer` — the engine that reverse-walks `vocabulary` edges in the merged DRG and produces a regenerable Markdown entity page per term at `.kittify/charter/compiled/glossary/<term-id>.md`.

Pages are build artifacts: gitignored, never committed, idempotent on re-run. This WP delivers the core renderer. CLI wiring (`glossary show`) and the charter hook are done in WP06 and WP07 (which depend on this WP).

**External dependency**: WP5.1 must have added `glossary:<id>` URN nodes and `vocabulary` edges to the merged DRG. If WP5.1 is not yet on main, use a fixture DRG in tests and a graceful `if drg_available` guard in the renderer.

## Context

### DRG access pattern

The merged DRG lives at `.kittify/doctrine/` (output of `charter compile`). Load via:
```python
from doctrine.drg.models import DRGGraph

def load_merged_drg(repo_root: Path) -> DRGGraph | None:
    drg_dir = repo_root / ".kittify" / "doctrine"
    if not drg_dir.exists():
        return None
    # Find the compiled graph file — inspect actual filename in doctrine package
    # typically something like merged_drg.json or drg.json
    for candidate in ["merged_drg.json", "drg.json", "compiled_drg.json"]:
        path = drg_dir / candidate
        if path.exists():
            return DRGGraph.model_validate(json.loads(path.read_text()))
    return None
```

Inspect `src/specify_cli/cli/commands/charter.py` lines ~955–1109 for the actual DRG file name used in the compile pipeline.

### Vocabulary edge shape

A `vocabulary` edge in the DRG connects a source node (action, profile, WP, ADR, etc.) to a target node (glossary term URN `glossary:<id>`):
```
source: "action:implement" 
type: "vocabulary"
target: "glossary:deployment-target"
```

Reverse-walk: group edges by `target`, collect all sources per term.

### Entity page output path

```python
output_dir = repo_root / ".kittify" / "charter" / "compiled" / "glossary"
output_dir.mkdir(parents=True, exist_ok=True)
page_path = output_dir / f"{term_id_slug}.md"
```

Where `term_id_slug` is the term ID with `:` replaced by `-` (e.g., `glossary-deployment-target`).

---

## Subtask T015 — `BacklinkEntry` Dataclass + Renderer Skeleton

**File**: `src/specify_cli/glossary/entity_pages.py` (new)

```python
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BacklinkEntry:
    source_id: str          # DRG node ID of the referencing artifact
    source_type: str        # "wp" | "adr" | "mission_step" | "retro_finding" | "charter_section" | "other"
    label: str              # human-readable label (e.g., "WP03 — Entity Page Renderer")
    artifact_path: str | None = None  # relative path to the artifact file, if resolvable


class TermNotFoundError(Exception):
    pass


class GlossaryEntityPageRenderer:
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root
        self._output_dir = repo_root / ".kittify" / "charter" / "compiled" / "glossary"

    def generate_all(self) -> list[Path]:
        """Generate entity pages for all terms in the merged DRG. Returns written paths."""
        ...

    def generate_one(self, term_id: str) -> Path:
        """Generate entity page for a single term. Raises TermNotFoundError if term missing."""
        ...
```

---

## Subtask T016 — DRG Reverse-Walk Logic

**File**: `src/specify_cli/glossary/entity_pages.py`

**Purpose**: Load the merged DRG, extract all glossary term nodes, and build a `backlink_index`.

```python
def _build_backlink_index(self, drg: DRGGraph) -> dict[str, list[BacklinkEntry]]:
    """
    Returns: { term_id_urn -> [BacklinkEntry, ...] }
    """
    index: dict[str, list[BacklinkEntry]] = {}
    for edge in drg.edges:
        if edge.type != "vocabulary":
            continue
        target = edge.target  # e.g. "glossary:deployment-target"
        if not target.startswith("glossary:"):
            continue
        source_node = drg.get_node(edge.source)
        source_type = self._classify_node_type(source_node) if source_node else "other"
        entry = BacklinkEntry(
            source_id=edge.source,
            source_type=source_type,
            label=self._node_label(source_node),
            artifact_path=self._node_artifact_path(source_node),
        )
        index.setdefault(target, []).append(entry)
    return index

def _classify_node_type(self, node) -> str:
    # Inspect node.type or node.urn prefix to determine source type
    # Map to: "wp" | "adr" | "mission_step" | "retro_finding" | "charter_section" | "other"
    urn = getattr(node, "id", "") or ""
    if urn.startswith("wp:"):       return "wp"
    if urn.startswith("adr:"):      return "adr"
    if urn.startswith("step:"):     return "mission_step"
    if urn.startswith("retro:"):    return "retro_finding"
    if urn.startswith("charter:"):  return "charter_section"
    return "other"
```

**Adapt** the URN prefix checks to whatever the actual DRG node ID scheme is (inspect `doctrine.drg.models`).

Also implement `_node_label()` and `_node_artifact_path()` — these extract a human label and optional file path from the node metadata. Return `node.id` as the fallback label; `None` as the fallback path.

---

## Subtask T017 — Markdown Template Rendering

**File**: `src/specify_cli/glossary/entity_pages.py`

**Purpose**: Given a term node and its backlinks, render the full Markdown entity page as a string.

```python
def _render_page(self, term_node, backlinks: list[BacklinkEntry]) -> str:
    """Render entity page Markdown for one term."""
    lines: list[str] = []

    # Header
    lines.append(f"# {term_node.surface or term_node.id}")
    lines.append("")
    lines.append(
        f"**ID**: `{term_node.id}`  "
        f"**Scope**: {getattr(term_node, 'scope', 'global')}  "
        f"**Status**: {getattr(term_node, 'status', 'unknown')}"
    )
    lines.append("")

    # Definition
    lines.append("## Definition")
    lines.append("")
    lines.append(getattr(term_node, 'definition', '_No definition recorded._'))
    lines.append("")

    # Provenance
    prov = getattr(term_node, 'provenance', None)
    if prov:
        lines.append("## Provenance")
        lines.append("")
        lines.append(f"First introduced: {prov}")
        lines.append("")

    # Inbound references, grouped by source_type
    if backlinks:
        lines.append("## References")
        lines.append("")
        groups: dict[str, list[BacklinkEntry]] = {}
        for bl in backlinks:
            groups.setdefault(bl.source_type, []).append(bl)
        type_labels = {
            "wp": "Work Packages", "adr": "ADRs",
            "mission_step": "Mission Steps", "retro_finding": "Retrospective Findings",
            "charter_section": "Charter Sections", "other": "Other",
        }
        for stype, entries in groups.items():
            lines.append(f"### {type_labels.get(stype, stype)}")
            lines.append("")
            for e in entries:
                if e.artifact_path:
                    lines.append(f"- [{e.label}]({e.artifact_path})")
                else:
                    lines.append(f"- {e.label} (`{e.source_id}`)")
            lines.append("")

    # Conflict history (from glossary event log)
    conflict_events = self._load_conflict_history(term_node.id)
    if conflict_events:
        lines.append("## Conflict History")
        lines.append("")
        lines.append("| Timestamp | Severity | Type | Resolution |")
        lines.append("|-----------|----------|------|------------|")
        for ev in conflict_events:
            ts = ev.get("checked_at", "")
            sev = ev.get("severity", "")
            ctype = ev.get("conflict_type", "")
            res = ev.get("resolution", "unresolved")
            lines.append(f"| {ts} | {sev} | {ctype} | {res} |")
        lines.append("")

    lines.append("---")
    lines.append(f"*Regenerated automatically. Do not edit manually.*")

    return "\n".join(lines)

def _load_conflict_history(self, term_id: str) -> list[dict]:
    """Scan event logs for SemanticCheckEvaluated events related to this term."""
    events_dir = self._repo_root / ".kittify" / "events" / "glossary"
    result = []
    if not events_dir.exists():
        return result
    for log_file in events_dir.glob("*.events.jsonl"):
        try:
            for line in log_file.read_text().splitlines():
                try:
                    ev = json.loads(line)
                    if (ev.get("event_type") == "semantic_check_evaluated"
                            and ev.get("term_id") == term_id):
                        result.append(ev)
                except json.JSONDecodeError:
                    pass
        except OSError:
            pass
    return result
```

---

## Subtask T018 — Atomic Write, Public API, and Tests

**File**: `src/specify_cli/glossary/entity_pages.py` and `tests/specify_cli/glossary/test_entity_pages.py`

**Atomic write helper**:
```python
def _write_page(self, term_id: str, content: str) -> Path:
    self._output_dir.mkdir(parents=True, exist_ok=True)
    slug = term_id.replace(":", "-").replace("/", "-")
    final_path = self._output_dir / f"{slug}.md"
    tmp_path = final_path.with_suffix(".md.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.rename(final_path)
    return final_path
```

**`generate_all()` implementation**:
```python
def generate_all(self) -> list[Path]:
    drg = _load_merged_drg(self._repo_root)
    if drg is None:
        logger.warning("entity_pages: merged DRG not found — skipping generation")
        return []
    backlink_index = self._build_backlink_index(drg)
    written = []
    for node in drg.nodes:
        if not getattr(node, 'id', '').startswith("glossary:"):
            continue
        backlinks = backlink_index.get(node.id, [])
        content = self._render_page(node, backlinks)
        path = self._write_page(node.id, content)
        written.append(path)
    return written
```

**`generate_one()` implementation**:
```python
def generate_one(self, term_id: str) -> Path:
    drg = _load_merged_drg(self._repo_root)
    if drg is None:
        raise TermNotFoundError(f"DRG not available (term: {term_id})")
    node = next((n for n in drg.nodes if n.id == term_id), None)
    if node is None:
        raise TermNotFoundError(f"Term not found in DRG: {term_id}")
    backlinks = self._build_backlink_index(drg).get(term_id, [])
    content = self._render_page(node, backlinks)
    return self._write_page(term_id, content)
```

**Tests** (`tests/specify_cli/glossary/test_entity_pages.py`):

1. **3-term fixture DRG** — Build an in-memory fixture with 3 glossary term nodes and 2 vocabulary edges per term. Call `generate_all()`. Assert 3 files written to the output dir.
2. **Page content** — Assert at least one of the pages contains the term's definition text and a "References" section with entries.
3. **Idempotency** — Call `generate_all()` twice. Assert no exception; assert file count unchanged.
4. **`generate_one()` success** — Call for a known term ID. Assert file exists, contains term name.
5. **`generate_one()` on missing term** — Call for a non-existent term ID. Assert `TermNotFoundError` is raised.
6. **Missing DRG** — Pass a `repo_root` with no `.kittify/doctrine/`. Assert `generate_all()` returns `[]` without raising.
7. **Atomic write** — Assert no `.md.tmp` file left behind after successful generation.

**Performance check**: Add a fixture with 500 generated term nodes. Assert `generate_all()` completes in <10 seconds.

**Run**: `cd src && pytest tests/specify_cli/glossary/test_entity_pages.py -v`

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: Allocated by `spec-kitty agent action implement WP03 --agent <name>`.

---

## Definition of Done

- [ ] `entity_pages.py` exists with `BacklinkEntry`, `TermNotFoundError`, `GlossaryEntityPageRenderer`
- [ ] `generate_all()` returns list of written paths; returns `[]` when DRG unavailable
- [ ] `generate_one()` raises `TermNotFoundError` for missing term
- [ ] Pages contain all sections from FR-008: definition, references, provenance, conflict history
- [ ] Atomic write: no `.md.tmp` files left on disk
- [ ] All 7 test scenarios pass: `pytest tests/specify_cli/glossary/test_entity_pages.py`
- [ ] 500-term performance test passes in <10 seconds
- [ ] `ruff check src/specify_cli/glossary/entity_pages.py` passes

---

## Reviewer Guidance

1. `generate_all()` must return `[]` (not raise) when the DRG is missing — WP5.1 may not be present.
2. The atomic write (`tmp → rename`) must be used — partial writes must never leave corrupt pages.
3. `_load_conflict_history()` must not raise even if all event files are missing.
4. Confirm `generate_one()` calls `_build_backlink_index(drg)` only once — not once per page.
5. Check that `output_dir` is not committed — verify `.gitignore` includes the path (WP06 handles this explicitly).
