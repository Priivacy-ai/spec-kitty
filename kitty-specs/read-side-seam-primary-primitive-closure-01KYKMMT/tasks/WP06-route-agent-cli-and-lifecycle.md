---
work_package_id: WP06
title: Route the agent-CLI and lifecycle shells
dependencies:
- WP02
- WP03
requirement_refs:
- FR-004
- FR-015
- FR-024
- NFR-001
- NFR-002
planning_base_branch: fix/read-side-seam-primary-primitive-closure
merge_target_branch: fix/read-side-seam-primary-primitive-closure
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-seam-primary-primitive-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-seam-primary-primitive-closure unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
phase: Phase 3 - Route
history:
- at: '2026-07-28T09:27:08Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_lifecycle_read_seam_migration.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/agent/mission_feature_resolution.py
- src/specify_cli/cli/commands/agent/mission_finalize.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/cli/commands/accept.py
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/merge/executor.py
- src/specify_cli/retrospective/writer.py
- tests/specify_cli/cli/commands/test_lifecycle_read_seam_migration.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Route the agent-CLI and lifecycle shells

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---


## Objective

Route the **10** `primary_feature_dir_for_mission` sites across the agent-CLI and
lifecycle-shell cluster, and correct the one husk comment in `next_cmd.py`.

This is the most mechanical of the routing WPs — no gate coupling, no foundation sites, no
non-compliant site. It runs fully in parallel with WP05 and WP07 (disjoint files).

## Context & Constraints

Follow **the shared migration procedure** in [tasks.md](../tasks.md) — read it before starting.

**Site distribution** (census on this base — re-derive before starting):

| File | Sites | Notes |
|---|---|---|
| `cli/commands/agent/mission_feature_resolution.py` | 1 | |
| `cli/commands/agent/mission_finalize.py` | 1 | |
| `cli/commands/agent/tasks_move_task.py` | 2 | |
| `cli/commands/accept.py` | 1 | |
| `cli/commands/next_cmd.py` | 3 | **+ 1 husk comment** |
| `merge/executor.py` | 1 | |
| `retrospective/writer.py` | 1 | ⚠ **foundation site — DO NOT route.** Beneath `read_dir`'s RETROSPECTIVE short-circuit; WP03 re-pointed it at the leaf. **Verify only** — see T029. |

- **The ledger is the authority** (`docs/development/read-side-seam-classification.md`, terminal
  shape from WP02). Apply verdicts; do not re-derive them.
- **NFR-001** — identical resolved directory for a materialized, non-backfilled mission; the only
  permitted delta is the seam's bare-`<slug>` backfill recovery.
- **NFR-002** — no new raises where leniency is the contract. A PRIMARY kind must not begin
  raising on husk / empty / deleted-coord.
- **C-007** — not a bulk edit. Each site gets an individual kind decision.
- **Do not edit any file under `tests/architectural/`.** Those gates belong to WP01 and WP02.

## Doctrine for this WP

- **`tactic:refactoring-strangler-fig`** — reroute cadence only: one caller at a time, **verify
  after each**, delete the legacy path last (WP08 does the deletion).
  `Run: spec-kitty charter context --include tactic:refactoring-strangler-fig`
  **When doing T029**, `next_cmd.py` has 3 sites and `tasks_move_task.py` 2 — verify per site.
  Ten sites batched into one test run makes a divergence unattributable, which is the only thing
  this cadence buys and the only reason it is prescribed.
- **`tactic:change-apply-smallest-viable-diff`** — route the read; leave the surrounding function
  alone. `Run: spec-kitty charter context --include tactic:change-apply-smallest-viable-diff`
- **`DIRECTIVE_041`** — classify every red **STALE / PATCHWORK / VALID**; never retry-to-green.
  Check WP01's `research/expected-reds.md` first — a red may be expected-by-design and owned elsewhere.
  `Run: spec-kitty charter context --include directive:DIRECTIVE_041`
- **`tactic:canonical-source-unification`** — reuse the module's existing seam import; do not add
  a per-module read helper.
  `Run: spec-kitty charter context --include tactic:canonical-source-unification`
  **When doing T029** for `retrospective/writer.py` specifically — see the note below.

## Subtasks

### T029 — Route the 10 sites per ledger verdict (FR-004)

Apply the shared procedure per site, verifying after each.

**Kind selection matters.** ~24 of the mission's sites have an unambiguous kind:
`PRIMARY_METADATA`, plus `WORK_PACKAGE_TASK` and `ANALYSIS_REPORT` where the site names those
artifacts. `mission_finalize.py` and `tasks_move_task.py` touch work-package tasks;
`accept.py` touches analysis reports. Pick the kind from **what the site actually reads
downstream**, not from what is least effort. A wrong `kind` argument is **census-invisible by
construction** — no gate catches it.

**`retrospective/writer.py:85` — DO NOT ROUTE. It is a foundation site; WP03 already re-pointed
it.** ⚠ My earlier instruction here said "route through `resolve_retrospective_home`" — that was
**wrong and self-recursive**: line 85 sits *inside* `resolve_retrospective_home` (defined at
line 37), so it would have routed a function through itself.

The real shape, found by WP03's reviewer: `PlacementSeam.read_dir` **short-circuits
`RETROSPECTIVE`** to `resolve_retrospective_home` (`mission_runtime/resolution.py:1462`), never
reaching `resolve_artifact_surface`. So this site sits **beneath** the seam, exactly like the four
FR-005 foundation sites. Routing it through `read_dir` is a genuine **infinite recursion**:
`read_dir(RETROSPECTIVE)` → `resolve_retrospective_home` → `read_dir(RETROSPECTIVE)` → …

**Your job here is to VERIFY, not to route**: confirm WP03 re-pointed line 85 at the module-private
leaf `_compose_primary_feature_dir`, that it is recorded as a foundation/sanctioned site, and that
no cycle exists in the `read_dir` call graph (NFR-009). If it still calls the public wrapper,
report it — do **not** route it through the seam.

**Watch for**: `next_cmd.py`'s sites sit near the husk comment you correct in T030 — handle them
together.

### T030 — Correct the `next_cmd.py` husk comment (FR-015)

One of the six husk-conflating comments lives here. It argues against routing by naming the
**coord-aware / topology-aware** resolver's failure mode — which is true of the *kind-blind*
`resolve_feature_dir_for_mission` and **false** of the kind-aware seam: for a PRIMARY-partition
kind the decision layer short-circuits to PRIMARY *before any coord probe*.

Preserve the **true** warning (the kind-blind resolver does select the husk); remove the
**false** implication about the seam. Correct it in the **same commit** as the call site it
annotates.

### T031 — Behaviour-preservation evidence for the cluster (NFR-001, NFR-002, NFR-003)

Write `tests/specify_cli/cli/commands/test_lifecycle_read_seam_migration.py`:

1. For **representative** migrated sites (at least one per file), a materialized mission
   resolves an **identical** directory pre/post migration.
2. A PRIMARY-kind read on a **husk** mission resolves the primary anchor and does **not** raise;
   same for an empty coord worktree and a deleted coord branch (NFR-002).
3. Red-first (NFR-003): verify by reverting one routed site and observing the failure.
4. Build fixtures under the **session scratchpad**, not a bare `/tmp` path; remove any throwaway
   worktree afterwards.

Do **not** duplicate WP04's husk pin for the other resolver — this is about *your* cluster's
sites.

## Branch Strategy

- Planning/base branch: **`fix/read-side-seam-primary-primitive-closure`**
- Final merge target: **`fix/read-side-seam-primary-primitive-closure`**
- Claim and prepare the workspace with the canonical entry point:
  `spec-kitty agent action implement WP06 --agent <name>`
- Worktree allocated **per computed lane** from `lanes.json` by that command.
  Never hand-construct it; never `git stash` inside a lane worktree.

## Test Strategy

```bash
PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest \
  tests/specify_cli/cli/commands/ tests/merge/ -q
```

Plus the six C-008 gates (tasks.md §5), `uv run ruff check <changed>`, and project-mode
`uv run python -m mypy --strict src/specify_cli src/charter src/doctrine`.

## Definition of Done

- All 10 sites routed per ledger verdict, each with a kind chosen from what it actually reads,
  verified per site (T029).
- `retrospective/writer.py` routed through `resolve_retrospective_home`, with the choice and its
  justification stated in the per-site kind table (above), not merely asserted.
- The `next_cmd.py` husk comment corrected in the same commit as its call site (T030).
- Behaviour preservation pinned red-first: identical directories for materialized missions; no
  new raises on husk / empty / deleted-coord (T031).
- No edits under `tests/architectural/`.
- **Per-site kind table in the Activity Log** (this is what makes Reviewer Guidance #1
  checkable): one row per routed site — *site → kind chosen → the downstream filename that
  justifies it*. A wrong `kind` argument is **census-invisible by construction**, so this table
  is the only artifact a reviewer can check it against.
- **Read-side census ratchet (zero additions)**: the bypass gate's finding set after this WP
  equals the set recorded in `research/expected-reds.md` **minus exactly the sites this WP
  routed** — no additions. The node stays red until WP08, so this per-site diff is the only
  real signal available to this WP; a new finding is a regression even though the node's
  red/green state did not change.
- `ruff` and project-mode `mypy` clean.
- Finish: commit, `spec-kitty agent tasks mark-status T029 T030 T031 --status done`, then `spec-kitty agent tasks move-task WP06 --to
  for_review` and **wait** for the synchronous pre-review gate.

## Risks

- **Wrong `kind` is the invisible error.** No gate catches it; only review does. Trace what each
  site reads downstream before choosing.
- **`retrospective/writer.py`** may need its dedicated home resolver rather than `read_dir` —
  check, do not default.
- A red in the fold-prescription gate on a newly-routed site means WP01's kind-discriminated
  widening did not cover your call shape. Report it as a WP01 gap; do **not** add a local
  exemption.
- Foreign honest-red P0s will appear in your lane (`tests/sync/test_sync_consent_default_deny.py`,
  #3031, marked `fast`). Not yours. Do not touch (C-010).

## Reviewer Guidance

1. For each of the 10 sites: does the declared **kind** match what the site actually reads?
2. Was `retrospective/writer.py` routed through the dedicated home resolver where that is the
   surface's idiom, rather than a second authority?
3. Is the behaviour-preservation test **red-first**? Revert a routed site and confirm.
4. Were sites verified **individually**, or batched and tested once at the end?
5. Does the corrected `next_cmd.py` comment keep the true kind-blind warning?

## Activity Log

> **CRITICAL**: entries MUST be chronological — **append** new entries at the END, never
> prepend or insert. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`, timestamp in
> UTC (`date -u "+%Y-%m-%dT%H:%M:%SZ"`). The acceptance system reads the LAST entry as the
> current state, so out-of-order entries fail acceptance even when the work is complete.

- 2026-07-28T09:27:08Z – system – Prompt created.
