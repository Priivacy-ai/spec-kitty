# Host Boundary Rules

When to use `spec-kitty orchestrator-api` vs the host CLI, and what external
systems must never do.

---

## The Boundary

Spec Kitty has two interfaces for driving workflows:

| Interface | Audience | Entry Point |
|-----------|----------|-------------|
| **Host CLI** | Agents running inside the project (Claude Code, Codex, etc.) | `spec-kitty next`, `spec-kitty agent tasks move-task`, slash commands |
| **Orchestrator API** | External systems (CI pipelines, custom orchestrators, dashboards) | `spec-kitty orchestrator-api <subcommand>` |

These are not interchangeable. Each has guarantees the other does not provide.

---

## When to Use the Orchestrator API

Use `spec-kitty orchestrator-api` when:

- The caller is a separate process, service, or pipeline -- not an agent
  running inside the spec-kitty project directory
- The caller needs a versioned JSON contract with stable error codes
- The caller must provide policy metadata (orchestrator identity, sandbox mode,
  tool restrictions) for audit and safety
- The caller coordinates multiple agents across multiple work packages
- The caller is a CI/CD system that needs to query state and trigger transitions

**Concrete examples:**

- A GitHub Actions workflow that assigns WPs to agents and tracks completion
- A custom dashboard that visualizes feature progress and triggers reviews
- A supervisor process that starts multiple agent containers in parallel
- A Slack bot that lets humans approve work packages

---

## When to Use the Host CLI

Use the host CLI (`spec-kitty next`, `spec-kitty agent tasks move-task`, slash
commands) when:

- The caller is an AI agent running inside the project directory
- The agent was launched by `spec-kitty next` or a slash command
- The agent has direct filesystem access to the worktree
- The agent is following a prompt file provided by the runtime

**Concrete examples:**

- Claude Code running `/spec-kitty.implement` inside a worktree
- Codex executing the prompt file from `spec-kitty next --agent codex`
- An agent moving its own WP to `for_review` after completing implementation

---

## What External Systems Must NOT Do

These anti-patterns bypass the orchestrator-api contract and can corrupt state,
break audit trails, or produce undefined behavior.

### Anti-pattern 1: Direct frontmatter mutation

```yaml
# WRONG: Editing WP frontmatter files directly
# kitty-specs/017-feature/tasks/WP01-setup.md
---
lane: in_progress  # <-- Do not write this directly!
---
```

**Why it breaks:** Skips guard validation, policy recording, history logging,
and lane transition hooks. The state machine does not know the transition
happened.

**Correct approach:** Use `spec-kitty orchestrator-api transition --to in_progress`.

### Anti-pattern 2: Calling internal CLI commands

```bash
# WRONG: Using host-internal commands from external systems
spec-kitty agent tasks move-task WP01 --to for_review
```

**Why it breaks:** Internal commands do not enforce policy metadata, do not
emit the JSON contract envelope, and may have different guard behavior than
the orchestrator-api.

**Correct approach:** Use `spec-kitty orchestrator-api transition`.

### Anti-pattern 3: Creating worktrees manually

```bash
# WRONG: Creating git worktrees without the API
git worktree add .worktrees/017-feature-WP01 -b 017-feature-WP01
```

**Why it breaks:** The orchestrator-api `start-implementation` command sets up
the worktree, generates the prompt file, records the claiming actor, writes
policy metadata, and transitions the WP atomically. Manual worktree creation
skips all of that.

**Correct approach:** Use `spec-kitty orchestrator-api start-implementation`.

### Anti-pattern 4: Polling by reading files

```bash
# WRONG: Reading frontmatter to determine WP state
grep "lane:" kitty-specs/017-feature/tasks/WP01-setup.md
```

**Why it breaks:** File content may be stale (another worktree committed a
change), partially written, or in a format that changes between versions.

**Correct approach:** Use `spec-kitty orchestrator-api feature-state` or
`list-ready`.

### Anti-pattern 5: Skipping contract-version check

```bash
# WRONG: Calling commands without verifying contract compatibility
spec-kitty orchestrator-api start-implementation --feature ...
```

**Why it breaks:** If the host CLI has been upgraded and the contract version
changed, command semantics may differ. The orchestrator may send fields the
host ignores or miss fields the host now requires.

**Correct approach:** Call `contract-version` at orchestrator startup.

### Anti-pattern 6: Skipping policy on run-affecting transitions

```bash
# WRONG: Transitioning to in_progress without policy
spec-kitty orchestrator-api transition --feature 017-feature --wp WP01 \
  --to in_progress --actor "ci-bot"
```

**Why it breaks:** Returns `POLICY_METADATA_REQUIRED`. Run-affecting lanes
(`claimed`, `in_progress`, `for_review`) require policy metadata for audit
and safety enforcement.

**Correct approach:** Include `--policy` with all required fields.

---

## Boundary Decision Matrix

| Scenario | Interface | Reason |
|----------|-----------|--------|
| Agent implements a WP it was assigned | Host CLI | Agent is inside the project |
| CI pipeline starts implementation for an agent | Orchestrator API | CI is external |
| Agent moves its own WP to for_review | Host CLI | Agent is inside the project |
| Dashboard moves a WP to approved | Orchestrator API | Dashboard is external |
| Agent queries its next step | Host CLI (`spec-kitty next`) | Agent is inside the project |
| Supervisor queries ready WPs | Orchestrator API (`list-ready`) | Supervisor is external |
| Agent reads its prompt file | Filesystem (direct read) | Prompt file is a local artifact |
| External tool reads WP state | Orchestrator API (`feature-state`) | External tool must use API |
| User accepts a feature from CLI | Host CLI (`spec-kitty accept`) | User is at the terminal |
| CI accepts a feature after all checks pass | Orchestrator API (`accept-feature`) | CI is external |

---

## Policy Metadata Purpose

Policy metadata serves three functions:

1. **Identity** -- `orchestrator_id` and `orchestrator_version` identify WHO
   is driving the workflow, enabling audit and blame tracking.

2. **Safety** -- `sandbox_mode`, `network_mode`, `dangerous_flags`, and
   `tool_restrictions` declare the execution environment. The host can enforce
   safety invariants or refuse transitions that violate project policy.

3. **Auditability** -- Policy is recorded in the WP history alongside every
   run-affecting transition. Post-incident review can reconstruct exactly what
   orchestrator, with what permissions, drove each state change.

---

## Summary

- External systems use `spec-kitty orchestrator-api` exclusively
- Agents inside the project use the host CLI exclusively
- Never mix the two interfaces for the same actor
- Always verify `contract-version` before issuing commands
- Always provide `--policy` for run-affecting transitions
- Never mutate frontmatter, create worktrees, or call internal commands from
  external systems
