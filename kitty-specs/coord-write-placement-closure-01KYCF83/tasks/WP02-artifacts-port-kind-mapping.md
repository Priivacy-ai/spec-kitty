---
work_package_id: WP02
title: Partition-aware meta routing + decisions/traces classification (artifacts.py port)
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-006
planning_base_branch: feat/coord-write-placement-closure
merge_target_branch: feat/coord-write-placement-closure
branch_strategy: Planning artifacts for this mission were generated on feat/coord-write-placement-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-write-placement-closure unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-coord-write-placement-closure-01KYCF83
base_commit: 17f6e3081fb9d64c303139004966d8ebcedc8ae7
created_at: '2026-07-25T13:53:01.634678+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
- T054
phase: Phase 1 - Placement foundation
history:
- at: '2026-07-25T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/artifacts.py
create_intent:
- tests/mission_runtime/test_artifact_partition_mapping.py
execution_mode: code_change
owned_files:
- src/mission_runtime/artifacts.py
- tests/mission_runtime/test_artifact_partition_mapping.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Partition-aware meta routing + decisions/traces classification

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objective

This is the **foundational placement WP** (no dependencies). It owns `src/mission_runtime/artifacts.py` — the single partition SSOT — and merges **two** collision edits into one pass so no other WP co-edits this file:

1. **IC-03 (FR-002)**: give `PRIMARY_METADATA` a partition-aware write target — the **one-field flip** `commit_target=None` → `commit_target=placement_ref` at `artifacts.py:218-224` (delete the special-case arm so it matches the generic primary arm), so `write_meta` / `_flip_phase` / `_bake_mission_number` can route meta writes through the port and a coord/primary two-partition write becomes expressible.
2. **IC-04-classify (FR-003, FR-006)**: classify `decisions.events.jsonl` and `traces/` in the SSOT dicts `_MISSION_FILE_KIND_BY_BASENAME:181` and `_COORD_RESIDUE_DIRS:207` (both currently classify to `None` → COORD). Classification lives **only** in these two dicts — writers CALL `kind_for_mission_file`, they never classify inline.

**Done** = the sentinel flip lands with a grep-verified inert-consumer audit; `decisions.events.jsonl` + `traces/` resolve to COORD via the single classifier; `assert_partition_invariant()` stays exhaustive + disjoint; a new unit test pins the mapping.

## Context & Constraints

- Spec: [spec.md](../spec.md) US3 AS2/AS4, FR-002, FR-003, FR-006. Plan: [plan.md](../plan.md) IC-03 + IC-04-classify. Data model: [data-model.md](../data-model.md) "MissionArtifactKind → MissionArtifactHome". Research D-01, D-05.
- **C-002 boundary**: this is an *extension* of the existing port kind-mapping, NOT a `MissionArtifactHome`/topology re-architecture. Do not touch topology resolution.
- **Layering (folded squad finding)**: `mission_runtime` already imports `specify_cli` (top-level + ~40 late). **Add NO new top-level `specify_cli` import** to `artifacts.py`.
- **Cross-WP coordination (resolution.py:949)**: the sole `commit_target` consumer lives at `resolution.py:949`, which is owned by **WP07** (the read-authority WP). Your job here is the *audit* (T005): grep-confirm no consumer reads `commit_target is None` as "skip commit". If the flip requires a consumer change, that change is made in WP07 (which lands after this WP transitively via the gate) — record the finding in `tracers/design-decisions.md` and hand it to WP07. Do NOT edit `resolution.py`.

## Branch Strategy

- **Strategy**: generated on `feat/coord-write-placement-closure`; changes merge back into `feat/coord-write-placement-closure`.
- **Planning base branch**: `feat/coord-write-placement-closure`
- **Merge target branch**: `feat/coord-write-placement-closure`

## Subtasks & Detailed Guidance

### Subtask T005 – Audit the `commit_target is None` sentinel consumers (RED-safety first)

- **Purpose**: FR-002 risk (a) — before flipping the sentinel, prove no consumer treats `None` as "skip commit".
- **Steps**: `grep -rn "commit_target" src/` and inspect every read site, especially `resolution.py:949`. Confirm the sentinel is inert today (the plan's grep says so — verify on this branch). Record the audit result in `tracers/design-decisions.md` (mission dir, not owned_files). If a consumer DOES branch on `None`, stop and hand the required consumer edit to WP07 with the exact site.
- **CONFIRMED-INERT (post-tasks squad evidence — record this verdict in the tracer)**: the audit is **CONFIRMED INERT**. Only `resolution.py:949` reads the *port* `home.commit_target`; the `tasks_map_requirements.py` `commit_target` hits are a **different** `MergeState.commit_target` (not the placement port). Because the sole port consumer at `:949` does not branch on `None`-as-skip, WP07's T033 `:949` adjustment is therefore **cosmetic** (an inertness-asserting regression, not a behavioral change). This is precisely why **no WP09→WP07 dependency is added** (avoids needless serialization).
- **Fallback line (record in tracer)**: IF a future change makes the sentinel **non-inert** (a real consumer starts branching on `None`), promote WP09→WP07 so the birth-cutover write cannot race the consumer adjustment.
- **Files**: read-only + tracer note.
- **Validation**: written audit with the enumerated consumer sites + the CONFIRMED-INERT verdict + the fallback line.

### Subtask T006 – Flip `PRIMARY_METADATA.commit_target` to partition-aware

- **Purpose**: FR-002 — route meta writes through the port.
- **Steps**: At `artifacts.py:218-224`, delete the `PRIMARY_METADATA` special-case arm (`commit_target=None`) so it resolves through the same generic PRIMARY arm as other primary kinds, yielding `commit_target=placement_ref`. Keep the change surgical — one arm removed, not a mapping rewrite.
- **Files**: `src/mission_runtime/artifacts.py`.
- **Validation**: `PRIMARY_METADATA` now resolves a non-None `commit_target`; existing `resolve_placement_only(PRIMARY_METADATA)` callers get a routed target.
- **Edge cases**: ensure the generic arm actually covers `PRIMARY_METADATA`'s partition (PRIMARY) — do not accidentally route meta to COORD.

### Subtask T007 – Classify `decisions.events.jsonl` in the basename SSOT

- **Purpose**: FR-003 — `decisions.events.jsonl` must resolve to COORD via the classifier.
- **Steps**: Add `decisions.events.jsonl` to `_MISSION_FILE_KIND_BY_BASENAME:181` mapping to its COORD-homed kind. Do NOT classify at any writer site — writers (WP03) call `kind_for_mission_file`.
- **Files**: `src/mission_runtime/artifacts.py`.
- **Validation**: `kind_for_mission_file("decisions.events.jsonl")` returns the COORD-homed kind.

### Subtask T008 – Classify `traces/` in the residue-dirs SSOT

- **Purpose**: FR-006 — `traces/` classified to COORD.
- **Steps**: Add `traces/` to `_COORD_RESIDUE_DIRS:207` (or the correct residue-dir SSOT) so `traces/` resolves COORD. Note in the tracer that this is a PRIMARY→COORD reclassification that may move existing writes (WP03 routes the writers).
- **Files**: `src/mission_runtime/artifacts.py`.
- **Validation**: a `traces/…` path classifies to COORD via the classifier.
- **Edge cases**: confirm no other classifier already homes `traces/` to PRIMARY (avoid a double-home that breaks disjointness).

### Subtask T009 – Pin the mapping + partition invariant (red-first unit test)

- **Purpose**: lock the SSOT so a future edit that breaks exhaustiveness/disjointness reds. **Red-first (DIRECTIVE_041)**: these assertions must be authored to fail on the *pre-edit* classifier and pass only after T006–T008 land — not green-on-arrival.
- **Steps**: Write `tests/mission_runtime/test_artifact_partition_mapping.py` asserting: (a) `PRIMARY_METADATA` resolves a non-None PRIMARY `commit_target`; (b) `decisions.events.jsonl` → COORD; (c) `traces/` → COORD; (d) `assert_partition_invariant()` passes (exhaustive + disjoint). Use behavioral assertions on the resolver, not literal dict snapshots that break on unrelated additions. **Author the test BEFORE the T006–T008 edits and confirm it reds**: pre-edit, `traces/` and `decisions.events.jsonl` resolve to their stale/`None`/PRIMARY home and `PRIMARY_METADATA.commit_target` is `None`, so assertions (a)–(c) fail; they go green only after the SSOT edits.
- **Files**: `tests/mission_runtime/test_artifact_partition_mapping.py` (new).
- **Validation**: red on the pre-edit classifier (asserting the target COORD/PRIMARY partitions before the edit); green after T006–T008; deleting any classification re-reds.

### Subtask T054 – Behavioral proof: `write_meta` lands meta on the PRIMARY surface via the port

- **Purpose**: FR-002 behavioral closure — the flipped sentinel must be proven to *route a real meta write* to the PRIMARY surface here at the foundation, NOT first observed at WP09's birth-cutover seam (where a regression would surface far too late).
- **Steps**: In the same `tests/mission_runtime/test_artifact_partition_mapping.py`, add a small behavioral test that drives `write_meta` (or the nearest real meta-write entry point that consumes `PRIMARY_METADATA`) against a coord-topology fixture and asserts `meta.json` lands on the resolved **PRIMARY** surface via the port (non-None routed `commit_target`), not an ambient `feature_dir`. Keep it a behavioral assertion on the resolved surface, not a dict snapshot.
- **Files**: `tests/mission_runtime/test_artifact_partition_mapping.py` (extend).
- **Validation**: `write_meta` routes meta to PRIMARY via the port; forcing the old `commit_target=None` arm makes it red.

## Test Strategy

- New: `tests/mission_runtime/test_artifact_partition_mapping.py`.
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/mission_runtime/test_artifact_partition_mapping.py -q` plus the existing `mission_runtime` partition tests to confirm no regression.

## Definition of Done

- `PRIMARY_METADATA.commit_target` flipped; sentinel audit recorded.
- `decisions.events.jsonl` + `traces/` classified COORD in the two SSOT dicts only.
- `assert_partition_invariant()` exhaustive + disjoint.
- FR-002 behavioral proof present (T054): `write_meta` routes meta to the PRIMARY surface via the port — validated here, not deferred to WP09.
- No new top-level `specify_cli` import in `artifacts.py`.
- `ruff` + `mypy` clean.

## Risks & Mitigations

- **Sentinel not inert** → T005 audit gates the flip; hand consumer edit to WP07.
- **traces/ double-home** → T008 disjointness check + T009 invariant assertion.
- **Scope creep into topology** → keep to the two dicts + one arm (C-002).

## Review Guidance

- Verify classification lands ONLY in the two SSOT dicts, never at writer sites.
- Verify the sentinel audit is recorded and the consumer at `resolution.py:949` was handed to WP07 if non-inert.
- Verify no new top-level `specify_cli` import.

## Activity Log

- 2026-07-25T12:00:00Z – system – Prompt created.
