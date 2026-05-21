---
title: /spec-kitty Host Skill
description: Contract for the natural-language /spec-kitty host surface that wraps ask/advise/do, executes the work in the host agent, and leaves a git-managed trace.
---

# /spec-kitty Host Skill

`/spec-kitty` is the host-facing natural-language entrypoint for governed work
outside the full mission loop. It is not a Python CLI subcommand. It is a skill,
slash command, prompt, or MCP prompt installed into a host such as Claude Code,
Codex, Cursor, Gemini, or another supported agent surface.

The CLI commands `spec-kitty ask`, `spec-kitty advise`, `spec-kitty do`, and
`spec-kitty profile-invocation complete` are backend primitives. The host skill
owns the user experience:

```text
User: /spec-kitty Which PRD has to do with Beads?

Host skill:
  1. opens a profile invocation
  2. reads the returned governance context
  3. performs the repo search or work
  4. answers the user in normal language
  5. writes a git-managed trace
  6. closes the invocation and links artifacts or commits
```

## Supported intents

The host skill must route common daily requests without exposing raw JSON or
requiring the user to know profile IDs:

| User intent | Example | Default profile/action behavior |
|---|---|---|
| Repo/spec lookup | `/spec-kitty what's in the PRD?` | Use a researcher profile, search repo-local specs, PRDs, docs, and issue references. |
| Research | `/spec-kitty research whether we should support Beads` | Use a researcher profile unless a more specific domain profile is obvious. |
| Advice | `/spec-kitty what should I do, this or that?` | Use an architect, planner, reviewer, or researcher profile based on topic. |
| Review | `/spec-kitty review the auth middleware changes` | Use a reviewer/security/profile-specific reviewer when possible. |
| Implementation | `/spec-kitty make this change` | Use implementer routing, produce code/docs, run checks, and create a content commit when appropriate. |

If routing is ambiguous, the host skill should choose the safest explicit
profile or ask one short clarification. It should not surface `ROUTER_NO_MATCH`
as the primary user experience for ordinary lookup, research, or advice.

## Required host loop

For every `/spec-kitty` invocation that reaches the CLI, the host skill must run
the full open/work/trace/complete loop:

1. Resolve the project root. If no initialized Spec Kitty project is found, stop
   with a clear setup error before opening an invocation.
2. Open the invocation with `--json`, preferring `ask <profile>` when the host
   has classified the intent and using `advise` or `do` only as internal routing
   helpers.
3. Read `governance_context_text`, `profile_id`, `action`,
   `governance_context_hash`, and `invocation_id` from the JSON payload.
4. Execute the actual work in the host agent. The CLI does not call another LLM
   and does not search the repository on its own.
5. Produce a user-visible answer or work product.
6. Write a git-managed trace under `kitty-specs/_profile-invocations/`.
7. If code, docs, or other durable project files changed, commit those content
   changes before closing the invocation.
8. Close the invocation with `spec-kitty profile-invocation complete`, linking
   artifacts and the primary content commit when one exists.
9. Commit the trace file so the user has a timestamped, reviewable git record.

On failure after an invocation has opened, the host skill must still call
`profile-invocation complete --outcome failed` or `--outcome abandoned` unless
the process was interrupted before it could recover.

## Git-managed trace

The Tier 1 JSONL file at `.kittify/events/profile-invocations/<id>.jsonl` is the
runtime audit log. It is local and append-only, but `.kittify/events/` is
runtime state and is not the git-managed project record.

The `/spec-kitty` host skill must also create a tracked trace file:

```text
kitty-specs/_profile-invocations/YYYY-MM-DD/
  YYYY-MM-DDTHHMMSSZ-<slug>-<invocation_id>/
    trace.md
```

The trace file is the git-managed projection of the invocation. It is managed
like other Spec Kitty artifacts such as `spec.md`: it is explicit, reviewable,
and committed to the repository.

Minimum trace content:

```markdown
# /spec-kitty Trace: <short title>

- Invocation ID: <id>
- Started: <ISO-8601 timestamp>
- Completed: <ISO-8601 timestamp>
- Profile: <profile_id>
- Action: <action>
- Governance Context Hash: <hash>
- Request: <user request>
- Outcome: done | failed | abandoned
- Content Commit: <sha or none>
- Artifacts: <paths or none>

## Answer

<the answer returned to the user, or a summary of the work performed>

## Evidence

<repo paths searched, commands run, checks performed, citations, or failure notes>
```

For read-only research or advice, the trace commit may be the only git commit.
For code or doc changes, the content commit comes first; the trace commit comes
second and records the content commit SHA. This avoids a circular dependency
where the invocation needs to link a commit SHA before the trace file itself has
been committed.

## Relationship to `profile-invocation complete`

The host skill closes the local JSONL trail with:

```bash
spec-kitty profile-invocation complete \
  --invocation-id <id> \
  --outcome done \
  --artifact <changed-or-created-path> \
  --commit <primary-content-commit-sha>
```

For read-only answers, omit `--commit` unless there is a separate content
commit. The git-managed trace still captures the answer and is committed by the
host as a history record.

If the invocation produced checkable evidence, the host may also pass
`--evidence <path>` for eligible `task_execution` invocations. Evidence
promotion is local in the 3.2.x release line; the tracked `trace.md` remains the
durable git record that reviewers can inspect with normal git tooling.

## Acceptance examples

### PRD lookup

```text
User: /spec-kitty Which PRD has to do with Beads?

Expected behavior:
- Host opens `ask researcher-robbie "..."`
- Host searches PRD/spec/doc locations in the repo.
- Host answers with the matching PRD path and reason.
- Host writes `kitty-specs/_profile-invocations/.../trace.md`.
- Host closes the invocation with outcome `done`.
- Host commits the trace file.
```

### Advice

```text
User: /spec-kitty What should I do, this approach or that approach?

Expected behavior:
- Host opens an invocation for the appropriate advisory profile.
- Host applies the governance context to the trade-off analysis.
- Host answers with a recommendation and rationale.
- Host writes and commits the trace file.
- Host closes the invocation.
```

### Implementation

```text
User: /spec-kitty Update the auth middleware error handling.

Expected behavior:
- Host opens an implementer or reviewer-routed invocation.
- Host edits code, runs checks, and commits the content changes.
- Host closes the invocation with `--commit <content-sha>` and relevant
  `--artifact` paths.
- Host writes and commits the trace file with the content SHA and checks.
```

