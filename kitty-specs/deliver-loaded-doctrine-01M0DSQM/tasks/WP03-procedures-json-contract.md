---
work_package_id: WP03
title: procedures[] typed array in context --json (#3389) — versioned-contract bump
dependencies: []
requirement_refs:
- FR-008
- FR-009
- FR-010
- FR-011
planning_base_branch: m4-doctrine-delivery
merge_target_branch: m4-doctrine-delivery
branch_strategy: Planning artifacts for this mission were generated on m4-doctrine-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into m4-doctrine-delivery unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-deliver-loaded-doctrine-01M0DSQM
base_commit: 7fdec0995d96d8974343f64331a13be6b7d3647b
created_at: '2026-08-19T20:29:33.115521+00:00'
subtasks:
- T013
- T014
- T015
- T016
history:
- Created by /spec-kitty.tasks (M4 charter-resolution program)
agent_profile: python-pedro
authoritative_surface: src/charter/context_contract.py
create_intent:
- tests/charter/test_procedures_json_array.py
execution_mode: code_change
owned_files:
- src/charter/progressive_disclosure.py
- src/charter/context.py
- src/charter/context_contract.py
- tests/charter/test_context_parity.py
- tests/charter/test_procedures_json_array.py
role: implementer
tags: []
tracker_refs:
- '3389'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so your boundaries, directives, and tactics are active:

```
/ad-hoc-profile-load python-pedro
```

Then run `spec-kitty charter context --action implement --json` and apply the resolved initialization. State which directives/tactics you applied before writing code.

## Objectives & Success Criteria

Promote `procedure` to the fifth typed array in the `charter context --json` payload, keep `asset` reference-only (stated in the contract), and bump the versioned contract atomically — closing #3389.

- **SC (FR-008)**: `charter context --action <a> --json` carries a top-level typed `procedures[]` array whenever procedures are delivered, decorated like the other typed arrays (`references[]` + `delivery` cadence marker).
- **SC (FR-009)**: `asset` remains reference-only (no `assets[]` typed array); the asymmetry is stated deliberately in `context_contract.py` (no resolution/install path — #3037).
- **SC (FR-010/C-005)**: `CONTEXT_SCHEMA_VERSION` bumps `1.0.0` → `1.1.0` and `"procedures"` is added to `CONTEXT_CONTRACT_TOP_LEVEL_KEYS` in the **same** change as the array promotion.
- **SC (FR-011)**: org-authored procedures (M2 bridge landed) surface in `procedures[]` via the same path as built-in.

## Context & Constraints

Read `kitty-specs/deliver-loaded-doctrine-01M0DSQM/{spec.md,plan.md,research.md,data-model.md}` and `contracts/context-json-contract.md`.

Current state (verified against `upstream/main`):
- `charter/progressive_disclosure.py::_ARRAY_BY_KIND` (L~317) maps 4 kinds: `directive`/`tactic`/`styleguide`/`toolguide` → their array names. `build_disclosure_payload` iterates `repos_by_kind` into `out[_ARRAY_BY_KIND[kind]]`, then folds `extra_delivered` (procedure/asset) into the flat `references[]` only.
- `charter/context.py` (~L487–500): builds `repos_by_kind={directive, tactic, styleguide, toolguide}` and passes `extra_delivered={"procedure": bundle.procedure_ids, "asset": bundle.asset_ids}`.
- `charter/context_contract.py`: `CONTEXT_SCHEMA_VERSION = "1.0.0"`; `CONTEXT_CONTRACT_TOP_LEVEL_KEYS` frozenset lists the top-level keys (directives/tactics/styleguides/toolguides/references/…) — **no** `procedures`. Its docstring states the maintenance rule: bump the version whenever the key set changes.
- Guard `tests/charter/test_context_parity.py::TestJsonEntryPointParity` asserts the array-valued governance keys on a bootstrap payload.

**Constraints**: versioned-contract change is deliberate and atomic (C-005). `asset` stays reference-only (D-003). Do not reshape any other top-level key (C-C4). Zero `ruff`/`mypy --strict` suppressions (C-002). Red-first (C-003). `charter` must not import `specify_cli` (C-001).

## Branch Strategy

Planning base **`m4-doctrine-delivery`**; final merge target **`m4-doctrine-delivery`** (single_branch topology). Execution worktrees are allocated per computed lane from `lanes.json`; do not hand-create branches. One PR to `main` lands the whole mission later.

## Subtasks & Detailed Guidance

### Subtask T013 – Red: procedures[] typed array + versioned bump
Write `tests/charter/test_procedures_json_array.py`: build the `--json` payload for an action that delivers at least one procedure (reuse the parity-test harness / a bootstrap action); assert (a) a top-level `procedures` key exists and is a typed array whose entries carry the same decoration as `directives` entries (`references`/`delivery` fields), (b) `context_schema_version == "1.1.0"`, (c) `"procedures"` ∈ `CONTEXT_CONTRACT_TOP_LEVEL_KEYS`, (d) there is **no** top-level `assets` array. This must **fail** on `upstream/main` (no `procedures[]`, version 1.0.0). Prove red first.

### Subtask T014 – Add procedure to the typed-array map
In `progressive_disclosure.py`: add `"procedure": "procedures"` to `_ARRAY_BY_KIND`. (Do NOT add `"asset"` — asset stays reference-only.)

### Subtask T015 – Move procedure into repos_by_kind
In `context.py` (~L487): move `procedure` from `extra_delivered` into `repos_by_kind` — add `"procedure": (service.procedures, bundle.procedure_ids)` and leave `extra_delivered={"asset": bundle.asset_ids}`. This makes `build_disclosure_payload` emit a typed `procedures[]` array while `asset` remains folded into `references[]` only. Confirm `procedure` still appears in the `references[]` link set (it now comes from `repos_by_kind`'s `delivered` map, so the reference completeness is preserved).

### Subtask T016 – Bump the versioned contract atomically
In `context_contract.py`: bump `CONTEXT_SCHEMA_VERSION` `"1.0.0"` → `"1.1.0"`; add `"procedures"` to `CONTEXT_CONTRACT_TOP_LEVEL_KEYS`; add a docstring/comment line stating the `asset` asymmetry is deliberate (reference-only, no resolution/install path — #3037) so a reader does not "fix" it later. Update `tests/charter/test_context_parity.py` so its structural guard includes `procedures` (and still excludes `assets`). All in this one change (C-005). Record subtasks: `spec-kitty agent tasks mark-status T013 T014 T015 T016 --status done --mission deliver-loaded-doctrine-01M0DSQM`.

## Test Strategy
Red-first (T013 fails on base). Run targeted:
`PATH=.venv/bin:$PATH SPEC_KITTY_SYNC_DISABLE=1 pytest tests/charter/test_procedures_json_array.py tests/charter/test_context_parity.py -q`.
Smoke: `PATH=.venv/bin:$PATH spec-kitty charter context --action implement --json | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['context_schema_version'], 'procedures' in d, 'assets' in d)"` → `1.1.0 True False`.
Then `mypy --strict src/charter` and `ruff check src/charter`.

## Risks & Mitigations
- **Non-atomic bump** (C-005) → land `_ARRAY_BY_KIND` + `context.py` + version + ledger in one change; the parity guard reddens on any undeclared key so a missed ledger update fails loudly.
- **Accidentally promoting asset** → only `procedure` goes into `repos_by_kind`/`_ARRAY_BY_KIND`; assert no `assets` array in T013.
- **Breaking reference completeness** → verify `procedure` still appears in `references[]` after moving to `repos_by_kind` (T013 covers both surfaces).

## Review Guidance
Verify: `procedures[]` typed array present + decorated; `asset` reference-only with a stated reason; `context_schema_version == 1.1.0`; `procedures` in the ledger; parity guard updated; no other top-level key reshaped; `charter` does not import `specify_cli`; zero new suppressions; `mypy --strict` clean.

## Activity Log
- (implementer appends entries here)
