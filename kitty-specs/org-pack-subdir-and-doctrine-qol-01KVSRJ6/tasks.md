# Tasks: Org-Pack Subdir Source & Doctrine QoL

**Mission**: org-pack-subdir-and-doctrine-qol-01KVSRJ6 | **Branch**: feat/doctrine-qol-2083

5 work packages across 4 threads. WP02 depends on WP01 (effective-root seam). WP03/WP04/WP05 are independent parallel lanes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `subdir` field to `OrgPackConfig` | WP01 | |
| T002 | Add `subdir` string-level escape validator | WP01 | |
| T003 | Add `effective_root(repo_root)` seam (normalize + join + symlink containment) | WP01 | |
| T004 | Round-trip `subdir` (`_pack_to_yaml_dict` + `_build_legacy_single_pack`) | WP01 | |
| T005 | Surface structured containment error (not swallowed by `load_pack_registry`) | WP01 | |
| T006 | Unit tests for T001–T005 | WP01 | |
| T007 | Adopt `effective_root` in `charter/drg.py` (doctor-health path) | WP02 | |
| T008 | Adopt in `charter/pack_context.py` + `charter/context.py` | WP02 | |
| T009 | Adopt in `doctrine/org_charter.py` + `doctor.py` + `org_layer.py` lint | WP02 | |
| T010 | `doctrine fetch` reports effective-root artifact count | WP02 | |
| T011 | Update `config-schema.yaml` contract (add `subdir`) | WP02 | [P] |
| T012 | Integration tests: SC-001 doctor-healthy-on-subdir, SC-002 no-subdir regression, SC-003 fetch wrong-subdir | WP02 | |
| T013 | Audit ruamel vs PyYAML usage (≥3 named sites + dual-use modules) | WP03 | [P] |
| T014 | Write the YAML-library choice doc (current-vs-aspirational) | WP03 | [P] |
| T015 | Verify doc reachability / cross-link | WP03 | [P] |
| T016 | Author tiered-standards `styleguide` (tiers → named `src/` areas + rigour table) | WP04 | [P] |
| T017 | Add inbound DRG edge from a directive/paradigm | WP04 | [P] |
| T018 | Regenerate `graph.yaml` via generator | WP04 | [P] |
| T019 | Non-orphan DRG test | WP04 | [P] |
| T020 | Validate-time guard: reject `applies_to_languages: [any]`/`[all]` | WP05 | [P] |
| T021 | `scoping.py` defense-in-depth (normalize/clarify any/all) | WP05 | [P] |
| T022 | `_catalog_miss.py` "present-but-scope-filtered" diagnostic | WP05 | [P] |
| T023 | Tests: validate rejection + scope-filtered diagnostic | WP05 | [P] |

---

## WP01 — OrgPackConfig effective-root seam, validation & round-trip (Thread A foundation)

**Goal**: Add `subdir` to `OrgPackConfig` and a single canonical `effective_root(repo_root)` seam (FR-001/002/003/005/006, C-005/C-007). Foundation for WP02.
**Priority**: P1 (driver). **Independent test**: unit tests assert `effective_root` joins/normalizes correctly, validator rejects the escape set, round-trip preserves/omits `subdir`.
**Prompt**: [tasks/WP01-org-pack-effective-root-seam.md](tasks/WP01-org-pack-effective-root-seam.md)

- [ ] T001 Add `subdir: str | None = None` to `OrgPackConfig` (WP01)
- [ ] T002 Add `subdir` field_validator: reject absolute (POSIX/Windows/UNC) + any `..`; normalize `.`/empty → None (WP01)
- [ ] T003 Add `effective_root(repo_root)` — normalize relative-to-repo_root, join `subdir`, symlink containment via `ensure_within_directory` (WP01)
- [ ] T004 Round-trip: `_pack_to_yaml_dict` emits `subdir` only when set; `_build_legacy_single_pack` reads it (WP01)
- [ ] T005 Ensure containment failure raises a structured, operator-visible error (not swallowed by `load_pack_registry`) (WP01)
- [ ] T006 Unit tests for T001–T005 in `tests/doctrine/` (WP01)

**Dependencies**: none. **Risks**: `effective_root` must be the single normalization point (retire raw-vs-relative split).

## WP02 — All-consumer adoption, fetch reporting & contract (Thread A integration)

**Goal**: Route every pack-root reader through `effective_root` so a subdir pack loads everywhere incl. `doctor doctrine` health; report effective-root at fetch; align the contract (FR-004/007/008, SC-001/002/003).
**Priority**: P1. **Independent test**: SC-001 end-to-end `doctor doctrine` on a subdir fixture pack reports healthy.
**Prompt**: [tasks/WP02-consumer-adoption-fetch-contract.md](tasks/WP02-consumer-adoption-fetch-contract.md)

- [ ] T007 Adopt `effective_root` in `charter/drg.py` (`load_org_pack` — the doctor-health path) (WP02)
- [ ] T008 Adopt in `charter/pack_context.py` (`_read_org_packs`) + `charter/context.py` (WP02)
- [ ] T009 Adopt in `specify_cli/doctrine/org_charter.py` + `cli/commands/doctor.py` (`_build_pack_entries`) + `charter_runtime/lint/checks/org_layer.py` (WP02)
- [ ] T010 `doctrine fetch` reports artifact count at the effective root (`specify_cli/doctrine/snapshot.py`) (WP02)
- [ ] T011 Update `kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/config-schema.yaml` to include `subdir` (WP02)
- [ ] T012 Integration tests: SC-001 healthy-on-subdir, SC-002 no-subdir regression, SC-003 fetch wrong-subdir signal (WP02)

**Dependencies**: WP01. **Risks**: a missed consumer = silent partial fix; SC-001 integration test is the catch-all.

## WP03 — YAML-library choice documentation (Thread B / #707)

**Goal**: Document the honest ruamel-vs-PyYAML rule (FR-009, SC-004).
**Priority**: P3. **Independent test**: doc names ≥3 real call sites + the dual-use sites; declares current-vs-aspirational.
**Prompt**: [tasks/WP03-yaml-library-docs.md](tasks/WP03-yaml-library-docs.md)

- [ ] T013 Audit ruamel vs PyYAML usage; list ≥3 named sites + the dual-use modules (WP03)
- [ ] T014 Write the YAML-library choice doc under `docs/` (current-vs-aspirational; name contradiction sites) (WP03)
- [ ] T015 Verify reachability / cross-link from a discoverable index (WP03)

**Dependencies**: none (parallel). **Risks**: must not assert a clean invariant that doesn't exist.

## WP04 — Tiered-standards styleguide + DRG edge (Thread C / #2096)

**Goal**: A non-orphan tiered-standards `styleguide` mapped to named `src/` areas + ≥1 inbound DRG edge (FR-010/011, SC-005, C-001/004).
**Priority**: P2. **Independent test**: non-orphan DRG test + generator freshness passes.
**Prompt**: [tasks/WP04-tiered-standards-styleguide.md](tasks/WP04-tiered-standards-styleguide.md)

- [ ] T016 Author `src/doctrine/styleguides/built-in/tiered-standards.styleguide.yaml` (tiers → named `src/` areas + rigour table) (WP04)
- [ ] T017 Add an inbound `suggests`/`requires` edge from an existing directive/paradigm (WP04)
- [ ] T018 Regenerate `src/doctrine/graph.yaml` via `spec-kitty doctrine regenerate-graph` (WP04)
- [ ] T019 Add a non-orphan DRG test asserting ≥1 inbound edge (WP04)

**Dependencies**: none (parallel; graph regen is single-writer). **Risks**: orphan stub = doctrine theater (FR-011 edge + test prevent it); no CI/agent-effort bleed (C-001).

## WP05 — applies_to_languages guard & diagnostic (Thread D / #2092)

**Goal**: Fail loud at authoring for `any`/`all` language tokens; name scope-filtered artifacts in the catalog-miss diagnostic (FR-012/013, SC-006, C-006).
**Priority**: P1. **Independent test**: `doctrine validate` rejects `[any]` with an actionable message; diagnostic names scope-filtered cause.
**Prompt**: [tasks/WP05-language-scope-guard.md](tasks/WP05-language-scope-guard.md)

- [ ] T020 Validate-time guard rejecting `applies_to_languages: [any]`/`[all]` in `cli/commands/doctrine.py` validate (WP05)
- [ ] T021 `scoping.py` defense-in-depth: normalize/clarify `any`/`all` handling (WP05)
- [ ] T022 `charter/_catalog_miss.py`: add "present-but-scope-filtered" diagnostic branch (WP05)
- [ ] T023 Tests: validate-time rejection + scope-filtered diagnostic (WP05)

**Dependencies**: none (parallel; de-risks WP04). **Risks**: prefer validate-time rejection over silent query-time wildcarding (C-006).

---

## Execution Notes

- **MVP**: WP01 + WP02 (the #2083 driver end-to-end).
- **Parallel lanes**: WP01→WP02 (lane A, sequential); WP03, WP04, WP05 independent.
- **Tests**: SC-001 (WP02), non-orphan (WP04), validate-rejection (WP05) are the non-fakeable acceptance anchors.
