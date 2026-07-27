---
work_package_id: WP09
title: Orchestrator API Reference Update
dependencies: [WP01]
requirement_refs: [FR-005]
planning_base_branch: fix/skill-audit-and-expansion
merge_target_branch: fix/skill-audit-and-expansion
branch_strategy: Planning artifacts for this feature were generated on fix/skill-audit-and-expansion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/skill-audit-and-expansion unless the human explicitly redirects the landing branch.
base_branch: 056-documentation-parity-sprint-WP01
base_commit: a3c2fae9fa7c40e05f6ae6b06619574b80195a42
created_at: '2026-03-22T14:59:00.879725+00:00'
subtasks: [T043, T044, T045, T046, T047, T048]
history:
- date: '2026-03-22'
  action: created
  agent: claude
  note: Generated from plan.md Phase 4
authoritative_surface: ''
execution_mode: code_change
mission_id: 01KN2371WVZGV7TH7WMR2CN9Q2
owned_files:
- docs/reference/orchestrator-api.md
- docs/reference/toc.yml
- src/doctrine/skills/spec-kitty-orchestrator-api-operator/SKILL.md
wp_code: WP09
---

# WP09: Orchestrator API Reference Update

## Objective

Expand existing `docs/reference/orchestrator-api.md` (currently 182 lines) with
content from the `spec-kitty-orchestrator-api-operator` skill. Add all 9
commands with flags, JSON output examples, error codes, and policy metadata.

## Source Material

Read `src/doctrine/skills/spec-kitty-orchestrator-api-operator/SKILL.md` and
`references/orchestrator-api-contract.md` and `references/host-boundary-rules.md`.
Read existing `docs/reference/orchestrator-api.md`.

## Implementation

### T043: All 9 commands with flags

Document each command with its full flag set (verify against `--help`):
1. `contract-version` [--provider-version]
2. `feature-state` --feature (required)
3. `list-ready` --feature (required)
4. `start-implementation` --feature --wp --actor --policy
5. `start-review` --feature --wp --actor --policy --review-ref
6. `transition` --feature --wp --to --actor [--note] [--policy] [--force] [--review-ref]
7. `append-history` --feature --wp --actor --note
8. `accept-feature` --feature --actor
9. `merge-feature` --feature [--target] [--strategy] [--push]

### T044: JSON output examples

Add real JSON output examples for the most-used commands:
- `feature-state` — show the summary counts and work_packages array
- `list-ready` — show ready_work_packages with recommended_base
- `contract-version` — show api_version and min_supported_provider_version

Run each command against a real feature to capture actual output.

### T045: Error code catalog

Add a table of all error codes:

| Code | Cause |
|---|---|
| CONTRACT_VERSION_MISMATCH | Provider version below minimum |
| FEATURE_NOT_FOUND | Feature slug doesn't resolve |
| WP_NOT_FOUND | WP ID doesn't exist |
| TRANSITION_REJECTED | Invalid lane transition |
| WP_ALREADY_CLAIMED | Another actor owns the WP |
| POLICY_METADATA_REQUIRED | Missing --policy on run-affecting lane |
| POLICY_VALIDATION_FAILED | Bad JSON or contains secrets |
| FEATURE_NOT_READY | Not all WPs done |
| PREFLIGHT_FAILED | Dirty worktrees or diverged target |
| UNSUPPORTED_STRATEGY | Bad merge strategy |

### T046: Policy metadata

Document the 7 required fields with a complete example:

```json
{
  "orchestrator_id": "my-ci-bot",
  "orchestrator_version": "1.0.0",
  "agent_family": "claude",
  "approval_mode": "manual",
  "sandbox_mode": "container",
  "network_mode": "restricted",
  "dangerous_flags": []
}
```

Explain that policy is required for run-affecting lanes (claimed, in_progress,
for_review) and recorded in the event log for auditability.

### T047: Host boundary rules

Add a section explaining what external systems must NOT do:
- Don't edit frontmatter directly
- Don't call internal CLI commands
- Don't create worktrees manually
- Don't poll by reading files
- Always check contract-version first

### T048: Update toc.yml

Verify `docs/reference/toc.yml` has the orchestrator-api entry (it likely
already does since the file exists).

## Definition of Done

- [ ] All 9 commands documented with flags
- [ ] JSON output examples included (from real CLI output)
- [ ] Error code catalog complete
- [ ] Policy metadata schema documented
- [ ] Host boundary rules included
- [ ] All commands verified against --help
- [ ] toc.yml verified

## Implementation Command

```bash
spec-kitty implement WP09 --base WP01
```

## Activity Log

- 2026-03-22T14:59:01Z – coordinator – shell_pid=21973 – lane=doing – Assigned agent via workflow command
- 2026-03-22T15:05:00Z – coordinator – shell_pid=21973 – lane=for_review – Orchestrator API reference expanded with all 9 commands verified against --help, real JSON output examples, complete error code catalog, policy metadata schema, and host boundary rules
- 2026-03-22T15:06:43Z – coordinator – shell_pid=21973 – lane=approved – Review passed: docs-only changes, correct files, toc updated
