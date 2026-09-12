---
work_package_id: WP03
title: Silent-kind-drop closure — consumer sites
dependencies:
- WP01
requirement_refs:
- FR-003
- NFR-004
- C-002
planning_base_branch: remediation/doctrine-silence-guards
merge_target_branch: remediation/doctrine-silence-guards
branch_strategy: Planning artifacts for this mission were generated on remediation/doctrine-silence-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/doctrine-silence-guards unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T017
phase: Phase 2 - Boundaries
history:
- at: '2026-07-26T19:45:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/query.py
create_intent:
- tests/doctrine/drg/test_unknown_kind_fails_loudly.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/query.py
- src/charter/context.py
- tests/doctrine/drg/test_unknown_kind_fails_loudly.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Silent-kind-drop closure (consumer sites)

## ⚡ Do This First: Load Agent Profile

Load the `python-pedro` profile via `/ad-hoc-profile-load` and behave according to its guidance before parsing the rest of this prompt.

---

## Objectives & Success Criteria

- An unknown kind fails loudly at **all four** sites.
- The graph invariant holds: **311 nodes / 774 edges** unchanged (NFR-004).

**Requirement refs**: FR-003, NFR-004, C-002, SC-002

## Context & Constraints

Measured on this branch, not inherited — the sequencing authority's figures were a static read:

| Site | Shape | Kinds lost |
|---|---|---|
| `query.py:230-242` | 16 buckets filled, 10 read out | 6 |
| `charter/context.py:672-683` | 4 branches, **no `else`** | 12 |
| `extractor.py:133-145` | 11 of 16 mapped | **5** |
| `extractor.py:1210-1229` | field-by-field writers | any new field |

`_KIND_MAP` drops `anti_pattern`, `asset`, `glossary`, `glossary_pack`, `glossary_scope`. **No artefact references any of them today**, so closing it is graph-neutral — the drop is **latent, not harmless**, and goes live when mission C authors 2 anti-patterns and 4 assets.

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

### Subtask T012 – Failing-first test.

Plant an unknown kind at each of the four sites; assert the current silence. The RED is the deliverable.

### Subtask T013 – Close `query.py:230-242`.

16 `NodeKind` buckets are filled and 10 read out. Make the shortfall loud.

### Subtask T014 – Close `charter/context.py:672-683`.

Four kind branches, no `else`. **Pin behaviourally, not by code shape** — see risks.

### Subtask T015 – Close `extractor.py:133-145` (`_KIND_MAP`).

11 of 16 kinds mapped. An unmapped kind must raise, not vanish.

### Subtask T016 – Close `extractor.py:1210-1229`.

`_node_to_dict` / `_edge_to_dict` enumerate fields by hand.

### Subtask T017 – Assert the graph invariant.

311 nodes / 774 edges before and after. If it moves, that is a finding to ledger — **not a number to bump**.

## Test Strategy

- `PYTHONPATH=src python -m pytest tests/doctrine/drg/ -q`
- Graph check: load `src/doctrine` and assert 311 nodes / 774 edges.

## Risks & Mitigations

- **Collides with `#2532`** (decompose `charter/context.py`) — the missing `else` is inside the module being split. **Assert behaviourally** so the decomposition cannot drop it. Cross-reference both issues.
- Closing `_KIND_MAP` may surface previously-dropped kinds. Verified none today; re-verify, and ledger any movement.

## Review Guidance

- Verify red→green: the WP's first commit was RED on `remediation/doctrine-silence-guards` and is GREEN at the final commit.
- Verify every gate added is **non-vacuous**: it must reject a planted violation, and its allowlist must be empty.
- Verify the graph invariant where the WP claims it (311 nodes / 774 edges).

## Activity Log

> **CRITICAL**: entries in chronological order, oldest first. **Append** new entries at the END.

- 2026-07-26T19:45:15Z – system – Prompt created.
