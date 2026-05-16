# Tasks: WP-Prompt Governance Payload Completeness

**Mission**: `wp-prompt-governance-payload-01KRR8HS`
**Mission ID**: `01KRR8HS66A7NFV64HHPXG2JJE`
**Branch**: `feat/org-doctrine-layer` → `feat/org-doctrine-layer`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Total WPs**: 7 | **Total subtasks**: 31

---

## Work Package Overview

| WP | Title | Dependencies | FRs covered | Subtasks | agent_profile |
|---|---|---|---|---|---|
| WP01 | Schema extensions for `Directive.references` and `authority_paths` | — | FR-006 (partial), FR-008 (partial) | T001–T003 | python-pedro |
| WP02 | charter sync: catalog-citation detection + `authority_paths` extraction | WP01 | FR-006, FR-007 (partial), FR-008 (partial) | T004–T008 | python-pedro |
| WP03 | Make `build_charter_context(profile=)` load-bearing | WP01 | FR-002, FR-004 (partial) | T009–T013 | python-pedro |
| WP04 | Render authority paths + critical-section bodies in compact/bootstrap text | WP02, WP03 | FR-001, FR-003 | T014–T018 | python-pedro |
| WP05 | Token-budget mechanism + fetch substitution | WP04 | NFR-001 | T019–T022 | python-pedro |
| WP06 | Wire WP frontmatter `agent_profile` through prompt builder + add Governance Payload Contract section | WP03, WP04 | FR-005, FR-010 | T023–T028 | python-pedro |
| WP07 | Dogfood: declare `template_set` + `available_tools` + `authority_paths` in `.kittify/charter/charter.md` | WP02 | FR-009 | T029–T031 | curator-carla |

WP06 and WP07 can run in parallel after WP02 + WP03 + WP04 land.
WP02 and WP03 can run in parallel after WP01.

---

## FR Coverage Matrix

| FR | Statement (summary) | WP(s) |
|---|---|---|
| FR-001 | Action-critical section bodies surface verbatim or with fetch + when-doing | WP04 |
| FR-002 | `profile=` parameter is load-bearing; profile-cited directives + tactics surface | WP03 |
| FR-003 | `Project authority paths:` block (defaults + charter-declared) appears in bootstrap output | WP04 |
| FR-004 | `_governance_context` forwards `agent_profile` from WP frontmatter to `build_charter_context` | WP03 (resolver side), WP06 (wiring side) |
| FR-005 | Runtime templates either drop the forbid clause OR carry `## Governance Payload Contract` | WP06 |
| FR-006 | `charter sync` detects `DIRECTIVE_NNN` / tactic-id citations and emits `references:` | WP01 (schema), WP02 (detection) |
| FR-007 | Charter may declare `template_set:` and `available_tools:` fenced YAML; sync persists them; no fallback diagnostic | WP02 (sync side), WP07 (charter side) |
| FR-008 | Charter may declare `authority_paths:` extending the default set | WP01 (schema), WP02 (sync), WP04 (render) |
| FR-009 | Spec-kitty's own `.kittify/charter/charter.md` declares `template_set` + `available_tools` | WP07 |
| FR-010 | Aggregate self-sufficiency: `test_implement_prompt_self_sufficiency` passes | WP06 (gate) |

---

## ATDD Test → WP Mapping

The acceptance gate is `tests/specify_cli/next/test_wp_prompt_governance_contract.py` (NFR-003: 23/23 pass).

| Test | WP that turns it green |
|---|---|
| `test_implement_prompt_regression_vigilance_body_or_fetch_with_when_doing_rule` | WP04 |
| `test_python_pedro_directive_010_referenced_in_implement_prompt` | WP03 |
| `test_implement_prompt_references_glossary_path` | WP04 |
| `test_implement_prompt_references_adr_path` | WP04 |
| `test_template_either_drops_forbid_or_guarantees_governance_payload` | WP06 |
| `test_charter_sync_emits_cross_link_when_body_cites_catalog_id` | WP02 |
| `test_implement_prompt_self_sufficiency` | WP06 (aggregate; requires WP01–WP05 first) |
| `test_project_charter_declares_template_set` | WP07 |
| `test_project_charter_declares_available_tools` | WP07 |
| `test_implement_action_context_includes_profile_directive_references_when_profile_known` | WP03 |

The 14 currently-passing tests MUST remain green throughout (no regression).

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add `references: list[str] = []` to `charter.schemas.Directive` | WP01 | | [D] |
| T002 | Add `authority_paths: list[str] = []` to `charter.schemas.DoctrineSelectionConfig` | WP01 | [D] |
| T003 | Schema round-trip + backward-compat tests for the two new fields | WP01 | [D] |
| T004 | Add `DIRECTIVE_\d{3}` / tactic-id detection regex helper in `charter.extractor` | WP02 | | [D] |
| T005 | Extend `Extractor._extract_directives` to populate `Directive.references` from detected citations | WP02 | | [D] |
| T006 | Extend `Extractor._merge_doctrine_selection` to read `authority_paths:` from fenced YAML blocks | WP02 | [D] |
| T007 | Extend the same site to persist `template_set:` and `available_tools:` from the YAML block (FR-007) | WP02 | [D] |
| T008 | Unit tests in `tests/charter/test_sync_references.py` (citation detection, authority_paths/template_set extraction, no-citation no-error) | WP02 | [D] |
| T009 | Replace `_ = profile` at `src/charter/context.py:92` with a real profile lookup helper | WP03 | |
| T010 | Add `_load_agent_profile(profile_id)` helper in `charter.context` delegating to `doctrine.agent_profiles.AgentProfileRepository` | WP03 | |
| T011 | Add `_render_profile_directives(profile, service)` renderer | WP03 | |
| T012 | Add `_render_profile_tactics(profile, service)` renderer | WP03 | [P] |
| T013 | Unit tests in `tests/charter/test_context_profile.py` (known profile, unknown profile graceful skip, empty references) | WP03 | [P] |
| T014 | Add `_render_authority_paths(repo_root, doctrine_selection)` helper (defaults + charter-declared) | WP04 | |
| T015 | Add `_render_critical_section_bodies(charter_content, action)` helper (slice headings) | WP04 | |
| T016 | Wire both renderers into `_render_bootstrap_text` and the compact-context surface | WP04 | |
| T017 | Unit tests in `tests/charter/test_context_authority_paths.py` (default present/absent, additive declarations, missing dirs silent) | WP04 | [P] |
| T018 | Unit tests in `tests/charter/test_context_section_bodies.py` (Terminology Canon, Regression Vigilance, Code Review Checklist surface) | WP04 | [P] |
| T019 | Implement `_apply_token_budget(text, budget=32_000)` substitution mechanism | WP05 | |
| T020 | Implement the fetch + when-doing stanza formatter (`directive:`, `tactic:`, `section:` selectors) | WP05 | |
| T021 | Measure baseline against `layered-doctrine-org-layer-01KRNPEE` WP01–WP10 prompts (C-004); record in WP notes | WP05 | |
| T022 | Unit tests in `tests/charter/test_context_token_budget.py` (under budget unchanged, longest-first substitution, severely over → all substituted, warning emitted) | WP05 | [P] |
| T023 | In `_build_wp_prompt` extract `wp_meta.agent_profile` and pass to `_governance_context` | WP06 | |
| T024 | In `_governance_context` forward `profile=` to `build_charter_context` | WP06 | |
| T025 | Add `## Governance Payload Contract` section to `src/specify_cli/missions/software-dev/command-templates/implement.md` (four-block schema) | WP06 | |
| T026 | Add `## Governance Payload Contract` section to `src/specify_cli/missions/software-dev/command-templates/review.md` (reviewer-oriented variant) | WP06 | [P] |
| T027 | Add architectural test `tests/architectural/test_template_governance_payload_contract.py` (template promise ↔ resolver reality) | WP06 | [P] |
| T028 | Run full ATDD suite; confirm 23/23 pass | WP06 | |
| T029 | Add `## Charter Resolution Hints` fenced YAML block to `.kittify/charter/charter.md` declaring `template_set: software-dev-default` | WP07 | |
| T030 | Extend the same block with `available_tools: [git, spec-kitty, pytest, mypy, ruff]` and `authority_paths: [glossary/contexts/, architecture/2.x/adr/]` | WP07 | |
| T031 | Run `spec-kitty charter sync`; verify no `Template set not selected in charter; fallback ... applied` diagnostic | WP07 | |

---

## Critical Path

`WP01 → WP02 → WP04 → WP05 → WP06`

(WP03 forks from WP01 in parallel with WP02 and rejoins at WP04.)

Total critical-path length: 5 WPs (WP01 → WP02 → WP04 → WP05 → WP06).

---

## Parallel Opportunities

| After landing | Can run in parallel |
|---|---|
| WP01 | WP02 + WP03 |
| WP04 | WP05 only (WP05 is the next critical-path node) |
| WP02 + WP03 + WP04 | WP06 + WP07 |

WP07 (charter dogfood) depends only on WP02 (the sync side), so it can land any time after WP02 completes — it does not need WP03, WP04, WP05, or WP06.

---

---

## Work Packages

### WP01 — Schema extensions for `Directive.references` and `authority_paths`

**Dependencies**: none
**FRs**: FR-006 (partial), FR-008 (partial), NFR-005
**Subtasks**: T001, T002, T003
**Agent profile**: python-pedro
**Owned**: `src/charter/schemas.py`, `tests/charter/test_schemas_additive_fields.py`

Pure schema change. See [tasks/WP01-schema-extensions.md](tasks/WP01-schema-extensions.md).

---

### WP02 — charter sync: catalog-citation detection + `authority_paths` extraction

**Dependencies**: WP01
**FRs**: FR-006, FR-007, FR-008, NFR-005
**Subtasks**: T004, T005, T006, T007, T008
**Agent profile**: python-pedro
**Owned**: `src/charter/extractor.py`, `src/charter/sync.py`

Detects `DIRECTIVE_NNN` citations and reads fenced YAML resolver-input declarations.
See [tasks/WP02-charter-sync-extensions.md](tasks/WP02-charter-sync-extensions.md).

---

### WP03 — Make `build_charter_context(profile=)` load-bearing

**Dependencies**: WP01
**FRs**: FR-002, FR-004 (resolver side), NFR-004
**Subtasks**: T009, T010, T011, T012, T013
**Agent profile**: python-pedro
**Owned**: `src/charter/context.py`

Profile lookup via doctrine layer; emits profile-cited directives/tactics sections.
See [tasks/WP03-build-charter-context-profile.md](tasks/WP03-build-charter-context-profile.md).

---

### WP04 — Render authority paths and critical-section bodies in compact/bootstrap text

**Dependencies**: WP02, WP03
**FRs**: FR-001, FR-003, NFR-004
**Subtasks**: T014, T015, T016, T017, T018
**Agent profile**: python-pedro
**Owned**: `src/charter/context.py`

Two new rendered sections: `Project authority paths:` and
`Action-Critical Charter Sections (<action>):`.
See [tasks/WP04-authority-paths-and-section-bodies.md](tasks/WP04-authority-paths-and-section-bodies.md).

---

### WP05 — Token-budget enforcement and fetch substitution

**Dependencies**: WP04
**FRs**: NFR-001, NFR-002
**Subtasks**: T019, T020, T021, T022
**Agent profile**: python-pedro
**Owned**: `src/charter/context.py`, `scripts/measure-wp-prompt.py`

Auto-substitute longest bodies with fetch stanzas under 32 000 char budget.
See [tasks/WP05-token-budget-and-fetch-substitution.md](tasks/WP05-token-budget-and-fetch-substitution.md).

---

### WP06 — Wire WP frontmatter `agent_profile` through prompt builder + Governance Payload Contract templates

**Dependencies**: WP03, WP04
**FRs**: FR-004 (wiring), FR-005, FR-010, NFR-003
**Subtasks**: T023, T024, T025, T026, T027, T028
**Agent profile**: python-pedro
**Owned**: `src/specify_cli/next/prompt_builder.py`,
`src/specify_cli/missions/software-dev/command-templates/implement.md`,
`src/specify_cli/missions/software-dev/command-templates/review.md`

Final integration WP. Gate for 23/23 ATDD pass.
See [tasks/WP06-prompt-builder-wiring-and-templates.md](tasks/WP06-prompt-builder-wiring-and-templates.md).

---

### WP07 — Dogfood: declare `template_set` + `available_tools` + `authority_paths` in spec-kitty's own charter

**Dependencies**: WP02
**FRs**: FR-007, FR-008, FR-009, C-005
**Subtasks**: T029, T030, T031
**Agent profile**: curator-carla
**Owned**: `.kittify/charter/charter.md`

Markdown-only change. Eliminates fallback diagnostics on spec-kitty's own missions.
See [tasks/WP07-dogfood-charter-resolution-hints.md](tasks/WP07-dogfood-charter-resolution-hints.md).

---

## References

- `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23 ATDD tests (executable spec).
- `docs/development/wp-prompt-governance-atdd-findings.md` — per-test failure-to-FR mapping.
- `docs/development/org-doctrine-layer-architecture-review.md` — root-cause analysis.
- `contracts/charter-context-resolver.md`, `contracts/charter-sync-cross-link.md`, `contracts/runtime-template-governance-payload-contract.md` — the three contracts this mission must satisfy.
- `data-model.md` — schema additions (additive, NFR-005 by construction).
