---
work_package_id: WP10
title: Terminology Canon Sweep & Follow-Up Issue
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
requirement_refs:
- FR-014
tracker_refs: []
planning_base_branch: feat/docs-ia-onboarding-overhaul
merge_target_branch: feat/docs-ia-onboarding-overhaul
branch_strategy: Planning artifacts for this mission were generated on feat/docs-ia-onboarding-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-ia-onboarding-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
- T043
- T044
history: []
agent_profile: curator-carla
authoritative_surface: docs/development/terminology-sweep-report.md
create_intent:
- docs/development/terminology-sweep-report.md
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/development/terminology-sweep-report.md
role: implementer
tags: []
shell_pid_created_at: "1784575545.25976"
agent: "claude:sonnet-5:curator-carla:reviewer"
shell_pid: "35105"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load curator-carla` (role: implementer). Then read, in order:
[spec.md](../spec.md) FR-014 + C-003, [plan.md](../plan.md) §IC-08, and
`docs-audit.md` (WP01's file, now containing every other WP's findings appended).

## Objective

This is the mission's final work package — it runs only after every other WP (WP01-WP09) has
landed. Run both terminology/glossary checks across the mission's full combined output, fix any
remaining flagged occurrence, verify NFR-005's 100% Divio frontmatter coverage, and file the
GitHub issue tracking full glossary alias/banned-synonym governance as deferred follow-up work
(C-003). This WP is what makes Success Criteria 7 ("a terminology/glossary-canonical-form check
runs clean ... at completion") true, and closes the NFR-005 coverage gap flagged by
`/spec-kitty.analyze` finding C1.

## Context

- This WP's one exclusively owned file is `docs/development/terminology-sweep-report.md` (new —
  the closing report for this mission, filed in the contributor zone WP01 established). Every
  other edit this WP makes (fixing flagged terminology in files other WPs created) is a small,
  targeted out-of-map edit — per this mission's ownership rules, that's expected and acceptable
  here since this WP is strictly serialized after everyone else; just record a one-line
  rationale per file touched.
- This WP has a hard dependency on all 9 other WPs. Do not start it until they have all landed —
  running it early would miss terminology introduced by the later-landing WPs, defeating its
  purpose as the final gate.
- C-003 (spec.md): "Full alias/banned-synonym glossary governance ... is out of scope for this
  mission; a GitHub issue is filed to track it as follow-up." This WP is where that filing
  actually happens — don't skip it.

## Subtask guidance

- **T040 — Run both checks across the full mission diff.** Run:
  ```bash
  pytest tests/architectural/test_no_legacy_terminology.py -v
  pytest tests/architectural/test_glossary_canonical_terms.py -v
  ```
  Scope your attention to files this mission actually touched or created (check `git diff
  --name-only` against the mission's base branch) — pre-existing failures elsewhere in `docs/`
  that predate this mission are out of scope to fix here (though worth noting if found; see this
  repo's CLAUDE.md guidance on pre-existing test failures — file a separate issue for those
  rather than silently absorbing them into this mission's scope, per this project's DIR-013).
- **T041 — Fix flagged occurrences.** For every genuine hit within this mission's own
  touched/created files, apply the minimal correction (fix the casing/spelling, or fix the
  actual forbidden-term usage). Do not touch files outside this mission's diff.
- **T042 — File the C-003 follow-up issue.** Use `gh issue create` (if `gh auth status` fails
  with a token-scope error, `unset GITHUB_TOKEN` first per this repo's CLAUDE.md guidance on
  GitHub CLI authentication). Title something like "Glossary: add alias/banned-synonym
  governance (full canonical-term enforcement)". Body should reference: this mission's slug
  (`docs-ia-onboarding-overhaul-01KY02JB`), spec.md's C-003, the current glossary schema gap
  (no `aliases` field in `.kittify/glossaries/spec_kitty_core.yaml`), and
  `tests/architectural/test_glossary_canonical_terms.py` as the narrower check this issue would
  extend. Record the created issue's URL/number in this WP's Activity Log and in a short note
  appended to `docs-audit.md`.
- **T043 — Final summary.** Write `docs/development/terminology-sweep-report.md`: total pages
  moved/merged/removed/created (pull from `docs-audit.md`), final top-level nav entry counts per
  zone, terminology-check status (clean), NFR-005 coverage result (T044), and the follow-up issue
  reference. Also append a short pointer to this report at the bottom of `docs-audit.md` so both
  artifacts cross-reference each other. This report is the mission's closing record for the
  eventual mission-review pass.
- **T044 — Verify NFR-005 (Divio frontmatter coverage).** Grep every page this mission touched or
  created (use `git diff --name-only` against the mission's base branch, filtered to `docs/`) for
  a `type:` frontmatter field with a value in {tutorial, how-to, reference, explanation}. For any
  page missing it or carrying an invalid value, add/fix the frontmatter based on the page's actual
  content (a tutorial walks a user through a task step by step; a how-to solves one specific
  problem; a reference is lookup-oriented; an explanation covers concepts/why). This closes the
  gap flagged by `/spec-kitty.analyze` finding C1 — do not skip it even though it wasn't in the
  original WP list.

## Branch Strategy

Planning artifacts were generated on `feat/docs-ia-onboarding-overhaul`. This WP branches from
that base during `/spec-kitty.implement`, strictly after WP01-WP09 have all landed, and merges
back into `feat/docs-ia-onboarding-overhaul`.

## Definition of Done

- [ ] Both terminology tests pass clean (zero flags) across every file this mission touched or
      created.
- [ ] Any pre-existing failure outside this mission's diff is noted, not silently fixed or
      silently ignored (filed separately if warranted, per DIR-013).
- [ ] 100% of mission-touched/created `docs/` pages carry valid Divio `type:` frontmatter (NFR-005).
- [ ] The C-003 follow-up GitHub issue exists, with its URL recorded.
- [ ] `docs-audit.md` carries a final closing summary.

## Risks & Mitigations

- **Running too early**: if dispatched before all 9 dependencies have actually landed, this WP's
  findings will be incomplete and it will need to re-run. Confirm all dependency WPs report
  done/approved before starting T040.
- **Scope creep into fixing pre-existing, unrelated docs issues**: stay inside this mission's
  own diff; anything else is a separate concern per this repo's own DIR-013 discipline.

## Review Guidance

- Re-run both pytest commands yourself; don't trust a self-report.
- Confirm the filed GitHub issue actually exists at the URL recorded (not just claimed).

## Activity Log

- {{TIMESTAMP}} – system – Prompt created.
- 2026-07-20T18:45:59Z – claude:sonnet-5:curator-carla:implementer – shell_pid=26403 – Started implementation via action command
- 2026-07-20T19:08:43Z – claude:sonnet-5:curator-carla:implementer – shell_pid=27978 – Ready for review: terminology sweep clean for mission scope, NFR-005 Divio coverage closed, both follow-up issues filed (#2822, #2823)
- 2026-07-20T19:10:05Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=31704 – Started review via action command
- 2026-07-20T19:16:02Z – user – Moved to planned
- 2026-07-20T19:16:49Z – claude:sonnet-5:curator-carla:implementer – shell_pid=33226 – Started implementation via action command
- 2026-07-20T19:25:19Z – claude:sonnet-5:curator-carla:implementer – shell_pid=33226 – Cycle 2: removed self-referential terminology violations from closing report
- 2026-07-20T19:25:47Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=35105 – Started review via action command
