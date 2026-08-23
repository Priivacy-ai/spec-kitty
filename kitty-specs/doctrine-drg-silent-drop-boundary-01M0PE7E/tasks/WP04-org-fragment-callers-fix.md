---
work_package_id: WP04
title: Org fragment silent-drop fix at the callers (#3530)
dependencies:
- WP03
requirement_refs:
- FR-009
- FR-010
planning_base_branch: fix/doctrine-drg-silent-drop-boundary
merge_target_branch: fix/doctrine-drg-silent-drop-boundary
branch_strategy: Planning artifacts for this mission were generated on fix/doctrine-drg-silent-drop-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/doctrine-drg-silent-drop-boundary unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
history:
- at: '2026-08-23T00:00:00Z'
  actor: tasks
  note: WP created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/mission_step_contracts/
create_intent:
- tests/specify_cli/mission_step_contracts/test_executor_org_fragment.py
- tests/charter/test_action_doctrine_bundle_org_fragment.py
execution_mode: code_change
owned_files:
- src/specify_cli/mission_step_contracts/executor.py
- src/charter/action_doctrine_bundle.py
- packs/internal/README.md
- tests/specify_cli/mission_step_contracts/test_executor_org_fragment.py
- tests/charter/test_action_doctrine_bundle_org_fragment.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (+ `spec-kitty charter context --action
implement --json`). Apply + state what you applied. Shadow venv:
`export PATH="$PWD/.venv/bin:$PATH"`.

## Objective

Stop the two deficient consumer seams from silently dropping an org pack's
`drg/fragment.yaml`. Fix **at the callers** (thread `org_fragments`), NOT at the
`org_roots=` seam. This is the branch-named silent-drop and the #3530 enabler.

## Context (squad findings F1, F11–F13 — decisive)

- `load_validated_graph` (`src/charter/_drg_helpers.py`) has two org seams. The
  `org_fragments=` seam folds `drg/fragment.yaml` via `merge_three_layers`; the
  `org_roots=` seam reads only root `*.graph.yaml` and **ignores fragments** (and
  falsely suppresses the "no graph" warning when a fragment exists, `:174`).
- **Do NOT fix at the seam** (architect F1): 4 callers already pass BOTH
  `org_roots`+`org_fragments` (`gate_bindings.py:305`, `activate.py:300/398`,
  `deactivate.py:156`); a seam fix would double-fold for them and mis-tier org
  content into the built-in precedence base. The correct fix mirrors those 4:
  thread `org_fragments=load_org_drg(repo_root, strict=False)` at the two deficient
  callers only.
- The two deficient callers: `src/specify_cli/mission_step_contracts/executor.py:362`
  and `src/charter/action_doctrine_bundle.py:192`. Do **not** widen to
  `action_doctrine_bundle.py:245` (the DoctrineService seam — different path, F13).
- The executor also has a pre-probe (`executor.py:347-360`) that raises
  `DRGLoadError` for a fragment-only pack → excludes it from `healthy_roots`
  (a warned drop). Ensure content still arrives via `org_fragments` regardless; tidy
  the pre-probe warning if noisy.
- The existing degrade test (`test_executor.py:878-916`) uses a **malformed**
  fragment — it does not cover a **valid** fragment's nodes being folded. Your red
  test must use a valid fragment.

## Subtasks

### T017 — Thread `org_fragments` at the executor
- At `executor.py:362`, pass `org_fragments=load_org_drg(repo_root, strict=False)`.
  **`load_org_drg` is NOT currently imported in `executor.py`** (post-tasks G9) —
  add it to the existing `charter.drg` import (~`executor.py:23`, the block that
  already imports `ArtifactKind, DRGGraph, DRGLoadError, …`). Mirror the 4 correct
  dual-callers. Ensure the pre-probe (`:347-360`) does not defeat delivery (content
  arrives via fragments even if a fragment-only root is excluded from the
  `org_roots` health list).
- **Invoke WP03's org-governance guard** (post-tasks G1): after the merged graph is
  available, call WP03's `validator` governance-scope escalation
  (`validate_*governance_scope*` from `doctrine.drg.validator`) so an org-tier
  nonexistent `selected_*` raises here. This is the one-line wiring WP03's guard was
  designed for; do the same at `action_doctrine_bundle.py` in T018.

### T018 — Thread `org_fragments` at action_doctrine_bundle  [P]
- At `action_doctrine_bundle.py:192`, pass
  `org_fragments=load_org_drg(repo_root, strict=False)`. Leave the `:245`
  DoctrineService seam untouched (F13).
- Also invoke WP03's org-governance validator here (same one-line post-merge call
  as T017) so the org-tier fail-loud fires on this path too.

### T019 — Valid-fragment red test + no-double-fold assertion
- New tests (`test_executor_org_fragment.py`, `test_action_doctrine_bundle_org_fragment.py`):
  - Red-first: an org pack shipping only a **valid** `drg/fragment.yaml` (declaring
    e.g. `directive:OPERATOR_SIGNAL_CONTRACT`) — assert its node reaches the merged
    DRG via each caller's path. FAILS before T017/T018, passes after.
  - **No-double-fold**: assert the merged edge/node **multiset count** for the
    fragment equals the single-fold count (n, not 2n) — protects the 4 dual-callers.
  - Warning honesty: a genuinely graphless root emits the warning; a fragment-only
    root, once folded, does not falsely suppress.

### T020 — Refresh `packs/internal/` README  [P]
- Update `packs/internal/README.md`: its Layout block omits the on-disk
  `directives/` dir and the `OPERATOR_SIGNAL_CONTRACT` node now in
  `drg/fragment.yaml`. Bring the doc in line with the pack.

## Branch Strategy

Planning base + merge target: `fix/doctrine-drg-silent-drop-boundary`. Worktrees
per computed lane from `lanes.json` at implement time.

## Definition of Done

- `executor.py:362` and `action_doctrine_bundle.py:192` thread `org_fragments`; a
  valid fragment-only org pack's nodes/edges reach the merged DRG via both paths.
- No-double-fold multiset assertion passes (dual-callers unaffected). `:245` seam
  untouched.
- `packs/internal/README.md` matches the pack contents.
- `ruff` + `mypy --strict` clean; no new suppressions. Terminology guard green
  (`pytest tests/architectural/test_no_legacy_terminology.py -q`, NFR-003 — this WP
  edits `packs/internal/README.md` prose).
- Targeted greens: `pytest tests/specify_cli/mission_step_contracts/test_executor_org_fragment.py tests/charter/test_action_doctrine_bundle_org_fragment.py tests/specify_cli/mission_step_contracts/test_executor.py -q`.

## Risks / reviewer guidance

- Reviewer: reject any change to `_drg_helpers.py` `org_roots=` seam logic (F1 —
  seam fix double-folds). The fix must be at the two callers. Confirm the
  no-double-fold count assertion exists. Confirm `:245` untouched.
