# Mission Specification: Lifecycle Gate Execution Context and Tool-Artifact Ownership

**Mission Branch**: `remediation/coord-lifecycle-gates`
**Created**: 2026-07-23
**Status**: Draft
**Input**: Brownfield remediation of the implement→review→accept→consolidate lifecycle-gate cluster, re-grounded by a pre-spec squad against base `eb06ca176`.

## Overview

A lifecycle gate is a checkpoint that decides whether mission work may advance. Today a gate inherits whatever working tree and directory its caller happened to be standing in, instead of being handed the surface it is meant to judge. Two failure shapes follow:

- **The gate judges a surface where the fact cannot be true.** It then emits a confident wrong verdict — blocking honest work, or silently passing dishonest work.
- **The gate trips over files the toolchain itself wrote.** Because no component owns the lifecycle of generated bookkeeping files, each gate that stumbles on them has been taught a one-off exemption. At least a dozen such mechanisms exist today (the exact population is derived by rule, not counted — see FR-013); none of them commits or rolls anything back.

This mission gives gates an explicit evaluation context they must be handed, and gives generated artifacts an owner that commits or reverts them — so wrong verdicts and exemption lists both stop accumulating.

**Core invariant:** *A lifecycle gate must evaluate the fact it is gating against a surface in which that fact can be true — or refuse to evaluate — and must never trip on, nor orphan, the toolchain's own generated writes.*

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acceptance is not blocked by an uncheckable invariant (Priority: P1)

An operator finishes a mission and runs the acceptance gate. The mission declared a negative invariant — a statement of something that must be absent, such as "this defective pattern no longer occurs" — that can only be judged once the mission's own changes exist in the tree. Pre-consolidation, those changes live on lane branches, so the tree being checked cannot contain them.

Today the gate runs the check anyway from the primary checkout, concludes the invariant is violated, and blocks acceptance. The operator's only escape is to declare no invariants at all — which is what the most recent flagship mission did.

**Why this priority**: This is the live defect that makes command-verified negative invariants unusable at exactly the moment the workflow calls for them. It pushes operators toward recording no invariants, which silently removes a whole class of acceptance evidence.

**Independent Test**: Run acceptance on a mission whose invariant references something the mission itself adds. The gate must not report the invariant violated; it must record that the check is deferred until a surface exists where it can be judged.

**Acceptance Scenarios**:

1. **Given** a mission with an unverified negative invariant whose subject cannot exist in the pre-consolidation tree, **When** the operator runs the acceptance gate, **Then** the invariant is recorded as deferred with a stated reason, and acceptance is not blocked on it.
2. **Given** a negative invariant already judged during work-package review from a surface that did contain the change, **When** the acceptance gate runs later, **Then** the recorded judgement is preserved unchanged and is not re-judged from a different surface.
3. **Given** a deferred invariant, **When** lane consolidation has completed and the post-consolidation verification Op runs, **Then** the invariant is judged against the consolidated tree and its outcome is recorded together with the surface it was judged against.
4. **Given** a deferred invariant that is genuinely violated on the consolidated tree, **When** the post-consolidation verification Op runs, **Then** that Op closes as failed and names the violated invariant, while the completed consolidation is left untouched.

---

### User Story 2 - The consolidation readiness preview tells the truth (Priority: P1)

An operator runs a consolidation readiness preview before consolidating a coordination-topology mission. The preview reports the mission ready. The real consolidation then correctly refuses, because a work package carries a rejected review outcome.

The preview asked one gate to judge two different things — the lane state of each work package, and the review outcome for each work package — while handing it a single directory. Those two facts live on different surfaces. The preview handed the surface that is correct for one and empty for the other, so every work package looked like it had no state at all, and the gate passed by default.

**Why this priority**: A readiness preview that can report ready when the real operation will refuse destroys the value of previewing. The real consolidation is unaffected, so this is a trust defect rather than a data-integrity one — but it is the clearest live instance of the gate-surface confusion this mission exists to remove.

**Independent Test**: Run the readiness preview on a coordination-topology mission holding a genuinely rejected review outcome. The preview must report not-ready, matching what the real consolidation does.

**Acceptance Scenarios**:

1. **Given** a coordination-topology mission with a genuinely rejected review outcome on a work package, **When** the operator runs the consolidation readiness preview, **Then** the preview reports not-ready and names the offending work package.
2. **Given** a coordination-topology mission carrying a stale leftover review file that is not the authoritative record, **When** the preview runs, **Then** the leftover does not cause a false not-ready result.
3. **Given** any gate that needs facts from two different surfaces, **When** it is invoked, **Then** it resolves each fact from its own declared surface rather than from a single directory supplied by its caller.

---

### User Story 3 - Merge is not blocked by the toolchain's own bookkeeping (Priority: P1)

An operator finishes the work and runs the consolidation. It refuses, because the coordination working tree holds uncommitted changes that a safe resynchronisation would destroy. Those changes are not the operator's work — they are files spec-kitty itself wrote during the normal lifecycle and then left behind, owned by nobody.

The operator's recovery today is to hand-commit or hand-revert the toolchain's own files inside a working tree they are explicitly told never to hand-commit into.

**Why this priority**: This blocks the terminal step of a mission and its only workaround violates a standing rule of the workflow. It also blocks *this* mission, which runs on coordination topology.

**Independent Test**: Run a mission through claim to consolidation on coordination topology without any manual intervention in the coordination working tree. The consolidation must complete.

**Acceptance Scenarios**:

1. **Given** a mission whose lifecycle has written toolchain bookkeeping files, **When** the operator runs the consolidation, **Then** it proceeds without the operator touching those files by hand.
2. **Given** a consolidation that is rolled back partway, **When** the operator resumes it, **Then** the resumed run starts from a clean state with no leftover writes from the aborted attempt.
3. **Given** a toolchain-generated write during any lifecycle step, **When** that step completes or aborts, **Then** the write is either committed to its declared home or fully reverted — never left orphaned.

---

### User Story 4 - A gate that cannot judge says so (Priority: P2)

An agent or operator triggers a gate in a situation the gate cannot meaningfully evaluate. Rather than guessing from whatever surface is at hand and producing a verdict that looks authoritative, the gate declines and states why.

**Why this priority**: This is the general contract underneath Stories 1 and 2. Delivering it turns two site fixes into a property of every gate, including gates added later.

**Independent Test**: Invoke a gate with a context in which its subject cannot exist. It must return a distinguishable "cannot evaluate here" outcome rather than a pass or fail.

**Acceptance Scenarios**:

1. **Given** a gate whose declared evaluation surface cannot be resolved, **When** it is invoked, **Then** it fails loudly with a named reason and does not quietly fall back to a different surface.
2. **Given** a gate invoked at a lifecycle phase in which its subject cannot yet exist, **When** it runs, **Then** it returns a not-applicable-here outcome rather than a verdict.
3. **Given** any gate verdict, **When** it is recorded or displayed, **Then** it names the surface it was judged against.

---

### User Story 5 - The next contributor cannot add another exemption (Priority: P2)

A contributor adds or changes a gate and finds it trips over a toolchain-generated file. Today the established path is to add that filename to an exemption list — one more such list. This mission makes that path unavailable and points them at the owner instead.

**Why this priority**: Without this, the class regrows. The exemptions accumulated one ticket at a time precisely because each individual addition was locally reasonable — which is also why the population was miscounted repeatedly (8, then 9, then ≥11) and why the registry, not a count, is the authority.

**Independent Test**: Attempt to introduce a new filename-based gate exemption. An automated check must refuse it and name the owner as the correct route.

**Acceptance Scenarios**:

1. **Given** the exemption mechanisms have been retired, **When** a contributor adds a new filename-based exemption to any dirty-state gate, **Then** an automated check fails and names the artifact owner as the supported route.
2. **Given** a toolchain-generated artifact kind, **When** it is written anywhere in the lifecycle, **Then** exactly one owner is accountable for committing or reverting it.

---

### User Story 6 - Archiving a completed mission does not become an escape hatch (Priority: P3)

An operator archives an old, completed mission so its artifacts are preserved as an
explicitly-legacy snapshot and no longer participate in live validation. The operation refuses to
let them dodge a real, unresolved problem.

**Why this priority**: archiving is independently useful, but an ungoverned archive is a
one-command escape from any acceptance failure. The guards are what make it safe rather than a
hole.

**Independent Test**: attempt to archive a mission that is not terminal, and a terminal mission
that still carries a `still_present` invariant; both must be refused. Archive a genuinely terminal,
clean mission; it must succeed, remain enumerable, and drop out of live validation.

**Acceptance Scenarios**:

1. **Given** a mission that is not terminal (not merged or closed), **When** the operator attempts
   to archive it, **Then** the operation is refused with a stated reason.
2. **Given** a terminal mission carrying an invariant recorded `still_present`, **When** archiving
   is attempted, **Then** it is refused — a violation must be resolved, not filed away.
3. **Given** a terminal mission with no `still_present` invariant, **When** it is archived, **Then**
   the archive record names the operator, the timestamp and the reason; the mission is excluded
   from live validation; and it remains enumerable (e.g. via `doctor`) so the debt stays visible.
4. **Given** the schema migration (FR-014) encounters a mission it cannot bring onto the schema,
   **When** the migration runs, **Then** it does **not** auto-archive — archiving is operator-invoked
   only, never reachable from the migration's own failure path.

---

### Edge Cases

- **A mission with no coordination topology.** The wrong-surface defect in Story 1 is not specific to coordination missions — it occurs identically on a flat mission whose work sits on lane branches not yet consolidated. Fixes must not be conditioned on topology, or the flat case stays broken.
- **A multi-lane mission pre-consolidation.** There is no single tree containing every lane's changes before consolidation. A gate must not fabricate one by picking an arbitrary lane's surface and calling it integrated.
- **An invariant deferred to consolidation that is then violated.** The post-consolidation verification Op is where it surfaces; failing there must be loud, must name the invariant, and must leave the completed consolidation untouched — enforcement is the external CI check (FR-016), not an abort inside consolidation.
- **A gate that is genuinely correct to block.** Removing false blocks must not remove true ones — a real rejected review must still stop a consolidation.
- **A rollback partway through the consolidation.** Reverting must return every toolchain-written surface to its prior state, not only the branch.
- **Re-running an already-judged invariant.** A second judgement must never silently replace a first one recorded from a different surface.
- **Concurrent lifecycle steps writing the same artifact.** Ownership must be unambiguous when two steps touch one generated file.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Gates receive an explicit evaluation context | As an operator, I want every lifecycle gate to be handed the surface, reference point, and lifecycle phase it must judge, so that it never silently judges whatever surface its caller happened to be standing in. | High | Open |
| FR-002 | Judgements carry their surface | As an operator, I want every recorded invariant judgement to state which surface and reference point it was established against, so that a later reader can tell whether the judgement is still meaningful. | High | Open |
| FR-003 | Unjudgeable invariants defer instead of failing | As an operator, I want an invariant whose subject cannot exist in the current surface to be recorded as deferred with a stated reason, so that acceptance is never blocked by a check that could not have passed. | High | Open |
| FR-004 | Deferred invariants are judged post-consolidation, when the verification runs | As an operator, I want invariants deferred at acceptance to be judged against the consolidated mission tree — the first surface on which a mission-wide fact can be true — and recorded with that surface, so that deferral postpones the check rather than skipping it. Judgement is performed by the post-consolidation verification Op (dispatched, not automatic) and enforced by the external CI check (FR-016); absent that CI, the deferral is **disclosed** (FR-017), not silently judged. This is a deliberate, disclosed limitation — see FR-016/FR-017 and ADR 2026-07-23-2. | High | Open |
| FR-005 | A violated deferred invariant fails its Op, not the consolidation | As an operator, I want a deferred invariant that proves violated on the consolidated tree to fail the post-consolidation verification Op with the invariant named — leaving the completed consolidation untouched — so that deferral never becomes a way to smuggle a violation through, and so that verification never becomes a new abort path inside consolidation itself. | High | Open |
| FR-006 | Each fact resolves from its own surface | As an operator, I want a gate that needs facts from two different surfaces to resolve each independently rather than trusting one directory supplied by its caller, so that the consolidation readiness preview stops silently passing rejected reviews. | High | Open |
| FR-007 | Generated artifacts have a single owner | As a maintainer, I want one component accountable for the lifecycle of every artifact the toolchain generates, so that writing, committing, and reverting them is a property of the system rather than of each caller. | High | Open |
| FR-008 | Generated writes are committed or reverted, never orphaned | As an operator, I want every toolchain-generated write to end up either committed to its declared home or fully reverted, so that no lifecycle step leaves state behind that a later gate must be taught to ignore. | High | Open |
| FR-009 | Every mechanism on the exemption registry is retired | As a maintainer, I want every filename- or path-based gate exemption on the registry removed and its behaviour subsumed by the owner, so that the class is closed rather than frozen at its current size. **No count is normative**: the registry (FR-013 / NFR-006) is the authority, and it is derived by rule, not hand-enumerated — successive hand counts gave 8, 9, then ≥11. | High | Open |
| FR-010 | Acceptance evidence is authored once, to one home | As a maintainer, I want the acceptance record written directly to its declared home with no second scaffolded copy, so that added fields cannot diverge between two copies. | Medium | Open |
| FR-011 | The claim-time blocking mechanism is established by live reproduction | As a maintainer, I want the actual mechanism that blocks consolidation after a claim confirmed by reproducing it, so that the fix addresses the real cause rather than a reported one that no longer matches the code. | High | Open |
| FR-012 | One canonical churn classifier | As a maintainer, I want a single definition of what counts as toolchain-generated churn, consumed by every gate that needs it, so that two gates cannot disagree about the same file. | Medium | Open |
| FR-013 | Adding a new exemption is refused | As a maintainer, I want an automated check that refuses a newly added filename-based gate exemption and names the owner as the route, so that the class cannot regrow after this mission. | High | Open |
| FR-014 | Existing matrices migrate onto the schema with a truthful sentinel | As a maintainer, I want a one-time migration that brings all existing acceptance matrices onto the provenance schema. Because `verified_surface_kind` is typed `TopologySurface` (whose anti-phantom rule forbids an unresolvable member), the legacy sentinel is **not** a `TopologySurface` value: it is a separate nullable provenance-origin field — `provenance_origin: recorded | legacy_unrecorded` — where `legacy_unrecorded` means *recorded before provenance existed*, leaves `verified_surface_kind` and `verified_ref` null, and is accepted by `validate_matrix_evidence` in place of them for exactly that origin. This carries one validity regime without grandfathering by version or fabricating a surface. | High | Open |
| FR-015 | Archiving is a first-class mission lifecycle operation | As an operator, I want to archive a completed or abandoned mission so its artifacts are preserved as an immutable, explicitly-legacy snapshot and excluded from live validation, so that historical missions never block current work. Archiving is refused for a mission that is not terminal, and refused while any invariant is `still_present`; the record names operator, timestamp and reason; archived missions remain enumerable so the debt stays visible rather than deleted. | Medium | Open |
| FR-016 | Dangling post-consolidation work fails CI | As a maintainer, I want a consistency check at the front of the CI quality run that fails any pull request still carrying an unresolved `deferred_to_consolidation` invariant, so that deferral is enforced where the artifact is actually readable rather than by a loop guardrail that cannot fire. | High | Open |
| FR-017 | Deferral discloses its own contract | As an operator, I want Spec Kitty to tell me — at the moment it assigns `deferred_to_consolidation` — that the mission loop will not verify this and what gate I need, so that a repository without this project's CI check is not silently relying on an enforcer it does not have. | High | Open |
| FR-018 | User-facing guides describe the deferral contract | As an operator reading the docs, I want the accept-and-merge guide to explain when an invariant is deferred, what the post-consolidation step verifies, and what gate my repository needs, so that the contract is discoverable before I hit it rather than only at assignment time. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No undeclared surface substitution | Zero code paths on the acceptance, preview, and merge-guard routes may resolve to a surface the caller did not declare **without saying so**. Each coordination state has ONE declared answer — `DELETED` raises; `EMPTY` and `UNMATERIALIZED` resolve primary *and stamp `surface_kind = PRIMARY` on the verdict*; `MATERIALIZED` resolves coord — and a gate handed a PRIMARY-stamped surface for a COORD-homed kind must return cannot-evaluate rather than a verdict. Verified by fault-injection over the enumerated resolver states, not over an unbounded 'every such path'. | Reliability | High | Open |
| NFR-002 | Transactional generated writes | For every row in the tool-artifact enrolment inventory, interrupting the step leaves the artifact in its pre-step or fully-committed post-step state; no third state is observable. Verified by a fork+SIGKILL trial harness (≥100 trials with a both-outcomes non-vacuity floor, POSIX-gated) in the idiom of `tests/integration/test_intake_atomic_writes.py`; commit-spanning paths are verified by recovery instead. The inventory, not an unbounded path set, is the oracle. **The fork+SIGKILL harness is POSIX-gated**, so byte-level transactionality is verified on Linux/macOS but not Windows; on Windows the recovery-based guarantee is the sole check — a disclosed platform gap, not an unstated one. | Reliability | High | Open |
| NFR-003 | Every verdict names its surface | 100% of gate verdicts and recorded invariant judgements carry a resolvable identifier of the surface and reference point they were derived from. | Observability | High | Open |
| NFR-004 | No regression of shipped escape hatches | The previously delivered gate opt-out and environment-variable suppression behaviours remain green throughout; their existing regression tests are run unchanged and must not be modified to pass. | Reliability | High | Open |
| NFR-005 | Interactive latency unchanged | Measured against a named baseline captured on the mission base before any work package lands: `spec-kitty accept --diagnose` on the coord and flat fixtures. No gate touched by this mission may increase that baseline by more than 5 seconds. Post-consolidation invariant judgement is explicitly non-interactive and exempt. | Performance | Medium | Open |
| NFR-006 | Every enumerated exemption symbol is retired | Each mechanism on the mission's named retirement list is absent from `src/` at mission end, verified per symbol; and an automated check refuses a newly introduced one. Stated as an enumerated list, not a count — the count was hand-derived, was wrong (9, not 8), and needs an oracle nobody has written. | Maintainability | High | Open |
| NFR-007 | Quality gates clean | All changed code passes the project linter and type checker with zero new issues and zero suppressions added; no function introduced or modified exceeds the project complexity ceiling of 15. | Maintainability | High | Open |
| NFR-008 | Behaviour pinned by tests; structure only where the property IS structural | Every requirement is verified by a test asserting observable behaviour on a realistic fixture rather than by a scan for code shape. **Amended 2026-07-23**: a structural test is permitted ONLY for a property that is inherently structural — the absence of a code pattern cannot be observed behaviourally — and then only in **negative, registry-backed** form (assert nothing exists outside an explicit, shrinking registry), never as a positive literal count. This is the single exception; it exists because FR-013's ratchet and the unamended NFR were in direct contradiction. | Testability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Work touching the `merge/` package waits on in-flight pull requests | No work package that edits `merge/preflight.py` or `merge/executor.py` may begin until the two in-flight pull requests touching those files have landed and this mission has rebased onto them. | Technical | High | Open |
| C-002 | The claim-time consolidation blocker is fixed first | Because this mission runs on coordination topology, the defect that blocks consolidation after a claim must be reproduced and fixed before any other work package reaches its terminal step, or the mission cannot consolidate itself. | Technical | High | Open |
| C-003 | The mission runs on coordination topology | This mission dogfoods coordination topology deliberately, accepting that the defects under repair will be exercised during its own lifecycle. | Technical | High | Open |
| C-004 | Fixes must not be conditioned on topology | The wrong-surface defect occurs on flat missions too; no fix may be gated on coordination topology being active, and none may carry a coordination-specific name that would exclude the flat case. | Technical | High | Open |
| C-005 | New shared symbols must be registered on the compatibility surface | Any new symbol exposed on the task-command surface must be registered in the compatibility inventory and its golden count updated in the same work package. | Technical | Medium | Open |
| C-006 | New sinks and test files must be registered with the project gates | Any new filesystem sink requires a row in the path audit inventory; any new architectural test file must be registered with the shard map; the coverage baselines must be updated deliberately, not silently. | Technical | Medium | Open |
| C-007 | Harvest the rejected contribution's tests with attribution | The two coordination-topology integration tests from the pull request that was kept for reference must be harvested with attribution to their author rather than rewritten from scratch. | Process | Medium | Open |
| C-008 | Delivery is a draft pull request; the operator publishes | Work lands as a draft pull request from the fork branch. **Publish** (sense 3) is the operator's action alone — this mission never publishes. No direct push to the upstream primary branch under any circumstance. | Process | High | Open |
| C-009 | No hand-commits into the coordination working tree | The workflow rule stands during this mission: no manual commits into the coordination working tree. If a defect forces one, that is evidence for the mission, and must be recorded rather than quietly worked around. | Process | High | Open |
| C-010 | Retirement is behaviour-preserving where the exemption was right | Some exemptions encode genuinely correct behaviour. Retiring the mechanism must preserve that behaviour through the owner; a retirement that reintroduces a false block is a regression, not a simplification. | Technical | High | Open |

### Key Entities

- **Gate Execution Context**: The bundle a gate is handed rather than infers — which surface to judge, which reference point that surface is expected to be at, and which lifecycle phase the judgement is happening in. A gate that cannot be given a valid one refuses instead of guessing.
- **Lifecycle Phase**: Where in the mission lifecycle a judgement is being made (review, acceptance, post-consolidation). Some facts can only be true from certain phases onward; a gate declares which phases it is valid in.
- **Negative Invariant**: A recorded statement that something must be absent, together with how to check it, the outcome, and — new in this mission — the surface and reference point the outcome was established against.
- **Deferred Judgement**: An invariant that could not be judged in the current phase, recorded with the reason and the phase at which it will be judged, so that deferral is visible rather than silent.
- **Tool-Artifact Owner**: The single component accountable for artifacts the toolchain generates — writing them to their declared home, committing them, and reverting them on failure. Replaces the practice of teaching each gate to ignore them.
- **Generated Artifact**: A file spec-kitty writes as part of running the workflow, as distinct from work authored by the operator. The distinction is what the exemptions were approximating.
- **Artifact Home**: The declared authoritative location for an artifact kind. Reads and writes both resolve to it; a fact is judged where it lives.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A mission declaring a `custom_command` negative invariant completes acceptance without emptying or weakening its invariant list — demonstrated by (a) the pending-leg red→green regression test, and (b) **this mission's own `acceptance-matrix.json` shipping a non-empty `negative_invariants` list**. Stated as a capability claim, not a "rate": the prior population is a single mission, and a rate over n=1 is rhetoric.
- **SC-002**: The consolidation readiness preview and the real consolidation agree on readiness in 100% of cases across the coordination and flat fixtures, including the rejected-review case that currently disagrees.
- **SC-003**: A mission runs from claim through merge on coordination topology with zero manual interventions in the coordination working tree.
- **SC-004**: Every mechanism on the enumerated retirement list is absent from `src/` at mission end — verified per named symbol rather than by counting — and an automated check refuses a newly introduced one. Judged **post-consolidation**: this is a mission-wide absence claim that no single lane can prove and the primary tree contradicts until consolidation, so it is recorded `deferred_to_consolidation` and resolved by the verification Op.
- **SC-005**: Every recorded invariant judgement states the surface it was established against; judgements without that information are refused at validation time.
- **SC-006**: For **every row in the tool-artifact enrolment inventory** — a tool-derived list that self-asserts in both directions (no undiscovered sink, no ghost row) — interrupting the writing step leaves the artifact byte-identical to either its pre-transaction snapshot or its committed post-state. Scoped to the inventory rather than an unbounded "every write path", which had no oracle. Where a write path spans a git commit, the guarantee is verified by **recovery** (re-invoking reaches the committed state, leaves no residue) rather than by kill-atomicity.
- **SC-008**: Archiving is refused for any non-terminal mission and for any terminal mission
  carrying a `still_present` invariant; a successful archive is enumerable afterward and excluded
  from live validation; and the migration never auto-archives. Verified by the four US6 scenarios.
- **SC-007**: No previously passing behaviour regresses. At consolidation, the full architectural suite and the existing escape-hatch and rollback regression tests are green. **Amended 2026-07-23** to distinguish two things C-006 otherwise put in direct conflict: *regression tests* must be green **without being modified** (diff-checkable), while *baseline and registry files* — the shard map, the gate-coverage baselines, the path-audit inventory, the compat golden — are updated **deliberately and reviewed**, which C-006 requires. Updating a baseline is not modifying a test.

## Assumptions

- The artifact placement authority delivered by the recently merged coordination-commit-integrity work is sound and is consumed as a given; this mission extends it to the gate layer rather than revisiting it.
- The existing transactional component used for coordination-branch status writes is the right foundation to generalise, rather than a new parallel mechanism — the project already carries two compensating implementations and a third would be a regression.
- Judging deferred invariants after consolidation is acceptable to operators as later-but-honest feedback, in preference to earlier-but-wrong feedback. The blast radius is bounded because the consolidated tree is the mission/PR branch, not the primary branch — a violation blocks the pull request, and the operator's manual publish step remains a further gate.
- The exemption mechanisms are individually well-intentioned and some encode correct behaviour; retirement is a migration to a single owner, not deletion of their effect.
- Coordination topology for this mission is workable once the claim-time merge blocker is fixed first, per C-002.

## Out of Scope

The following were considered and excluded, with reasons, so that a later planner does not re-import them:

- **The synchronous pre-review gate's progress reporting.** Both originally requested asks — an opt-out flag and environment-variable suppression — are already delivered and green on the mission base. The residue is a progress heartbeat, which is cosmetic once an escape hatch exists. Its regression tests are protected by NFR-004.
- **The coordination artifact-authority hardening residuals.** All five named residuals are closed and complete. The one genuinely unfinished piece found during re-grounding was filed separately rather than absorbed here.
- **Non-transactional merge rollback of coordination status writes.** Fixed by prior work; its regression test is green on the mission base and is protected by NFR-004.
- **The changelog symlink-versus-file conflict on a stale base.** Adjacent context in the source report, not an ask; it belongs to the base-staleness family, which already has a detector.
- **Analysis-report freshness friction.** A different seam and a different class. It may be encountered during this mission's own implement loop; if it recurs it is to be recorded as evidence, not fixed here.

## Domain Language

This mission touches two known overloaded terms. The specification uses them in exactly one sense each, and work packages must do the same:

- **Surface** is used throughout in preference to the overloaded alternatives, and means *the concrete tree or directory from which a fact is read or judged*.
- **Primary** appears only as **primary partition** (the artifact partition) or **primary branch** (the repository's main line), always qualified. It is never used bare.
- **Consolidation** is the canonical name for the `spec-kitty merge` step that integrates lane branches into the mission branch. **Post-consolidation** names the phase, the surface (`CONSOLIDATED`), and the verification that runs there. The bare word *merge* is never used for this, because it already carries three senses in this codebase.
- **Merge** appears only as **branch integration** (a git merge) or **publish** (sending commits to the upstream remote), never as a name for the mission lifecycle step. This mission never publishes; the operator does.
- **Deferred** means an invariant judgement postponed to the post-consolidation phase, and is distinct from a decision deferred during discovery.
