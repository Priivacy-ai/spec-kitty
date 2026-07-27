# Tooling-Friction Trace — implement-loop-coord-authority-completion-01KW2E7A

**Purpose:** a running log of spec-kitty tooling friction encountered while running this
mission (itself a coord-topology / dogfooding mission that *fixes* the implement-loop
read split-brain). Seeded at spec; **append during the implement loop**; reviewed at
close to assess tooling state. This mission is peak dogfooding — the very read paths it
fixes are the paths the loop uses to run it, so friction here is often a live repro of
the bug under fix.

> Format per entry: `[date] [phase] SYMPTOM — anchor — disposition (fixed PR#/ticket#/workaround/open)`

---

## Seeded during spec (2026-06-26)

1. **[spec] Branch base hygiene — old design branch carried 68 unsquashed commits.**
   `design/infra-logic-separation-2173` held the full unsquashed Phase-1 history while
   PR #2181 squash-merged to upstream/main as `551044214`. Disposition: **workaround** —
   branched the new mission cleanly from `upstream/main` (not the stale design branch).
   Not a tool bug; a branch-lifecycle reminder (squash-merge leaves local history ahead).

2. **[spec] `mission create` left `spec.md` at 0 bytes (expected, #846 boundary).**
   The scaffold writes an untracked empty spec.md; agent authors + `spec-commit`s. Worked
   as documented. Disposition: **expected** (not friction; noting the boundary held).

## During implement loop — APPEND BELOW

3. **[implement-start] PEAK DOGFOODING — the mission's own loop hit the #2115 bug it fixes.**
   `spec-kitty agent tasks status` (and `next`) failed at implement-start with
   `Tasks directory not found: .worktrees/<slug>-coord/kitty-specs/<slug>/tasks`. The mission
   was created `--pr-bound` → `topology: coord`; the coord husk carries no `tasks/` (planning
   artifacts went to PRIMARY per #2106), and the status reader resolved the coord-aware path.
   **This is FR-001's exact symptom, witnessed LIVE** (the coord branch is empty for the
   mission dir; all `tasks/WP*.md` are on the primary design branch) — strong acceptance
   evidence that #2115 is real and reachable. Disposition: **workaround = flatten** (meta.json
   `topology: coord`→`single_branch`, removed `coordination_branch`, `flattened: true`), the
   operator-established pattern; reads then resolve primary and the loop runs. Orphaned
   `-coord` worktree/branch left in place (single_branch resolvers ignore it). Note: after this
   mission lands, coord-topology missions won't hit this.
<!-- WATCH (this mission dogfoods these exact surfaces): does `tasks status`/`tasks list`
     hard-fail "Tasks directory not found" on this coord mission (FR-001 live repro)? does
     `review` auto-find fail (FR-002 / _find_first_for_review_wp)? does the workspace WP
     index 404 (FR-005 / build_normalized_wp_index)? does `_mark_wp_merged_done` silently
     skip the done-transition at merge (FR-004)? does `record-analysis`/move-task/finalize
     fight the coord topology? Cite witnessed evidence + disposition. Each live repro here
     is also acceptance evidence for the matching FR. -->

4. **[implement-loop] Flat-execution / lane-workflow tension — the approve gate wants code on a
   lane branch, but flat/on-branch execution should be possible.** After flattening to
   `single_branch` and choosing flat execution (code committed directly on the design branch,
   no lane worktree), the approve gate refused with *"No implementation commits on lane branch!"*
   — it inspects the lane branch for the deliverable, which doesn't exist under flat execution.
   Compounding guards on the same path: `agent action implement`/`review` re-spawn a lane
   worktree even for a flat mission; the kitty-specs-on-lane guard blocks `move-task` when a
   lane carries status files; and lane allocation branched from the stale pre-rebase base. The
   only escape is `move-task --to approved --force`, which is a blunt override (also bypasses
   real lane-deliverable verification). **Disposition: workaround = flat + `--force` approve;
   gap = the workflow has no first-class "flat / on-branch execution" mode.** A flattened
   `single_branch` mission should support implement→review→approve with the deliverable on the
   target branch itself — the approve gate should accept on-branch commits (verify the WP's
   owned_files changed on the design branch) instead of demanding a lane branch. Candidate
   follow-up under the #2017 guard-friction umbrella (operator chose not to file now).

_(append during implement)_

5. **[merge/naming] `spec-kitty merge` is misnamed — should probably be `finalize`.** Operator
   observation (2026-06-27): the `merge` verb conflicts in intent with how this repository's
   own workflow uses "merge." Here, `spec-kitty merge` integrates a mission's lane branches into
   the **local** integration/target branch (it explicitly does NOT push to origin/main — see
   CLAUDE.md). But in our actual development model, "merge" means the **final PR merge into
   mainline after human review**: fully-finalized feature branches → PR → review → merge to
   main. So the command's name collides with the load-bearing meaning of "merge" in the team's
   git workflow, inviting the exact mistake the no-direct-push policy guards against. Renaming it
   to **`finalize`** (it finalizes the mission's lanes onto the integration branch, leaving the
   PR-merge to the operator) would disambiguate intent and align the vocabulary with the
   PR-based process. Disposition: **naming/UX gap, candidate follow-up** (operator-noted; not
   filed). Adjacent to the flat-execution / lane-loop friction in entries #3–#4 above.
