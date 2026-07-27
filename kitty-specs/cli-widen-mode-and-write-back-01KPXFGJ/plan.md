# Technical Implementation Plan — CLI Widen Mode & Decision Write-Back

**Mission:** `cli-widen-mode-and-write-back-01KPXFGJ`
**Issue:** `spec-kitty#758`
**Depends on:** spec-kitty #757 (merged), spec-kitty-saas #110, spec-kitty-saas #111

---

## Charter Check

_Skipped — no project charter exists in this repo. Interview-only flow._

---

## 1. Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11+ |
| CLI framework | `typer` (existing) |
| Rich rendering | `rich` (existing: `Console`, `Panel`, `Table`, `Prompt`) |
| YAML I/O | `ruamel.yaml` (existing, for answers.yaml; widen state uses JSONL) |
| Pydantic models | Pydantic v2 (existing, used in `decisions/models.py`) |
| HTTP client | `httpx` (sync, pluggable for tests) |
| Test runner | `pytest` + `typer.testing.CliRunner` |
| Type checking | `mypy` |
| Lint | `ruff` |
| ULID minting | `ulid` (already vendored in decisions layer) |

### Active LLM Integration Surface

The CLI does **not** embed an LLM or call an inference API directly (C-002, and consistent with the charter synthesizer comment in `charter.py` line 1086: "spec-kitty never calls an LLM itself"). The active LLM session (Claude Code, Codex, or equivalent harness) performs summarization by:

1. The CLI fetches discussion data from SaaS (#111's endpoint) and writes/renders it into the current tool-output context.
2. The CLI emits a structured prompt contract (see `contracts/cli-contracts.md` §4) that instructs the active LLM session to produce a candidate summary and candidate answer in a specific JSON block format.
3. The LLM session responds with the structured block; the CLI parses it and presents it to the owner for `[a/e/d]` review.
4. The owner confirms; the CLI calls `decision resolve` with the accepted/edited payload.

This is a **prompt-contract** model, not an API-call model. The CLI acts as orchestrator and reviewer; the LLM session acts as summarizer. No direct `anthropic` SDK or OpenAI SDK calls are made from this codebase.

---

## 2. Module Structure

### New module: `src/specify_cli/widen/`

```
src/specify_cli/widen/
    __init__.py          # Public API re-exports
    prereq.py            # PrereqChecker: Teamspace + Slack + SaaS reachability
    audience.py          # AudienceReviewer: fetch default audience, trim UX
    review.py            # CandidateReviewer: render discussion + [a/e/d] prompt
    state.py             # WidenPendingStore: JSONL sidecar read/write
    flow.py              # WidenFlow: top-level orchestrator used by charter/specify/plan
```

#### `prereq.py`
Exposes `check_prereqs(saas_client, auth_context) -> PrereqState`.
- Teamspace membership: from auth context (session token carries team membership; see `saas_client.auth.get_auth_context()`).
- Slack integration: `GET /api/v1/teams/{slug}/integrations` — checks for `slack` entry in response. Timeout 500ms; failure → `slack_ok=False`.
- SaaS reachability: lightweight `GET /api/v1/health` probe. Timeout 500ms; failure → `saas_reachable=False`.
- All three must be `True` for `all_satisfied=True`; otherwise `[w]` is suppressed (C-009: silently, no noisy error).

#### `audience.py`
Exposes `run_audience_review(saas_client, mission_id, console) -> list[str] | None`.
- Calls `GET /api/v1/missions/{id}/audience-default` (FR-004).
- Renders audience list via `rich.Panel`.
- Prompts: `[Enter] to confirm or type comma-separated names to trim`.
- Returns trimmed list, or `None` on cancel (`[Esc]` / `cancel` keyword).

#### `review.py`
Exposes `run_candidate_review(discussion_data, console) -> CandidateReview | None`.
- Renders fetched discussion context (compact form: participant names + message count + thread URL).
- Emits the LLM prompt contract (see §4 of contracts) that instructs the active harness to produce the candidate block.
- Reads the LLM-produced candidate block from stdin (the harness writes it back into the session output).
- Presents candidate summary + candidate answer via `rich.Panel`.
- Prompts `[a]ccept | [e]dit | [d]efer`.
- On `[e]`: opens `$EDITOR` (via `typer.launch` or `click.edit`) pre-filled with candidate answer.
- Returns `CandidateReview` or `None` on defer.

#### `state.py`
Exposes `WidenPendingStore` class.
- Backed by `kitty-specs/<slug>/widen-pending.jsonl`.
- `add_pending(entry: WidenPendingEntry) -> None`
- `list_pending() -> list[WidenPendingEntry]`
- `remove_pending(decision_id: str) -> None`
- `clear() -> None`
- JSONL schema: one `WidenPendingEntry` per line (see `data-model.md` §2).

#### `flow.py`
Exposes `WidenFlow` class used by `charter.py`, `specify`, and `plan` interview loops.
- `run_widen_mode(decision_id, mission_slug, repo_root, console, saas_client, actor) -> WidenResult`
- Orchestrates: audience review → POST widen → pause semantics prompt → return `WidenResult(action=block|continue|cancel)`.

### New module: `src/specify_cli/saas_client/`

```
src/specify_cli/saas_client/
    __init__.py          # SaasClient factory
    client.py            # SaasClient (httpx-based, pluggable)
    auth.py              # AuthContext: read session token + team slug from env/config
    endpoints.py         # Typed endpoint helpers (audience_default, widen, discussion_fetch)
    errors.py            # SaasClientError, SaasAuthError, SaasTimeoutError
```

`SaasClient` is constructed with a base URL and auth token; tests inject a mock `httpx.Client`. No singleton — constructed fresh per CLI invocation, passed as a dependency.

Auth token source (FR-003, C-007): `SPEC_KITTY_SAAS_TOKEN` env var → falls back to `.kittify/saas-auth.json` (written by future `spec-kitty login` command). If token absent → `saas_reachable=False` → `[w]` suppressed silently.

### Extensions to existing files

#### `src/specify_cli/cli/commands/charter.py`

The `interview()` command (lines 413–596) is extended:

1. **Prereq check** (once, before the question loop): construct `SaasClient` if env allows; call `check_prereqs()` → `prereq_state`. O(1) — three parallel async probes or sequential with short timeouts (NFR-001: ≤300ms combined).
2. **Per-question prompt extension**: if `prereq_state.all_satisfied` AND decision is not already widened/terminal, append `[w]iden` to prompt text (FR-001, FR-020, C-009).
3. **Answer capture loop**: after `typer.prompt`, detect if user typed `w` → enter `WidenFlow.run_widen_mode()`.
   - On `WidenResult.action == cancel`: return to prompt unchanged.
   - On `WidenResult.action == block`: enter blocked-prompt loop (FR-008).
   - On `WidenResult.action == continue`: call `_dm_service.open_decision(...)` then mark pending in `WidenPendingStore`, advance to next question (FR-009).
4. **Blocked-prompt loop** (FR-008, FR-018): special prompt loop that accepts either `[a/e/d]` commands or plain-text local answer. On plain text → `decision resolve` with `source=manual`; on `[a/e/d]` → `run_candidate_review()`.
5. **End-of-interview pending pass** (FR-010): after all questions answered, check `WidenPendingStore.list_pending()`. If non-empty, surface "N widened questions still pending" and iterate through `run_candidate_review()` for each.
6. **LLM widen hint** (FR-021): the LLM harness may prepend a suggestion hint to the question render. The CLI reads from the hint output prefix (see contracts §5) and renders it as `[dim]` text before the prompt. The `[w]` affordance is always present regardless.

The same pattern applies to `specify` and `plan` interview flows (FR-002), which will import `WidenFlow` and `check_prereqs` from `specify_cli.widen`.

#### `src/specify_cli/cli/commands/decision.py` (existing or new)

Adds internal `widen` subcommand under `spec-kitty agent decision` group (FR-022):

```
spec-kitty agent decision widen <decision_id> --invited <comma-separated-names>
                                               [--mission-slug <slug>]
                                               [--dry-run]
```

Hidden from `--help` by default (`hidden=True` on the typer command). Calls `SaasClient.widen_decision_point(decision_id, invited)` and `WidenPendingStore` as needed. Exists for automation and test harness use.

---

## 3. SaaS Client Design

```python
class SaasClient:
    def __init__(self, base_url: str, token: str, timeout: float = 5.0) -> None: ...
    def get_audience_default(self, mission_id: str) -> list[str]: ...           # FR-004
    def post_widen(self, decision_id: str, invited: list[str]) -> WidenResponse: ... # FR-005
    def get_team_integrations(self, team_slug: str) -> list[str]: ...           # FR-003
    def health_probe(self) -> bool: ...                                          # FR-003
    def fetch_discussion(self, decision_id: str) -> DiscussionData: ...         # FR-011
```

All methods raise `SaasClientError` (subclassed by `SaasTimeoutError`, `SaasAuthError`). Callers wrap in `contextlib.suppress` or explicit try/except; SaaS failures are non-fatal for the interview (C-007).

Pluggable via dependency injection: `SaasClient` takes an optional `_http: httpx.Client` parameter for test injection. Production code calls `SaasClient.from_env()` factory.

---

## 4. DecisionStatus Extension

The existing `DecisionStatus` enum in `decisions/models.py` needs a new value:

```python
PENDING_EXTERNAL_INPUT = "pending-external-input"
```

This is a non-terminal, non-open state: the question has been widened and the user chose `[c]`ontinue. The decision is "parked". It is not stored in the `index.json` in this state (that remains open); instead, the `widen-pending.jsonl` sidecar tracks it locally (FR-009).

Alternatively, `pending-external-input` can be tracked purely in the local JSONL sidecar without touching `DecisionStatus`. This is preferred to avoid mutating the decisions store schema — the existing `open` status remains on the `IndexEntry`; the `widen-pending.jsonl` is the additional local signal.

**Decision: sidecar-only for pending-external-input.** `IndexEntry.status` stays `open` for parked decisions; `widen-pending.jsonl` is the authoritative local signal for the end-of-interview pass (FR-010).

---

## 5. Widen Decision Point Lifecycle (CLI-side)

```
interview question
  └─ prereqs satisfied? ──No──> prompt without [w]
       Yes
       └─ user presses [w]
            └─ AudienceReviewer: fetch default, trim, confirm
                 Cancel ──────────────────────────────────────> return to prompt unchanged
                 Confirm
                 └─ SaasClient.post_widen(decision_id, invited)
                      Error ─────────────────────────────────> surface error, return to prompt
                      Success (DecisionPoint now widened in SaaS)
                      └─ prompt: [b/c] (default: b)
                           [c] continue
                           └─ WidenPendingStore.add_pending(entry)
                                advance to next question
                           [b] block
                           └─ enter blocked-prompt loop
                                while True:
                                  show "Waiting for widened discussion..."
                                  prompt accepts: [a/e/d] or plain text or wait
                                  plain text ──> decision.resolve(manual) → SaaS observes → #111 closes Slack
                                  [a/e/d] ──────> run_candidate_review() → decision.resolve/defer
                                  both paths ──> exit blocked loop, resume interview at next question
```

At end of interview, for each entry in `WidenPendingStore.list_pending()`:
- Fetch discussion via `SaasClient.fetch_discussion(decision_id)`.
- Run `run_candidate_review()`.
- `[a]` / `[e]` → `decision.resolve()`.
- `[d]` → `decision.defer()`.
- Remove entry from sidecar.

---

## 6. Testing Strategy

### Unit tests (fast, no network)

| Test file | What it covers |
|---|---|
| `tests/specify_cli/widen/test_prereq.py` | `check_prereqs()` with mocked `SaasClient`; all prereq combinations |
| `tests/specify_cli/widen/test_audience.py` | `run_audience_review()` with mocked SaaS; trim parsing; cancel path |
| `tests/specify_cli/widen/test_review.py` | `run_candidate_review()` with stubbed LLM output; `[a/e/d]` branches; material-edit detection |
| `tests/specify_cli/widen/test_state.py` | `WidenPendingStore` CRUD; JSONL round-trip; `schema_version` |
| `tests/specify_cli/saas_client/test_client.py` | Contract tests with `respx` (httpx mock); timeout handling; auth error |

### Integration tests

| Test file | What it covers |
|---|---|
| `tests/specify_cli/cli/commands/test_charter_widen.py` | `CliRunner` end-to-end: `w` → audience → widen → `[b]` → local answer; `w` → `[c]` → end-of-interview pass |
| `tests/specify_cli/cli/commands/test_charter_prereq_suppression.py` | No `[w]` in prompt when prereqs not satisfied |
| `tests/specify_cli/cli/commands/test_decision_widen_subcommand.py` | Internal `agent decision widen` subcommand; `--dry-run` mode |

### NFR-005 compliance

Suite additions must not add more than 90s to the full test run. All HTTP calls are mocked via `respx`; no real network. LLM summarization is stubbed with a fixture JSON block.

### Type-checking / lint

`mypy` and `ruff` run clean on all new code (NFR-006). Use `from __future__ import annotations` on all new modules. Pydantic v2 `model_config = ConfigDict(frozen=True)` on data models.
