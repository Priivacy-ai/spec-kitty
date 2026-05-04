# Contract: Command And Skill Surface Generation

## Scope

This contract covers #968 retired checklist cleanup and #964 generated skill frontmatter.

## Required Behavior

- Fresh command and skill generation must not produce active `spec-kitty.checklist*` commands.
- Active registry entries, packaged command templates, generated command counts, runtime doctor expectations, installer cleanup, and docs/comments that name active counts must agree.
- Upgrade/install cleanup must remove stale checklist files only when they are package-managed, or ignore/preserve unknown files intentionally.
- Generated `SKILL.md` files must include required YAML frontmatter or use a documented host-accepted schema.
- The Codex/global `.agents/skills/spec-kitty.advise/SKILL.md` repro must be covered by automated generation tests.

## Acceptance Checks

- Fresh generation inventory contains zero active checklist commands.
- Registry and packaged template inventories match.
- Runtime diagnostics report the same command/skill counts that generation produces.
- Stale package-managed checklist files are cleaned up.
- Unknown user-authored files are not deleted by broad name matching.
- Generated `SKILL.md` files parse as frontmatter-bearing Markdown for the target host surface.

## Non-Goals

- Resurrecting `checklist`.
- Renaming active user-facing commands.
- Deleting user-owned custom commands or skills based only on filename pattern.
