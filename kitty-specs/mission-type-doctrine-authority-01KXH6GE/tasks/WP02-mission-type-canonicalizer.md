---
work_package_id: WP02
title: Single boundary-safe mission-type canonicalizer
dependencies: []
requirement_refs:
- C-001
- FR-001
- FR-003
- FR-012
- NFR-002
- NFR-003
tracker_refs:
- '883'
planning_base_branch: mission/883-mission-type-governance-profiles
merge_target_branch: mission/883-mission-type-governance-profiles
branch_strategy: Planning artifacts for this mission were generated on mission/883-mission-type-governance-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/883-mission-type-governance-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1358384"
shell_pid_created_at: "1784068357.85"
history:
- at: '2026-07-14T21:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-02, Lane B root — precedes the resolver seam)
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- src/charter/mission_type_key.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/mission_type_key.py
- src/specify_cli/mission.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read: [plan.md](../plan.md) §IC-02 +
"Canonicalizer census" cross-cutting note, [spec.md](../spec.md) FR-012 / FR-001 / FR-003 / FR-003a /
C-001, and the ADR decision "A single mission-type canonicalizer (`WP-CANON`), across the package
boundary" ([ADR 2026-07-14-2](../../../docs/adr/3.x/2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md)).

## Objective

Provide **one** canonicalizer for the mission-type key that both the `charter` and `specify_cli` layers
consume, and **remove the `software-dev` governance default** at its source in `specify_cli/mission.py`
(FR-012, FR-001) — closing the leak on the governance/dossier path. Because `charter/` may not import
`specify_cli` (C-001, `test_layer_rules.py`), the canonicalizer lives where both may import it:
`charter/` (legal because `specify_cli → charter` is allowed). This is the Lane-B root that WP03 builds on.

## Context

- **Framing correction (squad):** `mission_type_profiles.py:380` **already raises** on an unknown type — it
  does NOT default silently to software-dev. Do **not** treat it as a leak site. The only **live governance
  sinks** that silently default are `specify_cli/mission.py` (this WP) and `charter/context.py:865`
  (closed by WP04). `mission.py get_mission_type` returns `software-dev` when `meta.json` omits the key,
  and it feeds the **dossier** path behind the package boundary — that is this WP's target.
- `mission.py` also has a `get_deliverables_path` sw-dev-defaulting sink and a **dead** `get_mission_key`
  (no live src callers → retire). **Line numbers have drifted — grep-repin them live before editing**
  (approx: `get_mission_type` ~556, `get_deliverables_path` ~578, `get_mission_key` ~535).
- `get_mission_type` has **~13 live callers**. Each must be **classified**, not blanket-changed:
  has-`meta.json` → unaffected; typeless → **neutral degrade, never software-dev** (FR-003a). A partial
  census leaves the split half-closed (the plan is explicit about this).

## Subtask guidance

- **T006 — canonicalizer module.** Create `src/charter/mission_type_key.py` with a small, pure
  canonicalizer (normalize the raw mission-type string → canonical key; no I/O, no sw-dev default baked
  in). It must be importable by both layers without violating C-001 — **verify** `charter/` does not gain
  a `specify_cli` import. Keep it minimal and fully typed.
- **T007 — remove the governance default.** At `mission.py:get_mission_type:575`, remove the
  `software-dev` fallback for the **governance** read; route through the canonicalizer. Per C-006, the
  `meta.json`-less **template-file-selection** fallback (`mission.py:466,469`) is **out of scope** — do
  NOT remove that one; scope it OUT with a rationale comment referencing C-006.
- **T008 — deliverables path.** Route `get_deliverables_path:605` through the canonicalizer, preserving
  its current behaviour for typed missions.
- **T009 — retire dead code.** Delete `get_mission_key:548` (dead — grep the tree to prove 0 live src
  callers; test-only callers are updated/removed with it).
- **T010 — caller census.** **Grep-repin the live line numbers first** — the `mission.py` sink lines have
  drifted (`get_mission_type` ~556, `get_deliverables_path` ~578, `get_mission_key` ~535); pin them live
  before classifying. Then classify the ~13 live `get_mission_type` callers named in the plan
  (`runtime_bridge.py:1232,2244`, `mission_runtime/resolution.py:946`, `next_cmd.py:665` [note `:658`
  documents default reliance], `research.py:102`, `tasks_parsing_validation.py:982`,
  `mission_setup_plan.py:678`, `sync/dossier_pipeline.py:250`, `workflow_executor.py:564`,
  `mission.py:768`, …). For each: **has `meta.json`** → unaffected (document why); **typeless** → route to
  the neutral/degrade result, never software-dev. Record the classification inline (or in the PR body) as
  **justified out-of-map** dispositions — callers outside owned_files are touched only where the census
  requires and with a one-line rationale each.
- **T011 — RED-first + gates.** Write a RED behavioural test through a **typeless** entry that today
  silently yields `software-dev`, asserting it now degrades neutrally (FR-003a) and never loads sw-dev.
  Make it green. `ruff` + `mypy` clean; complexity ≤ 15.

## Branch Strategy

Planning artifacts were generated on `mission/883-mission-type-governance-profiles`. This WP branches from
the mission base during `/spec-kitty.implement` and merges back into
`mission/883-mission-type-governance-profiles`. It is a Lane-B **root** (no deps); WP03 depends on it.

## Definition of Done

- [ ] `src/charter/mission_type_key.py` exists, pure, fully typed; it adds **no module-level**
      `specify_cli` import, and `tests/architectural/test_layer_rules.py::…test_charter_does_not_import_specify_cli`
      stays green. (A pre-existing **function-local** import at
      `src/charter/synthesizer/synthesize_pipeline.py:68` is tolerated by the guard — do NOT touch it.)
- [ ] `get_mission_type:575` no longer returns `software-dev` on a typeless/absent-key read (governance
      path); the `mission.py:466,469` **template-file-selection** fallback is left in place, rationale-scoped OUT (C-006).
- [ ] `get_deliverables_path:605` routes through the canonicalizer; dead `get_mission_key:548` deleted (0 live callers).
- [ ] All ~13 `get_mission_type` callers classified; typeless ones degrade neutrally (never sw-dev);
      dispositions recorded.
- [ ] RED-first test proves a former typeless-→-software-dev path now degrades neutrally (FR-003a).
- [ ] `ruff` + `mypy` clean; complexity ≤ 15.

## Risks

- **Layer-rule trip** — a `specify_cli` import sneaking into `charter/mission_type_key.py`. Guard with
  `test_layer_rules.py`.
- **Partial census** — leaving a caller silently defaulting entrenches the split half-closed. The census
  must enumerate every sink/caller or scope it OUT with rationale.
- **Turning a silent default into a silent crash** — the degrade branch (FR-003a) must be per-entry and
  never a blanket hard-error (blanket hard-error breaks dispatch/workflow which have no mission).

## Reviewer guidance (reviewer-renata, opus)

- Confirm C-001 holds — `test_layer_rules.py::…test_charter_does_not_import_specify_cli` green; no new
  module-level `specify_cli` import in `mission_type_key.py` (the pre-existing function-local import at
  `synthesize_pipeline.py:68` is untouched).
- Confirm every `get_mission_type` caller is accounted for (census is complete, not partial).
- Confirm the RED-first test drives a genuinely typeless path (not a has-`meta.json` path that would pass
  vacuously) and that the template-file-selection fallback was deliberately preserved (C-006).

## Activity Log

- 2026-07-14T22:12:35Z – claude:sonnet:python-pedro:implementer – shell_pid=1312977 – Assigned agent via action command
- 2026-07-14T22:31:51Z – claude:sonnet:python-pedro:implementer – shell_pid=1312977 – Ready: canonicalizer + sw-dev governance defaults removed; layer guard green
- 2026-07-14T22:32:45Z – claude:opus:reviewer-renata:reviewer – shell_pid=1358384 – Started review via action command
- 2026-07-14T22:37:15Z – user – shell_pid=1358384 – Review passed: single boundary-safe canonicalizer charter/mission_type_key.py is pure, module-level-import-clean (C-001 guard green, 17 passed), absence/blank->None (no baked-in default). mission.py get_mission_type + get_deliverables_path route through it and neutral-degrade to ''/None on typeless reads (FR-003a) instead of software-dev. Dead get_mission_key + get_feature_mission_key retired (grep 0). C-006 template-selection sw-dev fallbacks preserved with rationale comments (473/476/780/803 template-file-selection, not governance). Census: 10 live get_mission_type callers unchanged; dossier_pipeline:250 'or mission_type' falls through correctly. Stale ==software-dev assertions FLIPPED to neutral-degrade (not deleted-to-green). Gates: ruff/mypy --strict clean, 32 impacted tests pass, layer-rules 17 pass.
