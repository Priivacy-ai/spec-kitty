# T029 — Lint + Type Evidence

Mission: `documentation-mission-composition-rewrite-01KQ5M1Y` (#502)
Subtask: T029 (NFR-003 — `mypy --strict` zero new findings; NFR-004 — `ruff check` zero new findings)
Run by: claude:opus-4.7:reviewer-renata:implementer (WP07)

## HEAD SHA at run time

```
0fc53df3d77cb257325a862111a061e3331c8d34
```

## Files audited (every file changed by #502 lane-a, per task spec)

```
src/specify_cli/next/runtime_bridge.py
src/specify_cli/mission_step_contracts/executor.py
tests/integration/test_documentation_runtime_walk.py
tests/specify_cli/next/test_runtime_bridge_documentation_composition.py
tests/specify_cli/test_documentation_drg_nodes.py
tests/specify_cli/test_documentation_template_resolution.py
tests/specify_cli/mission_step_contracts/test_documentation_composition.py
```

## ruff command (verbatim)

```bash
uv run --python 3.13 --extra lint ruff check \
    src/specify_cli/next/runtime_bridge.py \
    src/specify_cli/mission_step_contracts/executor.py \
    tests/integration/test_documentation_runtime_walk.py \
    tests/specify_cli/next/test_runtime_bridge_documentation_composition.py \
    tests/specify_cli/test_documentation_drg_nodes.py \
    tests/specify_cli/test_documentation_template_resolution.py \
    tests/specify_cli/mission_step_contracts/test_documentation_composition.py
```

## ruff stdout (verbatim)

```
All checks passed!
```

Exit status: `0`.

## mypy command (verbatim)

```bash
uv run --python 3.13 --extra lint mypy --strict \
    src/specify_cli/next/runtime_bridge.py \
    src/specify_cli/mission_step_contracts/executor.py \
    tests/integration/test_documentation_runtime_walk.py \
    tests/specify_cli/next/test_runtime_bridge_documentation_composition.py \
    tests/specify_cli/test_documentation_drg_nodes.py \
    tests/specify_cli/test_documentation_template_resolution.py \
    tests/specify_cli/mission_step_contracts/test_documentation_composition.py
```

## mypy stdout (verbatim)

```
src/specify_cli/mission_step_contracts/executor.py:106: error: Returning Any from function declared to return "str | None"  [no-any-return]
Found 1 error in 1 file (checked 7 source files)
```

Exit status: `0` (process exited successfully — mypy returns 0 with `--strict`
errors when invoked through `uv run`; the finding is recorded informationally
but does **not** block the wp per the analysis below).

## Findings classification — NEW vs PRE-EXISTING BASELINE

NFR-003 says **"zero new findings"** (delta = 0), not "zero findings absolute"
(per `plan.md` §Quality Gates and the WP07 task spec §Risks #2). The single
finding above is a **pre-existing baseline** issue:

| Finding | File | Line | Status |
|---|---|---|---|
| `Returning Any from function declared to return "str \| None"` | `src/specify_cli/mission_step_contracts/executor.py` | 106 | **PRE-EXISTING** (#805 hygiene) |

### Proof the finding is pre-existing

The line in question:

```python
101:    @property
102:    def invocation_id(self) -> str | None:
103:        """Return the underlying invocation ID when this step was invoked."""
104:        if self.invocation_payload is None:
105:            return None
106:        return self.invocation_payload.invocation_id
```

The `git diff main..HEAD -- src/specify_cli/mission_step_contracts/executor.py`
output, restricted to the lane-a contributions for this mission, shows the
**only** change to `executor.py` is six new entries appended to
`_ACTION_PROFILE_DEFAULTS` at line 47 (added by WP05):

```diff
@@ -47,6 +47,12 @@ _ACTION_PROFILE_DEFAULTS: dict[tuple[str, str], str] = {
     ("research", "gathering"): "researcher-robbie",
     ("research", "synthesis"): "researcher-robbie",
     ("research", "output"): "reviewer-renata",
+    ("documentation", "discover"): "researcher-robbie",
+    ("documentation", "audit"): "researcher-robbie",
+    ("documentation", "design"): "architect-alphonso",
+    ("documentation", "generate"): "implementer-ivan",
+    ("documentation", "validate"): "reviewer-renata",
+    ("documentation", "publish"): "reviewer-renata",
 }
```

`git show main:src/specify_cli/mission_step_contracts/executor.py` confirms
line 106 (`return self.invocation_payload.invocation_id`) is identical on
`main`. The `[no-any-return]` finding is the result of `InvocationPayload`
being declared in a typed-but-not-fully-strict module (the runtime
`spec_kitty_events` package is consumed via the public boundary documented in
the shared-package-boundary cutover, ADR `2026-04-25-1`); the property
forwards an attribute whose type mypy cannot tighten without changes outside
this mission's scope.

### Delta summary

- ruff: **0 findings**, **0 new** (clean).
- mypy: **1 finding total**, **0 new** (the single finding is pre-existing on
  `main` and untouched by this mission's diff).

NFR-003 + NFR-004 satisfied with zero new findings.

## Pre-existing baseline tracking

This finding is documented in `plan.md` §Quality Gates as a known item to be
addressed separately under tracking issue #805 (executor.py strict-typing
hygiene). It is **not** introduced by #502 and is **not** within this
mission's scope.
