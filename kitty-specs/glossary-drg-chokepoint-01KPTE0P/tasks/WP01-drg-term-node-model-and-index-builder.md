---
work_package_id: WP01
title: DRG Term Node Model and Index Builder
dependencies: []
requirement_refs:
- C-003
- C-004
- FR-001
- FR-002
- FR-003
- FR-004
- FR-013
- FR-015
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history:
- date: '2026-04-22'
  event: created
  author: planner
authoritative_surface: src/doctrine/drg/
execution_mode: code_change
mission_id: 01KPTE0P5JVQFWESWV07R0XG4M
mission_slug: glossary-drg-chokepoint-01KPTE0P
owned_files:
- src/doctrine/drg/models.py
- src/specify_cli/glossary/drg_builder.py
- tests/doctrine/drg/test_glossary_node_kind.py
- tests/specify_cli/glossary/test_drg_builder.py
tags: []
---

# WP01 — DRG Term Node Model and Index Builder

## Objective

Establish the `glossary:<id>` URN scheme and the runtime-computed in-memory DRG layer that makes every active glossary term addressable. Deliver `GlossaryTermIndex`, the data structure the chokepoint (WP02) will consume.

No DRG YAML is written. No new CLI commands. No operator sync step. All outputs are code only.

## Branch Strategy

- **Planning/base branch:** `main`
- **Final merge target:** `main`
- **Execution worktree:** Allocated by `spec-kitty agent action implement WP01 --agent <name>`. The worktree path is resolved from `lanes.json` — do not guess it.
- **Start command:** `spec-kitty agent action implement WP01 --agent <name>`

## Context

### Relevant existing files

| File | Purpose |
|------|---------|
| `src/doctrine/drg/models.py` | Contains `NodeKind` StrEnum, `Relation` StrEnum, `DRGNode`, `DRGEdge`, `DRGGraph` — **modify** |
| `src/charter/_drg_helpers.py` | `load_validated_graph()` — use to get shipped action URNs |
| `src/specify_cli/glossary/models.py` | `TermSense`, `TermSurface`, `SenseStatus` — read-only, no changes |
| `src/specify_cli/glossary/scope.py` | `GlossaryScope`, `SCOPE_RESOLUTION_ORDER` — read-only |
| `src/specify_cli/glossary/store.py` | `GlossaryStore` — read-only |
| `src/specify_cli/glossary/extraction.py` | `COMMON_WORDS` constant — import for reuse in normalizer |

### Key constraint

The existing `DRGNode` validator enforces `urn.split(":")[0] == kind.value`. Adding `NodeKind.GLOSSARY = "glossary"` means `kind.value = "glossary"` and URNs must use the `glossary:` prefix — this is exactly what we want.

---

## Subtask T001 — Add `NodeKind.GLOSSARY` to `src/doctrine/drg/models.py`

**Purpose:** Extend the DRG node kind enum to include glossary term nodes, enabling `DRGNode(kind=NodeKind.GLOSSARY)` and `glossary:` URN validation.

**Steps:**

1. Open `src/doctrine/drg/models.py`.
2. In `class NodeKind(StrEnum)`, add one member **below** `GLOSSARY_SCOPE`:
   ```python
   GLOSSARY_SCOPE = "glossary_scope"
   GLOSSARY = "glossary"           # URN prefix: "glossary:<id>"
   ```
3. Do **not** change any other member or the `_URN_RE` pattern.
4. Verify the existing validator passes for a `DRGNode(urn="glossary:abc12345", kind=NodeKind.GLOSSARY)` without error — you can check mentally: `"glossary".split(":")[0]` → `"glossary"` == `NodeKind.GLOSSARY.value` ✓
5. Verify backward-compat: a `DRGNode(urn="directive:DIRECTIVE_001", kind=NodeKind.DIRECTIVE)` still validates.

**Files:** `src/doctrine/drg/models.py`

**Validation:**
- [ ] `NodeKind.GLOSSARY.value == "glossary"`
- [ ] `str(NodeKind.GLOSSARY) == "glossary"` (StrEnum behavior)
- [ ] Existing node kinds unchanged

---

## Subtask T002 — Implement `glossary_urn()` in `src/specify_cli/glossary/drg_builder.py`

**Purpose:** Produce a stable, deterministic `glossary:<id>` URN from a canonical surface form.

**Steps:**

1. Create `src/specify_cli/glossary/drg_builder.py` (new file).
2. Add module-level imports: `from __future__ import annotations`, `import hashlib`, `import logging`, `from pathlib import Path`, and the needed types from `doctrine.drg.models` and `specify_cli.glossary.*`.
3. Implement `glossary_urn(surface_text: str) -> str`:
   ```python
   def glossary_urn(surface_text: str) -> str:
       """Derive a stable glossary:<id> URN from a canonical surface form.

       The id is the first 8 hex chars of SHA-256(surface_text, utf-8).
       """
       hex_id = hashlib.sha256(surface_text.encode()).hexdigest()[:8]
       return f"glossary:{hex_id}"
   ```
4. Implement collision detection in the index builder (T005). Collision here only means the function itself — test it separately.
5. Verify determinism: same input → same output across process restarts.

**Expected output for test inputs:**
- `glossary_urn("lane")` → `"glossary:c5c5c8d0"` (verify with `hashlib.sha256("lane".encode()).hexdigest()[:8]` in a Python REPL)
- `glossary_urn("work package")` → deterministic value (record it in the test file)

**Files:** `src/specify_cli/glossary/drg_builder.py` (new)

**Validation:**
- [ ] `glossary_urn("lane") == glossary_urn("lane")` — same output on repeated calls
- [ ] `glossary_urn("lane") != glossary_urn("Work Package")` — different inputs give different IDs
- [ ] Output matches `"glossary:" + hashlib.sha256(s.encode()).hexdigest()[:8]` formula

---

## Subtask T003 — Implement `build_glossary_drg_layer()`

**Purpose:** Build a `DRGGraph` containing one `DRGNode` per active glossary term (in `applicable_scopes`) and one `DRGEdge(relation=Relation.VOCABULARY)` per (action node → term node) pair. This is the runtime-computed DRG "glossary overlay."

**Steps:**

1. In `drg_builder.py`, import:
   ```python
   from charter._drg_helpers import load_validated_graph
   from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
   from specify_cli.glossary.models import SenseStatus
   from specify_cli.glossary.scope import GlossaryScope
   from specify_cli.glossary.store import GlossaryStore
   ```
2. Define the `GlossaryTermIndex` dataclass (used by T005):
   ```python
   from dataclasses import dataclass, field

   @dataclass
   class GlossaryTermIndex:
       surface_to_urn: dict[str, str]               # normalized surface → glossary:<id>
       surface_to_senses: dict[str, list]            # normalized surface → list[TermSense]
       applicable_scope_set: frozenset[str]
       term_count: int
   ```
3. Implement `build_glossary_drg_layer`:
   ```python
   def build_glossary_drg_layer(
       store: GlossaryStore,
       applicable_scopes: set[GlossaryScope],
       repo_root: Path,
   ) -> DRGGraph:
       """Build an in-memory DRG layer for active glossary terms.

       Nodes: one GLOSSARY node per unique active sense surface in applicable_scopes.
       Edges: VOCABULARY from each shipped action node to each term node.
       """
       scope_values = {s.value for s in applicable_scopes}

       # Collect unique active senses
       seen_urns: dict[str, str] = {}   # surface → urn (collision detection)
       nodes: list[DRGNode] = []
       for scope_str, surface_map in store._cache.items():
           if scope_str not in scope_values:
               continue
           for surface, senses in surface_map.items():
               active = [s for s in senses if s.status == SenseStatus.ACTIVE]
               if not active:
                   continue
               urn = glossary_urn(surface)
               if surface in seen_urns:
                   continue  # dedup by surface
               if urn in seen_urns.values():
                   _logger.warning("glossary_urn collision for surface %r", surface)
                   continue
               seen_urns[surface] = urn
               nodes.append(DRGNode(urn=urn, kind=NodeKind.GLOSSARY, label=surface))

       # Get action URNs from shipped DRG
       shipped = load_validated_graph(repo_root)
       action_urns = [n.urn for n in shipped.nodes if n.kind == NodeKind.ACTION]

       # Build VOCABULARY edges
       edges: list[DRGEdge] = []
       for action_urn in action_urns:
           for term_node in nodes:
               edges.append(DRGEdge(
                   source=action_urn,
                   target=term_node.urn,
                   relation=Relation.VOCABULARY,
               ))

       import datetime
       return DRGGraph(
           schema_version="1.0",
           generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           generated_by="glossary-drg-builder-v1",
           nodes=nodes,
           edges=edges,
       )
   ```
   Add `_logger = logging.getLogger(__name__)` at module level.
4. Note: `store._cache` is the internal `dict[str, dict[str, list[TermSense]]]` structure — see `GlossaryStore.add_sense()` in `store.py`. If the store adds a public `all_senses()` iterator in a follow-on, prefer that; for now, access `_cache` directly and document the dependency.

**Files:** `src/specify_cli/glossary/drg_builder.py`

**Validation:**
- [ ] Returned `DRGGraph.nodes` contains exactly one node per unique active sense surface in applicable_scopes
- [ ] All nodes have `kind=NodeKind.GLOSSARY`
- [ ] `DRGGraph.edges` contains `len(action_urns) * len(term_nodes)` edges, all with `relation=Relation.VOCABULARY`
- [ ] An empty store returns an empty `DRGGraph` (no crash)

---

## Subtask T004 — Implement `_normalize()` suffix-stripper

**Purpose:** Deterministic token normalization for the chokepoint's term matching. Converts inflected forms ("lanes", "working", "missions") to their canonical surface form ("lane", "work", "mission").

**Steps:**

1. In `drg_builder.py`, implement `_normalize(token: str) -> str`:
   ```python
   import re as _re

   _SUFFIX_RULES = [
       (r"ments$", ""),
       (r"ment$",  ""),
       (r"tions$", ""),
       (r"tion$",  ""),
       (r"ers$",   ""),
       (r"ing$",   ""),
       (r"ness$",  ""),
       (r"ed$",    ""),
       (r"er$",    ""),
       (r"es$",    ""),
       (r"s$",     ""),
   ]
   _MIN_STEM_LEN = 3

   def _normalize(token: str) -> str:
       """Lowercase and apply English suffix stripping."""
       token = token.lower().strip()
       for pattern, replacement in _SUFFIX_RULES:
           candidate = _re.sub(pattern, replacement, token)
           if len(candidate) >= _MIN_STEM_LEN:
               return candidate
       return token
   ```
2. Apply rules in order; stop at the first match that yields a stem ≥ 3 chars.
3. Reuse `COMMON_WORDS` from `specify_cli.glossary.extraction` to filter stop words after normalization.

**Files:** `src/specify_cli/glossary/drg_builder.py`

**Validation:**
- [ ] `_normalize("lanes") == "lane"`
- [ ] `_normalize("missions") == "mission"`
- [ ] `_normalize("implementing") == "implement"`
- [ ] `_normalize("WP") == "wp"` (too short to strip — returned as-is after lowercasing)
- [ ] `_normalize("the") == "the"` (stop word handled at lookup time, not here)

---

## Subtask T005 — Implement `build_index() → GlossaryTermIndex`

**Purpose:** Build the in-memory lookup structure the chokepoint uses: maps normalized/lemmatized surfaces to URNs and senses.

**Steps:**

1. In `drg_builder.py`, implement:
   ```python
   def build_index(
       store: GlossaryStore,
       applicable_scopes: set[GlossaryScope],
   ) -> GlossaryTermIndex:
       """Build a GlossaryTermIndex from active senses in applicable_scopes.

       Includes both canonical surface and lemmatized-form aliases.
       """
       scope_values = {s.value for s in applicable_scopes}
       surface_to_urn: dict[str, str] = {}
       surface_to_senses: dict[str, list] = {}

       for scope_str, surface_map in store._cache.items():
           if scope_str not in scope_values:
               continue
           for surface, senses in surface_map.items():
               active = [s for s in senses if s.status == SenseStatus.ACTIVE]
               if not active:
                   continue
               urn = glossary_urn(surface)
               # Canonical form
               surface_to_urn[surface] = urn
               surface_to_senses[surface] = active
               # Normalized/lemmatized alias (if different from canonical)
               normalized = _normalize(surface)
               if normalized != surface:
                   if normalized not in surface_to_urn:
                       surface_to_urn[normalized] = urn
                       surface_to_senses[normalized] = active

       return GlossaryTermIndex(
           surface_to_urn=surface_to_urn,
           surface_to_senses=surface_to_senses,
           applicable_scope_set=frozenset(scope_values),
           term_count=len({v for v in surface_to_urn.values()}),
       )
   ```
2. Collision handling: if two surfaces normalize to the same form and have different URNs, the first one wins and a warning is logged.

**Files:** `src/specify_cli/glossary/drg_builder.py`

**Validation:**
- [ ] Index contains canonical surface "lane" → `glossary_urn("lane")`
- [ ] Index also contains "lanes" (normalized form) → same URN as "lane"
- [ ] `term_count` equals the number of unique URNs in the index
- [ ] Store with zero active senses returns empty index (no crash)

---

## Subtask T006 — Backward-compat tests in `tests/doctrine/drg/test_glossary_node_kind.py`

**Purpose:** Confirm that adding `NodeKind.GLOSSARY` does not break existing DRG load/validation paths and that the new kind validates correctly.

**File:** `tests/doctrine/drg/test_glossary_node_kind.py` (new)

**Test cases:**

```python
from doctrine.drg.models import DRGNode, NodeKind
from doctrine.drg.loader import load_graph
from charter._drg_helpers import load_validated_graph
from pathlib import Path

def test_glossary_kind_value():
    assert NodeKind.GLOSSARY.value == "glossary"
    assert str(NodeKind.GLOSSARY) == "glossary"

def test_glossary_urn_validates():
    node = DRGNode(urn="glossary:abc12345", kind=NodeKind.GLOSSARY, label="lane")
    assert node.urn == "glossary:abc12345"

def test_glossary_urn_prefix_mismatch_raises():
    import pytest
    with pytest.raises(Exception):
        DRGNode(urn="directive:abc12345", kind=NodeKind.GLOSSARY)

def test_existing_drg_loads_without_glossary_nodes(tmp_path):
    """Shipped graph.yaml has no glossary nodes — must load cleanly."""
    merged = load_validated_graph(tmp_path)  # tmp_path has no project overlay
    kinds = {n.kind for n in merged.nodes}
    assert NodeKind.GLOSSARY not in kinds  # no glossary nodes in shipped graph
    # No exception = backward-compat confirmed

def test_existing_kinds_unchanged():
    from doctrine.drg.models import NodeKind
    expected = {"directive", "tactic", "paradigm", "styleguide", "toolguide",
                "procedure", "agent_profile", "action", "glossary_scope", "glossary"}
    assert {k.value for k in NodeKind} == expected
```

**Validation:**
- [ ] All tests pass
- [ ] `mypy --strict tests/doctrine/drg/test_glossary_node_kind.py` zero errors

---

## Subtask T007 — Unit tests in `tests/specify_cli/glossary/test_drg_builder.py`

**Purpose:** Validate `glossary_urn()`, `build_glossary_drg_layer()`, `_normalize()`, and `build_index()`.

**File:** `tests/specify_cli/glossary/test_drg_builder.py` (new)

**Test cases (representative set — add more for edge cases):**

```python
import hashlib
import pytest
from specify_cli.glossary.drg_builder import (
    GlossaryTermIndex, _normalize, build_index, build_glossary_drg_layer, glossary_urn
)
from specify_cli.glossary.models import SenseStatus, TermSense, TermSurface, Provenance
from specify_cli.glossary.scope import GlossaryScope
from specify_cli.glossary.store import GlossaryStore
from datetime import datetime

# --- glossary_urn ---

def test_glossary_urn_deterministic():
    assert glossary_urn("lane") == glossary_urn("lane")

def test_glossary_urn_formula():
    expected = "glossary:" + hashlib.sha256("lane".encode()).hexdigest()[:8]
    assert glossary_urn("lane") == expected

def test_glossary_urn_different_surfaces_differ():
    assert glossary_urn("lane") != glossary_urn("work package")

def test_glossary_urn_prefix():
    assert glossary_urn("anything").startswith("glossary:")

# --- _normalize ---

def test_normalize_lanes():
    assert _normalize("lanes") == "lane"

def test_normalize_missions():
    assert _normalize("missions") == "mission"

def test_normalize_implementing():
    assert _normalize("implementing") == "implement"

def test_normalize_short_stays():
    assert _normalize("WP") == "wp"  # below min stem length

def test_normalize_already_canonical():
    assert _normalize("lane") == "lane"

# --- build_index and build_glossary_drg_layer ---

def _make_store(surfaces: list[str], scope: GlossaryScope = GlossaryScope.SPEC_KITTY_CORE) -> GlossaryStore:
    store = GlossaryStore.__new__(GlossaryStore)
    store._cache = {}
    store._lookup_cached = lambda *a: ()  # stub
    from datetime import datetime
    for surface in surfaces:
        sense = TermSense(
            surface=TermSurface(surface),
            scope=scope.value,
            definition=f"Definition of {surface}",
            provenance=Provenance(actor_id="test", timestamp=datetime.now(), source="test"),
            confidence=1.0,
            status=SenseStatus.ACTIVE,
        )
        store.add_sense(sense)
    return store

def test_build_index_basic():
    store = _make_store(["lane", "mission"])
    index = build_index(store, {GlossaryScope.SPEC_KITTY_CORE})
    assert "lane" in index.surface_to_urn
    assert "mission" in index.surface_to_urn
    assert index.surface_to_urn["lane"].startswith("glossary:")

def test_build_index_lemmatized_alias():
    store = _make_store(["lane"])
    index = build_index(store, {GlossaryScope.SPEC_KITTY_CORE})
    # "lanes" should map to the same URN as "lane"
    assert "lanes" in index.surface_to_urn
    assert index.surface_to_urn["lanes"] == index.surface_to_urn["lane"]

def test_build_index_excludes_wrong_scope():
    store = _make_store(["lane"], scope=GlossaryScope.MISSION_LOCAL)
    index = build_index(store, {GlossaryScope.SPEC_KITTY_CORE})
    assert "lane" not in index.surface_to_urn

def test_build_index_empty_store():
    store = GlossaryStore.__new__(GlossaryStore)
    store._cache = {}
    index = build_index(store, {GlossaryScope.SPEC_KITTY_CORE})
    assert index.term_count == 0
```

**Validation:**
- [ ] All tests pass
- [ ] `mypy --strict tests/specify_cli/glossary/test_drg_builder.py` zero errors
- [ ] `ruff check tests/specify_cli/glossary/test_drg_builder.py` zero errors

---

## Definition of Done

- [ ] `src/doctrine/drg/models.py` has `NodeKind.GLOSSARY = "glossary"` added
- [ ] `src/specify_cli/glossary/drg_builder.py` exists with: `glossary_urn()`, `GlossaryTermIndex` dataclass, `build_glossary_drg_layer()`, `_normalize()`, `build_index()`
- [ ] `tests/doctrine/drg/test_glossary_node_kind.py` exists and all tests pass
- [ ] `tests/specify_cli/glossary/test_drg_builder.py` exists and all tests pass
- [ ] `mypy --strict src/doctrine/drg/models.py src/specify_cli/glossary/drg_builder.py` → zero errors
- [ ] `ruff check src/doctrine/drg/models.py src/specify_cli/glossary/drg_builder.py` → zero errors
- [ ] Existing DRG tests in `tests/doctrine/` still pass (backward-compat)
- [ ] `pytest src/ tests/doctrine/ tests/specify_cli/glossary/` exits 0

## Reviewer Guidance

1. Confirm `NodeKind.GLOSSARY.value` is `"glossary"` (not `"glossary_term"` or similar).
2. Confirm existing DRG YAML loads clean via `load_validated_graph()` in a test.
3. Spot-check `glossary_urn("lane")` == `"glossary:" + hashlib.sha256("lane".encode()).hexdigest()[:8]`.
4. Confirm `build_index()` includes lemmatized aliases in `surface_to_urn`.
5. Verify no new external dependencies were added (`pip show` the environment).
