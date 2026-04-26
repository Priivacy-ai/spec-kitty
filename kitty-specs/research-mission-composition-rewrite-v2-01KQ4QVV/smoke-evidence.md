# Dogfood Smoke Evidence — research-mission-composition-rewrite-v2

**Captured**: 2026-04-26T13:21:35Z
**Operator**: claude:opus-4.7:test:operator (acting as implementer-ivan running WP06)
**Spec-kitty HEAD**: `697f8b59 feat(WP05): research composition dispatch + 5 guards + fail-closed default` (lane-a worktree)

## Step 1: Clean checkout setup

```
$ cd /tmp && rm -rf demo-research-smoke && mkdir demo-research-smoke && cd demo-research-smoke
$ git init -q && git commit --allow-empty -m "init" -q
$ pwd
/tmp/demo-research-smoke
$ git log --oneline -3
678b978 init
```

```
$ SPEC_KITTY_REPO=/Users/robert/spec-kitty-dev/spec-kitty-20260426-090759-jdStAC/spec-kitty/.worktrees/research-mission-composition-rewrite-v2-01KQ4QVV-lane-a
```

## Step 2: spec-kitty init

```
$ uv --project $SPEC_KITTY_REPO run spec-kitty init --non-interactive --ai claude
... (truncated; final lines below)
  • .kittify/events/
  • .kittify/merge-state.json
  • .kittify/missions/__pycache__/
  • .kittify/runtime/
  • .kittify/workspaces/
Updated .gitattributes to semantically merge status.events.jsonl
Created .claudeignore to optimize AI assistant scanning
Saved agent configuration
```

## Step 3: Create research mission

```
$ uv --project $SPEC_KITTY_REPO run spec-kitty agent mission create demo-smoke \
      --mission-type research --json
```

Stdout (key fields extracted from the full JSON envelope; full envelope contains
`branch_context`, `runtime_vars`, etc.):

```json
{
  "result": "success",
  "mission_slug": "demo-smoke-01KQ4Z73",
  "mission_id": "01KQ4Z738YZ9EBDHT7CZCEV9XH",
  "mission_type": "research",
  "feature_dir": "/private/tmp/demo-research-smoke/kitty-specs/demo-smoke-01KQ4Z73"
}
```

No `MissionRuntimeError`. No Python traceback. The v1 P0 finding is closed:
the runtime template chain resolves the research mission and writes the
mission directory cleanly.

## Step 4: First `spec-kitty next` (query mode)

```
$ uv --project $SPEC_KITTY_REPO run spec-kitty next \
      --agent claude:opus-4.7:test:operator --mission demo-smoke-01KQ4Z73

[QUERY — no result provided, state not advanced]
  Mission: demo-smoke-01KQ4Z73 @ not_started
  Mission Type: research
  Next step: scoping
```

`Mission Type: research` and `Next step: scoping` together confirm the
runtime resolved the research-mission template (no fallthrough to a default
software-dev template).

## Step 5: Advance scoping via composition

```
$ uv --project $SPEC_KITTY_REPO run spec-kitty next \
      --agent claude:opus-4.7:test:operator --mission demo-smoke-01KQ4Z73 \
      --result success

[STEP] demo-smoke-01KQ4Z73 @ scoping
  Mission Type: research
  Action: scoping
  Run ID: a6532a306ddd44f4826d4c88142d3cf1
```

(First `--result success` issues scoping.) Re-run to drive the composition
dispatch on the just-issued scoping step:

```
$ uv --project $SPEC_KITTY_REPO run spec-kitty next \
      --agent claude:opus-4.7:test:operator --mission demo-smoke-01KQ4Z73 \
      --result success

[STEP] demo-smoke-01KQ4Z73 @ methodology
  Mission Type: research
  Action: methodology
  Run ID: a6532a306ddd44f4826d4c88142d3cf1
```

`methodology` is the research-native step that follows `scoping` in
`mission-runtime.yaml`. The transition `scoping → methodology` (with no
software-dev verbs leaking through) proves the composition path fired and
the planner advanced through the research DAG.

## Step 6: Trail records

```
$ ls -la .kittify/events/profile-invocations/
total 48
drwxr-xr-x  8 robert  wheel  256 Apr 26 15:21 .
drwxr-xr-x  5 robert  wheel  160 Apr 26 15:21 ..
-rw-r--r--  1 robert  wheel  980 Apr 26 15:21 01KQ4Z7PK9NAQP3CGYHN66GH9P.jsonl
-rw-r--r--  1 robert  wheel  984 Apr 26 15:21 01KQ4Z7PZJY9YMG51Z8XA3VHXB.jsonl
-rw-r--r--  1 robert  wheel  934 Apr 26 15:21 01KQ4Z7QA64HV0XQWJCMZESKW3.jsonl
-rw-r--r--  1 robert  wheel  903 Apr 26 15:21 01KQ4Z7QMMTREQDFJQQGGTFEJY.jsonl
-rw-r--r--  1 robert  wheel  968 Apr 26 15:21 01KQ4Z7QZBN7TGX5BM47GW2BQT.jsonl
-rw-r--r--  1 robert  wheel  930 Apr 26 15:21 01KQ4Z7R9VK1SG3VFR8R04PR54.jsonl
```

Sample paired-record content (one of the six files):

```json
{
  "event": "started",
  "invocation_id": "01KQ4Z7PK9NAQP3CGYHN66GH9P",
  "profile_id": "researcher-robbie",
  "action": "scoping",
  "request_text": "Execute mission step contract research-scoping (research/scoping).\nStep bootstrap: Load charter context for this action\nDeclared command: spec-kitty charter context --action scoping --role scoping --json\nCommand status: declared only; the host/operator owns execution.",
  "governance_context_hash": "a971aa9db1e35bcc",
  "governance_context_available": true,
  "actor": "claude:opus-4.7:test:operator",
  "started_at": "2026-04-26T13:21:35.218340+00:00"
}
{
  "event": "completed",
  "invocation_id": "01KQ4Z7PK9NAQP3CGYHN66GH9P",
  "profile_id": "researcher-robbie",
  "action": "",
  "request_text": "",
  "governance_context_hash": "",
  "governance_context_available": true,
  "actor": "unknown",
  "router_confidence": null,
  "started_at": "",
  "completed_at": "2026-04-26T13:21:35.218802+00:00",
  "outcome": "done",
  "evidence_ref": null,
  "mode_of_work": null
}
```

Key facts in the started record:

- `profile_id` is `researcher-robbie` — the research-native profile (NOT
  the software-dev `architect-alphonso` / `implementer-ivan` defaults).
- `action` is `scoping` — the research-native step ID, threaded
  unchanged through `StepContractExecutor` → `ProfileInvocationExecutor`.
- The completed event is paired with the started event by
  `invocation_id` and carries `outcome: "done"`.

## Verdict

**PASS** — fresh research mission created and advanced via composition.
v1 P0 finding (`MissionRuntimeError: Mission 'research' not found`) is
closed. Composition dispatch fires, the planner advances through the
research DAG (`scoping → methodology`), and paired invocation records are
written under `.kittify/events/profile-invocations/` with the
research-native action and profile.
