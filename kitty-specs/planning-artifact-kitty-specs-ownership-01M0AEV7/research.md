# Research — Planning-artifact WPs Own kitty-specs Paths

Phase 0 consolidation. Every open question was resolved by a 3-lens research squad
(root-cause · lifecycle · related-issue survey) plus git archaeology; no NEEDS
CLARIFICATION markers remain. No dependency decisions (supply-chain N/A).

## Decision 1 — Direction: exempt planning_artifact from the finalize ban

- **Decision**: Make the `finalize-tasks` `kitty-specs/` owned-files ban execution-mode-aware:
  skip work packages whose `execution_mode == planning_artifact`; keep the ban fail-closed for
  `code_change` (and unset→inferred-code).
- **Rationale**: The ownership model already treats `kitty-specs/` ownership as the *blessed* shape
  for `planning_artifact` (`ownership/validation.py:75` `_PLANNING_PREFIXES`;
  `validate_execution_mode_consistency:274-285` only warns when owned files fall *outside*
  `kitty-specs/`+`docs/`). The lane layer already routes such work packages to the repo-root
  planning lane (`lanes/compute.py:326-355`, `_build_planning_lane`). Only `finalize-tasks`
  disagrees, via a mode-blind predicate.
- **Archaeology**: The ban is a later over-reach, not older doctrine. Planning model landed
  2026-03-30 (`5d23865743`, #347); the blanket ban landed 2026-05-21 (`c8c5a34ee4`, #1269 WP03).
  #1269's own spec (User Story 3) scoped the ban to *"kitty-specs files that lane branches cannot
  commit"* — the `code_change`/worktree hazard. The same mission (WP04) even added a sibling
  planning-artifact carve-out at the implement preflight but never applied it to the finalize ban.
- **Alternatives considered**:
  - *Support `owned_files: []` end-to-end for executable WPs* — rejected: invents an "executable WP
    that owns nothing," erases the auditable deliverable (#2643's own complaint), and forces changes
    in two load-bearing places (`build_wp_manifests`, `compute_lanes`) the overlap/surface/merge
    machinery was never designed for.
  - *Own a path under neither prefix (e.g. `scripts/foo.py`)* — the current workaround; distorts the
    decomposition and, if switched to `code_change`, drops the WP into a `.venv`-less lane worktree.

## Decision 2 — Fix locus: the ban predicate, not the path classifier

- **Decision**: Add the guard inside `_invalid_mission_specs_owned_files`
  (`cli/commands/agent/mission_parsing.py:220-229`), which already iterates each WP's `WPMetadata`
  (so `execution_mode` is in hand). Do **not** touch `_is_mission_specs_owned_file` (a bare
  `path: str` with no mode).
- **Rationale**: Minimal, keeps the path classifier pure, and preserves the mode-aware decision at
  the one place that owns it. `execution_mode` is authoritative at ban time because
  `_validate_owned_files_not_in_mission_specs` runs at `mission_finalize.py:2069`, *after*
  `_run_bootstrap_loop` populates `state.inmemory_frontmatter` (explicit-authored preserved; absent
  inferred).
- **Seam constraint**: preserve the dynamic alias `_invalid_kitty_specs_owned_files`
  (`mission_parsing.py:236`) and the shim re-exports — they are monkeypatch targets.

## Decision 3 — Safety: no downstream change needed

- **Decision**: No change to `ownership/validation.py`, `lanes/compute.py`, `workspace/context.py`,
  `policy/commit_guard.py`, or the move-task lane-hygiene guard.
- **Rationale (proven)**: `planning_artifact` WPs resolve to the repo-root/primary checkout, never a
  `.worktrees/` lane branch (`workspace/context.py:800-842`, `879-893`; `create_planning_workspace`
  returns `repo_root`). The lane commit guard is gated behind `is_implementation_branch`
  (`commit_guard.py:70-71`) and the move-task lane-hygiene guard returns early for repo-root WPs
  (`tasks_move_task.py:568-570`) — so neither can fire for a planning artifact. And
  `build_wp_manifests` emits a manifest whenever `owned_files` is truthy (`validation.py:356`), so a
  populated `planning_artifact` WP routes to the planning lane without the "no ownership manifest"
  raise.

## Adversarial evidence

No security-impacting dependency decision was made (supply-chain N/A). A post-plan adversarial
squad challenge pass is run per the mission pipeline; contested findings and their dispositions are
recorded against `contracts/adversarial-evidence-contract.md` if any arise.

## Residual / out of scope (tracked)

- File-less (`owned_files: []`) planning WP support remains latently broken at `validation.py:356` /
  `compute.py:331` — sidestepped by requiring a real deliverable; follow-up if a real mission needs it.
- `validate_no_overlap` planning-lane intra-lane overlap caveat — pre-existing; only bites parallel
  planning WPs with overlapping scopes.
- #3214 (validators exported but never called) and #3432 (P0, same `compute_lanes` raise) — adjacent,
  out of scope; noted for coordination.
