---
work_package_id: WP05
title: DRG writer registry unify + discovery gate
dependencies: []
requirement_refs:
- FR-010
- NFR-006
planning_base_branch: feat/doctrine-delivery-activation
merge_target_branch: feat/doctrine-delivery-activation
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-activation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-activation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-delivery-activation-01KYQVQK
base_commit: 045584c6f9f5666d45e847589bb1904901c1a7e0
created_at: '2026-07-30T05:21:24.021675+00:00'
subtasks:
- T020
- T021
- T022
- T023
phase: Phase 3 - DRG writer registry hygiene (Lane C, parallel)
history:
- at: '2026-07-29T22:08:45Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/drg_writers/
create_intent:
- tests/architectural/test_drg_writer_discovery.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/migration/rewrite_opposed_by.py
- src/charter/synthesizer/project_drg.py
- src/specify_cli/doctrine/pack_assembler.py
- src/specify_cli/drg_writers/registry.py
- tests/specify_cli/drg_writers/test_registry_completeness.py
- tests/architectural/test_drg_writer_discovery.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – DRG writer registry unify + discovery gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work
package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or
  the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation
  TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you
  changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or
in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Route ALL THREE `src/` sites that serialize a whole `DRGGraph` document (the five top-level keys
  `schema_version`/`generated_at`/`generated_by`/`nodes`/`edges`) through the sole canonical serializer
  `graph_document_to_dict` (`src/doctrine/drg/migration/extractor.py:1424`).
- Register each converted site as a `DocumentWriter` member in `DOCUMENT_WRITERS`
  (`src/specify_cli/drg_writers/registry.py:171-176`, growing it from 1 to 4 members) so the existing
  member-iterating completeness test covers it with zero new hand-written membership logic.
- Author a NEW, non-vacuous discovery gate that scans `src/` for graph-document emitters in **both** shapes
  — (i) dict literals carrying `schema_version`+`nodes`+`edges`, and (ii) `DRGGraph`→dict via raw
  `.model_dump()` — and asserts each callsite delegates to the canonical serializer or is a registry member.
- Prove non-vacuity with a self-mutation **battery**: an injected unregistered dict-literal writer AND an
  injected unregistered `.model_dump()`-shaped writer must each red **independently**.
- **Scope boundary (important):** this WP closes contract sections C1+C2+C3 (`drg-writer-discovery-gate.md`)
  only — i.e. acceptance A1+A2. The Protocol-typing half (C4/A3, the 12 `# type: ignore[attr-defined]`
  removals) is **WP04's** job (IC-06b), sequenced after WP01+WP08 because it edits WP01's own
  `context.py`/`progressive_disclosure.py` hunks. Do not attempt C4 here.

## Context & Constraints

- Plan: [plan.md](../plan.md) IC-06a · Contract: [drg-writer-discovery-gate.md](../contracts/drg-writer-discovery-gate.md)
  (C1/C2/C3, A1/A2) · Ledger: [pre-planning-ledger.md](../pre-planning-ledger.md) Scout 2 "Item 1 — Writer-
  registry blind spot (#3075)" + POST-PLAN squad D12/R-B3 (IC-06 split) + D-M5/R-M5 (both-shape non-vacuity).
- **Canonical serializer** (`extractor.py:1424` `graph_document_to_dict`): derives the document's top-level
  keys from `DRGGraph.model_fields`, withholds `FIELDS_WITHHELD_FROM_GRAPH_OUTPUT` (`extractor.py:1319`, =
  `frozenset({"provenance"})`), and recurses `nodes`/`edges` through `model_to_graph_dict`
  (`extractor.py:1379`, itself field-derived and empty-value-aware via `_FIELDS_OMITTED_WHEN_EMPTY`). A
  top-level field added to `DRGGraph` later is emitted automatically — no writer needs editing.
- **MAPPING level is already unified** — do not touch it. `MAPPING_WRITERS` (`registry.py:153-169`) already
  has 3 members (`extractor`, `charter.synthesizer.project_drg`, `specify_cli.migration.rewrite_opposed_by`),
  all wrapping `model_to_graph_dict`, covered by the existing non-vacuous mutation battery in
  `tests/specify_cli/drg_writers/test_registry_completeness.py` (T004-T007 from the parent
  `doctrine-delivery-reachability` mission). This WP is scoped to the **DOCUMENT** level only.
- **DOCUMENT level is NOT unified** — `DOCUMENT_WRITERS` (`registry.py:171-176`) has exactly ONE member
  today: `_FunctionDocumentWriter(name="extractor._dump_graph_document", document_fn=graph_document_to_dict)`.
  Three sites hand-restate the 5 top-level keys instead of delegating:
  1. `src/specify_cli/migration/rewrite_opposed_by.py:_write_graph` (lines 368-380, #2977) — hand-builds
     `payload = {"schema_version": ..., "generated_at": ..., "generated_by": ..., "nodes": [...], "edges": [...]}`
     using its already-canonical `_node_to_dict`/`_edge_to_dict` helpers for the node/edge entries, but
     restates the 5 document-level keys itself.
  2. `src/charter/synthesizer/project_drg.py:_serialize_graph` (lines 86-104) — same shape.
  3. `src/specify_cli/doctrine/pack_assembler.py`, inside `_copy_drg_fragments` (def at line 443; the
     force-dedup fragment-pruning path at lines 495-501) — **the third, worse, unnamed site**: restates the
     5 keys AND bypasses the mapping funnel entirely via raw `n.model_dump()` / `e.model_dump()` (NOT
     `model_to_graph_dict`), so it also drops `FIELDS_WITHHELD_FROM_GRAPH_OUTPUT` (emits `provenance`, which
     the canonical path withholds) and the omit-when-empty rule.
- **Import conventions per site** (verified in this repo today, follow them — do not invent a new import
  style):
  - `rewrite_opposed_by.py` already has a static top-level `from charter.drg import (DRGEdge, DRGGraph,
    DRGNode, NodeKind, Relation, model_to_graph_dict)` (lines 97-104) — add `graph_document_to_dict` to
    that same block.
  - `project_drg.py` already has `from doctrine.drg.migration.extractor import model_to_graph_dict`
    (line 31, direct import — `charter` sits above `doctrine` so no facade indirection is needed here) —
    add `graph_document_to_dict` to that same import line.
  - `pack_assembler.py` has NO static top-level doctrine/charter import; `_copy_drg_fragments` imports
    `DRGLoadError`/`load_graph` **dynamically** inside a `try/except ModuleNotFoundError: pass` guard
    (lines 466-472) so the module degrades gracefully when the doctrine package is stripped from a test
    environment. Add `from doctrine.drg.migration.extractor import graph_document_to_dict` inside that same
    guarded block — do not introduce a hard top-level dependency this file doesn't already have.
- **Registry hosting layer constraint** (`registry.py:19-25` docstring): the registry lives in
  `src/specify_cli/` (the top layer) because a `Final` tuple naming both `charter.synthesizer.project_drg`
  and `specify_cli.migration.rewrite_opposed_by` cannot live in `doctrine` or `charter` without reversing an
  import-layer edge. Members are wired **explicitly** — no self-registration by design, so a writer that
  never joins the tuple is invisible to the completeness gate (exactly the blind spot this WP closes with a
  scanning gate instead of relying on the tuple alone).
- **C-007 closure gate**: #3075 and #2977 close **only if** this WP's C1+C2+C3 AND WP04's C4 (Protocol
  typing) both land. This WP alone must leave both tickets OPEN with a residual tracker note naming what
  remains (WP04's typing half) — do not write "Closes #3075" from this WP's PR.
- **NFR-006 non-vacuity (D-M5, binding)**: the self-mutation battery MUST inject an unregistered
  **dict-literal** writer AND an unregistered **`.model_dump()`-shaped** writer, each proven to red
  **independently**. A single dict-literal mutation leaves the `.model_dump()` shape — the exact shape that
  motivated this WP (`pack_assembler.py`) — unproven. Memory precedent: "gate-unmask can't self-validate" —
  prove the gate PARSES its authority (both shapes), not a literal-vs-literal echo.
- **Bounded claim (contract, explicit)**: the gate closes the KNOWN dict-literal + `.model_dump()` shapes
  and regressions of those shapes. Graph-document construction via `merge`/dict-comprehension/`**spread`
  remains uncovered — state this as a residual note in the final report, not a defect to chase in this WP.
- **File-path discrepancy — read before creating the discovery-gate file.** The plan's Project Structure,
  the contract, the pre-planning ledger, and `quickstart.md` all name the discovery-gate test
  `tests/architectural/test_drg_writer_discovery.py`. As of this grounding pass, **no file exists at that
  path.** The EXISTING per-member completeness gate (field-coverage mutation battery, T004-T007 from the
  parent mission, including the exact lines the contract cites: `test_registry_completeness.py:199-220`)
  lives at `tests/specify_cli/drg_writers/test_registry_completeness.py` (275 lines, confirmed present).
  Resolve as follows, do not silently pick one without recording the split:
  1. **Extend** the existing `tests/specify_cli/drg_writers/test_registry_completeness.py` for C1/C2 —
     once `DOCUMENT_WRITERS` grows from 1 to 4 members, its existing member-iterating tests
     (`test_every_document_writer_emits_every_graph_field` / `test_every_document_writer_preserves_a_novel_graph_field`,
     lines 199-220) automatically cover all 4 members with **zero new test code** — this is literally the
     contract's own claim ("the existing member-iterating completeness test covers it").
  2. **Create** a genuinely NEW file at `tests/architectural/test_drg_writer_discovery.py` for C3 (the
     discovery gate + both-shape self-mutation battery) — this is a distinct, whole-repo static-scan gate
     (same family as `test_no_dead_symbols.py` / `test_layer_rules.py`), architecturally appropriate for
     `tests/architectural/`, and matches the plan's literal Project Structure path and `quickstart.md`'s
     literal `uv run pytest tests/architectural/test_drg_writer_discovery.py -q` command.
  3. Both `tests/architectural/` and `tests/specify_cli/drg_writers/` carry `__init__.py`, so the shared
     basename across the two directories does NOT collide at pytest collection (verified). Give the new
     file's module docstring an explicit one-line pointer to the sibling file ("complements, does not
     replace, `tests/specify_cli/drg_writers/test_registry_completeness.py`'s per-member gate") so a future
     reader isn't confused by the shared basename.

## Branch Strategy

- **Strategy**: Planning artifacts generated on feat/doctrine-delivery-activation; during implement this WP
  may branch from a dependency-specific base but merges back into feat/doctrine-delivery-activation unless
  the human redirects.
- **Planning base branch**: feat/doctrine-delivery-activation
- **Merge target branch**: feat/doctrine-delivery-activation

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T020 – Route all 3 document-emit sites through `graph_document_to_dict`

- **Purpose**: Close contract C1 — kill the two "hand-restate the 5 keys" sites and the `pack_assembler`
  raw-`.model_dump()` site, so a top-level `DRGGraph` field added later can't drop silently at any of them.
- **Steps**:
  1. In `rewrite_opposed_by.py`, rewrite `_write_graph` (lines 368-380) to build `payload =
     graph_document_to_dict(graph)` and dump that via the existing `_make_yaml()`/`yaml_rt.dump(payload, fh)`
     call. Drop the hand-built dict. `_node_to_dict`/`_edge_to_dict` in this module stay (they're still
     registered `MAPPING_WRITERS` members used elsewhere) — only `_write_graph`'s own inline construction
     goes; `graph_document_to_dict` already recurses through `model_to_graph_dict` internally.
  2. In `project_drg.py`, rewrite `_serialize_graph` (lines 86-104) the same way: `payload =
     graph_document_to_dict(graph)`, keep the ruamel-YAML-dump-to-`io.StringIO()` wrapper unchanged.
  3. In `pack_assembler.py`'s `_copy_drg_fragments` (line 443), the `force`-dedup path already builds
     `kept_edges` (the pruned edge list, existing domain logic — keep it as-is). Replace the `pruned = {...}`
     dict literal (lines 495-501) with a call to `graph_document_to_dict` over a transient graph carrying
     the PRUNED edges — e.g. `graph_document_to_dict(graph.model_copy(update={"edges": kept_edges}))`
     (pydantic v2 `.model_copy()`) — rather than hand-restating the top-level keys around the smaller edge
     list. Remove the now-dead `n.model_dump()` / `e.model_dump()` calls entirely.
  4. Grep the three touched files afterward for any remaining `.model_dump()` or hand-typed
     `{"schema_version": ...}`-shaped literal outside the new call — there should be none.
- **Files**: `src/specify_cli/migration/rewrite_opposed_by.py`, `src/charter/synthesizer/project_drg.py`,
  `src/specify_cli/doctrine/pack_assembler.py`.
- **Parallel?**: Yes — file-disjoint from the core lane (WP01-WP04); genuinely parallel per the registry's
  own docstring.
- **Notes**: Contract acceptance A1 ("adding a hypothetical new top-level `DRGGraph` field, all three sites
  emit it, RED before C1") is naturally proven by T021's grown `DOCUMENT_WRITERS` tuple exercising the
  existing mutation fixture (`_GraphWithNovelField` pattern, see
  `tests/specify_cli/drg_writers/test_registry_completeness.py:102-103`) — land T020 and T021 in the same
  commit/PR; do not merge T020 alone with a red T021.

### Subtask T021 – Register all three sites as `DocumentWriter` members

- **Purpose**: Close contract C2 — the sites T020 fixed must be enumerable by the registry, not just
  individually correct.
- **Steps**:
  1. In `registry.py`, grow `DOCUMENT_WRITERS` (currently 1 member, lines 171-176) to 4 members using the
     existing `_FunctionDocumentWriter(name=..., document_fn=...)` adapter shape (same pattern as the
     existing `extractor._dump_graph_document` member). Follow the `MAPPING_WRITERS` naming convention
     already established (`"specify_cli.migration.rewrite_opposed_by"`, `"charter.synthesizer.project_drg"`)
     and add a fourth name for pack_assembler (`"specify_cli.doctrine.pack_assembler"`).
  2. Each `document_fn` needs an addressable, importable callable per module. If T020 inlined
     `graph_document_to_dict(graph)` directly inside `_write_graph`/`_serialize_graph`/
     `_copy_drg_fragments` rather than naming a standalone wrapper, extract a thin named wrapper per module
     (e.g. `def _document_dict(graph: DRGGraph) -> dict[str, Any]: return graph_document_to_dict(graph)`) so
     each registered member is independently attributable in a W-5 failure message, mirroring how
     `_node_to_dict`/`_edge_to_dict` are already separately addressable per module for `MAPPING_WRITERS`.
  3. Import each module's wrapper into `registry.py` following the existing pattern (`from specify_cli.migration
     import rewrite_opposed_by as _rewrite_opposed_by` at line 46 is the precedent) — add `from
     specify_cli.doctrine import pack_assembler as _pack_assembler`.
- **Files**: `src/specify_cli/drg_writers/registry.py`.
- **Parallel?**: With T020 (same PR, sequenced immediately after).
- **Notes**: Verify no import cycle before wiring `pack_assembler` into `registry.py` — `pack_assembler.py`
  currently imports only `.pack_validator`, `.snapshot`, `.sources.protocol` at module level plus the
  dynamic doctrine import inside `_copy_drg_fragments`; it does not import the registry back, so a static
  `registry.py -> pack_assembler` edge should be safe. Confirm this holds after T020's edits.

### Subtask T022 – Author the discovery gate (both shapes)

- **Purpose**: Close contract C3 — a NEW gate that scans `src/` directly (not just iterates the registry
  tuple) so a FUTURE fourth hand-restating site can't repeat the exact blind spot this WP fixes.
- **Steps**:
  1. Create `tests/architectural/test_drg_writer_discovery.py` (new file — see the file-path discrepancy
     note in Context & Constraints; state the sibling-file relationship in its module docstring).
  2. Implement an `ast`-based scan over `src/**/*.py` (`ast.parse` + `ast.walk` — this repo's established
     idiom for whole-repo static gates, see e.g. `tests/architectural/test_layer_rules.py`'s use of `ast` +
     `importlib.util`; read one existing architectural AST-scan test for the scan-and-report shape before
     inventing a new one) that flags two shapes:
     - **Shape (i)**: an `ast.Dict` literal whose string keys are a superset of `{"schema_version", "nodes",
       "edges"}`, appearing outside `graph_document_to_dict`'s own definition
       (`src/doctrine/drg/migration/extractor.py`) and outside a function whose body is a single delegating
       call to a registered `DocumentWriter`'s `document_fn`.
     - **Shape (ii)**: a call to `.model_dump()` (`ast.Attribute` with `attr == "model_dump"`) on a value
       inferable as a `DRGGraph`/`DRGNode`/`DRGEdge` instance (or a comprehension over `.nodes`/`.edges`)
       whose result later merges with `schema_version`/`nodes`/`edges` keys, outside the canonical helpers.
  3. For each flagged site, assert it is EITHER (a) a delegating call to `graph_document_to_dict` /
     `model_to_graph_dict`, OR (b) named as a `DOCUMENT_WRITERS`/`MAPPING_WRITERS` member's `document_fn` /
     `node_fn` / `edge_fn` (cross-reference the live registry by qualified name — import
     `specify_cli.drg_writers.registry` and check membership programmatically). Anything else fails the
     gate, naming the file:line + the offending shape (W-5-style failure message, matching this repo's
     existing registry-gate convention).
  4. Keep the gate's own allowlist minimal and explicit — do not hand-maintain a second "known writers" list
     that drifts from `registry.py`; cross-reference the registry's actual members programmatically instead.
- **Files**: `tests/architectural/test_drg_writer_discovery.py` (new).
- **Parallel?**: Yes.
- **Notes**: Scope shape-(i) matching tightly (all three keys present together, in a context that also
  supplies `nodes:`/`edges:` values) rather than any dict sharing three key-name substrings, to bound false
  positives — comment the scoping choice so a reviewer can audit precision vs. recall.

### Subtask T023 – Self-mutation battery (NFR-006 non-vacuity, both shapes independently)

- **Purpose**: Prove the T022 gate actually catches what it claims — a static gate that never reds against a
  real regression is a false-green machine (memory: "gate-unmask can't self-validate"; "no RecursionError ≠
  no cycle" is the same family of trap — absence of a failure is not proof of coverage).
- **Steps**:
  1. Add a test that materializes a TEMPORARY unregistered writer of **shape (i)** — a fixture `.py` source
     (e.g. written to `tmp_path` and pointed at via a parametrized `src_root` argument on the gate's scan
     function, NOT a literal edit to real `src/`) containing a dict literal with `schema_version`/`nodes`/
     `edges` keys that does NOT delegate to `graph_document_to_dict`. Run the scan function directly against
     that fixture path and assert it REDS.
  2. Add a SECOND, independent test with a **shape (ii)** fixture — a `.model_dump()`-based writer not
     delegating to the canonical helper. Run the SAME scan against it and assert it ALSO reds,
     **independently** of test 1. Per D-M5/C3: do not let one mutation stand in for both — a dict-literal-
     only mutation proves nothing about the `.model_dump()` shape, which is exactly the class of bug
     `pack_assembler.py` had.
  3. Add a THIRD test proving the gate is GREEN against the real (post-T020/T021) `src/` tree — run the
     actual gate over the actual `src/` directory and assert zero violations, so the two self-mutation tests
     aren't the only thing keeping the gate honest in CI.
  4. State the bounded claim explicitly in the WP's Activity Log / final report (contract wording): "closes
     the known dict-literal + `.model_dump()` shapes and regressions of them; graph-document construction
     via merge/comprehension/`**spread` remains uncovered — residual note."
- **Files**: `tests/architectural/test_drg_writer_discovery.py`.
- **Parallel?**: With T022 (same file, sequenced after the scan function exists).
- **Notes**: Keep the injected-fixture mutations OUT of real `src/` — inject via a parametrized scan-root or
  a `tmp_path`-written fixture file, never a literal (even temporary) edit to a real production module, so
  CI never has a moment where the actual codebase contains the deliberately-broken writer.

## Definition of Done

```bash
uv run pytest tests/specify_cli/drg_writers/test_registry_completeness.py -q
uv run pytest tests/architectural/test_drg_writer_discovery.py -q
uv run pytest tests/architectural/test_drg_writer_discovery.py -q -k "self_mutation or dict_literal or model_dump"
uv run ruff check src/specify_cli/migration/rewrite_opposed_by.py src/charter/synthesizer/project_drg.py src/specify_cli/doctrine/pack_assembler.py src/specify_cli/drg_writers/registry.py tests/architectural/test_drg_writer_discovery.py
uv run mypy --strict src/specify_cli/drg_writers/registry.py
```

Do NOT run the full `tests/architectural/` suite locally — targeted node-ids only (repo policy; CI owns the
full sweep).

## Risks & Mitigations

- The registry is fail-open by design (no self-registration) — the T022/T023 discovery gate is the ONLY
  thing preventing a future FOURTH hand-restating site; keep its allowlist minimal so it doesn't quietly
  grow into a second hand-maintained membership list.
- C-007 is all-or-nothing: do not close #3075/#2977 from this WP alone; leave a tracker comment naming what
  remains (WP04's Protocol typing half) if this WP lands first.
- `pack_assembler.py`'s layer-import direction: confirm no import cycle before wiring it into `registry.py`
  (T021 notes).
- File-path discrepancy between the plan's literal path and the pre-existing per-member gate's actual
  location — resolved above (extend one, create the other); flag this resolution explicitly to the reviewer
  so it isn't mistaken for an accidental duplicate.

## Reviewer Guidance

- Confirm A1: a hypothetical new top-level `DRGGraph` field is actually EMITTED by all three T020 sites
  (not merely registered) — exercise `tests/specify_cli/drg_writers/test_registry_completeness.py`'s
  `_GraphWithNovelField` mutation fixture against the grown `DOCUMENT_WRITERS` tuple.
- Confirm A2: the two self-mutation tests (T023) fail INDEPENDENTLY when only one shape's fixture is broken
  — as a sanity check, temporarily comment out one assertion locally and confirm the other still catches its
  own shape (not a permanent test change).
- Confirm the `pack_assembler.py` fix REMOVES the raw `.model_dump()` calls entirely rather than leaving
  them dead-but-present alongside the new canonical call.
- Confirm `tests/specify_cli/drg_writers/test_registry_completeness.py`'s existing tests (lines 199-220)
  pass UNMODIFIED with `DOCUMENT_WRITERS` grown to 4 members — the "no new test code needed there" claim is
  the point; if new test code WAS required in that file, that's a signal the registry wiring diverged from
  the established pattern.
- Confirm the PR does NOT say "Closes #3075" / "Closes #2977" unless WP04's Protocol-typing half already
  landed (C-007).

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If
entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-29T22:08:45Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP05 --to <status>` to
change WP status.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/` to keep bundles grouped while maintaining lexical
ordering.
