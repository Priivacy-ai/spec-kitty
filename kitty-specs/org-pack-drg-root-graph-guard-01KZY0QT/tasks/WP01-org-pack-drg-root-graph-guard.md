---
work_package_id: WP01
title: Org Pack DRG Root Graph Guard — guard + drg/ merge + malformed-content visibility
dependencies: []
requirement_refs:
- C-001
- C-002
- C-003
- C-004
- C-005
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-002
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
phase: Phase 1 - Full functional change (single WP)
assignee: ''
agent: "claude"
shell_pid: "381232"
history:
- at: '2026-08-13T21:17:50Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/charter/_drg_helpers.py
create_intent:
- tests/charter/test_org_root_graph_guard.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/_drg_helpers.py
- src/charter/action_doctrine_bundle.py
- tests/charter/test_org_root_graph_guard.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Org Pack DRG Root Graph Guard

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or
any user-defined profile), and behave according to its guidance before parsing the rest of this
prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for
this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via
  `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your
  implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining
  what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity
Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

Close GitHub issue #3384: an org doctrine pack whose only DRG content lives at
`<org_root>/drg/*.graph.yaml` — the **only** layout the shipped authoring guide
(`docs/guides/how-to/governance/create-an-org-doctrine-pack.md`) documents — currently zeroes
every action-scoped directive/tactic/styleguide/toolguide/procedure count the moment the pack
is declared, silently, with only a WARNING log line. This WP delivers the complete fix (all
three implementation concerns from plan.md, combined into one function's evolution) plus its
full regression-test coverage:

1. **FR-001/FR-002 (IC-01)**: guard the org-root load with a combined
   `has_graph_files`-style existence check across **both** `org_root` and `org_root/drg/`, and
   actually load `drg/*.graph.yaml` fragments when present. A pack with content in neither
   location degrades cleanly to `None` ("no org DRG layer"); a pack with content only in
   `drg/` (the guide-compliant shape) now actually contributes its edges.
2. **FR-003 (IC-02)**: when both a root-level graph and `drg/` fragments are present, merge
   them via `merge_layers(root_graph, drg_graph)` (root as `built_in`, `drg/` as `project` —
   `drg/` wins on same-URN node-label conflicts) and deduplicate any identically-repeated
   `(source, target, relation)` edge triple across the two sources to exactly one retained
   copy, using the existing canonical `doctrine.drg.validator.duplicate_edge_triples` primitive
   — never an independently-written comparison (C-001).
3. **FR-004 (IC-03)**: malformed org-layer content — whether the root-level graph or a `drg/`
   fragment, invalid YAML or schema-invalid — surfaces as a real, structurally distinguishable
   failure (a new `OrgDRGFragmentError`, deliberately not a `DRGLoadError` subclass, left
   **uncaught** all the way to the CLI's existing generic exception boundary) instead of being
   silently swallowed into an empty-but-reported-success bundle. Root-level and `drg/`-level
   loads are wrapped **independently**, so a malformed root graph no longer takes a valid,
   loadable sibling `drg/` fragment down with it.

**Success criteria** (all must hold at Definition of Done):

- All 9 tests in the new `tests/charter/test_org_root_graph_guard.py` pass, each having gone
  RED on `planning_base_branch` before its corresponding implementation commit and GREEN on the
  WP's final commit (charter C-011 / spec.md C-003).
- `pytest tests/charter/ tests/architectural/` passes (excluding any failure attributable to
  the pre-existing #3284 red baseline — see T001/T009).
- `mypy --strict src/charter/_drg_helpers.py src/charter/action_doctrine_bundle.py` is clean.
- `ruff check src/charter/_drg_helpers.py src/charter/action_doctrine_bundle.py
  tests/charter/test_org_root_graph_guard.py` is clean.
- `_drg_helpers.py`'s `__all__` remains `["load_validated_graph"]` — the three new symbols
  (`_load_org_layer`, `_dedup_org_layer_edges`, `OrgDRGFragmentError`) are deliberately **not**
  added (C-002/C-007).
- No change anywhere to `src/charter/kind_vocabulary.py`, `src/doctrine/drg/loader.py`'s public
  signatures, or `merge_layers()`'s implementation (C-001).

## Context & Constraints

- **Read first**: `.kittify/charter/charter.md` (binding governance; ATDD-first C-011, `__all__`
  convention C-007), `kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/spec.md` (all four User
  Stories, all FR/NFR/C rows), `kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/plan.md`
  (Implementation Concern Map IC-01/IC-02/IC-03, Test Strategy per Acceptance Criterion table,
  `__all__` Export Discipline table, Baseline section), and both
  `kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/reviews/spec.ruling.md` +
  `.../reviews/plan.ruling.md` (binding operator rulings — do not relitigate).
- **Blast radius (C-001, hard constraint)**: only `src/charter/_drg_helpers.py`,
  `src/charter/action_doctrine_bundle.py` (comment only), and
  `tests/charter/test_org_root_graph_guard.py` (new file). No change to
  `src/charter/kind_vocabulary.py` (that is issue #3385, an explicit non-goal — do not touch it
  even if you notice its related bug while working here), no change to
  `src/doctrine/drg/loader.py`'s public signatures, and **`merge_layers()`'s implementation is
  not modified** — its additive-only, no-removal semantics stay byte-for-byte unchanged. The
  root+`drg/` dedup is new logic local to `_drg_helpers.py`, operating on `merge_layers`'s
  *output*, not a change to `merge_layers` itself.
- **`--json` procedure-count carve-out (spec ruling SPEC-FRESH4-001, binding)**: `charter
  context --action <a> --json` exposes typed arrays for `directives`/`tactics`/`styleguides`/
  `toolguides` only — **never** a `procedures` array. Any test asserting a procedure count MUST
  do so against the **plain-text render** of the same action (`build_charter_context` /
  `result.text`, whose Procedures section lives in
  `src/charter/context_renderers/bootstrap_text.py`), never against the `--json` payload. Do
  not add a `procedures[]` array to the `--json` payload — that is issue #3389, out of scope
  here.
- **No further design broadening (plan ruling, binding)**: `OrgDRGFragmentError`'s scope is
  fixed at "malformed root-level graph OR malformed `drg/` fragment, org-branch only" — do not
  extend it to the project-layer `.kittify/doctrine` catch (that stays swallowed by the
  existing wide `except DRGLoadError`, unchanged, per spec.md's Non-Goals) and do not invent
  any further design change beyond what plan.md/its ruling already settled.
- **Current code** (`src/charter/_drg_helpers.py`, lines 83–97 today):
  ```python
  if org_root is None:
      org_root = _resolve_org_root(repo_root)

  built_in = load_built_in_graph()
  org = load_graph_or_dir(org_root) if org_root and org_root.exists() else None
  project_dir = repo_root / ".kittify" / "doctrine"
  project = (
      load_graph_or_dir(project_dir)
      if has_graph_files(project_dir)
      else None
  )

  merged = merge_layers(merge_layers(built_in, org), project)
  assert_valid(merged)
  return merged
  ```
  The `org = load_graph_or_dir(org_root) if org_root and org_root.exists() else None` line is
  the defect: it calls `load_graph_or_dir` unconditionally whenever `org_root.exists()`, with
  no check for whether `org_root` (or its `drg/` subdirectory) actually contains a loadable
  graph. `load_graph_or_dir` raises `DRGLoadError` on a directory with no root-level graph file
  and never even looks at `drg/` when no root graph is present but a `drg/` directory exists
  alongside it — the caller's wide `except DRGLoadError` in
  `_load_action_doctrine_bundle` (`src/charter/action_doctrine_bundle.py`, ~line 200) then
  collapses the **entire resolved action bundle to empty across all five doctrine kinds**
  (built-in + org + project layers together — not merely the org layer's contribution, because
  the exception aborts `load_validated_graph` before the project-layer load or final merge ever
  run), logging only a WARNING.
- **Existing primitives you compose, do not reimplement**:
  - `doctrine.drg.loader.has_graph_files(path: Path) -> bool` — true iff *path* is a directory
    containing `graph.yaml` or at least one `*.graph.yaml` fragment. Already imported in
    `_drg_helpers.py`.
  - `doctrine.drg.loader.load_graph_or_dir(path: Path) -> DRGGraph` — raises `DRGLoadError` on
    missing/malformed content. Already imported.
  - `doctrine.drg.loader.merge_layers(built_in: DRGGraph, project: DRGGraph | None) ->
    DRGGraph` — additive-only merge, override-wins-on-label-conflict semantics for its second
    argument. Already imported.
  - `doctrine.drg.loader.DRGLoadError` — the exception `load_graph_or_dir`/`load_graph` raise.
    Already imported.
  - `doctrine.drg.validator.duplicate_edge_triples(graph: DRGGraph) -> list[DRGEdge]` — returns
    the second-and-later occurrence of each repeated `(source, target, relation)` triple, in
    graph edge order. **Not yet imported in `_drg_helpers.py`** — you will add this import.

## Branch Strategy

- **Strategy**: single lane, single WP (see `tasks.md`'s "Why one WP" section — the plan phase
  already concluded this mission is right-sized for one PR / plausibly one WP).
- **Planning base branch**: `main` (per `meta.json`'s `target_branch`; this mission's spec/plan
  phases actually committed to the mission branch itself,
  `kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT`, under `lanes` topology — see
  `tracer-tooling-friction.md`'s SK-12 entry for the tooling caveat on this field).
- **Merge target branch**: `main`.

> These fields are populated automatically by `spec-kitty agent mission tasks`. Do NOT change
> them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T001 – Capture the pre-existing baseline red set (C-005)

- **Purpose**: Distinguish pre-existing red (issue #3284, ~23 known-red tests / 2 errors on
  `main`, plus #3283's shared pytest test-venv lock) from anything this WP introduces, per
  charter's Test Remediation standing order and plan.md's Baseline section. This must happen
  **before** the first functional-change (RED test) commit lands.
- **Steps**:
  1. On the current branch, **before** any of this WP's commits, run:
     `pytest tests/charter/ tests/architectural/ -q` (or with `-n auto --dist loadfile` if the
     environment supports parallel execution, per AGENTS.md's convention).
  2. Record the resulting red test IDs + failure summaries verbatim in this mission's
     `tracer-tooling-friction.md`, under its "Baseline-capture record" section — per plan.md's
     Baseline procedure step 5 ("committed to the mission's tracer notes"), not this WP's
     Activity Log — this is the baseline for *this mission's targeted surface* specifically,
     which may be a subset of #3284's full ~23.
  3. Do not attempt to fix any of these pre-existing failures.
- **Files**: none changed; this is an observation step.
- **Parallel?**: No — must run before T002.
- **Notes**: If a #3283-style test-venv lock timeout occurs, that is a CI-environment failure
  (AGENTS.md's baseline-red-gotcha category 2), not attributable to this WP — note it and do
  not retry into a stale-install false green.

### Subtask T002 – [RED] Commit failing ATDD tests for IC-01 (FR-001, FR-002, FR-005; User Stories 1 & 2)

- **Purpose**: Pin the guard/load behavior *before* implementing it, per charter C-011 / spec.md
  C-003. This commit must be RED against the code as it exists today (the unconditional
  `load_graph_or_dir(org_root) if org_root and org_root.exists() else None` line).
- **Steps**:
  1. Create `tests/charter/test_org_root_graph_guard.py` following the inline-fixture
     convention already used in `tests/charter/test_merged_graph_on_live_path.py` (patch
     `charter._drg_helpers.load_built_in_graph` to inject a fixture built-in graph) and
     `tests/charter/test_context_org_governance.py` (declare an org pack via
     `.kittify/config.yaml`'s `doctrine.org.packs` list, resolved through
     `charter.org_pack_discovery._enumerate_org_pack_paths` /
     `charter.drg.resolve_org_roots`). Do **not** create a `tests/charter/fixtures/` directory
     of committed fixture files — build fixtures inline with `tmp_path`, matching both sibling
     files' convention (plan.md's Project Structure section is explicit about this).
  2. Add module docstring crediting this mission (`org-pack-drg-root-graph-guard-01KZY0QT`,
     #3384) and `pytestmark = pytest.mark.fast`.
  3. Write `test_drg_only_pack_preserves_or_grows_typed_counts` (US1 AC1; FR-001/002/005;
     SC-001):
     - Fixture: a `tmp_path` repo whose declared org pack root has **only**
       `drg/fixture.graph.yaml` (no root `graph.yaml`/`*.graph.yaml`). The fragment should
       declare at least one `tactic`-kind node reachable from the resolved action (reuse this
       fixture for T002's second test too, to avoid duplicated fixture-building — see below).
     - Compute the **no-pack baseline** in the same test: invoke `charter context --action <a>
       --json` (via the `charter_app` Typer CLI, `typer.testing.CliRunner`, with
       `monkeypatch.setattr(charter_pkg, "find_repo_root", lambda: repo_root)` — mirror
       `tests/charter/test_context_include.py`'s `TestJsonEntryPoint` pattern) with **no** org
       pack declared, and record its `directives`/`tactics`/`styleguides`/`toolguides` typed-ID
       list lengths.
     - Then invoke the same command **with** the pack declared and assert each of the four
       typed counts is `>=` the dynamically-computed no-pack baseline — never a hardcoded
       magic number (this is the non-vacuous floor C-004 requires).
     - Separately, using the **plain-text render** of the same action (no `--json`), assert the
       Procedures section's count is likewise `>=` the plain-text no-pack baseline (per the
       spec ruling's binding `--json`/plain-text split — do not attempt to read a procedure
       count out of the `--json` payload).
     - Pick a real action + mission type combination that resolves a non-trivial action grain
       — `--mission-type software-dev --action implement` is a safe default (matches the CLI's
       own `--mission-type` option and this repo's dominant mission type).
  4. Write `test_drg_fragment_node_reaches_resolved_bundle` (US1 AC2; FR-002; SC-002):
     - Reuse T002.3's fixture pack. Assert the fixture's specific `drg/`-declared tactic-kind
       artifact ID is a **member of** the `--json` payload's `tactics` typed ID list (positive
       membership — not "no error", not "list is non-empty").
  5. Write `test_empty_org_pack_degrades_to_no_pack_baseline` (US2 AC1+AC2; FR-001; SC-003):
     - Fixture: a `tmp_path` repo whose declared org pack root directory **exists** but has no
       `graph.yaml`/`*.graph.yaml` anywhere — neither at the root nor under `drg/` — cover
       **both** the no-`drg/`-directory-at-all case and the empty-`drg/`-directory case (two
       assertions, or two parametrized sub-cases, in this one test function).
     - Assert the with-pack run's typed counts are `==` (not merely `>=`) the no-pack baseline
       across all four `--json` kinds, **and** the plain-text-render procedure count is `==`
       the no-pack plain-text baseline. No exception raised.
  6. Run `pytest tests/charter/test_org_root_graph_guard.py -v` and confirm all three tests
     fail (RED) — for the *right* reason: the with-pack counts should show `0`/collapsed
     (today's bug), not an unrelated collection error or fixture-setup crash. If a test errors
     instead of failing on the assertion, fix the fixture, not the assertion.
  7. Commit with a `test:` type message (per `commitlint.config.cjs`'s `type-enum`) — this is
     the WP's first commit.
- **Files**: `tests/charter/test_org_root_graph_guard.py` (new).
- **Parallel?**: No — depends on T001 having run first (baseline capture), and must precede T003.
- **Notes**: **Reverted-code check** (what "RED for the right reason" means here): if you
  imagine `_load_org_layer` were reverted to today's unconditional
  `load_graph_or_dir(org_root) if org_root and org_root.exists() else None`, the drg/-only
  pack's load raises `DRGLoadError` → the wide catch collapses the whole bundle to empty → all
  four typed counts drop to `0`, which is `<` the no-pack baseline → the `>=` assertion in
  `test_drg_only_pack_preserves_or_grows_typed_counts` fails → RED. Confirm this is the actual
  failure mode you observe, not a fixture-construction error.

### Subtask T003 – [GREEN] Implement IC-01: combined existence-guard in `_load_org_layer()`

- **Purpose**: Make T002's three tests pass by replacing the unconditional org-root load with a
  guarded, `drg/`-aware helper.
- **Steps**:
  1. In `src/charter/_drg_helpers.py`, add a new module-private function:
     ```python
     def _load_org_layer(org_root: Path) -> DRGGraph | None:
         """Load org-pack DRG content from *org_root* and/or *org_root*/drg/.

         Returns ``None`` when neither location has a recognisable graph file
         (the "no org DRG layer" case). Guards the FR-001 P0 zeroing: today's
         unconditional ``load_graph_or_dir(org_root)`` raises ``DRGLoadError``
         on a directory with no root-level graph, even when a guide-compliant
         ``drg/*.graph.yaml`` fragment sits alongside it.
         """
     ```
  2. Inside it, compute `has_root_graph = has_graph_files(org_root)` and
     `drg_dir = org_root / "drg"`, `has_drg_layer = has_graph_files(drg_dir)`.
  3. If neither is true, `return None`.
  4. If only `has_root_graph` is true, `return load_graph_or_dir(org_root)`.
  5. If only `has_drg_layer` is true, `return load_graph_or_dir(drg_dir)`.
  6. If both are true, this is IC-02's territory (T005) — for T003, a minimal correct
     implementation may `return merge_layers(load_graph_or_dir(org_root),
     load_graph_or_dir(drg_dir))` as a placeholder (T005 replaces this call with the dedup-aware
     version); do not skip the both-present branch entirely, since `has_root_graph and
     has_drg_layer` is a real case T002's tests do not exercise but T004's will.
  7. In `load_validated_graph`, replace the line:
     `org = load_graph_or_dir(org_root) if org_root and org_root.exists() else None`
     with:
     `org = _load_org_layer(org_root) if org_root and org_root.exists() else None`
     — the outer `org_root and org_root.exists()` guard is unchanged (preserves the existing,
     out-of-scope "org_root itself does not exist" edge case from spec.md).
  8. Run `pytest tests/charter/test_org_root_graph_guard.py -v` and confirm T002's three tests
     now pass (GREEN).
  9. Run `pytest tests/charter/ tests/architectural/ -q` and confirm no new red beyond T001's
     captured baseline.
  10. Commit with a `fix:` type message. This closes the RED→GREEN pair for T002.
- **Files**: `src/charter/_drg_helpers.py`.
- **Parallel?**: No — depends on T002.
- **Notes**: Do **not** wrap either `load_graph_or_dir` call in exception handling yet — that is
  IC-03's job (T007), landing after IC-02 (T005). If `has_root_graph` is true but the root graph
  is malformed, `load_graph_or_dir(org_root)` still raises a plain `DRGLoadError` at this point
  in the sequence, which propagates up to the existing wide catch in
  `_load_action_doctrine_bundle` exactly as it did before this WP — this is the *correct*,
  unremediated interim state per plan.md's IC-01 Risks note. Do not "fix" this early; T007 owns
  it.

### Subtask T004 – [RED] Commit failing ATDD tests for IC-02 (FR-003, FR-006; User Story 4)

- **Purpose**: Pin the root+`drg/` merge and identical-edge-triple dedup behavior before
  implementing the dedup step.
- **Steps**:
  1. Append to `tests/charter/test_org_root_graph_guard.py`:
  2. Write `test_root_and_drg_both_present_neither_node_dropped` (US4 AC1; FR-003/FR-006a;
     SC-005):
     - Fixture: a `tmp_path` repo whose org pack root has **both** a root-level `graph.yaml`
       declaring a `tactic`-kind node A and `drg/fixture.graph.yaml` declaring a
       `directive`-kind node B — distinct URNs, no overlap.
     - Assert A's artifact ID is a member of the `--json` payload's `tactics` typed ID list
       **and** B's artifact ID is a member of the `--json` payload's `directives` typed ID list
       — two independent positive-membership assertions (guards the vacuity-by-empty-set
       hazard: "no exception while iterating a possibly-empty discovered set" would pass
       vacuously and prove nothing).
  3. Write `test_identical_edge_triple_deduped_to_one_not_dropped` (US4 AC2; FR-003/FR-006b;
     SC-006):
     - Fixture: root `graph.yaml` and `drg/fixture.graph.yaml` both declare the **exact same**
       `(source, target, relation)` edge triple (reuse two nodes both files declare, or declare
       the same node in both and the same edge referencing it).
     - Call `_load_org_layer` (or `load_validated_graph`) **directly** — not the `--json` CLI —
       since the `--json` payload does not expose raw edge triples (per the spec's own
       methodology note).
     - Assert **both**: (a) no `DRGValidationError` is raised by the eventual `assert_valid`
       call inside `load_validated_graph`, **and** (b) the resolved `DRGGraph.edges` filtered to
       that exact `(source, target, relation)` triple has length **exactly 1** — not merely "no
       exception" (C-004's vacuity guard).
  4. Run `pytest tests/charter/test_org_root_graph_guard.py -v` and confirm both new tests fail
     (RED): the first because T003's minimal both-present branch does exist and should actually
     pass already if implemented per T003 step 6 — if it unexpectedly passes, check whether
     T003's placeholder already satisfies FR-003's *node*-presence half; that is fine and
     expected (T003's `merge_layers` call already merges both node sets). The **dedup** test
     (`test_identical_edge_triple_deduped_to_one_not_dropped`) MUST fail at this point: without
     dedup, `assert_valid` raises `DRGValidationError` on the duplicated triple.
  5. Commit with a `test:` type message.
- **Files**: `tests/charter/test_org_root_graph_guard.py`.
- **Parallel?**: No — depends on T003; must precede T005.
- **Notes**: **Reverted-code check** for the dedup test: without T005's dedup step, the
  org-internal root+`drg/` sub-merge carries both copies of the identical triple through to the
  final `assert_valid` → `DRGValidationError` raises → the "no raise" assertion fails → RED.

### Subtask T005 – [GREEN] Implement IC-02: root+`drg/` merge with dedup

- **Purpose**: Make T004's dedup test pass (and formalize the both-present merge T003 stubbed).
- **Steps**:
  1. In `src/charter/_drg_helpers.py`, add the import:
     `from doctrine.drg.validator import duplicate_edge_triples` (alongside the existing
     `from doctrine.drg.validator import assert_valid`).
  2. Add a new module-private helper:
     ```python
     def _dedup_org_layer_edges(graph: DRGGraph) -> DRGGraph:
         """Collapse identically-repeated (source, target, relation) triples to one.

         Scoped strictly to the org-internal root+drg/ sub-merge (FR-003) — a
         duplicate between the org layer and the built-in/project layers is a
         different scope and continues to raise at the final assert_valid.
         Reuses the canonical duplicate_edge_triples() definition of
         "duplicate" (C-001) rather than reimplementing the comparison.
         """
     ```
     Implementation: call `duplicate_edge_triples(graph)` to get the list of repeat-occurrence
     edge objects to drop; filter by **identity**, unambiguously — build
     `dup_ids = {id(e) for e in duplicate_edge_triples(graph)}`, then keep
     `deduped_edges = [e for e in graph.edges if id(e) not in dup_ids]`. Do **not** filter with
     `e not in duplicate_edge_triples(graph)` (value/triple-equality, via `in`/`==`): `DRGEdge`
     has no custom `__eq__`, so when `when`/`reason`/`provenance` are unset the first and second
     occurrence of an identical triple are pydantic-value-equal to each other, and a
     value-equality filter drops *both* copies — leaving zero retained edges instead of the
     required exactly one (T004's `test_identical_edge_triple_deduped_to_one_not_dropped`
     asserts length == 1). Return a new `DRGGraph` via
     `graph.model_copy(update={"edges": deduped_edges})`.
  3. In `_load_org_layer`'s both-present branch (T003 step 6's placeholder), replace the plain
     `merge_layers(...)` call with:
     ```python
     merged_org = merge_layers(root_graph, drg_graph)
     return _dedup_org_layer_edges(merged_org)
     ```
     where `root_graph = load_graph_or_dir(org_root)` and `drg_graph =
     load_graph_or_dir(drg_dir)` — keep these as separate local variables (T007/IC-03 will wrap
     each independently).
  4. Run `pytest tests/charter/test_org_root_graph_guard.py -v` and confirm T004's two tests now
     pass.
  5. Run `pytest tests/charter/ tests/architectural/ -q` and confirm no new red beyond baseline.
  6. Commit with a `fix:` type message.
- **Files**: `src/charter/_drg_helpers.py`.
- **Parallel?**: No — depends on T004.
- **Notes**: Do not widen `_dedup_org_layer_edges` to touch edges outside the org-internal
  root+`drg/` sub-merge result — it must only ever be called on that intermediate `DRGGraph`,
  never on the final `merge_layers(built_in, org)` result. A duplicate between the org layer and
  built-in/project layers is out of FR-003's scope and must continue to raise normally.

### Subtask T006 – [RED] Commit failing ATDD tests for IC-03 (FR-004; User Story 3 + root-level broadening)

- **Purpose**: Pin the malformed-content-visibility behavior — for both the `drg/`-fragment
  case (User Story 3's literal text) and the root-level-graph case (the plan ruling's
  defect-class-closure broadening, IC-03's sole ownership per plan.md) — before implementing the
  exception wrap. **Four** distinct tests, matching plan.md's Test Strategy table exactly.
- **Steps**:
  1. Append to `tests/charter/test_org_root_graph_guard.py`.
  2. Write `test_malformed_yaml_drg_fragment_raises_distinguishable_failure` (US3 AC1; FR-004;
     SC-007):
     - Fixture: org pack root has no root graph; `drg/broken.graph.yaml` contains invalid YAML
       syntax (e.g. unbalanced brackets or a tab character where YAML forbids it).
     - Invoke the `charter context --action <a> --json` **CLI entry point** (via `CliRunner`,
       not by calling `_load_org_layer`/`load_validated_graph` directly — this is the load-
       bearing FR-004/SC-007 verification plan.md names explicitly).
     - Assert the JSON output has `result != "success"` **and** a non-empty `error` field — a
       shape User Story 2's genuinely-empty case never produces (that case reports
       `"result": "success"`).
  3. Write `test_schema_invalid_drg_fragment_raises_same_distinguishable_shape` (US3 AC2;
     FR-004; SC-007):
     - Fixture: `drg/broken.graph.yaml` is valid YAML but violates `DRGGraph`'s schema (e.g. a
       stray top-level key, or a node missing a required field like `urn` or `kind`).
     - Same assertion shape as T006.2 — proves the failure signal is identical regardless of
       parse-error vs. schema-violation cause.
  4. Write `test_malformed_root_graph_with_valid_drg_sibling_raises_distinguishable_failure`
     (FR-001/FR-004; the plan ruling's defect-class-closure rationale):
     - Fixture: root `graph.yaml` is malformed (invalid YAML **or** schema-invalid — pick one;
       either is a valid instance) **and** `drg/fixture.graph.yaml` alongside it is valid and
       declares a loadable, reachable node.
     - Same assertion shape (`result != "success"`, non-empty `error`) — a valid `drg/` fragment
       sitting next to a malformed root graph must not be silently taken down with it.
  5. Write `test_malformed_root_graph_no_drg_directory_raises_distinguishable_failure`
     (FR-001/FR-004; **the load-bearing test per PLAN-FRESH2-003** — do NOT collapse this into
     T006.4's test):
     - Fixture: root `graph.yaml` is malformed; **no** `drg/` directory exists at all (not even
       an empty one) — the org pack's *only* content is the malformed root graph.
     - Same assertion shape. This is deliberately its **own separate test function**, distinct
       from T006.4: its fixture has no `drg/` content whatsoever, so it is the only test that
       goes RED against a conforming-but-incomplete implementation that only fires the
       root-level wrap when `drg/` also happens to exist alongside it.
  6. Run `pytest tests/charter/test_org_root_graph_guard.py -v` and confirm all four new tests
     fail (RED): today, all four malformed-content cases are caught by the existing wide
     `except DRGLoadError` and reported as `"result": "success"` with a zeroed bundle — the
     `result != "success"` assertion fails for each.
  7. Commit with a `test:` type message.
- **Files**: `tests/charter/test_org_root_graph_guard.py`.
- **Parallel?**: No — depends on T005; must precede T007.
- **Notes**: This is the subtask charter C-003 names explicitly as needing FR-004 coverage for
  "a malformed `drg/` fragment" — and the plan ruling's binding broadening extends the same
  distinguishable-failure requirement to the root-level-graph case, closing PLAN-ARCH-001's
  confirmed gap. Keep T006.4 and T006.5 as two distinct test functions; this is a binding
  instruction (see the mission's tasks-phase brief and PLAN-FRESH2-003) — do not merge them into
  one parametrized test that only checks the combined case.

### Subtask T007 – [GREEN] Implement IC-03: `OrgDRGFragmentError` + independent wraps

- **Purpose**: Make T006's four tests pass by wrapping both the root-level and `drg/`-level
  loads independently in a new, deliberately-uncaught exception type.
- **Steps**:
  1. In `src/charter/_drg_helpers.py`, add a new exception class (module-level, near the top of
     the file, after the imports):
     ```python
     class OrgDRGFragmentError(Exception):
         """Raised when org-layer DRG content (root graph or drg/ fragment) is
         malformed. Deliberately NOT a DRGLoadError subclass, so it is left
         uncaught by the existing wide `except DRGLoadError` in
         _load_action_doctrine_bundle and propagates to the CLI's generic
         exception boundary (charter context's `except Exception`), which
         already reports it as a structurally distinguishable failure.
         """
     ```
  2. In `_load_org_layer`, wrap the root-level load:
     ```python
     if has_root_graph:
         try:
             root_graph = load_graph_or_dir(org_root)
         except DRGLoadError as exc:
             raise OrgDRGFragmentError(
                 f"Malformed org DRG root graph at {org_root}: {exc}"
             ) from exc
     ```
     and, independently, the `drg/`-level load:
     ```python
     if has_drg_layer:
         try:
             drg_graph = load_graph_or_dir(drg_dir)
         except DRGLoadError as exc:
             raise OrgDRGFragmentError(
                 f"Malformed org DRG drg/ fragment at {drg_dir}: {exc}"
             ) from exc
     ```
     Each load must be attempted and wrapped **independently of the other's outcome** — do not
     put both loads inside one shared `try` block, or a malformed root graph will still take a
     valid, loadable `drg/` fragment down with it (the exact bug T006.4/T006.5 pin against).
  3. Add the `from doctrine.drg.loader import DRGLoadError` import (or extend the existing
     `from doctrine.drg.loader import (...)` import block) if not already present.
  4. Verify `_drg_helpers.py`'s `__all__` is still exactly `["load_validated_graph"]` — do
     **not** add `_load_org_layer`, `_dedup_org_layer_edges`, or `OrgDRGFragmentError` to it
     (C-002/C-007; `OrgDRGFragmentError` is intentionally left off despite not being
     underscore-prefixed, since it is designed to propagate uncaught with no `src/`-internal
     caller ever needing to import and catch it by name — see plan.md's `__all__` Export
     Discipline table for the full rationale).
  5. Run `pytest tests/charter/test_org_root_graph_guard.py -v` and confirm T006's four tests
     now pass.
  6. Run `mypy --strict src/charter/_drg_helpers.py` and confirm the new exception class and
     both helper functions are fully typed (no missed `Optional`, no untyped `except` binding).
  7. Run `pytest tests/charter/ tests/architectural/ -q` and confirm no new red beyond baseline
     — in particular, `tests/architectural/test_no_dead_symbols.py` must still pass (proves the
     `__all__` decision in step 4 is consistent).
  8. Commit with a `fix:` type message.
- **Files**: `src/charter/_drg_helpers.py`.
- **Parallel?**: No — depends on T006.
- **Notes**: Double-check that `OrgDRGFragmentError` is raised **only** inside `_load_org_layer`
  — never anywhere in the project-layer (`.kittify/doctrine`) load path elsewhere in
  `load_validated_graph`. The Non-Goals in spec.md are explicit: project-layer malformed-content
  visibility is unchanged and out of scope. The narrowing is achieved entirely by the new type
  simply not matching the existing `except DRGLoadError` clause in `action_doctrine_bundle.py`
  — you do not need to (and must not) edit that except-clause's code.

### Subtask T008 – Update `action_doctrine_bundle.py`'s comment (doc-only, no functional change)

- **Purpose**: Document that the existing wide `except DRGLoadError` in
  `_load_action_doctrine_bundle` now only fires for project-layer malformed content — malformed
  org-layer content of either shape (root or `drg/`) is IC-03's new, deliberately-uncaught
  `OrgDRGFragmentError` and no longer reaches this catch.
- **Steps**:
  1. Open `src/charter/action_doctrine_bundle.py`. Locate the comment block immediately above
     the `try:`/`except DRGLoadError as exc:` sequence inside `_load_action_doctrine_bundle`
     (currently reads: `# The DRG load honours the built-in + org + project three-layer overlay
     ... A project authoring a doctrine artifact without a sibling *.graph.yaml raises
     DRGLoadError; that is orthogonal to charter-level selection rendering, so we collapse it to
     an empty bundle and log a WARNING (WP04).`).
  2. Extend or rewrite the comment to state plainly: this catch continues to fire for
     project-layer (`.kittify/doctrine`) malformed content, unchanged; it no longer fires for
     org-layer malformed content (root graph or `drg/` fragment) — that now raises the new,
     module-private `OrgDRGFragmentError` from `_load_org_layer`, which is **not** a
     `DRGLoadError` subclass and propagates uncaught to the CLI's generic exception boundary
     (see `_drg_helpers.py`).
  3. Make **no** code change in this file — only the comment text changes. Do not touch the
     `try`/`except` block itself, the function signature, or any other line.
  4. Run `ruff check src/charter/action_doctrine_bundle.py` to confirm the comment-only edit
     introduces no lint issue (e.g. line-length).
  5. Commit with a `docs:` type message.
- **Files**: `src/charter/action_doctrine_bundle.py`.
- **Parallel?**: No — logically follows T007 (references `OrgDRGFragmentError` by name), though
  it has no test dependency.
- **Notes**: This is intentionally the only touch to this file. Do not use this as an
  opportunity for any other cleanup in this module — locality of change (`DIRECTIVE_024`)
  applies; this WP's file set is fixed by C-001.

### Subtask T009 – Full targeted gate set + baseline-red diff

- **Purpose**: Prove the complete WP is green against every gate plan.md names, and confirm no
  newly-introduced red beyond T001's captured baseline.
- **Steps**:
  1. `mypy --strict src/charter/_drg_helpers.py src/charter/action_doctrine_bundle.py` — must
     be clean.
  2. `ruff check src/charter/_drg_helpers.py src/charter/action_doctrine_bundle.py
     tests/charter/test_org_root_graph_guard.py` — must be clean.
  3. `pytest tests/charter/ tests/architectural/ -q` (or with `-n auto --dist loadfile`) — run
     the full targeted surface, not a hand-picked subset (NFR-002). Explicitly confirm, by name:
     - `tests/architectural/test_no_dead_symbols.py` passes (C-002/C-007 `__all__` convention).
     - `tests/architectural/test_no_legacy_terminology.py` passes (AGENTS.md's pre-push
       instruction, since this touches `src/charter/` prose).
     - `tests/architectural/test_layer_rules.py` passes (confirms no new `specify_cli` import
       leaked into `src/charter/`).
  4. Diff the resulting red-test-ID set against T001's captured baseline. Only newly-red tests
     (red now, green in the T001 baseline) are this WP's to fix. Any test red in both should be
     reported as pre-existing (#3284), not folded into this WP's scope.
  5. Confirm the CLI JSON error-surface exercise (FR-004/SC-007) is proven by T006's four tests
     already invoking the `charter context --action <a> --json` Typer entry point end-to-end —
     no separate CI step needed; this is the load-bearing verification named in plan.md's Gate
     Set item 5.
  6. Record the final gate results in the Activity Log below.
- **Files**: none changed (verification-only subtask).
- **Parallel?**: No — depends on T001, T003, T005, T007, T008 all having landed.
- **Notes**: This is the Definition-of-Done gate. Do not move the WP to `for_review` without
  this subtask's results recorded.

## Test Strategy

All nine tests live in the single new file `tests/charter/test_org_root_graph_guard.py`.
Assertion shapes, fixture shapes, and reverted-code checks for each test are specified
per-subtask above (T002/T004/T006) and mirror plan.md's "Test Strategy per Acceptance
Criterion" table exactly — consult that table if any ambiguity remains about an assertion's
exact form. Every assertion is a positive membership/exact-count/exact-inequality check against
a concrete, non-zero or dynamically-computed floor — never "no exception was raised" alone
(Standing Order #5 / C-004's vacuity guard, stated explicitly in plan.md).

Run commands:
```bash
pytest tests/charter/test_org_root_graph_guard.py -v
pytest tests/charter/ tests/architectural/ -q
mypy --strict src/charter/_drg_helpers.py src/charter/action_doctrine_bundle.py
ruff check src/charter/_drg_helpers.py src/charter/action_doctrine_bundle.py tests/charter/test_org_root_graph_guard.py
```

## Risks & Mitigations

See "Risks & Mitigations" in `tasks.md`'s WP01 section — repeated here for convenience:

- Conforming-but-incomplete root-level wrap (fires only when `drg/` also exists) → mitigated by
  T006.5's standalone test.
- Independently-reimplemented triple comparison in the dedup step → mitigated by T005's
  explicit instruction to import and call `duplicate_edge_triples`.
- `OrgDRGFragmentError` accidentally added to `__all__` → mitigated by T007 step 4's explicit
  check and T009's `test_no_dead_symbols.py` run.
- Rollout risk for pre-existing downstream root+`drg/` packs with previously-dormant malformed
  content (plan.md's "Mid-flight rollout note") — not a code-level risk to mitigate in this WP;
  state this plainly in the mission's PR description at close, mirroring the #3385 disclosure.

## Review Guidance

- Verify the RED→GREEN sequencing is real: check out `planning_base_branch`, apply only the
  test commits (T002, T004, T006) without their paired implementation commits, and confirm each
  test set fails for the assertion reason documented in this prompt's "Reverted-code check"
  notes — not a collection/import error.
- Confirm `merge_layers()` (`src/doctrine/drg/loader.py`) has zero diff — this is a hard
  constraint (C-001).
- Confirm `src/charter/kind_vocabulary.py` has zero diff.
- Confirm the dedup step (T005) imports `duplicate_edge_triples` rather than writing its own
  `(source, target, relation)` tuple comparison.
- Confirm all nine tests use dynamically-computed baselines / positive-membership assertions,
  never a hardcoded magic number or a bare "no exception raised" check.
- Confirm T006.4 and T006.5 remain two separate test functions.
- Confirm `_drg_helpers.py`'s `__all__` is unchanged (`["load_validated_graph"]`).
- Confirm `action_doctrine_bundle.py`'s diff is comment-only (no functional-code line changed).
- Confirm NFR-001 (byte-for-byte-unaffected output when no org pack is declared): the
  `org_root is None`/`not org_root.exists()` branch of `load_validated_graph`'s ternary is
  byte-identical to `planning_base_branch` — the diff should only touch the `if` side of the
  ternary (`load_graph_or_dir(org_root)` → `_load_org_layer(org_root)`), never the surrounding
  condition or the `else: None` fallback.

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

**Why this matters**: The acceptance system reads the LAST activity log entry as the current
state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-08-13T21:17:50Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use
`spec-kitty agent tasks move-task WP01 --to <status>` to change WP status.
- 2026-08-13T22:31:21Z – claude – shell_pid=381232 – Assigned agent via action command
