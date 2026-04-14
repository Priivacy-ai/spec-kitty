# Data Model: Phase 1 Excision

**Mission**: `excise-doctrine-curation-and-inline-references-01KP54J6`
**Plan reference**: [plan.md](plan.md)
**Phase**: 1 — design & contracts
**Date**: 2026-04-14

This mission is primarily a **deletion** tranche. The only new data entities are (a) the occurrence-classification artifact (per-WP YAML + mission-level aggregate), (b) the validator-rejection error shape, and (c) the public contract of the replacement function `resolve_transitive_refs()`. Existing data entities are shown with their post-Phase-1 shape to make the removal explicit.

---

## Entities

### E-1 — Occurrence-Classification Artifact (NEW)

**Purpose**: per-WP, category-aware inventory of every string occurrence touched by that WP. Verifier script asserts the "to-change" set is empty on disk at WP completion.

**Schema**: see `contracts/occurrence-artifact.schema.yaml`.

**Fields**:

| Field | Type | Required | Semantics |
| --- | --- | --- | --- |
| `wp_id` | `str` | yes | E.g. `WP1.1`, `WP1.2`, `WP1.3`. |
| `mission_slug` | `str` | yes | `excise-doctrine-curation-and-inline-references-01KP54J6`. |
| `requires_merged` | `list[str]` | yes | Preceding WP IDs that must be merged. WP1.1 → `[]`; WP1.2 → `[WP1.1]`; WP1.3 → `[WP1.1, WP1.2]`. |
| `categories` | `list[OccurrenceCategory]` | yes | Per-#393 categories; see below. |
| `permitted_exceptions` | `list[PermittedException]` | yes | Paths or strings explicitly carved out of the must-be-zero set, each with a rationale. |
| `verifier_command` | `str` | yes | Shell command to re-run the verifier. Canonical: `python scripts/verify_occurrences.py kitty-specs/<slug>/occurrences/WP1.<n>.yaml`. |

**OccurrenceCategory** sub-shape:

| Field | Type | Required | Semantics |
| --- | --- | --- | --- |
| `name` | `str` | yes | One of: `import_path`, `symbol_name`, `yaml_key`, `filesystem_path_literal`, `cli_command_name`, `docstring_or_comment`, `template_reference`, `test_identifier`. |
| `strings` | `list[str]` | yes | Literal strings searched for. |
| `include_globs` | `list[str]` | yes | Paths within repo that are in scope for this category. |
| `exclude_globs` | `list[str]` | yes | Paths explicitly excluded (e.g. `kitty-specs/**`, `.claude/**` agent copies). |
| `expected_final_count` | `int` | yes | Number of hits that should remain at WP completion. Almost always `0`; exceptions get a permitted-exception entry. |
| `to_change` | `list[FileHit]` | yes | Pre-edit list of hits the WP must resolve. At merge, this list must be empty when re-run by the verifier. |

**FileHit** sub-shape: `{file: <path>, line: <int>, snippet: <str>, action: <delete|replace|rewrite>}`.

**PermittedException** sub-shape: `{pattern: <glob or literal>, reason: <str>, owner_wp: <WP ID>}`.

**Validation rules**:
- `categories` is non-empty.
- `wp_id` matches `WP1\.[1-3]`.
- Every string in `categories[*].strings` appears in at least one `to_change[*].snippet` OR in `permitted_exceptions`.
- `expected_final_count == len(to_change_after_edits)` (enforced by verifier).

---

### E-2 — Mission-Level Occurrence Index (NEW)

**Purpose**: aggregate assertion across all WPs that the mission-wide must-be-zero set is empty at final merge.

**Path**: `kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/index.yaml`

**Fields**:

| Field | Type | Required | Semantics |
| --- | --- | --- | --- |
| `mission_slug` | `str` | yes | Mission slug. |
| `wps` | `list[str]` | yes | Ordered list: `[WP1.1, WP1.2, WP1.3]`. |
| `must_be_zero` | `list[StringAssertion]` | yes | Canonical set of strings that must return zero hits across `src/` and `tests/` at final merge. |
| `permitted_exceptions` | `list[PermittedException]` | yes | Union of all WP-level exceptions, with `owner_wp` preserved. |

**StringAssertion** sub-shape:

```yaml
- literal: "curation"
  scopes: ["src/**", "tests/**"]
  excluding:
    - "kitty-specs/**"
    - "src/specify_cli/upgrade/migrations/m_3_1_1_charter_rename.py"  # C-006 carve-out
  final_count: 0
```

**Canonical must-be-zero set** (from spec NFR-004):
```
curation, _proposed, tactic_refs, paradigm_refs, applies_to,
reference_resolver, include_proposed, build_context_v2
```

The retained context-builder name `build_charter_context` is **not** in the must-be-zero set (it's the sole name post-Phase-1).

---

### E-3 — Validator Rejection Error (NEW behavior on existing validators)

**Purpose**: structured error raised by any per-kind `validation.py` when a YAML contains a forbidden inline reference field.

**Schema**: see `contracts/validator-rejection-error.schema.json`.

**Error class**: `InlineReferenceRejectedError` (subclass of existing doctrine validation exception — exact parent decided in WP1.3 implementation; must inherit whatever `validation.py` already raises today for schema violations).

**Fields**:

| Field | Type | Required | Semantics |
| --- | --- | --- | --- |
| `file_path` | `str` | yes | Absolute path of the offending YAML. |
| `forbidden_field` | `str` | yes | One of: `tactic_refs`, `paradigm_refs`, `applies_to`. |
| `artifact_kind` | `str` | yes | One of: `directive`, `tactic`, `procedure`, `paradigm`, `styleguide`, `toolguide`, `agent_profile`. |
| `migration_hint` | `str` | yes | Fixed text pointing at the graph-edge migration pattern: `"Remove <field> from YAML; add edge {from: <kind>:<id>, to: <target-kind>:<target-id>, kind: uses} to src/doctrine/graph.yaml"`. |

**Error message format**:
```
Inline reference rejected in <file_path>:
  artifact_kind: <kind>
  forbidden_field: <field>
  migration: <hint>
```

**Validation rules**:
- Raised on load, not on compile — so the error surfaces as early as possible.
- Every per-kind validator implements identical rejection semantics; the `tests/doctrine/test_inline_ref_rejection.py` suite exercises one negative fixture per kind.

---

### E-4 — `ResolveTransitiveRefsResult` (NEW return type of replacement function) — **corrected 2026-04-14**

**Purpose**: return payload for `resolve_transitive_refs()` in `src/doctrine/drg/query.py`. Per-kind bucketed output with bare IDs (URN prefix stripped) so `resolver.py` and `compiler.py` callers see a field shape close to the legacy `ResolvedReferenceGraph`.

**Schema**: see the corrected `contracts/resolve-transitive-refs.contract.md`.

**Dataclass** (frozen):

| Field | Type | Required | Semantics |
| --- | --- | --- | --- |
| `directives` | `list[str]` | yes | Bare artifact IDs of reachable directives (URN prefix stripped, lex-sorted). |
| `tactics` | `list[str]` | yes | Bare artifact IDs of reachable tactics. |
| `paradigms` | `list[str]` | yes | Bare artifact IDs of reachable paradigms. **(New vs legacy — legacy bucket didn't exist)** |
| `styleguides` | `list[str]` | yes | Bare artifact IDs of reachable styleguides. |
| `toolguides` | `list[str]` | yes | Bare artifact IDs of reachable toolguides. |
| `procedures` | `list[str]` | yes | Bare artifact IDs of reachable procedures. |
| `agent_profiles` | `list[str]` | yes | Bare artifact IDs of reachable agent profiles. **(New vs legacy)** |
| `unresolved` | `list[tuple[str, str]]` | yes | `(source_urn, target_urn)` — always `[]` for a graph that passed `assert_valid()`. |

**Property**:
- `is_complete: bool` — `True` when `len(unresolved) == 0`. Preserved from legacy for callers that use it.

**Function signature**:
```python
from doctrine.drg.models import DRGGraph, Relation

def resolve_transitive_refs(
    graph: DRGGraph,
    *,
    start_urns: set[str],
    relations: set[Relation],
    max_depth: int | None = None,
) -> ResolveTransitiveRefsResult:
    """Walk `relations` edges from `start_urns` in `graph`, bucketing reachable
    nodes by NodeKind.

    Thin wrapper over `walk_edges`. Does not reimplement BFS or cycle detection.
    Cycles in `requires` are rejected at graph-load time by `assert_valid()`.
    Other relations are allowed to cycle; the BFS visited-set handles convergence.
    """
```

**Traversal rules**:
- Delegates to `doctrine.drg.query.walk_edges(graph, start_urns, relations, max_depth)`.
- Edge kinds walked: whatever the CALLER passes in `relations`. For legacy parity with `resolve_references_transitively`, callers use `{Relation.REQUIRES, Relation.SUGGESTS}`.
- URN format: node URNs are `<kind>:<id>` (e.g. `directive:001-architectural-integrity-standard`).
- Deterministic ordering: within each returned list, bare IDs are lexicographically sorted.

---

### E-5 — DRG `DRGGraph` (existing, unchanged by this mission) — **corrected 2026-04-14**

Already present in `src/doctrine/drg/models.py`. Documented here only to show the input-side contract that `resolve_transitive_refs()` consumes. An earlier draft of this section referenced a fabricated `MergedGraph` type; the correct type is `DRGGraph`.

```python
from pydantic import BaseModel, Field

class DRGGraph(BaseModel):
    schema_version: str = Field(pattern=r"^1\.0$")
    generated_at: str
    generated_by: str
    nodes: list[DRGNode]
    edges: list[DRGEdge]

    def node_urns(self) -> set[str]: ...
    def edges_from(self, urn: str, relation: Relation | None = None) -> list[DRGEdge]: ...
    def get_node(self, urn: str) -> DRGNode | None: ...
```

`merge_layers(shipped, project)` returns a `DRGGraph` (not a separate type). `assert_valid(graph: DRGGraph)` rejects dangling edges, duplicate edges, and `requires` cycles.

**Unchanged in this mission**. Any change to `DRGGraph` is out of scope.

---

### E-6 — Shipped Artifact YAML (existing, field shape changed by this mission)

Post-Phase-1 shape for each of the seven artifact kinds:

| Kind | Forbidden fields (post-Phase-1) | Source of cross-artifact relationships |
| --- | --- | --- |
| `directive` | `tactic_refs`, `applies_to` | `graph.yaml` edges |
| `paradigm` | `tactic_refs`, `paradigm_refs` | `graph.yaml` edges |
| `procedure` | `tactic_refs` (including inside `steps[*]`) | `graph.yaml` edges |
| `tactic` | `paradigm_refs`, `tactic_refs` | `graph.yaml` edges |
| `styleguide` | `tactic_refs` | `graph.yaml` edges |
| `toolguide` | `tactic_refs` | `graph.yaml` edges |
| `agent_profile` | `tactic_refs`, `paradigm_refs`, `applies_to` | `graph.yaml` edges (if any cross-refs exist) |

**Transformation per kind** (applied in WP1.2):
1. Parse YAML with `ruamel.yaml` preserving order and comments.
2. Remove any top-level occurrence of the forbidden fields.
3. For procedures, also recurse into `steps[*]` and remove `tactic_refs` if present.
4. Write back preserving everything else byte-for-byte where possible.

---

## State Transitions

There is no runtime state machine in this mission — it is a deletion tranche. However, **mission-level sequencing** has explicit states that are tracked via the occurrence artifacts:

```
(initial)
    │
    └── WP1.1 PR open, occurrences/WP1.1.yaml authored
           │
           ├── verifier: red  ──► implementation continues
           │
           └── verifier: green + PR merged
                  │
                  ▼
           WP1.1 merged, WP1.2 unblocked
                  │
                  └── WP1.2 PR open, occurrences/WP1.2.yaml authored
                         │
                         ├── R-1 audit run, graph edges patched if needed
                         │
                         ├── verifier: red  ──► implementation continues
                         │
                         └── verifier: green + PR merged
                                │
                                ▼
                         WP1.2 merged, WP1.3 unblocked
                                │
                                └── WP1.3 PR open, occurrences/WP1.3.yaml + index.yaml final
                                       │
                                       ├── resolve_transitive_refs added + tests
                                       ├── validators reject inline refs
                                       ├── call-site flip → rename → delete reference_resolver
                                       ├── parity/legacy tests deleted AFTER replacement green
                                       │
                                       └── verifier: green + mission-level index zero + PR merged
                                              │
                                              ▼
                                       Phase 1 complete
```

**Invariant**: The occurrence artifact's `requires_merged` field is enforced in CI — a WP cannot pass the verifier unless every predecessor in `requires_merged` is merged to `main`.

---

## Summary

This mission introduces three new entities: the occurrence-classification artifact (per-WP + mission-level), the validator-rejection error, and the `ResolveTransitiveRefsResult` dataclass. It changes the on-disk shape of seven artifact kinds by removing three forbidden fields. It deletes one resolver package, one CLI command surface, one validator module, one package (`curation`), and a handful of supporting files. All of this is driven by the plan-phase decisions in `plan.md`.
