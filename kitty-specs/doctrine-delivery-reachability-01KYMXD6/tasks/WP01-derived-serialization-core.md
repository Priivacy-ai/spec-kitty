---
work_package_id: WP01
title: Derived serialization core and the writer registry
dependencies: []
requirement_refs:
- C-001
- C-005
- C-006
- C-010
- FR-001
- FR-002
- NFR-002
- NFR-005
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-delivery-reachability-01KYMXD6
base_commit: 32d37437da55f5fbab87288587c6ac9e82a4fe17
created_at: '2026-07-28T20:51:19.263906+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Foundation
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/drg_writers/
create_intent:
- src/specify_cli/drg_writers/__init__.py
- src/specify_cli/drg_writers/registry.py
- tests/specify_cli/drg_writers/test_registry_completeness.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/drg_writers/**
- src/doctrine/drg/migration/extractor.py
- src/charter/synthesizer/project_drg.py
- src/specify_cli/migration/rewrite_opposed_by.py
- src/charter/drg.py
- tests/specify_cli/drg_writers/**
- tests/doctrine/drg/test_model_strictness_roundtrip.py
- tests/charter/synthesizer/test_project_drg.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP01 — Derived serialization core and the writer registry

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show python-pedro`** — this returns the *resolved*
definition, with `specializes_from` lineage and `enhances`/`overrides` merges applied. **Do not read
`src/doctrine/agent_profiles/built-in/*.agent.yaml` directly**: the raw file is the unresolved base
and silently drops exactly the doctrine this mission exists to deliver. To discover a profile when one
is not named, run `spec-kitty agent profile list`.

---

## Objective

Make the set of graph write paths **derived and enumerable**, so that a field added to `DRGNode` or
`DRGEdge` later cannot be silently dropped by a writer nobody remembered to update.

This is mission **B1's unblock**. B1 (`drg-relation-impacts-vocabulary-01KYFV87`) exists to add two
new edge fields (`impacts`, `is_symmetric`). Landing B1 over the current writers reproduces the exact
defect class this programme exists to close — the field ships inert and every test stays green.

**This work package must carry no inbound dependency.** It is the one package that can land alone.

## Context you need before starting

### The defect, measured

`DRGEdge.model_fields` is `[source, target, relation, when, reason, provenance]`.
`DRGNode.model_fields` is `[urn, kind, label, provenance, tags]`.

Three code paths persist that state, and only one derives its output from the model:

| Site | Status |
|---|---|
| `src/doctrine/drg/migration/extractor.py` — `_node_to_dict` / `_edge_to_dict` | **Derived already.** `_model_to_dict` + `_FIELDS_WITHHELD_FROM_GRAPH_OUTPUT`. This is the reference implementation |
| `src/specify_cli/migration/rewrite_opposed_by.py:338` / `:347` | Hand-restated — but **already guarded** by `tests/doctrine/drg/test_model_strictness_roundtrip.py:520` / `:557`, which go red when B1 lands |
| `src/charter/synthesizer/project_drg.py:65` `_serialize_graph` | Hand-restated, dicts built **inline in two loops**, and **guarded by nothing** |

**Priority inside this WP is inverted from the obvious reading.** Verified by mutation: deleting
`edge.reason` from `project_drg._serialize_graph` leaves `tests/charter/synthesizer/test_project_drg.py`
at 23 passed — identical to baseline. `grep -n "tags\|provenance\|model_fields"` on that test file
returns nothing. **`project_drg` is the unprotected one. Start there.**

### Two traps that will cost you a day each

**The derived helper is not actually total.** `_render_for_yaml` returns `None` for `None` **and for
an empty list**, and `_model_to_dict` then drops the key. Proven:

| novel field added to the model | survives the derived writers? |
|---|---|
| `impacts: str \| None = None` | **no** |
| `impacts: list[str] = []` | **no** |
| `is_symmetric: bool = False` | yes |

B1's `impacts` is plausibly list-shaped. If you assert W-1 over a sparsely-populated instance, the
gate passes for every writer and is **vacuous for exactly the field it exists to protect**.

**The registry cannot live in `doctrine`.** A tuple naming `charter.synthesizer.project_drg` and
`specify_cli.migration.rewrite_opposed_by` requires `doctrine` to import upward, which reds
`tests/architectural/test_layer_rules.py:282` and `:293`. `charter` reds `:311`. **Only
`src/specify_cli/` can statically hold all members.** Tests are not layered — the precedent is
`tests/doctrine/drg/test_model_strictness_roundtrip.py:542`, which already imports
`specify_cli.migration`.

Do **not** solve this with import-time self-registration. It makes membership depend on import order
and re-opens the blind spot the registry already concedes.

### Read before you start

- [`contracts/writer-registry.md`](../contracts/writer-registry.md) — the binding contract, W-1 to W-5
- [`research/post-plan-squad-findings.md`](../research/post-plan-squad-findings.md) §3 — the mutation evidence
- [`quickstart.md`](../quickstart.md) — the reproduction commands and the trap table

---

## Subtasks

### T001 — Export the derived serialization helper from the extractor

**Purpose**: The derived helper (`_model_to_dict`, `_FIELDS_WITHHELD_FROM_GRAPH_OUTPUT`) is private to
the extractor. Every other writer needs it.

**Steps**:
1. Promote `_model_to_dict` to a public, documented surface in `src/doctrine/drg/migration/extractor.py`.
   Keep the private alias if internal callers use it.
2. Export it through `src/charter/drg.py`'s **existing** `__all__`. That module already exists — 532
   lines, 24 entries — and `rewrite_opposed_by.py:97` already imports `DRGEdge, DRGGraph, DRGNode,
   NodeKind, Relation` through it. **You are adding to an export surface, not creating a facade.**
3. Confirm no import cycle: `charter/synthesizer/project_drg.py` imports `doctrine.drg.models` and
   `charter.synthesizer._constants`, not `charter.drg`.

**Validation**: `pytest tests/architectural/test_layer_rules.py tests/architectural/test_runtime_charter_doctrine_boundary.py -q` stays green (17 + 14 at baseline).

### T002 — Close the empty-value hole (contract W-1a)

**Purpose**: Make the derivation total over *values*, not just over field names.

**Steps**:
1. Write the failing test first: construct an edge with a novel field whose value is `None`, and one
   whose value is `[]`. Assert both keys are emitted.
2. Decide and **document** the rule — emit-with-empty, or a second declared withholding set that names
   which empty values are intentionally dropped. Either is acceptable; silence is not.
3. Implement in `_render_for_yaml` / `_model_to_dict`.

**Validation**: the two red tests go green; existing graph fragments are byte-identical unless the
rule intentionally changes them — if it does, that is a composition-ledger row under NFR-004, not a
silent diff.

### T003 — Extract `project_drg`'s inline dicts into mapping functions [P]

**Purpose**: `_serialize_graph` builds its node and edge dicts inline in two loops, so it cannot join a
registry. This is a **prerequisite refactor**, not a registry join.

**Steps**:
1. Extract `_node_to_dict(node) -> dict` and `_edge_to_dict(edge) -> dict` from the two loops in
   `src/charter/synthesizer/project_drg.py:65`.
2. Keep behaviour byte-identical at this step. Prove it: serialize a fixture graph before and after,
   assert equality.
3. Only then switch them to the derived helper (T005).

**Validation**: `pytest tests/charter/synthesizer/test_project_drg.py -q` green at each step.

### T004 — Define the three registry shapes

**Purpose**: The five persistence sites are three different kinds of thing. One Protocol cannot hold
them.

**Steps**:
1. Create `src/specify_cli/drg_writers/registry.py` with three Protocols:
   - `MappingWriter` — `node_to_mapping(DRGNode) -> dict`, `edge_to_mapping(DRGEdge) -> dict`
   - `DocumentWriter` — `document_to_mapping(DRGGraph) -> dict`
   - `ModelBridge` — mints a `DRGEdge`/`DRGNode` from a foreign fragment shape
2. Declare `MAPPING_WRITERS`, `DOCUMENT_WRITERS`, `MODEL_BRIDGES` as explicit `Final` tuples.
3. Each member carries a stable `name` used in failure messages.

**Why three**: `project_drg._serialize_graph` is `(DRGGraph) -> str`; `_dump_graph_document` is
`(DRGGraph, Path) -> None`; `_bridge_org_edge_to_drg_edge` takes a fragment edge and returns
`tuple[DRGEdge | None, conflict | None]`. Forcing them into `edge_to_mapping` is not type-correct.

### T005 — Join the mapping writers; retire the hand-written dicts

**Steps**:
1. Point `project_drg`'s extracted functions at the derived helper. **This is the fix that matters** —
   it is the unguarded writer.
2. Point `rewrite_opposed_by._node_to_dict` / `_edge_to_dict` at the derived helper and register them.
   Their existing tests at `test_model_strictness_roundtrip.py:520`/`:557` must stay green — **do not
   add a duplicate assertion**, they already cover this writer.
3. Register the extractor pair.

**Validation**: `pytest tests/doctrine/drg/test_model_strictness_roundtrip.py tests/charter/synthesizer/test_project_drg.py -q`.

### T006 — Derive `_dump_graph_document`'s document-level keys

**Purpose**: The extractor's own docstring names four sites and closes with *"Anyone adding a model
field should check all four sites, not just this one."* The document level is the fourth.

**Steps**:
1. Derive the five document-level keys from `DRGGraph.model_fields` rather than restating them.
2. Register `_dump_graph_document` as a `DocumentWriter`.

**Note**: `DRGGraph.model_config` (adding `extra="forbid"`) is **WP02's**, deliberately — it is a
consumer-facing read-path break and must not ride the lane that lands first and alone.

### T007 — Red-first mutation fixture across all registry shapes

**Purpose**: C-006 requires the mutation be **executable and committed**, never narrated.

**Steps**:
1. Build the fixture by **subclassing** — verified as the only viable route: the models are not frozen
   (only `extra="forbid"`), attribute injection raises `ValueError`, and an extra constructor kwarg
   raises `ValidationError`. `DRGGraph` does **not** re-validate or coerce, so a subclass instance
   survives into a graph and reaches the document writer.
2. Populate **every** field (W-1) so the empty-value hole from T002 does not mask a real drop.
3. Iterate the registry — do not enumerate writers in the test.
4. Assert the failure message names the member and the missing field.

**Validation**: revert T005's change to any one writer and confirm the test goes red naming that
writer. Commit the red state first.

---

## Branch Strategy

- **Planning base**: `feat/doctrine-delivery-reachability`
- **Final merge target**: `feat/doctrine-delivery-reachability`
- Execution worktrees are allocated per computed lane from `lanes.json` after `finalize-tasks`. Do not
  create a worktree by hand; `spec-kitty implement WP01` resolves it.

## Test strategy

Named gate files only — **never the full architectural suite** in the WP loop:

```bash
PWHEADLESS=1 pytest \
  tests/doctrine/drg/test_model_strictness_roundtrip.py \
  tests/charter/synthesizer/test_project_drg.py \
  tests/doctrine/drg/migration/test_extractor_projection.py \
  tests/architectural/test_layer_rules.py \
  tests/architectural/test_runtime_charter_doctrine_boundary.py -q
```

Baseline on `ed470756e`: **57 passed** across these five files.

**Baseline-red discipline**: a broad run shows red that is not yours. Classify before fixing —
known-P0 reds on main, CI-environment failures, and stale-install false reds (`pip install -e .` after
touching anything that shells out to `spec-kitty`).

## Definition of Done

- [ ] Every registry member emits `set(model_fields) - withheld` for a **fully-populated** instance
- [ ] A field whose value is `None` or `[]` is handled by a **documented** rule, not dropped silently
- [ ] `project_drg` is derived and covered — mutating it now turns a test red
- [ ] `rewrite_opposed_by` is registered without a duplicate assertion
- [ ] `_dump_graph_document` derives its document keys
- [ ] The registry lives in `src/specify_cli/` and both layer gates stay green
- [ ] The mutation fixture is committed, subclass-based, and iterates the registry
- [ ] A red commit precedes each green commit in history (C-006)
- [ ] `ruff` and `mypy --strict` clean with **zero** new suppressions (NFR-002)

## Risks

| Risk | Mitigation |
|---|---|
| Asserting over a sparse instance makes the gate vacuous | T002 + fully-populated fixture in T007 |
| Hosting the registry in `doctrine` reds two layer gates | Host in `specify_cli`; T001 verifies |
| Import-time self-registration seems easier | Explicitly forbidden — order-dependent membership |
| Treating `rewrite_opposed_by` as unguarded and duplicating its test | It is guarded; register only |
| Regenerating graph fragments as a side effect | If T002's rule changes output, that is a ledger row, not a silent diff |

## Reviewer guidance

Verify by **mutation, not inspection**:

1. Delete one field from one registry member's output. The suite must go red **naming that member and
   that field**.
2. Add a novel `list[str] = []` field to the edge model in a scratch copy. Confirm it survives every
   member — this is the case that fails today.
3. Confirm the registry is iterated by the test, not enumerated in it.
4. Confirm `git log` shows a red commit before each green one.
5. Confirm no `# noqa` or `# type: ignore` was added.

**Do not accept** a claim that a writer is covered without seeing the mutation go red.
