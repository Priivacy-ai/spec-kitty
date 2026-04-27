---
work_package_id: WP11
title: Documentation rewrite (docs/how-to/install-and-upgrade.md)
dependencies:
- WP08
- WP09
requirement_refs:
- FR-023
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T042
agent: "claude:opus:python-reviewer:reviewer"
shell_pid: "20703"
history:
- at: '2026-04-27T08:19:12Z'
  actor: planner
  note: WP authored from /spec-kitty.tasks
authoritative_surface: docs/how-to/install-and-upgrade.md
execution_mode: code_change
mission_id: 01KQ6YDNMX2X2AN4WH43R5K2ZS
mission_slug: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
owned_files:
- docs/how-to/install-and-upgrade.md
priority: P3
tags: []
---

# WP11 — Documentation rewrite

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP11 --agent <name>` after WP08 and WP09 merge (so the documented behavior actually exists).

## Objective

Make SC-008 land. Rewrite `docs/how-to/install-and-upgrade.md` to clearly explain "upgrade the CLI" vs "migrate this project", with worked examples for every FR-023 case, the new flags, the env vars, the exit codes, and a link to the JSON contract.

This is the user-facing deliverable for the mission. After this WP, a user reading this single page knows how to interpret every nag and every block message Spec Kitty produces about upgrades.

## Context

- Spec: SC-008.
- Plan: §"Implementation phasing" step 6.
- Quickstart: [`quickstart.md`](../quickstart.md) — use the structure as a starting point, but rewrite for an end-user audience (not implementers).
- Contract: link to `kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json` for tooling consumers.

## Subtasks

### T042 — Rewrite `docs/how-to/install-and-upgrade.md`

**Outline of the rewritten file** (sections, in order):

1. **Two upgrades, not one** — the conceptual split.
   - "Spec Kitty has two distinct upgrade concepts: upgrading the CLI itself, and migrating a project's `.kittify/` schema."
   - When you'd want each.
   - Reassurance: the CLI never silently upgrades itself, never touches projects you're not currently inside.

2. **Upgrade the CLI** — `spec-kitty upgrade --cli`.
   - What it does: prints install-method-specific guidance.
   - Examples for each install method (pipx, pip, brew, system package).
   - The "unknown install method" fallback — manual upgrade instructions.

3. **Migrate the current project** — `spec-kitty upgrade` (no flags) or `spec-kitty upgrade --project`.
   - Run from inside the project.
   - Preview with `--dry-run`.
   - Apply non-interactively with `--yes` (or `--force` — both work).
   - Idempotent and ordered.

4. **The throttled nag** — what it looks like, when you'll see it.
   - One-line message before normal output.
   - Throttled to once per 24 hours by default.
   - Configure with `SPEC_KITTY_NAG_THROTTLE_SECONDS` or `~/.config/spec-kitty/upgrade.yaml`.
   - Disable entirely with `--no-nag` or `SPEC_KITTY_NO_NAG=1`.

5. **The lazy gate** — when Spec Kitty refuses to run a command.
   - Worked example: stale project; explanation of the message; remediation.
   - Worked example: too-new project; explanation; remediation (upgrade the CLI).
   - Read-only / `--help` / `--version` / `upgrade*` always work.

6. **Behavior in CI** — deterministic, no network.
   - `CI=1` automatically suppresses the nag and skips the network call.
   - Same for non-TTY (e.g. piped stdout).
   - The lazy gate still runs — incompatible projects still block CI builds.

7. **Exit codes**.
   - `0` — success / safe pass-through.
   - `2` — usage error (e.g. `--cli --project` together).
   - `4` — project needs migration; run `spec-kitty upgrade`.
   - `5` — project too new for installed CLI; upgrade the CLI.
   - `6` — project metadata corrupt / unreadable.

8. **JSON output for tooling** — link to the contract.
   - Brief example: `spec-kitty upgrade --dry-run --json | jq .case`.
   - Schema link: `kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json`.
   - Stable across patch releases; minor releases may add fields.

9. **Troubleshooting**.
   - "I get the nag every time" → check throttle window / cache file.
   - "The CLI won't upgrade with the printed command" → install method may have changed; rerun `spec-kitty upgrade --cli` for fresh detection.
   - "I'm told my project is corrupt" → check `.kittify/metadata.yaml` exists, parses, and has `spec_kitty.schema_version` as an integer.
   - "I'm in CI and see no nag but commands still block" → expected; nag is suppressed but the project compatibility gate still runs.

**Steps**:
1. Read the current `docs/how-to/install-and-upgrade.md` to preserve any existing content that's still accurate (don't rewrite for the sake of it).
2. Write the rewrite per the outline above. Keep prose concise — diátaxis "how-to" style: imperative, task-focused.
3. Use ```bash``` fences for shell examples; ```json``` for JSON output examples.
4. Cross-link to: `kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/spec.md` (for the formal requirements), `contracts/compat-planner.json` (for tooling).

**Files**: `docs/how-to/install-and-upgrade.md`.

**Validation**: manual review during mission acceptance; markdown lint clean (`pre-commit run markdownlint --files docs/how-to/install-and-upgrade.md` if a lint hook exists).

## Definition of Done

- [ ] All nine sections present and complete.
- [ ] Every FR-023 case worked through with a concrete example.
- [ ] All new flags (`--cli`, `--project`, `--yes`, `--no-nag`) and env vars (`SPEC_KITTY_NO_NAG`, `SPEC_KITTY_NAG_THROTTLE_SECONDS`) documented.
- [ ] Exit codes 0/2/4/5/6 documented.
- [ ] Link to `contracts/compat-planner.json` present.
- [ ] No code samples reference flags that don't exist after WP09 merges (verify by running each documented command against a fixture project).
- [ ] Markdown lint clean if a hook exists.

## Risks

- The doc may drift from implementation if WP08/WP09 change shape. WP11 is intentionally last. If anything in WP08/WP09 review surfaces a behavior change, update WP11 in the same review pass.
- The "Troubleshooting" section is qualitative — keep it short and only document failure modes that can actually occur given the implementation.

## Reviewer Guidance

1. **Audience check**: this is for end users, not implementers. Avoid internal terms ("planner", "compat package") in user-facing prose; use "Spec Kitty" / "the CLI".
2. **Worked examples runnable**: the bash examples should literally produce the documented output against a fresh fixture project.
3. **Cross-link correctness**: the link to the JSON contract resolves correctly relative to the docs file's location.
4. **Conciseness**: target ≤ 250 lines for the whole file. Cut prose, keep examples.

## Implementation command

```bash
spec-kitty agent action implement WP11 --agent <name>
```

## Activity Log

- 2026-04-27T10:37:33Z – claude:sonnet:python-implementer:implementer – shell_pid=20347 – Started implementation via action command
- 2026-04-27T10:40:17Z – claude:sonnet:python-implementer:implementer – shell_pid=20347 – Ready: install-and-upgrade rewritten with all 9 sections, end-user voice, cross-linked
- 2026-04-27T10:40:40Z – claude:opus:python-reviewer:reviewer – shell_pid=20703 – Started review via action command
