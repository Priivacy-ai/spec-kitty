# Work Packages: Doctrine Stack Init and Profile Integration

**Inputs**: Design documents from `/kitty-specs/057-doctrine-stack-init-and-profile-integration/`
**Prerequisites**: plan.md ✓, spec.md ✓

**Tests**: ATDD (acceptance-test-driven) + ZOMBIES TDD per WP, as required by the per-WP quality contract.

**Quality gates (constitution-mandated, applies to every WP)**:
- `pytest --cov=<new_module> --cov-fail-under=90` — 90%+ coverage on new code
- `mypy --strict <changed files>` — strict mode, zero errors
- `ruff check .` + `ruff format --check .` — zero violations
- Use `rg` (ripgrep) not `grep` in all verification steps

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each WP is independently deliverable and testable. All WPs are strictly sequential — see dependency chain below.

**Prompt Files**: Each work package references a matching prompt file in `/tasks/`. Lane status is stored in YAML frontmatter (`lane: planned|doing|for_review|done`).

---

## Phase A — Pre-work (Strictly Sequential)

---

## Work Package WP01: `--feature` → `--mission` CLI Flag Rename (Priority: P1) 🎯 MVP

**Goal**: Add `--mission` as the canonical flag across all 16 CLI entry points, preserve `--feature` as a backward-compatible hidden alias with a deprecation warning, and create the shared `resolve_mission_or_feature()` utility.
**Independent Test**: Run `spec-kitty agent workflow implement WP01 --mission 056-my-feature` — command works normally. Run with `--feature 056-my-feature` — command works and emits a deprecation warning. Run with both flags providing different values — clear error raised.
**Prompt**: `/tasks/WP01-feature-to-mission-flag-rename.md`

### Included Subtasks

- [ ] T001 Create `resolve_mission_or_feature(mission, feature)` utility in `src/specify_cli/cli/commands/_flag_utils.py`
- [ ] T002 Write ATDD acceptance tests in `tests/specify_cli/cli/commands/test_mission_flag_rename.py` (tests first — must fail before implementation)
- [ ] T003 Apply rename to top-level commands (8 files): `accept.py`, `implement.py`, `merge.py`, `lifecycle.py`, `next_cmd.py`, `research.py`, `validate_encoding.py`, `verify.py`
- [ ] T004 Apply rename to agent subcommands (6 files): `agent/__init__.py`, `agent/context.py`, `agent/feature.py`, `agent/status.py`, `agent/tasks.py`, `agent/workflow.py`
- [ ] T005 Update existing tests for affected commands to exercise both `--mission` and `--feature` code paths; verify deprecation warning fires correctly

### Implementation Notes

- Utility signature: `resolve_mission_or_feature(mission: str | None, feature: str | None) -> str | None`. Returns `mission` if set; returns `feature` with `typer.echo("⚠️ --feature is deprecated, use --mission instead", err=True)` if only feature is set; raises `typer.BadParameter` if both set with different values; returns `None` if neither set.
- Pattern for each command: replace `typer.Option("--feature", ...)` with two options: `--mission` (primary, visible) and `--feature` (hidden alias, `is_eager=False`, `hidden=True`). Call `resolve_mission_or_feature()` at the top of the command body.
- Update all help text strings to use "mission" terminology.
- Keep `--feature` fully functional — existing automation must not break (C-005).

### Parallel Opportunities

- T003 and T004 can be applied by a single implementer sequentially, or split to two implementers if the file surfaces are split cleanly. No cross-file dependencies within the batch.

### Dependencies

- None (first WP, no prerequisites).

### Risks & Mitigations

- Wide blast radius (14 files) → mechanical, identical change repeated; diff should be trivially reviewable.
- Missing an occurrence → test T002 covers all 4 acceptance scenarios; grep for remaining `typer.Option.*--feature` as final sanity check.

---

## Work Package WP02: Glossary Update for Mission Rename (Priority: P2)

**Goal**: Update canonical glossary entries so the `Feature` entry documents the CLI flag deprecation and `--feature` appears in `historical-terms.md` as a deprecated alias.
**Independent Test**: `grep "\\-\\-mission" glossary/contexts/orchestration.md` returns at least one line. `grep "\\-\\-feature" glossary/historical-terms.md` returns a dedicated deprecated-alias entry.
**Prompt**: `/tasks/WP02-glossary-update-mission-rename.md`

### Included Subtasks

- [ ] T006 Update `Feature` entry in `glossary/contexts/orchestration.md` — note CLI flag deprecation, canonical flag now `--mission`
- [ ] T007 Add `--feature` deprecated alias entry in `glossary/historical-terms.md`
- [ ] T008 Run `spec-kitty agent feature check-prerequisites --feature 056-...` and any available glossary integrity check to verify no broken cross-references

### Implementation Notes

- The `Feature` glossary entry should note: "The CLI flag `--feature` is deprecated as of 2.2.0. Use `--mission` instead. `--feature` remains a backward-compatible alias for one deprecation cycle."
- `historical-terms.md` entry should follow the existing deprecated-term pattern (check the file first).
- No source code changes in this WP.

### Parallel Opportunities

- All 3 subtasks are sequential (T008 validates T006/T007).

### Dependencies

- Depends on WP01 (Phase A gate: WP01 must be reviewed and merged first).

### Risks & Mitigations

- Glossary cross-reference breakage → T008 runs integrity check.

---

## Phase B — Core Profile Infrastructure (Strictly Sequential)

---

## Work Package WP03: Profile Inheritance — Merge-by-Default with Excluding (Priority: P1) 🎯 MVP

**Goal**: Change `AgentProfileRepository.resolve_profile()` list-field merge semantics from child-replaces-parent to union (no duplicates). Add `excluding` field to `AgentProfile` for selective removal of inherited fields or values. Fix missing-parent to raise a clear error instead of warning-and-returning.
**Independent Test**: Create a child profile with `specializes-from: implementer` that adds one directive; resolved profile contains parent + child directives (union). Create a child with `excluding: {directive-references: [DIRECTIVE_010]}`; resolved profile omits DIRECTIVE_010 from merged directives.
**Prompt**: `/tasks/WP03-profile-inheritance-merge-excluding.md`

### Included Subtasks

- [ ] T009 Write ATDD acceptance tests in `tests/doctrine/test_profile_inheritance.py` covering all 6 US-6 scenarios (tests first — must fail before implementation begins)
- [ ] T010 Add `excluding` field to `AgentProfile` model in `src/doctrine/agent_profiles/profile.py` — supports both field-level (`excluding: [directives]`) and value-level (`excluding: {directive-references: [DIRECTIVE_010]}`) forms
- [ ] T011 Update `resolve_profile()` in `repository.py` — change list-type field merge from child-replaces-parent to union (no duplicates): `directives`, `directive_references`, `capabilities`, `canonical_verbs`, `mode_defaults`
- [ ] T012 Apply `excluding` removals in `resolve_profile()` after union merge — remove specified fields or specific values from the resolved result
- [ ] T013 Fix missing-parent handling in `resolve_profile()`: change current warn-and-return to `raise KeyError(f"Profile '{profile_id}' references missing parent '{parent_id}'")`

### Implementation Notes

- Current merge in `shallow_merge()` uses child-replaces-parent for all fields. Need to distinguish: list fields → union; scalar/dict fields → keep existing shallow merge.
- `excluding` YAML schema: `excluding: [field_name]` (drop entire field) OR `excluding: {field_name: [value1, value2]}` (remove specific values from list field).
- Cycle detection already raises `ValueError` — no change needed there.
- Multi-level chains: apply union merge at each step (root → child → grandchild), then apply exclusions at each level, cascading down.
- ZOMBIES coverage required: Zero (no parent), One parent, Many-level chain, Boundary (excluding a value not in parent), Interface (return type), Exception (cycle → ValueError, missing parent → KeyError), Simple scenario (basic inherit).

### Parallel Opportunities

- T009 (tests) must run first and fail; T010-T013 implement against failing tests.
- T010 and T011 touch different parts of the codebase and can be developed in parallel by the same implementer (T010 = model, T011 = resolver).
- T012 depends on T010 (excluding field must exist on model before resolver can read it).

### Dependencies

- Depends on WP02 (Phase A must be complete before Phase B begins).

### Risks & Mitigations

- Existing profile tests may break if they relied on child-replaces-parent list semantics → run `pytest tests/doctrine/ -x` after T011 and fix any regressions before proceeding.
- Exclusion of nonexistent value should be silently ignored (not an error) per spec edge case.

---

## Work Package WP04: Generic-Agent Profile in `_proposed/` (Priority: P2)

**Goal**: Create the `generic-agent` profile YAML in `_proposed/` with a single DIRECTIVE_028 reference, valid schema, broad specialization. Verify it is NOT in `shipped/` (C-001).
**Independent Test**: `src/doctrine/agent_profiles/_proposed/generic-agent.agent.yaml` exists. `AgentProfileRepository.get("generic-agent")` returns the profile. Schema validation passes. File does NOT exist in `shipped/`.
**Prompt**: `/tasks/WP04-generic-agent-profile.md`

### Included Subtasks

- [ ] T014 Write ATDD acceptance tests in `tests/doctrine/test_generic_agent_profile.py` (3 US-5 scenarios: exists in _proposed with valid schema, DIRECTIVE_028 reference, NOT in shipped)
- [ ] T015 Create `src/doctrine/agent_profiles/_proposed/generic-agent.agent.yaml` — root profile, `primary_focus: "General-purpose task execution"`, single `directive-references` entry for DIRECTIVE_028, no `specializes-from`
- [ ] T016 Verify schema validation by running `AgentProfileRepository` validation against the new file; fix any validation errors; confirm `validate_hierarchy()` passes

### Implementation Notes

- Study an existing shipped profile (e.g., `implementer.agent.yaml`) for the exact YAML structure.
- `generic-agent` must meet C-004: pass existing agent-profile JSON schema validation including minimum one directive reference requirement.
- No `specializes-from` — this is a root profile that other profiles can specialize from.
- The `_proposed/` directory may need to be created if it doesn't exist yet (`ls src/doctrine/agent_profiles/`).
- `initialization-declaration` should be broad: "I am a general-purpose agent. I will execute the work package faithfully, using efficient local tooling (DIRECTIVE_028) and respecting the project's governance boundaries."

### Parallel Opportunities

- T014 first; T015 and T016 sequential.

### Dependencies

- Depends on WP03 (profile.py model must be stable before creating a profile that is validated against it).

### Risks & Mitigations

- Schema drift between `_proposed/` loader and `shipped/` loader → test T016 exercises the same `AgentProfileRepository` code path that workflow injection will use.

---

## Work Package WP05: Human-in-Charge Sentinel Profile (Priority: P1)

**Goal**: Add `sentinel` field to `AgentProfile`, create `human-in-charge.agent.yaml` in `_proposed/`, and render HiC WPs with a 👤 marker in kanban status output.
**Independent Test**: `human-in-charge.agent.yaml` exists in `_proposed/` with `sentinel: true`. `AgentProfileRepository.get("human-in-charge").sentinel` is `True`. `spec-kitty agent tasks status` shows 👤 before the WP ID when `agent_profile: human-in-charge` is set in WP frontmatter.
**Prompt**: `/tasks/WP05-human-in-charge-sentinel-profile.md`

### Included Subtasks

- [ ] T017 Write ATDD acceptance tests in `tests/doctrine/test_human_in_charge_profile.py` (sentinel in _proposed, schema valid, sentinel=True, not in shipped; kanban 👤 rendering for HiC WPs)
- [ ] T018 Add optional `sentinel: bool = False` field to `AgentProfile` model in `src/doctrine/agent_profiles/profile.py`
- [ ] T019 Create `src/doctrine/agent_profiles/_proposed/human-in-charge.agent.yaml` with `sentinel: true`, broad `primary_focus`, no `specializes-from`, no `directive-references`, no `initialization-declaration`
- [ ] T020 Add 👤 marker in kanban WP rendering — in `src/specify_cli/cli/commands/agent/status.py` (or wherever kanban rows are rendered), when a WP frontmatter `agent_profile` resolves to a sentinel profile, prepend 👤 to the WP ID display

### Implementation Notes

- `sentinel: bool = False` default means existing profiles are unaffected (no YAML change needed for shipped profiles).
- `human-in-charge.agent.yaml` must pass schema validation even with minimal fields — ensure `purpose`, `specialization`, `name`, `profile-id` are present (required fields). `initialization-declaration` may be empty or omitted if schema allows.
- Kanban rendering: the kanban loop reads WP frontmatter; add a step that, if `agent_profile` field is present, resolves it via `AgentProfileRepository` and checks `.sentinel`. If `True`, prefix the WP ID display with `👤`. This should be a soft failure — if the profile cannot be resolved, skip the marker silently.
- The glossary entry for "Human-in-Charge WP" was already added in a prior commit (architecture docs phase). No glossary work needed in this WP.

### Parallel Opportunities

- T017 first (ATDD). T018 and T019 can proceed in parallel (different files). T020 after T018 (needs sentinel field to exist).

### Dependencies

- Depends on WP04 (profile.py must be stable; `_proposed/` directory must exist).

### Risks & Mitigations

- Kanban resolution adds a `AgentProfileRepository` instantiation in the status render path — keep it lightweight; catch all exceptions and degrade gracefully (show WP without marker if resolution fails).

---

## Work Package WP06: Workflow Profile Injection (Priority: P1) 🎯 MVP

**Goal**: Add `_render_profile_context()` to `workflow.py`, inject the resolved agent profile identity fragment into the implement prompt, handle the sentinel skip path, the missing-profile error/warning paths, and wire `--allow-missing-profile` flag.
**Independent Test**: Run implement workflow on a WP with `agent_profile: implementer` — prompt output contains implementer's identity fragment. Run on a WP with `agent_profile: human-in-charge` — no identity injected, "Human-in-charge WP" message shown. Run on a WP with unresolvable profile without `--allow-missing-profile` — exit with error.
**Prompt**: `/tasks/WP06-workflow-profile-injection.md`

### Included Subtasks

- [ ] T021 Write ATDD acceptance tests in `tests/agent/cli/commands/test_workflow_profile_injection.py` (5 scenarios: implementer injection, architect injection, no-field → generic-agent default, human-in-charge → no injection, unresolvable + --allow-missing-profile)
- [ ] T022 Implement `_render_profile_context(repo_root, wp_frontmatter, allow_missing)` in `workflow.py` — reads `agent_profile` via `extract_scalar`, defaults to `"generic-agent"`, resolves via `AgentProfileRepository.resolve_profile()`
- [ ] T023 Implement sentinel check and fallback logic: `if profile.sentinel → return ""` (with log message); if missing + `allow_missing=True` → warn and return `""`; if missing + `allow_missing=False` → raise `typer.Exit(1)` with clear error
- [ ] T024 Add `--allow-missing-profile / --no-allow-missing-profile` flag to the `implement` command in `workflow.py`
- [ ] T025 Wire `_render_profile_context()` into the implement command output — append profile fragment to prompt lines after the constitution context block (following the `_render_constitution_context()` call at line ~576)

### Implementation Notes

- `_render_profile_context` return value is a markdown string (or empty string). Pattern mirrors `_render_constitution_context()` exactly.
- Profile identity fragment format: `## Agent Identity\n**Profile**: {name}\n**Role**: {role}\n**Purpose**: {purpose}\n**Specialization**: {primary_focus}\n**Directives**: {directive refs}\n\n{initialization_declaration}`.
- `AgentProfileRepository` must be instantiated with `repo_root` so it searches both `shipped/` and `_proposed/` (and project overrides). Check existing usage patterns in the codebase.
- When `generic-agent` is not yet promoted and `agent_profile` is absent, the "not found" warning path fires (NFR-003 backward compatibility — projects without doctrine stack continue to work).
- WP frontmatter is already parsed at the point where constitution context is injected — reuse the existing `wp.frontmatter` dict.

### Parallel Opportunities

- T021 first (ATDD). T022-T025 sequential.

### Dependencies

- Depends on WP05 (sentinel field on AgentProfile must exist; human-in-charge profile must be resolvable; generic-agent profile should exist for default path).

### Risks & Mitigations

- Performance: profile resolution adds latency — keep under NFR-002 500ms. `AgentProfileRepository` reads YAML files; single profile resolution should be well under 50ms.
- Profile not found when generic-agent not promoted: this is the expected path for fresh projects without doctrine; the warning path ensures backward compat (NFR-003).

---

## Phase C — Init-Time Doctrine (Strictly Sequential)

---

## Work Package WP07: Constitution Defaults File + Init Integration (Priority: P1) 🎯 MVP

**Goal**: Create `defaults.yaml` for one-click doctrine setup, wire it into `init.py` with accept/configure/skip paths, implement resume/restart checkpoint for interrupted init, and deliver the init-doctrine user journey document.
**Independent Test**: Run `spec-kitty init` on a fresh project → prompted for doctrine stack → accept defaults → `.kittify/constitution/constitution.md` exists. Run `spec-kitty init --non-interactive` → constitution generated automatically. Interrupt init mid-interview, re-run → offered resume or restart.
**Prompt**: `/tasks/WP07-constitution-defaults-init-integration.md`

### Included Subtasks

- [x] T026 Write ATDD acceptance tests in `tests/specify_cli/cli/commands/test_init_doctrine.py` (US-1 scenarios 1-3 + US-2 scenarios 1-4 including the resume-after-interrupt scenario)
- [x] T027 Create `src/doctrine/constitution/defaults.yaml` with predefined paradigm, directive, and tool selections that represent sensible defaults for a new project
- [x] T028 Add doctrine stack choice step to `init.py` (after `.kittify/` skeleton creation) — "Accept defaults" path: load `defaults.yaml`, call `constitution generate` with those selections, populate `.kittify/constitution/`
- [x] T029 Add "Configure manually" path to `init.py` — present interview depth choice (minimal/comprehensive), inform user about what the interview does and how to customize later (FR-015), delegate to existing `constitution interview` flow inline
- [x] T030 Implement skip-if-exists (FR-004) and `--non-interactive` auto-defaults (FR-005) paths in `init.py`
- [x] T031 Implement init resume/restart checkpoint: on init interrupt (e.g., `KeyboardInterrupt`), write progress to `.kittify/.init-checkpoint.yaml`; on next invocation detect checkpoint and prompt "Resume previous session? [Y]es / [N]o (start over)"; restart discards checkpoint (FR-020)
- [x] T032 Write user journey document in `architecture/2.x/user_journey/init-doctrine-flow.md` — full flow diagram/narrative covering: accept defaults, configure manually (minimal/comprehensive), skip existing, non-interactive, resume/restart paths

### Implementation Notes

- The existing `init.py` already creates `.kittify/constitution/` (line ~191) and calls `copy_constitution_templates()` (line ~946). The new step slots in after skeleton creation and before or after those calls — inspect the exact flow first.
- `defaults.yaml` should select a minimal practical set: 2-3 paradigms, 3-5 directives (including DIRECTIVE_028), standard tool config. Study `src/constitution/interview.py` and `src/constitution/compiler.py` to understand the input format.
- Checkpoint file format: `{ "phase": "interview" | "defaults", "step": int, "answers_so_far": {...}, "started_at": ISO timestamp }`. Store in `.kittify/.init-checkpoint.yaml`.
- `constitution interview` and `constitution generate` commands must continue to work independently (C-002).
- `--non-interactive` path must respect NFR-001: ≤2s overhead.

### Parallel Opportunities

- T026 (ATDD) first. T027 and T028 can proceed in parallel (different files). T029 requires T028 to be stable. T030, T031 extend T028/T029. T032 is independent documentation.

### Dependencies

- Depends on WP06 (Phase B must be complete before Phase C begins).

### Risks & Mitigations

- `init.py` is 1400 lines — read the full function signature and flow before editing.
- Checkpoint race condition: ensure checkpoint is written atomically (use `atomic_write` from `kernel.atomic`).

---

## Work Package WP08: Profile-Context Upgrade Migration (Priority: P2)

**Goal**: Create an upgrade migration that deploys `profile-context.md` to all configured agent command directories. Migration must be idempotent and config-aware.
**Independent Test**: Run `spec-kitty upgrade` on a project with claude and opencode configured → `profile-context.md` exists in both `.claude/commands/` and `.opencode/command/`. Run upgrade again → no duplicate, no error.
**Prompt**: `/tasks/WP08-profile-context-upgrade-migration.md`

### Included Subtasks

- [x] T033 Write ATDD acceptance tests in `tests/specify_cli/test_profile_context_migration.py` (US-4 scenarios: migration deploys to configured agents, skips unconfigured agents, idempotent on re-run, correct template content deployed)
- [x] T034 Create `src/specify_cli/upgrade/migrations/m_2_2_0_profile_context_deployment.py` — uses `get_agent_dirs_for_project()` from `m_0_9_1_complete_lane_migration`, copies `profile-context.md` from `src/doctrine/templates/command-templates/profile-context.md` to each configured agent's command directory
- [x] T035 Make migration idempotent: check if destination file already exists; if it does and content matches source, skip; if stale (content differs), overwrite and log
- [x] T036 Register migration and verify it runs during `spec-kitty upgrade` — study `__init__.py` autodiscovery pattern; ensure file naming convention is followed (`m_{version}_{name}.py`)

### Implementation Notes

- Pattern: follow `m_2_0_11_install_skills.py` closely — same `@MigrationRegistry.register`, same `BaseMigration` inheritance, same `get_agent_dirs_for_project()` call.
- Skip if directory doesn't exist (respect user deletions, per CLAUDE.md guidance).
- Template destination file name: `spec-kitty.profile-context.md` (matching the slash command convention for other commands).
- Test with at least `.claude/commands/` and `.opencode/command/` (common agents per CLAUDE.md testing guidance).

### Parallel Opportunities

- T033 first. T034 and T035 are tightly coupled — implement together. T036 after T034.

### Dependencies

- Depends on WP07 (Phase C sequential).

### Risks & Mitigations

- Agent directory naming inconsistencies (`command` vs `commands`) → use `get_agent_dirs_for_project()` which handles this correctly.

---

## Work Package WP09: Task Template Role Hints + Profile Suggestion (Priority: P2)

**Goal**: Add `agent_role` hints to mission task templates, implement profile suggestion logic in task generation, and update `finalize-tasks` to write suggested `agent_profile` into WP frontmatter for user confirmation.
**Independent Test**: Generate tasks for a software-dev mission — each generated WP frontmatter contains `agent_profile` with a suggested profile based on the WP's role. During `finalize-tasks`, user is shown the suggested profiles and can confirm or override.
**Prompt**: `/tasks/WP09-task-template-role-hints-profile-suggestion.md`

### Included Subtasks

- [x] T037 Write acceptance tests in `tests/specify_cli/test_task_profile_suggestion.py` (FR-013/FR-014: role hint in template, suggestion written to WP frontmatter, user confirmation in finalize)
- [x] T038 Add `agent_role` field to mission template task definitions in YAML mission configs — update software-dev, research, documentation, and plan mission templates with role hints per task type (implementer, reviewer, planner, researcher, writer, curator)
- [x] T039 Update task generation logic: read `agent_role` from mission template, determine the most appropriate concrete `agent_profile` based on role hint + WP task content, write the suggestion into generated WP frontmatter as `agent_profile`
- [x] T040 Update `finalize-tasks` to display a profile suggestion confirmation step — show each WP's suggested `agent_profile`, allow user to confirm (`y`), override (type a different profile name), or skip (leave blank = no profile)
- [x] T041 Update mission templates for software-dev, research, documentation, plan to include `agent_role` hints for all standard task types (implement→implementer, review→reviewer, plan→planner, research→researcher, document→writer)

### Implementation Notes

- `agent_role` in template is a hint (human-readable), not a hard binding. The suggestion step translates hint → concrete profile name via a simple mapping table: `{"implementer": "implementer", "reviewer": "reviewer", "planner": "planner", "researcher": "researcher", "writer": "designer", "curator": "curator"}`.
- Task generation logic: find the mission template config YAML, read `agent_role` from the relevant task section, look up the profile mapping, write `agent_profile: <profile-name>` into the WP `.md` frontmatter.
- `finalize-tasks` user confirmation: only prompt if `agent_profile` was auto-populated (not manually set). If `--json` flag is used, skip interactive confirmation and keep the suggestion as-is.
- Do NOT block finalize-tasks if the suggested profile doesn't exist yet — it may be in `_proposed/` or not yet created. Profile resolution happens at implement time, not at task-generation time.

### Parallel Opportunities

- T037 first (ATDD). T038 and T039 should be developed together. T040 and T041 extend T038/T039.

### Dependencies

- Depends on WP08 (Phase C sequential).

### Risks & Mitigations

- Task generation logic location: this may span multiple files (template rendering, finalize-tasks command). Read `agent/feature.py` `finalize-tasks` implementation first to understand the full pipeline.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03 → WP04 → WP05 → WP06 → WP07 → WP08 → WP09 (strictly sequential — no parallel waves in this feature)
- **Phase gates**: WP02 completes Phase A (both WPs reviewed, merged, worktrees cleaned). WP06 completes Phase B. WP09 completes Phase C.
- **MVP Scope**: WP01 + WP03 + WP04 + WP06 + WP07 are the P1 MVPs. WP02, WP05, WP08, WP09 are P2 polish/extension.
- **Feature flag availability**: `--mission` canonical flag is in WP01. All subsequent WPs use `--mission` in their implementation.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | `resolve_mission_or_feature()` utility | WP01 | P1 | No |
| T002 | ATDD tests for flag rename | WP01 | P1 | No (first) |
| T003 | Apply rename to 8 top-level commands | WP01 | P1 | Yes (with T004) |
| T004 | Apply rename to 6 agent subcommands | WP01 | P1 | Yes (with T003) |
| T005 | Update existing tests for both flags | WP01 | P1 | No |
| T006 | Update `Feature` glossary entry | WP02 | P2 | Yes |
| T007 | Add `--feature` to historical-terms.md | WP02 | P2 | Yes |
| T008 | Glossary integrity check | WP02 | P2 | No |
| T009 | ATDD tests for profile inheritance | WP03 | P1 | No (first) |
| T010 | Add `excluding` field to AgentProfile | WP03 | P1 | Yes (with T011) |
| T011 | Union merge for list fields | WP03 | P1 | Yes (with T010) |
| T012 | Apply excluding removals post-merge | WP03 | P1 | No |
| T013 | Fix missing-parent → raise KeyError | WP03 | P1 | No |
| T014 | ATDD tests for generic-agent | WP04 | P2 | No (first) |
| T015 | Create generic-agent.agent.yaml | WP04 | P2 | No |
| T016 | Verify schema validation | WP04 | P2 | No |
| T017 | ATDD tests for HiC sentinel profile | WP05 | P1 | No (first) |
| T018 | Add `sentinel` field to AgentProfile | WP05 | P1 | Yes (with T019) |
| T019 | Create human-in-charge.agent.yaml | WP05 | P1 | Yes (with T018) |
| T020 | 👤 kanban marker for HiC WPs | WP05 | P1 | No |
| T021 | ATDD tests for workflow injection | WP06 | P1 | No (first) |
| T022 | Implement `_render_profile_context()` | WP06 | P1 | No |
| T023 | Sentinel check + fallback logic | WP06 | P1 | No |
| T024 | `--allow-missing-profile` flag | WP06 | P1 | No |
| T025 | Wire profile context into implement output | WP06 | P1 | No |
| T026 | ATDD tests for init doctrine flow | WP07 | P1 | No (first) |
| T027 | Create doctrine/constitution/defaults.yaml | WP07 | P1 | Yes (with T028) |
| T028 | Accept-defaults path in init.py | WP07 | P1 | No |
| T029 | Configure-manually path in init.py | WP07 | P1 | No |
| T030 | Skip-if-exists + non-interactive paths | WP07 | P1 | No |
| T031 | Init resume/restart checkpoint | WP07 | P1 | No |
| T032 | User journey doc for init-doctrine flow | WP07 | P1 | Yes |
| T033 | ATDD tests for profile-context migration | WP08 | P2 | No (first) |
| T034 | Create migration m_2_2_0_*.py | WP08 | P2 | No |
| T035 | Make migration idempotent | WP08 | P2 | No |
| T036 | Register migration in upgrade system | WP08 | P2 | No |
| T037 | Acceptance tests for profile suggestion | WP09 | P2 | No (first) |
| T038 | Add agent_role to mission templates (YAML) | WP09 | P2 | Yes (with T039) |
| T039 | Profile suggestion in task generation | WP09 | P2 | Yes (with T038) |
| T040 | Profile confirmation step in finalize-tasks | WP09 | P2 | No |
| T041 | Update mission templates with role hints | WP09 | P2 | No |

<!-- status-model:start -->
## Canonical Status (Generated)

- WP07: done
- WP08: done
- WP09: done
<!-- status-model:end -->
