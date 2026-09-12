# Tasks: Legacy→Journal Capture Cutover

**Mission**: `legacy-journal-capture-cutover-01M03BSX`
**Plan**: [plan.md](./plan.md) (post-squad revision) · **Spec**: [spec.md](./spec.md)
**Branch**: `fix/legacy-journal-capture-cutover` → merges to `fix/legacy-journal-capture-cutover`

6 work packages, 30 subtasks. Completion is event-sourced — record with
`spec-kitty agent tasks mark-status Txxx --status done`, not by ticking boxes.

## Ownership map (no overlap — finalize-tasks validated)

| WP | Concern | Authoritative surface | Owns (core) |
|----|---------|----------------------|-------------|
| WP01 | Credential auth-signal (IC-01) | `src/specify_cli/sync/` | `queue.py`, `preflight.py`, `target_authority.py`, `mission_setup_plan.py` |
| WP02 | Dedup identity + ownerless attribution (IC-00/IC-03) | `src/specify_cli/sync/` | `migrate_journal.py`, `project_store_migration.py`, `event_journal/journal.py` |
| WP03 | Layout resolution + crash-safe cutover (IC-02) | `src/specify_cli/sync/` | `layout_generation.py` |
| WP04 | Loud cutover/backfill (IC-04, #3476) | `src/specify_cli/cli/commands/` | `migrate_cmd.py` |
| WP05 | Observable emitter (IC-05, #3391) | `src/specify_cli/sync/` | `emitter.py` |
| WP06 | Repro rewrite + LEGACY-flip reconcile (IC-06) | `tests/` | `test_issue_3425_*`, `test_layout_generation.py` |

## Dependency graph

```
WP01 (credentials)   WP02 (identity/attribution)      ← both independent, parallel
        │                     │
        └─────────┬───────────┘
                  ▼
              WP03 (layout + cutover)                  ← depends WP01, WP02
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
    WP04        WP05        WP06                        ← depend WP03 (WP06 also WP01)
  (backfill)  (emitter)  (repro/reconcile)
```

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | red-first: coherent authenticated host passes setup-plan preflight (SPEC_KITTY_HOME-isolated) | WP01 | |
| T002 | restore `read_queue_scope_from_credentials` to parse supported creds → auth signal | WP01 | |
| T003 | setup-plan gate consumes boolean "authenticated?", not a derived path | WP01 | |
| T004 | red-first: physical-store invariance — restoring parsing does not change which store a live write lands in | WP01 | |
| T005 | green B/C; keep JSON-path parsing working | WP01 | |
| T006 | red-first: cutover conservation — one authoritative record per event incl ownerless rows (0 loss/dup) | WP02 | [P] |
| T007 | red-first: divergent-payload quarantine (not last-write-win) | WP02 | [P] |
| T008 | wire `(event_id, source_digest)` provenance dedup via `migrate_journal` | WP02 | |
| T009 | ownerless-row `project_uuid` attribution via `project_store_migration` | WP02 | |
| T010 | confirm/harden `journal.append` `event_id` idempotence | WP02 | |
| T011 | red-first: greenfield root → project_only, never persists LEGACY, captures events (was 0) | WP03 | |
| T012 | red-first: idempotence-under-interruption — crash between begin/publish → re-enter same migration_id, no brick | WP03 | |
| T013 | red-first: emit during CUTOVER_PENDING → zero loss (block-and-retry, else loud) | WP03 | |
| T014 | red-first: SPEC_KITTY_NO_AUTO_CUTOVER → loud actionable refusal, no mutation | WP03 | |
| T015 | detection-before-persist: decide project_only before `_initial_state` LEGACY write; real detector via `discover_source_dbs` | WP03 | |
| T016 | lazy auto-cutover: invoke canonical engines with deterministic root-derived migration_id + auto source discovery; CUTOVER_PENDING/FAILED recovery | WP03 | |
| T017 | CUTOVER_PENDING write routing (block-and-retry bounded, else loud) + escape-hatch impl | WP03 | |
| T018 | red-first: backfill/cutover write that cannot land surfaces failure (not silent no-op) | WP04 | |
| T019 | red-first: legitimate already-migrated no-op is NOT flagged as failure | WP04 | |
| T020 | impl loud failure path in `backfill-runtime-state` | WP04 | |
| T021 | distinguish no-op from failure; actionable message | WP04 | |
| T022 | red-first: unrecoverable capture failure observable at command boundary, non-fatal | WP05 | |
| T023 | fix `_capture_to_journal` swallow (~2114) | WP05 | |
| T024 | fix `_emit_for_project_context` swallow (~2334-2336) — the live-reproduced site | WP05 | |
| T025 | process-level captured-failure flag/counter + command-epilogue inspection (no `emit_*` signature change) | WP05 | |
| T026 | rate-limit loud path (no warning-storm); coordinate #3391 seam | WP05 | |
| T027 | rewrite Test A: correct attribution to `journal.py:119 ProjectLayoutRequiredError`, drop retired no-arg queue API, KEEP behavioral pins | WP06 | |
| T028 | green the 3 `#3425` reproductions end-to-end (conservation + warning-absence) | WP06 | |
| T029 | enumerate + update the coordinated LEGACY-flip set (existing `tests/sync`/`event_journal` LEGACY-default pins outside the blocking selection) | WP06 | |
| T030 | pin auth-adjacent tests on `SPEC_KITTY_HOME` (not just `HOME`); verify `regression tests (blocking)` green on-branch | WP06 | |
| T031 | deep honest `CutoverResult.error` (runtime_state_cutover/backfill_runtime_state) + consume WP05 capture-failure flag at the cutover epilogue (FR-010 boundary consumer) | WP04 | |

---

## WP01 — Restore credential parsing as an auth signal (IC-01)

**Goal**: Stop the setup-plan auth gate refusing authenticated hosts (the real #3293 regression reddening blocking CI) WITHOUT re-introducing credential→path derivation (C-003/FR-009).
**Priority**: P1 (un-redder) · **Dependencies**: none · **Requirements**: FR-004, FR-009 · **Est.**: ~320 lines
**Independent test**: a coherent authenticated host passes setup-plan preflight (exit 0), scope derived; and a live write lands in the same physical store before/after the change.
**Subtasks**: T001 T002 T003 T004 T005
**Risks**: the pre-#3293 `server|user|team` piped form flows into `scope_db_path` at `preflight.py:480/516` and `target_authority.py:401/466` — restore parsing to auth-signalling only; do not revert path derivation. Prompt: `tasks/WP01-credential-auth-signal.md`

## WP02 — Dedup identity + ownerless-row attribution foundation (IC-00 / IC-03)

**Goal**: Pin the copy identity so cutover cannot duplicate/drop, incl. legacy rows predating per-project ownership; quarantine divergent payloads (#2846).
**Priority**: P1 (foundation) · **Dependencies**: none · **Requirements**: FR-005 · **Est.**: ~300 lines
**Independent test**: seed a temp root with duplicate + ownerless legacy rows; run the copy; assert exactly one authoritative record each, divergent payloads quarantined.
**Subtasks**: T006 T007 T008 T009 T010
**Risks**: naïve copy of an ownerless row raises "project UUID does not match store owner" (`queue.py:346-348`) — attribute first. Prompt: `tasks/WP02-dedup-identity-attribution.md`

## WP03 — Layout resolution + canonical, crash-safe auto-cutover (IC-02)

**Goal**: Fresh roots → project_only before any LEGACY persist; legacy-with-data roots auto-migrate via the canonical engines with stable id, closed drop window, and crash recovery — never bricking a root.
**Priority**: P1 (core) · **Dependencies**: WP01, WP02 · **Requirements**: FR-002, FR-003 · **Est.**: ~480 lines
**Independent test**: greenfield temp root captures events (was 0); interrupted cutover re-enters and converges; emit during CUTOVER_PENDING loses nothing; escape hatch refuses loudly.
**Subtasks**: T011 T012 T013 T014 T015 T016 T017
**Risks**: `_destination` returns LEGACY for CUTOVER_PENDING → swallow → P0 made permanent; bricking on crash; heavily test-pinned LEGACY default. ALL tests use temp roots — never the live machine-global `~/.spec-kitty`. Prompt: `tasks/WP03-layout-resolution-cutover.md`

## WP04 — Loud cutover / backfill failures (IC-04, #3476)

**Goal**: `backfill-runtime-state` cutover writes that cannot land surface the failure, distinguishable from a legitimate already-migrated no-op.
**Priority**: P2 · **Dependencies**: WP03, WP05 · **Requirements**: FR-007, FR-010 · **Est.**: ~300 lines
**Independent test**: a cutover write that cannot land surfaces a non-silent failure (populated `CutoverResult.error`); a legitimate no-op does not; a recorded unrecoverable capture failure is surfaced at the epilogue non-fatally.
**Owns (post-tasks fold)**: also `migration/runtime_state_cutover.py` + `migration/backfill_runtime_state.py` (deep honest error) — resolves post-tasks MAJOR-2. WP04 is the boundary consumer of WP05's capture-failure flag — resolves MAJOR-1.
**Subtasks**: T018 T019 T020 T021 T031
**Risks**: must not flag legitimate no-op as failure. Confirm the exact backfill surface in `migrate_cmd.py`. Prompt: `tasks/WP04-loud-cutover-backfill.md`

## WP05 — Observable emitter capture failure (IC-05, folds #3391)

**Goal**: No silent-success capture: fix BOTH swallow sites and surface a genuinely-unrecoverable failure at the command boundary via a process-level flag — non-fatal.
**Priority**: P2 · **Dependencies**: WP03 · **Requirements**: FR-001, FR-010 · **Est.**: ~360 lines
**Independent test**: an unrecoverable capture failure is observable at the command boundary (epilogue) and the host command does not crash.
**Subtasks**: T022 T023 T024 T025 T026
**Risks**: `_emit` is "never raises" across ~30 `emit_*` callers — do not raise; thread a flag. Rate-limit to avoid warning-storm. Coordinate #3391 (MOES-Media). Prompt: `tasks/WP05-observable-emitter.md`

## WP06 — Rewrite #3425 reproductions + coordinated LEGACY-flip reconcile (IC-06)

**Goal**: Turn the mis-built red-first tests green against the real contract while KEEPING behavioral pins; update the existing LEGACY-default pins outside the blocking selection so a green blocking gate cannot mask NFR-003/004 regressions.
**Priority**: P2 · **Dependencies**: WP01, WP03 · **Requirements**: FR-008, FR-009 · **Est.**: ~340 lines
**Independent test**: the 3 `#3425` reproductions pass end-to-end; `regression tests (blocking)` + the coordinated `tests/sync`/`event_journal` set are green on-branch.
**Subtasks**: T027 T028 T029 T030
**Risks**: rewritten tests must stay behavioral (conservation + warning-absence), not permit-enum assertions; the ~80 LEGACY-referencing files sit OUTSIDE the blocking selection — enumerate the reddened subset explicitly. Prompt: `tasks/WP06-repro-rewrite-reconcile.md`
