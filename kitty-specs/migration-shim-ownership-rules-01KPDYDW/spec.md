# Migration and Shim Ownership Rules

**Mission ID**: `01KPDYDWVF8W838HNJK7FC3S7T`
**Mission slug**: `migration-shim-ownership-rules-01KPDYDW`
**Mission type**: `software-dev`
**Change mode**: `standard` (new rulebook + registry file + CI enforcement code; no cross-file same-string rewrite)
**Target branch**: `main`
**Created**: 2026-04-17
**Trackers**: [#615 — Centralize migration/compat ownership rules](https://github.com/Priivacy-ai/spec-kitty/issues/615)
**Umbrella epic**: [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461)
**Upstream dependency**: Mission `functional-ownership-map-01KPDY72` (#610) merged.
**Downstream dependents**: #612 (runtime extraction), #613 (glossary extraction), #614 (lifecycle extraction), model-discipline doctrine port.

---

## Primary Intent

Every slice extracted under the #610 ownership map will repeat the same pattern the charter slice used in mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880`: canonical implementation in a top-level package, thin re-export shim in `src/specify_cli/` with `__deprecated__`/`__canonical_import__`/`__removal_release__` attributes, a `DeprecationWarning` on import, a one-release deprecation window, and removal in the next minor release.

Without a shared rulebook, future extractions will reinvent these decisions ad hoc, shim metadata will drift, and removal targets will be forgotten. This mission writes the rulebook so #612, #613, #614, and the doctrine port each follow an identical, auditable pattern.

The mission also commits a **machine-readable shim registry** (`architecture/2.x/shim-registry.yaml`) and a **CI enforcement check** (`spec-kitty doctor shim-registry`) that fails when a registered shim's `__removal_release__` has been reached but the shim still exists on disk. With the registry and enforcement in place, "is it safe to remove this shim?" becomes a deterministic machine question rather than a human-archaeology exercise.

This mission writes rules, registry, and enforcement. It does **not** add, modify, or remove any live shim. Existing pre-#615 shims that do not match the rules get **grandfathered** in the registry with an explicit `grandfathered: true` flag and a rationale.

---

## User Scenarios & Testing

### Primary actors

- **Authors of future extraction PRs** (#612 runtime, #613 glossary, #614 lifecycle, doctrine port) — consume the rulebook to know how to shape their shim and migration artefacts.
- **Reviewers of extraction PRs** — validate that PRs conform to the rulebook and that new shims land in the registry.
- **Release managers** — consume the registry and CI check to answer "which shims are safe to delete in the next release?"
- **CI** — runs the enforcement check and fails builds when a shim's removal release has shipped but the shim is still present.
- **External downstream Python importers** of any deprecated `specify_cli.*` surface — benefit from a predictable, uniform deprecation contract.

### Acceptance scenarios

1. **Future extraction author consults the rulebook**
   - **Given** a contributor starting the #612 runtime extraction
   - **When** they open `architecture/2.x/06_migration_and_shim_rules.md`
   - **Then** they find: canonical shim module shape, required module attributes, `DeprecationWarning` emission rules, one-release deprecation window, removal-PR contract, registry-update instructions, and a worked example referencing the charter mission.

2. **Registry gains an entry per new shim**
   - **Given** the runtime extraction PR introduces `src/specify_cli/next/` as a re-export shim pointing to `src/runtime/`
   - **When** the PR lands
   - **Then** `architecture/2.x/shim-registry.yaml` contains a new entry with `legacy_path`, `canonical_import`, `introduced_in_release`, `removal_target_release`, `tracker_issue`, and `grandfathered: false`. The shim module attributes agree with the registry entry.

3. **CI blocks overdue removals**
   - **Given** a shim registered with `removal_target_release: 3.3.0` and the project version is `3.3.0`
   - **When** CI runs `spec-kitty doctor shim-registry`
   - **Then** the check fails with a clear message identifying the overdue shim and directing the contributor to either delete the shim or extend the removal target release (with justification).

4. **CI passes when shim is within window**
   - **Given** a shim registered with `removal_target_release: 3.4.0` and the project version is `3.3.0`
   - **When** CI runs the check
   - **Then** the check passes and the output lists the shim as pending removal in 3.4.0.

5. **Grandfathered shims do not falsely trip the check**
   - **Given** a pre-#615 shim that does not fully match the rulebook and is flagged `grandfathered: true` with a rationale
   - **When** CI runs the check
   - **Then** the check passes for that entry but emits a non-fatal advisory naming the shim and its grandfathered status. A separate check asserts that no new `grandfathered: true` entries are added after this mission lands.

6. **Rulebook aligns with existing schema-version enforcement**
   - **Given** the rulebook section on project schema/version gating
   - **When** a reviewer cross-references the existing doctrine/charter schema-version code paths
   - **Then** the rulebook accurately describes the current schema-version contract and names the tracker (`#461` Phase 7 doctrine versioning) where gaps will be closed.

7. **Charter mission is cited as the reference instance**
   - **Given** the rulebook's worked example section
   - **When** a reader reviews it
   - **Then** mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` is cited by slug with a side-by-side mapping of each rulebook rule to the specific artefact in that mission.

8. **Registry is machine-readable and schema-validated**
   - **Given** `architecture/2.x/shim-registry.yaml`
   - **When** a unit test parses it
   - **Then** every entry conforms to the documented schema (required fields present, enum values valid, release strings semver-shaped).

### Edge cases

- A shim whose canonical package has itself been renamed mid-deprecation-window. Resolution: the registry entry's `canonical_import` field updates in the same PR that renames the canonical package; the shim continues to re-export under the original legacy name until its registered removal release.
- A shim that legitimately needs to live longer than one release (e.g., external downstream importers need more notice). Resolution: extension is allowed only by explicit PR that updates `removal_target_release` and adds a `extension_rationale` field; reviewed like any other architecture change.
- A shim that covers multiple canonical imports (umbrella module). Resolution: the registry entry's `canonical_import` may be a list; the schema allows string-or-list.
- A new extraction that introduces a shim without registering it. Resolution: a separate pytest scans `src/specify_cli/` for modules carrying `__deprecated__ = True` and asserts each is present in the registry by `legacy_path`.

---

## Requirements

### Functional Requirements

| ID      | Requirement                                                                                                                                                                                                        | Status    |
|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| FR-001  | The mission produces the rulebook at `architecture/2.x/06_migration_and_shim_rules.md`.                                                                                                                             | Confirmed |
| FR-002  | The rulebook codifies four rule families: (a) project schema/version gating, (b) bundle/runtime migration authoring contract, (c) compatibility shim lifecycle, (d) removal plans and the registry contract.        | Confirmed |
| FR-003  | The rulebook specifies the canonical shim module shape: re-exports from the canonical package, `__deprecated__: bool`, `__canonical_import__: str`, `__removal_release__: str`, `__deprecation_message__: str`, and `warnings.warn(..., DeprecationWarning, stacklevel=2)` on import. | Confirmed |
| FR-004  | The rulebook mandates a one-release deprecation window (shim removed no earlier than the next minor release after introduction) with an explicit extension mechanism.                                               | Confirmed |
| FR-005  | The rulebook defines the removal-PR contract: PR deletes the shim, removes the registry entry (or marks it `removed`), updates `CHANGELOG.md` under *Removed*, and closes the tracker issue for the shim.           | Confirmed |
| FR-006  | The mission produces the shim registry at `architecture/2.x/shim-registry.yaml` populated with every shim present in the codebase at mission-start. Since upstream mission #610 removes `specify_cli.charter`, the registry is expected to start empty or near-empty; the FR-010 scanner test is the source of truth for completeness. | Confirmed |
| FR-007  | Each registry entry contains: `legacy_path`, `canonical_import` (string or list), `introduced_in_release`, `removal_target_release`, `tracker_issue`, `grandfathered: bool`, optional `extension_rationale`, optional `notes`. | Confirmed |
| FR-008  | Pre-existing shims that do not fully match the rulebook are flagged `grandfathered: true` with an explicit rationale; no pre-existing shim is silently retrofitted.                                                  | Confirmed |
| FR-009  | The mission implements a new CLI subcommand `spec-kitty doctor shim-registry` that: (a) parses the registry, (b) validates schema, (c) compares each entry's `removal_target_release` to the current project version, (d) fails with exit code non-zero when a removal target has been reached but the shim file still exists, (e) prints a summary table of pending and overdue shims. | Confirmed |
| FR-010  | A pytest asserts that every module under `src/specify_cli/` carrying `__deprecated__ = True` is present in the registry (keyed by legacy import path), preventing silent/unregistered shim additions.                  | Confirmed |
| FR-011  | A pytest asserts the registry schema: required fields, enum values, semver-shaped release strings.                                                                                                                  | Confirmed |
| FR-012  | The rulebook contains a worked-example section that walks through mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` as the reference instance, mapping each rule to the concrete artefacts in that mission. | Confirmed |
| FR-013  | The rulebook explicitly references the upcoming doctrine-versioning work in #461 Phase 7 as the follow-up that will extend the schema-version rule family for doctrine artefacts.                                    | Confirmed |
| FR-014  | The rulebook cross-references `architecture/2.x/05_ownership_map.md` (from mission #610) so each slice entry in the map corresponds to a future registry entry when that slice extracts.                              | Confirmed |
| FR-015  | `CHANGELOG.md` gains an *Unreleased* entry under "Added" announcing the rulebook, registry, and CI check.                                                                                                            | Confirmed |

### Non-Functional Requirements

| ID       | Requirement                                                                                                                                                                                  | Status    |
|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| NFR-001  | `spec-kitty doctor shim-registry` completes in ≤2 seconds on a project with up to 50 registry entries.                                                                                        | Confirmed |
| NFR-002  | The registry YAML schema test runs in ≤500 ms.                                                                                                                                               | Confirmed |
| NFR-003  | Rulebook is readable end-to-end by a new contributor in ≤15 minutes (peer-reviewed during `/spec-kitty.review`).                                                                              | Confirmed |
| NFR-004  | The CLI check's error messages name the specific shim, legacy path, canonical import, and suggested remediation.                                                                             | Confirmed |
| NFR-005  | Zero regressions in existing test suite.                                                                                                                                                      | Confirmed |

### Constraints

| ID     | Constraint                                                                                                                                                                                   | Status    |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| C-001  | The mission does **not** add, modify, or remove any live shim. If `specify_cli.charter` is still present when this mission starts, it is simply registered as an entry; its deletion belongs to mission #610. | Confirmed |
| C-002  | The mission does **not** implement doctrine-specific versioning (#461 Phase 7) — only references it as the follow-up.                                                                          | Confirmed |
| C-003  | The mission does **not** retrofit pre-existing non-charter migrations or shims to fully match the new rules. Non-conforming items are registered with `grandfathered: true`.                   | Confirmed |
| C-004  | The CI check is purely read-only — it never writes to the registry or modifies files.                                                                                                         | Confirmed |
| C-005  | The mission runs under `change_mode: standard`.                                                                                                                                              | Confirmed |
| C-006  | Terminology canon applies: **Mission** (not "feature"), **Work Package** (not "task").                                                                                                        | Confirmed |
| C-007  | The `spec-kitty doctor` subcommand must integrate cleanly with the existing `doctor` command group (currently `command-files`, `state-roots`, `identity`, `sparse-checkout`).                 | Confirmed |

---

## Success Criteria

1. **Rulebook completeness** — The rulebook covers all four rule families; every rule has a concrete example referenced from the charter mission.
2. **Registry populated** — Every active shim in the codebase appears in `architecture/2.x/shim-registry.yaml`; zero undetected shims when the FR-010 scanner test runs.
3. **CI enforcement active** — `spec-kitty doctor shim-registry` is integrated into CI; a deliberately-induced overdue-removal test case fails the check with the expected exit code and message.
4. **Grandfathered exception path works** — A pre-existing non-conforming shim can be registered with `grandfathered: true` and the rationale field, and the check passes with an advisory rather than failure.
5. **Downstream missions cite the rulebook** — Mission drafts for #612 and #613 already reference this rulebook as a direct prerequisite; their eventual specs and plans can point to specific rule IDs or sections.
6. **Zero regression** — Existing tests pass unchanged.

---

## Key Entities

- **Rulebook** — the Markdown document codifying migration and shim policy.
- **Shim registry** — the YAML artefact enumerating every active and grandfathered shim.
- **Registry entry** — a single YAML record with fields `legacy_path`, `canonical_import`, `introduced_in_release`, `removal_target_release`, `tracker_issue`, `grandfathered`, and optional `extension_rationale`, `notes`.
- **Rule family** — one of: schema/version gating, bundle/runtime migration contract, compatibility shim lifecycle, removal plans.
- **Compatibility shim** (same entity as in #610): a re-export module under `src/specify_cli/*` with `__deprecated__`, `__canonical_import__`, `__removal_release__`.
- **Doctor check** — the new `spec-kitty doctor shim-registry` CLI subcommand.
- **Grandfathered shim** — an existing shim that does not fully match the new rules but is allowed to persist under explicit rationale.

---

## Dependencies & Assumptions

### Upstream

- Mission `functional-ownership-map-01KPDY72` (#610) merged. This mission consumes the slice-by-slice shim inventory from the ownership map.

### Downstream

- #612, #613, #614 each produce at least one new registry entry as part of their extraction landing PR.
- The model-discipline doctrine port likewise registers any shim it introduces.
- #461 Phase 7 doctrine-versioning work extends the schema-version rule family.

### Assumptions

- A1. The `architecture/2.x/` directory is the correct home for both the rulebook (`06_migration_and_shim_rules.md`) and the registry (`shim-registry.yaml`).
- A2. `spec-kitty doctor` is the correct command group for the enforcement check (adjacent to the existing `command-files`, `state-roots`, `identity`, `sparse-checkout` subcommands).
- A3. The project uses semver release strings; `removal_target_release` values are validated against a semver-shaped regex.
- A4. At most a single-digit number of shims exist at mission-start time; registry file remains human-readable without pagination.
- A5. Retrofit of pre-existing non-charter migrations is explicitly out of scope. Forward-only rules apply from this mission.

---

## Out of Scope

- Adding, modifying, or removing any live shim.
- Implementing doctrine-specific versioning (#461 Phase 7).
- Retrofitting pre-existing non-conforming shims to match the new rules.
- Extracting any slice code (#612, #613, #614).
- Automating shim removal PRs (the rulebook describes the removal-PR contract; human authors open those PRs).
- Any version bump or release automation changes.

---

## Open Questions

None at spec time. All paths, formats, and enforcement behaviors are pinned in this spec. Plan phase will additionally determine:

- The exact YAML schema keys (should `canonical_import` allow a list only in dict form, or also as a sequence under the string key?).
- The precise integration point for the doctor subcommand within the existing `doctor` group's code layout.
- Whether the unregistered-shim scanner test lives under `tests/architecture/` or `tests/unit/`.
