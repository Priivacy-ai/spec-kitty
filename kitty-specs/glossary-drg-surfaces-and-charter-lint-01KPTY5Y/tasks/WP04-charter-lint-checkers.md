---
work_package_id: WP04
title: Charter Lint Checkers
dependencies: []
requirement_refs:
- C-003
- FR-019
- FR-020
- FR-021
- FR-022
- NFR-002
- NFR-003
planning_base_branch: feat/glossary-save-seed-file-and-core-terms
merge_target_branch: feat/glossary-save-seed-file-and-core-terms
branch_strategy: Planning artifacts for this feature were generated on feat/glossary-save-seed-file-and-core-terms. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/glossary-save-seed-file-and-core-terms unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
history:
- date: '2026-04-23'
  event: created
authoritative_surface: src/specify_cli/charter_lint/
execution_mode: code_change
mission_slug: glossary-drg-surfaces-and-charter-lint-01KPTY5Y
owned_files:
- src/specify_cli/charter_lint/__init__.py
- src/specify_cli/charter_lint/findings.py
- src/specify_cli/charter_lint/checks/__init__.py
- src/specify_cli/charter_lint/checks/orphan.py
- src/specify_cli/charter_lint/checks/contradiction.py
- src/specify_cli/charter_lint/checks/staleness.py
- src/specify_cli/charter_lint/checks/reference_integrity.py
- tests/specify_cli/charter_lint/checks/test_orphan.py
- tests/specify_cli/charter_lint/checks/test_contradiction.py
- tests/specify_cli/charter_lint/checks/test_staleness.py
- tests/specify_cli/charter_lint/checks/test_reference_integrity.py
tags: []
---

# WP04 — Charter Lint Checkers

**Mission**: glossary-drg-surfaces-and-charter-lint-01KPTY5Y  
**Branch**: `main` (planning base) → `main` (merge target)  
**Execute**: `spec-kitty agent action implement WP04 --agent <name>`

## Objective

Create the `src/specify_cli/charter_lint/` package containing:
- `LintFinding` and `DecayReport` data models
- A DRG loading helper
- Four independent checker classes: `OrphanChecker`, `ContradictionChecker`, `StalenessChecker`, `ReferenceIntegrityChecker`

Each checker has a single `run(drg, feature_scope) -> list[LintFinding]` method. No LLM calls. No inter-checker dependencies. WP07 orchestrates them via `LintEngine` (which depends on this WP).

**Critical constraints** (C-003 / NFR-003):
- Zero LLM calls in any checker
- All logic is graph traversal, string/hash comparison, timestamp arithmetic
- Total time for all four checkers on realistic input: ≤ 5 seconds wall time

## Context

### DRG access

Same as WP03 — load from `.kittify/doctrine/`. Add the `load_merged_drg` helper directly in this package (or import from `entity_pages.py` if WP03 exports it). Avoid duplication: if WP03 exports `load_merged_drg`, import it; otherwise duplicate the small helper here.

```python
# charter_lint/_drg.py (small internal helper)
from pathlib import Path
def load_merged_drg(repo_root: Path):
    from doctrine.drg.models import DRGGraph
    import json
    drg_dir = repo_root / ".kittify" / "doctrine"
    for name in ["merged_drg.json", "drg.json", "compiled_drg.json"]:
        p = drg_dir / name
        if p.exists():
            return DRGGraph.model_validate(json.loads(p.read_text()))
    return None
```

### Fixture DRG for tests

Build in-memory fixture DRGs using `DRGGraph` constructor (or a plain dict + `model_validate`) with manufactured decay:
- One orphan ADR (no incoming edges)
- Two ADRs with the same `topic` URN but different `decision` text
- One synthesized artifact with a `corpus_snapshot_id` older than 90 days
- One WP with a `references_adr` edge pointing to a superseded ADR

---

## Subtask T019 — Package Skeleton + Data Models

**Files**: `src/specify_cli/charter_lint/__init__.py`, `src/specify_cli/charter_lint/findings.py`

**`findings.py`**:
```python
from __future__ import annotations
import dataclasses
import json
from typing import Literal

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

@dataclasses.dataclass
class LintFinding:
    category: Literal["orphan", "contradiction", "staleness", "reference_integrity"]
    type: str                    # "wp", "adr", "glossary_term", "synthesized_artifact", etc.
    id: str                      # node ID or URN of the offending artifact
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    feature_id: str | None = None
    remediation_hint: str | None = None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class DecayReport:
    findings: list[LintFinding]
    scanned_at: str              # ISO 8601
    feature_scope: str | None
    duration_seconds: float
    drg_node_count: int
    drg_edge_count: int

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["findings"] = [f.to_dict() for f in self.findings]
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def filter_by_severity(self, min_severity: str) -> "DecayReport":
        min_val = SEVERITY_ORDER.get(min_severity, 0)
        filtered = [f for f in self.findings if SEVERITY_ORDER.get(f.severity, 0) >= min_val]
        return dataclasses.replace(self, findings=filtered)
```

**`__init__.py`**: export `LintFinding`, `DecayReport`, and the four checker classes.

---

## Subtask T020 — DRG Loading Helper

**File**: `src/specify_cli/charter_lint/_drg.py` (internal)

Implement `load_merged_drg(repo_root: Path) -> DRGGraph | None` as described in Context. This is the single import point for DRG access within `charter_lint/`. Do not duplicate if WP03 already exports this.

Also add:
```python
def get_nodes_by_type(drg, node_type: str) -> list:
    """Return all DRG nodes matching the given type string."""
    return [n for n in drg.nodes if getattr(n, 'node_type', None) == node_type
            or getattr(n, 'type', None) == node_type]

def get_incoming_edges(drg, node_id: str, edge_types: list[str] | None = None) -> list:
    """Return all edges whose target is node_id, optionally filtered by edge type."""
    return [e for e in drg.edges
            if e.target == node_id
            and (edge_types is None or e.type in edge_types)]
```

Inspect `doctrine.drg.models.DRGGraph` to discover the actual node/edge attribute names. Adapt accordingly.

---

## Subtask T021 — `OrphanChecker`

**File**: `src/specify_cli/charter_lint/checks/orphan.py`

**Logic**: For each node of an "expected-to-be-referenced" type, count incoming edges of the expected type(s). Zero incoming = orphan.

```python
from ..findings import LintFinding
from .._drg import get_nodes_by_type, get_incoming_edges

EXPECTED_INCOMING: dict[str, list[str]] = {
    "wp":                   ["mission_step_delegates", "lane_owns"],
    "adr":                  ["references_adr", "supersedes", "charter_cites"],
    "glossary_term":        ["vocabulary"],
    "synthesized_artifact": ["applies", "scope"],
    "procedure":            ["step_delegates"],
}

class OrphanChecker:
    def run(self, drg, feature_scope: str | None = None) -> list[LintFinding]:
        findings = []
        for node_type, expected_edge_types in EXPECTED_INCOMING.items():
            for node in get_nodes_by_type(drg, node_type):
                if feature_scope and not self._in_scope(node, feature_scope):
                    continue
                incoming = get_incoming_edges(drg, node.id, expected_edge_types)
                if not incoming:
                    findings.append(LintFinding(
                        category="orphan",
                        type=node_type,
                        id=node.id,
                        severity="medium",
                        message=f"{node_type} `{node.id}` has no incoming "
                                f"{' or '.join(expected_edge_types)} edges",
                        feature_id=feature_scope,
                        remediation_hint=f"Reference `{node.id}` from at least one "
                                         f"{expected_edge_types[0]} edge, or mark as superseded/canceled",
                    ))
        return findings

    def _in_scope(self, node, feature_scope: str) -> bool:
        """Return True if the node belongs to the given feature scope."""
        meta = getattr(node, 'metadata', {}) or {}
        return meta.get('feature_id') == feature_scope or feature_scope in (node.id or '')
```

**Adapt** the edge type names and node attribute names to the actual DRG schema.

**Tests** (`tests/specify_cli/charter_lint/checks/test_orphan.py`):
- Fixture DRG with one orphan ADR: assert 1 finding, `category="orphan"`, `type="adr"`
- Fixture DRG with all nodes properly connected: assert 0 findings
- `feature_scope` filter: orphan in feature A, query for feature B → 0 findings

---

## Subtask T022 — `ContradictionChecker`

**File**: `src/specify_cli/charter_lint/checks/contradiction.py`

**Logic**: Three contradiction patterns:

1. **ADR-topic contradiction**: Two ADRs with the same `topic` URN but different `decision` text hashes.
2. **Directive scope conflict**: Two directives whose `applies_to` scope sets intersect AND whose `severity` orders contradict (one is "high" while the other says the opposite about the same thing).
3. **Multiple active glossary senses**: Two `glossary_term` nodes with the same surface name and `status == "active"` in the same scope.

```python
import hashlib
from itertools import combinations
from ..findings import LintFinding

class ContradictionChecker:
    def run(self, drg, feature_scope: str | None = None) -> list[LintFinding]:
        findings = []
        findings.extend(self._check_adr_contradictions(drg, feature_scope))
        findings.extend(self._check_glossary_sense_conflicts(drg, feature_scope))
        return findings

    def _check_adr_contradictions(self, drg, feature_scope) -> list[LintFinding]:
        adrs = [n for n in drg.nodes if getattr(n, 'node_type', getattr(n, 'type', '')) == 'adr']
        by_topic: dict[str, list] = {}
        for adr in adrs:
            topic = getattr(adr, 'topic_urn', None) or getattr(getattr(adr, 'metadata', None), 'topic', None)
            if topic:
                by_topic.setdefault(topic, []).append(adr)
        result = []
        for topic, group in by_topic.items():
            if len(group) < 2:
                continue
            for a, b in combinations(group, 2):
                dec_a = hashlib.md5((getattr(a, 'decision', '') or '').encode()).hexdigest()
                dec_b = hashlib.md5((getattr(b, 'decision', '') or '').encode()).hexdigest()
                if dec_a != dec_b:
                    result.append(LintFinding(
                        category="contradiction",
                        type="adr",
                        id=f"{a.id} vs {b.id}",
                        severity="high",
                        message=f"ADRs `{a.id}` and `{b.id}` share topic `{topic}` but have conflicting decisions",
                        feature_id=feature_scope,
                        remediation_hint=f"Supersede one ADR with the other via a `replaces:` edge",
                    ))
        return result

    def _check_glossary_sense_conflicts(self, drg, feature_scope) -> list[LintFinding]:
        terms = [n for n in drg.nodes if (n.id or '').startswith('glossary:')]
        active = [t for t in terms if getattr(t, 'status', '') == 'active']
        by_surface: dict[str, list] = {}
        for t in active:
            surface = getattr(t, 'surface', t.id)
            scope = getattr(t, 'scope', 'global')
            key = f"{surface}::{scope}"
            by_surface.setdefault(key, []).append(t)
        result = []
        for key, group in by_surface.items():
            if len(group) > 1:
                ids = [t.id for t in group]
                result.append(LintFinding(
                    category="contradiction",
                    type="glossary_term",
                    id=", ".join(ids),
                    severity="high",
                    message=f"Multiple active senses for term in scope `{key}`: {ids}",
                    feature_id=feature_scope,
                    remediation_hint="Deprecate all but one active sense for this term in this scope",
                ))
        return result
```

**Tests**: ADR contradiction fixture → 1 finding; clean ADRs → 0; duplicate active senses → 1 finding.

---

## Subtask T023 — `StalenessChecker`

**File**: `src/specify_cli/charter_lint/checks/staleness.py`

**Logic**: Three staleness patterns:

1. **Stale synthesized artifact**: `corpus_snapshot_id` metadata contains a timestamp older than `staleness_threshold_days` (default: 90).
2. **WP references edited artifact**: WP node has `references_artifact` edges pointing to nodes whose `last_edited_at` > WP's `started_at`.
3. **Removed context-source**: Profile node has `context_sources` referencing a node ID that no longer exists in the DRG.

```python
import datetime
from ..findings import LintFinding

class StalenessChecker:
    def __init__(self, staleness_threshold_days: int = 90) -> None:
        self._threshold = staleness_threshold_days

    def run(self, drg, feature_scope: str | None = None) -> list[LintFinding]:
        findings = []
        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now - datetime.timedelta(days=self._threshold)
        node_ids = {n.id for n in drg.nodes}

        for node in drg.nodes:
            ntype = getattr(node, 'node_type', getattr(node, 'type', ''))
            meta = getattr(node, 'metadata', {}) or {}

            # Pattern 1: stale synthesized artifact
            if ntype == 'synthesized_artifact':
                snap_ts = meta.get('corpus_snapshot_timestamp') or meta.get('snapshot_at')
                if snap_ts:
                    try:
                        snap_dt = datetime.datetime.fromisoformat(snap_ts)
                        if snap_dt.tzinfo is None:
                            snap_dt = snap_dt.replace(tzinfo=datetime.timezone.utc)
                        if snap_dt < cutoff:
                            findings.append(LintFinding(
                                category="staleness",
                                type="synthesized_artifact",
                                id=node.id,
                                severity="medium",
                                message=f"Synthesized artifact `{node.id}` corpus snapshot "
                                        f"is {(now - snap_dt).days} days old (threshold: {self._threshold})",
                                feature_id=feature_scope,
                                remediation_hint="Re-run `spec-kitty charter synthesize` to refresh",
                            ))
                    except ValueError:
                        pass

            # Pattern 3: removed context-source
            if ntype == 'profile':
                for source_ref in (meta.get('context_sources') or []):
                    ref_id = source_ref if isinstance(source_ref, str) else source_ref.get('id', '')
                    if ref_id and ref_id not in node_ids:
                        findings.append(LintFinding(
                            category="staleness",
                            type="profile",
                            id=node.id,
                            severity="medium",
                            message=f"Profile `{node.id}` has context-source `{ref_id}` "
                                    f"that no longer exists in the DRG",
                            feature_id=feature_scope,
                            remediation_hint=f"Remove or update the `{ref_id}` context-source reference",
                        ))
        return findings
```

**Tests**: Stale artifact fixture (91 days old) → 1 finding; fresh artifact → 0; missing context-source → 1 finding.

---

## Subtask T024 — `ReferenceIntegrityChecker`

**File**: `src/specify_cli/charter_lint/checks/reference_integrity.py`

**Logic**: Two reference integrity patterns:

1. **WP references superseded ADR**: A `references_adr` edge points to an ADR that has an outgoing `replaces` edge (i.e., it has been superseded).
2. **Dangling edge**: Any DRG edge whose `target` node ID is not in the DRG node set.

```python
from ..findings import LintFinding

class ReferenceIntegrityChecker:
    def run(self, drg, feature_scope: str | None = None) -> list[LintFinding]:
        findings = []
        node_ids = {n.id for n in drg.nodes}

        # Build superseded ADR set
        superseded_adrs = {
            e.source for e in drg.edges if e.type == "replaces"
        }

        for edge in drg.edges:
            # Pattern 2: dangling edge
            if edge.target not in node_ids:
                findings.append(LintFinding(
                    category="reference_integrity",
                    type="edge",
                    id=f"{edge.source} -> {edge.target}",
                    severity="high",
                    message=f"Edge from `{edge.source}` targets `{edge.target}` which does not exist",
                    feature_id=feature_scope,
                    remediation_hint=f"Remove the edge or add the missing node `{edge.target}`",
                ))

            # Pattern 1: WP → superseded ADR
            if edge.type == "references_adr" and edge.target in superseded_adrs:
                findings.append(LintFinding(
                    category="reference_integrity",
                    type="wp",
                    id=edge.source,
                    severity="medium",
                    message=f"`{edge.source}` references superseded ADR `{edge.target}`",
                    feature_id=feature_scope,
                    remediation_hint=f"Update reference to the ADR that supersedes `{edge.target}`",
                ))

        return findings
```

**Tests**: Dangling edge fixture → 1 finding; superseded ADR reference → 1 finding; clean DRG → 0 findings.

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: Allocated by `spec-kitty agent action implement WP04 --agent <name>`.

---

## Definition of Done

- [ ] `charter_lint/__init__.py` exports `LintFinding`, `DecayReport`, and all four checkers
- [ ] `findings.py`: `LintFinding.to_dict()` and `DecayReport.to_json()` produce valid serialization
- [ ] `OrphanChecker.run()` detects the 5 expected orphan types from FR-019
- [ ] `ContradictionChecker.run()` detects ADR decision divergence and duplicate active glossary senses
- [ ] `StalenessChecker.run()` detects stale synthesized artifacts and removed context-sources
- [ ] `ReferenceIntegrityChecker.run()` detects dangling edges and superseded ADR references
- [ ] No LLM calls in any checker — enforced by test: assert LLM client never called
- [ ] 4 test files pass: `pytest tests/specify_cli/charter_lint/checks/ -v`
- [ ] `ruff check src/specify_cli/charter_lint/` passes

---

## Reviewer Guidance

1. Each checker must be independently instantiable — no shared mutable state between checkers.
2. `staleness_threshold_days` must be configurable at instantiation, not hardcoded.
3. All edge type name constants (e.g., `"vocabulary"`, `"references_adr"`, `"replaces"`) must be adapted to match the actual DRG schema — do not invent type names; read `doctrine.drg.models` first.
4. Confirm no LLM import exists anywhere in `charter_lint/`.
5. `DecayReport.to_json()` output must be parseable by `json.loads()` with no extra text — tested in WP07.
