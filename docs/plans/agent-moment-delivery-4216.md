---
title: Agent moment delivery policy
updated: '2026-09-11'
type: explanation
audience: automation-agent
---

# Agent moment delivery policy

Issue: #4216. Governed Op: `01M2808ND3ATY3DGYTG470R04A`.

An agent should discover unfamiliar missions and mission-less activity in the
single repository it requested. `team` changes admission within that scope; it
does not enumerate credentials or subscribe to additional repositories.
`mine` means locally known missions, not authenticated assignment.

## Approach and boundaries

One delivery service applies the same settings, canonical event identity,
receipt checks and event budget to CLI and MCP. The existing stream remains the
raw transport. Retained history is an explicit catch-up/replay source, using the
relay's existing `/managed/events` endpoint and its coverage metadata.

A receipt means the logical consumer acknowledged the returned batch. MCP
clients pass the previous `receipt` back as `acknowledge` on their next call;
this avoids recording failed tool delivery as read. CLI acknowledges only after
successful output and flush. Unacknowledged batches may be offered again.
Receipts store identities and timestamps, never event prose. Outstanding batches
reserve rolling-minute quota without being marked read; an atomic reservation
check prevents concurrent polls from multiplying that quota. A stable consumer
identifier must be shared across reconnects and CLI/MCP processes; it must not
be the authenticated human account. Without one, only process-local continuity
is possible and the result says so explicitly.

Receipt contexts include the consumer, requested repo, relay admission metadata and
effective filters. Legacy credentials without team/host/repo metadata start a
fresh context on rotation conservatively;
no opaque credential is decoded or treated as proof of authorization. The relay
continues to enforce the actual authorization boundary. No account-wide mark-read
flag exists. Source event IDs are normalized through the event contract package;
frames without a source event ID use relay epoch and sequence. Replay ignores
receipts intentionally, but still respects settings and context bounds.

## Design decisions and limitations

- Receipts are acknowledged explicitly, not on frame selection or rate rejection.
- A bounded receipt store fails explicitly when full instead of forgetting old
  identities silently. It contains no local event archive.
- Withheld frames do not advance a delivery cursor. Catch-up re-reads retained
  history and suppresses receipts before spending the context budget.
- Existing history is bounded and volatile. `gap`/`reset` and truncation remain
  visible; an empty result does not establish that nothing ever happened.
- Relay #295 is still open. Current publish ACK contains only `request_id` and
  `received_at`; `session_ref` is derived with private relay salt. No safe local
  own-publisher filter exists. Results report that capability unavailable, and
  this work remains draft pending its contract and command/reader integration.
- Relay #296 owns race-safe history/live handoff. Explicit history and live watch
  here remain separate reads, with overlap deduplicated after acknowledgement;
  this implementation does not claim a gap-free initial snapshot/live handoff.

## Issue matrix

| Issue | Claim | Delivery |
|---|---|---|
| spec-kitty/spec-kitty#4216 | Assigned and `status:claimed`; Op above | Client defaults/policy/receipts/catch-up; draft pending own-identity integration |
| spec-kitty/spec-kitty-zeitgeist#295 | External dependency | Verified publisher/subscriber identity and relay own-event suppression |
| spec-kitty/spec-kitty-zeitgeist#296 | External dependency | Initial snapshot and race-safe history/live handoff |

## Tooling friction

The prep inventory rejects the current owner-qualified CLI name. Its historical
`spec-kitty` entry follows GitHub's redirect to `spec-kitty/spec-kitty` correctly.
`uv sync --frozen --all-extras` warmed the checkout; pytest separately constructs
its own cached subprocess environment. The installed Spec Kitty dispatch opened
the Op and loaded governance; no mission or fabricated workflow state was created.
