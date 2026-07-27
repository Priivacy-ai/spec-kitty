# Research: Phase 1 Excision Preconditions

**Mission**: `excise-doctrine-curation-and-inline-references-01KP54J6`
**Plan reference**: [plan.md](plan.md)
**Phase**: 0 — outline & research
**Date**: 2026-04-14

Three narrow investigations whose outputs unblock Phase 1 design. No external technology research is required; this is a pure internal excision.

---

## R-1 — Inline-field inventory vs `graph.yaml` edge coverage

### Question
Does `src/doctrine/graph.yaml` already encode every relationship that is currently expressed inline via `tactic_refs:` on shipped artifacts? Any inline reference without a matching graph edge is a latent governance relationship that would be silently dropped if WP1.2 ran naïvely.

### Method
1. Enumerate every shipped YAML under `src/doctrine/` (excluding `_proposed/`, `schemas/`, and `graph.yaml`).
2. For each file, load `tactic_refs:` via `ruamel.yaml` and compute the normalized artifact ID for each referenced tactic.
3. Load `src/doctrine/graph.yaml` and index edges by `(from, to, kind)`.
4. For every `(directive|paradigm|procedure) → tactic` inline reference, assert a matching edge `{from: <kind>:<id>, to: tactic:<tactic-id>, kind: uses|references}` exists.
5. Produce a **missing-edges remediation list** — any inline reference that has no graph-edge counterpart.

### Decision
The deliverable of R-1 is the remediation list, consumed by WP1.2. If the list is non-empty:

- **Action**: WP1.2 adds the missing edges to `graph.yaml` in the same PR as the YAML stripping, **before** the fields are deleted on disk.
- **Atomicity**: Edges added and fields stripped in one PR so no intermediate commit loses the relationship.
- **Verification**: Post-edit, re-run the R-1 comparator — the "missing" set must be empty.

### Alternatives considered
- **(A)** Strip inline fields first, let tests catch the drop → rejected: tests do not currently diff inline vs graph relationships, the loss would be silent.
- **(B)** Delay WP1.2 until the Charter Synthesizer (Phase 3) can regenerate graph edges from YAML → rejected: that's exactly the coupling Phase 1 is trying to break.
- **(C)** Have the DRG validator reject a shipped tree where a `tactic_refs` field has no graph counterpart → considered but not adopted: validator only runs after Phase 1 lands; we want the remediation list before we edit.

### When to run
Run as part of WP1.2 implementation kickoff. A one-shot script; does not belong in CI. The script lives under `scripts/r1_inline_vs_graph_audit.py` in WP1.2's initial commit, is run once to produce the remediation list, and is deleted in the same PR once graph edges are added.

### Expected output shape
```yaml
# scripts/r1_inline_vs_graph_audit output (ephemeral — not committed)
missing_edges:
  - from: directive:001-architectural-integrity-standard
    to: tactic:some-tactic-that-was-inline-only
    kind: uses
    source: src/doctrine/directives/001-architectural-integrity-standard.directive.yaml
  - ...
total_shipped_artifacts_scanned: 13
total_inline_refs_found: NN
total_graph_edges_matched: NN
total_missing_edges: 0   # after remediation
```

---

## R-2 — Behavioral-equivalence of `resolve_references_transitively` and a DRG walk

### Question
Can a traversal of the merged DRG (shipped `graph.yaml` ∪ project overlay) produce an output that is a functional drop-in for `resolve_references_transitively()`'s `ResolvedReferenceGraph` payload?

### Method
1. Read `src/charter/reference_resolver.py` (187 LOC) to capture its full behavioral contract:
   - Inputs: `doctrine_service: DoctrineService`, starting directive IDs
   - Outputs: `ResolvedReferenceGraph(directives, tactics, styleguides, toolguides, procedures, unresolved)`
   - Traversal: depth-first, follows `tactic_refs`, `styleguide_refs`, `toolguide_refs`, `procedure_refs`
   - Cycle behavior: raises `DoctrineResolutionCycleError` on re-encounter in current DFS path
   - Convergence: skips re-visited nodes in the `_visited` set (DAG convergence ok)
   - Unresolved tracking: any `ref` that cannot be loaded from the service is recorded in `unresolved`
2. Read `src/doctrine/drg/query.py :: resolve_context()` and `src/doctrine/drg/loader.py :: merge_layers()` to capture the DRG traversal primitives already in place.
3. Design a new `resolve_transitive_refs()` in `src/doctrine/drg/query.py` that takes a merged graph + a list of starting artifact IDs and returns a payload with the same field shape as `ResolvedReferenceGraph` (directives, tactics, styleguides, toolguides, procedures, unresolved).
4. For every shipped directive (8 directives currently carry `tactic_refs:`), run both the legacy `resolve_references_transitively()` and the new `resolve_transitive_refs()` and assert the outputs are set-equal (sorted lists allowed for ordering differences).

### Decision (amended 2026-04-14 after internal review)
`resolve_transitive_refs()` lives in `src/doctrine/drg/query.py`. Contract details are in `contracts/resolve-transitive-refs.contract.md`.

**Correction from earlier draft**: the live DRG uses `DRGGraph` (not `MergedGraph`) and the `Relation` enum with 8 values (`requires, suggests, applies, scope, vocabulary, instantiates, replaces, delegates_to`) — NOT `uses`/`references` as an earlier draft said. `merge_layers()` returns a `DRGGraph`. The shipped traversal primitive `walk_edges(graph, start_urns, relations, max_depth)` in `src/doctrine/drg/query.py:31` is the BFS engine used internally.

**Traversal semantics**:
- `resolve_transitive_refs` is a thin bucketing wrapper over `walk_edges` — it does not reimplement BFS.
- **Relations for legacy parity**: callers pass `{Relation.REQUIRES, Relation.SUGGESTS}`. These are the two relation kinds the Phase 0 migration extractor (under `src/doctrine/drg/migration/`) used when translating inline `tactic_refs` and `paradigm_refs` into DRG edges. Confirmed by reading `resolve_context()` in the same module, which uses `SCOPE` + `REQUIRES` + `SUGGESTS` + `VOCABULARY` for action-driven context resolution — `REQUIRES` and `SUGGESTS` are the artifact-to-artifact dependency relations that mirror the legacy `tactic_refs` transitivity.
- **Start URNs**: caller constructs `start_urns = {f"directive:{d}" for d in starting_directive_ids}` (or the appropriate prefix per starting kind).
- **Return shape**: per-kind bucketed `ResolveTransitiveRefsResult`, with bare IDs (URN prefix stripped) to match legacy field shape.
- **Cycle behavior**: `requires` cycles are already rejected at load time by `assert_valid()`. Other relations are allowed to cycle; `walk_edges`' BFS-with-visited-set handles this safely. The function does NOT raise `DoctrineResolutionCycleError` — cycle detection is a DRG-validator concern, not a query concern.
- **Unresolved handling**: for a graph that passed `assert_valid()`, `unresolved` is always `[]` (dangling targets are rejected at load). The field exists for API symmetry.

**Proof of equivalence**: WP1.3 adds `tests/doctrine/drg/test_resolve_transitive_refs.py` with a behavioral-equivalence fixture per shipped directive that carried `tactic_refs:` on pre-WP02 state. The test asserts bucket-by-bucket set-equality between legacy `resolve_references_transitively([directive_id], svc)` and `resolve_transitive_refs(graph, start_urns={f"directive:{directive_id}"}, relations={Relation.REQUIRES, Relation.SUGGESTS})`. This test replaces the legacy `tests/charter/test_reference_resolver.py`. Equivalence is proved, not just claimed.

### Alternatives considered
- **(A)** Migrate `resolve_governance()` and `compile_charter()` directly to DRG query primitives, deleting the `ResolvedReferenceGraph` abstraction entirely → rejected: bigger scope than Phase 1; belongs to Phase 3 Synthesizer work.
- **(B)** Have `resolve_transitive_refs()` return a raw `dict` → rejected: strict-typed callers benefit from the dataclass shape; matching the legacy shape keeps call-site churn at zero.
- **(C)** Build on top of the `DoctrineService.get()` façade → rejected: that is what the legacy resolver did. The DRG graph has a distinct addressing scheme (`NodeKind:id`) that should be used directly.

---

## R-3 — Stringly-typed reference audit

### Question
Do any stringly-typed or dynamic references to `doctrine` / `curate` / `build_charter_context` / `reference_resolver` / `include_proposed` survive that static grep would miss?

### Method
1. Grep for the string `"doctrine"`, `"curate"`, `"promote"`, `"_proposed"`, `"include_proposed"`, `"reference_resolver"`, `"build_charter_context"`, `"build_context_v2"` across `src/` and `tests/`.
2. AST-walk Python source for dynamic dispatch patterns: `importlib.import_module(...)`, `getattr(module, name)`, `typer.main.get_command(...)`, `app.command(name=...)`, `register(...)`.
3. Audit Typer command-registration sites in `src/specify_cli/cli/commands/__init__.py` for any dynamic registration that might pick up `doctrine.py` even after deletion.
4. Audit `pyproject.toml` entry points and any dynamic-loaded plugin surface.
5. Audit shipped documentation under `docs/` and CLAUDE.md-style files under `src/specify_cli/missions/*/command-templates/` for reference text that must be updated.

### Decision
The deliverable of R-3 is the definitive "string occurrences that static grep missed" list — consumed by whichever WP's occurrence artifact is responsible for that category.

**Scope split by category**:
- `curate|promote|reset|status` CLI references → WP1.1 occurrence artifact
- `_proposed` path literals → WP1.1
- `tactic_refs|paradigm_refs|applies_to` schema/model references → WP1.2
- `reference_resolver` symbol references → WP1.3
- `build_charter_context|build_context_v2` symbol references → WP1.3
- `include_proposed` parameter references → WP1.3

### Alternatives considered
- **(A)** Only static grep → rejected: dynamic dispatch and string-based registration can hide references.
- **(B)** Full `pyright`/`mypy`-based reference-tracing + dead-code analysis → rejected: overkill for the scope; the simpler AST walk catches the important cases.

### Expected output shape
```yaml
# scripts/r3_stringly_typed_audit.py output (ephemeral)
static_grep_hits: NN
ast_walk_hits: 0              # any hits here are flagged for occurrence artifact
dynamic_registration_hits: 0  # same
pyproject_entry_points: 0
docs_prose_hits: NN           # routed to the SOURCE template owner
```

---

## Summary

| ID | Investigation | Phase 0 output | Consumer |
| --- | --- | --- | --- |
| R-1 | Inline-field vs graph-edge audit | Missing-edges remediation list | WP1.2 (graph edge additions before field stripping) |
| R-2 | Resolver replacement equivalence | `resolve_transitive_refs()` contract | WP1.3 (implementation + test) — captured in `contracts/resolve-transitive-refs.contract.md` |
| R-3 | Stringly-typed reference audit | Per-category occurrence inventory | WP1.1/WP1.2/WP1.3 occurrence artifacts |

All three investigations are actionable within the mission scope. None reopens Phase 0 DRG design (per spec C-004). None introduces external dependencies.
