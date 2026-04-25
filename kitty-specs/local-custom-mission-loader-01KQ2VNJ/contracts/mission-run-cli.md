# Contract: `spec-kitty mission run` CLI

## Command shape

```text
spec-kitty mission run <mission-key> --mission <mission-slug> [--json]
```

| Argument / option | Type | Required | Notes |
| --- | --- | --- | --- |
| `<mission-key>` | positional, str | yes | The reusable identifier for a custom mission *definition*. Resolved through internal-runtime discovery precedence. |
| `--mission <mission-slug>` | option, str | yes | The identifier of the *tracked* mission run under `kitty-specs/<mission-slug>/`. The resolver disambiguates by `mission_id` and returns a structured `MISSION_AMBIGUOUS_SELECTOR` error on ambiguity. |
| `--json / --no-json` | option, bool | no, default `false` | Emit machine-readable envelope on stdout. Without `--json`, a `rich.panel.Panel` is rendered. |

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success — runtime started or already running for the requested mission. |
| 1 | Infrastructure failure — filesystem error, repository corruption, etc. Not the operator's fault. |
| 2 | Validation error — the custom mission definition or selector is unfit. Operator-fixable. |

## Stdout envelopes

### Success envelope (`--json`)

```json
{
  "result": "success",
  "mission_key": "erp-integration",
  "mission_slug": "erp-q3-rollout-01KQ…",
  "mission_id": "01KQ…",
  "feature_dir": "/abs/path/kitty-specs/erp-q3-rollout-01KQ…",
  "run_dir": "/abs/path/.kittify/runtime/runs/<run-id>",
  "warnings": []
}
```

`warnings` is a list of `{code, message, details}` objects. Possible warning codes are documented in [validation-errors.md](./validation-errors.md).

### Error envelope (`--json`)

```json
{
  "result": "error",
  "error_code": "MISSION_RETROSPECTIVE_MISSING",
  "message": "Custom mission 'erp-integration' has no retrospective marker step.",
  "details": {
    "file": "/abs/path/.kittify/missions/erp-integration/mission.yaml",
    "mission_key": "erp-integration",
    "expected": "steps[-1].id == 'retrospective'",
    "actual": "write-report"
  },
  "warnings": []
}
```

### Human envelope (no `--json`)

A `rich.panel.Panel` is rendered with the same fields. The panel's title is the error code (or "Mission Run Started" on success). The body is the message followed by indented `details` (in success: `feature_dir`, `run_dir`).

## Discoverability

`spec-kitty mission --help` lists `run` alongside the existing subcommands (`list`, `current`, `info`, `create`). `spec-kitty mission run --help` shows the args + options table above plus a one-paragraph description: *Start (or attach to) a runtime for a project-authored custom mission definition.*

## Error code stability

The full closed enum is documented in [validation-errors.md](./validation-errors.md). New codes MAY be added in future tranches; existing codes MUST NOT change wire spelling.

## Locked invariants

- The CLI never invokes a model (charter / C-006). It only routes; the runtime composition path drives the host harness.
- Validation errors do NOT start a run. The `kitty-specs/<slug>/` directory is not created on validation failure.
- Success envelope's `feature_dir` is the absolute path; downstream tooling can `cd` to it without recomputation.
