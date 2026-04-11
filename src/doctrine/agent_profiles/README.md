# Agent Profiles

**Agent profiles** are doctrine artifacts that define an agent's identity — its role,
specialization boundaries, collaboration contracts, and initialization behavior.
Profiles are the **identity layer** beneath missions: missions orchestrate *what work
happens*; profiles govern *who does the work and how they behave*.

An agent profile is distinct from a tool configuration. An **agent** is a logical
collaborator identity (implementer, reviewer, architect); a **tool** is a concrete
runtime product (Claude Code, Codex, opencode). This package defines agent identity;
tool installation is managed by `ToolConfig`.

## 6-Section Structure

Each profile defines:

1. **Context Sources** — Doctrine layers and directives to load
2. **Purpose** — What the agent does and does not do
3. **Specialization** — Primary focus, secondary awareness, avoidance boundaries
4. **Collaboration Contract** — Handoff partners, output artifacts, canonical verbs
5. **Mode Defaults** — Operating modes with descriptions and use-cases
6. **Initialization Declaration** — Self-description loaded at session start

## Two-Source Loading

Profiles are loaded from two sources with field-level merge:

- **Shipped profiles** (`shipped/`) — 7 reference profiles included in the package
- **Project profiles** (`.kittify/charter/agents/`) — Custom overrides per project

Project profiles override shipped profiles at field level when sharing the same
`profile-id`.

## Shipped Profiles

| Profile ID    | Name               | Role        |
|---------------|--------------------|-------------|
| `implementer` | Implementer Ivan   | implementer |
| `reviewer`    | Reviewer Renata    | reviewer    |
| `architect`   | Architect Alphonso | architect   |
| `planner`     | Planner Petra      | planner     |
| `designer`    | Designer           | designer    |
| `researcher`  | Researcher Rosa    | researcher  |
| `curator`     | Curator Carla      | curator     |

## Python API

- `AgentProfile` — Pydantic domain model
- `AgentProfileRepository` — Two-source loading, hierarchy, weighted matching
- `RoleCapabilities` / `DEFAULT_ROLE_CAPABILITIES` — Role-based capability defaults

## Schema

Profiles are validated against `schemas/agent-profile.schema.yaml`.

## Glossary Reference

See [Agent](../../../glossary/contexts/identity.md#agent) and
[Tool](../../../glossary/contexts/execution.md#tool) in the glossary for the
canonical naming distinction.
