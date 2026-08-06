---
work_package_id: WP05
title: Reader collapse — ALL verdict readers die atomically + .md demote
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-006
- FR-008
- FR-013
planning_base_branch: feat/verdict-seam-write-unification
merge_target_branch: feat/verdict-seam-write-unification
branch_strategy: Planning artifacts for this mission were generated on feat/verdict-seam-write-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verdict-seam-write-unification unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
- T027
- T028
- T029
history: []
agent_profile: reviewer-renata
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
- src/specify_cli/cli/commands/agent/tasks_parsing_validation.py
- src/specify_cli/agent_utils/status.py
- src/specify_cli/post_merge/review_artifact_consistency.py
- src/specify_cli/review/artifacts.py
- src/specify_cli/review/cycle.py
- src/specify_cli/cli/commands/agent/workflow_cores.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- src/specify_cli/cli/commands/agent/workflow.py
- tests/architectural/test_2093_authority_invariant.py
- tests/integration/test_review_durability_matrix.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned profile: run `/ad-hoc-profile-load reviewer-renata` (or
`spec-kitty charter context --action implement`). Do not start work until the profile is loaded.
> Profile note: this WP is safety-critical (fail-open surface). It is assigned a review-grade lens for
> implementation; if your harness routes implementers to `python-pedro`, load that instead but hold the
> single-authority invariant as the acceptance bar.

## Objective

Repoint **every** verdict reader to the event authority `event_sourced_review_result`, retire the
`review/artifacts.py` verdict-parser family, delete the two frontmatter verdict readers, and **demote
the `.md` commit to best-effort** — all in **one atomic WP**. Once this lands, no consumer reads the
`.md` for a verdict, so the later schema/placement changes (WP06) are non-safety-critical.

## ⚠️ This WP MUST NOT be split
Two distinct binding reasons (both real; the no-split conclusion holds either way — squad #14):

- **Atomicity-bound** — the reader-repoint + `.md`-demote subtasks (**T023, T024, T025, T026**). Any
  interval where one reader is on the snapshot and another still parses `.md` **reopens the fail-open
  window** on `_guard_rejected_verdict` (post-spec squad finding; US1/US2): a rejected WP could be
  approved. These MUST land in one atomic wave.
- **Serialization / C-004-bound** — the derived-ratchet + durability re-point + census-row subtasks
  (**T027, T028, T029**). These share `verdict_seam_census.yaml` (shrinkage-red, C-004) and the
  durability anchors; they must land in the same change as the retirements they enumerate, and cannot
  race a parallel census lane.

Land them together or not at all.

## Context

- **Requirements**: FR-002 (single verdict authority), FR-004 (all readers on the event authority as a
  **derived ratchet**), FR-013 (merge gate pure-event), FR-003 (parser-family retirement), FR-006
  (reader-row + merge-gate-leg census shrink), FR-008 (**demote** the `.md` commit here — D-PLAN-11),
  and the FR-001 no-partial-order-fail-open guarantee delivered by ordering. SC-002/003/004.
- **Contracts**: [verdict-authority-read.md](../contracts/verdict-authority-read.md) (consumers, the
  three-way `ReviewResultLookup`, fail-closed on damaged/absent),
  [verdict-durability-write.md](../contracts/verdict-durability-write.md) (the demote).
- **Decisions**: **D-PLAN-9** (the approval-write probe `tasks_verdict_persistence.py:535` is a genuine
  frontmatter **verdict** read pulled into the atomic wave). **D-PLAN-11** (demote lands with the flip),
  **D-PLAN-13** (re-point the durability matrix anchors to count **event** records, not `.md` files).
- **⚠️ Scope correction (squad #1 — corrects a misdiagnosis carried from the D-PLAN-9 framing)**: the
  genuine verdict-parser functions are **only** `latest_review_artifact_verdict` and
  `rejected_review_artifact_for_terminal_lane`. **`ReviewCycleArtifact.latest` and `.from_file` are
  CONTENT / cycle-number loaders, NOT verdict readers** — verified live: `arbiter.py:461` uses `.latest`
  only for `cycle_number` (the override WRITE path, never `.verdict`); `workflow_executor.py:1116-1117`
  uses `.from_file`/`.latest` for the reviewer's feedback **prose body** in the fix prompt;
  `latest_review_artifact_verdict` does its **own** glob and does not call `.latest`. The census files
  all four under `reader` on a structural "parses frontmatter" shape, not "reads a verdict."
  **KEEP `.latest` + `.from_file` (census `status: active`, note "content loader, not verdict
  authority") — deleting them reds fix-mode (`workflow_executor.py:1117`) and strands the arbiter
  (writes `review-cycle-0.md`).** This is consistent with D3 (the artifact stays a written prose record).
- **Provenance interlock (SC-008)**: before deleting the frontmatter readers, **import and call** WP02's
  pure provenance function (`verdict_provenance_backfill.stranded_verdict_findings`) and assert it
  returns **zero** stranded findings (squad F7 — no `--json`/CLI dependency; WP02 owns only the migration
  module). This is the designed safety interlock — the reader-deletion subtask is gated on it.

Verified anchors: approval guard `resolve_review_verdict_facts` (`tasks_verdict_persistence.py:386`);
approval-write probe `latest_review_artifact_verdict(sub_artifact_dir)` (`:535`); the **two genuine
verdict functions** in `review/artifacts.py` — `latest_review_artifact_verdict:385`,
`rejected_review_artifact_for_terminal_lane:424`. Content loaders **kept**: `ReviewCycleArtifact.latest`
(`:332`), `.from_file` (`:277`).

## Subtasks

### T021 — Provenance interlock (SC-008) — run FIRST, block on non-zero
- **Purpose**: Guarantee no historical verdict is stranded before any reader dies.
- **Steps**: **Import** `stranded_verdict_findings` from WP02's `verdict_provenance_backfill.py` and
  **call** it (squad F7 — a pure function, not a `--json`/CLI gate; keeps ownership clean since WP02
  owns only the migration module). Assert it returns zero "terminal `.md` verdict + no event slot"
  findings. Encode this as a test that **blocks** the reader-deletion subtasks (T025/T026) until clean
  (US6 scenario 2). If findings remain, run the WP02 backfill first.
- **Files**: `tests/architectural/test_2093_authority_invariant.py` (or a sibling interlock test).
- **Validation**: green only when `stranded_verdict_findings(...)` is empty.

### T022 — Red-first: snapshot-vs-frontmatter disagreement (US1)
- **Purpose**: The single-authority anchor. A WP whose reducer snapshot says `rejected` but a stray
  `.md` says `approved` (and the inverse) must be read as the **snapshot** by every reader.
- **Steps**: Build the disagreement fixture; assert the approval guard refuses on snapshot-rejected
  regardless of `.md` (US1 scenario 1), the board shows the snapshot verdict (US1 scenario 2), and a
  damaged record fails closed (US1 scenario 3). Red-first against the current frontmatter readers.
- **Files**: `tests/architectural/test_2093_authority_invariant.py`, `tests/review/` fixtures.
- **Validation**: fails before the repoints; green after.

### T023 — Repoint the approval guard + approval-write probe (safety core)
- **Purpose**: FR-002 / D-PLAN-9. The two safety-critical readers move to the snapshot together.
- **Steps**: In `tasks_verdict_persistence.py`, repoint `resolve_review_verdict_facts` (`:386`) and the
  approval-write probe (`:535`, currently `latest_review_artifact_verdict(sub_artifact_dir)`) to
  `event_sourced_review_result`. Honour the three-way `ReviewResultLookup`: **absent** → no approval,
  **damaged** → fail-closed (never approve, never crash), **present** → the verdict. Remove the
  `from specify_cli.review.artifacts import latest_review_artifact_verdict` import.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`.
- **Validation**: US1 scenario 1 + SC-004 damaged-record path green.

### T024 — Repoint dashboard/board + status display + fix-mode
- **Purpose**: FR-004 — the non-gate readers (reviews slice of #2093 only).
- **Steps**: Repoint `agent_utils/status.py::show_kanban_status` / `_get_wp_review_verdict` and the
  review/verdict fields of the status display to the snapshot. Repoint fix-mode `has_prior_rejection` /
  `implement_try_render_fix_mode_prompt` raw joins in `workflow_cores.py`/`workflow_executor.py`/
  `workflow.py` to the snapshot. Delete `_get_latest_review_cycle_verdict` in `tasks_parsing_validation.py`.
- **Files**: `agent_utils/status.py`, `workflow_cores.py`, `workflow_executor.py`, `workflow.py`,
  `tasks_parsing_validation.py`.
- **Validation**: US1 scenario 2 (board shows snapshot); fix-mode reads the snapshot.

### T025 — Merge gate → pure-event; retire ONLY the two verdict functions (FR-013 + FR-003)
- **Purpose**: FR-013 (D-PLAN-8) — `find_rejected_review_artifact_conflicts` reads only the event
  authority; the `_artifact_dirs_for_wp` + `_resolve_terminal_verdict_conflict` artifact-frontmatter
  leg are **retired** (not repointed). FR-003 — retire the **two genuine verdict-parser functions**
  `latest_review_artifact_verdict` (`:385`) and `rejected_review_artifact_for_terminal_lane` (`:424`).
- **⚠️ KEEP `ReviewCycleArtifact.latest` + `.from_file` (squad #1)**: they are content / cycle-number
  loaders, **not** verdict readers (see the Scope-correction bullet above). Do **not** delete or repoint
  them — `workflow_executor.py:1117` (fix-mode prose) and `arbiter.py:461` (cycle_number for the
  override write) depend on them. Mark them census `status: active` with the note "content loader, not
  verdict authority" (in T029).
- **Steps**: Repoint the merge gate in `post_merge/review_artifact_consistency.py`; delete the artifact
  leg; delete only the two verdict functions from `review/artifacts.py` (leave the prose/`from_dict`
  shell **and** `.latest`/`.from_file` intact — do **not** remove the `verdict` field here, that is WP06
  and would break `from_dict` ordering per D-PLAN-12). Sweep the WP04-deferred inline-vocab in
  `cycle.py:794` + `review_artifact_consistency.py` (import+call `verdict_vocab`), then **remove those
  two entries from WP04's guard allowlist** (`tests/architectural/test_verdict_vocab_single_source.py` —
  out-of-map, rationale: guard-lands-last).
- **Files**: `post_merge/review_artifact_consistency.py`, `review/artifacts.py`, `review/cycle.py`;
  out-of-map `tests/architectural/test_verdict_vocab_single_source.py`.
- **Validation**: WP04's guard is green with an **empty** allowlist; merge gate resolves via events;
  fix-mode (`workflow_executor.py`) and arbiter cycle-number resolution still work (`.latest`/`.from_file`
  intact).

### T026 — Demote the `.md` commit to best-effort (FR-008 / D-PLAN-11)
- **Purpose**: With every reader on the snapshot, the `review-cycle-N.md` commit becomes non-authoritative.
- **Steps**: In `review/cycle.py`, demote the per-file `.md` commit from hard-error to **best-effort**
  (warn, not raise); retire the retry/hard-error/orphan-cleanup as the *authoritative* path (keep at
  most as best-effort-render defense). The authoritative durable act is WP03's `emit_status_transition`
  append. NFR-004: the `.md` render commit is excluded from the one-authoritative-call count.
- **Files**: `src/specify_cli/review/cycle.py`.
- **Validation**: a best-effort render failure does **not** error the verdict recording; the event slot
  is still authoritative.

### T027 — Extend `test_2093` derived ratchet (FR-004 enforcement)
- **Purpose**: FR-004/SC-002 non-vacuous enforcement (D-PLAN-4, belt + suspenders with the census).
- **Steps**: In `test_2093_authority_invariant.py` add `agent_utils`/`review`/`post_merge` to
  `_READER_AUTHORITY_ROOTS`, add a `review-cycle-*.md`-glob detector arm, add `verdict` to the tracked
  fields, and add a **synthetic-poison non-vacuity test** (a fake reader parsing `.md` frontmatter reds
  the ratchet).
- **Files**: `tests/architectural/test_2093_authority_invariant.py`.
- **Validation**: poison reds; the real tree passes.

### T028 — Re-point the durability matrix anchors to count EVENT records (D-PLAN-13) + negative control
- **Purpose**: `test_review_durability_matrix.py`'s SC-003 anchor asserts on `.md` files + clean git —
  the exact `.md`-commit property the mission retires; post-demote it would red. A naive re-point is
  **vacuously greenable** (squad #4) — so it must be proven to fail when a durable event is dropped.
- **Steps**: Re-point SC-003 to assert **≥2 distinct durable event records OR one explicit refusal**
  (`read_events`/reducer slots). Re-point NFR-004's "exactly one authoritative call" verifier to count
  the `emit_status_transition` append == 1 (the `.md`/`commit_artifact` observation becomes best-effort,
  not the authoritative count). **Add a negative control**: deliberately drop one durable event (e.g.
  monkeypatch one process's append to a no-op) and assert the re-pointed test goes **RED** — proving the
  assertion is not vacuous. These pins are **rewritten**, not greened as-is.
- **Files**: `tests/integration/test_review_durability_matrix.py`.
- **Validation**: `PWHEADLESS=1 pytest tests/integration/test_review_durability_matrix.py -n0 -q`
  (50×2 processes) green counting events; the negative-control case reds when an event is dropped.

### T029 — Census reader-row + merge-gate-leg shrink (FR-006) + SC-004 parametrized damaged test
- **Purpose**: FR-006/C-004 — every retirement lands in the census in the same change. SC-004 — a
  parametrized damaged-record test over **every** census safety-gate reader.
- **Steps**: Out-of-map edit WP01's `verdict_seam_census.yaml`: mark the **two deleted verdict
  functions** (`latest_review_artifact_verdict`, `rejected_review_artifact_for_terminal_lane`) + the
  retired merge-gate artifact leg as `status: retire` with `retiring_fr` (safe — serial after WP02).
  **Keep `ReviewCycleArtifact.latest` + `.from_file` as `status: active`** with the note "content
  loader, not verdict authority" (squad #1 — they are not verdict readers). Add a parametrized test
  iterating the census safety-gate readers, asserting each fails closed on a damaged record (SC-004),
  not "preserved natively" reasoning.
- **Files**: out-of-map `tests/architectural/verdict_seam_census.yaml`; a test in `tests/review/` or
  `tests/architectural/`.
- **Validation**: `pytest tests/architectural/test_verdict_seam_census.py -q` green (derived == fixture).

## Branch Strategy note

`already-confirmed`; base == target. Prepare with `spec-kitty implement WP05`. Hard-gated on WP02
(authority populated + provenance gate), WP03 (durability), WP04 (bridge). Serial in the census chain.
WP06/WP07/WP09 depend on this WP. **Do not split.**

## Definition of Done

- SC-002: zero consumers (gates, board, status display, fix-mode) parse artifact frontmatter for a
  verdict — enforced by the extended `test_2093` ratchet (T027) **and** the census (T029).
- SC-003 (T028, event-counted) + SC-004 (T029 parametrized damaged test) green.
- SC-008 interlock (T021) clean before any reader deletion. The **two genuine verdict functions**
  (`latest_review_artifact_verdict`, `rejected_review_artifact_for_terminal_lane`) + the two frontmatter
  readers + merge-gate artifact leg retired with matching census rows; `ReviewCycleArtifact.latest` +
  `.from_file` **kept active** (content loaders). `.md` demoted (T026).
- **BLOCKING acceptance check (squad #15)**: WP04's guard allowlist in
  `tests/architectural/test_verdict_vocab_single_source.py` is **empty** at the end of this WP — assert
  it programmatically (e.g. the guard is run with a zero-length allowlist). A non-empty allowlist
  **fails** this WP; it is not advisory.
- Gate: `pytest tests/architectural/test_2093_authority_invariant.py`
  `tests/architectural/test_verdict_seam_census.py`
  `tests/specify_cli/cli/commands/agent/test_tasks_parsing_validation.py tests/review/ -q`,
  plus the `-n0` durability matrix; `ruff` + `mypy --strict src/specify_cli/review src/specify_cli/status`
  clean (NFR-003).

## Risks

- **Fail-open on a partial repoint** — the entire reason for no-split. Land T023–T025 together.
- **Durability anchor mis-count** — T028 must count events, not `.md` (renata F1/F2); a wrong re-point
  silently passes on the old property.
- **Removing the `verdict` field here** — do **not** (D-PLAN-12); it breaks `from_dict` before WP06
  retires the parser family's schema. Only *retire the parser functions*, not the field.

## Reviewer guidance

Trace every consumer in [verdict-authority-read.md](../contracts/verdict-authority-read.md) to
`event_sourced_review_result`. Grep `src/` for surviving `review-cycle-*.md` frontmatter **verdict**
reads (should be none post-flip except WP06's not-yet-removed field). **Confirm `ReviewCycleArtifact.latest`
+ `.from_file` are still present and used by `workflow_executor.py:1117` (fix-mode prose) and
`arbiter.py:461` (cycle_number) — deleting them is a regression, not a retirement (squad #1).** Confirm
damaged → fail-closed on every safety-gate reader (SC-004). Confirm the provenance interlock ran before
deletion (T021). Confirm the WP04 guard allowlist is empty at the end (blocking).
