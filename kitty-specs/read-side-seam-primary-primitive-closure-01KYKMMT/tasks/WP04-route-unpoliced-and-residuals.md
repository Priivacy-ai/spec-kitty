---
work_package_id: WP04
title: Route the topology-routed reads and close the two residuals
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-004
- FR-011
- FR-013
- FR-015
- FR-024
- NFR-001
- NFR-002
planning_base_branch: fix/read-side-seam-primary-primitive-closure
merge_target_branch: fix/read-side-seam-primary-primitive-closure
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-seam-primary-primitive-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-seam-primary-primitive-closure unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
phase: Phase 3 - Route
history:
- at: '2026-07-28T09:27:08Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/mission_setup_plan.py
create_intent:
- tests/specify_cli/missions/test_topology_routed_read_migration.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/agent_tasks_ports.py
- src/specify_cli/cli/commands/decision.py
- src/specify_cli/cli/commands/mission_type.py
- src/specify_cli/context/resolver.py
- src/specify_cli/decisions/emit.py
- src/specify_cli/lanes/recovery.py
- src/specify_cli/widen/state.py
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- tests/specify_cli/missions/test_topology_routed_read_migration.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '2886'
- '2707'
---

# Work Package Prompt: WP04 – Route the topology-routed reads and close the two residuals

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

Close the **one genuinely unguarded silent-wrong-read path** in the tree, and the two
coord-awareness residuals that came with it.

`resolve_feature_dir_for_mission` is **kind-blind and topology-routed** — the combination that
lets it hand a caller the **husk** (a coord worktree that exists but carries no `meta.json`).
It is policed by nothing today; WP02 censused it and wrote a verdict per site. Your job is to
**apply** those verdicts, not to re-derive them.

Then route **both** `_run_documentation_wiring` metadata reads (#2886), which WP01 un-exempted
by removing the `#2214` pin — so the closeout gate is currently red on them and your routing is
what turns it green.

## Context & Constraints

Follow **the shared migration procedure** in [tasks.md](../tasks.md) — read it before starting.
It is the same eight steps for every routing WP.

- **The ledger is the authority.** `docs/development/read-side-seam-classification.md` (terminal
  shape landed by WP02) carries a disposition per site: **`migrate-fail-loud`** /
  **`stay-lenient`** / **`sanction-infra`**. Use those three names only. Do **not** invent a
  classification, and do not "improve" a verdict you disagree with — report the disagreement.
- **NFR-001** — identical resolved directory for a materialized, non-backfilled mission. The
  only permitted delta is the seam's bare-`<slug>` backfill recovery.
- **NFR-002** — no new raises where leniency is the contract. A PRIMARY kind must not begin
  raising on husk / empty / deleted-coord.
- **C-007** — this is **not** a bulk edit. Every site needs an individual semantic decision.
- **C-003** — a `stay-lenient` site keeps its production comment as the **rationale of record**
  in a per-site allow-list descriptor. No path-scoped blankets.

**Why both dependencies are real**: WP02 owns the classification you apply. WP01 taught the
fold-prescription gate the tier-1 seam idiom — routing **before** that lands would flag your
newly-routed sites as violations (green-by-omission in reverse) — and WP01 removed the `#2214`
pin, which is what makes T024 a red→green transition rather than a no-op.

## Doctrine for this WP

- **`tactic:refactoring-strangler-fig`** — **reroute cadence only**: one caller at a time,
  **verify after each**, delete the legacy path last. Its "build a parallel implementation"
  step does **not** apply — the seam already exists with 88 compliant sites.
  `Run: spec-kitty charter context --include tactic:refactoring-strangler-fig`
  **When doing T022/T023**, resist batching all 10 sites into one edit-then-test cycle. Verify
  per site; that is what makes an attribution possible when something diverges.
- **`tactic:canonical-source-unification`** — step 5: *"do not leave a non-canonical copy as a
  fallback — fallbacks revive the split-brain silently."*
  `Run: spec-kitty charter context --include tactic:canonical-source-unification`
  **When doing T024**, do not leave one read routed and one unrouted "for safety". That is the
  precise honesty hole this subtask exists to close.
- **`DIRECTIVE_041`** — for any test that reds while you work: classify **STALE / PATCHWORK /
  VALID** before touching it, and never retry-to-green.
  `Run: spec-kitty charter context --include directive:DIRECTIVE_041`
  **When a red appears**, first check WP01's `research/expected-reds.md` — it may already be accounted
  for and belong to another WP.
- **`tactic:change-apply-smallest-viable-diff`** — each routed site is a small local change; do
  not restructure the surrounding function while you are there.
  `Run: spec-kitty charter context --include tactic:change-apply-smallest-viable-diff`

## Subtasks

### T022 — Route the 8 `resolve_feature_dir_for_mission` sites per ledger verdict (FR-011)

The 8 sites / 7 files, confirmed by census on this base — **re-derive before you start**:

| File | Sites |
|---|---|
| `src/specify_cli/agent_tasks_ports.py` | 1 |
| `src/specify_cli/cli/commands/decision.py` | 1 |
| `src/specify_cli/cli/commands/mission_type.py` | **2** |
| `src/specify_cli/context/resolver.py` | 1 |
| `src/specify_cli/decisions/emit.py` | 1 |
| `src/specify_cli/lanes/recovery.py` | 1 |
| `src/specify_cli/widen/state.py` | 1 |

**Steps** (per site, following the shared procedure):
1. Look up the ledger verdict.
2. `migrate-fail-loud` → `placement_seam(repo_root, handle).read_dir(<kind>)`, the kind chosen
   from **what the site actually reads**. Reuse the module's existing seam import.
3. `stay-lenient` → leave it; confirm the allow-list carries its per-site descriptor with the
   production comment as rationale.
4. `sanction-infra` → do not route; confirm it is recorded by name.
5. Verify after **each** site (strangler-fig cadence), not once at the end.

**Watch for**: several of these sites carry production comments asserting the topology-routed
answer is *required*. Where the ledger says `stay-lenient`, that comment is the rationale of
record — keep it. Where the ledger says `migrate-fail-loud`, the comment is arguing against a
*different* resolver: correct it per FR-015 (preserve the true warning about the kind-blind
resolver; remove the false implication about the kind-aware seam).

### T023 — Route the 3 `primary_feature_dir_for_mission` sites in the same two files (FR-004)

`mission_type.py` (2 sites) and `agent_tasks_ports.py` (1 site) each carry the **primary
primitive** as well. They are yours because they are your files — one pass per file beats two
WPs touching the same lines.

Apply the shared procedure. These are `migrate-fail-loud` by construction (they read PRIMARY
artifacts off a deliberately PRIMARY anchor): pass the kind, let the resolver decide the
partition.

### T024 — Route **both** `_run_documentation_wiring` reads and the write that follows (FR-013)

**Purpose**: close #2886 honestly.

`src/specify_cli/cli/commands/agent/mission_setup_plan.py` performs **two** metadata reads in
`_run_documentation_wiring`, plus an audit-metadata **write** immediately after.

**Steps**:
1. Route **both** reads through the partition-aware authority. Routing only one clears the pin
   while leaving the defect — a green-gate honesty hole, and the specific failure this subtask
   is written to prevent.
2. The audit-metadata **write** must resolve through the **same authority** as the read
   (SC-007 scenario 2). A read routed to one surface and a write composed to another is the
   split this mission exists to end.
3. `gap-analysis.md` has **no artifact kind**. It anchors on the **resolved directory** and is
   recorded as an **honest bound** (WP02 T013 owns the record). **Do not invent a kind for it** —
   new `MissionArtifactKind` members are explicitly out of scope.
4. **Verify #2707 first.** It may already be fixed and stale. If it is live, it is one more read
   in this same file and belongs here — say so explicitly either way.

**Validation**: `uv run pytest tests/architectural/test_coord_read_residuals_closeout.py -q`
goes **green** — that is your red→green transition, and the reason WP01 had to remove the pin
first. Its clean scan must be green **with non-vacuity from its site floor** (not because the
scan found nothing).

### T025 — Pin the husk guarantee, or discharge the zero-case honestly (SC-005)

**Purpose**: the whole point of policing this resolver is that a PRIMARY artifact is never read
off the coord husk. That guarantee must be **pinned**, not asserted.

**Steps**:
1. Write `tests/specify_cli/missions/test_topology_routed_read_migration.py`: for each
   `migrate-fail-loud` site, drive it against a **coord mission whose worktree is a husk** and
   assert it resolves the **primary anchor** — zero husk substitutions.
2. Also assert behaviour preservation for the materialized case (NFR-001): identical directory.
3. **Zero-case discharge (SC-005, read this carefully)**: if WP02's census yielded **zero**
   `migrate-fail-loud` sites, the criterion is **not** satisfied by an empty set. Instead pin the
   husk guarantee with a **synthetic-site regression** — a test that drives the seam directly on
   a husk fixture — and cross-reference WP02's per-disposition counts and FR-017 honest bound.
   State explicitly in your handoff which branch of this you took.
4. Build fixtures under the **session scratchpad**, not a bare `/tmp` path; remove any throwaway
   worktree afterwards.

**Validation**: red-first (NFR-003) — verify by reverting the routed site.

## Branch Strategy

- Planning/base branch: **`fix/read-side-seam-primary-primitive-closure`**
- Final merge target: **`fix/read-side-seam-primary-primitive-closure`**
- Claim and prepare the workspace with the canonical entry point:
  `spec-kitty agent action implement WP04 --agent <name>`
- Worktree allocated **per computed lane** from `lanes.json` by that command.
  Never hand-construct it; never `git stash` inside a lane worktree.

## Test Strategy

```bash
PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest \
  tests/specify_cli/missions/ tests/specify_cli/cli/commands/agent/ -q
```

Plus the six C-008 gates (tasks.md §5) — the closeout gate in particular is your acceptance
signal. Plus `uv run ruff check <changed>` and project-mode
`uv run python -m mypy --strict src/specify_cli src/charter src/doctrine`.

## Definition of Done

- All 8 `resolve_feature_dir_for_mission` sites resolved per their **ledger verdict**, verified
  per site (T022).
- The 3 primary-primitive sites in your two files routed (T023).
- **Both** documentation-wiring reads routed, and the following write resolving through the
  same authority; #2707 explicitly verified live-or-stale (T024).
- `test_coord_read_residuals_closeout.py` **green**, with non-vacuity from its site floor.
- The husk guarantee pinned red-first — or the zero-case discharged explicitly with a
  synthetic-site regression and a named cross-reference (T025).
- No new raises on husk / empty / deleted-coord (NFR-002); identical directories for
  materialized missions (NFR-001).
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
- Issue matrix: **#2886 closes** with this WP. #2707 recorded either way.
- Finish: commit, `spec-kitty agent tasks mark-status T022 T023 T024 T025 --status done`, then
  `spec-kitty agent tasks move-task WP04 --to for_review` and **wait** for the synchronous pre-review gate.

## Risks

- **Routing one of the two reads is worse than routing neither** — it clears the pin while
  leaving the defect, and the gate then certifies a hole.
- **Do not invent a kind for `gap-analysis.md`.** Out of scope; it is an honest bound.
- **Do not re-derive verdicts.** If a ledger verdict looks wrong, report it — silently
  overriding it breaks WP02's reconciliation and the row-count assertion.
- A red in the closeout gate's **no-STATUS-reroute** check may be a **gate** defect (WP01's
  M7 fold-set widening) rather than an NFR-001 regression. Check whether the offending
  directory came from a **STATUS-kind** read before touching product code.

## Reviewer Guidance

1. Do **both** documentation-wiring reads route, and does the audit-metadata write resolve
   through the same authority? Read the function, do not trust the diff summary.
2. Does each routed site's kind match **what it actually reads**, or was a convenient kind
   picked to make it compile?
3. Is the husk pin **red-first**? Revert a routed site and confirm the failure. If the
   zero-case discharge was used, is the synthetic-site regression real and cross-referenced?
4. Is the closeout gate green **with** non-vacuity from its site floor — not green because the
   scan found nothing?
5. Any `stay-lenient` site: does its allow-list descriptor carry the production comment as
   rationale, per-site, with no path blanket?

## Activity Log

> **CRITICAL**: entries MUST be chronological — **append** new entries at the END, never
> prepend or insert. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`, timestamp in
> UTC (`date -u "+%Y-%m-%dT%H:%M:%SZ"`). The acceptance system reads the LAST entry as the
> current state, so out-of-order entries fail acceptance even when the work is complete.

- 2026-07-28T09:27:08Z – system – Prompt created.
