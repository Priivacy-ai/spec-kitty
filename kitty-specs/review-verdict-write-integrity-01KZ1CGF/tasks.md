# Tasks: Review Verdict Write Integrity

**Input**: Design documents from `kitty-specs/review-verdict-write-integrity-01KZ1CGF/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/review-cycle-writer.md, quickstart.md

Per plan.md's Implementation Concern Map (as corrected by the post-plan adversarial squad), this
mission decomposes into **two independent, parallel-safe work packages** — no dependency between
them, confirmed by direct file-ownership analysis (zero touched-file overlap).

## Subtask Index

| ID | Description | WP | Parallel |
|----|---|---|---|
| T001 | Generalize `create_rejected_review_cycle` with a `verdict` parameter (default `"rejected"`) | WP01 | |
| T002 | Loosen `validate_review_artifact` to accept both `"approved"` and `"rejected"` | WP01 | [P] |
| T003 | Add feedback-source provenance guard (path-identity + content-identity) | WP01 | |
| T004 | Add a commit step to the writer via the existing `commit_artifact` port capability | WP01 | |
| T005 | Wire `move-task --to approved`/`--to done` to call the writer when the latest artifact is `rejected` | WP01 | |
| T006 | Extend `tests/review/test_cycle.py`: rewrite one pinned test (`test_new_cycle_body_never_duplicates_a_prior_cycle_file` — its committed assertions predate this mission's design and must be updated to `pytest.raises`, not merely satisfied as-is), confirm both pinned tests pass, add a path-only case, approved-verdict coverage, and commit-assertion coverage | WP01 | |
| T007 | Extend `tests/post_merge/test_review_artifact_consistency.py`: confirm merge gate clears after a real approval | WP01 | |
| T008 | Drive a `lanes_with_coord` fixture through reject→approve using the shipped WP01 writer | WP02 | |
| T009 | Assert `agent tasks status --json` reports correctly with zero changes to `agent_utils/status.py`; commit the regression test | WP02 | |
| T010 | **Contingent** — only if T009 fails: trace the actual residual mechanism and implement a minimal, targeted fix with its own regression test | WP02 | |

## Work Packages

### WP01 — Durable, provenance-guarded review-verdict writer

**Goal**: Generalize the existing rejected-verdict writer into a single verdict-aware writer that
also handles `approved`, guards against fabricated/wrapped feedback sources, and commits its own
output. Closes FR-001, FR-002, C-002 in full; closes #2275's residual gap, #2996(a), #2996(b), #990,
and #2697.

**Priority**: P1 (User Stories 1 and 2 — the mission's P0-rated core defect)

**Independent Test**: See spec.md User Story 1 (Acceptance Scenarios 1–4) and User Story 2 (Acceptance
Scenarios 1–3); quickstart.md's FR-001/FR-002 sections give exact commands.

**Included subtasks**: T001, T002, T003, T004, T005, T006, T007 (tracked via `spec-kitty agent tasks
mark-status` — reference rows above, not checkboxes)

**Implementation sketch**: Generalize the writer first (T001) since T002–T005 all depend on its new
signature existing; T002 (validator) and T003 (provenance guard) touch different functions in the same
module and can be done in either order once T001 lands; T004 (commit step) is additive to the same
writer; T005 (move-task wiring) is the consumer; T006/T007 close the loop with tests. This WP's own
internal subtasks are sequential/same-function by nature (see plan.md's note on why IC-01+IC-02 were
merged) — do not attempt to split T001–T007 across parallel lanes within this WP.

**Estimated prompt size**: ~450 lines

**Dependencies**: None

**Requirement refs**: FR-001, FR-002, C-002, NFR-001, NFR-002, NFR-003

---

### WP02 — Verify #2646 closes via WP01 alone; contingent fix

**Goal**: After WP01 lands, prove (not assume) that #2646's stale-verdict display defect is already
closed by the existence of a real approved-verdict writer — with **zero changes** to
`agent_utils/status.py`. Only if that verification fails does this WP scope a targeted fix. Closes
FR-003.

**Priority**: P3 (User Story 3 — demoted from the original P2 after a post-plan squad found the fix
this spec originally committed to was type-shape broken and the underlying issue may already be moot)

**Independent Test**: See spec.md User Story 3 (Acceptance Scenarios 1–3); quickstart.md's FR-003
section gives exact commands.

**Included subtasks**: T008, T009, T010 (T010 is contingent — see below)

**Implementation sketch**: Reuse the existing `tests/integration/coord_topology_fixture.py` fixture
(already used by a post-plan squad's own live reproduction) rather than building a new one. Drive it
through reject→approve using WP01's shipped writer, then assert on `agent tasks status --json`'s
output. **If the assertion passes on the first attempt with no `agent_utils/status.py` changes, T010
is a no-op — do not implement a fix that has nothing to fix.** Only if the stale-verdict warning still
fires does T010 activate: trace the actual observed mechanism (which may differ from anything
documented in this mission's research — do not reuse the retracted `resolve_snapshot_review` design)
and implement the smallest fix that closes it, with its own regression test.

**Estimated prompt size**: ~200 lines (smaller WP — verify-first work, not a designed build)

**Dependencies**: None declared (zero file overlap with WP01), though T008/T009 need WP01's writer to
exist to have something real to verify against — sequence WP02's *execution* after WP01 completes even
though no `dependencies:` gate is declared, per plan.md's finding that this is a soft ordering
preference, not a hard blocking dependency.

**Requirement refs**: FR-003, NFR-001
