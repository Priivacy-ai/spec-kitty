---
work_package_id: WP03
title: Retire opposed_by / Contradiction
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-014
- NFR-002
planning_base_branch: doctrine/drg-missing-links-analysis
merge_target_branch: doctrine/drg-missing-links-analysis
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-missing-links-analysis. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-missing-links-analysis unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 1 - Foundation
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "17804"
shell_pid_created_at: "1784647538.174858"
history:
- at: '2026-07-21T11:08:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/migration/extractor.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/migration/extractor.py
- src/doctrine/directives/built-in/024-locality-of-change.directive.yaml
- src/doctrine/directives/built-in/025-boy-scout-rule.directive.yaml
- src/doctrine/tactics/built-in/change-apply-smallest-viable-diff.tactic.yaml
- src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml
- src/doctrine/paradigms/built-in/c4-incremental-detail-modeling.paradigm.yaml
- src/doctrine/paradigms/built-in/domain-driven-design.paradigm.yaml
- src/doctrine/schemas/directive.schema.yaml
- src/doctrine/schemas/paradigm.schema.yaml
- src/doctrine/schemas/tactic.schema.yaml
- src/doctrine/directives/models.py
- src/doctrine/tactics/models.py
- src/doctrine/paradigms/models.py
- src/doctrine/shared/models.py
- tests/doctrine/drg/migration/test_extractor.py
- tests/doctrine/test_directive_consistency.py
- tests/doctrine/fixtures/paradigm/valid/with-tactic-refs.yaml
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Retire opposed_by / Contradiction

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: src/doctrine/drg/migration/extractor.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review. Address all feedback; update the Activity Log as you go.

---

## ⚠️ BULK-EDIT GOVERNED WORK PACKAGE

This mission runs under `change_mode: bulk_edit` (Constraint C-007). Your diff will be checked at review time against `kitty-specs/doctrine-tension-edges-01KY1WPC/occurrence_map.yaml`. **Read that file before starting.** Its target is `opposed_by`, operation `remove`. Key rules from it that apply directly to this WP:

- `code_symbols` / `serialized_keys`: `manual_review` — every removal here is paired with content that moved to an edge WP02 already authored, not a mechanical delete.
- The `Contradiction` model removal (`src/doctrine/shared/models.py`) has an explicit exception entry — it has no literal `opposed_by` occurrence but is in scope.
- The unrelated `ContradictionChecker` (`src/specify_cli/charter_runtime/lint/checks/contradiction.py` and its importers/tests) has an explicit `do_not_change` exception — **do not touch it**, even though it shares the word "Contradiction." This is not in your `owned_files` list and should not be.

## Objectives & Success Criteria

Remove `opposed_by` (field, schema property, `contradiction` definition) and the `Contradiction` model, in Constraint C-006's mandated order, without losing the edges WP02 already authored.

Done means:
- `grep -rn "opposed_by" src/ docs/ tests/` returns **zero** hits.
- `doctrine.shared.models.Contradiction` and its `__all__` entry are gone.
- The dead-symbol gate (scoped to the `Contradiction` symbol specifically, per NFR-002) is green.
- The regenerated `*.graph.yaml` fragments no longer contain the mis-minted 024↔025 `replaces` cycle, AND still contain every edge/node WP02 authored.
- `ruff`/`mypy` zero issues; full `tests/doctrine/` suite green.

## Context & Constraints

- **C-006 order (do not reorder)**: (1) stop the extractor minting from `opposed_by` AND remove `opposed_by:` from the built-in YAML *together* (T013+T014) — dropping the YAML first without disabling the extractor block is harmless (extractor just finds nothing to convert), but disabling the extractor block first while YAML still has `opposed_by:` would silently orphan that content; (2) drop the schema property (T015); (3) drop the field + `Contradiction` model + imports (T016). Authoring an edge before its enum member, or dropping the schema property before the YAML, are the specific red states C-006 names — you're past the first risk (WP01/WP02 already landed); avoid the second by keeping this order.
- **This WP depends on WP02.** WP02's hand-authored `in_tension_with`/`reconciles_tension`/`rejects` edges must already exist in the graph fragments before you touch anything here — if WP02 is not yet merged, stop and escalate rather than proceeding on an incomplete foundation.
- Read `spec.md`'s Change Surface Map (Write row) and NFR-002 before starting.

## Branch Strategy

- **Strategy**: single_branch — no coordination/lanes topology; planning and merge-target branch are the same branch.
- **Planning base branch**: `doctrine/drg-missing-links-analysis`
- **Merge target branch**: `doctrine/drg-missing-links-analysis`

Implementation command: `spec-kitty agent action implement WP03 --agent <name>` (depends on WP02).

## Subtasks & Detailed Guidance

### Subtask T013 – Remove the `opposed_by`-minting extractor block

- **Purpose**: Stop generating the mis-encoded `replaces` cycle at the source.
- **Steps**:
  1. In `src/doctrine/drg/migration/extractor.py`, locate the `# opposed_by` block (reads `data.get("opposed_by", [])`, resolves `opp_kind`, calls `_ensure_node` + `_add_edge(... relation=Relation.REPLACES ...)`).
  2. Delete that block entirely (it appears at least once for directives — check whether tactics/paradigms have their own near-identical block each, given each has its own `opposed_by` field, and remove all instances).
- **Files**: `src/doctrine/drg/migration/extractor.py`
- **Parallel?**: No — do this alongside T014, before T015/T016.
- **Notes**: Do not leave a dead `_kind_for_type`/`artifact_to_urn` call orphaned if it was only used by this block — check for now-unused helpers, but do not remove a helper still used elsewhere.

### Subtask T014 – Remove `opposed_by:` from the 5 built-in YAML sources

- **Purpose**: The source-of-truth removal — once this is gone, nothing feeds the (now-deleted) extractor block anyway.
- **Steps**: Remove the `opposed_by:` block from each of:
  1. `src/doctrine/directives/built-in/024-locality-of-change.directive.yaml`
  2. `src/doctrine/directives/built-in/025-boy-scout-rule.directive.yaml`
  3. `src/doctrine/tactics/built-in/change-apply-smallest-viable-diff.tactic.yaml`
  4. `src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml`
  5. `src/doctrine/paradigms/built-in/c4-incremental-detail-modeling.paradigm.yaml`
  6. `src/doctrine/paradigms/built-in/domain-driven-design.paradigm.yaml`
     (6 files — the tactic file has one `opposed_by` entry, the 2 directives have one each, the 3 paradigms carry the 8 anti-pattern rejection entries between them.)
- **Files**: the 6 files above
- **Parallel?**: Yes, relative to T013 (different files) and to each other.
- **Notes**: Before deleting, cross-check each entry against WP02's Activity Log (which documents exactly what edges/nodes were authored) — confirm every `opposed_by` entry you're deleting has a corresponding edge WP02 already created. If you find one that doesn't, stop and flag it rather than deleting silently — that would be a genuine content loss, not a mechanical cleanup.

### Subtask T015 – Remove the schema property + `contradiction` definition

- **Purpose**: `additionalProperties: false` schemas must stop accepting `opposed_by` once nothing consumes it, or authored-but-ignored content becomes a silent trap for pack authors.
- **Steps**: In each of `src/doctrine/schemas/directive.schema.yaml`, `paradigm.schema.yaml`, `tactic.schema.yaml`: remove the `opposed_by` property from the schema's `properties:` block, and remove the shared `contradiction` `$defs`/definition block if present (check whether it's defined once and referenced, or duplicated per file).
- **Files**: the 3 schema files above
- **Parallel?**: Yes, relative to each other; sequential after T013/T014 per C-006.
- **Notes**: This is the step FR-015's downstream migration tool (WP07) exists to soften the blow of — after this lands, any downstream org-pack YAML still authoring `opposed_by` will fail schema validation. That's expected; WP07 is the escape hatch, not this WP's job to build.

### Subtask T016 – Remove the field + `Contradiction` model

- **Purpose**: Complete the code-model side of the removal.
- **Steps**:
  1. Remove `opposed_by: list[Contradiction] = Field(default_factory=list)` from `src/doctrine/directives/models.py`, `src/doctrine/tactics/models.py`, `src/doctrine/paradigms/models.py`.
  2. Remove the corresponding `from doctrine.shared.models import Contradiction` import from each of those 3 files.
  3. Remove the `Contradiction` class + its `__all__ = ["Contradiction"]` entry from `src/doctrine/shared/models.py`.
- **Files**: the 4 files above
- **Parallel?**: No — do after T015.
- **Notes**: `src/doctrine/shared/models.py` has **no literal `opposed_by` occurrence** — it only defines `Contradiction`. It is in scope per the occurrence_map.yaml exception, not because it matched a grep.

### Subtask T017 – Remove/repoint the opposed_by-specific tests

- **Purpose**: Tests asserting behavior that no longer exists must be removed or repointed to assert the new behavior — never left vacuously green.
- **Steps**:
  1. In `tests/doctrine/drg/migration/test_extractor.py`: remove `test_directive_opposed_by_produces_replaces` (around line 183 as of plan time — confirm the current line number, it may have shifted). Do NOT touch the freshness-canary tests in this same file (`test_shipped_graph_yaml_is_fresh` etc.) except as needed in T018.
  2. In `tests/doctrine/test_directive_consistency.py`: remove/repoint the 3 opposed_by tests (around lines 349/376/403 as of plan time — confirm current line numbers).
  3. Update `tests/doctrine/fixtures/paradigm/valid/with-tactic-refs.yaml` to drop any `opposed_by` content it carries, replacing with the new-edge equivalent if the fixture's purpose requires it.
- **Files**: the 3 files above
- **Parallel?**: Yes, relative to each other.
- **Notes**: "Repoint" (not just delete) where the test's underlying intent still matters — e.g. if a test asserted "opposed_by produces a replaces edge," consider whether an equivalent assertion about "in_tension_with produces a queryable, non-replaces edge" belongs here or is already covered by WP05's tests. Don't duplicate WP05's coverage; do make sure nothing silently loses coverage.

### Subtask T018 – Regenerate `*.graph.yaml`; reconcile the freshness canary

- **Purpose**: The committed graph fragments must reflect both removals (T013-T016) and additions (WP02) — this is the one place this WP legitimately touches WP02's files, per the out-of-map note in tasks.md.
- **Steps**:
  1. Run the extractor regeneration process (however it's invoked — check `src/doctrine/drg/migration/extractor.py`'s module docstring or an existing CLI command like `spec-kitty doctrine regenerate-graph` for the actual entry point) against the now-`opposed_by`-free built-in YAML.
  2. Confirm the regenerated output drops the old 024↔025 `replaces` cycle and every other `opposed_by`-derived edge.
  3. Confirm WP02's hand-authored `in_tension_with`/`reconciles_tension`/`rejects` edges and the 6 anti-pattern nodes are still present after regeneration — if the regeneration process overwrites the whole file, you will need to re-apply WP02's hand-authored content on top, or adjust the freshness-canary comparison to treat WP02's edges as an expected addendum rather than drift. Read `test_shipped_graph_yaml_is_fresh`/`test_shipped_graph_is_fresh_and_byte_identical`/`test_shipped_graph_is_fresh` (three separate tests across `test_extractor.py`, `test_path_ref_resolver.py`, `test_extractor_projection.py`) to understand exactly what "fresh" currently means before changing it.
  4. Adjust the freshness-canary comparison logic (not its intent — it must still catch genuine drift) so it accounts for the specific, enumerable set of hand-authored edges/nodes from WP02, rather than disabling the check.
- **Files**: `src/doctrine/*.graph.yaml` (out-of-map, WP02's files — small, justified touch, rationale: dropping stale extractor-derived content while preserving hand-authored additions), plus whichever of the three freshness-canary test files needs its comparison logic updated
- **Parallel?**: No — last step, needs T013-T017 done first.
- **Notes**: This is explicitly flagged as the mission's hardest risk (plan.md IC-02's risk note). Take the time to actually read all three freshness-canary tests rather than patching the first one you find and assuming the other two are equivalent.

## Test Strategy

- Run the full `tests/doctrine/` suite: `.venv/bin/pytest tests/doctrine/ -q`.
- Confirm `grep -rn "opposed_by" src/ docs/ tests/` is empty.
- Run the dead-symbol gate (whatever command/test enforces it — check for a `test_dead_symbols` or similar in `tests/architectural/`) and confirm it's scoped to the `Contradiction` symbol, not a bare word match (it must NOT flag `ContradictionChecker`).
- `.venv/bin/ruff check` + `.venv/bin/mypy` on every file in `owned_files`.

## Risks & Mitigations

- **Risk** (highest in this mission): T018's graph regeneration silently drops WP02's hand-authored content, and no test catches it because the freshness canary was "fixed" by weakening it rather than teaching it about the new edges. **Mitigation**: after T018, explicitly re-verify (by reading the regenerated YAML, not just running tests) that all of WP02's specific edges/nodes are present.
- **Risk**: The dead-symbol gate false-positives on the unrelated `ContradictionChecker`. **Mitigation**: confirm the gate is symbol-scoped (module+class path), not a grep for the word "Contradiction," before relying on it.

## Review Guidance

- Confirm zero `opposed_by` occurrences and a green, correctly-scoped dead-symbol gate.
- Confirm the regenerated graph fragments contain WP02's edges — ask the implementer to show the specific diff lines proving this, don't just trust "tests pass."
- Confirm `src/specify_cli/charter_runtime/lint/checks/contradiction.py` and its importers/tests were not touched (occurrence_map.yaml exception).
- This WP's diff will be checked against `occurrence_map.yaml` at review time — verify no file outside the map's categories/exceptions was touched.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-07-21T11:08:12Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP03 --to <status>` to change WP status.
- 2026-07-21T14:29:00Z – claude:sonnet:python-pedro:implementer – shell_pid=93463 – Assigned agent via action command
- 2026-07-21T15:19:50Z – claude:sonnet:python-pedro:implementer – shell_pid=93463 – Ready for review
- 2026-07-21T15:25:43Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=17804 – Started review via action command
- 2026-07-21T15:34:44Z – user – shell_pid=17804 – Review passed: verified opposed_by/Contradiction fully retired (zero grep hits outside exempted historical docs), hand_authored_overlay.py registry (6 nodes/13 edges) matches WP02 commit a576d713e verbatim, both production bug fixes (DRGNode.tags emission + regenerate-graph --check/write overlay wiring) confirmed correct in code, ContradictionChecker untouched, f09f128c5 golden-set fix verified accurate and non-loosened. Added occurrence_map.yaml exception for doctrine.py's legitimate regenerate-graph touch (bulk-edit gate now clean, only justified manual_review flags). Full tests/doctrine/ suite: 2749 passed/0 failed. ruff+mypy clean. Dead-symbol gate: 25/26 passed, the 1 failure (SYNC_DISABLE_ENV_VARS) is confirmed pre-existing baseline red with zero diff overlap with this mission.
