# Mission Spec (LIGHT — not finalized): Lane base honoring

**Mission**: M1 — Lane base honoring (P0)
**Primary issue**: #3571 (`bug(implement): honor explicit --base when allocating a lane`, priority:P0, milestone 3.2.x, parent #1795)
**Status**: Draft (specify-phase only; NOT planned, NOT finalized)
**Source of truth**: `docs/plans/investigations/friction-bugs-processing-charter-root-cause.md` §3 (#3571), §5 WP-B1, §10, decision #5

---

## Problem & impact (BLUF)

An operator runs `spec-kitty implement WP01 --mission <id> --base op/elu-detached-forward`
expecting the lane worktree to descend **only** from `op/elu-detached-forward`.
The command prints `→ Using explicit base ref: op/elu-detached-forward` — a
**fabricated success line** — yet the created lane descends from an entirely
unrelated branch and does **not** contain `--base` as an ancestor. On modern
coord-topology missions (the default) `--base` is silently a no-op.

Root cause (code-verified against `main`): two disjoint allocation routes.
`--base` is applied by `_resolve_active_lanes_manifest`
(`cli/commands/implement.py:1391`), which patches **only**
`lanes_manifest.mission_branch` (`:1412`) and prints the success line (`:1411`).
But `allocate_lane_worktree` (`lanes/worktree_allocator.py:136`) branches
coord-topology missions from `coordination_branch` (`:260-264`) and reads
`mission_branch` **only** in the legacy `else` (`:272-276`). The operator's
override binds a field the dominant path never reads.

**Impact**: unrelated pending work is silently pulled into a supposedly
independent lane, invalidating review scope and risking accidental merge of
blocked evidence. Severity P0 because the failure is silent *and* actively
misreports success. This is a **regression / topology gap** (`--base` was wired
for the legacy route by #1684), not a missing feature.

---

## In scope

- Thread an explicit `base` parameter into `allocate_lane_worktree` so the
  override binds the field the coord-topology (dominant) path actually reads.
- Stop smuggling the override through `mission_branch` for the coord path.
- Make the fresh-create coord path parent the lane on `base` (when supplied)
  instead of `coordination_branch`.
- **Fail loud** on any allocation route that cannot honor a supplied `base`
  (notably the reuse and crash-recovery early-returns) rather than printing
  success and silently ignoring it.
- Extend the existing red-first repro harness
  (`tests/specify_cli/lanes/test_worktree_allocator_coord.py`) with a divergent
  `explicit-base` branch and an ancestry assertion.
- Correct the stale docstring at `worktree_allocator.py:450-453` (it claims
  `--base` selects the root via `mission_branch`).

## Out of scope (+ where deferred)

- The **coord two-route architectural seam** — the recurrence-prevention refactor
  that would unify the two allocation routes so this class of drift cannot recur.
  Deferred to **Mission M8 / epic #3460 / #3462 / #3536** (cite, do not solve).
- The other override-written-to-one-field-read-from-another twins **#3122 / #3029**
  (fold candidates flagged in investigation §11; not this mission).
- Any change to `--base` semantics for repository-root / non-lane planning work
  beyond keeping the existing "ignored, with a warning" behavior.
- Data model / contract detail (deferred to the later plan phase).

---

## Functional requirements

| ID | Requirement (testable) | Priority |
|----|------------------------|----------|
| FR-001 | When `implement` is invoked with `--base <ref>` on a **coord-topology** mission and a fresh lane is created, the resulting lane branch MUST have `<ref>` as an ancestor (`git merge-base --is-ancestor <ref> <lane>` succeeds). | High |
| FR-002 | Per **D1**, `--base` fully REPLACES the parent: the lane MUST NOT have `coordination_branch` as a parent, and MUST NOT inherit ancestry reachable only through `coordination_branch` and not from `<ref>` (the unrelated-branch symptom is absent). | High |
| FR-003 | `allocate_lane_worktree` MUST accept the base as an explicit parameter (not via a mutated `mission_branch` proxy field). | High |
| FR-004 | Per **D2/D3**, when `--base` is supplied but the active route cannot honor it — an already-existing `coordination_branch` that would need re-parenting (D2), reuse of an existing lane worktree, or crash-recovery re-attachment of an existing lane branch (D3) — the command MUST **hard-error** (non-zero) with a message naming the route, the WP, and the unhonored base. No warn-and-continue; no success line. | High |
| FR-005 | The `→ Using explicit base ref: <ref>` success line MUST NOT be printed on any path where the base is subsequently ignored. | High |
| FR-006 | The **legacy** (no `coordination_branch`) route MUST continue to honor `--base` exactly as before (#1684 behavior preserved). | High |
| FR-007 | `--base` for repository-root / non-lane planning work MUST continue to emit the existing "ignored" warning and take no other effect. | Medium |
| FR-008 | The docstring at `worktree_allocator.py:450-453` MUST accurately describe how `base` is threaded (no reference to the retired `mission_branch` smuggling for the coord path). | Low |

---

## Acceptance criteria (high-level)

- **AC-1 (red-first repro, coord path).** Extending
  `test_worktree_allocator_coord.py`: build a coord-topology fixture whose
  `coordination_branch` descends from an unrelated commit, create a separate
  `explicit-base` branch that diverges, allocate a fresh lane with the explicit
  base, and assert (a) `--is-ancestor explicit-base lane` **succeeds** and
  (b) `--is-ancestor <coord-only-ancestor> lane` **fails**. This test is RED on
  `main` and GREEN after the fix. (Mirrors #3571's own `git merge-base
  --is-ancestor` evidence method.)
- **AC-2 (legacy unbroken).** The existing
  `test_legacy_topology_skips_sparse_checkout` and the legacy `--base` behavior
  stay GREEN — the legacy `mission_branch` route is unchanged.
- **AC-3 (hard-error on unhonorable route — D2/D3).** Tests prove that supplying
  `--base` produces a non-zero hard error (never a warning-then-continue, never a
  success line) when: (a) the lane worktree already exists (reuse early-return),
  (b) the lane branch exists but its directory is gone (crash-recovery
  early-return), and (c) an existing `coordination_branch` would need re-parenting.
- **AC-4 (never fabricate success).** A test/assertion proves the
  `→ Using explicit base ref: <ref>` line is emitted **only** on a path that has
  actually parented the lane on `<ref>`. On every path where the base is ignored
  or cannot be honored, the command errors instead of printing that line — the
  #3571 "prints success while discarding intent" behavior is provably gone.

**Given/When/Then anchor (AC-1):**
> **Given** a coord-topology mission whose `coordination_branch` descends from an
> unrelated commit `U`, and a divergent branch `B` that does not contain `U`,
> **When** the operator allocates a fresh lane for a WP with base `B`,
> **Then** the lane branch descends from `B` alone (`B` is an ancestor, `U` is not).

---

## Key design decisions (the minimal fix)

- **Thread, don't smuggle.** Add an explicit `base: str | None` parameter to
  `allocate_lane_worktree`; drop the `mission_branch=base` patch in
  `_resolve_active_lanes_manifest` for the coord path. Per **D1**, when `base` is
  present the fresh-create coord path parents the lane on `base` **alone** —
  `coordination_branch` is not layered on as a parent.
- **Fail-loud sites** (the early-returns that cannot re-parent an existing base):
  1. **Reuse** — `allocate_lane_worktree` when `worktree_path.exists()`
     (`worktree_allocator.py:~189-210`): an existing lane cannot be re-parented.
  2. **Crash-recovery** — the `_branch_exists(repo_root, branch)` re-attach branch
     (`:~235-258`): re-attaches an existing branch, cannot re-parent.
  3. **Existing coordination branch (D2)** — when honoring `<base>` would require
     re-parenting an already-existing `coordination_branch` (the real two-route
     reconciliation, owned by M8).
  When `base` is supplied and any of these paths is taken, raise a typed error
  naming the WP, the route, and the unhonored base — never a silent no-op, never
  a warn-and-continue.
- **Move the success line** so `→ Using explicit base ref` prints only after the
  base has actually been bound as the lane parent (or is emitted by the allocator
  itself), never speculatively in the manifest-patch step.
- **Preserve the legacy route** untouched (`worktree_allocator.py:272-276`).

---

## RESOLVED DECISIONS (operator, 2026-08-20)

**D1 — `--base` fully REPLACES the coord parent (investigation decision #5).**
On a coord-topology mission, `--base` fully replaces the lane parent: the lane
descends from `<base>` **alone**; `coordination_branch` parentage is NOT layered
on. This is what #3571's reporter expected and verified, is the minimal fix, and
is the binding contract for FR-001/FR-002. Any deeper coord-branch re-parenting
belongs to the M8 seam, not M1.

**D2 — Existing coordination branch that cannot be re-parented ⇒ FAIL LOUD.**
When `--base` is supplied and the `coordination_branch` already exists such that
honoring `<base>` would require re-parenting it, the command MUST fail loud
(error; non-zero) rather than mint a divergent lineage or fabricate success. The
genuine two-route reconciliation is Mission M8 (#3460 / #3462 / #3536). Binds
FR-004.

**D3 — Reuse / crash-recovery paths where `--base` can't apply ⇒ HARD ERROR.**
When `--base` is supplied but the lane worktree already exists (reuse) or the
lane branch already exists but its directory is gone (crash-recovery), the base
cannot be applied to an already-created lane. The command MUST hard-error — no
warn-and-continue. A scroll-past warning reproduces the exact "silently proceeded
while ignoring operator intent" harm this P0 exists to kill. Any
re-enter-with-base escape hatch is a follow-up, not M1. Binds FR-004.

---

## Risks / blast-radius

- **Legacy route must keep working.** The `else`-branch `mission_branch` route
  (`worktree_allocator.py:272-276`) is the one place `--base` already works
  (#1684). Threading an explicit param must not change its behavior — pinned by
  AC-2 and FR-006.
- **Signature change fan-out.** Adding a parameter to `allocate_lane_worktree`
  touches every caller; the plan phase must enumerate call sites (dispatch is
  through `implement.py`'s `_resolve_active_lanes_manifest` seam today).
- **Dependency-lane merge composition.** The fresh coord path also merges the
  recorded planning commit (`_merge_recorded_planning_commit`) and approved
  dependency-lane tips (`_merge_dependency_lane_tips`) on top of the base. These
  must continue to compose on top of `--base` (investigation §10 notes the
  dep-tip merge composes cleanly).
- **Fabricated-success removal.** Moving/removing the success print must not
  suppress it on the paths where it is legitimately true.

---

## Issues

- **In scope**: #3571 (P0 — this mission).
- **Adjacent / recurrence-prevention epic (reference, do not solve)**: #3460,
  #3462, #3536 (coord two-route seam → Mission M8).
- **Fold candidates NOT taken here** (same override-field/read-field pattern):
  #3122, #3029 (investigation §11).
- **Parent**: #1795. **Prior art**: #1684 (wired `--base` for the legacy route).
