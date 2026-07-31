---
work_package_id: WP05
title: Packaging (wheel + sdist) and clean-install CI
dependencies:
- WP03
requirement_refs:
- FR-007
- NFR-002
planning_base_branch: feat/relocate-builtin-doctrine-packs
merge_target_branch: feat/relocate-builtin-doctrine-packs
branch_strategy: Planning artifacts for this mission were generated on feat/relocate-builtin-doctrine-packs. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/relocate-builtin-doctrine-packs unless the human explicitly redirects the landing branch.
created_at: '2026-07-30T19:45:00Z'
subtasks:
- T013
- T014
- T015
phase: Phase 1 - Relocation
history:
- at: '2026-07-30T19:45:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: pyproject.toml
create_intent:
- tests/doctrine/test_packaging_parity.py
execution_mode: code_change
model: ''
owned_files:
- pyproject.toml
- .github/workflows/ci-quality.yml
- tests/doctrine/test_packaging_parity.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP05 — Packaging (wheel + sdist) and clean-install CI

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for the frontmatter profile first.
- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`
Resolve with **`spec-kitty agent profile show python-pedro`**. Do not read the raw `*.agent.yaml`.

---

## Objective
Ship `packs/built-in/` in **both** the wheel and the sdist, and prove it in a clean venv + CI. Runs in **parallel with WP04** (both depend only on WP03). Contract: `contracts/packaging-parity.md`.

## Subtasks
### T013 — pyproject packaging
- Wheel: `[tool.hatch.build.targets.wheel] force-include = { "packs" = "packs" }` (lands `packs/` as a site-packages sibling of `doctrine` — matches WP02 resolver step 3). Verified by the post-plan squad.
- Sdist: extend `[tool.hatch.build.targets.sdist].include` (currently `src/**/*`) with `"packs/**"` — else the sdist ships **zero** built-in content.
- **Do NOT delete** the existing `artifacts` wildcards — schemas/templates/etc STAY under `src/doctrine`; the moved files simply stop matching once gone (no dual-home).

### T014 — Packaging-parity test (`tests/doctrine/test_packaging_parity.py`)
- Build wheel + sdist into a temp dir. Assert the set of `packs/built-in/` relative paths in **each** equals `content-manifest.json` (exact set-equality, NOT `≥` — a `≥` passes on duplication).
- Install the wheel into a **clean venv** (declared deps only, no repo `src/`); assert **packaging truth only**: `import doctrine` succeeds and `resolve_pack_root("built-in")` reads a known data file with 0 missing-file errors.
- **Do NOT assert `load_built_in_graph()` 324/892 here** — the loader isn't repointed until WP04, and WP05 depends only on WP03. The full-graph-load-from-clean-install proof lives in WP07 (which depends on WP04+WP05).

### T015 — Extend the clean-install CI job
- In `.github/workflows/ci-quality.yml`, extend the existing `clean-install-verification` job with a post-wheel-install `spec-kitty doctor doctrine --json` assertion — the CI-facing half of NFR-002. Assert the **specific fields** (`skipped_profiles == []`, no `org_drg` errors, no skipped glossary packs), not a soft top-level "healthy" flag that can be green while a dimension degraded.

## Branch Strategy
Planning branch & merge target: `feat/relocate-builtin-doctrine-packs`. Worktrees per `lanes.json` lane.

## Definition of Done
- Built wheel AND sdist each carry `packs/built-in/` at exact path-set parity with the manifest.
- Clean-venv install imports + resolves built-in, 0 missing-file errors.
- CI `clean-install-verification` asserts `doctor doctrine` healthy.

## Risks
- Build-green-but-empty (the pre-spec squad found this once) — gate on artifact CONTENTS + live import, never on exit code.
- sdist silently drops `packs/` — the `packs/**` include is mandatory.

## Reviewer guidance
Actually inspect the built artifacts' file lists; confirm the CI job runs `doctor doctrine`, not just import.
