# Research — CLI Widen Mode & Decision Write-Back

**Mission:** `cli-widen-mode-and-write-back-01KPXFGJ`

Design decisions locked during discovery. Each section records the chosen option and why alternatives were rejected.

---

## R-1: Entry Affordance for Widen Mode

**Question:** How should the user enter Widen Mode from within a live interview?

### Options Considered

| Option | Description |
|---|---|
| A | Drop to a separate `spec-kitty widen <decision_id>` shell command. User exits the interview. |
| B | Dedicated `[w]` prompt only shown if LLM detects a widen signal. |
| C | LLM auto-widens without human confirmation (no affordance needed). |
| **D (chosen)** | **Inline `[w]` always present in per-question prompt when prereqs satisfied. LLM may nudge (FR-021) but human confirms (C-001).** |

### Rationale

**D chosen.** The inline affordance is the lowest-friction path: it keeps the user inside the interview flow, avoids context-switching to a separate command (which would require re-navigating to the right question), and is consistent with the existing `[d]efer | [!cancel]` options that are always present. Suppression is prereq-gated (FR-003), not signal-gated, so the affordance is predictably available to qualified users.

**A rejected** because it breaks the interview flow and requires the user to re-enter the interview after widening — a friction cliff for what should be a fast escalation. It also forces the CLI to handle re-entry state, complicating the decision lifecycle.

**B rejected** because LLM-gated visibility creates an unpredictable UX: users who know they want to widen have to wait for or coax an LLM signal. The LLM suggestion (FR-021) is better as an informational hint, not a gate.

**C rejected explicitly** by C-001: "LLM may suggest; LLM never auto-widens." Widening has real team-facing consequences (Slack post, participant invitations). Human confirmation is non-negotiable.

---

## R-2: Pause Semantics After Widen

**Question:** After the owner confirms a widen, what happens to the interview?

### Options Considered

| Option | Description |
|---|---|
| A | Always block — interview pauses at this question until resolved. |
| B | Always continue — interview parks the question and moves on. |
| **C (chosen)** | **[b/c] prompt with `b` (block) as default. Owner chooses per question.** |
| D | No pause — widen fires and the interview continues silently to the next question. |

### Rationale

**C chosen with `b` default.** The per-question choice honors the fact that some decisions are gating (the answer affects all later questions) while others are incidental (the interview can proceed without blocking). The `b` default reflects the most common expectation: if you bothered to widen a question, you probably want to wait for the answer before continuing. But forcing block on every widen would make the CLI unusable for missions with multiple widened questions, which is why `[c]` is available.

**A rejected** because it prevents parallelism for missions that can widen multiple questions and continue the rest of the interview while Slack discussions run. This is exactly the secondary scenario (spec.md §User Scenarios).

**B rejected** because silent continuation is wrong for high-stakes gating questions. The owner needs to choose.

**D rejected** because it gives no signal that widen happened from within the interview flow — the owner loses track of pending widened questions. Worse, it means the interview can "complete" with unresolved widened questions, which is a surprise at finalization time.

---

## R-3: Slack Thread Closure Trigger

**Question:** Who or what closes the Slack discussion thread when a widened decision is resolved?

### Options Considered

| Option | Description |
|---|---|
| i | CLI posts a closure message directly to Slack via Slack API. |
| **ii (chosen)** | **CLI calls `decision resolve` (local). SaaS observes the terminal state on the widened decision. `spec-kitty-saas #111` posts the closure message to Slack as a downstream effect.** |
| iii | User manually closes the Slack thread. CLI does nothing. |

### Rationale

**ii chosen.** This is the correct separation of concerns. The CLI's job is to record the terminal state; SaaS's job is to orchestrate Slack. Posting to Slack from the CLI would require the CLI to carry Slack credentials (a security surface) and replicate Slack-posting logic that already lives in #111. C-004 is explicit: "Slack closure messages are a `spec-kitty-saas #111` responsibility triggered by observing the terminal state on a widened decision. This mission does NOT post to Slack directly."

**i rejected** per C-004. Also imposes a Slack token on the CLI, which is the wrong trust model.

**iii rejected** because it creates unresolved Slack threads with no signal that the decision is done. Participants would be left wondering whether the discussion is still open.

---

## R-4: Write-Back UX

**Question:** How should the owner review and accept a candidate summary + answer after widened discussion is fetched?

### Options Considered

| Option | Description |
|---|---|
| A | Auto-accept candidate answer with no review step. |
| **B refined (chosen)** | **`[a]ccept | [e]dit | [d]efer` prompt. Candidate rendered in a `rich.Panel`. `[e]` opens pre-filled editor. Material edit detection for provenance tagging.** |
| C | Always open editor with candidate pre-filled; no accept shortcut. |
| D | Free-text prompt; candidate shown as default; override by typing. |

### Rationale

**B refined to `[a/e/d]` chosen.** Three-way split gives the owner the full choice surface: fast-path accept (FR-014), precision editing (FR-015, FR-016), or explicit deferral (FR-017). The `[a]` path is zero-friction for cases where the candidate is good. The `[e]` path handles cases where the candidate needs tuning. The `[d]` path keeps decisions honest — defer is always available.

Material edit detection (FR-015, FR-016) is straightforward: compare normalized edit output against the candidate answer; if Levenshtein distance > threshold (or if the edit is empty, indicating a fresh write), tag `source=mission_owner_override` or `source=manual` accordingly.

**A rejected** because it violates C-001 (human-gated) and SC-005 (owner must be able to correct a materially wrong candidate summary).

**C rejected** because it makes the common case (good candidate → accept) require more keystrokes than necessary. The `[a]` shortcut is worth the extra branching.

**D rejected** because a free-text prompt doesn't convey the three distinct semantic outcomes (accept, edit, defer) clearly, and it doesn't naturally surface the provenance distinction between "I edited the candidate" vs "I wrote this fresh."

---

## R-5: Summary Production Model

**Question:** Who produces the candidate summary and candidate answer from the fetched Slack discussion?

### Options Considered

| Option | Description |
|---|---|
| A (rejected) | SaaS produces the summary server-side when discussion is fetched. |
| **B (chosen)** | **The active local CLI LLM session (Claude Code, Codex, or equivalent) summarizes the fetched discussion. SaaS is pure state transport.** |

### Rationale

**B chosen.** C-002 is unambiguous: "SaaS performs no inference in V1." The architectural rationale is that the CLI's active LLM session already has the project context (spec, mission, prior interview answers). It is better positioned to produce a decision-relevant summary than a generic server-side inference pass. Server-side inference would also require SaaS to carry model API credentials and inference budget, which is not appropriate for V1.

The local LLM surfacing pattern is described in R-7.

**A rejected** per C-002 and the architectural correction locked during discovery.

---

## R-6: Prereq Detection

**Question:** How are the three prereqs (Teamspace membership, Slack integration, SaaS reachability) checked, and what happens when they fail?

### Approach Chosen

All three checked at interview start via `check_prereqs()` (single synchronous call with short timeouts). Result cached for the duration of the interview. If `all_satisfied=False`, `[w]` is suppressed silently from every question prompt — no error banner, no explanation in the interview UX (C-009, FR-003, SC-004).

- **Teamspace membership**: auth context derived from session token (`SPEC_KITTY_SAAS_TOKEN`). If token absent or invalid, `teamspace_ok=False`. No separate API call needed if the token payload includes membership claims.
- **Slack integration**: `GET /api/v1/teams/{slug}/integrations`. Returns a list of configured integrations; CLI checks for `"slack"` in the list. Timeout 500ms. If timeout or error → `slack_ok=False`.
- **SaaS reachability**: `GET /api/v1/health`. Timeout 500ms. If network error → `saas_reachable=False`.

### Rationale for Silent Suppression

Noisy prereq errors would interrupt the interview for users who have never set up SaaS/Slack. The charter interview is local-first (C-007) and must work without SaaS. Silently dropping `[w]` from the prompt is the correct UX: users who see `[w]` know they have the capability; users who don't see it are unaffected. A future `spec-kitty doctor widen` diagnostic (noted out of scope for V1, spec.md §Out of Scope) can explain why `[w]` is missing.

### Alternatives Rejected

- **Lazy per-question check**: adds 300ms latency per prompt, violating NFR-001. Pre-check at interview start is correct.
- **Hard error on missing prereqs**: breaks C-007 (local-first). Wrong for users without SaaS.
- **Poll in background during interview**: adds complexity for a V1 feature; prereqs are stable within a session.

---

## R-7: Local LLM Surfacing Pattern

**Question:** Since the CLI itself contains no embedded LLM, how does the active harness LLM (Claude Code, Codex, etc.) produce the candidate summary and candidate answer during a live CLI session?

This is the most architecturally novel element of this mission.

### Context

The `specify_cli` codebase explicitly does not call LLM APIs (`charter.py:1086`). The active harness LLM is always the user's IDE or terminal agent (Claude Code, Codex, etc.) that is driving the CLI interactively. The CLI is a subprocess of the LLM session, not the other way around.

### Chosen Pattern: Structured Tool-Output Prompt Contract

When the CLI needs the LLM to produce a candidate summary + answer, it:

1. **Fetches** the discussion data from SaaS (`SaasClient.fetch_discussion(decision_id)` → `DiscussionData`).
2. **Renders** a structured prompt block to `stdout` (via `rich.Console`) that is structured so the active LLM session will read it as an instruction. The format is:

```
╔══════════════════════════════════════════════════════════╗
║  WIDEN SUMMARIZATION REQUEST                             ║
║  decision_id: <ulid>                                     ║
║  question: <interview question text>                     ║
╚══════════════════════════════════════════════════════════╝

[DISCUSSION DATA]
Participants: Alice, Carol
Messages: 7
Thread URL: https://...

<message 1>
<message 2>
...

Please produce a candidate summary and candidate answer in this exact format:
```json
{
  "candidate_summary": "<concise summary of the discussion>",
  "candidate_answer": "<proposed answer to the question>",
  "source_hint": "slack_extraction"
}
```
```

3. **Reads** the LLM's response from the next stdin input. The CLI's `run_candidate_review()` function blocks on `input()` after rendering the instruction block, waiting for the LLM to paste the JSON response block.
4. **Parses** the JSON block (Pydantic `CandidateReview` model).
5. **Presents** the parsed candidate to the owner for `[a/e/d]` review.

### Why This Works

The CLI is always invoked from within an active LLM session (that's the entire spec-kitty usage model). When the CLI prints a structured instruction to stdout, the active LLM session reads it as tool output and responds. The CLI then reads the LLM's response from stdin. This is exactly how all other spec-kitty slash commands work: the LLM harness drives the CLI, reads its output, and feeds structured responses back.

### Fallback: LLM Unavailable or Times Out

If no valid JSON block is received within `NFR-003`'s 30s timeout (or if the block fails to parse), `run_candidate_review()` falls back to:
- Displaying the raw discussion data (participant list, thread URL, raw messages up to 50).
- Opening the editor pre-filled with blank — owner writes the answer manually.
- Tagging `source=manual`.

This satisfies SC-005 and the "Discussion fetch fails" and "LLM summarization fails" edge cases in spec.md.

### Alternatives Rejected

- **Direct `anthropic` SDK call**: rejected per existing architecture. The CLI does not carry API keys. Would create a hard anthropic dependency, break offline/local-first (C-007), and duplicate inference cost.
- **SaaS-side summarization endpoint**: rejected per C-002. SaaS does not infer in V1.
- **Write candidate to a temp file and have the LLM read it**: adds file system complexity for no benefit. stdout/stdin is the natural channel.
- **Skip summarization; always open editor blank**: valid fallback but not the primary path. Owners get a better experience from a candidate they can accept/edit vs writing from scratch every time.

---

## R-8: Pending-External-Input Storage

**Question:** How should the CLI track which widened questions are in `pending-external-input` state (user chose `[c]`ontinue) during an interview?

### Chosen Approach: Per-Mission JSONL Sidecar

`kitty-specs/<slug>/widen-pending.jsonl` — one `WidenPendingEntry` per line. Written immediately when user chooses `[c]`. Read at end-of-interview pass. Entries removed after resolution.

### Rationale

- **Survives process crash/restart**: if the CLI exits mid-interview, the sidecar preserves pending state. On next run, the end-of-interview pass can still surface the pending questions.
- **Consistent with existing patterns**: `status.events.jsonl` uses the same JSONL-per-mission pattern. JSONL is append-friendly and human-readable.
- **Lightweight**: no DB, no in-memory-only approach that would be lost on crash.
- **Per-mission**: scoped to the mission dir, consistent with `decisions/` artifacts.

### Alternatives Rejected

- **In-memory only**: lost on crash or Ctrl+C. Acceptable for V1? Possibly, but the sidecar adds almost zero implementation cost and provides durability.
- **Append to `decisions/index.json`**: would require adding a non-standard status to `DecisionStatus`; the index is designed for terminal outcomes + open state. Mixing in a pending-external-input state would pollute the existing decisions schema.
- **SQLite**: overkill for a per-mission list of at most ~20 entries.
- **`.kittify/` level**: wrong scope — pending state is per-mission, not per-repo.
