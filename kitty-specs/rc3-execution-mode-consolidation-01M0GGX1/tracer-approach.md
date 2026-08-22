---
type: explanation
updated: 2026-08-21
---

# Tracer: approach (M7 ExecutionMode consolidation)

## Shape of the work

Two WPs, linear (WP02 depends on WP01), single-branch topology:

- **WP01 — retire dead enum #2** (`mission_runtime.context.ExecutionMode`).
  Governance-gate: delete class + package/module `__all__` entries + surface-list
  entry + ADR public-API listing (dated Amendments note). Verified dead first
  (no member access; `execution_mode` field is a raw `str`).
- **WP02 — rename live enum #1** (`ownership.models.ExecutionMode` → `WorkProductKind`)
  across all consumers + a red-first re-drift guard + CHANGELOG. WP02 depends on WP01
  so the guard's "no `class ExecutionMode` in src/" turns green purely on the rename.

## Why WP02 depends on WP01

The mission's single user-observable contract is "the footgun is gone." The re-drift
guard asserts *no `class ExecutionMode` under `src/`*. That is only true once BOTH the
dead enum (WP01) and the ownership enum (WP02) are handled. Making WP02 depend on WP01
means WP02's guard goes red→green on its own rename (enum #2 is already gone by then),
giving each WP a clean local red→green rather than a guard that spans two lanes.

## Red-first discipline

- **WP02:** `test_execution_mode_no_redrift.py` written first and shown RED
  (`test_no_class_named_execution_mode_in_src` fails while enum #1 is still named
  `ExecutionMode`), then GREEN after the rename.
- **WP01:** the honest red-first signal was weak — the `_PUBLIC_SURFACE` list it edits is
  a vacuous pin (F2 in tooling-friction), so removing the entry produces no red. WP01 is a
  dead-code deletion; its contract is "import still works + arch gates green + no consumers
  break," verified directly. The mission-level red-first lives in WP02's guard.

## Behavior-preservation strategy

- Member NAMES and VALUES held constant (`CODE_CHANGE="code_change"`,
  `PLANNING_ARTIFACT="planning_artifact"`) → WP frontmatter `execution_mode:` stays
  wire-compatible.
- Field name `execution_mode` and function name `infer_execution_mode` unchanged → only
  the class symbol moved; no signature/behavior change anywhere.
- Green merge-base baseline captured before any edit (668 passed on the targeted
  surfaces) so post-change reds are attributable.

## Verification ladder (per WP)

- WP01: surface test + `import mission_runtime` + ruff + mypy(strict) + 50 arch gates.
- WP02: guard (red→green) + 841 targeted tests + 78 direct-module tests + full arch suite
  + ruff + mypy(strict, no new errors) + whole-repo scan for old-name stragglers (none).
