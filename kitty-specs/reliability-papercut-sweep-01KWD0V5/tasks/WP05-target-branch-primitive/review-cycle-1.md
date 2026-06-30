---
affected_files: []
cycle_number: 1
mission_slug: reliability-papercut-sweep-01KWD0V5
reproduction_command:
reviewed_at: '2026-06-30T21:44:46Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
---

# WP05 Review — Changes Requested (review cycle 1)

## Verdict: FAIL (suite left red) — the implementation is correct, but three pre-existing tests now fail

The core change is well-built and I want to be clear that the *product* code is
right. The blocker is purely that the contract change was not reconciled with
three existing suite tests that pin the **old** silent-fallback behavior. Those
tests are now RED. A WP that changes an observable contract must re-pin the tests
that assert the retired contract (DIR-030 — Test & Typecheck Quality Gate; the
WP's own DoD "ruff + mypy clean"; T023 "verify call-site stability").

## What is correct (no action needed)

- `read_target_branch_from_meta` + `_load_meta_fail_closed` are the single
  authority for the absent-vs-read-failure decision. Confirmed genuinely
  distinguished: field-absent / missing file → `None` (caller applies default);
  corrupt JSON / non-object / I/O error → `MissionMetaReadError` (fail-closed).
- Routes through the WP04-shared `mission_metadata.load_meta(allow_missing=True,
  on_malformed="raise")` family — exactly the coordinated meta loader. Good call
  preferring this over the literally-suggested `load_meta_strict`/`load_meta_or_empty`,
  which don't fit (strict raises on missing; or_empty swallows corruption).
- git_ops `resolve_target_branch` is a true thin adapter: imports the paths
  primitive, removed `import json` and the silent `except (JSONDecodeError,
  OSError): target = fallback`. No duplicated decision across the two core modules.
- Signatures/return types byte-identical; ~18-20 call sites need no edit (mypy
  clean confirms type compatibility; spot-checked prompt_builder, worktree_topology,
  merge/resolve, orchestrator_api/commands, mission_runtime/resolution).
- ruff + mypy clean on both changed source files.
- Red-first proven *behaviorally* (not just ImportError): on pre-fix source,
  `get_feature_target_branch` with corrupt meta returned `'master'` silently;
  post-fix it raises `MissionMetaReadError`.

## Blocker: three existing tests pin the removed silent-fallback contract

All three assert that **corrupt/malformed meta.json silently falls back to the
primary branch** — the exact anti-pattern FR-005/#2139 removes. They now fail:

1. `tests/git_ops/test_git_ops.py::test_resolve_target_branch_invalid_meta_json`
   (line ~389) — asserts `resolution.target == "main"  # Fallback on invalid JSON`.
2. `tests/git_ops/test_git_ops_unit.py::test_resolve_target_branch_invalid_meta_falls_back`
   (line ~168) — asserts `resolution.target == "main"` for `"{ invalid json }"`.
3. `tests/specify_cli/context/test_cli.py::TestGetFeatureTargetBranch::test_falls_back_on_malformed_meta`
   (line ~295) — asserts a non-empty branch string for `"INVALID JSON {{"`.

## Required fix (re-pin, do not delete the test)

For each of the three, preserve the repo/fixture setup and replace the
silent-fallback assertion with the new fail-closed contract — i.e.:

```python
from specify_cli.core.paths import MissionMetaReadError
with pytest.raises(MissionMetaReadError):
    resolve_target_branch("005-test", repo, "main", respect_current=True)
```

Rename them to reflect the new contract (e.g. `..._invalid_meta_fails_closed` /
`..._malformed_meta_raises`). This is the "delete-the-assertion-not-the-test"
remediation (DIR-041): keep the excavated setup, swap the wrong assertion.

**Do NOT touch the field-absent siblings** — e.g.
`tests/git_ops/test_git_ops_unit.py::test_resolve_target_branch_meta_missing_field_falls_back`
and `..._no_meta_falls_back_to_primary` correctly still pass and must keep
asserting the documented default. Their passing is the proof that absent ≠ failed.

These three test files are outside `owned_files`, but they directly assert the
contract this WP changes — re-pinning them is squarely in scope (ownership leeway
for directly-contradicted tests). Note the edit in your move-task reason.

## After fixing

Re-run at minimum:
```
pytest tests/git_ops/test_git_ops.py tests/git_ops/test_git_ops_unit.py \
       tests/specify_cli/context/test_cli.py \
       tests/specify_cli/core/test_target_branch_primitive.py \
       tests/agent/test_orchestrator_merge_target.py -q
```
and confirm green, plus a grep for any other `falls_back`/`invalid_meta`/
`malformed` assertion against these three readers I may not have run.
