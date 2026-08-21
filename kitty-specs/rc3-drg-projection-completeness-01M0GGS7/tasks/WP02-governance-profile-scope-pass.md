---
work_package_id: WP02
title: '#3604 — type-wide governance projected + _DRG_NODE_KINDS fold'
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- C-003
planning_base_branch: rc3-drg-projection-completeness-01M0GGS7
merge_target_branch: rc3-drg-projection-completeness-01M0GGS7
branch_strategy: Planning artifacts for this mission were generated on rc3-drg-projection-completeness-01M0GGS7. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-drg-projection-completeness-01M0GGS7 unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T014
history: []
agent_profile: implementer-ivan
authoritative_surface: src/doctrine/drg/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/drg/migration/extractor.py
- src/doctrine/drg/models.py
- src/charter/synthesizer/topic_resolver.py
- docs/architecture/doctrine-relationships.md
- tests/charter/test_cascade.py
tags: []
tracker_refs: []
---

# WP02 — #3604: type-wide governance projected + node-kind fold

**Goal:** a mission type's type-wide `governance-profile.yaml` selections reach the
DRG as `mission_type:<t> --scope--> <gov>` edges (all four built-in types), so the
cascade for `mission_type:plan` stops resolving to empty. Net-new emit pass.

**Grounding (current main):** no pass reads `governance-profile.yaml` for DRG
emission (`extract_action_edges` at `:1044` reads only `actions/*/index.yaml`). The
`mission_type:<t>` node already exists (`_discover_mission_type_nodes:1177`);
`extract_mission_type_edges:1289` emits `--requires--> action` only. `plan` authors
1 directive (`031-context-aware-design`), 9 tactics, 3 paradigms, 1 styleguide
(`planning-and-tracking`). `_DRG_NODE_KINDS` (`topic_resolver.py:37`) lacks
`mission_type`. **Depends on WP01 — same file `extractor.py`; run after it.**

### Subtask T005 — fold `mission_type` into `_DRG_NODE_KINDS`
- **Files:** `src/charter/synthesizer/topic_resolver.py:37` (+1 line).
- Add `"mission_type"` to the frozenset (FR-006/AC-005) so the new edge source
  resolves. Load-bearing for T007.

### Subtask T006 — `[red]` rewrite the plan-cascade test
- **Files:** `tests/charter/test_cascade.py` (`:406`, `:449–459`).
- Move `mission_type:plan` into `_GOVERNANCE_BEARING_MISSION_TYPE_URNS` (`:406`);
  **rewrite** `test_plan_cascade_is_empty_because_its_actions_scope_no_governance`
  (`:449`) to assert plan cascades to its 1 directive / 9 tactics / 3 paradigms / 1
  styleguide, and revise the rationale comment (`:452–459`). **RED before T007.**
  (FR-004/AC-003)

### Subtask T007 — the governance-profile.yaml → scope pass
- **Files:** `extractor.py` (new function wired next to `extract_action_edges`).
- Walk `packs/built-in/missions/*/governance-profile.yaml`; for each type emit
  `mission_type:<t> --scope--> <selected_* target>` for every entry of
  `selected_directives`/`selected_tactics`/`selected_paradigms`/`selected_styleguides`
  (bare-id targets → do NOT reuse `_reference_edge_kwargs`). Relation `scope`, source
  node `mission_type` (**C-003, locked**). Fire identically for all four types.
  GREEN T006. (FR-003, FR-005)

### Subtask T008 — `[red]` per-type coverage assertions
- **Files:** `tests/charter/test_cascade.py` (or a sibling test).
- **Primary (robust):** for each of documentation/research/software-dev/plan, assert
  `mission_type:<t>` has a `scope` edge to **every** entry of its
  `governance-profile.yaml` `selected_*` lists (AC-004). **Secondary (ratchet):**
  pin cascade counts documentation 31 / research 23 / software-dev 160 / plan
  populated, with a comment that they move as doctrine grows.

### Subtask T014 — `[lockstep]` update the SCOPE relation authority (post-plan squad, MAJOR)
- **Purpose:** the new `mission_type --scope--> gov` edges falsify the canonical
  `RELATION_DESCRIPTIONS[Relation.SCOPE]` prose, which claims `scope` originates
  **only** from "a mission-step action node" and cites a hard edge count ("165").
  This authority is byte-mirrored to `docs/architecture/doctrine-relationships.md`
  and enforced by `tests/doctrine/test_relation_doc_parity.py` — but **no test
  checks the count against the live graph**, so this drift goes silently un-red.
- **Files:** `src/doctrine/drg/models.py` (`RELATION_DESCRIPTIONS[Relation.SCOPE]`,
  ~`:197–207`) + mirrored `docs/architecture/doctrine-relationships.md` (~`:163`).
- Reword the source-kind claim so it is TRUE after #3604 (scope now also
  originates from a `mission_type` node), and update/soften the edge-count prose.
  Keep `test_relation_doc_parity` green (models.py text == doc text). This is the
  codebase's standing lockstep-doc convention (cf. `test_extractor_projection.py`
  ledger entries 16–19). Do NOT skip — it is the one change here that turns a
  parity-enforced canonical statement false with zero automated signal.

## Definition of Done
- [ ] `mission_type` ∈ `_DRG_NODE_KINDS`.
- [ ] `RELATION_DESCRIPTIONS[Relation.SCOPE]` + mirrored doc updated in lockstep;
      `test_relation_doc_parity` green (T014).
- [ ] T006 red before T007, green after; rationale comment revised (not silently deleted).
- [ ] New pass emits `scope` edges for all four types; membership coverage asserted.
- [ ] `ruff` + `mypy` clean. **Do NOT regenerate goldens here** (WP04).
- [ ] This is a completeness fix (authored governance was dropped), not a signed-off
      policy reversal — no ADR needed (unlike M3/M5).

Implement: `spec-kitty agent action implement WP02 --agent claude`
