# Tasks: Tracker Binding Context Discovery

**Feature**: 062-tracker-binding-context-discovery
**Date**: 2026-04-04
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Branch**: `main` → `main`

## Subtask Index

| ID | Description | WP | Parallel |
|----|------------|-----|----------|
| T001 | Add binding_ref, display_label, provider_context fields to TrackerProjectConfig | WP01 | [P] |
| T002 | Update is_configured for dual-read (binding_ref OR project_slug) | WP01 | |
| T003 | Update to_dict()/from_dict() with backward compat + _extra passthrough | WP01 | |
| T004 | Write config roundtrip tests (new fields, legacy compat, unknown passthrough) | WP01 | |
| T005 | Write is_configured tests (all SaaS field combinations) | WP01 | |
| T006 | Create BindableResource + BindCandidate dataclasses with from_api() | WP02 | [P] |
| T007 | Create BindResult + ValidationResult + ResolutionResult with from_api() | WP02 | |
| T008 | Add find_candidate_by_position() pure helper | WP02 | |
| T009 | Write from_api() tests for each dataclass | WP02 | |
| T010 | Write find_candidate tests (valid, out of range, empty) | WP02 | |
| T011 | Enrich SaaSTrackerClientError with error_code, status_code, details | WP03 | [P] |
| T012 | Update _request_with_retry to populate enriched attrs from PRI-12 envelope | WP03 | |
| T013 | Write enriched error tests (codes preserved, backward compat) | WP03 | |
| T014 | Write regression tests (existing callers unaffected) | WP03 | |
| T015 | Add path constants for 4 new endpoints | WP04 | |
| T016 | Implement resources(provider) — GET | WP04 | |
| T017 | Implement bind_resolve(provider, project_identity) — POST | WP04 | |
| T018 | Implement bind_confirm(provider, candidate_token, project_identity) — POST | WP04 | |
| T019 | Implement bind_validate(provider, binding_ref, project_identity) — POST | WP04 | |
| T020 | Update status() and mappings() signatures (project_slug optional, binding_ref kwarg) | WP05 | [P] |
| T021 | Update pull(), push(), run() signatures (same pattern) | WP05 | |
| T022 | Update wire format: conditional routing key in query/body | WP05 | |
| T023 | Add validation: at least one routing key required | WP05 | |
| T024 | HTTP tests for resources() | WP06 | [P] |
| T025 | HTTP tests for bind_resolve() | WP06 | |
| T026 | HTTP tests for bind_confirm() | WP06 | |
| T027 | HTTP tests for bind_validate() | WP06 | |
| T028 | HTTP tests for existing endpoints with binding_ref routing | WP06 | |
| T029 | Tests for stale-binding error codes in enriched SaaSTrackerClientError | WP06 | |
| T030 | Add _resolve_routing_params() to SaaSTrackerService | WP07 | |
| T031 | Update existing delegated methods to use _resolve_routing_params() | WP07 | |
| T032 | Add _maybe_upgrade_binding_ref(response) helper | WP07 | |
| T033 | Wire _maybe_upgrade_binding_ref into each call site | WP07 | |
| T034 | Create StaleBindingError subclass + stale-binding detection | WP07 | |
| T035 | Write service tests: routing, upgrade, stale detection | WP07 | |
| T036 | Add discover(provider) → client.resources() → list[BindableResource] | WP08 | |
| T037 | Add resolve_and_bind() → orchestrate resolve → evaluate match_type | WP08 | |
| T038 | Exact match handling (skip confirm if binding_ref present, else confirm) | WP08 | |
| T039 | Candidates handling (return to caller, accept chosen, call confirm) | WP08 | |
| T040 | Candidate token retry (re-discover once on token-rejected) | WP08 | |
| T041 | Write service tests: discover, resolve exact/candidates/none, retry | WP08 | |
| T042 | Add discover(provider) to TrackerService facade (SaaS-only) | WP09 | |
| T043 | Update facade bind() for SaaS → delegates to resolve_and_bind() | WP09 | |
| T044 | Add status(all=False) parameter to facade | WP09 | |
| T045 | Guard local providers against discover() and status(all=True) | WP09 | |
| T046 | Write facade dispatch tests | WP09 | |
| T047 | Add discover_command() with --provider and --json flags | WP10 | [P] |
| T048 | Rich table output: numbered rows, bound/unbound distinction | WP10 | |
| T049 | --json output: full payload | WP10 | |
| T050 | Error handling: no installation, empty resources, auth errors | WP10 | |
| T051 | Number alignment: numbering = sort_position + 1 | WP10 | |
| T052 | Write CLI tests for discover command | WP10 | |
| T053 | Update bind_command() SaaS path: remove --project-slug, add --bind-ref, --select | WP11 | [P] |
| T054 | Discovery flow: call facade, handle exact/candidates/none | WP11 | |
| T055 | Candidate selection UI: numbered list, user input, validation | WP11 | |
| T056 | --bind-ref path: validate via facade, persist if valid | WP11 | |
| T057 | --select N path: auto-select candidate | WP11 | |
| T058 | Re-bind confirmation: existing binding warning | WP11 | |
| T059 | Write CLI tests for all bind scenarios | WP11 | |
| T060 | Add --all flag to status_command() | WP12 | [P] |
| T061 | Installation-wide output formatting | WP12 | |
| T062 | Error handling: SaaS-only guard for --all | WP12 | |
| T063 | Write CLI tests for status --all | WP12 | |
| T064 | Scenario 1 test: auto-bind (single confident match) | WP13 | |
| T065 | Scenario 2 test: ambiguous selection (multiple candidates) | WP13 | |
| T066 | Scenario 3/7b tests: no candidates, host unavailable | WP13 | |
| T067 | Scenario 4/5 tests: --bind-ref (valid/invalid), --select N | WP13 | |
| T068 | Scenario 6/7a tests: legacy config compat, opportunistic upgrade | WP13 | |
| T069 | Scenario 11/12 tests: stale binding, no silent fallback | WP13 | |

## Work Packages

### Wave 1 — Foundation (parallel, no inter-dependencies)

#### WP01: Config Model Evolution
**Priority**: High | **Subtasks**: T001-T005 (5) | **~350 lines**
**Dependencies**: None
**Prompt**: [tasks/WP01-config-model-evolution.md](tasks/WP01-config-model-evolution.md)

Evolve `TrackerProjectConfig` with `binding_ref`, `display_label`, `provider_context` fields. Update `is_configured` for dual-read. Add `_extra` dict for unknown field passthrough. Full backward compatibility with pre-062 configs.

- [x] T001: Add new fields to dataclass
- [x] T002: Update is_configured property
- [x] T003: Update to_dict()/from_dict() with _extra passthrough
- [x] T004: Write roundtrip tests
- [x] T005: Write is_configured tests

#### WP02: Discovery Dataclasses
**Priority**: High | **Subtasks**: T006-T010 (5) | **~350 lines**
**Dependencies**: None
**Prompt**: [tasks/WP02-discovery-dataclasses.md](tasks/WP02-discovery-dataclasses.md)

Create pure data module `tracker/discovery.py` with dataclasses for API response parsing: `BindableResource`, `BindCandidate`, `BindResult`, `ValidationResult`, `ResolutionResult`. No I/O, no terminal interaction.

- [x] T006: Create BindableResource + BindCandidate
- [x] T007: Create BindResult + ValidationResult + ResolutionResult
- [x] T008: Add find_candidate_by_position() helper
- [x] T009: Write from_api() tests
- [x] T010: Write find_candidate tests

#### WP03: Client Error Enrichment
**Priority**: High | **Subtasks**: T011-T014 (4) | **~300 lines**
**Dependencies**: None
**Prompt**: [tasks/WP03-client-error-enrichment.md](tasks/WP03-client-error-enrichment.md)

Enrich `SaaSTrackerClientError` with `error_code`, `status_code`, `details`, `user_action_required` attributes. Update `_request_with_retry` to populate from PRI-12 envelope. Backward-compatible with existing callers.

- [x] T011: Enrich exception class
- [x] T012: Update _request_with_retry
- [x] T013: Write enriched error tests
- [x] T014: Write regression tests

### Wave 2 — Client Layer (depends on Wave 1)

#### WP04: SaaS Client New Methods
**Priority**: High | **Subtasks**: T015-T019 (5) | **~400 lines**
**Dependencies**: WP02, WP03
**Prompt**: [tasks/WP04-saas-client-new-methods.md](tasks/WP04-saas-client-new-methods.md)

Add 4 new methods to `SaaSTrackerClient`: `resources()`, `bind_resolve()`, `bind_confirm()`, `bind_validate()`. Each follows the existing `_request_with_retry` pattern.

- [x] T015: Add path constants
- [x] T016: Implement resources()
- [x] T017: Implement bind_resolve()
- [x] T018: Implement bind_confirm()
- [x] T019: Implement bind_validate()

#### WP05: Existing Endpoint Evolution
**Priority**: High | **Subtasks**: T020-T023 (4) | **~300 lines**
**Dependencies**: WP03
**Prompt**: [tasks/WP05-existing-endpoint-evolution.md](tasks/WP05-existing-endpoint-evolution.md)

Update all 5 existing client methods (`status`, `mappings`, `pull`, `push`, `run`) to accept optional `binding_ref` alongside `project_slug`. Coordinated SaaS contract change.

- [x] T020: Update GET method signatures
- [x] T021: Update POST method signatures
- [x] T022: Update wire format logic
- [x] T023: Add routing key validation

### Wave 3 — Tests + Service Core (depends on Waves 1-2)

#### WP06: Client HTTP Contract Tests
**Priority**: High | **Subtasks**: T024-T029 (6) | **~500 lines**
**Dependencies**: WP04, WP05
**Prompt**: [tasks/WP06-client-http-contract-tests.md](tasks/WP06-client-http-contract-tests.md)

HTTP-level contract tests for all 4 new endpoints + binding_ref routing variants on existing endpoints. Uses `_make_response()` pattern from existing test_saas_client.py.

- [x] T024: Tests for resources()
- [x] T025: Tests for bind_resolve()
- [x] T026: Tests for bind_confirm()
- [x] T027: Tests for bind_validate()
- [x] T028: Tests for existing endpoints with binding_ref
- [x] T029: Tests for stale-binding error codes

#### WP07: Service Layer – Routing & Upgrade
**Priority**: High | **Subtasks**: T030-T035 (6) | **~450 lines**
**Dependencies**: WP01, WP03, WP05
**Prompt**: [tasks/WP07-service-routing-upgrade.md](tasks/WP07-service-routing-upgrade.md)

Core service infrastructure: routing key resolution, opportunistic binding_ref upgrade, stale-binding detection. Touches all existing service methods.

- [x] T030: Add _resolve_routing_params()
- [x] T031: Update existing methods to use it
- [x] T032: Add _maybe_upgrade_binding_ref()
- [x] T033: Wire upgrade into call sites
- [x] T034: Create StaleBindingError + detection
- [x] T035: Write service tests

### Wave 4 — Service Orchestration + Facade (depends on Wave 3)

#### WP08: Service Layer – Discovery & Bind
**Priority**: High | **Subtasks**: T036-T041 (6) | **~450 lines**
**Dependencies**: WP02, WP04, WP07
**Prompt**: [tasks/WP08-service-discovery-bind.md](tasks/WP08-service-discovery-bind.md)

New service methods: `discover()` for resource inventory, `resolve_and_bind()` for the full discovery-selection-confirmation flow. Handles exact match, candidates, none, and token retry.

- [x] T036: Add discover()
- [x] T037: Add resolve_and_bind()
- [x] T038: Exact match handling
- [x] T039: Candidates handling
- [x] T040: Token retry
- [x] T041: Write service tests

#### WP09: TrackerService Facade
**Priority**: High | **Subtasks**: T042-T046 (5) | **~350 lines**
**Dependencies**: WP07, WP08
**Prompt**: [tasks/WP09-tracker-service-facade.md](tasks/WP09-tracker-service-facade.md)

Add `discover()`, update `bind()`, add `status(all=)` to the `TrackerService` dispatch facade. Guard local providers against SaaS-only operations.

- [x] T042: Add discover() to facade
- [x] T043: Update bind() dispatch
- [x] T044: Add status(all=) parameter
- [x] T045: Guard local providers
- [x] T046: Write facade tests

### Wave 5 — CLI Commands (depends on Wave 4; parallel within wave)

#### WP10: CLI Discover Command
**Priority**: High | **Subtasks**: T047-T052 (6) | **~450 lines**
**Dependencies**: WP09
**Prompt**: [tasks/WP10-cli-discover-command.md](tasks/WP10-cli-discover-command.md)

New `tracker discover --provider <provider>` command with rich table default + `--json`. Numbered rows align with `--select N`.

- [x] T047: Add discover_command()
- [x] T048: Rich table output
- [x] T049: --json output
- [x] T050: Error handling
- [x] T051: Number alignment
- [x] T052: Write CLI tests

#### WP11: CLI Bind Command Update
**Priority**: High | **Subtasks**: T053-T059 (7) | **~500 lines**
**Dependencies**: WP09
**Prompt**: [tasks/WP11-cli-bind-command-update.md](tasks/WP11-cli-bind-command-update.md)

Rewrite SaaS bind path: remove `--project-slug`, add `--bind-ref`/`--select`. Discovery flow with candidate selection, re-bind confirmation, non-interactive modes.

- [x] T053: Update bind_command() flags
- [x] T054: Discovery flow
- [x] T055: Candidate selection UI
- [x] T056: --bind-ref path
- [x] T057: --select N path
- [x] T058: Re-bind confirmation
- [x] T059: Write CLI tests

#### WP12: CLI Status --all
**Priority**: Medium | **Subtasks**: T060-T063 (4) | **~250 lines**
**Dependencies**: WP09
**Prompt**: [tasks/WP12-cli-status-all.md](tasks/WP12-cli-status-all.md)

Add `--all` flag to `tracker status` for installation-wide summary. Different output format from project-scoped status.

- [x] T060: Add --all flag
- [x] T061: Installation-wide formatting
- [x] T062: Error handling
- [x] T063: Write CLI tests

### Wave 6 — Integration (depends on all above)

#### WP13: Integration & Acceptance Tests
**Priority**: Medium | **Subtasks**: T064-T069 (6) | **~400 lines**
**Dependencies**: WP10, WP11, WP12
**Prompt**: [tasks/WP13-integration-acceptance-tests.md](tasks/WP13-integration-acceptance-tests.md)

End-to-end acceptance tests covering all 12 spec scenarios. Mock at SaaSTrackerClient boundary. Verify full flow from CLI through service to config persistence.

- [x] T064: Scenario 1 (auto-bind)
- [x] T065: Scenario 2 (ambiguous selection)
- [x] T066: Scenarios 3, 7b (no candidates, host unavailable)
- [x] T067: Scenarios 4, 5 (--bind-ref, --select N)
- [ ] T068: Scenarios 6, 7a (legacy compat, opportunistic upgrade)
- [ ] T069: Scenarios 11, 12 (stale binding, no fallback)

## Summary

| Metric | Value |
|--------|-------|
| Total subtasks | 69 |
| Total work packages | 13 |
| Avg subtasks/WP | 5.3 |
| Avg prompt size | ~375 lines |
| Max prompt size | ~500 lines (WP06, WP11) |
| Waves | 6 |
| Max parallel WPs per wave | 3 (Waves 1, 5) |
