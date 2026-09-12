---
work_package_id: WP05
title: Route the trio and green its gate
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
- T026
- T027
- T028
phase: Phase 3 - Route
history:
- at: '2026-07-28T09:27:08Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/
create_intent:
- tests/specify_cli/acceptance/test_trio_read_seam_migration.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/workflow_cores.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/implement_cores.py
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/acceptance/summary_core.py
- src/specify_cli/acceptance/gates_core.py
- tests/specify_cli/acceptance/test_trio_read_seam_migration.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '2465'
- '2824'
---

# Work Package Prompt: WP05 – Route the trio and green its gate

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

Route the **10** `primary_feature_dir_for_mission` sites in the trio's 4 rewrite targets,
correct the 5 misleading comments those files carry, and turn `test_trio_seam_only.py` green on
the positive assertion WP01 installed.

## ⚠ Why this WP owns all 8 trio files (non-negotiable slicing axis)

`test_trio_seam_only.py` asserts its blessed resolver names are **currently used** by 8
specific files, 4 of which are rewrite targets. A directory-based split would scatter those 4
across three WPs, and the blessed-name shrink would only become safe after the *third* one
landed — three-way cross-WP coordination on a single gate, which is precisely the predecessor
mission's known failure mode.

So: **trio membership beats directory.** You own all 8 trio files, even the 4 with no call
sites (the cores), because the gate scans all 8.

## Context & Constraints

Follow **the shared migration procedure** in [tasks.md](../tasks.md) — read it before starting.

- **The ledger is the authority** (`docs/development/read-side-seam-classification.md`, terminal
  shape from WP02). Apply verdicts; do not re-derive them.
- **NFR-001** — identical resolved directory for a materialized, non-backfilled mission; the only
  permitted delta is the seam's bare-`<slug>` backfill recovery.
- **NFR-002** — no new raises where leniency is the contract.
- **C-007** — not a bulk edit. Each site gets an individual kind decision.
- **WP01 already shrank the blessed set and installed a positive assertion.** That gate is
  currently **red by design** (it is on `research/expected-reds.md`). Greening it is your deliverable —
  do **not** edit `test_trio_seam_only.py`; WP01 owns it. If you believe the assertion is wrong,
  report it rather than editing another WP's file.

**Site distribution** (census on this base — re-derive before starting):

| File | Primary-primitive sites | Comments to correct |
|---|---|---|
| `cli/commands/agent/workflow.py` | 2 | — |
| `cli/commands/agent/workflow_executor.py` | 3 | **3 husk comments** |
| `cli/commands/implement.py` | 4 | — |
| `acceptance/__init__.py` | 1 | **2 misleading comments** (~:1021-1023) |
| `workflow_cores.py`, `implement_cores.py`, `acceptance/summary_core.py`, `acceptance/gates_core.py` | 0 (gate-scanned only) | — |

## Doctrine for this WP

- **`tactic:refactoring-strangler-fig`** — reroute cadence only: one caller at a time, **verify
  after each**, delete the legacy path last (the deletion is WP08's, not yours).
  `Run: spec-kitty charter context --include tactic:refactoring-strangler-fig`
  **When doing T026**, `implement.py` has 4 sites and `workflow_executor.py` 3 — verify per site,
  not per file. A batched edit makes divergence unattributable.
- **`tactic:change-apply-smallest-viable-diff`** — route the read; do not restructure the
  surrounding function.
  `Run: spec-kitty charter context --include tactic:change-apply-smallest-viable-diff`
- **`DIRECTIVE_041`** — classify every red **STALE / PATCHWORK / VALID** before touching it;
  never retry-to-green. Check `research/expected-reds.md` first — a red may belong to another WP.
  `Run: spec-kitty charter context --include directive:DIRECTIVE_041`
  **When doing T028**, the trio gate red is expected-by-design until your routing lands.
- **`tactic:canonical-source-unification`** — one authority per question.
  `Run: spec-kitty charter context --include tactic:canonical-source-unification`
  **When doing T026**, reuse the module's existing seam import; introducing a second read helper
  "for the cores" is the split-brain shape.

## Subtasks

### T026 — Route the 4 trio rewrite targets (10 sites) (FR-004)

Apply the shared procedure per site. All 10 read PRIMARY artifacts off a deliberately PRIMARY
anchor, so they are `migrate-fail-loud` by construction — but **confirm each against the
ledger** rather than assuming.

**Kind selection**: ~24 of the mission's sites have an unambiguous kind — `PRIMARY_METADATA`,
plus `WORK_PACKAGE_TASK` and `ANALYSIS_REPORT` where the site names those artifacts. `implement.py`
and `workflow_executor.py` read work-package tasks and analysis reports; do not flatten
everything to `PRIMARY_METADATA` when a more precise kind is what the site actually reads. The
whole point is that the caller declares *what*.

**Steps**:
1. Per site: read what it opens downstream, pick the kind from that, route through
   `placement_seam(repo_root, handle).read_dir(<kind>)`.
2. Reuse the existing seam import in the module. Do **not** add a second read authority.
3. Verify after each site.
4. The 4 core files carry no call sites — confirm by census, and leave them alone beyond that.

**Validation**: no trio file imports `primary_feature_dir_for_mission` or
`_canonicalize_primary_read_handle`.

### T027 — Correct the 5 misleading comments (FR-015)

**Purpose**: these comments are the mission's origin story. They argue against routing by
describing failure modes of a *different* resolver — the same defect class that manufactured
issue #3014.

**The correction to make** (all 5): the **kind-blind** resolver
(`resolve_feature_dir_for_mission`) genuinely can select the **husk**. The **kind-aware seam**
does not have that property: for a PRIMARY-partition kind the decision layer short-circuits to
PRIMARY *before any coord probe*. Preserve the **true** warning; remove the **false**
implication about the seam.

1. **`acceptance/__init__.py` (~:1021-1023)** — two comments, the `#2824` residual. The
   functional defect they describe was **already fixed** in `6923d1d40` and is regression-green;
   only the comments remain wrong. The suggested fix in #2824 would have broken `lanes.json`
   placement (C-001: `LANE_STATE` **is** PRIMARY). Make sure the corrected comment does not
   re-assert that `lanes.json` belongs on COORD.
2. **`workflow_executor.py` — 3 husk comments.** Same correction; each names the coord-aware
   resolver as the reason not to route.

Correct them **in the same commit as the call site you are standing next to** — a comment
corrected in a different commit from the code it annotates goes stale immediately.

### T028 — Green the trio gate (SC-001 partial)

**Purpose**: demonstrate the red→green transition WP01 set up.

**Steps**:
1. Run `uv run pytest tests/architectural/test_trio_seam_only.py -q`. It should go from red
   (expected, on `research/expected-reds.md`) to **green**.
2. Confirm the gate is green **because the positive assertion holds**, not because a set went
   empty. Sanity-check it by planting a leaf-primitive import in a trio file and confirming the
   gate **reds**, then reverting.
3. Write `tests/specify_cli/acceptance/test_trio_read_seam_migration.py`: behaviour preservation
   for representative migrated sites — identical directory for a materialized mission (NFR-001),
   and no new raise on husk / empty / deleted-coord for a PRIMARY kind (NFR-002).
4. Record the transition in your handoff: the node ids that went green and the `research/expected-reds.md`
   entries they discharge.

**Scope check (#2465)**: that issue asks whether all four resolvers in one of these files can be
consolidated. Assess and **report** — no closing keyword. Do not widen scope to do it unless it
falls out of the routing naturally.

## Branch Strategy

- Planning/base branch: **`fix/read-side-seam-primary-primitive-closure`**
- Final merge target: **`fix/read-side-seam-primary-primitive-closure`**
- Claim and prepare the workspace with the canonical entry point:
  `spec-kitty agent action implement WP05 --agent <name>`
- Worktree allocated **per computed lane** from `lanes.json` by that command.
  Never hand-construct it; never `git stash` inside a lane worktree.

## Test Strategy

```bash
PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest \
  tests/specify_cli/acceptance/ tests/specify_cli/cli/commands/ -q
```

Plus the six C-008 gates (tasks.md §5), `uv run ruff check <changed>`, and project-mode
`uv run python -m mypy --strict src/specify_cli src/charter src/doctrine`.

## Definition of Done

- All 10 sites routed per ledger verdict, each with a kind chosen from what it actually reads,
  verified per site (T026).
- No trio file imports either drained name.
- All 5 comments corrected, each in the same commit as its call site; none re-asserts that
  `lanes.json` belongs on COORD (T027).
- `test_trio_seam_only.py` **green**, and demonstrably green because the positive assertion
  holds — verified by planting a leaf import and observing the red (T028).
- Behaviour preservation pinned: identical directories for materialized missions; no new raises.
- `research/expected-reds.md` entries this WP discharges are named in the handoff.
- #2465 assessed and **reported as a comment on the issue itself** (no closing keyword) — a
  named venue, not "reported" in the abstract.
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
- Finish: commit, `spec-kitty agent tasks mark-status T026 T027 T028 --status done`, then `spec-kitty agent tasks move-task WP05 --to
  for_review` and **wait** for the synchronous pre-review gate.

## Risks

- **Do not edit `test_trio_seam_only.py`** — WP01 owns it. Its red is expected until you land.
- **Do not flatten kinds** to `PRIMARY_METADATA` for convenience. A wrong `kind` argument is
  **census-invisible by construction** — no gate will catch it, which makes it the one error
  class only review can stop.
- The `acceptance/__init__.py` comment sits *at* a rewritten call site. Correct them together.
- A red in the fold-prescription gate on a newly-routed site means WP01's kind-discriminated
  widening did not cover your call shape — report it as a WP01 gap rather than adding a local
  exemption.

## Reviewer Guidance

1. For each of the 10 sites: does the declared **kind** match what the site actually reads
   downstream? This is the error class no gate catches.
2. Is `test_trio_seam_only.py` green because the **positive assertion holds**? Plant a leaf
   import yourself and confirm it reds.
3. Do the 5 corrected comments still carry the **true** warning about the kind-blind resolver,
   and does none of them re-assert the `lanes.json`-on-COORD error (C-001)?
4. Were sites verified **individually** (strangler-fig cadence), or batched and tested once?
5. Was `test_trio_seam_only.py` left untouched (WP01's file)?

## Activity Log

> **CRITICAL**: entries MUST be chronological — **append** new entries at the END, never
> prepend or insert. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`, timestamp in
> UTC (`date -u "+%Y-%m-%dT%H:%M:%SZ"`). The acceptance system reads the LAST entry as the
> current state, so out-of-order entries fail acceptance even when the work is complete.

- 2026-07-28T09:27:08Z – system – Prompt created.
