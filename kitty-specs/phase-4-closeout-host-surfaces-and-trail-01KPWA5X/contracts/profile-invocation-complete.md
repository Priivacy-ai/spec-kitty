# Contract: `spec-kitty profile-invocation complete` (extended)

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Covers**: FR-007 (correlation), FR-009 (mode enforcement at promotion), FR-012 (local-first invariant)
**Target file**: `src/specify_cli/cli/commands/profile_invocation.py` (CLI) + `src/specify_cli/invocation/executor.py::complete_invocation` (runtime)

## Purpose

Close an open profile invocation record and, optionally:

1. Promote its output to a Tier 2 evidence artifact (**existing** behaviour; now mode-gated).
2. Attach one or more correlation links to the invocation JSONL — artifact references and/or a single commit SHA (**new**).

## Command Shape

```
spec-kitty profile-invocation complete \
    --invocation-id <id> \
    [--outcome done|failed|abandoned] \
    [--evidence <path>] \
    [--artifact <path>]... \
    [--commit <sha>] \
    [--json]
```

### Flag semantics

| Flag | Cardinality | Type | Required | Default | Description |
|------|-------------|------|----------|---------|-------------|
| `--invocation-id` | 1 | str (ULID) | yes | — | Target invocation file. |
| `--outcome` | 1 | enum `done` / `failed` / `abandoned` | no | `None` | Recorded on the `completed` event. |
| `--evidence` | 1 | path-or-string | no | `None` | Tier 2 promotion trigger. Mode-gated: rejected for `advisory` / `query`. |
| `--artifact` | ≥ 0 | path-or-string | no | — | **Repeatable.** Each value appends one `artifact_link` event. |
| `--commit` | 0 or 1 | str (SHA) | no | `None` | **Singular.** Appends one `commit_link` event. |
| `--json` | flag | bool | no | false | Existing behaviour — JSON output. |

### Execution order

On a successful invocation with all flags present, the runtime performs these steps in order:

1. Read `started` event (first line of the invocation JSONL).
2. **Mode enforcement** (FR-009): if `--evidence` is set and the derived `mode_of_work` ∈ `{advisory, query}`, raise `InvalidModeForEvidenceError` and exit **without** appending any new lines.
3. Append `completed` event (existing `write_completed`).
4. If `--evidence` is set (and mode check passed): resolve + normalise `ref`, then call existing `promote_to_evidence()`.
5. For each `--artifact <path>`: resolve + normalise, append `artifact_link` event.
6. If `--commit <sha>`: append `commit_link` event.
7. Submit `completed` to SaaS propagator (existing behaviour). Correlation events are **also** submitted to the propagator, but projection is subject to `POLICY_TABLE` (see `projection-policy.md`).

### Why steps 5 and 6 run after step 3

The append-only invariant holds in both orderings, but closing the invocation first lets readers distinguish `completed` from the correlation tail. Running correlation writes after the `completed` event also means a filesystem failure on a correlation write leaves the invocation in a fully-closed state — a retry of `complete` with the remaining correlation flags is a clean append, not a recovery.

## Error shapes

| Condition | Error class | Exit code | Message guidance |
|-----------|-------------|-----------|------------------|
| `--invocation-id` points to missing file | `InvocationError` | 2 | "Invocation record not found: <id>." |
| Already-completed invocation | `AlreadyClosedError` | 2 | Existing. |
| `--evidence` supplied on `advisory` or `query` | `InvalidModeForEvidenceError` (new) | 2 | "Cannot promote evidence on invocation <id>: mode is <mode>; Tier 2 evidence is only allowed on task_execution or mission_step invocations." |
| Filesystem write fails for any event | `InvocationWriteError` | 2 | Existing. |

## Ref normalisation (for `--artifact` and `--evidence`)

Per `data-model.md` §6:

- Resolve the input path. If resolution succeeds and the resolved path is under `repo_root`, persist the **repo-relative** string.
- Otherwise persist the **absolute resolved** path.
- If resolution raises (malformed input), persist the input verbatim — same fallback the existing `executor.complete_invocation` already uses for unreadable evidence refs.

This normalisation rule applies uniformly to both `--artifact` and `--evidence`, so correlation refs and evidence refs read the same.

## JSON output (when `--json` is set)

Response shape extended to report appended correlation events:

```json
{
  "result": "success",
  "invocation_id": "01HXYZ...",
  "outcome": "done",
  "evidence_ref": "kitty-specs/042-foo/evidence/snapshot.md",
  "artifact_links": ["kitty-specs/042-foo/tasks/WP03.md", "build/report.html"],
  "commit_link": "a1b2c3d4e5f67890..."
}
```

- `evidence_ref` is present only when `--evidence` was supplied and promotion succeeded.
- `artifact_links` is an array (possibly empty). Order matches the input order of `--artifact` flags.
- `commit_link` is a string or `null`.
- Existing fields (`result`, `invocation_id`, `outcome`) are unchanged.

On error, the existing JSON error envelope shape is used.

## Invariants

- **No existing JSONL line is mutated.** All new events are append-only (C-004).
- **Tier 1 unconditional.** The `completed` event is written before any correlation append; a filesystem failure on correlation does not leave the invocation half-closed. Tier 1 must keep working with SaaS disabled, unauthenticated, or network-unreachable (C-002, FR-012).
- **No new top-level command.** This is a flag extension on an existing subcommand (C-008).
- **Backwards-compatible.** Omitting `--artifact` and `--commit` yields identical behaviour to 3.2.0a5. Pre-mission invocations (no `mode_of_work` field on `started`) accept `--evidence` — `None` mode skips enforcement.

## Acceptance tests (selected)

These tests live in `tests/specify_cli/invocation/test_correlation.py` (new) and `tests/specify_cli/invocation/test_invocation_e2e.py` (extended):

1. `complete` with two `--artifact` values appends two `artifact_link` events in order.
2. `complete` with `--commit abc123` appends exactly one `commit_link` event.
3. `complete` with `--artifact kitty-specs/042/spec.md` (under checkout) persists `"kitty-specs/042/spec.md"`.
4. `complete` with `--artifact /tmp/report.log` (outside checkout) persists `"/tmp/report.log"`.
5. `complete` with `--artifact ./build/out.log` persists `"build/out.log"` (repo-relative).
6. `complete` on an `advisory` invocation with `--evidence path` raises `InvalidModeForEvidenceError`; no `completed` event, no evidence artifact, no correlation events written.
7. `complete` on a `task_execution` invocation with `--evidence path --artifact other --commit sha` writes (in order) `completed` → `artifact_link` → `commit_link`, and promotes evidence to `.kittify/evidence/<id>/`.
8. `complete` with sync disabled writes all events locally; `.kittify/events/propagation-errors.jsonl` remains empty.
9. Second call to `complete` for the same invocation_id raises `AlreadyClosedError` before any mutation (existing behaviour preserved).
