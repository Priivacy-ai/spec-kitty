# Tasks — CLI Interview Decision Moments

**Mission:** `cli-interview-decision-moments-01KPWT8P` (mid8: `01KPWT8P`)
**Planning/base branch:** `main`
**Final merge target:** `main`
**Date:** 2026-04-23

Every subtask appears in exactly one work package. No two WPs touch the same files.

## Subtask Index

| ID   | Description                                                                                       | WP   | Parallel |
|------|---------------------------------------------------------------------------------------------------|------|----------|
| T001 | Bump `spec-kitty-events` dep from 3.3.0 → 4.0.0 in `pyproject.toml`                                | WP01 |          | [D] |
| T002 | Refresh vendored `src/specify_cli/spec_kitty_events/` from 4.0.0 source tree                       | WP01 |          | [D] |
| T003 | Audit existing DecisionPoint emitters (if any); add `origin_surface="adr"` where required          | WP01 |          | [D] |
| T004 | Create `src/specify_cli/decisions/models.py` — enums + IndexEntry + DecisionIndex                  | WP02 |          | [D] |
| T005 | Create `src/specify_cli/decisions/store.py` — atomic I/O for `index.json` + `DM-<id>.md`           | WP02 |          | [D] |
| T006 | Create `src/specify_cli/decisions/emit.py` — wraps status emitter with DecisionPoint events         | WP03 |          | [D] |
| T007 | Create `src/specify_cli/decisions/service.py` — open/resolve/defer/cancel with idempotency logic    | WP03 |          | [D] |
| T008 | Create `src/specify_cli/decisions/verify.py` — marker ↔ decision cross-check                        | WP04 |          | [D] |
| T009 | Create `src/specify_cli/cli/commands/decision.py` — typer subgroup (5 subcommands, JSON, errors)    | WP05 |          | [D] |
| T010 | Register `decision` subgroup in `src/specify_cli/cli/main.py`                                       | WP05 |          | [D] |
| T011 | Wire decision calls into `src/specify_cli/cli/commands/charter.py` interview loop                   | WP06 |          | [D] |
| T012 | Update `src/specify_cli/missions/software-dev/command-templates/specify.md`                         | WP07 | [D] |
| T013 | Update `src/specify_cli/missions/software-dev/command-templates/plan.md`                            | WP07 | [D] |
| T014 | Unit tests `tests/specify_cli/decisions/test_models.py`                                             | WP02 |          | [D] |
| T015 | Unit tests `tests/specify_cli/decisions/test_store.py` (atomic writes, determinism, key lookup)     | WP02 |          | [D] |
| T016 | Unit tests `tests/specify_cli/decisions/test_emit.py` — event payload shape matches 4.0.0           | WP03 |          | [D] |
| T017 | Unit tests `tests/specify_cli/decisions/test_service_idempotency.py` — open retries                 | WP03 |          | [D] |
| T018 | Unit tests `tests/specify_cli/decisions/test_service_terminal.py` — resolve/defer/cancel + conflict | WP03 |          | [D] |
| T019 | Unit tests `tests/specify_cli/decisions/test_verify.py` — three finding kinds                       | WP04 |          | [D] |
| T020 | CLI integration tests `tests/specify_cli/cli/commands/test_decision.py`                             | WP05 |          | [D] |
| T021 | Extend `tests/specify_cli/cli/commands/test_charter.py` — charter emits decision events             | WP06 |          | [D] |
| T022 | End-to-end charter emission integration test — answers.yaml + paper trail + events coherent         | WP06 |          | [D] |
| T023 | Update `CHANGELOG.md` with V1 Decision Moments entry + note events dep bump                         | WP07 | [D] |
| T024 | Verify integration test — end-to-end drift detection across spec.md / plan.md                       | WP04 |          | [D] |

## Work Packages

### WP01 — Dep bump + vendored events refresh

**Goal.** Move the repo onto `spec-kitty-events 4.0.0`: update `pyproject.toml`, refresh the vendored `src/specify_cli/spec_kitty_events/` tree, and audit existing DecisionPoint emitters.

**Priority.** P0 (everything else depends on 4.0.0 payload types).

**Independent test.** `pip install -e ".[dev]"` succeeds; `python -c "import spec_kitty_events; print(spec_kitty_events.__version__)"` → `4.0.0`; `pytest tests/` stays green on this WP alone.

**Included subtasks.**

- [x] T001 Bump pyproject.toml version pin to `spec-kitty-events==4.0.0` (WP01)
- [x] T002 Refresh vendored `src/specify_cli/spec_kitty_events/` from 4.0.0 source (WP01)
- [x] T003 Audit existing DecisionPoint emitters and add `origin_surface="adr"` where required (WP01)

**Dependencies.** None.

**Estimated prompt size.** ~180 lines.

---

### WP02 — Decisions core (models + store)

**Goal.** Ship the foundation runtime modules: `models.py` (Pydantic models + enums) and `store.py` (atomic I/O for `index.json` + `DM-<decision_id>.md` artifacts). Lock shapes and I/O correctness.

**Priority.** P0.

**Independent test.** `pytest tests/specify_cli/decisions/test_models.py tests/specify_cli/decisions/test_store.py -q` green; `mypy --strict src/specify_cli/decisions/models.py src/specify_cli/decisions/store.py` clean; `ruff check` clean.

**Included subtasks.**

- [x] T004 models.py — enums + IndexEntry + DecisionIndex (WP02)
- [x] T005 store.py — atomic index.json + DM-<id>.md I/O (WP02)
- [x] T014 test_models.py (WP02)
- [x] T015 test_store.py (WP02)

**Dependencies.** WP01.

**Estimated prompt size.** ~400 lines.

---

### WP03 — Decisions service (emit + orchestration)

**Goal.** Ship `emit.py` (DecisionPoint event emission) + `service.py` (open/resolve/defer/cancel orchestration with idempotency). This is the core contract-producer.

**Priority.** P0.

**Independent test.** `pytest tests/specify_cli/decisions/test_emit.py tests/specify_cli/decisions/test_service_idempotency.py tests/specify_cli/decisions/test_service_terminal.py -q` green.

**Included subtasks.**

- [x] T006 emit.py — wraps status emitter for DecisionPoint events (WP03)
- [x] T007 service.py — open/resolve/defer/cancel orchestration (WP03)
- [x] T016 test_emit.py (WP03)
- [x] T017 test_service_idempotency.py (WP03)
- [x] T018 test_service_terminal.py (WP03)

**Dependencies.** WP02.

**Estimated prompt size.** ~500 lines.

---

### WP04 — Decision verifier

**Goal.** Ship `verify.py` — scans `spec.md` and `plan.md` for marker-anchor comments and cross-checks against the deferred decisions in the index. Returns structured findings; exits non-zero on drift.

**Priority.** P1.

**Independent test.** `pytest tests/specify_cli/decisions/test_verify.py -q` green with all three finding kinds (`DEFERRED_WITHOUT_MARKER`, `MARKER_WITHOUT_DECISION`, `STALE_MARKER`) exercised.

**Included subtasks.**

- [x] T008 verify.py — marker↔decision cross-check (WP04)
- [x] T019 test_verify.py (WP04)
- [x] T024 verify integration test — end-to-end drift across spec.md and plan.md (WP04)

**Dependencies.** WP02 (uses store).

**Estimated prompt size.** ~300 lines.

---

### WP05 — CLI command subgroup (typer)

**Goal.** Ship `src/specify_cli/cli/commands/decision.py` — the typer subgroup that exposes `spec-kitty agent decision {open, resolve, defer, cancel, verify}`. Register it in `cli/main.py`. Cover CLI-level behavior with integration tests.

**Priority.** P1.

**Independent test.** `pytest tests/specify_cli/cli/commands/test_decision.py -q` green; CLI help text is accurate; `--dry-run` produces no side effects.

**Included subtasks.**

- [x] T009 decision.py — typer subgroup (WP05)
- [x] T010 Register subgroup in cli/main.py (WP05)
- [x] T020 CLI integration tests (WP05)

**Dependencies.** WP03 and WP04.

**Estimated prompt size.** ~350 lines.

---

### WP06 — Charter integration

**Goal.** Wire `decision open`/`resolve`/`defer`/`cancel` into the existing `spec-kitty charter interview` loop. Preserve `answers.yaml` semantics exactly. Prove charter now emits Decision Moment events and paper trail alongside answers.yaml.

**Priority.** P1.

**Independent test.** `pytest tests/specify_cli/cli/commands/test_charter.py -q` green; end-to-end test demonstrates coherent triple (events + paper trail + answers.yaml).

**Included subtasks.**

- [x] T011 charter.py changes (WP06)
- [x] T021 test_charter.py extensions (WP06)
- [x] T022 End-to-end charter integration test (WP06)

**Dependencies.** WP05.

**Estimated prompt size.** ~300 lines.

---

### WP07 — Template updates + CHANGELOG

**Goal.** Update the SOURCE command templates `specify.md` and `plan.md` to instruct the LLM to call `decision open/resolve/defer/cancel/verify` at ask time and resolution time. Add a CHANGELOG entry documenting the V1 Decision Moments feature and events dep bump.

**Priority.** P1 (templates are required for specify/plan flows to actually emit decisions in LLM-driven interviews).

**Independent test.** Manual: LLM prompted with updated templates calls the decision subcommands correctly in a walkthrough. Documentary: `CHANGELOG.md` has a coherent entry.

**Included subtasks.**

- [x] T012 specify.md template update (WP07)
- [x] T013 plan.md template update (WP07)
- [x] T023 CHANGELOG entry (WP07)

**Dependencies.** WP05.

**Estimated prompt size.** ~280 lines.

## MVP Scope

WP01 + WP02 + WP03 + WP05 yields a working CLI subgroup without charter integration, verifier, or template updates. Adding WP06 + WP04 + WP07 completes V1.

## Dependencies graph

```
WP01 ──► WP02 ──► WP03 ──┐
              └─► WP04   ├──► WP05 ──┬──► WP06
                         │           └──► WP07
                         │
                         (WP04 also feeds WP05)
```

## Parallelization notes

- After WP02 lands: WP03 and WP04 can run in parallel (different owned files).
- After WP05 lands: WP06 and WP07 can run in parallel.
- WP01 is strict foundation (sequential).

## Size validation

| WP   | Subtasks | Est. prompt lines | Status |
|------|----------|-------------------|--------|
| WP01 | 3        | ~180              | ✓      |
| WP02 | 4        | ~400              | ✓      |
| WP03 | 5        | ~500              | ✓      |
| WP04 | 3        | ~300              | ✓      |
| WP05 | 3        | ~350              | ✓      |
| WP06 | 3        | ~300              | ✓      |
| WP07 | 3        | ~280              | ✓      |

All WPs within the ideal 3-7 subtasks / 200-500 lines range.
