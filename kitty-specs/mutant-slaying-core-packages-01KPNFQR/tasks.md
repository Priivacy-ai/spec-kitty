# Tasks: Mutant Slaying in Core Packages

**Mission**: `mutant-slaying-core-packages-01KPNFQR`
**Target branch**: `feature/711-mutant-slaying`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

This task list operationalises the three phases from `spec.md` into **11 work packages** totalling **58 subtasks**. Each WP targets exactly one sub-module so that scoped `mutmut run "<dotted.pattern>*"` invocations can verify kills independently. All WP PRs land on `feature/711-mutant-slaying`; the final mission PR targets `main` (per C-007).

## Baseline reference

All survivor counts and mutant IDs cited below are from the 2026-04-20 partial mutmut run captured in `docs/development/mutation-testing-findings.md`. Phase 2 and Phase 3 WPs may refine against a fresher baseline (NFR-007: re-sample ≤ 7 days old before starting a phase); compat + kernel survivor lists are stable (done in baseline).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Kill `_validate_entry` survivors (7) | WP01 | |
| T002 | Kill `_validate_canonical_import` survivors (6) | WP01 | [P] |
| T003 | Kill `_validate_version_order` survivors (2) | WP01 | [P] |
| T004 | Kill `validate_registry` (top-level) survivors (3) | WP01 | |
| T005 | Kill `load_registry` + `RegistrySchemaError` survivors (2) | WP01 | [P] |
| T006 | Rescope mutmut, verify, append findings residuals | WP01 | |
| T007 | Kill `_safe_re` compile/re2 survivors (~8) | WP02 | [P] |
| T008 | Kill `_safe_re` search/match-family survivors (~10) | WP02 | [P] |
| T009 | Kill `_safe_re` split/sub/subn survivors (~8) | WP02 | [P] |
| T010 | Rescope mutmut, verify, append findings residuals | WP02 | |
| T011 | Kill `kernel.paths.render_runtime_path` survivors (6) | WP03 | [P] |
| T012 | Kill `kernel.paths.get_kittify_home` survivors (10) | WP03 | [P] |
| T013 | Kill `kernel.paths.get_package_asset_root` survivor (1) | WP03 | [P] |
| T014 | Kill `kernel.atomic.atomic_write` survivors (13) | WP03 | [P] |
| T015 | Kill `kernel.glossary_runner.register` survivor (1) | WP03 | [P] |
| T016 | Rescope mutmut, verify, append findings residuals | WP03 | |
| T017 | Kill `doctrine.resolver._resolve_asset` survivors | WP04 | |
| T018 | Kill `doctrine.resolver._warn_legacy_asset` + nudge survivors | WP04 | [P] |
| T019 | Kill `doctrine.resolver.resolve_mission/command/template` survivors | WP04 | [P] |
| T020 | Kill `doctrine.resolver` tier-comparison and fallback-branch survivors | WP04 | |
| T021 | Rescope mutmut, verify ≥ 80 %, append findings residuals | WP04 | |
| T022 | Kill `doctrine.agent_profiles` repository/loader survivors | WP05 | |
| T023 | Kill `doctrine.agent_profiles` precedence-and-merge survivors | WP05 | [P] |
| T024 | Kill `doctrine.agent_profiles` validation-and-warning survivors | WP05 | [P] |
| T025 | Kill `doctrine.agent_profiles` YAML/frontmatter parsing survivors | WP05 | [P] |
| T026 | Rescope mutmut, verify ≥ 60 %, append findings residuals | WP05 | |
| T027 | Kill `doctrine.missions` schema-validation survivors | WP06 | |
| T028 | Kill `doctrine.missions` step-contract reference survivors | WP06 | [P] |
| T029 | Kill `doctrine.missions` version/precedence survivors | WP06 | [P] |
| T030 | Kill `doctrine.missions` error-formatting survivors | WP06 | [P] |
| T031 | Rescope mutmut, verify ≥ 60 %, append findings residuals | WP06 | |
| T032 | Kill `doctrine.shared.errors` class-behaviour survivors | WP07 | |
| T033 | Kill `doctrine.shared.exceptions` payload survivors | WP07 | [P] |
| T034 | Kill `doctrine.shared` inline-reference-check survivors | WP07 | [P] |
| T035 | Rescope mutmut, verify ≥ 60 %, append findings residuals | WP07 | |
| T036 | Kill `charter.resolver.resolve_governance` precedence survivors | WP08 | |
| T037 | Kill `charter.resolver` fallback-branch survivors | WP08 | [P] |
| T038 | Kill `charter.resolver.resolve_governance_for_profile` survivors | WP08 | [P] |
| T039 | Kill `charter.resolver.collect_governance_diagnostics` survivors | WP08 | [P] |
| T040 | Rescope mutmut, verify ≥ 80 %, append findings residuals | WP08 | |
| T041 | Kill `charter.context` policy-summary-extraction survivors | WP09 | |
| T042 | Kill `charter.context` action-doctrine-routing survivors | WP09 | [P] |
| T043 | Kill `charter.context` reference-loading survivors | WP09 | [P] |
| T044 | Kill `charter.context` first-load-vs-compact survivors | WP09 | [P] |
| T045 | Kill `charter.context` bootstrap-edge-case survivors | WP09 | [P] |
| T046 | Rescope mutmut, verify ≥ 60 %, append findings residuals | WP09 | |
| T047 | Kill `charter.synthesizer.evidence` bundle-hash survivors | WP10 | |
| T048 | Kill `charter.synthesizer.neutrality` lint-gate survivors | WP10 | [P] |
| T049 | Kill `charter.synthesizer.request` threading survivors | WP10 | [P] |
| T050 | Kill `charter.synthesizer.orchestrator` pipeline survivors | WP10 | [P] |
| T051 | Kill `charter.synthesizer.bundle` packaging survivors | WP10 | [P] |
| T052 | Assess residual survivor count; split WP if >100 remain | WP10 | |
| T053 | Rescope mutmut, verify ≥ 60 %, append findings residuals | WP10 | |
| T054 | Kill `charter.evidence.code_reader` collector survivors | WP11 | |
| T055 | Kill `charter.evidence.corpus_loader` survivors | WP11 | [P] |
| T056 | Kill `charter.evidence.orchestrator` invariant survivors | WP11 | [P] |
| T057 | Kill `charter.evidence` hash-computation survivors | WP11 | [P] |
| T058 | Rescope mutmut, verify ≥ 60 %, append findings residuals | WP11 | |

*`[P]` indicates subtasks inside the same WP that touch different test files and are safe to parallelise within the WP's own session.*

---

## Phase 1 — Narrow-surface foundation (compat + kernel)

### WP01 — Kill `specify_cli.compat.registry` validator survivors

- **Goal**: Bring `compat.registry` to ≥ 80 % mutation score by killing all 20 current survivors (FR-001 / NFR-001).
- **Priority**: P1 — first deliverable; demonstrates the pattern.
- **Independent test**: `uv run mutmut run "specify_cli.compat*"` reports ≤ 4 survivors (or equivalent-mutant annotations with rationale).
- **Prompt**: [tasks/WP01-kill-compat-registry-survivors.md](tasks/WP01-kill-compat-registry-survivors.md) (~450 lines)
- **Subtasks**:
  - [ ] T001 Kill `_validate_entry` survivors (7)
  - [ ] T002 Kill `_validate_canonical_import` survivors (6)
  - [ ] T003 Kill `_validate_version_order` survivors (2)
  - [ ] T004 Kill top-level `validate_registry` survivors (3)
  - [ ] T005 Kill `load_registry` + `RegistrySchemaError` survivors (2)
  - [ ] T006 Rescope mutmut, verify, append findings residuals
- **Dependencies**: None. Start here.
- **Parallelizable**: T002, T003, T005 touch different test functions and can be implemented in parallel within this WP's session.

### WP02 — Kill `kernel._safe_re` survivors

- **Goal**: Bring `kernel._safe_re` to ≥ 80 % mutation score by killing ~26 survivors across the regex-safety wrapper family (FR-002 / NFR-001).
- **Priority**: P1 — regex safety underpins every upstream guard.
- **Independent test**: `uv run mutmut run "kernel._safe_re*"` reports ≤ 5 survivors (≥ 80 %).
- **Prompt**: [tasks/WP02-kill-kernel-safe-re-survivors.md](tasks/WP02-kill-kernel-safe-re-survivors.md) (~350 lines)
- **Subtasks**:
  - [ ] T007 Kill compile / re2 compile survivors (~8)
  - [ ] T008 Kill search / match / findall / finditer / fullmatch survivors (~10)
  - [ ] T009 Kill split / sub / subn survivors (~8)
  - [ ] T010 Rescope mutmut, verify, append findings residuals
- **Dependencies**: None.

### WP03 — Kill `kernel.paths` + `kernel.atomic` + `kernel.glossary_runner` survivors

- **Goal**: Bring the remaining kernel sub-modules to ≥ 60 % mutation score (FR-003 / FR-004 / NFR-002).
- **Priority**: P1 — closes Phase 1.
- **Independent test**: scoped mutmut runs per sub-module each hit target.
- **Prompt**: [tasks/WP03-kill-kernel-paths-atomic-runner.md](tasks/WP03-kill-kernel-paths-atomic-runner.md) (~450 lines)
- **Subtasks**:
  - [ ] T011 Kill `paths.render_runtime_path` survivors (6)
  - [ ] T012 Kill `paths.get_kittify_home` survivors (10)
  - [ ] T013 Kill `paths.get_package_asset_root` survivor (1)
  - [ ] T014 Kill `atomic.atomic_write` survivors (13)
  - [ ] T015 Kill `glossary_runner.register` survivor (1)
  - [ ] T016 Rescope mutmut, verify, append findings residuals
- **Dependencies**: None.

---

## Phase 2 — Doctrine core

**Precondition for Phase 2 planning**: fresh mutmut baseline ≤ 7 days old (NFR-007). Subtask IDs T017–T035 below reference the 2026-04-20 survivor counts; individual WP prompts re-derive concrete mutant IDs from a fresh run at the start of implementation.

### WP04 — Kill `doctrine.resolver` survivors (CORE, ≥ 80 %)

- **Goal**: Bring `doctrine.resolver` to ≥ 80 % mutation score (FR-005 / NFR-001).
- **Priority**: P2 — primary doctrine target; used at every mission boot.
- **Independent test**: `uv run mutmut run "doctrine.resolver*"` ≥ 80 %.
- **Prompt**: [tasks/WP04-kill-doctrine-resolver-survivors.md](tasks/WP04-kill-doctrine-resolver-survivors.md) (~450 lines)
- **Subtasks**:
  - [ ] T017 Kill `_resolve_asset` survivors
  - [ ] T018 Kill `_warn_legacy_asset` + migrate-nudge survivors
  - [ ] T019 Kill `resolve_mission` / `resolve_command` / `resolve_template` survivors
  - [ ] T020 Kill tier-comparison and fallback-branch survivors
  - [ ] T021 Rescope mutmut, verify ≥ 80 %, append findings residuals
- **Dependencies**: WP01 (validates that the Phase-1 kill-the-survivor pattern is working end-to-end before starting larger-scope doctrine work).

### WP05 — Kill `doctrine.agent_profiles` survivors

- **Goal**: Bring `doctrine.agent_profiles` to ≥ 60 % mutation score (FR-006 / NFR-002).
- **Priority**: P2
- **Independent test**: `uv run mutmut run "doctrine.agent_profiles*"` ≥ 60 %.
- **Prompt**: [tasks/WP05-kill-doctrine-agent-profiles-survivors.md](tasks/WP05-kill-doctrine-agent-profiles-survivors.md) (~400 lines)
- **Subtasks**:
  - [ ] T022 Kill repository / loader survivors
  - [ ] T023 Kill precedence / merge survivors
  - [ ] T024 Kill validation / warning survivors
  - [ ] T025 Kill YAML / frontmatter parsing survivors
  - [ ] T026 Rescope mutmut, verify ≥ 60 %, append findings residuals
- **Dependencies**: WP04 (same kill methodology; resolver work establishes the doctrine-test conventions).

### WP06 — Kill `doctrine.missions` survivors

- **Goal**: Bring `doctrine.missions` to ≥ 60 % mutation score (FR-007 / NFR-002).
- **Priority**: P2
- **Independent test**: `uv run mutmut run "doctrine.missions*"` ≥ 60 %.
- **Prompt**: [tasks/WP06-kill-doctrine-missions-survivors.md](tasks/WP06-kill-doctrine-missions-survivors.md) (~400 lines)
- **Subtasks**:
  - [ ] T027 Kill schema-validation survivors
  - [ ] T028 Kill step-contract reference survivors
  - [ ] T029 Kill version / precedence survivors
  - [ ] T030 Kill error-formatting survivors
  - [ ] T031 Rescope mutmut, verify ≥ 60 %, append findings residuals
- **Dependencies**: WP04.

### WP07 — Kill `doctrine.shared` survivors

- **Goal**: Bring `doctrine.shared` to ≥ 60 % mutation score (FR-008 / NFR-002).
- **Priority**: P2 — closes Phase 2.
- **Independent test**: `uv run mutmut run "doctrine.shared*"` ≥ 60 %.
- **Prompt**: [tasks/WP07-kill-doctrine-shared-survivors.md](tasks/WP07-kill-doctrine-shared-survivors.md) (~300 lines)
- **Subtasks**:
  - [ ] T032 Kill `errors` class-behaviour survivors
  - [ ] T033 Kill `exceptions` payload survivors
  - [ ] T034 Kill inline-reference-check survivors
  - [ ] T035 Rescope mutmut, verify ≥ 60 %, append findings residuals
- **Dependencies**: WP04.

---

## Phase 3 — Charter core

**Precondition for Phase 3 planning**: fresh mutmut baseline ≤ 7 days old (NFR-007). Especially critical for `charter.synthesizer` where ~1800 mutants were still pending in the partial 2026-04-20 baseline.

### WP08 — Kill `charter.resolver` survivors (CORE, ≥ 80 %)

- **Goal**: Bring `charter.resolver` to ≥ 80 % mutation score (FR-009 / NFR-001).
- **Priority**: P3 — primary charter target.
- **Independent test**: `uv run mutmut run "charter.resolver*"` ≥ 80 %.
- **Prompt**: [tasks/WP08-kill-charter-resolver-survivors.md](tasks/WP08-kill-charter-resolver-survivors.md) (~450 lines)
- **Subtasks**:
  - [ ] T036 Kill `resolve_governance` precedence survivors
  - [ ] T037 Kill fallback-branch survivors
  - [ ] T038 Kill `resolve_governance_for_profile` survivors
  - [ ] T039 Kill `collect_governance_diagnostics` survivors
  - [ ] T040 Rescope mutmut, verify ≥ 80 %, append findings residuals
- **Dependencies**: WP07 (Phase 2 completion signals mature doctrine-test patterns that transfer to charter).

### WP09 — Kill `charter.context` survivors

- **Goal**: Bring `charter.context` to ≥ 60 % mutation score (FR-011 / NFR-002).
- **Priority**: P3
- **Independent test**: `uv run mutmut run "charter.context*"` ≥ 60 %.
- **Prompt**: [tasks/WP09-kill-charter-context-survivors.md](tasks/WP09-kill-charter-context-survivors.md) (~500 lines)
- **Subtasks**:
  - [ ] T041 Kill policy-summary-extraction survivors
  - [ ] T042 Kill action-doctrine-routing survivors
  - [ ] T043 Kill reference-loading survivors
  - [ ] T044 Kill first-load-vs-compact-load survivors
  - [ ] T045 Kill bootstrap-edge-case survivors
  - [ ] T046 Rescope mutmut, verify ≥ 60 %, append findings residuals
- **Dependencies**: WP07.

### WP10 — Kill `charter.synthesizer` survivors

- **Goal**: Bring `charter.synthesizer` to ≥ 60 % mutation score (FR-010 / NFR-002).
- **Priority**: P3 — largest single concentration of survivors (528+).
- **Independent test**: `uv run mutmut run "charter.synthesizer*"` ≥ 60 %.
- **Prompt**: [tasks/WP10-kill-charter-synthesizer-survivors.md](tasks/WP10-kill-charter-synthesizer-survivors.md) (~500 lines)
- **Subtasks**:
  - [ ] T047 Kill `evidence` bundle-hash / corpus-snapshot survivors
  - [ ] T048 Kill `neutrality` lint-gate survivors
  - [ ] T049 Kill `request` threading survivors
  - [ ] T050 Kill `orchestrator` pipeline survivors
  - [ ] T051 Kill `bundle` packaging survivors
  - [ ] T052 Assess residual count; split follow-up WP if > 100 remain
  - [ ] T053 Rescope mutmut, verify ≥ 60 %, append findings residuals
- **Dependencies**: WP07.
- **Note**: This WP is at the maximum recommended size (7 subtasks). If the fresh baseline shows a survivor count higher than current estimates, T052 may trigger a follow-up WP (out-of-scope for initial planning; amends this file).

### WP11 — Kill `charter.evidence` survivors

- **Goal**: Bring `charter.evidence` to ≥ 60 % mutation score (FR-012 / NFR-002).
- **Priority**: P3 — closes the mission.
- **Independent test**: `uv run mutmut run "charter.evidence*"` ≥ 60 %.
- **Prompt**: [tasks/WP11-kill-charter-evidence-survivors.md](tasks/WP11-kill-charter-evidence-survivors.md) (~400 lines)
- **Subtasks**:
  - [ ] T054 Kill `code_reader` collector survivors
  - [ ] T055 Kill `corpus_loader` survivors
  - [ ] T056 Kill `orchestrator` invariant survivors
  - [ ] T057 Kill hash-computation survivors
  - [ ] T058 Rescope mutmut, verify ≥ 60 %, append findings residuals
- **Dependencies**: WP07.

---

## Dependencies summary

Phase-1 WPs have no dependencies. Phase-2 WPs depend on WP01. Phase-3 WPs depend on WP07. Within a phase, WPs are internally parallel (no intra-phase dependencies beyond the shared phase-boundary anchor).

- WP01: no dependencies
- WP02: no dependencies
- WP03: no dependencies
- WP04: depends on WP01
- WP05: depends on WP04
- WP06: depends on WP04
- WP07: depends on WP04
- WP08: depends on WP07
- WP09: depends on WP07
- WP10: depends on WP07
- WP11: depends on WP07

## Sizing summary

- **Total WPs**: 11
- **Total subtasks**: 58
- **Average subtasks per WP**: ~5.3 (within the 3–7 target range)
- **Max WP size**: WP10 with 7 subtasks (within max of 10)
- **Prompt size estimates**: 300–500 lines per WP; all within target.

## MVP recommendation

**WP01 (compat.registry)** is the MVP. It's the smallest and most self-contained — 20 survivors in a single file, stable baseline, clear target. A contributor unfamiliar with mutation testing can pick it up, follow the prompt end-to-end, and produce a ship-ready PR in a focused session. It sets the kill-the-survivor pattern that WP02–WP11 follow.
