# CLI Widen Mode & Decision Write-Back

**Mission ID:** `01KPXFGJXXCV25X3T9DWGME5V1`
**Issue:** `spec-kitty#758`
**Created:** 2026-04-23
**Target branch:** `main`

## Purpose

Add CLI Widen Mode — an inline affordance during charter/specify/plan interviews that lets the mission owner escalate an interview question to Teamspace collaboration via Slack, then review a locally-summarized discussion and write back the approved answer.

## Context

Spec Kitty V1 Decision Moments (mission #757) let missions record interview questions locally. The next step is widening — letting a mission owner pull the team in for a decision that needs more input.

V1 keeps the control model **human-gated** (LLM may suggest, human confirms) and the inference model **local-first** (the active Claude Code / Codex CLI session summarizes fetched discussion; SaaS is pure state transport). This mission adds the CLI-side UX: the `[w]` affordance, audience review/trim, interview pause semantics (per-question block-or-continue choice with pause as default), candidate review via `[a/e/d]`, and the local-answer-closes-Slack path.

This mission depends on the SaaS work in `spec-kitty-saas #110` (widen endpoint + audience-default API) and `spec-kitty-saas #111` (Slack orchestration + discussion/transcript fetch surface). It does NOT reimplement any of those.

## Domain Language

| Canonical term | Meaning | Synonyms to avoid |
|---|---|---|
| **Widen** | The mission owner escalates a single interview question to Teamspace collaboration via Slack. Triggered from inside the live interview, human-confirmed. | "Share", "Broadcast" |
| **Widen Mode** | The inline CLI UX flow: audience review → trim → confirm widen → interview pause choice. | "Widen Wizard" |
| **Candidate summary / candidate answer** | The locally-produced (CLI's active LLM session) rollup of widened discussion + proposed answer, shown to the mission owner for review before write-back. | "SaaS summary" (SaaS does not produce inference in V1) |
| **Write-back** | Resolving the widened DecisionPoint terminally, using the accepted/edited candidate answer. Handled via the existing `decision resolve` path. | "Commit", "Finalize" |
| **Pending external input** | A widened question the interview has moved past (user chose `[c]`ontinue) awaiting external resolution. Surfaced at interview completion. | "Parked", "Pending" |
| **Prereqs satisfied** | Teamspace membership exists AND Slack integration configured for the team AND SaaS reachable. All three required before `[w]` is shown. | "Ready" |
| **Inline widen UX** | The `[w]` affordance is always present in the per-question prompt when prereqs are satisfied. No out-of-band subcommand required for users. | "Command mode" |

## User Scenarios & Testing

### Primary scenario — happy path (widen → block → summarize → accept)

1. Owner runs `spec-kitty charter interview --mission <slug>`.
2. At question 3, the prompt shows: `[enter]=accept default | [text]=type answer | [w]iden | [d]efer | [!cancel]`.
3. Owner presses `w`.
4. CLI calls `GET /api/v1/missions/{id}/audience-default` (repo 3); renders: *"Default consulted audience for this decision: Alice, Bob, Carol, Dana. [Enter] to confirm, or type comma-separated names to trim."*
5. Owner trims to `Alice, Carol` and confirms.
6. CLI calls `POST /api/v1/decision-points/{id}/widen` with trimmed invite list. SaaS stamps `widened_at` and creates `DecisionPointParticipation` rows (repo 3). #111 posts the discussion to Slack.
7. CLI asks: `Block here or continue with other questions? [b/c] (default: b)`. Owner presses Enter → `b`.
8. Interview is blocked at question 3. CLI polls (or waits on signal) for discussion activity.
9. After Alice and Carol have contributed on Slack, the CLI fetches discussion data via #111's query surface.
10. The active local LLM session produces a candidate summary + candidate answer from the fetched discussion.
11. CLI renders: fetched discussion context + candidate summary + candidate answer. Prompts `[a]ccept | [e]dit | [d]efer`.
12. Owner presses `a` → CLI calls `decision resolve` with `final_answer=candidate` and `summary_json={text, source=slack_extraction, ...}`. `rationale` stays empty unless owner added one.
13. Interview resumes at question 4. The widened DecisionPoint is `resolved`. SaaS observes the terminal state; #111 posts closure to the Slack thread.

### Secondary scenario — continue-on-widen, resolve at end

1. Same as primary 1–6.
2. At step 7, owner presses `c` → `continue`. Question 3 enters `pending-external-input` state.
3. Interview continues through questions 4–10. Each question that gets widened enters the pending-external-input list.
4. At interview completion, CLI surfaces: *"3 widened questions still pending. Resolve them now."*
5. For each, CLI fetches discussion + produces local candidate + shows `[a/e/d]` review.
6. Owner handles each; writes back via `decision resolve`. After all are resolved (or explicitly deferred), interview finalizes and writes `answers.yaml`.

### Tertiary scenario — local answer closes Slack discussion

1. Same as primary 1–7 (blocked).
2. Before the discussion produces a useful candidate, owner types `session`  as a plain text answer at the blocked prompt.
3. CLI detects a terminal local answer → calls `decision resolve` with `final_answer=session`, `summary_json=null` (or preserves any pre-fetched transcript with `source=manual`).
4. SaaS observes the terminal state; #111 posts *"Resolved locally — this decision has been closed"* to the Slack thread and marks the discussion closed.
5. Interview resumes at question 4.

### Edge cases

- **Prereqs not satisfied.** If the user is not in any Teamspace, or the team has not configured Slack, or SaaS is unreachable, the `[w]` option is suppressed from the prompt. Existing `[enter]=default | [text]=answer | [d]efer | [!cancel]` still work (local-first).
- **Widen during specify or plan.** Same UX applies in `/spec-kitty.specify` and `/spec-kitty.plan` interview flows (not just charter). Origin flow is recorded accordingly.
- **Owner cancels mid-Widen Mode.** During audience review or trim, owner can press `[Esc]` or type `cancel`. No `widen` call is made. Returns to the interview prompt unchanged.
- **LLM suggests widen but owner declines.** LLM's suggestion is informational only. Prompt still shows the full option set; owner chooses.
- **Discussion fetch fails.** CLI shows the raw available data (participant list, thread URL) and falls back to `[e]dit` with blank pre-fill — owner can manually write the answer. `summary.source=manual`.
- **Local LLM summarization fails.** Same fallback: show raw discussion data, prompt owner to write the answer manually. `summary.source=manual`.
- **Owner edits answer to something materially different from candidate.** CLI prompts for optional rationale (not required).
- **Duplicate widen on same decision.** Disallowed. `[w]` is suppressed on questions that are already widened. The per-question prompt shows current state instead (e.g., `[pending-external-input]` with option to fetch/resolve).
- **Widen on already-resolved decision.** Disallowed; `[w]` is not shown.
- **LLM never suggests.** Normal; `[w]` is user-initiated in that case. The LLM hint is an assist, not a gate.

## Domain Language: Local-LLM Inference Model

This section is explicit because it's a common misconception.

**What SaaS does** (owned by #110 + #111):
- Stores DecisionPoint state, widened_at, participants
- Stores Slack thread/session metadata
- Provides a discussion fetch surface (transcript or message list)

**What SaaS does NOT do** (in V1):
- Summarization
- Inference
- Candidate answer generation

**What the CLI's active LLM session does** (this mission):
- Fetches discussion data from SaaS
- Produces the candidate summary (from fetched discussion)
- Produces the candidate answer (from fetched discussion)
- Renders both to the owner for review + approval

**Provenance** (persisted in `summary_json.source`):
- `slack_extraction`: CLI LLM summarized from fetched Slack discussion as-is
- `mission_owner_override`: CLI LLM summarized, owner materially edited
- `manual`: owner wrote the summary fresh (discussion fetch failed, or owner disregarded CLI LLM output)

## Functional Requirements

| ID | Status | Requirement |
|---|---|---|
| FR-001 | proposed | `spec-kitty agent charter interview` shall show `[w]iden` as an inline prompt option when prereqs are satisfied. Option is suppressed when any prereq is missing. |
| FR-002 | proposed | `spec-kitty agent specify` and `spec-kitty agent plan` interview flows shall show `[w]` under the same prereq rule. |
| FR-003 | proposed | Prereq check: user must be a Teamspace member AND the team must have Slack integration configured AND SaaS must be reachable. All three, or `[w]` is suppressed. |
| FR-004 | proposed | Pressing `w` shall enter inline Widen Mode: fetch the mission's audience-default (`GET /api/v1/missions/{id}/audience-default` from #110), render the member list, accept a trimmed subset. |
| FR-005 | proposed | Widen Mode shall call `POST /api/v1/decision-points/{id}/widen` (from #110) with the trimmed invite list and the source `decision_id` of the interview question. |
| FR-006 | proposed | Widen Mode shall support cancel: user can exit without invoking the widen endpoint; interview prompt resumes unchanged. |
| FR-007 | proposed | After successful widen, CLI shall prompt: `Block here or continue with other questions? [b/c]` with default `b`. |
| FR-008 | proposed | `b` (block) shall pause the interview at this question until a resolution path is taken (accept candidate, edit candidate, type local answer, or explicitly defer/cancel). |
| FR-009 | proposed | `c` (continue) shall mark the question as `pending-external-input` in local state, and interview shall proceed to the next question. |
| FR-010 | proposed | At interview completion, any `pending-external-input` questions shall be surfaced for explicit resolution; interview is not considered complete until all such questions are resolved or deferred. |
| FR-011 | proposed | When returning to a widened question (either via `b`-path unblock or end-of-interview pass), CLI shall fetch discussion data for the decision via the `spec-kitty-saas #111` Slack discussion fetch surface. |
| FR-012 | proposed | The active local LLM session (Claude Code, Codex, or equivalent) shall produce a candidate summary and candidate answer from the fetched discussion. |
| FR-013 | proposed | CLI shall render: the fetched discussion context (or a compact form), the candidate summary, and the candidate answer. Owner prompt is `[a]ccept | [e]dit | [d]efer`. |
| FR-014 | proposed | `a` (accept) shall call `decision resolve` with `final_answer=candidate answer`, `summary_json={text: candidate summary, source: "slack_extraction", ...}`, `rationale=None`. |
| FR-015 | proposed | `e` (edit) shall open an editor pre-filled with the candidate answer. On save, CLI shall detect whether the owner's answer materially differs from the candidate. If yes, prompt (optionally) for a rationale. |
| FR-016 | proposed | After edit save: `final_answer=edited answer`, `summary_json={text: edited-or-accepted summary, source: "mission_owner_override" if summary/answer edited substantially OR "manual" if the owner deleted everything and wrote fresh}`, `rationale=owner-supplied or empty`. |
| FR-017 | proposed | `d` (defer) shall transition the DecisionPoint to `deferred` via `decision defer` with an owner-supplied rationale. The widened state remains recorded but no `final_answer` is written. |
| FR-018 | proposed | Typing a plain text answer at a blocked widened prompt (before the `[a/e/d]` review step) shall call `decision resolve` with `final_answer=typed answer`, `summary_json={source: "manual"}` with empty text, `rationale=None`. |
| FR-019 | proposed | The local-answer-at-blocked-prompt path shall NOT post directly to Slack. It calls `decision resolve`; SaaS observes the new terminal state; `spec-kitty-saas #111` posts closure to the Slack thread as a downstream effect. |
| FR-020 | proposed | Widen is suppressed on already-widened or already-terminal (`resolved`/`deferred`/`canceled`) DecisionPoints. The prompt shows the current state instead. |
| FR-021 | proposed | LLM-suggested widen: when the active LLM session detects a strong widening signal (e.g., question is high-stakes, or user explicitly asks "should I widen this?"), it may include a suggestion hint in the prompt ("This looks like a good widen candidate; press `w` to consult the team."). The suggestion is informational; the `[w]` option remains human-initiated regardless. |
| FR-022 | proposed | A `spec-kitty agent decision widen <decision_id> --invited <list>` internal primitive subcommand shall exist as the implementation hook for FR-005. Not surfaced to end users in `--help` by default; exists for automation/testing. |

## Non-Functional Requirements

| ID | Status | Requirement |
|---|---|---|
| NFR-001 | proposed | The `[w]` option rendering, prereq check, and audience-default fetch combined shall add no more than 300ms of perceptible latency to interview prompt rendering at p95. |
| NFR-002 | proposed | Discussion fetch on return-to-widened-question shall succeed within 3s at p95 when SaaS is reachable; timeout at 10s with fallback to manual. |
| NFR-003 | proposed | Local-LLM summarization timeout: 30s maximum. On timeout, fall back to raw-discussion display + manual edit. |
| NFR-004 | proposed | The CLI shall never block the interview indefinitely on a widened question; if `b`-path block exceeds 60 minutes of real-time inactivity, CLI shall surface a reminder prompt ("Still waiting on widened discussion. Check Slack, type a local answer, or `[d]efer`.") |
| NFR-005 | proposed | New tests: aggregate suite add ≤ 90s to the full test run. |
| NFR-006 | proposed | Project type-checking (`mypy`) and linting (`ruff`) remain clean on all new code. |

## Constraints

| ID | Status | Requirement |
|---|---|---|
| C-001 | proposed | Widening is always human-gated. LLM may suggest; LLM never auto-widens. |
| C-002 | proposed | SaaS performs no inference in V1. Candidate summary and candidate answer are produced by the local CLI LLM session from SaaS-fetched discussion data. |
| C-003 | proposed | The canonical widen state transition lives in `spec-kitty-saas #110`. This mission calls the widen endpoint; it does NOT create participation rows or stamp `widened_at` directly. |
| C-004 | proposed | Slack closure messages are a `spec-kitty-saas #111` responsibility triggered by observing the terminal state on a widened decision. This mission does NOT post to Slack directly. |
| C-005 | proposed | `summary_json.source` field values are restricted to: `slack_extraction`, `mission_owner_override`, `manual`. No other source values in V1. |
| C-006 | proposed | `rationale` field stays owner-authored. The CLI shall never auto-populate rationale from a discussion summary. |
| C-007 | proposed | Local-first: missions run without SaaS/Slack continue working. `[w]` affordance is suppressed; `open/resolve/defer/cancel` keep working locally as in mission #757. |
| C-008 | proposed | The inline `[w]` affordance is the sole user-facing entry point to Widen Mode. No "drop to another command" required for users. The internal `decision widen` subcommand (FR-022) is implementation only; not promoted in end-user docs. |
| C-009 | proposed | Prereq suppression of `[w]` is silent — no noisy error. The interview UX just doesn't offer the option when prereqs aren't met. A `spec-kitty doctor widen` diagnostic command may optionally report why `[w]` is unavailable, but that's out of scope for V1. |
| C-010 | proposed | Duplicate widening on the same decision is disallowed. `[w]` is not shown on already-widened decisions. |
| C-011 | proposed | Widening on already-terminal decisions is disallowed. `[w]` is not shown. |

## Key Entities

- **DecisionPoint** (existing, V1 extended in mission #757 + #110). This mission adds no new columns; it consumes the widened-state lifecycle.
- **Interview prompt** (existing in `charter.py`, being extended). This mission adds the `[w]` affordance + pause-semantics prompt + blocked-prompt behavior.
- **Widen Mode flow** (new CLI module, e.g., `src/specify_cli/widen/`). Owns: prereq detection, audience review, trim UX, widen-endpoint client, pause-semantics prompt.
- **Pending widened decisions state** (new, per-mission JSONL file or in-memory during interview). Tracks questions in `pending-external-input` state.
- **Candidate review renderer** (new). Renders fetched discussion, candidate summary, candidate answer, and the `[a/e/d]` prompt.

## Success Criteria

| ID | Criterion |
|---|---|
| SC-001 | A mission owner can press `w` during a charter interview, trim the default audience to 2 people, confirm widen, and see the Slack discussion appear — all within 60 seconds of keypress (subject to network). |
| SC-002 | When the owner chooses `b` and blocks on a widened question, and then types a local answer, the Slack thread closes automatically within 30 seconds via downstream #111 behavior. |
| SC-003 | When the owner chooses `c` and continues through 3 questions, the interview completion pass surfaces the 3 pending widened questions and the owner can resolve each with `[a]`, `[e]`, or `[d]` without restarting the CLI. |
| SC-004 | A mission where the user isn't in any Teamspace completes normally; `[w]` is never shown; the existing interview paths work as in mission #757. |
| SC-005 | When the candidate summary produced by the local LLM is materially wrong, the owner can press `[e]`, delete the pre-fill, type a fresh answer, and the persisted summary carries `source=manual`. |
| SC-006 | Over a full interview with 10 questions, the interactive performance stays below 300ms perceptible latency per prompt (NFR-001), with or without widen used. |
| SC-007 | When a widened discussion never produces enough signal and the owner simply wants to answer locally, they can do so at the blocked prompt without having to unwind the widen first. |
| SC-008 | The CLI honors all three widen surfaces (`charter`, `specify`, `plan`) equivalently: same prompt affordance, same Widen Mode UX, same review/write-back. |

## Assumptions

- `spec-kitty-saas #110` ships the widen endpoint + audience-default endpoint with the contracts written in its contracts/ directory (committed).
- `spec-kitty-saas #111` ships a discussion-fetch surface that returns enough data for the local LLM to produce a useful summary. Exact shape TBD in #111's contracts; this mission adapts to whatever #111 exposes.
- The active CLI LLM session has enough context window to summarize a Slack discussion with up to ~50 messages. Longer discussions may need pagination or windowing; V1 accepts truncation with a notice to the owner.
- The user's authenticated SaaS session is the source of truth for Teamspace membership detection. No separate identity flow.
- Slack integration is checked via a lightweight team-scoped SaaS endpoint (e.g., `GET /api/v1/teams/{slug}/integrations` or equivalent — exact contract from #111).
- `spec-kitty-events 4.0.0` is the canonical wire format; all widen-related events use that.

## Out of Scope (for this mission)

- Slack message posting (closure, notification, anything to Slack): owned by `spec-kitty-saas #111`.
- Widen endpoint implementation, audience-default computation, invited-participant row creation, `widened_at` stamping: owned by `spec-kitty-saas #110`.
- Non-Slack channels (email, Teams, mobile push): out of V1.
- Widen on ADR-origin DecisionPoints (V1 is interview-origin only): out of scope.
- `spec-kitty doctor widen` diagnostic: noted as future work.
- Auto-widen by LLM (no human confirm): explicitly forbidden by C-001.
- Persistent LLM-suggestion learning (remembering what user accepts/rejects for future suggestions): out of V1.

## Dependencies

- `spec-kitty-saas #110` — widen endpoint + audience-default endpoint + extended DecisionPoint schema. **Hard dependency** for FR-004, FR-005.
- `spec-kitty-saas #111` — Slack orchestration + discussion/transcript fetch surface. **Hard dependency** for FR-011, FR-019.
- `spec-kitty #757` (mission `cli-interview-decision-moments-01KPWT8P`, now merged) — `decision open/resolve/defer/cancel` service API. **Hard dependency** for FR-014, FR-016, FR-017, FR-018.
- `spec-kitty-events 4.0.0` — wire format; already vendored.

## Notes

- The coordination path with #110 and #111 matters. Ideal sequencing: #110 ships first (or is already in plan/tasks and this mission can stub its endpoints for tests); #111 ships second; this mission (#758) is last in the dependency chain.
- An implementation plan option is to integrate with #110 and #111 contracts via a thin CLI client layer — mocked in tests, so this mission can be developed before #111 is fully merged, as long as #111's discussion-fetch response shape is stable.
