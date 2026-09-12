---
work_package_id: WP04
title: Gate scaffolding (extended lint + touched-set + reconcile gates)
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-017
- FR-018
- FR-023
- NFR-002
- NFR-005
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T011
- T012
- T013
- T014
- T041
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: scripts/docs/touched_set_gates.py
create_intent:
- scripts/docs/touched_set_gates.py
- scripts/docs/rename_reconcile.py
- tests/docs/test_touched_set_gates.py
execution_mode: code_change
owned_files:
- packs/built-in/assets/docs_structural_lint.py
- scripts/docs/touched_set_gates.py
- scripts/docs/rename_reconcile.py
- tests/docs/test_touched_set_gates.py
- .github/workflows/docs-freshness.yml
- packs/built-in/styleguides/common-docs.styleguide.yaml
- scripts/generate_schemas.py
- src/doctrine/schemas/styleguide.schema.yaml
- tests/doctrine/test_schema_generation_integrity.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load python-pedro
```
Confirm TDD/red-first; run pytest+ruff+mypy before handoff.

## Objective
Build the gates that make the mission's acceptance criteria verifiable — advisory at this stage (WP13
flips the structural ones to blocking). See [plan.md](../plan.md) IC-03a, [research.md](../research.md) D4, and the
[Gate Coverage Matrix](../plan.md).

## Context
`docs_structural_lint.py` is whole-tree (no diff awareness) — so presence checks (Divio-type, audience)
must be **touched-set** gates keyed off `git diff --name-only <base>`, NOT whole-tree lint (would red
untouched pages, C-012). Policy values come from the `structural_lint_config` block — no inlined
literals. `_guards.assert_examined_floor` and `related_validator` exist to reuse.
Note: T004 (the four `structural_lint_config` invariant fields) was reconciled here from WP01 — the
three-way schema/LintConfig/YAML parity guard requires those fields to land together with this WP's
LintConfig dataclass + check-fns.

## Subtasks
- **T004** — Declare the `structural_lint_config` invariant fields and restore three-way parity: add
  `sanctioned_content_sections`, `non_content_dirs`, `root_allowlist` (array-of-string) and
  `one_index_per_dir` (bool) to `common-docs.styleguide.yaml`; extend `STRUCTURAL_LINT_CONFIG_SCHEMA`
  (`_STRUCTURAL_LINT_CONFIG_DEF`) in `scripts/generate_schemas.py` and regenerate
  `src/doctrine/schemas/styleguide.schema.yaml` (`python scripts/generate_schemas.py`); add the four
  fields to the frozen `LintConfig` dataclass + `_from_block` loader (add a `_require_bool` helper) in
  `docs_structural_lint.py`, and update the `_make_config` fixture + the property pin in
  `tests/doctrine/test_schema_generation_integrity.py`. This is the config surface T011
  (sanctioned-section/one-index checks) and T041 (root-allowlist) consume.
- **T011** — Extend `docs_structural_lint.py` with config-driven check-fns: one-index-per-dir (extend
  `check_index_completeness`) and sanctioned-section membership (from the WP01 config list). Advisory
  (report-only) for now; keep the current tree green (NFR-003 scoping).
- **T012** — `scripts/docs/touched_set_gates.py`: compute the touched set from `git diff --name-only
  <base>`; assert each touched in-scope page (a) declares a resolvable `audience:` (presence), (b) has a
  `description` in 50–180 chars, (c) sits in the section its audience dictates (internal→development/,
  external→guides/) for `how_to`-typed pages. Denominator = touched set, not whole tree.
- **T013** — `scripts/docs/rename_reconcile.py`: assert `git diff --find-renames` under `docs/` (and
  retired root dirs) ⊆ `occurrence_map.yaml moves:`, and the existing `occurrence_map ⊆ redirect_map`
  cross-check. Fail on any rename/deletion not recorded in the spine.
- **T014** — Wire into `.github/workflows/docs-freshness.yml`: `audience_resolver --strict`,
  `relative_link_fixer --check`, `check_cli_reference_freshness.py` (NFR-009 — regenerated behavior-doc
  pages can't silently drift), and scope the freshness gate to changed paths / emit a baseline-diff
  classification (#3147) so the required check reflects only mission-introduced reds.
- **T041** — Implement the root-allowlist check (NFR-006/SC-002) in `touched_set_gates.py`: enumerate
  documentation-bearing files outside `docs/`, diff against the closed sanctioned root allowlist (from
  the WP01 config / spec Definitions), fail on any file not in the allowlist. Red-first test. Advisory
  here; WP13 T040 flips it blocking. (This is the single-root assertion the structural lint — rooted at
  `docs/` — structurally cannot see.)

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane.

## Definition of Done
- All new gates run green on the current tree and red on injected violations; `tests/docs/test_touched_set_gates.py`
  covers each. docs-freshness.yml updated. ruff/mypy clean. The pre-merge DocFX **build** job is WP13.

## Risks
- OB-2: do NOT make single-root/sanctioned-section a standing blocking lint here — advisory only; WP13
  handles terminal blocking, respecting the #2851 retirement unless re-sanctioned.
