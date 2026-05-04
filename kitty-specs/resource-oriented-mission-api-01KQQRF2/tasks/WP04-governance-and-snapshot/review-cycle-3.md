---
affected_files: []
cycle_number: 3
mission_slug: resource-oriented-mission-api-01KQQRF2
reproduction_command:
reviewed_at: '2026-05-04T07:53:35Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP04
---

## Review Cycle 1 — WP04 Governance Wrap-up and OpenAPI Snapshot

**Reviewer**: claude:claude-sonnet-4-6:reviewer-renata:reviewer
**Date**: 2026-05-04

---

### Summary

Four of five acceptance criteria pass. One deliverable is missing.

---

### Issue 1 — T030: Migration runbook section not added (BLOCKING)

**Description**: The task T030 requires adding a "Resource-Oriented Mission Endpoints" section to `docs/migration/dashboard-fastapi-transport.md`. This section was specified in the WP04 task prompt and is listed in the Definition of Done:

> "Migration runbook updated."

`git diff 06a928c4c348d37c2e8ae402f0298ddd0ad061f2..HEAD -- docs/migration/dashboard-fastapi-transport.md` produces no output — the file was not touched by WP04. The "Resource-Oriented Mission Endpoints" section is absent.

**How to fix**: Add the section to `docs/migration/dashboard-fastapi-transport.md` as specified in the T030 subtask. The section must document:
- The 5 new canonical endpoints (`GET /api/missions`, `/api/missions/{id}`, etc.)
- The deprecated aliases (`/api/features`, `/api/kanban/{id}`) and the `Deprecation: true` + `Link` headers they emit
- The HATEOAS-LITE `_links` navigation block example
- The MCP exposure pathway (FastAPI surface at `/openapi.json` documents all routes)
- Reference to ADR `2026-05-03-2-resource-oriented-mission-api.md`

Commit the change and move WP04 back to `for_review` when done.

---

### Passing Criteria (for reference)

- ADR `architecture/2.x/adr/2026-05-03-2-resource-oriented-mission-api.md` — present, contains all required sections (Context, Decision, Alternatives Considered, Consequences, Deprecation Timeline, Future Work). PASS.
- `architecture/2.x/adr/README.md` — row for ADR 2026-05-03-2 present at line 25. PASS.
- `architecture/2.x/05_ownership_map.md` Dashboard section — references `src/dashboard/api/routers/missions.py`, marks #957 and #958 as "✅ shipped". PASS.
- `kitty-specs/resource-oriented-mission-api-01KQQRF2/issue-matrix.md` — present, #957 marked ✅ fixed (WP01, WP02), #958 marked ✅ fixed (WP03). PASS.
- T026 (OpenAPI snapshot regen) — deferred to post-merge due to lane isolation; acceptable per review instructions. PASS (acknowledged deferral).

---

### Verdict

**CHANGES REQUESTED** — Re-implement T030 and resubmit for review.
