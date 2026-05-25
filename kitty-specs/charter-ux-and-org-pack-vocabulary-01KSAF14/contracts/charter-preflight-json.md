# Contract — `spec-kitty charter preflight` (new)

**Backed by**: FR-006, FR-007, FR-008

## CLI surface

```text
Usage: spec-kitty charter preflight [OPTIONS]

  Verify charter-derived state and (optionally) refresh stale or missing
  synthesized doctrine before a governed session begins.

Options:
  --json                Emit JSON result.
  --auto-refresh        Run safe refresh steps automatically when applicable
                        (default: off; opt-in via config flag or this flag).
  --strict              Exit non-zero on any non-fresh state (default: exit
                        zero unless a hard block occurs).
  --help
```

## JSON output

```json
{
  "passed": true | false,
  "checks": [
    {
      "name": "charter_source",
      "state": "fresh" | "stale" | "missing" | "invalid" | "skipped",
      "detail": "human-readable",
      "remediation": "exact command" | null
    },
    {
      "name": "synced_bundle",
      "state": "...",
      "detail": "...",
      "remediation": null
    },
    {
      "name": "synthesized_drg",
      "state": "fresh" | "stale" | "missing" | "built_in_only" | "invalid" | "skipped",
      "detail": "...",
      "remediation": "spec-kitty charter synthesize" | null
    }
  ],
  "auto_refresh_applied": true | false,
  "auto_refresh_actions": ["spec-kitty charter sync", "spec-kitty charter synthesize"],
  "blocked_reason": "human-readable" | null
}
```

## State semantics

| Field | Description |
|---|---|
| `passed` | `true` iff every check is `fresh`, `skipped`, or `built_in_only`. |
| `auto_refresh_applied` | `true` iff `--auto-refresh` was honoured AND at least one refresh action ran. |
| `auto_refresh_actions` | Ordered list of exact commands executed. |
| `blocked_reason` | Non-null iff `passed=false` AND `auto_refresh_applied=false`. The string MUST include an actionable next command. |

## Safety rule (FR-008)

When the worktree contains uncommitted changes to `.kittify/charter/` or `.kittify/doctrine/`, `--auto-refresh` MUST be a no-op:
- `auto_refresh_applied: false`
- `blocked_reason: "uncommitted generated artifacts; commit or stash and retry"`
- Each affected file is named in `detail` of the corresponding check.

### Detection mechanism (binding)

Uncommitted-artifact detection MUST use a single `git status --porcelain -- .kittify/charter/ .kittify/doctrine/` invocation, parsed line-by-line. Any output line marks the worktree as dirty for the purposes of `--auto-refresh`. The detection MUST NOT use `git diff`, file-mtime heuristics, or string-matching of pathnames — these all produce known false negatives on Windows.

Failure-mode contract:
- `git` not on PATH → `passed=false`, `blocked_reason: "git CLI not available; cannot determine worktree cleanliness"`.
- `git status` returns non-zero → `passed=false`, `blocked_reason` includes the exit code and stderr first line.
- Detection itself MUST complete within 100 ms on a clean tree to stay under NFR-001.

## Hook caller contract (DIR-031)

The session-start hook callable `run_charter_preflight(...)` is consumed by three entry points. Each consumer obeys the following rules:

| Consumer | On `passed=true` | On `passed=false` |
|---|---|---|
| `spec-kitty next` | log a single line at INFO level; continue. | abort with exit code 1; print `result.blocked_reason`; do not perform any state mutation. |
| `spec-kitty implement WP##` | log + continue. | abort with exit code 1 before creating or reusing any worktree; do not modify `.kittify/`. |
| `dashboard serve` / `dashboard start` | log + continue. | start the server but render a top-of-page banner (severity=critical) carrying `result.blocked_reason` and the exact remediation command. Do NOT silently fall back to stale doctrine. |

Each consumer MUST call `run_charter_preflight(auto_refresh=<config>)` where `<config>` reads the project-level `preflight.auto_refresh` flag (default `false`). A consumer MUST NOT pass `auto_refresh=True` unconditionally.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | `passed=true` OR (`passed=false` AND `--strict` not set AND `blocked_reason` non-null) |
| 1 | `passed=false` AND `--strict` set |
| 2 | Hard error (charter file unreadable, etc.) — never produces a JSON payload |

## Hook contract

Internal callable surface for session-start hooks:

```python
from specify_cli.charter_preflight import run_charter_preflight, CharterPreflightResult

result: CharterPreflightResult = run_charter_preflight(
    repo_root=Path("."),
    auto_refresh=False,
    strict=False,
)
```

Callers (`spec-kitty next`, `spec-kitty implement`, `dashboard serve`) check `result.passed` and either log + continue (when `passed=true`) or surface `result.blocked_reason` and abort.
