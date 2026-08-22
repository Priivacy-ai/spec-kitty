---
work_package_id: WP04
title: Deprecate dead .kittify/overrides manifest mirrors
dependencies:
- WP01
requirement_refs:
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-expected-artifacts-manifest-repair-01KZY498-lane-c
base_commit: 69ba9e5d5afea015a84738f8581cbcb3bed0cbd5
created_at: '2026-08-14T04:54:42.138207+00:00'
subtasks:
- T018
- T019
phase: Phase 2 - Override deprecation (depends on WP01, scheduling-only — see Context)
assignee: ''
agent: claude
history:
- timestamp: '2026-08-14T00:00:00Z'
  agent: claude
  action: Prompt generated via manual /spec-kitty.tasks-outline + /spec-kitty.tasks-packages equivalent (tasks-authoring agent)
agent_profile: implementer-ivan
authoritative_surface: .kittify/overrides/missions/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .kittify/overrides/missions/research/expected-artifacts.yaml
- .kittify/overrides/missions/documentation/expected-artifacts.yaml
- .kittify/overrides/missions/software-dev/expected-artifacts.yaml
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 – Deprecate dead `.kittify/overrides/` manifest mirrors

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Stop a future maintainer from investing in `.kittify/overrides/missions/{research,
documentation,software-dev}/expected-artifacts.yaml` content that can never be
read, by marking each file explicitly deprecated/inert via a header comment — per
Decision 4's DIRECTIVE_044-driven resolution (mark-deprecated, don't refresh,
don't delete). This is **Implementation Concern IC-04** from `plan.md`.

## Context

**Why this WP exists**: the spec's own "second-order finding" (and
`tracer-approach.md`'s "A discovery that reframed part of the blast radius")
establish that `.kittify/overrides/missions/*/expected-artifacts.yaml` are
consumed by **zero** readers in this repository —
`MissionTemplateRepository._expected_artifacts_path()`
(`src/doctrine/missions/repository.py:476-490`) composes only the built-in pack
root, with no override tier for this specific file type (unlike
`mission.yaml`/templates/command-templates, which *do* resolve through
`.kittify/overrides/` first).

**Why NOT to refresh their content to match WP02's reconciled built-in copies**:
per `tracer-design-decisions.md` Decision 4, refreshing dead content to keep it
"in sync" is the literal shape of parity-with-a-dead-quirk (charter
DIRECTIVE_044's named anti-pattern) — it would restate, dressed up as
maintenance, the exact single-canonical-authority violation the second-order
finding just diagnosed. **This WP changes only a header comment in each file —
the existing body content is otherwise untouched, not refreshed to parity.**

**Why NOT to delete them**: Decision 4's Option C (delete outright) was
considered and rejected — deletion removes the historical starting point a future
override-tier-wiring mission might want, and a present-but-marked-dead file is
discoverable by a maintainer browsing the tree; a deleted file requires git
archaeology to learn it ever existed.

**Content-independent, but sequenced after WP01**: this WP's own file edits
(the three `.kittify/overrides/` header comments) have **no content dependency**
on WP01/WP02/WP03 — these three files are never read by any production code
path (confirmed above), so nothing about WP01's schema hardening or WP02/WP03's
content edits affects the deprecation-header content itself. `wps.yaml` declares
`WP01` as a dependency anyway, purely for **scheduling**: this WP's own
out-of-map edit to `tests/dossier/test_manifest.py` (T018, below) is one of four
WPs that touch that same shared file, and WP01 is the sole owner that
establishes it first (see "Out-of-map edit" below and
`tracer-approach.md`'s "Chokepoints & execution sequencing" addendum). The
dependency edge makes that ordering a structural fact the lanes/scheduling
machinery can see, rather than prose an automated orchestrator has no way to
honor.

### ⚠️ Out-of-map edit: `tests/dossier/test_manifest.py`

Same pattern as WP02/WP03: this WP does not list `tests/dossier/test_manifest.py`
in `owned_files` (WP01 owns it) but makes a small, well-justified out-of-map edit
adding a new class, `TestOverrideMirrorDeprecation`, with exactly one new test.
Stay strictly within that new class. This WP now carries a formal `dependencies:
[WP01]` edge in `wps.yaml` for exactly this reason: **do not start T018's edit to
`test_manifest.py` until WP01 has actually landed** — this is now a structural
scheduling constraint the lanes machinery enforces (WP04 lands in a later
`parallel_group` than WP01), not merely prose an orchestrator has to remember to
honor. That closes the collision this WP used to risk with WP01's own
first-touch commit — but per `lanes.json`, WP04 now lands in `parallel_group: 1`,
the same group as WP02 and WP03 (all three depend only on WP01, with no
dependency edge among the three of them), so the residual, still-advisory-only
risk is a **three-way** collision with WP02's and WP03's own edits to this same
file, not with WP01. See `tracer-approach.md`'s "Chokepoints & execution
sequencing" addendum for the full picture and the recommended sequencing.

## Subtask T018: Red-first test — override mirror files carry the deprecation header

**Purpose**: Pin the specific-mechanism wording requirement before editing the
three files, and provide the concrete regression guard for Decision 4 (so a future
"drift hygiene" refresh that overwrites the header back to content-parity wording
fails this test, not just manual review).

**Steps**:
1. In `tests/dossier/test_manifest.py`, add a new class
   `TestOverrideMirrorDeprecation`.
2. Add `test_override_mirror_files_carry_deprecation_header`: for each of
   `.kittify/overrides/missions/{research,documentation,software-dev}/expected-artifacts.yaml`,
   read the file's raw text and assert the header comment names the **specific
   inert mechanism** — e.g. assert the text contains both a recognizable
   "deprecated"/"inert" marker **and** a reference to
   `_expected_artifacts_path()` (or equivalent specific-mechanism language, e.g.
   "no override tier for this asset type") — not merely a generic "deprecated"
   string with no mechanism named. Also assert each file's **body content**
   (the `required_by_step` structure) is unchanged from its current state — a
   content-diff or key-count check confirms this WP does not refresh content,
   only adds the header.

**Files**: `tests/dossier/test_manifest.py` (new class + 1 test, ~30-40 lines,
likely reading all 3 files in a loop with per-file assertions).
**Validation**: RED — none of the three files currently carries any deprecation
header.

## Subtask T019: Implement — add the header comment to all three override files

**Purpose**: Land the header comment matching T018's red-first test, with no other
content change.

**Steps**:
1. For each of `.kittify/overrides/missions/{research,documentation,software-dev}/expected-artifacts.yaml`,
   prepend a header comment block (above the existing `# Expected artifact
   manifest for ... mission` comment, or replacing/extending it — keep the
   existing header's informational content, add to it rather than deleting it)
   stating explicitly:
   - This file is **not consumed** by any resolver for this asset type.
     `MissionTemplateRepository._expected_artifacts_path()`
     (`src/doctrine/missions/repository.py`) composes only the built-in pack path
     (`packs/built-in/missions/<type>/expected-artifacts.yaml`) with no override
     tier — unlike `mission.yaml`/templates/command-templates, which do resolve
     through `.kittify/overrides/` first.
   - The canonical, consumed copy is
     `packs/built-in/missions/<type>/expected-artifacts.yaml`.
   - A future correction (wiring an override-resolution tier for this asset type)
     is a named follow-up candidate, not implemented here — point at this
     mission's spec.md "Out of Scope" section / C-004 for context (a repo-internal
     pointer is sufficient; no new tracker issue is required by FR-014).
2. **Do not** modify the `required_by_step`/`optional_always`/any other body
   content in these three files — verify via `git diff` that only the header
   comment block changed before committing.

**Files**: `.kittify/overrides/missions/research/expected-artifacts.yaml`,
`.kittify/overrides/missions/documentation/expected-artifacts.yaml`,
`.kittify/overrides/missions/software-dev/expected-artifacts.yaml` (each edited,
header-comment-only, ~8-12 new lines each).
**Validation**: T018's test goes GREEN, including its content-unchanged
assertion.

## Definition of Done

- [ ] `TestOverrideMirrorDeprecation` section exists with its one new test,
      committed **before** T019's implementation commit (C-011).
- [ ] All three override files carry the specific-mechanism deprecation header.
- [ ] No body content changed in any of the three files (verified by the test's
      content-unchanged assertion and by manual `git diff` review).
- [ ] No new `.kittify/overrides/missions/plan/expected-artifacts.yaml` is
      created (that is WP03's explicit non-action, not this WP's).

## Risks

- **Low.** The only failure mode is writing a comment vague enough that a future
  maintainer still believes the override might take effect — the comment must
  name the specific mechanism, not just say "deprecated" (per
  `plan.md`'s IC-04 risk note).
- **Chokepoint**: this WP now carries a formal `dependencies: [WP01]` edge in
  `wps.yaml` (added during the tasks-phase adversarial-review fix), so the
  WP04-vs-WP01 chokepoint on `test_manifest.py` is structurally enforced by the
  lanes machinery, not merely advisory. The residual, still-advisory-only
  exposure is WP04 sharing `test_manifest.py` with WP02 and WP03, all three of
  which sit in the same `parallel_group: 1` with no dependency edge among them —
  see the Context section above and the mission's `tracer-approach.md`
  "Chokepoints & execution sequencing" addendum for the sequencing
  recommendation.

## Reviewer Guidance

- Confirm the header comment names the specific mechanism
  (`_expected_artifacts_path()` / "no override tier for this asset type"), not a
  generic "deprecated" string.
- Confirm `git diff` on all three files shows only comment-block changes, no body
  content changes — this is the literal test of Decision 4's "don't refresh"
  half.
- Confirm no `.kittify/overrides/missions/plan/` file was added.

Implementation command: `spec-kitty agent action implement WP04 --agent claude`
