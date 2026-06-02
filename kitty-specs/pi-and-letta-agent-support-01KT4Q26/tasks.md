# Tasks: Pi and Letta Code Agent Support

**Mission**: `pi-and-letta-agent-support-01KT4Q26`
**Branch**: `main` → `main`
**Date**: 2026-06-02
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Context

Most of the Pi and Letta implementation (config registration, Agent Skills, init flow, gitignore, CLI, tests) landed in earlier development cycles and is already on `main`. This mission completes the two remaining gaps: (1) an upgrade migration to backfill existing projects, and (2) decision records + documentation to satisfy DIRECTIVE_003 and DIRECTIVE_037.

## Subtask Index

| ID   | Description                                                        | WP   | Parallel |
|------|--------------------------------------------------------------------|------|----------|
| T001 | Write `m_3_2_10_pi_letta_backfill.py` migration class skeleton    | WP01 | —        |
| T002 | Implement gitignore backfill logic (`.pi/`, `.letta/` if missing)  | WP01 | —        |
| T003 | Implement skill-pack trigger (detect missing skills, call installer)| WP01 | —        |
| T004 | Register migration and bump target version string                  | WP01 | —        |
| T005 | Write integration tests for the migration                          | WP01 | [P]      |
| T006 | Write ADR for Pi skill-only support decision                       | WP02 | [P]      |
| T007 | Write ADR for Letta skill-only support decision                    | WP02 | [P]      |
| T008 | Update CLAUDE.md agent count (17 → 19) and agent tables            | WP02 | [P]      |
| T009 | Close GitHub issues #1050 and #1054 with implementation summaries  | WP02 | [P]      |

## Work Packages

---

### WP01 — Upgrade Migration: Pi and Letta Backfill

**Phase**: Foundation
**Priority**: High — existing projects without migration will lack gitignore entries
**Estimated prompt size**: ~350 lines
**Depends on**: none (standalone)

**Goal**: Write, register, and test a `spec-kitty upgrade` migration that adds `.pi/` and `.letta/` gitignore entries and repairs missing Agent Skills for projects where these agents are configured.

**Included subtasks**:

- [x] T001 Write `m_3_2_10_pi_letta_backfill.py` migration class skeleton (WP01)
- [x] T002 Implement gitignore backfill logic for `.pi/` and `.letta/` (WP01)
- [x] T003 Implement skill-pack trigger for missing `.agents/skills/spec-kitty.*` files (WP01)
- [x] T004 Register migration in the migration chain and set target_version (WP01)
- [x] T005 Write integration tests covering both agents, idempotency, and dry-run (WP01)

**Implementation sketch**:
1. Create `src/specify_cli/upgrade/migrations/m_3_2_10_pi_letta_backfill.py` using `BaseMigration` + `@MigrationRegistry.register`.
2. In `apply()`, call `get_configured_agents(project_path)` to get the enabled agent list.
3. For `pi` and `letta`, if configured: use `GitignoreManager` to add `.pi/` or `.letta/` if absent.
4. For each configured agent, check `project_path / ".agents" / "skills" / f"spec-kitty.{cmd}" / "SKILL.md"` for any canonical command; if any are missing, call `command_installer.install()`.
5. Return a `MigrationResult` with a descriptive `changes_made` list; changes that are already applied return an empty list (idempotent).

**Risks**: The `command_installer.install()` call requires a skill registry; if the registry is unavailable (e.g., stripped wheel), the migration should log a warning and continue rather than fail.

**Prompt file**: [tasks/WP01-upgrade-migration-pi-letta-backfill.md](tasks/WP01-upgrade-migration-pi-letta-backfill.md)

---

### WP02 — Decision Records and Documentation

**Phase**: Closure
**Priority**: Medium — satisfies DIRECTIVE_003 and DIRECTIVE_037; should land with or shortly after WP01
**Estimated prompt size**: ~320 lines
**Depends on**: none (can run in parallel with WP01)

**Goal**: Capture the Pi and Letta design decisions in ADRs, update CLAUDE.md's agent count and tables, and close the tracking issues.

**Included subtasks**:

- [x] T006 Write ADR for Pi agent skill-only support decision (WP02)
- [x] T007 Write ADR for Letta agent skill-only support decision (WP02)
- [x] T008 Update CLAUDE.md agent count (17 → 19) and Agent Skills Agents table (WP02)
- [x] T009 Close GitHub issues #1050 and #1054 with implementation summaries (WP02)

**Implementation sketch**:
1. Write `architecture/3.x/adr/2026-06-02-1-pi-agent-skill-only-support.md` using the ADR template.
2. Write `architecture/3.x/adr/2026-06-02-2-letta-agent-skill-only-support.md` using the ADR template.
3. Update `CLAUDE.md`: change "17 AI agents total" → "19 AI agents total"; add Pi and Letta rows to the Agent Skills Agents table; update the `SKILL_ONLY_AGENTS` reference note if present.
4. Post a comment on GitHub issue #1050 summarising what was implemented and what was deferred (orchestrator invoker), then close it. Repeat for #1054.

**Parallel opportunities**: T006 and T007 can be written concurrently; T008 and T009 are independent.

**Prompt file**: [tasks/WP02-decision-records-and-documentation.md](tasks/WP02-decision-records-and-documentation.md)
