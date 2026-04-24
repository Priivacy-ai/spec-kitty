# Implementer Quickstart — CLI Widen Mode & Decision Write-Back

**Mission:** `cli-widen-mode-and-write-back-01KPXFGJ`
**For:** Implementing engineer (WP implementers)

This walkthrough covers the full development loop: environment setup, happy path verification, each test branch, and the release checklist.

---

## 1. Setup

### 1.1 Prerequisites

- Python 3.11+ virtual environment with `spec-kitty-cli` installed in editable mode:
  ```bash
  cd /path/to/spec-kitty
  pip install -e ".[dev]"
  ```
- `mypy`, `ruff`, `pytest`, `respx` (httpx mock) installed in dev extras.
- `spec-kitty-saas` running locally or a staging deployment accessible.

### 1.2 Environment variables

```bash
# Required for widen mode (all three must be set for prereqs to pass)
export SPEC_KITTY_SAAS_URL="http://localhost:8000"       # or staging URL
export SPEC_KITTY_SAAS_TOKEN="your-session-token"        # from spec-kitty login or staging

# Optional: suppress LLM summarization timeout for fast manual testing
export SPEC_KITTY_WIDEN_SUMMARIZE_TIMEOUT="300"          # 300s for interactive dev
```

If `SPEC_KITTY_SAAS_TOKEN` is not set, `check_prereqs()` returns `saas_reachable=False` and `[w]` is silently suppressed. The rest of the interview works normally (C-007).

### 1.3 Slack integration on staging team

For end-to-end Slack testing, ensure your staging Teamspace has:
- A Slack workspace connected (via `GET /api/v1/teams/{slug}/integrations` returning `["slack"]`).
- The bot token configured in the SaaS staging env.

For unit/integration tests, Slack is always mocked — no real Slack connection needed.

### 1.4 Verify prereqs with a doctor check

```bash
# (Out of scope for V1, but useful during dev)
spec-kitty doctor widen  # If implemented in a future mission
```

During V1 development, verify prereqs manually:
```bash
python -c "
from specify_cli.widen.prereq import check_prereqs
from specify_cli.saas_client import SaasClient
client = SaasClient.from_env()
state = check_prereqs(client, team_slug='your-team-slug')
print(state)
"
```

---

## 2. Run charter interview and verify `[w]` appears

```bash
spec-kitty charter interview --mission-slug cli-widen-mode-and-write-back-01KPXFGJ
```

At the first question, you should see:
```
What is the project name? [my-project]:
[enter]=accept default | [text]=type answer | [w]iden | [d]efer | [!cancel]
```

If `[w]iden` is absent, check that all three prereqs are satisfied:
- Is `SPEC_KITTY_SAAS_TOKEN` set and valid?
- Is `SPEC_KITTY_SAAS_URL` pointing to a live instance?
- Does your token's team have Slack integration? (`GET /api/v1/teams/{slug}/integrations`)

---

## 3. Press `w` — audience review → trim → confirm → SaaS widen called

At any question prompt, type `w` and press Enter.

Expected flow:
1. CLI calls `GET /api/v1/missions/{id}/audience-default` and renders:
   ```
   ╭─ Widen: What is the project name? ────────────────────────────────╮
   │ Default audience for this decision:                               │
   │   Alice Johnson, Bob Smith, Carol Lee, Dana Park                  │
   │ ...                                                               │
   ```
2. Press Enter to accept all, or type `Alice Johnson, Carol Lee` to trim.
3. CLI calls `POST /api/v1/decision-points/{id}/widen` with `{"invited": ["Alice Johnson", "Carol Lee"]}`.
4. Success banner appears with Slack thread URL.

**To verify with a local mock instead of staging:**

```bash
# In a separate terminal, start the httpx mock server (or use respx in tests)
# See tests/specify_cli/saas_client/test_client.py for mock patterns
```

In tests, use the `CliRunner` pattern:
```python
from typer.testing import CliRunner
from specify_cli.cli.app import app

runner = CliRunner()
result = runner.invoke(app, ["charter", "interview", "--mission-slug", "test-mission"],
                       input="w\n\nAlice Johnson, Carol Lee\n\n")
assert "Slack thread created" in result.output
```

---

## 4. Test both `[b]` block and `[c]` continue paths

### 4.1 Block path

After widen succeeds and the `[b/c]` prompt appears, press Enter (default `b`):

```
Block here or continue with other questions? [b/c] (default: b):
```

Expected: interview pauses. You see:
```
╭─ Waiting for widened discussion ──────────────────────────────────╮
│ Question: What is the project name?                               │
│ Participants: Alice Johnson, Carol Lee                            │
│ Slack thread: https://...                                         │
╰───────────────────────────────────────────────────────────────────╯
Waiting >
```

Verify the blocked prompt accepts `f`, plain text, and `d`.

### 4.2 Continue path

After widen succeeds, type `c` at the `[b/c]` prompt:

```
Block here or continue with other questions? [b/c] (default: b): c
Question parked as pending. You'll be prompted to resolve it at end of interview.
```

Expected: interview advances to the next question. The pending entry appears in `kitty-specs/<slug>/widen-pending.jsonl`.

```bash
cat kitty-specs/cli-widen-mode-and-write-back-01KPXFGJ/widen-pending.jsonl
# Should show one JSON line with the parked question's decision_id
```

At end of interview:
```
╭─ Pending Widened Questions ────────────────────────────────────────╮
│ 1 widened question is still pending...                            │
╰────────────────────────────────────────────────────────────────────╯
```

---

## 5. Test local-answer-at-blocked-prompt → SaaS observes terminal state

From the blocked prompt (`Waiting >`), type a plain-text answer:

```
Waiting > PostgreSQL with migration path planned from day 1
```

Expected:
1. CLI calls `decision.resolve(final_answer="PostgreSQL...", summary_json={"source": "manual", "text": ""})`.
2. CLI prints: `Resolved locally. SaaS will close the Slack thread shortly.`
3. Interview resumes at next question.

Verify in SaaS: `GET /api/v1/decision-points/{id}` should show `status=resolved`.
Verify in Slack (staging): the thread should receive a closure message from #111 within ~30 seconds (SC-002).

---

## 6. Test review prompt `[a/e/d]` with mocked discussion fetch

From the blocked prompt, type `f` to fetch & review:

```
Waiting > f
Fetching discussion...
```

The CLI renders the LLM summarization request (contracts §5) and waits for the LLM response. In a test harness, inject the mock response:

```python
# Simulate LLM producing a candidate block
mock_llm_response = '{"candidate_summary": "Team agrees on PostgreSQL.", "candidate_answer": "PostgreSQL.", "source_hint": "slack_extraction"}'
runner.invoke(app, [...], input=f"f\n{mock_llm_response}\na\n")
```

Verify `[a]ccept`:
- `decisions/index.json` entry has `status=resolved`, `final_answer="PostgreSQL."`.
- `summary_json.source = "slack_extraction"`.

Verify `[e]dit` with material change:
```python
runner.invoke(app, [...], input=f"f\n{mock_llm_response}\ne\n")
# Editor opens pre-filled with "PostgreSQL."
# User saves with "PostgreSQL with read replicas."
# CLI detects material change → prompts for optional rationale
```
- `summary_json.source = "mission_owner_override"`.

Verify `[d]efer`:
```python
runner.invoke(app, [...], input=f"f\n{mock_llm_response}\nd\nNot enough context yet\n")
```
- `decisions/index.json` entry has `status=deferred`, `rationale="Not enough context yet"`.

---

## 7. Test provenance tagging

### `slack_extraction`
- Accept candidate unchanged: `[a]`.
- Minor edit (fix a typo in candidate): `[e]`, save with <30% distance change.
- Verify: `summary_json.source == "slack_extraction"`.

### `mission_owner_override`
- Material edit: `[e]`, save with significantly different text.
- Verify: `summary_json.source == "mission_owner_override"`.

### `manual`
- LLM timeout: set `SPEC_KITTY_WIDEN_SUMMARIZE_TIMEOUT=0` (force timeout), then `[f]etch & review`.
- Verify: editor opens blank, owner types fresh answer.
- Verify: `summary_json.source == "manual"`.
- Also: plain-text answer at blocked prompt → `source == "manual"`.

```bash
SPEC_KITTY_WIDEN_SUMMARIZE_TIMEOUT=0 spec-kitty charter interview --mission-slug test
```

---

## 8. Test prereq suppression

### User without Teamspace

```bash
# Use a token that belongs to no Teamspace (or unset the token)
unset SPEC_KITTY_SAAS_TOKEN
spec-kitty charter interview --mission-slug test
```

At every question, `[w]iden` must NOT appear in the prompt. The interview must complete normally using the existing `[d]efer | [!cancel]` options (SC-004, C-007, C-009).

Verify:
- No `[w]iden` in any prompt text.
- No error banners or noisy warnings about missing Teamspace.
- `answers.yaml` written correctly at the end.

### Slack integration not configured

Mock `GET /api/v1/teams/{slug}/integrations` to return `[]` (empty list):
```python
# In test:
with respx.mock:
    respx.get(".../integrations").respond(200, json=[])
    result = runner.invoke(...)
assert "[w]iden" not in result.output
```

### SaaS unreachable

```bash
export SPEC_KITTY_SAAS_URL="http://localhost:9999"  # nothing listening
spec-kitty charter interview --mission-slug test
```

`[w]iden` suppressed. Interview completes locally (C-007).

---

## 9. Test suite commands

```bash
# Run all widen-related tests
cd /path/to/spec-kitty
pytest tests/specify_cli/widen/ -v

# Run charter interview integration tests (includes widen paths)
pytest tests/specify_cli/cli/commands/test_charter_widen.py -v
pytest tests/specify_cli/cli/commands/test_charter_prereq_suppression.py -v

# Run saas_client contract tests
pytest tests/specify_cli/saas_client/ -v

# Full suite (verify NFR-005: ≤90s added to baseline)
time pytest tests/ -x -q

# Type checking
mypy src/specify_cli/widen/ src/specify_cli/saas_client/

# Lint
ruff check src/specify_cli/widen/ src/specify_cli/saas_client/
```

Expected: all tests pass, mypy clean, ruff clean (NFR-006).

---

## 10. Release checklist

Before marking the implementation WP as ready for review:

- [ ] All new test files pass: `pytest tests/specify_cli/widen/ tests/specify_cli/saas_client/`
- [ ] Charter interview integration tests pass (widen happy path, both `[b]` and `[c]` branches, prereq suppression)
- [ ] `mypy src/specify_cli/widen/ src/specify_cli/saas_client/` exits 0
- [ ] `ruff check src/specify_cli/widen/ src/specify_cli/saas_client/` exits 0
- [ ] `WidenPendingStore` JSONL round-trip test passes (write + read + remove)
- [ ] `summary_json.source` provenance verified for all three values in tests
- [ ] `NFR-001`: prompt render time (with mocked prereq check) < 300ms verified in test assertions
- [ ] `NFR-004`: inactivity reminder fires at 60m (unit test with time mock)
- [ ] Internal `spec-kitty agent decision widen --dry-run` subcommand works
- [ ] `[w]` is NOT shown in prompt when `SPEC_KITTY_SAAS_TOKEN` is unset (SC-004)
- [ ] `answers.yaml` is written correctly at interview completion with and without widen
- [ ] No direct Slack API calls anywhere in `specify_cli` codebase (grep confirms C-004)
- [ ] `contracts/widen-state.schema.json` validates against a real `widen-pending.jsonl` entry using `jsonschema`
- [ ] Full test suite wall-clock delta confirmed ≤ 90s (NFR-005)
