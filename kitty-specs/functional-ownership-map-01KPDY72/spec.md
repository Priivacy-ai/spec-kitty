# Functional Ownership Map

**Mission ID**: `01KPDY72HV348TA2ERN9S1WM91`
**Mission slug**: `functional-ownership-map-01KPDY72`
**Mission type**: `software-dev`
**Change mode**: `standard` (new architecture artefact + limited code removal; no cross-file same-string rewrite)
**Target branch**: `main`
**Created**: 2026-04-17
**Trackers**: [#610 — Functional ownership map for `src/specify_cli/*`](https://github.com/Priivacy-ai/spec-kitty/issues/610), [#611 — Remove `specify_cli.charter` deprecation shim (rolled in)](https://github.com/Priivacy-ai/spec-kitty/issues/611)
**Umbrella epic**: [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461)
**Downstream dependents**: #612 (runtime extraction), #613 (glossary extraction), #614 (lifecycle extraction), #615 (migration/shim rules)

---

## Primary Intent

`src/specify_cli/` currently commingles four responsibilities: (1) CLI routing and presentation, (2) domain logic, (3) legacy bridge/compatibility surfaces, (4) integration adapters. The charter slice (completed by mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880`) established the extraction pattern: canonical implementation in a top-level package, thin re-export shim in `src/specify_cli/` with an explicit removal release.

This mission produces the **canonical functional ownership map** for every remaining major slice of `src/specify_cli/`. The map is the normative architectural artefact that every subsequent extraction PR (#612, #613, #614, and the model-discipline doctrine port) will cite. It is not itself an extraction of any new slice.

Scope was expanded during discovery to absorb issue **#611** (removal of the `specify_cli.charter` deprecation shim). That removal keeps the ownership map honest: the charter slice entry reads as *fully consolidated* rather than *mid-transition* at the time the map lands. The mission does **not** bump the project version — the 3.3.0 release cut is left to the upstream maintainers.

The mission additionally publishes a **machine-readable ownership manifest** (YAML) alongside the Markdown map so downstream tooling (CI checks, the shim registry in #615, future scripts) can enumerate slice ownership without parsing prose.

---

## User Scenarios & Testing

### Primary actors

- **Spec Kitty contributors authoring future extraction PRs** — consume the map to know target package paths, dependency rules, and shim contracts.
- **Spec Kitty maintainers / reviewers** — use the map to reject PRs that reintroduce cross-slice shortcuts or place code in the wrong package.
- **Tooling authors (CI, release scripts, #615 shim registry)** — consume the machine-readable manifest.
- **Downstream contributors and external Python importers of `specify_cli.charter.*`** — must be informed that the shim is gone and the canonical import is `charter.*`.

### Acceptance scenarios

1. **Extraction PR author locates target ownership**
   - **Given** a contributor preparing the runtime-extraction PR (#612)
   - **When** they consult the ownership map
   - **Then** they find a slice entry for runtime with: current-state file list, canonical owner package name, enumerated adapter responsibilities that legitimately stay in `specify_cli`, shim contract (referencing #615 rules once that mission lands), cross-slice seams, and runtime-specific dependency rules.

2. **Reviewer validates an extraction PR against the map**
   - **Given** a PR claims to extract a slice per the map
   - **When** the reviewer checks the PR against the slice entry
   - **Then** every bullet in the slice entry can be ticked off or is explicitly deferred with a tracker reference; no bullet is silently skipped.

3. **Doctrine `model_task_routing` has a resolved posture**
   - **Given** a contributor opens `src/doctrine/model_task_routing/`
   - **When** they consult the doctrine slice entry in the ownership map
   - **Then** the map documents `model_task_routing` as a **specialization** under an existing doctrine kind (not a first-class kind peer of tactic/directive/toolguide), names the parent kind, and records the reasoning.

4. **Charter slice reads as fully consolidated**
   - **Given** the map lands together with the #611 shim removal
   - **When** a reader looks at the charter slice entry
   - **Then** current state = canonical (`src/charter/`), `specify_cli/charter/` is absent from the tree, and there is no "mid-transition" framing. The entry is explicitly labelled as the reference exemplar for other slices.

5. **`specify_cli.charter` shim is gone**
   - **Given** the mission has landed
   - **When** a user runs `python -c "import specify_cli.charter"`
   - **Then** the import fails with `ModuleNotFoundError` (not a `DeprecationWarning`). `CHANGELOG.md` contains an entry under the *Unreleased* heading noting the removal and pointing users at `charter`.

6. **Machine-readable manifest is parseable and complete**
   - **Given** the manifest at `architecture/2.x/05_ownership_manifest.yaml`
   - **When** a tool parses it
   - **Then** it enumerates all eight slices by canonical key, with fields: `canonical_package`, `current_state`, `adapter_responsibilities`, `shims[]`, `seams[]`, `extraction_sequencing_notes`, and (for the runtime slice) `dependency_rules`. Schema is validated by a test.

7. **Cross-reference from implementation mapping works**
   - **Given** a reader lands on `architecture/2.x/04_implementation_mapping/README.md`
   - **When** they ask "where does slice X live today and where is it going?"
   - **Then** the implementation mapping doc links prominently to the ownership map and the reader can navigate from general guidance to slice-specific ownership in one hop.

8. **Safeguard references point to real artefacts**
   - **Given** the map references issues #393 (architectural tests), #394 (deprecation scaffolding), #395 (import-graph tooling), and #461 (direction)
   - **When** a reader follows those references
   - **Then** each reference resolves to the expected tracker and the map explains which safeguards must be in place before the corresponding slice extracts.

### Edge cases

- A slice whose current boundary is ambiguous (e.g., lifecycle/status code partially under `specify_cli/status` and partially duplicated elsewhere). Resolution: the map documents the current fragmented state factually, then commits to a single canonical target.
- An external Python importer of `specify_cli.charter.*` who did not migrate in the 3.1.x window. Resolution: removal is preceded by a CHANGELOG entry and the deprecation warning that has already shipped since 3.1.0; no extra grace window.
- Slices where the canonical package path is legitimately contested. Resolution: the map picks one path and records a short rationale; paths are not left open.
- A post-mission PR that proposes altering the map. Resolution: the map is a living document; future changes edit it in place and each extraction PR confirms the slice entry it lands under.

---

## Requirements

### Functional Requirements

| ID      | Requirement                                                                                                                                                                                                                  | Status    |
|---------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| FR-001  | The mission produces one authoritative ownership map document at `architecture/2.x/05_ownership_map.md`.                                                                                                                     | Confirmed |
| FR-002  | The map contains a dedicated section for each of the eight functional slices: CLI shell, charter/governance, doctrine, runtime/mission execution, glossary, lifecycle/status, orchestrator/sync/tracker/SaaS, migration/versioning. | Confirmed |
| FR-003  | Each slice section records: current state (primary files), canonical owner package, enumerated adapter responsibilities that remain in `specify_cli`, shim inventory (if any), cross-slice seams, and extraction sequencing notes. | Confirmed |
| FR-004  | The runtime slice section additionally specifies dependency rules: what runtime may call and what may call into runtime.                                                                                                      | Confirmed |
| FR-005  | The doctrine slice section records the disposition of `src/doctrine/model_task_routing/` as a **specialization** under an existing doctrine kind and names the parent kind.                                                   | Confirmed |
| FR-006  | The charter slice section uses the `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` mission as the reference exemplar pattern that other slices follow.                                                    | Confirmed |
| FR-007  | The map is cross-referenced from `architecture/2.x/04_implementation_mapping/README.md` so readers navigating that doc are directed to the ownership map for slice-level questions.                                          | Confirmed |
| FR-008  | The map references the enabling safeguards tracked in #393, #394, and #395 and explains which safeguards must be in place before each slice extracts.                                                                         | Confirmed |
| FR-009  | The map explicitly notes how the extraction series supports the direction in #461.                                                                                                                                             | Confirmed |
| FR-010  | The mission publishes a machine-readable ownership manifest at `architecture/2.x/05_ownership_manifest.yaml` that enumerates all eight slices with canonical_package, current_state, adapter_responsibilities, shims, seams, extraction_sequencing_notes, and (for runtime) dependency_rules.     | Confirmed |
| FR-011  | A schema validation test asserts the manifest is parseable and every slice contains the required fields.                                                                                                                       | Confirmed |
| FR-012  | The mission deletes `src/specify_cli/charter/` (all files in that directory) and removes any test-fixture or lint exceptions scoped to that shim (the three C-005 exceptions documented in mission `01KPD880`).             | Confirmed |
| FR-013  | `CHANGELOG.md` gains an *Unreleased* entry under "Removed" describing the `specify_cli.charter` shim deletion and pointing users at the `charter` canonical package.                                                           | Confirmed |
| FR-014  | Issue #611 is closed as part of this mission's merge commit (referenced in the commit message with `Closes #611`).                                                                                                             | Confirmed |
| FR-015  | No other slice code is moved, renamed, or extracted by this mission.                                                                                                                                                          | Confirmed |

### Non-Functional Requirements

| ID       | Requirement                                                                                                                                                                                         | Status    |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| NFR-001  | The ownership map is readable end-to-end by a new contributor in ≤20 minutes (enforced via peer review during `/spec-kitty.review`, not automated).                                                  | Confirmed |
| NFR-002  | The machine-readable manifest validates against its documented schema in the unit test in ≤1 second.                                                                                                 | Confirmed |
| NFR-003  | Existing test suite continues to pass with zero regressions; the shim removal introduces zero test-fixture exceptions (previously three existed for C-005 — those are deleted, not replaced).        | Confirmed |
| NFR-004  | Post-merge, `import specify_cli.charter` raises `ModuleNotFoundError` within the normal Python import resolution time (<100 ms on a warm interpreter).                                               | Confirmed |

### Constraints

| ID     | Constraint                                                                                                                                                                                      | Status    |
|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| C-001  | ~~The mission does **not** bump the project version. `pyproject.toml` `version = "3.1.6"` is untouched.~~ **Revised per reviewer feedback (PR #683)**: version bumped to `3.2.0` to align the shim removal with the deprecation contract that promised removal "in a future release". The 3.3.0 reference in the original shim `__removal_release__` was aspirational; the actual removal ships in this PR as 3.2.0. | Revised |
| C-002  | The mission does **not** move or extract any slice beyond the `specify_cli.charter` shim deletion. Runtime, glossary, lifecycle, and orchestrator code stay exactly where they are today.         | Confirmed |
| C-003  | The mission does **not** implement the #615 shim rulebook or registry — it only references that follow-up as the governing artefact for future shim lifecycles.                                   | Confirmed |
| C-004  | The mission does **not** implement the model-discipline doctrine port — it only decides the disposition of `model_task_routing` in the map.                                                       | Confirmed |
| C-005  | The map must align with the canonical terminology: **Mission** (not "feature"), **Work Package** (not "task"), per the repository's terminology canon in `AGENTS.md`.                               | Confirmed |
| C-006  | The mission runs under `change_mode: standard`; no cross-file same-string rewrite is performed (the `specify_cli.charter` shim is already fully re-exporting and has no live internal call sites to migrate). | Confirmed |

---

## Success Criteria

Measurable, technology-agnostic outcomes:

1. **Map completeness** — All eight functional slices each have a complete ownership section containing every required sub-field; zero missing sections measurable by a checklist walkthrough during `/spec-kitty.review`.
2. **Machine-readable manifest coverage** — The YAML manifest parses cleanly and enumerates all eight slices; the schema test passes deterministically in CI.
3. **Charter shim removal** — `import specify_cli.charter` raises `ModuleNotFoundError`; `CHANGELOG.md` contains the removal entry; `CLOSES #611` appears in the merge commit.
4. **Cross-reference integrity** — Every external tracker referenced in the map (`#393`, `#394`, `#395`, `#461`, `#612`, `#613`, `#614`, `#615`) resolves to the intended issue; every internal doc referenced (`architecture/2.x/04_implementation_mapping/README.md`) exists and in turn links back to the ownership map.
5. **Zero regression** — 100% of existing tests pass unchanged; zero new test-fixture exceptions introduced; the three prior C-005 exceptions for the charter shim are deleted.
6. **Downstream actionability** — Missions #612, #613, #614, and the doctrine port can start their own `/spec-kitty.plan` phases by citing specific ownership-map slice entries; validated by confirming #612 and #613 draft specs in `work/mission-drafts/` already reference this map as a direct prerequisite.

---

## Key Entities

- **Functional slice** — a named responsibility area of the codebase (CLI shell, charter, doctrine, runtime, glossary, lifecycle, orchestrator, migration).
- **Canonical owner package** — the top-level Python package that owns a slice's real implementation (e.g., `charter/`, `src/runtime/` TBD).
- **Adapter responsibility** — CLI-only work (routing, argument parsing, Rich rendering, exit-code mapping) that legitimately remains in `src/specify_cli/` after extraction.
- **Compatibility shim** — a legacy re-export module under `src/specify_cli/*` that preserves external import paths, with `__deprecated__`, `__canonical_import__`, and `__removal_release__` attributes.
- **Slice seam** — a defined interaction point between two slices, documented in the map (e.g., runtime reads charter context through `build_charter_context()`).
- **Dependency rule** (runtime-specific) — a constraint on which slices runtime may call, and which slices may call into runtime.
- **Ownership manifest entry** — a single YAML record under the machine-readable manifest, keyed by slice name.

---

## Dependencies & Assumptions

### Upstream (must land before this mission starts)

- None. Mission is standalone on `main` at 3.1.6.

### Downstream (depend on this mission)

- **#615** (migration/shim ownership rules) — consumes the slice-by-slice shim inventory.
- **#612** (runtime extraction) — consumes the runtime slice entry and dependency rules.
- **#613** (glossary extraction) — consumes the glossary slice entry.
- **#614** (lifecycle/status extraction) — consumes the lifecycle slice entry.
- **Model-discipline doctrine port** — consumes the doctrine slice entry's `model_task_routing` disposition.

### Assumptions

- A1. The eight-slice taxonomy in issue #610 is sufficient; no ninth slice is needed. If plan-phase investigation surfaces a missed responsibility area, it is added as a ninth slice entry.
- A2. The `architecture/2.x/` directory is the correct home for this artefact (existing series already contains `04_implementation_mapping/`).
- A3. Deleting `src/specify_cli/charter/` does not break any currently-shipped CI job or release script. A plan-phase grep confirms this.
- A4. The prior `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` mission is already merged; its PR description is available as reference material for the exemplar section of the map.

---

## Out of Scope

- Any actual extraction of runtime, glossary, lifecycle, or orchestrator slices (that's #612, #613, #614).
- Authoring the shim registry YAML itself (that's #615 — this mission references the registry as the target artefact but does not create it).
- The model-discipline doctrine port.
- The brownfield-investigation skill design (#666) — unrelated to ownership.
- Any version bump in `pyproject.toml` or release automation change.
- Renaming canonical packages that already exist (`charter/`, `doctrine/`, etc.).

---

## Open Questions

None at spec time. Three decisions are pinned in this spec:

- Ownership map path: `architecture/2.x/05_ownership_map.md` (FR-001).
- Machine-readable manifest: required, at `architecture/2.x/05_ownership_manifest.yaml` (FR-010, FR-011).
- `model_task_routing` posture: **specialization** (FR-005). Plan phase documents the parent kind and reasoning.

Plan-phase will additionally determine:

- The concrete canonical package names for slices where the name is not already established (runtime, lifecycle).
- The parent doctrine kind under which `model_task_routing` is recorded as a specialization.
