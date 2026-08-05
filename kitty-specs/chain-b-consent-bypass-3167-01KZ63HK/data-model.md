# Data model — Chain-B consent bypass (`Priivacy-ai/spec-kitty#3167`)

Entities and relationships this mission touches. Nothing here is a proposed new table — the mission
changes *which identity a decision is keyed on*, not the schema. Every row cites where it is
established.

## Entities

| Entity | Where | Attributes that matter here |
|---|---|---|
| **Queued event** | `queue` table, `sync/queue.py:651`; drained by `drain_queue` (`:1570`) | The envelope/payload dict. **No dedicated `project_uuid` column.** Identity is resolved from the body via the dotted-path mechanism (`NAMESPACE_PROJECT_UUID = "namespace.project_uuid"`, `:55`; resolver `:325-326`). |
| **Queued artifact body** | `body_upload_queue`, `sync/queue.py:1029-1048` | Carries `project_uuid TEXT NOT NULL` (`:1031`) and is indexed on `(project_uuid, mission_slug, target_branch)` (`:1048`). This is the contrast case: identity is a column, not a body read. |
| **Project identity** | `project_uuid` (UUID string) | The **only** admissible subject of a consent question. A blank, missing or nil-sentinel value denies (`sync/runtime.py:220-222`). |
| **Consent record** | `sync/consent.py`, queried via `consented_project_uuids` (`:694`) | Keyed on `project_uuid`. Has a machine-global level plus an optional project-local level; offered checkout roots can only *narrow* the answer, never widen it (`sync/body_upload.py:86-88`). |
| **Checkout routing** | `CheckoutSyncRouting`, `sync/routing.py:243-254` | `repo_root`, `project_uuid`, `project_slug`, `build_id`, `repo_slug`, `local_sync_enabled`, `repo_default_sync_enabled`, `effective_sync_enabled`. **`repo_slug` is the mutable-git-remote key that carries the fresh-clone inheritance.** |
| **Auto-start preference** | `sync.auto_start` in `<project>/.kittify/config.yaml`, read at `sync/runtime.py:139-166` | A runtime convenience. **Explicitly not consent** and must never be unified with `sync.enabled` (`:141-148`). |

## Relationships

```
Queued event ──resolve_event_project_uuid──▶ project_uuid ──consented_project_uuids──▶ granted?
                (sync/project_identity.py,                    (Chain A, sync/consent.py:694)
                 reached sync/runtime.py:237)

Checkout (cwd or repo_root) ──resolve_checkout_sync_routing_readonly──▶ CheckoutSyncRouting
                                                                        .effective_sync_enabled
                              (Chain B, sync/routing.py:255)   ◀── includes repo_slug-keyed
                                                                   [sync.repo_defaults] grant
```

**The mission's change, stated as a relationship:** the event drain currently derives its decision
from *Checkout*, and must derive it from *Queued event → project_uuid* instead — the edge the publish
seam (`sync/runtime.py:196`) and the body drain (`sync/background.py:280`) already traverse.

## Cardinality — the property the fix turns on

One drain call handles **N queued events**, which may belong to **M distinct projects** where
`M >= 1`. Chain A answers per `project_uuid`. Therefore:

- the decision is **not** one boolean per drain — it is a **partition of the batch** by consent;
- a batch containing one consenting project must **not** authorize the rest
  (`sync/runtime.py:227-229` warns of exactly this, and names the drain as the caller that would
  trigger it);
- resolution is done **once per distinct uuid**, not once per event — the pattern
  `sync/background.py:280-299` already establishes for bodies.

## Gate inventory — the three egress seams and what each keys on

| Seam | Location | Keys on | State |
|---|---|---|---|
| daemon publish | `sync/runtime.py:196` | the event's own uuid | **Chain A** ✅ |
| artifact body drain | `sync/background.py:280` | each task's stored uuid | **Chain A** ✅ |
| **event batch drain** | `sync/batch.py:336-341` | **process cwd** | **Chain B** ❌ — this mission |

Non-egress, listed so it is not mistaken for a fourth gate: `sync/runtime.py:106` (auto-start). See
research §3b and open question **D-M5a-1**.

## Invariants the implementation must preserve

1. **Fail closed per subject.** An unresolvable uuid denies that event. Inability to determine
   consent is not consent (`sync/runtime.py:219-222`, `sync/background.py:288-291`).
2. **No consent widening by scope.** Offered checkout roots may narrow the answer only
   (`sync/body_upload.py:86-88`).
3. **One representation of consent (C-003).** No new consent predicate — reach
   `consented_project_uuids`. Adding a second answer to the same question is the defect class.
4. **Auto-start ≠ consent** (`sync/runtime.py:141-148`). Whatever D-M5a-1 decides must not collapse
   them.
