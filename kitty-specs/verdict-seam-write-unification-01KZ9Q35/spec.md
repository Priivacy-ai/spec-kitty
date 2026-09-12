# Mission Specification: Verdict-Seam Write-Side Unification

**Mission Branch**: `feat/verdict-seam-write-unification`
**Created**: 2026-08-05
**Status**: Draft (revised after post-spec adversarial squad — 4 lenses)
**Input**: Follow-up to PR #3211 / epic #3044 — complete the review-cycle verdict-seam write-side
unification. Full pre-spec research (five profile-loaded streams, `file:line`-anchored):
`research/pre-spec-research.md`. Revised to fold post-spec squad findings (architecture,
requirement-quality, scope/decomposition, single-authority-integrity).

## Context

PR #3211 landed an **event-authoritative dual-store with declared precedence, not single
authority**. The *read* side of a review verdict follows `MissionArtifactKind.REVIEW_CYCLE` to
the coordination (COORD) partition; the *write* seam is still pinned to the `WORK_PACKAGE_TASK`
/ primary (PRIMARY) partition (`src/specify_cli/review/cycle.py::_review_cycle_wp_dir`). As a
result ~16 frontmatter readers survive as a fallback, and the two ends of a single review
decision can consult different surfaces — the defect class (#2275) that spawned epic #3044.

This mission flips the write seam to `REVIEW_CYCLE`, collapses the frontmatter-fallback
dual-store to one event authority (the event-sourced reducer snapshot), extends single-authority
to the dashboard readers, and greens the carry-red gate-artifact and concurrency defects that are
symptoms of the split. Single-authority is made **structural**, not disciplinary: the written
artifact carries no field re-readable as a verdict, the enforcing checks are derived ratchets,
and a **verdict-provenance backfill** guarantees the event authority is populated for every
existing mission before any frontmatter reader is deleted.

### ID convention (disambiguation)

This mission's whole point is authority disambiguation, so its own IDs are unambiguous. Local
IDs are `FR-0NN` / `NFR-0NN` / `C-0NN` / `SC-0NN`. Where a criterion **inherits** from the
predecessor mission `review-cycle-verdict-seam-rebuild-01KZ2W7W`, the inherited ID is written
with a `p#3044/` prefix (e.g. `p#3044/SC-006`). A bare `SC-00N` always means *this* spec.

### Scope ledger

- **In scope (authorized):** the write-seam flip + authority collapse (operator decisions
  D1/D2/D3), the reviews slice of epic #2093, #3216, #3217, #2804 — and, folded after the
  squad: **#2404** (accept-writes-to-COORD, the write-side de-husk that makes #2804 *stay*
  fixed) and a **verdict-provenance backfill** (the safety precondition for deleting the
  frontmatter readers). Operator-added: **#3219** (extract the canonical
  `flatten_coordination_metadata` primitive — the same canonical-source-unification pattern on a
  sibling field-set; the residual refactor deferred from PR #3218, the #3086 hotfix). #3219
  assumes PR #3218 has landed on the base (it converges the executor call site #3218 adds).
- **Out of scope:** #3086 (proven independent — handed to a parallel session, research §12),
  #2782 (sync). The full rest of epic #2093's WP-metadata catalogue
  (`owned_files`/`dependencies`/`execution_mode`/`authoritative_surface`/`create_intent`) stays
  with #2093/#2400 — only the *reviews* slice is claimed here.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One authority for the current verdict (Priority: P1)

Every component that answers "is this work package approved?" reads the same answer from the
event-sourced reducer snapshot — never by parsing a `review-cycle-N.md` frontmatter. The
approval gate, the merge gate, the kanban/dashboard board, the status display, and fix-mode all
agree, because they all consult one authority.

**Why this priority**: This is the single-authority guarantee the epic exists to deliver. Today
a genuine approval and a stale rejection can be read from different surfaces, letting a rejected
WP be approved (a safety-critical fail-open).

**Independent Test**: Construct a WP whose reducer snapshot verdict disagrees with its
`review-cycle-N.md` frontmatter; assert every reader (gate, board, fix-mode) reports the
snapshot verdict and none reports the frontmatter verdict.

**Acceptance Scenarios**:

1. **Given** a WP whose latest recorded verdict is `rejected` in the event log, **When** an
   approval-lane `move-task` is attempted, **Then** the approval guard refuses — regardless of
   what any on-disk `review-cycle-N.md` frontmatter says or which partition it lives on.
2. **Given** a WP whose reducer snapshot says `approved` but a stray frontmatter file says
   `rejected`, **When** the dashboard/kanban board renders, **Then** the board shows the
   snapshot verdict (approved), not the frontmatter verdict.
3. **Given** a damaged/unreadable verdict record, **When** a safety-gate reader resolves the
   verdict, **Then** it fails closed (refuses or surfaces "damaged"), never fails open to
   "approved" and never crashes uncaught.

---

### User Story 2 - The verdict lands where every reader looks (Priority: P1)

When a reviewer or the arbiter records a verdict, it is written to the one directory that every
read, write, gate, display, and dashboard path resolves — the COORD surface under a coordination
topology, PRIMARY under `SINGLE_BRANCH`/`LANES`. No consumer resolves a review-cycle path from a
caller-supplied directory, and the write seam and the safety-critical verdict reader change
partition together within one merge — with the safety core (write-default + safety verdict reader
+ approval-write probe + cycle-number allocator) in a single commit.

**Why this priority**: A partial flip of the *safety core* (write moves, the safety reader lags —
in either direction) opens a fail-open window on the approval guard; the research proves no safe
partial order exists for that core. The remaining flip-wave consumers are correctness (fix-mode,
collision) concerns that must land in the same PR but need not share the safety core's commit.

**Independent Test**: Under a materialized coordination topology, record a verdict and assert the
write, the safety verdict reader, the approval probe, the allocator, the pointer resolver, and
the fix-mode sites all resolve the same COORD directory; assert an AST invariant that no code
path resolves the write dir at a `kind` different from the safety-critical reader.

**Acceptance Scenarios**:

1. **Given** a materialized coordination topology, **When** a review-cycle verdict is recorded,
   **Then** the artifact's physical directory and every consumer's resolved directory are the
   same COORD directory.
2. **Given** a `SINGLE_BRANCH` or `LANES` topology (no coordination surface), **When** a verdict
   is recorded, **Then** the same one directory is PRIMARY and every consumer resolves it.
3. **Given** a mission whose coordination branch was deleted at merge time, **When** the write /
   prose-locate seam resolves the directory, **Then** the exception-absorption fallback lands it
   on PRIMARY (backward-compat preserved), not an unhandled error.

---

### User Story 3 - Two concurrent verdicts never lose one (Priority: P1)

Two verdicts recorded at the same time from separate processes produce two durable records or one
explicit refusal — never a silently dropped verdict and never a spurious crash — and the
durability path holds no inter-process lock across a git subprocess.

**Why this priority**: The predecessor asserted a lost record today (`p#3044/SC-004`). The loss
is a symptom of verdict durability being a bespoke per-file git commit rather than an append to
the already-concurrency-safe event log.

**Independent Test**: Over ≥50 iterations at 2+ concurrent OS processes, drive two distinct
verdicts through the real reviewer entry point; assert each iteration ends with two durable
records or one explicit refusal, with a clean working tree.

**Acceptance Scenarios**:

1. **Given** two concurrent processes each recording a distinct verdict for the same mission,
   **When** both complete, **Then** both verdicts are durably recorded in the event authority
   (no lost record) or one is explicitly refused with a diagnostic.
2. **Given** the durability path, **When** it records a verdict, **Then** it never holds an
   inter-process lock across a `git` subprocess invocation, and it makes exactly one authoritative
   durability call (the event append); the best-effort `.md` render commit may fail without
   erroring.

---

### User Story 4 - Merge preserves the accepted gate artifacts (Priority: P1)

A completed mission's filled `acceptance-matrix.json` and `issue-matrix.json` (terminal
verdicts, evidence) survive `spec-kitty merge` — the merged branch carries the accepted record,
not an empty placeholder — because those artifacts are authored on **one** write surface (COORD),
not two.

**Why this priority**: #2804 is a P0 that silently destroys the audit trail an operator needs at
PR time. It is a symptom of the same coord/PRIMARY write-surface split, on the sibling matrix
artifacts. Merely changing which copy wins at merge (driver registration) is timing-dependent;
removing the second write surface (accept→COORD, #2404) removes the divergence at the source.

**Independent Test**: Green the existing red-first pin
`tests/regression/test_issue_2804_merge_resets_gate_artifacts.py`: author a filled acceptance +
issue matrix, run the real merge, assert the filled verdicts/evidence survive; plus a write-side
check that no code path authors a PRIMARY-partition acceptance-matrix under a coordination
topology.

**Acceptance Scenarios**:

1. **Given** a mission with a filled `acceptance-matrix.json` (overall `pass`) and a terminal
   `issue-matrix.json`, **When** `spec-kitty merge` runs, **Then** the merged branch retains the
   filled verdicts and evidence — no placeholder reset.
2. **Given** a coordination topology, **When** `accept` fills the acceptance-matrix, **Then** it
   is written to the COORD surface only (no PRIMARY husk), so no add/add divergence exists for
   the merge to mis-resolve; the row-aware driver-registration guarantee is defense-in-depth.

---

### User Story 5 - The census check cannot be fooled (Priority: P2)

The architectural verdict-seam census fails CI when any new writer, resolver, or reader is
introduced — including a record constructed through a helper or a `.from_dict` classmethod, not
only a direct constructor call — and this hardening lands **before** the collapse relies on the
census to prove every reader was retired.

**Why this priority**: #3217 — the SC-008 guarantee currently holds only for members matching a
narrow AST predicate; a helper-wrapped reader can be added (or *missed during retirement*)
without tripping the ratchet.

**Independent Test**: Add a synthetic `.from_dict`-constructed reader and assert the census
derivation classifies it; assert an event-authority `.from_dict` deserializer stays excluded.

**Acceptance Scenarios**:

1. **Given** a new function that constructs a review record via `ReviewOverride.from_dict(...)`,
   **When** the census check runs, **Then** it classifies the function and fails on the
   uncounted member.
2. **Given** an event-authority deserializer the census deliberately excludes, **When** the
   broadened predicate runs, **Then** it stays excluded via a named reason (no over-match).

---

### User Story 6 - No historical verdict is stranded by the collapse (Priority: P1)

A work package whose terminal rejection was recorded before the event-authority era — only in
`review-cycle-N.md` frontmatter, never as a `review_result` event — still refuses approval after
the frontmatter readers are deleted, because its verdict was backfilled into the event log first.

**Why this priority**: The event log carries the current verdict only via the post-#3211 render
path; nothing backfills historical `.md` verdicts. Since #3211 merged 2026-08-05, essentially
every existing mission is in this cohort. Deleting the frontmatter readers without a backfill
turns every historical `.md`-only rejection into a silent fail-open — the exact defect the epic
exists to close.

**Independent Test**: Seed a mission whose only rejection record is a pre-event `.md`; run the
backfill; delete the readers; assert the approval guard still refuses.

**Acceptance Scenarios**:

1. **Given** a mission whose terminal verdict exists only as `review-cycle-N.md` frontmatter with
   no corresponding event `review_result` slot, **When** the verdict-provenance backfill runs,
   **Then** the verdict is durably present in `status.events.jsonl` (idempotently — a re-run adds
   nothing).
2. **Given** the pre-flip gate, **When** any WP still has a terminal `.md` verdict and no event
   `review_result` slot, **Then** the gate reports it and the reader-deletion step is blocked
   until zero such findings remain.

### Edge Cases

- A reviewer re-reports a recurring defect with byte-identical prose: must remain admissible (the
  frontmatter artifact retains its prose role; only its *verdict* authority is retired, and the
  written `.md` no longer carries an authoritative verdict field).
- A verdict record carrying a non-`{approved, rejected}` value (`arbiter_override`,
  `approved_after_orchestrator_fix`): the single-sourced vocabulary bridge maps it
  deterministically to `{approved, changes_requested}`, never reclassifies it as damaged.
- Two divergent **best-effort** `.md` renders meet at merge: must **not** abort the squash (the
  `.md` is non-authoritative prose, so its merge driver retires or downgrades to non-aborting).
- A merge run with `--delete-branch --no-remove-worktree`: out of scope here (that path is the
  #3086 parallel-session fix), but must not regress.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Atomic flip — safety core in one commit, wave in one PR | As a maintainer, I want the safety core (write-default + safety verdict reader `resolve_review_verdict_facts` + approval-write probe + cycle-number allocator) flipped to `REVIEW_CYCLE` in **one commit**, and the remaining flip-wave consumers in the **same PR** (merge-atomicity), so no partial order can fail open on `_guard_rejected_verdict`. Enforced by an AST invariant: no code path resolves the write dir at a `kind` different from the safety-critical reader. Re-pins `test_analysis_report_rehome.py`. | High | Open |
| FR-002 | Single verdict authority | As a reviewer, I want every consumer to answer "is this WP approved?" from the event-sourced reducer snapshot (`event_sourced_review_result`), so a verdict has exactly one source of truth. | High | Open |
| FR-003 | Artifact verdict read-path retired; artifact carries no verdict field | As a maintainer, I want the `review-cycle-N.md` artifact to be **write-only prose** — written **without any field the census classifies as a verdict** (structural single-authority, not disciplinary) — retiring the `review/artifacts.py` verdict-parser family and both frontmatter verdict readers. The prose-locate / pointer read (`resolve_review_cycle_pointer`) and the `_guard_feedback_source_provenance` guard are each explicitly retired or re-expressed without a verdict read-back (design fork resolved in plan, not left open). | High | Open |
| FR-004 | All readers bound to the event authority as a derived ratchet | As an operator, I want every reader of a WP's review/verdict state — the gates **and** the dashboard/kanban board (`agent_utils/status.py::show_kanban_status`, `_get_wp_review_verdict`) and the **review/verdict fields of** the status display — bound to the reducer snapshot (reviews slice of epic #2093 only; the rest of #2093's catalogue stays out). Enforcement is a **derived ratchet**, not spot assertions: extend `test_2093_authority_invariant.py` by adding `agent_utils`/`review`/`post_merge` to `_READER_AUTHORITY_ROOTS`, adding a `review-cycle-*.md`-glob detector arm, and adding `verdict` to the tracked fields — with a synthetic-poison non-vacuity test — **or** re-point enforcement to the verdict-seam census (which already models glob-based verdict readers). | High | Open |
| FR-005 | Single-sourced, complete vocabulary bridge | As a maintainer, I want the artifact↔event verdict vocabulary bridge to be **one canonical surface** (a single function/const beside `status/models.py`) with a complete directional mapping of all inbound values `{approved, rejected, arbiter_override, approved_after_orchestrator_fix}` → `{approved, changes_requested}` (and the reverse for prose/render), **plus** an architectural guard forbidding any other module from spelling the `rejected`↔`changes_requested` equivalence inline (today it is inline in 9 modules). #3216's two frontmatter readers are **deleted**, not folded. | High | Open |
| FR-006 | Census retirements land with the change that makes them | As a maintainer, I want every census shrinkage to land in `verdict_seam_census.yaml` in the **same** change: the 5 resolver retire rows + 3 unrouted sites + 2 raw-join re-homes (with FR-001), the **reader-row shrinkage** from FR-002/004/005 deletions/repoints (with the collapse), and the merge-gate artifact-leg retirement (FR-013). The census check reds on shrinkage; the shared file forbids parallel lanes across census-touching WPs. | High | Open |
| FR-007 | Backward-compat fallback preserved; location gate mechanism concrete | As an operator upgrading a repository, I want the COORD→PRIMARY exception-absorption fallback preserved verbatim, its rationale re-scoped to the **surviving write / prose-locate seam** (no reader routes through `_review_cycle_wp_dir(kind=REVIEW_CYCLE)` after FR-003), and the pre-flip **location** gate stated concretely: parse `doctor review-cycle-reconcile --json` (an informational, exit-0 command) and assert zero `live_coord_pre_adr_primary_record` findings as a test artifact. | High | Open |
| FR-008 | SC-004 durability via the event log | As a maintainer, I want verdict durability routed to an append on `status.events.jsonl` via `emit_status_transition` (union-merge-driver protected), demoting the `review-cycle-N.md` commit to best-effort (warning, not hard error) and retiring the per-file retry/hard-error/orphan-cleanup machinery as the authoritative path. This lands **with or after** the backfill (FR-012) and reader-collapse so the event authority is populated before the `.md` write is demoted. | High | Open |
| FR-009 | COORD-authoritative gate artifacts, de-husked at the write side (#2804 + #2404) | As an operator, I want `spec-kitty merge` to preserve filled `acceptance-matrix.json` / `issue-matrix.json`: **no code path authors a PRIMARY-partition acceptance-matrix under a coordination topology** (single write surface at both finalize-scaffold and accept-fill, #2404), verified by a write-side check; the merge executor guarantees the row-aware drivers are registered/active before the squash (defense-in-depth); `issue-matrix.md` is retired; and the `.md`→`.json` driver seed drift is fixed. | High | Open |
| FR-010 | Census `.from_dict` blind-spot closed **before** the collapse (#3217) | As a maintainer, I want the census AST derivation to classify records constructed via `.from_dict`/factory helpers (and, ideally, key the reader predicate on "touches a `review-cycle-*.md` path by name" rather than a fixed verb list; concrete gap: `backfill_runtime_state.py::_runtime_repair_delta`), paired with named `_EXCLUDED_MODULE_REASONS` additions so event-authority deserializers stay excluded. This lands **before** FR-002/003/004 so the census can prove reader-retirement during the collapse. | High | Open |
| FR-011 | Stale docstring reconciled | As a contributor, I want the `cycle.py:70-77` disclosure corrected (the merge gate does **not** opt into `REVIEW_CYCLE`), as campsite doc-hygiene in the FR-001 commit. | Medium | Open |
| FR-016 | Arbiter root threaded (coord fail-path) | As a maintainer, I want `persist_arbiter_decision` to receive the caller-resolved `main_repo_root` (never self-infer `feature_dir.parent.parent`), so an arbiter override under a coordination topology resolves the correct COORD root and status-lock root. Red-first: an arbiter decision under a materialized coord topology lands on the resolved COORD root. | High | Open |
| FR-012 | Verdict-provenance backfill + provenance gate | As an operator, I want an idempotent migration that reduces every existing terminal `.md` verdict into `status.events.jsonl` (via `emit_status_transition`), and a pre-flip **provenance** gate — "any WP with a terminal `.md` verdict and no event `review_result` slot" — that **blocks the FR-003 reader deletion** until zero such findings remain, so no historical rejection is stranded. Red-first: a mission whose only rejection is a pre-event `.md` still refuses approval after the flip. | High | Open |
| FR-013 | Merge gate bound to the event authority (pure-event) | As a maintainer, I want `find_rejected_review_artifact_conflicts` bound to the event authority: `_artifact_dirs_for_wp` and the `_resolve_terminal_verdict_conflict` artifact-frontmatter leg are **retired** (census retirement rows), not repointed. Depends on FR-008/FR-012 (authority populated). | High | Open |
| FR-014 | Review-cycle merge driver relaxed under D3 | As a maintainer, I want the `spec-kitty-review-cycle` fail-closed conflict-marker driver to **retire or downgrade to non-aborting** now that the `.md` is non-authoritative unread prose, so two divergent best-effort renders do not abort an otherwise-clean squash. | Medium | Open |
| FR-015 | Canonical `flatten_coordination_metadata` primitive (#3219) | As a maintainer, I want the three-mutation coordination flatten (`del coordination_branch` + `pop topology` + `flattened=True`) extracted into one canonical `flatten_coordination_metadata(feature_dir)` in `mission_metadata.py` (single load→mutate→`write_meta(validate=False)`, importing the `topology`/`flattened` key constants from `backfill_topology.py`), with all three call sites (`merge/executor.py` #3218, `_coordination_doctor.py`, `mission_type.py::mission close --discard`) converged onto it — **correcting the `mission close --discard` partial-flatten latent bug** (it clears `coordination_branch` but never pops `topology`, so a discarded coord mission can still route through coordination and hit `CoordinationBranchDeleted`). Also verify the `--push` origin-divergence note from the #3218 landing review. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No lock across a git subprocess | The verdict-durability serialization introduced by FR-008 holds **zero** inter-process locks across any `git` subprocess invocation (carries `p#3044/NFR-006`; not applied retroactively to pre-existing holds). | Reliability | High | Open |
| NFR-002 | Census fails on any uncounted member | The census check fails when a new writer, resolver, or reader is introduced, including helper/`.from_dict`-constructed records; ≥1 synthetic-poison test and ≥1 real-data test exercise the extended predicate (`p#3044/SC-008`). | Maintainability | High | Open |
| NFR-003 | Zero new lint or type debt | `ruff` and `mypy --strict` report zero issues on every touched file, with zero new suppressions. | Maintainability | High | Open |
| NFR-004 | One authoritative durable-persistence call per verdict | Exactly **one** call to the authoritative durability seam (`emit_status_transition` for the verdict event) per recorded verdict; the best-effort `review-cycle-N.md` render commit is **excluded** from this count and MAY fail without erroring. | Reliability | Medium | Open |
| NFR-005 | Verdict recording stays responsive | Recording one verdict including durable persistence completes within the existing 2-second budget, measured by `tests/review/test_cycle.py`. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical sources only | Consolidation targets the existing canonical surface (the reducer snapshot for verdict authority, the owner resolver for directories, the existing drivers/primitives for merge, a single vocabulary-bridge surface). No improvised parallel mechanism; a missing canonical surface is filed upstream, not worked around. | Technical | High | Open |
| C-002 | Red-first through pre-existing entry points | Every bug is reproduced RED-FIRST through the real entry point. The predecessor's `p#3044/C-005` pin `test_issue_2804_merge_resets_gate_artifacts.py` already exists and is red — green it, do not rewrite it. New behaviour lands via a failing-first ATDD test before implementation. | Process | High | Open |
| C-003 | No renames (change_mode normal) | `meta.json` carries no `change_mode: bulk_edit`. No identifier/path/key rename lands in this mission; the seam is unified in place. | Process | High | Open |
| C-004 | Census reds on shrinkage | The census AST check reds on shrinkage as well as growth, so every retirement lands in `verdict_seam_census.yaml` in the same change that retires the code (FR-006). | Technical | High | Open |
| C-005 | No version prescription | The mission assigns no patch/version number; release sequencing is the operator's call. | Process | Medium | Open |
| C-006 | Bounded scope | Out of scope: #3086 (proven independent — parallel session, research §12) and #2782 (sync); neither is greened here. In scope by squad-confirmed addition: #2404 (as the #2804 write-side prerequisite) and the FR-012 backfill. Only the reviews slice of #2093 is claimed. | Process | High | Open |
| C-007 | Preserve backward-compat fallback | The COORD→PRIMARY exception-absorption fallback is preserved verbatim, its rationale re-scoped to the surviving **write / prose-locate** seam (the retired verdict read-path no longer exercises it). It is not removed by the collapse. | Technical | High | Open |
| C-008 | Ordering constraints are load-bearing | FR-010 (census `.from_dict`) lands **before** the collapse; FR-012 (backfill) + FR-008 (durability) land **before/with** the reader-collapse (FR-002/003/004/013); the shared `verdict_seam_census.yaml` **forbids parallel lanes** across the census-touching WPs. `/plan` and `/tasks` must encode these as hard WP dependencies. | Process | High | Open |

### Key Entities

- **Current verdict**: the authoritative answer to "is this WP approved?" — the event-sourced
  `ReviewResult` on the reducer snapshot (`event_sourced_review_result` / `ReviewResultLookup`).
  Vocabulary `{approved, changes_requested}`; bridged to the artifact vocabulary `{approved,
  rejected, arbiter_override, approved_after_orchestrator_fix}` via one canonical surface (FR-005).
- **Review-cycle artifact** (`review-cycle-N.md`): after this mission, a write-only prose record
  (reviewer body, affected files, repro command) carrying **no** field re-readable as a verdict.
- **Verdict-seam census** (`tests/architectural/verdict_seam_census.yaml` +
  `test_verdict_seam_census.py`): the all-`src/` AST-derived writer/resolver/reader enumeration;
  the SC-008 structural ratchet.
- **Verdict-provenance backfill**: an idempotent migration reducing every terminal `.md` verdict
  into `status.events.jsonl`, plus the pre-flip provenance gate that blocks reader deletion.
- **COORD-partition gate artifacts**: `acceptance-matrix.json`, `issue-matrix.json` — authored on
  one write surface (COORD) and reconciled COORD-authoritative at merge.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (write-side of `p#3044/SC-006`): every read, write, gate, display, and dashboard
  path resolves one identical review-cycle directory — COORD under a coordination topology,
  PRIMARY under `SINGLE_BRANCH`/`LANES` — verified by the US2 co-resolution test **and** an AST
  invariant that no consumer resolves a review-cycle path from a caller-supplied directory or at
  a divergent `kind`. Not by inspection.
- **SC-002** (generalizes `p#3044/SC-011` from gates to all readers): zero consumers — gates
  **and** the dashboard/board **and** the status display — answer "is this WP approved?" by
  parsing artifact frontmatter, enforced by the **derived ratchet** of FR-004 (expanded
  `test_2093_authority_invariant.py` roots/arms/fields with a poison test, and/or the
  verdict-seam census), not by spot assertions.
- **SC-003** (`p#3044/SC-004`): two concurrent distinct verdicts produce two durable records or
  one explicit refusal, over ≥50 iterations at 2+ concurrent processes, with no lost record and
  no spurious crash.
- **SC-004** (`p#3044/SC-012` preserved): zero readers in the census crash uncaught on a damaged
  verdict record, and zero safety-gate readers return "no verdict"/approve for one — verified by
  a **parametrized damaged-record test iterating the census safety-gate readers**, not by
  "preserved natively" reasoning.
- **SC-005** (#2804 + #2404): after `spec-kitty merge`, a filled `acceptance-matrix.json` and
  terminal `issue-matrix.json` retain their verdicts and evidence — no placeholder reset
  (greening the existing red-first pin) — **and** a write-side check confirms no PRIMARY-partition
  acceptance-matrix is authored under a coordination topology.
- **SC-006** (`p#3044/SC-008`): the census check fails when a new writer, resolver, or reader is
  introduced, including helper/`.from_dict`-constructed records; the existing 5 retire rows are
  discharged and the fixture matches the post-flip derived set exactly.
- **SC-007** (structural single-authority): the written `review-cycle-N.md` carries no field the
  census classifies as a verdict — verified by a check, so the file physically cannot be re-read
  as a verdict source.
- **SC-008** (no stranded history): a mission whose only rejection record is a pre-event `.md`
  still refuses approval after the flip, because the FR-012 backfill populated its event
  `review_result` slot and the provenance gate blocked reader deletion until it did.
- **SC-009** (#3219): the three coordination-flatten mutations (`del coordination_branch`, `pop
  topology`, `flattened=True`) execute through exactly one canonical primitive; zero call sites
  re-inline any of the three; a discarded coord mission has `topology` popped (no residual
  `CoordinationBranchDeleted` route). Verified by an architectural single-source check + a
  `mission close --discard` regression.
