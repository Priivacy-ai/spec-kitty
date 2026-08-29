# Mission Specification: Charter Preflight Remediation Authority

**Mission Branch**: `fix/charter-preflight-remediation`
**Created**: 2026-07-27
**Status**: Draft
**Input**: Fixes #2831 (P0). Four behavioural contracts verified against `main@1aed89411`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The gate's own advice can unblock the operator (Priority: P1)

An operator runs the implement step on a project that was set up before the charter bundle was
consolidated. Its charter directory holds the older multi-file bundle and no consolidated charter
file.

The gate refuses to let implementation start, and tells the operator exactly what to run to fix it.
They run it. It reports success-shaped output, changes nothing, and the gate refuses again with the
identical message. Running it a third time changes nothing. There is no other instruction to
follow, and nothing in the output suggests the command was the wrong one.

The operator is in a loop with no exit. Implementation is blocked for every new mission on that
project.

**Why this priority**: This is the P0. It is not a slow fix or a confusing message — it is an
unexitable state reached by following the tool's own instruction.

**Independent Test**: Drive the gate into a blocked state, execute the remediation string it
emitted, re-run the gate, and assert the check's state changed. Delivers the fix on its own.

**Acceptance Scenarios**:

1. **Given** a preflight check reporting a non-passing state and emitting a remediation, **When**
   the operator executes that remediation and re-runs the preflight, **Then** that check's state
   changes.
2. **Given** the same project, **When** the operator follows the remediation the gate now emits,
   **Then** the implement step proceeds — the loop is exitable.
3. **Given** a check whose non-passing state genuinely cannot be self-remediated, **When** it
   reports, **Then** it emits no remediation and is recorded in an explicit, enumerable exemption
   set — it may not satisfy the guarantee by emitting prose that merely *reads* like escalation.
4. **Given** any future check added to the preflight registry, **When** it emits a remediation,
   **Then** the same guarantee is enforced automatically rather than by author discipline.

---

### User Story 2 - Every surface agrees on whether the charter exists (Priority: P1)

The same operator, trying to understand the refusal, runs every diagnostic available. The charter
sync command reports the charter in sync. The charter context command returns the project's full
governance content. Each surface that answers the question at all says the project is healthy.

The gate continues to refuse, because it is asking a different question of a different file than
every diagnostic the operator can reach. Nothing surfaces that disagreement; the operator concludes
the gate is broken, or that their project is fine and something else is wrong.

**Why this priority**: This is what makes the P0 undiagnosable. The block alone is survivable if the
operator can see why; two surfaces silently disagreeing means every investigative step confirms the
wrong conclusion.

**Independent Test**: With the charter in a state one surface calls present and another calls
missing, ask every surface and assert they agree.

**Acceptance Scenarios**:

1. **Given** any project state, **When** the gate and every operator-facing surface *that resolves
   charter presence* are each asked whether the charter exists, **Then** they return the same
   answer. The set of such surfaces is closed and enumerated by plan (FR-004); a surface that never
   asks the question is out of scope and must not be given the capability by this mission.
2. **Given** a project where the charter is genuinely absent, **When** the operator runs any
   diagnostic, **Then** it reports the charter absent rather than reporting healthy.
3. **Given** the older multi-file bundle with no consolidated file, **When** the operator runs the
   diagnostics, **Then** the output distinguishes "no charter at all" from "charter present but not
   in the form the gate requires" — the two states are not conflated.

---

### Edge Cases

- The charter exists but is unparseable — must be distinguishable from absent, on every surface.
- A project with no charter at all (never initialised) must keep its current advisory treatment and
  not be newly blocked by this work.
- A remediation that is correct but requires elevated context (e.g. an upgrade the operator must run
  deliberately) must still be classified as effective, not silently exempted.
- A check emitting no remediation at all is legitimate and must not be forced to invent one — but it
  must be enumerated as exempt, not silently absent, so the exemption is visible and countable.
- At least one existing surface performs a *mutating* refresh while answering what the operator
  experiences as a read-only question. C-002's consolidation must not spread that side effect: the
  surviving canonical resolver must be able to answer without mutating the project.
- Two checks emitting the same remediation string must both be verified independently — a shared
  string does not mean a shared outcome.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | A remediation can clear the check that emitted it | As an operator blocked by a gate, I want the command it tells me to run to actually change the state it is complaining about, so that following the instructions gets me unblocked. | High | Open |
| FR-002 | The blocked charter state names a remediation that works | As an operator on a legacy-bundle project, I want the specific instruction I am given to move me from blocked to unblocked, so that I am not stuck in a loop. | High | Open |
| FR-003 | Remediation effectiveness is enforced structurally | As a maintainer, I want every present and future preflight check held to FR-001 by an automated check, so that the guarantee does not depend on each author remembering it. | High | Open |
| FR-004 | One answer to "does the charter exist" | As an operator, I want the gate and every surface that answers this question to agree on whether my charter is present, so that investigating a refusal converges instead of contradicting itself. Plan must first enumerate the closed set of resolvers and state which are in scope. | High | Open |
| FR-005 | Absent and unusable are distinguishable | As an operator, I want "no charter" and "charter present but not in the required form" reported differently, so that I can tell which problem I actually have. | Medium | Open |
| FR-006 | Existing advisory behaviour is preserved | As an operator on a project with no charter at all, I want the current advisory (non-blocking) treatment to continue, so that this fix does not newly block greenfield work. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | The structural check is non-vacuous | The FR-003 enforcement must fail when a deliberately ineffective remediation is introduced, and must carry a concrete floor equal to the current count of remediation-emitting checks so it cannot pass by finding nothing. It must additionally pin the size of the FR-003 exemption set, so a check cannot escape the effectiveness test by being reclassified as exempt without that reclassification turning the enforcement red. | Reliability | High | Open |
| NFR-002 | Red-first evidence precedes the fix | The reproduction for FR-002 is committed as a failing test before the corrective change, per ADR `2026-07-17-1` and the maintainer's explicit request on #2831. | Maintainability | High | Open |
| NFR-003 | No new blocking states | The change introduces zero project states that are blocked after the fix but were not blocked before, verified across the four fixture shapes in Key Entities. | Reliability | High | Open |
| NFR-004 | Diagnostics stay tolerant | Charter resolution continues to degrade to a reported state rather than raising to the operator; zero new uncaught exception paths on any diagnostic surface. | Reliability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Structural mechanism, not a corrected string | Per `DIRECTIVE_043`, the FR-001/FR-003 response must be an enforcement mechanism that makes the violation a build failure. Correcting the one bad remediation string without that mechanism is non-compliant — it defers the next occurrence rather than closing the class. | Technical | High | Open |
| C-002 | Consolidate, do not patch parity | Per `DIRECTIVE_044`, FR-004 must converge the surfaces onto a single canonical resolver. Teaching the non-canonical surface to mimic the canonical one is an architectural violation, not a fix. | Technical | High | Open |
| C-003 | Do not relocate charter artifacts | The mission changes how charter presence is *resolved and reported*. It must not move, rename, or change the home of any charter artifact. | Technical | High | Open |
| C-004 | Migration behaviour is inherited, not redefined | The consolidation migration that genuinely repairs a legacy-bundle project already exists and works. This mission may point operators at it; it must not reimplement or alter it. | Technical | High | Open |
| C-005 | Issue closure | The mission closes #2831 and claims no other issue. | Business | High | Open |

### Key Entities

- **Preflight check**: One question the gate asks about project readiness. Reports a state, and may
  offer a remediation — an instruction the operator can follow to change that state.
- **Remediation**: The operator-facing instruction attached to a non-passing check. Its defining
  property, currently unenforced, is that executing it changes the state of the check that emitted
  it.
- **Charter presence**: The answer to "does this project have a usable charter". Currently resolved
  independently by more than one consumer, against more than one artifact, which is the defect in
  User Story 2. The spec deliberately does not state how many — the count is a plan deliverable
  (FR-004), and an early draft's guess of "two" was already an undercount.
- **Legacy-bundle project**: A project set up before the charter bundle was consolidated — the
  trigger shape for both stories.
- **Fixture shapes** (the four states every change must be evaluated against): no charter at all;
  legacy multi-file bundle without the consolidated file; consolidated file present and valid;
  consolidated file present but unparseable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every preflight check that emits a remediation, executing that remediation changes
  the emitting check's state — verified for 100% of remediation-emitting checks, not a sample.
- **SC-002**: An operator on a legacy-bundle project reaches an unblocked implement step by
  following only the instructions the tool gives them, in a bounded number of steps, with no
  external knowledge.
- **SC-003**: Plan enumerates every independent resolver of "does the charter exist" and pins the
  count. After the change, the number of *operator-reachable* resolvers is one, and the pinned
  count cannot grow without the enumeration being updated deliberately.
- **SC-004**: Across the four fixture shapes, the count of states that block implementation is the
  same or lower than before the change — never higher.
- **SC-005**: Introducing a deliberately ineffective remediation turns the FR-003 enforcement red.

## Assumptions

- The existing consolidation migration correctly repairs a legacy-bundle project; this mission
  relies on that and does not re-verify its internals beyond the contract that it clears the gate.
- Checks that legitimately have no self-service remediation exist, and the enforcement must
  accommodate them explicitly rather than forcing every check to name a command.
- The operator-reachable resolution paths for charter presence are reconcilable — they are not
  deliberately answering different questions that happen to share a name. Plan must confirm this
  before consolidating; if they turn out to be genuinely different questions, FR-004 becomes "name
  them differently" instead.
- Resolvers that exist only inside one-time migrations are expected to have their own
  idempotency-shaped definition and are not operator-reachable. Plan enumerates them so the count is
  honest, but FR-004 does not oblige them to converge.

## Out of Scope

- Relocating or renaming charter artifacts (C-003).
- Teaching a surface to answer "does the charter exist" when it does not ask today. The mission
  converges surfaces that already disagree; giving a new surface the capability is net-new scope and
  is explicitly not carried here.
- Changing the consolidation migration's behaviour (C-004).
- Remediation effectiveness for gates outside the charter preflight registry — the mechanism should
  be reusable, but proving it across other gates is not this mission's work.

## Diagnosis Provenance

Reported 2026-07-21 against v3.2.5. The reporter's original body arrived with its evidence stripped;
a reproduction was supplied 2026-07-24 against `main@721165a22`, and the maintainer escalated to P0
and invited the fix red-first.

All four contracts were **re-verified against `main@1aed89411`** on 2026-07-27 before this spec was
written — 110 commits later, with zero commits touching the three implicated surfaces in between.

One correction carried forward: the original reproduction cited a `Source:` line printed by the
context command as evidence for User Story 2. That output no longer appears — the command now runs
in a more compact mode. The contract is unchanged and is in fact better evidenced now (it resolves
governance *successfully* while the gate calls the charter missing), but the quoted line is stale
and must not be reused.
