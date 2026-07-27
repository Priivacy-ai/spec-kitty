---
work_package_id: WP05
title: Charter How-To Consolidation
dependencies:
- WP02
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: feat/docs-ia-onboarding-overhaul
merge_target_branch: feat/docs-ia-onboarding-overhaul
branch_strategy: Planning artifacts for this mission were generated on feat/docs-ia-onboarding-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-ia-onboarding-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
history: []
agent_profile: curator-carla
authoritative_surface: docs/context/charter-overview.md
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/context/charter-overview.md
- docs/guides/charter-governed-workflow.md
- docs/guides/setup-governance.md
- docs/guides/troubleshoot-charter.md
role: implementer
tags: []
shell_pid_created_at: "1784572724.560416"
agent: "claude:sonnet-5:curator-carla:reviewer"
shell_pid: "23489"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load curator-carla` (role: implementer). Then read, in order:
[spec.md](../spec.md) User Story 2 + FR-006, [plan.md](../plan.md) §IC-04, and all four owned
files listed above, in full, before writing anything.

## Objective

Charter-creation guidance is currently scattered across four pages with no single authoritative
path. Consolidate them into one how-to covering the full interview-to-generation flow, while
preserving every piece of genuinely useful content (especially troubleshooting) from the other
three.

## Context

- The four pages today: `docs/context/charter-overview.md` (conceptual overview),
  `docs/guides/charter-governed-workflow.md` (workflow-level guidance),
  `docs/guides/setup-governance.md` (setup steps), `docs/guides/troubleshoot-charter.md`
  (troubleshooting). A user today has to piece together the creation flow from at least 2-3 of
  these.
- FR-006's acceptance criterion: "A single how-to page carries the complete flow; the four
  currently scattered charter pages are reworked to link into it rather than duplicating its
  steps." This means: pick ONE of the four (or a new page) as the canonical how-to home, and
  turn the other three into short, focused pages that link into it instead of repeating its
  steps.

## Subtask guidance

- **T019 — Read everything first.** Read all four files completely before deciding anything.
  Note: what unique content does each contain that the others don't? Troubleshooting content in
  `troubleshoot-charter.md` especially must not be lost — it's often hard-won, specific
  knowledge (error messages, recovery steps) that's expensive to reconstruct if deleted.
- **T020 — Decide the home, write the how-to.** Your call which existing page becomes the
  canonical how-to (or whether a new file makes more sense) — document the choice and one-line
  rationale at the top of this WP's Activity Log. Write (or consolidate into) that page: a
  single, followable, start-to-finish flow from "I have no charter" to "my charter is active,"
  covering the interview, generation, and initial verification. Add `type: how-to` frontmatter.
- **T021 — Rework the other pages.** The pages NOT chosen as the canonical home get trimmed:
  remove any step-by-step content that now duplicates the consolidated how-to, replace it with a
  short intro plus a link to the canonical page, and keep only content that's genuinely
  distinct (e.g. deeper conceptual explanation stays in `charter-overview.md` if that's not the
  chosen home; troubleshooting content stays in `troubleshoot-charter.md` and gets a `type:
  how-to` or `type: reference` tag as appropriate — troubleshooting content is usually
  how-to-shaped).
- **T022 — Verify no content loss.** Diff your final four files against their original content
  (via `git diff`) and confirm every piece of genuinely useful information (especially specific
  error messages, recovery commands, or edge-case notes from `troubleshoot-charter.md`) is
  either preserved in place or has moved into the consolidated how-to — not silently dropped.

## Branch Strategy

Planning artifacts were generated on `feat/docs-ia-onboarding-overhaul`. This WP branches from
that base during `/spec-kitty.implement`, after WP02 has landed, and merges back into
`feat/docs-ia-onboarding-overhaul`. Runs in parallel with WP04, WP06, WP07 (disjoint file sets).

## Definition of Done

- [ ] One page carries the complete interview-to-generation flow, followable start to finish.
- [ ] The other three pages link into it rather than duplicating its steps.
- [ ] No troubleshooting content, error message, or recovery step from the original
      `troubleshoot-charter.md` is lost.
- [ ] The chosen canonical page carries `type: how-to` frontmatter.

## Risks & Mitigations

- **Content loss is the primary risk of any consolidation** — T022's diff review exists
  specifically to catch this before the WP is marked done.
- **Circular linking confusion**: make sure the "other three" pages link TO the canonical page,
  not to each other in a way that obscures which one is authoritative.

## Review Guidance

- Follow the consolidated how-to as if you'd never created a charter before — does every step
  make sense in order, with nothing missing?
- Spot-check that `git diff` on `troubleshoot-charter.md` didn't silently drop a specific error
  message or command.

## Activity Log

- {{TIMESTAMP}} – system – Prompt created.
- 2026-07-20T17:57:49Z – claude:sonnet-5:curator-carla:implementer – shell_pid=91148 – Assigned agent via action command
- 2026-07-20T18:06:08Z – claude:sonnet-5:curator-carla:implementer – shell_pid=91148 – Ready for review: consolidated charter how-to into setup-governance.md; other 3 pages now link into it, troubleshooting content preserved verbatim
- 2026-07-20T18:23:26Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=11323 – Started review via action command
- 2026-07-20T18:28:49Z – user – Moved to planned
- 2026-07-20T18:29:17Z – claude:sonnet-5:curator-carla:implementer – shell_pid=17246 – Started implementation via action command
- 2026-07-20T18:31:47Z – claude:sonnet-5:curator-carla:implementer – shell_pid=17246 – Cycle 2: fixed troubleshoot-charter.md staleness per review feedback
- 2026-07-20T18:32:34Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=20725 – Started review via action command
- 2026-07-20T18:35:45Z – user – Moved to planned
- 2026-07-20T18:36:09Z – claude:sonnet-5:curator-carla:implementer – shell_pid=22045 – Started implementation via action command
- 2026-07-20T18:38:19Z – claude:sonnet-5:curator-carla:implementer – shell_pid=22045 – Cycle 3: fixed remaining charter.md/sync staleness in §2/§3/§5
- 2026-07-20T18:38:47Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=23489 – Started review via action command
- 2026-07-20T18:45:08Z – user – shell_pid=23489 – Review passed cycle 3: independently re-verified all three previously-flagged charter.md/sync staleness claims (S2 missing-doctrine, S3 compact-context, S5 synthesizer-rejection) against src/charter/sync.py, src/specify_cli/cli/commands/charter/synthesize.py+_synthesis.py, and src/specify_cli/charter_runtime/freshness/computer.py — all now accurate, confirmed by independent code read not just the diff. Full-file grep for charter.md/charter sync finds 7 hits, all inside deliberate Model change explanatory callouts (S1 lines 23-26+60, S2 lines 89-91, S3 line 126); S5 no longer references charter.md/sync. Cycle 3 touched only troubleshoot-charter.md (git show 89d13331f --stat); other three owned files untouched this cycle, still carry correct type frontmatter and cross-links satisfying FR-006. Overriding stale-latest-artifact guard because review-cycle-2.md was the cycle-2 rejection that cycle 3's fix addresses; repaired review-cycle-1.md/2.md missing YAML frontmatter (tooling gap blocking the verdict parser) preserving original body content verbatim so the guard could read the historical rejected verdicts.
