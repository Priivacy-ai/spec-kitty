# Mission Specification: `_org_scan_dirs` must scan the real org-pack layout, not a phantom one

**Mission Branch**: `main` (topology `single_branch`; no lane branch is minted for this
mission — `spec-kitty agent mission branch-context --json` resolves `current_branch` /
`target_branch` / `planning_base_branch` / `merge_target_branch` all to `main`)
**Created**: 2026-08-13
**Status**: Draft
**Issue**: [#3385](https://github.com/Priivacy-ai/spec-kitty/issues/3385) — `_org_scan_dirs` scans
a phantom layout: one `charter activate` silently drops every org-pack artifact from the DRG.
**Sibling defect (out of scope, verification-only)**: [#3384](https://github.com/Priivacy-ai/spec-kitty/issues/3384)
— org-graph root-graph guard. Both are the two halves of the `up-org-pack-load-integrity` P0
pair; #3384 is handled by a sibling mission (`org-pack-drg-root-graph-guard`) already in
progress in parallel. This mission is **#3385 only**.

## Clarifications

### Session 2026-08-13 (operator scope ruling, pre-mission)

- Q: This P0 pair has two independent defects (#3384: org-graph load requires a root-level
  `*.graph.yaml`; #3385: `_org_scan_dirs` scans a layout no real org pack uses). Should one
  mission fix both? → A: **No.** Split strictly by issue. This mission (`org-activation-scan-dirs`)
  authors production code **only** for #3385 (**D2**). #3384 (**D1**) is handled by a sibling
  mission (`org-pack-drg-root-graph-guard`, same operator, running in parallel) and must not
  be touched here as anything other than read-only evidence-gathering — no D1 code, no change
  competing with #3384's fix.
- Q: If this mission can't fix D1, what does it owe D1 at all? → A: A **verification-only**
  contribution: define acceptance criteria, contingent on #3384 landing, that (a) prove a
  declared org pack with no root-level `*.graph.yaml` no longer zeros the built-in action
  doctrine grain once #3384 ships, and (b) check two specific things #3384's fix may
  legitimately omit — whether the diagnostic it surfaces is a *named* diagnostic (not a bare
  `logging.WARNING`), and whether `<org_root>/drg` content is read as an alternative graph
  location. These are re-verification criteria for a later pass, not implementation tasks for
  this mission.
- Q: `_built_in_scan_dir` and `_layer_scan_dirs` sit in the same file as `_org_scan_dirs` and
  are similarly terse — should the mission clean them up while it's in the file (Boy Scout
  Rule, `DIRECTIVE_025`)? → A: **No.** Per `RECONCILE_CHANGE_SCOPE_TENSIONS`
  (`.kittify/charter/charter.md`), step 3 — Locality of Change — is what governs here: edits
  stay close to the specific problem, and `_built_in_scan_dir`/`_layer_scan_dirs` are not
  broken and are not the cited defect (`_org_scan_dirs` is). Both functions already sit in the
  one file smallest-viable-diff selects for this change (`src/charter/kind_vocabulary.py`), so
  touching them would not grow the file set at all — the reason to leave them alone is that
  they are not the problem this mission exists to fix, not that editing them would expand
  scope. Deferred, not silently folded in.

## User Scenarios & Testing *(mandatory)*

**Primary actor**: any project or organization that installs an org doctrine pack and then
runs `charter activate <kind> <stem>` for any single built-in or project artifact — the
documented, expected way to use activation.

**Problem, restated in this mission's own words (verified independently at checkout HEAD
`ab0a0b9b5b5e6803775e45bebd66d1cc8d3b68dc`, byte-identical to issue #3385's citation)**:

`charter.kind_vocabulary._org_scan_dirs` (`src/charter/kind_vocabulary.py:200-209`) is:

```python
def _org_scan_dirs(
    kind: ArtifactKind, org_roots: list[Path] | None
) -> list[tuple[Path, bool]]:
    """Return ``<root>/<plural>/built-in`` dirs that exist for *org_roots*."""
    dirs: list[tuple[Path, bool]] = []
    for root in org_roots or []:
        candidate = root / kind.plural / "built-in"
        if candidate.is_dir():
            dirs.append((candidate, True))
    return dirs
```

It scans **only** `<org_root>/<kind.plural>/built-in/` — a legacy, package-shaped layout that
no real org pack uses. Three independent sources agree the real layout is **flat**
(`<org_root>/<plural>/`, no `built-in/` segment):

1. **The live doctrine loader.** `DoctrineService._org_dirs` (`src/doctrine/service.py:47-55`)
   returns `[root / artifact for root in self._org_roots]` — one directory per configured org
   root, no `built-in` suffix — consumed by every repository property (e.g.
   `DoctrineService.directives`, `:57-64`) and, at the base-repository level, by
   `BaseDoctrineRepository._load` (`src/doctrine/base.py:356-373`), which walks this org list
   with a **non-recursive** `glob` (`src/doctrine/base.py:25`, `:159`) — distinct from the
   built-in layer's `rglob` (`:182`).
2. **The pack-layout guide.** `docs/guides/how-to/governance/create-an-org-doctrine-pack.md:58`
   shows the shipped example tree with a bare `directives/` directory — no `built-in/` segment
   anywhere in the documented layout.
3. **The recognised-artifact-dirs contract.** `_RECOGNISED_ARTIFACT_DIRS`
   (`src/specify_cli/doctrine/snapshot.py:38-50`) enumerates `directives`, `tactics`,
   `styleguides`, `toolguides`, `paradigms`, `procedures`, `agent_profiles`,
   `mission_step_contracts`, `drg` — flat names, again no `built-in` segment.

**The failure mechanism, cited by file:line, independently re-walked in this checkout**:

- `charter activate directive <stem>` writes the `activated_directives` key (the pattern
  computed at `src/charter/pack_manager.py:126`,
  `f"activated_{ArtifactKind.from_operator_token(token).plural}"`) into `.kittify/config.yaml`
  — the exact key that arms the per-artifact-ID gate.
- `filter_graph_by_activation` calls `_resolve_activated_urns_by_kind`
  (`src/charter/drg.py:384-406`), which calls `_resolve_activated_urns_for_kind`
  (`:333-381`) once per kind. For every stem in the activated set it calls
  `resolve_artifact_urn(kind_enum, stem, doctrine_root=doctrine_root, org_roots=org_roots)`
  (`:374-377`).
- `resolve_artifact_urn` (`src/charter/kind_vocabulary.py:253+`) walks `_scan_roots`
  (`:142-180`), which appends `_built_in_scan_dir(kind)` then extends with
  `_org_scan_dirs(kind, org_roots)` (`:176-179`). Because `_org_scan_dirs` only looks under
  `.../built-in/`, a flat-layout org pack contributes **zero** scan directories, so
  `resolve_artifact_urn` cannot find the org artifact at any stem and raises
  `UnknownArtifactIdError` (`src/charter/kind_vocabulary.py:85`).
- Back in `_resolve_activated_urns_for_kind`, that `UnknownArtifactIdError` is caught and
  swallowed (`src/charter/drg.py:379-380`, `except UnknownArtifactIdError: continue  #
  Skip-with-report`), so the org artifact's URN never enters the resolved-URN set for that
  kind.
- `_node_is_activated` (`src/charter/drg.py:409-475`) step 3 (`:467-473`) then drops the org
  node from the filtered graph: its full URN is absent from `resolved_urns`, and since the
  gate is non-`None` (the config key is present) and non-empty (another artifact was
  activated), the org node fails membership and is excluded.

**Net effect**: activating the org pack's **own** artifact by its own config-stem can never
succeed — `resolve_artifact_urn` cannot find it via `_org_scan_dirs`, so it can never survive
`_node_is_activated`'s step-3 filter, no matter what else is or isn't activated alongside it — no
error, no warning, `charter activate` reports success while quietly failing to do the one thing
the operator asked for. (Relatedly, and *not a defect this mission changes*: activating some
other, unrelated built-in or project artifact by stem also does not surface an org-pack artifact
that was never itself explicitly activated — the per-artifact-ID gate in `_node_is_activated`
step 3 (`src/charter/drg.py:467-473`) excludes ANY URN absent from the resolved-activation set
once that set is armed (non-`None`), symmetrically for org, built-in, and project artifacts alike
— it is not an org-specific gap in `default.yaml`'s enumeration. `CharterPackManager.activate`'s
default-pack materialization (`src/charter/pack_manager.py:601-616`,
`plan_activation`'s `if current is None:` branch, `src/charter/activation_engine.py:257-268`)
seeds an unset activation set from the STATIC shipped `default.yaml`
(`src/charter/pack_manager.py:511-518`, `src/charter/packs/default.yaml`) rather than enumerating
every artifact on disk — but the same exclusion would equally apply to an unlisted built-in or
project artifact, not only to org ones. This mission makes the org pack's *own* stem always
resolve when explicitly activated; it does not change the gate's general selectivity — see
Acceptance Scenario 5.) With the
`activated_*` key absent, the filter is default-allow
(`_resolve_activated_urns_for_kind` returns `None` when `activated_ids is None`, `:359-360`) and
the org artifact survives — which is why this is easy to miss in ad hoc testing and guaranteed
once a project does the documented thing of activating its own org artifact by stem.

### User Story 1 - A correctly-laid-out org pack survives activation, loudly (Priority: P1)

As an operator who has installed an org doctrine pack in the documented flat layout
(`<org_root>/directives/…`, no `built-in/` segment) and who runs `charter activate directive
<org-directive-stem>` for one of my own org directives, I want that directive to actually
resolve and survive activation filtering — not silently vanish because `_org_scan_dirs` never
looked in the directory it actually lives in. The **observable, loud** signal of success is
structural: the org artifact's URN is a member of the resolved-URN set returned by
`_resolve_activated_urns_by_kind`, and the corresponding node survives `_node_is_activated`'s
step-3 gate and appears in `filter_graph_by_activation`'s output graph. This replaces today's
silent failure (`resolve_artifact_urn` raising `UnknownArtifactIdError`, swallowed by
`_resolve_activated_urns_for_kind`) with a positive, checkable fact — not a warning bolted onto
the old behavior, but the artifact genuinely being found. This holds regardless of what else is
or isn't activated alongside it (Acceptance Scenario 5) — but activating something other than
the org stem itself cannot surface it; the per-artifact-ID gate is selective by design, not
something this mission changes.

**Why this priority**: this is the whole defect. Every project with an org pack that tries to
activate one of its own org-pack artifacts by stem hits this today — the artifact can never
resolve via `_org_scan_dirs`, so it silently fails to survive activation filtering, with no
error surfaced to the operator.

**Independent Test**: build a fixture org pack in the flat layout — including a root-level
`*.graph.yaml` declaring the org directive as a DRG node (fixture-construction detail per
FR-002; test data only, not a change to `_drg_helpers.py`, consistent with C-002) —
register it as an org root, call `charter activate directive <org-directive-stem>` for the org
directive's own config-stem (or the equivalent programmatic `plan_activation`/`commit_activation`
call), then assert the org pack's own directive URN is present in
`filter_graph_by_activation`'s output graph.

**Acceptance Scenarios**:

1. **Given** an org root containing `<org_root>/directives/<org-directive>.directive.yaml`
   (flat layout, no `built-in/` segment) **and** a root-level `<org_root>/<org-directive>.graph.yaml`
   declaring the org directive as a DRG node (fixture-construction detail — test data only, not a
   change to `_drg_helpers.py`; `filter_graph_by_activation` only ever operates on nodes already
   in the merged graph, and DRG nodes come from `*.graph.yaml` fragments, never synthesized from
   `*.directive.yaml` artifact files) and no other activation state, **When**
   `charter activate directive <org-directive-stem>` runs for the org directive's own
   config-stem — the full `activate()` → `filter_graph_by_activation()` round trip, not a direct
   `resolve_artifact_urn` call — **Then** the org directive's node is present in the graph
   returned by `filter_graph_by_activation`.
2. **Given** the same org root, **When** `resolve_artifact_urn(ArtifactKind.DIRECTIVE,
   <org-directive-stem>, doctrine_root=doctrine_root, org_roots=[org_root])` is called directly,
   **Then** it returns the org directive's URN instead of raising `UnknownArtifactIdError`.
3. **Given** an org root that additionally contains the legacy
   `<org_root>/directives/built-in/<legacy-directive>.directive.yaml` shape, **When** the same
   activation runs, **Then** artifacts under **both** the flat directory and the legacy
   `built-in/` subdirectory are found — the fix is additive (the old scan location keeps
   working), not a replacement that trades one phantom layout for a different single layout.
4. **Given** an org root containing a same-config-stem artifact file under both
   `<org_root>/directives/<stem>.directive.yaml` (flat, `id: DIRECTIVE_FLAT`) and the legacy
   `<org_root>/directives/built-in/<stem>.directive.yaml` (`id: DIRECTIVE_LEGACY`), **When**
   `resolve_artifact_urn(ArtifactKind.DIRECTIVE, <stem>, doctrine_root=doctrine_root,
   org_roots=[org_root])` is called, **Then** it returns `directive:DIRECTIVE_FLAT` — the
   flat-layout file's URN — per FR-001's precedence rule, never the legacy file's URN and never a
   result that depends on incidental scan order.
5. **Given** the org root from Scenario 1 (flat-layout org directive plus the root-level
   `*.graph.yaml` DRG-node fixture), **When** `charter activate directive <org-directive-stem>`
   and `charter activate directive <unrelated-built-in-stem>` both run, in either order, **Then**
   the org directive's node is present in `filter_graph_by_activation`'s output in both
   orderings — its presence follows from its own stem being a member of the activated set, not
   from what else is activated or in which order. Activating **only** the unrelated built-in
   stem, without ever activating the org stem itself, does **not** surface the org node — the
   per-artifact-ID gate in `_node_is_activated` step 3 (`src/charter/drg.py:467-473`) is
   selective by design, not a defect this mission changes.

### User Story 2 - The regression test is red before the fix and green after (Priority: P1)

As a reviewer applying the charter's ATDD-First Discipline (`C-011`) and Standing Order #4
(test remediation & bug-fix discipline, red-first through the pre-existing entry point), I want
the regression test for this defect to demonstrably fail against the current, unfixed
`_org_scan_dirs` before the ~5 LOC production fix lands, and pass after — proving the test
actually exercises the defect rather than trivially passing regardless.

**Why this priority**: co-equal with Story 1. A regression test that cannot be shown red first
does not prove the fix does anything.

**Independent Test**: run the new regression test against the pre-fix `_org_scan_dirs` body
(the code quoted verbatim above) and observe `AssertionError` / the org node missing from the
filtered graph; then run it again after the fix and observe green. The implementing work
package records both runs (or the git history: a red commit followed by a green one on the
same test, never a single commit that adds a test already green).

**Acceptance Scenarios**:

1. **Given** the mission's `planning_base_branch` (`main` at this mission's start,
   `ab0a0b9b5`), **When** the new regression test (User Story 1's Independent Test, made
   concrete as a pytest test) runs, **Then** it fails — the org directive is absent from the
   filtered graph / `UnknownArtifactIdError` is raised.
2. **Given** the mission head with the `src/charter/kind_vocabulary.py:200-209` fix applied,
   **When** the same test runs unmodified, **Then** it passes.

### User Story 3 - Once #3384 lands, two things about its fix get checked (Priority: P3, contingent)

As the operator who split this P0 pair across two missions, I want this mission to leave behind
the two verification criteria that #3384's own fix is not obligated to satisfy on its own, so a
later pass (this mission's own follow-up, or #3384's implementer) can check them without
re-deriving the question from scratch.

**Why this priority**: verification-only, blocked on a fix this mission does not author.
Lowest priority; does not block D2's own acceptance.

**Independent Test (to run only after #3384 merges)**: activate an org-pack artifact whose org
root has no root-level `*.graph.yaml`, then (a) inspect whatever diagnostic the fixed load path
surfaces and check whether it is a named diagnostic type/code rather than a bare
`logging.WARNING`; (b) place the org's DRG fragments under `<org_root>/drg/*.graph.yaml`
instead of directly under `<org_root>/*.graph.yaml` and check whether the fixed load path finds
them.

**Acceptance Scenarios** (contingent — not blocking this mission's own completion; recorded so
the follow-up check has a fixed target):

1. **Given** #3384's fix merged and an org root with no root-level `*.graph.yaml`, **When** the
   action-doctrine bundle loader's collapse-to-empty-bundle path
   (`src/charter/action_doctrine_bundle.py:152-156`, today `# … collapse it to an empty bundle
   and log a WARNING (WP04)`) is exercised, **Then** record whether the surfaced diagnostic is a
   named exception/diagnostic type (e.g. a dedicated `OrgGraphRootMissing`-style class) or
   remains a bare `_LOGGER.warning(...)` call — this mission takes no position on which #3384
   should choose, only that the fact gets checked and recorded.
2. **Given** #3384's fix merged and DRG fragments placed under `<org_root>/drg/*.graph.yaml`
   (a location `_RECOGNISED_ARTIFACT_DIRS`, `src/specify_cli/doctrine/snapshot.py:38-50`,
   already names as a recognised org-pack subdirectory), **When** `load_validated_graph`
   (`src/charter/_drg_helpers.py:55-97`, read-only reference — not modified by this mission)
   resolves the org layer, **Then** record whether those fragments are found. **Current
   evidence, gathered read-only and not acted on**: `load_graph_or_dir`
   (`src/doctrine/drg/loader.py:81-107`) globs `*.graph.yaml` directly under the path it is
   given (`path.glob("*.graph.yaml")`, non-recursive) — so as the code reads today, fragments
   nested one level down at `<org_root>/drg/` are **not** found by a call with
   `org_root=<org_root>`. This is stated as a finding for the follow-up check, not as a defect
   this mission is fixing.

### Edge Cases

- **A genuinely absent or misspelled stem — explicitly out of scope, named so it is not
  silently expanded into.** After this fix, an org pack in the flat layout is *findable*, but
  activating a stem that does not exist anywhere (built-in, org, or project) still hits
  `resolve_artifact_urn` → `UnknownArtifactIdError` → the `continue` skip-with-report in
  `_resolve_activated_urns_for_kind` (`src/charter/drg.py:379-380`) → the typo'd artifact is
  quietly absent from the resolved set. That swallow-on-typo behavior is a separate, larger
  defect class (it touches the activation contract's error-reporting story generally, not just
  org-pack scanning) and is **not** fixed by this mission.
- **Legacy `built-in/`-shaped org packs must not regress.** If any org pack in the wild does
  use the legacy `<root>/<plural>/built-in/` shape (the one `_org_scan_dirs` already scans
  today), the fix is additive — both directories are scanned where each exists — so that shape
  keeps working exactly as before.
- **Recursive-flag parity with the live loader.** The existing `built-in/` scan entry is
  recorded recursive (`(candidate, True)`, mirroring `_built_in_scan_dir`'s and the built-in
  layer's `rglob` — `src/doctrine/base.py:182` — because several built-in kinds nest artifacts
  under category subdirectories). The live loader's org-layer scan is **non-recursive**
  (`src/doctrine/base.py:25`, `:159`, plain `glob`). The new flat-layout entry should carry
  `recursive=False` to match the loader it is closing the gap with — a recursive flat scan
  would silently accept a layout the live loader does not, reopening a smaller version of the
  same source-of-truth divergence this defect is about.
- **No opportunistic cleanup of `_built_in_scan_dir` / `_layer_scan_dirs`.** Both sit in
  `src/charter/kind_vocabulary.py` next to `_org_scan_dirs` and are not touched — see
  Clarifications, `RECONCILE_CHANGE_SCOPE_TENSIONS`.
- **Same-config-stem file present in both the flat and legacy directories.** Per FR-001's
  precedence rule, the flat-layout file wins (Acceptance Scenario 4) — a deliberate, documented
  choice, not an accident of `_scan_roots`'s list order. Surfacing a collision warning (mirroring
  the `DoctrineLayerCollisionWarning` pattern, `src/doctrine/base.py:46,202`) is not required by
  this mission; silently preferring flat is sufficient to close the ambiguity this raises.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | Requirement | User Story | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| FR-001 | `_org_scan_dirs` scans both the flat and legacy org layouts | `_org_scan_dirs` (`src/charter/kind_vocabulary.py:200-209`) returns a scan entry for `<root>/<plural>` (flat, `recursive=False`, matching `DoctrineService._org_dirs` / `BaseDoctrineRepository`'s non-recursive org glob) **and**, where it separately exists on disk, `<root>/<plural>/built-in` (`recursive=True`, unchanged from today), for every configured org root, with the flat entry ordered before the legacy entry in the returned list. Neither directory existing is not an error — the function returns fewer entries, never raises. **Precedence rule**: when a same-config-stem artifact file exists under both `<root>/<plural>` and `<root>/<plural>/built-in` for one org root, the flat-layout file wins — `resolve_artifact_urn` (`:253+`) is first-match-wins over `_scan_roots`'s output, so ordering the flat entry first makes this a deliberate, documented choice (flat is the canonical/current layout; legacy is kept only for backward compatibility) rather than an accidental list-order artifact. See Acceptance Scenario 4. | User Story 1 | High | Open |
| FR-002 | Red-first regression test at the activation-filter level | A new pytest regression test proves an org-pack artifact (flat layout) is present in `filter_graph_by_activation`'s output after `charter activate directive <org-directive-stem>` activates the org artifact's **own** config-stem (the full `activate()` → `filter_graph_by_activation()` round trip, not a direct `resolve_artifact_urn()` call). The fixture must also declare the org directive as a DRG node in a root-level `*.graph.yaml` — test-fixture data only, not a change to `_drg_helpers.py` (C-002) — since `filter_graph_by_activation` only ever operates on nodes already present in the merged graph, and DRG nodes come from `*.graph.yaml` fragments, never synthesized from `*.directive.yaml` files. The test is authored to fail against the pre-fix `_org_scan_dirs` body and to pass against the post-fix body (both runs recorded by the implementing WP). | User Story 2 | High | Open |
| FR-003 | Existing unit-level `_org_scan_dirs` tests updated for the new contract | `TestOrgScanDirsHelper` in `tests/charter/test_kind_vocabulary_scan_roots.py` (currently `test_none_org_roots_returns_empty_list`, `test_missing_org_built_in_dir_skipped`, `test_existing_org_built_in_dir_returned` — the last of which today pins the **old**, phantom-layout-only behavior) is extended to cover: only the flat dir present, only the legacy `built-in/` dir present, both present (both returned), neither present (empty list), and a same-config-stem file present under both directories asserting `resolve_artifact_urn` returns the flat-layout file's URN (FR-001's precedence rule) — without deleting the pre-existing legacy-shape coverage. This is unit-level coverage of `_org_scan_dirs`/`resolve_artifact_urn`; unlike FR-002's activation-filter-level test, it needs no DRG-graph (`*.graph.yaml`) fixture. | User Story 1 | High | Open |

### Contingent Verification Criteria

These are deliberately **not** `FR-NNN` functional requirements — they are recorded as `VC-NNN`
("verification criteria") so that `parse_requirement_ids_from_spec_md`
(`src/specify_cli/requirement_mapping.py:104-117`, regex `\b(?:FR|NFR|C)-\d+\b`) does not treat
them as functional-requirement IDs a work package must claim via `requirement_refs`. Both are
contingent on issue #3384 landing (a sibling mission's fix, out of scope here — see
Clarifications) and verification-only: this mission records the finding, it does not implement a
change to make either true, and neither gates `mission finalize-tasks` or this mission's own
completion (SC-005).

| ID | Title | Verification Criterion | User Story | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| VC-001 | Named-diagnostic check for the D1 collapse path | Once issue #3384's fix lands, verify whether the collapse-to-empty-bundle path at `src/charter/action_doctrine_bundle.py:152-156` surfaces a named diagnostic (not a bare `logging.WARNING`) when an org pack has no root-level `*.graph.yaml`. This mission records the finding; it does not implement a change to make it true. | User Story 3 | Low | Open |
| VC-002 | `<org_root>/drg` alternative-location check | Once issue #3384's fix lands, verify whether DRG fragments placed at `<org_root>/drg/*.graph.yaml` (a location `_RECOGNISED_ARTIFACT_DIRS` already names, `src/specify_cli/doctrine/snapshot.py:38-50`) are read as an alternative to `<org_root>/*.graph.yaml`. Pre-fix evidence (read-only, `src/doctrine/drg/loader.py:81-107`): they currently are not, because `load_graph_or_dir`'s glob is non-recursive at the given path. This mission records the finding; it does not implement a change to make it true. | User Story 3 | Low | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Bounded file set (smallest-viable-diff) | Production change is confined to `src/charter/kind_vocabulary.py` (the ~5 LOC `_org_scan_dirs` body). Test changes are confined to `tests/charter/test_kind_vocabulary_scan_roots.py` (unit level, FR-003) plus one new or extended test module for the activation-filter-level regression (FR-002) — e.g. alongside `tests/charter/` coverage for `filter_graph_by_activation` / `_resolve_activated_urns_for_kind`. No other production file is touched. | Technical | High | Open |
| C-002 | No D1 production code | `src/charter/_drg_helpers.py` and any other code path implementing #3384's fix are read-only evidence sources for this mission. No commit in this mission changes `_drg_helpers.py`'s behavior or competes with the `org-pack-drg-root-graph-guard` mission's fix. | Technical | High | Open |
| C-003 | No opportunistic refactor of neighboring scan helpers | `_built_in_scan_dir` and `_layer_scan_dirs` (same file as `_org_scan_dirs`) are not modified, renamed, or restructured by this mission even though they sit in the touched file. | Technical | Medium | Open |
| C-004 | Red-first, not retry-to-green | FR-002's regression test must be shown red against the pre-fix code before the fix commit, per Standing Order #4 and `C-011`. A test authored already-green against the fix is not acceptable evidence. | Process | High | Open |
| C-005 | No new suppressions | `ruff` and `mypy --strict` stay clean on touched files; no new `# type: ignore` / `# noqa`. | Technical | High | Open |

### Key Entities

- **`_org_scan_dirs`** (`src/charter/kind_vocabulary.py:200-209`) — the function this mission
  fixes.
- **`_scan_roots`** (`:142-180`) — the caller that combines `_built_in_scan_dir` and
  `_org_scan_dirs` into the `(Path, bool)` list `_iter_artifact_paths` walks.
- **`resolve_artifact_urn`** (`:253+`) — resolves a config-stem ID to a canonical URN by walking
  `_scan_roots`'s output; raises `UnknownArtifactIdError` when nothing matches.
- **`_resolve_activated_urns_for_kind`** / **`_resolve_activated_urns_by_kind`**
  (`src/charter/drg.py:333-406`) — batch-resolve each kind's activated stems to URNs once per
  `filter_graph_by_activation` call; the `except UnknownArtifactIdError: continue` at `:379-380`
  is where an unresolvable org stem is swallowed.
- **`_node_is_activated`** (`src/charter/drg.py:409-475`) — the per-node gate whose step 3
  (`:467-473`) drops a node absent from the resolved-URN set.
- **`DoctrineService._org_dirs`** (`src/doctrine/service.py:47-55`) and
  **`BaseDoctrineRepository._load`** (`src/doctrine/base.py:356-373`) — the live loader this
  mission's fix brings `_org_scan_dirs` into agreement with.
- **`TestOrgScanDirsHelper`** (`tests/charter/test_kind_vocabulary_scan_roots.py:125-135`) — the
  existing unit test class that currently pins the phantom-layout-only behavior and must be
  extended (FR-003).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The FR-002 regression test, run against the `planning_base_branch` commit
  (`main` @ `ab0a0b9b5` or later unfixed state), fails; run against the mission head with the
  FR-001 fix applied, passes. Both runs are recorded.
- **SC-002**: `charter activate directive <org-directive-stem>` — the org directive's **own**
  config-stem — (or the programmatic `plan_activation`/`commit_activation` equivalent), run
  against a fixture project with a flat-layout org pack (including a root-level `*.graph.yaml`
  declaring the org directive as a DRG node) registered as an org root, leaves that org-pack
  directive node present in `filter_graph_by_activation`'s output graph — the loud, positive,
  checkable success signal named in User Story 1. This holds regardless of what else is
  activated alongside it (Acceptance Scenario 5); it does **not** hold when only an unrelated
  artifact is activated and the org stem itself never is.
- **SC-003**: `TestOrgScanDirsHelper` (FR-003) covers flat-only, legacy-only, both-present,
  neither-present, and same-config-stem-in-both-directories (precedence) cases and is green; the
  pre-existing `test_existing_org_built_in_dir_returned` case (legacy shape) still passes
  unmodified in behavior (still returns the legacy dir), only its assertion about what else is
  returned may change if a flat dir is also present in that fixture.
- **SC-004**: `ruff check` and `mypy --strict` are clean on `src/charter/kind_vocabulary.py` and
  every touched test file, with no new suppressions.
- **SC-005** *(contingent, tracked for a later pass, not gating this mission's completion)*: once
  #3384 merges, VC-001 and VC-002's findings are recorded (as a follow-up note, issue comment, or
  successor mission input) rather than lost.

## Out of Scope

- **Issue #3384 itself** (the org-graph root-`*.graph.yaml` requirement and its collapse-to-empty
  action-doctrine-bundle consequence). Owned by the `org-pack-drg-root-graph-guard` mission.
  This mission only reads `src/charter/_drg_helpers.py` and related loader code for evidence
  (Clarifications; C-002).
- **The typo/unknown-stem swallow** in `_resolve_activated_urns_for_kind`
  (`src/charter/drg.py:379-380`, `except UnknownArtifactIdError: continue`). A genuinely
  absent or misspelled activation stem will still be silently skipped after this fix — that is
  a separate, larger defect class (activation error-reporting generally, not org-pack scanning
  specifically) and is not addressed here (see Edge Cases).
- **Refactoring `_built_in_scan_dir` or `_layer_scan_dirs`.** Same file, not broken, deliberately
  left untouched per `RECONCILE_CHANGE_SCOPE_TENSIONS` (C-003).
- **Any change to the `activated_*` config-key computation** (`src/charter/pack_manager.py:126`)
  or to `_node_is_activated`'s gate logic (`src/charter/drg.py:409-475`) — both are cited as
  mechanism evidence, neither is modified; the defect is fully closed by making
  `_org_scan_dirs` find what is really on disk.
- **The per-artifact-ID gate's general selectivity.** Excluding any artifact — org, built-in, or
  project — that is not on an armed activation list is unchanged by this mission; it is a
  by-design property of `_node_is_activated` step 3 (`src/charter/drg.py:467-473`), not a defect
  being deferred — see Acceptance Scenario 5.

## Assumptions

- The live loader's flat `<org_root>/<plural>/` layout (`src/doctrine/service.py:47-55`,
  `src/doctrine/base.py:356-373`) and the pack-layout guide
  (`docs/guides/how-to/governance/create-an-org-doctrine-pack.md:58`) are the canonical,
  intended org-pack layout — not the `built-in/`-nested one `_org_scan_dirs` scans today. No
  real org pack in this codebase's fixtures or docs uses the `built-in/`-nested shape as its
  sole layout.
- The `(Path, bool)` recursive-flag contract already established by `_scan_roots` /
  `_iter_artifact_paths` (`src/charter/kind_vocabulary.py:142-250`) is the correct integration
  point; the fix adds entries to the list this contract already consumes, rather than
  introducing a new resolution path.
- A fixture org pack for FR-002/FR-003 can be constructed under `tmp_path` in the existing test
  style already used by `TestOrgScanDirsHelper` and neighboring `tests/charter/` tests — no new
  fixture infrastructure is required.
