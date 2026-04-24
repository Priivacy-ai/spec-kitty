---
work_package_id: WP05
title: Widen Flow Orchestrator
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- C-001
- C-003
- FR-005
- FR-007
- FR-008
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
agent: "claude:sonnet-4-7:python-reviewer:reviewer"
shell_pid: "73827"
history:
- date: '2026-04-23T15:43:52Z'
  event: created
agent_profile: python-implementer
authoritative_surface: src/specify_cli/widen/flow.py
execution_mode: code_change
mission_slug: cli-widen-mode-and-write-back-01KPXFGJ
model: claude-sonnet-4-7
owned_files:
- src/specify_cli/widen/flow.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-implementer
```

---

## Objective

Implement `WidenFlow` in `src/specify_cli/widen/flow.py` — the top-level orchestrator called by the interview loops when the user presses `w`. It sequences: audience review → POST widen → `[b/c]` pause-semantics prompt, and returns a `WidenFlowResult` to the caller.

---

## Context

`WidenFlow.run_widen_mode()` is the single entry point from charter/specify/plan interview loops. It owns the sequence described in plan.md §5 (Widen Decision Point Lifecycle, CLI-side). It must handle every failure gracefully and always return a `WidenFlowResult` — never raise to the interview loop.

The `[b/c]` prompt produces `BLOCK` or `CONTINUE`. On `BLOCK`, the flow returns and the interview loop enters the blocked-prompt loop (implemented in WP06, not here). On `CONTINUE`, the flow returns and the caller writes a `WidenPendingEntry` to the store.

---

## Branch Strategy

Depends on WP01, WP02, WP03, WP04. Implementation command:
```bash
spec-kitty agent action implement WP05 --agent claude
```

---

## Subtask T021 — Implement `WidenFlow.run_widen_mode()` Orchestrator

**Purpose:** Top-level orchestration: call audience review, then POST widen, then ask block-or-continue.

**File:** `src/specify_cli/widen/flow.py`

```python
from __future__ import annotations
from pathlib import Path
from rich.console import Console
from specify_cli.saas_client import SaasClient, SaasClientError
from specify_cli.widen.audience import run_audience_review
from specify_cli.widen.models import WidenAction, WidenFlowResult, WidenResponse

class WidenFlow:
    def __init__(
        self,
        saas_client: SaasClient,
        repo_root: Path,
        console: Console,
    ) -> None:
        self._client = saas_client
        self._repo_root = repo_root
        self._console = console

    def run_widen_mode(
        self,
        decision_id: str,
        mission_id: str,
        mission_slug: str,
        question_text: str,
        actor: str,
    ) -> WidenFlowResult:
        """Orchestrate Widen Mode: audience review → POST widen → [b/c] prompt.

        Returns WidenFlowResult(action=CANCEL|BLOCK|CONTINUE).
        Never raises.
        """
        # Step 1: Audience review
        invited = run_audience_review(
            saas_client=self._client,
            mission_id=mission_id,
            question_text=question_text,
            console=self._console,
        )
        if invited is None:
            return WidenFlowResult(action=WidenAction.CANCEL)

        # Step 2: POST widen
        widen_response = self._post_widen(decision_id, invited)
        if widen_response is None:
            return WidenFlowResult(action=WidenAction.CANCEL)

        # Step 3: [b/c] prompt
        action = self._prompt_pause_semantics(question_text, widen_response)
        return WidenFlowResult(
            action=action,
            decision_id=decision_id,
            invited=invited,
        )
```

---

## Subtask T022 — Widen POST Call

**Purpose:** Call `SaasClient.post_widen()` and handle errors gracefully.

**Implementation:**
```python
def _post_widen(
    self, decision_id: str, invited: list[str]
) -> WidenResponse | None:
    """POST /api/v1/decision-points/{id}/widen. Returns WidenResponse or None on error."""
    try:
        return self._client.post_widen(decision_id, invited)
    except SaasClientError as exc:
        self._console.print(f"[red]Widen failed:[/red] {exc}")
        self._console.print("Returning to interview prompt.")
        return None
```

**On success:** The `WidenResponse` contains `decision_id`, `widened_at`, `slack_thread_url`, and `invited_count`. Pass it to the `[b/c]` prompt renderer (T025).

---

## Subtask T023 — `[b/c]` Pause-Semantics Prompt

**Purpose:** After successful widen, ask the owner whether to block the interview or continue with other questions.

**Implementation:**
```python
def _prompt_pause_semantics(
    self, question_text: str, response: WidenResponse
) -> WidenAction:
    """Render [b/c] prompt. Returns BLOCK or CONTINUE.

    Default is BLOCK (FR-007): pressing Enter → block.
    """
    raw = self._console.input(
        "Block here or continue with other questions? [bold][b/c][/bold] (default: b): "
    )
    choice = raw.strip().lower()
    if choice == "c":
        self._console.print(
            "Question parked as pending. You'll be prompted to resolve it at end of interview."
        )
        return WidenAction.CONTINUE
    # Any other input (Enter, "b", anything else) → BLOCK
    return WidenAction.BLOCK
```

**FR-007:** Default is `b` (block). Empty input → `BLOCK`.

---

## Subtask T024 — Return `WidenFlowResult`

**Purpose:** Ensure the caller (interview loop) always gets a fully populated `WidenFlowResult`.

All three code paths in `run_widen_mode()` return a `WidenFlowResult`:
- `CANCEL`: `decision_id=None, invited=None` (no SaaS call was made).
- `BLOCK`: `decision_id=<id>, invited=<list>` (widen POST succeeded; interview will enter blocked loop).
- `CONTINUE`: `decision_id=<id>, invited=<list>` (widen POST succeeded; caller writes `WidenPendingEntry`).

The caller pattern in `charter.py`:
```python
result = widen_flow.run_widen_mode(
    decision_id=current_decision_id,
    mission_id=mission_id,
    mission_slug=mission_slug,
    question_text=prompt_text,
    actor=actor,
)
if result.action == WidenAction.CANCEL:
    continue  # re-show question prompt
elif result.action == WidenAction.BLOCK:
    _enter_blocked_prompt_loop(result.decision_id, prompt_text, ...)
elif result.action == WidenAction.CONTINUE:
    store.add_pending(WidenPendingEntry(...))
    # advance to next question
```

---

## Subtask T025 — Render Success Panel with Slack Thread URL

**Purpose:** After successful widen POST, render the success panel (§3 contract) showing participants and Slack thread URL before the `[b/c]` prompt.

**Panel format** (from `contracts/cli-contracts.md §3`):
```
╭─ Widened ✓ ────────────────────────────────────────────────────────╮
│ Slack thread created. Alice Johnson and Carol Lee have been        │
│ invited to discuss: "<question text (truncated to 50 chars)>"      │
╰────────────────────────────────────────────────────────────────────╯
```

**Implementation:**
```python
def _render_widen_success(
    self,
    invited: list[str],
    question_text: str,
    response: WidenResponse,
) -> None:
    from rich.panel import Panel

    invited_str = " and ".join(invited) if len(invited) <= 2 else f"{', '.join(invited[:-1])}, and {invited[-1]}"
    q_short = question_text[:50]
    thread_line = f"\nThread: {response.slack_thread_url}" if response.slack_thread_url else ""
    self._console.print(Panel(
        f"Slack thread created. {invited_str} have been invited to discuss:\n"
        f'  "{q_short}"{thread_line}',
        title="Widened ✓",
    ))
```

Call `_render_widen_success()` after a successful `_post_widen()`, before `_prompt_pause_semantics()`.

---

## Definition of Done

- [ ] `WidenFlow.run_widen_mode()` always returns a `WidenFlowResult` (never raises).
- [ ] `CANCEL` path: no POST call, returns immediately.
- [ ] `BLOCK` path: POST succeeded, success Panel rendered, `[b/c]` prompt returned BLOCK.
- [ ] `CONTINUE` path: POST succeeded, success Panel rendered, `[b/c]` prompt returned CONTINUE.
- [ ] Default is BLOCK (Enter or empty input → BLOCK).
- [ ] `tests/specify_cli/widen/test_flow.py` — stubs present (full tests in WP10).
- [ ] `mypy src/specify_cli/widen/flow.py` exits 0.
- [ ] `ruff check src/specify_cli/widen/flow.py` exits 0.

## Risks

- **`console.input()`**: Rich's `Console.input()` may raise `EOFError` in non-interactive environments (CI, CliRunner). Wrap in try/except and default to BLOCK on EOFError.
- **Render-then-prompt ordering**: The success Panel must appear before the `[b/c]` prompt. Ensure `_render_widen_success()` is called before `_prompt_pause_semantics()`.

## Reviewer Guidance

Verify that pressing Enter (empty string) maps to BLOCK, not CONTINUE. Verify that the `invited` list passed to `WidenPendingEntry` is the trimmed list (as returned by `run_audience_review()`), not the full default. Verify the success panel shows the Slack thread URL when `response.slack_thread_url` is not None.

## Activity Log

- 2026-04-23T16:35:53Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=72958 – Started implementation via action command
- 2026-04-23T16:40:56Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=72958 – Ready for review: WidenFlow orchestrator implemented — audience review → POST widen → success panel → [b/c] prompt, all 3 decision branches covered, 31 tests pass
- 2026-04-23T16:41:49Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=73827 – Started review via action command
- 2026-04-23T16:44:42Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=73827 – Review passed: all 31 tests green (88 total, 2 skipped), ruff clean, mypy clean. CANCEL/BLOCK/CONTINUE branches fully covered. EOFError→BLOCK CI-safe. Success panel renders before [b/c] prompt (ordering test). SaasClientError hierarchy caught correctly. WidenFlowResult shape correct for all paths. No pending entry written on failure. Per-spec design: check_prereqs gates [w] display upstream; store.add_pending is caller responsibility. 3 sampled tests are substantive (ordering test, EOFError test, truncation test). Approved.
