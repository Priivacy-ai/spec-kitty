---
work_package_id: WP07
title: Followable guidance + discriminating gates
dependencies:
- WP01
- WP04
requirement_refs:
- FR-008
- FR-009
- NFR-003
planning_base_branch: remediation/doctrine-silence-guards
merge_target_branch: remediation/doctrine-silence-guards
branch_strategy: Planning artifacts for this mission were generated on remediation/doctrine-silence-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/doctrine-silence-guards unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
- T037
- T038
- T039
- T040
phase: Phase 3 - Guidance
history:
- at: '2026-07-26T19:45:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/skills/
create_intent:
- tests/architectural/test_no_dead_doctrine_paths.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/shared/errors.py
- src/doctrine/shared/exceptions.py
- src/doctrine/styleguides/models.py
- src/doctrine/tactics/built-in/common-docs-find.tactic.yaml
- src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml
- src/charter/activation/schemas.py
- src/specify_cli/calibration/walker.py
- src/doctrine/directives/validation.py
- src/doctrine/procedures/validation.py
- src/doctrine/tactics/validation.py
- src/doctrine/paradigms/validation.py
- src/doctrine/procedures/models.py
- src/doctrine/tactics/models.py
- src/doctrine/paradigms/models.py
- src/doctrine/agent_profiles/schema_models.py
- src/doctrine/agent_profiles/repository.py
- src/doctrine/skills/
- src/doctrine/templates/diagrams/
- src/doctrine/templates/architecture/
- src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml
- src/doctrine/directives/README.md
- src/doctrine/tactics/README.md
- src/doctrine/schemas/README.md
- src/doctrine/model_task_routing/catalog/model-to-task_type.yaml
- tests/architectural/test_no_dead_doctrine_paths.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – Followable guidance + discriminating gates

## ⚡ Do This First: Load Agent Profile

Load the `doctrine-daphne` profile via `/ad-hoc-profile-load` and behave according to its guidance before parsing the rest of this prompt.

---

## Objectives & Success Criteria

- No source site instructs an operator to edit `src/doctrine/graph.yaml`.
- Zero `<kind>/shipped/` **path** references remain; every relative cross-link in built-in markdown resolves on disk.
- Both gates carry discriminators and do not false-red on correct code.

**Requirement refs**: FR-008, FR-009, NFR-003, SC-007, SC-008

## Context & Constraints

The rejection hint names a file sharded out of existence by `#2680`. The `shipped/` pack layer named in two operator-facing `SKILL.md` files **has never existed on disk**.

Measured: **22 `shipped/` hits across 9 files**; at least one (`model-to-task_type.yaml`: "shipped/packaged") is **prose, not a path**.

The earlier fix-by-inspection missed **21 of 27** — which is why this is gated, not reviewed.

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

### Subtask T034 – Failing-first test for the dead `graph.yaml` path, with discriminators.

The gate must **not** flag `.kittify/doctrine/graph.yaml` (a live project-tier path) or the sites naming the dead path *in order to forbid it*.

### Subtask T035 – Correct the rejection hint.

`InlineReferenceRejectedError` and its contract fixture name an existing per-kind `<kind>.graph.yaml` fragment.

### Subtask T036 – Correct the remaining dead-path sites.

~10 sites across the validation/model modules and READMEs.

### Subtask T037 – Failing-first test for `<kind>/shipped/` [P].

With a **path-shape** discriminator so "shipped/packaged" is not flagged.

### Subtask T038 – Correct the 22 `shipped/` hits [P].

Across 9 files, including two `SKILL.md` and a canonical glossary term body.

### Subtask T039 – Cross-link resolution.

Every relative cross-link in built-in markdown resolves on disk.

### Subtask T040 – Discriminator fixtures (NFR-003).

Each gate needs a fixture that would false-red **without** its discriminator. This is what proves the discriminator is real.

## Test Strategy

- `PYTHONPATH=src python -m pytest tests/architectural/test_no_dead_doctrine_paths.py -q`
- `PYTHONPATH=src python -m pytest tests/architectural/test_no_legacy_terminology.py -q` — CI-only gate, run before pushing prose changes.

## Risks & Mitigations

- **Ownership, corrected by the post-tasks squad.** The earlier rationale for running this WP last was wrong on two of its three files: `drg/merge.py:29` says "shipped" as **prose**, and `doctrine-daphne.agent.yaml:129` names the dead path **in order to forbid it** — both are the discriminator cases T034/T037 must *not* flag, i.e. fixture material, not edits. Only `agent_profiles/profile.py` was real, and WP04 now fixes that line (T023a).
- **The real gap was elsewhere and is now closed.** `grep -rl "src/doctrine/graph\.yaml" src/` returns **17 files**; this WP originally owned 9. `InlineReferenceRejectedError` lives in `src/doctrine/shared/exceptions.py` and the hint is built in `src/doctrine/shared/errors.py` — **neither was owned by any WP**, so T035 could not be met inside its own boundary. Those two plus five more carriers and the contract fixture are now owned here.
- **The contract fixture is out of `owned_files` by rule, not by oversight.** `owned_files` may not reference `kitty-specs/` paths, but `.../excise-doctrine-curation-and-inline-references-01KP54J6/contracts/validator-rejection-error.schema.json` hard-pins the dead path in its regex, so T035 is not complete until it is updated too. Do it, and say so in the Activity Log — the ownership map cannot carry it.
- **Do not widen a discriminator to silence an unfixable site.** NFR-003 requires each discriminator be proven by a fixture that would false-red without it, but sets no cap on breadth. Pin each discriminator's **effect set** positively — assert the exact excluded paths and their count — so widening it is a visible diff rather than a regex tweak.
- **A bare string gate false-reds on correct code.** Both discriminators are mandatory, and T040 is what proves them.

## Review Guidance

- Verify red→green: the WP's first commit was RED on `remediation/doctrine-silence-guards` and is GREEN at the final commit.
- Verify every gate added is **non-vacuous**: it must reject a planted violation, and its allowlist must be empty.
- Verify the graph invariant where the WP claims it (311 nodes / 774 edges).

## Activity Log

> **CRITICAL**: entries in chronological order, oldest first. **Append** new entries at the END.

- 2026-07-26T19:45:15Z – system – Prompt created.
- 2026-07-27T00:00:00Z – doctrine-daphne – T035 out-of-ownership edit, as the
  prompt's third risk note directs. `owned_files` cannot carry a `kitty-specs/`
  path, so the rejection-error contract fixture at
  `kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/contracts/validator-rejection-error.schema.json`
  was updated here instead: its `migration_hint` regex now reads
  `to src/doctrine/[a-z_]+\.graph\.yaml$`, its example names
  `src/doctrine/directive.graph.yaml`, and its title description records the
  correction. The commit guard **warned** on this path (and on the occurrence
  map) rather than blocking, so nothing was forced.
- 2026-07-27T00:00:00Z – doctrine-daphne – Occurrence map reconciled against the
  real occurrence set (documented bulk-edit exception). Three divergences
  recorded in the map itself: WP04's T023a had already shrunk the dead-path
  carrier set 17→16; the live project-tier `.kittify/doctrine/graph.yaml` class
  was under-enumerated 2→6; and `shipped/` prose also exists outside
  `src/doctrine/` (`runtime/next/_internal_runtime/planner.py:104`). Exceptions
  were only added, never widened to excuse an unfixed site.
- 2026-07-27T00:00:00Z – doctrine-daphne – WP02's `field_path` exception key is
  **not** available on this lane: lane-g's copy of
  `src/doctrine/schemas/occurrence-map.schema.yaml` still has
  `additionalProperties: false` on `exception_entry` with no `field_path`.
  Resolves at merge; path-glob granularity covered every WP07 exemption, so
  nothing was blocked by it.
- 2026-07-27T00:00:00Z – doctrine-daphne – Graph invariant verified at the final
  commit: `doctrine regenerate-graph --check` reports fresh, and the loaded DRG
  is 311 nodes / 774 edges. `doctrine validate src/doctrine` passes 252/252.
