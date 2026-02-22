# Naming Decision: Tool vs Agent

**Decision date**: 2026-02-15
**Status**: Agreed and active

## Decision

- **Tool**: concrete execution product (Claude Code, Codex, opencode, etc.)
- **Agent**: logical collaborator identity/role in the workflow

## Why

- Avoids overloaded wording where one term means both product and role
- Makes event payloads and docs easier to interpret
- Improves cross-tool comparisons in workflow audits

## Usage Rule

- Use "tool" for install/config/invocation concerns
- Use "agent" for assignment/handoff/role concerns
