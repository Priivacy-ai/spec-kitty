# Feature Specification: Mission Registry and API Boundary Doctrine

**Feature Slug**: `mission-registry-and-api-boundary-doctrine-01KQPDBB`
**Mission ID**: `01KQPDBBC0BP9G41751TN4TF2T`
**Mission Type**: software-dev
**Created**: 2026-05-03
**Target Branch**: `feature/650-dashboard-ui-ux-overhaul`
**Parent epic**: [#645 — Stable Application API Surface (UI / CLI / MCP / SDK)](https://github.com/Priivacy-ai/spec-kitty/issues/645)
**Primary tracker**: [#956](https://github.com/Priivacy-ai/spec-kitty/issues/956)

## Overview

Today, every consumer of mission and work-package data — the dashboard FastAPI routers, the CLI subcommand `spec-kitty dashboard --json`, and (in the future) MCP tools and external SDKs — reads `kitty-specs/<slug>/` from the filesystem through independent code paths. There is no caching, no observability hook, and no architectural test that forbids transport-side modules from importing the scanner directly.

On a project with 144 missions (this repo), `dashboard.js` polling the FastAPI surface at 1 Hz triggers ~720 file `open()` syscalls per second per browser tab. Two transports reading the same data through two independent readers means a bugfix to one path can land silently with no enforcement that the other path keeps producing the same shape.

This mission ships three coupled deliverables that, together, close the gap between "we have services" (already true post mission `frontend-api-fastapi-openapi-migration-01KQN2JA`) and "every consumer reads through the same canonical service layer" (the architectural goal):

1. **`MissionRegistry` + `WorkPackageRegistry`** — the canonical service-layer entry point. Mtime-cached filesystem reads. Single sanctioned reader for transport-side modules.
2. **Three new doctrine artefacts** — `DIRECTIVE_API_DEPENDENCY_DIRECTION`, `DIRECTIVE_REST_RESOURCE_ORIENTATION`, `HATEOAS-LITE` paradigm — making the architectural rules explicit so future work cannot regress them by accident.
3. **Three architectural tests** — each enforces one of the directives in CI.

Per planner+architect agreement (initiative § 3 and the planner's revision), these three are bundled into one mission rather than split: directives without enforcement tests rot.

A **prerequisite boyscout WP (WP01)** lands first and gates every other WP in the mission. Its job is to leave the substrate clean enough that the registry can be built on top without inheriting pre-existing debt.

## Domain Language

| Term | Canonical meaning |
|------|-------------------|
| **Transport** | A code surface that exposes mission/WP data to a consumer: a FastAPI router, a CLI subcommand body, a (future) MCP tool function. |
| **Service layer** | The Pydantic-free Python objects in `src/dashboard/services/` that own retrieval logic. The registry lives here. |
| **Backbone** | The filesystem itself plus the low-level scanner walkers in `specify_cli.dashboard.scanner` / `specify_cli.scanner`. |
| **Single sanctioned reader** | The architectural rule that exactly one well-defined object — the registry — is allowed to talk to the backbone. Transports go through the service layer; the service layer goes through the registry; the registry goes to the backbone. |
| **HATEOAS-LITE** | A subset hypermedia convention: every resource response includes a `_links: {<rel>: {href: ...}}` block. We do not adopt full HAL or JSON:API; see initiative § 3.3 for the future-graduation triggers. |
| **Boyscout WP** | A cleanup work package that lands first and gates the rest of the mission. Pre-existing debt that would otherwise compound during the substantive work. |

## User Scenarios & Testing

### User Story 1 — Future-contributor adding a new transport (P0)

A future contributor adds a new transport — say, an MCP tool that lists missions for an LLM agent. They search the codebase for "how does the dashboard read missions?" and find `MissionRegistry.list_missions()`. Their MCP tool calls that method directly. They do not need to know about `scan_all_features`, `build_mission_registry`, `kitty-specs/<slug>/meta.json`, or the cache invalidation rules — those are the registry's concern. The new transport ships with no architectural-test failures because the boundary directive holds by construction.

### User Story 2 — Operator using the dashboard at scale (P0)

An operator opens the dashboard browser tab and leaves it running for an hour while triaging missions across a large project (~150 missions). The browser polls every second. The dashboard process serves every poll from the registry's mtime-cached snapshot — file `open()` count stays in the single digits per second (the cache-stale check), not the ~720 per second the legacy FastAPI surface produces today. CPU stays low; battery doesn't drain.

### User Story 3 — Reviewer auditing the boundary (P1)

A reviewer pulls a PR that adds a new FastAPI route. They want to confirm the new route does not bypass the service layer. They run `pytest tests/architectural/test_transport_does_not_import_scanner.py` and see green: the AST scanner walked every router file and found no direct scanner imports. The reviewer does not need to manually grep for forbidden imports — CI does it deterministically.

### User Story 4 — Doctrine reader looking up "what is the API design rule?" (P1)

A new contributor reads the doctrine catalogue. They find `DIRECTIVE_API_DEPENDENCY_DIRECTION` (transports go through services; services go through the registry) and `DIRECTIVE_REST_RESOURCE_ORIENTATION` (URLs are noun-shaped; methods carry the verb). The HATEOAS-LITE paradigm describes the `_links` convention. Each directive cross-links the architectural test that enforces it, so the contributor can read the rule and inspect the enforcement in the same workflow.

### Edge cases

- **Stale `status.json` from a daemon mutation**: a background `spec-kitty next` process may rewrite `status.json` while a dashboard request is mid-scan. The registry's cache invalidation must handle the file changing under it without corrupting the served snapshot.
- **File deleted then recreated with identical mtime**: the cache key includes `(mtime_ns, file_size, hash_of_filenames)` so identical-mtime drift does not serve stale data.
- **Concurrent writes during a scan**: the registry's read path is single-threaded per cache entry; concurrent reads share the cache; concurrent writes upstream invalidate it on the next access.
- **Missing `meta.json`**: a malformed or absent `meta.json` for one mission must not crash a list-missions call. The registry returns the mission as `legacy:<slug>` per the existing convention from mission #083 (Mission Identity Model).
- **CLI consumer running outside the dashboard process**: the CLI command `spec-kitty dashboard --json` runs in a separate process and gets its own registry instance. No shared cache across processes; mtime-based invalidation keeps them eventually consistent.

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | A `MissionRegistry` Python class lives at `src/dashboard/services/registry.py` with public methods: `list_missions() -> list[MissionRecord]`, `get_mission(mission_id_or_slug: str) -> MissionRecord \| None`, `list_work_packages(mission_id_or_slug: str) -> list[WorkPackageRecord]`, `get_work_package(mission_id_or_slug: str, wp_id: str) -> WorkPackageRecord \| None` | Approved |
| FR-002 | The registry mtime-caches its reads. Cache keys use `(mtime_ns, file_size, sorted_dirent_names_hash)` for the relevant subtree (`kitty-specs/<slug>/meta.json`, `kitty-specs/<slug>/status.events.jsonl`, `kitty-specs/<slug>/tasks/`). Cache hits do not touch the filesystem beyond the staleness check (3 stat calls per missed cache entry); cache misses re-scan only the affected subtree. | Approved |
| FR-003 | The registry is the only sanctioned caller of `scan_all_features`, `scan_feature_kanban`, `build_mission_registry`, `resolve_active_feature`, `resolve_feature_dir`, `format_path_for_display` from `specify_cli.dashboard.scanner`. The shimmed `specify_cli.scanner` re-export is downgraded to "internal use only" via docstring; the architectural test (FR-009) catches any new violator. | Approved |
| FR-004 | All existing FastAPI routers under `src/dashboard/api/routers/` that currently call into the scanner / `MissionScanService` are migrated to call into the registry instead. Routers that only call other services (token validation, file reader, sync) are unchanged. | Approved |
| FR-005 | The CLI subcommand `spec-kitty dashboard --json` (`src/specify_cli/cli/commands/dashboard.py:59`) is migrated to call the registry instead of `build_mission_registry` directly. | Approved |
| FR-006 | A new directive `DIRECTIVE_API_DEPENDENCY_DIRECTION` is authored in the shipped doctrine (`src/doctrine/directives/shipped/`). Rule: any module under `src/dashboard/api/routers/`, `src/specify_cli/cli/commands/`, or future MCP tool surfaces consumes mission / WP / artifact data exclusively via the canonical service-layer interface. Forbidden imports (and their AST patterns) are enumerated in the directive body. The directive cross-links the architectural test in FR-009. | Approved |
| FR-007 | A new directive `DIRECTIVE_REST_RESOURCE_ORIENTATION` is authored in the shipped doctrine. Rule: public HTTP endpoints follow resource-oriented naming (collection / item / sub-collection paths; HTTP method names the verb; action-shaped URLs are explicitly tagged `actions`). The directive references the URL-naming architectural test in FR-010. | Approved |
| FR-008 | A new paradigm `HATEOAS-LITE` is authored in the shipped doctrine (`src/doctrine/paradigms/shipped/`). Rule: resource responses include a `_links: dict[str, Link]` block. The paradigm carries the rationale for choosing lite over full HAL / JSON:API and documents the future-graduation triggers (initiative § 3.3). The marker class `ResourceModel` it requires is introduced as a Pydantic base in `src/dashboard/api/models.py` so subsequent missions can subclass it. | Approved |
| FR-009 | A new architectural test `tests/architectural/test_transport_does_not_import_scanner.py` AST-walks every file under `src/dashboard/api/routers/` and `src/specify_cli/cli/commands/dashboard.py`. It fails on any import from `specify_cli.dashboard.scanner`, `specify_cli.scanner`, or any module path matching `*scanner*` outside an explicit allowlist. Includes a positive meta-test (synthetic violator detected) and a negative meta-test (synthetic clean module passes). | Approved |
| FR-010 | A new architectural test `tests/architectural/test_url_naming_convention.py` walks the FastAPI app's `/openapi.json` paths. Every path either matches the resource-noun convention (`/api/<collection>` or `/api/<collection>/{id}`...) or is registered in a small allowlist for action-shaped URLs (`/api/sync/trigger`, `/api/shutdown`). Includes positive + negative meta-tests. | Approved |
| FR-011 | A new architectural test `tests/architectural/test_resource_models_have_links.py` walks the Pydantic class hierarchy under `src/dashboard/api/models.py`. Every class subclassing the marker `ResourceModel` declares a `_links` field of the documented shape. The test lights up empty in this mission (no resource models exist yet — they land in mission B); the marker class and the test are in place so mission B can subclass and the test goes from informational to enforcing. Includes positive + negative meta-tests. | Approved |
| FR-012 | The ADR `architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md` is promoted from `Proposed` to `Accepted`. The status line is updated; the ADR README index reflects the new status. | Approved |
| FR-013 | The boyscout WP (WP01 of this mission) audits the existing scanner entry points and documents each one's I/O shape in a table inside `src/specify_cli/dashboard/scanner.py`'s module docstring. Functions the registry will subsume gain a `# TODO(remove with mission-registry-and-api-boundary-doctrine-01KQPDBB)` marker. No behavioural changes in this WP. | Approved |
| FR-014 | The boyscout WP replaces the `git update-index --assume-unchanged` workaround for daemon-driven `kitty-specs/*/status.json` drift. The chosen direction (stop the daemon mutation, or gitignore the materialised snapshot) is recorded in WP01's review record with rationale. The canonical event log `status.events.jsonl` remains tracked. | Approved |
| FR-015 | The boyscout WP adds a baseline parity test `tests/test_dashboard/test_scanner_entrypoint_parity.py`. For the same fixture project, it asserts `scan_all_features(...)` and `build_mission_registry(...)` produce structurally compatible mission identity (same set of `mission_id`s; same `mission_slug`s for shared rows). A failing baseline is acceptable and documented; the test is the safety net for the registry refactor in subsequent WPs. | Approved |
| FR-016 | The ownership map (`architecture/2.x/05_ownership_map.md`) and manifest (`05_ownership_manifest.yaml`) Dashboard slice are updated to reflect the registry as the canonical service-layer reader; the new doctrine artefacts and architectural tests are referenced. The "Open dashboard sub-tickets" callout marks #956 as `in-progress` while this mission runs and `done` when it merges. | Approved |
| FR-017 | The migration runbook (`docs/migration/dashboard-fastapi-transport.md`) gains a section explaining the registry's existence and the `DIRECTIVE_API_DEPENDENCY_DIRECTION` constraint so future contributors do not re-introduce per-request scanner walks. | Approved |

## Non-Functional Requirements

| ID | Attribute | Threshold | Status |
|----|-----------|-----------|--------|
| NFR-001 | Per-request file `open()` count on `/api/features` (warm cache, cache-hit case) | ≤ 5 syscalls per request, measured by `strace -c -e trace=openat` against the running dashboard for a 30-second poll loop | Approved |
| NFR-002 | Cache-miss latency on a full re-scan (cold cache, 144-mission project) | Within 25 % of the existing `scan_all_features` latency on the same machine — the registry adds a thin wrapper, not a heavy substrate | Approved |
| NFR-003 | Cache-stale check overhead (cache-hit path) | ≤ 3 stat syscalls per `list_missions()` call (one per cache key component); zero `open()` calls | Approved |
| NFR-004 | New top-level Python dependencies | Zero. The registry uses stdlib `os.stat` for mtime; no new packages added to `pyproject.toml` | Approved |
| NFR-005 | Test suite execution time | Total test wall-clock increases by ≤ 10 % after the new tests + the boyscout parity test land | Approved |
| NFR-006 | Type-checking debt | No new `# type: ignore` directives in `src/dashboard/services/registry.py` or in any router migrated from the scanner to the registry | Approved |
| NFR-007 | Doctrine artefacts pass schema validation | Each new directive / paradigm passes `tests/doctrine/test_*_schema.py` (or equivalent) on first commit; no schema-suppression markers added | Approved |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | All changes land on `feature/650-dashboard-ui-ux-overhaul`; no separate feature branches; no PRs to other branches | Confirmed |
| C-002 | The registry is the **only** sanctioned reader for the scanner functions enumerated in FR-003. The architectural test in FR-009 fails CI on any new violator. The legacy scanner shim at `src/specify_cli/scanner.py` remains importable but is downgraded to internal-use-only via docstring | Confirmed |
| C-003 | Mission-wide test sanity rules — every test must constrain real production code paths (synthetic-fixture-only tests are forbidden); every architectural test ships with a positive AND a negative meta-test; performance verification uses syscall tracing not file-walk counting; OpenAPI snapshot is regenerated ONCE at the end of the mission, not per WP; the registry's mtime-cache edge cases (file deleted-then-recreated with identical mtime; truncated file with same length; concurrent writes during a scan) each have an explicit named test | Confirmed |
| C-004 | The boyscout WP01 does NOT change production behaviour. It only documents, removes the assume-unchanged workaround, and adds a parity baseline test. Every other WP in the mission depends on WP01 (declared via `dependencies: [WP01]` in WP frontmatter); WP01 is the ordering anchor | Confirmed |
| C-005 | No public API surface change in this mission. `/api/features` and `/api/kanban/{id}` continue to return their existing shapes; only the backing data flow changes (now via registry). The deprecation cycle to rename to `/api/missions` is mission B's job (#957), not this mission | Confirmed |
| C-006 | The HATEOAS-LITE paradigm declares the `_links` convention but no resource response actually includes `_links` yet. The marker `ResourceModel` and the architectural test FR-011 are in place; the actual `_links` blocks land when mission B introduces the new resource-oriented endpoints | Confirmed |
| C-007 | The companion tickets #957 (resource-oriented endpoints) and #958 (OpenAPI tag grouping) are explicitly OUT OF SCOPE for this mission and will be addressed in a follow-up mission B per the planner's collapse. Mention them only as cross-references; no implementation | Confirmed |
| C-008 | The two open service-extraction follow-ups #954 (glossary) and #955 (lint) are OUT OF SCOPE; addressed in mission C | Confirmed |

## Key Entities

- **`MissionRegistry`** — `src/dashboard/services/registry.py`. Stateful Python object; one instance per process. Public methods enumerated in FR-001. Cache implementation private. Constructor takes `project_dir: Path`.
- **`WorkPackageRegistry`** — same file (or sibling module). Per-mission scope. Cache invalidates on changes to `kitty-specs/<slug>/tasks/` or `kitty-specs/<slug>/status.events.jsonl` mtime / dirent set.
- **`MissionRecord`** / **`WorkPackageRecord`** — Pydantic-free Python `dataclass` types returned by the registry. Internal to the service layer; routers map them to Pydantic response models at the transport boundary.
- **`ResourceModel`** — new Pydantic marker base class in `src/dashboard/api/models.py`. Subclassing it asserts (via FR-011 test) that the model declares a `_links` field. Used by mission B's new resource-oriented endpoints.
- **`DIRECTIVE_API_DEPENDENCY_DIRECTION`** — shipped doctrine artefact; see FR-006.
- **`DIRECTIVE_REST_RESOURCE_ORIENTATION`** — shipped doctrine artefact; see FR-007.
- **`HATEOAS-LITE`** — shipped paradigm artefact; see FR-008.
- **Three architectural tests** — `tests/architectural/test_transport_does_not_import_scanner.py`, `test_url_naming_convention.py`, `test_resource_models_have_links.py`.
- **ADR `2026-05-03-1-dashboard-mission-registry-and-cache.md`** — already exists in `Proposed` state; this mission promotes it to `Accepted` (FR-012).

## Success Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| SC-001 | The registry is the only sanctioned reader of the legacy scanner functions; CI fails on any new violator from a router or CLI command | `tests/architectural/test_transport_does_not_import_scanner.py` passes; positive meta-test confirms it would fail on a violator |
| SC-002 | Per-request file `open()` count on `/api/features` warm-cache stays ≤ 5 | NFR-001 syscall trace recorded in WP06's review record |
| SC-003 | Three new doctrine artefacts exist, pass schema validation, and are cross-linked from the ownership map | NFR-007 schema test passes; ownership map review |
| SC-004 | The mission's full test suite (existing + new) is green | `pytest tests/test_dashboard/ tests/architectural/ tests/sync/test_daemon_intent_gate.py -q` returns success |
| SC-005 | The boyscout WP01 leaves the substrate clean: no `assume-unchanged` files for `kitty-specs/*/status.json`; scanner module docstring carries the entry-point table; parity baseline test exists | `git ls-files -v` clean; visual code review |
| SC-006 | The ADR is promoted to `Accepted` and the README index reflects this | Index review |
| SC-007 | Post-merge mission review finds zero blocking drift, risk, or security findings | `/spec-kitty.mission-review` after merge |

## Assumptions

- The existing scanner functions (`scan_all_features`, etc.) are correct today and produce the data shape consumers expect. The registry is a wrapper, not a rewrite. Any divergence the parity baseline test (FR-015) catches is a pre-existing bug in scanner divergence, not a registry bug.
- The daemon-driven `status.json` drift problem (FR-014) has a discoverable root cause within ~30 minutes of investigation; the WP01 reviewer can choose between (a) stop the daemon, or (b) gitignore the materialised snapshots. Both are reversible.
- The shipped doctrine schema validation infrastructure exists today and can validate the three new artefacts on first commit (NFR-007 assumes this; if it doesn't, the WP introducing the artefacts must extend the schema test).
- No consumer outside the dashboard / CLI / planned MCP surface reads from `kitty-specs/<slug>/` directly. If one exists, it is deemed legacy and out of scope (the `# TODO(remove)` marker in scanner docstrings makes this explicit).
- The strangler period for the legacy scanner shim continues; no removal of `specify_cli.scanner` until a separate retirement mission.

## Governance

### Active Directives

- **DIRECTIVE_024** (Locality of Change) — allowed scope: `src/dashboard/services/`, `src/dashboard/api/`, `src/specify_cli/cli/commands/dashboard.py`, `src/specify_cli/dashboard/scanner.py` (docstring only — no behaviour change), `src/doctrine/directives/shipped/`, `src/doctrine/paradigms/shipped/`, `tests/architectural/`, `tests/test_dashboard/`, `architecture/2.x/`, `docs/migration/`, `kitty-specs/<this-mission>/`.
- **DIRECTIVE_010** (Test Coverage Discipline) — every new module has at least one test that exercises a non-trivial path; the parity baseline (FR-015) plus the registry unit tests plus the three architectural tests together meet this for substantive coverage.
- **DIRECTIVE_036** (Adapter Test Pattern) — the registry's tests use real fixture projects (mkdir + meta.json + status.events.jsonl) rather than mocked scanner returns. This is enforced by the mission-wide test sanity rule in C-003.
- **NEW: DIRECTIVE_API_DEPENDENCY_DIRECTION** (introduced by FR-006) — applies from this mission forward.
- **NEW: DIRECTIVE_REST_RESOURCE_ORIENTATION** (introduced by FR-007) — applies from this mission forward; first enforcement is the test in FR-010.

### Applied Tactics

- `mtime-cache-with-fallback` — for the registry's invalidation strategy (NFR-001..003).
- `architectural-test-with-positive-and-negative-meta-tests` — every architectural test ships with both meta-tests; this is the C-003 mission-wide rule.
- `boyscout-cleanup-as-prerequisite-wp` — WP01 lands first and gates the rest.
- `adr-drafting-workflow` (via `how-we-apply-directive-003`) — promotes the existing Proposed ADR to Accepted (FR-012).

## Out of Scope (explicit non-goals)

- **NG-1**: No new HTTP endpoints. `/api/missions/{id}/...` is mission B's scope (#957).
- **NG-2**: No `_links` blocks on existing responses. The HATEOAS-LITE paradigm and the `ResourceModel` marker land here; actual application is mission B.
- **NG-3**: No URL renames. `/api/features` and `/api/kanban/{id}` keep their current paths; renames are mission B.
- **NG-4**: No OpenAPI tag grouping. Mission B's WP06.
- **NG-5**: No glossary or lint service extraction. Missions C (#954, #955).
- **NG-6**: No retirement of the legacy `BaseHTTPServer` stack. Separate retirement mission, sequenced after at least one release with FastAPI as default.
- **NG-7**: No async update transport (WebSocket / SSE). Step 6 of epic #645.
- **NG-8**: No frontend (`dashboard.js`) refactor. Sibling epic #650.
