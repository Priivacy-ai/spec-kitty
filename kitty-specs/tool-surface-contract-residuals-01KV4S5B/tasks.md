# Tasks — ToolSurfaceContract Residual Closeout

**Mission**: `tool-surface-contract-residuals-01KV4S5B` · **Branch**: `feat/tool-surface-contract-residuals` → PR to `main`
**Source**: [plan.md](./plan.md) (IC-00..IC-04) · [spec.md](./spec.md)

5 work packages. **WP01 (protection net + dead-code pre-clean) first, no deps.** WP02–WP05 each depend on WP01 and are otherwise **independent parallel lanes** (disjoint `owned_files`). ATDD/test-first per the spec's Governing Doctrine.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Verify frozen baselines (doctor-skills, agent-config) present + green — the protection net | WP01 | |
| T002 | Delete dead `model.SurfaceFinding` from `tool_surface/model.py` | WP01 | |
| T003 | Drop the stale 7-field `SurfaceFinding` test from `test_model.py` | WP01 | |
| T004 | Grep-confirm zero live importers; full `tool_surface` suite + ruff/mypy green | WP01 | |
| T005 | RED tests: one per new finding code (source-invalid/name-invalid/overlay-conflict/sentinel-skipped) | WP02 | [P] |
| T006 | Add the 4 finding-code constants to `findings.py` (append-only) | WP02 | |
| T007 | Emit each code at its condition in `profiles/projection.py` + `renderers.py` | WP02 | |
| T008 | Add manifest provenance `source_path`/`source_hash`/`projection_version` (8-field), backward-read-compat | WP02 | |
| T009 | Manifest round-trip + legacy-6-field-read tests; profiles suite + ruff/mypy green | WP02 | |
| T010 | RED tests: `SKILL_ONLY_AGENTS == set(command_installer.SUPPORTED_AGENTS)`; "configured Claude w/ session presence" | WP03 | [P] |
| T011 | Derive `SKILL_ONLY_AGENTS`/`VALID_AGENTS` from `command_installer.SUPPORTED_AGENTS` (no cycle) | WP03 | |
| T012 | Fold `command_renderer.SUPPORTED_AGENTS` → import from `command_installer` | WP03 | |
| T013 | Frozen agent-config compat tests stay green; ruff/mypy | WP03 | |
| T014 | RED adversarial test: injected unregistered `.agents/skills/spec-kitty.*` doc ref → docs-lint fails | WP04 | [P] |
| T015 | Re-mark `test_docs.py` `pytestmark` `unit` → `integration` | WP04 | |
| T016 | Add `tool_surface` paths-filter + shard mapping in `ci-quality.yml` (integration-core-misc) | WP04 | |
| T017 | Verify: clean tree passes; injected drift fails; shard `-m` selector collects it | WP04 | |
| T018 | RED tests: `SPECIFY_REPO_ROOT`→`.kittify`-less dir resolves to it; doctor-skills test deterministic | WP05 | [P] |
| T019 | `paths.py`: make `SPECIFY_REPO_ROOT` authoritative when `env_path.exists()` (drop `.kittify` precondition) | WP05 | |
| T020 | Write user-facing Tool-vs-Agent upgrade + repair guide under `docs/`; TOC/inventory; lint-clean | WP05 | |
| T021 | Note 3-way `locate_project_root` split (deferred #1971); docs-lint + doctor-skills test + ruff/mypy | WP05 | |

---

## WP01 — Protection net & dead-code pre-clean (IC-00)

- **Goal**: Establish the backward-compat protection net and remove the dead `model.SurfaceFinding` duplicate before any finding-code work begins.
- **Priority**: P1 (gate). **Dependencies**: none. **Independent test**: full `tests/specify_cli/tool_surface/` + frozen baselines green after the deletion.
- **Requirement refs**: NFR-001, FR-008.
- [x] T001 Verify frozen baselines (doctor-skills, agent-config) present + green — the protection net (WP01)
- [x] T002 Delete dead `model.SurfaceFinding` from `tool_surface/model.py` (WP01)
- [x] T003 Drop the stale 7-field `SurfaceFinding` test from `test_model.py` (WP01)
- [x] T004 Grep-confirm zero live importers; full `tool_surface` suite + ruff/mypy green (WP01)
- **Risks**: deleting the class breaks `test_model.py` import unless the stale test is removed in the same change.

## WP02 — #1940 profile diagnostics + manifest provenance (IC-01)

- **Goal**: Implement the 4 missing finding codes + 3 manifest provenance fields per the canonical `data-model.md`.
- **Priority**: P1. **Dependencies**: WP01. **Independent test**: per-finding-code tests + manifest round-trip/legacy-read green.
- **Requirement refs**: FR-001, FR-002.
- [x] T005 RED tests: one per new finding code (WP02)
- [x] T006 Add the 4 finding-code constants to `findings.py` (append-only) (WP02)
- [x] T007 Emit each code at its condition in `profiles/projection.py` + `renderers.py` (WP02)
- [x] T008 Add manifest provenance (8-field), backward-read-compat (WP02)
- [x] T009 Manifest round-trip + legacy-read tests; profiles suite + ruff/mypy (WP02)
- **Risks**: do not rename the 3 existing profile codes (append-only); legacy 6-field manifests must still load.

## WP03 — #1941 registry-backed agent sets (IC-02)

- **Goal**: Collapse the duplicated tool-universe literals to one registry-backed source; add the missing test scenario.
- **Priority**: P1. **Dependencies**: WP01. **Independent test**: frozen `test_agent_config_compat.py` green + new Claude-session-presence test.
- **Requirement refs**: FR-003, FR-004.
- [x] T010 RED tests: registry-backed equality + "configured Claude w/ session presence" (WP03)
- [x] T011 Derive `SKILL_ONLY_AGENTS`/`VALID_AGENTS` from `command_installer.SUPPORTED_AGENTS` (WP03)
- [x] T012 Fold `command_renderer.SUPPORTED_AGENTS` → import from `command_installer` (WP03)
- [x] T013 Frozen agent-config compat tests stay green; ruff/mypy (WP03)
- **Risks**: import cycle pulling `command_installer` into `config.py` — use a module-load helper if a cycle exists; values must stay byte-identical.

## WP04 — #1942 docs-lint CI enforcement (IC-03)

- **Goal**: Make the docs-contract lint a CI-collected fail-on-drift gate (currently invisible: `unit` marker + no path filter).
- **Priority**: P1. **Dependencies**: WP01. **Independent test**: clean tree passes; injected drift fails; the shard actually collects it.
- **Requirement refs**: FR-005.
- [x] T014 RED adversarial test: injected unregistered doc ref → docs-lint fails (WP04)
- [x] T015 Re-mark `test_docs.py` `unit` → `integration` (WP04)
- [x] T016 Add `tool_surface` paths-filter + shard mapping in `ci-quality.yml` (WP04)
- [x] T017 Verify clean-pass / drift-fail / shard collection (WP04)
- **Risks**: re-marking alone isn't enough without a path filter (double invisibility); confirm the shard `-m` selector includes `integration`.

## WP05 — #1944 migration guide + #1965 deterministic resolver (IC-04)

- **Goal**: Ship the user-facing Tool-vs-Agent upgrade/repair guide + make `SPECIFY_REPO_ROOT` authoritative so the doctor-skills test is deterministic.
- **Priority**: P1. **Dependencies**: WP01. **Independent test**: docs-lint clean on the new guide; doctor-skills test deterministic with ambient `~/.claude` present.
- **Requirement refs**: FR-006, FR-007.
- [x] T018 RED tests: env-override resolution + deterministic doctor-skills test (WP05)
- [x] T019 `paths.py`: `SPECIFY_REPO_ROOT` authoritative when `env_path.exists()` (WP05)
- [x] T020 Write the upgrade+repair guide under `docs/`; TOC/inventory; lint-clean (WP05)
- [x] T021 Note 3-way split (deferred #1971); run docs-lint + doctor-skills + ruff/mypy (WP05)
- **Risks**: the `paths.py` change must not alter resolution for real `.kittify/` projects (keep `env_path.exists()` guard); full 3-way consolidation is out of scope (#1971).
