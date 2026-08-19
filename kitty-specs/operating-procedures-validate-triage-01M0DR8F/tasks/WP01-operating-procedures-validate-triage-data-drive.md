---
work_package_id: WP01
title: Operating-Procedures Validate → Triage → Data-Drive
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
planning_base_branch: feat/operating-procedures-validate-triage
merge_target_branch: feat/operating-procedures-validate-triage
branch_strategy: Planning artifacts for this mission were generated on feat/operating-procedures-validate-triage. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/operating-procedures-validate-triage unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
phase: Phase 1 - Doctrine graph
history:
- timestamp: '2026-08-19T19:40:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: src/doctrine/agent_profiles/
create_intent:
- src/doctrine/agent_profiles/operating_procedures.py
- tests/architectural/test_operating_procedures_resolve.py
- tests/doctrine/agent_profiles/test_operating_procedures.py
- tests/specify_cli/cli/commands/test_doctor_operating_procedures.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/agent_profiles/operating_procedures.py
- src/doctrine/drg/migration/extractor.py
- src/specify_cli/cli/commands/_doctrine_collect.py
- src/specify_cli/cli/commands/_doctrine_health.py
- packs/built-in/agent_profiles/*.agent.yaml
- packs/built-in/*.graph.yaml
- tests/architectural/test_operating_procedures_resolve.py
- tests/doctrine/agent_profiles/test_operating_procedures.py
- tests/doctrine/drg/migration/test_extractor.py
- tests/doctrine/drg/migration/test_extractor_projection.py
- tests/specify_cli/cli/commands/test_doctor_operating_procedures.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#2994'
- '#3352'
- '#3488'
---

# Work Package Prompt: WP01 – Operating-Procedures Validate → Triage → Data-Drive

## ⚡ Do This First: Load Agent Profile

Load the `curator-carla` profile via `/ad-hoc-profile-load` (knowledge-base & doctrine
maintenance specialist) and behave according to its guidance before parsing the rest of this prompt.

---

## Objective & Success Criteria

Make every built-in agent-profile `collaboration.operating-procedures` entry resolve to a real
**procedure** DRG node — loud on failure — then triage the 44 that don't, then teach the DRG
extractor to derive `agent_profile --requires--> procedure` edges from the field (guarded), retiring
the two operating-procedures-sourced hand-pins. Ride along the unwired RECONCILE third trigger edge.

Success (mirrors spec Success Criteria):
- **SC-001**: built-in unresolved operating-procedures set = **0** (was 44).
- **SC-002**: the empty-set gate reddens when a fictional entry is injected (non-vacuous).
- **SC-003**: regenerated graph derives `agent_profile→procedure` edges incl. the 4 previously-inert real refs; **0** dangling (`assert_valid` passes); `agent_profile→procedure` = **8**.
- **SC-004**: the 2 op-proc-sourced `_CURATED_ARTIFACT_EDGES` pins are removed and their edges persist (data-driven); the 2 prose pins remain.
- **SC-005**: all 3 RECONCILE triggers have inbound edges (RECONCILE inbound = **3**).
- **SC-006**: no change to `REFERENCE_RELATIONS` (cascade) or the procedure delivery/render surface.

**Requirement refs**: FR-001…FR-010.

## Context & Constraints

- **Charter**: `.kittify/charter/charter.md`. **Spec**: `../spec.md`. **Plan**: `../plan.md`. **Research (census + seam map + triage table + graph delta)**: `../research.md`. **Contracts**: `../contracts/validator-and-emission-contract.md`.
- **Hard internal order (load-bearing, C-001)**: validate → triage → data-drive. Do the subtasks in order. Data-driving before triage mints dangling edges → `assert_valid` failure.
- **ATDD / red-first (C-011)**: the empty-set gate test (T002) and the extractor emission test (T006) are each committed RED before their fix, and are GREEN at the WP's final commit. The reviewer verifies red-on-base / green-at-final.
- **Single-authority (C-004)**: the validator lives under `src/doctrine/`. `charter` must not import `specify_cli`. `specify_cli` (doctor) importing `doctrine` is fine.
- **Scope guards**: do **NOT** touch `REFERENCE_RELATIONS` / cascade traversal (C-002, #2829=M5) or the procedure delivery/render surface / `procedures[]` array (C-003, #3488 render=M4). Do **NOT** author net-new procedure nodes for fictional refs (C-007).
- **NFR-001**: zero ruff/mypy `--strict` issues; **no** `# noqa` / `# type: ignore` / per-file-ignore additions.
- **NFR-004**: `extract_artifact_edges` is at the C901 ceiling (15) — factor new logic into a helper; do not raise complexity.
- **Baseline-red gotcha**: only failures red on this branch AND green on the merge-base are yours. Do not greenwash pre-existing P0 reds.
- **Never run the full `tests/architectural/` directory** in one go if the harness struggles — prefer targeted single-file runs.

### Ground-truth census (from research.md)
50 op-proc declarations across 16 profiles: **6 real procedure**, **8 wrong-kind** (all tactics), **36 fictional**. Baseline `agent_profile→procedure` edges = 4 (`doctrine-daphne`, `researcher-robbie` = op-proc pins to retire; `lexical-larry`, `minutes-maker-mahad` = prose pins to keep). RECONCILE inbound = 2.

## Branch Strategy

- **Planning base branch**: `feat/operating-procedures-validate-triage`
- **Merge target**: `feat/operating-procedures-validate-triage` → draft PR to `main`; the operator merges.
- Execution worktree is allocated per the computed lane from `lanes.json`; work inside the resolved workspace.

## Subtasks & Detailed Guidance

### T001 — Pure validator `resolve_operating_procedures` + `UnresolvedOpProc`

**File (new)**: `src/doctrine/agent_profiles/operating_procedures.py`.

- Define a frozen dataclass `UnresolvedOpProc(profile_id: str, entry: str, reason: Literal["no_node","wrong_kind"], resolved_kind: str | None)`. Mirror the shape/discipline of `doctrine/agent_profiles/diagnostics.py::SkippedProfile`.
- Define:
  ```python
  def resolve_operating_procedures(
      profiles: Iterable[AgentProfile],
      procedure_urns: AbstractSet[str],
      node_urns_by_kind: Mapping[NodeKind, AbstractSet[str]] | None = None,
  ) -> list[UnresolvedOpProc]:
  ```
  For each profile, for each entry in `profile.collaboration.operating_procedures`:
  `procedure:<entry>` ∈ `procedure_urns` → resolved (skip); else if `<entry>` matches a node of another kind (via `node_urns_by_kind`) → `wrong_kind` with `resolved_kind`; else → `no_node`.
- Pure, total, deterministic (sorted by `(profile_id, entry)`). No fuzzy match (NFR-003). Build the procedure URN via `doctrine.drg.migration.id_normalizer.artifact_to_urn("procedure", entry)`. Declare `__all__` and add a module docstring.

### T002 — Empty-set architectural gate (RED @ 44) + non-vacuity

**File (new)**: `tests/architectural/test_operating_procedures_resolve.py` — declare a `pytestmark` marker per repo convention.

- Load the real built-in profiles (`AgentProfileRepository(...).list_all()` restricted to the built-in layer) and the built-in procedure node URN set (`{n.urn for n in load_built_in_graph().nodes if n.kind is NodeKind.PROCEDURE}`, plus `node_urns_by_kind` for the wrong-kind classification).
- **Assert** `resolve_operating_procedures(...) == []`. This is **RED now (44 unresolved)** — commit it first, before triage.
- Add a **non-vacuity / self-mutation** check: construct an in-memory profile with a fictional op-proc entry and assert it is reported (proves the gate isn't vacuous), mirroring `tests/architectural/test_no_authored_applies_edge.py`.
- Commit T001+T002 together as the failing-first commit.

### T003 — Triage: delete the 36 fictional entries

Edit `packs/built-in/agent_profiles/*.agent.yaml`. Delete exactly the 36 fictional `operating-procedures` entries listed in research.md's disposition table (architect-alphonso, curator-carla, debugger-debbie, designer-dagmar, frontend-freddy, implementer-ivan, java-jenny, node-norris, paula-patterns, planner-priti, python-pedro, randy-reducer, researcher-robbie, retrospective-facilitator, reviewer-renata). Leave the 6 real entries intact. If deleting an entry empties the list, keep an empty `operating-procedures: []` or drop the key per the schema default (both are valid; prefer dropping the key when the whole list is gone).

### T004 — Triage: migrate 5 wrong-kind tactics, delete 3 redundant → gate GREEN

- **MIGRATE** (add to the profile's `tactic-references` as `{id: <tactic>, rationale: "..."}`, then remove from `operating-procedures`) — these tactics reach the profile via **no** other channel today (verified), so migration rescues genuine orphaned intent:
  - frontend-freddy → tdd-red-green-refactor
  - java-jenny → acceptance-test-first, tdd-red-green-refactor
  - node-norris → tdd-red-green-refactor
  - python-pedro → tdd-red-green-refactor
- **DELETE-redundant** (already in `tactic-references`; drop the op-proc entry only):
  - frontend-freddy → bug-fixing-checklist
  - node-norris → bug-fixing-checklist
  - reviewer-renata → reverse-speccing
- Re-run the T002 gate → **GREEN (0 unresolved)**.

### T005 — Doctor diagnostic

- In `src/specify_cli/cli/commands/_doctrine_collect.py`, compute the unresolved op-proc set (reuse `resolve_operating_procedures` — single authority) and surface it as a structured finding on the report (e.g. `org_drg["operating_procedures_unresolved"]`: list of `{profile_id, entry, reason, resolved_kind}`) via the established `_run_cross_grain_check`-style seam that mutates the report before `exit_code` derivation. Non-empty-on-built-in flips `healthy` false.
- Reflect the field in `_doctrine_health.py::DoctrineHealthReport.to_dict()` passthrough if needed.
- **Test (new)**: `tests/specify_cli/cli/commands/test_doctor_operating_procedures.py` — post-triage the built-in list is present-and-empty; a fixture with a fictional entry surfaces the finding and flips `healthy` false.

### T006 — Extractor: guarded emission + fail-closed raise (red-first)

**File**: `src/doctrine/drg/migration/extractor.py`, agent-profile block in `extract_artifact_edges`.

- **Red-first**: extend `tests/doctrine/drg/migration/test_extractor.py` with: (a) a synthetic profile fixture whose `operating-procedures` names a real procedure → exactly one `agent_profile:<id> --requires--> procedure:<target>` edge; (b) a synthetic profile whose op-proc entry is absent/non-procedure → **no** procedure edge (guard). Commit RED.
- Then implement: for each op-proc entry, emit `requires` to `procedure:<entry>` **only when** `procedure:<entry>` is already a known procedure node (guard — belt-and-suspenders for org/project tiers). Dedup via the existing `_add_edge` triple key.
- Add a **fail-closed raise**: if any op-proc entry on a **built-in** profile is unresolved, raise (post-triage this never fires). Reuse `resolve_operating_procedures`.
- Extract the new loop into a module-level helper to keep `extract_artifact_edges` ≤ C901 15 (NFR-004).

### T007 — Retire op-proc hand-pins + RECONCILE edge

- In `_CURATED_ARTIFACT_EDGES`, **remove** the two op-proc-sourced entries (`agent_profile:researcher-robbie → procedure:spike-timebox-policy` [edge 5] and `agent_profile:doctrine-daphne → procedure:onboard-external-agent-to-pack` [WP09 pin]). **Keep** `lexical-larry` and `minutes-maker-mahad` (prose-sourced; those profiles have no op-proc field). Update the surrounding comments so they no longer claim those two are hand-pinned.
- **Add** `tactic:change-apply-smallest-viable-diff --suggests--> directive:RECONCILE_CHANGE_SCOPE_TENSIONS` (the third trigger named in the reconciler's `scope:`; the other two already exist). Add a one-line rationale comment.

### T008 — Regenerate graph + reconcile counts + full validation

- Run `spec-kitty doctrine regenerate-graph` to rewrite the committed `packs/built-in/*.graph.yaml` fragments. Confirm `spec-kitty doctrine regenerate-graph --check` exits 0.
- Update `tests/doctrine/drg/migration/test_extractor_projection.py` pinned node/edge/orphan counts to the new correct values. **Expected delta (research.md)**: +4 net-new `agent_profile→procedure` edges, +5 `agent_profile→tactic` (migrations), +1 RECONCILE = **+10 edges, 0 new nodes**; `agent_profile→procedure` total = 8, RECONCILE inbound = 3. Record the delta table in the commit message as the rationale (this is not greenwashing — the pins reflect the intended graph).
- Validation sweep (targeted): `tests/doctrine/drg/migration/`, `tests/doctrine/agent_profiles/`, `tests/doctrine/test_profile_model.py`, the new gate + doctor tests, `tests/architectural/test_doctrine_regenerate_graph_roundtrip.py`, and `tests/architectural/test_no_legacy_terminology.py`. Then `ruff check` the touched surfaces and `mypy --strict` the new module. Confirm `assert_valid` passes via the graph build.
- Append the three mission tracer files (tooling-friction, approach, design-decisions) with anything learned.

## Definition of Done

- Empty-set gate GREEN (0 unresolved); non-vacuity check present.
- 44 entries triaged exactly per the disposition table; 6 real kept.
- Extractor emits guarded `agent_profile→procedure` edges; fail-closed raise on built-in unresolved.
- 2 op-proc pins retired (edges persist, data-driven); 2 prose pins kept; RECONCILE third edge wired.
- `regenerate-graph --check` green; `assert_valid` passes; count pins + golden updated with rationale.
- Doctor surfaces the diagnostic. ruff + mypy --strict clean, zero suppressions. Terminology guard green.
- Issue-matrix rows + tracker comments for #2994, #3352, #3488 (op-proc channel).

## Reviewer Guidance

- Verify red-on-base / green-at-final for both the empty-set gate and the extractor emission test.
- **Graph-delta audit (NFR-002)**: diff the regenerated `*.graph.yaml` against base; confirm exactly the +10 edges, every removed pin re-derived, zero dangling. Reject any cascade-relation (`REFERENCE_RELATIONS`) or delivery/render change (out of scope).
- Confirm the validator is the single authority (imported by both extractor and doctor; no restated procedure-id list; no `charter → specify_cli` import).
- Confirm `extract_artifact_edges` complexity ≤ 15 and no new suppressions.
- Spot-check 3–4 triage dispositions against research.md; confirm the 6 real entries are untouched and the 5 migrations landed in `tactic-references`.
