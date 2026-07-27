# Specify Brief Intake Mode

**Mission ID**: 01KPMXQBM67RJQTCWB31SC6PGM
**Mission Slug**: specify-brief-intake-mode-01KPMXQB
**Mission Type**: software-dev
**Status**: Specified
**Created**: 2026-04-20
**GitHub Issue**: Priivacy-ai/spec-kitty#700

---

## Problem Statement

Every coding harness ships some form of plan mode. Users arrive at `/spec-kitty.specify` having already done serious planning work — yet the command ignores it, running a full discovery interview that re-asks questions the plan already answers. The same problem applies to tracker tickets fetched by `mission create --from-ticket`: the ticket body contains the requirements, but specify re-derives them from scratch.

This feature lets `/spec-kitty.specify` consume pre-existing plan documents and tracker tickets instead of fighting them.

---

## Goals

- Enable users to ingest any plan document (Markdown file, piped content) into a canonical brief artifact that `/spec-kitty.specify` can detect and use
- When a brief is present, reduce the discovery interview to gap-filling only (0–2 questions for a comprehensive plan, up to 5 for a sparse one)
- Reuse the existing `ticket-context.md` path so tracker-ticket-originated missions also benefit
- Preserve the full quality bar: same spec format, same checklists, same readiness gate

---

## Out of Scope

- `--auto` flag for detecting harness plan files by location (deferred to a follow-on mission; see GitHub issue #700 Part A extension)
- Changes to `src/specify_cli/tracker/ticket_context.py` (detection added to the template only)
- Support for non-Markdown plan documents (HTML, PDF, etc.)
- Any changes to the `/spec-kitty.plan`, `/spec-kitty.tasks`, or downstream commands

---

## Actors

| Actor | Role |
|-------|------|
| Developer | Runs `spec-kitty intake` and then `/spec-kitty.specify` |
| AI Agent | Executes the specify template; reads brief and extracts requirements |
| Spec Kitty CLI | Provides the `intake` command and writes brief artifacts |

---

## User Scenarios

### Scenario 1 — Developer with a plan document (primary flow)

1. Developer writes `PLAN.md` using Claude Code plan mode, Cursor, Codex, or any editor
2. Developer runs `spec-kitty intake PLAN.md`
3. CLI writes `.kittify/mission-brief.md` (plan content with provenance header) and `.kittify/brief-source.yaml`
4. Developer runs `/spec-kitty.specify`
5. Agent detects `.kittify/mission-brief.md`, prints "BRIEF DETECTED", enters brief-intake mode
6. Agent presents a one-paragraph summary of the plan
7. Agent asks 0–2 gap-filling questions (or none for a comprehensive plan)
8. Agent presents extracted FR/NFR/C requirement set for one-round user confirmation
9. Agent writes `spec.md`, commits it
10. Agent deletes the brief files

### Scenario 2 — Stdin / piped input

1. Developer runs `cat PLAN.md | spec-kitty intake -`
2. CLI reads from stdin; `.kittify/mission-brief.md` and `.kittify/brief-source.yaml` are written
3. Flow continues as Scenario 1 from step 4

### Scenario 3 — Tracker ticket origin (existing flow, new detection)

1. Developer previously ran `spec-kitty mission create --from-ticket linear:ABC-123`
2. `.kittify/ticket-context.md` already exists (written by the tracker command)
3. Developer runs `/spec-kitty.specify`
4. Agent detects `.kittify/ticket-context.md` (priority 2, fallback)
5. Brief-intake mode entered; spec produced from ticket content
6. After spec committed, agent deletes `ticket-context.md` and `pending-origin.yaml`

### Scenario 4 — Brief already exists without `--force`

1. Developer runs `spec-kitty intake PLAN.md` a second time
2. CLI exits with non-zero status: "Brief already exists at .kittify/mission-brief.md. Use --force to overwrite."
3. No files are modified

### Scenario 5 — No brief present (regression / normal flow)

1. Developer runs `/spec-kitty.specify` without any prior intake
2. No brief files detected
3. Normal Discovery Gate runs exactly as today — no change in behavior

### Scenario 6 — Inspect current brief

1. Developer runs `spec-kitty intake --show`
2. CLI prints the current brief content and provenance (source_file, ingested_at, brief_hash)
3. No files are modified

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `spec-kitty intake <path>` reads a plan document from the specified file path and stores its content as `.kittify/mission-brief.md` | Proposed |
| FR-002 | `spec-kitty intake -` reads plan content from stdin and stores it as `.kittify/mission-brief.md` | Proposed |
| FR-003 | The intake command prepends a provenance header block to the plan content before writing `.kittify/mission-brief.md`; the original content is otherwise unmodified | Proposed |
| FR-004 | The intake command writes `.kittify/brief-source.yaml` containing: `source_file` (original path or "stdin"), `ingested_at` (ISO 8601 UTC timestamp), `brief_hash` (SHA-256 hex digest of the raw plan content) | Proposed |
| FR-005 | If `.kittify/mission-brief.md` already exists and `--force` is not passed, the command exits with a non-zero status code and an error message; no files are modified | Proposed |
| FR-006 | With `--force`, the intake command overwrites existing `.kittify/mission-brief.md` and `.kittify/brief-source.yaml` | Proposed |
| FR-007 | `spec-kitty intake --show` prints the current brief content and provenance to stdout without modifying any files; exits with non-zero status if no brief exists | Proposed |
| FR-008 | Both `.kittify/mission-brief.md` and `.kittify/brief-source.yaml` are added to `.gitignore` following the same pattern as `ticket-context.md` and `pending-origin.yaml` | Proposed |
| FR-009 | The specify source template checks for `.kittify/mission-brief.md` as first priority before starting the Discovery Gate | Proposed |
| FR-010 | The specify source template checks for `.kittify/ticket-context.md` as second priority (fallback) when no mission brief is found | Proposed |
| FR-011 | When a brief file is detected, the agent prints "BRIEF DETECTED: `<filename>` (source: `<source_file>`)" and presents a one-paragraph summary of the plan to the user | Proposed |
| FR-012 | In brief-intake mode, the agent extracts functional requirements (FR-###), non-functional requirements (NFR-###), and constraints (C-###) directly from the brief without re-asking questions the brief already answers | Proposed |
| FR-013 | In brief-intake mode, the agent asks only gap-filling questions: 0–2 for a comprehensive brief (objective + constraints + approach + acceptance criteria), up to 5 for a sparse brief (goal statement only) | Proposed |
| FR-014 | Before writing `spec.md`, the agent presents the extracted requirement set to the user for a single round of confirmation; the user may correct or supplement before the spec is written | Proposed |
| FR-015 | After `spec.md` is committed, the agent deletes all brief files: `.kittify/mission-brief.md`, `.kittify/brief-source.yaml`, `.kittify/ticket-context.md` (if present), and `.kittify/pending-origin.yaml` (if present) | Proposed |
| FR-016 | When no brief file is detected, `/spec-kitty.specify` proceeds with the normal Discovery Gate with no change in behavior | Proposed |
| FR-017 | The updated specify source template is propagated to all 13 agent directories by running `spec-kitty upgrade` after the source edit | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The `intake` command completes within 3 seconds for plan files up to 1 MB | ≤ 3 seconds for ≤ 1 MB input | Proposed |
| NFR-002 | New code achieves 90% or higher line coverage in automated tests | ≥ 90% line coverage | Proposed |
| NFR-003 | mypy --strict reports zero type errors on all new modules | 0 type errors | Proposed |
| NFR-004 | Brief-intake mode reduces discovery question count to 0–2 for any plan that specifies objective, constraints, approach, and acceptance criteria | ≤ 2 questions for comprehensive plans | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | `src/specify_cli/tracker/ticket_context.py` is the reference pattern for `intake.py`; the write/read/clear pattern must be followed without deviation | Proposed |
| C-002 | Only the SOURCE template (`src/specify_cli/missions/software-dev/command-templates/specify.md`) is edited; agent copies in `.claude/`, `.amazonq/`, etc. are not modified directly | Proposed |
| C-003 | `spec-kitty upgrade` must be run after the source template is edited; the upgrade must succeed for all 13 configured agent directories | Proposed |
| C-004 | `src/specify_cli/tracker/ticket_context.py` is not modified; brief detection is added to the specify template only | Proposed |
| C-005 | Brief content is never copied verbatim into `spec.md`; the agent extracts and structures requirements using FR-###, NFR-###, C-### IDs | Proposed |
| C-006 | The spec produced by brief-intake mode must pass the same quality checklist and readiness gate as a spec produced by normal specify; the quality bar is not lowered | Proposed |
| C-007 | The `--auto` flag for harness plan location detection is explicitly out of scope for this mission | Proposed |

---

## Key Entities

| Entity | Location | Role |
|--------|----------|------|
| MissionBrief | `.kittify/mission-brief.md` | Transient local artifact: verbatim plan content with provenance header; consumed and deleted by specify |
| BriefSource | `.kittify/brief-source.yaml` | Provenance metadata: source_file, ingested_at, brief_hash; deleted alongside MissionBrief |
| TicketContext | `.kittify/ticket-context.md` | Existing artifact written by `mission create --from-ticket`; detected by specify as priority-2 brief |
| IntakeCommand | `src/specify_cli/cli/commands/intake.py` | New CLI module implementing `spec-kitty intake` |
| SpecifyTemplate | `src/specify_cli/missions/software-dev/command-templates/specify.md` | Source template receiving the new Brief Context Detection section |

---

## Success Criteria

1. A user with a comprehensive `PLAN.md` can run `spec-kitty intake PLAN.md` followed by `/spec-kitty.specify` and reach a committed `spec.md` with 0–2 discovery questions
2. A user with no brief file experiences no observable change in the `/spec-kitty.specify` workflow
3. After spec is committed, `.kittify/mission-brief.md` and `.kittify/brief-source.yaml` are absent from the working tree
4. All new code passes `mypy --strict` and achieves ≥ 90% line coverage in automated tests
5. The Brief Context Detection section is present in all 13 agent directories after `spec-kitty upgrade` completes

---

## Dependencies

| Dependency | Type | Notes |
|-----------|------|-------|
| `src/specify_cli/tracker/ticket_context.py` | Internal reference | Read-only reference; not modified |
| `spec-kitty upgrade` migration system | Internal | Must propagate template change to all 13 agent directories |
| `hashlib` (stdlib) | Runtime | SHA-256 hashing for `brief_hash` |
| `typer`, `rich` | Runtime | Existing CLI dependencies; no new packages required |

---

## Assumptions

| # | Assumption |
|---|-----------|
| 1 | `spec-kitty intake` is registered as a root-level standalone command, avoiding conflict with the existing `spec-kitty plan` command (which scaffolds plan.md and is unchanged) |
| 2 | SHA-256 hex digest of the raw (pre-header) plan content is sufficient for content fingerprinting |
| 3 | Brief files are transient local artifacts (following the `ticket-context.md` precedent); they are not expected to survive across machine boundaries, only across session restarts on the same machine |
| 4 | `source_agent` field seen in the GitHub issue's `brief-source.yaml` schema is optional metadata that may be omitted in the initial implementation |
| 5 | `spec-kitty upgrade` is already functional and will propagate source template changes correctly to all 13 configured agent directories |
