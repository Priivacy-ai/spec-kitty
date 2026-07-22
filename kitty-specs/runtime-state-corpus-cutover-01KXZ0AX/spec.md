# Mission Specification: Runtime-State Corpus Cutover

**Mission Branch**: `feat/runtime-state-corpus-cutover`
**Created**: 2026-07-20
**Status**: Draft
**Input**: Follow-up to #2684 / PR #2817 — issue #2816. Complete the deferred runtime-state
corpus cutover: make event-log authority unconditional and retire the phase-1 dual-write toggle,
per the strict migration contract `backfill → verify(FAIL-CLOSED) → flip reader+writer → delete
fallbacks → reduce`.

## Context *(why this mission exists)*

Mission #2684 evicted runtime-mutable work-package state (`shell_pid`, subtask completion,
activity-log notes, `tracker_refs`, `agent`/`assignee`, review-cycle fields) into one off-axis
`InnerStateChanged` event and read it back from the reduced status snapshot — **but shipped it as
dual-write behind an off-by-default flag** (`_phase1_snapshot_authority_active`, keyed on
`meta.json` `status_phase`). With the flag OFF (the production default), the legacy WP-file
frontmatter / `tasks.md` checkboxes remain the live authority and every runtime write hits **both**
surfaces. The corpus was never migrated and the flag was never flipped. Until that lands, #2684's
headline outcome — *stop writing WP-file runtime state* — holds only at `status_phase:1`.

This mission runs the deferred cutover as a **real production-default migration** (staged
backfill + fail-closed verify + an upgrade path for existing deployments), not a code tidy. The
governing contract is `kitty-specs/wp-runtime-state-eviction-01KXWN13/contracts/migration.md`; the
ADR of record is `docs/adr/3.x/2026-07-19-1-wp-runtime-state-event-log-eviction-via-innerstatechanged.md`.

**Scope generalization (operator decision 2026-07-20).** Beyond flipping the flag, the mission makes
the **WP/dashboard reader** reconstruct a WP's **resolved final-state from the event log** rather than
reading in-file metadata for canonical status — and generalizes the eviction to the WP's runtime
**identity**: the *actual* `role`, `agent_profile`, and `model` that take a WP are **event-sourced**
(recorded at each pick-up), distinct from the *authored/recommended* assignment that stays
frontmatter-canonical. The reason is a lifecycle one: the actual identity **shifts** (implementer→reviewer,
model swaps), so a static frontmatter value is wrong mid-cycle. This implements the resolved-binding
("record + reconstruct") half of #2093's ruling and the WP-metadata slice of sub-epic #2400; the full
fail-closed *enforcement* (#2399) stays out of scope. A SaaS consumer for the resolved binding is in the
works (the SaaS team is aware); delivery rides the existing structured `actor` on the claim transition.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator runs a safe, fail-closed corpus cutover (Priority: P1)

An operator (or the upgrade path acting on their behalf) needs to migrate every mission's
frontmatter/checkbox runtime state into the event log and only then switch that mission to
snapshot-authority. The migration must be observable (dry-run first), must prove parity before it
flips anything, and must **refuse to flip** any mission whose backfill/verify has not passed.

**Why this priority**: This is the load-bearing safety mechanism. Flipping a mission to
snapshot-authority before its legacy state is seeded as events means a WP with frontmatter-only
runtime state reduces to `{}` → `None` = **silent data loss**. Everything else depends on this
gate existing and being fail-closed.

**Independent Test**: On a corpus with legacy frontmatter runtime state, run the cutover CLI in
dry-run (reports would-seed counts, writes nothing), then for real: it seeds events, verifies
count+value parity against the old reader, and only flips missions that passed. Inject a corrupt
seed → the command aborts before any flip and leaves `status_phase` unchanged.

**Acceptance Scenarios**:

1. **Given** a mission carrying `shell_pid`/`agent`/`tracker_refs`/subtask completion only in the
   WP files, **When** the operator runs `spec-kitty migrate backfill-runtime-state --dry-run`,
   **Then** the command reports the seed counts per mission and writes nothing (no events, no flip).
2. **Given** the same corpus, **When** the operator runs the cutover for real, **Then** the reduced
   snapshot for every WP equals the old frontmatter/checkbox reader by count and value, and only
   then is `status_phase` set to the snapshot-authority value.
3. **Given** a mission whose backfill would produce a snapshot that diverges from the old reader
   (fault-injected corrupt deterministic seed row), **When** the cutover runs, **Then** it aborts
   fail-closed **before** flipping that mission and reports the mismatch; `status_phase` is untouched.
4. **Given** a mission already migrated, **When** the cutover is re-run, **Then** it seeds nothing
   (idempotent) and the flip is a no-op.

---

### User Story 2 - Event log is the unconditional authority (Priority: P1)

After cutover the reduced snapshot is the authority for WP runtime state everywhere — the phase-1
flag and its flag-OFF (dual-write / frontmatter-authority) branch no longer exist. A runtime
transition writes to the event log only; it never mutates `tasks/WP##.md`.

**Why this priority**: This is the mission's headline outcome and the reason #2684 was undertaken.
While the flag exists, the production default is still the legacy path, so the eviction is not
actually in effect.

**Independent Test**: Grep proves `_phase1_snapshot_authority_active` and its facade export are
gone. Drive a runtime transition (claim / move-task / mark-status) and assert the WP file is
byte-identical before and after, while the event log gains the event and the snapshot reflects it.

**Acceptance Scenarios**:

1. **Given** the cutover is complete, **When** any of the ~10 read/write sites resolves WP runtime
   state, **Then** it reads the snapshot / writes an event only — there is no flag branch to select
   the legacy path.
2. **Given** a claimed WP, **When** its `shell_pid`/`agent`/`assignee`/`tracker_refs`/subtask/review
   state changes, **Then** `tasks/WP##.md` is byte-stable and the change is visible only via the
   snapshot.
3. **Given** the codebase after this mission, **When** the predicate `_phase1_snapshot_authority_active`
   is searched for (source and status facade `__all__`), **Then** there are zero occurrences.

---

### User Story 3 - Existing deployments migrate safely on upgrade (Priority: P2)

A user upgrading an existing Spec Kitty project must have their corpus backfilled+verified as part
of `spec-kitty upgrade`, so the unconditional cutover does not strand their un-migrated on-disk WP
state. A fresh install with no corpus is a no-op.

**Why this priority**: A big-bang production-default flip without an upgrade migration would break
every existing deployment on the first runtime read after upgrade. This makes the cutover shippable.

**Independent Test**: On a fixture project with legacy runtime state, run the upgrade sequence and
confirm the corpus is backfilled + verified idempotently. On a fresh project (no `kitty-specs/` or
no legacy state), confirm the migration is a no-op. On a corpus that fails verify, confirm the
upgrade migration aborts with an actionable operator message and does not leave a partial flip.

**Acceptance Scenarios**:

1. **Given** a legacy deployment, **When** `spec-kitty upgrade` runs, **Then** the runtime-state
   backfill+verify migration runs (sequenced like the charter.yaml fold) and the corpus is migrated.
2. **Given** a fresh install, **When** `spec-kitty upgrade` runs, **Then** the runtime-state
   migration detects no corpus / no legacy state and no-ops.
3. **Given** an upgrade run whose verify fails for some mission, **When** the migration executes,
   **Then** it aborts that step fail-closed with a message naming the mismatch and does not flip.

---

### User Story 4 - Single-authority invariant is enforced with no exceptions (Priority: P2)

The `#2093` authority invariant test must forbid **any** frontmatter authority read for runtime
state, with an **empty** tolerated-gate set (the flag it tolerated is gone). The two remaining
ungated bypass readers documented in #2817's allow-list are routed onto the snapshot seam so no
split-brain reader survives.

**Why this priority**: The whole point of a single canonical authority is defeated if a stray
reader still resolves frontmatter after the flip. This closes the #2093 debt and prevents
regression.

**Independent Test**: `tests/architectural/test_2093_authority_invariant.py` passes with an empty
tolerated set. The two bypass readers (`tasks_move_task.py` ownership read; `workflow_cores.py`
review-status read) resolve via the snapshot accessor; a reintroduced frontmatter authority read
trips the invariant red.

**Acceptance Scenarios**:

1. **Given** the cutover is complete, **When** the #2093 invariant runs, **Then** the
   tolerated-fallback set is empty and the test passes.
2. **Given** `tasks_move_task.py` and `workflow_cores.py`, **When** they read `current_agent`/
   `shell_pid`/`review_status`/`review_feedback`, **Then** they resolve from the snapshot seam,
   not `extract_scalar(front, ...)`.
3. **Given** a hypothetical new frontmatter authority read, **When** the invariant runs, **Then**
   it fails (the guard is non-vacuous).

---

### User Story 5 - Post-cutover reduction of inert fields (Priority: P3, optional)

After the flip, the `wp_metadata` fields that fed the retired legacy path and the cosmetic
`WP_FIELD_ORDER` slots are inert. Reducing them (the deferred #2684 "IC-08"; this mission's IC-06 /
FR-011) is a bounded cleanup that is safe only
post-cutover and is not a gate on mission completion.

**Why this priority**: Pure hygiene with no behavioural consequence. Explicitly deferrable to a
follow-up so it never blocks the load-bearing cutover.

**Independent Test**: With the reduction applied, the inert fields are gone and no reader
references them; the full suite stays green. If deferred, the mission still completes on US1–US4.

**Acceptance Scenarios**:

1. **Given** the cutover is complete, **When** the inert `wp_metadata` fields / `WP_FIELD_ORDER`
   slots are removed, **Then** no live reader references them and the suite is green.

---

### User Story 6 - WP runtime identity reflects the actual, reconstructed from the event log (Priority: P2)

The dashboard, the `agent tasks status` board, and every WP-view consumer must show a WP's **resolved
actual** runtime identity — the `role`/`agent_profile`/`model` that genuinely took the WP — reconstructed
from the event log, not the stale authored recommendation in frontmatter. Because that identity **shifts
across the lifecycle** (an implementer profile on model A claims it, later a reviewer profile on model B
picks it up), a single frontmatter value is wrong mid-cycle; only the event log's latest-actual reduction
is correct. The authored/recommended assignment is still shown, but **distinctly labeled** — never
conflated with the actual.

**Why this priority**: This is the operator's canonical-authority decision generalized beyond the
#2684-evicted fields. It closes the split-brain where a viewer trusts a pre-advised profile/model that no
longer matches reality. It depends on the cutover (US1–US4) but is the reason the reconstruction reader
exists.

**Independent Test**: Drive a WP through implement-claim (profile P1/model M1) then review-claim
(profile P2/model M2). Assert the reconstructed view shows the *current* actual (P2/M2) after the review
claim, the authored recommendation from frontmatter separately, and that all three readers (dashboard,
status board, `WorkPackage`) agree because they share one reconstruction path.

**Acceptance Scenarios**:

1. **Given** a WP claimed by an implementer (profile P1, model M1), **When** the reconstruction reader
   assembles its view, **Then** the resolved `role`/`agent_profile`/`model` = P1/M1 (from the event log),
   and the authored recommendation is shown as a distinct field.
2. **Given** that WP later review-claimed (profile P2, model M2), **When** the view is reassembled,
   **Then** the resolved actuals update to P2/M2 (latest-wins reduction) with no frontmatter write.
3. **Given** the dashboard, the `agent tasks status` board, and `WorkPackage`, **When** each renders the
   same WP, **Then** they agree (one shared reconstruction reader, three gates collapsed to one).
4. **Given** the recorded resolved profile, **When** it is written, **Then** it came from
   `resolve_profile`/`resolved_agent()`, never a copy of the frontmatter `agent_profile` string (#2093).

---

### Edge Cases

- **A WP that was never claimed** carries no claim anchor; its runtime seeds are skipped (a
  never-claimed WP cannot honestly carry completed subtasks). Backfill must warn, not fail.
- **A mission with no `kitty-specs/` or no `tasks/` directory** (fresh install) → backfill skips
  cleanly; upgrade migration no-ops.
- **`status_phase` hand-flipped to the authority value before backfill runs** — there is no
  production writer for `status_phase` today; the cutover CLI must be the only path that flips it,
  and must refuse to flip a mission whose verify has not passed (no hand-flip footgun).
- **Strip-before-verify** — verify against the *un-stripped* frontmatter; if the frontmatter key a
  snapshot slot depends on has already been stripped, fail closed (`MigrationOrderingError`).
- **Tampered same-slot seed annotation** masked by ULID tiebreak — the raw-stream conflict scan
  aborts fail-closed regardless of fold order.
- **A partially-migrated corpus** (some missions flipped, some not) must be a valid intermediate
  state: unflipped missions still read correctly (they simply have not been cut over yet), and the
  migration is resumable/idempotent.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Backfill CLI entry point | As an operator, I want an invocable `migrate backfill-runtime-state` command with a `--dry-run` mode so that I can seed the corpus and preview counts before writing. | High | Open |
| FR-002 | Fail-closed verify (wire) | As an operator, I want the command to invoke the **existing** WP03 fail-closed verify (count+value parity vs the old reader; the conflicting-seed value-parity guard already shipped in #2817) and abort on any mismatch, so that no mission is flipped on divergent state. Scope is *wiring* the library verify, not re-deriving it. | High | Open |
| FR-003 | Atomic verify-then-flip | As an operator, I want the command to flip `status_phase` to snapshot-authority **only** for missions whose backfill+verify passed, refusing to flip otherwise, so that there is no hand-flip data-loss footgun. (`status_phase` has no production writer today — this CLI is the clean-slate sole writer.) | High | Open |
| FR-004 | Unconditional reader/writer cutover | As a maintainer, I want the flag-OFF (legacy/dual-write) branch removed across **all 12 call sites in 11 files** — the brief's 10 files **plus `cli/commands/agent/tasks_status_cmd.py`, and note `task_utils/support.py` carries two sites** — so the reduced snapshot is always the authority and runtime writes are event-only. Remove each paired local `from specify_cli.status import …` import too. | High | Open |
| FR-005 | Delete the phase-1 predicate | As a maintainer, I want `_phase1_snapshot_authority_active` (`status/emit.py`) and its status-facade export (`status/__init__.py` alias `phase1_snapshot_authority_active` + `__all__` entry) deleted so that no runtime flag remains. `_legacy_lane_mirror_enabled` is **kept** (C-004). | High | Open |
| FR-006 | Replace + delete T037 legacy fallbacks | As a maintainer, I want the legacy fallbacks removed: (a) the verdict/review-field read fallback in `cli/commands/agent/workflow_cores.py` (`resolve_review_feedback_context`), and (b) the done-evidence synthesis in `merge/done_bookkeeping.py` (`_extract_done_evidence`). **(b) requires BUILDING the event-sourced done-evidence read first** — neither `_extract_done_evidence` nor the `:295` fallback reads the snapshot `review` slot today; that snapshot-sourced read must be wired and tested (event-only mission, no frontmatter review → correct `DoneEvidence`) **before** the frontmatter synthesis is deleted (C-001 order). | High | Open |
| FR-007 | Route bypass readers onto the snapshot seam | As a maintainer, I want every ungated frontmatter runtime reader for the **#2684-evicted fields** resolved via the snapshot accessor: `tasks_move_task.py` (`agent`/`current_agent`), `workflow_cores.py` (`review_status`/`review_feedback`), and **`dashboard/scanner.py`** + **`tasks_status_cmd.py`** (`agent`/`assignee`/subtask-completion — MISSED readers using `read_wp_frontmatter().<attr>` / `extract_scalar` attribute access). Resolved `role`/`agent_profile`/`model` reconstruction is FR-012/FR-013 (event-sourced, not "keep frontmatter"). **Note:** the `workflow_cores.py` read is the **same code block** as FR-006(a) — ONE edit. A `/tasks` surface sweep must also confirm the writer-side (`frontmatter.write_shell_pid_claim`, `task_metadata_validation` template emitters) and partial readers (`stale_detection`, `ownership/frontmatter_source`, `context/resolver`). | High | Open |
| FR-008 | Harden the #2093 invariant | As a maintainer, I want the #2093 invariant to forbid **any** frontmatter authority read: reduce `_SANCTIONED_READER_MODULES` to `frozenset()`, rewrite the now-vacuous canonical-gate-identity arm into a "zero frontmatter-authority reads" assertion, **and EXTEND the detector to catch attribute-access reads** (`read_wp_frontmatter().<field>` / `WPMetadata`/`WorkPackage` runtime attributes) — today it only matches `extract_scalar(…)`, so emptying the tolerated set alone is a false green (the dashboard reader escapes it). Prove the extended detector flags the dashboard scanner red before FR-007 reroutes it. | High | Open |
| FR-009 | Reconcile the split test suite | As a maintainer, I want the flag-ON/flag-OFF split test suite reconciled — flag-OFF dual-write tests deleted or re-pointed, flag-ON assertions made unconditional — so the suite reflects the single end-state. | High | Open |
| FR-010 | Upgrade-path migration | As an upgrading user, I want the runtime-state backfill+verify to run as an **auto-discovered** `m_<version>_runtime_state_backfill.py` upgrade migration (self-registers via `@MigrationRegistry.register`; version-key ordered to sort **after** the charter folds; idempotent; no-op on fresh installs; fail-closed on verify failure) so my corpus migrates safely. | High | Open |
| FR-011 | Inert-field reduction (deferred #2684 cleanup) | As a maintainer, I want the now-inert `wp_metadata` fields and cosmetic `WP_FIELD_ORDER` slots reduced, safe only post-cutover, so the model carries no dead runtime slots. (The six-way `wp_snapshot_state` accessor dedup already shipped in #2817 — scope is field/slot removal only.) | Low (optional/deferrable) | Open |
| FR-012 | Canonical WP-view reconstruction reader | As a maintainer, I want the **three** hand-rolled snapshot-authority gates — `dashboard/scanner.py`, `cli/commands/agent/tasks_status_cmd.py` (the `agent tasks status` board), and `task_utils/support.py::WorkPackage` — collapsed into **one** canonical reader that reconstructs a WP's **resolved final-state from the event log/snapshot** for all dynamic fields (lane, agent, assignee, subtasks, review, and the resolved `role`/`agent_profile`/`model` from FR-013), while surfacing the **authored/recommended** assignment from frontmatter **distinctly labeled** (so the dashboard shows "assigned X / running Y" without conflating them). No reader hand-rolls its own gate afterward. | High | Open |
| FR-013 | Resolved-binding event vocabulary (role/profile/model actuals) | As an operator, I want the **actual** resolved `role`, `agent_profile` (+ `agent_profile_version`), `model`, and `provider` that take a WP **recorded on the event log at each pick-up/claim/reassign transition**, folded latest-wins into the snapshot, so the reconstructed view reflects what genuinely ran — because these actuals **shift across the WP lifecycle** (implementer→reviewer, model swaps), a static frontmatter value is wrong mid-cycle. The recorded value MUST come from `AgentProfileRepository.resolve_profile`/`resolved_agent()`, **never** the frontmatter `agent_profile` string (#2093, C-007). The **authored/recommended** assignment stays frontmatter-canonical. The per-field authority is ratified in the C-009 ADR **before** this vocabulary lands. | High | Open |
| FR-014 | Dispatch→claim linkage for the resolved binding | As a maintainer, I want the **genuinely-resolved** model + profile (+version) established on the dispatch/Op path (`invocation/executor.py` — the winning candidate model on `RoutingRecommendation.candidates` via `catalog_candidate`/`profile_candidate`, not a `.model` attribute — + `registry.resolve`/`resolve_profile`; recorded in `invocation/record.py`, keyed by `invocation_id`) **threaded into the implement/review commands** (new `--model`/`--profile`/`--invocation-id` options or a sanctioned side-channel on `cli/commands/agent/workflow.py`) so the claim-time emit records the **true dispatch-resolved** binding incl. model — closing the gap that the claim seam has only the bare `--agent` string + frontmatter-coerced values (recording those would violate C-007). Operator decision: full model-actual now. | High | Open |
| FR-015 | SaaS fan-out of resolved binding | As the SaaS team (consumer, already aware of the new event), I want the resolved-binding actuals delivered across the package boundary by enriching the **structured `actor`** (`{role, profile, tool, model}`) on the claim/review `StatusEvent` + its existing `_saas_fan_out`; `spec_kitty_events` 6.1.0 `StatusTransitionPayload.actor` **already accepts** `Union[str, Dict]` → **zero shared-package change**. **BUT the local emit path is `str`-typed end-to-end** (`StatusEvent.actor: str`, `build_status_event`, `from_dict` does `str(...)`), so a non-trivial **local** type-surface change is required to round-trip a dict actor. Also emit the binding as an **annotation** (for latest-wins reduction — the claim `policy_metadata` fold fires only on `planned→claimed`, not review-claim). Fallback off-axis `WPResolvedBindingChanged` event stays version-gated. | Medium | Open |
| FR-016 | Subtask completion fully event-sourced; markdown checkboxes removed | As an operator, I want subtask completion to be **solely** event-sourced (via `mark-status` → `InnerStateChanged.subtasks` → snapshot) and the `- [ ] T###` **markdown checkboxes removed** from `tasks.md`/WP templates, so the WP view pulls the *resolved* status not the incoherent checkbox proxy. Requires: reroute the lane-transition guard + dashboard off checkbox counting onto the snapshot `subtasks` slot; **update the doctrine prompt templates** (`src/doctrine/missions/mission-steps/…` + tasks templates) so agents are directed to `mark-status`, not checkbox ticks; remove the checkboxes **only after** the backfill has seeded historical completion from them (C-010 order). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero silent data loss | Any count or value parity mismatch (including a fault-injected corrupt deterministic seed row) aborts before the flip; **zero** tolerated mismatches; `status_phase` never changes on a failed verify. | Reliability | High | Open |
| NFR-002 | Idempotency | Re-running backfill mints byte-identical seed ids and seeds nothing on a second run; the upgrade migration is a no-op when the corpus is already migrated. | Reliability | High | Open |
| NFR-003 | WP-file byte-stability | After cutover, a runtime-state transition writes zero bytes to `tasks/WP##.md`; the file is byte-identical before and after (the #2684 AC-5 outcome, now unconditional). | Correctness | High | Open |
| NFR-004 | Suite green with no suppression | The full `tests/architectural/` suite (run per-file) and the `status` test suite pass on the branch; `ruff` and `mypy` report zero issues with no new blanket `# noqa` / `# type: ignore` / per-file ignores. | Quality | High | Open |
| NFR-005 | Upgrade abort safety | An upgrade whose verify fails for any mission aborts that migration step with an operator-actionable message naming the mismatch and leaves the deployment on a consistent (non-partially-flipped) state. | Reliability | High | Open |
| NFR-006 | Backfill performance | Corpus backfill+verify is linear in the number of missions and completes within a few seconds per mission on the dogfood corpus; it performs no network I/O. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Strict contract order | The migration MUST follow `backfill → verify(FAIL-CLOSED) → flip reader+writer → delete fallbacks → reduce`; no step may precede its predecessor (deleting a fallback before backfill is wired+verified strands legacy corpora). | Technical | High | Open |
| C-002 | Big-bang production default | The end-state is a genuine unconditional flip: the predicate is **deleted**, not merely defaulted ON; no residual runtime toggle remains. | Technical | High | Open |
| C-003 | Canonical write target | Backfill AND the upgrade migration resolve their write target via `canonicalize_feature_dir`, never `Path.cwd()` (C-003 / #2647). The new event-writing paths must add **no** repo-root write path (#2815 co-constraint); a regression test asserts no `status.events.jsonl` lands at repo root. | Technical | High | Open |
| C-004 | Lane-mirror out of scope | `_legacy_lane_mirror_enabled` is retained — the `lane` field is still frontmatter-authored, so evicting it is a separate concern deferred to its own follow-up. | Technical | Medium | Open |
| C-005 | Honesty bound (no-data-loss) | "No data loss" is asserted against count+value parity of the reduced snapshot, not temporal fidelity: backfilled subtask timestamps are clamped and seed ULIDs are content-namespaced. Holds only because no consumer reads subtask-completion time or relies on seed-ULID chronological order — asserted as a precondition. | Technical | Medium | Open |
| C-006 | No dead-symbol / arch-gate drift | The 15-symbol `_CATEGORY_C_DEFERRED_RUNTIME_STATE_BACKFILL_CUTOVER` frozenset in `tests/architectural/test_no_dead_symbols.py` (content-hash pins for the WP03 backfill library) MUST be **removed** in the same WP that first wires a caller — the ratchet + `test_auto_exempt_disjoint_from_hand_allowlist` trips otherwise. `test_2093`'s `_SANCTIONED_READER_MODULES` → `frozenset()`. Updated in-mission, never suppressed; no new `# noqa`/`# type: ignore`. | Technical | High | Open |
| C-007 | Resolved binding never re-reads frontmatter | The recorded resolved `agent_profile`/`role`/`model` MUST be produced by `resolve_profile`/`resolved_agent()` / the dispatch resolution, **never** by copying the frontmatter `agent_profile` string into an event (#2093: copying static intent into events manufactures a *new* split-brain). | Technical | High | Open |
| C-008 | Authored intent and resolved actual never conflated | The reconstruction reader surfaces the frontmatter **authored/recommended** assignment and the event-sourced **resolved actual** as **distinct** values; no consumer treats the authored value as "what ran" or the resolved value as "what was intended". | Technical | Medium | Open |
| C-009 | Field-authority ADR of record | The per-field authority decision (resolved `role`/`agent_profile`/`model` → dynamic/event-log; authored assignment → static/frontmatter) is recorded as an ADR (addendum to `2026-07-19-1`, which deferred model election as blocker B4) before the vocabulary lands — a per-field authority ruling is ADR-worthy per #2093 precedent. | Process | High | Open |
| C-010 | Checkbox removal ordered after seed | The `tasks.md`/WP markdown checkboxes MUST be removed **only after** the backfill has seeded historical subtask completion from them (they are the legacy source `read_legacy_runtime` reads). Removing them earlier strands historical completion (same class as C-001). | Technical | High | Open |
| C-011 | No authored-to-resolved historical fabrication | Superseded during closeout by the binding C-009 ADR's C-007/C-008 ruling: historical authored `role`/`agent_profile`/`model` MUST remain recommendations and MUST NOT be seeded as resolved actuals. Legacy WPs therefore retain an empty resolved binding until a genuine resolver-backed pick-up/claim/reassign records one. Any deterministic authored-derived `resolved_binding` seed rows produced before this correction must be removed precisely by their namespaced seed IDs. | Technical | High | Superseded |

### Key Entities

- **Reduced status snapshot**: the deterministic event→snapshot projection; the sole authority for
  WP runtime state after cutover.
- **`InnerStateChanged` seed events**: deterministic, content-namespaced-ULID seed annotations (+ a
  seed `planned→claimed` transition for claim state) reconstructing pre-eviction frontmatter/checkbox
  state.
- **`LegacyWPRuntime` (old reader)**: the pre-eviction frontmatter/checkbox per-WP view — the ground
  truth verify compares the snapshot against.
- **Phase-1 predicate (`_phase1_snapshot_authority_active`)**: the dual-write flag, keyed on
  `meta.json` `status_phase`; to be deleted.
- **`status_phase` (meta.json)**: the per-mission cutover marker the CLI flips atomically after a
  passing verify (the only writer of this field).
- **Bypass readers (`tasks_move_task.py`, `workflow_cores.py`, `dashboard/scanner.py`, `tasks_status_cmd.py`)**:
  the ungated frontmatter authority reads (#2093 debt) routed onto the snapshot seam.
- **Resolved binding (event-sourced)**: the *actual* `role` + `agent_profile` (+ version) + `model` +
  `provider` that took a WP at a pick-up/claim/reassign transition; folded latest-wins into the snapshot.
- **Authored/recommended assignment (frontmatter)**: the *design-intent* `role`/`agent_profile`/`model`
  authored at tasks-finalize; static, frontmatter-canonical; distinct from the resolved actual.
- **Canonical WP-view reconstruction reader**: the single reader (replacing the three hand-rolled gates)
  that assembles a WP's resolved final-state from the snapshot + authored intent from frontmatter.
- **Structured actor (`spec_kitty_events` 6.1.0 `StatusTransitionPayload.actor`)**: `Union[str, Dict]`
  carrying `{role, profile, tool, model}` — the SaaS delivery vehicle for the resolved binding (FR-015).

## Domain Language *(canonical terms — use consistently)*

- **Authored intent** (a.k.a. *assigned/recommended*, *static design-intent*): who/what a WP was
  designed to be run by — authored once at planning, **frontmatter-canonical**, never mirrored into
  events. Fields: authored `role`/`agent_profile`/`model` recommendation.
- **Resolved binding** (a.k.a. *actual on pick-up*, *dynamic runtime state*): who/what **actually**
  resolved and ran the WP at a given lifecycle transition — **event-log/snapshot-authoritative**,
  latest-wins. Shifts across the lifecycle (implementer→reviewer, model swaps). Produced by
  `resolve_profile`/`resolved_agent()`; never a re-read of the frontmatter string.
- **Canonical authority**: exactly one source per datum — static → frontmatter; dynamic → event log.
  (Terms `authored intent` / `resolved binding` are #2093-ruling vocabulary, pending glossary adoption
  in `docs/context/identity.md` — see C-009.)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of corpus missions are backfilled + verified with **zero** parity mismatches
  before any `status_phase` flip; a fault-injected corrupt seed aborts the run before any flip.
- **SC-002**: `_phase1_snapshot_authority_active` and its facade export have **zero** occurrences in
  the source tree after this mission.
- **SC-003**: `tests/architectural/test_2093_authority_invariant.py` passes with an **empty**
  tolerated-gate set and fails if a frontmatter authority read is reintroduced.
- **SC-004**: A runtime-state transition writes **0 bytes** to `tasks/WP##.md` (byte-identical
  before/after) with the flag removed.
- **SC-005**: `spec-kitty upgrade` migrates a legacy corpus idempotently (second run seeds nothing)
  and no-ops on a fresh install; a verify failure aborts the step with an actionable message.
- **SC-006**: The full `tests/architectural/` suite (per-file) and the `status` suite are green on
  the branch; `ruff` + `mypy` clean with no new suppressions.
- **SC-007**: The dashboard, the `agent tasks status` board, and `WorkPackage` return the **same**
  resolved runtime state for a WP (one shared reconstruction reader; three hand-rolled gates → one).
- **SC-008**: After a WP is implement-claimed (profile P1/model M1) then review-claimed (P2/M2), the
  reconstructed view shows the **current actual** (P2/M2) from the event log — with **0 bytes** written
  to `tasks/WP##.md` — while the authored recommendation remains readable and distinctly labeled. A WP
  with **no** resolved-binding events shows the authored recommendation and an **empty** resolved actual
  (never the authored value masquerading as resolved).
- **SC-009**: The extended #2093 detector flags an attribute-access frontmatter runtime read (e.g. the
  pre-reroute dashboard scanner) **red**, and is green only once every such reader resolves the snapshot.
- **SC-010**: No `- [ ] T###` markdown checkbox remains in `tasks.md`/WP templates; subtask completion is
  read from the snapshot everywhere (dashboard + lane-transition guard); the guard blocks/unblocks
  correctly off the snapshot; agent prompt templates direct `mark-status`. Historical completion was
  seeded before any checkbox removal (C-010).
- **SC-011**: The recorded resolved binding includes the genuine dispatch-resolved `model` (threaded via
  the dispatch→claim linkage), not a frontmatter-coerced value; where a genuine model is unavailable it is
  recorded explicitly absent, never fabricated.

## Out of Scope & Follow-ups

- **`_legacy_lane_mirror_enabled` / `lane` eviction** (C-004) — kept in place; the frontmatter-authored
  `lane` field is a separate concern. **File a follow-up issue** for lane-mirror eviction so that
  `Closes #2093` is defensible (its title frames "generalize the lane retirement"); if the operator
  deems the lane deferral to hold #2093 open, downgrade the PR to `Contributes to #2093`.
- **Inert-field reduction (FR-011 / IC-06 — the deferred #2684 "IC-08")** — if deferred rather than
  landed in-mission, **file a fresh follow-up issue** so nothing tracked in #2816's scope dangles.
- **The "record" slice of the resolved-binding half is now IN SCOPE** (operator decision 2026-07-20):
  FR-012–FR-015 record the resolved `role`/`agent_profile`/`model` actuals and reconstruct the WP view
  from them. **Out of scope remains #2399's full fail-closed *enforcement*** — an agent being unable to
  act without a resolved+recorded profile, across ops/dispatch/ad-hoc/mission-WP. This mission does
  **record + reconstruct**; #2399 owns **enforce**.
- **Escalating to `spec_kitty_events`** — the SaaS delivery (FR-015) rides the **existing** structured
  `actor` on the claim transition (`spec_kitty_events` 6.1.0 already accepts `{role, profile, tool,
  model}`), so **no shared-package change is required** for the preferred path. A new off-axis shared
  event (`WPResolvedBindingChanged`) + a `emit_inner_state_changed` fan-out is the **fallback**, added
  behind a version gate (mirroring the genesis-lane gate) only if an off-transition binding-change event
  is needed. Coordinate the final contract with the SaaS team (already aware).

**Closing posture for the eventual PR:** `Closes #2816` **only if** FR-001–FR-016 land (or FR-011/optional
and any deferred slice are split to filed follow-ups); otherwise `Contributes to #2816`. `Closes #2093`
iff the resolved-binding record + reconstruction (FR-012–FR-014) and the invariant hardening (FR-008)
land and the lane-mirror follow-up is filed. `Contributes to #2400` and `Contributes to #2399` (the
record slice; #2399 stays open for enforcement) — never Closes either. Establish tracker links:
#2400 → {#2093, #2399} → #2816; note downstream dependant #2819 (event-log replay) and co-constraint
#2815 (repo-root write class). *(Tracker refreshed 2026-07-20 — comments posted on #2093/#2400/#2399.)*

## Pre-planning verification note

The concrete code claims in this spec were verified against the post-#2817 tree by a brownfield
point-cut squad (2 lenses). Corrections already folded above: the flag surface is **12 call sites
across 11 files** (not "~10"); FR-006(a) and FR-007-`workflow_cores` are the **same** code block;
FR-002/FR-008/FR-011 are **narrowed** to exclude parts already shipped in #2817; `done_bookkeeping.py`
lives under `merge/`; the upgrade migration is **auto-discovered** (no registry-list edit); and the
15-symbol dead-symbol frozenset must be un-pinned in the CLI-wiring WP.

## Assumptions

- **Inert-field reduction (FR-011 / IC-06 — the deferred #2684 "IC-08") is optional/deferrable** — the
  mission's Definition of Done rests on **US1–US4 + US6 (FR-001–FR-010, FR-012–FR-015)**; FR-011/US5 and
  any deferred slice split to filed follow-ups.
- **`_legacy_lane_mirror_enabled` is kept** (C-004); evicting the frontmatter-authored `lane` field
  is a separate follow-up, out of scope here.
- **The upgrade migration auto-runs** backfill+verify (fail-closed) as a sequenced upgrade step,
  mirroring the charter.yaml fold; it does not require a separate operator opt-in.
- **Not a DIRECTIVE_035 bulk edit** — collapsing the flag branches is a heterogeneous per-site
  refactor (each call site collapses differently), not a mechanical token rename, so no
  `occurrence_map.yaml` is required. (Re-evaluated at plan if the flip proves mechanically uniform.)
- **The WP03 backfill library is complete and correct** (seed backfill + fail-closed verify that
  catches value tampering regardless of ULID fold order); this mission wires + invokes it, and does
  not re-derive it.
- **Resolved-binding scope (operator decision 2026-07-20)**: `role`/`agent_profile`/`model` **actuals**
  are event-sourced (all three), distinct from the frontmatter **authored** recommendation, because the
  actual identity shifts across the WP lifecycle. This mission owns **record + reconstruct** (FR-012–015);
  #2399 owns the full fail-closed **enforcement**.
- **SaaS delivery rides the existing structured `actor`** (`spec_kitty_events` 6.1.0), so no shared-package
  release blocks this mission; a new off-axis shared event is a version-gated fallback only.
- **`role` is treated as a resolved actual** here (per the #2093 ruling text), reversing the earlier
  interim "keep role frontmatter" note — the authored role recommendation still lives in frontmatter, but
  the *actual* role that ran is event-sourced. Ratified in the C-009 ADR.
