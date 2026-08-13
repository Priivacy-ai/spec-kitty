# Mission Specification: Org Pack DRG Root Graph Guard

**Mission Branch**: `kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT`
**Created**: 2026-08-13
**Status**: Draft
**Input**: GitHub issue [#3384](https://github.com/Priivacy-ai/spec-kitty/issues/3384) —
"Org pack without a root-level `*.graph.yaml` silently zeroes ALL action-scoped doctrine
for every mission"

## Clarifications

### Session 2026-08-13 (operator, pre-specify)

- Q: Fix shape for #3384 — guard the org branch, scan `drg/`, or both? → A: Both. Add the
  `has_graph_files`-style guard at `_drg_helpers.py:87` (so a pack with no loadable graph
  at its root, and nothing under `drg/`, degrades to "no org DRG layer" instead of
  raising) **and** make the org branch look for graph content at `<org_root>/drg/`
  (mirroring how the guide documents fragments) in addition to `<org_root>` itself.
  Consequence: the P0 (total zeroing) is closed AND the documented pack layout actually
  contributes its DRG edges — matches what the guide tells authors to build. This is the
  only option that makes a guide-compliant pack fully functional: the guide-compliant
  shape is `drg/`-only, so guard-alone would leave every correctly-authored pack's own DRG
  edges permanently unloaded (a smaller, still-silent residual drop).
- Q: Does this mission also fix #3385, given the issue text says the two "compound"? → A:
  No — #3384 only; leave #3385 as a separate mission. This mission ships the graph-load
  guard/scan above, with its own regression test, and closes only #3384. The PR touches
  `src/charter/_drg_helpers.py` / `action_doctrine_bundle.py` and its tests; nothing in
  `kind_vocabulary.py`. Consequence: smaller, reviewable, one-issue-one-mission diff,
  consistent with the one-PR-per-mission default; but "declare an org pack, then run
  `charter activate`" still silently drops org artifacts afterward via #3385 — an
  operator who only reads #3384's fix and tries the full documented workflow will still
  hit a silent drop, just from the other function. The mission report/PR description
  states this plainly so nobody closes #3385 by mistake believing #3384's fix covered it.

---

## User Scenarios & Testing *(mandatory)*

> **`--json` usage convention (applies uniformly to all four User Stories below):**
> `charter context --action <a>` is invoked with `--json` whenever a scenario's
> assertion depends on structured data the plain-text render omits — specific
> directive/tactic/procedure counts, count comparisons against the no-pack
> baseline, or artifact IDs — because without `--json` the command only prints
> `result.text` (a rendered text block); the per-artifact `id` fields and the
> `directives`/`tactics`/`styleguides`/`toolguides` lists exist only in the
> `--json` payload (`src/specify_cli/cli/commands/charter/context.py`,
> `json_output` branch). `--json` is **not** added where the assertion checks
> internal graph structure that payload does not expose — e.g. a specific edge
> triple's multiplicity — those scenarios verify by inspecting the resolved
> `DRGGraph` directly instead. `--json` may be omitted where a scenario asserts
> only that an exception did or did not propagate, with no numeric or ID
> comparison.

### User Story 1 - Guide-compliant org pack keeps its DRG edges after declaration (Priority: P1)

A governance maintainer authors an org doctrine pack following
`docs/guides/how-to/governance/create-an-org-doctrine-pack.md`: DRG extension content
lives under `<pack>/drg/*.graph.yaml`, and there is no root-level `*.graph.yaml` (the
guide never tells authors to create one). They declare the pack in the consumer
project's `.kittify/config.yaml` and run `charter context --action <a>`. Today this
silently collapses the action's directive/tactic/procedure counts to zero, with success
reported and only a WARNING log line as evidence. After the fix, the same command
resolves the built-in + project doctrine at its pre-adoption baseline (21 directives / 69
tactics / 10 procedures on this checkout) **plus** whatever edges the pack's own
`drg/*.graph.yaml` fragments contribute — never fewer than the bare-project baseline.

**Why this priority**: This is the exact defect in #3384 — P0-class, because it makes
every guide-compliant org pack (the only shape the guide documents) silently destroy a
project's action-scoped doctrine on adoption, with no operator-visible failure.

**Independent Test**: Build a fixture org pack containing only `drg/fixture.graph.yaml`
(no root `*.graph.yaml`), declare it, and assert `charter context --action <a> --json`
reports non-zero directive/tactic/procedure counts at least equal to the no-pack
baseline, and that any node declared in the pack's `drg/` fragment is present in the
resolved bundle.

**Acceptance Scenarios**:

1. **Given** an org pack directory containing only `drg/*.graph.yaml` fragments (no
   root-level `*.graph.yaml`, no `graph.yaml`), **When** the pack is declared and
   `charter context --action <a> --json` is run, **Then** the action-scoped
   directive/tactic/styleguide/toolguide/procedure counts are **not lower** than the
   bare-project baseline (no pack declared).
2. **Given** the same fixture pack, **When** `charter context --action <a> --json` is run
   and the pack's `drg/` fragment declares a node reachable from the resolved action,
   **Then** that node's artifact ID appears in the resolved doctrine bundle (the pack's
   content is actually loaded, not merely tolerated).

---

### User Story 2 - Org pack with genuinely no DRG content anywhere degrades cleanly (Priority: P1)

A pack directory is declared but truly has no graph content anywhere — no root
`graph.yaml`/`*.graph.yaml` and no `drg/` directory (or an empty one). This must degrade
to "no org DRG layer" — exactly as the existing project-branch behavior already does for
the equivalent empty-project-overlay case — and must **never** be reported as a success
with a silently emptied doctrine bundle for reasons other than "there was truly nothing
to load." The distinction from User Story 1 matters: a pack that legitimately has no DRG
content is not a bug, and the fix must not turn a well-formed empty pack into an error;
it must also not let a genuinely broken/malformed graph fail silently the way today's
`DRGLoadError` catch-and-collapse does.

**Why this priority**: This is the silent-success failure mode named by Standing Order #5
and the repo's dominant failure-mode pattern (SK-02/SK-04/SK-06 family in
`SPEC-KITTY-LEDGER.md`) — the fix must close the defect *class*, not just the one
reported instance, so the next "pack with no loadable graph" shape doesn't reopen the
same bug under a different directory layout.

**Independent Test**: Declare a pack directory that exists but contains no recognisable
graph file anywhere (root or `drg/`), run `charter context --action <a> --json`, and
assert the built-in + project doctrine baseline is preserved exactly (no zeroing) with no
exception raised and no reduction below the no-pack baseline.

**Acceptance Scenarios**:

1. **Given** an org pack directory that exists but has no `graph.yaml`, no
   `*.graph.yaml` at its root, and no `drg/` directory (or an empty `drg/`), **When**
   `charter context --action <a> --json` is run, **Then** the built-in + project doctrine
   resolves at the bare-project baseline (no reduction, no exception propagating past
   the resolver as an unhandled failure).
2. **Given** the same "nothing to load" pack, **When** the same `charter context
   --action <a> --json` invocation from Scenario 1 completes, **Then** the outcome is
   indistinguishable in doctrine counts from declaring no org pack at all —
   degrade-to-empty-org-layer, not degrade-to-empty-everything.

---

### User Story 3 - Malformed `drg/` fragment surfaces as a real, diagnosable failure (Priority: P1)

A governance maintainer's org pack `drg/` directory contains a fragment that is either
invalid YAML (a parse error) or valid YAML that fails `DRGGraph` schema validation. This
is a genuine authoring mistake, not an empty pack. `charter context --action <a>` must
not report success with a silently emptied bundle the way today's single
`except DRGLoadError` catch in `_load_action_doctrine_bundle` collapses this case
identically to "nothing to load." The outcome must be structurally distinguishable from
User Story 2's genuinely-empty success path, so a caller (human or automated) can tell
"malformed" apart from "there was truly nothing here."

**Why this priority**: FR-004 is High priority and is specifically about failure
visibility — without a concrete, checkable acceptance signal, an implementation could
satisfy FR-004's letter with a vacuous log-level bump while still swallowing the failure,
reopening the same silent-success shape this mission exists to close.

**Independent Test**: Build two fixture `drg/` fragments — one with invalid YAML syntax,
one with valid YAML that fails `DRGGraph` schema validation — declare each pack in turn,
run `charter context --action <a> --json`, and assert the outcome is structurally
distinguishable from User Story 2's genuinely-empty success path (e.g. a specific raised
exception type that is not the bare `DRGLoadError` already caught upstream, or a
non-empty, machine-checkable error field in the JSON output that User Story 2's case
never populates).

**Acceptance Scenarios**:

1. **Given** an org pack whose `drg/` directory contains a fragment file with invalid
   YAML syntax, **When** `charter context --action <a> --json` is run, **Then** the call
   does not report success with an empty-looking bundle; it produces a structurally
   distinguishable failure signal (a specific exception type, or a non-empty
   machine-checkable error field in the JSON output), never silently collapsing to the
   same shape as User Story 2's genuinely-empty case.
2. **Given** an org pack whose `drg/` directory contains a fragment file that is valid
   YAML but fails `DRGGraph` schema validation, **When** `charter context --action <a>
   --json` is run, **Then** the same distinguishable-failure outcome as Scenario 1
   occurs — the failure signal for "content existed and failed to parse/validate" has the
   same shape whether the cause was a YAML syntax error or a schema violation, and
   remains distinct from User Story 2's "nothing to load" success path.

---

### User Story 4 - Root-level graph and `drg/` fragments merge without silent drops or unresolved conflicts (Priority: P2)

A governance maintainer's org pack has both a root-level `*.graph.yaml` and a `drg/`
directory, each declaring different content. `charter context --action <a>` must load
and merge both — not silently prefer one over the other — and must have a decidable,
pinned outcome when the two sources disagree or duplicate each other, rather than
crashing or leaving the result to implementer discretion.

**Why this priority**: This is the "both present" shape FR-003 commits to supporting;
Medium priority because it is a less common authoring shape than the guide-compliant
`drg/`-only layout (User Story 1), but it must not be left untested since an unpinned
merge/conflict rule is exactly the kind of undocumented behavior that regresses silently.

**Independent Test**: Build a fixture org pack with a root-level `*.graph.yaml` declaring
node A and a `drg/fixture.graph.yaml` declaring node B (no conflict), declare it, run
`charter context --action <a> --json`, and assert both A's and B's artifact IDs are
present in the resolved doctrine bundle. Build a second fixture where the root graph and a
`drg/` fragment declare the identical edge triple (same source, target, relation), declare
it, run `charter context --action <a>`, and assert the call succeeds without raising
`DRGValidationError` **and** — by inspecting the resolved `DRGGraph` directly, since
`charter context --json`'s payload does not expose raw edge triples — that the resolved
graph contains exactly one instance of that (source, target, relation) triple afterward
(the org-layer sub-merge dedupes the triple to one copy — it does not drop it — per
FR-003).

**Acceptance Scenarios**:

1. **Given** an org pack root containing both a root-level `*.graph.yaml` declaring node
   A and a `drg/fixture.graph.yaml` declaring node B, **When** the pack is declared and
   `charter context --action <a> --json` is run, **Then** both A's and B's artifact IDs
   are present in the resolved doctrine bundle (neither source is silently dropped in
   favor of the other).
2. **Given** an org pack root where the root-level graph and a `drg/` fragment both
   declare the identical edge triple (same source, target, relation), **When** the pack
   is declared and `charter context --action <a>` is run, **Then** the call succeeds (no
   `DRGValidationError` propagates) **and** — verified by inspecting the resolved
   `DRGGraph` directly, since `charter context --json`'s payload does not expose raw edge
   triples — the org-layer sub-merge deduplicates the identical triple before validation
   so the resolved graph contains **exactly one** instance of the (source, target,
   relation) triple afterward, deduplicated to one retained copy, not dropped entirely,
   consistent with FR-003's dedup rule.

---

### Edge Cases

- What happens when the org pack root has **both** a root-level `*.graph.yaml`/`graph.yaml`
  **and** a `drg/` directory with fragments? Both sources exist per the guide's "all
  directories are optional" layout; the fix must load and merge both rather than picking
  one and silently dropping the other (the guide does not forbid combining them, and
  picking one silently would itself be a new instance of this defect class). See User
  Story 4: FR-003 pins `drg/`-authoritative precedence on same-URN node-label conflicts,
  and dedup (not raise) on identical edge triples.
- What happens when `<org_root>/drg/` exists but contains a malformed or invalid
  `*.graph.yaml` fragment (parse error, schema violation)? This is a genuinely
  unexpected error, not a "nothing to load" case — it must **not** be swallowed the way
  today's `DRGLoadError` catch in `_load_action_doctrine_bundle` swallows a legitimate
  parse/validation failure indistinguishably from an empty-pack case. The fix's guard
  narrows what gets treated as "no org layer"; it must not widen what gets silently
  caught. See User Story 3: FR-004 pins this as an org-branch-only narrowing — the
  project-layer catch is unchanged (see Non-Goals).
- What happens when `org_root` itself does not exist (the pack directory was declared
  but deleted, or misconfigured)? This must continue to degrade to "no org DRG layer"
  exactly as `_drg_helpers.py:87`'s existing `.exists()` check already handles today —
  out of scope for behavior change, only in scope in that the new guard must not
  regress it.
- What happens to a mission that is mid-flight (already past `specify`, mid-`implement`)
  when this fix lands? Only projects that declare an org pack (`organisation_packs` /
  equivalent config key present and resolving to an existing directory) are affected by
  this code path at all. A mid-flight mission with no org pack declared is unaffected —
  `org_root` stays `None` and the changed branch never executes. A mid-flight mission
  that *does* have an org pack declared and was silently running on a zeroed doctrine
  bundle sees its action-scoped doctrine counts increase (correctly) on its next
  `charter context` call; no state migration is needed since nothing persists the
  zeroed bundle across calls.

## Non-Goals

- **#3385 is explicitly out of scope.** `charter.kind_vocabulary._org_scan_dirs` scans a
  legacy `<pack>/<plural>/built-in/` layout that no org pack uses, which causes
  `charter activate <kind> <id>` to silently evict every org-pack artifact from the
  activation-filtered DRG the moment any single artifact is activated by id. This is a
  separate, independently P0-class silent-drop bug in a different function
  (`kind_vocabulary.py`, not `_drg_helpers.py` / `action_doctrine_bundle.py`) with its
  own fix and its own regression test, deferred to a separate mission. **Consequence to
  state plainly in the mission report and PR description:** even after this mission's fix
  lands, an operator who declares an org pack correctly (fixed by this mission) and then
  runs `charter activate` on any artifact (still broken per #3385) will still silently
  lose their org-pack artifacts — from the activation-filter path instead of the
  graph-load path. Do not close #3385 as resolved by this mission's PR.
- No change to `src/charter/kind_vocabulary.py`.
- No change to the org-doctrine-pack authoring guide
  (`docs/guides/how-to/governance/create-an-org-doctrine-pack.md`) is anticipated — it
  already documents the `drg/`-only, no-root-graph layout that triggers this defect; the
  fix makes the code match the guide rather than the other way around. If plan/tasks
  phases determine a clarifying note is warranted, that is an in-scope documentation
  touch, but no rewrite of the guide's structure is expected.
- No change to the built-in graph loader's public contract
  (`doctrine.drg.loader.load_graph_or_dir`, `has_graph_files`) — this mission composes
  existing loader primitives at the `_drg_helpers.py` call site; it does not change their
  signatures or semantics.
- **No change to project-layer `DRGLoadError` handling.** The same wide
  `except DRGLoadError` catch in `_load_action_doctrine_bundle` that FR-004 narrows for
  the org-pack branch also currently swallows malformed PROJECT-layer
  (`.kittify/doctrine`) graph content identically (a schema-invalid project overlay
  fragment raises `DRGLoadError` from `load_graph` and is caught the same way). FR-004's
  narrowing is scoped to the org branch only; project-layer malformed-content visibility
  is unchanged and explicitly out of scope for this mission. Extending the same
  visibility fix to the project layer is a plausible follow-up but is not something
  #3384 reported and is not tasked here.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Guard the org DRG root load with a graph-files check | As a governance maintainer, I want an org pack root with no loadable graph to degrade to "no org DRG layer" instead of raising `DRGLoadError`, so that declaring a pack never reduces available doctrine below the bare-project baseline. | High | Open |
| FR-002 | Load DRG content from `<org_root>/drg/` | As a governance maintainer, I want my guide-compliant pack's `drg/*.graph.yaml` fragments to actually be loaded, so that the DRG edges I authored per the documented layout take effect. | High | Open |
| FR-003 | Merge root-level and `drg/`-level org graph content when both are present | As a governance maintainer, I want a pack with both a root graph and `drg/` fragments to have both loaded and merged, so that no authored content is silently dropped based on which location it lives in. On a same-URN node-label conflict between the root graph and `drg/` fragments, **`drg/` fragments are authoritative**: the org-layer sub-merge calls `merge_layers(root_graph, drg_graph)` — the root graph as the first (`built_in`) positional argument, `drg/` content as the second (`project`) positional argument — mirroring the override-wins convention `merge_layers` already applies to its second argument when the org layer overrides built-in. (This second parameter happens to be named `project` in `merge_layers`' own signature — a pre-existing overload baked into the function itself, not something this spec invented; confusingly, that name is normally used for the outer built-in-vs-project-layer merge, but here it is being reused for the org-internal `drg/`-vs-root composition, not the document's own "project layer" [`.kittify/doctrine`] concept.) `merge_layers()` itself (`src/doctrine/drg/loader.py`) is **not modified** by this fix and keeps its additive-only, no-removal semantics unchanged; the dedup step below is new logic local to `_drg_helpers.py` that runs on the org-internal root+`drg/` sub-merge result *before* that result is fed into the existing, unmodified `merge_layers(built_in, org)` call used elsewhere in `load_validated_graph`. When the root graph and `drg/` fragments declare an **identical edge triple** (same source, target, and relation), the org-layer sub-merge **deduplicates the triple before the final `assert_valid` validation pass** (see C-001 for the required implementation mechanism) — an exact duplicate across the two sources is treated as redundant authoring, not a conflict, collapsed to exactly one retained copy of the triple, and must not raise `DRGValidationError`. | Medium | Open |
| FR-004 | Preserve genuine load-failure visibility | As a governance maintainer, I want a malformed or invalid `drg/` fragment to still surface as a real, non-swallowed failure (not silently collapsed into an empty bundle the same way "nothing to load" is), so that authoring mistakes are diagnosable rather than mistaken for an empty pack. This narrowing is **scoped to the org-pack branch only**: the existing wide `except DRGLoadError` catch in `_load_action_doctrine_bundle` continues to catch and collapse malformed PROJECT-layer (`.kittify/doctrine`) graph content exactly as it does today — that behavior is unchanged and explicitly out of scope for this mission (see Non-Goals). This requirement is verified by an automated regression test (see User Story 3) that exercises both an invalid-YAML `drg/` fragment fixture and a valid-YAML-but-schema-invalid fragment fixture, and asserts the failure outcome is structurally distinguishable from User Story 2's genuinely-empty success path. | High | Open |
| FR-005 | Non-vacuous regression test: doctrine counts survive org-pack declaration | As a maintainer of this codebase, I want an automated regression test that declares a `drg/`-only fixture org pack and asserts the resolved directive/tactic/procedure counts for `charter context --action <a> --json` are not lower than the no-pack baseline (mirroring the issue's own probe: 21 directives / 69 tactics / 10 procedures on this checkout), so that this defect class cannot silently reopen without a test going red first. | High | Open |
| FR-006 | Non-vacuous regression test: root+`drg/` merge and conflict handling | As a maintainer of this codebase, I want automated regression tests that (a) declare a fixture org pack with a root-level graph declaring node A and a `drg/` fragment declaring node B and assert **both** A's and B's artifact IDs are present in the resolved doctrine bundle, and (b) declare a fixture org pack where the root graph and a `drg/` fragment declare an identical edge triple and assert **both** that the org-layer sub-merge deduplicates it without raising `DRGValidationError` **and** that the resolved graph contains **exactly one** instance of that (source, target, relation) triple afterward — not merely that no exception was raised — so that FR-003's merge and conflict-precedence behavior cannot silently regress into either a false conflict or a silently dropped edge. (Which internal comparison the dedup step uses is a code-review-time constraint, not something this test asserts — see C-001.) | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No regression to bare-project baseline | For any project with no org pack declared, `charter context --action <a>` output (directive/tactic/styleguide/toolguide/procedure counts and IDs) is byte-for-byte unaffected by this change — the changed branch only executes when `org_root` is non-`None` and resolves to an existing directory. | Reliability | High | Open |
| NFR-002 | Scoped test run | This mission's verification runs only the affected test packages (`tests/charter/`, `tests/architectural/`), not the full repository suite, consistent with the Testing Requirements framing for a change of this blast radius. | Process | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Blast radius | Changes are confined to `src/charter/_drg_helpers.py`, `src/charter/action_doctrine_bundle.py`, and new regression fixtures/tests under `tests/charter/`. No change to `src/charter/kind_vocabulary.py`, `src/doctrine/drg/loader.py`'s public signatures, **or `merge_layers()`'s implementation** (its additive-only, no-removal semantics must remain byte-for-byte unchanged — the root+`drg/` dedup required by FR-003/FR-006 is new logic in `_drg_helpers.py`, not a modification to `merge_layers`), or the org-pack authoring guide's documented layout. The root+`drg/` dedup step required by FR-003/FR-006(b) **must reuse the existing canonical `doctrine.drg.validator.duplicate_edge_triples` primitive as the single definition of "duplicate"** — no independently-written `(source, target, relation)` comparison. This is a code-review-time / architectural-conformance constraint on the implementation, not a black-box-testable FR commitment: the regression test mandated by FR-006(b) verifies the observable outcome (no `DRGValidationError`, exactly one retained triple), not which comparison code path produced it. | Technical | High | Open |
| C-002 | `__all__` export discipline (charter C-007) | Any new module-level helper function introduced in `src/charter/_drg_helpers.py` in service of this fix must either be added to that module's `__all__` (if it becomes an external export with real callers) or kept module-private (no leading-underscore-free name added to `__all__` without a caller in `src/`) — `tests/architectural/test_no_dead_symbols.py` enforces this. | Technical | High | Open |
| C-003 | ATDD-first (charter C-011) | Failing-first ATDD tests pinning FR-004's, FR-005's, and FR-006's observable behavior — respectively: a structurally distinguishable failure signal for a malformed `drg/` fragment (FR-004); non-zero doctrine counts surviving org-pack declaration (FR-005); and the root+`drg/` both-present merge and identical-edge-triple dedup outcomes (FR-006) — are each committed as a separate commit before any implementation commit; each test must be RED on the WP's `planning_base_branch` and GREEN on the WP's final commit. | Process | High | Open |
| C-004 | Non-vacuous architectural gate discipline (Standing Order #5) | The regression tests required by FR-004, FR-005, and FR-006 must each assert a concrete, checkable outcome, not merely "no exception raised" or "a log line changed": FR-005's test asserts a non-zero floor (the baseline counts); FR-004's test asserts a structurally distinguishable failure signal (a specific exception type, or a non-empty machine-checkable error field) for the malformed-fragment case, distinct in shape from User Story 2's genuinely-empty success path; FR-006's tests assert both the both-present node-presence outcome and the identical-edge-triple dedup outcome. A test that only checks for the absence of an exception, or only that a log line changed, would be vacuous against the actual reported defect (empty bundle reported as success). | Technical | High | Open |
| C-005 | Pre-existing red-main exclusion | Issue #3284's known-red baseline on `main` is pre-existing and unrelated to this defect; this mission does not attempt to fix it and does not file a duplicate issue for it. Any failure attributable to #3284 encountered while running `tests/charter/` or `tests/architectural/` is reported as pre-existing, not folded into this mission's scope. | Process | Medium | Open |

### Key Entities

- **Org DRG root** (`org_root`): the configured filesystem path to a declared org
  doctrine pack, resolved by `_resolve_action_bundle` in
  `src/charter/action_doctrine_bundle.py`. May contain a root-level `graph.yaml` /
  `*.graph.yaml`, a `drg/` subdirectory of `*.graph.yaml` fragments, both, or neither.
- **Doctrine bundle** (`_ActionDoctrineBundle`): the resolved set of
  directive/tactic/styleguide/toolguide/procedure/asset IDs for a given
  `(action, mission_type)` pair, produced by `_load_action_doctrine_bundle`. This is the
  artifact that silently zeroes today when the org-root load raises `DRGLoadError`.
- **DRG graph** (`DRGGraph`): the merged built-in + org + project directive-relation graph
  loaded by `load_validated_graph` in `src/charter/_drg_helpers.py`, the function this
  mission's fix directly modifies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A `drg/`-only fixture org pack (no root-level graph file), once declared,
  yields `charter context --action <a> --json` directive/tactic/procedure counts that are
  **not lower** than the bare-project (no-pack) baseline on the same checkout — verified
  by the regression test required by FR-005.
- **SC-002**: The same fixture pack's `drg/`-declared node is present in the resolved
  action doctrine bundle's artifact IDs, demonstrating the pack's content is loaded, not
  merely tolerated.
- **SC-003**: A pack directory that exists but contains no graph content anywhere (root
  or `drg/`) degrades to the bare-project baseline with no exception propagating and no
  reduction in doctrine counts — the "nothing to load" case is provably indistinguishable
  from "no org pack declared."
- **SC-004**: `tests/charter/` and `tests/architectural/` pass (excluding any failure
  attributable to the pre-existing #3284 red baseline), including
  `tests/architectural/test_no_dead_symbols.py` for the `__all__` convention (C-002) and
  `tests/architectural/test_no_legacy_terminology.py`.
- **SC-005**: A fixture org pack with a root-level graph declaring node A and a `drg/`
  fragment declaring node B, once declared, yields a resolved doctrine bundle containing
  **both** A's and B's artifact IDs — verified by the regression test required by FR-006.
- **SC-006**: A fixture org pack where the root graph and a `drg/` fragment declare an
  identical edge triple (same source, target, relation), once declared, resolves without
  raising `DRGValidationError`, **and** the resolved graph contains **exactly one**
  instance of that (source, target, relation) triple — the org-layer sub-merge
  deduplicates the triple (collapses two authored copies to one), it does not drop it
  entirely, before validation, per FR-003 — verified by the regression test required by
  FR-006.
- **SC-007**: A fixture `drg/` fragment that is invalid YAML, and a second fixture that
  is valid YAML but fails `DRGGraph` schema validation, each produce a failure outcome
  from `charter context --action <a>` that is structurally distinguishable from User
  Story 2's genuinely-empty success path (a specific exception type, or a non-empty
  machine-checkable error field) — verified by the regression test required by FR-004.
