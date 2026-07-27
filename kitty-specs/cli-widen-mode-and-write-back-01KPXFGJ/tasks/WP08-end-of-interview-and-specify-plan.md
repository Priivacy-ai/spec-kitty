---
work_package_id: WP08
title: End-of-Interview Pending Pass + Specify/Plan Integration
dependencies:
- WP06
- WP07
- WP05
requirement_refs:
- C-008
- FR-002
- FR-010
- FR-011
- FR-020
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
- T043
- T044
- T045
agent: "claude:sonnet-4-7:python-reviewer:reviewer"
shell_pid: "81639"
history:
- date: '2026-04-23T15:43:52Z'
  event: created
agent_profile: python-implementer
authoritative_surface: src/specify_cli/missions/plan/
execution_mode: code_change
mission_slug: cli-widen-mode-and-write-back-01KPXFGJ
model: claude-sonnet-4-7
owned_files:
- src/specify_cli/cli/commands/research.py
- src/specify_cli/missions/plan/plan_interview.py
- src/specify_cli/missions/plan/specify_interview.py
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

This WP has three concerns:

1. **End-of-interview pending pass** (FR-010): After the charter question loop, surface any `pending-external-input` questions from `WidenPendingStore` and resolve them via `run_candidate_review()`.
2. **Specify + Plan integration** (FR-002): Apply the same `[w]` affordance + `WidenFlow` to the `specify` and `plan` interview flows.
3. **Already-widened question prompt** (FR-020, §1.3 contract): When a question is already in `widen-pending.jsonl`, show `[f]etch & resolve | [local answer] | [d]efer` instead of the standard prompt.

---

## Context

Before implementing, locate the specify and plan interview command entry points:
```bash
find src/specify_cli -name "*.py" | xargs grep -l "interview\|Interview" | grep -v __pycache__
```

The plan.md §2 (Module Structure) refers to `specify` and `plan` interview flows. Determine the actual file locations first, then apply the same pattern established in WP06 (charter integration). The `origin_flow` passed to `_dm_service.open_decision()` should be `SPECIFY` or `PLAN` respectively.

**Update the `owned_files` list above** if the actual specify/plan interview files differ from the stubs listed.

---

## Branch Strategy

Depends on WP05, WP06, WP07. Implementation command:
```bash
spec-kitty agent action implement WP08 --agent claude
```

---

## Subtask T040 — End-of-Interview Pending Pass in Charter `interview()`

**Purpose:** After all questions are answered and before writing `answers.yaml`, check `WidenPendingStore.list_pending()`. If non-empty, surface the pending questions for resolution.

**Location:** In `charter.py` `interview()`, after the question loop and before the paradigms/directives prompts (or after, depending on flow).

**Panel format** (from `contracts/cli-contracts.md §7`):
```
╭─ Pending Widened Questions ────────────────────────────────────────╮
│ 3 widened questions are still pending. Resolve them before        │
│ finalizing the interview.                                          │
╰────────────────────────────────────────────────────────────────────╯
(1/3) Question: <question text>
      Widened at: 2026-04-23 16:00 UTC
      Participants: Alice Johnson, Carol Lee
      Fetching discussion...
```

**Implementation:**
```python
# After the question loop, before writing answers:
if widen_store is not None:
    pending = widen_store.list_pending()
    if pending:
        from rich.panel import Panel
        console.print(Panel(
            f"{len(pending)} widened question{'s are' if len(pending) != 1 else ' is'} still pending. "
            "Resolve them before finalizing the interview.",
            title="Pending Widened Questions",
        ))
        for idx, entry in enumerate(pending, start=1):
            console.print(f"({idx}/{len(pending)}) Question: {entry.question_text}")
            _resolve_pending_entry(entry, widen_store, saas_client, ...)
```

---

## Subtask T041 — Resolve Each Pending Entry (Fetch + Review)

**Purpose:** For each pending entry: fetch discussion from SaaS, run `run_candidate_review()`, then remove from store.

```python
def _resolve_pending_entry(
    entry: WidenPendingEntry,
    store: WidenPendingStore,
    saas_client: SaasClient,
    mission_slug: str,
    repo_root: Path,
    console: Console,
    dm_service: Any,
    actor: str,
) -> None:
    """Fetch + review one pending entry. Remove from store after any terminal action."""
    from specify_cli.widen.review import run_candidate_review
    from specify_cli.widen.models import DiscussionFetch
    from specify_cli.saas_client import SaasClientError

    console.print(f"      Widened at: {entry.entered_pending_at.strftime('%Y-%m-%d %H:%M UTC')}")

    # Fetch discussion
    try:
        console.print("      Fetching discussion...")
        raw = saas_client.fetch_discussion(entry.decision_id)
        discussion = DiscussionFetch.model_validate(raw)
    except SaasClientError as exc:
        console.print(f"      [yellow]Fetch failed:[/yellow] {exc}. You can still type an answer manually.")
        discussion = DiscussionFetch(participants=[], message_count=0, thread_url=None, messages=[], truncated=False)

    # Run candidate review (always — even on fetch failure, fallback mode)
    result = run_candidate_review(
        discussion_data=discussion,
        decision_id=entry.decision_id,
        question_text=entry.question_text,
        mission_slug=mission_slug,
        repo_root=repo_root,
        console=console,
        dm_service=dm_service,
        actor=actor,
    )

    # Remove from store after any action (accept, edit, defer — all are terminal)
    store.remove_pending(entry.decision_id)
```

---

## Subtask T042 — Remove Resolved Entries from Store

**Purpose:** After each pending entry is resolved or deferred, call `store.remove_pending(entry.decision_id)`.

This is already embedded in T041. The separate subtask ensures the behavior is explicitly tested: after the end-of-interview pass, `widen_store.list_pending()` must return `[]` for all handled entries.

**Edge case:** If `run_candidate_review()` raises an unexpected exception (not DecisionError), still remove the entry from the store to avoid infinite pending loops. Use:
```python
try:
    result = run_candidate_review(...)
finally:
    store.remove_pending(entry.decision_id)
```

This ensures the interview always makes progress, even on unexpected failures.

---

## Subtask T043 — Extend `specify` Interview Flow with `[w]` Affordance

**Purpose:** Apply the same pattern from WP06 (charter integration) to the `specify` interview flow.

**Steps:**
1. Locate the specify interview command file (search `src/specify_cli` for the specify interview entry point).
2. Add `SaasClient.from_env()` + `check_prereqs()` at startup (same non-fatal pattern as WP06 T026).
3. Extend the per-question prompt to include `| [w]iden` when `prereq_state.all_satisfied`.
4. Detect `w` input → `WidenFlow.run_widen_mode()` with `origin_flow=SPECIFY`.
5. Add blocked-prompt loop (reuse `_run_blocked_prompt_loop()` helper extracted from charter.py).
6. Add end-of-interview pending pass.

**Reuse pattern:** Extract the shared logic (`_run_blocked_prompt_loop`, `_resolve_pending_entry`, `_fetch_and_review`) from charter.py into `src/specify_cli/widen/interview_helpers.py` (new file — add to owned_files if needed). Then import from both charter.py and specify/plan flows.

**`origin_flow` value:** Use `_DmOriginFlow.SPECIFY` (from `decisions/service.py`; verify the exact enum value).

---

## Subtask T044 — Extend `plan` Interview Flow with `[w]` Affordance

**Purpose:** Same as T043 but for the `plan` interview flow.

Apply the same pattern. `origin_flow=_DmOriginFlow.PLAN`.

**Parallelizable with T043:** T043 and T044 can be implemented in the same commit batch or in parallel since they touch different files. The shared helpers from T043 are reused.

---

## Subtask T045 — Already-Widened Question Prompt (`[f]etch & resolve`)

**Purpose:** When the interview reaches a question whose `decision_id` is already in `widen-pending.jsonl`, show the §1.3 already-widened prompt instead of the standard prompt.

**Already-widened prompt** (from `contracts/cli-contracts.md §1.3`):
```
<question text> [pending-external-input]
[f]etch & resolve | [local answer]=type answer | [d]efer | [!cancel]
```

**Detection:** Before rendering the standard prompt for a question, check:
```python
if widen_store is not None and _is_already_widened(widen_store, current_decision_id):
    _render_already_widened_prompt(question_text, current_decision_id, ...)
    continue
```

**`_render_already_widened_prompt()`:**
```python
def _render_already_widened_prompt(
    question_text: str,
    decision_id: str,
    mission_slug: str,
    repo_root: Path,
    saas_client: SaasClient,
    widen_store: WidenPendingStore,
    dm_service: Any,
    actor: str,
    console: Console,
) -> None:
    console.print(f"{question_text} [dim][pending-external-input][/dim]")
    hint = "[f]etch & resolve | [local answer]=type answer | [d]efer | [!cancel]"
    console.print(f"[dim]{hint}[/dim]")

    raw = console.input("").strip()
    if raw.lower() == "f":
        _fetch_and_review(decision_id, mission_slug, question_text, ...)
        widen_store.remove_pending(decision_id)
    elif raw.lower() in ("d", "[d]efer"):
        _defer_decision(decision_id, mission_slug, repo_root, dm_service, actor, console)
        widen_store.remove_pending(decision_id)
    elif raw.lower() == "!cancel":
        raise typer.Exit()
    elif raw:
        _resolve_locally(decision_id, mission_slug, repo_root, raw, dm_service, actor, console)
        widen_store.remove_pending(decision_id)
```

---

## Definition of Done

- [ ] End-of-interview pending pass in charter `interview()` — renders §7 Panel and resolves each pending entry.
- [ ] After pass, `widen_store.list_pending()` returns `[]` for handled entries.
- [ ] `specify` interview flow has `[w]` affordance + WidenFlow + blocked-prompt loop.
- [ ] `plan` interview flow has `[w]` affordance + WidenFlow + blocked-prompt loop.
- [ ] Already-widened question prompt (§1.3) shown for questions already in `widen-pending.jsonl`.
- [ ] Shared helpers extracted and importable from both charter and specify/plan.
- [ ] `tests/specify_cli/cli/commands/test_end_of_interview_pending_pass.py` — at least 2 test cases.
- [ ] Existing tests for specify and plan flows still pass.
- [ ] `mypy` and `ruff` clean on all touched files.

## Risks

- **Specify/plan interview file locations unknown:** Investigate before coding. If these flows are significantly different from charter's interview loop, the integration may require more effort than estimated.
- **Shared helper extraction:** If `_run_blocked_prompt_loop()` references charter-specific state (like `answers_override`), it may need refactoring to be generically importable.

## Reviewer Guidance

Verify: SC-008: charter, specify, and plan show the same `[w]` affordance, same Widen Mode UX, same review/write-back. Verify: after the end-of-interview pass with 3 pending entries, all 3 are removed from the sidecar file. Verify: the already-widened prompt does not show `[w]iden` again (C-010).

## Activity Log

- 2026-04-23T17:32:55Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=80092 – Started implementation via action command
- 2026-04-23T17:45:59Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=80092 – Ready for review: end-of-interview pending pass + specify/plan widen integration + already-widened prompt (T040-T045)
- 2026-04-23T17:46:54Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=81639 – Started review via action command
- 2026-04-23T18:19:43Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=81639 – Review passed: T040-T045 all implemented correctly. end-of-interview pending pass (run_end_of_interview_pending_pass) is silent no-op on empty store, renders §7 Panel when non-empty, iterates via list_pending. T042 always-progress rule verified via try/except/finally. specify/plan integration (T043/T044) fully implemented with correct OriginFlow enums, shared helpers, blocked-prompt loop reuse from charter (lazy import, no circular dependency). Already-widened prompt (T045) matches §1.3 contract with f/d/local-answer/!cancel paths all tested. Charter CONTINUE test patch is a correct isolation fix. Ruff clean, mypy clean (11 source files). 19/19 WP08 tests pass, 38/38 combined WP08+WP06 tests pass, 174 passed/2 skipped in full widen+WP08 suite.
