# Tasks: Charter End-User Docs Parity (#828)

**Mission**: `charter-end-user-docs-828-01KQCSYD`
**Branch**: `docs/charter-end-user-docs-828` → PR → `main`
**Generated**: 2026-04-29

---

## Summary

10 work packages, 45 subtasks covering gap analysis, navigation architecture, 14 new documentation pages, 5 updated pages, a validation pass, and a release handoff. Content WPs (WP02-WP08) can all run in parallel after WP01 completes.

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Produce gap-analysis.md with Divio coverage matrix | WP01 | — |
| T002 | Update docs/toc.yml (add 3x/, relabel 2x/) | WP01 | — |
| T003 | Create docs/3x/toc.yml | WP01 | — |
| T004 | Update/create section toc.yml files (tutorials/, how-to/, explanation/, reference/, migration/) | WP01 | — |
| T005 | Update docs/2x/index.md with archive notice | WP01 | — |
| T006 | Write docs/3x/index.md (Charter hub landing) | WP02 | [P] |
| T007 | Write docs/3x/charter-overview.md (synthesis, DRG, bundle) | WP02 | [P] |
| T008 | Write docs/3x/governance-files.md (authoritative vs generated) | WP02 | [P] |
| T009 | Verify docs/3x/ pages integrate with toc.yml | WP02 | [P] |
| T010 | Write docs/tutorials/charter-governed-workflow.md end-to-end | WP03 | [P] |
| T011 | Smoke-test tutorial command snippets in temp project | WP03 | [P] |
| T012 | Verify tutorial in toc.yml; add cross-links | WP03 | [P] |
| T013 | Update docs/how-to/setup-governance.md (Charter synthesis + bundle; remove 2.x prereq) | WP04 | [P] |
| T014 | Write docs/how-to/synthesize-doctrine.md | WP04 | [P] |
| T015 | Write docs/how-to/run-governed-mission.md | WP04 | [P] |
| T016 | Update docs/how-to/manage-glossary.md for Charter runtime integration | WP04 | [P] |
| T017 | Smoke-test synthesis/mission snippets; add cross-links to 3x hub | WP04 | [P] |
| T018 | Write docs/how-to/use-retrospective-learning.md | WP05 | [P] |
| T019 | Write docs/how-to/troubleshoot-charter.md | WP05 | [P] |
| T020 | Smoke-test retro snippets; add cross-links | WP05 | [P] |
| T021 | Write docs/explanation/charter-synthesis-drg.md | WP06 | [P] |
| T022 | Write docs/explanation/governed-profile-invocation.md | WP06 | [P] |
| T023 | Write docs/explanation/retrospective-learning-loop.md (Divio-shaped) | WP06 | [P] |
| T024 | Convert docs/retrospective-learning-loop.md to redirect stub | WP06 | [P] |
| T025 | Update docs/explanation/toc.yml; add cross-links from explanation pages | WP06 | [P] |
| T026 | Run uv run spec-kitty --help for Charter-era command surfaces | WP07 | [P] |
| T027 | Write docs/reference/charter-commands.md | WP07 | [P] |
| T028 | Update docs/reference/cli-commands.md with Charter-era section | WP07 | [P] |
| T029 | Write docs/reference/profile-invocation.md | WP07 | [P] |
| T030 | Verify docs/reference/toc.yml has all reference page entries | WP07 | [P] |
| T031 | Write docs/reference/retrospective-schema.md | WP08 | [P] |
| T032 | Write docs/migration/from-charter-2x.md | WP08 | [P] |
| T033 | Review docs/explanation/documentation-mission.md for phase accuracy | WP08 | [P] |
| T034 | Update docs/explanation/documentation-mission.md if stale | WP08 | [P] |
| T035 | Verify docs/migration/toc.yml and reference/toc.yml have correct entries | WP08 | [P] |
| T036 | Run uv run pytest tests/docs/ -q (zero failures) | WP09 | — |
| T037 | Check new pages reachable from toc.yml; grep TODO markers | WP09 | — |
| T038 | Verify CLI flags in charter-commands.md match --help | WP09 | — |
| T039 | Verify doc mission phases in changed pages match mission-runtime.yaml | WP09 | — |
| T040 | Execute tutorial smoke-test from fresh temp repo | WP09 | — |
| T041 | Write checklists/validation-report.md with evidence | WP09 | — |
| T042 | Produce release-handoff.md (FR-015) | WP10 | — |
| T043 | Update docs release notes/changelog if maintained | WP10 | — |
| T044 | Final grep for stale text ("TODO", "2.x" in current-facing pages) | WP10 | — |
| T045 | Verify branch is clean and ready for PR | WP10 | — |

---

## Work Packages


---

**Phase 1: Foundation

## WP01 — Gap Analysis and Navigation Architecture

**Goal**: Produce the gap-analysis.md and establish the navigation infrastructure (toc.yml files, 2x archive label).
**Priority**: P0 — All content WPs depend on this.
**Prompt**: [WP01-gap-analysis-and-navigation-architecture.md](tasks/WP01-gap-analysis-and-navigation-architecture.md)
**Estimated size**: ~280 lines

**Subtasks**:

- [ ] T001 Produce gap-analysis.md with Divio coverage matrix (WP01)
- [ ] T002 Update docs/toc.yml (add 3x/, relabel 2x/ as Archive) (WP01)
- [ ] T003 Create docs/3x/toc.yml (WP01)
- [ ] T004 Update/create section toc.yml files for tutorials/, how-to/, explanation/, reference/, migration/ (WP01)
- [ ] T005 Update docs/2x/index.md with archive notice and forward pointer to docs/3x/ (WP01)

**Dependencies**: none
**Parallelization**: none; all content WPs (WP02–WP08) are blocked on this.

---


---

**Phase 2: Content Generation (parallel)

## WP02 — docs/3x/ Charter Hub

**Goal**: Create the docs/3x/ hub directory with the three core pages.
**Priority**: P0 — Referenced by all content WPs.
**Prompt**: [WP02-3x-charter-hub.md](tasks/WP02-3x-charter-hub.md)
**Estimated size**: ~350 lines

**Subtasks**:

- [ ] T006 Write docs/3x/index.md (Charter hub landing) (WP02)
- [ ] T007 Write docs/3x/charter-overview.md (synthesis, DRG, bundle, bootstrap vs compact) (WP02)
- [ ] T008 Write docs/3x/governance-files.md (authoritative vs generated files table) (WP02)
- [ ] T009 Verify docs/3x/ pages integrate with toc.yml from WP01 (WP02)

**Dependencies**: WP01
**Parallelization**: [P] with WP03, WP04, WP05, WP06, WP07, WP08

---

## WP03 — Charter End-to-End Tutorial

**Goal**: Write the single end-to-end Charter workflow tutorial (FR-017).
**Priority**: P0 — Highest-value user-facing deliverable.
**Prompt**: [WP03-charter-tutorial.md](tasks/WP03-charter-tutorial.md)
**Estimated size**: ~420 lines

**Subtasks**:

- [ ] T010 Write docs/tutorials/charter-governed-workflow.md — arc: governance setup → charter lint/bundle validate → charter synthesize → spec-kitty next → retrospect summary → next steps (WP03)
- [ ] T011 Smoke-test all command snippets in tutorial against a temp project (WP03)
- [ ] T012 Verify tutorial entry in docs/tutorials/toc.yml; add "See also" cross-links (WP03)

**Dependencies**: WP01
**Parallelization**: [P] with WP02, WP04, WP05, WP06, WP07, WP08

---

## WP04 — How-To: Governance, Synthesis, Missions, Glossary

**Goal**: Update setup-governance.md and write three new how-to pages for synthesis, missions, and glossary.
**Priority**: P0
**Prompt**: [WP04-howto-governance-synthesis-missions.md](tasks/WP04-howto-governance-synthesis-missions.md)
**Estimated size**: ~460 lines

**Subtasks**:

- [ ] T013 Update docs/how-to/setup-governance.md — add Charter bundle validation + synthesis flow; remove "Spec Kitty 2.x" prereq (WP04)
- [ ] T014 Write docs/how-to/synthesize-doctrine.md (dry-run, apply, status, lint, provenance, recovery) (WP04)
- [ ] T015 Write docs/how-to/run-governed-mission.md (spec-kitty next, composed steps, Charter context, blocked decisions) (WP04)
- [ ] T016 Update docs/how-to/manage-glossary.md for Charter glossary runtime integration (FR-011) (WP04)
- [ ] T017 Smoke-test synthesis/mission command snippets; add cross-links to docs/3x/ hub (WP04)

**Dependencies**: WP01
**Parallelization**: [P] with WP02, WP03, WP05, WP06, WP07, WP08

---

## WP05 — How-To: Retrospective and Troubleshooting

**Goal**: Write use-retrospective-learning.md and troubleshoot-charter.md.
**Priority**: P1
**Prompt**: [WP05-howto-retrospective-troubleshooting.md](tasks/WP05-howto-retrospective-troubleshooting.md)
**Estimated size**: ~380 lines

**Subtasks**:

- [ ] T018 Write docs/how-to/use-retrospective-learning.md (retrospect summary, agent retrospect synthesize default dry-run / --apply with --mission <mission>, facilitator failures, HiC/autonomous, skip semantics, exit codes) (WP05)
- [ ] T019 Write docs/how-to/troubleshoot-charter.md (stale bundle, missing doctrine, compact context, retro gate failure, synthesizer rejection) (WP05)
- [ ] T020 Smoke-test retrospect command snippets; add cross-links to reference/retrospective-schema.md (WP05)

**Dependencies**: WP01
**Parallelization**: [P] with WP02, WP03, WP04, WP06, WP07, WP08

---

## WP06 — Explanation Pages

**Goal**: Write three Divio-shaped explanation pages and convert the root-level retrospective stub.
**Priority**: P1
**Prompt**: [WP06-explanation-pages.md](tasks/WP06-explanation-pages.md)
**Estimated size**: ~440 lines

**Subtasks**:

- [ ] T021 Write docs/explanation/charter-synthesis-drg.md (FR-003, FR-006) — DRG edges, bootstrap vs compact context, known limitations (WP06)
- [ ] T022 Write docs/explanation/governed-profile-invocation.md (FR-007) — (profile, action, gov-context) primitive; ask/advise/do; lifecycle trails (WP06)
- [ ] T023 Write docs/explanation/retrospective-learning-loop.md — Divio-shaped understanding doc (WP06)
- [ ] T024 Convert docs/retrospective-learning-loop.md to one-line redirect stub (WP06)
- [ ] T025 Update docs/explanation/toc.yml; add cross-links from explanation pages to how-to and reference pages (WP06)

**Dependencies**: WP01
**Parallelization**: [P] with WP02, WP03, WP04, WP05, WP07, WP08

---

## WP07 — Reference: CLI and Profile Invocation

**Goal**: Write charter-commands.md and profile-invocation.md; update cli-commands.md.
**Priority**: P0
**Prompt**: [WP07-reference-cli-profile.md](tasks/WP07-reference-cli-profile.md)
**Estimated size**: ~480 lines

**Subtasks**:

- [ ] T026 Run uv run spec-kitty --help and every Charter-era command surface required by #828 (`charter`, `profiles`, `ask`, `advise`, `do`, `profile-invocation`, `next`, `mission`, `glossary`, `retrospect`, `agent retrospect`) to capture current usage (WP07)
- [ ] T027 Write docs/reference/charter-commands.md — one section per subcommand, all flags verified against --help output (WP07)
- [ ] T028 Update docs/reference/cli-commands.md — add Charter-era section with cross-links to charter-commands.md (WP07)
- [ ] T029 Write docs/reference/profile-invocation.md — ask/advise/do flags, profile-invocation complete, trail fields, lifecycle states (WP07)
- [ ] T030 Verify docs/reference/toc.yml has all reference page entries (WP07)

**Dependencies**: WP01
**Parallelization**: [P] with WP02, WP03, WP04, WP05, WP06, WP08

---

## WP08 — Reference: Schema, Migration, Documentation Mission

**Goal**: Write retrospective-schema.md and from-charter-2x.md; update documentation-mission.md.
**Priority**: P1
**Prompt**: [WP08-reference-schema-migration.md](tasks/WP08-reference-schema-migration.md)
**Estimated size**: ~400 lines

**Subtasks**:

- [ ] T031 Write docs/reference/retrospective-schema.md — retrospective.yaml schema, proposal kinds, event fields, exit codes (WP08)
- [ ] T032 Write docs/migration/from-charter-2x.md — changed paths/commands, re-run steps after upgrade, known migration failures (WP08)
- [ ] T033 Review docs/explanation/documentation-mission.md for phase accuracy against mission-runtime.yaml (FR-009) (WP08)
- [ ] T034 Update docs/explanation/documentation-mission.md with current phases if stale (WP08)
- [ ] T035 Verify docs/migration/toc.yml and reference/toc.yml have correct entries (WP08)

**Dependencies**: WP01
**Parallelization**: [P] with WP02, WP03, WP04, WP05, WP06, WP07

---


---

**Phase 3: Quality Gate

## WP09 — Validation Pass

**Goal**: Run all docs validation checks; produce validation-report.md.
**Priority**: P0 — Required before PR.
**Prompt**: [WP09-validation.md](tasks/WP09-validation.md)
**Estimated size**: ~320 lines

**Subtasks**:

- [ ] T036 Run uv run pytest tests/docs/ -q — zero failures required (WP09)
- [ ] T037 Check all new/changed pages are reachable from toc.yml; grep for "TODO: register in docs nav" (WP09)
- [ ] T038 Verify all CLI flags in docs/reference/charter-commands.md match current uv run spec-kitty charter --help output (WP09)
- [ ] T039 Verify documentation mission phases in all changed pages match mission-runtime.yaml (WP09)
- [ ] T040 Execute charter-governed-workflow.md tutorial smoke-test from a fresh temp repo; verify no source-repo pollution (WP09)
- [ ] T041 Write kitty-specs/charter-end-user-docs-828-01KQCSYD/checklists/validation-report.md with evidence of each check (WP09)

**Dependencies**: WP02, WP03, WP04, WP05, WP06, WP07, WP08

---


---

**Phase 4: Ship

## WP10 — Release Handoff

**Goal**: Produce the release handoff artifact and finalize the branch for PR.
**Priority**: P0 — Required to close the mission.
**Prompt**: [WP10-release-handoff.md](tasks/WP10-release-handoff.md)
**Estimated size**: ~250 lines

**Subtasks**:

- [ ] T042 Produce kitty-specs/charter-end-user-docs-828-01KQCSYD/release-handoff.md (FR-015) — pages added/updated, snippets validated, tests run, known limitations, follow-up issues (WP10)
- [ ] T043 Update docs release notes or changelog if the repo maintains them (WP10)
- [ ] T044 Final grep for stale text across all changed files — "TODO", "2.x" in current-facing pages, dead placeholder text (WP10)
- [ ] T045 Verify docs/charter-end-user-docs-828 branch is clean and ready for PR to main (WP10)

**Dependencies**: WP09
