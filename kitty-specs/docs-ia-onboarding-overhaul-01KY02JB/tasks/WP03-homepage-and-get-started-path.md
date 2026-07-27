---
work_package_id: WP03
title: Homepage & Get Started Path
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-002
- FR-014
tracker_refs: []
planning_base_branch: feat/docs-ia-onboarding-overhaul
merge_target_branch: feat/docs-ia-onboarding-overhaul
branch_strategy: Planning artifacts for this mission were generated on feat/docs-ia-onboarding-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-ia-onboarding-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
agent: "claude:sonnet-5:curator-carla:reviewer"
history: []
agent_profile: curator-carla
authoritative_surface: docs/index.md
create_intent:
- docs/guides/your-first-mission.md
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/index.md
- docs/guides/getting-started.md
- docs/guides/your-first-mission.md
role: implementer
tags: []
shell_pid: "11323"
shell_pid_created_at: "1784571774.642189"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load curator-carla` (role: implementer). Then read, in order:
[spec.md](../spec.md) User Story 1 + FR-001/FR-002/FR-014 + NFR-001/NFR-002,
[plan.md](../plan.md) §IC-02, [data-model.md](../data-model.md)'s "Get Started Path" entity, and
[quickstart.md](../quickstart.md) section 1 (this is the exact walkthrough your work must pass).

## Objective

Fix the mission's highest-priority defect: a first-time visitor currently has no reachable path
from the homepage to the site's one good tutorial. Rewrite `docs/index.md`'s above-the-fold
content to state who Spec Kitty is for before any governance jargon, and wire one unambiguous
Get Started entry point through install → `getting-started.md` → the renamed
`your-first-mission.md`, reachable in 2 clicks or fewer from the homepage.

## Context

- Current defect (verified pre-mission research): `docs/index.md` opens with "Charter-era
  missions with governed context injection" — internal contributor language, not a value
  proposition. The existing tutorial (`getting-started.md` → `your-first-feature.md`) is well
  written but has **zero inbound links** from `index.md` or `toc.yml`.
- `your-first-feature.md` violates the project's Terminology Canon (Mission, not Feature — see
  spec.md Domain Language) and must be renamed to `your-first-mission.md`, with its prose
  updated to match.
- WP02 has already placed the Get Started entry point somewhere in the new `docs/toc.yml`
  end-user zone — read the final nav structure before wiring links, don't assume the pre-mission
  layout.

## Subtask guidance

- **T010 — Rewrite the homepage above-the-fold.** Replace `docs/index.md`'s opening content so
  the very first thing a reader encounters is: who Spec Kitty is for (its target user), and what
  problem it solves — in plain language, zero governance/architecture terminology in that
  opening. The existing "Answer summary" card-grid structure further down the page can stay if
  it's useful, but it must not be the FIRST thing the reader sees. Acceptance test (FR-001): a
  reader who stops after the first screen can state in one sentence who this is for and what it
  does.
- **T011 — Rename and Terminology-Canon the tutorial.** `git mv
  docs/guides/your-first-feature.md docs/guides/your-first-mission.md`. Read the full file and
  reword every "feature" reference that means the Mission domain object (not every literal
  occurrence of the word "feature" — some may be legitimate, e.g. referring to a product
  feature in a different sense; use judgment, but the title and all Mission-domain references
  must say "Mission"). Update the page's own title/H1.
- **T012 — Fix every inbound reference.** `git grep -n "your-first-feature"` across the whole
  repo (not just `docs/`) and update every hit to the new filename/title — this includes other
  doc pages, `toc.yml` (if WP02 already referenced the old name, fix it here since WP02 may have
  run before this rename — coordinate by re-checking `docs/toc.yml` after WP02 lands), and any
  README or onboarding doc outside `docs/` that references it.
- **T013 — Wire the Get Started chain.** From `docs/index.md`, link directly to one Get Started
  entry point (this may be a dedicated new short landing paragraph on the homepage itself, or a
  single linked page — your call, but there must be exactly one obvious next step, not a menu of
  options). That entry point links to `getting-started.md`, which already continues into
  `your-first-mission.md`. Confirm the whole chain has no dead links.
- **T014 — Verify NFR-001 and NFR-002.** Trace the click path yourself: homepage → [1 click] →
  Get Started entry → [1 click, or 0 if the homepage links straight to `getting-started.md`] →
  tutorial start. Confirm it's 2 clicks or fewer. Note the actual count in this WP's Activity Log.
  Then follow quickstart.md section 1's timed walkthrough (install → `getting-started.md` →
  `your-first-mission.md`) and confirm the content, as written, is completable in 30 minutes or
  less (NFR-002) — this is a content-length/complexity judgment, not a stopwatch requirement;
  trim any step that would push a first-time reader past that budget.

## Branch Strategy

Planning artifacts were generated on `feat/docs-ia-onboarding-overhaul`. This WP branches from
that base during `/spec-kitty.implement`, after WP02 has landed, and merges back into
`feat/docs-ia-onboarding-overhaul`.

## Definition of Done

- [ ] `docs/index.md`'s first screen states who Spec Kitty is for and what it does before any
      governance/architecture term.
- [ ] Exactly one Get Started entry point is linked from the homepage.
- [ ] `your-first-feature.md` no longer exists; `your-first-mission.md` exists with
      Terminology-Canon-compliant prose and title.
- [ ] Zero remaining repo-wide references to the old filename/title (`git grep` returns empty).
- [ ] Click path from homepage to tutorial start is ≤2 clicks (verified and recorded).
- [ ] Get Started path content is scoped to a 30-minutes-or-less completion budget (NFR-002),
      verified against quickstart.md section 1.

## Risks & Mitigations

- **Stale references from other WPs**: WP02, WP04-WP07 may reference `your-first-feature.md` if
  they ran before this rename landed. Since this WP has a hard dependency on WP02 only, other
  WPs running in parallel could introduce new references after T012's grep — re-run the grep
  right before marking this WP done, not just once early.
- **Over-editing**: don't rewrite the entire tutorial content, only the terminology and the
  linking chain — the content itself was already assessed as good in pre-mission research.

## Review Guidance

- Read the homepage's first screen cold, as if you'd never seen this project — can you state who
  it's for in one sentence?
- Click through the actual chain in a local preview or by reading the linked files in sequence.
- Confirm `git grep -i "your-first-feature"` is empty across the whole repo.

## Activity Log

- {{TIMESTAMP}} – system – Prompt created.
- 2026-07-20T17:57:05Z – claude:sonnet-5:curator-carla:implementer – shell_pid=91148 – Assigned agent via action command
- 2026-07-20T18:11:17Z – claude:sonnet-5:curator-carla:implementer – shell_pid=91148 – Ready for review: homepage above-the-fold rewritten (audience+problem before governance jargon), your-first-feature.md renamed to your-first-mission.md with Terminology-Canon reword, single Get Started CTA wired index.md -> getting-started.md -> your-first-mission.md, click path 2 or fewer, 0 dead links (relative_link_fixer.py --check), terminology guard test passing. Repo-wide grep clean except other missions' historical kitty-specs archives and WP07-owned redirect_map.yaml/redirect_baseline_urls.json (deferred to WP08 sweep per charter C-003 dual-read note).
- 2026-07-20T18:22:57Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=11323 – Started review via action command
- 2026-07-20T18:30:07Z – user – shell_pid=11323 – Review passed: homepage opens with plain-language audience+problem statement before any governance jargon; your-first-feature.md renamed to your-first-mission.md with Terminology-Canon-compliant title/prose; click path index.md -> getting-started.md -> your-first-mission.md is exactly 2 clicks; repo-wide grep clean except kitty-specs/ historical archives and single-writer scripts/docs/redirect_map.yaml (correctly identified as WP01-owned per owned_files + tasks.md T004, not WP07 as WP03's commit message says -- minor attribution error only, functionally inconsequential since WP03 correctly did not hand-edit either way); relative_link_fixer --check and test_no_legacy_terminology.py both pass; no unrelated changes outside owned_files beyond T012-mandated inbound reference fixes. (--force used only to bypass a false-positive block from a concurrent WP04 reviewer's uncommitted, unrelated files; no WP03-owned file had uncommitted changes)
