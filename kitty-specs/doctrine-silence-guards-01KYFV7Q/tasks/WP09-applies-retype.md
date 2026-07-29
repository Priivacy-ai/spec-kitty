---
work_package_id: WP09
title: '`applies` retype and relation gate'
dependencies:
- WP08
requirement_refs:
- FR-012
- NFR-002
planning_base_branch: remediation/doctrine-silence-guards
merge_target_branch: remediation/doctrine-silence-guards
branch_strategy: Planning artifacts for this mission were generated on remediation/doctrine-silence-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/doctrine-silence-guards unless the human explicitly redirects the landing branch.
subtasks:
- T046
- T047
- T048
- T049
phase: Phase 3 - Guidance
history:
- at: '2026-07-26T19:45:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/agent_profiles/built-in/doctrine-daphne.agent.yaml
create_intent:
- tests/architectural/test_no_authored_applies_edge.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/agent_profiles/built-in/doctrine-daphne.agent.yaml
- src/doctrine/agent_profile.graph.yaml
- tests/architectural/test_no_authored_applies_edge.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP09 – `applies` retype and relation gate

## ⚡ Do This First: Load Agent Profile

Load the `doctrine-daphne` profile via `/ad-hoc-profile-load` and behave according to its guidance before parsing the rest of this prompt.

---

## Objectives & Success Criteria

- `procedure:onboard-external-agent-to-pack` has a traversable inbound edge.
- A newly-authored `applies` edge fails a gate.

**Requirement refs**: FR-012, NFR-002, SC-010

## Context & Constraints

Exactly one `applies` edge exists: `agent_profile:doctrine-daphne --applies--> procedure:onboard-external-agent-to-pack`. It is that procedure's **only** inbound edge, which makes daphne's own operating procedure unreachable.

This is the **one** WP in the mission that changes a graph relation — the single ledgered exception to NFR-004.

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

### Subtask T046 – Failing-first test.

The procedure is currently unreachable. Prove it.

### Subtask T047 – Retype the edge.

To a relation traversal actually reads.

### Subtask T048 – Gate the relation.

No newly-authored `applies` edge. **Build it on measurement, not on the wrong comment at `drg/merge.py:97-98`.**

### Subtask T049 – Ledger the change.

Golden counts: cardinality unchanged, relation changed. Record the entry.

## Test Strategy

- `PYTHONPATH=src python -m pytest tests/architectural/test_no_authored_applies_edge.py -q`
- Graph check: 311 nodes / 774 edges, with the relation histogram change ledgered.

## Risks & Mitigations

- Retyping changes a live traversal result — that is the point, but it must be ledgered, not slipped in.
- The `applies` relation is still produced by `project_drg.py`; the gate targets **newly-authored** edges, not the relation's existence.

## Review Guidance

- Verify red→green: the WP's first commit was RED on `remediation/doctrine-silence-guards` and is GREEN at the final commit.
- Verify every gate added is **non-vacuous**: it must reject a planted violation, and its allowlist must be empty.
- Verify the graph invariant where the WP claims it (311 nodes / 774 edges).

## Activity Log

> **CRITICAL**: entries in chronological order, oldest first. **Append** new entries at the END.

- 2026-07-26T19:45:15Z – system – Prompt created.
- 2026-07-27T02:00:00Z – claude – **Implemented; moved to `for_review`.** Commits `98203999f` (ATDD red, 7 failed / 12 passed) → `a82ad8222` (green, 19 passed). The retype: the sole inbound edge to `procedure:onboard-external-agent-to-pack` was typed `applies`, which no activation traversal follows. Measured consequence — `cascade_activation_targets(graph, "agent_profile:doctrine-daphne", CascadeScope.all())` pulled 17 directives, 39 tactics, 5 procedures, 5 styleguides, 6 templates, 3 toolguides and a paradigm, and **not** the one procedure the profile's own initialization declaration says it runs. Now reached. Graph invariant held at 311 nodes / 774 edges / 32 orphans; `applies` 1 → 0, `requires` 259 → 260.
- 2026-07-27T02:00:01Z – claude – **Gate non-vacuity proven against production surfaces, not tmp fixtures.** Three mutations, each restored: (a) shipped fragment back to `relation: applies` → fragment check RED; (b) curated table back to `Relation.APPLIES` **while leaving the fragment at `requires`** → generator check RED while the fragment check stayed GREEN, which is the proof the second surface is not redundant; (c) a `requires` description made to claim zero edges → absence-claim check RED. `_ALLOWLIST` is `frozenset()` and asserted empty. A scanner floor separates "compliant tree" from "broken parser".
- 2026-07-27T02:00:02Z – claude – **Scope note on the gate.** The comment at `drg/merge.py:97-98` claims "no traversal reads `APPLIES`"; measured, that is **false** — the orphan lint's `directive` rule reads it and `project_drg.py` emits it. Neither touched this edge (its target is a procedure). The gate therefore enforces the narrow true property — *no `applies` edge is **authored** into the shipped tree* — rather than the broader claim in that comment.
- 2026-07-27T02:00:03Z – claude – **Corrected three false claims in `RELATION_DESCRIPTIONS`, one self-contradictory.** `requires` claimed to be "the emission-heaviest relation (255 edges)" while `suggests` **also** claimed most-emitted; measured 260 vs 332, so `suggests` was right and `requires` is now "second-most-emitted (260 edges)". `suggests` 330 → 332. `applies` no longer claims an edge that no longer exists. `docs/architecture/doctrine-relationships.md` regenerated from the registry for exact-text parity. Nothing checked these counts before; `TestAbsenceClaimsAreTrue` closes the class per C-004 rather than handing it to a follow-up.
- 2026-07-27T02:00:04Z – claude – **Ownership crossings, flagged not hidden.** Beyond its three `owned_files`: `src/doctrine/drg/migration/extractor.py` and `src/doctrine/drg/models.py` (both WP04's, approved, no concurrent lane), plus unowned `tests/doctrine/drg/migration/test_extractor_projection.py` and `docs/architecture/doctrine-relationships.md`. The extractor edit is unavoidable — the fragment is generated from it and `test_shipped_graph_is_fresh_and_byte_identical` compares `(source, target, relation)` triples, so editing only the fragment would red. Regenerated via `spec-kitty doctrine regenerate-graph`; the fragment was never hand-edited.
- 2026-07-27T02:00:05Z – claude – **Ledger entry (5)** added to the composition ledger in `test_extractor_projection.py`: a relation-only change at constant cardinality, the mission's single ledgered NFR-004 exception. The counts beneath it are deliberately unchanged, which is exactly why the entry is needed — a cardinality baseline **cannot see a relation change**, so a live traversal result moved while every golden count stayed green.
- 2026-07-27T02:00:06Z – claude – **Found and deliberately not fixed → [#2994](https://github.com/Priivacy-ai/spec-kitty/issues/2994).** `collaboration.operating-procedures` mints no DRG edge: **16** built-in profiles declare one and exactly **1** edge exists — the one retyped here. Independently reproduced. So before this WP, 16 of 16 declarations were unreachable: fifteen had no edge, and the sixteenth had one no traversal follows. Wiring the fifteen would mint fifteen edges, an NFR-004 violation in the mission's final WP requiring per-profile correctness review rather than a bulk mint. The trap is recorded in `doctrine-daphne`'s `secondary-awareness` ("treat a named operating procedure as unwired until the edge is confirmed") so the next authoring pass cannot miss it.
- 2026-07-27T02:00:07Z – claude – **Also not fixed, with reasons.** Positive edge counts in `RELATION_DESCRIPTIONS` remain ungated — the absence claim is one sentence shared by six entries (now gated), while the positive counts use five different phrasings and gating them needs cross-registry normalisation; all three drifted numbers were corrected so nothing is knowingly false today. `_orphan_urns` counts incidence rather than traversability — which is precisely why this defect survived — but changing that definition would move a golden count mission-wide.
- 2026-07-27T02:00:08Z – claude – **Verification.** 19 passed on the new gate; 2970 across `tests/doctrine/` + `tests/charter/test_cascade.py`; 1703 passed / 4 skipped across charter + charter_runtime + regenerate-graph; `doctor doctrine --json` healthy, 18/18 profiles, 0 errors; ruff + `mypy --strict` clean on every changed module with zero suppressions. Pre-review gate reported `unverified_baseline` — the known open gate defect, no evidentiary weight.
