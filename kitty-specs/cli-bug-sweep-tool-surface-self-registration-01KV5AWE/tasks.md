# Tasks: CLI Bug Sweep & Tool Surface Self-Registration

**Mission**: cli-bug-sweep-tool-surface-self-registration-01KV5AWE
**Branch**: `fix/cli-bug-sweep-tool-surface-self-registration`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Generated**: 2026-06-15

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Remove xfail decorator + comment from test_distribution.py | WP01 | [P] |
| T002 | Add docstring invariant to _human_slug_for_mid8_branch() | WP01 | [P] |
| T003 | Add pathological mid8-mismatch test case to test_branch_naming_human_slug.py | WP01 | [P] |
| T004 | git rm 7 stale provenance sidecar files | WP02 | — |
| T005 | Fix doctrine_kind_subdir() to use singular directory names | WP02 | — |
| T006 | Audit and fix hardcoded plural-dir paths in write_pipeline.py | WP02 | — |
| T007 | Add built_in_only early-exit to validate_synthesis_state() | WP02 | — |
| T008 | Add test covering built_in_only fresh-seed scenario | WP02 | — |
| T009 | Create _registry.py with SurfaceRegistration + SurfaceProviderRegistry | WP03 | — |
| T010 | Create _discovery.py with explicit import tuple | WP03 | — |
| T011 | Refactor service.py to derive all config from the registry | WP03 | — |
| T012 | Update agent_profiles.py to call SurfaceProviderRegistry.register() | WP04 | [P] |
| T013 | Update command_skills.py to call SurfaceProviderRegistry.register() | WP04 | [P] |
| T014 | Update managed_skills.py to call SurfaceProviderRegistry.register() | WP04 | [P] |
| T015 | Update native_config.py to call SurfaceProviderRegistry.register() | WP04 | [P] |
| T016 | Update plugin_bundle.py to call SurfaceProviderRegistry.register() (synthetic_key) | WP04 | [P] |
| T017 | Update session_presence.py to call SurfaceProviderRegistry.register() (3 definitions) | WP04 | [P] |
| T018 | Update slash_commands.py to call SurfaceProviderRegistry.register() | WP04 | [P] |
| T019 | Add test_provider_registration.py Directive-030 conformance test | WP04 | — |
| T020 | Fix map-requirements spec.md resolution when coord worktree is present | WP05 | — |
| T021 | Fix validate_glob_matches to include create_intent hint even when nearest-match suggestion present | WP05 | — |

---

## Work Packages

### WP01 — Test Hygiene: xfail Removal & Branch Naming Gap

**Goal**: Remove the stale xfail mask from the distribution test and close the branch naming pathological-case test coverage gap.
**Priority**: High (unblocks clear CI signal)
**Independent test**: `pytest tests/adversarial/test_distribution.py::TestUpgradeWithAllMissions::test_upgrade_updates_templates -v` → PASSED (no XFAIL/XPASS); `pytest tests/core/test_branch_naming_human_slug.py -v` → all pass
**Estimated prompt**: ~250 lines
**Can start**: Immediately (no dependencies)

**Subtasks**:
- [x] T001 Remove xfail decorator + comment block from test_distribution.py (WP01)
- [x] T002 Add docstring invariant statement to _human_slug_for_mid8_branch() (WP01)
- [x] T003 Add pathological mid8-mismatch parameterized test case (WP01)

**Implementation sketch**:
1. Delete the `@pytest.mark.xfail(strict=False, reason=…)` decorator and its inline comment from `tests/adversarial/test_distribution.py:193–206`.
2. Add a one-sentence docstring to `_human_slug_for_mid8_branch()` in `src/specify_cli/lanes/branch_naming.py:134` stating the invariant: the guard only strips the embedded mid8 when it matches `mission_id`'s mid8.
3. Add a parameterized test case to `tests/core/test_branch_naming_human_slug.py` covering the case where the slug's mid8 (`AAAA1111`) differs from `mission_id`'s mid8 (`01KV3NGS`). Assert the exact double-appended output as documented behavior.

**Parallel opportunities**: T001, T002, T003 touch different files and can be done in any order.
**Dependencies**: none
**Risks**: If `ensure_runtime()` is flaky in CI after T001, that is a pre-existing latent issue — file a new issue, do not restore the xfail.
**Prompt file**: [tasks/WP01-test-hygiene.md](tasks/WP01-test-hygiene.md)

---

### WP02 — Charter Bundle Validation Repair

**Goal**: Fix `spec-kitty charter bundle validate` so it exits 0 on a fresh checkout with no project synthesis artifacts. Three-part fix: remove stale sidecars, correct the synthesizer's subdir mapping, add built_in_only early-exit to the validator.
**Priority**: High (blocks contributors running `charter bundle validate` on the repo)
**Independent test**: `spec-kitty charter bundle validate --json` exits 0
**Estimated prompt**: ~380 lines
**Can start**: Immediately (no dependencies)

**Subtasks**:
- [x] T004 git rm 7 stale provenance sidecar files from .kittify/charter/provenance/ (WP02)
- [x] T005 Fix doctrine_kind_subdir() to return singular subdir names (WP02)
- [x] T006 Audit and fix all callers of doctrine_kind_subdir() and hardcoded plural paths in write_pipeline.py (WP02)
- [x] T007 Add built_in_only early-exit to validate_synthesis_state() in src/charter/bundle.py (WP02)
- [x] T008 Add test covering built_in_only fresh-seed state returning no errors (WP02)

**Implementation sketch**:
1. Run `git rm` on all 7 `.kittify/charter/provenance/*.yaml` sidecar files listed in spec.md.
2. In `src/charter/synthesizer/artifact_naming.py`, change `doctrine_kind_subdir()` to return `"directive"`, `"tactic"`, `"styleguide"` (singular). Read the current implementation first.
3. Grep for `doctrine_kind_subdir(` in `src/charter/synthesizer/write_pipeline.py` and fix any hardcoded plural-dir strings (`directives/`, `tactics/`, `styleguides/`) at lines ~174, ~206, ~584.
4. In `src/charter/bundle.py`, add an early-exit in `validate_synthesis_state()` after loading the manifest: if `manifest.built_in_only is True and not manifest.artifacts`, return success immediately without checking for sidecar files.
5. Add a test in `tests/specify_cli/charter/` that seeds a temp repo with `synthesis-manifest.yaml` containing `built_in_only: true` and `artifacts: []` (no sidecar files, no artifact files) and asserts that `validate_synthesis_state()` returns no errors.

**Dependencies**: none (independent of IC-04)
**Risks**: Part T006 requires reading write_pipeline.py carefully to find all call sites — missing one leaves a dangling plural path. The T008 early-exit condition must be `built_in_only AND artifacts == []`; do not suppress validation for repos with real synthesis state.
**Prompt file**: [tasks/WP02-charter-bundle-validation.md](tasks/WP02-charter-bundle-validation.md)

---

### WP03 — Tool Surface Registry Infrastructure

**Goal**: Create the `SurfaceRegistration` dataclass, `SurfaceProviderRegistry` class store, and `_discovery.py` explicit import tuple. Refactor `service.py` to derive all provider configuration from the registry. This WP establishes the infrastructure; WP04 migrates the providers.
**Priority**: High (WP04 depends on this)
**Independent test**: `pytest tests/specify_cli/tool_surface/ -v` → all pass (existing tests)
**Estimated prompt**: ~340 lines
**Can start**: Immediately (no dependencies)

**Subtasks**:
- [x] T009 Create src/specify_cli/tool_surface/providers/_registry.py (WP03)
- [x] T010 Create src/specify_cli/tool_surface/providers/_discovery.py (WP03)
- [x] T011 Refactor service.py to consume registry instead of central literals (WP03)

**Implementation sketch**:
1. Create `_registry.py` with `SurfaceRegistration` (frozen dataclass: `provider_class`, `definitions: tuple[SurfaceDefinition, ...]`, `kind_tokens: dict[str, SurfaceKind]`, `synthetic_key: str | None`, `order: int`) and `SurfaceProviderRegistry` (class with `_registrations: list[SurfaceRegistration]` classvar, `register(reg)` classmethod, `build_kind_tokens()`, `build_providers()`, `build_registry(tool_keys, project_root)` methods that sort by `.order` before iterating).
2. Create `_discovery.py` with a module-level explicit import of all 7 provider modules (not pkgutil). Importing this module fires all registration calls. Export a `_PROVIDERS` tuple for dead-symbol gate traceability.
3. In `service.py`: (a) replace the 7 multi-symbol import blocks with `from .providers._discovery import _PROVIDERS` (this also ensures registrations fire); (b) replace `_KIND_TOKENS` dict literal with `SurfaceProviderRegistry.build_kind_tokens()`; (c) replace `build_providers()` and `build_registry()` function bodies to delegate to `SurfaceProviderRegistry`. Keep `_BUNDLE_SOURCE_TOOL_KEYS` as-is (it is not provider identity). Keep the `PluginBundleProvider` lazy import workaround in `plugin_bundle.py` unchanged.

**Dependencies**: none
**Risks**: `service.py` refactor must preserve the `plugin_bundle` synthetic-key behavior. At T011 time, no providers have registered yet (T012–T018 are in WP04), so `service.py` will work but produce empty provider lists. Existing tests that call `build_providers()` with no registrations may need adjustment — read the existing test suite before editing.
**Prompt file**: [tasks/WP03-tool-surface-registry.md](tasks/WP03-tool-surface-registry.md)

---

### WP04 — Tool Surface Provider Self-Registrations & Conformance Test

**Goal**: Update all 7 provider modules to call `SurfaceProviderRegistry.register(SurfaceRegistration(...))` at module level, and add a Directive-030 conformance test asserting `service.py` has no central provider literal lists.
**Priority**: High (completes the tool surface seam)
**Independent test**: `pytest tests/specify_cli/tool_surface/ -v` → all pass including new conformance test
**Estimated prompt**: ~450 lines
**Can start**: After WP03 is merged (depends on WP03)

**Subtasks**:
- [x] T012 Update agent_profiles.py with SurfaceProviderRegistry.register() call (WP04)
- [x] T013 Update command_skills.py with SurfaceProviderRegistry.register() call (WP04)
- [x] T014 Update managed_skills.py with SurfaceProviderRegistry.register() call (WP04)
- [x] T015 Update native_config.py with SurfaceProviderRegistry.register() call (includes underscore alias token) (WP04)
- [x] T016 Update plugin_bundle.py with SurfaceProviderRegistry.register() call (synthetic_key; preserve lazy import) (WP04)
- [x] T017 Update session_presence.py with SurfaceProviderRegistry.register() call (3 definitions) (WP04)
- [x] T018 Update slash_commands.py with SurfaceProviderRegistry.register() call (WP04)
- [x] T019 Add tests/specify_cli/tool_surface/test_provider_registration.py conformance test (WP04)

**Implementation sketch**:
1. For each standard provider (T012–T015, T018): add a module-level `SurfaceProviderRegistry.register(SurfaceRegistration(provider_class=..., definitions=(...,), kind_tokens={...}, synthetic_key=None, order=N))` call. Read the current `_KIND_TOKENS` entries in `service.py` to get the correct token strings and kinds for each provider.
2. T016 (plugin_bundle): same pattern but set `synthetic_key=PLUGIN_BUNDLE_TOOL_KEY`. Do NOT remove or change the lazy import of `build_plans_for_bundles` from service.py inside the method body.
3. T017 (session_presence): `definitions=(context_file_definition, hook_definition, rule_definition)` — 3 elements. `kind_tokens` includes the underscore alias entries for context_file.
4. T019: create `tests/specify_cli/tool_surface/test_provider_registration.py`. It must assert: (a) `SurfaceProviderRegistry._registrations` has exactly 7 entries after importing `_discovery`; (b) `service.py` source does not contain the pattern `build_providers` with an inner list literal (ast-parse or regex the source file).

**Dependencies**: WP03
**Risks**: The `order` integer for each provider must be stable and unique. Use the current position of the provider in `service.py`'s `build_providers()` list as the reference ordering. T016's synthetic-key handling must match the exact PLUGIN_BUNDLE_TOOL_KEY constant — read it from the current `plugin_bundle.py`.
**Prompt file**: [tasks/WP04-provider-self-registrations.md](tasks/WP04-provider-self-registrations.md)

---

### WP05 — Task-Workflow DX Fixes

**Goal**: Fix two workflow bugs found during this mission's own planning: (A) `map-requirements` can't find `spec.md` when the coord worktree exists and the primary checkout is on a different branch; (B) `finalize-tasks --validate-only` omits the `create_intent` guidance when it also produces a "did you mean?" nearest-match suggestion.
**Priority**: High (blocks the documented planning workflow; misleads authors about how to fix ownership errors)
**Independent test**: `spec-kitty agent tasks map-requirements` succeeds with a coord worktree present; `finalize-tasks --validate-only` error for a zero-match literal path always includes `create_intent` guidance
**Estimated prompt**: ~250 lines
**Can start**: Immediately (no dependencies)

**Subtasks**:
- [x] T020 Fix map-requirements to resolve spec.md from coord worktree when primary checkout lacks the target branch (WP05)
- [x] T021 Fix validate_glob_matches to include create_intent hint in error message even when nearest-match suggestion is present (WP05)

**Implementation sketch**:
1. In `src/specify_cli/cli/commands/agent/tasks.py`, after `feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)`, check if `feature_dir.exists()`. If not, search for a coord worktree (`.worktrees/<mission_slug>-coord/`) that has the target branch checked out and resolve `feature_dir` from there. If no worktree is found either, emit the existing "Mission directory not found" error. The resolved `feature_dir` is then used to read `spec.md`.
2. In `src/specify_cli/ownership/validation.py` → `validate_glob_matches`, change the `if suggestion: ... else: ...` block that builds the zero-match literal-path error message. Both the "did you mean?" suggestion and the `create_intent` hint must appear in the message regardless of whether a suggestion is found. The hint text: `" If this file will be created by this WP, add it to 'create_intent' in the WP frontmatter."`.

**Parallel opportunities**: T020 and T021 touch independent files; they can be implemented in any order.
**Dependencies**: none
**Risks**: T020 must not regress the case where the primary checkout IS on the target branch (common scenario — no coord worktree). T021's message change may break existing test assertions that match the old exact error string; audit `tests/specify_cli/ownership/` and `tests/specify_cli/` for affected assertions.
**Prompt file**: [tasks/WP05-task-workflow-dx-fixes.md](tasks/WP05-task-workflow-dx-fixes.md)
