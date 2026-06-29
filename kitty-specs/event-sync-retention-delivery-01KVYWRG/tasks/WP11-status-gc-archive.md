---
work_package_id: WP11
title: Status report assembly + GC/archive
dependencies:
- WP03
- WP05
- WP10
requirement_refs:
- FR-009
- FR-010
- FR-019
tracker_refs: []
planning_base_branch: mission/event-sync-retention-delivery
merge_target_branch: mission/event-sync-retention-delivery
branch_strategy: Planning artifacts for this mission were generated on mission/event-sync-retention-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/event-sync-retention-delivery unless the human explicitly redirects the landing branch.
subtasks:
- T064
- T065
- T066
- T067
- T068
- T069
- T070
phase: Phase 5 - Policy, migration, status, CLI
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "82987"
history:
- at: '2026-06-29T06:21:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/delivery/status_report.py
create_intent:
- src/specify_cli/delivery/status_report.py
- src/specify_cli/delivery/retention.py
- tests/delivery/test_status_report.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/delivery/status_report.py
- src/specify_cli/delivery/retention.py
- tests/delivery/test_status_report.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP11 – Status report assembly + GC/archive

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`
If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

This WP implements the **logic half of plan concern IC-08** — status-report assembly and the GC/archive
retention operations. The CLI wiring that calls into these modules is **WP12** (`cli/commands/sync.py`),
which must stay thin. Keep all heavy assembly here so WP12 is wiring only.

You complete this WP when:

- `src/specify_cli/delivery/status_report.py` assembles the seven additive JSON sections required by
  contract §6 (Status And Compatibility) — `target_authority`, `event_journal`, `delivery_targets`,
  `delivery_ledger`, `migration_conflicts`, `terminal_failures`, `body_upload_compatibility` — as pure,
  callable data builders consumable by the CLI (**FR-019**, **SC-010**).
- The distinct counts mandated by **US4 acceptance scenario 1** and **SC-003** are each surfaced as a
  separate number: retained event count, current-target delivered count, previous-target delivered count,
  terminal-failed count, body-upload count, and the oldest retained timestamp (**FR-009**).
- `src/specify_cli/delivery/retention.py` implements GC/archive as **explicit-operator-action-only**
  operations that archive/purge payloads while **preserving delivery-ledger history and provenance**
  (**FR-010**, contract §3 — "the only destructive payload operations and preserve delivery
  history/provenance").
- A GC suggestion surfaces **only** when the journal is large **AND** fully delivered to all known targets
  (**NFR-004**); journal size is always surfaced so "explicit only" never degrades into silent unbounded
  growth.
- Existing queue/body-upload counts remain available for existing consumers, and **no** status field
  implies body-upload rows are event-journal rows (**NFR-006**, **C-006**, contract §6).
- The `sync-status-output.md` contract is updated additively (T069), preserving every old top-level field.
- `tests/delivery/test_status_report.py` proves the contract §6 "Required tests" plus **SC-010** against
  observable JSON and on-disk/ledger state.

**Acceptance criteria satisfied**: FR-009, FR-010, FR-019, NFR-004, NFR-006, SC-003, SC-010, C-006,
US4 acceptance scenarios 1 & 2, contract §3 & §6.

## Context & Constraints

**Prerequisite WPs and what they hand you:**

- **WP03 (`event_journal/`)** hands you the append-only journal: it can report the retained event count,
  the archived-event marker, the oldest retained timestamp, and journal size. Read these via the journal's
  public surface (`src/specify_cli/event_journal/journal.py`) — never re-implement counting against raw
  SQLite. The journal never deletes during normal `sync now` (contract §3); GC/archive are the only
  destructive payload operations and they live in *this* WP's `retention.py`.
- **WP05 (`delivery/ledger.py`)** hands you per-event/per-target delivery state. You need its query surface
  to compute: delivered-to-current-target count, delivered-to-previous-target count, pending/rejected/
  transient counts, terminal-failed count, and the **delivered-anywhere / fully-delivered-to-all-known-targets**
  predicate that gates the GC suggestion (`delivered_anywhere(event_id)` style query — used by NFR-004).
- **WP10 (`sync/migrate_journal.py`)** hands you the migration-conflict records (divergent duplicate
  `event_id` rows). The `migration_conflicts` section reports these unresolved conflicts; when conflicts
  exist, source-DB cleanup is blocked — surface that state, do not resolve it here.

**Links:**

- Spec: `kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md`
- Plan: `kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md` (IC-08)
- Contract: `kitty-specs/event-sync-retention-delivery-01KVYWRG/contracts/event-sync-delivery-contract.md` §3, §6

**Architectural constraints to honor:**

- **C-006 / NFR-006 (body-upload separation)**: `body_upload_queue` and `body_upload_failure_log` stay
  owned by `sync/queue.py` and are NOT event-journal rows. The `body_upload_compatibility` section reports
  these counts *explicitly separately*; no field name or grouping may conflate them with journal/ledger
  counts. Existing top-level `active_queue.body_upload_count` / `legacy_queue.body_upload_count` consumers
  must keep working unchanged.
- **NFR-004 (bounded growth visibility)**: journal size is *always* surfaced. The GC *suggestion* is gated;
  the *size* never is.
- **NFR-001 (observable-state tests)**: tests assert JSON output and on-disk/ledger state, not internal
  call order. No "assert called_with" on private helpers.
- **Terminology Canon**: "Mission" not "feature"; no `feature*` aliases in any field, key, or message you
  add.

**OUT-OF-MAP edit (T069):** `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/contracts/sync-status-output.md`
is NOT in `owned_files`. **Rationale (one line):** that doc is the canonical published contract for
`sync status --check --json`; FR-019/SC-010 require the new sections to be documented there *additively*,
and no other WP owns that file, so this WP records the contract extension it produces. Keep the edit purely
additive — preserve every existing top-level field.

## Branch Strategy
- **Strategy**: Planning artifacts were generated on mission/event-sync-retention-delivery; completed changes must merge back into mission/event-sync-retention-delivery.
- **Planning base branch**: mission/event-sync-retention-delivery
- **Merge target branch**: mission/event-sync-retention-delivery
> Populated by `spec-kitty agent mission tasks`. Do not change manually.

## 🔴 ATDD-First (binding — charter C-011)

**You cannot start implementation until a failing-first ATDD test exists.** Per the charter's *ATDD-First Discipline* (binding, C-011), this WP follows red→green→refactor:

1. **RED first** — before any implementation commit, write at least one acceptance test that pins the user-observable behaviour this WP delivers (see the Subtasks/Acceptance below) and commit it **as the lane's first, separate commit while it FAILS**.
2. **GREEN** — implement until that test (and the rest) pass.
3. **Refactor** with the tests green.

The reviewer verifies **red→green**: the ATDD test was RED on `mission/event-sync-retention-delivery` and GREEN on this WP's final commit. A WP without a failing-first ATDD commit is **rejected at review** even if the code works.

## Subtasks & Detailed Guidance

### Subtask T064 – Assemble the seven additive JSON sections
- **Purpose**: Build the additive status payload mandated by contract §6 so WP12 can emit it under
  `sync status --check --json`. This is the FR-019 / SC-010 core: `target_authority`, `event_journal`,
  `delivery_targets`, `delivery_ledger`, `migration_conflicts`, `terminal_failures`,
  `body_upload_compatibility`.
- **Steps**:
  1. In `src/specify_cli/delivery/status_report.py` define a single entry point (e.g.
     `build_status_report(...)`) that returns a serializable dict whose top level contains the seven
     additive keys above as nested objects. Accept the already-resolved inputs (the `ResolvedSyncTarget`
     from WP01/WP02 target authority, the journal handle from WP03, the ledger from WP05, the migration
     conflict source from WP10) — do NOT resolve targets or open SQLite directly here; consume the domain
     surfaces.
  2. `target_authority`: mirror the contract §1 fields exactly — `configured_server_url`, `env_server_url`,
     `override_mode`, `resolved_server_url`, `user_id`/`team_slug`, `derived_queue_scope`, `queue_db_path`,
     `active_queue_scope_status`. This makes env/config disagreement observable and non-silent before
     network calls (contract §1, SC-008 surface).
  3. `event_journal`: retained event count, archived event count, oldest retained event timestamp, journal
     size bytes (the bounded-growth surface for NFR-004).
  4. `delivery_targets`: current target identity (URL + scope) plus a summary of previous targets that have
     received deliveries (per US4 "current vs previous").
  5. `delivery_ledger`: per-status counts — delivered/current-target, delivered/previous-target, pending,
     rejected, transient.
  6. `terminal_failures`: the selector-excluded permanent failures (FR-015 rows) that remain inspectable —
     count plus enough identity to inspect (e.g. event_ids and last error), never deleted.
  7. `migration_conflicts`: unresolved divergent-duplicate conflicts from WP10; include enough to identify
     the conflicting `event_id`s and that cleanup is blocked.
  8. `body_upload_compatibility`: the `body_upload_queue` / `body_upload_failure_log` counts, labeled to
     make their separateness explicit (C-006).
  9. Keep this function's cyclomatic complexity ≤ 15 — split each section into a small named builder
     (`_target_authority_section`, `_event_journal_section`, …) so the top-level assembler is a flat
     compose of those helpers. Each helper is independently testable (Sonar discipline).
- **Files**: `src/specify_cli/delivery/status_report.py` (authoritative surface).
- **Parallel?**: Yes — `[P]`. This is the lead subtask; the others build on the module it creates.
- **Validation**:
  - [ ] Calling the assembler returns a dict containing all seven keys.
  - [ ] Each section's shape matches contract §6 and the `sync-status-output.md` "Event Journal Extension".
  - [ ] No section reads raw SQLite directly — all data flows through WP03/WP05/WP10 surfaces.
  - [ ] Top-level assembler complexity ≤ 15.
- **Edge cases**: empty journal (counts = 0, oldest timestamp = null, not an error); no previous target
  (empty `delivery_targets.previous`); no migration conflicts (empty list, section still present).

### Subtask T065 – Distinct counts (US4 + SC-003)
- **Purpose**: Guarantee the six distinct numbers that US4 acceptance scenario 1 and SC-003 require are
  *separate fields*, not derived or collapsed: retained event count, current-target delivered count,
  previous-target delivered count, terminal-failed count, body-upload count, and oldest retained timestamp
  (**FR-009**).
- **Steps**:
  1. Source each count from the correct domain: retained / oldest-timestamp / journal-size from WP03
     journal; current-target / previous-target / terminal-failed counts from WP05 ledger queries;
     body-upload count from the existing `sync/queue.py` body-upload surface (read-only).
  2. Place each count in its semantically-correct section (T064) — retained/oldest under `event_journal`,
     delivered/terminal under `delivery_ledger` + `terminal_failures`, body-upload under
     `body_upload_compatibility`. Do not duplicate a single number under a misleading second name.
  3. Implement the US4 scenario-1 case precisely: 124 retained delivered to a *previous* target but 0 to the
     *current* one must read as retained=124, current-target-delivered=0, previous-target-delivered=124,
     and a populated oldest-retained timestamp. "Current" is keyed off the resolved active target from
     target authority; "previous" is any other target with deliveries in the ledger.
- **Files**: `src/specify_cli/delivery/status_report.py`.
- **Parallel?**: No — depends on T064's section scaffolding.
- **Validation**:
  - [ ] retained, current-target-delivered, previous-target-delivered, terminal-failed, body-upload, and
        oldest-timestamp are six independently-asserted JSON values.
  - [ ] Current vs previous is computed from the resolved active target, not a guess.
  - [ ] SC-003: retained count and current-target delivered count are distinct numbers in the output.
- **Edge cases**: same event delivered to both current and previous targets must not be double-counted in a
  way that conflates the two per-target tallies; a target switch (US1) makes the old target "previous".

### Subtask T066 – GC/archive logic (explicit-only; preserve ledger history)
- **Purpose**: Implement the only destructive payload operations in this domain in
  `src/specify_cli/delivery/retention.py`. They run **only under explicit operator action** and **preserve
  delivery-ledger history and provenance** (**FR-010**, contract §3).
- **Steps**:
  1. In `src/specify_cli/delivery/retention.py` provide explicit operations — e.g. `archive_payloads(...)`
     and `gc_payloads(...)` — that the WP12 `sync gc` / `sync archive` commands call. They take the journal
     and ledger handles; they never run as a side effect of `sync now`.
  2. Archive: move/mark payload bytes to an archived state (consume the WP03 journal's archived marker);
     purge under GC per policy. In **both** cases the `delivery_ledger` rows (history/provenance: which
     event reached which target, when, with what result) are **preserved** — only payload bytes are
     archived/purged.
  3. Return a structured result (counts archived/purged, anything skipped because still relevant) so WP12
     can print observable output and tests can assert on it.
  4. Never call these from any automatic path. US4 acceptance scenario 3: "no explicit cleanup command →
     any `sync now` completes → no source events deleted." Enforce by *not wiring* retention into the
     dispatcher; assert this with a test that runs a sync and verifies retention untouched.
  5. Keep each operation ≤ 15 complexity; factor the shared "preserve ledger, mutate journal payload" core.
- **Files**: `src/specify_cli/delivery/retention.py` (in `owned_files`).
- **Parallel?**: No — uses WP03/WP05 surfaces and the section model.
- **Validation**:
  - [ ] After `archive`/`gc`, ledger rows for affected events still exist with original provenance.
  - [ ] Neither operation is reachable from `sync now` / the dispatcher.
  - [ ] Operations are no-ops unless explicitly invoked.
- **Edge cases**: GC requested on events not yet delivered anywhere — must respect policy (do not purge
  undelivered Teamspace-bound payloads silently; the suggestion gating in T067 governs *suggestion*, but the
  explicit operation itself must not erase undelivered durability the spec requires retained); archive an
  already-archived event (idempotent).

### Subtask T067 – Gate the GC suggestion (NFR-004)
- **Purpose**: A GC suggestion surfaces only when the journal is **large AND fully delivered to all known
  targets**; journal size is always surfaced so "explicit only" never means "silent unbounded growth"
  (**NFR-004**, contract §6 "GC/archive suggestions trigger only when retained payloads are large and
  delivered to all known targets").
- **Steps**:
  1. In `status_report.py` compute a `gc_suggested` boolean (or a small suggestion object with reason) as
     part of the `event_journal`/status payload.
  2. The predicate is: `journal_is_large AND every_retained_event_delivered_to_all_known_targets`. Use the
     WP05 ledger's delivered-to-all-known-targets query; "large" is a defined threshold constant (hoist as a
     named module constant per Sonar S1192, do not inline a magic number in multiple places).
  3. *Always* surface `journal_size` (bytes and/or count) regardless of the suggestion — the visibility half
     of NFR-004 is unconditional.
  4. Document the threshold in the contract update (T069) so operators know the trigger.
- **Files**: `src/specify_cli/delivery/status_report.py`.
- **Parallel?**: No — depends on T064/T065.
- **Validation**:
  - [ ] Large + fully-delivered → suggestion present.
  - [ ] Large + NOT fully delivered → no suggestion, but size still shown.
  - [ ] Small + fully delivered → no suggestion, but size still shown.
  - [ ] Threshold is a single named constant.
- **Edge cases**: zero known targets (cannot be "delivered to all known targets" meaningfully — define and
  test: a journal with no delivery target configured does not get a GC suggestion); exactly-at-threshold
  boundary.

### Subtask T068 – Preserve existing counts; never imply body-upload == journal (NFR-006, C-006)
- **Purpose**: Existing queue/body-upload consumers keep working, and no status field may imply body-upload
  rows are event-journal rows (**NFR-006**, **C-006**, contract §6).
- **Steps**:
  1. Confirm the existing top-level fields (`active_queue.event_count`, `active_queue.body_upload_count`,
     `legacy_queue.*`, etc. from `sync-status-output.md`) are preserved untouched by the additive sections —
     this WP *adds* sections, it does not rename or remove. (The actual top-level emission is WP12's wiring;
     here ensure the `body_upload_compatibility` section's labels and structure do not collide with or
     redefine those fields.)
  2. In `body_upload_compatibility`, label counts so a reader cannot mistake them for journal/ledger counts:
     explicitly name them as `body_upload_queue` / `body_upload_failure_log` counts and keep them out of the
     `event_journal` / `delivery_ledger` sections.
  3. Add a short module-level comment in `status_report.py` stating the C-006 separation invariant so future
     editors do not merge the two.
- **Files**: `src/specify_cli/delivery/status_report.py`.
- **Parallel?**: No.
- **Validation**:
  - [ ] `body_upload_compatibility` counts live only in that section.
  - [ ] No `event_journal`/`delivery_ledger` field is sourced from body-upload tables.
  - [ ] Existing top-level field names are unchanged by anything in this WP.
- **Edge cases**: a project with body uploads but zero events (and vice-versa) — both sections report
  honestly and independently.

### Subtask T069 – Additive contract update to `sync-status-output.md`
- **Purpose**: Document the seven new sections in the canonical published status contract while preserving
  all old top-level fields (**FR-019**, **SC-010**, contract §6).
- **Steps**:
  1. Edit `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/contracts/sync-status-output.md` — the
     existing "Event Journal Extension (#2124/#2131)" section already sketches these; reconcile it with the
     final seven-section shape (`target_authority`, `event_journal`, `delivery_targets`, `delivery_ledger`,
     `migration_conflicts`, `terminal_failures`, `body_upload_compatibility`) and the distinct counts /
     GC-suggestion threshold this WP implements.
  2. State explicitly: the extension is purely additive; existing top-level fields (`foreground`,
     `daemon_owner_record`, `active_queue`, `legacy_queue`, `mismatches`, `orphan_records`) remain available
     and unrenamed for old consumers.
  3. Note the GC-suggestion trigger (large AND fully delivered) and that journal size is always surfaced.
- **Files**: `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/contracts/sync-status-output.md`
  — **OUT-OF-MAP** (not in `owned_files`; rationale stated in Context & Constraints).
- **Parallel?**: No — finalize after the section shapes (T064–T068) settle.
- **Validation**:
  - [ ] All seven sections documented and consistent with the implementation.
  - [ ] Old top-level fields documented as preserved.
  - [ ] Terminology Canon: no `feature*` wording introduced.
- **Edge cases**: do not delete the existing extension prose — refine it; an over-eager rewrite that drops a
  previously-documented field is a regression.

### Subtask T070 – Tests (contract §6 Required tests + SC-010)
- **Purpose**: Prove the observable JSON and on-disk/ledger behavior in
  `tests/delivery/test_status_report.py`.
- **Steps**:
  1. **JSON completeness (SC-010)**: assemble a report against fixture journal/ledger/migration state; assert
     all seven sections are present AND that the old top-level field set is preserved (assert presence of the
     documented top-level keys).
  2. **Distinct counts (SC-003, US4)**: build the 124-retained / previous-delivered / current-0 fixture;
     assert retained=124, current-target-delivered=0, previous-target-delivered=124, plus a populated oldest
     timestamp — three distinct numbers, not the same value reused.
  3. **GC/archive suggestion gating (NFR-004)**: three cases — large+fully-delivered → suggested;
     large+not-fully-delivered → not suggested but size shown; small → not suggested but size shown.
  4. **Retention preserves ledger (FR-010, contract §3)**: run `archive`/`gc`, then assert ledger rows for
     the affected events still exist with provenance; assert a `sync now`-style path does not trigger
     retention (US4 scenario 3).
  5. **Body-upload separation (NFR-006/C-006)**: assert body-upload counts appear only in
     `body_upload_compatibility` and never in `event_journal`/`delivery_ledger`.
  6. Tests assert observable output + on-disk/ledger state, NOT internal call order (NFR-001). Use real
     SQLite-backed journal/ledger fixtures from WP03/WP05 rather than mocks where practical.
- **Files**: `tests/delivery/test_status_report.py` (in `owned_files`).
- **Parallel?**: No.
- **Validation**:
  - [ ] All five test groups above pass.
  - [ ] No test asserts call order or mock invocation sequence.
- **Edge cases**: empty-journal report; report with migration conflicts present (cleanup-blocked flagged);
  report with terminal-failed rows present and inspectable.

## Test Strategy

- Mandatory file: `tests/delivery/test_status_report.py`.
- Command: `PWHEADLESS=1 .venv/bin/pytest tests/delivery/test_status_report.py -q`.
- Parallel-safe (pure assembly + SQLite fixtures, no real ports/daemon): runs fine under
  `-n auto --dist loadfile`. No `-n0` serial pass needed for this WP.
- Fixtures: build a small journal (WP03) and ledger (WP05) in a temp home; populate the
  124-retained/previous-target scenario, a terminal-failed row, and a migration-conflict row to exercise
  every section. Prefer real domain objects over mocks (NFR-001).
- Re-run the relevant slice of the suite before handing off:
  `PWHEADLESS=1 .venv/bin/pytest tests/delivery/ -q`.
- `.venv/bin/ruff check src/specify_cli/delivery/status_report.py src/specify_cli/delivery/retention.py`
  and `.venv/bin/mypy` must pass with zero issues.

## Risks & Mitigations

- **Status back-compat regression (plan IC-08 risk)**: existing stats consumers must keep working with
  clarified semantics. *Mitigation*: additive-only sections; T068 + T070 assert old top-level fields persist;
  T069 documents the additivity.
- **Conflating body-upload and journal counts (C-006)**: easy to merge for convenience. *Mitigation*:
  dedicated `body_upload_compatibility` section, module comment, explicit test (T070.5).
- **Complexity ceiling**: the seven-section assembler can balloon past 15. *Mitigation*: one small builder
  per section, flat compose; threshold/large-journal magic numbers hoisted to named constants (S1192).
- **Silent unbounded growth**: forgetting to always surface journal size. *Mitigation*: size is
  unconditional (T067), suggestion is gated; tested in all three gating cases.
- **Retention leaking into the auto path**: GC/archive run as a side effect would violate US4 scenario 3.
  *Mitigation*: retention lives only in `retention.py`, never wired into the dispatcher; tested.

## Review Guidance

A reviewer for `/spec-kitty.review` must verify, tying to contract §6 "Required tests":

- JSON includes all seven additive sections AND preserves old top-level fields (SC-010).
- Status distinguishes retained / current-target-delivered / previous-target-delivered / terminal-failed /
  body-upload counts as separate numbers (SC-003, US4 scenario 1).
- GC/archive suggestion triggers only when retained payloads are large AND delivered to all known targets;
  journal size always shown (NFR-004).
- GC/archive are explicit-operator-only and preserve delivery-ledger history/provenance (FR-010, contract §3).
- No status field implies body-upload rows are event-journal rows (NFR-006, C-006).
- The `sync-status-output.md` edit is purely additive — no old field removed/renamed (T069).
- Tests assert observable output + on-disk/ledger state, not call order (NFR-001).
- Logic lives here; nothing assumes the CLI does assembly work (WP12 stays thin).

## Activity Log
> Entries chronological, appended at END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`
- 2026-06-29T06:21:37Z – system – Prompt created.
- 2026-06-29T09:46:42Z – claude:opus:python-pedro:implementer – shell_pid=80045 – Assigned agent via action command
- 2026-06-29T10:10:23Z – claude:opus:python-pedro:implementer – shell_pid=80045 – for_review (propagate; lane pristine at 1450fda17, T069 doc on lane)
- 2026-06-29T10:10:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=82987 – Started review via action command
- 2026-06-29T10:16:18Z – user – shell_pid=82987 – Review passed: 7 additive sections + base preserved (SC-010); distinct counts 124/prev/current-0 (SC-003/US4); body_upload only in body_upload_compatibility (NFR-006/C-006); gc purges only delivered_anywhere, never touches ledger (FR-010); evaluate_gc_suggestion gated large AND fully-delivered, zero-targets=none (NFR-004); T069 doc additive; ATDD red 36030fc2d->green 1450fda17; mypy/ruff clean; 89/89 tests; 100% cov. --force used: lane guard flags authorized T069 kitty-specs doc edit.
- 2026-06-29T10:17:00Z – user – shell_pid=82987 – Approved by reviewer-renata (on record): base preserved, distinct counts, body-upload separated, gc-only-delivered. Propagating.
