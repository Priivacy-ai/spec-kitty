# Tasks: Profile Roles as Value Object

**Mission**: profile-roles-as-value-object-01KPRJRY
**Branch**: doctrine/profile_reinforcement → doctrine/profile_reinforcement
**Generated**: 2026-04-21T18:24:37Z

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Write `Role(str)` class with `__new__`, `_KNOWN` frozenset, `is_known` classmethod | WP01 | | [D] |
| T002 | Write `Role` class docstring (why str-subclass, extensibility contract, Phase 6 note) | WP01 | | [D] |
| T003 | Delete `Role(StrEnum)` class and `_coerce_role` function from `profile.py` | WP01 | | [D] |
| T004 | Verify `capabilities.py` — `DEFAULT_ROLE_CAPABILITIES` and `get_capabilities` work unchanged | WP01 | | [D] |
| T005 | Add `model_validator(mode="before")` `_coerce_scalar_role` to `AgentProfile` | WP01 | | [D] |
| T006 | Replace `role` field with `roles: list[Role]` + add `@property role` | WP01 | | [D] |
| T007 | Add `avatar_image: str | None = Field(default=None, alias="avatar-image")` to `AgentProfile` | WP01 | | [D] |
| T008 | Update `TaskContext.required_role` annotation to use new `Role` type | WP01 | | [D] |
| T009 | Write `tests/doctrine/test_role_value_object.py` | WP01 | | [D] |
| T010 | Write `AgentProfile` model tests (coercion, multi-role, avatar, neither-key rejection) | WP01 | | [D] |
| T011 | Add `roles` property to JSON schema (array of strings, minItems: 1) | WP02 | [D] |
| T012 | Add `avatar-image` optional string property to JSON schema | WP02 | [D] |
| T013 | Add constraint to reject profiles with neither `role` nor `roles` | WP02 | [D] |
| T014 | Update `schema_models.py` — add `roles: list[str] | None` and `avatar_image` fields | WP02 | [D] |
| T015 | Write schema validation tests for all new rules | WP02 | [D] |
| T016 | Rewrite `_filter_candidates_by_role` to use `profile.roles` list | WP03 | [P] |
| T017 | Rewrite `_exact_id_signal` with primary (1.0) / secondary (0.5) scoring | WP03 | [P] |
| T018 | Rewrite `find_by_role` to check `role in profile.roles` | WP03 | [P] |
| T019 | Remove dead `isinstance(p.role, ...)` branches from `repository.py` | WP03 | [P] |
| T020 | Write new routing tests + audit existing tests for old `.role.value` / StrEnum patterns | WP03 | [P] |
| T021 | `git mv` 7 renamed YAML files (atomic with T022+T023) | WP04 | |
| T022 | Update `profile-id` + `role:` → `roles: [...]` in 7 renamed files; update names for planner/researcher | WP04 | |
| T023 | [ATOMIC with T021] Update `specializes-from: implementer-ivan` in java-jenny + python-pedro | WP04 | |
| T024 | Migrate `role:` → `roles:` in generic-agent and human-in-charge | WP04 | |
| T025 | Migrate `role:` → `roles:` in java-jenny and python-pedro | WP04 | |
| T026 | Update `graph.yaml` — 7 URN renames + label corrections | WP04 | |
| T027 | Update `shipped/README.md` table | WP04 | |
| T028 | Update `test_shipped_profiles.py` — EXPECTED_PROFILE_IDS + parametrize entries | WP04 | |
| T029 | Fix `tests/doctrine/test_service.py` — fixture profiles, Role usage | WP05 | [D] |
| T030 | Fix `tests/charter/test_catalog.py` — fixture profiles | WP05 | [D] |
| T031 | Fix `tests/specify_cli/status/test_wp_metadata.py` — agent_profile strings | WP05 | [D] |
| T032 | Run full test suite; fix any remaining failures | WP05 | | [D] |
| T033 | Run `mypy --strict src/doctrine/agent_profiles/ tests/doctrine/`; fix any type annotation issues | WP05 | | [D] |
| T036 | Performance gate: load all shipped profiles, assert ≤5% regression vs pre-migration timing | WP05 | [D] |
| T034 | Fix `implement.md` — correct stale field names + add `for_review` profile-handoff guidance | WP06 | [D] |
| T035 | Update `review.md` — add profile-load step + add reject profile-handoff guidance | WP06 | [D] |
| T036 | Write migration module to insert profile-load + handoff blocks into .kittify templates | WP07 | | [D] |
| T037 | Register migration in upgrade registry | WP07 | | [D] |
| T038 | Write migration tests (idempotency, insertion, stale-field-fix, missing-dir guard) | WP07 | | [D] |

---

## Work Packages

### WP01 — Role Value Object + AgentProfile Model

**Priority**: Critical — foundation for all other WPs
**Estimated prompt size**: ~520 lines
**Dependencies**: none
**Parallelizes with**: WP02

**Goal**: Replace `Role(StrEnum)` with a half-open `str`-subclass value object and
update `AgentProfile` to use `roles: list[Role]`, a computed `role` property, and an
optional `avatar_image` field.

**Included subtasks**:
- [x] T001 Write `Role(str)` class — `__new__`, `_KNOWN` frozenset, `is_known`, class constants (WP01)
- [x] T002 Write `Role` class docstring (WP01)
- [x] T003 Delete `Role(StrEnum)` and `_coerce_role` (WP01)
- [x] T004 Verify `capabilities.py` unchanged (WP01)
- [x] T005 Add `model_validator` `_coerce_scalar_role` to `AgentProfile` (WP01)
- [x] T006 Replace `role` field with `roles: list[Role]` + `@property role` (WP01)
- [x] T007 Add `avatar_image` field (WP01)
- [x] T008 Update `TaskContext.required_role` (WP01)
- [x] T009 Write `test_role_value_object.py` (WP01)
- [x] T010 Write `AgentProfile` model tests (WP01)

**Prompt file**: `tasks/WP01-role-value-object-and-agent-profile-model.md`

---

### WP02 — YAML Schema + Schema Models

**Priority**: High — gates WP04
**Estimated prompt size**: ~250 lines
**Dependencies**: WP01
**Parallelizes with**: WP03

**Goal**: Update `agent-profile.schema.yaml` to accept `roles` (list) and `avatar-image`,
keep `role` (scalar, deprecated), and reject profiles with neither. Mirror in `schema_models.py`.

**Included subtasks**:
- [x] T011 Add `roles` to JSON schema (WP02)
- [x] T012 Add `avatar-image` to JSON schema (WP02)
- [x] T013 Add neither-key rejection constraint (WP02)
- [x] T014 Update `schema_models.py` (WP02)
- [x] T015 Write schema validation tests (WP02)

**Prompt file**: `tasks/WP02-yaml-schema-and-schema-models.md`

---

### WP03 — Repository and Routing Update

**Priority**: High — gates WP05
**Estimated prompt size**: ~260 lines
**Dependencies**: WP01
**Parallelizes with**: WP02, WP04 (different file sets)

**Goal**: Update `repository.py` so all role-based filtering, scoring, and lookup
uses `profile.roles` (list). Primary role (index 0) scores 1.0; secondary roles score 0.5.

**Included subtasks**:
- [ ] T016 Rewrite `_filter_candidates_by_role` (WP03)
- [ ] T017 Rewrite `_exact_id_signal` with primary/secondary scoring (WP03)
- [ ] T018 Rewrite `find_by_role` (WP03)
- [ ] T019 Remove dead `isinstance` branches (WP03)
- [ ] T020 Write new routing tests (WP03)

**Prompt file**: `tasks/WP03-repository-and-routing-update.md`

---

### WP04 — Shipped Profile Migration and Renames

**Priority**: High — gates WP05
**Estimated prompt size**: ~440 lines
**Dependencies**: WP01, WP02
**Parallelizes with**: WP03

**Goal**: Migrate all 11 shipped profiles to `roles: [...]` syntax, rename 7 profiles
to character-name IDs, update `graph.yaml` URNs, `README.md`, and `test_shipped_profiles.py`.
CRITICAL: `implementer` → `implementer-ivan` rename and `specializes-from` updates must be atomic.

**Included subtasks**:
- [ ] T021 `git mv` 7 renamed YAML files (WP04)
- [ ] T022 Update profile-id + roles in renamed files; fix planner/researcher names (WP04)
- [ ] T023 [ATOMIC] Update specializes-from in java-jenny + python-pedro (WP04)
- [ ] T024 Migrate role → roles in generic-agent + human-in-charge (WP04)
- [ ] T025 Migrate role → roles in java-jenny + python-pedro (WP04)
- [ ] T026 Update graph.yaml — 7 URN renames + label fixes (WP04)
- [ ] T027 Update shipped/README.md (WP04)
- [ ] T028 Update test_shipped_profiles.py (WP04)

**Prompt file**: `tasks/WP04-shipped-profile-migration-and-renames.md`

---

### WP05 — Test Suite Alignment

**Priority**: Normal — final integration gate
**Estimated prompt size**: ~230 lines
**Dependencies**: WP01, WP02, WP03, WP04
**Parallelizes with**: nothing (integration gate)

**Goal**: Fix all test files outside `test_shipped_profiles.py` that reference old profile IDs,
old Role enum, or old scalar role field. Verify full suite passes with zero failures.

**Included subtasks**:
- [x] T029 Fix `tests/doctrine/test_service.py` (WP05)
- [x] T030 Fix `tests/charter/test_catalog.py` (WP05)
- [x] T031 Fix `tests/specify_cli/status/test_wp_metadata.py` (WP05)
- [x] T032 Run full test suite; fix remaining failures (WP05)
- [x] T033 Run `mypy --strict`; fix type annotation issues (WP05)
- [x] T036 Performance gate: profile load time ≤5% regression (WP05)

**Prompt file**: `tasks/WP05-test-suite-alignment.md`

---

### WP06 — Review Workflow Agent Profile Handoff

**Priority**: Normal — quality-of-life for implement/review cycle
**Estimated prompt size**: ~200 lines
**Dependencies**: none
**Parallelizes with**: WP01–WP05 (touches only command templates)

**Goal**: Update `implement.md` and `review.md` to (a) fix stale field names (`profile`→`agent_profile`,
`tool`→`agent`) and (b) add explicit guidance for updating `agent_profile` in WP frontmatter
when handing off between implementer and reviewer roles — forward when moving to `for_review`,
and backward when rejecting.

**Included subtasks**:
- [x] T034 Fix `implement.md` — correct stale field names + add `for_review` profile-handoff guidance (WP06)
- [x] T035 Update `review.md` — add profile-load step + add reject profile-handoff guidance (WP06)

**Prompt file**: `tasks/WP06-review-workflow-agent-profile-handoff.md`

---

### WP07 — .kittify Template Migration for Profile Handoff

**Priority**: Medium — propagates WP06 source changes to installed client projects
**Estimated prompt size**: ~200 lines
**Dependencies**: WP06
**Parallelizes with**: nothing (depends on WP06)

**Goal**: Implement a spec-kitty upgrade migration that inserts the profile-load block
and review handoff guidance into existing `.kittify/missions/software-dev/command-templates/`
files, so projects that have already run `spec-kitty upgrade` receive the WP06 changes on
their next upgrade run.

**Included subtasks**:
- [x] T036 Write migration module to insert profile-load + handoff blocks into .kittify templates (WP07)
- [x] T037 Register migration in upgrade registry (WP07)
- [x] T038 Write migration tests (idempotency, insertion, stale-field-fix, missing-dir guard) (WP07)

**Prompt file**: `tasks/WP07-kittify-template-migration.md`
