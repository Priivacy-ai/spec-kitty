---
work_package_id: WP05
title: Arch-Gate + ADR + CHANGELOG
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-011
planning_base_branch: fix/expected-artifacts-loader-unification
merge_target_branch: fix/expected-artifacts-loader-unification
branch_strategy: Planning artifacts for this mission were generated on fix/expected-artifacts-loader-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/expected-artifacts-loader-unification unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
phase: Phase 4 - Gate & Docs
history:
- timestamp: '2026-08-31T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/architectural/test_expected_artifacts_loader_gate.py
create_intent:
- tests/architectural/test_expected_artifacts_loader_gate.py
- docs/adr/3.x/2026-08-31-1-expected-artifacts-loader-relocation.md
execution_mode: code_change
mission_id: 01M1C9VQZ28CFRW741WRADS6SZ
owned_files:
- tests/architectural/test_expected_artifacts_loader_gate.py
- docs/adr/3.x/2026-08-31-1-expected-artifacts-loader-relocation.md
- CHANGELOG.md
tags: []
tracker_refs: []
wp_code: WP05
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Close the "mirror loader regrows" defect class **by construction** with a
non-vacuous arch-gate (FR-011, DIRECTIVE_043), and record the cross-boundary
relocation in an ADR (C-005) plus a CHANGELOG entry. This WP MUST land AFTER
WP01-WP04: the gate's allowlist points at the relocated charter helper and
assumes every mirror `model_validate` call is already gone — enabling it earlier
would trip on surviving mirrors or the pre-relocation location.

## Context & Constraints

- **What is forbidden** (in `src/`, outside the allowlist): bare
  `ExpectedArtifactManifest.model_validate(` AND bare `ExpectedArtifactManifest(`
  direct construction. The second form matters because `from_yaml_file` proved
  `cls(**data)` bypasses a `model_validate`-only gate (FR-013 deleted it; this gate
  keeps it dead).
- **Allowlist (the ONLY permitted call sites):**
  `charter/activation/manifest_loader.py` (the canonical loader), the model's own
  definition module (`expected_artifact_manifest.py` for any internal
  construction), and test modules that deliberately construct the model directly
  (`tests/**`, explicitly exempted).
- **Non-vacuity (DIRECTIVE_043):** concrete floor (assert the allowlist has exactly
  the expected entries, not "0 or more"); self-mutation test (inject a forbidden
  call into a temp fixture → gate FAILS); refactor-stable (AST/module allowlist,
  not brittle line-match); shrink-only baseline (allowlist may only shrink in
  future missions, never silently grow).
- See `contracts/arch-gate.md` for the full contract and the sequencing hard
  constraint.
- **Sequencing:** depends on WP01 (moves canonical `model_validate` into charter),
  WP02 (deletes mirror `model_validate` calls), WP03 (behavioral), and WP04
  (launder seam) — all landed first.

## Subtasks & Detailed Guidance

### T018 — Non-vacuous bare-construction arch-gate (FR-011)

**Purpose.** Prevent the mirrors from regrowing and keep `cls(**data)` dead.

**Steps.**
1. Author `tests/architectural/test_expected_artifacts_loader_gate.py` as an
   AST/module-keyed scan of `src/` forbidding bare
   `ExpectedArtifactManifest.model_validate(` AND bare `ExpectedArtifactManifest(`
   outside the allowlist.
2. Allowlist EXACTLY: `charter/activation/manifest_loader.py`, the model's own
   module, and `tests/**` (direct-construction characterization exempt).
3. Concrete floor: assert the allowlist equals the expected set (not ">= 0").
4. Self-mutation test: inject a forbidden call into a temp fixture and assert the
   gate FAILS — proves it is not theater.
5. Refactor-stable: key by module/AST, never line number.
6. Shrink-only: pin a frozen baseline the allowlist can only shrink from.

**Files.** `tests/architectural/test_expected_artifacts_loader_gate.py`.

**Validation.** Gate passes on the post-WP01-04 tree; self-mutation case fails;
model direct-construction tests are exempt and pass. Confirm it does NOT trip on
the charter helper or on any surviving mirror (there should be none).

### T019 — [P] ADR for the relocation (C-005)

**Purpose.** Record the charter↔specify_cli seam decision.

**Steps.**
1. Write `docs/adr/3.x/2026-08-31-1-expected-artifacts-loader-relocation.md` per
   the ADR template.
2. Cover: (a) the charter↔specify_cli seam rationale (C-001 forces the loader
   **and** `ManifestSchemaError` into `charter/activation/manifest_loader.py`, while
   `MalformedManifestError` stays in `charter/offering/missions/repository.py` —
   the two siblings live in different modules because offering cannot import
   activation); (b) the sibling-error model (`MalformedManifestError` =
   present-but-unparseable both tiers; `ManifestSchemaError` = schema/`extra=forbid`;
   never conflated); (c) the deprecation-shim contract (four re-exports with object
   identity; removal is a future announced deprecation); (d) the decision that
   `ManifestRegistry` STAYS in specify_cli as a thin delegate (D3); (e) the C-006
   consequence — a corrupt ORG override on a REGISTERED built-in family
   (`software-dev`) hard-blocks the whole family because the manifest resolution
   raises `MalformedManifestError` at gather time (before the guard-table
   short-circuit); this is intentional (the operator authored the override
   expecting effect).

**Files.** `docs/adr/3.x/2026-08-31-1-expected-artifacts-loader-relocation.md`.

**Validation.** ADR renders; cross-links spec FR-001/002/003/007/008 and decision
`01M1CBARZBBWVGWBTWRMHPP661`.

### T020 — [P] CHANGELOG entry

**Purpose.** Record the user-visible outcome, union-merge friendly.

**Steps.**
1. Add a single line-block entry under the appropriate heading in `CHANGELOG.md`.
2. Note #3770 (loader unification) + #3412 (org-tier fail-loud) closed; epic #3410.
3. Keep it to one contiguous block so parallel lanes union-merge cleanly.

**Files.** `CHANGELOG.md`.

**Validation.** `pytest tests/architectural/test_no_legacy_terminology.py` passes
(terminology guard); entry cites the two issues + epic.

### T021 — Final grep proof appended to the gate

**Purpose.** Prove SC-001: exactly one load implementation/module remains, orphan
gone.

**Steps.**
1. Append to the gate test docstring / PR notes the grep proof: exactly one load
   **implementation/module** owns the org→built-in precedence + `model_validate`
   logic (`charter/activation/manifest_loader.py`). Note this single helper
   legitimately contains TWO `model_validate` calls (the org branch and the
   built-in branch) — the proof is "one load module", NOT "one `model_validate`
   call". `from_yaml_file` is gone (`grep -rn from_yaml_file src/ tests/` empty).
2. Cross-reference the WP02/T009 mirror-removal grep and WP01/T003 deletion.

**Files.** `tests/architectural/test_expected_artifacts_loader_gate.py` (docstring).

**Validation.** Grep commands in the docstring reproduce the single-implementation
claim; reviewers can re-run them.

## Branch Strategy

Planning artifacts were generated on `fix/expected-artifacts-loader-unification`.
During `/spec-kitty.implement` the execution workspace (worktree) is allocated
per-lane from `lanes.json` by `resolve_workspace_for_wp` — do not reconstruct the
path. Completed changes merge back into `fix/expected-artifacts-loader-unification`
unless the human redirects. This WP is the final gate+docs lane and MUST sequence
after WP01-WP04 land into the lane base. Final PR targets upstream as a DRAFT —
the operator merges.

## Definition of Done

- Arch-gate forbids bare `model_validate(` AND bare `ExpectedArtifactManifest(`
  outside the allowlist; is non-vacuous (concrete floor, self-mutation failure,
  refactor-stable, shrink-only) and passes on the post-WP01-04 tree.
- ADR records the seam, sibling-error model (two siblings in two modules), shim
  contract, ManifestRegistry-stays decision, and the C-006 hard-block note.
- CHANGELOG has a single union-merge-friendly block citing #3770 + #3412, epic
  #3410.
- Grep proof (one load implementation/module — the helper's two `model_validate`
  calls are expected; no `from_yaml_file`) is in the gate docstring.
- Terminology guard + `ruff` + `mypy` green.

## Risks

- **Vacuous gate.** A gate that passes on an injected forbidden call is theater —
  the self-mutation test is mandatory (DIRECTIVE_043).
- **Premature enablement.** Landing the gate before WP01-04 trips on surviving
  mirrors or the old location — respect the sequencing constraint.
- **Line-number brittleness.** A line-match gate falsely trips on a later refactor
  — key by AST/module.
- **CHANGELOG merge churn.** A multi-line scattered entry causes union-merge
  conflicts across lanes — keep it one block.

## Reviewer Guidance

- Run the self-mutation case yourself: inject a forbidden call, confirm the gate
  FAILS, then remove it.
- Confirm the allowlist is exactly {charter helper, model module, tests} and is
  asserted as an equality (concrete floor), not a lower bound.
- Verify the ADR covers all four points (seam, sibling model, shim contract,
  ManifestRegistry-stays) and links the decision id.
- Re-run the T021 grep commands and confirm a single load implementation remains
  and `from_yaml_file` is gone.
