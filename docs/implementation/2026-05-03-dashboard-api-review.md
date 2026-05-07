# Engineering Log — Dashboard API Surface Review

**Date**: 2026-05-03
**Reviewer**: Claude (Sonnet 4.7)
**Trigger**: Operator inspection of `/openapi.json` after the FastAPI/OpenAPI
transport mission (`frontend-api-fastapi-openapi-migration-01KQN2JA`) shipped.
**Live snapshot reviewed**: `tests/test_dashboard/snapshots/openapi.json`
(58 KB, 23 paths, OpenAPI 3.1.0)
**Parent epic**: [#645 — Frontend Decoupling and Application API Platform](https://github.com/Priivacy-ai/spec-kitty/issues/645)

This log records substantive findings from a manual review of the published
OpenAPI surface and the underlying service / router code. Every finding is
mapped to a concrete remediation issue (filed as a child of #645) so the
work can be sequenced without re-deriving the analysis.

---

## Finding 1 — No tag grouping in the OpenAPI document

**Symptom**: every operation in `/openapi.json` has `tags: []`. Swagger UI
at `/docs` and ReDoc at `/redoc` therefore render every route in a single
flat list; consumers have no way to navigate by domain.

**Evidence**:

```bash
$ curl -s http://127.0.0.1:9337/openapi.json | jq -r \
  '[.paths[][].tags // []] | flatten | unique'
[]
```

**Expected**: each route is tagged with its domain. Suggested initial set
(matches the operator's mental model from #645 "Sequencing"):

| Tag           | Routes                                                                |
|---------------|-----------------------------------------------------------------------|
| `missions`    | `/api/missions`, `/api/missions/{id}`, `/api/missions/{id}/status`, `/api/missions/{id}/workpackages`, `/api/missions/{id}/workpackages/{wp_id}` |
| `kanban`      | `/api/kanban/{feature_id}` (or fold into `missions`; see Finding 3)  |
| `research`    | `/api/research/{feature_id}`, `/api/research/{feature_id}/{file_name}` |
| `contracts`   | `/api/contracts/{feature_id}`, `/api/contracts/{feature_id}/{file_name}` |
| `checklists`  | `/api/checklists/{feature_id}`, `/api/checklists/{feature_id}/{file_name}` |
| `charter`     | `/api/charter`, `/api/charter-lint`                                  |
| `dossier`     | `/api/dossier/overview`, `/api/dossier/artifacts`, `/api/dossier/artifacts/{key}`, `/api/dossier/snapshots/export` |
| `glossary`    | `/api/glossary-health`, `/api/glossary-terms`                        |
| `health`      | `/api/health`, `/api/diagnostics`                                    |
| `sync`        | `/api/sync/trigger`                                                  |
| `lifecycle`   | `/api/shutdown`                                                      |
| `static`      | `/`, `/static/*` (low priority — already low in any consumer's view) |

**Remediation**: each FastAPI router declares `tags=[...]` on its
`APIRouter(...)` constructor. Single-line change per router. The OpenAPI
snapshot test (`tests/test_dashboard/test_openapi_snapshot.py`) catches
the diff; reviewer signoff per `contracts/openapi-stability.md`.

**Tracker**: child issue under #645.

---

## Finding 2 — `/api/features` should be `/api/missions`

**Symptom**: the dashboard's primary list endpoint is `/api/features`, but
the canonical noun in spec-kitty docs, the CLI (`spec-kitty next --mission`),
the migration ADRs, the ownership map, and the GitHub epic body
([#645](https://github.com/Priivacy-ai/spec-kitty/issues/645)) is **mission**.
The terminology drift originates pre-extraction (the legacy handler was named
`handle_features_list`) and was carried forward unchanged by the FastAPI
migration per spec C-004 ("no contract redesign in this mission").

**Evidence**:
- `architecture/2.x/05_ownership_map.md` uses "mission" exclusively (`mission_slug`,
  `mission_id`, `mission_number`).
- `CLAUDE.md` § "Mission Identity Model (083+)" treats *mission* as canonical.
- `meta.json` files use `mission_id`, `mission_slug`, `friendly_name`.
- `/api/features` returns objects with `id`, `name`, `path`, etc. — most of
  which are mission identity fields, not feature-specific fields.

**Expected**:
- `/api/missions` (plural list) and `/api/missions/{mission_id}` (single mission detail).
- `/api/features` retained as a deprecated alias under the same router for at
  least one release; emits a `Deprecation` HTTP header pointing at
  `/api/missions`.
- Response field `active_feature_id` → `active_mission_id`; same retention
  pattern (return both keys for one release, document the migration).

**Remediation**: a small mission that performs the rename additively. The
strangler period for the old `/api/features` URL parallels the legacy
BaseHTTPServer retention period: removed in the same release that retires
the legacy stack.

**Tracker**: child issue under #645.

---

## Finding 3 — Kanban API and mission API are highly redundant

**Symptom**: `/api/features` returns mission rows that already include a
`kanban_stats` block (counts per lane plus `weighted_percentage`).
`/api/kanban/{feature_id}` returns the same `kanban_stats` shape **plus**
a `lanes` map keyed by lane name with `KanbanTaskData[]` lists. There is
no separation of "summary" vs "detail" in the URL; the heavy detail is
wedged into a single endpoint.

**Evidence**: `KanbanResponse` in `api_types.py` and `KanbanResponse` in
`api/models.py` both declare `lanes: dict[str, list[KanbanTaskData]]`,
`is_legacy: bool`, `upgrade_needed: bool`, `weighted_percentage: float`.
The same fields appear under each mission's `kanban_stats` in the
`/api/features` response.

**Expected**: clean separation along resource lines:

| URL | Returns | Use case |
|-----|---------|----------|
| `GET /api/missions` | list of `MissionSummary` (id, slug, lane counts) | dashboard mission grid |
| `GET /api/missions/{id}` | full `Mission` (summary + metadata + active flag) | single mission card |
| `GET /api/missions/{id}/status` | `MissionStatus` (lane counts, weighted_percentage, blocked_reason, current_phase) | status badge / poll |
| `GET /api/missions/{id}/workpackages` | list of `WorkPackageSummary` | kanban board source |
| `GET /api/missions/{id}/workpackages/{wp_id}` | full `WorkPackage` (subtasks, assignment, prompt, history) | WP detail panel |

`/api/kanban/{id}` becomes a deprecated alias for the WP list endpoint.

**Remediation**: same mission as Finding 4 (the new endpoints define
the canonical surface; kanban and features fold into it as deprecated
aliases).

**Tracker**: child issue under #645.

---

## Finding 4 — Missing canonical mission endpoints

**Symptom**: there is no resource-oriented surface for individual missions
or work packages. The only way for a consumer to discover a single
mission's status today is to fetch the whole `/api/features` list and
filter client-side (O(N) per request, where N can be 144+). There is no
single-WP endpoint at all; consumers must fetch the entire kanban for a
mission and find the WP inside it.

**Missing endpoints**:

1. `GET /api/missions/{id}/status` — single-mission status snapshot.
   Returns `{ "lane_counts": {...}, "weighted_percentage": 95.0, "current_phase": "review", "blocked_reason": null, "active_assignments": [...] }`.

2. `GET /api/missions/{id}/workpackages` — list of WPs for a mission.
   Returns `[{ "wp_id": "WP01", "title": "...", "lane": "done", "assignment": WorkPackageAssignment, "subtask_count": 4, "subtasks_done": 4 }, ...]`.

3. `GET /api/missions/{id}/workpackages/{wp_id}` — single WP detail.
   Returns full WP including subtasks, assignment, prompt, history, owned_files.

**Schema requirement**: a typed `WorkPackageAssignment` model that captures
ownership / status:

```python
class WorkPackageAssignment(BaseModel):
    """Who owns this WP and what state it is in."""
    wp_id: str                             # "WP01"
    lane: Lane                             # "planned" | "claimed" | "in_progress" | ...
    assignee: str | None                   # "claude:opus-4-7" | None
    agent_profile: str | None              # "python-pedro"
    role: str | None                       # "implementer"
    claimed_at: datetime | None
    last_event_id: str | None              # most recent status.events.jsonl entry
    blocked_reason: str | None             # populated when lane == "blocked"
    review_evidence: ReviewEvidence | None # populated for in_review / approved / done
```

This model exists nowhere today. Lane membership is implicit in the
kanban response (the dict key); assignee is a free-form string in
`KanbanTaskData.agent`; review evidence lives only in the JSONL event
log.

**Remediation**: scoped mission to add the three endpoints + the
`WorkPackageAssignment` model + a service-layer abstraction
(`MissionRegistry` and `WorkPackageRegistry`) that backs both the new
endpoints and the existing legacy-shaped responses.

**Tracker**: child issue under #645.

---

## Finding 5 — Direct filesystem access in routers and services

**Symptom**: every dashboard request reads files from disk. There is no
caching layer, no observability hook, no read-through abstraction. A
single page-load by `dashboard.js` hits at least:
- `/api/features` → `scan_all_features()` → walks every `kitty-specs/*/`
  directory, opens every `meta.json`, opens every `status.events.jsonl`,
  reads every `tasks.md`, opens every `tasks/WP*.md`.
- `/api/kanban/{id}` → `scan_feature_kanban()` → similar walk for one mission.
- `/api/health`, `/api/diagnostics` → similar.

The `dashboard.js` polls `/api/features` every 1 second (`setInterval(fetchData, 1000)`).
On the spec-kitty repo today (~144 missions, hundreds of WP files), each
poll reads thousands of small files.

**Evidence** (file I/O sites in service-layer code):

```
src/dashboard/file_reader.py:44     content = path.read_text(encoding="utf-8")
src/dashboard/file_reader.py:52     content = path.read_text(encoding="utf-8", errors="replace")
src/dashboard/file_reader.py:77     for file_path in sorted(research_dir.rglob("*")):
src/dashboard/file_reader.py:125    for file_path in sorted(artifact_dir.rglob("*")):
src/specify_cli/dashboard/scanner.py — full scan walk
src/specify_cli/glossary_semantic_events — DRG file walk per /api/glossary-health request
src/dashboard/api/routers/lint.py:45-47  if not report_path.exists(): / report_path.read_text(...)
src/dashboard/api/routers/glossary.py:57-59  drg_path.exists() / drg_path.open(...)
```

The FastAPI mission packaged this logic as service objects but did NOT
introduce a registry / cache abstraction. The transport changed; the
backing strategy did not.

**Expected** (the user's stated goal):
> Each dashboard lookup can be done using an API call, rather than using
> direct file access.

The user's framing is correct in spirit but the practical translation is
two layers:
1. **Service-layer abstraction**: a `MissionRegistry` that reads from
   the filesystem ONCE per mtime change and serves cached snapshots.
   The router calls `registry.list_missions()`, not `scan_all_features()`.
2. **Cache invalidation**: backed by a watcher (inotify / polling at a
   coarser cadence than the per-request 1-second poll) or by mtime
   stamping on `kitty-specs/*/status.events.jsonl`.

This is the right architectural shape for #645's Step 5 (async update
transport) anyway: when the registry changes, push a WebSocket / SSE
event instead of having every client poll independently.

**Remediation**: separate mission. Architecturally significant; warrants
an ADR. See the Architectural Updates section below.

**Tracker**: child issue under #645.

---

## Finding 6 — `dashboard.js` polls `/api/features` every 1 second

**Symptom**: `setInterval(fetchData, 1000)` on line 1568 of
`dashboard.js`. Every browser tab open to the dashboard performs one
full scan of the project per second.

**Cost on this project** (144 missions × ~5 files per scan):
- ~720 file `open()` syscalls per second per browser tab
- ~720 JSONL parses per second per browser tab
- Bandwidth: 27 KB OpenAPI doc on init + ~50–100 KB `/api/features`
  response per second per tab

This is not catastrophic on a local dev machine but is **wasteful** and
**directly conflicts with the registry/cache architecture in Finding 5**.
A registry + WebSocket / SSE push (Step 5 of #645) would eliminate the
poll entirely.

**Remediation**: deferred until Step 5 of #645 (async update transport)
is designed. Document as a known scaling cliff.

**Tracker**: capture in the Step 5 mission spec when it is filed; not
a separate ticket.

---

## Finding 7 — Glossary and lint routes still call into legacy handlers

**Symptom**: `src/dashboard/api/routers/glossary.py` and
`src/dashboard/api/routers/lint.py` are transport-only migrations.
Their TODO markers point at follow-up issues
[#954](https://github.com/Priivacy-ai/spec-kitty/issues/954) (glossary)
and [#955](https://github.com/Priivacy-ai/spec-kitty/issues/955) (lint).

**Status**: known and tracked. Mentioned here for completeness so the
remediation set is self-contained.

---

## Finding 8 — `WorkpackageAssignment` schema does not exist

**Symptom**: the operator asked specifically for a `WorkpackageAssignment`
schema that captures ownership / status. Searching the codebase:

```bash
$ grep -r "WorkPackageAssignment\|WorkpackageAssignment" src/ tests/
```

returns zero hits (one `AgentAssignment` exists in `specify_cli.lanes` but
is not exposed via the dashboard API).

**Expected**: see Finding 4. The `WorkPackageAssignment` model is the
contract handle for "who owns this WP, what state is it in, what evidence
backs that state." It is the structural anchor for the new
`/api/missions/{id}/workpackages` endpoint and the natural payload shape
for any future MCP tool / external SDK that needs WP-level data.

**Remediation**: same mission as Finding 4.

---

## Architectural updates required

The findings collectively imply the following architectural artefact updates:

1. **ADR**: a new ADR
   `architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md`
   documenting:
   - the move from per-request filesystem scans to a `MissionRegistry`
     abstraction (Finding 5)
   - the resource-oriented URL surface (`/api/missions/...`) replacing the
     verb-shaped `/api/features` + `/api/kanban` (Findings 2, 3, 4)
   - cache invalidation strategy (mtime polling at coarser cadence vs
     inotify) and rejected alternatives (per-request walk; in-memory
     full-replication).

2. **Ownership map** (`architecture/2.x/05_ownership_map.md`) §
   Dashboard:
   - update `current_state` to mark `MissionRegistry` and
     `WorkPackageRegistry` as the new cache abstraction owners
   - update `seams` to reflect "FastAPI router → registry.method() →
     filesystem read (cached)" instead of "FastAPI router → scanner walk"

3. **Manifest** (`architecture/2.x/05_ownership_manifest.yaml`) — mirror
   the map updates.

4. **OpenAPI stability contract**
   (`kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/contracts/openapi-stability.md`)
   — add a section documenting the deprecation alias pattern (how
   `/api/features` maps to `/api/missions` for one release).

5. **Migration runbook**
   (`docs/migration/dashboard-fastapi-transport.md`) — add a section
   describing the deprecated routes and the upgrade window.

These updates are sized to land alongside the remediation missions, not
as a separate prerequisite.

---

## Remediation summary table

| Finding | Severity | Remediation tracker | Sequencing |
|---------|----------|---------------------|------------|
| 1 — No tags | LOW | new issue (one-day fix) | can ship independently |
| 2 — `/features` → `/missions` | MEDIUM | new issue (small mission) | depends on Finding 4 surface |
| 3 — Kanban / mission redundancy | MEDIUM | folded into Finding 4 | – |
| 4 — Missing endpoints + assignment schema | HIGH | new issue (medium mission) | needs Finding 5 first for the registry abstraction |
| 5 — Direct FS access (registry + cache) | HIGH | new issue (medium mission, ADR-grade) | prerequisite for 4 |
| 6 — 1-second polling | LOW | rolled into the eventual #645 Step 5 mission | – |
| 7 — Glossary / lint extraction | LOW | already #954, #955 | independent |
| 8 — `WorkPackageAssignment` schema | HIGH | folded into Finding 4 | – |

The tickets listed below are filed as child items of #645.
