# Contract — Specify/Plan Auto-Commit Boundary (post-#846)

Maps to FR-012, FR-013, FR-014, FR-015 and INV-846-{1,2,3} in `data-model.md`.

## Boundary

The `/spec-kitty.specify` and `/spec-kitty.plan` workflows auto-commit `spec.md` / `plan.md` to the target branch **only when** the file passes a `_is_substantive(file_path, kind)` check. When the check fails:

1. The workflow does **not** auto-commit.
2. The workflow emits a documented "needs substantive content" status (in JSON output and in human-facing text).
3. Workflow status JSON does **not** indicate the spec/plan phase as ready.

## `_is_substantive(file_path, kind)` definition

```
def _is_substantive(file_path: Path, kind: Literal["spec", "plan"]) -> bool:
    body = file_path.read_bytes()
    scaffold = canonical_scaffold(kind)  # cached, computed once at module load
    if len(body) - len(scaffold) > SUBSTANTIVE_DELTA:  # default 256 bytes
        return True
    return required_sections_present(body, kind)
```

Required sections per kind:

| kind | Required sections (any one missing → False) |
|---|---|
| `spec` | A non-empty Functional Requirements table (≥1 row that has a real ID like `FR-001`). |
| `plan` | A non-empty Technical Context section (presence of populated `Language/Version`, `Primary Dependencies`, etc., not just template placeholders). |

## Producer obligations (`src/specify_cli/cli/commands/agent/mission.py`)

- The auto-commit branch in `setup-plan` (and the analogous specify path) wraps its commit in:
  ```python
  if _is_substantive(file_path, kind):
      _safe_commit(...)
      status_payload["phase_complete"] = True
  else:
      status_payload["phase_complete"] = False
      status_payload["blocked_reason"] = "spec/plan content is not substantive yet; agent must populate before phase can advance"
      # do NOT commit
  ```
- The status JSON returned to the caller reflects `phase_complete` accurately.

## Consumer obligations (workflow status reporters, `mission setup-plan --json`, dashboard)

- Treat `phase_complete=False` with `blocked_reason` containing the substantive-content phrase as **incomplete**, never as "ready".
- Do not silently retry or auto-advance.

## Regression test contract (`tests/integration/test_specify_plan_commit_boundary.py`)

```
GIVEN a fresh mission whose spec.md is exactly the empty scaffold from `mission create`
WHEN `setup-plan` (or the specify auto-commit path) runs
THEN no commit is created
  AND the JSON output reports phase_complete=False with a substantive-content blocked_reason
  AND status of the spec/plan phase is "incomplete" or equivalent
```

```
GIVEN a fresh mission whose spec.md has been populated with real FRs (≥1 row in the FR table)
WHEN `setup-plan` (or the specify auto-commit path) runs
THEN a commit IS created
  AND the JSON output reports phase_complete=True
```

```
GIVEN a fresh mission whose spec.md is the empty scaffold + 300 bytes of arbitrary prose
WHEN auto-commit runs
THEN it COMMITS (byte-length branch of _is_substantive triggers, even without FR table)
```

## Template documentation (`src/specify_cli/missions/<mission-type>/command-templates/{specify,plan}.md`)

Each template file gets a short "Commit Boundary" subsection explaining:

- Why the workflow may refuse to auto-commit your scaffold.
- What "substantive content" means operationally.
- How to advance the workflow once content is real.

## What this contract does NOT change

- The mission create / scaffold step itself (it still produces an empty/template `spec.md`).
- The location of `spec.md` / `plan.md`.
- The set of required sections beyond the explicit pair listed above.
- Any other auto-commit behavior in the codebase.
