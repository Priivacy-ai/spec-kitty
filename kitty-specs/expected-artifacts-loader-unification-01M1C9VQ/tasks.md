# Tasks: Unify expected-artifacts.yaml Loading + Close Org-Tier Fail-Loud Gap

**Mission**: expected-artifacts-loader-unification-01M1C9VQ
**Branch**: `fix/expected-artifacts-loader-unification`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

## Overview

5 work packages. WP01 is the sequential foundation (relocate the authority);
WP02/WP03 run in parallel after it; WP04 integrates their result to close the
launder seam; WP05 gates by construction + docs. Red-first regressions live in
WP03 (loader/reader level) and WP04 (composed-guard integration).

## Dependency Graph

```
WP01 (foundation: relocate + shim + delegate + delete orphan)
  ├──► WP02 (retire 3 mirrors → delegate)        ┐
  └──► WP03 (org-tier fail-loud + unreadable)     ├──► WP04 (close launder seam) ──► WP05 (arch-gate + ADR + CHANGELOG)
                                                   ┘
```

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Create `charter/activation/manifest_loader.py` cached authority + move `ManifestSchemaError` | WP01 | |
| T002 | `ManifestRegistry.load_manifest` → thin delegate; shim re-exports (4 names) | WP01 | |
| T003 | Delete `from_yaml_file`; migrate its 3 tests | WP01 | |
| T004 | Reconcile stale `load_manifest` docstring/comments (FR-014) | WP01 | [P] |
| T005 | Shim re-export + cache characterization tests | WP01 | |
| T006 | Retire `resolver._load_expected_artifact_manifest` → delegate | WP02 | [P] |
| T007 | Retire `_presence_filenames_for` load half → authority + projection (None→frozenset()) | WP02 | [P] |
| T008 | Re-point `_resolve_expected_artifacts_slot` → authority (absent→None, malformed→raise) | WP02 | [P] |
| T009 | Update parity/characterization tests for the three re-points | WP02 | |
| T010 | [RED] broken ORG manifest → `MalformedManifestError` at the reader (real broken YAML) | WP03 | |
| T011 | Implement org-tier fail-loud in `_read_yaml_mapping` (FR-007); absence still None | WP03 | |
| T012 | [RED] present-but-unreadable built-in manifest → `MalformedManifestError` (FR-012) | WP03 | |
| T013 | Implement unreadable-present fail-loud both tiers (FR-012); absence→None | WP03 | |
| T014 | Distinctness unit tests (non-mapping / unreadable / absent) both tiers; NFR-005 message | WP03 | |
| T015 | [RED] custom family + broken org manifest through composed guard → raise, never `[]` | WP04 | |
| T016 | Pin `composition.py:504` `except` to `UnregisteredMissionFamilyError` only (FR-009/010) | WP04 | |
| T017 | Durability + absent-still-tolerant-green characterization | WP04 | |
| T018 | Non-vacuous arch-gate: bare `model_validate(`/`ExpectedArtifactManifest(` outside helper (FR-011) | WP05 | |
| T019 | ADR for the relocation + shim contract (C-005) | WP05 | [P] |
| T020 | CHANGELOG entry (union-merge friendly) | WP05 | [P] |
| T021 | Final grep proof: one load impl; orphan gone | WP05 | |

---

## WP01 — Relocate & unify the loader authority *(Foundation)*

- **Goal**: One cached `expected-artifacts.yaml` authority in `charter`, with a
  deprecation shim so no consumer breaks; delete the orphan direct-read loader.
- **Priority**: P1 (MVP — blocks everything).
- **Independent test**: old-path imports of `ManifestRegistry`, `load_manifest`,
  `ManifestSchemaError`, `MalformedManifestError` resolve with object identity;
  `TestManifestRegistryOrgTier` cache tests pass via the delegate.
- **Subtasks**: T001, T002, T003, T004, T005
- **Depends on**: none. **Requirements**: FR-001, FR-002, FR-003, FR-013, FR-014, NFR-001, NFR-002
- **Prompt**: [tasks/WP01-relocate-loader-authority.md](./tasks/WP01-relocate-loader-authority.md) (~260 lines)

## WP02 — Retire the three mirror loaders *(delegate)*

- **Goal**: The resolver mirror, the runtime-bridge mirror, and the charter-tier
  raw-mapping loader all obtain their manifest from the one authority.
- **Priority**: P1. **Independent test**: exactly one `model_validate` load impl
  remains (grep); bridge-parity + configured-artifact-name suites green; charter
  slot gains validation while absence still returns `None`.
- **Subtasks**: T006, T007, T008, T009
- **Depends on**: WP01. **Requirements**: FR-004, FR-005, FR-006
- **Prompt**: [tasks/WP02-retire-mirror-loaders.md](./tasks/WP02-retire-mirror-loaders.md) (~230 lines)

## WP03 — Org-tier fail-loud + unreadable widening *(RED-first)*

- **Goal**: A present-but-corrupt manifest (YAML-syntax, non-mapping, or
  unreadable) raises `MalformedManifestError` on BOTH tiers, distinct from absence.
- **Priority**: P1. **Independent test**: broken org manifest raises at the reader
  (RED on main); absent still `None`; built-in unreadable now raises.
- **Subtasks**: T010, T011, T012, T013, T014
- **Depends on**: WP01. **Requirements**: FR-007, FR-008, FR-012, NFR-005
- **Prompt**: [tasks/WP03-org-tier-fail-loud.md](./tasks/WP03-org-tier-fail-loud.md) (~250 lines)

## WP04 — Close the launder seam *(RED-first integration)*

- **Goal**: The malformed signal propagates through the composed-action guard and
  is never degraded to `[]`.
- **Priority**: P1. **Independent test**: custom family + broken org manifest
  through `_dispatch_via_composition` raises `MalformedManifestError`, result
  never `[]` (RED on main); absent family still tolerant-green.
- **Subtasks**: T015, T016, T017
- **Depends on**: WP02, WP03. **Requirements**: FR-009, FR-010
- **Prompt**: [tasks/WP04-close-launder-seam.md](./tasks/WP04-close-launder-seam.md) (~200 lines)

## WP05 — Arch-gate + ADR + CHANGELOG *(gate by construction)*

- **Goal**: Non-vacuous gate keeps the loaders unified; ADR records the seam;
  CHANGELOG documents the change.
- **Priority**: P2. **Independent test**: gate fails on an injected bare
  construction and passes on model direct-construction tests.
- **Subtasks**: T018, T019, T020, T021
- **Depends on**: WP01, WP02, WP03, WP04. **Requirements**: FR-011
- **Prompt**: [tasks/WP05-arch-gate-and-docs.md](./tasks/WP05-arch-gate-and-docs.md) (~220 lines)

---

*Subtask completion is event-sourced — record with
`spec-kitty agent tasks mark-status Txxx --status done`. The rows above are
reference rows, not checkboxes.*
