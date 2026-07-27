# Tasks: Agent Profile Projection and Plugin Production Pipeline

**Mission:** agent-profile-projection-plugin-production-01KV3NGS
**Mission ID:** 01KV3NGSDCJ272573TF6T6NWDW
**Branch:** feat/agent-profile-projection-plugin-production
**Generated:** 2026-06-14

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Audit `SurfaceRepairService.repair()` and extract `run_surface_repair()` helper for init/upgrade callers | WP01 | |
| T002 | Implement `DriftPolicySummary` dataclass; wire Missing→auto-create and Stale→auto-repair rules | WP01 | |
| T003 | Implement drift-protection policy (Rules 3-5): interactive prompt, non-interactive report-only, `--repair-drift=overwrite` | WP01 | |
| T004 | Wire `run_surface_repair()` into `spec-kitty init` post-agent-config-write with summary output | WP01 | |
| T005 | Wire `run_surface_repair()` into `spec-kitty upgrade` post-migrations with summary output; verify idempotency | WP01 | |
| T006 | Add `tomli-w` to dependencies; implement `CodexProfileRenderer.render()` producing valid TOML | WP02 | [P] |
| T007 | Implement `CodexProfileRenderer.can_render()`, `output_path()`, `format_key`; add optional-field passthrough | WP02 | [P] |
| T008 | Register `CodexProfileRenderer` in renderer registry; update `FORMAT_CODEX_AGENT` constant | WP02 | [P] |
| T009 | Verify `doctor tool-surfaces --kind agent-profile` no longer reports `research_gap` for `codex` | WP02 | [P] |
| T010 | Confirm Amazon Q CLI agent format; implement `AmazonQProfileRenderer` targeting user-global path | WP03 | [P] |
| T011 | Confirm Augment Code subagent format; implement `AugmentProfileRenderer` for `.augment/agents/<id>.md` | WP03 | [P] |
| T012 | Build `HarnessCapabilityRecord`; register Windsurf/Cursor/Kiro/Gemini/Qwen/OpenCode/Kilocode as `not_applicable` with reasons | WP03 | [P] |
| T013 | Update `AgentProfilesProvider` to emit per-harness `not_applicable` findings from capability registry | WP03 | [P] |
| T014 | Verify `doctor tool-surfaces --kind agent-profile --json` emits exactly the six valid statuses | WP03 | [P] |
| T015 | Scaffold `spec-kitty plugin build --target <target>` CLI command with build context and output dir logic | WP04 | |
| T016 | Generate `.claude-plugin/plugin.json` with real version from `importlib.metadata`; validate semver | WP04 | |
| T017 | Copy canonical command-skill set (≥15 skills) to `skills/` in bundle | WP04 | |
| T018 | Copy built-in agent profile Markdown files to `agents/` in bundle | WP04 | |
| T019 | Run `claude plugin validate --strict` at end of build and surface errors clearly | WP04 | |
| T020 | Generate `bin/spec-kitty-wrapper` (bash) + `spec-kitty-wrapper.cmd` (Windows) with PATH-check + `uvx` fallback | WP05 | [P] |
| T021 | Add `.github/workflows/plugin-validate.yml` CI job; install Claude CLI, build, validate | WP05 | [P] |
| T022 | Generate `marketplace.json` for git-based distribution; document `claude plugin marketplace add` install path | WP05 | [P] |
| T023 | Add `docs/how-to/install-claude-code-plugin.md` covering marketplace and `--plugin-dir` dev install | WP05 | [P] |
| T024 | Scaffold `spec-kitty plugin build --target codex` path; generate `.codex-plugin/plugin.json` | WP06 | [P] |
| T025 | Validate Codex plugin.json: `hooks` key absent, `agents` key absent, all required interface fields present | WP06 | [P] |
| T026 | Copy command-skill set to `skills/` in Codex bundle; include `hooks/` by filesystem presence only | WP06 | [P] |
| T027 | Generate Codex `marketplace.json` for repo-local install via `codex plugin marketplace add` | WP06 | [P] |
| T028 | Repair stale command-skill manifests (11→canonical count) following safe-stale policy during upgrade | WP07 | |
| T029 | Apply drift policy to drifted `SKILL.md` files in `.agents/skills/`; prompt/report-only path | WP07 | |
| T030 | Detect and remove unsafe symlink artifacts (e.g., `.agents/skills/spec-kitty.advise`) during upgrade | WP07 | |
| T031 | Remove `roo` from `AI_CHOICES` in `src/specify_cli/core/config.py` and from `AGENT_DIRS` in migration module | WP07 | |
| T032 | Emit Roo Code deprecation notice when `.roo/` detected during upgrade; preserve directory | WP07 | |
| T033 | Remove `roo` from `.kittify/config.yaml` when present; include in upgrade summary | WP07 | |
| T034 | Update `README.md` and `docs/` to remove Roo Code from Supported AI Agents list; note shutdown date | WP07 | |
| T035 | Unit tests for `ClaudeCodeProfileRenderer`: output path, YAML frontmatter fields, provenance footer, idempotent re-render | WP08 | [P] |
| T036 | Unit tests for `CodexProfileRenderer`: TOML validity, all three required fields, output path, optional-field passthrough | WP08 | [P] |
| T037 | Unit tests for `CopilotProfileRenderer`: file extension `.agent.md` (not `.chatmode.md`), output path | WP08 | [P] |
| T037b | Unit tests for `AmazonQProfileRenderer` (user-global path, JSON) and `AugmentProfileRenderer` (project-local, Markdown+frontmatter) | WP08 | [P] |
| T038 | Parametric test covering all five renderers against a shared fixture profile | WP08 | [P] |
| T039 | Verify ≥90% branch coverage on `profiles/renderers.py` and each new renderer module | WP08 | [P] |
| T040 | Integration tests for `init`/`upgrade` surface wiring: missing created, stale repaired, drifted reported-only in `--yes` | WP09 | |
| T041 | rc44-era migration acceptance fixture: `claude`+`codex` project, 11-entry manifest, no profiles → `upgrade --yes` heals all | WP09 | |
| T042 | `test_drift_policy.py` parametric test covering Rules 1-5 from drift-policy.md contract | WP09 | |
| T043 | Update `test_migration_compat.py` doctor JSON stability contract to include `agent_profile` surface kinds in frozen baseline | WP09 | |
| T044 | Full test suite pass: `mypy --strict` on changed modules, `ruff check`, `pytest` at ≥90% coverage on new paths | WP09 | |

---

## Work Packages

### WP01 — Surface Repair Wiring into Init/Upgrade

**Priority:** Critical (blocks WP02, WP03, WP07, WP08, WP09)
**Estimated prompt size:** ~380 lines
**Execution mode:** code_change
**Dependencies:** none

**Goal:** Make `spec-kitty init` and `spec-kitty upgrade` call the `SurfaceRepairService` after all agent configuration is written, applying the full 6-rule drift policy (auto-create missing, auto-repair stale, prompt/report drifted) and emitting a human-readable summary.

**Included subtasks:**
- [ ] T001 Audit `SurfaceRepairService.repair()` and extract `run_surface_repair()` helper (WP01)
- [ ] T002 Implement `DriftPolicySummary` dataclass; wire Missing→auto-create and Stale→auto-repair (WP01)
- [ ] T003 Implement drift-protection policy Rules 3-5: interactive prompt, non-interactive report-only, `--repair-drift=overwrite`; guard `--yes` (WP01)
- [ ] T004 Wire `run_surface_repair()` into `spec-kitty init` post-agent-config-write (WP01)
- [ ] T005 Wire into `spec-kitty upgrade` post-migrations; emit summary; verify idempotency (WP01)

**Implementation sketch:**
1. Audit `repair.py` `SurfaceRepairService.repair()` — understand current `RepairResult` shape
2. Add `DriftPolicySummary` dataclass with `created/repaired/drifted/overwritten/skipped` path lists
3. Implement drift rules: interactive `is_interactive` check, `--repair-drift=overwrite` flag, `--yes` guard
4. Extract `run_surface_repair(project_root, *, interactive, repair_drift)` function that init/upgrade call
5. Call `run_surface_repair()` at the tail of `init` (after agent dirs written) and at tail of upgrade runner
6. Emit summary with counts and paths; second run on clean project reports zero

**Parallel opportunities:** none (sequential — service extraction must precede wiring)
**Risks:** `upgrade/runner.py` may run migrations in a loop; repair must happen only once at the end, not per-migration

---

### WP02 — Codex Native Profile Renderer

**Priority:** High
**Estimated prompt size:** ~310 lines
**Execution mode:** code_change
**Dependencies:** [WP01]

**Goal:** Implement `CodexProfileRenderer` that projects Spec Kitty agent profiles to `.codex/agents/<profile_id>.toml` using TOML format, eliminating the `research_gap` finding for Codex in `doctor tool-surfaces`.

**Included subtasks:**
- [ ] T006 Add `tomli-w` to dependencies; implement `CodexProfileRenderer.render()` producing valid TOML (WP02)
- [ ] T007 Implement `can_render()`, `output_path()`, `format_key`; add optional-field passthrough (WP02)
- [ ] T008 Register renderer and `FORMAT_CODEX_AGENT` constant in renderer registry (WP02)
- [ ] T009 Verify `doctor tool-surfaces --kind agent-profile` no longer reports `research_gap` for `codex` (WP02)

**Implementation sketch:**
1. Add `tomli-w` to `pyproject.toml` dependencies
2. Create `src/specify_cli/tool_surface/profiles/codex_renderer.py` with `CodexProfileRenderer`
3. TOML shape: `{name, description, developer_instructions}` + optional `model`/`model_reasoning_effort`/`sandbox_mode`
4. `output_path` → `project_root / ".codex" / "agents" / f"{profile.profile_id}.toml"`
5. Register in `renderers.py` alongside `ClaudeCodeProfileRenderer` and `CopilotProfileRenderer`
6. Smoke test with `spec-kitty doctor tool-surfaces --kind agent-profile --json`

**Parallel opportunities:** T006-T009 are internally sequential; WP02 can run in parallel with WP03 after WP01 lands
**Risks:** `tomli-w` must be added to both `pyproject.toml` and the uv lockfile

---

### WP03 — Harness Capability Matrix Completion

**Priority:** High
**Estimated prompt size:** ~400 lines
**Execution mode:** code_change
**Dependencies:** [WP01]

**Goal:** Complete the harness capability matrix: implement Amazon Q and Augment Code renderers where confirmed; mark all remaining harnesses (Windsurf, Cursor, Kiro, etc.) as `not_applicable` with machine-readable reasons; ensure `doctor tool-surfaces --kind agent-profile --json` reports only the six valid statuses.

**Included subtasks:**
- [ ] T010 Confirm Amazon Q CLI agent format; implement `AmazonQProfileRenderer` targeting `~/.aws/amazonq/cli-agents/` (WP03)
- [ ] T011 Confirm Augment Code format; implement `AugmentProfileRenderer` for `.augment/agents/<id>.md` (WP03)
- [ ] T012 Build `HarnessCapabilityRecord`; register not-applicable harnesses with reasons (WP03)
- [ ] T013 Update `AgentProfilesProvider` to emit per-harness `not_applicable` findings from registry (WP03)
- [ ] T014 Verify `doctor tool-surfaces --kind agent-profile --json` emits exactly the six valid statuses (WP03)

**Implementation sketch:**
1. Implement `AmazonQProfileRenderer` — user-global path, NOT manifest-tracked, suggestion-only output
2. Implement `AugmentProfileRenderer` — YAML frontmatter + Markdown body + provenance footer, manifest-tracked
3. Add `HarnessCapabilityRecord` dataclass; populate capability matrix for all 19 configured harnesses
4. Update `AgentProfilesProvider` to consult capability matrix when building findings
5. Verify with `--kind agent-profile --json`: every harness is `present`/`missing`/`stale`/`drifted`/`not_applicable` or `research_gap` only for truly unassessed ones

**Parallel opportunities:** T010 and T011 can execute in parallel (independent renderer files)
**Risks:** Amazon Q user-global path must not be added to project manifest; must use direct filesystem inspection in doctor

---

### WP04 — Claude Code Plugin Build Command

**Priority:** High
**Estimated prompt size:** ~420 lines
**Execution mode:** code_change
**Dependencies:** none

**Goal:** Implement `spec-kitty plugin build --target claude-code` that generates a complete, validatable plugin bundle at `dist/spec-kitty-plugins/claude-code/` with real version metadata, all canonical skills, and all built-in agent profiles.

**Included subtasks:**
- [ ] T015 Scaffold `spec-kitty plugin build --target <target>` CLI command with build context and output dir logic (WP04)
- [ ] T016 Generate `.claude-plugin/plugin.json` with real version from `importlib.metadata`; validate semver (WP04)
- [ ] T017 Copy canonical command-skill set (≥15 skills) to `skills/` in bundle (WP04)
- [ ] T018 Copy built-in agent profile Markdown files to `agents/` in bundle (WP04)
- [ ] T019 Run `claude plugin validate --strict` at end of build; surface errors clearly (WP04)

**Implementation sketch:**
1. Add `plugin build` subcommand to `src/specify_cli/cli/commands/plugin.py` (or extend existing)
2. `plugin.json` builder: `name`, `displayName`, `version=importlib.metadata.version("spec-kitty-cli")`, `description`, `author`, component pointers
3. Copy skills from `src/doctrine/` canonical set to `dist/.../skills/spec-kitty.<cmd>/SKILL.md`
4. Copy profile Markdown files from doctrine to `dist/.../agents/<id>.md`
5. Shell out to `claude plugin validate --strict` if `claude` CLI is found; display result; non-zero exit on failure

**Parallel opportunities:** none (sequential bundle build)
**Risks:** `claude` CLI may not be installed in dev environment; validate step should be skippable in unit tests but must run in CI

---

### WP05 — Claude Code Plugin Runtime Bootstrap and Distribution

**Priority:** High
**Estimated prompt size:** ~320 lines
**Execution mode:** code_change
**Dependencies:** [WP04]

**Goal:** Complete the Claude Code plugin with the `bin/spec-kitty-wrapper` runtime bootstrap script (PATH-check + uvx fallback), CI validation job, `marketplace.json` for git-based distribution, and developer documentation.

**Included subtasks:**
- [ ] T020 Generate `bin/spec-kitty-wrapper` (bash) + `spec-kitty-wrapper.cmd` (Windows) with PATH-check + `uvx` fallback (WP05)
- [ ] T021 Add `.github/workflows/plugin-validate.yml` CI job (WP05)
- [ ] T022 Generate `marketplace.json` for git-based distribution; document `claude plugin marketplace add` install path (WP05)
- [ ] T023 Add `docs/how-to/install-claude-code-plugin.md` covering marketplace and `--plugin-dir` dev install (WP05)

**Implementation sketch:**
1. `spec-kitty-wrapper` bash script: `command -v spec-kitty >/dev/null && exec spec-kitty "$@"` else `exec uvx spec-kitty-cli==<VERSION> "$@"` where `<VERSION>` is substituted at build time; mark executable
2. `.cmd` Windows equivalent: `where spec-kitty >nul 2>&1 && spec-kitty %*` else `uvx spec-kitty-cli==<VERSION> %*`
3. `plugin-validate.yml`: `npm install -g @anthropic-ai/claude-code`, `spec-kitty plugin build --target claude-code`, `claude plugin validate --strict dist/...`
4. `marketplace.json` format per contract at `contracts/plugin-manifest-claude.md`
5. README how-to: marketplace install (3-minute) + `--plugin-dir` dev install

**Parallel opportunities:** T020-T023 can execute in parallel within WP05
**Risks:** `npm install -g @anthropic-ai/claude-code` requires Node.js in CI; CI matrix must include Node setup step

---

### WP06 — Codex Plugin Bundle Projector

**Priority:** Medium
**Estimated prompt size:** ~350 lines
**Execution mode:** code_change
**Dependencies:** [WP04]

**Goal:** Implement `spec-kitty plugin build --target codex` that generates a Codex plugin bundle at `dist/spec-kitty-plugins/codex/` with a schema-valid `.codex-plugin/plugin.json` (no `hooks` key, no `agents` key), canonical skills, and a `marketplace.json` for repo-local install.

**Included subtasks:**
- [ ] T024 Scaffold `--target codex` path in plugin build command; generate `.codex-plugin/plugin.json` (WP06)
- [ ] T025 Validate Codex plugin.json: `hooks` key absent, `agents` key absent, all required interface fields present (WP06)
- [ ] T026 Copy command-skill set to `skills/` in Codex bundle; include `hooks/` by presence only (WP06)
- [ ] T027 Generate Codex `marketplace.json` for repo-local install (WP06)

**Implementation sketch:**
1. Extend `plugin build` target dispatch to handle `--target codex`; output to `dist/spec-kitty-plugins/codex/`
2. Build `plugin.json` per `contracts/plugin-manifest-codex.md`: required fields, NO `hooks` key, NO `agents` key
3. Copy skills to `skills/` subdirectory matching Codex skill discovery conventions
4. `marketplace.json` format: `{name, plugins: [{name, source: {source: "local", path: "."}, ...}]}`
5. Assertion in build step: `assert "hooks" not in manifest` and `assert "agents" not in manifest`

**Parallel opportunities:** WP06 runs in parallel with WP05 (different output targets)
**Risks:** Codex plugin schema changes may invalidate the manifest; build must be re-verified against current docs

---

### WP07 — Command-Skill Manifest Repair and Roo Code Deprecation

**Priority:** Medium
**Estimated prompt size:** ~450 lines
**Execution mode:** code_change
**Dependencies:** [WP01]

**Goal:** Make stale command-skill manifests self-heal during upgrade (11→canonical count); apply drift policy to modified SKILL.md files; remove unsafe symlink artifacts; fully remove Roo Code from AI_CHOICES, AGENT_DIRS, config.yaml; emit deprecation notice for existing `.roo/` directories; update documentation.

**Included subtasks:**
- [ ] T028 Repair stale command-skill manifests following safe-stale policy during upgrade (WP07)
- [ ] T029 Apply drift policy to drifted SKILL.md files in `.agents/skills/`; interactive prompt / report-only (WP07)
- [ ] T030 Detect and remove unsafe symlink artifacts (e.g., `.agents/skills/spec-kitty.advise`) during upgrade (WP07)
- [ ] T031 Remove `roo` from `AI_CHOICES` in `config.py` and from `AGENT_DIRS` in migration module (WP07)
- [ ] T032 Emit Roo Code deprecation notice when `.roo/` detected during upgrade; preserve directory (WP07)
- [ ] T033 Remove `roo` from `.kittify/config.yaml` when present; include in upgrade summary (WP07)
- [ ] T034 Update `README.md` and `docs/` to remove Roo Code from Supported AI Agents list (WP07)

**Implementation sketch:**
1. In `src/specify_cli/skills/manifest_store.py`: compare current manifest entry count against canonical set; if stale, auto-repair (add missing entries, report in summary)
2. For drifted SKILL.md files, reuse the drift policy from WP01's `run_surface_repair()` — same `is_interactive` / `repair_drift` flags
3. Symlink detection: `os.path.islink(path)` in `.agents/skills/`; `os.unlink()` on matches; report in summary
4. Remove `"roo": "Roo Code"` from `AI_CHOICES` dict in `config.py`; remove `("roo", ...)` from `AGENT_DIRS`; guard C-007 (no failure if `.roo/` absent)
5. Upgrade migration: detect `.roo/` presence → emit Rich deprecation panel; remove from `config.yaml` via `load_agent_config/save_agent_config`
6. README: remove Roo Code row from Supported AI Agents table; add "Roo Code (shut down 2026-05-15)" to archived section

**Parallel opportunities:** T028-T030 relate to skills; T031-T034 relate to Roo Code — these two groups can run in parallel within WP07
**Risks:** `AI_CHOICES` removal must not break any project that previously created `.roo/` commands — guard for absence per C-007

---

### WP08 — Renderer Unit Tests

**Priority:** High (gates WP09)
**Estimated prompt size:** ~380 lines
**Execution mode:** code_change
**Dependencies:** [WP01, WP02, WP03]

**Goal:** Write focused unit tests for all five profile renderers (ClaudeCode, Codex, Copilot, AmazonQ, Augment) covering output path, required fields, idempotency, and format validity; achieve ≥90% branch coverage on renderer modules.

**Included subtasks:**
- [ ] T035 Unit tests for `ClaudeCodeProfileRenderer`: output path, YAML frontmatter fields, provenance footer, idempotent re-render (WP08)
- [ ] T036 Unit tests for `CodexProfileRenderer`: TOML validity, all three required fields, output path, optional-field passthrough (WP08)
- [ ] T037 Unit tests for `CopilotProfileRenderer`: file extension `.agent.md` (not `.chatmode.md`), output path under `.github/agents/` (WP08)
- [ ] T037b Unit tests for `AmazonQProfileRenderer` and `AugmentProfileRenderer` (WP08)
- [ ] T038 Parametric test covering all five renderers against a shared fixture profile (WP08)
- [ ] T039 Verify ≥90% branch coverage on `profiles/renderers.py` and each new renderer module (WP08)

**Implementation sketch:**
1. `test_profile_renderers.py`: fixture `AgentProfile` with full field set; test each renderer in isolation
2. For `ClaudeCodeProfileRenderer`: assert path ends in `.claude/agents/<id>.md`; YAML frontmatter contains `name` and `description`; body has provenance line; re-render produces identical bytes
3. For `CodexProfileRenderer`: parse rendered output with `tomllib.loads()`; assert keys `name`, `description`, `developer_instructions`; optional keys present only when profile has them
4. For `CopilotProfileRenderer`: assert path ends in `.github/agents/<id>.agent.md`; NOT `.chatmode.md`
5. Parametric: `@pytest.mark.parametrize("renderer", [Claude, Codex, Copilot, AmazonQ, Augment])` with shared `AgentProfile`; assert `can_render()` returns True for their respective tool_key

**Parallel opportunities:** T035-T038 can execute in parallel (different renderer test files)
**Risks:** TOML validation in T036 requires `tomllib` (stdlib ≥3.11) — already available in Python 3.11+

---

### WP09 — Integration Tests, Migration Acceptance Fixture, and CI Gate

**Priority:** Critical (definition of done)
**Estimated prompt size:** ~430 lines
**Execution mode:** code_change
**Dependencies:** [WP01, WP02, WP03, WP07, WP08]

**Goal:** Write integration tests for init/upgrade surface wiring and drift policy; implement the rc44-era migration acceptance fixture; update the doctor JSON stability contract; run the full suite at ≥90% coverage on all new code.

**Included subtasks:**
- [ ] T040 Integration tests for `init`/`upgrade` surface wiring: missing created, stale repaired, drifted reported-only in `--yes` mode (WP09)
- [ ] T041 rc44-era migration acceptance fixture: `claude`+`codex` project, 11-entry manifest, no native profile dirs → `upgrade --yes` heals all (WP09)
- [ ] T042 `test_drift_policy.py` parametric test covering Rules 1-5 from `drift-policy.md` contract (WP09)
- [ ] T043 Update `test_migration_compat.py` doctor JSON stability contract to include `agent_profile` surface kinds (WP09)
- [ ] T044 Full test suite pass: `mypy --strict` on changed modules, `ruff check`, `pytest` ≥90% coverage on new paths (WP09)

**Implementation sketch:**
1. `test_surface_repair_wiring.py`: tmp project fixture; call `init`/`upgrade`; assert profile files created; modify profile; call upgrade `--yes`; assert file preserved and exit non-zero; call `--repair-drift=overwrite`; assert overwritten
2. `test_rc44_migration_fixture.py`: fixture with `config.yaml` for claude+codex, 11-entry `command-skills-manifest.json`, no `.claude/agents/`, no `.codex/agents/`; run upgrade; assert profiles created; assert manifest repaired to canonical count; assert `doctor tool-surfaces --json` shows zero `missing`/`stale`/`drifted`
3. `test_drift_policy.py`: parametric fixture for each rule 1-5; assert Rules 3/4/5 behaviour w.r.t. is_interactive and --repair-drift
4. `test_migration_compat.py`: add `"agent_profile"` to the `expected_surface_kinds` baseline; assert `doctor tool-surfaces --json` schema still additive-only
5. Final gate: `mypy --strict` on all WP-touched modules; `ruff check` on all changed files; `pytest --cov` targeting new paths

**Parallel opportunities:** T040-T043 can run in parallel; T044 is the sequential gate
**Risks:** Migration fixture may require a real or mocked `get_agent_dirs_for_project()` call; must use test-project isolation (tmp_path)

---

## Progress Tracking

| WP | Title | Subtasks | Status |
|---|---|---|---|
| WP01 | Surface Repair Wiring | T001-T005 | planned |
| WP02 | Codex Native Profile Renderer | T006-T009 | planned |
| WP03 | Harness Capability Matrix Completion | T010-T014 | planned |
| WP04 | Claude Code Plugin Build Command | T015-T019 | planned |
| WP05 | Claude Code Plugin Runtime and Distribution | T020-T023 | planned |
| WP06 | Codex Plugin Bundle Projector | T024-T027 | planned |
| WP07 | Command-Skill Manifest Repair and Roo Code Deprecation | T028-T034 | planned |
| WP08 | Renderer Unit Tests | T035-T039 | planned |
| WP09 | Integration Tests and Migration Acceptance Fixture | T040-T044 | planned |
