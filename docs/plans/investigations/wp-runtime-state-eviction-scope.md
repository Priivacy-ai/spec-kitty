---
title: WP Runtime-State Eviction — Prerequisite Mission Scope
description: 'Scope for the enabling mission that evicts all runtime-mutable state (shell_pid, history, subtask-checkbox state, review-cycle fields) out of tasks/WP##.md into the canonical event log — the prerequisite that unblocks a YAML-authoritative / markdown-derived WP prompt. Generalises the shipped lane retirement; the #2093/#2400 charter.'
doc_status: proposal
updated: '2026-07-16'
related:
- wp-op-schema-proposal.md
- wp-op-schema-model.md
- wp-op-schema-related-tickets.md
---
# WP Runtime-State Eviction — Prerequisite Mission Scope

The squad pressure-test ([wp-op-schema-proposal.md](wp-op-schema-proposal.md) Part 4,
**B3/B4**) established that the YAML-authoritative / markdown-derived WP prompt
**cannot be built** while `tasks/WP##.md` still holds runtime-mutable state that
live code writes and reads. Declaring that file "derived, do not edit" would
clobber claim-liveness and implementation evidence on the very next `implement`.

**This mission is that unblock.** It moves *all* runtime-mutable WP state out of
the WP file into the canonical append-only status/event log — generalising the
already-shipped `lane` retirement (`frontmatter.py:47-49`;
`task_metadata_validation.py:82` MIGRATION-ONLY). After it lands, `WP##.md` holds
**only static design-intent**, and the WP-prompt schema work (proposal Parts 1–3)
becomes a pure formalization with no runtime collision.

This is not new construction against the milestone — it **is the charter of
#2093 / #2400** (static intent stays canonical; dynamic runtime state retires to
event-log/invocation authority), carried to completion.

---

## Problem: what still lives in `WP##.md` and churns

| Runtime field | Where in file | Writer (live) | Reader (live) | Why it must move |
|---|---|---|---|---|
| `shell_pid`, `shell_pid_created_at` | frontmatter | `implement.py:1730` → `write_shell_pid_claim_to_file` (`frontmatter.py:393`) | `stale_detection.py:403` (claim-liveness) | Claim ownership written on every implement; a re-render from a static spec erases it → live claims read as reclaimable. |
| `history[]` | frontmatter | `add_history_entry` (`frontmatter.py:347`) | audit/display | In-place mutable list; perturbs the file hash on every event. |
| subtask **checkbox state** (`- [x] T###`) | body / `tasks.md` | `tasks_materialization.py:260,304` (mark-status) | `subtask_rows.py:181` → `emit.py:302` (done-inference: `done==total`) | Completion evidence that gates lane transitions; not reconstructable from a static spec. |
| `review_status`, `reviewed_by`, `reviewer*`, `review_feedback` (pointer) | frontmatter | review-cycle writes | `workflow_cores.py:341` | Review-cycle state; already declared event-log-owned in intent (`frontmatter.py:47-48`) but still written. |
| `activity_log` (narrative) | body `## Activity Log` (1670×) | appended mid-work | dashboard display | Free-form narrative; has no structured home today. |
| `lane` | — | **already evicted** ✅ | — | The precedent this mission generalises. |

The static residue that **stays** in the WP file: `work_package_id`, `title`,
`dependencies`, `requirement_refs`, `plan_concern_refs`, `owned_files`,
`create_intent`, `authoritative_surface`, `scope`, `task_type`, `cross_cutting`,
`agent_profile` (authored), `tracker_refs`, `branch_strategy` /
`merge_target_branch` / `planning_base_branch`, `priority`, `phase`, and the
prompt-body prose. (Note M1 from Part 4: the branch-contract + `priority`/`phase`
are static and must be **kept**, not evicted.)

## Target architecture

Each evicted field gets exactly one new home; `WP##.md` becomes a read-derived
view for the runtime parts.

| Field | New authority | Mechanism |
|---|---|---|
| `shell_pid` (+ baseline) | status event log | new `claimed`-event payload carrying `shell_pid`/`baseline`; `stale_detection` reads the reduced snapshot, not frontmatter. |
| `history[]` | status event log | already the event stream; drop the frontmatter mirror; render `## History` from reduced events at display time. |
| subtask checkbox `done/total` | status event log | a `subtask_marked` event (id, status); `count_wp_section_subtask_rows` is replaced by a reducer count; the body checkbox becomes a *rendered* view. |
| review-cycle fields | status event log | already modelled as review events; drop the frontmatter mirror. |
| `activity_log` narrative | status event log | new event payload with a free-text `note` (the one genuinely-new event shape — resolves Part 4 **M7** data-loss). |

**Invariant after eviction:** `content_hash(WP##.md)` (or its successor
`content_hash(spec)`) is stable across *every* runtime transition — claim,
subtask-done, review, history append. That is the acceptance test that proves the
mission (and directly delivers the original hash-churn fix).

## Acceptance criteria (draft)

- **AC-1** — No `spec-kitty implement` / `mark-status` / review action writes to
  `tasks/WP##.md`. (Guard test: snapshot file mtime+bytes across a full WP
  lifecycle; assert unchanged.)
- **AC-2** — Claim-liveness (`stale_detection`) resolves from the reduced event
  snapshot, not frontmatter `shell_pid`; a claimed WP is correctly detected as
  live with an empty frontmatter.
- **AC-3** — Done-inference (`emit.py` `done==total`) resolves from reduced
  subtask events; lane transitions gate identically to today.
- **AC-4** — `## Activity Log`, `## History`, review sections still render (from
  events) with no content loss vs today (resolves M7).
- **AC-5** — A full WP lifecycle produces a **stable content hash** (the churn
  fix; wire once, no mixed pool — resolves Part 4 **M2/M4**).
- **AC-6** — Migration backfills existing 278 missions' frontmatter runtime
  fields into seed events; idempotent; no data loss.

## Sequencing & dependencies

1. **Reconcile with #2093 / #2400** — this mission *is* their charter completion;
   it should land **under** #2400, not as a rival. Accept #2093's authority ruling
   (static intent stays canonical in the WP file).
2. **Blocks** the WP-prompt schema flip (proposal Parts 1–3) and the semantic
   content-hash (which must co-move with `sync/body_upload.py`, Part 4 M2).
3. **Independent of** the Op-debrief slice (proposal Part 4 — ships separately).
4. **Gated behind / coordinated with #1619** only for the *final* authority
   election (enrich `WPMetadata`); the eviction itself is #1619-neutral (it moves
   state to the already-shipped event log, adding no new aggregate).
5. **Coordinate with #2160** (coord-authority) — it also writes the `shell_pid`
   claim into frontmatter (`implement.py:1730`); the eviction must land with, not
   against, that writer's restructuring.

## Out of scope (explicitly)

- The WP-prompt body schema / YAML-authority flip (that is the *finish*, gated on
  this mission).
- Electing the canonical static model (`WorkPackageEntry` vs enrich `WPMetadata`)
  — deferred to the schema mission; grounding prefers enriching `WPMetadata`.
- The Op debrief (separate, landable now).

## Open questions

1. Is the `activity_log` note event a first-class status event, or a Tier-2
   evidence-style sidecar keyed by WP? (Affects M7's fix shape.)
2. Does subtask completion become an event per subtask, or a single
   `subtasks_snapshot`? (Reducer complexity vs event volume.)
3. Do we evict review-cycle frontmatter in this mission or fold it into the
   in-flight review-state work under #2160?
4. Migration ordering: backfill events **before** or **after** the writers are
   cut over? (AC-6 idempotency depends on the answer.)
