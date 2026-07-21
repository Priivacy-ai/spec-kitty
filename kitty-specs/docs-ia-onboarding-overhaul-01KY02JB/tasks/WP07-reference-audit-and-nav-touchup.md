---
work_package_id: WP07
title: Reference Section Accuracy & Nav Audit
dependencies:
- WP02
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: feat/docs-ia-onboarding-overhaul
merge_target_branch: feat/docs-ia-onboarding-overhaul
branch_strategy: Planning artifacts for this mission were generated on feat/docs-ia-onboarding-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-ia-onboarding-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
agent: "claude:sonnet-5:curator-carla:reviewer"
history: []
agent_profile: curator-carla
authoritative_surface: docs/api/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/api/**
- docs/adr/**
- docs/operations/**
- docs/migrations/**
- docs/archive/**
role: implementer
tags: []
shell_pid: "11323"
shell_pid_created_at: "1784571774.642189"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load curator-carla` (role: implementer). Then read, in order:
[spec.md](../spec.md) FR-010 + Out of Scope + Assumption 4, [plan.md](../plan.md) §IC-06, and
skim the target directories' `index.md`/`toc.yml` files to orient yourself before auditing.

## Objective

Pre-mission research found the reference-heavy sections (API, ADR, Configuration, Operations,
Migrations, Historical Archive) structurally sound. This WP performs a narrow, evidence-based
accuracy and nav-placement audit — confirming that assumption where it holds, and fixing
specific inaccuracies where it doesn't. This is explicitly **not** a rewrite: spec.md's Out of
Scope section forbids wholesale rewriting of these sections.

## Context

- Scope: `docs/api/`, `docs/adr/`, `docs/configuration/` (if it exists as a distinct directory
  — verify), `docs/operations/`, `docs/migrations/`, `docs/archive/`.
- "Accuracy" here means: does the documented CLI behavior, command syntax, or configuration
  option actually match the live code? Spot-check against the actual CLI (`--help` output,
  source modules) rather than assuming prose is correct.
- "Nav placement" changes are **findings you record**, not edits you make directly — `docs/toc.yml`
  is WP02's exclusive owned surface. If you find a placement issue, note it in `docs-audit.md`
  (WP01's audit file — append to it, don't create a competing file) as a recommendation.
- `docs/adr/` specifically: ADR bodies are immutable historical snapshots (per
  `tests/architectural/test_no_legacy_terminology.py`'s own docstring: "docs/adr/ holds
  immutable historical decision records whose bodies are preserved byte-for-byte"). Do NOT
  rewrite ADR content for terminology or style — only touch an ADR if it contains a genuine
  factual error unrelated to historical accuracy (rare; be conservative here).

## Subtask guidance

- **T028 — Audit `docs/api/`.** Cross-check a representative sample of documented commands
  against the live CLI (`spec-kitty <command> --help`). Flag any mismatch: wrong flag name,
  outdated example, missing option, described behavior that doesn't match code. Record findings
  even where everything checks out — "audited, no issues found" is a valid, useful finding.
- **T029 — Audit `docs/adr/`, `docs/migrations/`, `docs/operations/`.** For ADRs: check only for
  broken internal links or metadata errors, never rewrite decision content (see Context above).
  For migrations/operations: verify commands and file paths referenced still exist and behave as
  described.
- **T030 — Audit `docs/archive/` nav placement.** This is lower-stakes historical content;
  confirm it's still reachable (not orphaned) and that its placement (currently its own nested
  `toc.yml` group, per research) still makes sense post-restructure. Record any recommendation.
- **T031 — Fix confirmed inaccuracies.** For every genuine mismatch found in T028-T030 (not
  stylistic preferences — actual factual errors), make the minimal correction. Do not expand
  scope into a rewrite of surrounding content.
- **T032 — Record all findings.** Append a "WP07 Reference Audit Findings" section to
  `docs-audit.md` (WP01's file) listing every section audited, what was checked, what was found,
  and what was fixed vs. merely recommended (e.g. nav-placement suggestions for WP02/future
  follow-up).

## Branch Strategy

Planning artifacts were generated on `feat/docs-ia-onboarding-overhaul`. This WP branches from
that base during `/spec-kitty.implement`, after WP02 has landed, and merges back into
`feat/docs-ia-onboarding-overhaul`. Runs in parallel with WP04, WP05, WP06 (disjoint file sets).

## Definition of Done

- [ ] Each target directory has a recorded audit finding (even if "no issues").
- [ ] Every confirmed inaccuracy is fixed with a minimal, targeted edit.
- [ ] No ADR body content was rewritten except for genuine non-historical factual errors (rare;
      justified in the findings if it happened).
- [ ] Nav-placement recommendations are recorded in `docs-audit.md`, not applied directly to
      `docs/toc.yml`.

## Risks & Mitigations

- **Scope creep into rewrites**: this is the highest-risk WP for accidentally violating the
  mission's explicit Out-of-Scope constraint. If you find yourself rewriting more than a
  sentence or two per fix, stop and reconsider whether it's actually a confirmed inaccuracy or
  just a style preference.
- **ADR immutability violation**: rewriting ADR prose for terminology/style would violate this
  project's own architectural test precedent (`test_docs_adr_exemption_is_narrow`). When in
  doubt, leave ADR content untouched.

## Review Guidance

- Confirm every T031 fix corresponds to a specific, verifiable inaccuracy (cite the live command
  output or code that proves it) — not a preference-driven edit.
- Grep `docs/adr/` diffs specifically to confirm no historical content was altered beyond a
  narrow, justified factual correction.

## Activity Log

- {{TIMESTAMP}} – system – Prompt created.
- 2026-07-20T17:58:34Z – claude:sonnet-5:curator-carla:implementer – shell_pid=91148 – Assigned agent via action command
- 2026-07-20T18:21:17Z – claude:sonnet-5:curator-carla:implementer – shell_pid=91148 – Ready for review: audited docs/api, docs/adr, docs/migrations, docs/operations, docs/archive; fixed 8 confirmed inaccuracies, recorded full findings in docs-audit.md
- 2026-07-20T18:24:00Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=11323 – Started review via action command
- 2026-07-20T18:30:40Z – user – shell_pid=11323 – Review passed: independently verified all 8 claimed fixes against live CLI (--help), source, CHANGELOG.md, and the freshen_adr_inventory.py tool re-run (now reports clean). WP07 commit d229dd7ff isolated and confirmed to touch only owned_files (docs/api/**, docs/adr/**, docs/migrations/**, docs/operations/**), no docs/toc.yml, no ADR body content. Diff sizes proportional to narrow corrections (largest single-file change is feature-flag-deprecation.md correcting one repeated false premise, justified in docs-audit.md). docs-audit.md WP07 findings section records both fixes and audited-no-issues items for all 3 target areas. Terminology guard and relative-link checker both pass.
