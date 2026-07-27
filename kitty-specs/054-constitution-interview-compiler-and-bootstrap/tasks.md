---
description: "Work packages for 054-constitution-interview-compiler-and-bootstrap"
---

# Work Packages: Constitution Interview Compiler and Context Bootstrap

**Inputs**: Design documents from `kitty-specs/054-constitution-interview-compiler-and-bootstrap/`
**Prerequisites**: `plan.md` ✅ · `spec.md` ✅ · `research.md` ✅ · `data-model.md` ✅ · `quickstart.md` ✅ · `contracts/constitution-cli-contract.md` ✅

**Tests**: This feature explicitly requires CLI, compiler, context, migration, and integration regression coverage.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into focused work packages (`WPxx`). Each work package is scoped so an implementer can complete it end-to-end in one focused session.

**Prompt Files**: Each work package references a matching prompt file in `kitty-specs/054-constitution-interview-compiler-and-bootstrap/tasks/`.

## Subtask Format: `[Txxx] [P?] Description`

- `[P]` indicates the subtask can proceed in parallel once package prerequisites are met.
- Every subtask points to concrete modules, assets, or tests.

## Path Conventions

- Runtime code: `src/specify_cli/`, `src/doctrine/`
- Planning artifacts: `kitty-specs/054-constitution-interview-compiler-and-bootstrap/`
- Tests: `tests/specify_cli/`, `tests/integration/`, `tests/e2e/`

---

## Work Package WP01: Harden Interview and Generate CLI Contracts (Priority: P1) 🎯 MVP

**Goal**: Make the interview/generate workflow strict and scriptable: `interview` writes the canonical answers file, `generate` hard-fails when interview answers are missing, and overwrite/error behavior is deterministic.
**Independent Test**: `spec-kitty constitution interview --defaults --json` returns the canonical answers payload; `spec-kitty constitution generate` fails without `.kittify/constitution/interview/answers.yaml`; when generated outputs already exist and `--force` is absent, the command warns listing conflicting files and prompts interactively — proceeding only on confirmation, aborting on rejection; `--force` bypasses the prompt entirely.
**Prompt**: `tasks/WP01-cli-contract-hardening.md`
**Requirement Refs**: FR-001, FR-002, FR-010, FR-011, SC-001, SC-002

### Included Subtasks

- [x] T001 Audit the current `interview`, `generate`, and `generate-for-agent` command flows in `src/specify_cli/cli/commands/constitution.py`
- [x] T002 Normalize `interview --json` and failure payloads to the feature contract
- [x] T003 Remove silent default fallback for `generate` / `generate-for-agent` when `--from-interview` is active and `answers.yaml` is missing
- [x] T004 Enforce overwrite checks across all generated files, not just `constitution.md`
- [x] T005 Add CLI regression tests for interview/generate hard-fail, JSON errors, and `--force`

### Implementation Notes

- Use `_interview_path(repo_root)` as the single source for the path shown in human and JSON errors.
- Keep `--no-from-interview` behavior intact for explicit default-based generation paths.
- Align JSON failures on `{"error": "<message>"}` and success responses on `{"result": "success", ...}`.
- Ensure overwrite guards account for `constitution.md`, `references.yaml`, `governance.yaml`, `directives.yaml`, and `metadata.yaml`. Without `--force`, list all conflicting files in the warning before prompting; do not write anything until the user confirms.

### Parallel Opportunities

- None inside this WP; all subtasks touch the same CLI contract surface.

### Dependencies

- None.

### Risks & Mitigations

- `generate-for-agent` shares most of the same control flow as `generate`; keep both commands aligned or reviewers will find inconsistent behavior.

### Estimated Prompt Size

~250 lines

---

## Work Package WP02: Model Local Support Declarations and Generated References (Priority: P1)

**Goal**: Add explicit local doctrine-support file declarations to the interview/compiler pipeline, emit them in `references.yaml`, report them via `library_files`, and stop materializing generated `library/` content.
**Independent Test**: A declared local markdown file appears in `references.yaml` and `generate --json` `library_files`; globs/directories are rejected; shipped-only runs emit an empty `library_files`; no generated `library/` directory remains.
**Prompt**: `tasks/WP02-local-support-and-references.md`
**Requirement Refs**: FR-004, FR-017, FR-018, NFR-001, SC-001

### Included Subtasks

- [x] T006 Extend the interview data model in `src/specify_cli/constitution/interview.py` for `local_supporting_files`
- [x] T007 Validate and normalize local support declarations: explicit file paths only, optional action scoping, optional target metadata
- [x] T008 Build additive local support references and conflict warnings in `src/specify_cli/constitution/compiler.py`
- [x] T009 Rewrite generated reference/output bookkeeping for `references.yaml`, `generated_files`, and `library_files`
- [x] T010 Remove generated `library/` materialization and stale library cleanup logic from bundle writing/status assumptions
- [x] T011 Add compiler and CLI tests for local supporting files, overlap warnings, and empty shipped-only `library_files`

### Implementation Notes

- Local support files are discoverable only from `answers.yaml` and mirrored `references.yaml`; there is no implicit filesystem scan.
- Path declarations must reject directories and glob-like values (`*`, `?`, `[]`, recursive `**` patterns).
- If `target_kind` and `target_id` overlap a shipped artifact, shipped doctrine stays primary and the compiler surfaces a warning instead of replacing shipped content.
- Free-form markdown is acceptable for local files; do not force them into shipped YAML schemas.

### Parallel Opportunities

- T006 and T007 can be split once the target field shape is agreed from `data-model.md`.

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- The current compiler writes physical reference content into `.kittify/constitution/library/`; remove that behavior carefully and update any downstream callers/tests that still count those files.

### Estimated Prompt Size

~320 lines

---

## Work Package WP03: Enforce Shipped-Only Validation Authority (Priority: P1)

**Goal**: Make the shipped doctrine catalog the authoritative validation source by default, keep `_proposed/` behind explicit opt-in, close template-set validation gaps, and confirm sync output excludes `agents.yaml`.
**Independent Test**: Invalid shipped selections fail with named-ID errors; invalid `template_set` values fail even when template-set metadata is empty; `_proposed/` content is excluded unless explicitly requested; sync output remains `governance.yaml`, `directives.yaml`, and `metadata.yaml` only.
**Prompt**: `tasks/WP03-shipped-validation-authority.md`
**Requirement Refs**: FR-003, FR-005, NFR-003, SC-003, SC-004

### Included Subtasks

- [x] T012 Audit `src/specify_cli/constitution/catalog.py`, `resolver.py`, and sync output expectations
- [x] T013 Keep shipped-only catalog loading as the default contract, with explicit `_proposed/` opt-in for curation flows
- [x] T014 Add template-set filesystem fallback against packaged mission directories when catalog metadata is empty
- [x] T015 Ensure shipped selection validation remains strict while local support files bypass catalog-ID enforcement
- [x] T016 Update sync/status assumptions so `agents.yaml` is absent and any stale assertions are removed
- [x] T017 Add catalog/resolver/sync regression tests for named-ID failures and shipped-only behavior

### Implementation Notes

- Validation errors must name the offending value directly; vague “invalid selection” failures are insufficient.
- If mission directories are unavailable in a packaged install, preserve the current offline-friendly behavior instead of inventing a new hard failure mode.
- Do not reintroduce `_proposed/` visibility through secondary validation paths.

### Parallel Opportunities

- T013 and T014 can be developed in parallel after T012.

### Dependencies

- None.

### Risks & Mitigations

- `load_doctrine_catalog()` is already used in multiple places; keep behavior changes explicit and covered by tests so curation-only callers can still opt in intentionally.

### Estimated Prompt Size

~280 lines

---

## Work Package WP04: Extract Software-Dev Action Doctrine Assets (Priority: P1)

**Goal**: Remove embedded governance prose from the software-dev `specify`, `plan`, `implement`, and `review` command templates, and relocate that content into per-action doctrine assets with action indexes.
**Independent Test**: The four source templates keep workflow/bootstrap instructions only; `src/doctrine/missions/software-dev/actions/<action>/guidelines.md` and `index.yaml` exist for each action; extracted guidance is retrievable at runtime instead of embedded inline.
**Prompt**: `tasks/WP04-action-doctrine-assets.md`
**Requirement Refs**: FR-012, FR-015, SC-008, SC-009

### Included Subtasks

- [x] T018 Audit the four software-dev command templates and mark governance prose to extract vs workflow content to preserve
- [x] T019 Create `actions/specify/` and `actions/plan/` `guidelines.md` + `index.yaml`
- [x] T020 Create `actions/implement/` and `actions/review/` `guidelines.md` + `index.yaml`
- [x] T021 Strip extracted prose from `src/doctrine/missions/software-dev/command-templates/*.md` without removing bootstrap, `$ARGUMENTS`, or workflow steps
- [x] T022 Populate action indexes with shipped doctrine IDs relevant to each action and verify the IDs are valid
- [x] T023 Add source-asset tests or golden assertions for the extracted templates and action files

### Implementation Notes

- This feature is software-dev mission only; do not touch other mission templates.
- Keep the exact `## Constitution Context Bootstrap (required)` blocks in source templates.
- Preserve command-template structure so existing agent-generation machinery still copies valid prompts.
- Extraction uses a **hybrid approach**: a script (or migration step) detects governance prose sections and stubs them into `guidelines.md` files; a contributor then reviews and refines the stubbed content before committing. Do not hand-author `guidelines.md` from scratch without the stub-generation step.

### Parallel Opportunities

- T019 and T020 are parallel once T018 has identified the extractable content.

### Dependencies

- None.

### Risks & Mitigations

- Over-extracting workflow instructions will break downstream command prompts; reviewers should diff the before/after template structure, not just search for removed headings.

### Estimated Prompt Size

~300 lines

---

## Work Package WP05: Implement Action-Scoped Iterative Context Retrieval (Priority: P1)

**Goal**: Rebuild `constitution context` around action indexes, per-type repository retrieval, explicit depth control, bootstrap state, and action-scoped local support files.
**Independent Test**: First `context --action plan` call returns depth-2 bootstrap output; subsequent calls default to compact depth 1; `--depth 3` adds styleguide/toolguide detail; `plan` does not leak `implement`-only doctrine; plan-scoped local support files appear only in `plan`.
**Prompt**: `tasks/WP05-action-scoped-context.md`
**Requirement Refs**: FR-006, FR-007, FR-013, FR-014, FR-015, FR-016, NFR-002, SC-005, SC-009, SC-010, SC-011

### Included Subtasks

- [x] T024 Add `ActionIndex` loading/export support under `src/doctrine/missions/`
- [x] T025 Rework `build_constitution_context()` for bootstrap state, explicit `--depth`, and graceful degradation on missing/corrupt constitution artifacts
- [x] T026 Fetch directives, tactics, styleguides, toolguides, and action guidelines through the correct repositories using action-index intersections
- [x] T027 Include action-scoped local support references from `references.yaml` without letting them override shipped doctrine
- [x] T028 Update `constitution context` CLI and downstream consumers for the new JSON shape (`context`, `text`, `mode`, `depth`)
- [x] T029 Add context and consumer regression tests for depth semantics, action isolation, missing files, and local-support scoping

### Implementation Notes

- Default depth is derived from bootstrap state only when `--depth` is omitted: first call -> depth 2, later calls -> depth 1.
- `context-state.json` is keyed by action and should remain deterministic JSON.
- `context` and `text` must contain the same rendered payload for compatibility.
- Each artifact type must be loaded from its own repository service; do not shortcut through generic file scans.

### Parallel Opportunities

- T024 can proceed in parallel with design work for T025/T026.

### Dependencies

- Depends on WP02.
- Depends on WP04.

### Risks & Mitigations

- `build_constitution_context()` is used by both direct CLI commands and workflow/prompt-builder consumers; keep signatures and compatibility updates synchronized.

### Estimated Prompt Size

~360 lines

---

## Work Package WP06: Migrate Generated Agent Templates to Bootstrap Context (Priority: P2)

**Goal**: Ship an idempotent migration that updates generated agent prompt files across all configured agents to use bootstrap context, removes stale inline governance prose, and cleans up obsolete constitution library output.
**Independent Test**: The migration updates all four command prompts per configured agent, inserts bootstrap calls once, strips targeted prose blocks, removes `.kittify/constitution/library/` if present, and produces no duplicate changes on a second run.
**Prompt**: `tasks/WP06-template-bootstrap-migration.md`
**Requirement Refs**: FR-008, FR-009, SC-006, SC-007, SC-008

### Included Subtasks

- [x] T030 Audit existing migration patterns and the generated prompt inventory for configured agents
- [x] T031 Implement migration detect/can-apply logic for stale inline-prose or missing bootstrap-call states
- [x] T032 Implement idempotent prompt rewriting for the four command prompts across markdown and TOML agent formats
- [x] T033 Remove obsolete `.kittify/constitution/library/` artifacts during migration apply when present
- [x] T034 Register the migration and add parametrized tests across all 12 supported agents
- [x] T035 Add second-run idempotency and configured-agent filtering coverage

### Implementation Notes

- Follow the migration style already used in `src/specify_cli/upgrade/migrations/`; do not invent a new migration harness.
- Action mapping must derive the correct `--action` from each prompt filename.
- A configured-agent project should not rewrite orphaned prompt directories for agents that are not active in `.kittify/config.yaml`.

### Parallel Opportunities

- T034 and T035 can be split once T031-T033 are stable.

### Dependencies

- Depends on WP04.
- Depends on WP05.

### Risks & Mitigations

- Generated prompts live in multiple directory conventions and formats; keep the migration logic centralized and heavily fixture-tested rather than scattering format-specific ad hoc replacements.

### Estimated Prompt Size

~300 lines

---

## Work Package WP07: Close the Integration and Compatibility Gaps (Priority: P2)

**Goal**: Refresh cross-cutting tests and downstream compatibility points so the end-to-end `interview -> generate -> context` workflow, next-prompt consumers, and reconstruction tests all match the new contract.
**Independent Test**: End-to-end tests cover explicit local support files, bootstrap-state transitions, absence of generated `library/` and `agents.yaml`, and compatibility with prompt-building/workflow consumers.
**Prompt**: `tasks/WP07-integration-compatibility-sweep.md`
**Requirement Refs**: FR-010, FR-017, FR-018, NFR-001, NFR-002, SC-001, SC-010

### Included Subtasks

- [x] T036 Update existing compiler, integration, and e2e tests that still assume materialized library docs or legacy JSON fields
- [x] T037 Add an end-to-end scenario for explicit local support declarations, additive conflict warnings, and first-vs-subsequent context behavior
- [x] T038 Verify `src/specify_cli/next/prompt_builder.py` and `src/specify_cli/cli/commands/agent/workflow.py` still consume bootstrap context correctly, adding targeted regressions where needed

### Implementation Notes

- This is the convergence package after the functional WPs land; avoid duplicating unit coverage already owned by earlier work packages.
- Use `quickstart.md` as the scenario source of truth for the end-to-end checks.

### Parallel Opportunities

- T036 and T038 can proceed in parallel after WP05 stabilizes.

### Dependencies

- Depends on WP01.
- Depends on WP02.
- Depends on WP03.
- Depends on WP05.
- Depends on WP06.

### Risks & Mitigations

- Cross-cutting test updates are easy to under-scope. Reviewers should confirm that legacy references to `success`, `constitution_path`, `files_written`, and `library/` have either been updated intentionally or are explicitly preserved for compatibility.

### Estimated Prompt Size

~210 lines

---

## Work Package WP08: Architectural Review, Glossary, and User Docs (Priority: P2)

**Goal**: Close the feature with a reviewer-oriented architectural pass, align glossary terminology, and update user-facing documentation for the new constitution workflow.
**Independent Test**: The implementation is cross-checked against the spec/plan contract; glossary terms are consistent across feature artifacts and user docs; user documentation reflects the shipped-only catalog rule, explicit local support declarations, no generated `library/`, and the `interview -> generate -> context` flow.
**Prompt**: `tasks/WP08-architecture-glossary-and-user-docs.md`
**Requirement Refs**: FR-013, FR-016, FR-017, FR-018, NFR-001

### Included Subtasks

- [x] T039 Perform an architectural review against `spec.md`, `plan.md`, `research.md`, and the implemented runtime surfaces, using a reviewer-role mindset
- [x] T040 Update glossary terms and canonical wording across feature artifacts and touched doctrine/CLI docs
- [x] T041 Update user-facing documentation for the constitution workflow, including local support declarations and bootstrap depth behavior
- [x] T042 Add or refresh documentation/regression checks so stale examples do not keep referring to `library/`, `agents.yaml`, or legacy JSON payloads

### Implementation Notes

- Treat this as a reviewer-oriented polish package, not another feature-design package.
- Canonical terms to keep consistent include: `local support file`, `action index`, `bootstrap context`, `compact context`, `shipped doctrine`, and `library_files`.
- User documentation should explain the additive conflict model for local files without implying they override shipped doctrine.

### Parallel Opportunities

- T040 and T041 can proceed in parallel after the architectural review notes from T039 are clear.

### Dependencies

- Depends on WP05.
- Depends on WP06.
- Depends on WP07.

### Risks & Mitigations

- Documentation polish often drifts from implementation reality. Ground every change in the actual CLI output and feature artifacts rather than rephrasing the spec abstractly.

### Estimated Prompt Size

~180 lines

---

## Work Package WP09: Extract Canonical ArtifactKind Enum and Consolidate Repetition (Priority: P2)

**Goal**: Create a single `ArtifactKind` `StrEnum` in `src/doctrine/artifact_kinds.py` that defines all doctrine artifact types once, with derived properties (`plural`, `glob_pattern`, `singular`). Replace the three duplicate reference-type enums, `ARTIFACT_TYPES`, `_GLOB_PATTERNS`, and `_REF_TYPE_MAP` with derivations from the enum.
**Independent Test**: `ArtifactKind` enum has 8 members with correct `plural` and `glob_pattern` properties; old `DirectiveReferenceType`, `ReferenceType` (tactics), and `ProcedureReferenceType` are fully removed; `ARTIFACT_TYPES` now includes `agent_profiles`; `_REF_TYPE_MAP` now includes `paradigm`; all existing tests pass.
**Prompt**: `tasks/WP09-doctrine-artifact-kind-enum.md`

### Included Subtasks

- [x] T043 Create `src/doctrine/artifact_kinds.py` with `ArtifactKind` enum
- [x] T044 Replace the three duplicate ReferenceType enums
- [x] T045 Replace `ARTIFACT_TYPES` and `_GLOB_PATTERNS` constants
- [x] T046 Replace `_REF_TYPE_MAP` in reference_resolver
- [x] T047 Add tests and verify no regressions

### Implementation Notes

- Keep `artifact_kinds.py` zero-dependency within doctrine (no imports from specify_cli).
- `TEMPLATE` kind exists in reference enums but has no repository or shipped directory; keep it in the enum but exclude from iteration helpers like `ARTIFACT_TYPES`.
- Verify Pydantic model deserialization still works with `ArtifactKind` as a `StrEnum`.

### Parallel Opportunities

- T043 can proceed independently; T044/T045/T046 can start once T043 is complete but are parallelizable with each other.

### Dependencies

- Depends on WP05.

### Risks & Mitigations

- Pydantic models use `StrEnum` for validation; verify that `ArtifactKind` serializes/deserializes identically to the old per-model enums.

### Estimated Prompt Size

~140 lines

---

## Work Package WP10: Migrate Remaining Consumers to ArtifactKind Enum (Priority: P2)

**Goal**: Align all remaining consumer-side naming with `ArtifactKind.plural` — rename `DoctrineCatalog.profiles` to `agent_profiles`, ensure `ActionIndex`, `GovernanceResolution`, and `ResolvedReferenceGraph` field names are consistent, and derive CLI help text from the enum.
**Independent Test**: `DoctrineCatalog.profiles` no longer exists (fully renamed to `agent_profiles`); `domains_present` uses `"agent_profiles"` not `"profiles"`; CLI help text no longer hardcodes artifact type lists; all tests pass.
**Prompt**: `tasks/WP10-artifact-kind-consumers.md`

### Included Subtasks

- [x] T048 Align `DoctrineCatalog` and catalog loading
- [x] T049 Align `ActionIndex`, `GovernanceResolution`, and `ResolvedReferenceGraph`
- [x] T050 Update doctrine CLI help text
- [x] T051 Run full test suite and fix regressions

### Implementation Notes

- The `profiles` → `agent_profiles` rename in `DoctrineCatalog` is a breaking change within this codebase — update all callers.
- Use thorough grep to catch attribute access patterns that don't show up in simple string searches.

### Parallel Opportunities

- T048, T049, and T050 can proceed in parallel; T051 runs last as a validation pass.

### Dependencies

- Depends on WP09.

### Risks & Mitigations

- The `profiles` → `agent_profiles` rename touches multiple callers; downstream code may use attribute access patterns that don't show up in simple string searches.

### Estimated Prompt Size

~100 lines

---

## Work Package WP11: Create MissionRepository and Redirect Package Asset Resolution (Priority: P2)

**Goal**: Create a `MissionRepository` service in `src/doctrine/missions/repository.py` following the established doctrine repository pattern, redirect `get_package_asset_root()` to resolve from `doctrine.missions` instead of the stale `specify_cli.missions`, and update `pyproject.toml` packaging.
**Independent Test**: `MissionRepository` lists missions and resolves command-templates; tier-5 resolution serves content from `doctrine/missions/`; installed distributions include `doctrine/missions/` data files; all existing tests pass.
**Prompt**: `tasks/WP11-doctrine-mission-repository.md`

### Included Subtasks

- [x] T052 Create `MissionRepository` in `src/doctrine/missions/repository.py`
- [x] T053 Redirect `get_package_asset_root()` to `doctrine.missions`
- [x] T054 Update `pyproject.toml` packaging
- [x] T055 Update `copy_specify_base_from_package()` to use doctrine source
- [x] T056 Add tests and verify no regressions

### Implementation Notes

- Keep the repository read-only (no save/delete) — missions are shipped assets.
- The 5-tier resolver in `specify_cli` handles overrides; the repository just provides the shipped defaults.
- Keep `specify_cli/missions` as a fallback during the transition (WP12 removes it).

### Parallel Opportunities

- T052 can proceed independently; T053/T054/T055 can start once T052 is complete.

### Dependencies

- Depends on WP05 and WP09 (both touch `doctrine/missions/`).

### Risks & Mitigations

- Changing `get_package_asset_root()` affects all tier-5 resolution. Keep a backward-compatible fallback until WP12.

### Estimated Prompt Size

~160 lines

---

## Work Package WP12: Remove Stale specify_cli/missions Content and Clean Up References (Priority: P2)

**Goal**: Remove the stale command-templates and templates from `src/specify_cli/missions/` (58 stale template copies, all divergent from doctrine source), update migration code to source from `doctrine/missions/`, remove the fallback in `get_package_asset_root()`, and fix all stale path references.
**Independent Test**: `src/specify_cli/missions/` contains only Python modules (no `.md`/`.yaml` template content); migrations source from `doctrine/missions/`; no stale `specify_cli/missions/*/command-templates/` references remain; all tests pass.
**Prompt**: `tasks/WP12-remove-stale-cli-missions.md`

### Included Subtasks

- [ ] T057 Remove command-templates and templates from `specify_cli/missions/`
- [ ] T058 Update migration code references
- [ ] T059 Remove `specify_cli/missions` fallback and update packaging
- [ ] T060 Fix stale path references and run full test suite

### Implementation Notes

- Use `git rm -r` for tracked content removal.
- Keep `__init__.py`, `glossary_hook.py`, `primitives.py`, and `mission.yaml` files.
- Migration code may need dual-path fallback logic for older projects.

### Parallel Opportunities

- T057 and T058 can proceed in parallel; T059 and T060 run after.

### Dependencies

- Depends on WP11.

### Risks & Mitigations

- Removing template content from `specify_cli/missions/` could break installed distributions if WP11's packaging update is incomplete. Verify with a test build.

### Estimated Prompt Size

~120 lines

---

## Dependency & Execution Summary

- **Recommended sequence**: WP01 + WP03 + WP04 can start immediately. WP02 follows WP01. WP05 follows WP02 and WP04. WP06 follows WP04 and WP05. WP07 closes the integration sweep after the main runtime and migration work lands. WP08 is the final reviewer/documentation closeout. WP09 follows WP05 (doctrine consolidation). WP10 follows WP09 (consumer alignment). WP11 follows WP05 and WP09 (mission repository). WP12 follows WP11 (stale content removal).
- **Best parallel lanes**: `WP01` / `WP03` / `WP04` in parallel first; then `WP02`; then `WP05`; then `WP06` / `WP09` in parallel; then `WP07` / `WP10` / `WP11`; then `WP12`; finish with `WP08`.
- **MVP scope**: WP01 through WP05. WP06 through WP08 are release-hardening. WP09-WP10 are doctrine consolidation (Phase 3). WP11-WP12 are mission consolidation (Phase 4).

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01 |
| FR-003 | WP03 |
| FR-004 | WP02 |
| FR-005 | WP03 |
| FR-006 | WP05 |
| FR-007 | WP05 |
| FR-008 | WP06 |
| FR-009 | WP06 |
| FR-010 | WP01, WP05, WP07 |
| FR-011 | WP01 |
| FR-012 | WP04 |
| FR-013 | WP05, WP08 |
| FR-014 | WP05 |
| FR-015 | WP04, WP05 |
| FR-016 | WP05, WP08 |
| FR-017 | WP02, WP07, WP08 |
| FR-018 | WP02, WP03, WP05, WP07, WP08 |
| NFR-001 | WP02, WP07, WP08 |
| NFR-002 | WP05, WP07 |
| NFR-003 | WP03 |

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Audit CLI interview/generate flows | WP01 | P1 | No |
| T002 | Normalize interview/generate JSON contracts | WP01 | P1 | No |
| T003 | Hard-fail missing interview answers | WP01 | P1 | No |
| T004 | Enforce overwrite checks across generated files | WP01 | P1 | No |
| T005 | Add CLI contract tests | WP01 | P1 | No |
| T006 | Extend interview model for local supporting files | WP02 | P1 | No |
| T007 | Validate explicit local declaration shapes | WP02 | P1 | Yes |
| T008 | Build additive local references and warnings | WP02 | P1 | No |
| T009 | Emit generated_files and library_files from bundle generation | WP02 | P1 | No |
| T010 | Remove library materialization | WP02 | P1 | No |
| T011 | Add local-support compiler/CLI tests | WP02 | P1 | No |
| T012 | Audit catalog/resolver/sync validation behavior | WP03 | P1 | No |
| T013 | Keep shipped-only catalog loading authoritative | WP03 | P1 | Yes |
| T014 | Add template-set fallback validation | WP03 | P1 | Yes |
| T015 | Preserve strict shipped validation while exempting local support docs | WP03 | P1 | No |
| T016 | Remove agents.yaml assumptions from sync/status | WP03 | P1 | No |
| T017 | Add catalog/resolver/sync tests | WP03 | P1 | No |
| T018 | Audit extractable software-dev template prose | WP04 | P1 | No |
| T019 | Create specify/plan action assets | WP04 | P1 | Yes |
| T020 | Create implement/review action assets | WP04 | P1 | Yes |
| T021 | Strip inline prose from source templates | WP04 | P1 | No |
| T022 | Validate action-index doctrine IDs | WP04 | P1 | No |
| T023 | Add source-template asset tests | WP04 | P1 | No |
| T024 | Add ActionIndex loader/export | WP05 | P1 | Yes |
| T025 | Rework bootstrap state and depth handling | WP05 | P1 | No |
| T026 | Implement repository-driven action scoping | WP05 | P1 | No |
| T027 | Include scoped local support references in context | WP05 | P1 | No |
| T028 | Update context CLI/consumer JSON contract | WP05 | P1 | No |
| T029 | Add context and consumer regression tests | WP05 | P1 | No |
| T030 | Audit migration patterns and target prompt inventory | WP06 | P2 | No |
| T031 | Implement migration detection | WP06 | P2 | No |
| T032 | Rewrite generated prompts idempotently | WP06 | P2 | No |
| T033 | Remove stale library artifacts during migration | WP06 | P2 | No |
| T034 | Add parametrized 12-agent migration coverage | WP06 | P2 | Yes |
| T035 | Add idempotency and config-filtering coverage | WP06 | P2 | Yes |
| T036 | Refresh legacy integration/e2e tests | WP07 | P2 | Yes |
| T037 | Add end-to-end declared-local-support scenario | WP07 | P2 | No |
| T038 | Verify workflow/prompt-builder compatibility | WP07 | P2 | Yes |
| T039 | Perform reviewer-oriented architectural review | WP08 | P2 | No |
| T040 | Normalize glossary and canonical terms | WP08 | P2 | Yes |
| T041 | Update user-facing constitution workflow docs | WP08 | P2 | Yes |
| T042 | Refresh documentation/regression checks for stale examples | WP08 | P2 | No |
| T043 | Create `ArtifactKind` enum in `src/doctrine/artifact_kinds.py` | WP09 | P2 | No |
| T044 | Replace three duplicate ReferenceType enums | WP09 | P2 | Yes |
| T045 | Replace `ARTIFACT_TYPES` and `_GLOB_PATTERNS` constants | WP09 | P2 | Yes |
| T046 | Replace `_REF_TYPE_MAP` in reference_resolver | WP09 | P2 | Yes |
| T047 | Add `ArtifactKind` tests and verify no regressions | WP09 | P2 | No |
| T048 | Align `DoctrineCatalog` and catalog loading | WP10 | P2 | Yes |
| T049 | Align `ActionIndex`, `GovernanceResolution`, `ResolvedReferenceGraph` | WP10 | P2 | Yes |
| T050 | Update doctrine CLI help text | WP10 | P2 | Yes |
| T051 | Run full test suite and fix regressions | WP10 | P2 | No |

<!-- status-model:start -->
## Canonical Status (Generated)

- WP01: done
- WP02: done
- WP03: done
- WP04: done
- WP05: done
- WP06: done
- WP07: done
- WP08: done
- WP09: done
- WP10: done
- WP11: done
- WP12: done
<!-- status-model:end -->
