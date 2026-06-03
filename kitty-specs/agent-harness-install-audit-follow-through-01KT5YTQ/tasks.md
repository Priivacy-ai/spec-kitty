# Tasks: Agent Harness Install Audit Follow-Through

**Mission**: agent-harness-install-audit-follow-through-01KT5YTQ
**Branch**: kitty/mission-agent-harness-install-audit-follow-through-01KT5YTQ → main
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-----------|----|----------|
| T001 | Update `docs/explanation/ai-agent-architecture.md` table row for Codex path | WP01 | [P] |
| T002 | Update `docs/how-to/upgrade-project.md` to remove `.codex/skills/` reference | WP01 | [P] |
| T003 | Update `docs/reference/upgrade-lifecycle.md` to remove `.codex/skills/spec-kitty.*/` reference | WP01 | [P] |
| T004 | Update `docs/reference/environment-variables.md` CODEX_HOME section | WP01 | [P] |
| T005 | Update `docs/reference/supported-agents.md` CODEX_HOME references | WP01 | [P] |
| T006 | Rework `docs/how-to/setup-codex-spec-kitty-launcher.md` to current model | WP01 | [P] |
| T007 | Run snapshot suite and capture failure output | WP02 | — |
| T008 | Locate and inspect snapshot files and source implement template | WP02 | — |
| T009 | Fix source template wording to canonical `approved or done` | WP02 | — |
| T010 | Regenerate snapshots for codex-implement and vibe-implement | WP02 | — |
| T011 | Run full 102-test suite to confirm zero failures | WP02 | — |
| T012 | Access Antigravity CLI and explore plugin/skills/MCP/hook command surface | WP03 | [P] |
| T013 | Document verified Antigravity install targets (global vs workspace, manifest shape) | WP03 | [P] |
| T014 | Smoke test Spec Kitty command skill install under Antigravity | WP03 | [P] |
| T015 | Review Kiro docs for Powers/extensions/plugin bundle primitive | WP03 | [P] |
| T016 | Classify Kiro: plugin-candidate or prompt-only for 3.3 scope | WP03 | [P] |
| T017 | Update `docs/reference/supported-harnesses.md` with Antigravity + Kiro entries | WP03 | — |
| T018 | Create or update harness how-to pages for Antigravity and Kiro | WP03 | — |

---

## Work Packages

---

### WP01 — Stale Codex Docs Cleanup

**Priority**: High
**Estimated prompt size**: ~350 lines
**execution_mode**: code_change
**Depends on**: none (bulk-edit gate: `occurrence_map.yaml` validated ✓)

**Goal**: Remove all active-guidance references to retired Codex install paths (`.codex/prompts/`, `.codex/skills/`, `CODEX_HOME=$(pwd)/.codex`) from 6 docs files and replace or remove per the `occurrence_map.yaml` classification.

**Subtasks**:
- [ ] T001 Update `docs/explanation/ai-agent-architecture.md` Codex path table row (WP01)
- [ ] T002 Update `docs/how-to/upgrade-project.md` `.codex/skills/` reference (WP01)
- [ ] T003 Update `docs/reference/upgrade-lifecycle.md` `.codex/skills/spec-kitty.*/` reference (WP01)
- [ ] T004 Update `docs/reference/environment-variables.md` CODEX_HOME section (WP01)
- [ ] T005 Update `docs/reference/supported-agents.md` CODEX_HOME references (WP01)
- [ ] T006 Rework `docs/how-to/setup-codex-spec-kitty-launcher.md` to current model (WP01)

**Implementation sketch**:
1. For each file listed: grep for stale strings, update per occurrence_map.yaml rules
2. Active how-to/reference → replace with `.agents/skills/spec-kitty.<command>/SKILL.md` and `$spec-kitty.<command>` syntax
3. `setup-codex-spec-kitty-launcher.md` → major rework: rewrite to current model or redirect to `docs/how-to/harnesses/codex.md`
4. After all edits: grep to verify zero occurrences in active docs

**Parallel opportunities**: T001–T006 all touch different files — safe to process in any order.
**Dependencies**: none
**Risks**: `setup-codex-spec-kitty-launcher.md` may need full rewrite; confirm with `docs/how-to/harnesses/codex.md` exists as redirect target before removing content.

**Prompt**: [WP01-stale-codex-docs-cleanup.md](tasks/WP01-stale-codex-docs-cleanup.md)

---

### WP02 — Command Renderer Snapshot Refresh

**Priority**: High
**Estimated prompt size**: ~280 lines
**execution_mode**: code_change
**Depends on**: none

**Goal**: Fix pre-existing snapshot drift in `tests/specify_cli/skills/test_command_renderer.py` for `codex-implement` and `vibe-implement`. Align WP lifecycle dependency-gate wording to canonical `approved or done` and regenerate snapshots. Full suite must pass (102 tests, zero failures).

**Subtasks**:
- [ ] T007 Run snapshot suite and capture failure output (WP02)
- [ ] T008 Locate snapshot files and inspect source implement template (WP02)
- [ ] T009 Fix source template wording to canonical `approved or done` (WP02)
- [ ] T010 Regenerate snapshots for codex-implement and vibe-implement (WP02)
- [ ] T011 Run full 102-test suite to confirm zero failures (WP02)

**Implementation sketch**:
1. `uv run pytest tests/specify_cli/skills/test_command_renderer.py -x 2>&1` — observe failures
2. Find source template: `src/doctrine/missions/mission-steps/*/implement/prompt.md`
3. Grep for `done` (without `approved`) in dependency-gate wording; fix to `approved or done`
4. Regenerate: `PYTEST_UPDATE_SNAPSHOTS=1 uv run pytest tests/specify_cli/skills/test_command_renderer.py`
5. Verify: `uv run pytest tests/specify_cli/skills/test_command_renderer.py` — all 102 pass

**Parallel opportunities**: none — sequential by nature (observe → fix → regenerate → verify).
**Dependencies**: none
**Risks**: Source template may not be the only location of stale wording; if snapshot diff shows wording that isn't in the template, grep `src/specify_cli/skills/` for `approved or done` to locate all rendering paths.

**Prompt**: [WP02-command-renderer-snapshot-refresh.md](tasks/WP02-command-renderer-snapshot-refresh.md)

---

### WP03 — Antigravity and Kiro Harness Verification

**Priority**: Medium
**Estimated prompt size**: ~420 lines
**execution_mode**: code_change
**Depends on**: none

**Goal**: Verify Antigravity CLI plugin/skills/MCP/hook install surfaces and Kiro plugin/Powers primitives via live access and upstream docs. Commit verified findings (or explicit "not verified" notes) to `docs/reference/supported-harnesses.md`, `docs/how-to/harnesses/antigravity.md`, and `docs/how-to/harnesses/kiro.md`. No implementation in `src/`.

**Subtasks**:
- [ ] T012 Access Antigravity CLI and explore plugin/skills/MCP/hook command surface (WP03)
- [ ] T013 Document verified Antigravity install targets (global vs workspace, manifest shape) (WP03)
- [ ] T014 Smoke test Spec Kitty command skill install under Antigravity (WP03)
- [ ] T015 Review Kiro docs for Powers/extensions/plugin bundle primitive (WP03)
- [ ] T016 Classify Kiro: plugin-candidate or prompt-only for 3.3 scope (WP03)
- [ ] T017 Update `docs/reference/supported-harnesses.md` with Antigravity + Kiro entries (WP03)
- [ ] T018 Create or update harness how-to pages for Antigravity and Kiro (WP03)

**Implementation sketch**:
1. Antigravity: run `agent --help`, `agent plugin`, `agent config`, `agent skills` (or equivalents); record actual command names and paths
2. Record: global vs workspace config dirs, manifest format (if any), whether `.agent/workflows/` and `.agent/skills/` are confirmed
3. Smoke test: attempt to install a Spec Kitty skill and invoke `$spec-kitty.specify`; document result
4. Kiro: browse `https://kiro.dev/docs` for Powers/extensions/plugins; check release notes and CLI help
5. Classify each agent; write findings into supported-harnesses.md entries
6. Create/update `docs/how-to/harnesses/antigravity.md` (new if Antigravity confirmed) and `docs/how-to/harnesses/kiro.md`

**Parallel opportunities**: T012–T014 (Antigravity) and T015–T016 (Kiro) can run in parallel; merge findings in T017–T018.
**Dependencies**: none
**Risks**: Antigravity CLI may not be installed locally; if access fails, record "not verified (2026-06-03, CLI unavailable)" rather than leaving entry blank. Kiro docs may not clearly state whether Powers is a bundle primitive — if ambiguous, classify as prompt-only with a noted caveat.

**Prompt**: [WP03-antigravity-kiro-harness-verification.md](tasks/WP03-antigravity-kiro-harness-verification.md)
