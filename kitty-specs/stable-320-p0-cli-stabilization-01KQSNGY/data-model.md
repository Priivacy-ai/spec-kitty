# Data Model: 3.2.0 Stable P0 CLI Stabilization

## Mission

- **Fields**: mission id, slug, branch contract, status artifacts, tasks directory, review artifacts, generated planning artifacts.
- **Rules**: The mission remains on `main` for planning/base and final merge. Mission status, mission review, and merge preflight cannot pass silently if completed WP state contradicts latest rejected review evidence.

## Work Package

- **Fields**: WP id, lane, status, frontmatter metadata, review-cycle artifact links, activity/history entries.
- **Rules**: A transition to `approved` or `done` is invalid when the latest applicable review-cycle artifact has `verdict: rejected`, unless a durable override exists.
- **State transitions in scope**:
  - planned/doing/for_review to approved or done through agent task commands, review actions, or merge/review acceptance paths.
  - done/approved state evaluated by mission status, mission review, and merge preflight diagnostics.

## Review-Cycle Artifact

- **Fields**: WP id, cycle number, verdict, reviewer metadata, created/updated timestamps where present, feedback pointers, optional override metadata or linked override reference.
- **Rules**:
  - Latest cycle is determined by the highest applicable cycle number for a WP.
  - `verdict: rejected` is blocking by default.
  - Later non-rejected terminal verdicts supersede earlier rejected cycles.

## Review Override

- **Fields**: WP id, rejected artifact reference, arbiter/orchestrator identity where available, reason, timestamp, and target transition.
- **Rules**:
  - Must be explicit operator intent.
  - Must be recorded before or as part of accepting the otherwise blocked transition.
  - Must remain discoverable by later mission review and merge diagnostics.

## Status Event

- **Fields**: event id or equivalent ordering signal, mission/WP identity, event kind, payload, timestamp, source command.
- **Rules**:
  - Bootstrap and emit tests must complete deterministically.
  - Fixture or adapter isolation must not weaken status semantic checks.

## Command Registry Entry

- **Fields**: command name, active/retired status, template source, generated output path, owning package/manifest proof, diagnostic count membership.
- **Rules**:
  - Retired `checklist` must not appear in active registries or fresh generated assets.
  - Stale installed checklist files are removed only when package-managed, or ignored/preserved intentionally when ownership is not proven.

## Generated Skill File

- **Fields**: skill name, host target, `SKILL.md` path, YAML frontmatter keys, body content source, generated timestamp only if the generator already uses one.
- **Rules**:
  - Required YAML frontmatter must be present in generated host-visible files.
  - The Codex/global `.agents/skills/spec-kitty.advise/SKILL.md` repro must be covered.

## Fresh Surface Evidence

- **Fields**: generation command, temporary output root, command inventory, skill inventory, warnings, validation result.
- **Rules**:
  - Evidence must prove command/skill generation is internally consistent.
  - Evidence must prove no retired checklist command is generated.
  - Evidence must prove generated skills have required frontmatter.
