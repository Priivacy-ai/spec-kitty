# Mission Specification: Next Resolves State From Committed Authority

**Mission Branch**: `fix/next-committed-state-authority`
**Created**: 2026-08-31
**Status**: Draft
**Milestone**: 3.2.6
**Input**: GitHub issues #2947 (P1) and #3780 (P2), parent epics #1619 / #2945-family. Folded into one mission because both are the same defect class: the mission loop decides *what to do next* from the wrong state authority — a stale coordination worktree checkout or a lane value read in isolation — instead of the committed mission status and the operator-provenance record.

## Intent Summary

**Primary actor**: the developer/operator driving a mission with `spec-kitty next` and inspecting it with `spec-kitty agent tasks status`.

**Problem**: The loop can read state from an authority that does not reflect the truth of the mission.
- When a mission has already merged but a coordination worktree checkout was left behind at an old commit, `next` ignores the committed status (which records every work package accepted) and treats the mission as unstarted — it fabricates a fresh discovery/research step and a new runtime run pointed at the stale checkout where the mission's artifacts are missing. `agent tasks status` rolls the mission up as all-`planned`.
- When an operator deliberately cancels a work package (an honest ending, carrying operator provenance), the loop's review-step advancement predicate treats the canceled package as "not handed off" and stalls, refusing to move the mission forward. A merely automated/synthetic cancellation should not advance it.

**Desired outcome**: The loop resolves mission and work-package state from the **committed status authority** and the **operator-provenance record** before it trusts any on-disk workspace. A finished (merged) mission is recognized as finished; an operator-canceled package lets the loop advance; a synthetic cancellation does not; and a workspace that is missing the mission's artifacts produces a structured blocked result rather than a fabricated "unstarted" run.

**Two load-bearing decisions**:
1. **Single state authority for `next`** — resolve mission/WP state from the committed status record + merge evidence *before* trusting or selecting a coordination workspace. A workspace missing the mission's artifacts fails closed.
2. **Provenance-gated advancement** — a canceled work package advances the loop *only* with operator provenance, mirroring the shipped acceptable-ending authority; a synthetic cancellation stays blocking (fail-closed).

**Assumptions** (recorded, not asked — the operator brief is authoritative):
- The acceptable-ending / operator-provenance authority shipped for accept, merge, dependency, and claim (issue #3774) is correct; this mission *routes the loop through it*, it does not reimplement or alter it.
- The lane state machine and transition matrix are correct and out of scope.
- "Committed status authority" = the reduced work-package state derived from the committed status record on the authoritative committed surface — the single source of truth for each package's lane and provenance — as distinct from a materialized-but-stale coordination worktree checkout.
- "Merge evidence" = the committed `mission_number` (assigned at merge; absent/`null` pre-merge), read together with the reduced committed status. Transient merge-progress signals (in-progress merge-state, an active git MERGE_HEAD) are *not* merge evidence — they are absent precisely when a mission is finished.

## Decision Outcomes (the `next` verdict, made observable)

The `next` query verdict on a mission, decided from committed authority **before** trusting any coordination checkout:

| Committed authority state | `next` verdict |
|---|---|
| `mission_number` assigned **and** every WP in an accepted terminal lane (approved / done / canceled-with-operator-provenance) | `kind: terminal` (already-closed); no runtime run created |
| `mission_number` assigned **but** committed status **not** all-accepted (merge evidence disagrees with per-WP status) | `kind: blocked`, structured conflict reason; never terminal, never a restart |
| `mission_number` absent (unmerged) **and** committed status present | proceed from the **committed** WP state (accept when all-accepted; otherwise the committed actionable step) — never fabricate an unstarted step from a stale checkout |
| Actionable work needs a coordination workspace, but the selected checkout is missing the mission's artifacts | `kind: blocked`, structured artifact-missing reason; never a fabricated unstarted/discovery step |
| No committed status authority at all (mission genuinely never started) | unchanged from today (fail loud on a genuinely-absent status log; not spuriously terminal) |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A merged mission is recognized as finished, not restarted (Priority: P1)

An operator returns to a mission whose work is complete and merged (its `mission_number` is assigned and its committed status shows every work package accepted). A coordination worktree checkout from earlier in the mission is still on disk at an old commit. The operator runs `spec-kitty next` and `spec-kitty agent tasks status`. The loop recognizes from committed authority that the mission is finished — `next` returns `kind: terminal` and creates no runtime run, and the status board shows the committed accepted lanes, not an all-`planned` rollup from the stale checkout.

**Why this priority**: This is a state-integrity defect (issue label P1). Restarting a merged mission fabricates a runtime run pointed at a stale workspace with missing artifacts and misreports finished work as unstarted — actively corrupting the operator's picture of the work.

**Independent Test**: Stand up a mission whose committed `meta.json` has `mission_number` assigned and whose committed status shows every WP accepted, with a stale coordination checkout present at an old commit. Assert `next` returns `kind: terminal` and creates no new run; assert `agent tasks status` reports each WP's committed accepted lane, not `planned`.

**Acceptance Scenarios**:

1. **Given** a mission with `mission_number` assigned and committed status all-accepted, and a stale coordination worktree checkout on disk, **When** the operator runs `next`, **Then** the result is `kind: terminal` and no runtime run is created.
2. **Given** the same merged mission, **When** the operator runs `agent tasks status`, **Then** the board reports each work package in its committed accepted lane (approved/done/canceled), not `planned`.
3. **Given** a mission whose `mission_number` is assigned but whose committed status is **not** all-accepted (evidence disagrees with per-WP status), **When** the operator runs `next`, **Then** the result is `kind: blocked` with a structured conflict reason — not `terminal`, not a restart.
4. **Given** an unmerged mission (`mission_number` absent) whose committed status shows real in-flight WP state, with a stale coordination checkout present, **When** the operator runs `next`, **Then** the loop proceeds from the committed WP state and never fabricates an unstarted/discovery step from the stale checkout.
5. **Given** an unmerged mission whose actionable step needs a coordination workspace but the selected checkout is missing the mission's artifacts, **When** the operator runs `next`, **Then** the result is `kind: blocked` with a structured artifact-missing reason.
6. **Given** a mission that genuinely never started (no committed status authority), **When** the operator runs `next`, **Then** behavior is unchanged from today — the mission is not spuriously reported terminal, and a genuinely-absent status log still fails loud.

---

### User Story 2 - An operator-canceled work package does not stall the loop (Priority: P2)

An operator deliberately cancels a work package that will not be completed, recording a real reason (operator provenance). Later the operator runs `spec-kitty next` to advance the mission. The loop treats the operator-canceled package as an acceptable ending and advances past the review step (and the implement step), instead of stalling as though the package were still awaiting hand-off. A package canceled by an automated/synthetic path — carrying no operator provenance — still blocks advancement, so nothing silently slips past review.

**Why this priority**: An operator-canceled package that stalls the loop blocks mission progress on an honest ending (issue label P2); unlike US1 it does not corrupt state and can be worked around by force. Both stories are in-scope for this mission; neither is deferred.

**Independent Test**: Stand up a mission with a work package canceled *with* operator provenance at the review step and assert `next` advances (does not stall); repeat at the implement step; repeat with a *synthetic* cancellation and assert `next` still blocks at both.

**Acceptance Scenarios**:

1. **Given** a work package canceled with operator provenance at the review step, **When** the operator runs `next`, **Then** the loop advances past review rather than treating the package as blocking.
2. **Given** a work package canceled with operator provenance at the implement step, **When** the operator runs `next`, **Then** the loop advances past implement.
3. **Given** a work package canceled with **no** operator provenance (a synthetic cancellation) at the review step, **When** the operator runs `next`, **Then** the loop continues to treat the package as blocking (fail-closed); likewise at the implement step.
4. **Given** a mission whose committed status log is genuinely absent, **When** the advancement decision is evaluated, **Then** the loop fails loud exactly as today — the change does not swallow a missing-authority condition into a silent pass.

---

### Edge Cases

- A merged mission with **no** leftover coordination checkout (already cleaned up) is still recognized as `kind: terminal`.
- A merged mission that **contains** an operator-canceled work package: the canceled package counts as an accepted terminal lane (via the shipped authority), so the mission is still terminal and the board shows the package as `canceled`, not `planned`.
- A canceled work package that is a **dependency** of another work package is handled by the existing dependency-readiness authority (which already routes through the shipped acceptable-ending authority); this mission does not change dependency gating.
- A canceled work package whose operator reason text happens to resemble an automated template is classified strictly by the shipped provenance authority — this mission introduces no new classification rules.
- Repeated `next` invocations on the same committed state produce the same verdict, independent of which coordination checkout exists on disk.
- Concurrent `next` invocations are out of scope — this mission adds no locking/concurrency behavior beyond today's.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Recognize a merged/terminal mission and emit `terminal` | As an operator, I want `next` to detect a finished mission (`mission_number` assigned + committed status all-accepted) and return `kind: terminal`, creating no runtime run. | High | Open |
| FR-002 | Resolve committed state before trusting a workspace | As an operator, I want `next` to derive mission/WP state from the committed status authority, not from whichever coordination worktree checkout exists, so a stale checkout can never make committed work look unstarted. | High | Open |
| FR-003 | Fail closed when a required workspace lacks the mission's artifacts | As an operator, I want `next` to return `kind: blocked` with a structured reason when actionable work needs a coordination workspace whose selected checkout is missing the mission's artifacts — never a fabricated unstarted/discovery step. | High | Open |
| FR-004 | Status board reads committed authority | As an operator, I want `agent tasks status` to report work-package lanes from the committed status authority (via the same read-path seam), so a merged mission's board shows its committed accepted lanes instead of an all-`planned` rollup from a stale checkout. | High | Open |
| FR-005 | Operator-canceled package advances the loop | As an operator, I want a work package canceled *with* operator provenance to count as an acceptable ending for step advancement, so `next` advances past review and implement instead of stalling. | High | Open |
| FR-006 | Synthetic cancellation stays blocking | As an operator, I want a work package canceled *without* operator provenance to continue blocking advancement, so an automated/synthetic cancellation can never silently advance the loop. | High | Open |
| FR-007 | One acceptable-ending authority, no second definition | As a maintainer, I want the loop's advancement decision to route through the same acceptable-ending / operator-provenance authority used by accept and merge, so a synthetic vs operator cancellation observably differ — proving one canonical definition, not a divergent lane-only predicate. | High | Open |
| FR-008 | One committed-authority definition, consumed by both surfaces | As a maintainer, I want the committed-authority resolution (the acceptable-ending fold and the terminal/conflict verdict) defined **once** in a single module and consumed by both `next` and `agent tasks status`, so neither surface reimplements stale-detection or terminal logic and the two cannot drift. (The shared *path resolver* stays a pure primitive — the committed-authority pre-check lives in the `next` query path, not injected into the resolver, whose other callers must not inherit it.) | High | Open |
| FR-009 | Merge-evidence/committed-status conflict fails closed | As an operator, I want `next` to return `kind: blocked` with a structured conflict reason when `mission_number` is assigned but the committed status is not all-accepted, so a corrupt/disagreeing record is surfaced rather than silently reported terminal or restarted. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Deterministic verdict | For identical committed status inputs, `next` and `agent tasks status` return the same verdict across repeated invocations, independent of which coordination checkout exists on disk (0 verdict variance over repeated runs on unchanged committed state). | Reliability | High | Open |
| NFR-002 | Fail-closed on ambiguity | Every ambiguous provenance input resolves to the safe side (blocking / not-terminal). The ambiguous set is enumerated: (a) the per-WP snapshot is absent/`None`; (b) the snapshot has no reason-source field; (c) the reason-source value is anything other than the canonical operator marker. All three resolve to *blocking* for a canceled WP. | Safety | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Do not modify the acceptable-ending authority | The acceptable-ending / operator-provenance authority (shipped correct in #3774) MUST NOT be changed; this mission routes the loop through it as a pure consumer. | Technical | High | Open |
| C-002 | Do not modify the lane state machine | The lane state machine and transition matrix MUST NOT be changed. | Technical | High | Open |
| C-003 | Preserve fail-loud on missing authority | The committed-state/provenance read MUST preserve today's fail-loud behavior when the status log is genuinely absent (it must not degrade to a silent empty/`None` read that swallows the missing-authority condition). | Technical | High | Open |
| C-004 | Single reduction, no redundant reads | The provenance-gated advancement decision MUST derive both lane and provenance from a single status reduction per work package (not one read for the lane and a second for provenance), so the fix adds no redundant status reduction to the `next` path. | Technical | Medium | Open |
| C-005 | Merge-evidence signal is the committed `mission_number` | Terminal detection MUST key on the committed `mission_number` (assigned at merge) together with the reduced committed status — NOT on transient merge-progress artifacts (in-progress merge-state files / an active git MERGE_HEAD), which are absent precisely when a mission is finished. | Technical | High | Open |
| C-006 | Terminology precision | Artifacts MUST distinguish the *committed status authority* from a *materialized-but-stale coordination worktree checkout*, and name the *read-path-resolution* seam precisely, per the repository's `primary` / `routing` terminology canon; the two authorities MUST NOT be conflated. | Documentation | Medium | Open |
| C-007 | Red-first, issue-pinned regressions + live evidence | Each issue MUST land a failing, issue-pinned regression test driven through the real command entry point, RED on the mission base and GREEN on the final commit (ADR 2026-07-17-1). #3780 additionally requires live `next`-run evidence that the stall is gone, not static reading. | Process | High | Open |
| C-008 | Secondary observations are out of scope | The two secondary #3780 observations (a redundant coordination read in done-bookkeeping; a reason-source denylist in the upstream contract) are out of this mission's blast radius; file them as separate tech-debt follow-ups only if confirmed. | Business | Medium | Open |

### Key Entities

- **Committed status authority**: the reduced work-package state derived from the committed status record on the authoritative committed surface — the single source of truth for each package's lane and its provenance. Distinct from any on-disk workspace.
- **Merge evidence**: the committed `mission_number` (assigned at merge, absent pre-merge), read with the reduced committed status to recognize a terminal (already-consolidated) mission.
- **Operator provenance**: the marker on a canceled work package indicating a human operator, not an automated process, ended it — the discriminator between an acceptable ending and a synthetic one.
- **Coordination workspace checkout**: the on-disk coordination worktree resolved by the read-path-resolution seam; it may be stale or missing the mission's artifacts, and is a *candidate* read surface that must be validated against committed authority, never trusted by mere existence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running `next` on a merged mission (`mission_number` assigned + committed status all-accepted) returns `kind: terminal` in 100% of cases and creates **zero** fabricated discovery/implement runs.
- **SC-002**: `agent tasks status` on a merged mission reports each work package's committed lane (approved/done/canceled) for 100% of packages — zero all-`planned` misreports.
- **SC-003**: Running `next` with an operator-canceled work package advances the loop at **both** the review and implement steps (0 stalls); running it with a synthetic cancellation at both steps blocks in 100% of cases (fail-closed).
- **SC-004**: An unmerged mission whose required workspace is missing the mission's artifacts yields `kind: blocked` with a structured reason from `next` in 100% of cases — zero fake "unstarted" results.
- **SC-005**: A mission whose `mission_number` is assigned but whose committed status is not all-accepted yields `kind: blocked` (conflict) in 100% of cases — never `terminal`, never a restart.
- **SC-006**: Two issue-pinned regression tests (#2947, #3780) are RED on the mission base and GREEN on the final commit, each driven through the real command entry point; #3780 is additionally confirmed by a live `next` run showing the stall is gone.
