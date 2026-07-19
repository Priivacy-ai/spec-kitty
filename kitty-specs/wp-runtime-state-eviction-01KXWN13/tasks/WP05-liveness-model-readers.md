---
work_package_id: WP05
title: Liveness + model readers
dependencies:
- WP01
- WP03
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: mission-prep/2684-wp-runtime-state-eviction
merge_target_branch: mission-prep/2684-wp-runtime-state-eviction
branch_strategy: Planning artifacts for this mission were generated on mission-prep/2684-wp-runtime-state-eviction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission-prep/2684-wp-runtime-state-eviction unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/stale_detection.py
create_intent:
- tests/specify_cli/core/test_stale_detection_snapshot_liveness.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/stale_detection.py
- src/specify_cli/task_utils/support.py
- src/specify_cli/status/wp_metadata.py
role: implementer
tags: []
shell_pid: "2682167"
shell_pid_created_at: "1784461922.96"
---

# Work Package Prompt: WP05 – Liveness + model readers

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load python-pedro` and adopt that profile before touching any
code. You are Python Pedro: TDD, type hints on every public API, and the full quality
gate (`pytest`, `ruff`, `mypy`) before handoff. The reduced-snapshot slot set
(`shell_pid`, `shell_pid_created_at`, `agent`, `assignee`, …) and the reducer fold are
delivered by WP01 and are authoritative; the migration/backfill + fail-closed verify +
the FR-005 fallback flag are delivered by WP03. Consume them — do not redesign the
snapshot shape or the flag.

## Objective

Re-source the runtime **readers** from the reduced snapshot: claim-liveness
(`stale_detection.py`, T018), the `WorkPackage.{shell_pid,agent,assignee}` model
properties (`task_utils/support.py`, T019), and `WPMetadata` coercion
(`status/wp_metadata.py`, T020) all resolve `shell_pid`/`agent`/`assignee` from the
event-sourced snapshot instead of parsing WP frontmatter — with the frontmatter path
retained **behind the FR-005 flag** until backfill is verified. Prove the decision
source is the snapshot with a **two-sided** liveness test (T021): a live snapshot PID
under empty frontmatter reads live, and mutating the **snapshot** PID to a dead value
flips it stale (SC-002 / AC-2 / US3). Closes the resume false-stale window by
construction (NFR-004).

## Context

- **Design of record**: ADR 2026-07-19-1.
- **FR-005**: claim-liveness (`stale_detection.py:402-403`) and model readers
  `WorkPackage.{shell_pid,agent,assignee}` (`task_utils/support.py:287-296`) +
  `WPMetadata` coercion resolve from the reduced snapshot; the frontmatter fallback is
  **retained behind a flag until backfill is verified, then torn down by this WP**.
  **Flag-teardown ownership**: WP05 OWNS the teardown of the
  `status/emit.py::_phase1_dual_write_enabled` dual-write usage in its own files
  (`stale_detection.py`) at this vertical's completion — gated after its reader cutover
  verifies (WP03 fail-closed verify has passed). This is **NOT** deferred to WP10; WP10
  only **verifies** via the FR-013 arch test that no dual-write path remains.
- **C-001 (symmetric window)**: this is the **reader** half of a per-field atomic
  switch. A snapshot-first reader must never consult the frontmatter fallback once a
  slot is backfilled — hence the flag gates authority, not a permanent dual read.
  Authority activation depends on WP03's fail-closed verify (why this WP depends on
  WP03).
- **SC-002 (AC-2), two-sided**: with empty frontmatter and a live PID in the snapshot,
  liveness = live; mutating the **snapshot** PID to a dead value flips it to stale
  (pins the snapshot as the decision source, not the frontmatter).
- **NFR-004**: a resumed `in_progress` WP is never falsely flagged stale due to a
  missing frontmatter `shell_pid` (0 false-stale on resume).
- **Key facts (two-sided liveness + fallback flag)**: the test must exercise *both*
  polarities off the **snapshot** — a live-then-dead flip driven by mutating the
  snapshot slot, not the frontmatter. The frontmatter read stays as a flagged fallback
  only during the migration window; **WP05 tears down its own dual-write fallback in
  `stale_detection.py`** once its reader cutover verifies (gated on WP03's fail-closed
  verify) — WP10 does not delete it, it only verifies via the FR-013 arch test. FR-013
  forbids a second permanent authority read path — the snapshot is the single authority
  once the flag resolves to it.

### Subtask T018 — Claim-liveness `stale_detection` → snapshot (behind flag)

**Purpose**: The staleness check must trust the snapshot's `shell_pid` /
`shell_pid_created_at` as the claim-liveness source, so a claimed WP with empty
frontmatter still reads live (and a resumed WP's refreshed PID keeps it live).

**Steps** (file:line-grounded in `stale_detection.py`):
1. Today `check_wp_staleness(wp_id, worktree_path, threshold_minutes=10, shell_pid=None,
   shell_pid_baseline=None)` (`:254-260`) takes `shell_pid`/`shell_pid_baseline` as
   frontmatter-extracted strings and `_is_claiming_process_alive(shell_pid,
   shell_pid_baseline)` (`:221`) decides liveness (`process_liveness.is_process_alive`
   / `is_claiming_process_alive`, `:250-251`). The frontmatter source is the caller's
   `WorkPackage.shell_pid` (T019) — so this vertical moves together.
2. Add a snapshot-first resolution: given `feature_dir`/`wp_id`, read
   `snapshot.work_packages[wp_id].{shell_pid, shell_pid_created_at}` (the WP01 slots)
   and pass those to `_is_claiming_process_alive`. When the FR-005 flag resolves to the
   snapshot, the snapshot values win; when off (pre-verify), fall back to the
   frontmatter values the caller still supplies. Keep the conservative contract
   (absent/unparseable PID → not provably alive → timestamp heuristic applies,
   `:226-228`).
3. Do **not** change the timestamp-heuristic logic (`get_last_meaningful_commit_time`,
   `:130`) or the `StaleCheckResult`/`StaleState` shapes — only the source of the
   `shell_pid` inputs changes.
4. Import the reducer via the same entry the rest of `status` uses (no new read path).

**Files**: `src/specify_cli/core/stale_detection.py`.

**Validation**: a claimed WP with **empty frontmatter** but a live PID in the snapshot
→ `check_wp_staleness` returns not-stale (live-claim suppression). A resumed WP whose
snapshot PID was refreshed via an `InnerStateChanged` delta stays live. Flag off →
today's frontmatter behavior, zero regression.

**Edge cases**: legacy claim (no `shell_pid_created_at`/baseline) preserves today's
live-PID trust (D3a, `:249-250`). Recycled PID (baseline mismatch) → not alive. No
worktree → `fresh` early return unchanged (`:296-301`).

### Subtask T019 — `WorkPackage.{shell_pid,agent,assignee}` + Activity Log / History render → snapshot

**Purpose**: The `WorkPackage` model properties that liveness and orchestration read
must return the event-sourced values, not `extract_scalar` off frontmatter bytes — **and**
the `## Activity Log` / `## History` render that `task_utils/support.py` produces must be
re-sourced to fold `notes`/history from the reduced snapshot (the event log), not the
WP-file body, so **SC-004 ("renders from events with no content loss") is actually
delivered** by this vertical.

**Steps** (file:line-grounded in `task_utils/support.py`):
1. `WorkPackage` currently exposes `assignee` (`:287-288`), `agent` (`:291-292`),
   `shell_pid` (`:295-296`) as `extract_scalar(self.frontmatter, "<key>")`. Re-point
   each to the reduced snapshot slot for the WP (`snapshot.work_packages[wp_id].{...}`),
   behind the FR-005 flag with the `extract_scalar` frontmatter read as the tolerated
   fallback.
2. Resolve `feature_dir`/`wp_id` the way the existing `lane` property does
   (`:298-306`: `feature_dir = self.path.parent.parent`; `wp_id = extract_scalar(...,
   "work_package_id") or self.path.stem.split("-")[0]`) — reuse that exact derivation so
   the snapshot lookup keys match.
3. Keep the return types (`str | None`) identical — `shell_pid` stays a `str | None`
   here (the snapshot stores `int | None`; coerce to `str` at this boundary to preserve
   the caller contract that `stale_detection` and orchestration already depend on).
4. Do **not** re-point `title`/`work_package_id` (`:279-284`) — those are static
   design-intent and stay frontmatter-canonical (field-authority table).
5. **SC-004 render re-point**: locate the `## Activity Log` / `## History` render in
   `task_utils/support.py` and re-source it to fold the `notes`/history from the reduced
   snapshot (the event-sourced `notes` slot + transition/annotation history), **not** the
   `## Activity Log` / `## History` sections parsed out of the WP-file body. Behind the
   FR-005 flag with the body-parse retained as the tolerated migration-window fallback,
   consistent with the other readers here. The render must fold from events with **no
   content loss** — every note/history entry the body carried must still appear.
6. Reuse the same canonical reducer entry as the property re-points (steps 1-2) — do NOT
   introduce a second parser/read path for the render (#2093 / FR-013).

**Files**: `src/specify_cli/task_utils/support.py`.

**Out-of-map note**: `cli/commands/agent/tasks.py` **also** renders `## Activity Log` /
`## History` and is **NOT** in this WP's `owned_files`. If that renderer must be
re-sourced in lockstep to keep SC-004 whole, flag it to the reviewer/orchestrator as a
**documented out-of-map edit** (or a WP10 follow-up) rather than silently widening
ownership. Do not edit it without that explicit sign-off.

**Validation**: `WorkPackage.shell_pid` returns the snapshot PID (as `str`) when the
flag resolves to the snapshot; `agent`/`assignee` likewise. With the flag off, returns
the frontmatter value. Type signatures unchanged (`mypy` clean). The rendered `## Activity
Log` / `## History` (flag on) reproduces every note/history entry from the event-sourced
snapshot with no content loss; the WP10 golden test (`test_render_parity_golden.py`) is
the mission-level parity guard.

**Edge cases**: a WP file whose frontmatter has no `work_package_id` still resolves the
id via `path.stem` (matches `lane`). Empty snapshot slot → `None` (or flagged
fallback). Do not eagerly reduce on every property access if it is hot — cache/reduce
once per `WorkPackage` if the existing pattern allows, but never at the cost of
correctness. A WP whose body carries legacy `## Activity Log` lines not yet backfilled
must still render them via the tolerated fallback (no content loss mid-migration).

### Subtask T020 — `WPMetadata` coercion → snapshot

**Purpose**: `WPMetadata` (the typed Pydantic read-model of WP frontmatter) must not
present runtime fields (`shell_pid`, `shell_pid_created_at`, `agent`, `assignee`) as if
frontmatter were their authority — the coercion resolves them from the snapshot.

**Steps** (file:line-grounded in `status/wp_metadata.py`):
1. `WPMetadata` declares `shell_pid: int | None` (`:251`), `shell_pid_created_at: str |
   None` (`:258`), `assignee: str | None` (`:246`), `agent: Any` (`:247`), plus the
   agent-resolution helpers (`_resolve_agent_from_*`, `:24-179`). Re-point the runtime
   fields' **read authority** to the snapshot: where a consumer reads
   `WPMetadata.shell_pid`/`agent`/`assignee` as *runtime* state, resolve from the
   reduced snapshot, behind the FR-005 flag.
2. Keep `agent_profile` (`:249`) and the authored/static fields (`title`, `dependencies`,
   `owned_files`, …) frontmatter-canonical — `agent_profile` is authored design-intent,
   distinct from the runtime `agent` reassignment slot (data-model field-authority
   table). Do **not** collapse the two.
3. **Do not** delete the inert model fields (`history`, `activity_log`,
   `coerce_shell_pid`, `reviewer_shell_pid`, `:255-272`) — that is the deferred IC-08
   post-cutover reduction, explicitly out of scope for this mission (tasks.md
   "Deferred"). This WP only re-points the read authority; it leaves the model surface
   intact so legacy on-disk WPs still parse mid-migration.
4. Preserve the `model_validator(mode="before")` legacy normalization (`:288+`) — it
   handles mission-004-shaped frontmatter and must keep parsing.

**Files**: `src/specify_cli/status/wp_metadata.py`.

**Validation**: a `WPMetadata` read of a WP with empty runtime frontmatter but a
populated snapshot returns the snapshot's `shell_pid`/`agent`/`assignee` (flag on);
legacy WPs still parse; `agent_profile` still comes from frontmatter.

**Edge cases**: dict-shaped legacy `agent` (`:247` comment) still resolves via
`_resolve_agent_from_dict` for the *authored* fallback; the runtime reassignment slot
is the snapshot `agent`. Empty snapshot → flagged frontmatter fallback, no crash.

### Subtask T021 — Two-sided liveness test (dead snapshot PID flips stale)

**Purpose**: Pin the **snapshot** as the liveness decision source with both polarities
(SC-002), proving the reader re-point is real and not a frontmatter passthrough.

**Steps**:
1. Create `tests/specify_cli/core/test_stale_detection_snapshot_liveness.py` (new;
   sits beside `tests/specify_cli/core/test_process_liveness.py`).
2. **Live side**: build a WP fixture with **empty frontmatter** (`shell_pid` blank) and
   a snapshot whose `subtasks`-adjacent `shell_pid` slot holds a **live** PID
   (`os.getpid()` is guaranteed alive). Assert `check_wp_staleness(...)` (via the
   snapshot-first path, flag on) returns not-stale — the live-claim suppression fires
   from the snapshot despite empty frontmatter.
3. **Dead side**: mutate the **snapshot** PID slot to a value that is provably dead
   (e.g. a never-live PID sentinel or a reaped PID) — do **not** touch the frontmatter.
   Assert `check_wp_staleness(...)` now falls through to the timestamp heuristic and
   flips stale (with an over-threshold last-commit). The flip must be driven by the
   snapshot mutation alone.
4. Resume-window control (NFR-004): a WP whose snapshot PID was refreshed via an
   `InnerStateChanged` delta after resume stays live even with no frontmatter PID.
5. Use the same reducer entry as production; do not stub a private read path.

**Files**: `tests/specify_cli/core/test_stale_detection_snapshot_liveness.py` (create).

**Validation**: both assertions pass; the dead-side flip is provably caused by the
snapshot mutation (assert frontmatter untouched). `ruff`/`mypy` clean on the test.

**Edge cases**: avoid PID-reuse flakiness — use `os.getpid()` for live and a guarded
never-alive sentinel for dead (or monkeypatch `is_process_alive`/`is_claiming_process_
alive` at the `core.process_liveness` seam to make the two polarities deterministic).
Cover the baseline-mismatch (recycled PID) case as a third assertion if cheap.
- 2026-07-19T11:19:37Z – claude:opus:python-pedro:implementer – shell_pid=2536901 – Assigned agent via action command
- 2026-07-19T11:51:17Z – claude:opus:python-pedro:implementer – shell_pid=2536901 – Ready: snapshot readers (flag-gated), two-sided liveness, SC-004 render re-point
- 2026-07-19T11:52:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=2682167 – Started review via action command
- 2026-07-19T11:55:46Z – user – shell_pid=2682167 – Review passed: T018-T021 verified. Snapshot-first readers (stale_detection claim-liveness, WorkPackage.{shell_pid,agent,assignee}, WPMetadata runtime fields) flag-gated behind _phase1_dual_write_enabled; flag-off/feature_dir-omitted paths proven byte-identical (2 zero-regression tests). T021 two-sided liveness pins snapshot as decision source (dead-side flip driven by InnerStateChanged annotation alone, args unchanged) + baseline-mismatch + resume-refresh. SC-004 activity fold adds event-sourced rows without content loss; existing callers unchanged. Readers reached by production (check_doing_wps_for_staleness passes feature_dir; properties/read_wp_frontmatter live). Scope confined to owned_files + 1 new test. 31 tests green; mypy 5 errors all pre-existing (verified vs base, zero new). Out-of-map cli/commands/agent/tasks.py and deferred flag-teardown accepted per WP prompt.

## Branch Strategy

`lane-per-wp`. Planning base and merge target are both
`mission-prep/2684-wp-runtime-state-eviction`. Rebases onto WP01 (snapshot slots +
reducer fold) and WP03 (backfill + fail-closed verify + FR-005 flag). Runs in the
parallel band with WP06/WP07/WP08/WP09; owns disjoint files so no writer-race with the
`tasks_*` command WPs.

## Definition of Done

- T018: `stale_detection` resolves claim-liveness from the snapshot `shell_pid` /
  `shell_pid_created_at`, frontmatter behind the FR-005 flag; conservative + timestamp
  heuristics unchanged.
- T019: `WorkPackage.{shell_pid,agent,assignee}` return snapshot values (flag on),
  frontmatter fallback (flag off); return types unchanged; static fields untouched. The
  `## Activity Log` / `## History` render is re-sourced to fold `notes`/history from the
  reduced snapshot (SC-004, no content loss); the unowned `cli/commands/agent/tasks.py`
  renderer is flagged as a documented out-of-map edit if it must move in lockstep.
- T020: `WPMetadata` runtime-field read authority is the snapshot; inert IC-08 fields
  left in place; `agent_profile`/authored fields still frontmatter-canonical.
- T021: two-sided snapshot liveness test lands and passes (live + dead-flip + resume
  control).
- **WP05 removes its own dual-write fallback** (`_phase1_dual_write_enabled` usage in
  `stale_detection.py`) once its reader cutover verifies (gated on WP03's fail-closed
  verify); **WP10 only verifies** this via the FR-013 arch test — WP05 does not defer its
  own teardown to WP10.
- `pytest` (touched paths + new test), `ruff`, `mypy` all clean.

## Risks

- **Deleting the fallback too early**: removing the frontmatter path before WP03's
  fail-closed verify passes strands un-migrated on-disk WPs. Keep it flagged **until this
  WP's reader cutover verifies**, then WP05 tears down its own dual-write in
  `stale_detection.py` (this teardown is owned here, not deferred to WP10 — WP10 only
  verifies via the FR-013 arch test).
- **One-sided test theatre**: a live-only assertion can pass on a frontmatter
  passthrough. The dead-side flip **must** be driven by the snapshot mutation (SC-002).
- **Type drift at the boundary**: snapshot stores `shell_pid: int`; `WorkPackage.shell_
  pid` contract is `str | None`. Coerce at the property, keep the signature.
- **Second read path (#2093)**: resolving the snapshot via a bespoke parser instead of
  the canonical reducer entry creates a dual authority. Reuse the `status` reducer.
- **Scope creep into IC-08**: do not delete inert `WPMetadata` fields/coercions here.

## Reviewer guidance

- Verify the dead-side of T021 flips stale by mutating **only** the snapshot PID (assert
  frontmatter bytes unchanged) — the two-sided proof is the whole point.
- Confirm WP05 tears down its **own** `_phase1_dual_write_enabled` dual-write fallback in
  `stale_detection.py` once its reader cutover verifies (gated on WP03) — this teardown is
  owned here, not punted to WP10; WP10 only verifies via the FR-013 arch test.
- Confirm the `## Activity Log` / `## History` render folds from the event-sourced
  snapshot with no content loss (SC-004), and that any lockstep edit to the unowned
  `cli/commands/agent/tasks.py` renderer was surfaced as a documented out-of-map edit,
  not made silently.
- Confirm `stale_detection` still applies the timestamp heuristic when no PID is
  provably alive (no behavior regression when the flag is off).
- Confirm `agent_profile` and authored/static fields still resolve from frontmatter
  (field-authority table not violated).
- Confirm the snapshot is read via the canonical reducer entry, not a new parser.
