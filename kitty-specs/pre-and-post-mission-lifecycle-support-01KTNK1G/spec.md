# Pre and Post Mission Lifecycle Support

**Mission ID**: 01KTNK1G481QA8GK4MFEHBE9AK
**Mission Slug**: pre-and-post-mission-lifecycle-support-01KTNK1G
**Mission Type**: software-dev
**Status**: Draft
**Created**: 2026-06-09
**Target Branch**: main
**GitHub Issue**: Priivacy-ai/spec-kitty#1802

---

## Problem Statement

Spec Kitty is strong once a mission exists and while it is actively executing, but the edges are still split across partially separate flows. Pre-mission intake can come from tracker tickets or imported briefs; post-mission follow-through can happen through merges, follow-up commits or PRs, or corrections to missions that were closed incorrectly. Today those edges do not feel like one lifecycle. Users need the mission source, follow-up work, and correction history to remain visible and auditable without changing the core in-mission state machine.

This mission absorbs and supersedes the former issue-tracker intake (#687) and GitHub Spec Kit import (#1220) epics, regrouping them as one pre/post-mission lifecycle concern.

## Goals

- Preserve external intent when a mission starts from a ticket or imported plan.
- Reuse that intent during specify, plan, and tasks instead of re-deriving it.
- Keep intake provenance local, readable, and auditable.
- Provide first-class follow-up and correction links after a mission completes.
- Let operators reopen or correct a mission that was completed incorrectly without rewriting history.
- Leave the core in-mission execution/state model unchanged.

## Out of Scope

- Changing the core mission state machine, dependency graph, or lane semantics.
- Introducing local credential storage or new tracker authentication mechanisms.
- Replacing existing in-mission execution commands wholesale.
- Non-Markdown or binary import formats beyond the current plan and brief pipeline.
- Any redesign of SaaS wire formats or tracker provider APIs.

## Actors

| Actor | Role |
|-------|------|
| Developer | Starts a mission from a ticket or imported brief, then follows it through completion and follow-up. |
| AI Agent | Runs specify, plan, and follow-up workflows and preserves provenance in the mission record. |
| External Source | Jira, Linear, GitHub, GitLab, PlanBridge, or a Markdown plan file that seeds the mission brief. |
| Maintainer / Reviewer | Confirms whether a completed mission needs follow-up, correction, or reopening. |
| Spec Kitty CLI | Creates intake artifacts, mission metadata, and lifecycle events on the local machine. |

## User Scenarios

### Scenario 1: Start from a supported tracker ticket

1. Developer has a ticket in GitHub, Jira, Linear, or GitLab that already captures the mission intent.
2. Developer starts a new mission from that ticket.
3. The mission stores the ticket provenance in local metadata and brief artifacts.
4. `/spec-kitty.specify` uses the ticket content as the starting brief instead of re-deriving the same requirements.
5. The resulting spec, plan, and tasks retain the original ticket source in a readable form.

### Scenario 2: Start from an imported plan or reviewed brief

1. Developer has a Markdown plan, a GitHub Spec Kit plan, or a PlanBridge-reviewed brief.
2. Developer imports that brief into the mission intake path.
3. The mission records the imported source and uses it as the authoritative starting point.
4. `/spec-kitty.specify` fills only the gaps that are not already covered by the brief.
5. The imported source remains locally inspectable while the mission is in progress.

### Scenario 3: Attach follow-up work after merge

1. A mission reaches done and is merged.
2. A maintainer later opens a follow-up commit or PR tied to that mission.
3. The follow-up stays linked to the original mission record.
4. Mission review and status surfaces show both the original completion and the follow-up trail.

### Scenario 4: Correct or reopen a mission that completed incorrectly

1. A mission was marked complete, but the completion was wrong or premature.
2. A maintainer reopens or corrects the mission through a governed lifecycle action.
3. The original completion history is preserved.
4. The correction is appended as new lifecycle history instead of rewriting the past.

### Scenario 5: No external input, no behavioral change

1. Developer starts a mission without a ticket, imported brief, or follow-up record.
2. Existing specify, plan, tasks, review, and merge behavior remains unchanged.
3. The mission lifecycle edge features stay dormant until they are needed.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Mission creation shall accept supported external tracker tickets as authoritative intake for new missions. | Proposed |
| FR-002 | Mission creation shall accept imported Markdown plan briefs as authoritative intake for new missions. | Proposed |
| FR-003 | Mission intake shall persist source provenance in local metadata using human-readable artifacts and append-only mission records. | Proposed |
| FR-004 | `spec-kitty specify` shall detect and consume existing mission brief or ticket-context artifacts before starting a fresh discovery interview. | Proposed |
| FR-005 | When intake artifacts already answer a question, specify shall not ask it again. | Proposed |
| FR-006 | Mission metadata and review surfaces shall expose the source kind, source reference, and source title for the mission brief. | Proposed |
| FR-007 | A completed mission shall be able to record one or more follow-up commits or PRs as mission-linked provenance. | Proposed |
| FR-008 | Follow-up links shall survive merge and remain visible in mission review and status surfaces. | Proposed |
| FR-009 | A completed mission shall be reopenable or correctable when the completion was wrong, with an append-only audit trail. | Proposed |
| FR-010 | Reopen or correction actions shall not erase the original completion history or follow-up records. | Proposed |
| FR-011 | External intake and post-mission follow-up shall not require the operator to store provider credentials locally. | Proposed |
| FR-012 | When no external intake or follow-up artifact is present, existing mission behavior shall remain unchanged. | Proposed |
| FR-013 | The mission shall not introduce new in-mission execution topology or dependency-gating rules. | Proposed |
| FR-014 | The mission shall preserve mission provenance in a form that can be inspected offline without SaaS access. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Intake and provenance capture shall not materially slow normal mission creation or closeout. | Bounded, interactive-scale latency | Proposed |
| NFR-002 | Mission history shall remain append-only and recoverable from local artifacts when disconnected from SaaS. | Zero destructive history rewrite | Proposed |
| NFR-003 | Imported source files and mission provenance shall remain human-readable and easy to inspect locally. | Offline intelligibility | Proposed |
| NFR-004 | Existing no-intake mission flows shall remain behaviorally stable. | No observable regression | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Mission is the canonical product term; do not introduce new user-facing Feature naming. | Confirmed |
| C-002 | Exact command names for post-mission follow-up and correction surfaces may be finalized during plan, as long as the behaviors above are met. | Confirmed |
| C-003 | Mission lifecycle edge work must reuse existing provenance and status-event patterns instead of introducing a parallel history model. | Confirmed |
| C-004 | Pre-mission intake and post-mission follow-up are related but distinct; in-mission execution logic remains separate. | Confirmed |
| C-005 | Existing ticket-context and brief-intake artifacts are the reference pattern for provenance capture. | Confirmed |

## Key Entities

| Entity | Location | Role |
|--------|----------|------|
| TicketContext | `.kittify/ticket-context.md` | Tracker ticket content that can seed specify and carry origin provenance. |
| MissionBrief | `.kittify/mission-brief.md` | Imported plan or brief content that can seed specify. |
| BriefSource | `.kittify/brief-source.yaml` | Provenance metadata for imported briefs. |
| PendingOrigin | `.kittify/pending-origin.yaml` | Tracker-origin metadata that specify can consume after mission creation. |
| MissionEventLog | `status.events.jsonl` | Append-only lifecycle history for state changes, follow-up links, and correction events. |
| FollowUpLink | Mission metadata or event record | Commit or PR reference attached after merge. |
| CorrectionRecord | Mission metadata or event record | Append-only record of reopen or correction actions. |

## Success Criteria

1. A supported ticket or imported plan can start a mission and retain source provenance.
2. The mission can be specified without re-asking already-answered questions.
3. A completed mission can gain follow-up commit or PR links that remain visible after merge.
4. A mission completed incorrectly can be reopened or corrected without erasing its history.
5. Missions started without external intake or follow-up data behave as they do today.

## Dependencies

| Dependency | Notes |
|-----------|-------|
| `src/specify_cli/tracker/ticket_context.py` | Reference pattern for tracker-origin provenance and brief artifacts. |
| `spec-kitty intake` | Existing brief import path for Markdown plan intake. |
| Existing mission status and merge surfaces | Needed for follow-up and correction visibility. |
| Existing tracker provider services | Needed for supported ticket intake sources. |

## Assumptions

| # | Assumption |
|---|------------|
| 1 | The first implementation slice will likely focus on pre-mission intake, then expand into post-mission follow-up. |
| 2 | GitHub issue #1802 is an umbrella epic and will be decomposed into smaller work packages during plan. |
| 3 | Imported plan formats remain Markdown-first for the initial delivery. |
| 4 | Follow-up and correction surfaces may extend existing commands rather than introduce a wholly new top-level workflow. |
