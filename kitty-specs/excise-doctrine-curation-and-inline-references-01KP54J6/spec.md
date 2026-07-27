# Feature Specification: Excise Doctrine Curation and Inline References

**Mission ID**: `01KP54J6W03W8B05F3P2RDPS8S` (`mid8`: `01KP54J6`)
**Mission Slug**: `excise-doctrine-curation-and-inline-references-01KP54J6`
**Mission Type**: `software-dev`
**Target branch**: `main`
**Created**: 2026-04-14
**Parent EPIC**: [Priivacy-ai/spec-kitty#461](https://github.com/Priivacy-ai/spec-kitty/issues/461) — Charter as Synthesis & Doctrine Reference Graph
**Tracking issue**: [Priivacy-ai/spec-kitty#463](https://github.com/Priivacy-ai/spec-kitty/issues/463) — [Phase 1] Excise curation + remove inline references
**Related WP issues**: [#476](https://github.com/Priivacy-ai/spec-kitty/issues/476) (WP1.1), [#477](https://github.com/Priivacy-ai/spec-kitty/issues/477) (WP1.2), [#475](https://github.com/Priivacy-ai/spec-kitty/issues/475) (WP1.3)
**Guardrail reference**: [Priivacy-ai/spec-kitty#393](https://github.com/Priivacy-ai/spec-kitty/issues/393) — bulk-edit occurrence-classification pattern (landed)

---

## Problem Statement

Phase 0 of the Doctrine Reference Graph (DRG) rebuild landed in 2026-04 and produced a parity-safe `build_context_v2()` at `src/charter/context.py:495`, a DRG infrastructure package at `src/doctrine/drg/`, a merged-graph validator, and a graph asset at `src/doctrine/graph.yaml`. [PR #609](https://github.com/Priivacy-ai/spec-kitty/pull/609) closed the final Phase 0 parity gaps (live-path graph validation, state-management parity, directive filtering, action-guideline rendering).

Despite that, current `main` still carries the pre-DRG curation pipeline and inline-reference machinery alongside the new DRG surface:

- **Curation pipeline is still present but obsolete.** `src/doctrine/curation/` (engine, state, workflow), the `spec-kitty doctrine curate|promote|reset|status` CLI (`src/specify_cli/cli/commands/doctrine.py`), the curation candidate validator (`src/specify_cli/validators/doctrine_curation.py`), and the `_proposed/` artifact trees under `src/doctrine/{directives,tactics,procedures,styleguides,toolguides,paradigms}/_proposed/` all still exist. Ten proposed YAML artifacts remain.
- **Inline reference fields still live on shipped YAMLs.** Thirteen shipped artifacts (eight directives, three paradigms, two procedures) carry `tactic_refs:` inline. Three artifact schemas and their Pydantic models still declare `tactic_refs`, `paradigm_refs`, and `applies_to` as valid fields, so validators accept them even though the authoritative edges now live in `graph.yaml`.
- **`build_context_v2()` is parity-safe but orphaned.** The legacy `build_charter_context()` still drives five live call sites (`src/specify_cli/next/prompt_builder.py`, `src/specify_cli/cli/commands/charter.py`, `src/specify_cli/cli/commands/agent/workflow.py`, and the `src/charter/__init__.py` / `src/specify_cli/charter/` wrappers). `build_context_v2()` has zero callers. The graph-validation-on-live-path claim is true only because v2 is guarded internally, but v2 is not actually on the live path until the call-site flip happens.
- **`src/charter/reference_resolver.py` and `load_doctrine_catalog(include_proposed=...)` still exist.** They power the legacy transitive-reference resolution that Phase 0 replaced with the merged-graph walk, and they are still called from `src/charter/compiler.py` and `src/charter/resolver.py`.

The coexistence of both models is the root problem. It doubles maintenance cost, permits inline/edge drift (a change to `tactic_refs:` in a YAML will not appear in `graph.yaml` and vice versa), and keeps the legacy resolver, the legacy context builder, and the curation UX alive. [EPIC #461](https://github.com/Priivacy-ai/spec-kitty/issues/461) §10 and the Phase 1 tracking issue [#463](https://github.com/Priivacy-ai/spec-kitty/issues/463) have explicitly authorized excision — **no fallback, no backwards compatibility, just excise it**.

The risk of doing this sloppily is real. This is a broad rename/deletion/edit tranche across YAML data, Python sources, schemas, CLI surfaces, validators, and tests. The already-landed #393 guardrail pattern (explicit occurrence classification, category-aware include/exclude rules, mission-level occurrence map, verification-by-completeness rather than semantic-diff heroics) exists specifically to prevent the silent-breakage class of failure that a naive sed-based excision would produce. Phase 1 must apply that guardrail to every work package.

---

## Goals

- Delete every artifact of the legacy curation pipeline on `main` so the only remaining doctrine authoring model is "edit the shipped artifact + graph edge, no proposal staging."
- Delete every inline reference field (`tactic_refs`, `paradigm_refs`, `applies_to`) from shipped YAMLs, schemas, and models so that the only source of truth for doctrine relationships is `src/doctrine/graph.yaml` resolved through the DRG.
- Make `build_context_v2()` the sole context builder, retire `build_charter_context()`, and remove the transitive reference resolver, the `include_proposed` catalog flag, and every other carrier of the legacy model.
- Keep the runtime contract preserved (bootstrap vs compact, directive filtering, action guidelines) — Phase 0 already proved parity; Phase 1 simply makes v2 the live path.
- Apply the #393 bulk-edit guardrail at every work package boundary so the excision is verified by completeness (occurrence maps, category-aware include/exclude, post-edit inventory checks), not by hand-eyed diff review.

## Non-Goals

- **Not redesigning the DRG.** Phase 0 is the authoritative baseline. `graph.yaml`, the merged-graph validator, and the Pydantic models under `src/doctrine/drg/` are not reopened unless a concrete blocker surfaces in current `main`.
- **Not building the unified emergent bundle layout.** That is [Phase 2 / #464](https://github.com/Priivacy-ai/spec-kitty/issues/464). Charter bundle freshness semantics and reader wiring stay as they are today.
- **Not touching the Charter Synthesizer.** [Phase 3 / #465](https://github.com/Priivacy-ai/spec-kitty/issues/465) owns FR1 (charter-as-synthesis) and the interview/code-reading/URL-fetching adapters.
- **Not removing the `m_3_1_1_charter_rename.py` migration.** That migration is explicitly permitted to carry legacy `constitution` strings for historical upgrades. Legacy-`constitution`-in-live-code has already been excised.
- **Not adding a fallback, compatibility shim, deprecation warning, or dual-read mode.** Per the EPIC, the removal is hard.
- **Not reshaping test architecture.** Tests are deleted, rewritten, or updated in place; no new test-framework abstractions introduced.
- **Not building project-local DRG overlays or provenance sidecars.** Those are Phase 3 / Phase 7 concerns.

---

## User Scenarios & Testing

### Primary Users
The primary "users" of this tranche are **Spec Kitty contributors and downstream agent integrators** who read, author, or validate doctrine. Operators running `spec-kitty` as end users experience this transition indirectly: an upgrade to the post-Phase-1 release will cause `spec-kitty doctrine curate|promote|reset|status` to fail as unknown commands and any project-local artifact carrying inline `tactic_refs:` to fail validation.

### Scenario 1 — Contributor authoring a new directive
- **Given** Phase 1 has landed and a contributor wants to add a new shipped directive with a related tactic.
- **When** they create `src/doctrine/directives/NNN-<slug>.directive.yaml` and add the tactic linkage.
- **Then** they add an edge to `src/doctrine/graph.yaml` (e.g. `{from: "directive:NNN-...", to: "tactic:...", kind: "uses"}`) rather than adding a `tactic_refs:` list inside the YAML, and the artifact validator rejects any attempt to add a `tactic_refs:` key.

### Scenario 2 — Operator invoking the retired CLI
- **Given** a contributor or operator runs `spec-kitty doctrine curate` (or `promote`, `reset`, `status`) after upgrading to the post-Phase-1 release.
- **When** the CLI dispatches the command.
- **Then** the command is unknown — the `doctrine` Typer app is not registered — and the CLI prints the standard unknown-command error. No deprecation shim exists.

### Scenario 3 — Runtime context assembly
- **Given** an agent invokes any action that previously triggered `build_charter_context()` (`specify`, `plan`, `tasks`, `implement`, `review`, `accept`, bootstrap paths, next-step prompt building).
- **When** the charter context is assembled.
- **Then** `build_context_v2()` is the single code path that runs, merged-graph validation executes on the live path (unchanged from Phase 0), and output text matches Phase 0 parity semantics (bootstrap-vs-compact, directive filtering, action guidelines).

### Scenario 4 — Project overlay with a stale inline field
- **Given** a downstream project that never migrated its local doctrine overlay still carries a YAML with `applies_to:` or `tactic_refs:`.
- **When** `spec-kitty` loads that overlay.
- **Then** the per-kind validator raises a structured error that names the offending file, the forbidden field, and points to the graph-edge migration pattern. The loader does not silently ignore the field.

### Scenario 5 — Contributor running the test suite
- **Given** a contributor checks out `main` after Phase 1.
- **When** they run the full pytest suite.
- **Then** all curation tests are gone, the reference-resolver tests are gone, the parity tests between legacy and v2 context builders are gone (there is no longer a legacy to diff against), the remaining tests pass, and a new validator-rejection test suite covers the "no inline refs" contract end-to-end.

### Edge Cases
- **Project overlays that reference `_proposed/`** are not expected to exist in the wild (curation was never advertised for project use), but the catalog loader must fail loudly if a project layout mentions `_proposed/`.
- **A contributor attempts to add `tactic_refs:` back** to a shipped YAML in a future PR; CI runs validators that reject the file and the artifact compliance test suite fails.
- **A downstream repo has an `include_proposed=True` call site** in a non-`spec-kitty` fork; the parameter is gone, so their import breaks at load time. That is the intended outcome.
- **Graph has a dangling edge** after a contributor deletes an artifact without updating `graph.yaml`; the merged-graph validator already catches this (Phase 0), but Phase 1 must keep that path live.

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
| --- | --- | --- |
| FR-001 | The shipped source tree must contain zero `_proposed/` directories under `src/doctrine/` after Phase 1 lands. | Draft |
| FR-002 | The `src/doctrine/curation/` package must be deleted in its entirety (engine, state, workflow, README, examples, imports). | Draft |
| FR-003 | The `src/specify_cli/cli/commands/doctrine.py` module and its `doctrine` Typer registration in `src/specify_cli/cli/commands/__init__.py` must be removed, and invoking `spec-kitty doctrine <anything>` must return the standard "unknown command" error with no shim text. | Draft |
| FR-004 | `src/specify_cli/validators/doctrine_curation.py` must be deleted. | Draft |
| FR-005 | No shipped YAML under `src/doctrine/` (outside `_proposed/`, which is itself removed) may contain a `tactic_refs:`, `paradigm_refs:`, or `applies_to:` key. | Draft |
| FR-006 | Every artifact schema file (`src/doctrine/schemas/*.schema.yaml`) must be updated so `tactic_refs`, `paradigm_refs`, and `applies_to` are not declared as valid fields. | Draft |
| FR-007 | Every per-kind Pydantic artifact model (under `src/doctrine/<kind>/models.py` or equivalent) must be updated so `tactic_refs`, `paradigm_refs`, and `applies_to` are not declared as valid fields. | Draft |
| FR-008 | Every per-kind `validation.py` must reject an artifact YAML that contains `tactic_refs`, `paradigm_refs`, or `applies_to`, with a structured error naming the offending file and field. **For `procedure` specifically, the check must scan both top-level keys and every entry in `steps[*]` since `ProcedureStep.tactic_refs` is a declared Pydantic field on current `main`; the field is removed from the Pydantic model in WP02 and the pre-Pydantic rejection path is added in WP03 so the user gets a structured `InlineReferenceRejectedError` rather than a bare Pydantic `extra_forbidden` error.** | Draft |
| FR-009 | The charter module must expose exactly one context builder under the name `build_charter_context` — the implementation must be the current `build_context_v2()` semantics (DRG-merged-graph-driven, with parity state management, directive filtering, and action guidelines). Either `build_context_v2` is renamed to `build_charter_context` and the old implementation deleted, or `build_context_v2` stays under its name and a re-export under `build_charter_context` is removed — but the codebase must end with a single context builder, reachable by a single import path for each of the two `charter` packages (`src/charter/` and `src/specify_cli/charter/`). | Draft |
| FR-010 | `src/charter/reference_resolver.py` must be deleted, along with its imports and call sites in `src/charter/compiler.py` and `src/charter/resolver.py`. The affected compiler/resolver modules must be refactored to consume the DRG merged-graph walk instead (or deleted if they only existed to drive the legacy resolver). | Draft |
| FR-011 | `load_doctrine_catalog()` in `src/charter/catalog.py` must no longer accept an `include_proposed` parameter, and every call site must be updated to match. | Draft |
| FR-012 | Every skill, command template, README, and doctrine-package documentation file that references `doctrine curate`, `doctrine promote`, `doctrine reset`, `doctrine status`, `_proposed/`, `reference_resolver`, `include_proposed`, `tactic_refs`, `paradigm_refs`, or `applies_to` must be updated or removed. The SOURCE directory is `src/specify_cli/missions/*/command-templates/`, `src/specify_cli/skills/`, `src/doctrine/*/README.md`, and `src/charter/README.md`; agent copy directories under `.claude/`, `.codex/`, etc. are OUT OF SCOPE and will re-flow from the source on the next upgrade. | Draft |
| FR-013 | Every test under `tests/` that exercises a removed surface must be deleted or rewritten. Concretely: curation tests (`tests/doctrine/curation/**`, `tests/cross_cutting/test_doctrine_curation_unit.py`); the full `reference_resolver` dependency set (`tests/charter/test_reference_resolver.py`, `tests/doctrine/test_cycle_detection.py`, `tests/doctrine/test_shipped_doctrine_cycle_free.py` — each of which imports `resolve_references_transitively` or `_Walker` directly — plus the `_REF_TYPE_MAP` import in `tests/doctrine/test_artifact_kinds.py` and the `charter.resolver.resolve_references_transitively` patch site in `tests/charter/test_resolver.py:293` and the comment reference in `tests/charter/test_compiler.py:107`); legacy-vs-v2 artifact-reachability parity test (`tests/charter/test_context_parity.py`); and inline-field assertions inside artifact model tests. `tests/charter/test_context.py` must be rewritten against the new single context builder. Cycle-detection coverage (previously in `test_cycle_detection.py` and `test_shipped_doctrine_cycle_free.py`) is rehomed to a new `tests/doctrine/drg/test_shipped_graph_valid.py` that loads `src/doctrine/graph.yaml` and asserts `assert_valid(merge_layers(...))` passes — the DRG validator already implements cycle detection for the `requires` subgraph. | Draft |
| FR-014 | A new validator-rejection test suite must assert that loading a YAML fixture containing `tactic_refs`, `paradigm_refs`, or `applies_to` raises the structured rejection error, for each artifact kind. | Draft |
| FR-015 | Each work package must produce an **occurrence classification artifact** in the mission spec directory (`kitty-specs/<mission_slug>/occurrences/WP1.<n>.yaml`) that enumerates every string/path occurrence, classifies it into a category (import path, symbol name, YAML key, filesystem path literal, CLI command name, docstring/comment, skill/template reference, test identifier), and declares per-category include/exclude rules. Implementation must verify the WP is complete by proving the artifact's "to-change" set is now empty on disk (verification-by-completeness), not by reviewing diff semantics. | Draft |
| FR-016 | The merged-graph validator (`assert_valid()` in `src/doctrine/drg/validator.py`) must remain on the live path of the post-Phase-1 context builder with no change in behavior, and a regression test must assert it runs on every `build_charter_context()` invocation. | Draft |

### Non-Functional Requirements

| ID | Requirement | Measurable Threshold | Status |
| --- | --- | --- | --- |
| NFR-001 | Total runtime of the pytest suite on CI must not regress by more than 5% compared to the last green run on `main` before Phase 1 lands (measured as p50 over three consecutive CI runs on the pre- and post-Phase-1 commits). | ≤5% regression | Draft |
| NFR-002a | **Artifact-reachability parity** — the post-Phase-1 `build_charter_context()` must resolve the same artifact URN set for every (profile, action, depth) combination as the pre-WP03 baseline. This is the semantic contract currently exercised by `tests/charter/test_context_parity.py`. The rewritten `tests/charter/test_context.py` inherits this contract post-cutover. | 100% artifact-URN-set equality for every (profile, action, depth) case the parity suite exercises today | Draft |
| NFR-002b | **Rendered-text parity** — a mission-owned baseline capture (committed under `kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/baseline/pre-wp03-context.json`) records the exact JSON response of `spec-kitty charter context --action <act> --json` for each bootstrap action (`specify`, `plan`, `implement`, `review`) on the pre-WP03 `main`. After WP03 merges, the same command invocations must return byte-identical JSON. The baseline is captured by T018 before any cutover step begins in WP03. Note: no such golden set exists on `main` as of 2026-04-14 — `tests/charter/test_context_parity.py:7` documents that it tests reachability only, and `tests/charter/test_context_v2.py` uses inline synthetic fixtures. This mission creates the baseline. | Zero diff between pre-capture and post-cutover JSON across all four bootstrap actions | Draft |
| NFR-003 | Every work package must keep `mypy --strict` passing and test coverage on new or rewritten code at or above 90%, matching the project's charter baseline. | 0 type errors, ≥90% line coverage on changed files | Draft |
| NFR-004 | The post-Phase-1 shipped source tree must contain zero occurrences of the strings `curation`, `_proposed`, `tactic_refs`, `paradigm_refs`, `applies_to`, `reference_resolver`, `include_proposed`, and `build_context_v2`, verified by grep on the final diff. The `m_3_1_1_charter_rename.py` migration file and any explicitly carved-out test fixture paths are permitted exceptions and must be listed in the mission-level occurrence map. | 0 stray occurrences outside the permitted-exceptions list | Draft |

### Constraints

| ID | Constraint | Status |
| --- | --- | --- |
| C-001 | No fallback, no backwards compatibility, no deprecation shim, no dual-read mode — per [EPIC #461 §10](https://github.com/Priivacy-ai/spec-kitty/issues/461) and [Phase 1 issue #463](https://github.com/Priivacy-ai/spec-kitty/issues/463). | Active |
| C-002 | The #393 bulk-edit guardrail pattern (explicit occurrence classification, category-aware include/exclude, mission-level occurrence map, verification-by-completeness) is mandatory for every work package in this tranche. | Active |
| C-003 | GitHub issues (#461, #463, #476, #477, #475) are authoritative. Local planning documents under `spec-kitty-planning/product-ideas/` are reference only and may not override the issue text. | Active |
| C-004 | Phase 0 design (DRG schema, `graph.yaml`, merged-graph validator, `build_context_v2()` semantics) may not be reopened unless a concrete blocker is discovered and documented. | Active |
| C-005 | Only SOURCE templates under `src/specify_cli/missions/*/command-templates/` may be edited. Agent copy directories (`.claude/`, `.amazonq/`, `.augment/`, `.codex/`, `.cursor/`, `.gemini/`, `.github/prompts/`, `.kilocode/`, `.opencode/`, `.qwen/`, `.roo/`, `.windsurf/`) are generated copies and may not be hand-edited in this mission. | Active |
| C-006 | Migration module `src/specify_cli/upgrade/migrations/m_3_1_1_charter_rename.py` is explicitly permitted to retain `constitution` strings and is out of scope for this tranche. | Active |
| C-007 | Work packages must land in dependency order: WP1.1 (curation surface excision) → WP1.2 (inline-field removal from YAMLs + schemas + models) → WP1.3 (validators reject + single context builder + resolver/catalog excision). Each WP is merged behind its own PR, preflight-verified, and validated end-to-end before the next begins. | Active |

---

## Success Criteria

The Phase 1 tranche is complete when **all** of the following hold on post-merge `main`:

1. `find src/doctrine -type d -name _proposed` returns no directories.
2. `test -d src/doctrine/curation` returns non-zero.
3. `test -f src/specify_cli/cli/commands/doctrine.py` returns non-zero, and `spec-kitty doctrine curate` on a fresh checkout fails with the standard unknown-command error.
4. `grep -R "tactic_refs\|paradigm_refs\|applies_to" src/doctrine` returns zero hits outside explicit carve-outs documented in the mission-level occurrence map.
5. `grep -R "build_context_v2\|build_charter_context" src/` returns exactly one public name (the retained context builder), plus legitimate imports.
6. `grep -R "reference_resolver\|include_proposed\|resolve_references_transitively\|ResolvedReferenceGraph\|_REF_TYPE_MAP" src/ tests/` returns zero hits outside documented carve-outs.
7. The full pytest suite passes with the runtime regression budget in NFR-001 respected.
8. A validator-rejection test suite (FR-014) exists and passes for all seven artifact kinds.
9. The merged-graph validator runs on the live charter-context path (FR-016) and a regression test asserts it.
10. Each of WP1.1 / WP1.2 / WP1.3 has a committed occurrence-classification artifact at `kitty-specs/<mission_slug>/occurrences/WP1.<n>.yaml` and the "to-change" set in each is empty at merge.
11. The changelog entry for the release that ships this tranche explicitly documents the removed CLI commands, the removed inline fields, and the absence of a compatibility shim.

---

## Key Entities

- **Doctrine artifact YAML** — a file under `src/doctrine/<kind>/*.yaml` describing a directive, tactic, procedure, styleguide, toolguide, or paradigm. After Phase 1, carries no inline `tactic_refs` / `paradigm_refs` / `applies_to`; all cross-artifact relationships live on edges in `graph.yaml`.
- **Doctrine Reference Graph (DRG)** — the merged graph (shipped `graph.yaml` + project overlays) assembled by `src/doctrine/drg/`, validated by `assert_valid()`, and walked by the charter context builder. Phase 0 artifact; Phase 1 does not change it.
- **Charter context builder** — the single post-Phase-1 function that produces the action-scoped governance context text used by bootstrap, compact, and reference-doc reader paths. Previously two functions (`build_charter_context` legacy + `build_context_v2` new); Phase 1 collapses to one.
- **Occurrence classification artifact** — a work-package-scoped YAML at `kitty-specs/<mission_slug>/occurrences/WP1.<n>.yaml` enumerating every string occurrence touched by that WP, categorized, with include/exclude rules and completeness assertions. Mandated by #393 guardrail.
- **Mission-level occurrence map** — the aggregated index at `kitty-specs/<mission_slug>/occurrences/index.yaml` that lists every permitted-exception path, every category exclusion rationale, and every category that must end with zero occurrences. Review gate for mission acceptance.

---

## Implementation Plan (Work Package Shape)

This section is recommended shape for `/spec-kitty.plan` and `/spec-kitty.tasks`; it is **not** a pre-committed WP layout. It is derived directly from issue #463's acceptance gates and from the inventory produced during specify.

### WP1.1 — Excise the curation surface
**Tracking issue**: [#476](https://github.com/Priivacy-ai/spec-kitty/issues/476)

Delete, in one coherent PR:
- `src/doctrine/curation/` (entire package — engine.py, state.py, workflow.py, README.md, imports/)
- `src/specify_cli/validators/doctrine_curation.py`
- `src/specify_cli/cli/commands/doctrine.py` and its registration line in `src/specify_cli/cli/commands/__init__.py`
- All `_proposed/` directories under `src/doctrine/` (10 real YAMLs + .gitkeep placeholders)
- Curation tests: `tests/doctrine/curation/**`, `tests/cross_cutting/test_doctrine_curation_unit.py`
- Any skill / command template / README prose that names the `doctrine` CLI subcommands or `_proposed/` (SOURCE files only; agent copies re-flow on upgrade)

Occurrence classification at `occurrences/WP1.1.yaml` must enumerate these file paths and string occurrences across the eight categories from #393 (import path, symbol name, filesystem path literal, dict/YAML key, docstring/comment, log message, CLI command name, test identifier).

### WP1.2 — Remove inline reference fields from shipped artifacts, schemas, and models
**Tracking issue**: [#477](https://github.com/Priivacy-ai/spec-kitty/issues/477)

Depends on WP1.1 (cleaner blast radius; no `_proposed/` artifacts to confuse grep).

- Strip `tactic_refs:` from 13 shipped artifact YAMLs (8 directives, 3 paradigms, 2 procedures) — the complete list is inventoried in Category D of the specify discovery.
- Remove `tactic_refs`, `paradigm_refs`, and `applies_to` from:
  - `src/doctrine/schemas/directive.schema.yaml`
  - `src/doctrine/schemas/paradigm.schema.yaml`
  - `src/doctrine/schemas/procedure.schema.yaml`
  - Corresponding Pydantic models under `src/doctrine/<kind>/`
  - `src/charter/schemas.py` (strip `applies_to: list[str]` from `Directive`)
- Update any model test asserting these fields exist to match the new contract.

Occurrence classification at `occurrences/WP1.2.yaml` must enumerate every YAML key, schema definition, model field, and test assertion touching the three field names.

### WP1.3 — Validators reject, `build_context_v2` becomes the sole context builder, resolver and catalog plumbing removed
**Tracking issue**: [#475](https://github.com/Priivacy-ai/spec-kitty/issues/475)

Depends on WP1.2 (no valid artifact still carries the field on disk) and WP1.1 (no curation-era catalog plumbing to collide with).

- Update each per-kind `validation.py` to reject `tactic_refs`, `paradigm_refs`, `applies_to`.
- Add the FR-014 validator-rejection test suite — one negative fixture per artifact kind.
- Rename/re-export `build_context_v2` as `build_charter_context` (decide in plan: rename vs alias; the end state is "one name, one implementation, one import path per public charter module").
- Flip the five live `build_charter_context` call sites to the new single implementation. Delete the legacy implementation.
- Delete `src/charter/reference_resolver.py`, remove its imports from `src/charter/compiler.py` and `src/charter/resolver.py`, and refactor those modules (or delete them if they only existed to drive the legacy resolver).
- Delete `tests/charter/test_reference_resolver.py` and `tests/charter/test_context_parity.py`; rewrite `tests/charter/test_context.py` against the single builder.
- Remove `include_proposed` from `src/charter/catalog.py` and all callers.
- Add the FR-016 regression test asserting merged-graph validation runs on the live path.

Occurrence classification at `occurrences/WP1.3.yaml` must enumerate every call site, import, test, and docstring touching the three retired symbols (`build_context_v2`, `build_charter_context` old impl, `reference_resolver`, `include_proposed`), plus any mission template references.

### Sequencing note
WP1.1 → WP1.2 → WP1.3 is strict sequential. Parallelizing WP1.1 and WP1.2 is tempting but rejected: WP1.2's occurrence classification is materially cleaner once WP1.1 has removed the `_proposed/` trees and curation test fixtures that otherwise polute grep and inventory. WP1.3 strictly requires both predecessors because it cannot enforce the no-inline-ref validator contract on `main` while shipped YAMLs still violate it.

---

## Validation & Test Strategy

### Verification-by-completeness (per #393)

Every WP produces an occurrence-classification artifact. At merge time, the reviewer runs a scripted check that walks every category in the artifact and asserts the "to-change" set is empty on disk. This replaces hand-reviewed semantic diffs for the bulk-edit categories.

The mission-level occurrence map at `kitty-specs/<mission_slug>/occurrences/index.yaml` aggregates across WPs and declares the final "must be zero" set (per NFR-004):

```
curation, _proposed, tactic_refs, paradigm_refs, applies_to,
reference_resolver, include_proposed, build_context_v2
```

plus the permitted-exceptions list (the `m_3_1_1_charter_rename.py` migration, any deliberate test-fixture carveouts, and the renamed context builder's single valid import path).

### Automated test coverage

1. **Deletion assertions** — new tests under `tests/doctrine/test_phase1_excision.py` (or equivalent) assert `_proposed/` dirs are absent, curation modules are absent, `doctrine` Typer app is not registered, and `spec-kitty doctrine ...` exits with unknown-command.
2. **Validator rejection suite** — one negative fixture per artifact kind loading a YAML with each forbidden field; asserts the structured error shape (`filename`, `field`, migration hint).
3. **Live-path graph validation regression** — asserts `build_charter_context()` calls `assert_valid()` on every invocation (mock or spy).
4. **Context builder parity against Phase 0 golden set** — NFR-002: reuse the Phase 0 `build_context_v2` golden fixtures as the Phase 1 baseline for the retained builder.
5. **Coverage/type check** — `pytest --cov` enforces NFR-003; `mypy --strict` must pass on every WP PR.

### Manual validation (spot checks)

- On a fresh checkout of the post-Phase-1 commit, run `spec-kitty charter context --action specify --json` and compare the output to a pre-merge capture at parity equivalence.
- On a project-local overlay with a deliberately-poisoned artifact (inline `tactic_refs:`), confirm validator produces the expected error message and refuses to load.

### CI integration

- The mission-level occurrence map check runs as a non-skippable job in the WP PRs and in the final merge PR.
- The validator-rejection suite runs in the default pytest job.
- NFR-001 (runtime regression budget) is measured by comparing the `pytest --durations=0` summary from the pre-Phase-1 and post-Phase-1 CI runs; any run exceeding the 5% budget blocks merge.

---

## Assumptions

- `graph.yaml` on `main` already encodes every relationship currently expressed inline in shipped YAMLs. Phase 0's migration extractor was designed to guarantee this, and Phase 0 calibration tests passed. If a missed edge surfaces during WP1.2, it is in-scope to add the missing edge to `graph.yaml` and must be called out in the occurrence artifact as a carved-out remediation.
- `build_context_v2()` as shipped by PR #609 is truly parity-safe. The Phase 0 parity test suite (`test_context_v2.py` and the Phase 0 golden fixtures) is the authority. If a parity gap surfaces during WP1.3, it must be fixed inside v2 before the call-site flip (not in legacy).
- Downstream projects consuming `spec-kitty` as a library do not call `load_doctrine_catalog(include_proposed=True)` in production paths. The `spec-kitty` public API surface does not guarantee that parameter.
- The 13-file inventory of shipped YAMLs carrying `tactic_refs:` (and the 0-file inventory for `paradigm_refs:` / `applies_to:`) is exhaustive. WP1.2's occurrence classification must re-verify this before editing.
- The five `build_charter_context()` call-site set enumerated in specify discovery is exhaustive. WP1.3's occurrence classification must re-verify this.
- Legacy module files that exist only to drive the reference resolver (`src/charter/compiler.py`, `src/charter/resolver.py`) may shrink dramatically or disappear in WP1.3. The plan phase will decide whether they are refactored or deleted based on what functionality — if any — survives the resolver excision.
- The #393 guardrail occurrence-classification section in `src/specify_cli/missions/software-dev/command-templates/implement.md` is the authoritative template for the per-WP occurrence artifact shape; the mission inherits it directly and does not redefine the contract.
- The retrospective-facilitator profile and FR4 post-mission retrospective contract are Phase 6 work and do not gate Phase 1 acceptance. This mission's retrospective (if any) is informal.

---

## Out of Scope (Deferred to Phase 2+)

- Unified emergent bundle layout and reader chokepoint (Phase 2, #464)
- Charter Synthesizer pipeline and FR1 implementation (Phase 3, #465)
- Profile-as-entry-point CLI and host-LLM advise/execute (Phase 4, #466)
- Glossary-as-DRG + chokepoint + dashboard tile (Phase 5, #467)
- Mission rewrite and retrospective contract (Phase 6, #468)
- Schema versioning and provenance hardening (Phase 7, #469)
- Karpathy wiki pattern follow-ups (#532, #533, #534, #535)
- Any restructuring of `src/doctrine/drg/` or `graph.yaml` beyond the minimum needed to keep the merged-graph walk live

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| A shipped YAML carries a relationship via inline `tactic_refs:` that has no corresponding edge in `graph.yaml`; WP1.2's deletion silently drops the relationship. | Medium | High (governance drift) | WP1.2 pre-flight: diff every inline ref against `graph.yaml`; any missing edge is added to `graph.yaml` in the same WP before the strip. |
| The five-site `build_charter_context()` inventory is incomplete; a dynamic import or string-based loader keeps the legacy function alive in production. | Low | High (runtime break) | WP1.3 occurrence artifact must include a grep across all of `src/` for any stringly-typed reference to the legacy name; symbol-level grep plus text grep plus Python AST walk. |
| `src/charter/compiler.py` or `src/charter/resolver.py` carry logic beyond reference resolution that the mission inadvertently deletes. | Medium | Medium (feature loss) | Plan-phase decision on rewrite-vs-delete must be backed by an explicit functional audit; WP1.3 spec must call out every non-resolver behavior found. |
| Per-kind validators diverge during the reject-inline-refs rewrite (one kind rejects, another silently allows). | Medium | Medium (validation inconsistency) | FR-014 test suite requires one negative fixture per kind; CI treats missing coverage as blocking. |
| Test-file deletion cascade breaks an unrelated test that happened to import from the deleted modules. | Medium | Low (red CI, fast to fix) | WP-level CI runs the full test suite before merge; the occurrence map includes "tests whose imports must be re-pointed." |
| The NFR-001 runtime budget is breached because validator-rejection fixtures slow down pytest startup. | Low | Low | Run fixture loading lazily; if breached, reshape the suite rather than relax the budget. |
| A PR review bypass lands WP1.2 before WP1.1, leaving stale curation plumbing that references inline fields that no longer exist. | Low | Medium (broken `main`) | The mission plan enforces sequencing; the orchestrator (`/spec-kitty.implement`) runs WPs in dependency order; branch protection on `main` requires the tracking issue checkboxes to advance in order. |

---

## Likely File Clusters

For plan-phase sizing. Paths are relative to repo root.

**Curation surface (WP1.1)**
- `src/doctrine/curation/` (entire tree)
- `src/doctrine/directives/_proposed/` (5 YAMLs + .gitkeep)
- `src/doctrine/tactics/_proposed/` (5 YAMLs + .gitkeep)
- `src/doctrine/{procedures,styleguides,toolguides,paradigms}/_proposed/` (empty dirs + .gitkeep)
- `src/specify_cli/cli/commands/doctrine.py`
- `src/specify_cli/cli/commands/__init__.py` (remove registration line only)
- `src/specify_cli/validators/doctrine_curation.py`
- `tests/doctrine/curation/**`
- `tests/cross_cutting/test_doctrine_curation_unit.py`

**Inline-field cluster (WP1.2)**
- `src/doctrine/directives/*.directive.yaml` (8 files with `tactic_refs:`)
- `src/doctrine/paradigms/*.paradigm.yaml` (3 files with `tactic_refs:`)
- `src/doctrine/procedures/*.procedure.yaml` (2 files with `tactic_refs:` — may also have step-level `tactic_refs:` inside `steps[*]`; both top-level and step-level are stripped)
- `src/doctrine/schemas/{directive,paradigm,procedure}.schema.yaml`
- `src/doctrine/<kind>/models.py` (Pydantic model per kind; **for procedures this specifically includes `ProcedureStep.tactic_refs: list[str]` on current `main` at line 54 — that field declaration is removed in WP1.2 so `extra="forbid"` on `ProcedureStep` subsequently rejects any residual step-level `tactic_refs:` at Pydantic-parse time, and WP1.3 adds the pre-Pydantic structured-error scan on top for a clearer error message**)
- `src/charter/schemas.py` (strip `applies_to`)
- `tests/doctrine/<kind>/test_models.py` (7 files)
- `tests/doctrine/test_artifact_compliance.py`, `tests/doctrine/test_enriched_directives.py`, `tests/doctrine/test_directive_consistency.py`, `tests/doctrine/test_procedure_consistency.py`, `tests/doctrine/test_tactic_compliance.py`

**Validator / context / resolver cluster (WP1.3)** — expanded after 2026-04-14 internal review
- `src/doctrine/{directives,tactics,procedures,styleguides,toolguides,paradigms,agent_profiles}/validation.py` (7 files)
- `src/doctrine/shared/errors.py` (ADD `InlineReferenceRejectedError`)
- `src/doctrine/drg/query.py` (ADD `resolve_transitive_refs` + `ResolveTransitiveRefsResult`)
- `src/charter/_drg_helpers.py` (NEW — `_load_validated_graph`)
- `src/specify_cli/charter/_drg_helpers.py` (NEW twin)
- `src/charter/context.py` (collapse to single builder)
- `src/charter/__init__.py` + `src/specify_cli/charter/__init__.py` (exports)
- `src/charter/reference_resolver.py` (DELETE)
- `src/charter/compiler.py` + `src/charter/resolver.py` (swap resolver import; do NOT delete)
- `src/charter/catalog.py` (drop `include_proposed`)
- `src/specify_cli/next/prompt_builder.py`, `src/specify_cli/cli/commands/charter.py`, `src/specify_cli/cli/commands/agent/workflow.py`, `src/specify_cli/charter/context.py`, `src/specify_cli/runtime/doctor.py` (call-site flip)
- `tests/charter/test_context.py` (REWRITE — inherits NFR-002a artifact-reachability parity contract)
- `tests/charter/test_merged_graph_on_live_path.py` (NEW — FR-016 regression)
- `tests/doctrine/drg/test_resolve_transitive_refs.py` (NEW — contract coverage + behavioral equivalence)
- `tests/doctrine/drg/test_shipped_graph_valid.py` (NEW — rehome target for cycle-detection coverage)
- `tests/doctrine/test_inline_ref_rejection.py` (NEW — 7 kinds including procedures step-level)
- `tests/charter/test_context_parity.py` (DELETE — only after rewritten `test_context.py` inherits contract)
- `tests/charter/test_reference_resolver.py` (DELETE)
- `tests/doctrine/test_cycle_detection.py` (DELETE — coverage rehomed to `test_shipped_graph_valid.py`)
- `tests/doctrine/test_shipped_doctrine_cycle_free.py` (DELETE — coverage rehomed)
- `tests/doctrine/test_artifact_kinds.py` (UPDATE — replace private `_REF_TYPE_MAP` imports with `doctrine.artifact_kinds.ArtifactKind` public enum)
- `tests/charter/test_resolver.py` (UPDATE — patch-target change at line 293)
- `tests/charter/test_compiler.py` (UPDATE — comment reference at line 107)
- `tests/agent/test_workflow_charter_context.py` (UPDATE — single-builder name)
- `tests/doctrine/drg/migration/test_extractor.py` (possibly update — migration code is Phase 0, but extractor fixtures may reference removed fields)
- `kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/baseline/pre-wp03-context.json` (NEW — NFR-002b rendered-text baseline captured at WP03 start)

---

## References

- EPIC [Priivacy-ai/spec-kitty#461](https://github.com/Priivacy-ai/spec-kitty/issues/461) — Charter as Synthesis & Doctrine Reference Graph
- Phase 1 tracking [Priivacy-ai/spec-kitty#463](https://github.com/Priivacy-ai/spec-kitty/issues/463)
- WP tracking: [#476 (WP1.1)](https://github.com/Priivacy-ai/spec-kitty/issues/476), [#477 (WP1.2)](https://github.com/Priivacy-ai/spec-kitty/issues/477), [#475 (WP1.3)](https://github.com/Priivacy-ai/spec-kitty/issues/475)
- Bulk-edit guardrail [Priivacy-ai/spec-kitty#393](https://github.com/Priivacy-ai/spec-kitty/issues/393) (closed; pattern landed)
- Phase 0 closeout PR [Priivacy-ai/spec-kitty#609](https://github.com/Priivacy-ai/spec-kitty/pull/609) — `build_context_v2()` parity and merged-graph validation
- Bundle freshness PR [Priivacy-ai/spec-kitty#605](https://github.com/Priivacy-ai/spec-kitty/pull/605) — `ensure_charter_bundle_fresh()`
- Charter architecture doc: `spec-kitty-planning/product-ideas/architecture-charter-as-synthesis-and-doctrine-reference-graph-v1-2026-04-07.md` (reference only; authoritative text is the GitHub issues)
