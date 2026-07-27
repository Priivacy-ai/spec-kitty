---
work_package_id: WP04
title: Audience Review UX
dependencies:
- WP01
- WP02
requirement_refs:
- C-008
- C-009
- FR-004
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
agent: "claude:sonnet-4-7:python-reviewer:reviewer"
shell_pid: "72388"
history:
- date: '2026-04-23T15:43:52Z'
  event: created
agent_profile: python-implementer
authoritative_surface: src/specify_cli/widen/audience.py
execution_mode: code_change
mission_slug: cli-widen-mode-and-write-back-01KPXFGJ
model: claude-sonnet-4-7
owned_files:
- src/specify_cli/widen/audience.py
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

Implement `run_audience_review()` in `src/specify_cli/widen/audience.py` — the inline UX for presenting the default audience to the mission owner, accepting trim input, confirming the invite list, and returning the confirmed list (or `None` on cancel).

This function is called by `WidenFlow.run_widen_mode()` (WP05) immediately after the user presses `w`.

---

## Context

The audience review UX must follow the exact prompt formats in `contracts/cli-contracts.md §2`. Key behaviors:
- Fetch default audience from SaaS `GET /api/v1/missions/{id}/audience-default`.
- Render audience list in a `rich.Panel`.
- Accept: `[Enter]` (use full list), CSV trim, or `cancel`.
- Cancel paths: typed `"cancel"` (case-insensitive) or `Ctrl+C` (KeyboardInterrupt).
- On SaaS fetch error: surface `[red]Widen failed[/red]` and return `None`.

---

## Branch Strategy

Depends on WP01 + WP02. Implementation command:
```bash
spec-kitty agent action implement WP04 --agent claude
```

---

## Subtask T016 — `run_audience_review()` Core + Audience Fetch + Panel Render

**Purpose:** Fetch default audience from SaaS and render the audience review Panel to the console.

**File:** `src/specify_cli/widen/audience.py`

**Function signature:**
```python
from __future__ import annotations
from rich.console import Console
from specify_cli.saas_client import SaasClient, SaasClientError

def run_audience_review(
    saas_client: SaasClient,
    mission_id: str,
    question_text: str,
    console: Console,
) -> list[str] | None:
    """Fetch default audience, render review Panel, accept trim input.

    Returns trimmed list on confirm, None on cancel (FR-006).
    """
```

**Panel format** (from `contracts/cli-contracts.md §2.1`):
```
╭─ Widen: <question_text truncated to 60 chars> ──────────────────╮
│ Default audience for this decision:                              │
│   Alice Johnson, Bob Smith, Carol Lee, Dana Park                 │
│                                                                  │
│ [Enter] to confirm, or type comma-separated names to trim.      │
│ Type "cancel" or press Ctrl+C to abort.                          │
╰──────────────────────────────────────────────────────────────────╯
```

Use `rich.panel.Panel` with `title=f"Widen: {question_text[:60]}"`. Render names joined with `, `.

**Audience fetch:**
```python
try:
    default_audience = saas_client.get_audience_default(mission_id)
except SaasClientError as exc:
    console.print(f"[red]Widen failed:[/red] {exc}")
    return None
```

If `default_audience` is empty: render `"No default audience configured for this mission."` and return `None` (can't widen with nobody).

---

## Subtask T017 — Trim-Input Parsing

**Purpose:** Parse the `Audience >` prompt input and return the final invite list.

**Implementation:**
```python
def _parse_audience_input(raw: str, default_audience: list[str]) -> list[str]:
    """Parse audience trim input.

    - Empty string → return default_audience unchanged.
    - Comma-separated names → return subset (case-insensitive match from default_audience).
    - Unknown names → include in list with a warning (owners may know team members not in default).
    Returns list of display names.
    """
    raw = raw.strip()
    if not raw:
        return list(default_audience)

    names = [n.strip() for n in raw.split(",") if n.strip()]
    lower_map = {name.lower(): name for name in default_audience}
    result = []
    unknown = []
    for name in names:
        if name.lower() in lower_map:
            result.append(lower_map[name.lower()])
        else:
            result.append(name)  # unknown name — include as-is
            unknown.append(name)
    return result

# In run_audience_review(), after rendering Panel:
def _warn_unknown(unknown: list[str], console: Console) -> None:
    if unknown:
        console.print(f"[yellow]Note:[/yellow] {', '.join(unknown)} not in default audience — including anyway.")
```

**Edge case:** Empty trim result (user types only commas or spaces) → treat as empty → use full default list.

---

## Subtask T018 — Cancel Path

**Purpose:** Handle the two cancel mechanisms: typed `"cancel"` and `Ctrl+C` (KeyboardInterrupt).

```python
def _prompt_audience(console: Console) -> str | None:
    """Prompt for audience input. Returns raw string, or None on cancel."""
    try:
        raw = console.input("[bold]Audience >[/bold] ")
        if raw.strip().lower() == "cancel":
            return None
        return raw
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Widen canceled.[/dim]")
        return None
```

When `_prompt_audience()` returns `None`, `run_audience_review()` returns `None` immediately (no widen call made). The interview loop interprets `None` as `WidenAction.CANCEL` and shows the original prompt unchanged (FR-006).

---

## Subtask T019 — Confirmation Display

**Purpose:** Render the audience confirmation and "Calling widen endpoint..." message before returning the confirmed list.

```python
# In run_audience_review(), after parsing audience:
console.print(f"Audience confirmed: {', '.join(trimmed)} ({len(trimmed)} members)")
console.print("Calling widen endpoint...")
```

This text appears before the flow returns the list to `WidenFlow`, which then calls `saas_client.post_widen()`. The "Calling..." message sets owner expectation.

**Timing:** The confirmation + message is printed before returning the list. The actual POST call happens in `WidenFlow.run_widen_mode()` (WP05), not in `run_audience_review()`.

---

## Subtask T020 — Error Handling on SaaS Failure

**Purpose:** Handle errors during audience fetch; render user-friendly error; return `None`.

**Error scenarios:**
1. `get_audience_default()` raises `SaasTimeoutError` → `"[red]Widen failed:[/red] SaaS request timed out. Try again."`
2. `get_audience_default()` raises `SaasAuthError` → `"[red]Widen failed:[/red] Authentication error. Check your SaaS token."`
3. Any other `SaasClientError` → `"[red]Widen failed:[/red] {str(exc)}"`
4. All cases return `None` → caller treats as cancel.

```python
except SaasTimeoutError:
    console.print("[red]Widen failed:[/red] SaaS request timed out.")
    return None
except SaasAuthError:
    console.print("[red]Widen failed:[/red] Authentication error — check SPEC_KITTY_SAAS_TOKEN.")
    return None
except SaasClientError as exc:
    console.print(f"[red]Widen failed:[/red] {exc}")
    return None
```

**Matches §2.3 contract:** On error, print `[red]Widen failed:[/red] <msg>` and `Returning to interview prompt.` (add the latter line too).

---

## Definition of Done

- [ ] `run_audience_review(saas_client, mission_id, question_text, console) -> list[str] | None` implemented.
- [ ] Panel renders per §2.1 contract (title truncated to 60 chars, audience list, instructions).
- [ ] Empty input → full default list returned.
- [ ] CSV input → subset list with unknown-name warning.
- [ ] `"cancel"` (case-insensitive) → `None` returned.
- [ ] `Ctrl+C` (KeyboardInterrupt) → `None` returned.
- [ ] SaaS error → `[red]Widen failed:[/red]` + `None` returned.
- [ ] `tests/specify_cli/widen/test_audience.py` — trim parsing + cancel path tests.
- [ ] `mypy src/specify_cli/widen/audience.py` exits 0.
- [ ] `ruff check src/specify_cli/widen/audience.py` exits 0.

## Risks

- **`rich.Console.input()`** may not exist in all Rich versions. Use `input()` with a `console.print()` for the prompt if needed, or wrap in a `Prompt.ask()` call (which handles Ctrl+C). Test with the version pinned in `pyproject.toml`.

## Reviewer Guidance

Verify the Panel title is truncated at 60 chars. Verify the test covers: empty input, CSV with all known names, CSV with unknown names, `cancel` keyword, Ctrl+C, and SaaS timeout error.

## Activity Log

- 2026-04-23T16:28:31Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=71893 – Started implementation via action command
- 2026-04-23T16:31:19Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=71893 – Ready for review: run_audience_review() implemented with Panel render, CSV trim, cancel paths, typed error handling, 29 tests all passing
- 2026-04-23T16:32:08Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=72388 – Started review via action command
- 2026-04-23T16:34:55Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=72388 – Review passed: all 29 audience tests pass (57 total non-skipped in widen/), ruff clean, mypy clean. Error dispatch correct for all 3 SaasError subclasses with distinct messages + 'Returning to interview prompt.' on each. Panel title uses [:60] slice. Cancel semantics cover typed 'cancel' (case-insensitive), KeyboardInterrupt, EOFError — all return None with user-visible message. CSV trim parsing handles all cases (all-known, partial, all-unknown, empty). Return shape (None for cancel/error) is by design and consistent with WP05 spec. Owner exclusion deferred to SaaS layer per contract.
