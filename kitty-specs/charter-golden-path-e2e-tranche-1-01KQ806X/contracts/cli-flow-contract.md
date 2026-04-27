# CLI Flow Contract — Charter Golden-Path E2E (Tranche 1)

This document is the authoritative contract between the test and the public CLI surface. The test is the consumer; `spec-kitty` is the provider. If the live CLI deviates from this contract at implementation time, the deviation is recorded under spec FR-021 in the PR description (not silently absorbed).

## Forbidden surface (C-001, C-002)

The test MUST NOT import, call, or reference any of the following symbols:

- `decide_next_via_runtime`
- `_dispatch_via_composition`
- `StepContractExecutor`
- `run_terminus`
- `apply_proposals`
- `ProfileInvocationExecutor` (the writer; the test reads its output, never calls it)
- Any private member of `specify_cli.next._internal_runtime` or sibling internal-only modules.

The test MUST NOT monkeypatch the dispatcher, executor, DRG resolver, or frozen-template loader.

## Public CLI surface contract (in flow order)

### Step 1 — Project bootstrap

| Subprocess | Args | Env | Expected exit | Expected post-state |
|---|---|---|---|---|
| `git` | `init -b main` | inherit | 0 | `.git/HEAD` present, on `main` |
| `git` | `config user.email e2e@example.com` | inherit | 0 | git config |
| `git` | `config user.name "E2E Test"` | inherit | 0 | git config |
| `spec-kitty` | `init . --ai codex --non-interactive` | isolated (run_cli) | 0 | `.kittify/` exists; `.gitignore` present |
| `git` | `add .` | inherit | 0 | staged |
| `git` | `commit -m "Initial spec-kitty init"` | inherit | 0 | commit on `main` |

### Step 2 — Charter governance

| Subprocess | Args | Expected exit | Expected post-state |
|---|---|---|---|
| `spec-kitty` | `charter interview --profile minimal --defaults --json` | 0 | parseable JSON; interview answers cached under `.kittify/charter/` |
| `spec-kitty` | `charter generate --from-interview --json` | 0 | parseable JSON; `.kittify/charter/charter.md` exists |
| `spec-kitty` | `charter bundle validate --json` | 0 | parseable JSON; success / compliance indicator |
| `spec-kitty` | `charter synthesize --adapter fixture --dry-run --json` | 0 | parseable JSON; `.kittify/doctrine/` does NOT exist (or is unchanged from pre-call snapshot) |
| `spec-kitty` | `charter synthesize --adapter fixture --json` | 0 | parseable JSON; `.kittify/doctrine/` exists with provenance/manifest |
| `spec-kitty` | `charter status --json` | 0 | parseable JSON; non-error state |
| `spec-kitty` | `charter lint --json` | 0 (or documented warning-only non-zero) | parseable JSON; no silent error downgrade |

### Step 3 — Mission scaffolding

| Subprocess | Args | Expected exit | Expected post-state |
|---|---|---|---|
| `spec-kitty` | `agent mission create "<slug>" --mission-type software-dev --friendly-name "<title>" --purpose-tldr "<…>" --purpose-context "<…>" --json` | 0 | JSON `result == "success"`; `kitty-specs/<slug>/spec.md` and `meta.json` present |
| `spec-kitty` | `agent mission setup-plan --mission <slug> --json` | 0 | JSON `result == "success"`; `kitty-specs/<slug>/plan.md` present |
| (test) | inline-write minimal `spec.md`, `tasks.md`, `tasks/WP01-*.md`, meta.json updates per smoke recipe | n/a | files present |
| `git` | `add .` then `commit -m "Seed minimal mission"` | 0 | clean working tree |
| `spec-kitty` | `agent mission finalize-tasks --mission <slug> --json` | 0 | JSON `result == "success"`; `WP01` frontmatter contains `dependencies` field |

### Step 4 — `next` issue and advance

| Subprocess | Args | Expected exit | Expected post-state |
|---|---|---|---|
| `spec-kitty` | `next --agent test-agent --mission <slug> --json` (query mode) | 0 | parseable JSON; `step_id` (or equivalent) present; prompt-file field non-null when exposed |
| `spec-kitty` | `next --agent test-agent --mission <slug> --result success --json` | 0 | parseable JSON; advancement decision OR documented structured "blocked / missing guard" envelope |

After step 4, `<temp-project>/.kittify/events/profile-invocations/` contains at least one JSONL file with paired `started` / `completed` records for the issued action.

### Step 5 — Retrospect

| Subprocess | Args | Expected exit | Expected post-state |
|---|---|---|---|
| `spec-kitty` | `retrospect summary --project <temp-project> --json` | 0 | parseable JSON object; no mutation of temp project state |

### Step 6 — Source-checkout pollution guard

This step has no subprocess; it's a read-only assertion against the source checkout:

```
assert post_status == pre_status                     # FR-017
assert post_inventory == pre_inventory               # FR-018
```

where `inventory` = recursive listing of `REPO_ROOT/{kitty-specs,.kittify,.worktrees,docs}` plus any `**/profile-invocations/` paths.

## Non-contract behaviours (the test must NOT depend on these)

- The exact text of charter `lint` warnings.
- The order of fields in any `--json` envelope.
- The on-disk format of `.kittify/charter/generated/` artifacts (the fixture adapter owns this; the test only asserts post-promote `.kittify/doctrine/` presence).
- The specific composed action issued by `next` for a freshly-finalized `software-dev` mission. The test asserts the action is structurally valid (step_id present, prompt-file present, paired lifecycle records emitted with matching action name) but does NOT hard-code which step is first.

## Failure-diagnostics contract (FR-019, NFR-004)

On any subprocess returning a non-expected exit code, the assertion message MUST include at minimum:

```
command: spec-kitty <args>
cwd:     <path>
rc:      <int>
stdout:  <captured>
stderr:  <captured>
```

A compact non-recursive directory listing of the temp project MAY be appended.

## Bulk-edit contract

Not applicable. This mission is `change_mode: normal` (no `change_mode` key set in `meta.json` ⇒ default normal). No `occurrence_map.yaml` is required.
