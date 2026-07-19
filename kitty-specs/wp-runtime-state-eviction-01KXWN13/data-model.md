# Phase 1 Data Model: WP runtime-state eviction

## New entities

### `InnerStateChanged` (event)

A generic, off-axis (non-transition) record in the same append-only `status.events.jsonl`.

| Field | Type | Notes |
|---|---|---|
| `event_id` | ULID | dedup key; must match `ULID_PATTERN`. Backfill seeds use a deterministic namespaced ULID (`mission_id+wp_id+field`) that orders **after** the annotated transition at equal `at`. |
| `kind` | `"annotation"` | wire/envelope discriminator distinguishing it from a lane `"transition"`; reconciled with the existing `event_type` skip rule in `store.is_non_lane_event`. |
| `wp_id` | str | target WP. |
| `at` | ISO-8601 | truthful for live events; clamped to the WP's `claimed` for backfilled subtask marks. |
| `actor` | str | who caused the change. |
| `delta` | `WPInnerStateDelta` | typed partial (below). |

**Invariants**: no `from_lane`/`to_lane`; bypasses `validate_transition`; **never** increments
`force_count`; can **never** be reduced as a lane transition (architectural test).

### `WPInnerStateDelta` (typed partial payload)

Typed optional fields — **not** a free `dict[str, Any]` (C-002).

| Field | Type | Merge rule in reducer |
|---|---|---|
| `shell_pid` | `int?` | **replace** |
| `shell_pid_created_at` | `str?` | **replace** |
| `subtasks` | `Mapping[str, Status]?` | **replace** per-subtask-id |
| `note` | `str?` | **append** to the snapshot `notes` list |
| `tracker_refs` | `list[str]?` | **union** |
| `agent` | `str?` | **replace** (reassignment; the claim `agent` rides the transition `policy_metadata`, see below) |
| `assignee` | `str?` | **replace** |
| `review` | `ReviewOverride?` | **replace** (`review_artifact_override_*` pair — the review-cycle slot) |

Only present fields are applied; absent fields leave the corresponding snapshot slot untouched.

### Reduced snapshot — new per-WP slots

`StatusSnapshot.work_packages[wp_id]` gains typed runtime slots alongside the existing
`{lane, actor, last_transition_at, last_event_id, force_count}`:

`shell_pid`, `shell_pid_created_at`, `subtasks: Mapping[str, Status]`, `notes: list[str]`,
`tracker_refs: list[str]`, `agent`, `assignee`, `review`.

**Reducer contract**: a lane transition updates `lane`/`actor`/… and **preserves** the runtime slots it
does not set (per-field independence). The **`planned→claimed` transition additionally sets**
`shell_pid`/`shell_pid_created_at`/`agent` into their snapshot slots from its `policy_metadata` sidecar
(FR-004 claim path) — this is the only case where a transition writes a runtime slot; every other
runtime slot is written by an `InnerStateChanged`, which updates only the delta's present slots and
leaves `lane` untouched. Fold order is an event-kind partition: all transitions, then all annotations
(last-writer-wins per field; `force_count` never bumped by an annotation).

## Field-authority table (post-mission)

| Field | Authority (post) | Read path (post) |
|---|---|---|
| `work_package_id`, `title`, `dependencies`, `scope`, `task_type`, `owned_files`, planning trio, prompt body, `agent_profile` (authored) | **static** — frontmatter | frontmatter |
| `shell_pid` (+`_created_at`) | **dynamic** — event log | reduced snapshot (`stale_detection`, `WorkPackage.shell_pid`) |
| subtask completion | **dynamic** — event log | snapshot `subtasks` (`_guard_subtasks`, `_infer_subtasks_complete`) |
| `agent`, `assignee` | **dynamic** — event log | snapshot |
| `## Activity Log`, `history` render | **dynamic** — event log | folded `notes` + transition history |
| `tracker_refs` | **dynamic** — event log (struck from static schema) | snapshot |
| review-cycle (`review_status`/`reviewed_by`/…/`review_artifact_override_*`) | **dynamic** — event log | snapshot / review artifact events |
| `history[]` frontmatter, `progress` | **removed** (dead) | n/a |

**No field appears in both columns of authority** — enforced by the FR-013 architectural test.

## State & transitions (unchanged FSM)

The 9-lane FSM and its 27 transition pairs are **not modified**. `InnerStateChanged` is off-axis and
never traverses the matrix. The only transition-adjacent change is FR-015: `build_transition_plan`
stops auto-promoting `force` on the five evidence-gated backward edges, decided by asking
`validate_transition` (not the matrix definition itself).

## Externally visible effects

- `status.events.jsonl` gains `annotation`-kind records (additive; no wire-schema break for existing
  consumers that read `transition` events).
- WP markdown files stop changing on runtime events → dossier content hash stabilises (AC-5).
- Persisted `StatusEvent.force` becomes truthful on review-rejection edges (FR-015).
