---
work_package_id: WP07
title: Candidate Review UX + LLM Prompt Contract
dependencies:
- WP01
- WP02
requirement_refs:
- C-002
- C-005
- C-006
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
- T038
- T039
agent: "claude:sonnet-4-7:python-reviewer:reviewer"
shell_pid: "79598"
history:
- date: '2026-04-23T15:43:52Z'
  event: created
agent_profile: python-implementer
authoritative_surface: src/specify_cli/widen/review.py
execution_mode: code_change
mission_slug: cli-widen-mode-and-write-back-01KPXFGJ
model: claude-sonnet-4-7
owned_files:
- src/specify_cli/widen/review.py
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

Implement `run_candidate_review()` in `src/specify_cli/widen/review.py`. This function:
1. Emits the structured LLM summarization request block to stdout (the active harness LLM reads it).
2. Reads the LLM's JSON response from stdin (with 30s timeout).
3. Parses the JSON response into a `CandidateReview` model.
4. Renders the candidate summary + answer in a `rich.Panel`.
5. Handles `[a]ccept`, `[e]dit`, and `[d]efer` with full provenance tagging.
6. Falls back to raw discussion display + blank editor on LLM timeout or parse failure.

---

## Context

**Read `contracts/cli-contracts.md §5` and `§6` before implementing.** These sections define the exact instruction block format and the `[a/e/d]` review prompt format. Tests must assert exact contract compliance.

**Prompt-contract model (R-7):** The CLI is a subprocess of the active LLM session (Claude Code, Codex, etc.). When the CLI prints the instruction block to stdout, the LLM session reads it as tool output and responds. The CLI reads the response from stdin. This is NOT an API call — it is the natural input/output channel of the CLI's harness.

---

## Branch Strategy

Depends on WP01, WP02 (does not depend on WP06). Can be developed in parallel with WP06 after WP02 is done.
```bash
spec-kitty agent action implement WP07 --agent claude
```

---

## Subtask T033 — Emit LLM Summarization Request Instruction Block

**Purpose:** Print the structured WIDEN SUMMARIZATION REQUEST block to stdout that the LLM session interprets as a task.

**File:** `src/specify_cli/widen/review.py`

**Format** (from `contracts/cli-contracts.md §5.1`):
```
╔══════════════════════════════════════════════════════════════════╗
║  WIDEN SUMMARIZATION REQUEST                                     ║
║  decision_id: <ulid>                                             ║
║  question: <full question text>                                  ║
╚══════════════════════════════════════════════════════════════════╝

[DISCUSSION DATA]
Participants: Alice Johnson, Carol Lee
Message count: 7
Thread URL: https://slack.com/archives/...

--- Messages ---
[Alice Johnson] We should definitely go with PostgreSQL for this.
...
---

Based on the discussion above, please produce a candidate summary and answer.
Respond with ONLY the following JSON block (no prose before or after):

```json
{
  "candidate_summary": "<concise summary of the discussion consensus>",
  "candidate_answer": "<proposed answer to the question above>",
  "source_hint": "slack_extraction"
}
```
```

**Implementation:**
```python
def _emit_summarization_request(
    decision_id: str,
    question_text: str,
    discussion: DiscussionFetch,
    console: Console,
) -> None:
    lines = [
        "╔══════════════════════════════════════════════════════════════════╗",
        "║  WIDEN SUMMARIZATION REQUEST                                     ║",
        f"║  decision_id: {decision_id:<48}║",
        f"║  question: {question_text[:52]:<54}║",
        "╚══════════════════════════════════════════════════════════════════╝",
        "",
        "[DISCUSSION DATA]",
        f"Participants: {', '.join(discussion.participants)}",
        f"Message count: {discussion.message_count}",
        f"Thread URL: {discussion.thread_url or 'unavailable'}",
        "",
        "--- Messages ---",
    ]
    for msg in discussion.messages[:50]:
        lines.append(msg)
    if discussion.truncated:
        lines.append(f"... ({discussion.message_count - 50} more messages truncated)")
    lines += [
        "---",
        "",
        "Based on the discussion above, please produce a candidate summary and answer.",
        'Respond with ONLY the following JSON block (no prose before or after):',
        "",
        "```json",
        "{",
        '  "candidate_summary": "<concise summary of the discussion consensus>",',
        '  "candidate_answer": "<proposed answer to the question above>",',
        '  "source_hint": "slack_extraction"',
        "}",
        "```",
    ]
    for line in lines:
        console.print(line)
```

---

## Subtask T034 — Read + Parse LLM JSON Response (with Timeout)

**Purpose:** Block on stdin for up to 30s waiting for the LLM to produce the JSON block. On timeout or parse failure, fall back.

**Implementation:**
```python
import json
import re
import threading

def _read_llm_response(timeout: float = 30.0) -> dict | None:
    """Read LLM JSON response from stdin within timeout seconds.

    Returns parsed dict or None on timeout/parse failure.
    """
    result: list[str | None] = [None]
    error: list[Exception | None] = [None]

    def _read():
        try:
            raw = input()  # reads one line from stdin
            result[0] = raw
        except Exception as exc:
            error[0] = exc

    thread = threading.Thread(target=_read, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if result[0] is None:
        return None  # timeout or error

    raw = result[0].strip()
    # Extract JSON object from response (LLM may include surrounding text)
    match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None
```

**Timeout constant:** `SUMMARIZE_TIMEOUT = float(os.environ.get("SPEC_KITTY_WIDEN_SUMMARIZE_TIMEOUT", "30"))`

**Parse into `CandidateReview`:**
```python
from specify_cli.widen.models import CandidateReview, DiscussionFetch, SummarySource

def _parse_candidate(raw: dict, decision_id: str, discussion: DiscussionFetch) -> CandidateReview:
    return CandidateReview(
        decision_id=decision_id,
        discussion_fetch=discussion,
        candidate_summary=raw.get("candidate_summary", ""),
        candidate_answer=raw.get("candidate_answer", ""),
        source_hint=SummarySource(raw.get("source_hint", "slack_extraction")),
        llm_timed_out=False,
    )
```

**Fallback (timeout or parse failure):** Return `CandidateReview(..., candidate_summary="", candidate_answer="", llm_timed_out=True, source_hint=SummarySource.MANUAL)`.

---

## Subtask T035 — `run_candidate_review()` Function + Candidate Panel

**Purpose:** The main entry point. Emits instruction block, reads response, renders candidate Panel.

**Signature:**
```python
from specify_cli.widen.models import CandidateReview, DiscussionFetch
from specify_cli.decisions import service as dm_service_module

def run_candidate_review(
    discussion_data: DiscussionFetch,
    decision_id: str,
    question_text: str,
    mission_slug: str,
    repo_root: Path,
    console: Console,
    dm_service: Any,
    actor: str,
) -> CandidateReview | None:
    """Full candidate review flow. Returns CandidateReview on resolve/defer, None on cancel."""
```

**Panel format** (from `contracts/cli-contracts.md §6`):
```
╭─ Candidate Review ─────────────────────────────────────────────────╮
│ Question: <question text>                                          │
│                                                                    │
│ Summary:                                                           │
│   <candidate_summary>                                              │
│                                                                    │
│ Proposed answer:                                                   │
│   <candidate_answer>                                               │
╰────────────────────────────────────────────────────────────────────╯
[a]ccept | [e]dit | [d]efer:
```

**On LLM timeout** (`llm_timed_out=True`), render fallback message from §5.3:
```
[yellow]Summarization timed out or produced invalid output.[/yellow]
Showing raw discussion. Please write the answer manually.
[a]ccept empty | [e]dit (blank pre-fill) | [d]efer
```

---

## Subtask T036 — `[a]ccept` Path

**Purpose:** Accept the candidate answer as-is. Call `decision.resolve()` with `source=slack_extraction`.

```python
def _handle_accept(
    candidate: CandidateReview,
    mission_slug: str,
    repo_root: Path,
    dm_service: Any,
    actor: str,
    console: Console,
) -> None:
    import contextlib
    from specify_cli.decisions import DecisionError

    with contextlib.suppress(DecisionError):
        dm_service.resolve_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=candidate.decision_id,
            final_answer=candidate.candidate_answer,
            summary_json={
                "text": candidate.candidate_summary,
                "source": SummarySource.SLACK_EXTRACTION,
            },
            actor=actor,
        )
    console.print("[green]Decision resolved.[/green]")
```

**No rationale prompt** (C-006: rationale stays owner-authored; accept path never auto-populates it).

---

## Subtask T037 — `[e]dit` Path + Material-Edit Detection

**Purpose:** Open `$EDITOR` pre-filled with candidate answer. Detect material change to assign correct provenance. Optionally prompt for rationale if materially changed.

```python
import click

def _handle_edit(
    candidate: CandidateReview,
    mission_slug: str,
    repo_root: Path,
    dm_service: Any,
    actor: str,
    console: Console,
) -> None:
    edited = click.edit(text=candidate.candidate_answer) or ""
    edited = edited.strip()

    source = _determine_source(candidate.candidate_answer, edited)

    rationale: str | None = None
    if source in (SummarySource.MISSION_OWNER_OVERRIDE, SummarySource.MANUAL):
        try:
            rationale = console.input("Optional rationale (press Enter to skip): ").strip() or None
        except (KeyboardInterrupt, EOFError):
            rationale = None

    import contextlib
    from specify_cli.decisions import DecisionError

    with contextlib.suppress(DecisionError):
        dm_service.resolve_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=candidate.decision_id,
            final_answer=edited or candidate.candidate_answer,
            summary_json={"text": candidate.candidate_summary, "source": source},
            rationale=rationale,
            actor=actor,
        )
    console.print("[green]Decision resolved.[/green]")
```

---

## Subtask T038 — `[d]efer` Path

**Purpose:** Defer the decision with a required rationale.

```python
def _handle_defer(
    candidate: CandidateReview,
    mission_slug: str,
    repo_root: Path,
    dm_service: Any,
    actor: str,
    console: Console,
) -> None:
    try:
        rationale = console.input("Rationale for deferral (required): ").strip()
    except (KeyboardInterrupt, EOFError):
        rationale = "deferred during candidate review"

    import contextlib
    from specify_cli.decisions import DecisionError

    with contextlib.suppress(DecisionError):
        dm_service.defer_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=candidate.decision_id,
            rationale=rationale or "deferred during candidate review",
            actor=actor,
        )
    console.print("[yellow]Decision deferred.[/yellow]")
```

---

## Subtask T039 — Provenance Assignment Logic

**Purpose:** Determine the correct `SummarySource` value based on how the owner changed the candidate answer.

```python
def _determine_source(candidate_answer: str, edited_answer: str) -> SummarySource:
    """Assign SummarySource based on edit distance and content.

    Rules from data-model.md §4:
    - Empty candidate + non-empty edit → MANUAL (wrote from scratch)
    - Edit is empty or blank → MANUAL (deleted everything)
    - Normalized edit distance > 30% of candidate length → MISSION_OWNER_OVERRIDE
    - Otherwise → SLACK_EXTRACTION (minor/no change)
    """
    if not candidate_answer.strip():
        return SummarySource.MANUAL  # no candidate to compare against
    if not edited_answer.strip():
        return SummarySource.MANUAL  # owner deleted everything

    # Levenshtein distance (stdlib difflib as approximation)
    import difflib
    ratio = difflib.SequenceMatcher(None, candidate_answer, edited_answer).ratio()
    # ratio=1.0 means identical; ratio=0.0 means completely different
    edit_distance_fraction = 1.0 - ratio
    if edit_distance_fraction > 0.30:
        return SummarySource.MISSION_OWNER_OVERRIDE
    return SummarySource.SLACK_EXTRACTION
```

**Threshold:** 30% normalized edit distance (data-model.md §4). Uses `difflib.SequenceMatcher` as a stdlib approximation to Levenshtein. The threshold may be tuned in a follow-up.

---

## Definition of Done

- [ ] `run_candidate_review()` function with correct signature in `review.py`.
- [ ] Instruction block emitted to stdout follows §5.1 format exactly.
- [ ] 30s timeout (`SPEC_KITTY_WIDEN_SUMMARIZE_TIMEOUT` env var respected).
- [ ] Fallback on timeout: blank candidate, `llm_timed_out=True`, §5.3 message rendered.
- [ ] Candidate Panel rendered per §6.
- [ ] `[a]` → `decision.resolve(slack_extraction)`, no rationale prompt.
- [ ] `[e]` → `click.edit()` pre-filled, `_determine_source()` called, optional rationale.
- [ ] `[d]` → `decision.defer()` with required rationale prompt.
- [ ] `_determine_source()` returns MANUAL on empty/blank edit, OVERRIDE on >30% edit distance, SLACK_EXTRACTION otherwise.
- [ ] `tests/specify_cli/widen/test_review.py` — stubs present (full tests in WP10).
- [ ] `mypy src/specify_cli/widen/review.py` exits 0.
- [ ] `ruff check src/specify_cli/widen/review.py` exits 0.

## Risks

- **`click.edit()` in non-interactive environments (CI):** Returns `None` or the original text when no `$EDITOR` is set. Default to `text` (unchanged) if `click.edit()` returns `None`.
- **Stdin blocking:** The `threading.Thread` approach for stdin read works on POSIX. On Windows, use `sys.stdin.readline()` with a different timeout approach if needed.

## Reviewer Guidance

Verify: `_determine_source("PostgreSQL.", "PostgreSQL with replicas.")` returns `MISSION_OWNER_OVERRIDE` (>30% different). Verify: `_determine_source("PostgreSQL.", "")` returns `MANUAL`. Verify: the instruction block printed to stdout matches §5.1 format character-for-character (tests should assert substrings). Verify: `source_hint` in `CandidateReview` is from LLM; the provenance written to `summary_json.source` is from `_determine_source()` (they may differ).

## Activity Log

- 2026-04-23T17:14:21Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=77777 – Started implementation via action command
- 2026-04-23T17:20:34Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=77777 – Ready for review: run_candidate_review fully implemented — §5.1 block, 30s stdin LLM read, §6 rich panel, [a/e/d] handlers with provenance, 45 tests passing, ruff+mypy clean
- 2026-04-23T17:21:42Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=78631 – Started review via action command
- 2026-04-23T17:24:31Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=78631 – Moved to planned
- 2026-04-23T17:25:31Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=79087 – Started implementation via action command
- 2026-04-23T17:29:33Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=79087 – Cycle 2: persist summary_json provenance on accept/edit
- 2026-04-23T17:30:29Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=79598 – Started review via action command
- 2026-04-23T17:31:58Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=79598 – Review passed: summary_json provenance persistence chain complete, signature additive with optional default, all 3 new provenance tests passing, 258 passed / 2 skipped, ruff+mypy clean.
