---
name: spec-kitty-orchestrator-api-operator
description: >-
  Teach external orchestration systems how to drive spec-kitty workflows through
  the orchestrator-api subcommand. Covers contract versioning, feature state
  queries, work package transitions, policy metadata, and merge operations.
  Triggers: "use orchestrator-api", "build a custom orchestrator",
  "automate externally", "integrate CI with spec-kitty", "call spec-kitty from
  another tool", "orchestrator contract", "external automation".
  Does NOT handle: host-internal lane mutation (use the host CLI directly),
  runtime loop advancement (use spec-kitty next), mission sequencing logic
  (the mission state machine owns that), or setup/repair diagnostics.
---

# spec-kitty-orchestrator-api-operator

Teach agents and external systems how to use `spec-kitty orchestrator-api` to
drive workflows from outside the host CLI. The orchestrator-api is the only
supported entry point for external automation -- direct frontmatter mutation,
git worktree manipulation, or internal CLI internals are not part of the
contract.

---

## When to Use This Skill

- Build an external orchestrator that drives spec-kitty workflows
- Integrate CI/CD pipelines with spec-kitty state transitions
- Query feature and work package state from an external tool
- Understand the boundary between host CLI and external API

Do NOT use when the caller is an agent inside the host CLI (use
`spec-kitty next`), wants setup/repair (use setup-doctor), or wants
mission sequencing (the state machine owns that).

---

## Step 1: Verify the API Contract

```bash
spec-kitty orchestrator-api contract-version --provider-version "1.0.0"
```

Check that `api_version` matches your orchestrator's expected version and
`min_supported_provider_version` is at or below your version. A
`CONTRACT_VERSION_MISMATCH` error means the orchestrator must be updated.

**Rule:** Always call `contract-version` at orchestrator startup.

---

## Step 2: Query Feature State

```bash
spec-kitty orchestrator-api feature-state --feature <slug>
spec-kitty orchestrator-api list-ready --feature <slug>
```

`feature-state` returns summary counts and per-WP lane details. `list-ready`
returns only WPs whose dependencies are satisfied, each with a
`recommended_base` value. Both are query-only and safe to poll.

---

## Step 3: Respect the Host Boundary

The orchestrator-api is the ONLY supported interface for external systems.
Do not write frontmatter directly, invoke internal CLI commands, or create
worktrees manually. See `references/host-boundary-rules.md` for the full
boundary specification, decision matrix, and anti-patterns.

---

## Step 4: Start Implementation with Policy

Claim and start a work package by providing policy metadata.

```bash
spec-kitty orchestrator-api start-implementation \
  --feature <slug> --wp WP01 --actor "ci-bot" \
  --policy '{"orchestrator_id":"my-orch","orchestrator_version":"1.0.0",...}'
```

The `--policy` flag takes a JSON object with required fields: `orchestrator_id`,
`orchestrator_version`, `agent_family`, `approval_mode`, `sandbox_mode`,
`network_mode`, `dangerous_flags`, `tool_restrictions`. See
`references/orchestrator-api-contract.md` for all field definitions.

The WP transitions planned -> claimed -> in_progress atomically. The response
includes `workspace_path` and `prompt_path`.

---

## Step 5: Transition Work Packages

Use `transition` for explicit lane changes after implementation or review.

```bash
spec-kitty orchestrator-api transition \
  --feature <slug> --wp WP01 --to for_review --actor "ci-bot" \
  --policy '{"orchestrator_id":"my-orch",...}'
```

**Target lanes:** `planned`, `claimed`, `in_progress`, `for_review`,
`approved`, `done`.

**Rules:**

- Run-affecting lanes (`claimed`, `in_progress`, `for_review`) require `--policy`
- Use `--force` only when recovering from a known-bad state
- Use `--note` to record transition reasoning in the audit trail
- Use `--review-ref` when transitioning to `for_review`

For `start-review`, use the dedicated composite command instead of `transition`.
See `references/orchestrator-api-contract.md` for all 9 commands.

---

## Step 6: Record History and Complete

```bash
# Append a history note
spec-kitty orchestrator-api append-history \
  --feature <slug> --wp WP01 --actor "ci-bot" --note "Tests passed"

# Accept feature (all WPs must be done)
spec-kitty orchestrator-api accept-feature --feature <slug> --actor "ci-bot"

# Merge feature
spec-kitty orchestrator-api merge-feature \
  --feature <slug> --target main --strategy squash --push
```

`accept-feature` returns `FEATURE_NOT_READY` if any WP is not in `done`.

---

## JSON Envelope

Every command returns a canonical JSON envelope with `contract_version`,
`command`, `timestamp`, `correlation_id`, `success`, `error_code`, and `data`.
Parse `success` first. On failure, read `error_code` for programmatic handling.

---

## What This Skill Does NOT Cover

- **Mission sequencing** -- use `spec-kitty next` (the state machine owns that)
- **Host-internal mutations** -- agents inside the host CLI use
  `spec-kitty agent tasks move-task`, not orchestrator-api
- **Setup and repair** -- use the setup-doctor skill

---

## References

- `references/orchestrator-api-contract.md` -- Full command reference with all 9 commands, flags, output fields, and error codes
- `references/host-boundary-rules.md` -- When to use orchestrator-api vs host CLI, anti-patterns, boundary rules
