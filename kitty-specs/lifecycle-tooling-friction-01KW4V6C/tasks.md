---
description: "Work package task list for Mission-Lifecycle Tooling Friction"
---

# Work Packages: Mission-Lifecycle Tooling Friction

**Inputs**: Design documents from `kitty-specs/lifecycle-tooling-friction-01KW4V6C/`
**Prerequisites**: plan.md (6 ICs), spec.md (10 FRs / 3 NFRs / 7 constraints), research.md, issue-matrix.md
**Topology**: lanes (no coord). Six file-disjoint lanes; WP03 sequenced after WP02 (C-005).

**Tests**: Red-first per WP through the pre-existing surface (C-006). Reuse existing authorities — do NOT fork (NFR-002). Every new branch/helper carries a focused test (NFR-003).

**Organization**: Subtasks (`Txxx`) roll up into WPs; each WP owns a disjoint file set (DIRECTIVE_024).

---

## Work Package WP01: WP-authoring contract SSOT (Priority: P1) 🎯 Lane A (#2220+#2221)

**Goal**: Make the WP-frontmatter contract agree across doctrine-prose, template, and the validator; guard it with a golden round-trip test.
**Independent Test**: A WP authored verbatim from the completed `task-prompt-template.md` with repo-relative placeholder paths passes `ownership` validation + `finalize-tasks` first time; an absolute-path entry fails consistently.
**Prompt**: `/tasks/WP01-wp-authoring-contract.md`
**Requirement Refs**: FR-001, FR-002, FR-003, C-004, C-006, NFR-003

### Included Subtasks
- [x] T001 Align BOTH `tasks/guidelines.md` copies (`actions/.../tasks/` + `mission-steps/.../tasks/`) to instruct **repo-root-relative** `owned_files` (remove "absolute").
- [x] T002 Complete `task-prompt-template.md` frontmatter: add `owned_files`, `authoritative_surface`, `execution_mode`, `create_intent` (with guidance comments).
- [x] T003 Golden round-trip test: template-authored WP (repo-relative paths) validates + finalizes first time; absolute path fails.

### Dependencies
- None.

### Risks & Mitigations
- Two doctrine copies must stay aligned (fix both). Round-trip test must drive the REAL validator+finalize path (not template-exists), per paula.

---

## Work Package WP02: vcs-lock claim-friction fix (Priority: P2) 🎯 Lane C (#2222)

**Goal**: Back-to-back claims under `auto_commit=False` aren't blocked by the first claim's vcs-lock self-write (exclude it from the dirty-tree guard — C-003).
**Independent Test**: Two back-to-back dependency-free root claims with `auto_commit=False`; the second does not `Exit(1)` on the first's vcs-lock write. `auto_commit=True` unchanged.
**Prompt**: `/tasks/WP02-vcs-lock-claim-fix.md`
**Requirement Refs**: FR-006, C-003, NFR-001, C-006

### Included Subtasks
- [x] T004 RED test through `spec-kitty agent action implement`: two `auto_commit=False` claims; assert the second is not blocked by the vcs-lock self-write.
- [x] T005 Exclude the vcs-lock-only `meta.json` change from `_ensure_planning_artifacts_committed_git` (the dirty-tree guard) in `implement.py`.
- [x] T006 Regression: `auto_commit=True` claim path byte-identical; + required negative guard: a `meta.json` dirtied with a NON-lock field STILL `Exit(1)`s (proves the exclusion is lock-field-only).

### Dependencies
- None. (Land with/before WP03 per C-005.)

### Risks & Mitigations
- The lock is VCS-type state, not the concurrency mutex — exclusion opens no race. Keep `auto_commit=True` unchanged.

---

## Work Package WP03: Create-time topology choice (Priority: P2) 🎯 Lane B (#2218)

**Goal**: `spec-kitty specify --topology <enum>` chooses topology at creation (canonical `MissionTopology` values); coord-branch minting conditional; proven end-to-end for a non-coord mission.
**Independent Test**: `specify --topology single_branch --json` → `topology: single_branch`, no `coordination_branch`; invalid values rejected; the mission completes `implement` + `merge`; omitting the flag is byte-identical to today.
**Prompt**: `/tasks/WP03-create-time-topology.md`
**Requirement Refs**: FR-004, FR-005, C-002, NFR-001, C-005, C-006

### Included Subtasks
- [x] T007 RED test through `spec-kitty specify --json`: `--topology single_branch` → `topology: single_branch` + no coord branch; reject non-enum values.
- [x] T008 Add `--topology` (Enum of the 4 `MissionTopology` values) to `specify`; thread CLI→agent→core; make `ensure_coordination_branch` minting conditional in `mission_creation.py`; default `coord`.
- [x] T009 End-to-end non-coord proof: a create-time `single_branch` mission with TWO dependency-free WPs claimed back-to-back under `auto_commit=False` (the load-bearing exercise of WP02's vcs-lock fix), then `merge`; assert FOUR observable post-merge facts: (a) the WP's file content is present on the merge-target branch, (b) the status event log reaches `done`/merged via the lane reader, (c) `read_topology == single_branch` after the full loop, (d) no `coordination_branch` key ever written to meta.json.
- [x] T010 Regression: omitting `--topology` → coord default byte-identical (meta + coord branch).

### Dependencies
- Depends on WP02 (C-005, load-bearing — T009 claims TWO dependency-free WPs back-to-back under `auto_commit=False`; without WP02's vcs-lock-guard fix the second claim `Exit(1)`s, so the dependency is a real prerequisite, not a sequencing preference).

### Risks & Mitigations
- HIDDEN-DEPTH: the create-time non-coord shape is new to the coord-or-legacy fallbacks across implement/merge — T009 e2e proof is mandatory. Classify via the existing `classify_topology` SSOT.

---

## Work Package WP04: Retrospect tracer ingestion (Priority: P2) 🎯 Lane D (#2217)

**Goal**: `retrospect` sources findings/proposals from `traces/*.md`; absent `data-model.md` is N/A for no-entity missions.
**Independent Test**: A mission with `traces/tooling-friction.md` content → ≥1 tracer-sourced finding; a no-entity mission → no false data-model gap.
**Prompt**: `/tasks/WP04-retrospect-traces.md`
**Requirement Refs**: FR-007, FR-008, NFR-002, C-006

### Included Subtasks
- [x] T011 RED test through `spec-kitty retrospect create`: tracer content yields ≥1 tracer-sourced finding; no-entity mission has no data-model gap.
- [x] T012 Add a `_load_traces` reader to the existing ingestor seam (`generator.py` `_build_ingestor_findings`); make the data-model gap conditional on domain entities. Best-effort (malformed tracer must not crash).

### Dependencies
- None.

### Risks & Mitigations
- Extend the seam, do not fork the generator (NFR-002). Best-effort ingest.

---

## Work Package WP05: Issue-matrix finalize-tasks lint (Priority: P3) 🎯 Lane E (#2223)

**Goal**: An advisory issue-matrix lint at `finalize-tasks` reusing the approve-gate rule engine (one engine, two callers).
**Independent Test**: A malformed matrix (two tables / open verdict / deferred without a handle) is flagged by `finalize-tasks` (advisory, non-blocking) using the same engine the approve gate uses.
**Prompt**: `/tasks/WP05-issue-matrix-lint.md`
**Requirement Refs**: FR-009, NFR-002, C-006

### Included Subtasks
- [x] T013 RED test: a malformed `issue-matrix.md` is advisory-flagged at `finalize-tasks`; a valid one is silent.
- [x] T014 Expose the `validate_issue_matrix` rule engine (+ completeness scan) from `review/_issue_matrix.py`; add the advisory call-site in `mission_finalize.py` (never blocks finalize).

### Dependencies
- None.

### Risks & Mitigations
- One rule engine, two callers — do NOT reimplement rules (drift). Advisory only.

---

## Work Package WP06: Backfill-topology verify + regression + close (Priority: P3) 🎯 Lane F (#2219)

**Goal**: Prove `migrate backfill-topology --mission X` touches only X; close #2219 `verified-already-fixed`.
**Independent Test**: In a multi-mission repo, `backfill-topology --mission X` changes only `kitty-specs/X/meta.json`; siblings byte-identical.
**Prompt**: `/tasks/WP06-backfill-scope-regression.md`
**Requirement Refs**: FR-010, C-006, NFR-002

### Included Subtasks
- [x] T015 Regression test: `backfill-topology --mission X` in a multi-mission repo touches only X (the 203-file blast-radius guard).
- [x] T016 Verify the upstream fix (`--mission` scope + `read_topology`) is wired into the planning/inspection paths; record #2219 as `verified-already-fixed` (no production change).

### Dependencies
- None.

### Risks & Mitigations
- Do NOT re-implement (fix already upstream #2070/#1814). Verify + guard only.

---

## Dependency & Execution Summary

- **Parallel**: WP01, WP02, WP04, WP05, WP06 (file-disjoint).
- **Sequenced**: WP02 → WP03 (C-005).
- **MVP**: WP01 (the highest-friction authoring fix) + WP02/WP03 (the topology/lock pair).

## Requirements Coverage Summary

| Requirement | Covered By |
|-------------|-----------|
| FR-001, FR-002, FR-003 | WP01 |
| FR-004, FR-005 | WP03 |
| FR-006 | WP02 |
| FR-007, FR-008 | WP04 |
| FR-009 | WP05 |
| FR-010 | WP06 |
| NFR-001 | WP02, WP03 |
| NFR-002 | WP04, WP05, WP06 |
| NFR-003 | all WPs |
| C-002 | WP03 · C-003 WP02 · C-004 WP01 · C-005 WP02→WP03 · C-006 all |

## Subtask Index

| Subtask | WP | Parallel? |
|---------|----|-----------|
| T001–T003 | WP01 | within-WP |
| T004–T006 | WP02 | ∥ |
| T007–T010 | WP03 | after WP02 |
| T011–T012 | WP04 | ∥ |
| T013–T014 | WP05 | ∥ |
| T015–T016 | WP06 | ∥ |
