---
work_package_id: WP08
title: '#2088 ownership-overlap dependency-exemption regression guard (Lane B)'
dependencies:
- WP00
requirement_refs:
- FR-007
tracker_refs:
- '#2088'
planning_base_branch: feat/gate-read-surface-completion
merge_target_branch: feat/gate-read-surface-completion
branch_strategy: Planning artifacts for this mission were generated on feat/gate-read-surface-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/gate-read-surface-completion unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
phase: Phase 2 - Lock-the-fix (Lane B, parallel)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4006361"
history:
- at: '2026-06-24T08:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/ownership/
create_intent:
- tests/specify_cli/ownership/test_dependency_overlap_exemption.py
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/ownership/test_dependency_overlap_exemption.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – #2088 ownership-overlap dependency-exemption regression guard (Lane B)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on
`authoritative_surface: tests/specify_cli/ownership/`.

---

## Objective

Add a **dedicated red-first regression guard** driving the reported #2088 scenario —
dependency-ordered WP pairs that legitimately share `owned_files` — through
`finalize-tasks --validate-only`. **The product fix already exists**
(`ownership/validation.py:127` `_dependency_reachability`; caller threads `_wp_dependencies`
at `mission.py:3521`); this WP **locks it** with a scenario-driving guard, then closes #2088
within the mission matrix.

Lane B — parallel with Lane A's spine; no dependency on the Lane A re-points (WP01–WP06).
Depends only on **WP00** (the write-surface foundation that fixes the editable CLI so this
WP's implement loop can run); WP00 is shared by every lane, not part of Lane A's spine.

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) FR-007; NFR-002 (revert the exemption to prove RED).
- [plan.md](../plan.md) IC-09.
- [data-model.md](../data-model.md) Lane B table (#2088 row).

Live-verified fix:
- `_dependency_reachability` at `src/specify_cli/ownership/validation.py:127` (takes a
  `Mapping[str, list[str]]` dependency graph; exempts dep-ordered pairs from the overlap error).
- Caller threads `_wp_dependencies` at `mission.py:3516-3521`
  (`validate_ownership(wp_manifests, _wp_dependencies)`).

**The scenario**: two same-lane SEQUENTIAL WPs (WP-B depends-on WP-A) that share an
`owned_files` glob. Without the exemption, the overlap validator errors; with it (dep
reachability A→B), the overlap is allowed. The guard drives this through
`finalize-tasks --validate-only` and asserts it PASSES (no overlap error) for the dep-ordered
pair, and STILL ERRORS for an independent (non-dep-ordered) overlapping pair.

**Negative scope**: do NOT change product code. Test-only lock. The guard goes RED if the
`_dependency_reachability` exemption is reverted.

## Branch Strategy

- **Strategy**: `parallel-lane` (Lane B — independent of Lane A)
- **Planning base branch**: `feat/gate-read-surface-completion`
- **Merge target branch**: `feat/gate-read-surface-completion`

> WP08 OWNS `tests/specify_cli/ownership/test_dependency_overlap_exemption.py` exclusively.

## Subtasks & Detailed Guidance

### Subtask T027 – Red-first dep-exemption guard via finalize-tasks --validate-only

- **Purpose**: Drive the reported scenario through the real validate-only entry point.
- **Files**: new `tests/specify_cli/ownership/test_dependency_overlap_exemption.py`.
- **Steps (red-first — DIRECTIVE_034)**:
  1. Build a mission fixture with two WPs: WP-A and WP-B where `WP-B.dependencies == ["WP-A"]`
     and BOTH declare an overlapping `owned_files` glob (e.g. both own
     `src/pkg/shared_surface.py`).
  2. Drive `finalize-tasks --validate-only` (the pre-existing entry point — the CLI command or
     its `validate_ownership` call path threaded with `_wp_dependencies`). Assert it PASSES
     (no `OWNERSHIP_OVERLAP` error) because A→B is dependency-reachable.
  3. NEGATIVE control: a second fixture with two INDEPENDENT WPs (no dep edge) sharing the same
     glob — assert validate-only STILL ERRORS (the exemption is dep-scoped, not a blanket
     allow). This kills the "always allow overlap" mutant.
  4. Production-shaped WP manifests (real ULID-based mission, real `owned_files` paths) — use
     the canonical mission/WP factory, not hand-built dicts.

### Subtask T028 – Prove RED by reverting the exemption

- **Purpose**: NFR-002 — non-vacuous proof.
- **Files**: `tests/specify_cli/ownership/test_dependency_overlap_exemption.py` (+ recorded proof).
- **Steps**:
  1. Temporarily revert the `_dependency_reachability` exemption in `validation.py` (locally,
     do NOT commit), run the new test, confirm the dep-ordered case goes RED (overlap error
     raised). Restore, confirm GREEN.
  2. Record the revert-and-restore evidence in the activity log.
  3. Close #2088 within the mission matrix (verified-already-fixed / regression-guarded).

## Test Strategy

- `pytest tests/specify_cli/ownership/test_dependency_overlap_exemption.py -q`.
- Red-first evidence (revert+restore) recorded.
- `ruff check` + `mypy` on the test — zero issues, no suppressions.

## Definition of Done

- [ ] Red-first guard: dep-ordered overlapping WP pair PASSES validate-only via the real
  entry point.
- [ ] Negative control: independent overlapping pair STILL ERRORS (mutant killed).
- [ ] RED proven by reverting the `validation.py` exemption (evidence recorded); GREEN with it.
- [ ] No product code changed (test-only lock).
- [ ] #2088 closed within the mission matrix.
- [ ] Production-shaped manifests via the canonical factory; ruff + mypy clean.

## Risks & Mitigations

- **Vacuous guard (always passes)**: Mitigation: the negative control (independent pair still
  errors) + the revert-proof.
- **Hand-built manifests masking real behavior**: Mitigation: canonical factory, real ULID.
- **Wrong entry point**: Mitigation: drive `finalize-tasks --validate-only` /
  `validate_ownership` with `_wp_dependencies`, not `_dependency_reachability` directly.

## Review Guidance

- Confirm both the positive (dep-ordered → pass) AND negative (independent → error) cases exist.
- Confirm the revert-and-restore RED evidence is recorded.
- Confirm manifests are production-shaped (canonical factory, real ULID), not hand-built.

## Activity Log

- 2026-06-24T08:00:00Z – system – Prompt created.
- 2026-06-24T15:13:46Z – claude:opus:python-pedro:implementer – shell_pid=3973827 – Assigned agent via action command
- 2026-06-24T15:24:01Z – claude:opus:python-pedro:implementer – shell_pid=3973827 – Red-first guard for #2088: 4 tests (2 positive dep-ordered pass, 2 negative concurrent still error). Revert proof: exemption commented out → 2 FAIL; restored → 4 PASS. Ruff+mypy clean. No product code changed. Test-only lock.
- 2026-06-24T15:24:34Z – user – shell_pid=3973827 – Lane-i code d6cc3e82c; status from main
- 2026-06-24T15:24:35Z – claude:opus:reviewer-renata:reviewer – shell_pid=4006361 – Started review via action command
- 2026-06-24T15:28:10Z – user – shell_pid=4006361 – Review passed (reviewer-renata): DIRECTIVE_041 revert-proof verified INDEPENDENTLY — commented out _dependency_reachability exemption (validation.py:201-207), reran the 4 tests: exactly the 2 dep-ordered tests (test_dep_ordered_pair_passes, test_transitive_dep_pair_passes) went RED with OWNERSHIP_OVERLAP, the 2 negative controls (test_independent_pair_still_errors_with_dep_map, test_sibling_pair_with_common_parent_dep_still_errors) stayed GREEN; restored → 4 passed, git status clean (NO product change). Real entry point: build_wp_manifests + validate_ownership threaded with _wp_dependencies mirroring mission.py:3516-3521. Production-shaped: canonical WPMetadata model (WP\d{2,} validator), 26-char ULID. Mutant-killers present (blanket-allow killed). ruff + mypy clean. Anti-pattern checklist all PASS/N-A.
