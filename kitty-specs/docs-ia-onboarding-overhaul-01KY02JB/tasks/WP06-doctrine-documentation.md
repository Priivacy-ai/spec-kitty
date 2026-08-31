---
work_package_id: WP06
title: Doctrine Documentation
dependencies:
- WP02
requirement_refs:
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: feat/docs-ia-onboarding-overhaul
merge_target_branch: feat/docs-ia-onboarding-overhaul
branch_strategy: Planning artifacts for this mission were generated on feat/docs-ia-onboarding-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-ia-onboarding-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
agent: "claude:sonnet-5:curator-carla:reviewer"
history: []
agent_profile: doctrine-daphne
authoritative_surface: docs/doctrine/doctrine-kinds.md
create_intent:
- docs/doctrine/doctrine-kinds.md
- docs/doctrine/create-a-doctrine-artifact.md
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/doctrine/doctrine-kinds.md
- docs/doctrine/create-a-doctrine-artifact.md
- docs/doctrine/index.md
role: implementer
tags: []
shell_pid: "11323"
shell_pid_created_at: "1784571774.642189"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load doctrine-daphne` (role: implementer). Then read, in order:
[spec.md](../spec.md) User Story 3 + FR-007/FR-008, [plan.md](../plan.md) §IC-05,
[data-model.md](../data-model.md)'s `DoctrineArtifactKind` entity, and the existing
`docs/doctrine/index.md`, `docs/doctrine/README.md`, `docs/doctrine/spdd-reasons.md`.

## Objective

The doctrine system — 8 distinct governed content kinds that shape mission/agent behavior — has
only 3 thin explanation files today and zero "how do I create one" guidance. Author a complete
explanation of all 8 kinds and a working, followable how-to for creating a new doctrine
artifact. This is the mission's most governance-critical content gap: doctrine underlies
Charter, missions, and agent profiles, and it is almost entirely undocumented.

## Context

- The 8 doctrine artifact kinds (single canonical authority — this exact list, sourced from this
  project's own charter kind-vocabulary module, per research.md item 7): `directive`, `tactic`,
  `styleguide`, `toolguide`, `paradigm`, `template`, `agent_profile`, `mission_step_contract`.
  Do not add, omit, or rename any of these.
- Ground truth for what each kind IS and how one is CREATED lives in the codebase — likely
  `charter.kind_vocabulary`, the charter activation engine (`plan_activation`/
  `commit_activation`), and any `charter synthesize`/`charter activate` CLI commands. Read the
  actual code before writing definitions — do not rely on this WP prompt's summary alone.
- The abandoned `kitty-specs/charter-end-user-docs-828-01KQAJA0` mission targeted exactly this
  gap (doctrine synthesis, governed missions) but was never executed (0/10 WPs done). Its
  `research.md`/`gap-analysis.md` may contain useful groundwork — check, but per spec.md C-006
  this mission's own audit is authoritative if anything conflicts or looks stale.

## Subtask guidance

- **T023 — Source the vocabulary from code.** Find and read `charter.kind_vocabulary` (or
  equivalent module) and the "Canonical Kind Vocabulary" table referenced in this project's own
  CLAUDE.md. Confirm the 8-kind list and the operator-token normalization (e.g.
  `agent-profile` → `agent_profile`, `mission-step-contract` → `mission_step_contract`).
- **T024 — Check the abandoned mission for reusable material.** Read
  `kitty-specs/charter-end-user-docs-828-01KQAJA0/research.md` and `gap-analysis.md` if they
  exist. Extract anything factually accurate and still current; discard anything stale or
  contradicted by your own T023 research. Do not copy content wholesale without verifying it
  against current code.
- **T025 — Author `docs/doctrine/doctrine-kinds.md`.** One section per kind: what it's for (its
  role in governance — e.g. a `directive` is a binding rule, a `tactic` is a reusable
  problem-solving procedure, etc. — verify each against T023's findings, don't guess), and one
  concrete example drawn from this repository's actual built-in doctrine (e.g. cite a real
  directive ID, a real tactic name from the charter context payloads you've seen referenced
  elsewhere in this mission's own planning artifacts, like `problem-decomposition` or
  `traceable-decisions`). Add `type: explanation` frontmatter.
- **T026 — Author `docs/doctrine/create-a-doctrine-artifact.md`.** A concrete, followable,
  start-to-finish how-to: what CLI command(s) create/register a new artifact of a given kind,
  what file/schema it needs, and how it gets activated (reference the `charter activate`
  command and cascade behavior if applicable). Test your own instructions mentally against one
  kind (e.g. walk through "create a new tactic" step by step) to confirm they're actually
  followable, not just plausible-sounding. Add `type: how-to` frontmatter.
- **T027 — Cross-link, don't duplicate.** Update `docs/doctrine/index.md` to link to both new
  pages as the primary entry points. Leave `README.md` and `spdd-reasons.md` as-is unless they
  contain content that directly duplicates your new pages (in which case, trim the duplication
  and link out, following the same principle as WP05's charter consolidation).

## Branch Strategy

Planning artifacts were generated on `feat/docs-ia-onboarding-overhaul`. This WP branches from
that base during `/spec-kitty.implement`, after WP02 has landed, and merges back into
`feat/docs-ia-onboarding-overhaul`. Runs in parallel with WP04, WP05, WP07 (disjoint file sets).

## Definition of Done

- [ ] `docs/doctrine/doctrine-kinds.md` covers exactly the 8 real kinds, each with a
      code-grounded purpose statement and a real example.
- [ ] `docs/doctrine/create-a-doctrine-artifact.md` gives concrete, verified-followable steps.
- [ ] `docs/doctrine/index.md` links to both new pages.
- [ ] Both new pages carry correct Divio frontmatter.
- [ ] Any content reused from the abandoned mission's research was verified against current
      code, not copied blind.

## Risks & Mitigations

- **Highest accuracy risk in the mission**: doctrine is governance-critical; a wrong "how to
  create one" instruction actively breaks a user's governance setup. Verify every command
  against the actual CLI (`--help` output) before documenting it.
- **Stale abandoned-mission content**: that mission's material is 0% executed and may describe
  an interface that has since changed — treat it as a lead to verify, never a source to copy.

## Review Guidance

- Pick one doctrine kind and mentally execute `create-a-doctrine-artifact.md`'s steps against
  the real CLI — do they actually work?
- Confirm the 8-kind list matches the project's own CLAUDE.md "Canonical Kind Vocabulary" table
  exactly.

## Activity Log

- {{TIMESTAMP}} – system – Prompt created.
- 2026-07-20T17:58:12Z – claude:sonnet-5:curator-carla:implementer – shell_pid=91148 – Assigned agent via action command
- 2026-07-20T18:13:54Z – claude:sonnet-5:curator-carla:implementer – shell_pid=91148 – Ready for review: doctrine-kinds.md + create-a-doctrine-artifact.md authored, code/CLI-verified 8-kind list (procedure not template — see commit msg for drift note), example tactic schema-validated, index.md cross-linked, link-checker and terminology guard pass.
- 2026-07-20T18:23:45Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=11323 – Started review via action command
- 2026-07-20T18:29:58Z – user – shell_pid=11323 – Review passed: independently re-verified the 8 doctrine-kind correction from scratch (read src/doctrine/artifact_kinds.py, src/charter/kind_vocabulary.py, live 'spec-kitty charter activate bogus-kind x' error output, 'spec-kitty charter list --all', and commit 1e3dc8d2c) - procedure (not template) is confirmed the correct 8th charter-activatable kind. All 8 cited example artifacts verified to exist with matching content. All CLI commands/flags verified against --help output. Schema claims verified. Links/anchors resolve. Terminology guard passes. WP06 commit touches only its 3 owned files.
