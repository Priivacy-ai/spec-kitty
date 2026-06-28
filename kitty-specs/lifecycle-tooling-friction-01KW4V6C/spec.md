# Mission Specification: Mission-Lifecycle Tooling Friction

**Mission Branch**: `mission/lifecycle-tooling-friction`
**Created**: 2026-06-27
**Status**: Draft
**Mission ID**: `01KW4V6C...`
**Topology**: lanes (no coordination branch)
**Input**: Operator scope — the 7 tooling/DX gaps surfaced by the Doctrine Governance Fidelity retrospective (#2217–#2223).

## Summary

The spec-kitty mission lifecycle (specify → tasks → finalize → implement → accept →
retrospect) has accumulated authoring friction — CLI/doctrine/template/validator
surfaces that fight the author or have drifted out of agreement. This mission
reconciles them. A pre-planning adversarial squad (priti / alphonso / debbie /
paula, profile-loaded, live-repro'd against `upstream/main` `c44a4fa82`) ground-
truthed all 7 candidates and reshaped scope:

- **#2219 is already fixed upstream** (the `--mission` scope + non-persisting
  `read_topology()` landed via #2070/#1814 after the retrospective) → **verify-and-close**.
- **#2220 + #2221 are one defect** (the WP-authoring frontmatter contract has no
  single source of truth across doctrine-prose / template / validator) → **folded**
  into one lane gated by a golden round-trip test.
- **#2223 re-scoped**: the "row for every `#NNNN`" rule does **not** exist in
  `validate_issue_matrix` (it lives in the approve-gate spec-scan); the real value is
  wiring the existing rule-engine as a **finalize-tasks lint**, not relaxing a rule.
- **#2218 is the one hidden-depth item** (coordination-branch *lifecycle*, not a flag)
  and it **causally amplifies #2222** (more create-time non-coord missions → more
  lock-gate friction).

Six file-disjoint lanes → `lanes` topology.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A WP authored from the template validates first time (Priority: P1) 🎯 Lane A (#2220+#2221)

An author copies `task-prompt-template.md`, fills in repo-relative `owned_files`, and
runs `finalize-tasks` — it passes without "authoritative_surface is empty" or
"WP does not own any files under src/ or tests/".

**Why this priority**: This friction bit every WP authored in the prior mission; the
contract is split across three drifting encodings with no SSOT. Highest day-to-day value.

**Independent Test**: Render the software-dev `task-prompt-template.md`, fill placeholder
repo-relative paths, run it through `ownership/validation` + `finalize-tasks` → passes.
Seed an absolute path → fails consistently with the doctrine guidance (which now says relative).

**Acceptance Scenarios**:

1. **Given** the software-dev `task-prompt-template.md`, **When** its frontmatter is
   inspected, **Then** it declares `owned_files`, `authoritative_surface`,
   `execution_mode`, and `create_intent` (with guidance comments).
2. **Given** both `tasks/guidelines.md` copies, **When** read, **Then** they instruct
   **repo-root-relative** `owned_files` paths (matching the validator), not absolute.
3. **Given** a WP authored verbatim from the completed template with repo-relative
   placeholder paths, **When** `ownership` validation + `finalize-tasks` run, **Then**
   it passes first time (the SSOT round-trip ratchet).

---

### User Story 2 — Choose mission topology at creation (Priority: P2) 🎯 Lane B (#2218)

An operator creating a mission can choose its topology up front instead of always
getting a coordination branch and hand-flattening `meta.json`.

**Why this priority**: P2 — real friction (hand-edit was the only escape), but the honest
fix is the coordination-branch *lifecycle*, with the largest blast radius in this mission.

**Independent Test**: `spec-kitty specify <name> --topology single_branch --json` →
`meta.json` has `topology: single_branch` and **no** `coordination_branch`; a
`single_branch` (and `lanes`) mission then runs end-to-end through `implement` + `merge`.

**Acceptance Scenarios**:

1. **Given** `spec-kitty specify`, **When** `--topology <value>` is passed, **Then** it
   accepts exactly the canonical `MissionTopology` values `single_branch | lanes | coord
   | lanes_with_coord` and rejects others.
2. **Given** `--topology single_branch` (or `lanes`), **When** the mission is created,
   **Then** **no** coordination branch is minted and `topology` is set accordingly.
3. **Given** `--topology coord` (or `lanes_with_coord`, or the flag omitted), **When** the
   mission is created, **Then** behaviour is byte-identical to today (coord branch minted).
4. **Given** a create-time `single_branch` mission, **When** it goes through
   `implement WP##` and `merge`, **Then** it completes coherently (the coord-or-legacy
   fallbacks handle the create-time non-coord shape) — proven end-to-end.

---

### User Story 3 — Back-to-back claims don't block on the vcs-lock self-write (Priority: P2) 🎯 Lane C (#2222)

An orchestrator claiming two dependency-free root WPs back-to-back with auto-commit
disabled isn't blocked by the first claim's own uncommitted vcs-lock write.

**Why this priority**: P2 — bites the parallel-claim loop on non-coord missions (and #2218
makes those more common). The lock is in-process VCS-type state, never the concurrency guard.

**Independent Test**: In a scratch mission with `auto_commit=False`, claim two
dependency-free roots in sequence; assert the second does not `Exit(1)` on the first's
vcs-lock write.

**Acceptance Scenarios**:

1. **Given** `auto_commit=False`, **When** a second WP claim runs after a first that wrote
   the vcs-lock to `meta.json`, **Then** the claim is not blocked by that self-write.
2. **Given** the vcs-lock write, **When** the dirty-tree guard evaluates the working tree,
   **Then** the lock-only meta change is excluded from "uncommitted planning artifacts"
   (the lock was never the concurrency guard — no race is introduced).
3. **Given** `auto_commit=True` (default), **When** claims run, **Then** behaviour is unchanged.

---

### User Story 4 — Retrospectives capture tracer learnings (Priority: P2) 🎯 Lane D (#2217)

A mission's `retrospect create`/synthesize reflects the rich learnings authors recorded in
`traces/*.md`, not just the event stream.

**Why this priority**: P2 — rich missions systematically under-capture; the generator's input
contract omits the tracer surface.

**Independent Test**: A mission with `traces/tooling-friction.md` content produces ≥1
finding/proposal sourced from the tracer; a no-domain-entity mission does not get a false
"missing data-model.md" gap.

**Acceptance Scenarios**:

1. **Given** a mission with `kitty-specs/<slug>/traces/*.md`, **When** `retrospect create`
   runs, **Then** the record includes findings sourced from the tracers (via the existing
   ingestor seam, extended — not a generator rewrite).
2. **Given** a governance/wiring mission with no `data-model.md`, **When** the record is
   generated, **Then** the absent data-model is treated as not-applicable, not a gap.

---

### User Story 5 — Issue-matrix problems surface at tasks time (Priority: P3) 🎯 Lane E (#2223)

An author runs `finalize-tasks` and gets an advisory lint of `issue-matrix.md` (one-table,
closed-verdict, deferred-needs-handle, completeness) so nothing surprises at the approve gate.

**Why this priority**: P3 — correct-but-late: the guard already emits structured errors, only
at approve time.

**Independent Test**: A malformed matrix (two tables / open verdict / deferred without a
handle) is flagged by `finalize-tasks` (advisory) using the same rule engine the approve gate uses.

**Acceptance Scenarios**:

1. **Given** `finalize-tasks`, **When** an `issue-matrix.md` violates a matrix rule, **Then**
   a non-blocking lint warning naming the rule is emitted at tasks time.
2. **Given** the lint and the approve gate, **When** both run, **Then** they use **one**
   shared rule engine (no duplicated/divergent rule set).

---

### User Story 6 — Mission-scoped backfill-topology is proven safe (Priority: P3) 🎯 Lane F (#2219)

`spec-kitty migrate backfill-topology --mission X` touches only mission X.

**Why this priority**: P3 — already fixed upstream; this lane verifies + locks it with a
regression test (the 203-file blast-radius guard) and closes the ticket.

**Independent Test**: Run `backfill-topology --mission X` in a repo with sibling missions;
assert only X's `meta.json` changed.

**Acceptance Scenarios**:

1. **Given** `migrate backfill-topology --mission X`, **When** it runs in a multi-mission
   repo, **Then** only `kitty-specs/X/meta.json` is touched; siblings are byte-identical.
2. **Given** the upstream fix, **When** verified, **Then** #2219 is closed as
   `verified-already-fixed` with a commit-pin and the regression test in place.

### Edge Cases

- **#2218 create-time `lanes`**: `lanes.json` only materializes at `finalize-tasks`, so a
  create-time `--topology lanes` sets the `topology` field to `lanes` with no coord branch
  (the pre-finalize state the operator currently hand-edits). `read_topology` must return `lanes`.
- **#2218 backward-compat**: omitting `--topology` must keep today's coord default exactly.
- **#2222 auto_commit=True**: no behaviour change (only the `False` path is affected).
- **#2220**: BOTH doctrine copies (`actions/.../tasks/guidelines.md` and
  `mission-steps/.../tasks/guidelines.md`) must be aligned, or they re-diverge.
- **#2217**: malformed/empty tracer files must not crash the generator (best-effort ingest).
- **#2223**: the tasks-time lint is **advisory** (never blocks finalize); only the approve gate blocks.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Doctrine guidance → repo-relative owned_files (both copies) | As an author, I want the tasks doctrine to instruct the path form the validator accepts. | High | Open |
| FR-002 | Complete task-prompt-template frontmatter | As an author, I want the template to declare `owned_files`/`authoritative_surface`/`execution_mode`/`create_intent` so authored WPs are self-describing. | High | Open |
| FR-003 | SSOT round-trip ratchet test | As a maintainer, I want a golden test proving a template-authored WP validates + finalizes first time, so the three encodings can't re-drift. | High | Open |
| FR-004 | `specify --topology <enum>` | As an operator, I want to choose topology at creation using the 4 canonical `MissionTopology` values; coord-branch minted only for coord/lanes_with_coord. | High | Open |
| FR-005 | Create-time non-coord mission works end-to-end | As an operator, I want a create-time `single_branch`/`lanes` mission to complete through implement + merge. | High | Open |
| FR-006 | vcs-lock self-write doesn't block claims | As an orchestrator, I want back-to-back claims (auto_commit=False) not blocked by the first claim's vcs-lock meta write. | High | Open |
| FR-007 | Retrospect ingests tracer files | As a facilitator, I want `retrospect` to source findings/proposals from `traces/*.md`. | Medium | Open |
| FR-008 | data-model gap is conditional | As a facilitator, I want absent `data-model.md` treated as N/A for no-entity missions, not a false gap. | Medium | Open |
| FR-009 | Issue-matrix lint at finalize-tasks | As an author, I want an advisory matrix lint at tasks time reusing the approve-gate rule engine. | Medium | Open |
| FR-010 | Mission-scoped backfill regression test + close | As a maintainer, I want `backfill-topology --mission X` proven to touch only X, and #2219 closed. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No regression on default paths | `--topology` omitted → coord default byte-identical; `auto_commit=True` claim path unchanged; existing missions unaffected. | Reliability | High | Open |
| NFR-002 | Reuse authorities, don't fork | #2217 extends the existing ingestor seam; #2223 = one rule engine / two call-sites; #2219 is not re-implemented. | Maintainability | High | Open |
| NFR-003 | New-code quality | ruff + mypy clean (no `# type: ignore`), complexity ≤ 15, a focused test per new branch/helper; diff-coverage ≥ 90% on critical paths. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Lanes topology, no coord | Mission runs `topology: lanes`, no coordination branch; six file-disjoint lanes. | Technical | High | Open |
| C-002 | Canonical topology vocabulary | FR-004's `--topology` accepts ONLY `single_branch \| lanes \| coord \| lanes_with_coord` (the `MissionTopology` enum). "flat" is NOT a canonical name. | Technical | High | Open |
| C-003 | #2222 fix = stop gating | Fix #2222 by excluding the vcs-lock self-write from the dirty-tree guard (operator decision), NOT by auto-committing the lock. | Technical | High | Open |
| C-004 | Code is the path authority | #2220: align the doctrine TEXT to repo-relative; do not patch the validator to accept absolute. Fix BOTH doctrine copies. | Technical | High | Open |
| C-005 | B↔C causal sequencing | #2218 mints more non-coord missions where #2222 bites; land Lane C (#2222) with/before Lane B (#2218), or prove B's flat-mission path includes the C fix. | Technical | Medium | Open |
| C-006 | Red-first + reuse-don't-rebuild | Each lane drives its pre-existing surface red-first; #2217/#2223/#2219 reuse existing seams/engines (per the squad). | Process | High | Open |
| C-007 | Realistic fixtures | Scratch missions/packs use real-format ids and shapes. | Process | Medium | Open |

## Issue Matrix

| Issue | Title | Priority | Parent | Lane | Verdict |
|-------|-------|----------|--------|------|---------|
| #2217 | Retrospect generator ignores tracer files | P2 | #1138 | D | in-mission |
| #2218 | `specify` forces topology:coord (no flag) | P3 | #1619 | B | in-mission |
| #2219 | `backfill-topology` repo-global | P2 | #1619 | F | verify-and-close (already fixed upstream #2070/#1814) |
| #2220 | `owned_files` absolute-vs-relative mismatch | P3 | #1676 | A | in-mission (folded with #2221) |
| #2221 | task-prompt-template missing frontmatter | P3 | #1676 | A | in-mission (folded with #2220) |
| #2222 | parallel-claim vcs-lock friction | P3 | #1795 | C | in-mission |
| #2223 | issue-matrix guard strict/under-documented | P3 | #2017 | E | in-mission (re-scoped: lint at tasks-time, not rule relaxation) |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A WP authored verbatim from the completed template validates + finalizes first time; an absolute-path entry fails consistently (FR-001/002/003).
- **SC-002**: `specify --topology single_branch` yields `topology: single_branch` + no coord branch; that mission completes implement + merge; omitting the flag is byte-identical to today (FR-004/005, NFR-001).
- **SC-003**: Two back-to-back `auto_commit=False` claims succeed; `auto_commit=True` unchanged (FR-006, NFR-001).
- **SC-004**: A mission with tracer content yields tracer-sourced retrospective findings; no false data-model gap for no-entity missions (FR-007/008).
- **SC-005**: `finalize-tasks` advisory-lints a malformed issue-matrix using the same engine as the approve gate (FR-009, NFR-002).
- **SC-006**: `backfill-topology --mission X` touches only X (regression test); #2219 closed `verified-already-fixed` (FR-010).
