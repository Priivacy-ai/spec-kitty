---
work_package_id: WP03
title: implement_cores + implement routing + second comparator retirement (atomic)
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-005
- FR-006
- FR-007
- NFR-002
planning_base_branch: feat/meta-json-l1-seam-routing-3259
merge_target_branch: feat/meta-json-l1-seam-routing-3259
branch_strategy: Planning artifacts for this mission were generated on feat/meta-json-l1-seam-routing-3259. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-json-l1-seam-routing-3259 unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
history:
- at: '2026-08-10'
  note: Authored by /spec-kitty.tasks (post-plan-squad model).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/implement_cores.py
create_intent:
- tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/implement_cores.py
- src/specify_cli/cli/commands/implement.py
- tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py
- tests/specify_cli/cli/commands/test_implement_cores.py
- tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py
- tests/specify_cli/test_specify_topology_flag.py
- tests/architectural/test_trio_seam_only.py
- tests/architectural/test_exemption_registry_ratchet.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Apply it, then read this WP, `spec.md` (FR-003/005/006/007, NFR-002), `data-model.md` (sites C/D + error-translation), and `research.md` (D6/D7). WP01 must be merged first.

## Objective

Route implement_cores' two `meta.json` reads (site C `_is_self_write_only_diff` decode at `:427`, site D `_committed_meta_mapping` at `:338`) fail-closed onto kernel L1, **retire implement_cores' OWN second comparator + field-set** (`_VCS_LOCK_META_FIELDS:50`, `_is_vcs_lock_only_meta_diff:241`) onto the kernel comparator, reconcile the `implement.py:62-70` historical-location shim, and retarget the binding tests. **One atomic unit** (deletion breaks callers). **Census-neutral** — route onto `decode_meta`, do not touch the floor.

> ⚠️ **NFR-002 ownership lives HERE.** implement_cores carries a *second* comparator+field-set beyond ref_advance's. If you route C/D but leave the comparator, WP05's NFR-002 "exactly 1 comparator" gate reds with no owner. Retiring it is in scope.

### Subtask T013 — Delete parser + retire second comparator/field-set

In `src/specify_cli/cli/commands/implement_cores.py`: delete `_parse_meta_mapping` (~:259); retire `_VCS_LOCK_META_FIELDS` (~:50) and `_is_vcs_lock_only_meta_diff` (~:241) in favor of `kernel.vcs_lock.is_vcs_lock_only_change` + `VCS_LOCK_META_FIELDS`. Import the kernel decode + comparator symbols. Atomic with T014/T015.

### Subtask T014 — Route sites C and D onto kernel L1

- **Site D `_committed_meta_mapping` (~:330)**: `GitPort.show_blob` `bytes` → `decode_meta(blob, on_malformed="raise")`. Preserve the benign missing/None arm (a `None` blob = absent, not corrupt).
- **Site C `_is_self_write_only_diff` decode (~:427)**: `source.read_bytes()` → `decode_meta(...)`. **KEEP THE READ INLINE** — `test_trio_seam_only.py:627` pins the token-substring `"source . read_bytes ( )"`; extracting it to a helper reds that gate. The `:471` byte-compare is NOT a decode — leave it untouched. Any caller that previously got `None`→`return False` now fails loud on a present-but-corrupt file (FR-007), while missing/empty stays benign (FR-005).

### Subtask T015 — Reconcile the implement.py shim

`implement.py:62-70` re-exports `_parse_meta_mapping`, `_committed_meta_mapping`, `_is_vcs_lock_only_meta_diff`, `_is_self_write_only_diff` "for external callers/tests." After T013 two of those symbols no longer exist. **Never leave a name pointing at a deleted symbol** (import-time crash). Options: drop the re-exports for deleted symbols and retarget importers (T016); keep `_committed_meta_mapping`/`_is_self_write_only_diff` re-exports (they survive, re-routed). Decide and apply so `import specify_cli.cli.commands.implement` succeeds.

### Subtask T016 — Retarget the binding tests (blast radius)

Rewrite these importers/assertions (each imports a deleted/retired symbol or asserts the old silent `None`):
- `tests/specify_cli/cli/commands/test_implement_cores.py:29-30,262-268` — imports `_parse_meta_mapping`/`_is_vcs_lock_only_meta_diff`; `is None` on malformed → `pytest.raises(MetaDecodeError)` (or `decode_meta(..., on_malformed="none") is None`); comparator asserts → kernel comparator.
- `tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py:39,405` — comparator truth-table → kernel comparator.
- `tests/specify_cli/test_specify_topology_flag.py:597` — `from specify_cli.cli.commands.implement import _is_vcs_lock_only_meta_diff` → kernel comparator (or the retained shim name).
- `tests/architectural/test_trio_seam_only.py:625,639` + `tests/architectural/test_exemption_registry_ratchet.py:436` — these register `_is_self_write_only_diff`; keep the registration valid (symbol survives, read stays inline) — update descriptors only if the symbol's signature/decoder changed.

### Subtask T017 — Red-first C/D diagnosability (unit, NO git)

Create `tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py` (declare `pytestmark` — **unit markers, NO `git_repo`**; site D uses the injectable `GitPort` fake at `implement_cores.py:112`, site C reads an on-disk `tmp_path` file). Assert per site: corrupt bytes → `pytest.raises(MetaDecodeError, match="meta.json")`; missing/empty → benign (FR-005); valid → pre-routing verdict unchanged. **Capture proof-of-red** against the pre-T013 tree.

### Subtask T018 — Confirm importable + census-neutral + gates green

- `python -c "import specify_cli.cli.commands.implement; import specify_cli.cli.commands.implement_cores"` succeeds.
- Census unchanged vs WP01 end state. Do NOT edit `ROUTED_CALLEES`/floor.
- Run: `PWHEADLESS=1 python -m pytest tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py tests/specify_cli/cli/commands/test_implement_cores.py tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py tests/specify_cli/test_specify_topology_flag.py tests/architectural/test_trio_seam_only.py tests/architectural/test_exemption_registry_ratchet.py tests/architectural/test_inline_meta_read_gate.py -q` → green.

## Branch Strategy

Base + merge target: `feat/meta-json-l1-seam-routing-3259`. Worktree per computed lane. Depends on WP01.

## Definition of Done

- `_parse_meta_mapping` deleted; implement_cores' second comparator+field-set retired onto kernel; sites C/D route onto kernel L1; site C read stays inline.
- implement.py shim reconciled (no dangling name); state the shim decision (drop vs retain the two surviving re-exports) at the top of your WP notes so the reviewer holds one decision. The ~5 binding test files retargeted and green.
- **Git-verifiable red-first**: commit the C/D diagnosability test in a commit PRECEDING the routing commit (proof-of-red is a git artifact). Run with `-rs`, confirm the corrupt-arm tests `passed`, **0 skips** (C/D are unit — no fixture-skip excuse).
- **NFR-002 proven, not grepped**: the retired symbols (`_VCS_LOCK_META_FIELDS`, `_is_vcs_lock_only_meta_diff`) are 0 in `src/` — and WP05's `test_meta_decoder_comparator_singletons.py` gate enforces this tree-wide; this WP must leave that gate green.
- **Census-neutral, proven**: grep the new decode callee is `decode_meta` (NOT a `ROUTED_CALLEES` member); reviewer re-runs the census one-liner and confirms unchanged. No `ROUTED_CALLEES`/floor change.
- `ruff` + `mypy --strict` clean.

## Reviewer guidance

Verify: NO second comparator/field-set survives in implement_cores (grep `_VCS_LOCK_META_FIELDS`/`_is_vcs_lock_only_meta_diff` → 0 in `src/`); site C `source.read_bytes()` stays inline (trio gate); shim has no dangling re-export; C/D tests carry NO `git_repo` marker; proof-of-red captured; census untouched.
