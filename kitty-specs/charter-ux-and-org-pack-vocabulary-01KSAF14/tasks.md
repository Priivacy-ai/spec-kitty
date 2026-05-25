# Tasks — Charter UX & Org-Pack Vocabulary

**Mission**: `charter-ux-and-org-pack-vocabulary-01KSAF14`
**Mission ID**: `01KSAF14K8FZ56MHYT45EGWHHC`
**Planning base branch**: `main`
**Merge target branch**: `main`
**Total WPs**: 10
**Total subtasks**: 57

## Wave map → Work-package map

| Wave | WP IDs | Theme |
|---|---|---|
| 1 — Charter freshness instrumentation | WP01, WP02 | Lint built-in fallback + status freshness + synthesize post-condition |
| 2 — Preflight | WP03, WP04 | New `charter preflight` command + caller hooks |
| 3 — Pack-authoring vocabulary | WP05, WP06 | `overrides`/`enhances` fields + DRG / validator updates |
| 4 — Vocabulary cutover | WP07, WP08, WP09 | `shipped → built-in` rename in code, tests, docs |
| Polish | WP10 | End-to-end smoke + field-merge edge case fixture |

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | ADR-1 `2026-05-DD-1-charter-freshness-ux-contract.md` | WP01 | |
| T002 | DIR-013 baseline pytest run; open GH issue if failures pre-exist | WP01 | |
| T003 | DIR-012 assign #1099 to HiC | WP01 | |
| T004 | Add `GraphState` StrEnum + extend `DecayReport.graph_state` | WP01 | |
| T005 | Built-in fallback path in `_drg.load_merged_drg` | WP01 | |
| T006 | Wire `LintEngine.run()` to set graph_state; update banner + JSON output | WP01 | |
| T007 | Tests for FR-001..FR-004 (missing / built_in_only / merged) | WP01 | |
| T008 | DIR-012 assign #1101, #1104 to HiC | WP02 | |
| T009 | Compute hash/timestamp freshness for charter_source / synced_bundle / synthesized_drg | WP02 | |
| T010 | Wire `freshness` sub-payload into `charter status --json` | WP02 | |
| T011 | Add `built_in_only` field to synthesis-manifest schema | WP02 | |
| T012 | Synthesizer post-condition: write graph.yaml OR `built_in_only` marker atomically | WP02 | |
| T013 | Conflict-resolution per data-model §6 (manifest authoritative; stale graph.yaml as `invalid`) | WP02 | |
| T014 | Tests for FR-005, FR-009 (including conflict case) | WP02 | |
| T015 | DIR-012 assign #1100 to HiC | WP03 | |
| T016 | Create `result.py` with `CharterPreflightCheck`, `CharterPreflightResult` dataclasses | WP03 | |
| T017 | Create `runner.py` — `run_charter_preflight(...)` consumes WP02 freshness payload | WP03 | |
| T018 | Uncommitted-artifact detection via `git status --porcelain` per FR-008 contract | WP03 | |
| T019 | Auto-refresh sequence: `charter sync` → `charter synthesize` → `bundle validate` | WP03 | |
| T020 | `cli.py` for `spec-kitty charter preflight` (`--auto-refresh`, `--strict`, `--json`) | WP03 | |
| T021 | Tests for FR-006, FR-007, FR-008 + NFR-001 perf budget | WP03 | |
| T022 | Add `preflight.auto_refresh` config flag (default `false`) to `.kittify/config.yaml` schema | WP04 | |
| T023 | Wire preflight hook into `spec-kitty next` (log+continue / abort) | WP04 | |
| T024 | Wire preflight hook into `spec-kitty implement` (abort before worktree allocation) | WP04 | |
| T025 | Wire preflight hook into dashboard launch (critical banner on failure) | WP04 | |
| T026 | Tests for each consumer's pass/fail behaviour | WP04 | |
| T027 | ADR-2 `2026-05-DD-2-pack-augmentation-vocabulary.md` | WP05 | |
| T028 | DIR-012 assign #1291 to HiC | WP05 | |
| T029 | Glossary entries for `enhances`/`overrides` (DIR-032) | WP05 | |
| T030 | `Tactic`: add `overrides`/`enhances` fields + cross-field validator + schema YAML | WP05 | [P] |
| T031 | `Styleguide`: same pattern | WP05 | [P] |
| T032 | `Paradigm`: same pattern | WP05 | [P] |
| T033 | `Procedure`: same pattern | WP05 | [P] |
| T034 | `AgentProfile`: same pattern | WP05 | [P] |
| T035 | Extend `Relation` enum with `ENHANCES`, `OVERRIDES` (retain `REPLACES`) | WP06 | |
| T036 | `org_pack_loader`: auto-emit `enhances`/`overrides` DRG edges from declared fields | WP06 | |
| T037 | `pack_validator`: branch advisory per `pack-validator-advisory.md` precedence rules | WP06 | |
| T038 | Add `unknown_target` + `intent_conflict` validator categories | WP06 | |
| T039 | Tests for FR-012, FR-013, FR-014 | WP06 | |
| T040 | ADR-3 `2026-05-DD-3-shipped-to-built-in-cutover.md` | WP07 | |
| T041 | Rename Python identifiers in `src/doctrine/base.py` per occurrence_map | WP07 | |
| T042 | Rename Python identifiers in `src/specify_cli/charter_lint/` + `cli/commands/charter.py` | WP07 | |
| T043 | Rename Python identifiers across remaining `src/` files per occurrence_map | WP07 | |
| T044 | Update log/advisory user-facing strings (coordinate with WP06 rewording) | WP07 | |
| T045 | Update `profiles_cmd.py` JSON value + delete `_warn_project_override` conversion | WP07 | |
| T046 | Migrate `tests/specify_cli/` test assertions per occurrence_map | WP08 | |
| T047 | Migrate `tests/integration/` and `tests/architectural/` test assertions | WP08 | |
| T048 | Migrate `tests/test_dashboard/` and remaining test directories | WP08 | |
| T049 | Run full pytest suite to zero failures (NFR-003) | WP08 | |
| T050 | New architectural regression test `tests/architectural/test_no_shipped_layer_label.py` (FR-016) | WP08 | |
| T051 | Update `docs/` markdown, schema descriptions, README excerpts per occurrence_map (FR-015 f) | WP09 | |
| T052 | CHANGELOG entry for breaking JSON change (FR-017) | WP09 | |
| T053 | Final acceptance grep — confirm zero `shipped` JSON-label occurrences | WP09 | |
| T054 | Cross-reference 3 new ADRs back to `2026-05-16-1-doctrine-layer-merge-semantics.md` | WP09 | |
| T055 | Run quickstart.md Steps 1-5 end-to-end on a fresh-clone fixture | WP10 | |
| T056 | Close-comment on issues #1099, #1100, #1101, #1104, #1291 with PR link (DIR-012 follow-through) | WP10 | |
| T057 | New fixture `tests/integration/test_pack_enhances_partial_fields.py` for field-merge edge case | WP10 | |

---

## WP01 — Wave 1 foundation: ADR + lint built-in fallback (FR-001..FR-004)

**Priority**: P0 (blocks Wave 1 follow-on WPs)
**Independent test**: `pytest tests/specify_cli/charter_lint/test_engine.py -v` passes with new `graph_state` assertions; `spec-kitty charter lint --json` on a fixture with no project DRG emits `graph_state: "built_in_only"`.
**Estimated prompt size**: ~260 lines
**Linked issue**: #1099
**Prompt file**: `tasks/WP01-wave1-foundation-and-lint-built-in-fallback.md`

Subtasks:
- [x] T001 ADR-1 (`2026-05-DD-1-charter-freshness-ux-contract.md`) — DIR-003 (WP01)
- [x] T002 DIR-013 baseline pytest run (WP01)
- [x] T003 DIR-012 assign #1099 to HiC (WP01)
- [x] T004 GraphState StrEnum + DecayReport.graph_state (WP01)
- [x] T005 Built-in fallback in `_drg.load_merged_drg` (WP01)
- [x] T006 Wire LintEngine + CLI banner + JSON (WP01)
- [x] T007 Tests for FR-001..FR-004 (WP01)

Dependencies: none.

---

## WP02 — Wave 1: status freshness + synthesize post-condition (FR-005, FR-009)

**Priority**: P0
**Independent test**: `spec-kitty charter status --json` exposes `freshness` sub-object with three sub-states; synthesize on fresh checkout either produces `graph.yaml` or writes `built_in_only: true` atomically.
**Estimated prompt size**: ~250 lines
**Linked issues**: #1101, #1104
**Prompt file**: `tasks/WP02-wave1-status-freshness-and-synthesize-post-condition.md`

Subtasks:
- [x] T008 DIR-012 assign #1101, #1104 to HiC (WP02)
- [x] T009 Hash/timestamp freshness computation (WP02)
- [x] T010 Wire freshness sub-payload into status --json (WP02)
- [x] T011 synthesis-manifest schema: built_in_only field (WP02)
- [x] T012 Synthesizer post-condition atomic write (WP02)
- [x] T013 Conflict resolution per data-model §6 (WP02)
- [x] T014 Tests for FR-005, FR-009 (WP02)

Dependencies: WP01.

---

## WP03 — Wave 2: charter_preflight package + CLI (FR-006, FR-007, FR-008)

**Priority**: P0
**Independent test**: `spec-kitty charter preflight --json` returns deterministic JSON; `--auto-refresh` honours the safety rule against uncommitted artifacts; warm run completes in <300 ms.
**Estimated prompt size**: ~290 lines
**Linked issue**: #1100
**Prompt file**: `tasks/WP03-wave2-charter-preflight-package-and-cli.md`

Subtasks:
- [x] T015 DIR-012 assign #1100 to HiC (WP03)
- [x] T016 result.py: CharterPreflightCheck/Result dataclasses (WP03)
- [x] T017 runner.py: run_charter_preflight consumes WP02 freshness (WP03)
- [x] T018 Uncommitted-artifact detection via git status --porcelain (WP03)
- [x] T019 Auto-refresh sequence wiring (WP03)
- [x] T020 cli.py for spec-kitty charter preflight (WP03)
- [x] T021 Tests for FR-006/FR-007/FR-008 + NFR-001 perf (WP03)

Dependencies: WP02.

---

## WP04 — Wave 2: preflight hook integration

**Priority**: P0
**Independent test**: `spec-kitty next` and `spec-kitty implement` abort cleanly on preflight failure without mutating worktrees; dashboard renders critical banner on failure.
**Estimated prompt size**: ~200 lines
**Prompt file**: `tasks/WP04-wave2-preflight-hook-integration.md`

Subtasks:
- [x] T022 preflight.auto_refresh config flag (WP04)
- [x] T023 Hook into spec-kitty next (WP04)
- [x] T024 Hook into spec-kitty implement (WP04)
- [x] T025 Hook into dashboard launch (WP04)
- [x] T026 Tests for each consumer behaviour (WP04)

Dependencies: WP03.

---

## WP05 — Wave 3: schema field additions (FR-010, FR-011)

**Priority**: P0
**Independent test**: All 5 affected Pydantic models accept `overrides:` and `enhances:` optional fields; cross-field validator rejects both-set case; pack tactic loading regression suite passes.
**Estimated prompt size**: ~320 lines
**Linked issue**: #1291
**Prompt file**: `tasks/WP05-wave3-schema-field-additions.md`

Subtasks:
- [x] T027 ADR-2 (`2026-05-DD-2-pack-augmentation-vocabulary.md`) (WP05)
- [x] T028 DIR-012 assign #1291 to HiC (WP05)
- [x] T029 Glossary entries for enhances/overrides (DIR-032) (WP05)
- [x] T030 [P] Tactic model + schema YAML (WP05)
- [x] T031 [P] Styleguide model + schema YAML (WP05)
- [x] T032 [P] Paradigm model + schema YAML (WP05)
- [x] T033 [P] Procedure model + schema YAML (WP05)
- [x] T034 [P] AgentProfile model + schema YAML (WP05)

Dependencies: none (runs parallel with Waves 1-2).

---

## WP06 — Wave 3: Relation enum + DRG auto-emit + validator (FR-012, FR-013, FR-014)

**Priority**: P0
**Independent test**: Pack tactic declaring `enhances:` against a known built-in passes validation without advisory and auto-emits `ENHANCES` DRG edge; declaring against unknown ID errors with `unknown_target`.
**Estimated prompt size**: ~250 lines
**Linked issue**: #1291
**Prompt file**: `tasks/WP06-wave3-relation-enum-drg-and-validator-advisory.md`

Subtasks:
- [x] T035 Relation enum: add ENHANCES, OVERRIDES (WP06)
- [x] T036 org_pack_loader: auto-emit edges (WP06)
- [x] T037 pack_validator advisory branching (WP06)
- [x] T038 unknown_target + intent_conflict validator categories (WP06)
- [x] T039 Tests for FR-012, FR-013, FR-014 (WP06)

Dependencies: WP05.

---

## WP07 — Wave 4: bulk-edit cutover (code) (FR-015 a-d)

**Priority**: P1
**Independent test**: `grep -rn '"shipped"\|'\''shipped'\''' src/ | grep -v __pycache__` returns 0 matches; `ruff check` and `mypy --strict` pass.
**Estimated prompt size**: ~270 lines
**Prompt file**: `tasks/WP07-wave4-bulk-edit-cutover-code.md`

Subtasks:
- [x] T040 ADR-3 (`2026-05-DD-3-shipped-to-built-in-cutover.md`) (WP07)
- [x] T041 Rename in src/doctrine/base.py (WP07)
- [x] T042 Rename in src/specify_cli/charter_lint/ + cli/commands/charter.py (WP07)
- [x] T043 Rename across remaining src/ Python files (WP07)
- [x] T044 Update user-facing log/advisory strings (WP07)
- [x] T045 profiles_cmd.py + delete _warn_project_override conversion (WP07)

Dependencies: WP04, WP06.

---

## WP08 — Wave 4: bulk-edit cutover (tests + architectural regression) (FR-015 e, FR-016)

**Priority**: P1
**Independent test**: Full pytest suite passes with zero regressions (NFR-003); new architectural test `test_no_shipped_layer_label.py` scans 5 public JSON surfaces and finds no `"shipped"`.
**Estimated prompt size**: ~220 lines
**Prompt file**: `tasks/WP08-wave4-bulk-edit-cutover-tests.md`

Subtasks:
- [x] T046 Migrate tests/specify_cli/ assertions (WP08)
- [x] T047 Migrate tests/integration/ + tests/architectural/ assertions (WP08)
- [x] T048 Migrate tests/test_dashboard/ + remaining (WP08)
- [x] T049 Full pytest zero-failures check (WP08)
- [x] T050 New architectural regression test FR-016 (WP08)

Dependencies: WP07.

---

## WP09 — Wave 4: docs + CHANGELOG + cross-references (FR-015 f, FR-017)

**Priority**: P1
**Independent test**: `docs/` text + schema descriptions contain no `shipped` as layer label; CHANGELOG entry exists for the JSON breaking change; new ADRs reference `2026-05-16-1`.
**Estimated prompt size**: ~190 lines
**Prompt file**: `tasks/WP09-wave4-docs-and-changelog.md`

Subtasks:
- [x] T051 docs/ + schema descriptions + README excerpts (WP09)
- [x] T052 CHANGELOG entry (WP09)
- [x] T053 Final acceptance grep (WP09)
- [x] T054 Cross-reference 3 new ADRs back to 2026-05-16-1 (WP09)

Dependencies: WP07.

---

## WP10 — Polish: end-to-end smoke + field-merge edge case fixture

**Priority**: P2
**Independent test**: Quickstart Steps 1-5 produce expected output on a fresh-clone fixture; `test_pack_enhances_partial_fields.py` passes.
**Estimated prompt size**: ~170 lines
**Prompt file**: `tasks/WP10-polish-smoke-and-field-merge-fixture.md`

Subtasks:
- [x] T055 End-to-end quickstart smoke (WP10)
- [x] T056 Close-comment on linked issues with PR link (WP10)
- [x] T057 New field-merge edge case fixture (WP10)

Dependencies: WP08, WP09.

---

## Parallelisation highlights

- **Independent waves**: WP05 (Wave 3 schema) can run in parallel with WP01..WP04. The doctrine package surface does not overlap with the charter CLI surface.
- **In-WP parallel subtasks**: WP05 T030-T034 are five symmetric model+schema changes safely runnable in parallel because each touches an isolated file pair.
- **WP07/WP08/WP09 are sequenced** because they share the bulk-edit gate and pytest baseline.

## MVP scope recommendation

WP01 → WP02 → WP03 → WP04 (Waves 1-2 only) constitutes the MVP that closes the four Slice A launch-blocker issues (#1099, #1100, #1101, #1104). Waves 3-4 close #1291 and the vocabulary cleanup; they can ship in a follow-up release if the MVP needs to ship first.
