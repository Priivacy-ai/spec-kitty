# Trail Model

*Operator reference for the Phase 4 runtime consumption baseline.*

## Overview

Every profile invocation in Spec Kitty — whether triggered by `advise`, `ask`, or `do` — leaves an auditable trail. The trail serves three purposes:

1. **Local accountability**: operators can reconstruct what happened on any checkout without SaaS connectivity.
2. **SaaS coherence**: the dashboard timeline shows the same history as the local audit log.
3. **Governance provenance**: downstream retrospective and doctrine work can reference specific invocations.

## Minimal Viable Trail

**One JSONL file per invocation, written locally before the executor returns.**

Every `advise`, `ask`, and `do` call writes a `started` event to:

```
.kittify/events/profile-invocations/{invocation_id}.jsonl
```

When `spec-kitty profile-invocation complete` is called, a `completed` event is appended to the same file.

This is the unconditional minimum — it is always written, regardless of SaaS connectivity, charter state, or sync configuration. The data model is defined in `src/specify_cli/invocation/record.py`.

## Mode-of-Work Taxonomy

Every invocation belongs to one of four work modes. The mode determines which optional trail tiers are eligible — it does not override the mandatory Tier 1 rule.

| Mode | Description | Example actions | Tier 2 eligible | Tier 3 eligible |
|------|-------------|-----------------|-----------------|-----------------|
| `advisory` | Pure routing/context advisory, no durable output | `advise` | No | No |
| `task_execution` | Produces a checkable output (code change, review, test run) | `ask`, `do` (non-mission) | Yes (caller-triggered) | No |
| `mission_step` | One step in a governed mission workflow | `specify`, `plan`, `tasks`, `merge`, `accept` | Yes (caller-triggered) | Yes |
| `query` | Read-only, no execution | `profiles list`, `invocations list` | No | No |

Mode-of-work is derived deterministically at runtime from the CLI entry command and recorded on the `started` event as the `mode_of_work` field. Runtime enforcement is active: `profile-invocation complete --evidence` is rejected for invocations in `advisory` or `query` mode (see "Mode Enforcement at Tier 2 Promotion" below).

### Mode Enforcement at Tier 2 Promotion

`spec-kitty profile-invocation complete --evidence <path>` is rejected with `InvalidModeForEvidenceError` when the target invocation's `mode_of_work` is `advisory` or `query`. The enforcement runs **before** any write, so the invocation remains open and uncommitted — rerun `complete` without `--evidence` to close cleanly.

Pre-mission records (invocations opened before this enforcement landed) have no `mode_of_work` field and are accepted by enforcement — legacy behaviour is preserved. See ADR-002-mode-derivation.md for the full derivation table and rationale.

## Trail Tiers

### Tier 1 — Every Invocation (mandatory)

Written unconditionally before the executor returns.

- **Storage**: `.kittify/events/profile-invocations/{invocation_id}.jsonl`
- **Content**: Two JSONL lines — a `started` event and (after completion) a `completed` event.
- **When**: All `advise`, `ask`, and `do` invocations.

### Glossary Check Event (conditional, Tier 1)

When the invocation executor's glossary chokepoint scan detects at least one
conflict — or encounters an error — it appends a `glossary_checked` event to the
same Tier 1 JSONL file, immediately after the `started` event.

**Written ONLY when:**
- `all_conflicts` is non-empty (one or more semantic conflicts detected), OR
- `error_msg` is non-null (the chokepoint scan encountered an unexpected exception).

**Clean invocations produce NO `glossary_checked` line.** This keeps Tier 1
files minimal when there are no glossary issues to report.

Example `glossary_checked` event line:

```json
{"event": "glossary_checked", "invocation_id": "01HXYZ...", "matched_urns": ["glossary:d93244e7"], "high_severity": [{"term": "lane", "conflict_type": "ambiguous_scope", "severity": "HIGH", "candidate_senses": ["execution lane (WP routing)", "git branch lane (worktree)"]}], "all_conflicts": [...], "tokens_checked": 8, "duration_ms": 2.7, "error_msg": null}
```

Readers that encounter `"event": "glossary_checked"` and do not recognise this
event type may safely skip the line — it is additive metadata and never affects
the `started`/`completed` pair.

### Correlation Links (Tier 1 extension)

`spec-kitty profile-invocation complete` accepts two additional flags that append correlation events to the invocation JSONL:

- `--artifact <path>` — repeatable. Each value appends one `{event: "artifact_link", invocation_id, kind, ref, at}` line to `.kittify/events/profile-invocations/<id>.jsonl`. Refs are stored repo-relative when the resolved path is under the checkout, absolute otherwise.
- `--commit <sha>` — singular. Appends one `{event: "commit_link", invocation_id, sha, at}` line.

Both events are append-only (never mutate existing lines) and readable by a single-file scan. Readers that do not recognise these event types may safely skip the line — the same additive-reader invariant that protects `glossary_checked`.

See ADR-001-correlation-contract.md for the design; contracts/profile-invocation-complete.md for the CLI shape.

### Tier 2 — Evidence Artifact (optional, caller-triggered)

Created when the caller explicitly flags that the invocation produced checkable output.

- **Trigger**: Caller sets `--evidence <path>` on `spec-kitty profile-invocation complete`.
- **Storage**: `.kittify/evidence/{invocation_id}/evidence.md` and `.kittify/evidence/{invocation_id}/record.json`
- **When**: `task_execution` and `mission_step` modes only.

### Tier 3 — Durable Project State (optional, action-driven)

Promotion to `kitty-specs/` or doctrine artifacts only when the invocation changes project-domain state.

- **Trigger**: Action is in `TIER_3_ACTIONS` — `{specify, plan, tasks, merge, accept}`.
- **Storage**: `kitty-specs/{mission_slug}/` — existing spec/plan/tasks/status files.
- **When**: `mission_step` mode only.

### Promotion Rules

```
Tier 1 always written
  |
  +-- If caller sets evidence_ref --> Tier 2 artifact created
  |
  +-- If action in TIER_3_ACTIONS --> Tier 3 artifacts produced by workflow
```

## SaaS Read-Model Policy

Projection is conditional on `CheckoutSyncRouting.effective_sync_enabled`. When sync is disabled for a checkout, no events are emitted — even if the user is authenticated. When sync is enabled and the user is authenticated, Spec Kitty consults `src/specify_cli/invocation/projection_policy.py::POLICY_TABLE` to decide per `(mode_of_work, event)` what to project.

| mode_of_work | event | project | include_request_text | include_evidence_ref |
|--------------|-------|---------|----------------------|----------------------|
| advisory | started | yes | no | no |
| advisory | completed | yes | no | no |
| advisory | artifact_link | no | — | — |
| advisory | commit_link | no | — | — |
| task_execution | started | yes | yes | no |
| task_execution | completed | yes | yes | yes |
| task_execution | artifact_link | yes | no | no |
| task_execution | commit_link | yes | no | no |
| mission_step | started | yes | yes | no |
| mission_step | completed | yes | yes | yes |
| mission_step | artifact_link | yes | no | no |
| mission_step | commit_link | yes | no | no |
| query | any | no | — | — |

Pre-mission records (no `mode_of_work`) project under the `task_execution` rules — the legacy 3.2.0a5 behaviour is preserved for them.

Policy is additive and resolvable from code/config alone. See ADR-003-projection-policy.md for the rationale.

Projection is additive. Events accumulate; there is no deletion, replay-based overwrite, or idempotency-key gating in 3.2.

## Tier 2 SaaS Projection — Deferred

**Status**: Tier 2 evidence artifacts (`.kittify/evidence/<invocation_id>/evidence.md` and `record.json`) are **local-only** in the 3.2.x release line. They are not uploaded to SaaS. This decision was finalised by the Phase 4 closeout mission (ADR-004-tier2-saas-deferral.md).

**Reasoning**:
1. The shipped 3.2.0a5 baseline already behaves this way; operators observing the product today see local-only evidence.
2. SaaS projection of evidence bodies requires privacy, redaction, and size-limit design that lies outside the Phase 4 closeout scope.
3. Future projection remains possible without contract change — a later epic can read the existing local artifact and emit its own envelope.

**Revisit trigger**: any of (a) a named future epic accepts SaaS evidence projection as scope, (b) operators actively request the feature with a concrete use case, (c) a regulatory or audit requirement mandates centralised retention.

## Retention and Redaction

| Field | Treatment |
|-------|-----------|
| `request_text` | Retained as-written in local JSONL. No automatic redaction in 3.2. |
| `governance_context_hash` | First 16 hex chars of SHA-256 only. Full governance context is never persisted. |
| JSONL files | Persist indefinitely unless the operator purges `.kittify/events/`. |
| SaaS propagation | Additive. No delete-on-disable in 3.2. |

Propagation failures are written to `.kittify/events/propagation-errors.jsonl` and never affect the CLI exit code.

## `spec-kitty intake` — Not a Profile Invocation

`spec-kitty intake` ingests a plan document into `.kittify/mission-brief.md` for use by `/spec-kitty.specify` brief-intake mode. It is **not** a profile invocation and produces no `InvocationRecord`. The governed trail begins when the host calls `spec-kitty advise`, `ask`, or `do` — not when the user stages a brief.

## Host surfaces that teach the trail

The advise/ask/do surface is taught to host LLMs through per-host skill packs. See [`docs/host-surface-parity.md`](host-surface-parity.md) for the authoritative matrix of supported hosts and each host's parity status.

## `spec-kitty explain` — Deferred to Phase 5

`spec-kitty explain` (issue #534) is not part of this release. It requires Phase 5 DRG glossary addressability to produce fully-cited answers. A partial implementation without glossary citations would be misleading.
