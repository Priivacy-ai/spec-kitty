---
work_package_id: WP03
title: Author plan manifest + file follow-up guard-gap issue
dependencies:
- WP01
requirement_refs:
- FR-010
- FR-011
- FR-012
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-expected-artifacts-manifest-repair-01KZY498-lane-b
base_commit: c54fbf13cdd2a52adde447eb05090f158d57687d
created_at: '2026-08-14T04:25:57.388817+00:00'
subtasks:
- T015
- T016
- T017
phase: Phase 2 - New plan manifest (depends on WP01)
assignee: ''
agent: claude
history:
- timestamp: '2026-08-14T00:00:00Z'
  agent: claude
  action: Prompt generated via manual /spec-kitty.tasks-outline + /spec-kitty.tasks-packages equivalent (tasks-authoring agent)
agent_profile: implementer-ivan
authoritative_surface: packs/built-in/missions/plan/
create_intent:
- packs/built-in/missions/plan/expected-artifacts.yaml
execution_mode: code_change
model: ''
owned_files:
- packs/built-in/missions/plan/expected-artifacts.yaml
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – Author `plan` manifest + file follow-up guard-gap issue

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Ship the fourth built-in mission type's `expected-artifacts.yaml` — `plan` — honestly
scoped to `plan` mission type's own state machine (Decision 1), and file the
independent upstream defect this investigation surfaced (the hardcoded
`mission_family="software-dev"` in `_check_cli_guards` + `plan`'s accidental
`review`-step-id collision). This is **Implementation Concern IC-03** from
`plan.md`.

## Context

**Why this WP exists**: `spec.md` User Story 2 / claim 1 — `plan` is the only
built-in mission type shipping no manifest. Author it against `plan`'s own state
machine and real artifacts, **not** `software-dev`'s CLI vocabulary — even though
that is the dispatch chain `plan`-type steps silently fall through to today (no
dedicated `plan`-family guard branch exists — see `tracer-design-decisions.md`
Decision 1 for the full, corrected mechanism, including the `review`-step-id
lexical collision that is NOT a second no-op fallback).

**Dependency on WP01**: same reasoning as WP02 — validate this new file against
the hardened `extra="forbid"` schema from the moment it's authored.

**This WP is the only WP that touches `packs/built-in/missions/plan/expected-artifacts.yaml`**
— it is a brand-new file (`.kittify/overrides/missions/plan/` already exists as a
directory with `mission.yaml`/`mission-runtime.yaml`/`README.md`/`templates/`/
`command-templates/`, but has **no** `expected-artifacts.yaml`; per FR-010's note
and C-004, **do not create one** — the override tier is inert for this asset type,
so a new override file here would add an unconsumed file, not restore
consistency).

### ⚠️ Out-of-map edit: `tests/dossier/test_manifest.py`

Same pattern as WP02: this WP does not list `tests/dossier/test_manifest.py` in
`owned_files` (WP01 owns it) but makes a small, well-justified out-of-map edit
adding a new class, `TestPlanManifest`, with exactly one new test. Stay strictly
within that new class — do not touch any other class in this file, including the
`TestManifestReconciliation` class WP02 owns and the `TestOverrideMirrorDeprecation`
class WP04 owns. **Chokepoint**: WP02 and WP04 similarly each edit this file and
each also depend only on WP01 — per `lanes.json`, WP02, WP03, and WP04 all sit in
`parallel_group: 1` with no dependency edge among the three of them. See
`tracer-approach.md`'s "Chokepoints & execution sequencing" addendum for the
recommended sequencing.

## Subtask T015: Red-first test — `plan` manifest loads and matches the state machine (FR-010, AS1-AS4 of US2)

**Purpose**: Pin the target shape of the new manifest before authoring it.

**Steps**:
1. In `tests/dossier/test_manifest.py`, add a new class `TestPlanManifest`.
2. Add `test_plan_manifest_loads_and_matches_state_machine`:
   - `ManifestRegistry.load_manifest("plan")` returns non-`None`.
   - `manifest.mission_type == "plan"`, `manifest.manifest_version == "1"`.
   - `manifest.get_step_ids()` returns **exactly** `["goals", "research",
     "structure", "draft", "review", "done"]` — order-sensitive, matching
     `packs/built-in/missions/plan/mission.yaml`'s `states` list (verify this
     order against the actual `mission.yaml` file, currently at lines 9-26, before
     writing the assertion — don't assume the order from this prompt alone).
   - `get_required_artifacts(manifest, "goals")` returns one blocking spec with
     `path_pattern == "goals.md"`.
   - `get_required_artifacts(manifest, "research")` returns one blocking spec with
     `path_pattern == "research.md"`.
   - `get_required_artifacts(manifest, "draft")` returns one blocking spec with
     `path_pattern == "plan.md"`.
   - `get_required_artifacts(manifest, "structure")`,
     `get_required_artifacts(manifest, "review")`, and
     `get_required_artifacts(manifest, "done")` each return `[]` — no filesystem
     artifact requirement, matching `mission.yaml`'s transitions for those states
     (note in a code comment that `structure→draft` is unconditional and
     `review→done` gates on `gate_passed("plan_approved")`, neither of which is a
     filesystem-artifact check this schema expresses).
3. Add a second, dedicated test in the same `TestPlanManifest` class,
   `test_plan_manifest_header_names_guard_gap_mechanism` — the AS4-specific
   assertion this subtask was previously missing (tasks-phase adversarial review
   fix, round 4, TASKS-FRESH4-001). Mirror the pattern WP04's T018 already
   establishes for the structurally parallel FR-014 case
   (`test_override_mirror_files_carry_deprecation_header`): read the **raw text**
   of `packs/built-in/missions/plan/expected-artifacts.yaml` (plain file read, not
   the parsed `ExpectedArtifactManifest` — the header comment is not part of the
   parsed model) and assert it contains the **specific-mechanism markers** from
   `tracer-design-decisions.md` Decision 1, not merely a generic "no guard exists
   yet" string:
   - the literal substring `mission_family="software-dev"` (or the equivalent
     `mission_family = "software-dev"` spacing actually used in T016's authored
     comment — match whatever T016 lands, don't over-fit to one exact spacing),
   - the literal substring `_check_cli_guards`,
   - a recognizable naming of the `review`-step lexical collision (e.g. the
     assertion should fail if the comment only says "no branch recognizes plan
     step ids" without naming that `review` specifically collides with
     software-dev's own `review` step id).
   Also assert the vaguer, explicitly-rejected framing is **absent** — e.g.
   `assert "no guard exists yet" not in raw_text.lower()` (or an equivalent
   negative check) — so a future genericization of the header that still
   technically mentions "no guard" but drops the specific mechanism is caught,
   not silently passed.

**Files**: `tests/dossier/test_manifest.py` (new class + 2 tests, ~45-60 lines).
**Validation**: RED — the file being tested (`plan/expected-artifacts.yaml`)
doesn't exist yet, so `load_manifest("plan")` currently returns `None` and every
assertion after the first fails in the first test, and the raw-text read in the
second test raises `FileNotFoundError`.

## Subtask T016: Implement — author `packs/built-in/missions/plan/expected-artifacts.yaml`

**Purpose**: Author the new manifest matching T015's red-first test.

**Steps**:
1. Create `packs/built-in/missions/plan/expected-artifacts.yaml` (new file).
   Follow the structural convention of the three existing manifest files (header
   comment block, `schema_version`, `mission_type`, `manifest_version`,
   `required_always: []`, `required_by_step:`, `optional_always: []`) — read
   `packs/built-in/missions/research/expected-artifacts.yaml` as the closest
   structural model (it also has a small, non-CLI state vocabulary).
2. Set `schema_version: "1.0"`, `mission_type: "plan"`, `manifest_version: "1"`.
3. `required_by_step`:
   - `goals:` → one blocking entry, `artifact_key: "output.goals.main"`,
     `artifact_class: "output"`, `path_pattern: "goals.md"`, `blocking: true`.
   - `research:` → one blocking entry, `artifact_key: "evidence.research"` (note:
     this reuses the `evidence.research` key style from the other manifests'
     `optional_always` blocks, but here it is `required_by_step`/blocking, a
     distinct usage — this is fine, `artifact_key` uniqueness is per-manifest, not
     cross-manifest), `artifact_class: "evidence"`, `path_pattern: "research.md"`,
     `blocking: true`.
   - `structure:` → `[]` (no filesystem gate; the `structure→draft` transition is
     unconditional per `mission.yaml`).
   - `draft:` → one blocking entry, `artifact_key: "output.plan.main"`,
     `artifact_class: "output"`, `path_pattern: "plan.md"`, `blocking: true`.
   - `review:` → `[]` (the `review→done` transition gates on
     `gate_passed("plan_approved")`, not a filesystem artifact — add an inline
     comment saying so, so a future reader doesn't assume this step has no gate at
     all).
   - `done:` → `[]`.
4. **Required header comment (AS4 of US2)** — at the top of the file, add a
   comment block stating explicitly, word-for-word matching the mechanism in
   `tracer-design-decisions.md` Decision 1 (not a vaguer "no guard exists yet"):
   that `plan` mission type's step ids are not enforced by a dedicated
   `plan`-family guard branch; `goals`/`research`/`structure`/`draft`/`done` fall
   to `_evaluate_software_dev_guards`'s bare `return []`; and `review` — because
   `_check_cli_guards` hardcodes `mission_family="software-dev"` for every mission
   type — lexically collides with software-dev's own `review` step id and is
   evaluated by `_evaluate_wp_iteration_guard`, today returning `[]` only because
   `wp_advance_ready` defaults `True` with no `tasks/` directory present (a latent
   spurious-block risk, not a second no-op fallback). State that this manifest
   describes `plan`'s own state-machine contract, not a proven cross-consistent
   guard enforcement.
5. **Required FR-013 rationale comment (Decision 2)** — a second, distinct
   comment (do not conflate with the AS4 comment above) at/near
   `manifest_version: "1"`, matching the same rationale text WP02 adds to the
   other three files: `manifest_version` is a sync-namespace identity key, not a
   content-freshness counter; kept at `"1"` per Decision 2.

**Files**: `packs/built-in/missions/plan/expected-artifacts.yaml` (new, ~50-70
lines including comments).
**Validation**: Both of T015's tests
(`TestPlanManifest.test_plan_manifest_loads_and_matches_state_machine` and
`TestPlanManifest.test_plan_manifest_header_names_guard_gap_mechanism`) go
GREEN — the former is the sole place `plan`'s loadability is asserted; the
latter is the sole place the AS4 header comment's specific-mechanism wording is
asserted (not merely reviewed by eye). WP01's own
`test_all_shipped_manifests_load_after_hardening` only ever asserts on
`research`/`documentation`/`software-dev` and was already fully GREEN at WP01's
completion, so there is no WP01-left-open check for this WP to close out.

## Subtask T017: File the upstream guard-gap issue (FR-011, SC-005)

**Purpose**: Name the real defect this investigation surfaced as its own,
independent, tracked issue — distinct from #3388, not fixed in this mission.

**Steps**:
1. **Idempotency guard (required before filing)**: before creating anything,
   search existing issues in this repository for a title/body match from a prior
   attempt at this WP — e.g. `gh issue list --repo Priivacy-ai/spec-kitty --search
   "_check_cli_guards hardcodes mission_family" --state all`. If a matching issue
   already exists (e.g. because WP03 was rejected in the implement-review loop and
   is now being reworked), do **not** file a second issue — reuse the existing
   issue's URL for the rest of this subtask's steps instead. Only proceed to step 2
   if no matching issue is found. This guard exists because `gh issue create` is
   not idempotent and a naive rework of this WP would otherwise file a duplicate
   upstream issue for the same defect.
2. File a new GitHub issue on this repository (`Priivacy-ai/spec-kitty`) via `gh
   issue create`, titled something like: "`_check_cli_guards` hardcodes
   `mission_family=\"software-dev\"`, causing `plan` mission type's `review` step
   to be evaluated by a mission-blind guard branch (latent spurious-block risk)".
3. Body must name, precisely (not "no branch recognizes plan step ids"):
   - `_check_cli_guards` (`src/runtime/next/runtime_bridge.py:680-698`) hardcodes
     `mission_family="software-dev"` for every mission type rather than resolving
     the mission's actual type.
   - `plan`-type missions are therefore always evaluated against
     `_evaluate_software_dev_guards`'s vocabulary.
   - `plan/mission.yaml`'s `review` state accidentally lexically collides with
     software-dev's own `review` step id, so it is evaluated by
     `_evaluate_wp_iteration_guard("review", snapshot)` instead of the bare `[]`
     fallback every other `plan`-type step id reaches.
   - Today this coincidentally still returns `[]` because `wp_advance_ready`
     defaults `True` when a plan mission's directory has no `tasks/` subdirectory —
     but it is a real, reachable, mission-blind branch with a latent
     spurious-block risk if a plan mission's directory ever contains a
     `tasks/WP*.md` set.
   - Cross-reference: discovered during mission
     `expected-artifacts-manifest-repair-01KZY498` (issue #3388), Decision 1 in
     that mission's `tracer-design-decisions.md`.
4. Record the resulting issue URL (whether newly filed in step 2 or reused from
   step 1's guard) in **two** places:
   - Append it to `tracer-design-decisions.md`'s Decision 1 section (a short
     addendum noting the filed issue URL — do not rewrite Decision 1's existing
     text, only append).
   - Include it in this mission's PR body when the PR is opened.
5. Per the charter's Tracker Ticket Assignment Rule, this new issue should be
   assigned to the Human-in-Charge (HiC) as part of filing it (or immediately
   after), the same as this mission's own originating issue #3388 was. If step 1's
   guard found and reused an existing issue, confirm it is already HiC-assigned
   rather than re-assigning it.

**Files**: `tracer-design-decisions.md` (append-only addition to Decision 1, ~3-5
new lines). No production code file.
**Validation**: `gh issue view <new-issue-number>` confirms the issue exists, is
distinct from #3388, and its URL is recorded in both places named above (this is a
tracker-state assertion, verified once at mission close per `plan.md`'s Test
Strategy table — not a pytest test).

## Definition of Done

- [ ] `TestPlanManifest` section exists with its one new test, committed **before**
      T016's implementation commit (C-011).
- [ ] `packs/built-in/missions/plan/expected-artifacts.yaml` exists, parses, and
      matches T015's assertions exactly.
- [ ] The file carries both the AS4 guard-gap header comment (word-for-word
      matching Decision 1's mechanism) and the separate FR-013 `manifest_version`
      rationale comment (Decision 2) — two distinct comments, not one serving both.
- [ ] No `.kittify/overrides/missions/plan/expected-artifacts.yaml` is created.
- [ ] A new GitHub issue exists (or, per T017 step 1's idempotency guard, a
      pre-existing matching issue from a prior attempt was correctly reused
      instead of duplicated), distinct from #3388, naming the precise defect; its
      URL is recorded in `tracer-design-decisions.md` and ready for the PR body.
- [ ] `manifest_version` is `"1"` in this new file (C-002).
- [ ] **T015/T016's code-content portion of this WP (the red-first test and the
      `expected-artifacts.yaml` file itself) may be reviewed and marked complete
      independently of T017's tracker-side completion.** T017 is a distinct,
      external, stateful tracker mutation (`gh issue create`), not ordinary
      code-review-able content — a reviewer approving T015/T016 need not block on
      T017's issue having been filed (or reused) yet, and rework triggered by a
      T015/T016 review comment does not require re-running T017.

## Risks

- **The header-comment requirement (AS4) is easy to under-specify** — it must name
  the exact hardcoded-`mission_family` + `review`-step-collision mechanism, not a
  vaguer "no guard exists yet." The reviewing squad should check this comment
  word-for-word against Decision 1's text, not just confirm a comment is present.
- **The FR-013 rationale comment is a second, distinct comment** this same file
  must carry (Decision 2, not Decision 1) — easy to drop precisely because AS4's
  comment is the more visually prominent one. Confirm both are present.
- **Chokepoint**: see the Context section's chokepoint note re: WP02 and WP04
  sharing `test_manifest.py`.

## Reviewer Guidance

- Read the AS4 header comment side-by-side with `tracer-design-decisions.md`
  Decision 1 — confirm it states the hardcoded-`mission_family` mechanism and the
  `review`-step collision precisely, not a generic "guard gap" statement.
- Confirm the FR-013 comment is present and distinct from the AS4 comment.
- Confirm the filed GitHub issue's body matches the precise defect description
  above, not a shortened "no branch recognizes plan step ids" version (this was
  explicitly corrected during spec review — see Decision 1's own "Correction"
  paragraph).
- Confirm `get_step_ids()`'s returned order matches `mission.yaml`'s `states` list
  order exactly.

Implementation command: `spec-kitty agent action implement WP03 --agent claude`
