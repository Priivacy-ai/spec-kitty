---
work_package_id: WP04
title: merge_driver routing
dependencies:
- WP01
requirement_refs:
- C-010
- FR-003
- FR-005
- FR-007
planning_base_branch: feat/meta-json-l1-seam-routing-3259
merge_target_branch: feat/meta-json-l1-seam-routing-3259
branch_strategy: Planning artifacts for this mission were generated on feat/meta-json-l1-seam-routing-3259. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-json-l1-seam-routing-3259 unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
history:
- at: '2026-08-10'
  note: Authored by /spec-kitty.tasks (post-plan-squad model).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/merge_driver.py
create_intent:
- tests/merge/test_merge_driver_meta_diagnosability.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/merge_driver.py
- tests/merge/test_merge_driver_wrappers_2709.py
- tests/merge/test_merge_driver_meta_diagnosability.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Apply it, then read this WP, `spec.md` (FR-003/005/007, C-010), and `data-model.md` (site E row + error-translation). WP01 must be merged first (you consume `parse_meta_file`).

## Objective

Route site E — `merge_driver._load_json_object` (~:174) — through the public L2 `parse_meta_file` with an exception-translating wrapper, so a corrupt merge-blob `meta.json` fails loud while the module's existing benign and domain-error contracts are preserved. **Census-neutral** (routes onto `parse_meta_file`, uncounted until WP05).

> ⚠️ **Do NOT route onto `load_meta_or_empty`.** It is already a `ROUTED_CALLEES` member and the tempting empty→`{}` choice; routing E onto it bumps the census mid-WP and reds the gate. Route onto the still-uncounted `parse_meta_file`.
>
> ⚠️ **`_parse_json_document` (~:337) is OUT OF SCOPE.** It decodes the issue/row-matrix document (raises `RowMatrixMergeError`), not `meta.json`. Do not touch it. WP05's FR-010 gate excludes it.

### Subtask T019 — Route site E onto public L2 with a translating wrapper

Rewrite `_load_json_object` (~:174) to stay a thin wrapper:
1. Preserve the **empty/whitespace → `{}`** short-circuit before decoding (C-010).
2. Decode via `parse_meta_file(path, on_malformed="raise")`.
3. **Catch `MetaDecodeError` → re-raise `EventLogMergeError(path)`** so the two error arms preserve their contract: the non-object arm (currently `EventLogMergeError`, `test_merge_driver_wrappers_2709.py:112-116`) and the malformed arm (currently a bare unnamed `JSONDecodeError`) both surface as `EventLogMergeError` naming the path (now fail-loud + named).

### Subtask T020 — Red-first E diagnosability

Create `tests/merge/test_merge_driver_meta_diagnosability.py` (declare `pytestmark`; site E is a plain on-disk `Path` — **NO `git_repo`**). Assert:
- corrupt `meta.json` blob → `pytest.raises(EventLogMergeError)` whose message names the path (was a silent/unnamed error);
- non-object → `EventLogMergeError` (preserved);
- empty/whitespace → `{}` (benign, preserved, C-010);
- valid → parsed mapping unchanged (FR-005).

**Capture proof-of-red**: the corrupt-malformed arm test is red against the pre-routing code (bare `JSONDecodeError`, not the named `EventLogMergeError`) — save that output.

### Subtask T021 — Confirm contracts + census-neutral

- `test_merge_driver_wrappers_2709.py` stays green (update only if the non-object message text changed — keep `match="not a JSON object"` satisfiable).
- `_parse_json_document:337` untouched (grep-confirm the row-matrix path is unchanged).
- Census unchanged; do NOT edit `ROUTED_CALLEES`/floor.
- Run: `PWHEADLESS=1 python -m pytest tests/merge/test_merge_driver_meta_diagnosability.py tests/merge/test_merge_driver_wrappers_2709.py tests/architectural/test_inline_meta_read_gate.py -q` → green.

## Branch Strategy

Base + merge target: `feat/meta-json-l1-seam-routing-3259`. Worktree per computed lane. Depends on WP01.

## Definition of Done

- Site E routes onto `parse_meta_file` via a wrapper catching `MetaDecodeError`→`EventLogMergeError(path)`; empty→`{}` preserved.
- **Git-verifiable red-first**: commit the E diagnosability test in a commit PRECEDING the routing commit (proof-of-red is a git artifact). Run with `-rs`, confirm the corrupt-arm test `passed`, **0 skips** (E is on-disk unit — no fixture-skip excuse). `test_merge_driver_wrappers_2709.py` green; `_parse_json_document:337` untouched.
- **Census-neutral, proven**: grep that E routes onto `parse_meta_file` and NOT `load_meta_or_empty` (or any `ROUTED_CALLEES` member); reviewer re-runs the census one-liner and confirms unchanged. No `ROUTED_CALLEES`/floor change.
- `ruff` + `mypy --strict` clean.

## Reviewer guidance

Verify: E routes onto `parse_meta_file`, NOT `load_meta_or_empty`; the row-matrix decoder is untouched; empty→`{}` and non-object→`EventLogMergeError` contracts intact; malformed now fails loud named; proof-of-red captured; census untouched.
