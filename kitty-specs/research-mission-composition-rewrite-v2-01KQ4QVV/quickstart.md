# Research Mission Quickstart — Operator Dogfood

This is the operator-runnable sequence that proves a fresh research mission
can be created and advanced through the composition path with no
`MissionRuntimeError`. WP06's `smoke-evidence.md` captures one canonical run
of this sequence verbatim. Reviewers should re-run it from a clean shell.

## Prerequisites

- A checkout of spec-kitty at HEAD (the worktree containing your changes).
- `uv` installed and on `$PATH`.

Set the path to your checkout once for the rest of the session:

```bash
SPEC_KITTY_REPO=/path/to/spec-kitty   # or the lane worktree
```

## Step 1 — Create an isolated sandbox

```bash
cd /tmp && rm -rf demo-research-smoke && mkdir demo-research-smoke && cd demo-research-smoke
git init -q && git commit --allow-empty -m "init" -q
```

Expected: a fresh empty git repo, no `.kittify/` yet.

## Step 2 — Initialize spec-kitty

```bash
uv --project $SPEC_KITTY_REPO run spec-kitty init --non-interactive --ai claude
```

Expected: `.kittify/` populated; agent dirs (e.g. `.claude/`) seeded; no error.

## Step 3 — Create a research mission

```bash
uv --project $SPEC_KITTY_REPO run spec-kitty agent mission create demo-smoke \
    --mission-type research --json
```

Expected JSON keys (verbatim sample in `smoke-evidence.md`):

- `result`: `"success"`
- `mission_type`: `"research"`
- `mission_slug`: `demo-smoke-<MID8>` (e.g. `demo-smoke-01KQ4Z73`)
- `mission_id`: a 26-char ULID
- `feature_dir`: `<repo>/kitty-specs/<mission_slug>`

No `MissionRuntimeError`, no Python traceback. The v1 P0 finding
(`MissionRuntimeError: Mission 'research' not found`) is closed as soon as
this command returns successfully.

## Step 4 — First `next` (query)

```bash
uv --project $SPEC_KITTY_REPO run spec-kitty next \
    --agent claude:opus-4.7:test:operator --mission <mission_slug>
```

Expected:

```
[QUERY — no result provided, state not advanced]
  Mission: <mission_slug> @ not_started
  Mission Type: research
  Next step: scoping
```

`Mission Type: research` and `Next step: scoping` confirm the runtime
template chain resolved the research template.

## Step 5 — Advance scoping (composition path)

```bash
uv --project $SPEC_KITTY_REPO run spec-kitty next \
    --agent claude:opus-4.7:test:operator --mission <mission_slug> \
    --result success
```

The first call issues `scoping`. Run it again with `--result success`; the
second call drives composition for the scoping step and the response shows:

```
[STEP] <mission_slug> @ methodology
  Mission Type: research
  Action: methodology
```

`methodology` is the next research-native step, proving composition fired
and the planner advanced through the research DAG (not the software-dev
DAG).

## Step 6 — Inspect the invocation trail

```bash
ls -la .kittify/events/profile-invocations/
```

Expected: one `<ulid>.jsonl` file per composed contract step. Each file
contains a paired `started` + `completed` record. The `started` record's
`action` field is `scoping` (the research-native step ID) and
`profile_id` is `researcher-robbie`.

```bash
cat .kittify/events/profile-invocations/<one>.jsonl
```

## Pass criteria

| Criterion | Where it shows up |
|---|---|
| No `MissionRuntimeError` for `'research'` | Step 3 + Step 4 succeed |
| Research template resolves | Step 4 prints `Mission Type: research` |
| Composition path fires for scoping | Step 5 second call returns `methodology` |
| Paired invocation records written | Step 6 trail files have `started` + `completed` |
| Action hint preserved on the trail | Step 6 trail file shows `"action": "scoping"` |

If any of these regress, the v1 P0 finding is open again.
