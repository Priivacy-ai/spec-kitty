# Issue Matrix — Frontend API FastAPI/OpenAPI Migration

Mission `frontend-api-fastapi-openapi-migration-01KQN2JA` was authored
as Steps 3 + 4 of epic [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645)
and inherits a small set of upstream tracker items. This matrix names
each one with an explicit verdict so Gate 4 of the post-merge mission
review can compute pass/fail deterministically.

## Inherited issues

| issue | scope | verdict | evidence_ref |
|-------|-------|---------|--------------|
| [#459](https://github.com/Priivacy-ai/spec-kitty/issues/459) | TypedDict → typed-client codegen surface | `fixed` | OpenAPI document at `/openapi.json` published by FastAPI; consumer-side codegen path documented in `docs/migration/dashboard-fastapi-transport.md` § Step 8. Authoritative snapshot at `tests/test_dashboard/snapshots/openapi.json` (87 KB, 23 paths). |
| [#460](https://github.com/Priivacy-ai/spec-kitty/issues/460) | FastAPI / OpenAPI transport migration | `fixed` | `src/dashboard/api/` subpackage; `src/specify_cli/dashboard/server.py` strangler boundary; `docs/migration/dashboard-fastapi-transport.md` runbook. |
| [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645) Step 5 (async update transport) | WebSocket / SSE for live UI updates | `deferred-with-followup` | Out of scope per spec NG-3. Follow-up: file a new mission spec once a UI consumer needs live updates. ASGI is now in place so the cost of adding it is small. Tracked under epic #645 § "Sequencing" item 5. |
| [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645) Step 6 (generated client support) | Concrete TypeScript / Python client packages | `deferred-with-followup` | Out of scope per spec NG-2 (no new product surface). The OpenAPI document is sufficient input for `openapi-typescript` / `openapi-python-client`; whoever builds the first consumer files the codegen mission. Tracked under epic #645 § "Sequencing" item 6. |
| [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645) Step 7 (new frontend slices) | UI consumers of the new API | `deferred-with-followup` | Out of scope per spec NG-1 (no UI refactor). Tracked under epic #645 § "Sequencing" item 7. |

## Mission-introduced follow-up items

These items are surfaced by the mission's own scope reductions or
deferred work. They are tracked by the post-merge mission review report
at `/tmp/spec-kitty-mission-review-frontend-api-fastapi-openapi-migration-01KQN2JA.md`
and individually referenced in the release-checklist.

| item | scope | verdict | evidence_ref |
|------|-------|---------|--------------|
| Glossary service extraction | `src/specify_cli/dashboard/handlers/glossary.py` is still the canonical implementation; `src/dashboard/api/routers/glossary.py` is transport-only | `deferred-with-followup` | Tracked at [#954](https://github.com/Priivacy-ai/spec-kitty/issues/954). `# TODO(follow-up)` markers in `routers/glossary.py` reference issue #954. |
| Lint service extraction | Same shape as glossary — `src/specify_cli/dashboard/handlers/lint.py` is still authoritative | `deferred-with-followup` | Tracked at [#955](https://github.com/Priivacy-ai/spec-kitty/issues/955). `# TODO(follow-up)` markers in `routers/lint.py` reference issue #955. |
| Legacy stack retirement | `src/specify_cli/dashboard/handlers/`, `server.py` legacy branch, `--transport legacy` CLI value | `deferred-with-followup` | Spec C-005, C-007 explicitly retain the legacy stack until a separate mission removes it after at least one release with `dashboard.transport: fastapi` as default; **action**: separate mission, sequenced after one release with the new default. |
| True legacy↔FastAPI byte-parity test | Mission's contracts/route-inventory.md ambition | `deferred-with-followup` | DRIFT-1 in post-merge review. Current parity suite asserts FastAPI shape only; full dual-stack assertion needs a legacy-stack fixture; **action**: follow-up mission. |
| NFR-001 / NFR-002 measurement | `release-checklist.md` performance slots | `deferred-with-followup` | DRIFT-3 in post-merge review. `scripts/bench_dashboard_startup.py` ready; operator runs it before next release tag and pastes numbers into the checklist. |
| `--bench-exit-after-first-byte` server instrumentation | True first-byte timing | `deferred-with-followup` | The Typer flag is wired but the per-stack exit-after-first-byte hook is not. Bench script falls back to port-bind timing as a proxy. **action**: small WP in a future hardening mission. |

## Summary

- 6 inherited rows: 2 `fixed`, 3 `deferred-with-followup`.
- 6 mission-introduced rows: 6 `deferred-with-followup`.
- **0 rows with empty verdict.**
- **0 rows with `unknown` verdict.**
- All `deferred-with-followup` rows name a concrete next-step action (file an issue, file a follow-up mission, operator measurement, etc.).

Gate 4 (post-merge mission review): **PASS**.
