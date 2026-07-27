# Contract: Op Record Events (v2)

File: `kitty-ops/<invocation_id>.jsonl` — append-only JSONL, one event per line.

## Started event

```json
{"event":"started","invocation_id":"01KTK5JBD69FQ8XVRFV1J630MJ","profile_id":"implementer-iris","action":"implement","request_text":"fix that bug","actor":"claude","mode_of_work":"task_execution","governance_context_hash":"d5ccab5678dcc4c8","governance_context_available":true,"router_confidence":"canonical_verb","started_at":"2026-06-10T20:00:00+00:00"}
```

Rules: write-once (exclusive create); `action` non-empty; `mission_id`/`wp_id` present only when non-null.

## Completed event

```json
{"event":"completed","invocation_id":"01KTK5JBD69FQ8XVRFV1J630MJ","completed_at":"2026-06-10T20:25:00+00:00","outcome":"done","closed_by":"agent","evidence_ref":".kittify/evidence/01KTK5JBD69FQ8XVRFV1J630MJ"}
```

Rules: `outcome` required ∈ {done, failed, abandoned}; `closed_by` required ∈ {agent, doctor_sweep}; no started-only fields; appended at most once (`AlreadyClosedError` on repeat); `evidence_ref` omitted when None and refused for advisory/query modes.

## Unchanged events

`artifact_link`, `commit_link`, `glossary_checked` retain their existing shapes.

## Git behavior

- Open Op (started only): file remains uncommitted in working tree.
- At close: record auto-committed, message `op(<profile-id>): <action> [<id8>]` (grep-able via `git log --grep="^op("`), including sweep closes.

## SaaS propagation envelope

Envelope dicts are rebuilt from the v2 models; shape follows the events above 1:1 (decision 01KTSJEQANMNEV16WMSAJP6FR1 — no wire-compat with the pre-mission envelope). Propagation remains async, best-effort, gated by `resolve_checkout_sync_routing()`; errors append to `kitty-ops/propagation-errors.jsonl`.
