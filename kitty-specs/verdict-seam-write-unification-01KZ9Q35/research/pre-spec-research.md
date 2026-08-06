# Pre-Spec Research — Review-Cycle Verdict-Seam Topology Unification

> Follow-up to PR #3211 (epic #3044). Read-only investigation across five profile-loaded
> research streams (paula-patterns, architect-alphonso ×2, debugger-debbie, reviewer-renata).
> Every claim below is anchored to `file:line` in the working tree at
> `/home/stijn/Documents/_code/SDD/fork/spec-kitty`. No product files were edited.
> Date: 2026-08-05.

---

## 0. Executive summary + the one decision the operator must make

PR #3211 landed an **event-authoritative dual-store with declared precedence, not single
authority**. The *read* side follows `MissionArtifactKind.REVIEW_CYCLE` → COORD partition;
the *write* seam is still pinned to `WORK_PACKAGE_TASK`/PRIMARY in
`src/specify_cli/review/cycle.py::_review_cycle_wp_dir` (its own docstring, lines 79–118, is
the deferred-follow-up charter for this mission). This mission flips the write seam to
`REVIEW_CYCLE`, collapses the frontmatter-fallback dual-store to a single event authority,
and greens the carry-red pins that were deliberately left red under the predecessor's C-005.

**Decision point (surfaced, not silently resolved):** the brief's binding premise — *"the
carry-red bugs are symptoms of the split; never patch them locally ahead of the
unification"* — **holds for SC-004, #2804, and WP07-fixture, but is falsified for #3086.**
#3086 is a merge-teardown omission with no causal dependence on the review-cycle seam
(differential-matrix proof, §7.3). Sequencing #3086 behind the unification leaves a live P0
crash open for the mission's entire duration. The operator must choose how #3086 is scoped
(see §11, Decision D1).

**Two additional falsifications of the brief's framing**, both material to the spec:
- The brief says `resolve_review_verdict_facts` "derives the SAME directory via a bare
  `wp_path.parent / wp_path.stem` join that is unconditionally PRIMARY-anchored." **Stale.**
  WP13 already routed it through `_review_cycle_wp_dir` — but at the *default*
  `WORK_PACKAGE_TASK` kind. The fail-open is **relocated, not open**: it flips from "bare
  join" to "routed-but-wrong-kind" (§4.C). The fix is a `kind=` flip, atomic with the write
  seam, not a re-route.
- The brief says #3216 readers "differ ONLY in failure polarity." **Incomplete.** They also
  differ in *verdict vocabulary* (§8.1). And under the collapse #3216 is not a dedup at all —
  it is an authority migration to `event_sourced_review_result` (§8.1).

---

## 1. The split, precisely located

| Layer | Where it resolves today | Anchor |
|---|---|---|
| **Write seam** (physical dir) | PRIMARY / `WORK_PACKAGE_TASK`, every topology | `review/cycle.py:52,702` (default kind), `_review_cycle_wp_dir` `:47-148` |
| **Commit target** (branch) | **already COORD** for coord topologies — per-file reclassification overrides the caller's kind | `coordination/commit_router.py::_group_files_by_partition:405-513`; pinned by `tests/coordination/test_analysis_report_rehome.py:234-255` |
| **Read seam** (verdict question) | `REVIEW_CYCLE` → COORD, with PRIMARY exception-absorption fallback | `review/cycle.py:127-145` |

The dual-store is: **allocate/read on PRIMARY, durably commit on COORD**. The artifact is
committed on the coord branch while a stale uncommitted working-tree copy lingers on PRIMARY —
the #2697 shape. The *only* thing the flip physically moves is the write location (§5.B);
the commit target is already correct.

## 2. Target invariant (already written by the predecessor; this mission completes the write side)

- **SC-006** (predecessor spec.md:291): *"every read, write, gate and display path resolves
  one identical directory … under a coordination topology that directory is on the COORD
  surface; under `SINGLE_BRANCH`/`LANES` it is PRIMARY. Zero consumers resolve a review-cycle
  path from a caller-supplied directory."*
- **SC-011** (predecessor spec.md:290): *"Zero consumers answer 'is this WP approved?' by
  parsing artifact frontmatter. The event's verdict is readable downstream of the reducer, and
  every gate consults it."*
- **SC-004** (spec.md:286): two concurrent distinct verdicts → two records or one explicit
  refusal, over ≥50 iterations at 2+ concurrent **processes**. "Asserted to lose one record
  today."
- The **C-005** carry-red pins already exist and are deliberately red:
  `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` (23 KB),
  `tests/regression/test_issue_3086_merge_delete_branch_flattens_coordination_metadata.py`.
  The predecessor spec forbade greening them there; this mission greens them.

## 3. Census baseline + the NFR-007/SC-008 check

`tests/architectural/verdict_seam_census.yaml` — 47 active rows (16 writer / 10 resolver /
16 reader) + 5 `status: retire` resolver rows. `test_verdict_seam_census.py::_derive_census`
(`:722`) derives the set via AST and asserts equality with the active fixture
(`test_derived_census_matches_fixture:958-976`; **shrinkage reds too**). Retire rows are
checked only by `_validate_retire_rows:884-908` (FR exists + WP-claimed; **no AST-presence
check**).

---

## 4. Census delta on the flip (Stream 1 — paula-patterns)

### A. The 5 retire rows and the 5-vs-4 reconciliation
| Row (resolver) | retiring_fr | Live state |
|---|---|---|
| `post_merge/review_artifact_consistency.py::_artifact_dirs_for_wp` | FR-007 | live + **also** in active set (double-listed) |
| `review/cycle.py::_review_cycle_wp_dir` | FR-003 | live + **also** in active set (double-listed) — the write-seam owner |
| `review/arbiter.py::_find_review_cycle_artifact` | FR-009 | **DELETED — tombstone** (the "5th" the brief's "4" omits) |
| `review/arbiter.py::persist_arbiter_decision` | FR-009 | present but AST-invisible (delegates cross-module) |
| `review/arbiter.py::get_arbiter_overrides_for_wp` | FR-009 | present but AST-invisible (reads event-sourced `ReviewOverride`) |

"4 still-live retire-marked resolvers" = the 5 minus the deleted tombstone. Only the first two
are double-listed (active **and** retire); the flip resolves that tension by removing the
active rows and discharging their retire intent.

### B. The 3 "unrouted sites" — **all MUST-ROUTE, none already-safe**
- `workflow.py::review` (`:1749-1760`) — the mkdir/cycle-number **allocation seam**; hardcodes
  `kind=WORK_PACKAGE_TASK` via `_resolve_workflow_read_dir`. On flip, allocator globs PRIMARY
  (empty) while writes accrete in COORD → **cycle-number collisions/overwrites**.
- `workflow_cores.py::has_prior_rejection` (`:384-388`) — bare `feature_dir / "tasks" / wp_slug`
  join. On flip → glob empty → **fix-mode never activates** for a rejected WP.
- `workflow_executor.py::implement_try_render_fix_mode_prompt` (`:1106-1117`) — bare join +
  `ReviewCycleArtifact.latest(...)` PRIMARY fallback → **fix-mode silently downgrades**.

### C. `resolve_review_verdict_facts` — the relocated fail-open (brief's stale claim)
`tasks_verdict_persistence.py::resolve_review_verdict_facts:386` → `_resolve_verdict_wp_dir:419`
→ `_review_cycle_wp_dir(main_repo_root, mission_slug, wp_path.stem)` at **default kind**
(`:457`). The bare join survives *only* as the `WorkspaceRootNotFound` degrade for git-less
fixtures (`:454`). Fail-open chain if the writer flips to COORD and this reader stays default:
approval-lane move → `_get_latest_review_cycle_verdict(primary_dir)` globs empty →
`(None, None)` → `_guard_rejected_verdict` refuse-arm requires `review_artifact_name is not None`
(`tasks_transition_core.py:405`) → **guard returns without refusing → a COORD-recorded
rejection is approved.** Safety-critical.

### D. The frontmatter-fallback readers to collapse
The 16 active `reader` rows are exactly the sites that read verdict from artifact frontmatter
(glob → `read_text` → `split_frontmatter`/`extract_scalar`/`ReviewCycleArtifact.from_file`)
rather than from the reducer snapshot. Safety-relevant gate readers to repoint to the
event authority: `tasks_parsing_validation.py::_get_latest_review_cycle_verdict` (move-task
gate), `agent_utils/status.py::_get_wp_review_verdict`/`show_kanban_status` (board),
`post_merge/review_artifact_consistency.py::find_rejected_review_artifact_conflicts` (merge
gate), `workflow_executor.py::implement_try_render_fix_mode_prompt`. The `review/artifacts.py`
parser family survives **iff** the artifact stays a written prose record — a scope decision the
spec must state (retire the verdict read-path; keep prose read).

### E. Net census shape after the flip
- All 5 retire rows discharged (2 by removing double-listed active resolvers; 3 arbiter already
  discharged/tombstoned).
- Active resolver set shrinks toward physical write/audit sites only.
- Active reader set shrinks by the gate readers repointed to the snapshot.
- **Zero rows added** — the single event authority (`state.get("review")` on the reducer
  snapshot) is *by design* not a frontmatter reader and matches no AST predicate (proven by
  `test_verdict_seam_census.py:994-1005`). Every shrinkage must land in the yaml in the **same**
  change (the check reds on shrinkage).

---

## 5. Flip ordering, atomicity, blast radius, topology (Stream 2 — architect-alphonso)

### A. Topology divergence
`MissionTopology.{SINGLE_BRANCH, LANES, COORD, LANES_WITH_COORD}` (`mission_runtime/context.py:55-67`);
`routes_through_coordination()` true iff `COORD`/`LANES_WITH_COORD`.

| Topology / coord-state | writes today | post-flip physical dir | diverges if readers stay WPT |
|---|---|---|---|
| `SINGLE_BRANCH`, `LANES` | PRIMARY | PRIMARY (affirmative) | **none — coincident** |
| `COORD`/`LANES_WITH_COORD` — **materialized** | PRIMARY | **COORD** | **YES — fail-open** |
| coord — empty/unmaterialized | PRIMARY | PRIMARY (EMPTY degrade) | none at write instant |
| coord — **branch DELETED** (post-merge) | PRIMARY | absorbed → PRIMARY | **none — absorbed** |

Only materialized coord topologies actually move the write. 45/45 merged coord missions in-repo
already have deleted branches (`_review_cycle_reconcile_doctor.py:24-52`).

### B. The exact break = physical write location only
Commit target is *already* COORD (per-file classification). The single concrete test break is
`test_analysis_report_rehome.py:231` — the **physical-path** assertion
(`rel == "kitty-specs/<slug>/tasks/WP01/review-cycle-1.md"`); the commit-ref assertions stay
green. Re-pin that test to the `.worktrees/…`-prefixed path in the same commit.

### C. Atomicity is the load-bearing constraint (not sequencing)
Both single-direction partial orders fail-open on `_guard_rejected_verdict`:
- **Write-first:** writes COORD, reader reads PRIMARY (empty) → fail-open approval.
- **Reader-first:** reader reads COORD (empty, nothing written yet) → fail-open approval.

∴ **the write default and the safety-critical verdict reader MUST flip in one atomic commit**,
together with all six `_review_cycle_wp_dir` consumers + the three bypass sites re-homed through
the owner. Non-safety items may lag (merge-gate lane leg already COORD;
`revert_committed_verdict_write` already `REVIEW_CYCLE`).

### D. Blast-radius (9 sites move in the flip wave)
6 routed consumers (`create_rejected_review_cycle` write; `resolve_review_verdict_facts`;
`_persist_approved_review_cycle` latest-verdict probe `:534`; `resolve_review_cycle_pointer`
read `:326`; `persist_arbiter_decision` `:460`; merge gate `_artifact_dirs_for_wp` `:197`) +
2 raw joins (`has_prior_rejection`, `implement_try_render_fix_mode_prompt`) + 1 counter site
(`workflow.py::review`). `_commit_review_cycle_artifact`/`revert_committed_verdict_write` are
already commit-target-correct.

### E. Backward-compat — **preserve the absorption fallback**
`cycle.py:140-144` (`StatusReadPathNotFound` → `read_dir(WORK_PACKAGE_TASK)`) is the ONLY thing
landing the 45 merged-coord missions' reads on PRIMARY where content lives. **Keep it verbatim.**
Residual `live_coord_pre_adr_primary_record` create-window records (WP08 found zero in-repo, but
the class is real) need the `doctor review-cycle-reconcile` sweep — recommend gating the flip on
zero such findings, or folding a re-home step.

### Stale-doc flags for the spec
- `cycle.py:70-77` claims the merge gate opts into `REVIEW_CYCLE` — it does **not**
  (`review_artifact_consistency.py:194-196`; T062 voided the flip). Reconcile before writing FRs
  off the cycle.py text.
- `persist_arbiter_decision` falls back to `feature_dir.parent.parent` for `main_repo_root` — a
  `SINGLE_BRANCH`/`LANES` inference; a coord mission needs the resolved root threaded through.

---

## 6. Merge-driver contract + SC-004 concurrency model (Stream 4 — architect-alphonso)

### A. COORD-authoritative merge contract
Two mechanism classes, chosen by reconciliation algebra, not partition:

| COORD artifact | Authoritative side | Mechanism | Fail-mode |
|---|---|---|---|
| `review-cycle-N.md` | whole-doc, both preserved | **driver** `spec-kitty-review-cycle` (`merge_driver.py:722-772`) | identical → write-through; distinct → conflict-marker doc + **Exit(1)** (aborts squash) |
| `acceptance-matrix.json` | per-row/field 3-way union; `overall_verdict` recomputed | **driver** (`:638-654`) | field collision → marker **as JSON string** (valid doc, non-aborting); malformed/dup → Exit(1) |
| `issue-matrix.json` | same, keyed by canonical `issue_ref` | **driver** (`:549-565`) | same two-tier |
| `issue-matrix.md` (legacy) | **retire/migrate** | **none** (gitattributes repointed to `.json`, `init.py:74-76`) | **silent `-X theirs` clobber — residual #2804 hole** |
| `meta.json::coordination_branch` | **absent post-merge** | **executor step, not driver** | deterministic `clear_coordination_metadata` after teardown |
| `meta.json` provenance | target (`ours`) | driver `spec-kitty-meta` | already correct |

Review-cycle's abort-refuse deliberately does **not** generalize to matrices (blendability +
abort-vs-continue). #2804's residual damage is the **idempotent scaffolder reading the wrong
partition** (sees PRIMARY husk "absent" → re-emits placeholder over filled COORD copy) + the
uncovered legacy `.md`. Single COORD authority makes the scaffolder's idempotence guard
(`tasks/issue_matrix.py:333-339`) no-op. #3086's `clear_coordination_metadata`
(`mission_metadata.py:721-747`) exists but is only wired to `mission close --discard`; the
`spec-kitty-meta` driver currently keeps `coordination_branch` *theirs*-authoritative (worse).

### B. SC-004 concurrency model — **RECOMMENDED: optimistic CAS on the COORD ref**
Root defect: **allocation authority (PRIMARY glob) ≠ durability authority (COORD ref).**
Recommended model:
1. Derive the cycle number from `git ls-tree <coord-ref> -- …/tasks/<wp>/` (retire the PRIMARY
   glob for allocation; keep the strict `review-cycle-(\d+)\.md$` parse + refuse-on-unparseable).
2. Build the commit by plumbing — `git hash-object -w` → `mktree`/`read-tree`+`update-index` →
   `git commit-tree -p <observed-coord-head>` (avoids `safe_commit`'s single-worktree HEAD
   constraint; lets any lane worktree contribute).
3. Publish with **CAS**: `git update-ref <coord-ref> <new-sha> <observed-old-sha>` (atomic).
   Requires extending `git/ref_advance.py:416` to emit the old-value positional (it does not
   today).
4. Bounded retry on CAS rejection (reuse `_COMMIT_CONTENTION_*` constants); on exhaustion raise
   `ReviewCycleError` (distinguish contention from plain failure — `_commit_failure_message`).
5. `feature_status_lock` optional in-process fast-path only.

**NFR-006 satisfied by construction** — git's atomic ref update is the serialization primitive;
no lock spans the subprocess. Guarantees: (a) monotonic allocation, (b) durable-on-COORD,
(c) no lock across git, (d) loser retries cleanly or fails closed — never a silent verdict drop.
The review-cycle merge driver remains the migration-window backstop for pre-migration residue.

> **Cross-stream reconciliation with §7.1 (SC-004):** Stream 4 recommends CAS-on-coord-ref
> (keeps a per-file `.md` as the durable record); Stream 3 recommends routing verdict durability
> to the append-only event log (union-merge-driver protected). These are **two viable
> single-authority designs.** The event-log route folds durability into an already-solved
> concurrency path (`emit_status_transition`) and removes the per-file commit entirely; the CAS
> route keeps the `.md` durable but makes the coord ref its sole allocation+durability
> authority. **Decision D2 (§11).**

---

## 7. Carry-red split-symptom verdicts (Stream 3 — debugger-debbie)

| Carry-red | Verdict | In unification? | Single-authority fix |
|---|---|---|---|
| **SC-004** | **qualified symptom** (loss mode = split; index.lock = independent, mitigated) | yes — *iff* durability moves off the per-file commit | route verdict durability to the event log **or** CAS-on-coord-ref (D2) |
| **#2804** | **proven symptom** of the *sibling* coord/PRIMARY write-surface split (matrix pair) | yes — same pattern on matrices | accept writes matrix to COORD (#2404 flip) + guarantee drivers registered/active at merge + fix `.md`→`.json` seed drift |
| **#3086** | **INDEPENDENT — disproven as seam symptom** | **NO — do not gate on unification** | wire canonical flatten into merge branch-delete cleanup |
| **WP07 fixture** | **proven symptom** | yes | collapse reader to snapshot-only; retire fallback + self-referential live-mission fixture; re-pin hermetically |

### 7.1 SC-004 (detail)
Two-phase writer: alloc+write+validate under `feature_status_lock` (`cycle.py:582-643`); commit
outside the lock (`:480-579`, NFR-006). Race in the shared working tree: (1) `index.lock`
collision exhausts the 3× retry; (2) staged-by-peer → A's commit sweeps B's staged file → B sees
"unchanged" → false hard-error (`:520-525`). Test: `test_review_durability_matrix.py:1452-1533`
(50 iter × 2 processes). Honest caveat: **SC-004 is the weakest split claim** — if the
unification keeps a per-file `.md` commit, the race persists; it closes only if durability moves
to a concurrency-safe authority (event-log append or CAS-on-ref).

### 7.2 #2804 (detail)
COORD-partition matrix authored on two surfaces: `finalize-tasks` scaffolds the placeholder on
the mission branch; `accept` writes the fill on the PRIMARY/target checkout (sibling #2404). The
add/add (no common base) is resolved by `git merge --squash -X theirs` → mission-branch
placeholder wins → accepted fill discarded. **Registration-completeness gaps that keep the pin
red:** the harness runs bare `git init` (no `.gitattributes`/driver config) so `-X theirs`
still fires — the merge executor must *guarantee* driver registration before the squash; and
`m_3_2_6_gate_artifact_merge_drivers.py` seeds the issue-matrix driver on the **retired `.md`**
pattern (live artifact is `.json`) — verify `m_3_2_6_issue_matrix_driver_repoint.py` supersedes it.

### 7.3 #3086 (detail — the independence proof)
`_phase_cleanup_worktrees_and_branches` (`executor.py:1246-1360`) has two decoupled gates:
branch-delete on `delete_branch` (`:1291-1325`); coordination-flatten folded into
`teardown_coordination_topology` on `remove_worktree` (`:1338-1355`). With
`remove_worktree=False, delete_branch=True` the branch is deleted but meta keeps
`coordination_branch` → every later `resolve_status_surface_with_anchor` hits `CoordState.DELETED`
→ raises `CoordinationBranchDeleted` (`surface_resolver.py:838-843`). **Differential-matrix:**
present/absent independent of the review-cycle seam; `coordination_branch` is legitimate
single-valued metadata, not a verdict dual-store. Fix = call the canonical flatten
(`clear_coordination_metadata` + pop `topology` + `flattened=True`) in the branch-delete path,
decoupled from `remove_worktree`. **Recommend standalone/fast-follow, not gated on the flip.**

### 7.4 WP07 fixture
`test_reducer.py:1027-1046` pins the **live, self-referential** mission dir and asserts
`event_sourced_review_result(feature_dir,"WP07") == ReviewResultLookup(slot_present=False,…)`.
Green only while the write seam is PRIMARY-pinned and authority is COORD — a lifecycle bomb that
reds when this mission merges (coord branch deleted, primary gains WP07 events). Fix: snapshot-only
reader (retire the fallback branch), re-pin hermetically to `tmp_path`
(pattern at `test_reducer.py:994-1025`). Watch `test_2093_authority_invariant.py` arm 2 during
the slot collapse.

---

## 8. #3216 dedup + #3217 census gap (Stream 5 — reviewer-renata)

### 8.1 #3216 — authority migration, not a dedup
`_get_latest_review_cycle_verdict` (`tasks_parsing_validation.py:296`),
`latest_review_artifact_verdict` (`artifacts.py:385`), `ReviewCycleArtifact.latest/.from_file`
are the same glob→sort→frontmatter logic. **Two divergences, not one:**
- *Polarity:* board reader returns `(None, artifact)` for damaged (FR-012); canonical **raises**.
- *Vocabulary:* board accepts `{approved, approved_after_orchestrator_fix, arbiter_override,
  rejected}` (`:58-60`, returns unknown-with-warning); canonical rejects anything outside
  `{approved, rejected}` (`artifacts.py:215`). A naive fold reclassifies `arbiter_override` →
  damaged — a behavior change.

Under the collapse the current-verdict authority is `event_sourced_review_result`
(`reducer.py:549`); the artifact is authoritative only for prose. **∴ both frontmatter verdict
readers become obsolete for the verdict question** — #3216 becomes *route the verdict question
to the reducer snapshot; keep the artifact readers for prose only.* FR-012's three-way survives
natively via `ReviewResultLookup` (`reducer.py:482-515`; `slot_present`/`result`), and
`event_sourced_review_result` fails closed on a corrupt log — SC-012 **preserved**. **Mandatory
vocabulary bridge:** event vocab is `{approved, changes_requested}` (`status/models.py:274`);
`"rejected" ≡ "changes_requested"` must be explicit or the stale-board flag silently stops firing.
Two call sites: `_apply_review_status_flags:404` (SC-012 fail-closed), `resolve_review_verdict_facts:410`.

### 8.2 #3217 — the real gap is `.from_dict`, narrower than the brief
`_review_from_frontmatter` is **already covered** (direct `ReviewOverride(...)` ctor → writer
row `census.yaml:231`). The genuine blind spot is the **`.from_dict` classmethod construction
shape**: scope regex `\bReviewOverride\(` misses `ReviewOverride.from_dict(`, and `_contains_ctor`
keys on the bare callee name (`from_dict` ∉ `_RECORD_CTOR_NAMES`). Concrete uncounted live
instance: `backfill_runtime_state.py::_runtime_repair_delta:1320`. Fix: extend the scope regex
+ writer classifier to recognize `<Record>.from_dict(` (reuse `_call_base_name`).
**Over-match hazard:** broadening sweeps in the event-authority deserializers the census
deliberately excludes (`reducer.py`, `models.py`, `wp_review.py`, `_snapshot_review_override`)
— pair the predicate with named `_EXCLUDED_MODULE_REASONS` additions so
`test_review_slot_is_event_authoritative_and_not_a_frontmatter_bypass:994` stays green.

---

## 9. Proposed spec backbone (FR / NFR / SC / Constraint)

**Functional (the unification):**
- FR-A **Write-seam flip.** `_review_cycle_wp_dir` default → `REVIEW_CYCLE`; all 9 flip-wave
  consumers (§5.D) resolve one identical directory (SC-006 write-side completion).
- FR-B **Single verdict authority.** Every gate/board/display answers "approved?" from the
  reducer snapshot (`event_sourced_review_result`); zero frontmatter verdict reads (SC-011).
  Artifact retained for prose only. Vocabulary bridge `rejected≡changes_requested` explicit.
- FR-C **Atomic flip.** Write default + safety-critical reader (`resolve_review_verdict_facts`,
  `_persist_approved_review_cycle` probe) flip in one commit (§5.C).
- FR-D **Retire the 5 census retire rows + the 3 unrouted sites**; re-home the 2 raw joins
  through the owner; update `verdict_seam_census.yaml` in the same change.
- FR-E **Preserve the exception-absorption fallback** (§5.E) + gate the flip on a clean
  `doctor review-cycle-reconcile` sweep (zero `live_coord_pre_adr_primary_record`).
- FR-F **#3216 authority migration** (route verdict to snapshot; prose-only readers).
- FR-G **#3217 census predicate extension** (`.from_dict` recognition + excluded-module reasons).

**Merge contract (COORD-authoritative):**
- FR-H **#2804** — accept writes matrix to COORD (#2404); guarantee driver registration before
  the squash; retire `issue-matrix.md`; fix the `.md`→`.json` seed drift.
- ~~FR-I #3086~~ — **REMOVED from this mission (Decision D1).** Handed to a parallel session
  (§12). #2782 remains out of scope (sync domain).

**Reader consistency (folded-in slice of epic #2093):**
- FR-K **Dashboard/board reads verdict from the event authority, not markdown.** Fold in the
  *reviews slice* of #2093 (architect-alphonso's 2026-07-05 ruling: dynamic runtime state incl.
  reviews retires to event-log authority; static design-intent stays frontmatter-canonical). Bind
  **every** reader of a WP's review/verdict state — not only the gates but the dashboard/kanban
  board (`agent_utils/status.py::show_kanban_status`, `_get_wp_review_verdict`) and the status
  display — to the single event-sourced reducer snapshot (`event_sourced_review_result`,
  `reducer.py:549`). This **generalizes SC-011 from "gates" to "all readers,"** closing the
  #2275 split-surface class (the two-ends-consult-different-surfaces defect that spawned epic
  #3044) at the reader level, not just the gate level. Guard by **extending
  `test_2093_authority_invariant.py`** to assert the review/verdict reader surface is
  event-authoritative (no frontmatter bypass). **Claim only the reviews slice of #2093**; the rest
  of its WP-metadata catalogue (`owned_files`/`dependencies`/`execution_mode`/
  `authoritative_surface`/`create_intent`) stays with #2093/#2400. The dashboard readers are
  already in the census (Stream 1 §4.D) as PRIMARY-pinned frontmatter readers, so this FR is the
  reader-consistency completion of the same collapse, not new surface.

**Concurrency:**
- FR-J / NFR-006 **SC-004 single-authority durability** (event-log append **or** CAS-on-coord-ref
  per Decision D2), holding no lock across a git subprocess.

**Success criteria carried/added:** SC-004, SC-006 (write-side), SC-011, SC-012 (preserved via
`ReviewResultLookup`), SC-008 (census fails on any new uncounted member incl. `.from_dict`).

**Constraints:** canonical sources only; red-first for every bug (the C-005 pins already exist);
the census check fails on shrinkage — every retirement lands in the yaml in the same change;
reconcile the two stale docstrings (§5) rather than writing FRs off stale text.

## 10. Sequencing plan

1. **Pre-flip audit** — `doctor review-cycle-reconcile`; gate on zero create-window records.
2. **Atomic flip commit** — FR-A + FR-C + FR-D + census yaml + re-pin
   `test_analysis_report_rehome.py` + stale-docstring reconciliation.
3. **Authority collapse** — FR-B + FR-F + FR-K (verdict → snapshot; artifact write-only; **all
   readers incl. dashboard/board bound to the event authority**; WP07 snapshot-only). Extend
   `test_2093_authority_invariant.py`.
4. **Concurrency** — FR-J (SC-004 via event-log durability), post-collapse.
5. **Merge contract** — FR-H (#2804). (#3086 is a separate parallel session — §12.)
6. **Census hardening** — FR-G (#3217).

Every WP is red-first through a pre-existing entry point (§7 names each). The two C-005 pins and
the SC-004 durability matrix are the driving regressions.

## 11. Operator decisions — RESOLVED (2026-08-05)

- **D1 — #3086 scoping → STANDALONE FAST-FOLLOW NOW.** #3086 is **out of this mission's scope.**
  Fix it as its own campsite PR immediately: wire the canonical flatten
  (`clear_coordination_metadata` + pop `topology` + `flattened=True`) into
  `_phase_cleanup_worktrees_and_branches`' branch-delete path (`executor.py:1291-1360`),
  decoupled from the `remove_worktree` gate, red-first through the existing pin
  `test_issue_3086_merge_delete_branch_flattens_coordination_metadata.py`. FR-I is removed from
  the unification spec. (The predecessor's C-005 kept this pin red; the fast-follow greens it.)
- **D2 — SC-004 durability → ROUTE TO THE EVENT LOG.** Verdict durability becomes an append to
  `status.events.jsonl` via `emit_status_transition` (already the sole serialized status
  authority; its commit is union-merge-driver protected, so concurrent appends union rather than
  clobber). **Scope consequences:** (1) the per-file authoritative commit is removed — the
  CAS-on-coord-ref model and the `ref_advance.py` old-value extension are **NOT needed**; (2) the
  `review-cycle-N.md` write demotes to a **best-effort, non-authoritative** human render whose
  commit failure is a *warning*, not a hard `ReviewCycleError` — retire the hard-error branch
  (`cycle.py:513-525`), the `git_operation_in_progress` retry loop (`:554-579`), and the
  orphan-cleanup complexity (`:757-790`) as authoritative machinery (keep at most defense-in-depth
  during migration); (3) SC-004 is satisfied because the authoritative datum no longer contends on
  a shared git index at all.
- **D3 — artifact read-path → FULLY RETIRE.** The `review-cycle-N.md` artifact becomes
  **write-only** (on-disk audit trail, never read back by the workflow). The `review/artifacts.py`
  parser family (`from_file`/`latest`/`latest_review_artifact_verdict`/
  `rejected_review_artifact_for_terminal_lane`) and every frontmatter verdict reader retire —
  maximum census shrinkage. **Scope consequences to verify in the spec:** (a) re-examine the two
  readers that consume the artifact for *non-verdict* reasons — `resolve_review_cycle_pointer`
  (pointer→path) and `_guard_feedback_source_provenance` (the #990/#2996 duplicate-feedback guard,
  which parses `feedback_source` as an artifact); confirm each is retired or re-expressed without a
  read-back; (b) with the `.md` non-authoritative *and* unread, the `spec-kitty-review-cycle`
  fail-closed conflict-marker merge driver (`merge_driver.py:722-772`) may relax (it guarded an
  authoritative record; a best-effort render need not abort a squash) — record whether it retires
  or downgrades; (c) `#3216` collapses to *"delete both frontmatter verdict readers"* rather than
  fold-then-migrate.

### Net effect of D1–D3 on the spec backbone (§9)

- **Drop FR-I** (#3086 leaves the mission — standalone fast-follow).
- **FR-J/SC-004 simplifies** to "route verdict durability to the event log; demote the `.md` to
  best-effort render" — no CAS, no `ref_advance.py` change.
- **FR-B + FR-F + D3 merge** into one collapse: verdict authority = reducer snapshot; artifact
  write-only; parser family + all frontmatter verdict readers retire; `#3216` = delete the two
  readers (with the explicit `rejected≡changes_requested` vocabulary bridge for the surviving
  event-verdict consumers); WP07 reader becomes snapshot-only.
- **FR-H (#2804) stays** (COORD-authoritative matrices + driver-registration guarantee + retire
  `issue-matrix.md` + fix the `.md`→`.json` seed drift).
- Remaining open detail (spec-time, not blocking): the exact fate of the review-cycle merge driver
  and the two non-verdict artifact readers under D3 (§11-D3 a/b).

---

## 12. #3086 — handover to a parallel session (removed from this mission, Decision D1)

Self-contained prompt for a separate session/agent. #3086 is a P0, independent of the
verdict-seam unification; the red-first pin already exists and must be greened.

> **Task:** Fix P0 issue **#3086** — `spec-kitty merge` deletes the coordination branch but never
> clears `coordination_branch` from `meta.json`, so every merged coord mission later crashes
> `retrospect create --update` / `implement` with `CoordinationBranchDeleted`. Real-world hit rate
> is 100% (45/45 merged coord missions in-repo already have deleted branches; the reconcile doctor
> measured this). This is a standalone campsite fix — it is **not** part of the review-cycle
> verdict-seam unification and must not be sequenced behind it.
>
> **Root cause (already diagnosed):** `_phase_cleanup_worktrees_and_branches`
> (`src/specify_cli/merge/executor.py:1246-1360`) has two decoupled gates — branch deletion on
> `delete_branch` (`:1291-1325`, runs `git branch -D`), and coordination-flatten folded into
> `teardown_coordination_topology` on `remove_worktree` (`:1338-1355`). The flatten is the only
> path that clears the meta key, so a `--delete-branch --no-remove-worktree` merge deletes the
> branch and strands `coordination_branch`. Every later `resolve_status_surface_with_anchor`
> (`src/specify_cli/coordination/surface_resolver.py:631-845`) then hits `CoordState.DELETED` and
> raises `CoordinationBranchDeleted` (`:838-843`) — the deliberate #1848 data-loss hard-fail.
>
> **Fix:** In the branch-delete path of `_phase_cleanup_worktrees_and_branches`, after the
> coordination branch is deleted, call the **canonical flatten already used by
> `mission close --discard` and `doctor coordination --fix`**:
> `clear_coordination_metadata(feature_dir)` (`src/specify_cli/mission_metadata.py:721-747`) + pop
> `topology` + set `flattened=True`, on the **target** feature dir, committed to the target ref via
> the existing bookkeeping-commit seam. **Decouple it from the `remove_worktree` gate** so a
> `--delete-branch --no-remove-worktree` merge also flattens. Do NOT invent a new mechanism — reuse
> the existing primitive.
>
> **Red-first (the pin already exists — do not rewrite it, green it):**
> `tests/regression/test_issue_3086_merge_delete_branch_flattens_coordination_metadata.py`. It
> drives `_phase_cleanup_worktrees_and_branches(run)` with `remove_worktree=False,
> delete_branch=True` on a real git repo whose coord branch exists and whose meta declares it, and
> asserts post-cleanup that `"coordination_branch" not in load_meta(feature_dir)`,
> `flattened is True`, `"topology" not in meta` (`:166-182`). It is RED today (the key survives);
> your fix greens it. The pin anchors on the *absence* of the key (the exact invariant
> `surface_resolver` keys `CoordState.DELETED` on), so it cannot be false-greened by a downstream
> `except` guard.
>
> **Governance:** assign #3086 to the HiC before starting (Tracker Ticket Assignment Rule); PR-only
> to `main` (operator merges); run `pytest tests/regression/test_issue_3086_*.py` +
> `tests/specify_cli/.../test_merge*.py` targeted, not the full suite. Also note the sibling
> `spec-kitty-meta` merge driver currently classifies `coordination_branch` as a *theirs*-
> authoritative planning key (`merge_driver.py:80,225-235`) — confirm the executor clear runs
> *after* any driver reconciliation so it is authoritative.
>
> **Out of scope for you:** the review-cycle write-seam flip, the verdict-authority collapse,
> #2804, #3216, #3217 — all owned by the parallel verdict-seam-unification mission.
