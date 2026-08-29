---
work_package_id: WP08
title: org→DRG bridge integrity
dependencies:
- WP04
requirement_refs:
- FR-010
- FR-011
planning_base_branch: remediation/doctrine-silence-guards
merge_target_branch: remediation/doctrine-silence-guards
branch_strategy: Planning artifacts for this mission were generated on remediation/doctrine-silence-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/doctrine-silence-guards unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
- T044
- T045
phase: Phase 2 - Boundaries
history:
- at: '2026-07-26T19:45:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: src/doctrine/drg/merge.py
create_intent:
- tests/doctrine/drg/test_org_drg_bridge.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/merge.py
- src/doctrine/drg/org_pack_loader.py
- CLAUDE.md
- tests/doctrine/drg/test_org_drg_bridge.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 – org→DRG bridge integrity

## ⚡ Do This First: Load Agent Profile

Load the `architect-alphonso` profile via `/ad-hoc-profile-load` and behave according to its guidance before parsing the rest of this prompt.

---

## Objectives & Success Criteria

- An unresolvable cross-layer edge fails loudly with a conflict record, never `None`-with-silence.
- The documented `specializes_from` snippet produces an edge.

**Requirement refs**: FR-010, FR-011, SC-009

## Context & Constraints

ADR `2026-07-26-3` is explicit: **the bridge fix must land before or with the `Relation.IMPACTS` migration**, or the new relation inherits a silent-drop path.

Three measured defects: a built-in-source → pack-target edge returns `None` with no warning and no conflict record; a bare built-in target id is blindly re-kinded to a node that may not exist; a URN-shaped target dies with a raw pydantic error instead of a typed pack error.

**Binding, every WP in this mission:**

- **Never run the full `tests/architectural/` directory** (C-003) — a known harness issue kills the session. Targeted single-file runs only.
- The 6 inherited `arch-adversarial` reds stay red (C-004). No greenwashing, no retry-to-green.
- **ATDD (C-006)**: the failing test is the **first commit** of this WP, RED on the planning base and GREEN at the final commit.
- New code passes `ruff` and `mypy --strict` with zero issues. No `# noqa` / `# type: ignore` to get there.
- Charter: `.kittify/charter/charter.md`. Spec: `../spec.md`. Plan: `../plan.md`. Manifest: `../tasks.md`.

## Branch Strategy

- **Planning base branch**: `remediation/doctrine-silence-guards`
- **Merge target branch**: `remediation/doctrine-silence-guards` → draft PR to `main`; the operator merges.

## Subtasks & Detailed Guidance

### Subtask T041 – Failing-first test.

A built-in-source → pack-target edge currently returns `None` silently. Prove it.

### Subtask T042 – Emit a conflict record.

Instead of `None`. The pack author must see the drop.

### Subtask T043 – Stop blind re-kinding.

A bare built-in target id must not be re-kinded to a node that may not exist.

### Subtask T044 – Typed pack error on URN-shaped targets.

Not raw pydantic.

### Subtask T045 – Fix the documented example (FR-011).

The `urn:profile:` `specializes_from` snippet in `CLAUDE.md` is silently dropped today — documentation that yields an inert declaration.

## Test Strategy

- `PYTHONPATH=src python -m pytest tests/doctrine/drg/ -q`

## Risks & Mitigations

- **`applies` is not a dead sink** — the comment at `drg/merge.py:97-98` is **wrong**. `charter_runtime/lint/checks/orphan.py` reads it and `charter/synthesizer/project_drg.py` produces it. Do not build anything on that comment (WP09 depends on this).
- Making previously-silent drops loud may surface existing broken pack edges. Each is a finding, not a reason to soften the error.

## Review Guidance

- Verify red→green: the WP's first commit was RED on `remediation/doctrine-silence-guards` and is GREEN at the final commit.
- Verify every gate added is **non-vacuous**: it must reject a planted violation, and its allowlist must be empty.
- Verify the graph invariant where the WP claims it (311 nodes / 774 edges).

## Activity Log

> **CRITICAL**: entries in chronological order, oldest first. **Append** new entries at the END.

- 2026-07-26T19:45:15Z – system – Prompt created.
- 2026-07-27T00:00:00Z – claude – **Implemented; moved to `for_review`.** **Four of five behind one endpoint policy, plus a second root cause on the node-minting side** — the earlier "one root cause, not five bugs" framing overstated it. D1/D2/D3/D5 share one fix (`_resolve_edge_endpoint`); D4 is a hand-restated *node*-kind map fixed by a different mechanism in a different module (`_derive_plural_to_singular`), and the node-side `malformed_urn` return is a third. The code was always correctly structured as two fixes in two modules; only the description overreached. The shared root cause: `merge.py` ran two asymmetric endpoint policies (source had to be fragment-local, miss → silently dropped; target fell back to `directive:<id>`, miss → invented kind), and neither accepted the URN form the pack's own emitter produces. Replaced by one ordered precedence in `_resolve_edge_endpoint`: fragment-local bare id → fully-qualified URN → bare id against the built-in layer recovering the *declared* kind → typed `OrgDRGConflict` hard fail.
- 2026-07-27T00:00:01Z – claude – **Measured before → after.** Built-in-source → pack-target edge: silently dropped (0 warnings, 0 conflicts) → resolved or typed conflict. Bare target naming a styleguide: phantom `directive:<id>` → `styleguide:<id>`. URN-shaped target: raw `pydantic_core.ValidationError` → forwarded verbatim. Org-pack plural kinds that mint a URN: **10 of 12 → 12 of 12**. Field-projection auto-emitted edges landing: **0% → 100%**.
- 2026-07-27T00:00:02Z – claude – **Two defects found beyond the spec's three** (FR-010 amended in `spec.md`, with a "Implementation findings that widened the spec" section). D4: `_PLURAL_TO_SINGULAR` was a fourth hand-restated writer, drifted two kinds behind — the in-repo `augment-all-kinds-pack` fixture could not be merged at all. D5: `_collect_augmentation_edges` emits `<kind>:<id>` while the source lookup keyed on bare ids, so 100% of the field-projection producer's output was discarded — FR-001's defect class inverted (a producer with no consumer).
- 2026-07-27T00:00:03Z – claude – **Hazard introduced and closed within the WP.** The first cut passed the running merge state as the bare-id index, making resolution depend on operator `organisation_packs:` ordering — same two packs, two orders, two graphs, nothing reported. Rule 3 now reads the built-in URN set only; pinned by `test_bare_resolution_does_not_depend_on_pack_declaration_order` (`968d4606c`).
- 2026-07-27T00:00:04Z – claude – **Design decision (tracer).** Cross-pack references must be fully qualified; bare ids resolve against the fragment and the built-in layer only, never the running merge state. Existence is deliberately not required for the qualified form — dangling detection belongs to the DRG validator; the bridge owes only that it never invents a kind and never drops in silence.
- 2026-07-27T00:00:05Z – claude – **Collateral.** `tests/architectural/_fixtures/org_packs/example_org/drg/fragment.yaml` referenced the styleguide `caveman-comments` by bare id and had been emitting phantom `directive:caveman-comments` for its entire life; qualified. `test_org_to_shipped_edge_targets_synthesized_urn` pinned that invented kind in its own name; re-pinned to the qualified form with a negative half asserting the bare id now hard-fails.
- 2026-07-27T00:00:06Z – claude – **Ownership crossing, flagged not hidden:** `src/doctrine/drg/models.py` is WP04's `owned_files`. The change is additive (`is_valid_urn`, 16 lines) and WP04 is approved, so no concurrent lane — recorded here rather than discovered at merge.
- 2026-07-27T00:00:07Z – claude – **Not fixed, filed instead:** `src/charter/activation/activations.py:194` `_PLURAL_TO_SINGULAR_KIND` and `src/charter/activation/_activation_render.py:270` `_singular_kind` are a fifth and sixth restatement of the same plural↔singular mapping (the latter's comment says it is "kept local to avoid leaking a private symbol"). Charter layer, outside this WP's surface; `ORG_PLURAL_TO_SINGULAR_KIND` is now the canonical target they should consume.
- 2026-07-27T00:00:08Z – claude – **Reds:** `test_a_baseline_entry_does_not_survive_its_owner` is the known cross-lane artefact (WP05's deletions live on lane-e), left red. Pre-review gate reported `unverified_baseline — baseline uncomputable`, a sibling of the known `no_coverage` gate defect; noted, not fixed. Otherwise 4601 passed / 4 skipped across `tests/doctrine` + `tests/charter`. `ruff` and `mypy --strict` clean on `src/doctrine/drg/`, zero suppressions.
