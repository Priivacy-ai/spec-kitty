# Data Model — Charter Golden-Path E2E (Tranche 1)

This mission's deliverable is a test asset; "data model" here means the entities, files, and JSON envelopes the test interacts with — not new persistent domain objects.

## Entities (test-visible state)

### E-001 — Temp project

| Attribute | Type | Notes |
|---|---|---|
| `path` | `pathlib.Path` | `tmp_path / "fresh-e2e-project"`; pytest auto-cleanup. |
| Initial state | filesystem | Empty git repo on `main` with `e2e@example.com` / `E2E Test` config; no other files. |
| Post-init state | filesystem | Contains `.kittify/`, agent dirs (`.codex/`), `.gitignore`, `.claudeignore`, all written by `spec-kitty init`. |
| Post-charter state | filesystem | `.kittify/charter/charter.md`, `.kittify/charter/generated/` (interview answers), `.kittify/doctrine/` (after synthesize promote). |
| Post-mission-create state | filesystem | `kitty-specs/<mission-slug>/` containing `spec.md`, `meta.json`, `tasks/README.md`. |
| Post-finalize state | filesystem | `kitty-specs/<mission-slug>/{plan.md,tasks.md,tasks/WP01-*.md}` plus committed git history. |
| Post-`next`-issue state | filesystem | `.kittify/events/profile-invocations/<id>.jsonl` lifecycle record (pre/started). |
| Post-`next`-advance state | filesystem | Lifecycle record gains a paired post/done line; mission state machine advances one step. |

### E-002 — Source checkout (under pollution guard)

| Attribute | Type | Notes |
|---|---|---|
| `path` | `pathlib.Path` | `Path(__file__).resolve().parents[2]` — same convention as existing `tests/e2e/conftest.py:21`. |
| Pre-test snapshot | `str` | `git status --short` output. |
| Pre-test path inventory | `dict[Path, set[Path]]` | Recursive listing of `kitty-specs/`, `.kittify/`, `.worktrees/`, `docs/`, plus any `**/profile-invocations/` paths. |
| Post-test invariant | n/a | Both snapshot and inventory must match pre-test values byte-for-byte. |

### E-003 — Lifecycle record file

Path: `<temp-project>/.kittify/events/profile-invocations/<invocation_id>.jsonl`

Each file contains JSONL records emitted by the composition dispatch path that `spec-kitty next` triggers. Each issued action produces a paired pair:

- One **started** record (written when `next` issues a step).
- One **completed** record (written when `next --result success` advances).

| Field | Type | Assertion |
|---|---|---|
| `kind` | string | One of `started`, `completed` (or domain-equivalent values; verified at implementation time against the live writer). |
| `action` | string | MUST equal the `step_id` returned by the immediately-preceding `next --json` invocation. MUST NOT be a role-default verb (`analyze`, `audit`) unless the mission step is literally `audit`. |
| `invocation_id` | string | Pre/post records share this id. |

The test reads the JSONL files with stdlib `json.loads` line-by-line; it does NOT call `ProfileInvocationExecutor` or any private writer.

### E-004 — Mission handle

`<slug>` returned by `spec-kitty agent mission create … --json` (the `mission_slug` field). The same handle is passed to all subsequent `--mission` flags.

## JSON envelope expectations

The test asserts each `--json` output below is parseable and contains the listed fields. Field names are pulled from live `--help` and from the source-tree command implementations consulted during research; the implementer SHALL widen the assertion if the live envelope contains additional public fields, and SHALL narrow it (and record a finding under FR-021) if any field name proves wrong.

| Command | Required parseable shape | Required fields (assert presence; tolerate additional fields) |
|---|---|---|
| `spec-kitty init . --ai codex --non-interactive` | exit 0, may emit Rich text or JSON depending on path | exit code 0; presence of `.kittify/` directory after run |
| `spec-kitty charter interview --profile minimal --defaults --json` | JSON object | `result`-style success indicator OR document the actual shape at impl time |
| `spec-kitty charter generate --from-interview --json` | JSON object | success indicator; `.kittify/charter/charter.md` exists post-call |
| `spec-kitty charter bundle validate --json` | JSON object | success / compliance indicator |
| `spec-kitty charter synthesize --adapter fixture --dry-run --json` | JSON object | "planned work" indicator; **`.kittify/doctrine/` MUST NOT be created/modified** |
| `spec-kitty charter synthesize --adapter fixture --json` | JSON object | success indicator; `.kittify/doctrine/` exists post-call with manifest/provenance |
| `spec-kitty charter status --json` | JSON object | non-error state field |
| `spec-kitty charter lint --json` | JSON object | findings array OR success indicator; warnings allowed, errors not silently downgraded |
| `spec-kitty agent mission create … --json` | JSON object with `result == "success"` | `mission_slug`, `mission_id`, `feature_dir`, `current_branch`, `target_branch` |
| `spec-kitty agent mission setup-plan --mission … --json` | JSON object with `result == "success"` | `plan_file`, `feature_dir` |
| `spec-kitty agent mission finalize-tasks --mission … --json` | JSON object with `result == "success"` | (no specific fields required beyond success) |
| `spec-kitty next --agent test-agent --mission … --json` (query) | JSON object | `step_id` or equivalent action identifier; prompt-file path (FR-014) when public field exists |
| `spec-kitty next --agent test-agent --mission … --result success --json` | JSON object | advancement decision OR documented structured "blocked / missing guard" envelope (FR-015) |
| `spec-kitty retrospect summary --project <temp-project> --json` | JSON object | parseable; specific fields TBD at impl time |

## State transitions (mission state machine — read-only assertions)

The test does not implement state transitions; it observes them. Allowed observed transitions for this tranche:

```
[no mission] → mission_slug present (after agent mission create)
no plan → plan_file present (after setup-plan)
no tasks finalized → WP01 frontmatter has dependencies (after finalize-tasks)
no issued step → issued_step_id present (after next --json query)
issued_step → next composed step OR documented blocked envelope (after next --result success)
```

Any transition outside this set produced by a single advance is unexpected and constitutes a test failure.

## Invariants

- **I-001** (FR-018, R-005 layer 2): For every `Path` p in the source-checkout pre-test inventory, the post-test inventory contains the same `Path` p with identical mtime/size, and contains no additional paths under the watched roots.
- **I-002** (FR-016): For every issued action, the count of `started` lifecycle records equals the count of `completed` lifecycle records (paired).
- **I-003** (FR-016): For every paired record, `started.action == completed.action == issued_step_id`.
- **I-004** (FR-011): Between `synthesize --dry-run` and `synthesize` (real), `.kittify/doctrine/` exists only after the second call.
