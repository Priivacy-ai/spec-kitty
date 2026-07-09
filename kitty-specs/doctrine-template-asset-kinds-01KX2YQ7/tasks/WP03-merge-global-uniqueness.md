---
work_package_id: WP03
title: Merge compose + global URN-uniqueness scan
dependencies: [WP01, WP02]
requirement_refs:
- FR-002
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: feat/doctrine-template-asset-kinds-2495
merge_target_branch: feat/doctrine-template-asset-kinds-2495
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-template-asset-kinds-2495. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-template-asset-kinds-2495 unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
phase: Phase 3 - Merge + uniqueness
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1860405"
history:
- at: '2026-07-09T10:15:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/merge.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/merge.py
- tests/doctrine/test_drg_merge.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Merge compose + global URN-uniqueness scan

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` for the frontmatter profile before parsing the rest.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Compose template/asset nodes into the merged DRG and enforce **global** URN-uniqueness with a **single
post-merge scan** — replacing today's silent first-wins and covering all three layers.

Done when:
- `_PLURAL_TO_SINGULAR` includes `templates`→`template`, `assets`→`asset`.
- A `_check_node_urn_unique(prefix, nodes)` helper exists; it is invoked once at `merge_three_layers` over the
  fully-merged node set for the `asset:` and `template:` prefixes.
- A duplicate `asset:` URN anywhere (built-in ∪ every pack ∪ project) → hard-fail `duplicate_asset_id`; a
  duplicate `template:` URN → `duplicate_template_id`. Order-independent.
- Red-first tests prove the fail-loud behavior for both prefixes and cross-layer collisions.

## Context & Constraints

- Plan IC-04. Research **D-04 (revised)** — one scan at `merge_three_layers`, NOT the per-fragment org-vs-org
  tweak. Spec **FR-002/007/008**; contract **AT-3, TT-3**.
- Ground truth: `merge.py:63` `_PLURAL_TO_SINGULAR`; `:271-280` `_bridge_org_node_to_drg_node` (mints **bare**
  `f"{singular}:{node.id}"` — confirm, do not pack-qualify); `:378-431` `_merge_org_fragment` (org-vs-org silent
  first-wins at `:424` — being superseded); `:349` `_resolve_builtin_collision` (built-in-vs-org override);
  `:471` `merge_three_layers`; `:559-564` project-vs-any (project wins).
- **Scope by URN prefix**: the other 9 kinds' layered override tolerance MUST stay intact. `models.py` enforces
  prefix==kind, so an `asset:`/`template:` URN can only collide with its own kind — do not touch the override
  path for other prefixes.
- **Complexity ≤15**: `_merge_org_fragment` is already at the ceiling — put the scan in the new
  `_check_node_urn_unique` helper, called from `merge_three_layers`, not nested inside existing conditionals.
- Depends on **WP01** (enum) and **WP02** (universe/aliases).

## Branch Strategy
- **Planning base branch**: feat/doctrine-template-asset-kinds-2495
- **Merge target branch**: feat/doctrine-template-asset-kinds-2495
- **Strategy**: feature-branch (worktree per lane from `lanes.json`)

## Subtasks & Detailed Guidance

### T010 – `_PLURAL_TO_SINGULAR` += templates, assets
- **Steps**: add both plural→singular entries so fragments under `templates/` and `assets/` compose.
- **Files**: `src/doctrine/drg/merge.py`.

### T011 – `_check_node_urn_unique` helper
- **Steps**: write a pure helper that, given a URN prefix and the merged node collection, returns the first
  duplicate (or raises the structured error). Keep it total-graph and order-independent (e.g. count by URN).
- **Files**: `src/doctrine/drg/merge.py`.

### T012 – Wire the scan at `merge_three_layers`
- **Steps**: after the three layers are assembled, call the helper for `asset:` (→ `duplicate_asset_id`) and
  `template:` (→ `duplicate_template_id`). Emit distinct, structured, testable errors (NFR-005). Do NOT alter the
  other prefixes' collision handling.
- **Files**: `src/doctrine/drg/merge.py`.

### T013 – Red-first dup-URN tests
- **Steps**: FIRST write failing tests: (a) two org packs each shipping `asset:logo` → `duplicate_asset_id`;
  (b) a built-in `template:x` + an org `template:x` → `duplicate_template_id`; (c) confirm a normal single-owner
  asset/template still merges; (d) confirm two *different-kind* same-id URNs (e.g. `directive:x` override) still
  behave as before. Then implement T010–T012 to green them.
- **Files**: `tests/doctrine/test_drg_merge.py`.

## Test Strategy
`pytest tests/doctrine/test_drg_merge.py -q`. Prove RED before GREEN for T013 (a→c). Include the regression
assertion (d) that the other kinds' override tolerance is untouched.

## Risks & Mitigations
- **Over-broad hard-fail**: scanning without a prefix filter would break the 9 kinds' override — always filter by
  `asset:`/`template:` prefix.
- **Order dependence**: count-by-URN, don't rely on iteration order.

## Review Guidance
- Confirm the scan runs once at `merge_three_layers` (not per-fragment), is prefix-scoped, and the two error
  codes are distinct. Confirm `_bridge_org_node_to_drg_node` still mints bare URNs.

## Activity Log
- 2026-07-09T10:15:17Z – system – Prompt created.
- 2026-07-09T11:24:42Z – claude:sonnet:python-pedro:implementer – shell_pid=1811721 – Assigned agent via action command
- 2026-07-09T11:39:29Z – claude:sonnet:python-pedro:implementer – shell_pid=1811721 – Ready: templates/assets added to _PLURAL_TO_SINGULAR; new DuplicateURNError + _check_node_urn_unique(prefix, nodes) helper wired once at merge_three_layers over a raw (pre-override-collapse) union of built-in/org/project asset:/template: nodes; scoped strictly by prefix so the other 9 kinds' override tolerance is untouched. 5 new red-first tests (org-vs-org dup asset, cross-layer built-in-vs-org dup template, single-owner clean merge, non-asset/template override regression, prefix-scoping regression) all green. tests/doctrine/test_drg_merge.py -q: 49 passed. ruff check src/doctrine/drg/merge.py tests/doctrine/test_drg_merge.py: exit 0 (All checks passed!). mypy src/doctrine/drg/merge.py: exit 0. Full tests/doctrine/ suite: 2478 passed, no regressions.
- 2026-07-09T11:40:12Z – claude:opus:reviewer-renata:reviewer – shell_pid=1860405 – Started review via action command
- 2026-07-09T11:46:30Z – user – shell_pid=1860405 – Review passed. Raw-union scan verified rigorously: _check_node_urn_unique (Counter-based, order-independent) runs once at merge_three_layers over _asset_template_candidates (raw per-layer union of built-in ASSET/TEMPLATE nodes + bridged org-fragment assets/templates + project nodes), NOT merged_nodes. Confirmed scanning merged_nodes WOULD hide collisions: org-vs-org first-wins and built-in-vs-org override both collapse to one dict key. Raw union catches all three pairings; no false-positive double-count (three inputs are distinct physical sources). Distinct codes duplicate_asset_id/duplicate_template_id. Scoping intact: only asset:/template: prefixes; collision fns additions-only. Bare URN minting preserved. Scan in separate helpers, ruff C901 clean. TEST-LOCKED: tests (a) org-vs-org and (b) built-in-vs-org cross-layer would both fail if scan ran over merged_nodes. 49 passed in test file; full tests/doctrine 2478 passed; ruff+mypy clean.
