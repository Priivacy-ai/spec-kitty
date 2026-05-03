# Release Checklist — `feature/650-dashboard-ui-ux-overhaul` (FastAPI/OpenAPI Migration)

This document records the release-readiness state of the FastAPI/OpenAPI
migration shipped by mission `frontend-api-fastapi-openapi-migration-01KQN2JA`.

The verifier / date / commit fields are intentionally left blank — the
operator who cuts a release downstream of `feature/650-dashboard-ui-ux-overhaul`
fills them in. This file is committed to the branch so the verification
artifact ships with the code being verified.

## Mandatory verification

### SC-006 — Live transport flip + browser smoke-test

> **Source**: spec.md SC-006: "An operator following
> `docs/migration/dashboard-fastapi-transport.md` can flip between legacy
> and FastAPI transport via config or CLI flag with no data loss or
> restart corruption."

| Field | Value |
|-------|-------|
| Verifier (name / handle) | _TBD — fill before tagging_ |
| Verification date (UTC) | _TBD_ |
| Commit at verification (`git rev-parse HEAD`) | _TBD_ |
| Browser used | _TBD (Chrome / Firefox / Safari + version)_ |
| Project used | _TBD (path)_ |

**Required dashboard checks** (must all be observed in a real browser
under both `--transport fastapi` and `--transport legacy`):

- [ ] Mission list renders for the active project; the active mission is
      highlighted.
- [ ] Kanban view loads for at least one mission and shows lanes
      consistent with `tasks/WP*` files.
- [ ] Health endpoint reports `status: ok` and a populated
      `websocket_status`.
- [ ] Sync trigger button (when present in the UI) returns either
      `scheduled` or one of the documented skip / unavailable branches
      without an error toast.
- [ ] No console errors in the browser dev-tools panels attributable to
      the dashboard frontend.
- [ ] `/openapi.json` returns valid OpenAPI 3.x JSON (FastAPI transport
      only — legacy returns 404, that is correct).
- [ ] `/docs` and `/redoc` render with a list of every dashboard route
      (FastAPI transport only).
- [ ] Flipping `dashboard.transport` in `.kittify/config.yaml` from
      `fastapi` to `legacy` and restarting the dashboard preserves the
      URL, project state, and operator-visible behavior. No browser
      reload errors. No data loss.

**Verdict**: ☐ PASS · ☐ PASS WITH NOTES · ☐ FAIL

**Notes / observations**:

> _Operator records what was tested, on what data, and any deviations
> from the expected behavior here._

---

## Performance verification

### NFR-001 — Cold-start time (≤ 25 % regression vs legacy)

Run from repo root with the project in the current working directory:

```bash
.venv/bin/python scripts/bench_dashboard_startup.py --runs 5
```

The script writes `/tmp/bench_dashboard_startup.json`. Paste the
relevant fields here:

| Stack | Median cold-start (s) | Min | Max |
|-------|------------------------|-----|-----|
| legacy | _TBD_ | _TBD_ | _TBD_ |
| fastapi | _TBD_ | _TBD_ | _TBD_ |

| NFR-001 threshold (legacy median × 1.25) | _TBD_ |
|------------------------------------------|------|
| FastAPI median within threshold? | ☐ YES · ☐ NO |

If NO: document the rationale in the notes section. Options:

- Optimise (lazy imports, defer router registration, etc.) and re-bench
- Adjust threshold with reviewer signoff and a documented rationale
- Hold the release until optimisation lands

**Notes**:

> _Operator records the machine specs (`uname -a`), Python version, and
> any environmental factors._

### NFR-002 — Per-request overhead (≤ 30 % on `/api/features`)

Per-request median timing is documented as a soft NFR; the contract-parity
test (`tests/test_dashboard/test_transport_parity.py`) verifies functional
correctness across stacks. Operator-level timing measurement is optional
unless a regression is suspected.

| `/api/features` median (warm process, hot cache) | legacy: _TBD_ ms · fastapi: _TBD_ ms |

---

## Standing release gates

The items below apply to any release tag derived from this branch.

- [ ] All tests pass on the head commit:

      ```bash
      .venv/bin/python -m pytest tests/test_dashboard/ tests/architectural/ \
          tests/sync/test_daemon_intent_gate.py -q --timeout=120
      ```

      Expected: ≥ 354 passed, 1 skipped (the skip is the unrelated
      retrospective-events boundary test).

- [ ] OpenAPI snapshot test is green
      (`tests/test_dashboard/test_openapi_snapshot.py`). If a planned
      change altered the snapshot, the snapshot file was regenerated per
      [`contracts/openapi-stability.md`](./contracts/openapi-stability.md)
      and reviewer signoff was obtained.

- [ ] No new unauthorized callers of `ensure_sync_daemon_running` per
      `tests/sync/test_daemon_intent_gate.py::test_no_unauthorized_daemon_call_sites`.
      The gate scans both `src/specify_cli/` AND `src/dashboard/` (post
      mission `dashboard-extraction-followup-01KQMNTW`).

- [ ] FR-010 invariant holds:
      `tests/architectural/test_dashboard_boundary.py` — no imports from
      `specify_cli.dashboard.*` inside `src/dashboard/`.

- [ ] FastAPI handler purity holds:
      `tests/architectural/test_fastapi_handler_purity.py` — no
      `Response` / `JSONResponse` writes inside `@router.<method>`-decorated
      route function bodies.

- [ ] CHANGELOG entry exists for the version that includes this branch.

- [ ] No outstanding ✗ items from any post-merge mission review report
      saved alongside the parent missions
      (`dashboard-service-extraction-01KQMCA6`,
      `dashboard-extraction-followup-01KQMNTW`,
      `frontend-api-fastapi-openapi-migration-01KQN2JA`) that have not
      been remediated.

- [ ] Two follow-up issues filed for glossary and lint service extraction
      (the routers in `src/dashboard/api/routers/glossary.py` and
      `lint.py` carry `# TODO(follow-up)` markers — service extraction
      is explicitly out of scope for this mission).

---

## Process notes

- This file lives **on the branch** so the verification artifact ships
  with the code being verified.
- The migration runbook at
  [`docs/migration/dashboard-fastapi-transport.md`](../../docs/migration/dashboard-fastapi-transport.md)
  is the operator-facing companion to this checklist.
- The OpenAPI stability contract at
  [`contracts/openapi-stability.md`](./contracts/openapi-stability.md)
  governs what's allowed to change in the snapshot file vs what's
  prohibited.
- The FastAPI/OpenAPI ADR at
  [`architecture/2.x/adr/2026-05-02-2-fastapi-openapi-transport.md`](../../architecture/2.x/adr/2026-05-02-2-fastapi-openapi-transport.md)
  records the architectural decision and the future-MCP exposure
  pathway.
- The legacy `BaseHTTPServer` stack stays in tree until a separate
  retirement mission removes it. That mission is sequenced after at
  least one release of this branch with FastAPI as the default. The
  retirement mission updates this checklist to a "history" note.
