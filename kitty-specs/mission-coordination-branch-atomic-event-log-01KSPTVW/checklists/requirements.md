# Specification Quality Checklist: Mission Coordination Branch with Atomic Event Log

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-28
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *naming concrete artifacts like `os.truncate`, `commit_helpers.py`, and `status.events.jsonl` is unavoidable: they are the actual entities the bug lives in. Otherwise no framework / library / DSL leak.*
- [x] Focused on user value and business needs — *primary value is "implement/review never leaves dangling state on main"; tracked through SCs.*
- [x] Written for non-technical stakeholders — *Purpose section, scenarios, and success criteria are readable without code knowledge. FR table necessarily uses internal terms.*
- [x] All mandatory sections completed — *Purpose, Scenarios, FR, NFR, Constraints, Success Criteria, Key Entities, Assumptions, Out of Scope, References. Domain Language included (optional).*

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-### (27), NFR-### (11), and C-### (13)
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds — *7/7 NFRs have explicit thresholds (100% test pass, < 100ms, ≤ 1 sync point, < 2s, ≤ 1 KB, ≥ 90% coverage, one stable identifier).*
- [x] Success criteria are measurable — *SC-01 through SC-07 each cite a count, threshold, or pass/fail check.*
- [x] Success criteria are technology-agnostic — *cite outcomes (lane state visibility, byte-identical file state, terminal output legibility), not implementation choices.*
- [x] All acceptance scenarios are defined — *Primary, Exception A (protected branch), Exception B (commit failure), Exception C (concurrent emit), 5 edge cases.*
- [x] Edge cases are identified — *5 edge cases enumerated.*
- [x] Scope is clearly bounded — *Out of Scope section names 6 explicit exclusions.*
- [x] Dependencies and assumptions identified — *8 assumptions, 7 references.*

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria — *each FR is single-statement, testable, and references concrete observable state.*
- [x] User scenarios cover primary flows — *primary multi-lane happy path is the lead scenario.*
- [x] Feature meets measurable outcomes defined in Success Criteria — *SC-06 explicitly maps to the issue #1348 regression check.*
- [x] No implementation details leak into specification — *Banned-but-named entities (`commit_helpers.py`, `os.truncate`, `status.events.jsonl`, `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS`) appear because they are the system surface the spec must constrain, not implementation choices being prescribed. The spec does not pick languages, frameworks, libraries, or design patterns beyond what the existing system already uses.*

## Issue #1348 Acceptance Coverage

The issue states three acceptance criteria:

- [x] **"One consistent rule about which commits implement allows on a protected branch, documented in `commit_helpers.py` and surfaced in implement output."** → Covered by FR-001 (symmetric refusal), FR-013 (no silent-bypass entries), FR-014 (commit summary in output).
- [x] **"`finalize-tasks` records the canonical target branch (typically `main`) in WP frontmatter / `lanes.json`, not the current checkout branch at the moment finalize ran."** → Covered by FR-012; verified by SC-04.
- [x] **"Implement output summarizes what was committed and where, before declaring success or failure."** → Covered by FR-014; verified by SC-03.

Plus from the comment:

- [x] **"Make event-log appends + tracking commits atomic"** (chosen approach: surgical rollback) → Covered by FR-009 (pre_emit_size capture), FR-010 (surgical truncate / event_id-targeted removal), FR-011 (diagnostic on rollback); verified by NFR-001, SC-05, SC-06.

## Notes

- This spec adds substantive scope beyond the issue's stated acceptance: the **coordination branch** topology. The user's interview answers explicitly directed this, identifying that "all-on-lane" without a coordination branch breaks the 3.0 status model's "event log is sole authority" invariant. The added scope is necessary to make the simpler fix (all-on-lane) actually work.
- **Cross-review integration (2026-05-28)**: After the initial spec draft, an independent investigation (Debugger Debbie / 5-paradigm) identified three additional architectural concerns that were folded back into the spec:
  - **Pre-flight policy gate** (FR-019, FR-020, FR-021, NFR-008, SC-08) — refuses the operation *before* any write, composing with the post-write surgical rollback (FR-010). The pre-flight gate handles protected-branch refusal cheaply; the rollback handles residual post-write failures (hook reject, disk full, branch-protection race).
  - **Named core invariant** in the Purpose section: "No workflow mutation may occur unless the corresponding git mutation is permitted." Elevates the implicit contract to a stated invariant.
  - **Outbound side-effect deferral** (FR-022, NFR-009, SC-09) — SaaS event sync, dossier ingress, and tracker fanout are deferred until *after* successful local commit. Addresses a same-class atomicity bug for external state that the initial draft missed.
  - File/line evidence from the cross-review is cited in the References section.
- **Second-round cross-review integration (2026-05-28, P0/P1/P2 findings)**: Five additional concerns surfaced after the first integration round:
  - **P0 — Coordination workspace ownership** (FR-023, FR-024, FR-025, C-011): the spec now names a `BookkeepingTransaction` service and a coordination worktree (`.worktrees/<slug>-<mid8>-coord/`) as the concrete mechanism by which lane-resident agents write to the coordination branch without `git checkout`-ing it. The earlier draft assumed this was self-evident; the reviewer was right that it isn't.
  - **P0 — Lane code preservation in merge topology** (FR-008 rewritten): the spec now describes a two-stage merge (per-WP lane → coordination integration; then coordination → target at mission close). The earlier draft's "merge coordination → target, never lane → target" wording would have dropped lane code on the floor.
  - **P1 — Policy gate input is `destination_ref`** (FR-019, FR-020, C-012; Exception A rewritten with three sub-cases): the gate evaluates against the explicit branch the would-be tracking commit targets, never against process CWD or current HEAD. This is what makes running from any branch correct as long as the bookkeeping target is non-protected.
  - **P1 — Lock-held atomic window** (FR-026, C-013; FR-010 rewritten; Scenario C removed): the existing feature status lock is held across emit → materialize → commit → rollback. With the lock held, the surgical truncate is unconditionally safe; event-id-targeted removal is no longer a code path; the append-only invariant (C-004) is preserved without contradiction.
  - **P1 — Legacy missions get the same invariants** (FR-017 rewritten, FR-027, SC-11): pre-flight gate, transaction contract, lock, rollback, and outbound deferral apply uniformly to legacy and coordination-branch missions. Only `destination_ref` and the worktree topology differ.
  - **P2 — Schema field names** (FR-012, Primary Scenario step 2): `planning_base_branch` and `merge_target_branch` match the current WP template; no schema migration required.
- One known operational risk flagged in Assumptions #4: rebase conflicts on `status.events.jsonl` when two lanes emit between syncs. Stock `git rebase` may or may not be sufficient. This is deferred to `/spec-kitty.plan` for resolution; it is not a hard FR of this spec.
- Bulk-edit gate: not applicable (no cross-file rename).
- All items pass on first iteration. Ready for `/spec-kitty.plan`.
