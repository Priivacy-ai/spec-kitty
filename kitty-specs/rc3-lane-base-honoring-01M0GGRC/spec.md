# Mission Spec: Lane base honoring

**Mission**: M1 — Lane base honoring (P0)
**Primary issue**: #3571 (`bug(implement): honor explicit --base when allocating a lane`, priority:P0, milestone 3.2.x, parent #1795)
**Status**: FINALIZED (specify-phase complete; re-verified live against `upstream/main` + hardened by post-spec adversarial squad 2026-08-21; ready for `/spec-kitty.plan`)
**Source of truth**: `docs/plans/investigations/friction-bugs-processing-charter-root-cause.md` §3 (#3571), §5 WP-B1, §10, decision #5
**Operator decisions**: D1, D2, D3 locked 2026-08-20 (see RESOLVED DECISIONS). Do not reopen.

---

## Problem & impact (BLUF)

An operator runs `spec-kitty implement WP01 --mission <id> --base op/elu-detached-forward`
expecting the lane worktree to descend **only** from `op/elu-detached-forward`.
The command prints `→ Using explicit base ref: op/elu-detached-forward` — a
**fabricated success line** — yet the created lane descends from an entirely
unrelated branch and does **not** contain `--base` as an ancestor. On modern
coord-topology missions (the default) `--base` is silently a no-op.

Root cause (code-verified against `upstream/main` 2026-08-21): two disjoint
allocation routes. `--base` is applied by `_resolve_active_lanes_manifest`
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
for the legacy route by #1684), not a missing capability.

---

## Respec vs pre-refactor baseline (re-verification, 2026-08-21)

The mission kick-off flagged that the coord-authority trio was refactored into
ports + pure cores (#2464 / #2465 / #2508) and that every cited symbol/line had
likely MOVED. **Re-grounded against current `upstream/main` — the citations HOLD
EXACTLY; no line-number respec was required.**

- **The #2464/#2465/#2508 refactor (`ed336e034e`) decomposed the coord-authority
  _status_ trio** (status-service / issue-matrix / runtime-bridge authority), **not
  the lane-allocation seam.** `git log` on `src/specify_cli/lanes/worktree_allocator.py`
  and the `--base` region of `src/specify_cli/cli/commands/implement.py` shows the
  allocator seam was untouched by that refactor. There is no `ports/` / pure-core
  split under `src/specify_cli/lanes/`.
- **Verified current locations (all match the pre-refactor spec):**
  - `implement.py:1391` `_resolve_active_lanes_manifest`; `:1411` the
    `→ Using explicit base ref` print; `:1412` `_dc_replace(lanes_manifest, mission_branch=base)`;
    caller at `:1884`.
  - `worktree_allocator.py:136` `allocate_lane_worktree(repo_root, mission_slug, wp_id, lanes_manifest)`;
    `:191` reuse early-return (`worktree_path.exists()`); `:235` crash-recovery
    `_branch_exists(...)` re-attach early-return; `:260-264` coord fresh-create from
    `coordination_branch`; `:272-276` legacy `else` reads `mission_branch`; `:450-453`
    stale docstring.
  - Red-first harness: `tests/specify_cli/lanes/test_worktree_allocator_coord.py`.
- **Live reproduction (NOT a static claim).** A standalone repro builds a
  coord-topology fixture whose `coordination_branch` descends from unrelated commit
  `U`, a divergent `explicit-base` branch `B` (not containing `U`), smuggles `B`
  through `mission_branch` exactly as `_resolve_active_lanes_manifest` does today,
  and calls `allocate_lane_worktree`. Result on current `upstream/main`:
  - `git merge-base --is-ancestor B <lane>` → **False** (FR-001 wants True)
  - `git merge-base --is-ancestor U <lane>` → **True** (FR-002 wants False)

  i.e. `--base` is discarded and the unrelated work `U` leaks in. **#3571 is live,
  not superseded.** Evidence script committed at
  `kitty-specs/rc3-lane-base-honoring-01M0GGRC/evidence/repro_3571_live_main.py`.

**Conclusion:** the seam, the dominant/legacy two-route split, and every fail-loud
early-return the fix targets are exactly where the operator's pre-refactor baseline
placed them. The line-number citations are unchanged; the D2 **attachment point**
moves (see below).

---

## POST-SPEC adversarial squad — findings folded in (2026-08-21)

A bounded 4-lens read-only squad (architect / debugger / reviewer / implementer,
all profile-loaded) stress-tested this spec against current `upstream/main`. Full
report: `evidence/post-spec-squad-findings.md`. The squad did NOT reopen D1/D2/D3;
it moved D2's attachment point and enlarged the true blast radius the light spec
under-captured. Folded revisions:

- **F1 → C-001**: real callers are `implement_support.py:92` + `orchestrator_api/commands.py:903`,
  plus provenance recording in `create_lane_workspace` — not just `allocate_lane_worktree`.
- **F2 → FR-006 / C-005 / Risks**: the seam is topology-blind; centralize base-routing in
  the topology-aware allocator so legacy `--base` (#1684) is not starved by smuggle-removal.
- **F3 → AC-3 / D2**: the "existing coordination_branch needs re-parenting" fail-loud site
  is a **phantom** (structurally unreachable); RETIRED and replaced by the dependency-lane trigger.
- **F4 → FR-002 (scoped to no-dep lanes) / FR-009 / FR-010 / FR-011 / C-004 / NFR-003 / Risks**:
  D1 "base alone" collides with dep-tip merge, detached planning-commit merge, and the
  `for_review` gate. Dependency lanes + `--base` ⇒ fail loud (D2/M8); detached base vs
  planning commit ⇒ fail loud (FR-010, pre-create guard); gate coupling ⇒ **in-scope M1 fix**
  (FR-011) per operator ruling — gate reads the recorded honored base (coord is the default).
- **Post-plan squad (2026-08-21)** additionally hardened: FR-010 as a PRE-CREATE atomicity guard
  (no retry-wedge); typed error subclasses `StructuredError` (machine-readable envelope); success
  print anchor + guard predicate; rewrite `tests/cli/commands/test_implement_base_flag.py` (pins the
  retired smuggle); add the missing FR-007 planning-warning test.
- **F5 → AC-1 / C-003**: red-first must drive the real `implement --base` seam, not the
  allocator in isolation.
- **F6 → AC-3 / AC-4**: real allocator state, no mocks, assert typed exception + success-line
  presence/absence in both directions.
- **F7 → NFR-004 / NFR-005 / design**: relocate the success print to post-allocation in the
  CLI layer; add the typed exception to the orchestrator except-tuple; default the new param.
- **F8 → Risks**: D3 reuse hard-errors on sequential same-lane WPs — pass `--base` only on
  lane creation.

**Plan-phase confirmation items (named per kick-off) — RESOLVED:**
1. ✅ Enumerated every `allocate_lane_worktree` / `create_lane_workspace` call site (2 prod callers +
   provenance) — authoritative grep in plan.md / research.md (C-001).
2. ✅ FR-010: base detached from the planning commit ⇒ **fail loud via a pre-create guard** (not
   `--allow-unrelated`, not a raw merge error).
3. ✅ C-004: **operator elevated to an in-scope M1 fix** (FR-011) — the `for_review` gate reads the
   recorded honored base (coord-as-base is not contradictory; coord is the default value).

---

## In scope

- Thread an explicit `base` parameter into `allocate_lane_worktree` and its two
  production callers (`create_lane_workspace`, `orchestrator_api`), so the override
  binds the field the coord-topology (dominant) path actually reads, and the recorded
  `base_branch`/`base_commit` provenance stays correct (C-001).
- Stop smuggling the override through `mission_branch`; route `base` through the
  topology-aware allocator to BOTH the coord and legacy paths (C-005).
- Make the fresh-create coord path parent a **no-dependency** lane on `base` (when
  supplied) instead of `coordination_branch` (D1).
- **Fail loud** (typed error) on any allocation route that cannot honor a supplied
  `base` — the reuse and crash-recovery early-returns (D3), a dependency-bearing lane
  (D2/FR-009), and a base detached from the planning commit (FR-010) — rather than
  printing success and silently ignoring it.
- Add a red-first test through the real `implement --base` seam, plus extend the
  allocator unit harness (`tests/specify_cli/lanes/test_worktree_allocator_coord.py`)
  with a divergent `explicit-base` branch and an ancestry assertion.
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

## User scenarios & testing

**Primary actor**: an operator (or orchestrating agent) running
`spec-kitty implement WP## --mission <handle> --base <ref>` on a coord-topology
mission — the default topology.

**Happy path (the fix).**
> **Given** a coord-topology mission whose `coordination_branch` descends from an
> unrelated commit `U`, and a divergent branch `B` that does not contain `U`,
> **When** the operator allocates a fresh lane for a WP with base `B`,
> **Then** the lane branch descends from `B` alone (`B` is an ancestor, `U` is not),
> **And** `→ Using explicit base ref: B` prints only because the lane was actually
> parented on `B`.

**Exception path (fail-loud, D2/D3).**
> **Given** the same mission and a `--base` supplied,
> **When** the active allocation route cannot honor it — the lane worktree already
> exists (reuse), the lane branch exists but its directory is gone (crash-recovery),
> the lane has dependencies whose coord-descended tips would need re-parenting onto
> `<base>` (D2/M8), or `<base>` is detached from the planning commit (FR-010) —
> **Then** the command exits non-zero with a typed error naming the route, the WP,
> and the unhonored base, **And** the `→ Using explicit base ref` line is NOT printed.

**Legacy path (unchanged, #1684).**
> **Given** a legacy mission with no `coordination_branch`,
> **When** `--base <ref>` is supplied,
> **Then** the lane parents on `<ref>` via the existing `mission_branch` route,
> byte-for-byte as before this mission.

**Invariant that must always hold**: the `→ Using explicit base ref: <ref>`
success line is emitted **only** on a path that has actually parented the lane on
`<ref>`. Every path that ignores or cannot honor the base errors instead.

---

## Functional requirements

| ID | Requirement (testable) | Priority | Status |
|----|------------------------|----------|--------|
| FR-001 | When `implement` is invoked with `--base <ref>` on a **coord-topology** mission and a fresh lane is created, the resulting lane branch MUST have `<ref>` as an ancestor (`git merge-base --is-ancestor <ref> <lane>` succeeds). | High | Accepted |
| FR-002 | Per **D1**, for a **no-dependency** lane (`depends_on_lanes` empty), `--base` fully REPLACES the parent: the lane MUST NOT have `coordination_branch` as a parent, and MUST NOT inherit ancestry reachable only through `coordination_branch` and not from `<ref>` (the unrelated-branch symptom is absent). Lanes with `depends_on_lanes` are governed by FR-009 (post-spec squad F4). | High | Accepted |
| FR-003 | `allocate_lane_worktree` MUST accept the base as an explicit parameter (not via a mutated `mission_branch` proxy field), threaded from the CLI/orchestrator seam through `create_lane_workspace` (C-001). | High | Accepted |
| FR-004 | Per **D3**, when `--base` is supplied but the active route cannot honor it — reuse of an existing lane worktree (`worktree_allocator.py:191`) or crash-recovery re-attachment of an existing lane branch (`:235`) — the command MUST **hard-error** (non-zero) with a typed error naming the route, the WP, and the unhonored base. No warn-and-continue; no success line. | High | Accepted |
| FR-005 | The `→ Using explicit base ref: <ref>` success line MUST NOT be printed on any path where the base is subsequently ignored or the command hard-errors; it prints only after the lane has actually been parented on `<ref>`. | High | Accepted |
| FR-006 | The **legacy** (no `coordination_branch`) route MUST continue to honor `--base` exactly as before (#1684 behavior preserved). The allocator, being topology-aware, routes the threaded `base` to the legacy path too; removing the `mission_branch=base` smuggle MUST NOT starve the legacy route of its base (post-spec squad F2). | High | Accepted |
| FR-007 | `--base` for repository-root / non-lane planning work MUST continue to emit the existing "ignored" warning and take no other effect. | Medium | Accepted |
| FR-008 | The docstring at `worktree_allocator.py:450-453` MUST accurately describe how `base` is threaded through the explicit parameter on both routes (no reference to the retired `mission_branch` smuggling). | Low | Accepted |
| FR-009 | Per **D2**, when `--base` is supplied for a lane with a non-empty `depends_on_lanes`, honoring the base would require re-parenting the coord-descended dependency tips onto `<ref>` (the M8 two-route reconciliation). M1 MUST **hard-error** (non-zero, typed, naming WP/route/base) rather than merge a coord-descended dep tip on top of a base-alone lane (which would re-import `coordination_branch`/unrelated ancestry and violate FR-002). This is the real, reachable attachment point of D2 (post-spec squad F3/F4). | High | Accepted |
| FR-010 | When `--base <ref>` is supplied and the recorded planning-artifact commit shares **no** common ancestor with `<ref>` (a genuinely detached base, e.g. `op/elu-detached-forward`), the command MUST **hard-error** (via a PRE-CREATE ancestry guard, leaving no residual worktree/branch) with a clear message rather than silently `--allow-unrelated-histories` or crash with a raw `PlanningCommitMergeConflictError`. (post-spec squad F4.2; post-plan atomicity) | Medium | Accepted |
| FR-011 | The `for_review` commit gate MUST resolve the lane base as the **actual honored parent** the lane was allocated on — the recorded `base_branch` provenance (`<ref>` when `--base` supplied, else the coordination branch for coord topology, else `mission_branch`). `rev-list <honored-base>..HEAD` then measures real implementation work regardless of whether the base was explicit or the coord default. A default no-`--base` coord lane MUST still be gated against `coordination_branch` (no regression). (operator ruling 2026-08-21, C-004) | Medium | Accepted |

## Non-functional requirements

| ID | Requirement (measurable) | Priority | Status |
|----|--------------------------|----------|--------|
| NFR-001 | The fix MUST NOT alter allocation behavior when `--base` is absent: every existing coord/legacy/reuse/crash-recovery test in `tests/specify_cli/lanes/` stays green (0 regressions). | High | Accepted |
| NFR-002 | Touched files MUST pass `ruff` and `mypy --strict` with zero new issues; the fail-loud error MUST be a typed exception (not a bare `RuntimeError`/`SystemExit` string). | High | Accepted |
| NFR-003 | For a **no-dependency** lane, the recorded-planning-commit merge MUST continue to compose **on top of** `--base` (not in place of it) — verified by an ancestry assertion that both `<base>` and the merged planning commit are ancestors of the lane. The verifying fixture MUST include a **detached-base** case (base with no common ancestor to the planning commit) to exercise FR-010, not only a shared-ancestor base. (Dependency-tip composition on a base-alone lane is governed by FR-009 fail-loud, not by this NFR — post-spec squad F4.) | High | Accepted |
| NFR-004 | The new fail-loud exception MUST be a typed class caught by BOTH production entry seams: the CLI wrapper (`implement.py`) and the orchestrator envelope (`orchestrator_api/commands.py:906-914`), so it never escapes as a raw traceback (post-spec squad F7). | High | Accepted |
| NFR-005 | `allocate_lane_worktree`'s new parameter MUST be `base: str \| None = None` (defaulted), so all existing call sites (~30 tests + 2 production callers) remain green without edits (NFR-001, post-spec squad F7). | Medium | Accepted |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The signature change to `allocate_lane_worktree` MUST thread `base` through **every** caller: the two production callers `lanes/implement_support.py:92` (`create_lane_workspace`) and `orchestrator_api/commands.py:903` (`_resolve_start_workspace`), PLUS the provenance-recording in `create_lane_workspace` (`base_branch`/`base_commit`/frontmatter/`WorkspaceContext`/`LaneWorkspaceResult`, implement_support.py:110-174). No caller may be left passing the base through `mission_branch` (post-spec squad F1). | Accepted |
| C-002 | The genuine two-route reconciliation (re-parenting coord-descended dependency tips onto `<base>`, and re-parenting an existing `coordination_branch`) is **out of scope**, owned by Mission M8 (#3460 / #3462 / #3536). M1 fails loud (FR-009) where M8 would reconcile. | Accepted |
| C-003 | Red-first discipline (ADR 2026-07-17-1): AC-1 MUST be RED on `upstream/main` **through the real `implement --base` entry seam** (`_resolve_active_lanes_manifest` → `create_lane_workspace` → allocator, not the allocator in isolation) before the fix and GREEN after; the swap-the-product-file-back proof is posted on the PR (post-spec squad F5). | Accepted |
| C-004 | The `for_review` gate MUST measure against the lane's **actual honored base** (FR-011), not a hardcoded coordination branch. Operator ruling (2026-08-21): coord-as-base and explicit `--base` are not contradictory — the gate reads whatever the lane was parented on (recorded `base_branch` provenance). Coord remains the default value (no regression when no `--base`). **In scope for M1** (post-spec squad F4.3 → operator-elevated). | Accepted |
| C-005 | The legacy route's parent-selection (`worktree_allocator.py:272-276`) is **behavior-preserving**, not necessarily byte-for-byte: it MUST receive its base from the threaded `base` param when supplied (`base if base is not None else mission_branch`), so #1684 keeps working after the smuggle is removed (post-spec squad F2). | Accepted |

---

## Acceptance criteria (high-level)

- **AC-1 (red-first repro, through the real seam — C-003/F5).** A test drives the
  base override **through `_resolve_active_lanes_manifest` → `create_lane_workspace`
  → allocator** (the real `implement --base` wiring), NOT the allocator in isolation:
  build a coord-topology fixture whose `coordination_branch` descends from an
  unrelated commit `U`, create a divergent `explicit-base` branch `B`, allocate a
  fresh **no-dependency** lane with the explicit base, and assert (a) `--is-ancestor
  B lane` **succeeds** and (b) `--is-ancestor U lane` **fails**. This test body is
  RED on `upstream/main` (symptom-red: wrong ancestry — not a kwarg `TypeError`) and
  GREEN after the fix. The allocator-direct unit (extending
  `test_worktree_allocator_coord.py`, as in `evidence/repro_3571_live_main.py`) is
  kept as a narrow companion, not as the C-003 proof.
- **AC-2 (legacy unbroken).** The existing
  `test_legacy_topology_skips_sparse_checkout` stays GREEN, AND a test drives legacy
  `--base` through the real seam and asserts the lane descends from the supplied ref
  (proving F2 — the smuggle removal did not starve the legacy route). The `#1684`
  cross-lane base tests stay GREEN.
- **AC-3 (hard-error on unhonorable route — D3/D2, real state, no mock — F3/F6).**
  Tests build the **real** allocator state (no mocking the allocator) and prove
  supplying `--base` produces a non-zero **typed** hard error (never warn-continue,
  never a success line) when: (a) the lane worktree already exists — allocate once,
  re-allocate with base (reuse early-return `:191`); (b) the lane branch exists but
  its directory is gone — allocate, `rm -rf` the worktree, re-allocate with base
  (crash-recovery early-return `:235`); (c) the lane has a non-empty
  `depends_on_lanes` and `--base` is supplied (FR-009 — the real, reachable D2
  trigger). *The pre-refactor spec's AC-3(c) "existing coordination_branch would need
  re-parenting" is RETIRED: post-spec squad F3 proved it structurally unreachable in
  M1 (M1 re-parents the lane, not the coord branch; a guard on it would fire on
  FR-001's own multi-lane happy path).*
- **AC-4 (never fabricate success, both directions — F6).** One assertion set proves
  the `→ Using explicit base ref: <ref>` line is PRESENT on the honored no-dependency
  fresh-create path AND ABSENT on an error path (reuse/recovery/dependency), captured
  through the real entry point (no allocator mock). The #3571 "prints success while
  discarding intent" behavior is provably gone in both directions.

**Given/When/Then anchor (AC-1):**
> **Given** a coord-topology mission whose `coordination_branch` descends from an
> unrelated commit `U`, and a divergent branch `B` that does not contain `U`,
> **When** the operator allocates a fresh lane for a WP with base `B`,
> **Then** the lane branch descends from `B` alone (`B` is an ancestor, `U` is not).

---

## Success criteria (measurable, outcome-focused)

- **SC-001** — On a coord-topology mission, `implement --base <ref>` on a
  no-dependency lane produces a lane where `git merge-base --is-ancestor <ref> <lane>`
  succeeds 100% of the time, and ancestry reachable only through the coordination
  branch is absent (the #3571 unrelated-work leak rate drops from 100% to 0%).
- **SC-005** — On a route M1 cannot honor cleanly (dependency-bearing lane, detached
  base, reuse, crash-recovery), the operator gets a non-zero exit and a typed message —
  never a divergent lineage that silently re-imports unrelated ancestry (0% silent
  mis-parenting).
- **SC-002** — When the base cannot be honored, the operator gets a non-zero exit and
  a message that names the route, the WP, and the base — never a silent success line
  (fabricated-success rate 0%).
- **SC-003** — Zero regressions: the full `tests/specify_cli/lanes/` suite stays green,
  including the legacy `--base` route (#1684).
- **SC-004** — The AC-1 regression is demonstrably red on `upstream/main` and green on
  the fix branch (proof posted on the PR).

---

## Key design decisions (the minimal fix)

- **Thread, don't smuggle.** Add an explicit `base: str | None = None` parameter to
  `allocate_lane_worktree` (defaulted — NFR-005), threaded from the CLI/orchestrator
  seam through `create_lane_workspace` (C-001); drop the `mission_branch=base` patch
  in `_resolve_active_lanes_manifest`. The **allocator is topology-aware** (it reads
  `coordination_branch` via `_read_coordination_branch`), so it routes `base` to BOTH
  the coord fresh-create path and the legacy path — the topology-blind seam does not
  have to discriminate (post-spec squad F2). Per **D1**, on a **no-dependency** lane
  the fresh-create coord path parents the lane on `base` **alone** —
  `coordination_branch` is not layered on.
- **Fail-loud sites** (typed error naming WP / route / unhonored base — never a silent
  no-op, never warn-and-continue):
  1. **Reuse** — `allocate_lane_worktree` when `worktree_path.exists()`
     (`worktree_allocator.py:191`): an existing lane cannot be re-parented (D3).
  2. **Crash-recovery** — the `_branch_exists(repo_root, branch)` re-attach branch
     (`:235`): re-attaches an existing branch, cannot re-parent (D3).
  3. **Dependency lane + base (D2, the REAL reachable trigger — F3/F4)** — a lane with
     a non-empty `depends_on_lanes` cannot be honored: its coord-descended dependency
     tips would have to be re-parented onto `<base>` (the M8 reconciliation), and
     merging them as-is would re-import `coordination_branch`/unrelated ancestry
     (violating FR-002). *(The pre-refactor "existing coordination_branch needs
     re-parenting" trigger is retired — squad F3 proved it structurally unreachable.)*
  4. **Detached base vs planning commit (FR-010)** — when `<base>` shares no common
     ancestor with the recorded planning commit, fail loud rather than
     `--allow-unrelated-histories` or a raw `PlanningCommitMergeConflictError`.
- **Move the success line** so `→ Using explicit base ref` prints only AFTER a
  successful `create_lane_workspace` return, in the CLI layer (`implement.py`,
  post-1886) — NOT inside `_resolve_active_lanes_manifest` (which runs before
  allocation) and NOT in the lanes core (the orchestrator path runs silent). It must
  cover both the coord-fresh-create-with-base and legacy-with-base honored paths.
- **Preserve the legacy route** behavior (`worktree_allocator.py:272-276`) — it now
  receives its base from the threaded param (`base if base is not None else
  mission_branch`), behavior-preserving per C-005.

---

## RESOLVED DECISIONS (operator, 2026-08-20)

**D1 — `--base` fully REPLACES the coord parent (investigation decision #5).**
On a coord-topology mission, `--base` fully replaces the lane parent: the lane
descends from `<base>` **alone**; `coordination_branch` parentage is NOT layered
on. This is what #3571's reporter expected and verified, is the minimal fix, and
is the binding contract for FR-001/FR-002. Any deeper coord-branch re-parenting
belongs to the M8 seam, not M1.

**D2 — A route that cannot honor `<base>` without re-parenting ⇒ FAIL LOUD.**
When `--base` is supplied and honoring it would require re-parenting work that
belongs to the M8 two-route reconciliation, the command MUST fail loud (error;
non-zero) rather than mint a divergent lineage or fabricate success. The genuine
two-route reconciliation is Mission M8 (#3460 / #3462 / #3536).

> **Squad refinement (post-spec F3/F4 — attachment point, not a reopening).** The
> operator's D2 intent stands. The pre-refactor spec attached D2 to "an existing
> `coordination_branch` that would need re-parenting"; the squad empirically proved
> that trigger **structurally unreachable** in M1 (M1 re-parents the *lane*, not the
> coord branch — and a pre-existing coord branch is the normal multi-lane case, so a
> guard on it would fire on FR-001's happy path). The **real, reachable** D2 trigger
> is a lane with a non-empty `depends_on_lanes` + `--base`: re-parenting its
> coord-descended dependency tips onto `<base>` is exactly the M8 reconciliation.
> D2 now binds **FR-009** (and FR-010 for the detached-planning-commit sibling case).

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
  touches two production callers (`create_lane_workspace`, `orchestrator_api`) plus
  the provenance-recording inside `create_lane_workspace` — see C-001 (F1).
- **Legacy-route base starvation (F2, HIGH).** The `_resolve_active_lanes_manifest`
  seam is topology-blind; the legacy `else` (272-276) reads only `mission_branch`,
  whose sole source is the smuggle. A naïve global smuggle-removal silently breaks
  legacy `--base` (#1684) — the exact regression class this P0 kills. Mitigated by
  centralizing base-routing in the topology-aware allocator (C-005) and pinned by AC-2.
- **Dependency-lane ancestry re-import (F4.1, HIGH).** `_merge_dependency_lane_tips`
  merges a coord-descended dep tip; on a base-alone lane that re-imports
  `coordination_branch`/unrelated ancestry, violating FR-002. Resolved by FR-009
  fail-loud (dep-lane + base is the M8 seam), NOT by silently composing.
- **Detached-base planning-commit merge (F4.2, MEDIUM).** `_merge_recorded_planning_commit`
  on a base with no common ancestor to the planning commit can raise "refusing to
  merge unrelated histories". Resolved by FR-010 fail-loud; verified by a detached-base
  NFR-003 fixture. **Plan-phase confirmation item.**
- **`for_review` gate coord-as-base coupling (F4.3, MEDIUM → FIXED IN M1).** `resolve_lane_base_ref`
  treated the coord branch as the lane base for `rev-list <base>..HEAD`; a base-alone lane
  was measured against the wrong ref and could spuriously pass. **Operator elevated this to an
  in-scope M1 fix (FR-011, C-004):** the gate now reads the recorded honored base uniformly
  (coord is the default value). No-regression pinned for the default no-`--base` coord lane.
- **D3 reuse on sequential same-lane WPs (F8, LOW).** Harnesses that pass `--base` on
  every WP invocation will now hard-error on WP2+ (reuse). Document: pass `--base`
  only on lane creation.
- **Orchestrator envelope leak (F7).** The new typed exception must join the
  `orchestrator_api/commands.py:906-914` except-tuple or it escapes as a raw traceback
  (NFR-004).
- **Fabricated-success removal.** Moving the success print must not suppress it on the
  paths where it is legitimately true (both coord-with-base and legacy-with-base).

---

## Issues

- **In scope**: #3571 (P0 — this mission).
- **Adjacent / recurrence-prevention epic (reference, do not solve)**: #3460,
  #3462, #3536 (coord two-route seam → Mission M8).
- **Fold candidates NOT taken here** (same override-field/read-field pattern):
  #3122, #3029 (investigation §11).
- **Parent**: #1795. **Prior art**: #1684 (wired `--base` for the legacy route).
