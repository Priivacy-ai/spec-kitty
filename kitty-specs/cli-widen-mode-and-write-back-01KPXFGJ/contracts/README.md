# Contracts Index — CLI Widen Mode & Decision Write-Back

**Mission:** `cli-widen-mode-and-write-back-01KPXFGJ`

This directory contains CLI-side contracts only. SaaS endpoint schemas are owned by spec-kitty-saas #110 (widen + audience-default) and #111 (Slack orchestration + discussion fetch). Do not duplicate them here.

---

## Files in this directory

| File | Contents |
|---|---|
| `README.md` | This index |
| `cli-contracts.md` | CLI prompt format specs: `[w]iden` affordance, `[b/c]` pause prompt, `[a/e/d]` review prompt, blocked-prompt behavior, LLM summarization request/response format, LLM suggestion hint format |
| `widen-state.schema.json` | JSON Schema for `widen-pending.jsonl` sidecar entries (`WidenPendingEntry`) |
| `review-payload.schema.json` | JSON Schema for the candidate-review internal payload (`CandidateReview`) produced by the active LLM session |

---

## Contract Ownership Notes

- `[w]iden` prompt text, `[b/c]` prompt text, `[a/e/d]` prompt text: owned here.
- `POST /api/v1/decision-points/{id}/widen` request/response schema: owned by spec-kitty-saas #110.
- `GET /api/v1/missions/{id}/audience-default` response schema: owned by spec-kitty-saas #110.
- Discussion fetch response schema (`DiscussionData`): owned by spec-kitty-saas #111.
- `decision resolve` call signature (existing): owned by spec-kitty #757.

---

## Versioning

All schemas carry `"schema_version": 1`. Breaking changes require a version bump and a migration note.
