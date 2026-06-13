# Contract — Dispatch parity (workstream B, NFR-001 / FR-005 / C-002)

## Canonical command

```
spec-kitty dispatch <request> [--profile <id>] [--json]
```

Routes through the single mechanism `ProfileInvocationExecutor.invoke()`. Mode derives from
the entry command via `invocation/modes.py::_ENTRY_COMMAND_MODE` (add `dispatch` →
`task_execution`).

## Retained first-class aliases (NOT deprecated)

| command | argument shape (UNCHANGED) | mode | profile resolution |
|---|---|---|---|
| `spec-kitty do <request> [--profile] [--json]` | optional `--profile` | `task_execution` | router if no profile; fail-closed |
| `spec-kitty advise <request> [--profile/-p] [--json]` | optional `--profile` | `advisory` | hint or router |
| `spec-kitty ask <profile> <request> [--json]` | **mandatory positional** profile | `task_execution` | direct lookup |
| `spec-kitty dispatch <request> [--profile] [--json]` | optional `--profile` | `task_execution` | hint or router |

All four call one shared `_dispatch_impl(request, profile_hint, mode, json_output)`.

## Parity assertions (pinned by tests)

For equivalent inputs, the Op record JSONL at `kitty-ops/<invocation_id>.jsonl` (the path
returned by `invocation/writer.py::invocation_path` — the test must source the path from there,
not hard-code it) MUST be byte/contract-identical across the canonical command and its alias,
field-for-field except the unique `invocation_id` and timestamps:

- same `event` ("started"/"completed") shape and required v2 fields
- same `profile_id`, `action`, `request_text`, `actor`, `governance_context_hash`,
  `governance_context_available`
- **same `mode_of_work`** for equivalent verbs (do/ask/dispatch → `task_execution`;
  advise → `advisory`)
- identical JSON envelope (`--json`): `status`, `close_contract`, glossary observations
- identical exit codes: 0 success; 1 routing/profile/write error; mode-enforcement behavior
  unchanged (advisory/query reject evidence promotion — pre-existing `invocation/` behavior,
  not introduced or altered by this mission)

## Binding constraint (C-002)

The alias entry points land in the **same change** as `dispatch`. There is never a commit
where `spec-kitty do --profile …` (which the governed-ops workflow itself depends on) is
broken. No router/executor/record/modes-semantics change beyond adding the `dispatch` entry.
