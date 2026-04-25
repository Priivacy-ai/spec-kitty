# Tasks — CLI Widen Mode & Decision Write-Back

**Mission:** `cli-widen-mode-and-write-back-01KPXFGJ`
**Issue:** `spec-kitty#758`
**Target branch:** `main`
**Generated:** 2026-04-23T15:43:52Z

---

## Summary

This mission adds Widen Mode to the CLI interview flows (charter, specify, plan). The owner can press `[w]` during a live interview to escalate a question to Teamspace collaboration via Slack, then review a locally-summarized discussion and write back the approved answer.

**Total subtasks:** 53
**Work packages:** 10
**Estimated prompt sizes:** 280–480 lines

---

## Subtask Index

| ID   | Description                                                | WP   | Parallel |
|------|------------------------------------------------------------|------|----------|
| T001 | Create `saas_client/` package skeleton + `__init__.py`     | WP01 |          | [D] |
| T002 | Implement `SaasClient` class with httpx + DI factory       | WP01 |          | [D] |
| T003 | Implement auth context: env var + saas-auth.json fallback  | WP01 |          | [D] |
| T004 | Implement endpoint helpers (audience_default, widen, discussion_fetch, integrations, health) | WP01 | | [D] |
| T005 | Implement `SaasClientError` hierarchy + timeout/auth errors | WP01 | | [D] |
| T006 | Create `widen/` package skeleton + `__init__.py`           | WP02 |          | [D] |
| T007 | Define `SummarySource` enum + `PrereqState` dataclass      | WP02 |          | [D] |
| T008 | Define `WidenAction` enum + `WidenFlowResult` dataclass    | WP02 |          | [D] |
| T009 | Define `WidenPendingEntry` Pydantic model                  | WP02 |          | [D] |
| T010 | Define `DiscussionFetch` + `CandidateReview` Pydantic models | WP02 | | [D] |
| T011 | Implement `WidenPendingStore` class (JSONL read/write)      | WP03 |          | [D] |
| T012 | Implement `add_pending()` + `list_pending()`               | WP03 |          | [D] |
| T013 | Implement `remove_pending()` + `clear()`                   | WP03 |          | [D] |
| T014 | Validate schema against `contracts/widen-state.schema.json` | WP03 | | [D] |
| T015 | Implement `check_prereqs()` — Teamspace + Slack + reachability | WP02 | | [D] |
| T016 | Implement `run_audience_review()` — fetch audience-default + rich.Panel render | WP04 | | [D] |
| T017 | Implement trim-input parsing (empty=all, CSV=subset, cancel=abort) | WP04 | | [D] |
| T018 | Implement cancel path (Esc / "cancel" keyword / Ctrl+C) for audience review | WP04 | | [D] |
| T019 | Render confirmation + `calling widen endpoint...` message   | WP04 |          | [D] |
| T020 | Error handling on SaaS failure during audience review       | WP04 |          | [D] |
| T021 | Implement `WidenFlow.run_widen_mode()` orchestrator         | WP05 |          | [D] |
| T022 | Widen POST call via `SaasClient.post_widen()` in flow      | WP05 |          | [D] |
| T023 | Implement `[b/c]` pause-semantics prompt (FR-007, FR-008, FR-009) | WP05 | | [D] |
| T024 | Return `WidenFlowResult` to interview loop caller           | WP05 |          | [D] |
| T025 | Render `[b/c]` success panel with Slack thread URL         | WP05 |          | [D] |
| T026 | Extend charter `interview()` prereq check at startup        | WP06 |          | [D] |
| T027 | Extend per-question prompt to include `[w]iden` when prereqs satisfied | WP06 | | [D] |
| T028 | Detect `w` input + call `WidenFlow.run_widen_mode()`       | WP06 |          | [D] |
| T029 | Implement blocked-prompt loop (`Waiting >` prompt)          | WP06 |          | [D] |
| T030 | Blocked-prompt: handle plain-text local answer → `decision.resolve(manual)` | WP06 | | [D] |
| T031 | Blocked-prompt: `[f]etch & review` → enter candidate review | WP06 | | [D] |
| T032 | Blocked-prompt: `[d]efer` → `decision.defer()`            | WP06 |          | [D] |
| T033 | Emit LLM summarization request instruction block to stdout  | WP07 |          | [D] |
| T034 | Read + parse LLM JSON response from stdin (with 30s timeout, NFR-003) | WP07 | | [D] |
| T035 | Implement `run_candidate_review()` — render discussion context + candidate | WP07 | | [D] |
| T036 | Implement `[a]ccept` path → `decision.resolve(slack_extraction)` | WP07 | | [D] |
| T037 | Implement `[e]dit` path → editor pre-fill + material-edit detection | WP07 | | [D] |
| T038 | Implement `[d]efer` path → `decision.defer()` with required rationale | WP07 | | [D] |
| T039 | Implement provenance assignment logic (`SummarySource` rules from data-model.md §4) | WP07 | | [D] |
| T040 | Implement end-of-interview pending pass in charter `interview()` | WP08 | | [D] |
| T041 | For each pending entry: fetch discussion + run candidate review | WP08 | | [D] |
| T042 | Remove resolved entries from `WidenPendingStore`            | WP08 |          | [D] |
| T043 | Extend `specify` interview flow with same `[w]` affordance + WidenFlow | WP08 | [D] |
| T044 | Extend `plan` interview flow with same `[w]` affordance + WidenFlow | WP08 | [D] |
| T045 | Implement `[f]etch & review` command at already-widened question prompt | WP08 | | [D] |
| T046 | Add `decision widen` subcommand (hidden=True) under `agent decision` | WP09 | | [D] |
| T047 | Implement `--dry-run` mode for `decision widen`             | WP09 |          | [D] |
| T048 | Implement `--invited` CSV parsing + `SaasClient.post_widen()` call | WP09 | | [D] |
| T049 | Implement `[WIDEN-HINT]` prefix detection + dim render (FR-021) | WP09 | | [D] |
| T050 | Unit tests: saas_client + prereq + audience + state         | WP10 |          | [D] |
| T051 | Unit tests: review (candidate review, provenance, fallback) | WP10 | [D] |
| T052 | Integration tests: charter widen flows (happy path `[b]`, `[c]`, prereq suppression) | WP10 | | [D] |
| T053 | Integration tests: `decision widen` subcommand + end-of-interview pass | WP10 | [D] |

---

## Work Packages

---

### WP01 — SaaS Client Foundation

**Goal:** Create the thin `src/specify_cli/saas_client/` HTTP client package that all widen modules will use to talk to spec-kitty-saas #110 and #111 endpoints.

**Priority:** P0 — All other widen WPs depend on this.

**Estimated prompt size:** ~330 lines

**Included subtasks:**
- [x] T001 Create `saas_client/` package skeleton + `__init__.py` (WP01)
- [x] T002 Implement `SaasClient` class with httpx + DI factory (WP01)
- [x] T003 Implement auth context: env var + saas-auth.json fallback (WP01)
- [x] T004 Implement endpoint helpers (audience_default, widen, discussion_fetch, integrations, health) (WP01)
- [x] T005 Implement `SaasClientError` hierarchy + timeout/auth errors (WP01)

**Implementation sketch:**
1. Create `src/specify_cli/saas_client/__init__.py`, `client.py`, `auth.py`, `endpoints.py`, `errors.py`.
2. `SaasClient.__init__` takes `base_url: str`, `token: str`, `timeout: float = 5.0`, optional `_http: httpx.Client`.
3. `SaasClient.from_env()` reads `SPEC_KITTY_SAAS_URL` + `SPEC_KITTY_SAAS_TOKEN`; falls back to `.kittify/saas-auth.json`.
4. All five endpoint methods, raising typed errors on failure.
5. Error hierarchy: `SaasClientError` → `SaasTimeoutError`, `SaasAuthError`, `SaasNotFoundError`.

**Dependencies:** None
**Parallel opportunities:** All five files can be written in parallel.

---

### WP02 — Widen Data Models + Prereq Checker

**Goal:** Create the `src/specify_cli/widen/` package with all shared data models and the prereq detection function.

**Priority:** P0 — Prereq logic feeds charter integration (WP06); models feed all other widen WPs.

**Estimated prompt size:** ~360 lines

**Included subtasks:**
- [x] T006 Create `widen/` package skeleton + `__init__.py` (WP02)
- [x] T007 Define `SummarySource` enum + `PrereqState` dataclass (WP02)
- [x] T008 Define `WidenAction` enum + `WidenFlowResult` dataclass (WP02)
- [x] T009 Define `WidenPendingEntry` Pydantic model (WP02)
- [x] T010 Define `DiscussionFetch` + `CandidateReview` Pydantic models (WP02)
- [x] T015 Implement `check_prereqs()` — Teamspace + Slack + reachability (WP02)

**Implementation sketch:**
1. Create `src/specify_cli/widen/__init__.py` (public re-exports), `models.py` (all Pydantic/dataclass shapes).
2. `models.py` includes: `SummarySource`, `PrereqState`, `WidenAction`, `WidenFlowResult`, `WidenPendingEntry`, `DiscussionFetch`, `CandidateReview`, `WidenResponse`.
3. `prereq.py`: `check_prereqs(saas_client, team_slug) -> PrereqState`. Three checks with 500ms timeouts each. Returns immediately if `SPEC_KITTY_SAAS_TOKEN` is absent (`saas_reachable=False`).
4. All models use `from __future__ import annotations`, `ConfigDict(frozen=True)`, `extra="forbid"` unless noted.

**Dependencies:** WP01 (SaasClient)
**Parallel opportunities:** `models.py` subtasks (T007–T010) can be written in one pass; T015 requires models.

---

### WP03 — Widen Pending State (JSONL Sidecar)

**Goal:** Implement `WidenPendingStore` — the per-mission JSONL file that tracks pending-external-input widened questions across CLI sessions.

**Priority:** P1 — Needed by WP05 (flow), WP06 (charter), WP08 (end-of-interview pass).

**Estimated prompt size:** ~280 lines

**Included subtasks:**
- [x] T011 Implement `WidenPendingStore` class (JSONL read/write) (WP03)
- [x] T012 Implement `add_pending()` + `list_pending()` (WP03)
- [x] T013 Implement `remove_pending()` + `clear()` (WP03)
- [x] T014 Validate schema against `contracts/widen-state.schema.json` (WP03)

**Implementation sketch:**
1. `state.py`: `WidenPendingStore(repo_root: Path, mission_slug: str)`. File path: `kitty-specs/<slug>/widen-pending.jsonl`.
2. `add_pending(entry)`: append JSON line. Enforces uniqueness by `decision_id`.
3. `list_pending()`: read file, parse each line, return list. Missing file = empty list.
4. `remove_pending(decision_id)`: rewrite file without the matching entry.
5. `clear()`: delete or truncate file.
6. Include a `validate_entry(raw: dict)` helper using the bundled JSON Schema (jsonschema).

**Dependencies:** WP02 (WidenPendingEntry model)
**Parallel opportunities:** T011–T013 are sequential; T014 can be added alongside T011.

---

### WP04 — Audience Review UX

**Goal:** Implement `run_audience_review()` — the inline UX for fetching the default audience, rendering it, accepting trim input, and returning the confirmed invite list (or None on cancel).

**Priority:** P1 — Called by WP05 flow orchestrator.

**Estimated prompt size:** ~320 lines

**Included subtasks:**
- [x] T016 Implement `run_audience_review()` — fetch audience-default + rich.Panel render (WP04)
- [x] T017 Implement trim-input parsing (empty=all, CSV=subset, cancel=abort) (WP04)
- [x] T018 Implement cancel path (Esc / "cancel" keyword / Ctrl+C) (WP04)
- [x] T019 Render confirmation + "Calling widen endpoint..." message (WP04)
- [x] T020 Error handling on SaaS failure during audience review (WP04)

**Implementation sketch:**
1. `audience.py`: `run_audience_review(saas_client, mission_id, question_text, console) -> list[str] | None`.
2. Render the Panel per `contracts/cli-contracts.md §2.1`. Title truncated to 60 chars.
3. Parse `Audience >` input: empty → full list; CSV → subset (case-insensitive match + unknown-name warning); `"cancel"` → return `None`.
4. Handle Ctrl+C (KeyboardInterrupt) → return `None` (same as cancel).
5. On SaaS error (audience fetch or widen POST): render `[red]Widen failed:[/red] <msg>` and return `None`.

**Dependencies:** WP01 (SaasClient), WP02 (models)
**Parallel opportunities:** T016–T020 are largely sequential; T018 is a small branch in T016.

---

### WP05 — Widen Flow Orchestrator

**Goal:** Implement `WidenFlow.run_widen_mode()` — the top-level entry point used by all interview loops. Orchestrates: audience review → POST widen → `[b/c]` pause-semantics prompt → return `WidenFlowResult`.

**Priority:** P1 — Gate for charter integration (WP06).

**Estimated prompt size:** ~340 lines

**Included subtasks:**
- [x] T021 Implement `WidenFlow.run_widen_mode()` orchestrator (WP05)
- [x] T022 Widen POST call via `SaasClient.post_widen()` in flow (WP05)
- [x] T023 Implement `[b/c]` pause-semantics prompt (FR-007, FR-008, FR-009) (WP05)
- [x] T024 Return `WidenFlowResult` to interview loop caller (WP05)
- [x] T025 Render `[b/c]` success panel with Slack thread URL (WP05)

**Implementation sketch:**
1. `flow.py`: `WidenFlow` class with `__init__(saas_client, repo_root, console)`.
2. `run_widen_mode(decision_id, mission_id, mission_slug, question_text, actor) -> WidenFlowResult`:
   - Call `run_audience_review()` → on cancel, return `WidenFlowResult(action=CANCEL)`.
   - Call `saas_client.post_widen(decision_id, invited)` → on error, render error + return `CANCEL`.
   - Render success Panel per §3 with Slack thread URL from response.
   - Prompt `Block here or continue? [b/c] (default: b):`. Enter or `b` → `BLOCK`; `c` → `CONTINUE`.
3. Return `WidenFlowResult(action=<action>, decision_id=decision_id, invited=invited)`.

**Dependencies:** WP01, WP02, WP03, WP04
**Parallel opportunities:** None (sequential chain).

---

### WP06 — Charter Integration

**Goal:** Extend `src/specify_cli/cli/commands/charter.py` `interview()` function with: prereq check at startup, `[w]iden` in per-question prompt, `w` input detection + `WidenFlow` dispatch, blocked-prompt loop, and pending-external-input tracking via `WidenPendingStore`.

**Priority:** P1 — Primary user-facing delivery for FR-001, FR-007–009, FR-018.

**Estimated prompt size:** ~460 lines

**Included subtasks:**
- [x] T026 Extend charter `interview()` prereq check at startup (WP06)
- [x] T027 Extend per-question prompt to include `[w]iden` when prereqs satisfied (WP06)
- [x] T028 Detect `w` input + call `WidenFlow.run_widen_mode()` (WP06)
- [x] T029 Implement blocked-prompt loop (`Waiting >` prompt) (WP06)
- [x] T030 Blocked-prompt: handle plain-text local answer → `decision.resolve(manual)` (WP06)
- [x] T031 Blocked-prompt: `[f]etch & review` → enter candidate review (WP06)
- [x] T032 Blocked-prompt: `[d]efer` → `decision.defer()` (WP06)

**Implementation sketch:**
1. Before the question loop: construct `SaasClient.from_env()` (non-fatal; catch all errors), call `check_prereqs()`, store `prereq_state`.
2. In per-question prompt construction: if `prereq_state.all_satisfied and not already_widened(decision_id)`, append `| [w]iden` to the hint line.
3. After `typer.prompt()`: if `user_answer.strip().lower() == "w"` → call `WidenFlow.run_widen_mode()`.
   - On `CANCEL`: loop again (show prompt again unchanged).
   - On `BLOCK`: enter blocked-prompt loop (see §4 of cli-contracts.md).
   - On `CONTINUE`: call `WidenPendingStore.add_pending(...)`, mark decision `open` in decisions store, advance.
4. Blocked-prompt loop: render `╭─ Waiting for widened discussion ─╮` Panel. Loop on input. Parse `f` → fetch+review, `d` → defer, `!cancel` → cancel, plain text → resolve(manual). Include NFR-004 60-minute inactivity reminder via threading.Timer.
5. Each resolution path calls the appropriate `_dm_service.*` call and breaks out of the blocked loop.

**Dependencies:** WP01, WP02, WP03, WP04, WP05, WP07
**Parallel opportunities:** T029–T032 (blocked-prompt branches) can be written in parallel once T029 scaffold exists.

---

### WP07 — Candidate Review UX + LLM Prompt Contract

**Goal:** Implement `run_candidate_review()` — emits the structured LLM summarization request, reads/parses the response, renders the candidate, and handles `[a]ccept`, `[e]dit`, and `[d]efer` with full provenance tagging.

**Priority:** P1 — Called by both WP06 (blocked prompt) and WP08 (end-of-interview pass).

**Estimated prompt size:** ~420 lines

**Included subtasks:**
- [x] T033 Emit LLM summarization request instruction block to stdout (WP07)
- [x] T034 Read + parse LLM JSON response from stdin (with 30s timeout, NFR-003) (WP07)
- [x] T035 Implement `run_candidate_review()` — render discussion context + candidate (WP07)
- [x] T036 Implement `[a]ccept` path → `decision.resolve(slack_extraction)` (WP07)
- [x] T037 Implement `[e]dit` path → editor pre-fill + material-edit detection (WP07)
- [x] T038 Implement `[d]efer` path → `decision.defer()` with required rationale (WP07)
- [x] T039 Implement provenance assignment logic (`SummarySource` rules) (WP07)

**Implementation sketch:**
1. `review.py`: `run_candidate_review(discussion_data: DiscussionFetch, decision_id: str, question_text: str, mission_slug: str, repo_root: Path, console: Console, dm_service, actor) -> CandidateReview | None`.
2. Render the discussion context compact block (§5.1 format) and the WIDEN SUMMARIZATION REQUEST instruction block to stdout.
3. Read stdin within 30s timeout using `threading.Timer` + `input()`. On timeout → fallback: `llm_timed_out=True`, empty candidate.
4. Parse JSON block from response (extract `{...}` from raw text, validate with `CandidateReview` Pydantic model).
5. Render `╭─ Candidate Review ─╮` Panel per §6.
6. `[a]`: resolve with `slack_extraction`. `[e]`: `click.edit(text=candidate_answer)` → detect material diff → assign source → optional rationale prompt → resolve. `[d]`: prompt rationale (required) → defer.
7. Provenance logic: normalized Levenshtein > 30% or empty → `mission_owner_override`/`manual`.

**Dependencies:** WP01, WP02
**Parallel opportunities:** T033–T034 (emit+read) can be developed in parallel with T035 (render).

---

### WP08 — End-of-Interview Pending Pass + Specify/Plan Integration

**Goal:** (1) Add end-of-interview pending-question resolution pass to charter. (2) Extend `specify` and `plan` interview flows with the same `[w]` affordance. (3) Handle the already-widened question prompt (`[f]etch & resolve`).

**Priority:** P1 — Closes FR-002, FR-010, FR-020.

**Estimated prompt size:** ~380 lines

**Included subtasks:**
- [x] T040 Implement end-of-interview pending pass in charter `interview()` (WP08)
- [x] T041 For each pending entry: fetch discussion + run candidate review (WP08)
- [x] T042 Remove resolved entries from `WidenPendingStore` (WP08)
- [x] T043 Extend `specify` interview flow with same `[w]` affordance + WidenFlow (WP08) [P]
- [x] T044 Extend `plan` interview flow with same `[w]` affordance + WidenFlow (WP08) [P]
- [x] T045 Implement `[f]etch & review` at already-widened question prompt (WP08)

**Implementation sketch:**
1. After the question loop in `charter.py`: check `WidenPendingStore.list_pending()`. If non-empty, render §7 Panel and iterate. For each: call `saas_client.fetch_discussion()` → `run_candidate_review()`. On resolve/defer: `store.remove_pending(decision_id)`.
2. For T043/T044: identify the interview loop in `src/specify_cli/missions/plan/` and `specify`-related commands. Apply the same `prereq_state + [w] affordance + WidenFlow.run_widen_mode()` pattern. The `origin_flow` field passed to `_dm_service.open_decision()` differs (`SPECIFY`, `PLAN`).
3. T045: in the per-question prompt render, if a decision is already in `widen-pending.jsonl`, show the §1.3 already-widened prompt instead of the standard prompt. `[f]` enters `fetch+review`.

**Dependencies:** WP06, WP07, WP05
**Parallel opportunities:** T043 and T044 can be done in parallel after WP06 pattern is locked.

---

### WP09 — Internal `decision widen` Subcommand + LLM Hint

**Goal:** Add the `spec-kitty agent decision widen` internal subcommand (FR-022, hidden from end-user `--help`) and implement `[WIDEN-HINT]` prefix detection + dim rendering (FR-021).

**Priority:** P2 — Useful for automation/testing; hint is informational only.

**Estimated prompt size:** ~280 lines

**Included subtasks:**
- [x] T046 Add `decision widen` subcommand (hidden=True) under `agent decision` (WP09)
- [x] T047 Implement `--dry-run` mode for `decision widen` (WP09)
- [x] T048 Implement `--invited` CSV parsing + `SaasClient.post_widen()` call (WP09)
- [x] T049 Implement `[WIDEN-HINT]` prefix detection + dim render (FR-021) (WP09)

**Implementation sketch:**
1. In `src/specify_cli/cli/commands/decision.py`: add `@decision_app.command(hidden=True)` `widen(decision_id: str, invited: str, mission_slug: str | None, dry_run: bool)`.
2. Parse `--invited` CSV → list. On `--dry-run`: print what would be called, exit 0.
3. Construct `SaasClient.from_env()`, call `post_widen(decision_id, invited)`, print result JSON.
4. `[WIDEN-HINT]` detection: in charter/specify/plan prompt rendering, check LLM output context (not applicable to normal `typer.prompt` path — this hint is rendered by the harness LLM, not CLI). In the CLI, detect lines with `[WIDEN-HINT] ` prefix that arrive as part of the current question's context prefix and render them `[dim]<text>[/dim]` above the prompt.

**Dependencies:** WP01, WP02, WP05
**Parallel opportunities:** T046–T048 and T049 can be developed in parallel.

---

### WP10 — Tests

**Goal:** Full test coverage for all new widen modules and integration paths. Mocked SaaS client via `respx`, mocked LLM response via fixture JSON, `typer.testing.CliRunner` for CLI flows.

**Priority:** P1 — Required for NFR-005 (≤90s delta) and NFR-006 (mypy/ruff clean).

**Estimated prompt size:** ~480 lines

**Included subtasks:**
- [x] T050 Unit tests: saas_client + prereq + audience + state (WP10)
- [x] T051 Unit tests: review (candidate review, provenance, fallback) (WP10) [P]
- [x] T052 Integration tests: charter widen flows (happy path `[b]`, `[c]`, prereq suppression) (WP10)
- [x] T053 Integration tests: `decision widen` subcommand + end-of-interview pass (WP10) [P]

**Test files:**
- `tests/specify_cli/saas_client/test_client.py` — contract tests with respx
- `tests/specify_cli/widen/test_prereq.py` — all prereq combinations
- `tests/specify_cli/widen/test_audience.py` — trim parsing, cancel
- `tests/specify_cli/widen/test_state.py` — JSONL CRUD + round-trip
- `tests/specify_cli/widen/test_review.py` — `[a/e/d]` branches, provenance, timeout fallback
- `tests/specify_cli/cli/commands/test_charter_widen.py` — CliRunner end-to-end
- `tests/specify_cli/cli/commands/test_charter_prereq_suppression.py` — no `[w]` when prereqs absent
- `tests/specify_cli/cli/commands/test_decision_widen_subcommand.py` — internal subcommand + `--dry-run`

**Dependencies:** WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08, WP09
**Parallel opportunities:** T050 and T051 can be written once their source modules are done; T052 and T053 require WP06+WP08.

---

## Execution Lanes (computed by finalize-tasks)

Dependency chain: WP01 → WP02 → WP03, WP04 → WP05 → WP06 → WP07 → WP08 → WP10

**Parallelization opportunities:**
- WP03 and WP04 can run in parallel (both depend on WP02 only).
- WP07 and WP08 share WP06 as dependency but WP07 must precede WP08 (review is called from end-of-interview pass).
- T043 and T044 (specify/plan) within WP08 are parallel.
- T050 and T051 within WP10 are parallel.

**MVP scope:** WP01 + WP02 + WP03 + WP04 + WP05 + WP06 + WP07 deliver the primary happy path (press `[w]`, block, fetch, accept/edit/defer). WP08 adds the secondary scenario (continue + end-of-interview pass + specify/plan). WP09 adds tooling and LLM hint.

**WP prompt files:**
- `tasks/WP01-saas-client-foundation.md`
- `tasks/WP02-widen-data-models-and-prereq.md`
- `tasks/WP03-widen-pending-state.md`
- `tasks/WP04-audience-review-ux.md`
- `tasks/WP05-widen-flow-orchestrator.md`
- `tasks/WP06-charter-integration.md`
- `tasks/WP07-candidate-review-ux.md`
- `tasks/WP08-end-of-interview-and-specify-plan.md`
- `tasks/WP09-decision-widen-subcommand.md`
- `tasks/WP10-tests.md`
