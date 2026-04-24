# CLI Prompt Contracts — CLI Widen Mode & Decision Write-Back

**Mission:** `cli-widen-mode-and-write-back-01KPXFGJ`

These contracts define the exact prompt strings, option sets, and structured output formats for all new CLI surfaces introduced by this mission. Implementers must match these formats exactly; tests must assert against them.

---

## §1. Per-Question Interview Prompt

### 1.1 Standard prompt (prereqs NOT satisfied or decision already widened/terminal)

Identical to mission #757 baseline:

```
<question text> [<default>]:
[enter]=accept default | [text]=type answer | [d]efer | [!cancel]
```

### 1.2 Widen-enabled prompt (prereqs satisfied, decision open, not already widened)

```
<question text> [<default>]:
[enter]=accept default | [text]=type answer | [w]iden | [d]efer | [!cancel]
```

`[w]iden` is appended between `[text]=type answer` and `[d]efer`. No other changes to the baseline prompt.

### 1.3 Already-widened question prompt (decision in widened state, pending-external-input)

```
<question text> [pending-external-input]
[f]etch & resolve | [local answer]=type answer | [d]efer | [!cancel]
```

`[f]etch & resolve` enters `run_candidate_review()`. Plain text answer triggers the local-answer-at-blocked-prompt path (FR-018).

### 1.4 LLM suggestion hint (FR-021, optional)

When the active LLM session detects a strong widen signal, it may prepend a dim hint line before the prompt. The CLI reads a special structured prefix from the LLM output:

```
[WIDEN-HINT] This looks like a good widen candidate — press w to consult the team.
```

The CLI detects lines starting with `[WIDEN-HINT]` in the current harness output context and renders them as `[dim]<text>[/dim]` above the prompt. The hint does not change the available options; `[w]` is always present regardless (FR-021, C-001).

Format invariant: `[WIDEN-HINT] ` prefix (case-sensitive, with trailing space) followed by the hint text. Single line only. CLI strips the prefix before rendering.

---

## §2. Widen Mode — Audience Review Prompt

Entered after user presses `w`. Fetches `GET /api/v1/missions/{id}/audience-default`.

### 2.1 Audience display

```
╭─ Widen: <question text (truncated to 60 chars)> ──────────────────╮
│ Default audience for this decision:                                │
│   Alice Johnson, Bob Smith, Carol Lee, Dana Park                   │
│                                                                    │
│ [Enter] to confirm, or type comma-separated names to trim.        │
│ Type "cancel" or press Ctrl+C to abort.                            │
╰────────────────────────────────────────────────────────────────────╯
Audience >
```

### 2.2 Trim input parsing

- Empty input (Enter) = use full default list.
- Comma-separated input = trim to named subset. Names are matched case-insensitively against the default list. Unknown names produce a warning but are not blocked (owner may know team members not in the default).
- `cancel` (case-insensitive) = abort Widen Mode; no widen call made (FR-006).
- Ctrl+C = same as `cancel`.

### 2.3 Confirmation display

```
Audience confirmed: Alice Johnson, Carol Lee (2 members)
Calling widen endpoint...
```

On error from SaaS:

```
[red]Widen failed:[/red] <error message>
Returning to interview prompt.
```

---

## §3. Pause Semantics Prompt (`[b/c]`)

Shown after successful `POST /widen` response (FR-007).

```
╭─ Widened ✓ ────────────────────────────────────────────────────────╮
│ Slack thread created. Alice Johnson and Carol Lee have been        │
│ invited to discuss: "<question text (truncated)>"                  │
╰────────────────────────────────────────────────────────────────────╯

Block here or continue with other questions? [b/c] (default: b):
```

- `b` or Enter → `WidenAction.BLOCK` (FR-008).
- `c` → `WidenAction.CONTINUE` (FR-009).

On `[c]`:

```
Question parked as pending. You'll be prompted to resolve it at end of interview.
```

---

## §4. Blocked-Prompt Behavior

Entered when user chose `[b]`. The interview is paused at this question (FR-008).

```
╭─ Waiting for widened discussion ───────────────────────────────────╮
│ Question: <question text>                                          │
│ Participants: Alice Johnson, Carol Lee                             │
│ Slack thread: https://...                                          │
╰────────────────────────────────────────────────────────────────────╯

Options:
  [f]etch & review   — fetch current discussion and produce candidate
  <type an answer>   — resolve locally right now (closes Slack thread)
  [d]efer            — defer this question for later

Waiting >
```

### 4.1 Inactivity reminder (NFR-004)

If the blocked prompt is idle for 60 minutes (real-time), the CLI re-renders:

```
[yellow]Still waiting on widened discussion.[/yellow]
Check Slack, type a local answer, or press d to defer.

Waiting >
```

This is implemented via a background thread or non-blocking `select`/`signal` approach. The reminder fires once; subsequent inactivity periods fire again.

### 4.2 Local answer at blocked prompt (FR-018)

If the user types plain text (not `f`, `d`, `!cancel`) at `Waiting >`:

- The input is treated as the `final_answer`.
- CLI calls `decision.resolve(final_answer=<typed text>, summary_json={"source": "manual", "text": ""})`.
- CLI prints: `Resolved locally. SaaS will close the Slack thread shortly.`
- Interview resumes at next question.

### 4.3 `[f]etch & review` path

Fetches discussion from SaaS (#111 endpoint), then enters the LLM Summarization Request flow (§5), then enters `[a/e/d]` Review Prompt (§6).

---

## §5. LLM Summarization Request / Response Contract

The CLI emits a structured instruction block to stdout that the active LLM session interprets as a task. The LLM responds with a structured JSON block.

### 5.1 CLI-emitted instruction block

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
[Carol Lee] Agreed, but let's make sure we consider the migration path.
[Alice Johnson] Good point. I'd say: PostgreSQL, plan migration from day 1.
... (4 more messages)
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

### 5.2 Expected LLM response format

The LLM must respond with exactly the JSON block — no prose, no markdown wrapping (the ` ```json ` fence is part of the instruction, not the response). CLI parses the response by extracting content between `{` and `}` (JSON object extraction with error handling).

**Valid response example:**
```json
{
  "candidate_summary": "Team consensus is PostgreSQL with migration-from-day-1 planning. Alice and Carol both agree on the direction.",
  "candidate_answer": "PostgreSQL, with migration path planned from day 1.",
  "source_hint": "slack_extraction"
}
```

### 5.3 Fallback on parse failure or timeout

If no valid JSON is received within 30s (NFR-003), or if parsing fails:

```
[yellow]Summarization timed out or produced invalid output.[/yellow]
Showing raw discussion. Please write the answer manually.

[a]ccept empty | [e]dit (blank pre-fill) | [d]efer
```

The CLI enters the `[a/e/d]` prompt with empty `candidate_summary` and `candidate_answer`. If owner types an answer via `[e]`, `source=manual`.

---

## §6. `[a/e/d]` Candidate Review Prompt (FR-013, FR-014, FR-015, FR-017)

Shown after a successful LLM summarization response.

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

### 6.1 `[a]ccept` path (FR-014)

- Calls `decision.resolve(final_answer=candidate_answer, summary_json={"text": candidate_summary, "source": "slack_extraction"})`.
- No rationale prompt (C-006: rationale stays owner-authored).
- Prints: `[green]Decision resolved.[/green]`

### 6.2 `[e]dit` path (FR-015, FR-016)

- Opens `$EDITOR` (or `VISUAL`) pre-filled with the candidate answer text.
- On save, CLI computes normalized edit distance between saved text and candidate answer.
- If distance > 30% of candidate length OR saved text is empty → `source=mission_owner_override` (or `manual` if empty).
- If minor/no change → `source=slack_extraction`.
- If owner changed the answer materially, CLI prompts: `Optional rationale (press Enter to skip):`.
- Calls `decision.resolve(final_answer=edited_answer, summary_json={"text": summary_text, "source": <determined above>}, rationale=<owner-supplied or None>)`.

### 6.3 `[d]efer` path (FR-017)

- Prompts: `Rationale for deferral (required):`.
- Calls `decision.defer(rationale=<owner-supplied>)`.
- Prints: `[yellow]Decision deferred.[/yellow]`
- The widened state is preserved in SaaS; the Slack thread remains open.

---

## §7. End-of-Interview Pending Pass (FR-010)

Shown at interview completion when `WidenPendingStore.list_pending()` returns non-empty.

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

Each pending question proceeds through §5 (LLM summarization) and §6 (`[a/e/d]` review). After all are resolved or deferred, the interview finalizes and writes `answers.yaml`.

If the owner defers all pending questions without resolving: the interview completes normally; the deferred decisions carry `status=deferred` in the decisions index.
