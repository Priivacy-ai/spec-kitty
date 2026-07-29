---
work_package_id: WP07
title: Route the runtime bridge and status aggregate; record the foundation sites
dependencies:
- WP02
- WP03
requirement_refs:
- FR-001
- FR-004
- FR-005
- FR-015
- FR-024
- NFR-001
- NFR-009
planning_base_branch: fix/read-side-seam-primary-primitive-closure
merge_target_branch: fix/read-side-seam-primary-primitive-closure
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-seam-primary-primitive-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-seam-primary-primitive-closure unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
- T034
phase: Phase 3 - Route
history:
- at: '2026-07-28T09:27:08Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/aggregate.py
create_intent:
- tests/specify_cli/status/test_aggregate_read_seam_migration.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/runtime/next/runtime_bridge.py
- src/runtime/next/runtime_bridge_identity.py
- src/specify_cli/status/aggregate.py
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/core/paths.py
- src/specify_cli/core/git_ops.py
- src/specify_cli/coordination/surface_resolver.py
- tests/specify_cli/status/test_aggregate_read_seam_migration.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – Route the runtime bridge and status aggregate

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

The hardest routing cluster in the mission. Three distinct jobs:

1. Route the **runtime-bridge** cluster (3 sites) and correct its 2 husk comments.
2. Route **`status/aggregate.py`** (4 sites) — which carries the mission's **one non-compliant
   site**, the **`.name`-derived divergence shape**, and the **four-site qualname** that is
   WP02's index acceptance fixture.
3. Record the **four foundation sites by name, unrouted** — because routing them risks a
   resolution cycle.

## Context & Constraints

Follow **the shared migration procedure** in [tasks.md](../tasks.md) — read it before starting.

**Site distribution** (census on this base — re-derive before starting):

| File | Sites | Disposition |
|---|---|---|
| `runtime/next/runtime_bridge.py` | 2 | route; **+ 1 husk comment** |
| `runtime/next/runtime_bridge_identity.py` | 1 | route; **+ 1 husk comment** |
| `status/aggregate.py` | 4 | route — the hard ones (see T033) |
| `coordination/commit_router.py` | 1 | route |
| `core/paths.py` | 2 | **FOUNDATION — record, do NOT route** |
| `core/git_ops.py` | 1 | **FOUNDATION — record, do NOT route** |
| `coordination/surface_resolver.py` | 1 | **FOUNDATION — record, do NOT route** |

- **NFR-009 — no resolution cycle.** This is the constraint that makes T034 a *recording* task
  rather than a routing task. `core/paths.py:727` is consumed by the **write-side composition
  root** (`resolve_placement_only`); the others are peer branch/surface resolvers. They sit
  *beneath* the seam. Authority tidiness is **not** worth a resolution cycle.
- **NFR-001 / NFR-002** — identical directory for a materialized, non-backfilled mission; no new
  raises where leniency is the contract.
- **C-003** — the foundation sites become **per-site** allow-list descriptors with individual
  rationale. `core/paths.py` and `core/git_ops.py` are **not** currently sanctioned modules, so
  they need explicit entries. No path-scoped blankets.
- **Do not edit files under `tests/architectural/`** — WP01 and WP02 own those.

## Doctrine for this WP

- **`tactic:refactoring-strangler-fig`** — reroute cadence only: one caller at a time, **verify
  after each**. Its "delete the legacy path last" step is WP08's, not yours.
  `Run: spec-kitty charter context --include tactic:refactoring-strangler-fig`
  **When doing T033**, `_find_meta_path` holds four censused sites in one function — verify after
  each, or you will not be able to say which one moved a directory.
- **`DIRECTIVE_041`** — classify every red **STALE / PATCHWORK / VALID**; never retry-to-green.
  Check WP01's `research/expected-reds.md` first.
  `Run: spec-kitty charter context --include directive:DIRECTIVE_041`
  **When a red appears in the closeout gate's no-STATUS-reroute check**, see the trap below —
  it may be a *gate* defect, not your regression.
- **`tactic:architectural-gate-non-vacuity`** — the recording in T034 must be **asserted**, never
  silently skipped: a named site with a rationale, provable by census.
  `Run: spec-kitty charter context --include tactic:architectural-gate-non-vacuity`
  **When doing T034**, "we left them alone" is not a record. A reviewer must be able to run a
  census and see the four names with their reasons.
- **`tactic:change-apply-smallest-viable-diff`** — `status/aggregate.py` is large; route the reads
  and stop. `Run: spec-kitty charter context --include tactic:change-apply-smallest-viable-diff`

## ⚠ Two traps specific to this WP

**Trap 1 — the false NFR-001 regression.** A red in the closeout gate's **no-STATUS-reroute**
check may be a **gate** defect (WP01's M7 kind-discriminated fold-set widening not covering your
call shape) rather than a directory regression. **Check whether the offending directory came
from a STATUS-kind read before touching any product code.** If it did, the STATUS leg is
*correct* and the gate is wrong — report it as a WP01 gap. "Fixing" a correct STATUS leg to
green a gate is the mission's named worst-case failure.

**Trap 2 — the `.name` escape hatch.** `status/aggregate.py:543` derives its handle via `.name`,
whose value is the **composed** `<slug>-<mid8>` form on a backfilled mission. Today that is
latent behind a short-circuit. WP03 recorded the shape; you discharge it. The routed site must
not silently return a **non-existent path** (US3 scenario 3).

## Subtasks

### T032 — Route the runtime-bridge cluster and correct its 2 husk comments (FR-004, FR-015)

**Steps**:
1. Route the 2 sites in `runtime_bridge.py` and the 1 in `runtime_bridge_identity.py` per ledger
   verdict, verifying after each.
2. Correct the husk comment in each file, **in the same commit as the call site it annotates**.
   The correction: the **kind-blind** resolver genuinely can select the husk; the **kind-aware
   seam** cannot, because for a PRIMARY-partition kind the decision layer short-circuits to
   PRIMARY *before any coord probe*. Preserve the true warning; remove the false implication.
3. Note the shared-package boundary: `src/runtime/next/` is the canonical runtime.
   `src/specify_cli/next/` is a deprecation shim — do not anchor anything new there.

### T033 — Route `status/aggregate.py` (4 sites), including the non-compliant `:522` (FR-001, FR-004)

This module is the mission's hardest single file. Three special properties:

**(a) `:522` is the one NON-compliant site in the tree.** It passes a handle from a canonicalizer
the fold-prescription gate's fold set does **not** recognise — so it is neither routed nor
allow-listed and passes **only because nothing looks for it** (green-by-omission). WP01 taught
the gate that canonicalizer / the seam idiom; your job is the site side: route it so it is
**affirmatively** checked (FR-001, SC-004). After your change it must no longer pass unexamined.

**(b) `:543` is the `.name` divergence shape** — see Trap 2 above. Route it so a backfilled
mission cannot yield a non-existent path, and **pin that** by test.

**(c) `_find_meta_path` carries FOUR censused sites in one qualname.** It is the acceptance
fixture for WP02's per-site index discriminator (SC-015). **Coordinate the spelling with the
ledger** — do not invent a second addressing convention. If the ledger's discriminator cannot
express your four sites, that is a WP02 gap: report it rather than working around it.

**Steps**: route each of the 4 sites per verdict, verifying after each; keep the diff local to
the reads.

**Validation**: the fold-prescription gate covers `:522` affirmatively (plant a bad read nearby
→ still flagged); a backfilled-mission fixture on `:543` resolves an existing directory.

### T034 — Route `commit_router.py`; record the four foundation sites, unrouted (FR-005, NFR-009)

**Steps**:
1. Route `coordination/commit_router.py` (1 site) per verdict.
2. **Re-point, then record — but do NOT route through the seam.**

   ⚠ **Expect a forced out-of-map edit, and write the rationale.** WP03 hit this first and it is
   structural, not overreach: `tests/architectural/resolution_gate_allowlist.yaml` pins the literal
   **token text** of sanctioned call sites (e.g. `token: primary_dir = primary_feature_dir_for_mission ( repo_root , handle )`).
   Re-pointing a sanctioned site at the leaf **changes that token**, so the YAML entry must change
   with it or the anchoring gate reds on a site you correctly fixed. Update the entry, keep the
   semantic sanction intact (same raw-probe intent, new literal callee name), and record a one-line
   rationale naming this WP and the reason — exactly as WP03's commit `77226250f` did. This is
   sanctioned leeway under tasks.md §6, not a violation; `owned_files` simply could not express the
   coupling. Do **not** silently widen or delete a sanction to make a red go away.
 These four import the
   **public** `primary_feature_dir_for_mission`, which WP08 **deletes**. Leaving them "unchanged"
   would `ImportError` at import of `core/paths.py`, `core/git_ops.py` and
   `coordination/surface_resolver.py` — the CLI would not start. So:
   **(a)** re-point each of the four at the **module-private leaf** WP03 extracted (a sanctioned
   cross-module import; SC-001 explicitly anticipates "in-module **and named-sanctioned**
   callers"), and **(b)** record each by name with its recursion rationale. They keep resolving
   exactly as they do today — this is an import-target change, not a routing change. Do **not**
   route them through `read_dir` (that is the resolution cycle NFR-009 forbids). The four:
   - `core/paths.py` (**2 sites**) — one is consumed by the write-side composition root
     `resolve_placement_only`; routing it risks a cycle.
   - `core/git_ops.py` (1 site) — peer branch resolver, beneath the seam.
   - `coordination/surface_resolver.py` (1 site) — peer surface resolver; the sanctioned
     single-authority site.
3. **Confirm — do not author.** Each of the four needs a **per-site allow-list descriptor with
   individual rationale** (C-003), and `core/paths.py` / `core/git_ops.py` are **not** currently
   sanctioned modules, so an assumed blanket will not cover them. Those descriptors live in
   `tests/architectural/test_no_read_side_bypass.py`, which is **WP02's exclusively owned file**
   and which you are forbidden to edit. So: verify WP02's descriptors exist for all four and
   match your census, and **report any gap as a WP02 gap** rather than editing that module.
4. **Prove they remain unrouted and cycle-free**: run the census recipe in
   [quickstart.md](../quickstart.md) §1 and confirm the four sites are present and unchanged, and
   that no cycle exists in the `read_dir` call graph (SC-014, NFR-009).

**Validation**: a census shows exactly four foundation sites, each named with a reason; no cycle.

## Branch Strategy

- Planning/base branch: **`fix/read-side-seam-primary-primitive-closure`**
- Final merge target: **`fix/read-side-seam-primary-primitive-closure`**
- Claim and prepare the workspace with the canonical entry point:
  `spec-kitty agent action implement WP07 --agent <name>`
- Worktree allocated **per computed lane** from `lanes.json` by that command.
  Never hand-construct it; never `git stash` inside a lane worktree.

## Test Strategy

Write `tests/specify_cli/status/test_aggregate_read_seam_migration.py` covering: identical
directory for a materialized mission per routed site (NFR-001); the `:543` backfilled-mission
case resolving an **existing** directory; no new raise on husk / empty / deleted-coord. Red-first
(NFR-003) — verify by reverting the routed site.

```bash
PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest \
  tests/specify_cli/status/ tests/specify_cli/coordination/ -q
```

Plus the six C-008 gates (tasks.md §5), `uv run ruff check <changed>`, and project-mode
`uv run python -m mypy --strict src/specify_cli src/charter src/doctrine`.

## Definition of Done

- Runtime-bridge cluster routed (3 sites); both husk comments corrected in the same commits as
  their call sites (T032).
- All 4 `status/aggregate.py` sites routed. `:522` no longer passes by omission — verified with a
  planted bad read (T033, SC-004).
- `:543`'s backfilled-mission case pinned: it resolves an **existing** directory (T033, US3.3).
- `_find_meta_path`'s four sites expressed in the **ledger's** discriminator spelling, not a
  local invention (T033, SC-015).
- `commit_router.py` routed; the **four** foundation sites recorded by name with per-site
  rationale and **still unrouted**, proven by census; no cycle (T034, SC-014, NFR-009).
- Behaviour preservation pinned red-first; no new raises.
- **SC-009 aggregate (this WP is the last comment-touching WP, so it owns the count)**: all **eight**
  misleading comments are corrected across the mission — 2 in `acceptance/__init__.py` + 3 in
  `workflow_executor.py` (WP05), 1 in `next_cmd.py` (WP06), 2 in the runtime bridge (this WP).
  Verify all eight, not just your two; report any WP05/WP06 gap rather than fixing it silently.
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
- Finish: commit, `spec-kitty agent tasks mark-status T032 T033 T034 --status done`, then `spec-kitty agent tasks move-task WP07 --to
  for_review` and **wait** for the synchronous pre-review gate.

## Risks

- **Trap 1 is the mission's worst-case failure**: a STATUS-kind red that looks like an NFR-001
  regression and invites you to "fix" a correct leg. Check the offending directory's origin
  first, every time.
- **Routing a foundation site is a resolution cycle** (NFR-009). `core/paths.py:727` feeds the
  write-side composition root. Record; do not route. If routing one looks tempting, that is the
  signal to stop.
- **The `.name` divergence is latent today** — it will not show up unless you build a backfilled
  fixture. Build one.
- `src/specify_cli/next/` is a **deprecation shim**; the canonical runtime is
  `src/runtime/next/_internal_runtime/`. Do not anchor new code in the shim.

## Reviewer Guidance

1. `:522` — plant a non-compliant read nearby yourself and confirm the fold-prescription gate
   flags it. "It routes now" is not the same as "it is checked now".
2. `:543` — is there a **backfilled-mission** fixture, and does it assert the resolved directory
   **exists**? A test that only checks the materialized case misses the entire point.
3. Does `_find_meta_path` use the **ledger's** discriminator spelling? Cross-check against WP02.
4. The four foundation sites: are they named **with reasons**, present in a census, and
   **unrouted**? Is `core/paths.py`/`core/git_ops.py` covered by an explicit per-site entry
   rather than an assumed blanket?
5. Any closeout-gate red: did the implementer verify the offending directory's **kind origin**
   before changing product code?

## Activity Log

> **CRITICAL**: entries MUST be chronological — **append** new entries at the END, never
> prepend or insert. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`, timestamp in
> UTC (`date -u "+%Y-%m-%dT%H:%M:%SZ"`). The acceptance system reads the LAST entry as the
> current state, so out-of-order entries fail acceptance even when the work is complete.

- 2026-07-28T09:27:08Z – system – Prompt created.
