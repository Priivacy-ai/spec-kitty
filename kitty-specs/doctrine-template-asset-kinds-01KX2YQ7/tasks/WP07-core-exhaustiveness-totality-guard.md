---
work_package_id: WP07
title: Core exhaustiveness + totality guard
dependencies: [WP01, WP02, WP03, WP04, WP05, WP06]
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/doctrine-template-asset-kinds-2495
merge_target_branch: feat/doctrine-template-asset-kinds-2495
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-template-asset-kinds-2495. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-template-asset-kinds-2495 unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
phase: Phase 4 - Exhaustiveness (core + guard)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1912552"
history:
- at: '2026-07-09T10:15:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/query.py
create_intent:
- tests/doctrine/drg/test_kind_mapping_totality.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/query.py
- src/specify_cli/mission_step_contracts/executor.py
- src/doctrine/template_catalog.py
- tests/doctrine/test_drg_relations.py
- tests/doctrine/drg/test_kind_mapping_totality.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Core exhaustiveness + totality guard

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` for the frontmatter profile before parsing the rest.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Fix the dropped-asset-node return + the remaining core maps, and add the C-005 **totality guard** — with the
critical `.get`-partial exemption so it does not false-fail on pre-existing code.

Done when:
- `ResolveTransitiveRefsResult` gains an `assets: list[str]` field AND a wired return line, so asset nodes reached
  transitively are returned, not silently dropped.
- `executor::_ARTIFACT_TO_NODE_KIND` includes asset + template; `template_catalog` reconciles the bare-URN scheme
  (its `template:<mission>/<name>` ids coexist with org bare `template:<id>` under the WP03 uniqueness scan).
- A totality guard test asserts every kind-keyed mapping table is total **OR a documented `.get`-partial**.
- The guard is proven to **exempt** the four pre-existing partials (`kind_vocabulary.py:75/79`,
  `pack_manager.py:132/225`) — no Day-1 false-fail.

## Context & Constraints

- Plan IC-05. Research **D-09, D-10, D-13**. Spec **FR-012, C-005**. Contract **AT-7 + the totality-guard section**.
- Ground truth: `drg/query.py:132/153` `ResolveTransitiveRefsResult` (fixed-field dataclass; the
  `{k:[] for k in NodeKind}` bucket includes ASSET but the return `:229-240` never reads
  `buckets[NodeKind.ASSET]` → dropped); `mission_step_contracts/executor.py:31` `_ARTIFACT_TO_NODE_KIND`;
  `template_catalog.py:122-124`; the existing subset guard `tests/doctrine/drg/test_nodekind_artifactkind.py:14`
  (`artifact_values <= node_values`) — this WP **upgrades** it to a totality guard.
- The four exempt partials (all `.get`-accessed, safe for new kinds): `charter/kind_vocabulary.py:75/79`,
  `charter/pack_manager.py:132/225`. The guard must distinguish totality-required maps from these.
- Depends on **WP01–WP06** — the guard requires every mapping site already total, so run last among code WPs.

## Branch Strategy
- **Planning base branch**: feat/doctrine-template-asset-kinds-2495
- **Merge target branch**: feat/doctrine-template-asset-kinds-2495
- **Strategy**: feature-branch (worktree per lane from `lanes.json`)

## Subtasks & Detailed Guidance

### T027 – `ResolveTransitiveRefsResult` += `assets`
- **Steps**: add `assets: list[str]` to the dataclass and populate it from `buckets[NodeKind.ASSET]` in the
  return (`:229-240`). Add a query test proving a transitively-reached asset node appears in `.assets`.
- **Files**: `src/doctrine/drg/query.py`, `tests/doctrine/test_drg_relations.py`.

### T028 – `_ARTIFACT_TO_NODE_KIND` + `template_catalog`
- **Steps**: add asset + template entries to `executor::_ARTIFACT_TO_NODE_KIND`; confirm `template_catalog`
  keeps its `template:<mission>/<name>` ids (bare-URN reconciliation — clashes caught by WP03's scan, not
  presumed disjoint).
- **Files**: `src/specify_cli/mission_step_contracts/executor.py`, `src/doctrine/template_catalog.py`.

### T029 – Totality guard test
- **Steps**: new `tests/doctrine/drg/test_kind_mapping_totality.py` — discover (by reflection/AST) every
  module-level `dict` keyed by `ArtifactKind`/`NodeKind` and assert it is total (an entry for every member) OR
  explicitly allow-listed as a documented `.get`-defaulted partial. Replaces/augments the subset guard.
- **Files**: `tests/doctrine/drg/test_kind_mapping_totality.py`.

### T030 – Prove the `.get`-partial exemption
- **Steps**: include the four known partials as fixtures/cases and assert the guard **passes** (exempts) them —
  i.e. a naive "every dict must be total" implementation would fail here; yours must not. Document the exemption
  criterion (e.g. an inline `# totality: get-partial` marker or an explicit allow-list keyed by qualified name).
- **Files**: `tests/doctrine/drg/test_kind_mapping_totality.py`.

## Test Strategy
`pytest tests/doctrine/drg/test_kind_mapping_totality.py tests/doctrine/test_drg_relations.py -q`. The guard must
be green against the *current* tree (including the four partials) — run the whole doctrine+charter suite to
confirm no over-fire.

## Risks & Mitigations
- **Guard over-fire**: the headline risk — a naive guard false-fails on the four partials. Prove the exemption
  (T030) before claiming done.
- **Silent drop regression**: without T027 the transitive query drops assets — assert it directly.

## Review Guidance
- Confirm the transitive result includes assets, the guard is total-or-exempt, and the four partials are proven
  exempt (not merely asserted).

## Activity Log
- 2026-07-09T10:15:17Z – system – Prompt created.
- 2026-07-09T11:48:11Z – claude:sonnet:python-pedro:implementer – shell_pid=1876863 – Assigned agent via action command
- 2026-07-09T12:04:17Z – claude:sonnet:python-pedro:implementer – shell_pid=1876863 – Ready: T027 wires buckets[NodeKind.ASSET] into ResolveTransitiveRefsResult.assets (was silently dropped); T028 adds ArtifactKind.ASSET to executor._ARTIFACT_TO_NODE_KIND (template_catalog.py needs no change -- confirmed no ArtifactKind-keyed dict there, bare template:<mission>/<name> ids stay as-is per WP03 uniqueness scan); T029/T030 new tests/doctrine/drg/test_kind_mapping_totality.py: AST-discovers every module-level dict keyed by ArtifactKind/NodeKind across src/, asserts total-or-exempt via explicit qualified-name allow-list (_EXEMPT_GET_PARTIALS = charter.kind_vocabulary::_ID_FIELD_BY_KIND/_PROJECT_KIND_DIRS + charter.pack_manager::_ID_FIELD_BY_KIND/_PROJECT_KIND_DIRS), plus a synthetic-source unit test proving the naive (unexempted) check would false-fail on the current tree. ruff check exit 0, mypy clean, tests/doctrine+tests/charter full sweep: 3918 passed, 1 skipped, 0 new failures.
- 2026-07-09T12:05:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=1912552 – Started review via action command
- 2026-07-09T12:12:05Z – user – shell_pid=1912552 – Review passed: (1) query.py ResolveTransitiveRefsResult gained assets field + wired assets=buckets[NodeKind.ASSET]; T027 test drives REAL resolve_transitive_refs over a 2-hop REQUIRES graph proving a transitively-reached asset surfaces in .assets. (2) executor._ARTIFACT_TO_NODE_KIND has ArtifactKind.ASSET:NodeKind.ASSET. (3) template_catalog claim verified: no ArtifactKind/NodeKind-keyed dict exists (bare URNs via template_urn), unchanged. (4) THE GUARD is genuinely load-bearing: MUTATION TEST PASSED — injected a partial dict[ArtifactKind,str] missing ASSET into query.py and the guard FAILED naming the missing ASSET member; reverted, guard green. Exemption proven necessary: all 4 partials confirmed discovered by scan, genuinely non-total, .get-accessed; T030 pins naive total-only check WOULD false-fail on them; mixed-shape dicts raise loudly. (5) Scope clean. ruff+mypy clean; owned tests 16/16; drg+exempt spot-check 198/198 green (no over-fire).
