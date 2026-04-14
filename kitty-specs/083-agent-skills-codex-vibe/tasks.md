# Tasks: Agent Skills Support for Codex and Vibe

**Feature**: 083-agent-skills-codex-vibe
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Research**: [research.md](./research.md)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|---------|
| T001 | Create `manifest_store.py` with `SkillsManifest` / `ManifestEntry` dataclasses and `ManifestError` | WP01 | — |
| T002 | Implement schema validation on `load()` using `skills-manifest.schema.json` | WP01 | — |
| T003 | Implement atomic save: sorted keys, 2-space indent, trailing newline, temp-file + rename | WP01 | — |
| T004 | Implement `fingerprint()` SHA-256 helper | WP01 | [P] |
| T005 | Unit tests — round-trip identity, schema rejection, atomic-save durability, fingerprint stability | WP01 | — |
| T006 | Create `command_renderer.py` with `RenderedSkill` dataclass and `SkillRenderError` | WP02 | — |
| T007 | Implement `## User Input` block identifier (heading through next same/shallower heading) | WP02 | — |
| T008 | Implement User-Input block rewrite to turn-content instruction; lock text in constants module | WP02 | — |
| T009 | Implement `$ARGUMENTS` stray-token guard raising `SkillRenderError("stray_arguments_token", ...)` | WP02 | — |
| T010 | Implement frontmatter builder (sorted, deterministic) with `name`, `description`, `user-invocable` | WP02 | [P] |
| T011 | Snapshot tests — render all 16 canonical commands × 2 agents; byte-identity across two runs; stray-token coverage | WP02 | — |
| T012 | Create `command_installer.py` with `InstallReport` / `RemoveReport` / `VerifyReport` | WP03 | — |
| T013 | Implement `install()` — idempotent, atomic file writes, ref-count add, manifest update | WP03 | — |
| T014 | Implement `remove()` — ref-count decrement; physical delete only when `agents` empties; preserve co-tenants and parent dir if shared | WP03 | — |
| T015 | Implement `verify()` — drift, orphans, gaps | WP03 | [P] |
| T016 | Coexistence tests — seed `.agents/skills/` with 3 third-party dirs, run install/remove cycles, assert byte-identity | WP03 | — |
| T017 | Drift integration test — mutate installed file, assert `verify()` reports path | WP03 | — |
| T018 | Edit `core/config.py` — add `vibe` to `AI_CHOICES`, `AGENT_TOOL_REQUIREMENTS`, `AGENT_SKILL_CONFIG`; drop `codex` from `AGENT_COMMAND_CONFIG` | WP04 | — |
| T019 | Edit `agent_utils/directories.py` — remove `.codex` prompts tuple; update `AGENT_DIR_TO_KEY` | WP04 | [P] |
| T020 | Edit `runtime/agent_commands.py` — route `codex` and `vibe` through `command_installer.install()` | WP04 | — |
| T021 | Edit `cli/commands/agent/config.py` — `remove` honours manifest for shared-root agents via `command_installer.remove()` | WP04 | — |
| T022 | Unit tests — registry shape, routing with mock installer | WP04 | — |
| T023 | Edit `cli/commands/init.py` — accept `--ai vibe`, invoke installer, print vibe next-steps | WP05 | — |
| T024 | Edit `cli/commands/verify.py` — detect `vibe` binary with existing output shape | WP05 | [P] |
| T025 | Edit `gitignore_manager.py` — protect `.vibe/` via existing helper | WP05 | [P] |
| T026 | Integration test — `init --ai vibe --non-interactive` end-to-end | WP05 | — |
| T027 | Integration tests — `verify-setup` detects vibe; `agent config add/remove vibe` | WP05 | — |
| T028 | Create migration `m_3_2_0_codex_to_skills.py` with `LegacyCodexPrompt` classifier | WP06 | — |
| T029 | Embed known prior-release hashes for each canonical command in `_legacy_codex_hashes.py` | WP06 | [P] |
| T030 | Implement migration `apply()`: classify → install skills → delete unedited → preserve edited + notice | WP06 | — |
| T031 | Migration integration tests against 4 fixture variants (clean, owned-unedited-only, mixed, user-edited) | WP06 | — |
| T032 | Register migration in version table; no-op guard when `codex` not in `agents.available` | WP06 | — |
| T033 | Capture pre-mission baseline snapshot for the 12 non-migrated agents' command output | WP07 | — |
| T034 | Regression test — zero-diff assertion vs baseline for all 12 non-migrated agents × 16 commands | WP07 | — |
| T035 | Update README supported-tools table — add Vibe; reword Codex row to note Agent Skills delivery | WP07 | [P] |
| T036 | Update CLAUDE.md — add Vibe to Supported AI Agents; document new `src/specify_cli/skills/command_*.py` modules | WP07 | [P] |
| T037 | Validate quickstart.md end-to-end against a smoke-test project | WP07 | — |

Totals: 37 subtasks across 7 work packages. 13 marked `[P]` (parallel-safe within their WP).

## Work Package Roadmap

Execution order and dependencies:

```
WP01 ──┐
       ├─► WP03 ──► WP04 ──► WP05 ──► WP06 ──► WP07
WP02 ──┘
```

- **WP01** and **WP02** have no mission-internal dependencies and can start in parallel on day 1.
- **WP03** depends on both (installer uses the manifest store and the renderer).
- **WP04** is the registry/routing seam; it needs WP03 to route to.
- **WP05** wires up the CLI surfaces and user-visible behavior for `vibe`; needs WP04 for the registry to accept `vibe`.
- **WP06** is the Codex legacy migration; needs the installer and the Codex registry change in place.
- **WP07** closes out with regression snapshots and docs; needs everything landed to produce accurate docs and to assert parity.

---

## WP01 — Skills Manifest Store and Schema Plumbing

**Priority**: P0 (foundation)
**Requirement Refs**: FR-007
**Size**: 5 subtasks, ~350 lines
**Independent test**: `pytest tests/specify_cli/skills/test_manifest_store.py` passes; round-trip of a populated manifest produces a byte-identical JSON file; malformed input is rejected with a structured `ManifestError`.

**Goal**: Deliver a pure, tested persistence layer for `.kittify/skills-manifest.json`. No behavior depends on the renderer or installer yet.

**Subtasks**:

- [x] T001 Create `src/specify_cli/skills/manifest_store.py` with dataclasses and `ManifestError` (WP01)
- [x] T002 Implement schema validation on `load()` against the contract schema (WP01)
- [x] T003 Implement atomic save with deterministic formatting (WP01)
- [x] T004 Implement `fingerprint()` SHA-256 helper (WP01)
- [x] T005 Unit tests — round-trip, schema rejection, atomic-save durability, fingerprint stability (WP01)

**Dependencies**: none.

**Prompt file**: `tasks/WP01-skills-manifest-store.md`

---

## WP02 — Command-Skill Renderer

**Priority**: P0 (foundation)
**Requirement Refs**: FR-004, FR-005, NFR-004
**Size**: 6 subtasks, ~450 lines
**Independent test**: `pytest tests/specify_cli/skills/test_command_renderer.py` passes; rendering any canonical command template twice produces byte-identical output; a template with a stray `$ARGUMENTS` outside `## User Input` raises `SkillRenderError`.

**Goal**: Deliver the pure renderer that turns `command-templates/<command>.md` into a `RenderedSkill` (frontmatter + body) for Codex and Vibe, with the User-Input block rewritten for turn-content delivery. Enforces the no-stray-`$ARGUMENTS` guard at render time.

**Subtasks**:

- [x] T006 Create `command_renderer.py` with `RenderedSkill` and `SkillRenderError` (WP02)
- [x] T007 Implement `## User Input` block identifier (WP02)
- [x] T008 Implement User-Input block rewrite; lock text in constants (WP02)
- [x] T009 Implement `$ARGUMENTS` stray-token guard (WP02)
- [x] T010 Implement frontmatter builder (sorted, deterministic) (WP02)
- [x] T011 Snapshot tests — 16 commands × 2 agents × 2 runs; stray-token coverage (WP02)

**Dependencies**: none.

**Prompt file**: `tasks/WP02-command-skill-renderer.md`

---

## WP03 — Command-Skill Installer

**Priority**: P0 (foundation)
**Requirement Refs**: FR-006, FR-008, NFR-002
**Size**: 6 subtasks, ~500 lines
**Independent test**: `pytest tests/specify_cli/skills/test_command_installer.py` passes; seeding `.agents/skills/` with three third-party directories and then running `install("codex")` + `install("vibe")` + `remove("codex")` leaves every third-party file byte-identical and all manifest entries with `agents=["vibe"]`.

**Goal**: Deliver the installer that owns the mutations of `.agents/skills/` with additive writes, reference-counted removes, third-party safety, and a `verify()` surface for doctor integration.

**Subtasks**:

- [ ] T012 Create `command_installer.py` with report dataclasses (WP03)
- [ ] T013 Implement `install()` (WP03)
- [ ] T014 Implement `remove()` with ref-count semantics (WP03)
- [ ] T015 Implement `verify()` (WP03)
- [ ] T016 Coexistence tests with 3 third-party dirs (WP03)
- [ ] T017 Drift integration test (WP03)

**Dependencies**: WP01, WP02.

**Prompt file**: `tasks/WP03-command-skill-installer.md`

---

## WP04 — Registry Wiring and Runtime Routing

**Priority**: P1 (enables CLI surface)
**Requirement Refs**: FR-001, FR-002, FR-011, FR-013
**Size**: 5 subtasks, ~350 lines
**Independent test**: `pytest tests/specify_cli/core/test_config_registry.py tests/specify_cli/runtime/test_agent_commands_routing.py` passes; `AI_CHOICES["vibe"]` is present; `AGENT_COMMAND_CONFIG` no longer contains `"codex"`; `runtime.agent_commands` dispatches `codex` and `vibe` to the installer while leaving every other agent's call site unchanged.

**Goal**: Wire the new installer into the existing runtime so that any code path that currently writes commands for `codex` or `vibe` instead goes through `command_installer.install()`. Expose `vibe` to `init`, config, and verify surfaces through registry changes.

**Subtasks**:

- [ ] T018 Edit `core/config.py` — add `vibe`; drop `codex` from command config (WP04)
- [ ] T019 Edit `agent_utils/directories.py` — adjust registries (WP04)
- [ ] T020 Edit `runtime/agent_commands.py` — route codex + vibe to installer (WP04)
- [ ] T021 Edit `cli/commands/agent/config.py` — `remove` uses `command_installer.remove()` (WP04)
- [ ] T022 Unit tests — registry shape and routing (WP04)

**Dependencies**: WP03.

**Prompt file**: `tasks/WP04-registry-and-runtime-routing.md`

---

## WP05 — Vibe CLI Surface (init, verify, gitignore)

**Priority**: P1 (user-visible)
**Requirement Refs**: FR-001, FR-003, FR-009, FR-010
**Size**: 5 subtasks, ~400 lines
**Independent test**: `pytest tests/specify_cli/cli/commands/test_init_vibe.py tests/specify_cli/cli/commands/test_verify_vibe.py tests/specify_cli/cli/commands/test_agent_config_vibe.py` passes; `spec-kitty init --ai vibe --non-interactive` on an empty tmpdir writes the manifest, 16 skill packages, protects `.vibe/` in `.gitignore`, and exits 0.

**Goal**: Make `vibe` a first-class CLI citizen end-to-end. Init accepts `--ai vibe`, verify-setup detects the `vibe` binary, gitignore protects the Vibe runtime directory, and `agent config` round-trips the agent.

**Subtasks**:

- [ ] T023 Edit `cli/commands/init.py` — accept `--ai vibe` and print vibe-specific next steps (WP05)
- [ ] T024 Edit `cli/commands/verify.py` — detect `vibe` binary (WP05)
- [ ] T025 Edit `gitignore_manager.py` — protect `.vibe/` (WP05)
- [ ] T026 Integration test — `init --ai vibe --non-interactive` end-to-end (WP05)
- [ ] T027 Integration tests — verify-setup detects vibe; `agent config add/remove vibe` (WP05)

**Dependencies**: WP04.

**Prompt file**: `tasks/WP05-vibe-cli-surface.md`

---

## WP06 — Codex Legacy Migration

**Priority**: P1 (zero-touch upgrade)
**Requirement Refs**: FR-012, NFR-003
**Size**: 5 subtasks, ~500 lines
**Independent test**: `pytest tests/specify_cli/upgrade/test_m_3_2_0_codex_to_skills.py` passes against all four fixture variants; after migration, `.codex/prompts/spec-kitty.*.md` files that matched the known prior-release hash are gone, user-edited variants are preserved with a printed notice, and `.agents/skills/spec-kitty.<command>/SKILL.md` is installed for every canonical command.

**Goal**: Deliver the one-shot upgrade migration that moves every existing Codex user from `.codex/prompts/` to `.agents/skills/` with zero manual steps. Preserve user edits, never touch third-party files, and integrate cleanly with the existing migration framework.

**Subtasks**:

- [ ] T028 Create `m_3_2_0_codex_to_skills.py` with `LegacyCodexPrompt` classifier (WP06)
- [ ] T029 Embed known prior-release hashes in `_legacy_codex_hashes.py` (WP06)
- [ ] T030 Implement `apply()` — classify, install, delete unedited, preserve edited (WP06)
- [ ] T031 Migration integration tests against 4 fixture variants (WP06)
- [ ] T032 Register migration; no-op guard when codex not in agents.available (WP06)

**Dependencies**: WP04, WP05 (the installer and registry must be live for the migration to install skills and route correctly).

**Prompt file**: `tasks/WP06-codex-legacy-migration.md`

---

## WP07 — Regression Snapshots and Documentation

**Priority**: P2 (ships the release)
**Requirement Refs**: FR-014, FR-015, FR-016, NFR-005
**Size**: 5 subtasks, ~350 lines
**Independent test**: `pytest tests/specify_cli/regression/test_twelve_agent_parity.py` passes with zero diff vs captured baseline; README and CLAUDE.md reflect the Vibe + Codex integration; quickstart.md walkthrough succeeds against a smoke-test project.

**Goal**: Lock in NFR-005 (the twelve non-migrated agents are byte-identical) with a regression snapshot, and ship the documentation updates that let users actually find Vibe support in the next release.

**Subtasks**:

- [ ] T033 Capture pre-mission baseline snapshot for 12 non-migrated agents (WP07)
- [ ] T034 Regression test — zero-diff assertion across all 12 agents × 16 commands (WP07)
- [ ] T035 Update README supported-tools table (WP07)
- [ ] T036 Update CLAUDE.md — Vibe + new module references (WP07)
- [ ] T037 Validate quickstart.md end-to-end (WP07)

**Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06.

**Prompt file**: `tasks/WP07-regression-and-docs.md`

---

## Parallelization Notes

- **Phase 1 (parallel)**: WP01 and WP02 have no internal dependencies. Two agents can start simultaneously in lane A and lane B.
- **Phase 2 (serial)**: WP03 joins A+B, then WP04 → WP05 → WP06 each land on `main` before the next begins.
- **Phase 3 (close-out)**: WP07 is the final lane — it captures the baseline against pre-mission `main` early (T033 could be scheduled at mission start to lock the baseline before any changes land) but the regression assertion and docs run last.

## MVP Scope Recommendation

The minimum shippable slice is **WP01 → WP02 → WP03 → WP04 → WP05**. That delivers Vibe as a new supported agent. WP06 (Codex migration) and WP07 (regression + docs) are required for the *announcement-worthy* release and must land in the same ship.

## Next Command

Run `spec-kitty agent feature finalize-tasks --feature 083-agent-skills-codex-vibe --json` to parse dependencies, validate ownership, and commit.

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: done
- WP02: done
<!-- status-model:end -->
