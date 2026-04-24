---
work_package_id: WP06
title: Charter Integration
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP07
requirement_refs:
- C-001
- C-004
- C-007
- C-008
- C-009
- C-010
- C-011
- FR-001
- FR-007
- FR-008
- FR-009
- FR-018
- FR-019
- FR-020
- FR-021
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
- T032
agent: "claude:sonnet-4-7:python-reviewer:reviewer"
shell_pid: "77306"
history:
- date: '2026-04-23T15:43:52Z'
  event: created
agent_profile: python-implementer
authoritative_surface: src/specify_cli/cli/commands/charter.py
execution_mode: code_change
mission_slug: cli-widen-mode-and-write-back-01KPXFGJ
model: claude-sonnet-4-7
owned_files:
- src/specify_cli/cli/commands/charter.py
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

Extend `src/specify_cli/cli/commands/charter.py` `interview()` command with:
1. Prereq check at startup (construct `SaasClient`, call `check_prereqs()`).
2. `[w]iden` added to the per-question prompt when prereqs are satisfied and decision is not already widened/terminal.
3. `w` input detection and `WidenFlow.run_widen_mode()` dispatch.
4. Blocked-prompt loop (`Waiting >`) for the BLOCK path.
5. Plain-text local answer at blocked prompt → `decision.resolve(manual)`.
6. `[f]etch & review` at blocked prompt → enter candidate review.
7. `[d]efer` at blocked prompt → `decision.defer()`.

---

## Context

`charter.py` already has the full interview loop (lines 469–556). This WP adds widen capabilities while leaving the existing `[d]efer` / `!cancel` / plain-answer paths intact. All widen additions are non-fatal: a failure at any point returns to the original interview prompt behavior (C-007).

The blocked-prompt loop is the most complex addition. It is a `while True:` loop that exits on resolution (resolve, defer, or local answer). It must support the inactivity reminder at 60 minutes (NFR-004).

**Read `contracts/cli-contracts.md §1.2`, `§4`, and `§4.1`** before implementing.

---

## Branch Strategy

Depends on WP01–WP05 and WP07. Implementation command:
```bash
spec-kitty agent action implement WP06 --agent claude
```

---

## Subtask T026 — Prereq Check at Startup

**Purpose:** Construct `SaasClient` and call `check_prereqs()` once before the question loop. Cache `prereq_state` for the interview session.

**Location:** In `interview()`, before `for question_id in question_order:`.

```python
# Widen Mode prereq check (non-fatal)
prereq_state: PrereqState = _WIDEN_PREREQS_ABSENT  # fallback
widen_flow: WidenFlow | None = None
widen_store: WidenPendingStore | None = None

if mission_slug is not None:
    try:
        from specify_cli.saas_client import SaasClient
        from specify_cli.widen import check_prereqs, PrereqState
        from specify_cli.widen.flow import WidenFlow
        from specify_cli.widen.state import WidenPendingStore

        _saas_client = SaasClient.from_env()
        _auth = _saas_client._auth  # or load separately
        prereq_state = check_prereqs(_saas_client, team_slug=_auth.team_slug or "")
        if prereq_state.all_satisfied:
            widen_flow = WidenFlow(_saas_client, repo_root, console)
            widen_store = WidenPendingStore(repo_root, mission_slug)
    except Exception:
        pass  # non-fatal; prereq_state stays ABSENT

_WIDEN_PREREQS_ABSENT = PrereqState(teamspace_ok=False, slack_ok=False, saas_reachable=False)
```

**NFR-001:** Combined prereq check must add ≤300ms at p95. The three probes have 500ms timeouts each. In practice they run in sequence and should complete in ≤200ms on a local network. If needed, run with `concurrent.futures.ThreadPoolExecutor` to parallelize.

---

## Subtask T027 — Extend Per-Question Prompt with `[w]iden`

**Purpose:** Add `| [w]iden` to the prompt hint text when prereqs are satisfied and the decision is not already widened/terminal.

**Current prompt pattern** (from existing charter.py):
```python
user_answer = typer.prompt(prompt_text, default=default_value)
```

**Extended pattern:**
```python
# Build hint line
widen_suffix = ""
if (
    prereq_state.all_satisfied
    and widen_store is not None
    and current_decision_id is not None
    and not _is_already_widened(widen_store, current_decision_id)
):
    widen_suffix = " | [w]iden"

hint_line = f"[enter]=accept default | [text]=type answer{widen_suffix} | [d]efer | [!cancel]"
console.print(f"[dim]{hint_line}[/dim]")

user_answer = typer.prompt(prompt_text, default=default_value)
```

**`_is_already_widened(store, decision_id)`:**
```python
def _is_already_widened(store: WidenPendingStore, decision_id: str) -> bool:
    return any(e.decision_id == decision_id for e in store.list_pending())
```

**C-020 / C-010:** If the decision is already widened (in the pending store), suppress `[w]` and show the §1.3 prompt instead. The §1.3 prompt is handled in WP08/T045.

---

## Subtask T028 — Detect `w` Input + Call `WidenFlow.run_widen_mode()`

**Purpose:** Intercept `w` (case-insensitive) from `typer.prompt()` and enter Widen Mode.

**Pattern:**
```python
user_answer = typer.prompt(prompt_text, default=default_value)

if user_answer.strip().lower() == "w" and widen_flow is not None and current_decision_id is not None:
    result = widen_flow.run_widen_mode(
        decision_id=current_decision_id,
        mission_id=_get_mission_id(repo_root, mission_slug),
        mission_slug=mission_slug,
        question_text=prompt_text,
        actor=actor,
    )
    if result.action == WidenAction.CANCEL:
        # Re-show the prompt (loop back)
        continue  # or break inner loop and restart outer prompt
    elif result.action == WidenAction.BLOCK:
        _run_blocked_prompt_loop(
            decision_id=result.decision_id,
            question_text=prompt_text,
            invited=result.invited,
            ...
        )
        continue  # after resolution, advance to next question
    elif result.action == WidenAction.CONTINUE:
        from datetime import timezone, datetime
        widen_store.add_pending(WidenPendingEntry(
            decision_id=result.decision_id,
            mission_slug=mission_slug,
            question_id=f"charter.{question_id}",
            question_text=prompt_text,
            entered_pending_at=datetime.now(tz=timezone.utc),
            widen_endpoint_response={},  # or store result.widen_response.model_dump()
        ))
        answers_override[question_id] = ""  # leave blank; resolved at end-of-interview pass
        continue  # advance to next question
```

**Note on `_get_mission_id()`:** The SaaS widen endpoint requires the `mission_id` (ULID), not `mission_slug`. Read it from `kitty-specs/<slug>/meta.json` → `mission_id` field. Add a small helper.

---

## Subtask T029 — Implement Blocked-Prompt Loop

**Purpose:** The `while True:` loop the interview enters when `WidenAction.BLOCK` is returned. Renders the waiting Panel and loops on input.

**Function:**
```python
def _run_blocked_prompt_loop(
    decision_id: str,
    question_text: str,
    invited: list[str],
    mission_slug: str,
    repo_root: Path,
    console: Console,
    saas_client: SaasClient,
    dm_service: Any,
    actor: str,
) -> None:
    """Block until the widened question is resolved via one of:
    - [f]etch & review → run_candidate_review()
    - plain text answer → decision.resolve(manual)
    - [d]efer → decision.defer()
    """
    from rich.panel import Panel

    _render_waiting_panel(console, question_text, invited)

    # NFR-004: inactivity reminder at 60 minutes
    _schedule_inactivity_reminder(console)

    while True:
        try:
            raw = console.input("Waiting > ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Type d to defer or a local answer to resolve.[/dim]")
            continue

        cmd = raw.strip()

        if not cmd:
            continue  # blank line, show panel again
        elif cmd.lower() == "f":
            resolved = _fetch_and_review(decision_id, mission_slug, question_text, ...)
            if resolved:
                break
        elif cmd.lower() == "d":
            _defer_decision(decision_id, mission_slug, repo_root, dm_service, actor, console)
            break
        elif cmd.lower() == "!cancel":
            console.print("[dim]Interview canceled.[/dim]")
            raise typer.Exit()
        else:
            # Plain text → local answer (FR-018)
            _resolve_locally(decision_id, mission_slug, repo_root, cmd, dm_service, actor, console)
            break
```

**`_render_waiting_panel()`** (from `contracts/cli-contracts.md §4`):
```
╭─ Waiting for widened discussion ───────────────────────────────────╮
│ Question: <question_text>                                          │
│ Participants: Alice Johnson, Carol Lee                             │
│ Slack thread: https://...                                          │
╰────────────────────────────────────────────────────────────────────╯
Options:
  [f]etch & review   — fetch current discussion and produce candidate
  <type an answer>   — resolve locally right now (closes Slack thread)
  [d]efer            — defer this question for later
```

---

## Subtask T030 — Plain-Text Local Answer at Blocked Prompt

**Purpose:** When the owner types a non-command string at `Waiting >`, resolve the decision locally (FR-018).

```python
def _resolve_locally(
    decision_id: str,
    mission_slug: str,
    repo_root: Path,
    final_answer: str,
    dm_service: Any,
    actor: str,
    console: Console,
) -> None:
    """FR-018: resolve with source=manual, empty summary text."""
    import contextlib
    from specify_cli.decisions import service as _dm_service, DecisionError

    with contextlib.suppress(DecisionError):
        _dm_service.resolve_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=decision_id,
            final_answer=final_answer,
            summary_json={"source": "manual", "text": ""},
            actor=actor,
        )
    console.print("[green]Resolved locally.[/green] SaaS will close the Slack thread shortly.")
```

**FR-019:** This call is to `decision.resolve()` only. The CLI does NOT post to Slack (C-004). SaaS observes the terminal state and #111 handles Slack closure.

---

## Subtask T031 — `[f]etch & review` at Blocked Prompt

**Purpose:** Trigger `SaasClient.fetch_discussion()` and then `run_candidate_review()` from the blocked prompt.

```python
def _fetch_and_review(
    decision_id: str,
    mission_slug: str,
    question_text: str,
    repo_root: Path,
    saas_client: SaasClient,
    dm_service: Any,
    actor: str,
    console: Console,
) -> bool:
    """Fetch discussion + run candidate review. Returns True if resolved/deferred."""
    from specify_cli.widen.review import run_candidate_review
    from specify_cli.saas_client import SaasClientError

    console.print("Fetching discussion...")
    try:
        discussion_raw = saas_client.fetch_discussion(decision_id)
    except SaasClientError as exc:
        console.print(f"[yellow]Discussion fetch failed:[/yellow] {exc}")
        console.print("You can type a local answer or press d to defer.")
        return False

    # Convert raw discussion to DiscussionFetch model
    from specify_cli.widen.models import DiscussionFetch
    discussion = DiscussionFetch(**discussion_raw)  # or via Pydantic model_validate

    return run_candidate_review(
        discussion_data=discussion,
        decision_id=decision_id,
        question_text=question_text,
        mission_slug=mission_slug,
        repo_root=repo_root,
        console=console,
        dm_service=dm_service,
        actor=actor,
    ) is not None
```

---

## Subtask T032 — `[d]efer` at Blocked Prompt

**Purpose:** Defer the widened decision from the blocked prompt.

```python
def _defer_decision(
    decision_id: str,
    mission_slug: str,
    repo_root: Path,
    dm_service: Any,
    actor: str,
    console: Console,
) -> None:
    import contextlib
    from specify_cli.decisions import DecisionError

    try:
        rationale = console.input("Rationale for deferral (press Enter to skip): ").strip()
    except (KeyboardInterrupt, EOFError):
        rationale = ""

    with contextlib.suppress(DecisionError):
        dm_service.defer_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=decision_id,
            rationale=rationale or "deferred from blocked widen prompt",
            actor=actor,
        )
    console.print("[yellow]Decision deferred.[/yellow]")
```

**NFR-004 inactivity reminder implementation:**
```python
import threading

def _schedule_inactivity_reminder(console: Console, delay_seconds: int = 3600) -> threading.Timer:
    def _remind():
        console.print(
            "\n[yellow]Still waiting on widened discussion.[/yellow] "
            "Check Slack, type a local answer, or press d to defer.\n"
            "Waiting > ",
            end="",
        )
    timer = threading.Timer(delay_seconds, _remind)
    timer.daemon = True
    timer.start()
    return timer  # caller may cancel if needed
```

---

## Definition of Done

- [ ] `interview()` runs prereq check at startup (non-fatal, ≤300ms).
- [ ] `[w]iden` appears in prompt only when `prereq_state.all_satisfied` is True and decision is not already widened.
- [ ] `w` input → `WidenFlow.run_widen_mode()` → CANCEL/BLOCK/CONTINUE handled.
- [ ] CONTINUE path: `WidenPendingEntry` written to sidecar, question skipped.
- [ ] BLOCK path: blocked-prompt loop entered.
- [ ] Blocked loop: `f` → fetch+review; plain text → resolve(manual); `d` → defer.
- [ ] `[green]Resolved locally.[/green]` message shown on local answer.
- [ ] NFR-004: inactivity timer scheduled on blocked loop entry.
- [ ] `mypy src/specify_cli/cli/commands/charter.py` exits 0.
- [ ] `ruff check src/specify_cli/cli/commands/charter.py` exits 0.
- [ ] Existing charter tests in `tests/specify_cli/cli/commands/test_charter.py` still pass.

## Risks

- **Re-prompting on CANCEL:** After a widen cancel, the interview must re-show the same question. This requires a `while True:` inner loop around the question prompt, or a flag to re-run. Review the existing prompt loop structure carefully before adding the outer loop.
- **`mission_id` vs `mission_slug`:** SaaS endpoints require `mission_id` (ULID). Extract from `meta.json` before the question loop.
- **`typer.prompt()` and `w` detection:** `typer.prompt(default=default_value)` returns `default_value` on empty Enter. Handle `w` in the returned string, not as a default.

## Reviewer Guidance

Verify: with `SPEC_KITTY_SAAS_TOKEN` unset, `[w]iden` does NOT appear in any prompt. Verify: existing `test_charter.py` tests still pass. Verify: typing `w` when `prereq_state.all_satisfied=True` triggers Widen Mode. Verify NFR-004 timer is a daemon thread (won't block process exit).

## Activity Log

- 2026-04-23T16:45:39Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=74270 – Started implementation via action command
- 2026-04-23T17:00:20Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=74270 – Ready for review: charter [w]iden integration complete. All 19 tests pass (CANCEL/BLOCK/CONTINUE paths + regressions). Ruff clean. mypy errors are pre-existing (18 errors same before and after WP06).
- 2026-04-23T17:01:16Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=76012 – Started review via action command
- 2026-04-23T17:06:22Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=76012 – Moved to planned
- 2026-04-23T17:07:17Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=76725 – Started implementation via action command
- 2026-04-23T17:10:18Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=76725 – Cycle 2: verified mypy baseline — follow_imports=skip in pyproject.toml means attr-defined error does not fire in this environment; original code at 51278bb4 already achieves 18-error baseline. No code change required. All 27 charter tests and 88 widen tests pass. Ruff clean.
- 2026-04-23T17:11:09Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=77306 – Started review via action command
- 2026-04-23T17:13:16Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=77306 – Review passed (cycle 2): Cycle-1 reviewer mypy count was inconsistent with actual mypy state. Cycle-2 verified no regression. Baseline pre-WP06 (3d22f676) = 18 charter.py errors; post-WP06 HEAD = 18 errors. follow_imports=skip suppresses attr-defined. All 26 charter tests pass, 88 widen tests pass, ruff clean, CANCEL/BLOCK/CONTINUE paths correct, add_pending on CONTINUE only, daemon inactivity timer confirmed.
