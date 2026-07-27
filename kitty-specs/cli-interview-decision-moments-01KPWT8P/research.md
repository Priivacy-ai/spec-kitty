# Research — CLI Interview Decision Moments

Phase 0 research for mission `cli-interview-decision-moments-01KPWT8P`.
All decisions were resolved during discovery; this document preserves the ADR rationale per DIRECTIVE_003.

## R-1 — Emission boundary: CLI-owned ledger, dual-caller

**Decision:** New `spec-kitty agent decision ...` CLI subgroup is the sole ledger API. Two callers: charter (Python, direct) and specify/plan (LLM-driven, template-instructed).

**Rationale:** Matches the #757 prompt's "ask time, not persistence time." Keeps identity minting in the CLI (single source of truth). Reuses the same API across Python-driven charter and LLM-driven specify/plan flows.

**Alternatives considered:**
- Persistence-time reconstruction — rejected (violates ask-time requirement; post-hoc inference from chat transcripts is fragile).
- Two separate APIs (Python API for charter, CLI for LLM) — rejected (drift risk, duplicate logic).

## R-2 — V1 scope: charter + specify + plan only

**Decision:** Tasks is out of scope. Widening to Slack is out of scope (`#758`). SaaS sync is out of scope (`#110`, `#111`).

**Rationale:** Tight scope slice aligned with #757 issue text. Tasks has no interview loop today — deferring lets us decide later whether to add one. Widening and SaaS are separate contract boundaries.

**Alternatives considered:** Include all flows — rejected (explodes blast radius; #758 explicitly owns Widen).

## R-3 — Idempotency semantics

**Decision:** `decision open` is idempotent on logical key `(mission_id, origin_flow, step_id|slot_key, input_key)`. Non-terminal match → return existing `decision_id` (no new event, no new artifact). Terminal match → structured `already_closed` error with existing `decision_id` and terminal outcome. Terminal commands idempotent on exact re-call; contradictory re-call → `DECISION_TERMINAL_CONFLICT`.

**Rationale:** LLM retries are real. Append-only event log + idempotent CLI commands = safe retry semantics. No silent auto-revival of closed decisions (if a question needs re-asking, caller must mint a new decision with a different slot_key).

**Alternatives considered:**
- Every call mints a new `decision_id` — rejected (duplicate decisions for the same logical question pollute the paper trail).
- Auto-revive on terminal retry — rejected (masks user intent).

## R-4 — Paper trail layout + step_id fallback

**Decision:** Flat `kitty-specs/<mission>/decisions/` tree. `index.json` (machine-readable) + `DM-<decision_id>.md` (human-readable). Events to existing `status.events.jsonl`. `decision open` requires either `--step-id` or `--slot-key`; no fallback hashing.

**Rationale:** Flat is greppable. `origin_flow` as metadata not directory. Single event log (no second per-decision log). Explicit slot keys make the LLM's question identity unambiguous and keeps idempotency keys stable across retries.

**Alternatives considered:** Per-flow subdir, events-only (no artifact tree), co-located with charter answers — all rejected. Hash-of-question-text for step_id — rejected (fragile under rewording).

## R-5 — `decision_id` format

**Decision:** Plain ULID (26-char Crockford base32). No `DM-` prefix on the wire. Filename convention `DM-<decision_id>.md` provides identification at the filesystem level.

**Rationale:** Matches existing events-contract convention (`decision_point_id: str`). Avoids `DM-DM-<ulid>.md` filename collision. Time-sortable.

**Alternatives considered:** `DM-<ulid>` on wire — rejected (filename collision). Composite semantic key — rejected (couples identity to renames).

## R-6 — Dependency bump to spec-kitty-events 4.0.0

**Decision:** Bump `spec-kitty-events` pin from `==3.3.0` to `==4.0.0`. Refresh vendored copy at `src/specify_cli/spec_kitty_events/` from the 4.0.0 source tree. Any existing ADR-style DecisionPoint emitter adds `origin_surface="adr"`.

**Rationale:** `DecisionPointOpenedInterviewPayload`, `DecisionPointResolvedInterviewPayload`, and `terminal_outcome` exist only in 4.0.0. Shipping against 3.3.0 would be knowingly mismatched.

**Alternatives considered:** Stay on 3.3.0 — rejected (new event types unavailable).

## R-7 — Migration posture for charter.answers.yaml and sentinels

**Decision:** (a) `.kittify/charter/interview/answers.yaml` remains primary charter state in V1; DecisionMoments are audit overlay for charter and primary typed state for specify/plan. (b) `[NEEDS CLARIFICATION: …]` markers stay LLM-authored with an adjacent hidden anchor `<!-- decision_id: <decision_id> -->`. `decision verify` is the gate that enforces marker↔decision consistency. Check-only in V1 (no auto-fix, no CLI doc patching).

**Rationale:** Low-risk V1. Future mission can flip to DecisionMoment-primary without re-spec. LLM stays in charge of natural-language doc composition. Hidden anchor makes verification robust without polluting human-readable output.

**Alternatives considered:** DecisionMoment primary with answers.yaml derived — deferred to later mission. CLI doc-patching — rejected (invasive).
