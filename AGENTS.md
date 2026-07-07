# Spec Kitty Development Guidelines

**Spec Kitty** is a toolkit for Spec-Driven Development (SDD) — clear, actionable specifications ahead of implementation, inspired by GitHub's [Spec Kit](https://github.com/github/spec-kit). **Spec Kitty CLI** bootstraps projects with the framework: directory structures, templates, and AI agent integrations. Every command template leads with a discovery interview; the CLI refuses to create specs or plans until the question set is answered.

---

## ⚠️ CRITICAL: Load the Project Charter First

**Every LLM agent working in this repository MUST read the project charter at [`.kittify/charter/charter.md`](.kittify/charter/charter.md) at the start of a session, before planning or making changes.**

The charter is the binding governance document. It carries rules that are NOT repeated in this file, including:

- **Governing principles** — single canonical authority, architectural alignment, DDD + tiered rigour, ATDD-first, terminology adherence.
- **Quality & Tech-Debt Standing Orders** — the eight binding practices (adversarial squad cadence, campsite cleaning, mission tracer files, test-remediation/red-first discipline, architectural gate discipline, canonical sources, git/workflow discipline, mission hygiene).
- **Agent operating discipline and collaboration strategy** — model routing, profile-loaded delegation, draft-PR-first, the operator merges.
- **Governance by workflow action** — which rules bind specify/plan/implement/review/merge.

For action-scoped detail, load the doctrine context via `spec-kitty charter context --action <name>` rather than improvising. If the charter and this file ever disagree, the charter wins — flag the drift instead of picking silently.

---

## ⚠️ CRITICAL: Template Source Location

**Edit SOURCE files, NOT agent copies!**

| What | Location | Action |
|------|----------|--------|
| **SOURCE templates** | `src/doctrine/missions/mission-steps/` | ✅ EDIT THESE |
| **Agent copies** | `.claude/`, `.amazonq/`, `.augment/`, etc. | ❌ DO NOT EDIT |

Agent directories are **generated copies** deployed to consumer projects via `spec-kitty upgrade`. Template flow:
```
src/doctrine/missions/mission-steps/{mission_type}/{step_id}/prompt.md  (SOURCE)
    ↓ spec-kitty upgrade
.claude/commands/, .amazonq/prompts/, ... (12 agent dirs + .agents/skills/)  (GENERATED)
```

---

## ⚠️ CRITICAL: Use Canonical Sources, Never Improvise

**Always use the canonical templates, skills, commands, and code surfaces rather than improvising or using older artefacts as examples.**

- Spec/plan/tasks templates come from `src/doctrine/missions/<type>/templates/` (resolved through the charter/doctrine chain) — never copy structure from an older mission in `kitty-specs/`.
- Workflows run through the documented `spec-kitty` CLI commands and the published skills — do not hand-roll equivalents or reconstruct paths the resolver should provide.
- When a canonical command, template, or code surface appears missing or broken, **trace the source and file an upstream gap** — do not silently work around it with an improvised substitute.

**Why:** older missions and ad-hoc artefacts drift from the canonical structure; copying them propagates the drift. The doctrine templates are the single source of truth.

---

## ⚠️ CRITICAL: Git Workflow — No Direct Pushes to origin/main

**All changes to origin/main MUST go through pull requests. Direct pushes are prohibited.**

- `spec-kitty merge` merges to **local main** only. It does NOT push to origin/main.
- After `spec-kitty merge`, if the user explicitly asks to share or publish: create a PR branch (`git checkout -b pr/<slug>`) and open a pull request (`gh pr create`). Do NOT do this automatically — wait for explicit user instruction.
- Never run `git push origin main` or equivalent. Use a PR branch and `gh pr create`.
- Always distinguish: **local main** (your checkout) vs **origin/main** (the remote). Never say just "main" — always qualify.

**Why:** The workflow is predicated on pull requests for review, CI gating, and audit trail. Direct pushes to origin/main bypass all of these.

**Recovery:** If you accidentally push to origin/main, do NOT force-push (branch protection blocks it). Instead: create a `revert/<slug>` branch from origin/main, commit a revert, open a PR to merge it, then open the real mission PR.

---

## Terminology Canon

- Canonical product term is **Mission** (plural: **Missions**).
- `Feature` / `Features` are prohibited in canonical, operator, and user-facing language for active systems.
- Do not introduce or preserve `feature*` aliases (API/query params, routes, fields, flags, env vars, command names, or docs) when the domain object is a Mission.
- Historical archived artifacts may retain legacy wording only as immutable snapshots, explicitly marked legacy.

---

## Supported AI Agents

19 agents total: 13 slash-command, 6 Agent Skills. Update all command-layer agents when changing slash commands, migrations, or templates.

### Slash-Command Agents (13)

| Agent | Directory | Subdirectory | Format |
|-------|-----------|--------------|--------|
| Claude Code | `.claude/` | `commands/` | Markdown |
| GitHub Copilot | `.github/` | `prompts/` | Markdown |
| Google Gemini | `.gemini/` | `commands/` | TOML |
| Cursor | `.cursor/` | `commands/` | Markdown |
| Qwen Code | `.qwen/` | `commands/` | TOML |
| OpenCode | `.opencode/` | `command/` | Markdown |
| Windsurf | `.windsurf/` | `workflows/` | Markdown |
| Kilocode | `.kilocode/` | `workflows/` | Markdown |
| Augment Code | `.augment/` | `commands/` | Markdown |
| Roo Cline | `.roo/` | `commands/` | Markdown |
| Amazon Q | `.amazonq/` | `prompts/` | Markdown |
| Kiro | `.kiro/` | `prompts/` | Markdown |
| Google Antigravity | `.agent/` | `workflows/` | Markdown |

**Argument placeholders:** Markdown agents use `$ARGUMENTS`; TOML agents use `{{args}}`; `{SCRIPT}` is replaced with the actual script path; `__AGENT__` is replaced with the agent name.

### Agent Skills Agents (6)

| Agent | Skills Root | Command Surface | Key |
|-------|-------------|-----------------|-----|
| Codex CLI | `.agents/skills/` | `$spec-kitty.<command>` | `codex` |
| Mistral Vibe | `.agents/skills/` via `.vibe/config.toml` | `/spec-kitty.<command>` | `vibe` |
| Pi | `.agents/skills/` | `/skill:spec-kitty.<command>` | `pi` |
| Letta Code | `.agents/skills/` | Agent Skills | `letta` |

Codex, Vibe, Pi, and Letta share `.agents/skills/spec-kitty.<command>/SKILL.md`. Manifest: `.kittify/command-skills-manifest.json`.

**Agent key mappings** (key differs from directory for some): `copilot` → `.github/prompts`, `auggie` → `.augment/commands`, `q` → `.amazonq/prompts`. Use `AGENT_DIR_TO_KEY` in [`src/specify_cli/agent_utils/directories.py`](src/specify_cli/agent_utils/directories.py) for conversions.

**Canonical source**: `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` → `AGENT_DIRS`

**When modifying**: Migrations → use `get_agent_dirs_for_project()`. Template changes propagate via migration. Test at least `.claude`, `.codex`, `.opencode`.

**Skills modules** (mission 083): `src/specify_cli/skills/` — `command_renderer.py`, `command_installer.py`, `manifest_store.py`.

---

## Agent Management

**CRITICAL: `.kittify/config.yaml` is the single source of truth for agent configuration.**

```bash
spec-kitty agent config list/add/remove/status/sync
```

**DO:** Use CLI commands. Let migrations respect config. **DON'T:** Manually delete agent dirs without updating config. Modify `config.yaml` directly.

### Writing Migrations

Always use the config-aware helper:
```python
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project

agent_dirs = get_agent_dirs_for_project(project_path)
for agent_root, subdir in agent_dirs:
    agent_dir = project_path / agent_root / subdir
    if not agent_dir.exists():
        continue  # respect deletions — never mkdir
    # process agent...
```

**DON'T:** Hardcode `AGENT_DIRS`. Create missing dirs. Assume all 12 agents are present. Process agents not in `config.yaml`.

**Key functions:**
- `get_agent_dirs_for_project(project_path)` — (dir, subdir) tuples for configured agents
- `load_agent_config(repo_root)` / `save_agent_config(repo_root, config)` — config I/O

**See also:** ADR #6, `tests/specify_cli/test_agent_config_migration.py`, `tests/specify_cli/cli/commands/test_agent_config.py`

### Adding New Agent Support

1. **Add to `AI_CHOICES`** in `src/specify_cli/__init__.py` and `agent_folder_map`.
2. **Update CLI help text** — `--ai` param description, docstrings, error messages.
3. **Update `README.md`** Supported AI Agents section.
4. **Update release script** `.github/workflows/scripts/create-release-packages.sh` — add to `ALL_AGENTS` array and case statement.
5. **Update GitHub release script** `.github/workflows/scripts/create-github-release.sh` — add agent packages.
6. **Add to `AGENT_DIRS`** in `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`.
7. **CLI tool check** (only for agents with required CLI tools, not IDE-based ones):
   ```python
   tracker.add("windsurf", "Windsurf IDE (optional)")
   check_tool_for_tracker("windsurf", "https://windsurf.com/", tracker)
   ```

**Agent categories:**
- *CLI-based* (require CLI tool): Claude Code (`claude`), Gemini (`gemini`), Cursor (`cursor-agent`), Qwen (`qwen`), opencode (`opencode`), Amazon Q (`q`)
- *IDE-based* (no CLI check needed): GitHub Copilot (VS Code), Windsurf (Windsurf IDE)

**Testing new agent:**
1. Run package creation script locally
2. `spec-kitty init --ai <agent>` and verify directory structure and files
3. Confirm generated commands work with the agent

**Common pitfalls:** Wrong argument placeholder format; directory naming deviates from agent convention; missing help text updates; unnecessary CLI checks for IDE-based agents.

---

## Project Structure

```
architecture/     # ADRs and technical specs
src/specify_cli/
  glossary/       # Glossary semantic integrity pipeline
  next/           # Canonical mission-next command loop (shim — see Shared Package Boundary)
tests/            # Test suite
kitty-specs/      # Mission specs (dogfooding)
docs/             # User documentation
```

New architectural designs → `architecture/` following `docs/architecture/README.md` template.

## Commands

```bash
pytest tests/
ruff check .
PWHEADLESS=1 pytest tests/   # headless (prevents browser windows)
```

### Local parallel test run (default)

Run the suite in parallel locally — at least 2× faster on a ≥4-core machine:

```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
# daemon/real-port tests run serially:
PWHEADLESS=1 pytest tests/sync/test_orphan_sweep.py -n0 -q
```

Rules:

- **Always `--dist loadfile`, never bare `--dist load`.** `loadfile` keeps every
  test in a file on a single worker, preserving file-scoped fixture and
  collection semantics; `load` scatters a file's tests across workers and breaks
  them.
- **Per-worker HOME isolation (WP04)** means a parallel run never touches the
  real `~/.spec-kitty` — each `pytest-xdist` worker (and the serial master) gets
  its own isolated home / XDG / AppData directories.
- **Real-port / daemon tests run serially.** OS-global resources (real ports,
  daemons — e.g. `tests/sync/test_orphan_sweep.py`, ports 9400–9449) are not
  protected by per-worker HOME isolation, so run them in their own `-n0` pass.

Full rationale, the volume env gates, and the stability ratchet:
[docs/guides/testing-parallel.md](docs/guides/testing-parallel.md).

When a test goes red on CI unrelated to your diff, follow the flakiness policy —
**tune budget gates, fix correctness flakes at the root, never retry-to-green:**
[docs/guides/testing-flakiness.md](docs/guides/testing-flakiness.md).

## Code Style

Python 3.11+. Follow standard conventions. Any changes to `__init__.py` require a version bump in `pyproject.toml` and a `CHANGELOG.md` entry.

**New code MUST pass `ruff` and `mypy` with zero issues and zero warnings. Do NOT disable, suppress, or relax checks (no blanket `# noqa`, `# type: ignore`, or per-file ignore additions) to achieve this — fix the code instead.** Narrowly-scoped, individually-justified suppressions are allowed only when the check is genuinely wrong about correct code, and must carry an inline rationale.

**Pre-push: run the terminology guard when touching `src/doctrine/` or user-facing prose.** Some repo-wide gates run only in CI's `integration-tests-core-misc` job, NOT in the `fast-tests-*` suites — so a forbidden-term regression passes local doctrine runs and only fails at CI. Before pushing doctrine/prose changes, run `pytest tests/architectural/test_no_legacy_terminology.py` (≈0.1 s); it enforces the Terminology Canon (e.g. canonical `status commit` not `ceremony`; `Mission` not `feature`). The full `tests/architectural/` suite is the complete safety net.

## Sonar Expectations

Treat these as code-shaping constraints, not post-hoc cleanup:

- **Complexity ceiling is 15.** Ruff `C901` and Sonar `S3776` are aligned (`[tool.ruff.lint.mccabe].max-complexity = 15`). When touching a function near that limit, keep it at `<=15` by extracting small helpers, flattening nested conditionals, or separating lookup/build/emit phases. Do **not** leave a function at 16+ and assume "tests passing" is enough.
- **Repeated non-trivial literals become constants.** If a string/path/message/help text appears `>=3` times in the same module, hoist it to a named module constant instead of duplicating it. This is the default response to Sonar `S1192`.
- **Do not leave empty or effect-free exception handlers.** If an `except` block does nothing meaningful, either remove it and let the exception propagate, or add the concrete recovery/logging/translation logic Sonar expects.
- **Every new branch/helper needs tests in the same PR.** Sonar's project gate is dominated by new-code coverage; extracting helpers without adding focused tests simply moves the failure. When you add or refactor logic, add narrow tests that execute the new branches/helpers directly.
- **Prefer testable extractions.** Sonar generally rewards pure/helper extraction plus focused tests. If a function is large, extract deterministic subroutines with stable inputs/outputs, then test those paths instead of only relying on a broad integration test.
- **Prefer real fixes over suppression.** Do not add `# noqa`, `# type: ignore`, or Sonar suppression comments to silence maintainability findings unless the tool is materially wrong about correct code. If suppression is unavoidable, keep it narrow and explain why the code is safe.
- **Loopback/local-only HTTP is a special case.** Do not "fix" localhost/127.0.0.1 control-plane URLs by forcing HTTPS when the transport is intentionally loopback-only. Keep the safe loopback semantics, add/keep regression tests, and record the rationale in the PR if Sonar raises a hotspot. Code change and hotspot review are separate actions.
- **PR description must call out remaining Sonar UI work.** If the code is correct but Sonar still needs hotspot review or UI-side rationale application, say so explicitly in the PR body so a later agent does not waste time trying to "fix" it in code.

## Recent Changes

- **068**: `src/specify_cli/post_merge/` (AST-based stale-assertion analyzer), `agent tests` CLI subgroup, `agent/release.py prep` subcommand, FR-019 safe_commit fix in `_run_lane_based_merge`, FR-021 `scan_recovery_state` + `implement --base`
- **047**: Added typer, rich, ruamel.yaml, requests, pytest, mypy; SQLite OfflineQueue sibling table
- **023**: Documentation sprint / agent management cleanup

---

## PyPI Release

**CRITICAL: NEVER create releases without explicit user instruction. NEVER release manually — use the GitHub release process.**

Only act on: "cut a release", "release v0.X.Y", "push to PyPI", or similar explicit instructions.

```bash
# 1. Bump version in pyproject.toml + add CHANGELOG.md entry
# 2. Tag and push:
git tag -a vX.Y.Z -m "Release vX.Y.Z - Brief description"
git push origin vX.Y.Z
# 3. Monitor: gh run list --workflow=release.yml --limit=1 && gh run watch <run_id>
# 4. Verify: gh release view vX.Y.Z
```

Full docs: [CONTRIBUTING.md](CONTRIBUTING.md#release-process)

---

## Execution Workspace Strategy (2.x)

- **Coord/primary partition** (canonical, operator-confirmed): coord = lifecycle surfaces
  (status, notes, trace, issue-matrix, `move-task`); primary = stable planning (spec/plan/WP
  outlines). Missions with no coordination topology (`SINGLE_BRANCH` / `LANES`) route
  everything to primary. Planning commands may be invoked from the repo root — no worktree is
  required to run `/spec-kitty.specify` / `/spec-kitty.plan` / `/spec-kitty.tasks`.
- `spec-kitty implement WP##` creates/reuses the execution workspace.
  - `lanes.json` present → `.worktrees/<feature>-lane-<id>`
  - `lanes.json` absent → legacy: `.worktrees/<feature>-WP##`

**Planning artifacts** (land on the primary partition):
- `/spec-kitty.specify` → `kitty-specs/<mission>/`
- `/spec-kitty.plan` → planning artifacts
- `/spec-kitty.tasks` → `tasks.md` + `tasks/*.md`
- `spec-kitty agent mission finalize-tasks` → validates deps, writes lane metadata

**Implementation:** `spec-kitty implement WP##` is the only supported way to prepare a workspace. Agent commands must consume the resolved workspace path, not reconstruct it.

**When modifying workspace/orchestration behavior:**
1. Update runtime resolver logic first.
2. Update agent wrappers to use the resolver.
3. Update templates, skills, and docs together.

**Testing:** Unit coverage for workspace resolution + integration coverage for `agent action implement/review`.

**Status source of truth:** the resolved status surface (coord branch for coord/lanes-with-coord
topologies; primary otherwise), not the open worktree.

**References:** [execution-lanes.md](docs/architecture/execution-lanes.md), [git-worktrees.md](docs/architecture/git-worktrees.md)

---

## Merge & Preflight Patterns (0.11.0+)

Merge progress saved in `.kittify/merge-state.json` for resumable operations.

**MergeState fields** (`src/specify_cli/merge/state.py`):

| Field | Type | Description |
|-------|------|-------------|
| `feature_slug` | `str` | Feature identifier |
| `target_branch` | `str` | Branch being merged into |
| `wp_order` | `list[str]` | Ordered WP IDs |
| `completed_wps` | `list[str]` | Successfully merged WPs |
| `current_wp` | `str\|None` | WP currently being merged |
| `has_pending_conflicts` | `bool` | Unresolved git conflicts |
| `strategy` | `str` | "merge", "squash", or "rebase" |
| `started_at` / `updated_at` | `str` | ISO timestamps |

Properties: `remaining_wps`, `progress_percent`. Import from `specify_cli.merge`: `MergeState`, `save_state`, `load_state`, `clear_state`, `has_active_merge`.

**Pre-flight validation** (`run_preflight()`): checks all WPs have worktrees, all are clean, target not behind origin. Returns `PreflightResult` with `.passed`, `.wp_statuses`, `.errors`, `.warnings`. `WPStatus` fields: `wp_id`, `worktree_path`, `branch_name`, `is_clean`, `error`.

**Common commands:**
```bash
spec-kitty merge --resume          # resume interrupted
spec-kitty merge --abort           # start fresh
spec-kitty merge --dry-run         # conflict forecast
spec-kitty merge --feature 017-my-feature
```

**Implementation files:** `merge/state.py`, `merge/preflight.py`, `merge/executor.py`, `merge/forecast.py`, `merge/status_resolver.py`, `cli/commands/merge.py`

---

## Status Model Patterns (034+, 060 cleanup)

Append-only event log (`status.events.jsonl`) is the **sole authority** for WP lane state. Frontmatter `lane` is retired (migration-only). Phase 2 is the only active model as of 3.0.

**Event format:**
```json
{"actor":"claude","at":"2026-02-08T12:00:00+00:00","event_id":"01HXYZ...","evidence":null,"execution_mode":"worktree","feature_slug":"034-feature","force":false,"from_lane":"planned","reason":null,"review_ref":null,"to_lane":"claimed","wp_id":"WP01"}
```

**Key functions:**

| Function | Module | Purpose |
|----------|--------|---------|
| `emit_status_transition()` | `status.emit` | Single entry point: validate → persist → materialize → views → SaaS |
| `reduce()` | `status.reducer` | Deterministic event → snapshot |
| `append_event()` / `read_events()` | `status.store` | JSONL I/O with corruption detection |
| `validate_transition()` | `status.transitions` | Check (from, to) against matrix + guards |
| `resolve_phase()` | `status.phase` | meta.json > config.yaml > default(1) |
| `resolve_lane_alias()` | `status.transitions` | `doing` → `in_progress` at input boundaries |

**9-lane state machine:**
```
planned → claimed → in_progress → for_review → in_review → approved → done
```
`blocked` reachable from all non-terminal. `canceled` reachable from all. Alias: `doing` → `in_progress` (never persisted). Terminal: `done`, `canceled` (force required to leave).

**Dependency gating:** WPs with `dependencies` frontmatter cannot be claimed/implemented until every dependency is `approved` or `done`. Computed by `dependency_readiness_for_wp()` (`src/specify_cli/core/dependency_graph.py`). `approved` satisfies the gate — gating on `done` only would deadlock same-mission chains. Re-invoking `implement` on an `in_progress` WP is a no-op resume (not re-gated).

**Quick status check (recommended for agents):**
```bash
spec-kitty agent tasks status
spec-kitty agent tasks status --feature 012-documentation-mission
```

**Package:** `src/specify_cli/status/` — `models.py`, `transitions.py`, `reducer.py`, `store.py`, `phase.py`, `emit.py`, `lane_reader.py`, `bootstrap.py`, `legacy_bridge.py`, `validate.py`, `doctor.py`, `reconcile.py`, `migrate.py` (migration-only), `history_parser.py` (migration-only).

**Common operations:**
```python
from specify_cli.status.emit import emit_status_transition
event = emit_status_transition(
    feature_dir=feature_dir, feature_slug="034-feature",
    wp_id="WP01", to_lane="claimed", actor="claude",
)

from specify_cli.status.reducer import materialize
snapshot = materialize(feature_dir)
```

**Docs:** [docs/status-model.md](docs/status-model.md), [data-model.md](kitty-specs/034-feature-status-state-model-remediation/data-model.md)

---

## Mission Identity Model (083+)

Every mission carries a ULID-based `mission_id` in `meta.json`. `mission_number` is display-only, assigned at merge time. Fixes `NNN-` prefix collision on selectors, branches, and dashboards.

| Field | Type | Role | When assigned |
|-------|------|------|---------------|
| `mission_id` | ULID (26 chars) | Canonical machine identity (immutable) | At `mission create` |
| `mid8` | First 8 chars | Branch/worktree disambiguator | Derived |
| `mission_slug` | kebab slug | Human handle | At `mission create` |
| `mission_number` | `int\|None` | Display-only, `null` pre-merge | At merge via `max+1` |
| `friendly_name` | string | Human display | At `mission create` |

`mission_id` is the only runtime identity. `mission_number` is never used for lookup, locking, or routing.

**Naming:** Branch: `kitty/mission-<slug>-<mid8>-lane-<id>` | Worktree: `.worktrees/<slug>-<mid8>-lane-<id>`

**Selector disambiguation:** Resolves `mission_id` → `mid8` → `mission_slug`. Ambiguous handles → structured error, **no silent fallback** (WP07 — reintroducing fallback is a regression).

**Migration** (pre-083 projects):
```bash
spec-kitty doctor identity --json        # audit
spec-kitty migrate backfill-identity     # mint mission_id for legacy missions
spec-kitty doctor identity --json        # confirm
```

Full runbook: [docs/migrations/mission-id-canonical-identity.md](docs/migrations/mission-id-canonical-identity.md)

---

## Shared Package Boundary (2026-04-25)

- **Runtime:** `src/runtime/next/_internal_runtime/` (canonical). `src/specify_cli/next/` is a deprecation shim removed in 3.3.0 — do not anchor new code there. `spec-kitty-runtime` PyPI package is retired.
- **Events / Tracker:** External PyPI dependencies. Consume only via `spec_kitty_events.*` / `spec_kitty_tracker.*` public imports. Vendored copies removed.
- **Dev editable/path overrides:** never committed in `pyproject.toml [tool.uv.sources]`. See [docs/development/local-overrides.md](docs/development/local-overrides.md).

Enforced by `tests/architectural/test_shared_package_boundary.py`, `test_pyproject_shape.py`, and the `clean-install-verification` CI job.

ADR: [`docs/adr/3.x/2026-04-25-1-shared-package-boundary.md`](docs/adr/3.x/2026-04-25-1-shared-package-boundary.md). Runbook: [`docs/migrations/shared-package-boundary-cutover.md`](docs/migrations/shared-package-boundary-cutover.md).

---

## Charter Activation and Doctrine Integrity Model

Governing ADR: [`docs/adr/3.x/2026-05-16-1-doctrine-layer-merge-semantics.md`](docs/adr/3.x/2026-05-16-1-doctrine-layer-merge-semantics.md)

### Activation Engine (`charter.activation_engine`)

Plan/commit seam: `plan_activation()` validates (non-mutating); `commit_activation()` writes config only after plan succeeds. Never mutates config on validation failure (NFR-003). `CharterPackConfigError` → fail-closed.

```python
plan = plan_activation(kind="directive", artifact_id="010-...", pack_context=ctx)
commit_activation(plan, project_root=Path("."))
```

### Charter Cascade (`charter.cascade`)

Follows DRG `requires`/`suggests` edges (not hardcoded per-kind logic).

```bash
charter activate mission-type research --cascade all
charter activate mission-type research --cascade agent-profile,tactic
charter deactivate mission-type research --cascade all
```

Without `--cascade`: warns about skipped artifacts with a suggested recovery command. **Shared-reference safety (C-005):** cascade deactivation skips artifacts still referenced by another active artifact.

### Canonical Kind Vocabulary

`charter.kind_vocabulary.from_operator_token` normalizes operator-facing tokens at input boundaries:

| Token | Canonical kind |
|-------|----------------|
| `agent-profile` | `agent_profile` |
| `mission-step-contract` | `mission_step_contract` |
| `directive` / `tactic` / `styleguide` / `toolguide` / `paradigm` / `template` | (same) |
| `mission-type` | raises `MissionTypeNotAnArtifactKind` |

### `specializes_from` DRG Lineage

Profile lineage is a DRG edge (C-009 binding constraint), not a per-profile field. Declare in org-pack DRG YAML:
```yaml
edges:
  - source: "urn:profile:my-analyst"
    target: "urn:profile:researcher-ryan"
    relation: specializes_from
```

- Distinct from `delegates_to` (runtime work handoff).
- Resolved via `AgentProfileRepository.resolve_profile` DRG traversal. Retired per-profile field form rejected at load time.
- `enhances` = field-merge (preserves action sequence + step I/O); `overrides` = full replacement. Silently dropping steps or stripping step I/O is rejected.

### Profile Load Diagnostics

`AgentProfileRepository.skipped_profiles` exposes load failures without filesystem rescans. Included in `spec-kitty doctor doctrine --json`. A pack with invalid profiles is NOT reported healthy even if DRG counts are valid (FR-010).

### Deferred Items

- [#1622](https://github.com/Priivacy-ai/spec-kitty/issues/1622): `coordination.status_service` dead-symbol debt
- [#1623](https://github.com/Priivacy-ai/spec-kitty/issues/1623): `doctor.py` god-module split (FR-012)
- [#1624](https://github.com/Priivacy-ai/spec-kitty/issues/1624): `_tag_source` provenance sidecar typing (FR-013)

---

## Branch Protection and CI

`main` has a **Protect Main Branch** CI workflow that enforces the no-direct-push policy. A "Protect Main Branch" failure on CI means code bypassed the PR workflow and must be addressed by revert + re-submit.

- `spec-kitty merge` merges lane branches into **local main** only — do NOT use `spec-kitty merge --push` or `git push origin main`.
- After `spec-kitty merge` completes locally, create a PR branch: `git checkout -b pr/<slug> && git push origin pr/<slug>` and open a PR with `gh pr create`.
- The only CI result relevant to code health is **CI Quality**. The protect-main failure indicates a workflow violation.

**Recovery if origin/main is accidentally pushed:** Do NOT force-push (branch protection blocks it). Create a `revert/<slug>` branch from origin/main, commit a single revert, open a PR to merge it, then open the real PR from the mission branch.

---

## Docker Mode Policy (`spec-kitty-saas`)

When work touches `/spec-kitty-saas`, use two explicit Docker modes:

- **`dev-live`** (implementation/debug loops): `make docker-app-up-live`, `make docker-app-down-live`
- **`prod-like`** (pre-merge/pre-deploy gate): `make docker-app-up`, `make docker-auth-check` (required before Fly promotion), `make docker-app-down`

Default to `dev-live` while editing Python, templates, or assets. Always run and pass `prod-like` auth preflight before merge or Fly promotion. If tracker connectors are missing in UI, verify waffle flag `tracker_connectors` is enabled for the team.

Runbook: `spec-kitty-saas/docs/docker-development-modes.md` in the sibling SaaS repo.

---

## Documentation Mission Patterns (0.11.0+)

**Modes:** `initial` (from scratch), `gap_filling` (audit + fill gaps), `feature_specific` (one feature/component).

**Divio types:** Tutorial (learning), How-To (task), Reference (API, often auto-generated), Explanation (architecture/why).

**Generators:** JSDoc (JS/TS, `npx`), Sphinx (Python, `sphinx-build`), rustdoc (Rust, `cargo`).

**Workflow:**
```bash
/spec-kitty.specify  # prompts for iteration_mode, divio_types, target_audience, generators
/spec-kitty.plan && /spec-kitty.tasks
/spec-kitty.implement  # creates Divio templates, configures generators, generates API docs
/spec-kitty.review && /spec-kitty.accept
```

**Gap-filling:** Auto-detects framework, classifies docs by Divio type, builds coverage matrix, prioritizes: HIGH (missing tutorials/reference for core), MEDIUM (how-tos for advanced), LOW (explanations). Output: `gap-analysis.md`.

**Troubleshooting:**
```bash
pip install sphinx sphinx-rtd-theme    # Python generator
npm install --save-dev jsdoc docdash   # JavaScript generator
```
Low-confidence classification: add `---\ntype: tutorial\n---` frontmatter. Unpopulated templates: replace all `[TODO: ...]` placeholders.

**Implementation:** `src/specify_cli/missions/documentation/mission.yaml`, `doc_generators.py`, `gap_analysis.py`, `doc_state.py`. User guide: [docs/architecture/documentation-mission.md](docs/architecture/documentation-mission.md).

---

## GitHub CLI Authentication

If `gh` fails with "Missing required token scopes" on org repos, `GITHUB_TOKEN` may have limited scopes. Unset it to use keyring auth (gho_* token with full `repo` scope):

```bash
unset GITHUB_TOKEN && gh auth status  # verify keyring token is active
unset GITHUB_TOKEN && gh issue comment <issue> --body "..."
```

## Other Notes

Never claim frontend works without Playwright proof. API responses don't guarantee UI works; frontend can fail silently (404 caught, shows fallback). This is enforced, not aspirational: the runnable regression guard lives at [`tests/ui/test_dashboard_wp_modal.py`](tests/ui/test_dashboard_wp_modal.py) (`PWHEADLESS=1 uv run pytest tests/ui/ -q`), runs headless in CI via [`.github/workflows/ui-e2e.yml`](.github/workflows/ui-e2e.yml), and is copy-template documented in [`docs/development/ui-e2e.md`](docs/development/ui-e2e.md) — extend that suite instead of asserting UI behavior from API responses alone.

---

## Skill Routing

When user's request matches a skill, invoke via Skill tool. When in doubt, invoke.

- Product ideas/brainstorming → `/office-hours`
- Strategy/scope → `/plan-ceo-review`
- Architecture → `/plan-eng-review`
- Design system/plan review → `/design-consultation` or `/plan-design-review`
- Full review pipeline → `/autoplan`
- Bugs/errors → `/investigate`
- QA/testing → `/qa` or `/qa-only`
- Code review/diff → `/review`
- Visual polish → `/design-review`
- Ship/deploy/PR → `/ship` or `/land-and-deploy`
- Save/resume context → `/context-save` / `/context-restore`

<!-- spec-kitty:orientation -->
**Spec Kitty v3.2.0rc39** — project: unknown (healthy)

Two usage patterns:
- **Full mission** (spec → plan → tasks → implement → review → merge):
  trigger: "spec out", "create a mission", "write a spec", "plan this"
  → run `/spec-kitty.specify`
- **Lightweight dispatch** (ad-hoc fix, question, or advice — no mission created):
  trigger: "hey spec kitty", "use spec kitty to", "spec kitty <anything>"
  → **ALWAYS run `spec-kitty dispatch "<request verbatim>"` — do NOT answer directly.**
  If you know the right profile, pass it to skip routing:
  `spec-kitty dispatch "<request verbatim>" --profile <profile-id>`
  Reason: `spec-kitty dispatch` loads governance context, routes the request,
  and opens the Op. Skipping it produces ungoverned, untracked responses.
  After finishing the work, close the Op:
  `spec-kitty profile-invocation complete --invocation-id <id> --outcome <done|failed|abandoned>`
<!-- /spec-kitty:orientation -->
