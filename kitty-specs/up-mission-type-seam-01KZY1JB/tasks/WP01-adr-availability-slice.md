---
work_package_id: WP01
title: 'ADR: mission-type roster layering is the availability slice, not the kind-promotion slice'
dependencies: []
requirement_refs:
- C-001
- C-002
- FR-012
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
phase: Phase 0 - ADR (mandatory first work package per spec CL-002/FR-012)
assignee: ''
agent: claude
history:
- at: '2026-08-13T00:00:00Z'
  actor: system
  action: Prompt generated during /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: docs/adr/3.x/
create_intent:
- docs/adr/3.x/2026-08-13-1-mission-type-roster-layering-seam.md
execution_mode: planning_artifact
model: ''
owned_files:
- docs/adr/3.x/2026-08-13-1-mission-type-roster-layering-seam.md
role: architect
tags: []
task_type: plan
---

# Work Package Prompt: WP01 – ADR: mission-type roster layering is the availability slice, not the kind-promotion slice

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `architect-alphonso` and behave according to its
guidance before parsing the rest of this prompt.

- **Profile**: `architect-alphonso`
- **Role**: `architect`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

This WP produces **one new markdown file**, no code. It is the mission's literal first work
package (spec CL-002 / FR-012): the plan/tasks phase must produce an ADR before any other WP is
worked, because it answers a real upstream sequencing risk — whether this mission's roster-layering
work quietly reopens a decision a *different*, larger, currently-unstarted mission is supposed to
make.

Success = a new ADR at `docs/adr/3.x/2026-08-13-1-mission-type-roster-layering-seam.md`,
following the frontmatter/section shape of existing ADRs in that directory (see
`docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md` for the closest
structural precedent — read it in full before drafting), that states, in these terms, all three
of:

1. **This mission does not promote mission-type to a first-class `ArtifactKind` member.**
   Confirm live before writing: `grep -n "class ArtifactKind" -A 30 src/doctrine/artifact_kinds.py`
   has no `MISSION_TYPE` member today, and `grep -n "MissionTypeNotAnArtifactKind"
   src/charter/activation/kind_vocabulary.py` shows the exception exists specifically to keep
   `"mission-type"` out of the charter-activatable `ArtifactKind` vocabulary while remaining a
   `CHARTER_KIND_TOKENS` member. That promotion is a separate, larger, currently-unstarted
   upstream effort — issue [#2468](https://github.com/Priivacy-ai/spec-kitty/issues/2468), blocked
   on the keystone pack-split [#2467](https://github.com/Priivacy-ai/spec-kitty/issues/2467).
2. **This mission's relation to
   `docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md`'s "no silent
   contract reversal" decision driver.** That ADR names `#2468`'s promotion as reversing a
   deliberate, tested "no silent fallback" contract (pinned by
   `tests/doctrine/test_org_pack_augmentation.py`) and requires it carry its own decision record
   rather than being smuggled into an availability slice. State plainly: this mission **is** the
   availability/resolution slice that ADR anticipates (layered lookup + projection + CLI-surface
   fixes for a type that already got *activated* — it never widens what can be *activated*, see
   C-003), and is **explicitly not** the contract-reversing type-promotion slice. A future reader
   auditing either ADR must not be able to conflate the two.
3. **The flat org-pack layout decision (CL-005) as its own short, self-contained decision
   record**, distinct from (1)/(2) above. The referenced ADR explicitly parks "nested-vs-flat
   mission-type path" as an undecided open sub-decision belonging to the `#2468` promotion slice
   ("This ADR does not bind it."). Record here: the org layer is flat —
   `<pack_root>/mission_types/*.yaml`, matching the sibling `mission-steps/` convention already
   used at the org/project pack tier (confirm live:
   `grep -n "mission-steps" src/doctrine/missions/mission_step_repository.py` — the pattern is
   `{pack_root}/mission-steps/{mission_type_id}/{step_id}/step.yaml`) — and the project layer is
   `.kittify/missions/mission_types/*.yaml`, scanned **non-recursively**. State the rejected
   alternative and why: `.kittify/doctrine/mission_types/` was considered and rejected because that
   directory shape, scanned recursively, would descend into a per-type `governance-profile.yaml`
   subdirectory and mint a bogus available mission type literally named `governance-profile` — a
   real trap in the live scanning code (`src/charter/activation/pack_manager.py`'s `list_available_detailed`,
   which uses `scan_dir.rglob(glob)` universally for other kinds), not a hypothetical one, though
   this mission's flat CL-005 shape structurally avoids it rather than fixing the underlying
   `rglob` behavior (that fix is out of scope — see WP05's prompt).

## Context & Constraints

- **Read first, in full, before drafting**: `kitty-specs/up-mission-type-seam-01KZY1JB/spec.md`
  (CL-001 through CL-006/CL-004a, User Stories 1–3, C-001/C-002), and
  `kitty-specs/up-mission-type-seam-01KZY1JB/plan.md`'s "Implementation Concern Map" preamble
  (the paragraph immediately before IC-01, which states WP01's three required contents in the
  plan's own words — this prompt restates and expands them but the plan is the binding source).
- Also read `docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md` in full
  — this is the ADR you are relating to, not merely citing. Cross-reference it by its real path,
  not by number alone (this repo's docs consistency gate checks link resolution against the
  changed markdown).
- **This WP is purely a planning artifact.** No `src/` or `tests/` file changes. `execution_mode:
  planning_artifact` in this file's frontmatter reflects that — do not let review tooling expect a
  code diff from this WP.
- **Constraints this ADR must acknowledge, not resolve**: C-001 (mission size class L, ~150-190
  `src/` LOC + ~260 test LOC across WP02–WP07, not counted against this WP), C-002 (ArtifactKind
  promotion explicitly out of scope — this is (1) above).

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on
  `kitty/mission-up-mission-type-seam-01KZY1JB`. During `/spec-kitty.implement` this WP may branch
  from a dependency-specific base, but completed changes must merge back into
  `kitty/mission-up-mission-type-seam-01KZY1JB` unless the human explicitly redirects the landing
  branch. The mission's own `target_branch` (`meta.json`) is `main` — the coordination branch is
  where WP work lands first, `main` is where the mission's single PR eventually targets (see
  `tasks.md`'s "PR Shape" section, which states and reasons about the one-PR-per-mission decision
  for this mission specifically; this is also spec-kitty's own `sk-implement` skill default —
  "One PR per mission by default").
- **Planning base branch**: `kitty/mission-up-mission-type-seam-01KZY1JB`
- **Merge target branch**: `main`

## Subtasks & Detailed Guidance

### Subtask T001 – Author the ADR

- **Purpose**: satisfy spec CL-002/FR-012 — the plan/tasks phase's first work package is an ADR,
  not code.
- **Steps**:
  1. Re-read `docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md` in
     full (structure: frontmatter with `title`/`description`/`status`/`date`, then `## Context and
     Problem Statement`, `## Decision Drivers`, and further sections — mirror this shape, don't
     invent a new one).
  2. Verify, live, the two source-code claims in the Objectives section above (`ArtifactKind` enum
     has no `MISSION_TYPE` member; `MissionTypeNotAnArtifactKind` exists in
     `src/charter/activation/kind_vocabulary.py`). Cite the actual line numbers you find, not the ones in this
     prompt (they will drift).
  3. Draft the ADR with frontmatter: `title`, `description` (one sentence, per the repo's ADR
     convention), `status: Accepted` (this ADR records a decision already made and being executed,
     not a proposal awaiting approval), `date: '2026-08-13'`.
  4. Write the three required content points (1)/(2)/(3) from the Objectives section above as
     distinct subsections — do not blend them into one paragraph; a future reader skimming section
     headers should be able to find each independently.
  5. Cross-reference `docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md`
     by its real relative path (this repo's architecture/docs-consistency lint gate checks link
     resolution).
  6. Reference issues [#2468](https://github.com/Priivacy-ai/spec-kitty/issues/2468) and
     [#2467](https://github.com/Priivacy-ai/spec-kitty/issues/2467) by number and one-line
     description (do not assume the reader has them open).
- **Files**: `docs/adr/3.x/2026-08-13-1-mission-type-roster-layering-seam.md` (new — verify no
  file with today's date already exists before picking the `-1` suffix; `ls docs/adr/3.x/ | grep
  2026-08-13` first).
- **Parallel?**: No — this is the mission's only subtask in this WP, and every other WP depends on
  it (transitively, via WP02).
- **Notes**: This is a **decision record**, not a design document — keep it focused on the three
  required points and their "why," not a restatement of the whole plan.md. If you find the
  `ArtifactKind` enum *does* already have a `MISSION_TYPE` member when you check live (i.e. this
  citation drifted since spec/plan authoring), STOP and report — that would mean point (1)'s
  premise changed and needs an operator ruling before this ADR can truthfully state it.

## Test Strategy

No automated test applies to this WP (planning artifact, no code). The gate this WP must clear is
markdown lint + the architecture/docs-consistency check (see Gate Set below) — not pytest.

## Risks & Mitigations

- **Risk**: drafting the ADR as a restatement of plan.md rather than a decision record — future
  readers need the "why," and plan.md is already a passed, binding document; duplicating it here
  adds a second copy that can drift. **Mitigation**: keep this ADR to the three required points and
  their rationale; link to plan.md and spec.md rather than re-deriving their content.
- **Risk**: citing `docs/adr/3.x/2026-08-05-1-...md` incorrectly (wrong issue numbers, wrong
  "no silent fallback" framing). **Mitigation**: quote the relevant sentence directly from that
  ADR rather than paraphrasing from memory of this prompt.

## Gate Set (this WP's Definition of Done)

Per plan.md's Gate Set, reproduced here as this WP's concrete DoD:

- **Always-on `lint` job** (`.github/workflows/ci-quality.yml`'s `lint` job): markdown lint,
  Contextive glossary freshness, doctrine schema freshness, TID251, Typer JSON error surface,
  `patch()` target validation, Bandit, pip-audit, commitlint. All run regardless of this WP adding
  no code — they are unconditional and this WP's new markdown file participates in the markdown
  lint pass specifically.
- **Architecture/docs consistency** (`ci-quality.yml:795`) — **WP01-specific, additionally
  required**: the new ADR's cross-references (to
  `docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md`, and to issues
  #2468/#2467) must resolve correctly.
- **`uv lock --check`** — always-on, required `quality-gate` member; this WP adds no dependency, so
  it is expected to pass trivially, but do not skip verifying it.
- **No pytest gate applies to this WP** — `execution_mode: planning_artifact`, no `src/`/`tests/`
  file in `owned_files`.
- `make lint` locally before handing off, per CLAUDE.md's Code Style section (the fast local
  pre-push check; the full `lint` job above is what CI enforces).

## Review Guidance

- Confirm the ADR states all three required points (1)/(2)/(3) as **distinct, findable** sections,
  not blended prose.
- Confirm the two source-code claims in point (1) are cited with real, live-verified line numbers,
  not copied uncritically from this prompt.
- Confirm the ADR does not accidentally *do* any of the deferred work it describes (e.g. it must
  not itself widen `ALLOWED_MISSION_TYPES` or add an `ArtifactKind.MISSION_TYPE` member — this is
  a decision record about staying out of that scope, not a place to sneak it in).
- Confirm `status: Accepted` (not `Proposed`) — this mission's spec/plan already passed review; the
  ADR documents an executing decision, matching the sibling ADR's own convention.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-13T00:00:00Z – system – Prompt created.
- 2026-08-14T00:34:30Z – user – ADR approved: 10/10 citations byte-verified; hygiene rework re-reviewed clean (8 lenses)
