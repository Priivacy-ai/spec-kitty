---
work_package_id: WP06
title: Org-layer DRG — schema, loader, merge, conflict policy, validator extension
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- C-001
- C-009
- FR-001
- FR-003
- FR-004
- FR-005
- NFR-003
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
- T031
- T032
- T033
agent: claude:opus-4-7:python-pedro:implementer
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/drg.py
execution_mode: code_change
owned_files:
- src/charter/drg.py
- src/specify_cli/cli/commands/charter.py
- tests/charter/test_org_drg_loader.py
- tests/integration/test_three_layer_drg_end_to_end.py
- tests/integration/test_org_pack_missing_path_hard_fails.py
- tests/charter/test_org_drg_cannot_override_shipped_invariants.py
- tests/integration/test_charter_lint_lints_all_layers.py
- tests/architectural/_fixtures/org_packs/example_org/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else.

---

## Objective

Land the **org-layer of the three-layer DRG** (Axis 1 of Slice F per spec §1.1): introduce `OrgDRGFragment` (Pydantic v2) + `OrgDRGConflict` (dataclass + exception) in `src/charter/drg.py`; implement `load_org_drg(repo_root) -> list[OrgDRGFragment]` reading `.kittify/config.yaml::organisation_packs:`; implement `merge_three_layers(shipped, org_fragments, project) -> DRGGraph` with shipped-wins-on-invariant + hard-fail-on-layer-rule-violation; extend `spec-kitty charter lint` to lint all three layers with named-source provenance.

This WP is the lane-opening WP for Lane C; subsequent WPs (WP07 integration, WP08 operator UX) turn additional ATDD assertions green.

---

## Context

Mission B added the **selection** layer of three-layer governance (the `selected_<kind>` / `required_<kind>` parity, the activation registry, mission-type profiles). Slice F adds the **DRG** layer — the graph of doctrine relationships overlaid as shipped → org → project.

Per **C-009** (binding): the org-DRG schema MUST reuse Mission B's 8-kind plural-naming union semantics. The 8 kinds are: `directives`, `tactics`, `styleguides`, `toolguides`, `paradigms`, `procedures`, `agent_profiles`, `mission_step_contracts`.

Per **C-001** (binding): the layer rule `kernel ← doctrine ← charter ← specify_cli` is preserved. The org-DRG loader lives under `src/charter/` (correct layer). Any org pack that imports across the layer boundary (e.g. its DRG fragment declares a node whose body references `src/specify_cli/...`) fails to load with `OrgDRGConflictError(kind="layer_rule_violation")`.

Per **FR-004** (mirroring Mission B FR-015): when a configured `local_path` does not exist on disk, the runtime hard-fails with an operator-actionable error. No silent fallback.

Per **NEW-1 resolution** (plan §6): this mission ships `source: local_path` only. `url` and `package` sources raise `NotImplementedError`.

References:
- [spec.md §"Scenario 1 — Organisation-tier doctrine"](../spec.md)
- [spec.md §"Slice F core — Axis 1: Three-layer DRG resolution"](../spec.md) (FR-001 .. FR-007)
- [plan.md §1.1, §2.1](../plan.md)
- [contracts/org-drg-schema.md](../contracts/org-drg-schema.md)
- [data-model.md §2 OrgDRGFragment, §3 OrgDRGConflict](../data-model.md)
- [atdd-coverage.md Scenario 1, AC-1](../atdd-coverage.md)

**Dependency on Lane A:** WP06 cannot START until WP01 merges (RR-1). New modules introduced here (`OrgDRGFragment`, loader, merge) must not grandfather themselves into Cat-7. WP02 requires `__all__` on new charter modules; WP03 requires contract round-trip frontmatter on `contracts/org-drg-schema.md`.

---

## ATDD Discipline

Per **C-011** WP06 is the lane-opening WP for Lane C and lands the full failing-first suite as its FIRST commit:

1. **Commit A (RED, T027):** Land all four ATDD tests RED on planning base. Commit message: `covers: Scenario 1, Scenario 1 exception, FR-004, FR-005, AC-1 — expected GREEN at: WP06/WP07/WP08 final commits`.
2. **Commits B..G (GREEN progression, T028-T033):** schema + loader + merge + validator + unit tests; the four ATDD tests turn green for FR-001/003/004/005 (charter status reporting GREEN comes in WP07 T034).

ATDD anchors per [atdd-coverage.md](../atdd-coverage.md):

- Scenario 1: `tests/integration/test_three_layer_drg_end_to_end.py::test_org_drg_fragment_merges_through_three_layers_with_provenance`
- Scenario 1 exception: `tests/integration/test_org_pack_missing_path_hard_fails.py::test_org_pack_with_missing_local_path_raises_named_error`
- FR-005: `tests/charter/test_org_drg_cannot_override_shipped_invariants.py`
- FR-003: `tests/integration/test_charter_lint_lints_all_layers.py`
- AC-1: `tests/integration/test_three_layer_drg_end_to_end.py::test_charter_lint_lints_all_three_layers_with_provenance`

---

## Subtasks

### T027 — Land failing-first Lane C ATDD suite (4 tests)

**Files (all new):**
- `tests/integration/test_three_layer_drg_end_to_end.py`
- `tests/integration/test_org_pack_missing_path_hard_fails.py`
- `tests/charter/test_org_drg_cannot_override_shipped_invariants.py`
- `tests/integration/test_charter_lint_lints_all_layers.py`

Each test imports from `charter.drg` symbols that don't yet exist (`OrgDRGFragment`, `load_org_drg`, `merge_three_layers`, `OrgDRGConflictError`). All FAIL with `ImportError` on planning base.

Also scaffold a fixture org pack: `tests/architectural/_fixtures/org_packs/example_org/` with `org-charter.yaml`, `drg/fragment.yaml`, and one referenced `directives/sox-controls.directive.yaml` (per RR-10).

Sample assertions:

```python
# test_three_layer_drg_end_to_end.py
def test_org_drg_fragment_merges_through_three_layers_with_provenance(tmp_repo_with_org_pack):
    from charter.drg import load_org_drg, merge_three_layers
    fragments = load_org_drg(tmp_repo_with_org_pack)
    assert len(fragments) == 1
    assert fragments[0].pack_name == "example-org"
    merged = merge_three_layers(shipped=..., org_fragments=fragments, project=None)
    assert any(n.source == "org:example-org" for n in merged.nodes)
    assert any(n.source == "built-in" for n in merged.nodes)

def test_charter_lint_lints_all_three_layers_with_provenance(tmp_repo_with_org_pack):
    # Invokes `spec-kitty charter lint` in-process; checks per-layer findings
    ...
```

```python
# test_org_pack_missing_path_hard_fails.py
def test_org_pack_with_missing_local_path_raises_named_error(tmp_repo_with_dangling_pack):
    from charter.drg import load_org_drg, OrgPackMissingError
    with pytest.raises(OrgPackMissingError, match="acme-compliance.*dangling-pack"):
        load_org_drg(tmp_repo_with_dangling_pack)
```

```python
# test_org_drg_cannot_override_shipped_invariants.py
def test_org_pack_overriding_shipped_node_hard_fails(...):
    from charter.drg import merge_three_layers, OrgDRGConflictError
    with pytest.raises(OrgDRGConflictError) as exc_info:
        merge_three_layers(shipped=<has node X>, org_fragments=[<overrides X>], project=None)
    assert exc_info.value.conflicts[0].kind in ("node_override", "edge_override")
```

**Validation:** `pytest tests/integration/test_three_layer_drg_end_to_end.py tests/integration/test_org_pack_missing_path_hard_fails.py tests/charter/test_org_drg_cannot_override_shipped_invariants.py tests/integration/test_charter_lint_lints_all_layers.py -v` MUST FAIL on planning base (ImportError). Commit RED.

### T028 — Add `OrgDRGFragment` Pydantic v2 model

**File:** `src/charter/drg.py`

Per data-model §2:

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "OrgDRGFragment",
    "OrgDRGConflict",
    "OrgDRGConflictError",
    "OrgPackMissingError",
    "load_org_drg",
    "merge_three_layers",
]

_CANONICAL_KINDS: frozenset[str] = frozenset({
    "directives", "tactics", "styleguides", "toolguides",
    "paradigms", "procedures", "agent_profiles", "mission_step_contracts",
})


class OrgDRGFragment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_name: str
    source_kind: Literal["local_path", "url", "package"]
    source_ref: str
    layer_index: int = Field(ge=1)
    provenance_marker: Literal["org"] = "org"
    nodes: list["DRGNode"] = Field(default_factory=list)
    edges: list["DRGEdge"] = Field(default_factory=list)

    @field_validator("nodes")
    @classmethod
    def _validate_node_kinds(cls, value: list["DRGNode"]) -> list["DRGNode"]:
        for n in value:
            if n.kind not in _CANONICAL_KINDS:
                raise ValueError(
                    f"node kind {n.kind!r} not in canonical 8-kind universe "
                    f"(C-009 binding): {sorted(_CANONICAL_KINDS)}"
                )
        return value
```

Reuse `DRGNode` and `DRGEdge` from the existing `doctrine.drg.models` module (do NOT re-implement). Verify the import is layer-rule-clean (`charter` may import from `doctrine` per the rule `kernel ← doctrine ← charter ← specify_cli`).

### T029 — Add `OrgDRGConflict` + `OrgDRGConflictError` + `OrgPackMissingError`

**File:** `src/charter/drg.py`

Per data-model §3:

```python
from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class OrgDRGConflict:
    kind: Literal["edge_override", "node_override", "kind_mismatch", "layer_rule_violation"]
    conflicting_layers: list[str]
    target_id: str
    shipped_value: Any | None
    org_value: Any
    project_value: Any | None
    resolution_applied: Literal["hard_fail", "shipped_wins", "project_wins"]


class OrgDRGConflictError(Exception):
    """Raised when an org-DRG fragment violates the layer rule or
    overrides a shipped invariant in a non-recoverable way."""

    def __init__(self, conflicts: list[OrgDRGConflict]):
        self.conflicts = conflicts
        super().__init__(self._format_message(conflicts))

    @staticmethod
    def _format_message(conflicts: list[OrgDRGConflict]) -> str:
        lines = [f"{len(conflicts)} org-DRG conflict(s):"]
        for c in conflicts:
            lines.append(
                f"  - kind={c.kind}, target_id={c.target_id}, "
                f"layers={c.conflicting_layers}, resolution={c.resolution_applied}"
            )
        return "\n".join(lines)


class OrgPackMissingError(Exception):
    """Raised when a configured org pack's local_path does not exist (FR-004)."""

    def __init__(self, pack_name: str, configured_path: str):
        self.pack_name = pack_name
        self.configured_path = configured_path
        super().__init__(
            f"Org pack {pack_name!r} configured at {configured_path!r} not found. "
            f"Either fetch the pack (`spec-kitty doctrine fetch --pack {pack_name}`) "
            f"or remove the entry from `.kittify/config.yaml`."
        )
```

### T030 — Implement `load_org_drg(repo_root) -> list[OrgDRGFragment]`

**File:** `src/charter/drg.py`

```python
from pathlib import Path
import yaml


def load_org_drg(repo_root: Path) -> list[OrgDRGFragment]:
    """Load all configured org packs from .kittify/config.yaml.

    Returns one OrgDRGFragment per pack in declaration order. Layer indices
    are assigned 1..N. Missing local_path raises OrgPackMissingError (FR-004).
    URL and package sources raise NotImplementedError (NEW-1).
    """
    config_path = repo_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        return []
    config = yaml.safe_load(config_path.read_text()) or {}
    packs_config = config.get("organisation_packs", []) or []
    fragments: list[OrgDRGFragment] = []
    for layer_index, entry in enumerate(packs_config, start=1):
        name = entry["name"]
        source = entry["source"]
        if source != "local_path":
            raise NotImplementedError(
                f"Org pack source {source!r} not yet implemented "
                f"(tracker: <ticket>). Use `source: local_path` for now."
            )
        path = Path(entry["path"])
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        if not path.is_dir():
            raise OrgPackMissingError(name, str(path))
        fragment_yaml = path / "drg" / "fragment.yaml"
        if not fragment_yaml.exists():
            raise OrgPackMissingError(name, str(fragment_yaml))
        fragment_data = yaml.safe_load(fragment_yaml.read_text())
        # Override pack-side declared fields with operator-side authoritative values:
        fragment_data["pack_name"] = name
        fragment_data["source_kind"] = "local_path"
        fragment_data["source_ref"] = str(path)
        fragment_data["layer_index"] = layer_index
        fragments.append(OrgDRGFragment.model_validate(fragment_data))
    return fragments
```

### T031 — Implement `merge_three_layers`

**File:** `src/charter/drg.py`

```python
def merge_three_layers(
    shipped: "DRGGraph",
    org_fragments: list[OrgDRGFragment],
    project: "DRGGraph | None",
) -> "DRGGraph":
    """Overlay shipped → org → project layers. Shipped invariants always win.

    Conflicts produce OrgDRGConflictError unless silently resolvable (shipped wins).
    Layer-rule violations always hard-fail (FR-005).
    """
    conflicts: list[OrgDRGConflict] = []
    merged_nodes: dict[str, Any] = {n.id: _tagged(n, "built-in") for n in shipped.nodes}
    merged_edges: list[Any] = [_tagged(e, "built-in") for e in shipped.edges]

    shipped_invariant_ids = _shipped_invariant_ids(shipped)

    for fragment in org_fragments:
        source = f"org:{fragment.pack_name}"
        for node in fragment.nodes:
            if _violates_layer_rule(node):
                conflicts.append(OrgDRGConflict(
                    kind="layer_rule_violation",
                    conflicting_layers=[source],
                    target_id=node.id,
                    shipped_value=None,
                    org_value=node,
                    project_value=None,
                    resolution_applied="hard_fail",
                ))
                continue
            if node.id in shipped_invariant_ids:
                conflicts.append(OrgDRGConflict(
                    kind="node_override",
                    conflicting_layers=["built-in", source],
                    target_id=node.id,
                    shipped_value=merged_nodes[node.id],
                    org_value=node,
                    project_value=None,
                    resolution_applied="hard_fail",   # invariants always hard-fail
                ))
                continue
            merged_nodes[node.id] = _tagged(node, source)
        # similar loop for edges...

    if any(c.resolution_applied == "hard_fail" for c in conflicts):
        raise OrgDRGConflictError(conflicts)

    if project is not None:
        for node in project.nodes:
            merged_nodes[node.id] = _tagged(node, "project")
        for edge in project.edges:
            merged_edges.append(_tagged(edge, "project"))

    return DRGGraph(nodes=list(merged_nodes.values()), edges=merged_edges)
```

The `_tagged` helper attaches a `source` field to each node/edge (use a sidecar dict if the model is frozen, or extend `DRGNode`/`DRGEdge` with an optional `source: str | None` field — verify the existing model shape first).

### T032 — Extend `spec-kitty charter lint` to lint all three layers

**File:** `src/specify_cli/cli/commands/charter.py`

Find the existing `charter lint` implementation. Extend the loader chain:

```python
def lint(...):
    shipped = load_shipped_drg()
    org_fragments = load_org_drg(repo_root)
    project = load_project_drg(repo_root)
    findings = []
    findings.extend(lint_layer("built-in", shipped))
    for fragment in org_fragments:
        findings.extend(lint_layer(f"org:{fragment.pack_name}", fragment))
    if project:
        findings.extend(lint_layer("project", project))
    render_findings(findings)
```

Per-layer findings include the source name in the output:

```
[built-in]    OK — 87 nodes, 142 edges
[org:acme-compliance]   OK — 12 nodes, 4 edges
[project]     warn: directive 'caveman-comments' selected but no body found
```

### T033 — Add unit coverage; Lane C ATDD GREEN

**File:** `tests/charter/test_org_drg_loader.py` (new)

Unit-level coverage for:

- `OrgDRGFragment` validates with all 8 kinds; rejects unknown kind (C-009).
- `load_org_drg` returns `[]` when no `.kittify/config.yaml` exists.
- `load_org_drg` returns one fragment per `organisation_packs:` entry.
- `load_org_drg` raises `OrgPackMissingError` when path missing.
- `load_org_drg` raises `NotImplementedError` for `source: url` / `package`.
- `merge_three_layers` tags every node/edge with the source name.
- `merge_three_layers` hard-fails on layer-rule violation (FR-005).
- `merge_three_layers` hard-fails on shipped-invariant override (FR-005).

Run:

```bash
pytest tests/charter/ tests/integration/test_three_layer_drg_end_to_end.py tests/integration/test_org_pack_missing_path_hard_fails.py tests/charter/test_org_drg_cannot_override_shipped_invariants.py tests/integration/test_charter_lint_lints_all_layers.py -v
# EXPECTED: GREEN (Lane C ATDD turns green for FR-001/003/004/005)

PWHEADLESS=1 pytest tests/architectural/ -v
# EXPECTED: exit 0 (NFR-005)

pytest tests/architectural/test_layer_rules.py -v
# EXPECTED: pass unchanged (NFR-003)
```

---

## Definition of Done

The following tests turn GREEN with this WP:

- ✅ `tests/integration/test_three_layer_drg_end_to_end.py::test_org_drg_fragment_merges_through_three_layers_with_provenance`
- ✅ `tests/integration/test_three_layer_drg_end_to_end.py::test_charter_lint_lints_all_three_layers_with_provenance`
- ✅ `tests/integration/test_org_pack_missing_path_hard_fails.py::test_org_pack_with_missing_local_path_raises_named_error`
- ✅ `tests/charter/test_org_drg_cannot_override_shipped_invariants.py::*`
- ✅ `tests/integration/test_charter_lint_lints_all_layers.py::*`
- ✅ `tests/charter/test_org_drg_loader.py::*` (new unit suite)
- ✅ `pytest tests/architectural/test_layer_rules.py -v` unchanged (NFR-003)
- ✅ Full architectural sweep exit 0 (NFR-005)
- ✅ 23 governance-contract fixtures pass unchanged (NFR-001 — no org pack configured ⇒ identical behaviour)

FR coverage:

- ✅ FR-001 — three-layer loader + merge with per-artifact provenance
- ✅ FR-003 — `charter lint` lints all three layers with named-source findings
- ✅ FR-004 — missing org pack path hard-fails with named error
- ✅ FR-005 — layer-rule violations hard-fail; shipped invariants cannot be overridden
- ✅ C-009 — 8-kind plural-naming reused from Mission B (no kind universe divergence)
- ✅ C-001 — layer rule preserved (charter may import from doctrine; not from specify_cli)

AC coverage:

- ✅ Partial AC-1 — three-layer DRG operational end-to-end (charter lint lints all three; AC-1's `build_charter_context` provenance comes in WP07)

---

## Risks

1. **`DRGNode` / `DRGEdge` shape mismatch** — the existing `doctrine.drg.models` may not have a `source` field. Mitigation: T031 either adds an optional `source: str | None` field to the model (charter is allowed to depend on doctrine) OR uses a sidecar `dict[node_id, source]` map threaded through the merge result. Choose based on the existing model's mutability constraints.
2. **Org pack kind mismatch (C-009 violation)** — Mission B's 8 kinds may not exactly match the pack-side schema if a typo lands. Mitigation: T028's `_validate_node_kinds` enforces; T033's unit suite asserts both valid and invalid examples.
3. **Layer-rule violation detection is hard** — how does the merge detect that a node's `body_path` references `src/specify_cli/`? Mitigation: T031's `_violates_layer_rule` checks (a) any path component matches `src/specify_cli/`, and (b) any import declaration references `specify_cli.*`. The check is conservative; false positives surface as actionable errors.
4. **Reading existing project DRG layer** — does `load_project_drg` already exist? Mitigation: if not, T030 + T031 just collapse to the shipped+org case; WP07's integration adds the project layer wiring if needed.
5. **Fixture org pack design** — `tests/architectural/_fixtures/org_packs/example_org/` shape needs to mirror operator reality (RR-10). Mitigation: T027 lands the canonical fixture (one fragment, one referenced artifact); subsequent WPs (WP07, WP08) reuse it.
6. **Hard-fail in `merge_three_layers` doesn't fire when org overrides a NON-invariant shipped node** — that's an edge_override but resolution is "shipped_wins" (silent) per data-model §3. Mitigation: T031 distinguishes "invariant override" (hard_fail) from "non-invariant override" (silent shipped-wins with WARNING log). Use a frozen set of `_SHIPPED_INVARIANTS` declared at module load time; refine the set as WP07 integration surfaces real invariants.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011):**

```bash
# 1. RED on planning base:
git checkout feat/org-doctrine-layer
pytest tests/integration/test_three_layer_drg_end_to_end.py \
       tests/integration/test_org_pack_missing_path_hard_fails.py \
       tests/charter/test_org_drg_cannot_override_shipped_invariants.py \
       tests/integration/test_charter_lint_lints_all_layers.py -v
# EXPECTED: ImportError or collection error (charter.drg symbols don't exist yet)

# 2. GREEN on WP final commit:
git checkout <wp_branch>
pytest tests/integration/test_three_layer_drg_end_to_end.py \
       tests/integration/test_org_pack_missing_path_hard_fails.py \
       tests/charter/test_org_drg_cannot_override_shipped_invariants.py \
       tests/integration/test_charter_lint_lints_all_layers.py \
       tests/charter/test_org_drg_loader.py -v
# EXPECTED: GREEN
```

**Substantive review checks:**

- Confirm `src/charter/drg.py` declares `__all__` per WP02's convention (C-007).
- Confirm `_CANONICAL_KINDS` matches Mission B's 8 kinds EXACTLY (no rename, no addition).
- Confirm `merge_three_layers` hard-fails on (a) layer-rule violation and (b) shipped-invariant override, with operator-actionable error messages.
- Confirm `load_org_drg` returns `[]` (empty list) when `.kittify/config.yaml` is absent — required for NFR-001 byte-stability (the 23 fixtures don't configure org packs).
- Confirm `charter.drg` imports nothing from `src/specify_cli/` (NFR-003).
- Confirm `contracts/org-drg-schema.md`'s tagged YAML codeblocks round-trip via WP03's gate (the `expect: valid` and `expect: invalid` examples).
- Confirm `tests/architectural/_fixtures/org_packs/example_org/` is committed and minimal.
- Confirm full architectural sweep exit 0 (NFR-005).

**FR-304 commit-message check:** T027 RED commit cites `covers: Scenario 1, Scenario 1 exception, FR-004, FR-005, AC-1 (partial)` and `expected GREEN at: WP06/WP07/WP08`.
