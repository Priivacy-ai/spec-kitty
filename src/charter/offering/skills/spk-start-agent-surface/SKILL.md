---
name: spk-start-agent-surface
description: "Choose the correct Spec Kitty workflow for Codex CLI, Claude Code, and supported slash-command or command-skill harnesses."
---

# spk-start-agent-surface

Use this skill when the question is about where Spec Kitty works, how commands
or skills appear in a specific agent, or why behavior differs by surface.

## Checks

1. Identify the surface: command line, Codex, Claude Code, slash-command host,
   or command-skill host.
2. Check whether slash commands, skills, and local filesystem access are
   available in that surface.
3. If commands are missing, route to `spk-admin-setup-doctor`.
4. If the user needs compatibility research, use the legacy
   `spec-kitty-agent-surface-research` skill when installed.

## Guidance

- Prefer local CLI workflows when the surface can read/write the repo.
- Prefer command skills for slash-command execution.
- Prefer `spk-*` skills for explanation, recovery, and orchestration.
- Do not assume cloud-hosted agents can access local `.kittify/`, `kitty-specs/`,
  or `.worktrees/` paths.
